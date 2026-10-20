# Quick start

This guide registers two actuators, loads them and runs them as a transmitter and a receiver. The example uses no third-party packages, so you can run it with only `nexgenpy` installed.

The two actuators are a toy goal-oriented pipeline. They are not a SemCom model. They only show the workflow.

- `keyword-extractor` is a `coding` actuator. It changes a sentence into a short list of keywords.
- `topic-classifier` is a `decoding` actuator. It changes the keywords into a task decision (a label). It does not recreate the sentence.

## Before you start

1. Start a [Nexgen Server](https://github.com/iamalreadynoob/nexgen-server#setup).
2. Install `nexgenpy` (see the [README](../README.md#install-the-library)).
3. Set the environment variables:

   ```bash
   export NEXGEN_BASE_URL="http://localhost:8000/api/v1"
   export NEXGEN_API_KEY="<your-key>"
   ```

## Step 1: Register the actuators

Make a file `publish.py`:

```python
import logging

from nexgenpy import actuator

logging.basicConfig(level=logging.INFO)


@actuator(
    name="keyword-extractor",
    atype="coding",
    version="1.0.0",
    is_latest=True,
    requirements=None,
)
def extract(text: str, max_words: int = 5) -> dict:
    import re

    stop_words = {"the", "a", "an", "of", "to", "and", "is", "in"}
    words = re.findall(r"[a-z]+", text.lower())
    keywords = [word for word in words if word not in stop_words]
    return {"keywords": keywords[:max_words]}


@actuator(
    name="topic-classifier",
    atype="decoding",
    version="1.0.0",
    is_latest=True,
    requirements=None,
)
def classify(keywords: list[str]) -> dict:
    weather_words = {"rain", "sun", "wind", "storm", "cloud", "snow"}
    hits = sum(1 for word in keywords if word in weather_words)
    return {"label": "weather" if hits > 0 else "other"}


if __name__ == "__main__":
    print("keyword-extractor:", extract())
    print("topic-classifier:", classify())
```

Run it:

```bash
python publish.py
```

Each call prints `True` if the server accepted the actuator. A call to a decorated function does not run the function. It sends the function to the server.

> [!NOTE]
> The `import re` statement is in the function body. The server stores only the function, so a module-level import is not available when the actuator runs. See [Writing actuators](writing-actuators.md).

## Step 2: Run the transmitter

Make a file `transmitter.py`:

```python
from nexgenpy import run_actuator

features = run_actuator(
    name="keyword-extractor",
    data={"text": "A storm with strong wind is coming to the coast"},
)

print(features)
# {'keywords': ['storm', 'with', 'strong', 'wind', 'coming']}
```

The first run downloads the actuator to `nexgen_actuators/keyword-extractor/`. To download it before the first run, call `load_actuator("keyword-extractor")`.

The application sends `features` to the receiver. `nexgenpy` does not carry data between the transmitter and the receiver. Use the link of your application, for example a socket, a message queue or a radio.

## Step 3: Run the receiver

Make a file `receiver.py`:

```python
from nexgenpy import Actuator

classifier = Actuator(name="topic-classifier")

features = {"keywords": ["storm", "with", "strong", "wind", "coming"]}
decision = classifier.run(data=features)

print(decision)
# {'label': 'weather'}
```

The `Actuator` class imports `method.py` one time. Use it when you run an actuator many times.

## Step 4: Store the output on the server

Give `dst` and `dst_headers` to send the output to the server as a data item:

```python
import os

from nexgenpy import run_actuator

features = run_actuator(
    name="keyword-extractor",
    data={"text": "A storm with strong wind is coming to the coast"},
    data_specs={"language": "en"},
    dst=os.environ["NEXGEN_BASE_URL"],
    dst_headers={"X-API-Key": os.environ["NEXGEN_API_KEY"]},
)
```

This call does these steps:

1. It runs the actuator.
2. It sends the original input to `POST {dst}/content` in a background thread. To stop this upload, set `dst_save_original=False`.
3. It sends the output to `POST {dst}/data`, with the server `id` of the actuator.
4. It returns the output.

## Step 5: Publish a new version

Change the function, increase the version and register it again:

```python
@actuator(
    name="keyword-extractor",
    atype="coding",
    version="1.1.0",
    is_latest=True,
    requirements=None,
)
def extract(text: str, max_words: int = 8) -> dict:
    ...
```

The local copy does not change automatically. Load the actuator again on each machine:

```python
from nexgenpy import load_actuator

load_actuator("keyword-extractor")
```

`load_actuator` compares the local `card.json` with the server. It replaces the local copy only if the `id` or the `version` is different.

## Next steps

- [Writing actuators](writing-actuators.md) gives the rules for actuator functions.
- [API reference](api/actuator.md) gives all parameters.
- [Concepts](concepts.md) explains how actuators fit a SemCom pipeline.
