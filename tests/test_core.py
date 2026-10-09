"""Tests for parsing, repair and encoding (zwave_qr_fix.core)."""

from __future__ import annotations

import pytest

from zwave_qr_fix import TLV, QRError, SmartStartCode, parse

from .helpers import PRODUCT_ID_TLV, PRODUCT_TYPE_TLV, SYNTHETIC_DSK, build

# ---------- checksum ----------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        # Well-known SHA-1 test vectors (FIPS 180): da39a3ee… and a9993e36…
        pytest.param("", "55865", id="empty"),
        pytest.param("abc", "43417", id="abc"),
        # Checksums below 10000 keep their leading zero
        pytest.param("005" + SYNTHETIC_DSK, "02176", id="leading-zero"),
    ],
)
def test_compute_checksum(body: str, expected: str) -> None:
    assert SmartStartCode.compute_checksum(body) == expected


def test_checksum_covers_everything_after_checksum_field() -> None:
    s = build()
    assert s[4:9] == SmartStartCode.compute_checksum(s[9:])


def test_checksum_mismatch_detected() -> None:
    s = build()
    bad = s[:4] + "00000" + s[9:]
    with pytest.raises(QRError, match=r"checksum mismatch \(label: 00000, computed: \d{5}\)"):
        parse(bad)


def test_checksum_mismatch_repaired() -> None:
    s = build()
    code, notes = parse(s[:4] + "00000" + s[9:], repair=True)
    assert code.encode() == s
    assert notes == [f"Checksum recomputed: 00000 -> {s[4:9]}"]


# ---------- parser: valid input ----------


def test_valid_roundtrip() -> None:
    s = build()
    code, notes = parse(s)
    assert code.encode() == s
    assert code.checksum_ok()
    assert not notes


def test_surrounding_whitespace_is_ignored() -> None:
    s = build()
    code, _ = parse(f"  {s}\n")
    assert code.encode() == s


def test_fields_are_parsed() -> None:
    code, _ = parse(build(keys=7))
    assert code.version == 1
    assert code.keys == 7
    assert code.dsk == SYNTHETIC_DSK
    assert code.pin == "12345"
    assert code.dsk_formatted == "-".join(["12345"] * 8)
    assert code.tlvs == [
        TLV(0, False, "0205404608"),
        TLV(1, False, "00411000481228901010"),
    ]


def test_s2_only_code_without_tlvs() -> None:
    s = build(version=0, keys=1, tlvs="")
    code, _ = parse(s)
    assert code.encode() == s
    assert code.describe()[:2] == [
        "Version:          0 (S2 only)",
        "Security classes: S2 Unauthenticated",
    ]


def test_critical_flag_roundtrip() -> None:
    # Type byte 05 = MaxInclusionRequestInterval (2) with the critical bit set
    s = build(tlvs=PRODUCT_TYPE_TLV + PRODUCT_ID_TLV + "0503" + "123")
    code, _ = parse(s)
    assert code.tlvs[2] == TLV(2, True, "123")
    assert code.encode() == s


def test_minimum_length_code_is_accepted() -> None:
    s = build(tlvs="")
    assert len(s) == 52
    parse(s)


# ---------- describe ----------


def test_describe_unknown_security_bits_and_tlvs() -> None:
    code, _ = parse(build(keys=0b1000, tlvs="1006" + "000042"))
    lines = code.describe()
    assert "Security classes: bit 3" in lines
    assert lines[-1] == "TLV 5: 000042"


def test_describe_unexpected_tlv_length_falls_back_to_raw_value() -> None:
    code, _ = parse(build(tlvs="0004" + "1234"))
    assert code.describe()[-1] == "ProductType: 1234"


# ---------- parser: errors ----------


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        pytest.param("", "too short (0 digits, need at least 52)", id="empty"),
        pytest.param("9001" + "0" * 47, "too short (51 digits, need at least 52)", id="51-digits"),
        pytest.param(
            "91" + build()[2:],
            "does not start with lead-in '90' – not a Z-Wave QR code",
            id="wrong-lead-in",
        ),
        pytest.param("9002" + build()[4:], "unknown QR version 2", id="unknown-version"),
        pytest.param(
            build(dsk="12345" * 2 + "70000" + "12345" * 5),
            "DSK block 3 out of range: 70000",
            id="dsk-block-over-65535",
        ),
        pytest.param(
            build()[:60] + "x" + build()[60:],
            "invalid character 'x' at position 60",
            id="invalid-character",
        ),
    ],
)
def test_parse_errors(raw: str, message: str) -> None:
    with pytest.raises(QRError) as exc:
        parse(raw)
    assert str(exc.value) == message


def test_garbage_inside_header_cannot_be_repaired() -> None:
    with pytest.raises(QRError, match=r"too short \(30 digits"):
        parse(build()[:30] + ".999", repair=True)


def test_dsk_block_out_of_range_is_not_repaired() -> None:
    with pytest.raises(QRError, match="DSK block 8 out of range: 99999"):
        parse(build(dsk="12345" * 7 + "99999"), repair=True)


def test_qrerror_is_a_valueerror() -> None:
    assert issubclass(QRError, ValueError)


# ---------- repair of truncated TLVs ----------


def test_float_artifact_is_repaired() -> None:
    s = build()[:-1] + ".9999999999999"  # same defect as Heatit labels
    with pytest.raises(QRError):
        parse(s)
    code, _ = parse(s, repair=True)
    fixed = code.encode()
    assert fixed.isdigit()
    assert len(fixed) == 90
    assert code.dsk == SYNTHETIC_DSK
    parse(fixed)  # must validate cleanly


def test_truncated_product_id_not_repaired_without_flag() -> None:
    with pytest.raises(QRError, match="ProductId truncated: expected 20 digits, got 19"):
        parse(build()[:-1])


def test_short_product_id_rebuilds_app_version() -> None:
    # Only 13 of 20 digits: manufacturer/type are padded, app version zeroed
    s = build(tlvs=PRODUCT_TYPE_TLV + "0220" + "0041100048122")
    code, notes = parse(s, repair=True)
    assert code.tlvs[1].value == "00411000481220000000"
    assert notes[0] == "ProductId truncated (13/20 digits) – rebuilding application version"


def test_truncated_product_type_is_zero_padded() -> None:
    code, notes = parse(build(tlvs="0010" + "20540460"), repair=True)
    assert code.tlvs[0].value == "0020540460"
    assert notes[0] == "ProductType truncated – zero-padding"


def test_truncated_variable_tlv_is_dropped() -> None:
    s = build(tlvs=PRODUCT_TYPE_TLV + "0610" + "12345")
    with pytest.raises(QRError, match="UUID16 truncated: expected 10 digits, got 5"):
        parse(s)
    code, notes = parse(s, repair=True)
    assert [t.type for t in code.tlvs] == [0]
    assert notes[0] == "Dropped truncated UUID16"


def test_incomplete_tlv_header() -> None:
    s = build() + "02"
    with pytest.raises(QRError, match="trailing data too short for a TLV: '02'"):
        parse(s)
    code, notes = parse(s, repair=True)
    assert len(code.tlvs) == 2
    assert notes[0] == "Dropped incomplete TLV header '02'"


def test_repair_keeps_dsk_unchanged() -> None:
    dsk = "12345" + "00001" + "65535" + "00000" + "54321" + "11111" + "22222" + "33333"
    code, _ = parse(build(dsk=dsk)[:-3] + ".9999999999999", repair=True)
    assert code.dsk == dsk


# ---------- --app-version ----------


@pytest.mark.parametrize(
    ("app_version", "encoded", "note"),
    [
        pytest.param("1.0", "00256", "Application version set to 1.0", id="major.minor"),
        pytest.param("2", "00512", "Application version set to 2.0", id="major-only"),
        pytest.param("3.242", "01010", "Application version set to 3.242", id="heatit"),
    ],
)
def test_app_version_override(app_version: str, encoded: str, note: str) -> None:
    code, notes = parse(build(), app_version=app_version)
    assert code.tlvs[1].value == "004110004812289" + encoded
    assert notes == [note]
    parse(code.encode())


def test_app_version_without_product_id_is_ignored() -> None:
    code, notes = parse(build(tlvs=PRODUCT_TYPE_TLV), app_version="1.0")
    assert notes == []
    assert code.tlvs == [TLV(0, False, "0205404608")]
