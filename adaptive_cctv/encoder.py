"""Differential H.264 encoding: event segments at high quality, the rest at low quality.

Per-segment CRF is applied in a single libx264 pass with x264 zones, so the video is
never cut and the source timestamps (including variable frame rate) pass through as is.
"""

import argparse
import os
import shutil
import subprocess

# Draft values from docs/DESIGN.md; provisional until tuned on real data.
DEFAULT_HIGH_CRF = 20
DEFAULT_LOW_CRF = 32
DEFAULT_PRESET = "medium"


def plan_segments(duration, intervals):
    """Split [0, duration] into ordered (start, end, is_event) segments.

    Intervals are clamped to [0, duration]; empty ones are dropped and overlapping or
    touching ones are merged. Gaps become normal segments. No segment has zero length.
    """
    duration = float(duration)
    if duration <= 0:
        return []
    merged = []
    for start, end in sorted((max(0.0, float(s)), min(duration, float(e))) for s, e in intervals):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    segments = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor:
            segments.append((cursor, start, False))
        segments.append((start, end, True))
        cursor = end
    if cursor < duration:
        segments.append((cursor, duration, False))
    return segments


def _require_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise RuntimeError("%s not found on PATH; ffmpeg must be installed" % tool)


def _run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    if result.returncode != 0:
        raise RuntimeError("%s failed:\n%s" % (cmd[0], result.stderr.strip()))
    return result.stdout


def _frame_times(video_path):
    """Presentation times in seconds of every video frame, relative to the first frame."""
    out = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "packet=pts_time", "-of", "csv=p=0", video_path])
    times = sorted(float(line.split(",")[0]) for line in out.split()
                   if line and line.split(",")[0] != "N/A")
    if not times:
        raise RuntimeError("no video frames found in %s" % video_path)
    return [t - times[0] for t in times]


def _duration(video_path):
    out = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=duration", "-of", "csv=p=0", video_path]).strip()
    if out and out != "N/A":
        return float(out)
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", video_path]).strip()
    return float(out)


def _encode(video_path, output_path, crf, preset, zones=None):
    params = ["-x264-params", "zones=" + zones] if zones else []
    # passthrough + demux time base: no frame is duplicated or dropped, and VFR
    # timestamps are not rounded to the default 1/r_frame_rate encoder time base.
    _run(["ffmpeg", "-y", "-v", "error", "-i", video_path, "-map", "0:v:0", "-an",
          "-c:v", "libx264", "-preset", preset, "-crf", str(crf)] + params +
         ["-fps_mode", "passthrough", "-enc_time_base:v", "demux", output_path])


def _event_zones(frame_times, segments, crf):
    """x264 zones (inclusive frame ranges) for event segments; a frame belongs to the
    segment that contains its presentation time, the last segment being closed.

    x264 applies a zone's crf= through encoder reconfiguration; its --help lists only
    q= and b=, so this relies on behaviour verified with the installed libx264.
    """
    zones = []
    for i, (start, end, is_event) in enumerate(segments):
        if not is_event:
            continue
        final = i == len(segments) - 1
        idx = [n for n, t in enumerate(frame_times) if start <= t and (final or t < end)]
        if idx:
            zones.append("%d,%d,crf=%s" % (idx[0], idx[-1], crf))
    return "/".join(zones)


def encode_differential(video_path, intervals, output_path, high_crf=DEFAULT_HIGH_CRF,
                        low_crf=DEFAULT_LOW_CRF, preset=DEFAULT_PRESET):
    """Encode one H.264 MP4 with event intervals at high_crf and the rest at low_crf.

    Returns the planned (start, end, is_event) segments.
    """
    _require_ffmpeg()
    segments = plan_segments(_duration(video_path), intervals)
    zones = _event_zones(_frame_times(video_path), segments, high_crf)
    _encode(video_path, output_path, low_crf, preset, zones)
    return segments


def encode_uniform(video_path, output_path, crf=DEFAULT_HIGH_CRF, preset=DEFAULT_PRESET):
    """Encode the whole video at one CRF; the baseline for measuring storage savings."""
    _require_ffmpeg()
    _encode(video_path, output_path, crf, preset)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m adaptive_cctv.encoder",
        description="Encode event intervals at high quality and the rest at low quality.")
    parser.add_argument("video", help="input video")
    parser.add_argument("output", help="output MP4")
    parser.add_argument("--interval", action="append", nargs=2, type=float, default=[],
                        metavar=("START", "END"),
                        help="event interval in seconds; repeatable")
    parser.add_argument("--high-crf", type=int, default=DEFAULT_HIGH_CRF,
                        help="CRF for event segments (default %(default)s)")
    parser.add_argument("--low-crf", type=int, default=DEFAULT_LOW_CRF,
                        help="CRF for normal segments (default %(default)s)")
    args = parser.parse_args(argv)

    segments = encode_differential(args.video, args.interval, args.output,
                                   high_crf=args.high_crf, low_crf=args.low_crf)
    for start, end, is_event in segments:
        quality = "high (CRF %d)" % args.high_crf if is_event else "low (CRF %d)" % args.low_crf
        print("%8.3f - %8.3f s  %s" % (start, end, quality))
    in_size = os.path.getsize(args.video)
    out_size = os.path.getsize(args.output)
    print("input:  %d bytes" % in_size)
    print("output: %d bytes (%.1f%% of input)" % (out_size, 100.0 * out_size / in_size))


if __name__ == "__main__":
    main()
