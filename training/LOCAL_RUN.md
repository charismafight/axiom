# Local wake-word training

This workflow trains an ONNX classifier for Axiom's `Hey Axiom` wake phrase using openWakeWord. Run it in WSL 2 with Ubuntu 22.04 and Python 3.10. Training data, generated audio, caches, and model files stay under this directory and are not committed.

## Setup

Install the system packages in WSL:

```bash
sudo apt update
sudo apt install -y git wget build-essential python3.10-venv libsndfile1
```

From the Axiom repository root:

```bash
cd training
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-wsl.txt
```

## Train

The first run downloads the upstream openWakeWord and Piper sources, feature assets, and training inputs. The MUSAN audio download is about 585 MB; the feature file download size depends on `--feature-samples`.

```bash
python train_local.py --wake-word "Hey Axiom" --steps 20000
```

To choose a smaller or larger leading slice of the ACAV100M feature array:

```bash
python train_local.py --wake-word "Hey Axiom" --steps 20000 --feature-samples 250000
```

After inputs have been downloaded, `--skip-data-download` reuses them:

```bash
python train_local.py --wake-word "Hey Axiom" --steps 20000 --skip-data-download
```

The output classifier is written to `training/output/my_custom_model/hey_axiom.onnx`. Data is stored in `training/data/`, upstream checkouts and assets in `training/cache/`, and generated clips/configuration in `training/output/`.

## Data sources

- Positive phrase examples are synthesized locally with Piper using its LibriTTS checkpoint.
- Background speech, music, and noise come from the [MUSAN dataset](https://huggingface.co/datasets/FluidInference/musan), a mirror of the MUSAN corpus.
- Room impulse responses come from [MIT Environmental Impulse Responses](https://huggingface.co/datasets/davidscripka/MIT_environmental_impulse_responses).
- Negative features and false-positive validation features come from the [openWakeWord feature dataset](https://huggingface.co/datasets/davidscripka/openwakeword_features).

Review the source dataset, voice/checkpoint, and upstream project licenses before redistributing generated audio or a trained model. In particular, the openWakeWord feature dataset is marked CC BY-NC-SA 4.0, and the MIT RIR mirror does not state a clear license. The repository does not include training data or generated audio. It does include a separately published classifier under `models/`; see its provenance and license notice before use or redistribution.

See [the model and licensing notes](../docs/wakeword-model.md) for Axiom's deployment guidance.
