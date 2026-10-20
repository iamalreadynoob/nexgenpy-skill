# Concepts

This document explains semantic communication (SemCom) and how `nexgenpy` fits a SemCom pipeline.

## What is SemCom?

SemCom is a communication paradigm. Its design objective is the correct delivery of the *meaning*, or of the *task-relevant content*, of a message. Its objective is not the bit-exact copy of the transmitted symbols.

Classical (Shannon) systems treat the link as a pipe that ignores content. They measure success with the bit error rate (BER) or the block error rate (BLER). SemCom changes the objective from **symbol fidelity** to **semantic fidelity**. In its goal-oriented form, the objective is **task success**.

### Weaver's three levels

The literature usually frames the field with Warren Weaver's extension of Shannon's theory (1949).

| Level | Problem | Question | Typical metric |
|---|---|---|---|
| **A: Technical** | Syntactic | How accurately can the symbols be transmitted? | BER, BLER, PSNR |
| **B: Semantic** | Meaning | How precisely do the symbols convey the intended meaning? | Sentence similarity, LPIPS, semantic distortion |
| **C: Effectiveness** | Pragmatic / goal | How effectively does the received meaning affect behaviour or achieve the goal? | Task accuracy, control cost, AoI/VoI |

Level B is SemCom in the narrow sense. Level C is **goal-oriented** (also called **task-oriented**) communication. Most current literature puts both levels under the SemCom name.

The field does not have an agreed definition or an agreed unit of semantic information yet.

### Why SemCom matters

- A system that sends only the semantically relevant information needs less bandwidth and power, and has lower latency.
- Learned joint source–channel coding (JSCC) schemes lose quality gradually at low signal-to-noise ratio (SNR). They do not fail abruptly.
- 6G is expected to carry machine-to-machine and agent-to-agent traffic. In that traffic, the receiver is a model that does a task, not a human who views raw data.

## The two objectives

`nexgenpy` and Nexgen Server support two objectives. Each application uses one of them for each link.

| Objective | The receiver… | Output `ŝ` | Example metric |
|---|---|---|---|
| **Semantic-level communication** | recovers the meaning, or recreates the source | A reconstruction | Sentence similarity, LPIPS |
| **Goal-oriented (task-oriented) communication** | does a task with the received representation | A task decision, for example a class label | Classification accuracy, detection mAP |

The [Quick start](quickstart.md) example is goal-oriented. The receiver outputs a label and does not recreate the sentence.

## The reference pipeline

The diagram shows the reference SemCom pipeline. The boxes show where Nexgen actuators can go.

```mermaid
flowchart LR
    S["Source s<br/>text / image / speech / video / sensor"] --> CA

    subgraph CA["coding actuator"]
        SE["Semantic Encoder"] --> CE["Channel Encoder"]
    end

    KBT[("Transmitter<br/>Knowledge Base K_T")] -.-> CA
    CA -- "x" --> CH{{"Physical Channel<br/>y = h·x + n"}}
    CH -- "y" --> DA

    subgraph DA["decoding actuator"]
        CD["Channel Decoder"] --> SD["Semantic Decoder"]
    end

    KBR[("Receiver<br/>Knowledge Base K_R")] -.-> DA
    DA --> O["Output ŝ<br/>reconstruction or task decision"]
    KBT <-. "synchronization / sharing" .-> KBR
```

| Symbol | Meaning |
|---|---|
| `s` | Source message (sentence, image, signal) |
| `z` | Semantic latent / feature vector |
| `x` | Channel input symbols |
| `y` | Channel output, `y = h·x + n` |
| `h` | Channel coefficient or matrix (channel state information, CSI) |
| `n` | Additive white Gaussian noise, `n ~ CN(0, σ²)` |
| `ŝ` | Reconstructed source or task output |
| `K_T`, `K_R` | Transmitter and receiver knowledge base |

`nexgenpy` does not model the physical channel. The application carries the output of the coding actuator to the receiver.

## Actuators in the pipeline

An actuator is a versioned, named Python function. Its type is `coding` or `decoding`.

- A **`coding`** actuator changes a source into a representation for transmission. It can be a semantic encoder, a channel encoder or a JSCC encoder.
- A **`decoding`** actuator changes a received representation into an output. The output is a reconstruction of the source or a task decision.

The actuator type does not say which SemCom block the actuator implements. The pipeline variant decides it:

| Variant | Coding actuator | Decoding actuator |
|---|---|---|
| **Separate semantic + channel coding** | Semantic encoder. A conventional channel code protects the features. | Semantic decoder |
| **Joint semantic–channel coding** | One network that contains the semantic encoder and the channel encoder (for example DeepSC or deep JSCC) | One network that contains the channel decoder and the semantic decoder |
| **Task-oriented (no reconstruction)** | Semantic encoder that keeps only the task-relevant features | Semantic decoder that outputs a decision directly |
| **Generative** | Encoder of compact cues (prompt, latent, sketch, tokens) | Generative model, conditioned on the received cues |
| **Split / edge inference** | Head of a deep neural network (DNN) on the device | Tail of the DNN on the edge server |

> [!WARNING]
> A generative decoding actuator can make content that looks correct but is wrong (hallucination). Perceptual metrics do not show this error. Also check semantic consistency, for example with CLIP score or semantic segmentation mIoU for images.

## Knowledge bases and versions

A knowledge base (KB) is the shared background knowledge that the transmitter and the receiver use to encode and interpret meaning. Examples are datasets, trained model weights, ontologies, knowledge graphs and codebooks.

If an actuator contains or downloads trained model weights, those weights are a part of the KB. A divergence between `K_T` and `K_R` is a **background knowledge mismatch**. It causes misinterpretation even when the physical link has no errors.

Nexgen versions help the two sides use the same actuator:

- For each actuator name, exactly one active version on the server is the latest.
- `load_actuator` always downloads the latest version.
- The server accepts a data item only from the latest version.

`nexgenpy` does not compare the transmitter version with the receiver version. A machine keeps its local copy until it calls `load_actuator` again. To keep the two sides in step, call `load_actuator` on each machine after each new version.

## Data and content items

| Item | What it stores | How `nexgenpy` makes it |
|---|---|---|
| **Data** | The output of an actuator (`metadata`), the `actuator_id`, an optional `linked_resource` and free-form `specs` | `run_actuator(..., dst=...)` sends `POST {dst}/data` |
| **Content** | An `identifier` and the original input of the actuator in `specs` | `run_actuator(..., dst=..., dst_save_original=True)` sends `POST {dst}/content` |

When `dst_save_original` is `True`, the library makes a random UUID. It uses the UUID as the content `identifier` and as the data `linked_resource`. Thus an application can find the original input of each output. For example, it can compare a reconstruction with its source, or train a model again.

## Standardization

As of October 2026, no 3GPP release specifies SemCom. 3GPP Release 20 is the 6G study phase, and Release 21 will carry the first normative 6G specifications. Nexgen does not follow a standard format for actuators, features or KBs.

## Further reading

- [Glossary](glossary.md) defines each term in this document.
- [References](references.md) lists surveys and papers about SemCom.
