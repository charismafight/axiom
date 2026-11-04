# ADR 0004: Offline Wake-Word Engine

- Status: Accepted
- Date: 2026-11-04

## Context

Axiom needs to detect `Hey Axiom` locally and offline before sending the configured ChatGPT Desktop Voice shortcut. The detector must consume the canonical microphone frames provided by Axiom and must not open or enumerate audio devices itself.

The project is public under MIT. Wake-word runtime code, model assets, custom-model training data, and any keys or account requirements have separate licensing and operating constraints that need to be considered.

## Decision

- Use the openWakeWord Python runtime through an Axiom-owned adapter.
- Load only an explicit custom ONNX classifier for `Hey Axiom`; do not load openWakeWord's built-in pretrained wake-word models.
- Keep model artifacts out of the public repository until their provenance and license are confirmed. The user supplies the model at `%APPDATA%\Axiom\models\hey_axiom.onnx` or sets another path in user configuration.
- Process only 16 kHz, mono, signed 16-bit little-endian PCM frames. The Windows audio backend remains responsible for adapting the Windows-selected default microphone to this format.
- Keep the openWakeWord dependency optional and import it only when constructing the wake-word adapter.

## Rationale

- openWakeWord supports Windows through ONNX Runtime and accepts a user-supplied model path: [openWakeWord README](https://github.com/dscripka/openWakeWord).
- The runtime source is Apache-2.0 and does not require a vendor access key for local inference.
- Its included pretrained model artifacts are licensed separately under CC BY-NC-SA. Axiom avoids those artifacts and loads a custom model only.
- Porcupine requires a Picovoice AccessKey and account-based usage limits, and Picovoice lists no dedicated plan for personal or non-commercial use. It is not selected for this personal always-on project: [Porcupine](https://picovoice.ai/docs/porcupine/), [Picovoice FAQ](https://picovoice.ai/docs/faq/general/).
- sherpa-onnx supports customizable keyword spotting and is Apache-2.0, but its published KWS model catalog does not clearly specify the artifacts' licenses. It is not selected while the model license remains unclear: [KWS model catalog](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html), [license clarification issue](https://github.com/k2-fsa/sherpa-onnx/issues/3760).

## Consequences

- Axiom needs a custom `Hey Axiom` ONNX model before wake detection can run.
- The `axiom prepare-wakeword` command downloads and validates only the shared ONNX feature-extractor assets. It does not use the upstream default downloader, which also downloads the separately licensed pre-trained wake-word classifiers.
- The custom model's own license and training-data provenance must be checked separately from the openWakeWord runtime license.
- Threshold and consecutive-frame patience require tuning with realistic room audio after the target microphone is available.
- A future change can replace the engine without changing the `WakeWordEngine` contract.

## Revisit when

- A suitable custom model cannot meet false-accept and false-reject needs on the target hardware.
- Model licensing for another engine becomes clear and better fits Axiom's distribution goals.
- Axiom expands to a platform or audio format not supported by this adapter.
