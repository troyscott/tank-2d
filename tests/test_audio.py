from tanks import audio


def test_sound_files_exist():
    assert set(audio._SOUND_FILES.keys()) == {"impact"}
    for filename in audio._SOUND_FILES.values():
        path = audio._SOUND_DIR / filename
        assert path.is_file(), f"missing sound file: {path}"
        assert path.stat().st_size > 0, f"empty sound file: {path}"


def test_credits_file_exists():
    assert (audio._SOUND_DIR / "CREDITS.txt").is_file()


def test_sound_dir_only_contains_expected_assets():
    expected = set(audio._SOUND_FILES.values()) | {"CREDITS.txt"}
    actual = {p.name for p in audio._SOUND_DIR.iterdir() if not p.name.startswith(".")}
    extras = actual - expected
    assert not extras, f"unexpected files in sounds dir: {extras}"
