# Configuration

`nexgenpy` reads its server settings from environment variables. The settings for data and content requests are function parameters.

## Environment variables

| Variable | Default | Used by | Description |
|---|---|---|---|
| `NEXGEN_BASE_URL` | `http://localhost:8000/api/v1` | `@actuator`, `load_actuator` | The root URL of the Nexgen Server API, including `/api/v1`. |
| `NEXGEN_API_KEY` | not set | `@actuator`, `load_actuator` | The API key. When it is set, the library sends it in the `X-API-KEY` header. |
| `NEXGEN_TIMEOUT` | `60` | `@actuator` | The timeout in seconds for `POST /actuators`. |

The library reads each variable when it sends the request, not at import time. Thus you can change a variable in the same process.

If `NEXGEN_TIMEOUT` is not a number, or is not more than 0, the library logs a warning and uses `60`.

Example:

```bash
export NEXGEN_BASE_URL="https://nexgen.example.com/api/v1"
export NEXGEN_API_KEY="<your-key>"
export NEXGEN_TIMEOUT="30"
```

> [!IMPORTANT]
> Do not write the API key in source code. Keep it in the environment or in a secret store.

## API key authentication

Nexgen Server needs the `X-API-Key` header on all endpoints except health when the server has an `API_KEY`. HTTP header names are not case-sensitive, so `X-API-KEY` and `X-API-Key` are the same header.

| Request | Header source |
|---|---|
| `POST /actuators` | `NEXGEN_API_KEY` |
| `GET /actuators/{name}/latest` | `NEXGEN_API_KEY` |
| `POST {dst}/data` | `dst_headers` |
| `POST {dst}/content` | `dst_headers` |

The data and content requests do not use `NEXGEN_API_KEY`. The `dst` server can be a different server with a different key. To send data to Nexgen Server, give the key yourself:

```python
import os

from nexgenpy import run_actuator

run_actuator(
    name="keyword-extractor",
    data={"text": "hello"},
    dst=os.environ["NEXGEN_BASE_URL"],
    dst_headers={"X-API-Key": os.environ["NEXGEN_API_KEY"]},
)
```

## Timeouts

| Request | Setting | Default |
|---|---|---|
| `POST /actuators` | `NEXGEN_TIMEOUT` environment variable | 60 s |
| `GET /actuators/{name}/latest` | `load_timeout` parameter of `load_actuator` | 60 s |
| `POST {dst}/data`, `POST {dst}/content` | `dst_timeout` parameter of `run_actuator` and `Actuator` | 60 s |

The venv and pip steps of `load_actuator` have no timeout.

## Local directory

| Parameter | Default | Used by |
|---|---|---|
| `actuators_dir` | `nexgen_actuators` | `load_actuator`, `run_actuator`, `Actuator` |

The default path is relative to the current working directory. If your application starts from different directories, give an absolute path:

```python
from pathlib import Path

ACTUATORS_DIR = str(Path.home() / ".nexgen" / "actuators")

load_actuator("keyword-extractor", actuators_dir=ACTUATORS_DIR)
run_actuator("keyword-extractor", data={"text": "hello"}, actuators_dir=ACTUATORS_DIR)
```

Use the same `actuators_dir` for `load_actuator` and for `run_actuator`.

## Logging

`nexgenpy` uses the standard `logging` module. It does not add handlers. Each module has its own logger:

| Logger | Messages |
|---|---|
| `nexgenpy.actuators` | Registration requests and `NEXGEN_TIMEOUT` warnings |
| `nexgenpy.manager` | Load steps, data requests and content uploads |

| Level | Examples |
|---|---|
| `ERROR` | An argument is invalid, just before the `ValueError` |
| `WARNING` | A request failed, an actuator is not local, `NEXGEN_TIMEOUT` is invalid |
| `INFO` | A request succeeded, a load step finished |

To see the messages, configure logging in your application:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("nexgenpy").setLevel(logging.WARNING)
```

> [!NOTE]
> The `INFO` and `WARNING` messages for requests include the response body of the server. The `GET /actuators/{name}/latest` message includes the full actuator source code.
