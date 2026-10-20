# Development

This document is for contributors to `nexgenpy`.

## Project layout

```text
nexgen/
├── nexgenpy/
│   ├── __init__.py       # public API
│   ├── actuators.py      # @actuator decorator (register)
│   └── manager.py        # load_actuator, run_actuator, Actuator (load and use)
├── tests/
│   ├── conftest.py       # fake requests.post / requests.get fixtures
│   ├── test_actuators.py
│   └── test_manager.py
├── docs/                 # this documentation
├── dist/                 # built sdist and wheel (committed)
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt      # mirrors the pinned versions in uv.lock
└── uv.lock
```

## Set up

1. Install [uv](https://github.com/astral-sh/uv).
2. Clone the repository:

   ```bash
   git clone https://github.com/iamalreadynoob/nexgen.git
   cd nexgen
   ```

3. Make the virtual environment and install the dependencies:

   ```bash
   uv sync
   ```

4. Install the pre-commit hooks:

   ```bash
   uv run pre-commit install
   ```

## Commands

| Task | Command |
|---|---|
| Run all tests | `uv run pytest` |
| Run the unit tests only | `uv run pytest -m "not integration"` |
| Run the integration tests only | `uv run pytest -m integration` |
| Lint | `uv run ruff check .` |
| Lint and fix | `uv run ruff check --fix .` |
| Format | `uv run ruff format .` |
| Run all pre-commit hooks | `uv run pre-commit run --all-files` |
| Build the sdist and the wheel | `uv run python -m build` |

## Tests

The tests do not need a running Nexgen Server. The fixtures in `tests/conftest.py` replace `requests.post` and `requests.get`. They also remove the `NEXGEN_*` environment variables of the host.

The tests with the `integration` marker make real virtual environments and run pip. They are slow.

## Continuous integration

`.github/workflows/ci.yml` runs on each push to `main` and on each pull request.

| Job | Platforms | Python | Steps |
|---|---|---|---|
| Ruff | Ubuntu | default | `ruff check`, `ruff format --check` |
| Actuators tests | Ubuntu | 3.12, 3.13 | `pytest tests/test_actuators.py` |
| Manager tests | Ubuntu, macOS, Windows | 3.12, 3.13 | `pytest tests/test_manager.py`, unit tests first, then integration tests |

The manager tests run on Windows because `load_actuator` uses a different `pip` path there.

## Code conventions

Ruff enforces a broad rule set. The line length is 88. Ruff does not check `__init__.py`. Some of the rules:

| Rule set | Requirement |
|---|---|
| `ANN` | Add type annotations to each function. |
| `D` | Write Google-style docstrings. |
| `S` | Obey the bandit security checks. |
| `T20` | Do not use `print`. Use the module-level `logger`. |

### Docstrings

Start each docstring with a Markdown-style heading line. Then add the Google-style sections:

```python
def load_actuator(name: str, actuators_dir: str = "nexgen_actuators") -> None:
    """# Load Actuator.

    Args:
        name (str): The name of the actuator.
        actuators_dir (str, optional): Located directory for the actuators.
    """
```

### Argument checks

Check the type of each argument at the start of each public function. Log the error, then raise `ValueError`:

```python
if isinstance(name, str) is False:
    logger.error("name is invalid, it has to be str")
    raise ValueError("name is invalid, it has to be str")
```

### Commit messages

Use the conventional commit style, for example `feat: add arun to Actuator` or `fix: ...`.

## Release

1. Change `version` in `pyproject.toml`.
2. Run the tests and the linter.
3. Build the package:

   ```bash
   uv run python -m build
   ```

4. Commit the new files in `dist/`.

## Documentation

The documentation is in `README.md` and `docs/`. Add each new document to the table in the [README](../README.md#documentation).

Write the documentation in Simplified Technical English style:

- Use short sentences and the active voice.
- Write one instruction in each sentence.
- Do not use semicolons.
- Use one term for one thing. See the [Glossary](glossary.md).
