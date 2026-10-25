---
id: decision-5
title: Markdown linting split pymarkdownlnt vs lint.py
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

Skill docs are the primary agent interface, so section order and hygiene are
contractual (SKILL.md must start with one H1, then `## When to use this
skill`, `## How to use it`; README.md needs `## Usage`). Two linter families
were evaluated with the constraint that everything comes from pixi:
markdownlint-cli (conda-forge, Node) and rumdl (conda-forge, Rust) exist, but
pymarkdownlnt (PyPI via `[pypi-dependencies]`) is Python-native and matches
the repo's language.

## Decision

Hygiene and structure are split between two linters, on purpose:

- **pymarkdownlnt** (`pixi run lint-md`, configs `.pymarkdown.skill.json` /
  `.pymarkdown.readme.json`) covers general hygiene plus MD041
  (first-content-must-be-H1, front-matter aware). The front-matter extension
  is explicitly enabled; MD013 (line length) is off.
- **`lint.py`** keeps the semantic section contracts. pymarkdown's MD043 was
  evaluated and rejected here: its `headings` parameter is a strictly
  positional comma-separated string with no wildcard for "any H1 title", so
  it cannot express "any H1, then exactly these H2s in order" — whereas
  markdownlint-cli's MD043 accepts an `*` glob. If the contract ever needs to
  be linter-native, markdownlint-cli is the documented swap path.

pymarkdown details that bit during setup (recorded so they don't bite again):
`"md013": false` is not a disable — use `{"enabled": false}`; the
front-matter extension defaults to off and unmuzzled YAML parses as content,
cascading MD041/MD022/MD023/MD003.

## Consequences

- Full markdown rule coverage in hooks + CI without a Node runtime dependency.
- Section contracts stay readable Python in lint.py with `--fix` autofixes;
  duplication of concerns is avoided by comments in both places.
