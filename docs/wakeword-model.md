# Custom Wake-Word Model

Axiom requires a custom ONNX classifier trained for the exact phrase `Hey Axiom`. The runtime does not load openWakeWord's included pre-trained wake-word classifiers.

## Model location

The default classifier path is `%APPDATA%\Axiom\models\hey_axiom.onnx`. Set `wakeword.model_path` in `%APPDATA%\Axiom\config.toml` to use another location. Keep the classifier and the `openwakeword` feature-asset directory together; `axiom prepare-wakeword` creates that directory beside the configured classifier.

Model files, generated speech, and training data are local artifacts and must not be committed to the public Axiom repository unless their provenance and licenses have been reviewed.

## Training route

The openWakeWord project provides an [automatic training notebook](https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb?usp=sharing) and a [more configurable training notebook](https://github.com/dscripka/openWakeWord/blob/v0.6.0/notebooks/training_models.ipynb). The automatic workflow is a quick starting point, but its authors warn that model performance can be low in some deployment environments. Use a custom classifier for `Hey Axiom` and export an ONNX file for Axiom.

The training workflow needs positive examples of the phrase and negative speech/noise examples. The upstream guide recommends several thousand positive examples as a starting point and explains that substantial negative audio helps reduce false activations. Training is separate from inference and can be done on a cloud or development machine; the N100 only needs to run the exported ONNX classifier.

## Licensing and data provenance

The openWakeWord runtime is Apache-2.0, but its included pre-trained classifiers are CC BY-NC-SA 4.0 and are not used by Axiom. The upstream synthetic-speech tooling uses TTS models with separate licenses. Review the licenses for any TTS weights, voice datasets, and training audio before generating or distributing a classifier. See the [upstream model training and license notes](https://github.com/dscripka/openWakeWord/blob/v0.6.0/README.md#training-new-models).

## Validation

Do not treat a successful ONNX load as evidence of wake-word quality. After the target microphone is available, evaluate the classifier in the intended room with varied positive pronunciations and long negative recordings. Adjust `wakeword.threshold` and `wakeword.patience` based on missed activations and false triggers. Keep these measurements with the model's provenance notes.
