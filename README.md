# adaptive-cctv

Importance-based differential storage for fixed traffic CCTV.

CCTV records every scene at the same high quality, so storage fills quickly and footage
cannot be kept for as long as it should be. adaptive-cctv detects abnormal driving in the
video and stores only those segments at high quality. Normal segments are stored at low
quality, which cuts the total storage needed.

This is a university capstone project (2026 fall semester).

## How it works

```
CCTV video
  -> vehicle detection (YOLO26n)
  -> vehicle tracking (ByteTrack)
  -> per-vehicle trajectory
  -> event detection: sudden stop, path deviation
  -> storage: normal segments at low quality, event segments at high quality
```

The current scope is an offline pipeline that runs on recorded video on a PC. Real-time
and on-camera operation are future work.

## Status

The modules (tracking, event detection, encoding) are being written separately and will be
integrated in this repository. Run instructions will be added here when the first code
lands.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Contributing

Commits follow [Conventional Commits](https://www.conventionalcommits.org/), for example
`feat(events): add sudden stop detector`. Pull requests are pre-filled from
`.github/PULL_REQUEST_TEMPLATE.md`.

## Documentation

- [docs/DESIGN.md](docs/DESIGN.md): decisions, module interfaces, event definitions,
  datasets, and evaluation.
- [MEMORY.md](MEMORY.md): progress log of changes and decisions, newest first.
- [AGENTS.md](AGENTS.md): working rules for coding agents.
