# Design

The design of adaptive-cctv as agreed by the team: decisions, module interfaces, event
definitions, storage quality, datasets, and evaluation. Values marked provisional or draft
are not final.

## Pipeline

```
CCTV video (mp4)
  -> frame sampling at 0.1 s intervals (10 fps)
  -> vehicle detection       in: frame HxWx3   out: bbox, class, conf
  -> vehicle class filter    COCO ids 2 car, 3 motorcycle, 5 bus, 7 truck
  -> multi-object tracking   in: bbox + conf   out: Kalman-smoothed bbox + track_id
  -> per-track trajectory and pixel speed
  -> event detection         sudden stop / path deviation
  -> events to high-quality time intervals
  -> encoder                 normal: low quality, event interval: high quality
```

Video is processed in 5-second chunks. Event logic sees the previous chunk plus the
current one (10 s), so tracks that cross a chunk boundary stay intact.

## Settled decisions

| Item | Decision | Note |
| --- | --- | --- |
| Detector | YOLO26n, COCO-pretrained, via Ultralytics | Nano model chosen for CPU speed. Write `YOLO26` / `YOLO11` without a `v`. |
| Confidence threshold | 0.4 | Set by the team; no comparison across values was recorded. |
| Inference size | `imgsz=1280` | Value used in the team's tracking code. |
| Tracker | ByteTrack (Ultralytics built-in) | `model.track(frame, persist=True, tracker="bytetrack.yaml", classes=[2, 3, 5, 7], conf=0.4)` |
| Frame interval | 0.1 s maximum | Tracking lost many targets at longer intervals. |
| Camera | Fixed | Motion is measured in pixels, which only holds for a static camera. |
| Speed | Per-vehicle ratio, never absolute px/s | Pixel speed varies with perspective, so only a vehicle's own before/after is comparable. |
| Quality levels | Two (normal / event) | A 0-100 importance score with graded quality is backlog. |
| Frame-level switch | One vehicle in an event puts the whole frame in high quality | Keeps quality control simple; high quality holds until every event has ended. |

## Team modules and data contracts

The modules were written separately by different team members and are integrated in this
repository.

| Module | Interface |
| --- | --- |
| Tracking | `TrackCar(video_path, chunk_seconds=5)` yields one chunk of tracking data at a time. `findtraj(chunk)` returns per-track trajectories. `findspeed(trajectories)` returns per-track pixel speed (px/s). |
| Visualization | `visualize()` draws bboxes, track ids, and the last 3 s of each path on the video. `save_csv()` writes frame, time, track id, center, and confidence. |
| Sudden stop | `EventDetector_SuddenStop().update(trajectories)` returns events for the chunk. `events_to_intervals(events, pre, post, merge_gap)` returns merged `(start, end)` high-quality intervals. |
| Path deviation | Draft only: `check_lane_departure_events(trajectory)` returns a bool for one vehicle. |
| Encoder | Not written. Consumes the `(start, end)` intervals. |

Shapes:

```python
# one detection (tracking output)
{"frame": int, "time": float, "track_id": int, "class_id": int, "class_name": str,
 "confidence": float, "bbox": [x1, y1, x2, y2], "center": [cx, cy]}

# trajectories
{track_id: [{"time": float, "center": [cx, cy]}, ...]}

# event: every detector emits at least these four keys
{"type": str, "track_id": int, "time": float, "center": [cx, cy]}
```

## Event definitions

All thresholds are provisional and will be tuned on real data.

### Sudden stop

A vehicle's current speed falls to 30% or less of its own recent speed. Two versions exist
and have not been reconciled:

| | Reported at the midterm | Draft code (2026-11-20) |
| --- | --- | --- |
| Reference | displacement over the preceding 0.5 s | median speed 0.6-2.5 s ago |
| Current | displacement over the last 0.5 s | median speed over the last 0.5 s |
| Trigger | 70% drop, held for a further 0.5 s | current <= 0.3 x reference, reference >= 30 px/s |
| End / repeat | variation within 20% of pre-drop for 2 s | 5 s cooldown per vehicle |
| Track gap | not specified | history reset after a gap over 1.0 s |

Known limits of the draft: a jam in which all vehicles slow together can be flagged, and a
vehicle already stopped when first seen is not detected.

### Path deviation

Either condition:

- Zigzag: 2 or more lane changes within 4 s, staying in the middle lane for 1.5 s or less.
  Ends after 3 s in one lane with no further change.
- Lane departure: on the shoulder or off the road for 1 s or more. Ends after returning to
  the normal area and staying there for 2 s.

How lanes are obtained is undecided. The draft splits the frame width into three fixed
columns, which only works when lanes run straight up the image. The options on the table
are lane detection, per-camera lane polygons, or comparing a vehicle's direction vector
against surrounding traffic.

### High-quality window

Keep high quality for 5 s after an event ends. The pre-event window is 5 s in the plan and
`pre=3.0` in the draft code; not reconciled. A new event during the tail extends the
window.

## Storage quality (draft values)

| Segment | Resolution | Frame rate | CRF |
| --- | --- | --- | --- |
| Event | 1080p | 30 fps | about 20 |
| Normal | 480p | 10-15 fps | about 32 |

- The encoder is not chosen. Changing bitrate or QP is to be tried before changing
  resolution mid-stream, to avoid stutter at the switch.
- Savings must come from the encoded file. Downscaling for display does not count.
- A ring buffer keeps pre-event footage available at high quality.

## Datasets

- **Main:** AI Hub "National Highway CCTV Abnormal Driving Detection" data
  (<https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71566>). About 2.1M images with
  per-frame bboxes and normal/abnormal labels, in 6-second clips of 60 images at 10 fps.
  The rate matches the pipeline's 0.1 s interval, so images in order form real-speed video.
- **Used for tracking tests:** TU-DAT (road traffic anomalies).
- **Extension (undecided):** AI City Challenge 2021 Track 4 (stalled vehicles and crashes
  on highway CCTV) or AI City Challenge 2024 WTS (pedestrian-centric, caption labels).

## Evaluation

Advisor feedback after the midterm fixed the priority: measure how well events are
detected, quantitatively, before anything qualitative.

- **Event detection (primary):** missed events and false detections against labeled
  ground truth, reported as precision, recall, and F1.
- **Storage reduction:** store the same video with the baseline (all high quality) and
  with this system, then compare file size (MB), reduction (%), bitrate (Mbps), and
  storage per hour (GB/h).
  - `bitrate_mbps = file_size_mb * 8 / duration_s`
  - `avg_after = (R_high * T_event + R_low * T_normal) / T_total`
  - `reduction = 1 - avg_after / R_high`
- **Qualitative (secondary):** 5-point scales for agreement with human judgment under
  adverse conditions and for smoothness of the quality switch.

A missed event is worse than a false one: a miss leaves the evidence in low quality, a
false detection only costs some storage.

## Open items

- Reconcile the two sudden-stop definitions and the pre-event window (3 s or 5 s).
- Decide how lanes are obtained for path deviation.
- Agree on one event `type` name per event (the sudden-stop draft uses both `sudden_stop`
  and `hard_brake`).
- Choose and implement the encoder, then run the storage-reduction experiments.
- Choose the extension dataset.
- Tune event thresholds on real data.
- Add supporting features: remaining storage capacity, lane information, lighting and
  weather, traffic congestion.
