# API: `actuator`

```python
from nexgenpy import actuator
```

## Signature

```python
def actuator(
    name: str,
    atype: Literal["coding", "decoding"],
    version: str,
    is_latest: bool,
    requirements: List[str] | None,
) -> Callable[[Callable[..., Any]], Callable[..., bool]]
```

A decorator that registers a function as an actuator on Nexgen Server.

## Parameters

All parameters are required. They have no default values.

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | The name of the actuator. |
| `atype` | `"coding"` or `"decoding"` | The type of the actuator. |
| `version` | `str` | The version of the actuator, for example `"1.0.0"`. |
| `is_latest` | `bool` | If `True`, the server marks this version as the latest version of `name`. |
| `requirements` | `List[str]` or `None` | The pip requirements of the actuator. `None` sends `[]`. |

## Returns

A decorator. The decorator returns a new function with the name and the docstring of the original function.

When the code calls the new function:

1. It sends `POST {NEXGEN_BASE_URL}/actuators`.
2. It returns `True` if the server returns a 2xx status.
3. It returns `False` if the request fails or the server returns a different status.

The new function accepts any arguments and ignores them. It does not run the original function.

## Raises

| Exception | Condition |
|---|---|
| `ValueError` | `name` or `version` is not a `str`. |
| `ValueError` | `atype` is not `"coding"` or `"decoding"`. |
| `ValueError` | `is_latest` is not a `bool`. |
| `ValueError` | `requirements` is not `None` and not a list of `str`. |

The decorator raises these errors when Python applies it, before any request.

The decorator also calls `inspect.getsource` and `typing.get_type_hints` on the function. These calls can raise `OSError` or `NameError`, for example for a function without a source file.

The decorated function does not raise for network errors. It logs a warning and returns `False`.

## Request

`POST {NEXGEN_BASE_URL}/actuators`

| Header | Value |
|---|---|
| `X-API-KEY` | `NEXGEN_API_KEY`, only if it is set |

Body:

```json
{
    "name": "keyword-extractor",
    "version": "1.0.0",
    "actuator_type": "coding",
    "set_latest": true,
    "requirements": [],
    "method": "def extract(text: str, max_words: int = 5) -> dict:\n    ...",
    "method_args": {
        "text": {"type": "<class 'str'>", "default": null},
        "max_words": {"type": "<class 'int'>", "default": "5"}
    }
}
```

`method` starts at the `def` line. The decorator lines are not in it.

## Example

```python
from nexgenpy import actuator


@actuator(
    name="keyword-extractor",
    atype="coding",
    version="1.0.0",
    is_latest=True,
    requirements=None,
)
def extract(text: str, max_words: int = 5) -> dict:
    import re

    words = re.findall(r"[a-z]+", text.lower())
    return {"keywords": words[:max_words]}


if extract() is False:
    raise SystemExit("The server did not accept the actuator")
```

## See also

- [Writing actuators](../writing-actuators.md)
- [Configuration](../configuration.md)
- [`load_actuator`](load-actuator.md)
