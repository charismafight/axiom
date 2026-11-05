"""Microphone input contracts for the Windows-default audio backend."""

from axiom.audio.io import AudioFrame, AudioInput
from axiom.audio.windows_input import AudioInputError, WindowsDefaultAudioInput

__all__ = [
    "AudioFrame",
    "AudioInput",
    "AudioInputError",
    "WindowsDefaultAudioInput",
]
