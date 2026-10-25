---
id: decision-2
title: Manifest-first skill resolution (skills-lock.json)
date: '2026-10-25T19:22:00Z'
status: accepted
---

## Context

Originally every Archont561 skill directory had to carry the `archont561-`
prefix so core could tell registry skills apart from arbitrary foreign
directories in `.agents/skills/`. The prefix is a weak namespace mechanism —
it leaks into every skill name and provides no explicit record of what is
supposed to be installed. The `npx skills` ecosystem already demonstrates the
manifest pattern (`.skills.json` / `skills-lock.json`) consumer-side.

## Decision

Resolution has two modes; the manifest wins when present and parseable:

1. `skills-lock.json` in the skills root pins the active skills:
   `{"skills": ["archont561", "hello"]}` or the mapping form
   `{"skills": {"hello": {"source": "..."}}}`. Listed directories are the
   ONLY active skills and may use any name — no prefix required. Entries that
   name no installable dir (missing dir or missing SKILL.md) are skipped and
   surfaced as `ctx.lock_missing` / a `doctor` warning, never fatal.
2. Fallback prefix scan: sibling directories named `archont561*`
   (`runtime.PREFIX`) with a SKILL.md. Lets a bare install work with zero
   bookkeeping; also keeps legacy `archont561-*` installs resolvable.

A missing, unreadable, malformed, or wrongly-shaped manifest fails OPEN to
mode 2 — a broken registry file must never brick the runtime.

## Consequences

- Skill directory names are decoupled from the publisher namespace; the repo
  itself ships `skills/archont561` + `skills/hello` with a repo-level
  manifest.
- `doctor` reports which resolver is active (`resolver: skills-lock.json` vs
  `resolver: prefix scan (archont561*)`) so discovery is never mysterious.
- Installers are expected to maintain the manifest; core only reads it.
