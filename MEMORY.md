# MEMORY.md

Project progress log: feature-level changes and decisions, newest on top.

How to maintain this file:

- Add an entry in the same change as every feature-level change or decision.
- Put the newest date at the top. Add to today's section if it already exists.
- One line per item, starting with **Decision** or **Change**. Say what and why, not how.
- This file is public. Generalize proper nouns: no names of people, organizations, or
  clients. Write "the advisor", "a teammate", "the main dataset".
- Details belong in [docs/design.md](docs/design.md). Link to it instead of repeating it.

---

## 2026-11-21

- **Change:** Set up the repository documentation: README for the project, design doc for
  the agreed design, AGENTS.md for agent working rules.
- **Change:** Added a pull request template (Summary, Changes, Testing, Notes) and a
  gitignore that keeps datasets, videos, and model weights out of the repository.
- **Decision:** Commits follow Conventional Commits.
- **Decision:** This repository is the integration point for the separately written
  modules.

## 2026-11-20

- **Change:** Sudden-stop detector drafted. It compares a vehicle's current speed with its
  own recent speed, using medians to absorb bounding-box jitter. Thresholds are
  provisional.
- **Change:** Path-deviation detector drafted (zigzag and lane departure). It splits the
  frame into fixed columns as a stand-in for lanes.
- **Change:** Tracking now processes video in 5-second chunks and exposes per-vehicle
  trajectory and pixel speed. Event logic reads the previous and current chunk together.
- **Decision:** Storage quality starts with two levels (normal and event). Graded quality
  is backlog.
- Open: how lanes are obtained, and which of the two sudden-stop definitions is kept.

## 2026-11-03

- **Decision:** After the midterm review, evaluation centers on how well events are
  detected (misses and false detections), measured quantitatively. Qualitative scales are
  secondary.
- **Decision:** Real-time operation is deferred to future work. A working offline
  algorithm comes first.
- Open: whether path deviation needs lane detection or can use vehicle direction relative
  to surrounding traffic.

## 2026-10-30

- **Decision:** Event start and end criteria defined for sudden stop and path deviation,
  with high quality kept for a few seconds before and after each event.
- **Decision:** Main dataset chosen: a public highway CCTV dataset with per-frame
  abnormal-driving labels at 10 fps.
- **Change:** Five-point scales drafted for the qualitative evaluation.

## 2026-10-20

- **Decision:** Detector and tracker chosen: a nano-size YOLO model with ByteTrack, at a
  0.4 confidence threshold.
- **Decision:** Frames are sampled at most 0.1 s apart, because tracking degraded at
  longer intervals in tests on public traffic videos.
- **Decision:** Project title fixed as an importance-based differential storage algorithm
  for CCTV.

## 2026-09

- **Decision:** Goal changed from optimizing video transmission to optimizing storage:
  judge events first, then store less important segments at lower quality.
- **Decision:** Scenario fixed to traffic CCTV, detecting vehicle accidents and abnormal
  stops from fixed cameras.
