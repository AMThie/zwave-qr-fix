"""
zwave-qr-fix – Repair malformed Z-Wave SmartStart QR code strings.

Some Z-Wave devices ship with a SmartStart label whose QR code is not
spec-compliant, e.g. Heatit Z-TRM6 units whose code ends in
"...1010.9999999999999" (a float artifact in the application-version field).
Z-Wave JS rejects those with "Invalid QR code ... (ZW1406)".

This tool parses the string, repairs truncated/garbled TLVs, recomputes the
SHA-1 checksum and prints (and optionally renders) a valid QR code.

The DSK is never changed – it is the only field the controller needs to
securely identify and include the device.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field

LEAD_IN = "90"
HEADER_LEN = 2 + 2 + 5 + 3 + 40  # lead-in, version, checksum, keys, DSK = 52

TLV_NAMES = {
    0: "ProductType",
    1: "ProductId",
    2: "MaxInclusionRequestInterval",
    3: "UUID16",
    4: "SupportedProtocols",
    50: "Name",
    51: "Location",
    52: "SmartStartInclusionSetting",
    53: "AdvancedJoining",
    54: "BootstrappingMode",
    55: "NetworkStatus",
}
# Expected value lengths (digits) for TLVs with a fixed size
TLV_FIXED_LEN = {0: 10, 1: 20}

SECURITY_CLASSES = {
    0: "S2 Unauthenticated",
    1: "S2 Authenticated",
    2: "S2 Access Control",
    6: "S0 Legacy",
}


class QRError(ValueError):
    pass


@dataclass
class TLV:
    type: int
    critical: bool
    value: str

    def encode(self) -> str:
        return f"{(self.type << 1) | int(self.critical):02d}{len(self.value):02d}{self.value}"


@dataclass
class SmartStartCode:
    version: int
    checksum: str
    keys: int
    dsk: str  # 40 digits
    tlvs: list[TLV] = field(default_factory=list)

    # ---------- encoding ----------
    def body(self) -> str:
        return f"{self.keys:03d}{self.dsk}" + "".join(t.encode() for t in self.tlvs)

    @staticmethod
    def compute_checksum(body: str) -> str:
        digest = hashlib.sha1(body.encode("ascii")).digest()
        return f"{int.from_bytes(digest[:2], 'big'):05d}"

    def encode(self) -> str:
        body = self.body()
        return f"{LEAD_IN}{self.version:02d}{self.compute_checksum(body)}{body}"

    def checksum_ok(self) -> bool:
        return self.checksum == self.compute_checksum(self.body())

    # ---------- pretty ----------
    @property
    def dsk_formatted(self) -> str:
        return "-".join(self.dsk[i:i + 5] for i in range(0, 40, 5))

    @property
    def pin(self) -> str:
        return self.dsk[:5]

    def describe(self) -> list[str]:
        lines = [
            f"Version:          {self.version} ({'SmartStart' if self.version == 1 else 'S2 only'})",
            f"Security classes: {', '.join(SECURITY_CLASSES.get(b, f'bit {b}') for b in range(8) if self.keys >> b & 1)}",
            f"DSK:              {self.dsk_formatted}",
            f"PIN:              {self.pin}",
        ]
        for t in self.tlvs:
            name = TLV_NAMES.get(t.type, f"TLV {t.type}")
            v = t.value
            if t.type == 0 and len(v) == 10:
                dc, icon = int(v[:5]), int(v[5:])
                lines.append(f"{name}:      generic 0x{dc >> 8:02X}, specific 0x{dc & 0xFF:02X}, icon 0x{icon:04X}")
            elif t.type == 1 and len(v) == 20:
                m, pt, pid, av = (int(v[i:i + 5]) for i in range(0, 20, 5))
                lines.append(f"{name}:        manufacturer 0x{m:04X}, type 0x{pt:04X}, id 0x{pid:04X}, "
                             f"app version {av >> 8}.{av & 0xFF}")
            else:
                lines.append(f"{name}: {v}")
        return lines


# ---------- parsing ----------
def parse(raw: str, repair: bool = False, app_version: str | None = None) -> tuple[SmartStartCode, list[str]]:
    """Parse a SmartStart string. With repair=True, fix known defects instead of failing."""
    notes: list[str] = []
    s = raw.strip()

    bad = re.search(r"\D", s)
    if bad:
        if not repair:
            raise QRError(f"invalid character {bad.group()!r} at position {bad.start()}")
        notes.append(f"Removed garbage starting at position {bad.start()}: {s[bad.start():]!r}")
        s = s[:bad.start()]

    if len(s) < HEADER_LEN:
        raise QRError(f"too short ({len(s)} digits, need at least {HEADER_LEN})")
    if not s.startswith(LEAD_IN):
        raise QRError("does not start with lead-in '90' – not a Z-Wave QR code")

    version = int(s[2:4])
    if version not in (0, 1):
        raise QRError(f"unknown QR version {version}")
    checksum = s[4:9]
    keys = int(s[9:12])
    dsk = s[12:52]
    for i in range(0, 40, 5):
        if int(dsk[i:i + 5]) > 65535:
            raise QRError(f"DSK block {i // 5 + 1} out of range: {dsk[i:i + 5]}")

    tlvs: list[TLV] = []
    rest = s[52:]
    while rest:
        if len(rest) < 4:
            if not repair:
                raise QRError(f"trailing data too short for a TLV: {rest!r}")
            notes.append(f"Dropped incomplete TLV header {rest!r}")
            break
        type_byte, length, rest = int(rest[:2]), int(rest[2:4]), rest[4:]
        t_type, critical = type_byte >> 1, bool(type_byte & 1)
        value, rest = rest[:length], rest[length:]
        name = TLV_NAMES.get(t_type, f"TLV {t_type}")
        if len(value) < length:
            if not repair:
                raise QRError(f"{name} truncated: expected {length} digits, got {len(value)}")
            if t_type == 1:
                notes.append(f"{name} truncated ({len(value)}/{length} digits) – rebuilding application version")
                value = value.ljust(15, "0")[:15] + value[15:].zfill(5)
            elif t_type in TLV_FIXED_LEN:
                notes.append(f"{name} truncated – zero-padding")
                value = value.zfill(length)
            else:
                notes.append(f"Dropped truncated {name}")
                continue
        tlvs.append(TLV(t_type, critical, value))

    code = SmartStartCode(version, checksum, keys, dsk, tlvs)

    if not code.checksum_ok():
        if not repair:
            raise QRError(f"checksum mismatch (label: {checksum}, computed: {code.compute_checksum(code.body())})")
        notes.append(f"Checksum recomputed: {checksum} -> {code.compute_checksum(code.body())}")

    if app_version is not None:
        major, _, minor = app_version.partition(".")
        av = (int(major) << 8) | int(minor or 0)
        for t in code.tlvs:
            if t.type == 1:
                t.value = t.value[:15] + f"{av:05d}"
                notes.append(f"Application version set to {major}.{minor or 0}")

    return code, notes


# ---------- optional helpers ----------
def read_from_image(path: str) -> str:
    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        sys.exit("Image input needs: pip install zxing-cpp pillow (and pillow-heif for .heic)")
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    for r in zxingcpp.read_barcodes(Image.open(path)):
        if r.text.startswith(LEAD_IN):
            return r.text
    sys.exit(f"No Z-Wave QR code found in {path}")


def write_png(data: str, path: str) -> None:
    try:
        import qrcode
    except ImportError:
        sys.exit("PNG output needs: pip install qrcode[pil]")
    qrcode.make(data, box_size=12, border=4).save(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Repair malformed Z-Wave SmartStart QR codes.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("code", nargs="?", help="SmartStart string as read from the QR code")
    src.add_argument("-i", "--image", help="photo of the label (jpg/png/heic)")
    ap.add_argument("--dsk", help="DSK printed on the label, to cross-check (e.g. 12345-12345-...)")
    ap.add_argument("--app-version", help="application version to encode, e.g. 1.0")
    ap.add_argument("-o", "--png", help="write the repaired QR code to this PNG file")
    ap.add_argument("--check", action="store_true", help="only validate, don't repair")
    args = ap.parse_args(argv)

    raw = read_from_image(args.image) if args.image else args.code
    print(f"Input:  {raw}\n")

    try:
        code, notes = parse(raw, repair=not args.check, app_version=args.app_version)
    except QRError as e:
        print(f"✗ Invalid: {e}")
        return 1

    for n in notes:
        print(f"• {n}")
    print("\n" + "\n".join(code.describe()) + "\n")

    if args.dsk:
        printed = re.sub(r"\D", "", args.dsk)
        if printed != code.dsk:
            print("✗ DSK in QR code does NOT match the printed DSK – do not use this code!")
            return 2
        print("✓ DSK matches the printed label")

    fixed = code.encode()
    if fixed == raw.strip():
        print("✓ Code is already valid")
    else:
        print(f"Fixed:  {fixed}")
    if args.png:
        write_png(fixed, args.png)
        print(f"PNG written to {args.png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
