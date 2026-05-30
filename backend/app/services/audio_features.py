"""Extract audio features from local files (librosa + ffmpeg normalize)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _normalize_to_wav(audio_path: str) -> tuple[str, bool]:
    """Return path to loadable audio; temp WAV if conversion was needed."""
    ext = Path(audio_path).suffix.lower()
    if ext == ".wav":
        return audio_path, False
    if not shutil.which("ffmpeg"):
        # Let librosa try the source file (works for some formats when codecs are available).
        return audio_path, False
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", "22050", tmp_path],
        capture_output=True,
        timeout=120,
        check=True,
    )
    return tmp_path, True


def extract_features(audio_path: str) -> dict[str, Any]:
    """Extract BPM, key, spectral profile, MFCCs from an audio file."""
    import librosa
    import numpy as np

    load_path, is_temp = _normalize_to_wav(audio_path)
    try:
        y, sr = librosa.load(load_path, sr=None, mono=True)
    finally:
        if is_temp and os.path.exists(load_path):
            os.unlink(load_path)

    tempo_result = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo_result, tuple):
        tempo = tempo_result[0]
    else:
        tempo = tempo_result
    bpm = float(tempo) if not hasattr(tempo, "__len__") else float(tempo.item())

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    best_corr = -1.0
    best_key = 0
    best_mode = "major"
    for shift in range(12):
        shifted = chroma_mean[shift:] if shift == 0 else np.concatenate([chroma_mean[shift:], chroma_mean[:shift]])
        corr_major = np.corrcoef(shifted, major_profile)[0, 1]
        corr_minor = np.corrcoef(shifted, minor_profile)[0, 1]
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = shift
            best_mode = "major"
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = shift
            best_mode = "minor"
    key = f"{note_names[best_key]} {best_mode}"

    spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    spectral_rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))
    spectral_bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
    spectral_contrast = float(np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)))
    zero_crossing_rate = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_means = [float(np.mean(mfccs[i])) for i in range(13)]
    rms = float(np.mean(librosa.feature.rms(y=y)))
    duration = float(len(y) / sr)

    return {
        "bpm": round(bpm, 1),
        "key": key,
        "duration_seconds": round(duration, 1),
        "spectral_centroid": spectral_centroid,
        "spectral_rolloff": spectral_rolloff,
        "spectral_bandwidth": spectral_bandwidth,
        "spectral_contrast": spectral_contrast,
        "zero_crossing_rate": zero_crossing_rate,
        "rms_energy": rms,
        "mfcc_means": mfcc_means,
    }
