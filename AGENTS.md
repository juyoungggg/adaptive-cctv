# AGENTS.md

Working rules for coding agents in this repository. For what the project is, read
[README.md](README.md). For the design, read [docs/DESIGN.md](docs/DESIGN.md).

## Before you change code

- Read `docs/DESIGN.md` before touching detection, tracking, event logic, or encoding. It
  holds the settled decisions, module interfaces, data shapes, and thresholds, and the
  code alone does not show which values the team has agreed on.

## Rules

- **Write code, comments, and documentation in English.** The repository is kept in one
  language regardless of the language used in conversation.
- **Do not introduce numbers or claims without a source.** Label any assumed or placeholder
  value as such where it appears. Results here are presented and defended, so an unsourced
  figure is a liability.
- **Do not change a settled decision, a threshold, or a module interface silently.** Each
  module has a different author and the values are what the team has reported. State the
  change and update `docs/DESIGN.md` in the same commit.
- **Keep every threshold as a named parameter or in configuration.** They are provisional
  and will be tuned on real data, so a literal buried in logic will be missed.
- **Get the base pipeline working end to end before adding anything else.** Supporting
  features and real-time operation come after; see the open items in `docs/DESIGN.md`.
- **Do not commit dataset files, videos, or model weights.** They are large and governed
  by each dataset's own terms of use.

## Progress log

- **Update [MEMORY.md](MEMORY.md) in the same change as every feature-level change or
  decision.** It is the only record of what was decided and when; the code does not show
  it. Newest entry on top.
- **Keep MEMORY.md free of proper nouns for people, organizations, and clients.** The file
  is public. Write "the advisor", "a teammate", "the main dataset".

## Commits

- Use Conventional Commits: `<type>(<scope>): <subject>`, for example
  `feat(events): add sudden stop detector`.
  - Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
  - Scope is optional: `tracking`, `events`, `encoder`, `eval`, `docs`.
  - Subject: imperative mood, lower case, no trailing period.
- Write the subject line only. Leave the commit message body empty.

## Commands

No toolchain is set up yet. When the first code lands, record the install, run, test, and
lint commands here.
