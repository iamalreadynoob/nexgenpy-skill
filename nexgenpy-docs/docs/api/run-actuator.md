# API: `run_actuator` and `Actuator`

```python
from nexgenpy import Actuator, run_actuator
```

Use `run_actuator` for one call. Use the `Actuator` class for many calls, or in `async` code. The class imports `method.py` one time. `run_actuator` imports it on each call.

## `run_actuator`

### Signature

```python
def run_actuator(
    name: str,
    data: Dict[str, Any],
    data_specs: Dict[str, Any] | None = None,
    actuators_dir: str = "nexgen_actuators",
    dst: str | None = None,
    dst_timeout: int = 60,
    dst_headers: Dict[str, Any] | None = None,
    dst_save_original: bool = True,
    try_load_actuator: bool = True,
) -> object
```

Runs a local actuator with `data`. If `dst` is given, it also sends the output to the `dst` server.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | The name of the actuator. |
| `data` | `Dict[str, Any]` | required | The input of the actuator. The function gets it as `**data`. |
| `data_specs` | `Dict[str, Any]` or `None` | `None` | Free-form information about the data. It goes to the `specs` field of the data item. |
| `actuators_dir` | `str` | `"nexgen_actuators"` | The directory for the local actuators. |
| `dst` | `str` or `None` | `None` | The root URL of the server that stores the output, for example `http://localhost:8000/api/v1`. If `None`, the function sends nothing. |
| `dst_timeout` | `int` | `60` | The timeout in seconds for each `dst` request. |
| `dst_headers` | `Dict[str, Any]` or `None` | `None` | The headers for each `dst` request, for example `{"X-API-Key": "..."}`. |
| `dst_save_original` | `bool` | `True` | If `True` and `dst` is given, the function also sends `data` as a content item. |
| `try_load_actuator` | `bool` | `True` | If `True` and the actuator is not local, the function calls `load_actuator` first. If `False`, it raises `ValueError`. |

### Returns

The return value of the actuator function.

### Steps

1. Check the arguments.
2. If `{actuators_dir}/{name}` does not exist, call `load_actuator(name, actuators_dir)` or raise `ValueError`.
3. Import `{actuators_dir}/{name}/method.py`.
4. Find the one function in `method.py`.
5. Call the function with `**data`.
6. If `dst` is `None`, return the output.
7. Read `id` from `card.json`.
8. If `dst_save_original` is `True`, make a random UUID. Send the content item in a background thread.
9. Send the data item.
10. Return the output.

`run_actuator` does not update a local actuator that exists. To get a new version, call `load_actuator` first.

### Raises

| Exception | Condition |
|---|---|
| `ValueError` | An argument has a wrong type. |
| `ValueError` | The actuator is not local and `try_load_actuator` is `False`. |
| `ValueError` | `method.py` does not define exactly one function. |
| `ImportError` | Python cannot load `method.py`. |
| Any exception | The actuator function raises it. |
| `requests.RequestException` | `POST {dst}/data` cannot connect or times out. |

`run_actuator` can also raise the exceptions of [`load_actuator`](load-actuator.md#raises) when it loads the actuator.

If `POST {dst}/data` returns a status that is not 2xx, the function logs a warning and returns the output. It does not raise.

### Requests

The requests go only to `dst`. They use `dst_headers`, not `NEXGEN_API_KEY`.

`POST {dst}/data`:

```json
{
    "actuator_id": "<id from card.json>",
    "metadata": "<output of the actuator>",
    "linked_resource": "<UUID, or null if dst_save_original is False>",
    "specs": "<data_specs, or null>"
}
```

`POST {dst}/content`, only if `dst_save_original` is `True`:

```json
{
    "identifier": "<the same UUID as linked_resource>",
    "specs": "<data>"
}
```

The content request runs in a background thread. The function does not wait for it. If the request fails, the thread logs a warning.

### Examples

Run an actuator locally:

```python
from nexgenpy import run_actuator

output = run_actuator(name="keyword-extractor", data={"text": "rain in the north"})
```

Run an actuator and store the output and the original input:

```python
import os

output = run_actuator(
    name="keyword-extractor",
    data={"text": "rain in the north"},
    data_specs={"language": "en", "source": "sensor-12"},
    dst=os.environ["NEXGEN_BASE_URL"],
    dst_headers={"X-API-Key": os.environ["NEXGEN_API_KEY"]},
)
```

Run an actuator only if it is already local:

```python
output = run_actuator(
    name="keyword-extractor",
    data={"text": "rain in the north"},
    try_load_actuator=False,
)
```

## `Actuator`

### Constructor

```python
class Actuator:
    def __init__(
        self,
        name: str,
        actuators_dir: str = "nexgen_actuators",
        dst: str | None = None,
        dst_timeout: int = 60,
        dst_headers: Dict[str, Any] | None = None,
        dst_save_original: bool = True,
        try_load_actuator: bool = True,
    ) -> None
```

The parameters have the same meaning as in [`run_actuator`](#parameters). The constructor does steps 1 to 4 of `run_actuator` one time. If `dst` is given, it also reads `id` from `card.json`.

The constructor raises the same exceptions as `run_actuator`, except the exceptions of the actuator function and of `POST {dst}/data`.

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | The name of the actuator. |
| `actuators_dir` | `str` | The directory for the local actuators. |
| `dst` | `str` or `None` | The root URL of the `dst` server. |
| `dst_timeout` | `int` | The timeout for each `dst` request. |
| `dst_headers` | `Dict[str, Any]` | The headers for each `dst` request. `{}` if `None` was given. |
| `dst_save_original` | `bool` | If `True`, each run also sends a content item. |
| `actuator_id` | `str` or `None` | The server `id` of the actuator. `None` if `dst` is `None`. |
| `method` | `Callable[..., Any]` | The function from `method.py`. |

### `run`

```python
def run(
    self,
    data: Dict[str, Any],
    data_specs: Dict[str, Any] | None = None,
) -> object
```

Runs the loaded function with `**data`. It does steps 5 to 10 of `run_actuator`. It returns the output.

### `arun`

```python
async def arun(
    self,
    data: Dict[str, Any],
    data_specs: Dict[str, Any] | None = None,
) -> object
```

The `async` version of `run`. It runs the function and `POST {dst}/data` in a worker thread with `asyncio.to_thread`. Thus the event loop can do other work. The content upload uses a background thread, as in `run`.

### Examples

Run an actuator many times:

```python
from nexgenpy import Actuator

extractor = Actuator(name="keyword-extractor")

for sentence in ["rain in the north", "sun in the south"]:
    print(extractor.run(data={"text": sentence}))
```

Run an actuator in `async` code:

```python
import asyncio

from nexgenpy import Actuator


async def main() -> None:
    extractor = Actuator(name="keyword-extractor")
    outputs = await asyncio.gather(
        extractor.arun(data={"text": "rain in the north"}),
        extractor.arun(data={"text": "sun in the south"}),
    )
    print(outputs)


asyncio.run(main())
```

If the actuator is not local, the constructor downloads it and runs pip. This blocks the event loop. Call `load_actuator` before the event loop starts.

### Notes

- An `Actuator` object keeps the function that it loaded. If you call `load_actuator` for a new version, make a new `Actuator` object.
- The function runs in the current Python process. See [Architecture](../architecture.md#the-actuator-environment).

## See also

- [`load_actuator`](load-actuator.md)
- [Configuration](../configuration.md)
- [Concepts: data and content items](../concepts.md#data-and-content-items)
