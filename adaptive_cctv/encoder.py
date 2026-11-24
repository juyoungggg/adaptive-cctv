import argparse
import os
import shutil
import subprocess

# Draft values from docs/DESIGN.md.
DEFAULT_HIGH_CRF = 20
DEFAULT_LOW_CRF = 32
DEFAULT_PRESET = "medium"


def plan_segments(duration, intervals):
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
    # passthrough + demux time base keep every frame and its exact timestamp on VFR input.
    _run(["ffmpeg", "-y", "-v", "error", "-i", video_path, "-map", "0:v:0", "-an",
          "-c:v", "libx264", "-preset", preset, "-crf", str(crf)] + params +
         ["-fps_mode", "passthrough", "-enc_time_base:v", "demux", output_path])


def _event_zones(frame_times, segments, crf):
    # crf= inside zones is not in x264's documentation; verified on libx264 via ffmpeg 9.0.2.
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
    _require_ffmpeg()
    segments = plan_segments(_duration(video_path), intervals)
    zones = _event_zones(_frame_times(video_path), segments, high_crf)
    _encode(video_path, output_path, low_crf, preset, zones)
    return segments


def encode_uniform(video_path, output_path, crf=DEFAULT_HIGH_CRF, preset=DEFAULT_PRESET):
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
