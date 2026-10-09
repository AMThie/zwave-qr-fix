"""Builders for synthetic SmartStart strings. No real device data."""

from __future__ import annotations

from zwave_qr_fix import SmartStartCode

SYNTHETIC_DSK = "12345" * 8
PRODUCT_TYPE_TLV = "0010" + "0205404608"
PRODUCT_ID_TLV = "0220" + "00411000481228901010"


def build(
    *,
    version: int = 1,
    keys: int = 3,
    dsk: str = SYNTHETIC_DSK,
    tlvs: str = PRODUCT_TYPE_TLV + PRODUCT_ID_TLV,
) -> str:
    """Return a SmartStart string with a correct checksum."""
    body = f"{keys:03d}{dsk}{tlvs}"
    return f"90{version:02d}{SmartStartCode.compute_checksum(body)}{body}"
