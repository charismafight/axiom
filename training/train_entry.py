"""Compatibility entry point for recent torchaudio versions."""
import runpy
import sys
import argparse

import torchaudio
import torch
import soundfile as sf
import numpy as np
from types import SimpleNamespace

if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda backend: None

# Recent torchaudio releases delegate load() to TorchCodec. The training
# pipeline reads WAV clips, so keep those reads compatible without another
# native dependency.
def _compat_audio_load(filepath, frame_offset=0, num_frames=-1, normalize=True,
                       channels_first=True, format=None, backend=None):
    frames = -1 if num_frames < 0 else num_frames
    audio, sample_rate = sf.read(
        filepath, start=frame_offset, frames=frames, dtype="float32", always_2d=True
    )
    if not normalize:
        audio = np.rint(audio * 32768).clip(-32768, 32767).astype(np.int16)
    audio = np.ascontiguousarray(audio.T if channels_first else audio)
    return torch.from_numpy(audio), sample_rate

torchaudio.load = _compat_audio_load

def _compat_audio_info(filepath, backend=None):
    info = sf.info(filepath)
    return SimpleNamespace(
        num_frames=info.frames,
        sample_rate=info.samplerate,
        num_channels=info.channels,
        bits_per_sample=0,
        encoding=info.subtype,
    )

torchaudio.info = _compat_audio_info

# Piper checkpoints are trusted official project artifacts and contain a
# serialized model object; PyTorch 2.6+ otherwise defaults to weights-only load.
_torch_load = torch.load
def _compat_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _torch_load(*args, **kwargs)
torch.load = _compat_torch_load

# The upstream trainer expects the TorchScript ONNX exporter. PyTorch 2.11
# defaults to the newer dynamo exporter, which has different dependencies.
_torch_onnx_export = torch.onnx.export
def _compat_onnx_export(*args, **kwargs):
    kwargs.setdefault("dynamo", False)
    return _torch_onnx_export(*args, **kwargs)
torch.onnx.export = _compat_onnx_export

# Upstream currently sets this store_true option's default to the non-empty
# string "False", which evaluates as true and unexpectedly starts TFLite
# conversion. This workflow produces ONNX, so normalize that default.
_parse_args = argparse.ArgumentParser.parse_args
def _compat_parse_args(self, *args, **kwargs):
    parsed = _parse_args(self, *args, **kwargs)
    if getattr(parsed, "convert_to_tflite", None) == "False":
        parsed.convert_to_tflite = False
    return parsed
argparse.ArgumentParser.parse_args = _compat_parse_args

script = sys.argv[1]
sys.argv = [script, *sys.argv[2:]]
runpy.run_path(script, run_name="__main__")

