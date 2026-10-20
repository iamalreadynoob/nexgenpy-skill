# Security

This document describes the security risks of `nexgenpy` and of SemCom systems in general.

## Downloaded actuator code

`nexgenpy` runs code that it downloads from the server. Treat each actuator as code that you install.

| Step | What runs | Where |
|---|---|---|
| `load_actuator` | `pip install -r requirements.txt` with the requirements from the server. pip can run build scripts of the packages. | A new venv in `{actuators_dir}/{name}/.venv` |
| `run_actuator`, `Actuator` | `method.py` with the source code from the server | The current Python process, with all its permissions |

The actuator code has the same access as your application. It can read files, read environment variables (including `NEXGEN_API_KEY`) and send network requests.

Do these steps to decrease the risk:

1. Use only a Nexgen Server that you trust.
2. Give the API key only to trusted people and machines. A caller with the key can publish a new latest version of each actuator.
3. Read `method.py` and `requirements.txt` before the first run of a new version.
4. Pin each requirement to a version, for example `numpy==2.0.0`.
5. Run actuators in a container or as a user with few permissions.
6. Use `try_load_actuator=False` in production. Then a missing actuator causes an error, not a download.

## Transport and keys

- Use `https://` for `NEXGEN_BASE_URL` and `dst` outside a local test setup. With `http://`, other parties on the network can read the API key and the data.
- Keep the API key in the environment or in a secret store. Do not write it in source code or in `data_specs`.
- `load_actuator` logs the server response at the `INFO` level. Do not send `INFO` logs to a place that untrusted users can read.

## Local files

- `load_actuator` rejects a `name` that is not a plain directory name, for example `"../other"`. Thus a name cannot write outside `actuators_dir`.
- `load_actuator` deletes `{actuators_dir}/{name}` before it writes a new version. Do not keep other files in that directory.
- Anyone who can write to `actuators_dir` can change `method.py`. Protect the directory with file permissions.

## Data and privacy

When `dst` is given and `dst_save_original` is `True`, `run_actuator` sends the **original input** to `{dst}/content`. If the input is private, set `dst_save_original=False`, or use a `dst` server that you control.

The output of a coding actuator can also contain private information. See the next section.

## SemCom threats

A SemCom system has threats that a classical link does not have. They apply to the actuators that you write and to the data that they make.

| Threat | Description |
|---|---|
| **Semantic eavesdropping / inference** | Intercepted features can reveal content or private attributes. An attacker can invert features to reconstruct recognizable images. |
| **Adversarial perturbations** | Small crafted perturbations, on the input or over the air, cause large semantic errors. Link-level metrics often do not show these errors. |
| **Semantic manipulation / latent tampering** | An attacker changes the meaning while the link appears healthy. |
| **Model-level attacks** | Data poisoning, backdoors, model extraction, model inversion. |
| **Availability attacks** | Jamming, flooding, and denial of service (DoS) that uses all the computation of semantic processing. |
| **Knowledge base (KB) attacks** | Corruption or desynchronization of shared knowledge bases. |

In Nexgen, an attacker with write access to the server can publish a changed actuator as the latest version. This is a model-level attack and a KB attack at the same time.

### Countermeasures

The literature lists these countermeasures:

- Adversarial training
- Input transformation and detection
- Differential privacy
- Semantic encryption and key generation
- Physical-layer security (artificial noise, covert transmission)
- Federated learning
- Blockchain-based KB integrity
- Learning methods that resist poisoning

`nexgenpy` does not implement these countermeasures. An actuator can implement some of them, for example input detection in a decoding actuator.

## Further reading

- *A Survey of Secure Semantic Communications*. [arXiv:2501.00842](https://arxiv.org/abs/2501.00842)
- *Secure Digital Semantic Communications: Fundamentals, Challenges, and Opportunities* *(preprint)*. [arXiv:2512.24602](https://arxiv.org/abs/2512.24602)
- *Rethinking Security in Semantic Communication: Latent Manipulation as a New Threat* *(preprint)*. [arXiv:2512.03361](https://arxiv.org/abs/2512.03361)

## Report a vulnerability

Do not open a public issue for a vulnerability. Contact the maintainer through the email address in `pyproject.toml`.
