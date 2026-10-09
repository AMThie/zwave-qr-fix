"""Command-line interface for zwave-qr-fix."""

from __future__ import annotations

import argparse
import re
import sys

from ._version import __version__
from .core import LEAD_IN, QRError, parse


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
    ap = argparse.ArgumentParser(
        prog="zwave-qr-fix", description="Repair malformed Z-Wave SmartStart QR codes."
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
