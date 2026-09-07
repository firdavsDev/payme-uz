from payme.redaction import mask, redact


def test_short_secrets_vanish_entirely():
    assert mask("abc") == "***"


def test_long_secrets_keep_a_correlatable_prefix():
    assert mask("6a9f0044" + "s" * 100) == "6a9f0044...(108 chars)"


def test_card_fields_are_masked_at_any_depth():
    payload = {"result": {"card": {"number": "8600069195406311", "expire": "1027"}}}
    redacted = redact(payload)
    assert redacted["result"]["card"]["number"] == "86000691...(16 chars)"
    assert redacted["result"]["card"]["expire"] == "***"


def test_the_original_payload_is_untouched():
    payload = {"token": "t" * 50}
    redact(payload)
    assert payload["token"] == "t" * 50


def test_lists_and_scalars_survive():
    assert redact({"items": [{"token": "t" * 20}, 5]}) == {
        "items": [{"token": "tttttttt...(20 chars)"}, 5]
    }
