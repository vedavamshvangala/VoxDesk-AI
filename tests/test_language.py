from app.voice.language import VoiceLanguageClassifier


def classify(text, **kwargs):
    return VoiceLanguageClassifier().classify(text, **kwargs)


def test_clear_english_is_english():
    assert classify("Open Notepad")["language"] == "en"


def test_english_content_words_do_not_trigger_telugu():
    assert classify("Open YouTube and search Telugu movies")["language"] == "en"
    assert classify("Search India news in Hyderabad")["language"] == "en"


def test_telugu_script_is_telugu():
    result = classify("నోట్ప్యాడ్ ఓపెన్ చెయ్యి")
    assert result["language"] == "te"
    assert "telugu_script_supporting" in result["signals"]


def test_romanized_telugu_is_telugu():
    assert classify("notepad open cheyyi")["language"] == "te"
    assert classify("calculator open cheyyi")["language"] == "te"


def test_code_switched_commands_are_te_en():
    assert classify("YouTube open chesi search cheyyi")["language"] == "te-en"
    assert classify("notepad lo hello ani type cheyyi")["language"] == "te-en"


def test_detected_telugu_metadata_is_strong_evidence():
    result = classify(
        "open notepad",
        stt_language="te",
        language_source="detected",
    )
    assert result["language"] == "te"
    assert "stt_detected_te" in result["signals"]


def test_english_metadata_conflict_is_ambiguous():
    result = classify(
        "notepad open cheyyi",
        stt_language="en",
        language_source="detected",
    )
    assert result["language"] == "te"
    assert result["ambiguous"] is True
    assert "stt_text_conflict" in result["signals"]


def test_missing_metadata_uses_text_signals():
    result = classify("youtube open chesi search cheyyi")
    assert result["language"] == "te-en"
    assert result["stt_language"] is None


def test_requested_fallback_is_not_detected_metadata():
    result = classify(
        "Open Notepad",
        stt_language="te",
        language_source="requested_fallback",
    )
    assert result["language"] == "en"
    assert result["language_source"] == "requested_fallback"
    assert "stt_detected_te" not in result["signals"]


def test_devanagari_alone_does_not_imply_telugu():
    result = classify("ओपन यूटूब और सर्च तेलिवो मोवीज तो")
    assert result["language"] == "en"
    assert "telugu_script_supporting" not in result["signals"]


def test_text_values_are_preserved():
    raw = "YouTube open chesi search cheyyi"
    normalized = "youtube open chesi search cheyyi"
    result = classify(raw, normalized_text=normalized)
    assert result["raw_text"] == raw
    assert result["normalized_text"] == normalized


def test_classifier_has_no_tool_arguments():
    result = classify("notepad open cheyyi")
    assert "arguments" not in result
    assert "tool" not in result