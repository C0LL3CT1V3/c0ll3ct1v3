"""Tests for audience mapper genre rules."""

from app.services.genre_classify import classify_genre, genre_search_queries


def test_classify_folk_tempo():
    features = {
        "bpm": 95.0,
        "spectral_centroid": 2200.0,
        "spectral_rolloff": 5000.0,
        "spectral_contrast": 18.0,
        "zero_crossing_rate": 0.04,
        "mfcc_means": [-100.0, 30.0] + [0.0] * 11,
    }
    scores = classify_genre(features)
    assert scores[0][0] in ("Folk / Americana", "Outlaw Country", "Singer-Songwriter")
    assert scores[0][1] > 30


def test_genre_search_queries():
    assert "americana" in genre_search_queries("Folk / Americana")
