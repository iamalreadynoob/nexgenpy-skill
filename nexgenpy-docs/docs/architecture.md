# Architecture

This document describes the modules of `nexgenpy`, the request flow for each operation, and the local files.

## Modules

| Module | Public API | Role |
|---|---|---|
| `nexgenpy/actuators.py` | `actuator` | Registers actuators on the server |
| `nexgenpy/manager.py` | `load_actuator`, `run_actuator`, `Actuator` | Downloads and runs actuators |

`nexgenpy/__init__.py` exports the four public names:

```python
from nexgenpy import Actuator, actuator, load_actuator, run_actuator
```

The library code imports one third-party package: `requests`.

## Register: `@actuator`

```mermaid
sequenceDiagram
    participant Dev as Developer code
    participant Lib as nexgenpy.actuators
    participant API as Nexgen Server

    Dev->>Lib: @actuator(name, atype, version, is_latest, requirements)
    Lib->>Lib: check the arguments (ValueError if invalid)
    Dev->>Lib: decorate func
    Lib->>Lib: read the source, signature and type hints of func
    Dev->>Lib: call the decorated func
    Lib->>API: POST /actuators
    API-->>Lib: response
    Lib-->>Dev: True if 2xx, else False
```

The decorator collects the actuator data when Python applies it to the function. The request goes to the server only when the code calls the decorated function. The call does not run the original function. It ignores the call arguments.

The request body has these fields:

| Field | Value |
|---|---|
| `name` | `name` |
| `version` | `version` |
| `actuator_type` | `atype` |
| `set_latest` | `is_latest` |
| `requirements` | `requirements`, or `[]` if it is `None` |
| `method` | The source of the function, from the `def` line. The decorator removes the decorator lines. |
| `method_args` | For each parameter: `{"type": str(annotation) or None, "default": str(default) or None}` |

## Load: `load_actuator`

```mermaid
sequenceDiagram
    participant App as Application
    participant Lib as nexgenpy.manager
    participant API as Nexgen Server
    participant FS as nexgen_actuators/{name}/

    App->>Lib: load_actuator(name)
    Lib->>Lib: check the arguments and the name
    alt update_actuator is False and the directory exists
        Lib-->>App: return (no request)
    end
    Lib->>API: GET /actuators/{name}/latest
    API-->>Lib: actuator (raise HTTPError if not 2xx)
    alt card.json has the same id and version
        Lib-->>App: return (already up to date)
    end
    Lib->>FS: delete the old directory
    Lib->>FS: write method.py and requirements.txt
    Lib->>FS: python -m venv .venv
    Lib->>FS: .venv pip install -r requirements.txt
    Lib->>FS: write card.json
    Lib-->>App: return
```

`load_actuator` writes `card.json` last. If the venv or pip step fails, the directory has no `card.json`. The next call then downloads the actuator again.

## Use: `run_actuator` and `Actuator`

```mermaid
sequenceDiagram
    participant App as Application
    participant Lib as nexgenpy.manager
    participant FS as nexgen_actuators/{name}/
    participant Dst as dst server

    App->>Lib: run_actuator(name, data, dst=...)
    alt the directory does not exist
        Lib->>Lib: load_actuator(name), or ValueError if try_load_actuator is False
    end
    Lib->>FS: import method.py
    Lib->>Lib: find exactly one function
    Lib->>Lib: output = function(**data)
    opt dst is given
        Lib->>FS: read the id from card.json
        opt dst_save_original is True
            Lib--)Dst: POST {dst}/content (background thread)
        end
        Lib->>Dst: POST {dst}/data
    end
    Lib-->>App: output
```

`run_actuator` imports `method.py` on each call. The `Actuator` class imports it one time, in the constructor. `Actuator.run` and `Actuator.arun` then use the loaded function.

`Actuator.arun` is the `async` version of `run`. It runs the function and the `POST {dst}/data` request in a worker thread with `asyncio.to_thread`. Thus they do not block the event loop.

## Local directory layout

The default directory is `nexgen_actuators`, relative to the current working directory. Use the `actuators_dir` parameter to change it.

```text
nexgen_actuators/
└── {name}/
    ├── card.json
    ├── method.py
    ├── requirements.txt
    └── .venv/
```

`card.json` stores these fields from the server response:

```json
{
    "id": "…",
    "name": "keyword-extractor",
    "version": "1.0.0",
    "actuator_type": "coding",
    "method_args": {"text": {"type": "<class 'str'>", "default": null}},
    "latest": true,
    "created_at": "…",
    "updated_at": "…"
}
```

`run_actuator` reads `id` from `card.json` and sends it as `actuator_id` in each data item.

## The actuator environment

`load_actuator` makes a virtual environment in `{name}/.venv` with the Python that runs `nexgenpy`. Then it installs `requirements.txt` into that environment.

`run_actuator` and `Actuator` do not use this environment. They import `method.py` into the current Python process. Thus the current environment must also have each package that the actuator imports. If a package is missing, the function raises `ModuleNotFoundError` when it runs.

## Error behavior

| Operation | Condition | Result |
|---|---|---|
| `@actuator(...)` | An argument has a wrong type or value | `ValueError` |
| decorated call | The request fails, or the server returns a status that is not 2xx | Logs a warning, returns `False` |
| `load_actuator` | An argument is invalid, or the name is not a plain directory name | `ValueError` |
| `load_actuator` | The server returns a status that is not 2xx | `requests.HTTPError` |
| `load_actuator` | The request cannot connect or times out | `requests.RequestException` |
| `load_actuator` | The venv or pip step fails | `subprocess.CalledProcessError` |
| `run_actuator`, `Actuator` | An argument is invalid | `ValueError` |
| `run_actuator`, `Actuator` | The actuator is not local and `try_load_actuator=False` | `ValueError` |
| `run_actuator`, `Actuator` | `method.py` does not define exactly one function | `ValueError` |
| `run_actuator`, `Actuator.run` | The actuator function raises an exception | The exception goes to the caller |
| `run_actuator`, `Actuator.run` | `POST {dst}/data` returns a status that is not 2xx | Logs a warning, returns the output |
| `run_actuator`, `Actuator.run` | `POST {dst}/data` cannot connect or times out | `requests.RequestException` |
| content upload | Any error | Logs a warning. The background thread does not raise. |
