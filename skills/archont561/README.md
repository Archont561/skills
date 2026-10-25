# Archont561 Core

Runtime engine for all Archont561 skills: installs the `archont561`
shim, discovers commands from sibling `archont561*` skills, builds the shared
context, and dispatches.

## Usage

```bash
gh skill install Archont561/skills archont561   # or: npx skills add Archont561/skills
python .agents/skills/archont561 setup          # one-time: PATH shim
python .agents/skills/archont561 setup --deps   # optional: rich/typer venv
archont561 list                               # run commands
```
