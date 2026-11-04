from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import datasets
from huggingface_hub import snapshot_download
import numpy as np
import requests
import scipy.io.wavfile
import yaml
from tqdm.auto import tqdm


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
CACHE = ROOT / "cache"
OPENWAKEWORD = CACHE / "openWakeWord"
PIPER = CACHE / "piper-sample-generator"


def run(args: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(args), flush=True)
    env = os.environ.copy()
    venv_lib = ROOT / ".venv" / "lib" / "python3.10" / "site-packages"
    piper_libs = venv_lib / "piper_phonemize.libs"
    phoneme_data = venv_lib / "piper_phonemize" / "espeak-ng-data"
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        [str(ROOT / ".venv" / "lib"), str(piper_libs), env.get("LD_LIBRARY_PATH", "")]
    )
    env["ESPEAK_DATA_PATH"] = str(phoneme_data)
    subprocess.run(args, cwd=cwd, check=True, env=env)


def download(url: str, target: Path, min_bytes: int = 1_000_000) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size >= min_bytes:
        return
    run(["wget", "-q", "-c", "-O", str(target), url])
    if not target.exists() or target.stat().st_size < min_bytes:
        raise RuntimeError(f"Download incomplete or too small: {target}")


def download_npy_prefix(url: str, target: Path, samples: int) -> None:
    """Range-download a valid leading slice of a large row-major NPY feature array."""
    target.parent.mkdir(parents=True, exist_ok=True)
    header_response = requests.get(url, headers={"Range": "bytes=0-4095"}, timeout=90)
    header_response.raise_for_status()
    header = header_response.content[:4096]
    stream = io.BytesIO(header)
    version = np.lib.format.read_magic(stream)
    shape, fortran_order, dtype = np.lib.format._read_array_header(stream, version)
    data_offset = stream.tell()
    if fortran_order or len(shape) < 1 or samples < 1 or samples > shape[0]:
        raise ValueError(f"Unsupported feature array layout: {shape}, fortran={fortran_order}")
    target_shape = (samples, *shape[1:])
    payload_bytes = int(np.prod(target_shape)) * dtype.itemsize
    end_byte = data_offset + payload_bytes - 1
    target_tmp = target.with_suffix(target.suffix + ".part")
    with requests.get(url, headers={"Range": f"bytes=0-{end_byte}"}, stream=True, timeout=(30, 120)) as response:
        response.raise_for_status()
        remaining = end_byte + 1
        with target_tmp.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if not chunk:
                    continue
                f.write(chunk[:remaining])
                remaining -= min(len(chunk), remaining)
                if remaining <= 0:
                    break
    if target_tmp.stat().st_size < end_byte + 1:
        raise RuntimeError(f"Incomplete ranged feature download: {target_tmp.stat().st_size} bytes")
    with target_tmp.open("rb") as src, target.open("wb") as dst:
        np.lib.format.write_array_header_1_0(
            dst, {"descr": dtype.str, "fortran_order": False, "shape": target_shape}
        )
        src.seek(data_offset)
        remaining = payload_bytes
        while remaining:
            chunk = src.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise RuntimeError("Feature array prefix ended unexpectedly.")
            dst.write(chunk)
            remaining -= len(chunk)
    target_tmp.unlink()


def prepare_repositories() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if not (OPENWAKEWORD / "openwakeword" / "train.py").is_file():
        if OPENWAKEWORD.exists():
            shutil.rmtree(OPENWAKEWORD)
        run(["git", "clone", "https://github.com/dscripka/openWakeWord.git", str(OPENWAKEWORD)])
    if not (PIPER / "generate_samples.py").is_file():
        if PIPER.exists():
            shutil.rmtree(PIPER)
        run(["git", "clone", "https://github.com/dscripka/piper-sample-generator.git", str(PIPER)])
    # This fork expects the LibriTTS checkpoint in this location.
    download(
        "https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/"
        "en_US-libritts_r-medium.pt",
        PIPER / "models" / "en_US-libritts_r-medium.pt",
    )
    default_piper_model = PIPER / "models" / "en-us-libritts-high.pt"
    if not default_piper_model.is_file():
        # openWakeWord's pinned Piper fork defaults to this basename and has its
        # matching config JSON checked into the repo; use the official LibriTTS
        # checkpoint downloaded above.
        shutil.copy2(PIPER / "models" / "en_US-libritts_r-medium.pt", default_piper_model)
    run([sys.executable, "-m", "pip", "install", "-e", str(OPENWAKEWORD), "--no-deps"])
    feature_models = OPENWAKEWORD / "openwakeword" / "resources" / "models"
    feature_models.mkdir(parents=True, exist_ok=True)
    for filename in ("melspectrogram.onnx", "embedding_model.onnx"):
        download(
            f"https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{filename}",
            feature_models / filename,
        )
    # piper-phonemize bundles a versioned eSpeak shared library, while
    # espeak-phonemizer loads the conventional libespeak-ng.so.1 name.
    venv_lib = Path(sys.prefix) / "lib"
    site_packages = venv_lib / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    bundled_espeak = sorted((site_packages / "piper_phonemize.libs").glob("libespeak-ng-*.so.*"))
    espeak_link = venv_lib / "libespeak-ng.so.1"
    if bundled_espeak and not espeak_link.exists():
        espeak_link.symlink_to(bundled_espeak[0])


def write_wav(path: Path, audio: dict) -> None:
    arr = np.asarray(audio["array"])
    scipy.io.wavfile.write(str(path), 16000, (arr * 32767).astype(np.int16))


def prepare_data(feature_samples: int) -> None:
    for name in ("mit_rirs", "musan_source", "musan_bg"):
        (DATA / name).mkdir(parents=True, exist_ok=True)

    rir_files = list((DATA / "mit_rirs").glob("*.wav"))
    if len(rir_files) < 200:
        print("Downloading MIT room impulse responses...")
        rir_ds = datasets.load_dataset(
            "davidscripka/MIT_environmental_impulse_responses",
            split="train",
            streaming=True,
        )
        rir_count = 0
        for i, row in enumerate(tqdm(rir_ds, desc="MIT RIR")):
            audio = row["audio"]
            name = Path(audio["path"]).name if audio.get("path") else f"rir_{i:04d}.wav"
            write_wav(DATA / "mit_rirs" / name, audio)
            rir_count += 1
        if rir_count == 0:
            raise RuntimeError("MIT RIR dataset returned no files.")

    # The old AudioSet shard URL used by many copied notebooks is no longer present.
    # MUSAN is a smaller, real speech/music/noise set with stable HF hosting.
    musan_bg = DATA / "musan_bg"
    if not list(musan_bg.glob("*.wav")):
        print("Downloading MUSAN speech/music/noise backgrounds (~585 MB)...")
        snapshot_download(
            repo_id="FluidInference/musan",
            repo_type="dataset",
            allow_patterns=["noise/**/*.wav", "music/**/*.wav", "speech/**/*.wav"],
            local_dir=str(DATA / "musan_source"),
        )
        source_root = DATA / "musan_source"
        wavs = list(source_root.rglob("*.wav"))
        if not wavs:
            raise RuntimeError("MUSAN download completed but no WAV files were found.")
        for wav in tqdm(wavs, desc="Preparing MUSAN"):
            rel = wav.relative_to(source_root).as_posix().replace("/", "_")
            shutil.copy2(wav, musan_bg / rel)

    download_npy_prefix(
        "https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/"
        "openwakeword_features_ACAV100M_2000_hrs_16bit.npy",
        DATA / f"openwakeword_features_ACAV100M_{feature_samples}.npy",
        feature_samples,
    )
    download(
        "https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/"
        "validation_set_features.npy",
        DATA / "validation_set_features.npy",
    )


def train(wake_word: str, steps: int, feature_samples: int) -> None:
    template = OPENWAKEWORD / "examples" / "custom_model.yml"
    if not template.is_file():
        raise FileNotFoundError(f"Official training config not found: {template}")
    with template.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    model_name = "_".join(wake_word.lower().split())
    model_dir = OUTPUT / "my_custom_model"
    config.update(
        {
            "model_name": model_name,
            "target_phrase": [wake_word.lower()],
            "steps": steps,
            "output_dir": str(model_dir),
            "piper_sample_generator_path": str(PIPER),
            "rir_paths": [str(DATA / "mit_rirs")],
            "background_paths": [str(DATA / "musan_bg")],
            "background_paths_duplication_rate": [1],
            "false_positive_validation_data_path": str(DATA / "validation_set_features.npy"),
            "feature_data_files": {
                "ACAV100M_sample": str(DATA / f"openwakeword_features_ACAV100M_{feature_samples}.npy")
            },
        }
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    config_path = OUTPUT / "my_model.yaml"
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    train_script = OPENWAKEWORD / "openwakeword" / "train.py"
    compat_entry = ROOT / "train_entry.py"
    for flag in ("--generate_clips", "--augment_clips", "--train_model"):
        run([sys.executable, str(compat_entry), str(train_script),
             "--training_config", str(config_path), flag], cwd=ROOT)
    print(f"Training complete. Model output directory: {model_dir / model_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an openWakeWord model locally in Docker.")
    parser.add_argument("--wake-word", default="Hey Axiom")
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--feature-samples", type=int, default=250000,
                        help="Leading ACAV100M feature rows to use (default 250000, downloads only that slice).")
    parser.add_argument("--skip-data-download", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prepare_repositories()
    if not args.skip_data_download:
        prepare_data(args.feature_samples)
    train(args.wake_word, args.steps, args.feature_samples)


if __name__ == "__main__":
    main()

