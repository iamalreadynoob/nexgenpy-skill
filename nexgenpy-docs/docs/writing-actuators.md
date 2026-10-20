# Writing actuators

An actuator is one Python function. The server stores the source code of that function, and each client runs it later in a different process. This document gives the rules that make the function work after the download.

## The rules

### 1. Define the function in a file

The decorator reads the source with `inspect.getsource`. This works only for a function in a `.py` file. A function that you type in an interactive shell has no source file, so the decorator fails.

### 2. Put all imports in the function body

The server stores only the function, from the `def` line to the end. The module-level imports do not go to the server.

Do this:

```python
@actuator(name="resizer", atype="coding", version="1.0.0", is_latest=True,
          requirements=["pillow"])
def resize(path: str, size: int = 64) -> list[int]:
    from PIL import Image

    image = Image.open(path).resize((size, size))
    return list(image.getdata(band=0))
```

Do not do this:

```python
from PIL import Image  # not in method.py


@actuator(name="resizer", atype="coding", version="1.0.0", is_latest=True,
          requirements=["pillow"])
def resize(path: str, size: int = 64) -> list[int]:
    image = Image.open(path).resize((size, size))  # NameError at run time
    return list(image.getdata(band=0))
```

The same rule applies to module-level constants and global variables.

### 3. Define helper functions in the function body

`method.py` must define exactly one top-level function. If it defines more than one, `run_actuator` raises `ValueError`. A helper function at module level also does not go to the server.

Define each helper in the body:

```python
def summarize(text: str) -> dict:
    def tokenize(value: str) -> list[str]:
        return value.lower().split()

    tokens = tokenize(text)
    return {"length": len(tokens), "first": tokens[:3]}
```

### 4. Match the parameter names to the input data

`run_actuator` calls the function with `**data`. Each key in `data` must be a parameter name. A positional-only parameter (before `/`) does not work.

```python
def classify(keywords: list[str], threshold: int = 1) -> dict: ...


run_actuator("topic-classifier", data={"keywords": ["storm"], "threshold": 2})
```

### 5. Return a JSON-compatible value

When you give `dst`, the library sends the output as the `metadata` field of a JSON request. Return types that JSON can encode: `dict`, `list`, `str`, `int`, `float`, `bool` or `None`.

Convert other types before you return them. For example, use `array.tolist()` for a NumPy array.

When `dst_save_original=True`, the library also sends `data` as JSON. Thus the input values must also be JSON-compatible.

### 6. List each requirement

Give each third-party package in `requirements`. Use the pip format, for example `"numpy==2.0.0"` or `"torch>=2.3"`. Use `None` or `[]` if the function needs only the standard library.

`load_actuator` installs the requirements in `nexgen_actuators/{name}/.venv`. But `run_actuator` runs the function in the current process. Install the same packages in the current environment too. See [Architecture](architecture.md#the-actuator-environment).

### 7. Add type hints

The decorator sends the type hint and the default value of each parameter as `method_args`. The server stores them, and `load_actuator` writes them to `card.json`. Type hints help other developers call the actuator correctly. They are not required.

## Versions

- Use one version string for each change, for example `1.0.0`, `1.1.0`, `2.0.0`.
- Set `is_latest=True` to make the new version the latest. Clients get only the latest version.
- Set `is_latest=False` to store a version without changing the latest. You can promote it later through the server API.
- The server accepts a data item only from the latest version. After you publish a new latest version, call `load_actuator` again on each client.

## Pairs of coding and decoding actuators

A coding actuator and a decoding actuator often form a pair. The output of the coding actuator is the input of the decoding actuator. Keep their interface the same:

- Return a `dict` from the coding actuator.
- Use the keys of that `dict` as the parameter names of the decoding actuator.
- Change the version of both actuators when the interface changes.

Then the receiver can call `run_actuator(name, data=received)` with the received `dict`.

## Checklist

- [ ] The function is in a `.py` file.
- [ ] All imports are in the function body.
- [ ] All helper functions and constants are in the function body.
- [ ] The parameter names match the keys of the input data.
- [ ] The return value is JSON-compatible.
- [ ] `requirements` lists each third-party package.
- [ ] The version string is new.
