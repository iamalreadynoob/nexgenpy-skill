# Glossary

## Project terms

| Term | Definition |
|---|---|
| **Actuator** | A versioned, named Python function that processes data. The server stores its source code. Clients download it and run it. |
| **Actuator type** | `coding` or `decoding`. The `atype` parameter of `@actuator` and the `actuator_type` field on the server. |
| **Coding actuator** | An actuator that changes a source into a representation for transmission. It can be a semantic encoder, a channel encoder or a JSCC encoder. |
| **Decoding actuator** | An actuator that changes a received representation into an output. The output is a reconstruction of the source or a task decision. |
| **Latest version** | The one active version of an actuator name that has `latest: true` on the server. `load_actuator` always downloads it. |
| **Card** | The `card.json` file in the local actuator directory. It stores the server `id`, the `version` and other metadata. |
| **Data item** | A record on the server that stores the output of an actuator (`metadata`), the `actuator_id`, a `linked_resource` and `specs`. |
| **Content item** | A record on the server that stores the original input of an actuator, with an `identifier` and `specs`. |
| **Linked resource** | The UUID that connects a data item to its content item. |
| **`dst`** | The root URL of the server that gets the data items and the content items. |
| **Actuators directory** | The local directory for downloaded actuators. The default is `nexgen_actuators`. |

## SemCom terms

| Term | Definition |
|---|---|
| **SemCom** | Semantic communication. A communication paradigm whose design objective is the correct delivery of the meaning, or of the task-relevant content, of a message. |
| **Semantic-level communication** | SemCom in which the receiver recovers the meaning or recreates the source. |
| **Goal-oriented / task-oriented communication** | SemCom in which the receiver must perform a task (classification, detection, control), not reconstruct the source. The transmitter transmits only task-relevant features. |
| **Semantic information** | The meaning that a message carries relative to a shared context or shared knowledge. It is different from Shannon's statistical (syntactic) information. |
| **Semantic encoder** | A module (usually a neural network) that extracts a compact representation of the meaning, or of the task-relevant features, of the source. |
| **Semantic decoder** | A module that interprets the received representation. It recovers the meaning, reconstructs the source, or outputs a task decision directly. |
| **Channel encoder / decoder** | A module that protects semantic features against channel impairments. In learned systems, it is often merged with the semantic encoder (see JSCC). |
| **Knowledge base (KB)** | Shared background knowledge that the transmitter and the receiver use to encode and interpret meaning. Examples: datasets, trained model weights, ontologies, knowledge graphs, codebooks. |
| **Background knowledge mismatch** | A divergence between the KB of the transmitter and the KB of the receiver. It causes misinterpretation even when the physical link has no errors. |
| **Semantic noise** | Any disturbance that changes meaning. Examples: ambiguity, KB mismatch, physical-channel errors that change semantics, adversarial perturbations. |
| **Semantic fidelity** | The degree to which the received meaning matches the transmitted meaning. |
| **JSCC** | Joint source–channel coding. Coding that designs compression and error protection together. It replaces the separate chain of source coding and channel coding. |
| **DJSCC** | Deep JSCC. JSCC in which the encoder and the decoder are neural networks, trained end-to-end through a differentiable channel model. |
| **SSCC** | Separate source–channel coding. The conventional design, for example JPEG/BPG/VVC + LDPC/Polar codes. It is optimal only asymptotically (infinite block length). |
| **Graceful degradation** | The quality decreases smoothly as the SNR decreases. This is a hallmark of DJSCC. |
| **Cliff effect** | In digital SSCC, the reconstruction quality collapses abruptly when the channel SNR drops below the design point. |
| **Generative SemCom (GenSC)** | SemCom in which the receiver regenerates content from compact semantic cues with a generative prior (VAE, GAN, diffusion model, LLM). |
| **Hallucination** | Generated content that looks correct but is wrong. A risk of generative receivers. |
| **Split / edge inference** | The encoder is the head of a DNN on a device. The decoder is the tail on the edge server. The semantic features are intermediate activations. |
| **IMT-2030** | The formal ITU designation for 6G. |

## Abbreviations

| Abbreviation | Meaning |
|---|---|
| AoI | Age of Information |
| BER | Bit error rate |
| BLER | Block error rate |
| CBR | Channel bandwidth ratio |
| CSI | Channel state information |
| DNN | Deep neural network |
| KB | Knowledge base |
| LLM | Large language model |
| SNR | Signal-to-noise ratio |
| UUID | Universally unique identifier |
| VoI | Value of Information |
