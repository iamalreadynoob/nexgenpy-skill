---
name: nexgenpy
description: Build with nexgenpy, the Python client for Nexgen Server. It covers registering semantic communication (SemCom) actuators with the @actuator decorator, downloading them with load_actuator, running them with run_actuator or the Actuator class (sync and async), and sending outputs and original inputs to the server as data and content items. Use this skill whenever code imports or mentions nexgenpy, Nexgen Server, NEXGEN_BASE_URL or NEXGEN_API_KEY, nexgen_actuators/, card.json or method.py, or when the user asks to write, publish, version, load, run or debug a coding or decoding actuator, wire a transmitter and receiver pipeline, or contribute to the nexgenpy library itself. Use it even if the user only says "actuator" or "semcom pipeline" without naming the library.
---

# nexgenpy

`nexgenpy` is the Python client for [Nexgen Server](https://github.com/iamalreadynoob/nexgen-server), a registry and data store for semantic communication (SemCom) apps. The server stores **actuators**: versioned, named Python functions. The server never runs them. Clients download the source and run it locally.

```python
from nexgenpy import Actuator, actuator, load_actuator, run_actuator
```

| Operation | API | What happens |
|---|---|---|
| Register | `@actuator(...)`, then **call** the decorated function | `POST /actuators` with the function's source. Returns `True` or `False`. |
| Load | `load_actuator(name)` | `GET /actuators/{name}/latest`, writes `nexgen_actuators/{name}/`, makes a venv, runs pip |
| Use | `run_actuator(name, data)` or `Actuator(name).run(data)` | Imports `method.py` into the **current** process and calls `func(**data)`. Can also POST the output to `dst`. |

Actuator types: `coding` turns a source into a representation for transmission (semantic encoder, channel encoder, JSCC encoder). `decoding` turns a received representation into a reconstruction or a task decision.

Install: `pip install "git+https://github.com/iamalreadynoob/nexgen.git"` (or `uv add ...`). Requires Python 3.12+.

## How actuator code really runs (read this before you write one)

Most bugs come from one fact. **The server stores only the function, from its `def` line to its end.** Decorator lines are stripped. Nothing else in the module goes with it. On the client the function becomes the only thing in `method.py`, runs in another process, maybe on another machine. So:

1. **Define the function in a `.py` file.** The decorator calls `inspect.getsource`, which fails in a REPL or notebook cell (`OSError`).
2. **Put every `import` inside the function body.** A module-level import is missing from `method.py`, so you get a `NameError` at run time, not at register time. The same applies to module-level constants, globals and config.
3. **Define helpers inside the function body.** `method.py` must hold exactly one top-level function, or `run_actuator` raises `ValueError`. A module-level helper does not get uploaded anyway.
4. **Name the parameters after the input keys.** The function is called as `func(**data)`. Positional-only parameters (before `/`) cannot work. `*args` never gets a value.
5. **Return JSON-serializable values** (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`) if the output goes to `dst`. Convert NumPy arrays with `.tolist()`, tensors with `.detach().cpu().tolist()`, and so on. When `dst_save_original=True` (the default), `data` is also sent as JSON, so the inputs must be serializable too.
6. **List every third-party package in `requirements`**, pinned if you can (`"numpy==2.0.0"`). Use `None` or `[]` for stdlib-only functions.
7. **Add type hints.** They go to the server as `method_args` and end up in `card.json`, so other developers know how to call the actuator.

Before you register an actuator, run the bundled static checker. It catches rules 2 to 4 and 6, and bad decorator arguments:

```bash
python <skill-dir>/scripts/check_actuator.py path/to/publish.py
```

It flags any name that the function uses but does not define, import or receive as a parameter. Each flag is a likely `NameError` after download.

Good:

```python
from nexgenpy import actuator


@actuator(
    name="image-encoder",
    atype="coding",
    version="1.0.0",
    is_latest=True,
    requirements=["numpy==2.0.0", "pillow==10.4.0"],
)
def encode(path: str, size: int = 64) -> dict:
    import numpy as np
    from PIL import Image

    def normalize(arr):  # the helper lives inside the actuator
        return (arr / 255.0).astype("float32")

    image = Image.open(path).convert("L").resize((size, size))
    return {"features": normalize(np.asarray(image)).flatten().tolist(), "size": size}


if __name__ == "__main__":
    if encode() is False:  # this call REGISTERS. It does not run encode.
        raise SystemExit("The server did not accept the actuator")
```

## Workflows

### Register (publish) an actuator

- All five decorator arguments are required and have no defaults: `name: str`, `atype: "coding" | "decoding"`, `version: str`, `is_latest: bool`, `requirements: list[str] | None`. A wrong type raises `ValueError` when the decorator is applied.
- **Calling the decorated function sends it to the server.** It ignores its arguments, never runs the body, and returns `True` on a 2xx status, else `False` with a logged warning. It does not raise on network errors, so check the return value. Do not test the actuator by calling the decorated function. For a local test, see "Test an actuator locally" below.
- Put the registration call under `if __name__ == "__main__":` so that an import of the module does not publish.
- The server URL comes from `NEXGEN_BASE_URL` (default `http://localhost:8000/api/v1`, and it must include `/api/v1`). The key comes from `NEXGEN_API_KEY`, sent as `X-API-KEY`. `NEXGEN_TIMEOUT` (default 60 s) is the timeout. The library reads them at request time.

### Load an actuator

```python
load_actuator("image-encoder")                          # get or update to the latest
load_actuator("image-encoder", update_actuator=False)   # only if no local copy exists
load_actuator("image-encoder", actuators_dir="/opt/nexgen/actuators", load_timeout=10)
```

- Always fetches the **latest** version. It replaces the local copy only if the `id` or `version` in `card.json` differs.
- It deletes `{actuators_dir}/{name}/` before it writes the new version, so do not keep other files there.
- `name` must be a plain directory name (`"../x"` and `"a/b"` raise `ValueError`).
- The pip step has no timeout and can be slow (e.g. `torch`). Load during startup or deploy, not on a hot path and not inside a running event loop.
- `card.json` is written last. If venv or pip fails, there is no card and the next call downloads again.

### Run an actuator

```python
out = run_actuator(name="image-encoder", data={"path": "cat.png", "size": 32})
```

- If the actuator is not local, `run_actuator` loads it first (`try_load_actuator=True`). Use `try_load_actuator=False` in production, so a missing actuator raises `ValueError` and does not trigger a surprise download and pip install.
- `run_actuator` **does not update** an existing local copy. Call `load_actuator` to pick up new versions.
- **The function runs in the current interpreter, not in `.venv`.** `load_actuator` installs requirements into `{name}/.venv`, but `run_actuator` and `Actuator` never use that venv. Install the same packages in the app's own environment, or the call raises `ModuleNotFoundError`. This is the most common "it loaded fine but crashes" issue.
- Use the same `actuators_dir` for `load_actuator` and `run_actuator`. The default is relative to the CWD, so prefer an absolute path in services.

For many calls or for async code, use the class. It imports `method.py` once:

```python
enc = Actuator(name="image-encoder")
for p in paths:
    enc.run(data={"path": p})

# async: runs the function and the POST /data in a worker thread (asyncio.to_thread)
results = await asyncio.gather(*(enc.arun(data={"path": p}) for p in paths))
```

Construct `Actuator` **before** the event loop starts, or after a `load_actuator` call. Otherwise the constructor may download and pip-install, which blocks the loop. An `Actuator` keeps the function it loaded. After `load_actuator` gets a new version, make a new object.

### Store outputs on the server (data and content items)

```python
import os

out = run_actuator(
    name="image-encoder",
    data={"path": "cat.png"},
    data_specs={"source": "camera-3"},           # free-form -> data item "specs"
    dst=os.environ["NEXGEN_BASE_URL"],
    dst_headers={"X-API-Key": os.environ["NEXGEN_API_KEY"]},
    dst_save_original=True,                       # default. Also POSTs data to /content.
)
```

- `dst` requests **do not use `NEXGEN_API_KEY`**. Pass the key in `dst_headers` yourself. Forgetting this is the usual cause of 401/403 warnings on data posts.
- Flow: run → (if `dst_save_original`) make a UUID and `POST {dst}/content` `{identifier, specs: data}` in a background thread, without waiting → `POST {dst}/data` `{actuator_id, metadata: output, linked_resource: uuid|null, specs: data_specs}` → return the output.
- A non-2xx response on `/data` only logs a warning. It does not raise. Connection errors and timeouts raise `requests.RequestException`. Content-upload failures only log.
- **The server accepts data only from the latest version.** If someone published a newer latest version, data posts start to fail with a warning. Fix it with `load_actuator(name)` (and a new `Actuator` object).
- Set `dst_save_original=False` when inputs are private or not JSON-serializable.

### Build a coding/decoding pair (transmitter → receiver)

`nexgenpy` does not move data between the two sides. The app carries the coding output over its own link (socket, queue, radio, HTTP). Keep the interface stable:

- The coding actuator returns a `dict`. The decoding actuator's parameter names are exactly that dict's keys. Then the receiver can call `run_actuator("decoder", data=received_dict)`.
- When the interface changes, bump the version of **both** actuators and reload on **every** machine. `nexgenpy` never compares the transmitter version with the receiver version.
- If either side bundles or downloads model weights, the weights are part of the shared knowledge base. A version mismatch between the two sides causes wrong results even on a perfect link.

### Publish a new version

Change the code, give it a new `version` string, keep `is_latest=True` (or use `False` to stage it without promoting it), and call the decorated function again. Then run `load_actuator(name)` on every client, and recreate any `Actuator` objects.

### Test an actuator locally before you publish

The decorator replaces the function, so test the logic in one of these ways:

- Keep the body in an undecorated function and apply the decorator in a separate publish step: `registrar = actuator(...)(encode)`. Then `encode(...)` still runs normally in tests, and `registrar()` publishes.
- Or exec the function's source in a fresh namespace to simulate `method.py`. This also proves that it has no hidden module-level dependencies.

## Debugging checklist

| Symptom | Likely cause → fix |
|---|---|
| `NameError` when the actuator runs | It uses a module-level import, constant or helper. Move it into the function body. Run `scripts/check_actuator.py`. |
| `ModuleNotFoundError` when it runs | The package is only in `{name}/.venv`. Install it in the current environment. |
| `OSError: could not get source code` while decorating | The function was defined in a REPL or notebook. Move it into a `.py` file. |
| `ValueError` about the number of functions | `method.py` has more than one top-level function. Nest the helpers. |
| `TypeError: unexpected keyword argument` | The `data` keys do not match the parameter names. |
| The decorated call returns `False` | Wrong `NEXGEN_BASE_URL` (missing `/api/v1`?), wrong or missing `NEXGEN_API_KEY`, the server is down, or the server rejected the body. The warning log contains the server's response body, so turn on logging to read it. |
| `requests.HTTPError` 404 from `load_actuator` | No actuator with that name on the server, or no latest version |
| Data post warns with non-2xx | Missing `dst_headers` key, an old local version (not the latest), or an output that is not JSON-serializable |
| The local copy never updates | `run_actuator` does not update, and neither does `update_actuator=False`. Call `load_actuator(name)`. |
| The event loop stalls | `Actuator(...)` downloaded and ran pip inside async code. Pre-load before the loop starts. |

For a downloaded actuator, run the inspector. It shows the card, the source and the arguments, and checks if each requirement is installed in the **current** interpreter:

```bash
python <skill-dir>/scripts/inspect_actuator.py image-encoder --dir nexgen_actuators
```

Turn on library logs with `logging.basicConfig(level=logging.INFO)`. The loggers are `nexgenpy.actuators` and `nexgenpy.manager`. INFO logs include server responses and the full actuator source, so do not ship them to places that untrusted users can read.

## Security defaults to apply

Downloaded actuators are code that runs with the app's full permissions. They can read `NEXGEN_API_KEY` and files, and they can make network calls. `load_actuator` also runs `pip install` with requirements that come from the server. When you write production code:

- Use only a trusted server, and use `https://` for `NEXGEN_BASE_URL` and `dst` outside local tests.
- Never hard-code the API key, and never put it in `data_specs`. Read it from the environment or a secret store.
- Pin requirements. Review `method.py` and `requirements.txt` for each new version. Run in a container or as a low-privilege user. Use `try_load_actuator=False`.
- Protect `actuators_dir` with file permissions. Anyone who can write there can change `method.py`.

## Reference files

Read these when you need more than the summary above:

- `references/api.md`: full signatures, parameters, return values, exceptions, HTTP request and response bodies, and the `card.json` format. Read it when you need exact parameter or field details.
- `references/configuration.md`: environment variables, timeouts, headers, the local directory and logging.
- `references/concepts.md`: SemCom background (Weaver levels, semantic vs goal-oriented objectives), pipeline variants mapped to coding and decoding actuators, knowledge bases, a glossary. Read it when you design an actuator pair or explain the domain.
- `references/security.md`: threat model for downloaded code and SemCom-specific threats with countermeasures.
- `references/contributing.md`: for changes to the nexgenpy library itself. It covers repo layout, uv commands, tests, CI, Ruff rules, docstring and argument-check conventions, release steps and the documentation style.
- `references/example-pipeline.md`: a complete runnable transmitter and receiver example (publish, transmit, receive, store, new version).
