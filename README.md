# adaptive-cctv

Importance-based differential storage for fixed traffic CCTV.

CCTV records every scene at the same high quality, so storage fills quickly and footage
cannot be kept for as long as it should be. adaptive-cctv detects abnormal driving in the
video and stores only those segments at high quality. Normal segments are stored at low
quality, which cuts the total storage needed.

This is a university capstone project (2026 fall semester).

## How it works

```mermaid
flowchart TD
  A[CCTV video] --> B[Frame sampling<br/>every 0.1 s]
  B --> C[Vehicle detection<br/>YOLO26n]
  C --> D[Vehicle tracking<br/>ByteTrack]
  D --> E[Trajectory and pixel speed<br/>per vehicle]
  E --> F[Sudden stop detector]
  E --> G[Path deviation detector]
  F --> H[High-quality intervals]
  G --> H
  H --> I[Encoder]
  I --> J[Stored video<br/>normal: low quality<br/>event: high quality]
```

The current scope is an offline pipeline that runs on recorded video on a PC. Real-time
and on-camera operation are future work.

## Status

Tracking, the sudden-stop detector, and a path-deviation draft are in the repository as
separate modules. They are not connected into one pipeline yet, and the encoder is not
written.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

Run from the repository root. Videos are not included in the repository; pass the path to
your own file.

```bash
# Print each vehicle's recent positions and pixel speed, in 5-second chunks
.venv/bin/python -m adaptive_cctv.tracking <video>

# Write a copy of the video with boxes, track ids, and paths, plus a CSV of positions
.venv/bin/python -m scripts.visualize <video> [--output OUT.mp4] [--csv OUT.csv] [--focus-id ID]
```

The first run downloads the `yolo26n.pt` weights into the working directory.

## Contributing

Commits follow [Conventional Commits](https://www.conventionalcommits.org/), for example
`feat(events): add sudden stop detector`. Pull requests are pre-filled from
`.github/PULL_REQUEST_TEMPLATE.md`.

## Documentation

- [docs/DESIGN.md](docs/DESIGN.md): decisions, module interfaces, event definitions,
  datasets, and evaluation.
- [MEMORY.md](MEMORY.md): progress log of changes and decisions, newest first.
- [AGENTS.md](AGENTS.md): working rules for coding agents.
