# Archont561 Skills

<p align="center">
  <a href="https://github.com/Archont561/skills/actions/workflows/ci.yml"><img src="https://github.com/Archont561/skills/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/Archont561/skills"><img src="https://codecov.io/gh/Archont561/skills/branch/main/graph/badge.svg" alt="codecov"></a>
  <a href="https://agentskills.io"><img src="https://img.shields.io/badge/spec-agent%20skills-blue" alt="Agent Skills spec"></a>
  <a href="https://github.com/Archont561/skills/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
</p>

**Plain-directory Agent Skills plus a stdlib-only Python runtime that
dispatches skill-defined commands.**

Each skill is a self-contained directory (`SKILL.md` + `commands/*.py`) that
ships verbatim to installers. The engine ships as a skill too — `archont561`
installs the `archont561` shim, resolves the active set
(`skills-lock.json` manifest first, `archont561*` prefix scan as fallback),
and dispatches. No third-party packages on consumer machines; richer output
is one opt-in venv away (`setup --deps`). Experimental `0.x`: releases and
commits are conventional-commit driven.

| Skill | What it is | Install |
| :-- | :-- | :-- |
| [`archont561`](skills/archont561) | The runtime engine: shim installer, resolver, dispatcher | `npx skills add Archont561/skills --skill archont561` |
| [`hello`](skills/hello) | Demo command provider (`greet`) — the minimal authoring example | `npx skills add Archont561/skills --skill hello` |

## Try it

```sh
npx skills add Archont561/skills --all       # or: gh skill install Archont561/skills
python .agents/skills/archont561 setup       # one-time: PATH shim (--deps for rich tables)
archont561 list
archont561 greet --name Ada
```

## Develop

```sh
pixi install && pixi run setup   # locked environment + git hooks
pixi run test                    # pytest-cov -> Codecov (scripts/ + skills/)
pixi run lint && pixi run lint-md && pixi run check --strict
```

## Documentation

The contracts live in the backlog store:

- [Runtime architecture and command contract](backlog/docs/doc-1%20-%20Runtime-architecture-and-command-contract.md)
- [Skill authoring and repository contract](backlog/docs/doc-2%20-%20Skill-authoring-and-repository-contract.md)
- [Quality and release pipeline](backlog/docs/doc-3%20-%20Quality-and-release-pipeline.md)
- [Decisions](backlog/decisions) (ADRs) and the [task board](backlog/tasks)

## License

MIT
