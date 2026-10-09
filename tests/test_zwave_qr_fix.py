import pytest
from zwave_qr_fix import parse, QRError, SmartStartCode

# Synthetic Heatit-style example (random DSK, not a real device)
def _make():
    body = "003" + "12345" * 8 + "0010" + "0205404608" + "0220" + "00411000481228901010"
    return "9001" + SmartStartCode.compute_checksum(body) + body

def test_valid_roundtrip():
    s = _make()
    code, notes = parse(s)
    assert code.encode() == s and not notes

def test_float_artifact_is_repaired():
    s = _make()[:-1] + ".9999999999999"   # same defect as Heatit labels
    with pytest.raises(QRError):
        parse(s)
    code, notes = parse(s, repair=True)
    fixed = code.encode()
    assert fixed.isdigit() and len(fixed) == 90
    assert code.dsk == "12345" * 8
    parse(fixed)  # must validate cleanly

def test_checksum_mismatch_detected():
    s = _make()
    bad = s[:4] + "00000" + s[9:]
    with pytest.raises(QRError):
        parse(bad)

def test_app_version_override():
    code, _ = parse(_make(), app_version="1.0")
    assert code.tlvs[1].value.endswith("00256")
