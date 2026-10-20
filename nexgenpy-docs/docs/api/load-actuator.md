# API: `load_actuator`

```python
from nexgenpy import load_actuator
```

## Signature

```python
def load_actuator(
    name: str,
    actuators_dir: str = "nexgen_actuators",
    load_timeout: int = 60,
    update_actuator: bool = True,
) -> None
```

Downloads the latest version of an actuator from Nexgen Server. It writes the actuator to `{actuators_dir}/{name}/` and installs its requirements.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | The name of the actuator. It must be a plain directory name. |
| `actuators_dir` | `str` | `"nexgen_actuators"` | The directory for the local actuators. |
| `load_timeout` | `int` | `60` | The timeout in seconds for the `GET` request. |
| `update_actuator` | `bool` | `True` | If `True`, the function asks the server for the latest version, also when a local copy exists. If `False` and a local copy exists, the function does nothing. |

## Returns

`None`.

## Steps

1. Check the arguments.
2. If `update_actuator` is `False` and `{actuators_dir}/{name}` exists, stop.
3. Send `GET {NEXGEN_BASE_URL}/actuators/{name}/latest`.
4. If the local `card.json` has the same `id` and `version` as the response, stop.
5. Delete the old `{actuators_dir}/{name}` directory, if it exists.
6. Write `method.py` and `requirements.txt`.
7. Make a virtual environment in `{actuators_dir}/{name}/.venv`.
8. Install `requirements.txt` with the `pip` of that environment.
9. Write `card.json`.

The function writes `card.json` last. If step 7 or step 8 fails, the next call downloads the actuator again.

## Raises

| Exception | Condition |
|---|---|
| `ValueError` | An argument has a wrong type. |
| `ValueError` | `name` is not a plain directory name, for example `"../other"` or `"a/b"`. |
| `requests.HTTPError` | The server returns a status that is not 2xx, for example 404 for an unknown name. |
| `requests.RequestException` | The request cannot connect or times out. |
| `subprocess.CalledProcessError` | The venv step or the pip step fails. |

## Request

`GET {NEXGEN_BASE_URL}/actuators/{name}/latest`

| Header | Value |
|---|---|
| `X-API-KEY` | `NEXGEN_API_KEY`, only if it is set |

The function uses these fields of the response: `id`, `name`, `version`, `actuator_type`, `method_args`, `latest`, `created_at`, `updated_at`, `requirements` and `method`.

## Files

| File | Content |
|---|---|
| `card.json` | `id`, `name`, `version`, `actuator_type`, `method_args`, `latest`, `created_at`, `updated_at` |
| `method.py` | The `method` field |
| `requirements.txt` | The `requirements` field, one item on each line |
| `.venv/` | A virtual environment with the requirements |

## Examples

Download or update an actuator:

```python
from nexgenpy import load_actuator

load_actuator("keyword-extractor")
```

Download an actuator only if no local copy exists:

```python
load_actuator("keyword-extractor", update_actuator=False)
```

Use a different directory and a shorter timeout:

```python
load_actuator(
    "keyword-extractor",
    actuators_dir="/opt/nexgen/actuators",
    load_timeout=10,
)
```

## Notes

- The pip step can take a long time for large requirements, for example `torch`. It has no timeout.
- `run_actuator` and `Actuator` do not use the `.venv`. See [Architecture](../architecture.md#the-actuator-environment).
- `load_actuator` runs `pip install` with requirements from the server. Use only a server that you trust. See [Security](../security.md).

## See also

- [`actuator`](actuator.md)
- [`run_actuator` and `Actuator`](run-actuator.md)
