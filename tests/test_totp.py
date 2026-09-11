from __future__ import annotations

import base64

from apps.accounts import totp

# RFC 6238 Appendix B, SHA-1 column. The shared secret is the ASCII string
# "12345678901234567890"; the published vectors are 8 digits, so the 6-digit
# expectation is the same value truncated to its last six characters.
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()
RFC_VECTORS: list[tuple[int, str]] = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


def test_matches_the_rfc_6238_published_vectors() -> None:
    for moment, expected in RFC_VECTORS:
        counter = totp.counter_at(moment)
        assert totp.code_for(RFC_SECRET, counter, digits=8) == expected
        assert totp.code_for(RFC_SECRET, counter) == expected[-6:]


def test_verify_accepts_the_current_code_and_reports_its_counter() -> None:
    moment = 1111111109
    code = totp.code_for(RFC_SECRET, totp.counter_at(moment))

    assert totp.verify(RFC_SECRET, code, at=moment) == totp.counter_at(moment)


def test_verify_tolerates_one_step_of_clock_drift_but_not_two() -> None:
    moment = 1111111109
    counter = totp.counter_at(moment)

    assert totp.verify(RFC_SECRET, totp.code_for(RFC_SECRET, counter - 1), at=moment) is not None
    assert totp.verify(RFC_SECRET, totp.code_for(RFC_SECRET, counter + 1), at=moment) is not None
    assert totp.verify(RFC_SECRET, totp.code_for(RFC_SECRET, counter - 2), at=moment) is None


def test_verify_rejects_malformed_input() -> None:
    assert totp.verify(RFC_SECRET, "", at=59) is None
    assert totp.verify(RFC_SECRET, "12345", at=59) is None
    assert totp.verify(RFC_SECRET, "not-a-code", at=59) is None


def test_generated_secrets_are_usable_base32_and_never_repeat() -> None:
    secrets_seen = {totp.generate_secret() for _ in range(50)}

    assert len(secrets_seen) == 50
    for secret in secrets_seen:
        assert len(totp.code_for(secret, 1)) == totp.DIGITS


def test_provisioning_uri_carries_the_issuer_and_account() -> None:
    uri = totp.provisioning_uri("ABCDEFGH", account="pessoa@example.test", issuer="HubContador")

    assert uri.startswith("otpauth://totp/HubContador%3Apessoa%40example.test?")
    assert "secret=ABCDEFGH" in uri
    assert "issuer=HubContador" in uri
