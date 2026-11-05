"""Command-line entry point for Axiom."""

from __future__ import annotations

import argparse
import asyncio
import math
import struct
import sys
import time

from axiom import __version__
from axiom.audio import AudioInputError, MODEL_SAMPLE_RATE, WindowsDefaultAudioInput
from axiom.config import get_config_path, load_settings
from axiom.integrations.codex_desktop import get_desktop_status
from axiom.integrations.windows_shortcut import InvalidShortcut, KeyboardShortcut
from axiom.runtime import RuntimeAdaptersPending, build_runtime
from axiom.wakeword.assets import (
    WakeWordAssetsError,
    get_feature_assets_dir,
    prepare_feature_assets,
)


def _show_status() -> int:
    print(f"Axiom {__version__}")
    print("Project stage: foundation")
    print("Microphone: Windows default input; stream is not open")
    try:
        settings = load_settings()
    except (OSError, ValueError) as error:
        print(f"User configuration: invalid ({error})")
        return 1
    if settings.wakeword_model_path and settings.wakeword_model_path.is_file():
        print(
            "Wake phrase: Hey Axiom (custom ONNX model: "
            f"{settings.wakeword_model_path})"
        )
    else:
        print(
            "Wake phrase: Hey Axiom (custom ONNX model missing: "
            f"{settings.wakeword_model_path})"
        )
    if settings.wakeword_model_path:
        feature_directory = get_feature_assets_dir(settings.wakeword_model_path)
        missing_features = [
            name
            for name in ("melspectrogram.onnx", "embedding_model.onnx")
            if not (feature_directory / name).is_file()
        ]
        if missing_features:
            print(
                "Wake-word feature assets: missing "
                f"({', '.join(missing_features)}; run axiom prepare-wakeword)"
            )
        else:
            print("Wake-word feature assets: ready")
    if settings.codex_voice_shortcut:
        try:
            shortcut = KeyboardShortcut.parse(settings.codex_voice_shortcut)
        except InvalidShortcut as error:
            print(f"Codex voice shortcut: invalid ({error})")
            return 1
        print(f"Codex voice shortcut: {shortcut.display}")
    else:
        print(f"Codex voice shortcut: not configured ({get_config_path()})")
    return 0


def _show_codex_status() -> int:
    status = get_desktop_status()
    try:
        settings = load_settings()
    except (OSError, ValueError) as error:
        print(f"Axiom configuration: invalid ({error})")
        return 1

    if status.running is True:
        print("ChatGPT Desktop: running")
    elif status.running is False:
        print("ChatGPT Desktop: not running")
    else:
        print("ChatGPT Desktop: status unavailable")
        if status.detail:
            print(f"Details: {status.detail}")

    if settings.codex_voice_shortcut:
        try:
            shortcut = KeyboardShortcut.parse(settings.codex_voice_shortcut)
        except InvalidShortcut as error:
            print(f"Codex voice shortcut: invalid ({error})")
            return 1
        print(f"Codex voice shortcut: {shortcut.display}")
    else:
        print(f"Codex voice shortcut: not configured ({get_config_path()})")
    print("Set the same shortcut in ChatGPT Desktop Settings > Voice.")
    print("Open a Codex task before triggering Voice with the wake phrase.")
    print("Codex handles conversation capture and speech output.")
    return 0 if status.running is not None else 1


def _run_runtime() -> int:
    try:
        runtime = build_runtime()
    except RuntimeAdaptersPending as error:
        print(str(error), file=sys.stderr)
        return 2

    try:
        asyncio.run(runtime.run())
    except KeyboardInterrupt:
        return 0
    except AudioInputError as error:
        print(f"Axiom microphone input failed: {error}", file=sys.stderr)
        return 1
    return 0


def _parse_test_duration(value: str) -> float:
    try:
        duration = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("duration must be a number of seconds") from error
    if not math.isfinite(duration) or not 1.0 <= duration <= 60.0:
        raise argparse.ArgumentTypeError("duration must be between 1 and 60 seconds")
    return duration


async def _capture_microphone_test(
    duration: float,
) -> tuple[float, int, int, int, int, int, float, float]:
    audio = WindowsDefaultAudioInput()
    frame_count = 0
    sample_count = 0
    peak = 0
    sum_squares = 0
    clipped_samples = 0
    start_time = time.monotonic()

    async with audio:
        capture_rate = audio.capture_sample_rate
        capture_channels = audio.capture_channels
        if capture_rate is None or capture_channels is None:
            raise AudioInputError("The microphone did not report its capture format.")

        print(
            f"Windows default input: {capture_rate:g} Hz, "
            f"{capture_channels} channel(s), float32 capture."
        )
        print(
            f"Wake-word input: {MODEL_SAMPLE_RATE} Hz, mono, signed 16-bit PCM."
        )
        print(f"Speak normally for {duration:g} seconds. Audio is not saved.")

        try:
            async with asyncio.timeout(duration):
                async for frame in audio.frames():
                    frame_count += 1
                    for (sample,) in struct.iter_unpack("<h", frame.pcm):
                        absolute = abs(sample)
                        peak = max(peak, absolute)
                        sum_squares += sample * sample
                        if absolute >= 32_760:
                            clipped_samples += 1
                        sample_count += 1
        except TimeoutError:
            pass

    elapsed = time.monotonic() - start_time
    return (
        capture_rate,
        capture_channels,
        frame_count,
        sample_count,
        peak,
        clipped_samples,
        math.sqrt(sum_squares / sample_count) if sample_count else 0.0,
        elapsed,
    )


def _test_microphone(duration: float) -> int:
    try:
        (
            capture_rate,
            capture_channels,
            frame_count,
            sample_count,
            peak,
            clipped_samples,
            rms,
            elapsed,
        ) = asyncio.run(_capture_microphone_test(duration))
    except AudioInputError as error:
        print(f"Microphone test failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Microphone test cancelled.", file=sys.stderr)
        return 130

    peak_dbfs = 20.0 * math.log10(peak / 32_768.0) if peak else float("-inf")
    rms_dbfs = 20.0 * math.log10(rms / 32_768.0) if rms else float("-inf")
    peak_text = f"{peak_dbfs:.1f} dBFS" if math.isfinite(peak_dbfs) else "-inf dBFS"
    rms_text = f"{rms_dbfs:.1f} dBFS" if math.isfinite(rms_dbfs) else "-inf dBFS"
    clipping_percent = 100.0 * clipped_samples / sample_count if sample_count else 0.0

    print(f"Captured {frame_count} model frames ({sample_count} samples) in {elapsed:.1f} seconds.")
    print(f"Peak level: {peak_text}; RMS level: {rms_text}.")
    print(f"Near-clipped wake-word samples: {clipping_percent:.3f}%.")
    if peak == 0:
        print("No non-zero audio samples were received. Check Windows input and microphone mute.")
        return 1
    print(
        f"Microphone input is active at {capture_rate:g} Hz with "
        f"{capture_channels} channel(s). This checks signal flow, not wake-word accuracy."
    )
    return 0


def _prepare_wakeword() -> int:
    try:
        settings = load_settings()
        if settings.wakeword_model_path is None:
            raise WakeWordAssetsError("No wake-word model path is configured.")
        results = prepare_feature_assets(settings.wakeword_model_path)
    except (OSError, ValueError, WakeWordAssetsError) as error:
        print(f"Could not prepare wake-word assets: {error}", file=sys.stderr)
        return 1

    for result in results:
        state = "downloaded" if result.downloaded else "already valid"
        print(f"Wake-word feature asset {state}: {result.path}")
    print("Shared ONNX feature assets are ready.")
    print("No pre-trained wake-word classifier models were downloaded.")
    if not settings.wakeword_model_path.is_file():
        print(
            "Custom Hey Axiom classifier still needed: "
            f"{settings.wakeword_model_path}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axiom",
        description="Axiom, your AI conversation companion.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Axiom {__version__}",
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("status", help="Show Axiom runtime status.")
    commands.add_parser("codex", help="Show Codex Desktop Voice trigger readiness.")
    commands.add_parser("run", help="Run Axiom as a resident user-session process.")
    commands.add_parser(
        "prepare-wakeword",
        help="Download and validate shared wake-word feature assets.",
    )
    test_parser = commands.add_parser(
        "test",
        help="Check the Windows default microphone without saving audio.",
    )
    test_parser.add_argument(
        "--duration",
        type=_parse_test_duration,
        default=5.0,
        metavar="SECONDS",
        help="Capture duration from 1 to 60 seconds (default: 5).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "codex":
        return _show_codex_status()
    if args.command == "run":
        return _run_runtime()
    if args.command == "prepare-wakeword":
        return _prepare_wakeword()
    if args.command == "test":
        return _test_microphone(args.duration)
    return _show_status()
