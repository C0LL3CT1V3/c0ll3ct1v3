from app.services.media_type import infer_asset_type, infer_mime_type


def test_infer_image_from_extension_overrides_audio_hint():
    assert infer_asset_type("photo.jpg", "application/octet-stream", "audio") == "image"


def test_infer_audio_from_mime():
    assert infer_asset_type("track", "audio/mpeg", None) == "audio"


def test_infer_image_from_mime():
    assert infer_asset_type("file", "image/png", "audio") == "image"


def test_infer_mime_from_extension_when_generic():
    assert infer_mime_type("shot.png", "application/octet-stream") == "image/png"
