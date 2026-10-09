# zwave-qr-fix

Repair malformed **Z-Wave SmartStart QR codes** that Z-Wave JS / Home Assistant rejects with

```
Invalid QR code: contains invalid characters (ZW1406)
```

## Background

Some devices ship with a SmartStart label whose QR code is not spec-compliant.
Known case: **Heatit Z-TRM6** (Art. no. 54 305 68, EAN 7071236018087). The QR code ends in

```
...122891010.9999999999999
```

The application-version field was apparently written as a floating-point number
when the label was generated. As a result, the code contains a non-digit character,
the ProductId TLV is one digit short, and the checksum no longer matches.

The **DSK on the label is correct**, and the DSK is all the controller needs to
identify and securely include the device. This tool keeps the DSK untouched,
rebuilds the broken fields and recomputes the checksum.

## How it works

A SmartStart string is digits only:

| Field | Digits | Notes |
|---|---|---|
| Lead-in | 2 | always `90` |
| Version | 2 | `00` = S2 only, `01` = SmartStart |
| Checksum | 5 | first 2 bytes of SHA-1 over everything after this field |
| Requested keys | 3 | bitmask of security classes |
| DSK | 40 | 8 blocks of 5 digits (block 1 = PIN) |
| TLVs | … | `type·2+critical` (2) + length (2) + value |

The tool removes anything after the first non-digit character, repairs truncated
ProductType/ProductId TLVs (or overrides the app version with `--app-version`),
and recomputes the checksum.

## Installation

```bash
pipx install "git+https://github.com/AMThie/zwave-qr-fix.git"
# with image input and PNG output:
pipx install "zwave-qr-fix[all] @ git+https://github.com/AMThie/zwave-qr-fix.git"
```

The core logic has no dependencies and runs on Python 3.9+.

## Usage

```bash
# Repair a string and cross-check it against the DSK printed on the label
zwave-qr-fix "9001...1010.9999999999999" --dsk 12345-12345-...

# Read straight from a photo of the label (jpg/png/heic) and write a PNG
zwave-qr-fix --image label.heic -o fixed.png

# Only validate, don't repair
zwave-qr-fix --check "9001..."
```

Then scan `fixed.png` in the Home Assistant Companion app
(*Settings → Devices & services → Z-Wave → Add device*), or paste the string into
the provisioning dialog of Z-Wave JS UI.

**Always use `--dsk`** to compare against the DSK printed on the label. If the
QR code's DSK does not match the label, the tool aborts.

## Fallback without SmartStart

Use classic S2 inclusion and enter the **PIN**, which is the first 5 digits of
the DSK, when prompted. You don't need a QR code for that.

## Privacy

The DSK is part of S2 security. **Do not post the full codes or DSKs of your
devices** in issues or forums. Use placeholders such as `12345-12345-…` instead.

## Disclaimer

Unofficial tool, not affiliated with Heatit or the Z-Wave Alliance. Use at your
own risk. Please also report affected devices to the manufacturer.

## License

MIT
