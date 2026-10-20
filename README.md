# nexgenpy skill for Claude Code

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) for **[nexgenpy](https://github.com/iamalreadynoob/nexgen)**, the Python client for [Nexgen Server](https://github.com/iamalreadynoob/nexgen-server).

With this skill installed, Claude knows how to write, publish, load and run nexgenpy actuators correctly, and it can debug them. It knows the rules that are easy to miss, for example:

- Only the function body is uploaded. Module-level imports, helpers and constants cause a `NameError` after the download.
- A call to the decorated function **publishes** the actuator. It does not run it.
- `run_actuator` runs the code in the **current** Python, not in the actuator's `.venv`.
- `dst` requests need the API key in `dst_headers`. They do not use `NEXGEN_API_KEY`.
- The server accepts data items only from the **latest** version.

## What it covers

| Area | Examples |
|---|---|
| Writing actuators | `coding` and `decoding` functions that work after download, requirements, type hints |
| Workflows | Register, load, run (sync and `async`), store data and content items, publish new versions |
| Pipelines | Transmitter and receiver pairs with a stable interface between them |
| Debugging | A symptom → fix table for `NameError`, `ModuleNotFoundError`, a `False` from registration, data posts that fail, and more |
| Security | Trusted servers, `https`, pinned requirements, `try_load_actuator=False` |
| Contributing | Repo layout, `uv` commands, tests, CI, Ruff rules and code conventions of nexgenpy |

Claude loads the skill on its own when you work with nexgenpy, for example when your code imports `nexgenpy` or you ask about actuators, `load_actuator`, `NEXGEN_BASE_URL` or a SemCom pipeline.

## Contents

```text
nexgenpy/                      # the skill: copy this folder
├── SKILL.md                   # main instructions (always loaded when the skill triggers)
├── references/                # loaded only when needed
│   ├── api.md                 # signatures, parameters, exceptions, request bodies, card.json
│   ├── configuration.md       # environment variables, timeouts, headers, logging
│   ├── concepts.md            # SemCom background, pipeline variants, glossary, papers
│   ├── security.md            # threat model and countermeasures
│   ├── contributing.md        # development guide for the nexgenpy library
│   └── example-pipeline.md    # full transmitter / receiver example
└── scripts/
    ├── check_actuator.py      # static check of actuator functions before you publish
    └── inspect_actuator.py    # check a downloaded actuator in nexgen_actuators/
nexgenpy-docs/                 # the nexgenpy documentation that the skill is built from
```

## Install the skill

Claude Code finds skills in two places:

| Location | Path | Who gets it |
|---|---|---|
| Project | `<your-project>/.claude/skills/nexgenpy/` | Everyone who works in that repository (commit it) |
| Personal | `~/.claude/skills/nexgenpy/` | Only you, in all your projects |

`SKILL.md` must be directly inside the `nexgenpy` folder:

```text
.claude/
└── skills/
    └── nexgenpy/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

### Option 1: Add it to a project (recommended for teams)

Run these commands in the root of your project. This can be the [nexgen](https://github.com/iamalreadynoob/nexgen) repository or an application that uses nexgenpy.

**Linux / macOS:**

```bash
git clone --depth 1 https://github.com/iamalreadynoob/nexgenpy-skill.git /tmp/nexgenpy-skill
mkdir -p .claude/skills
cp -r /tmp/nexgenpy-skill/nexgenpy .claude/skills/nexgenpy
rm -rf /tmp/nexgenpy-skill
```

**Windows (PowerShell):**

```powershell
git clone --depth 1 https://github.com/iamalreadynoob/nexgenpy-skill.git $env:TEMP\nexgenpy-skill
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Copy-Item -Recurse $env:TEMP\nexgenpy-skill\nexgenpy .claude\skills\nexgenpy
Remove-Item -Recurse -Force $env:TEMP\nexgenpy-skill
```

Then commit the skill so that your team gets it:

```bash
git add .claude/skills/nexgenpy
git commit -m "chore: add nexgenpy Claude Code skill"
```

### Option 2: Install it for yourself only

```bash
git clone --depth 1 https://github.com/iamalreadynoob/nexgenpy-skill.git /tmp/nexgenpy-skill
mkdir -p ~/.claude/skills
cp -r /tmp/nexgenpy-skill/nexgenpy ~/.claude/skills/nexgenpy
rm -rf /tmp/nexgenpy-skill
```

### Option 3: Link it and keep it up to date

Keep a clone of this repository and link the skill folder. Then `git pull` updates the skill.

```bash
git clone https://github.com/iamalreadynoob/nexgenpy-skill.git ~/src/nexgenpy-skill
mkdir -p ~/.claude/skills
ln -s ~/src/nexgenpy-skill/nexgenpy ~/.claude/skills/nexgenpy
```

For a single project, link it to `<your-project>/.claude/skills/nexgenpy` instead. Do not commit a symbolic link to a shared repository, because the link target exists only on your machine.

### Check the installation

1. Start Claude Code in your project (or start a new session).
2. Run `/skills` and look for `nexgenpy` in the list.
3. Or ask a question, for example: *"Write a coding actuator that embeds text with numpy and publish it."* Claude should put the imports inside the function and pass `dst_headers` when it stores data.

If the skill is not in the list, make sure the path is `.claude/skills/nexgenpy/SKILL.md`. A common mistake is `.claude/skills/nexgenpy/nexgenpy/SKILL.md`, which happens if you copy the whole repository and not just the `nexgenpy` folder.

## Use the skill

You do not need to call the skill by name. Ask Claude about your nexgenpy work:

- *"Register this function as a decoding actuator, version 1.1.0."*
- *"My actuator loads fine but `run_actuator` raises ModuleNotFoundError. Why?"*
- *"Build a transmitter and receiver pair for image classification with nexgenpy."*
- *"Make this receiver async with `Actuator.arun`."*
- *"Add a new test for `load_actuator` to the nexgen repo."*

### Helper scripts

Claude runs these scripts when they help, and you can run them yourself too. They need Python 3.10 or later. They only read files and never import or run actuator code.

Check actuator functions before you publish them:

```bash
python .claude/skills/nexgenpy/scripts/check_actuator.py publish.py
```

```text
[FAIL] publish.py:13 encode() [image-encoder]
    error:   line 16: `np` is a module-level import. It is not uploaded, so the actuator raises NameError. Move it into the function body.
    warning: line 14: imports `cv2`, but requirements does not list `opencv-python` (or the pip name differs). Add it, and install it in the app environment too.
```

Inspect a downloaded actuator. Run it with the same Python that runs your application:

```bash
python .claude/skills/nexgenpy/scripts/inspect_actuator.py image-encoder --dir nexgen_actuators
```

It prints the card, the arguments, the requirements and the source. It also reports a missing `card.json` (the install failed), a `method.py` without exactly one function, and requirements that are not installed in the current interpreter.

For a personal install, use `~/.claude/skills/nexgenpy/scripts/...` as the path.

## Update the skill

- **Copied install (Options 1 and 2):** delete `.claude/skills/nexgenpy` and run the install commands again.
- **Linked install (Option 3):** run `git pull` in your clone.

## Keep the skill in step with nexgenpy

The files in `nexgenpy/references/` come from the nexgenpy documentation in `nexgenpy-docs/`. When the nexgenpy API changes:

1. Update `nexgenpy-docs/` from the [nexgen](https://github.com/iamalreadynoob/nexgen) repository.
2. Update the matching files in `nexgenpy/references/`.
3. Update `nexgenpy/SKILL.md` if a workflow, a default value or a rule changed.
4. Run `scripts/check_actuator.py` on an example file to make sure that the checks still match the library.

## Related projects

- [nexgen](https://github.com/iamalreadynoob/nexgen): the nexgenpy library
- [nexgen-server](https://github.com/iamalreadynoob/nexgen-server): Nexgen Server
