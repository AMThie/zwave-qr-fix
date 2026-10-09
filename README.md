# zwave-qr-fix

[![CI](https://github.com/AMThie/zwave-qr-fix/actions/workflows/ci.yml/badge.svg)](https://github.com/AMThie/zwave-qr-fix/actions/workflows/ci.yml)
[![Python 3.9–3.13](https://img.shields.io/badge/python-3.9%E2%80%933.13-blue)](https://github.com/AMThie/zwave-qr-fix/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/github/license/AMThie/zwave-qr-fix)](https://github.com/AMThie/zwave-qr-fix/blob/main/LICENSE)
<!-- After the first PyPI release:
[![PyPI](https://img.shields.io/pypi/v/zwave-qr-fix)](https://pypi.org/project/zwave-qr-fix/)
-->

Repair malformed **Z-Wave SmartStart QR codes** that Z-Wave JS / Home Assistant rejects with

```
Invalid QR code: contains invalid characters (ZW1406)
```

Known case: **Heatit Z-TRM6** thermostats whose QR code ends in `…1010.9999999999999`.
See [DEVICES.md](https://github.com/AMThie/zwave-qr-fix/blob/main/DEVICES.md) for all known affected devices.

## Quickstart

You came from the Home Assistant forum and your device won't pair? Here's the fix:

1. **Install** with [pipx](https://pipx.pypa.io/) (keeps the tool isolated from your system Python):

   ```bash
   pipx install "zwave-qr-fix[all] @ git+https://github.com/AMThie/zwave-qr-fix.git"
   ```

2. **Repair the code.** Take a photo of the QR label (jpg, png or iPhone heic) and run the
   tool with the DSK printed on the label as a safety check:

   ```bash
   zwave-qr-fix --image label.heic --dsk 12345-23456-34567-45678-56789-65535-10101-20202 -o fixed.png
   ```

3. **Include the device.** Scan `fixed.png` in the Home Assistant Companion app
   (*Settings → Devices & services → Z-Wave → Add device*), or paste the printed
   `Fixed:` string into the provisioning dialog of Z-Wave JS UI.

No QR code at hand? You can also [skip SmartStart](#do-i-even-need-smartstart).

## Example

All values below are synthetic. Never post your real DSK (see [Privacy](#privacy)).

```console
$ zwave-qr-fix "90015755200312345234563456745678567896553510101202020010020540460802200041100048122891010.9999999999999" \
    --dsk 12345-23456-34567-45678-56789-65535-10101-20202
Input:  90015755200312345234563456745678567896553510101202020010020540460802200041100048122891010.9999999999999

• Removed garbage starting at position 89: '.9999999999999'
• ProductId truncated (19/20 digits) – rebuilding application version

Version:          1 (SmartStart)
Security classes: S2 Unauthenticated, S2 Authenticated
DSK:              12345-23456-34567-45678-56789-65535-10101-20202
PIN:              12345
ProductType:      generic 0x08, specific 0x06, icon 0x1200
ProductId:        manufacturer 0x019B, type 0x0030, id 0x3001, app version 3.242

✓ DSK matches the printed label
Fixed:  900157552003123452345634567456785678965535101012020200100205404608022000411000481228901010
```

## Installation

```bash
# core only: repair strings you pass on the command line
pipx install "git+https://github.com/AMThie/zwave-qr-fix.git"

# with image input (--image) and PNG output (-o)
pipx install "zwave-qr-fix[all] @ git+https://github.com/AMThie/zwave-qr-fix.git"
```

Plain `pip install` works the same way. The core has **no dependencies** and runs on
Python 3.9 or newer. The extras are optional:

| Extra | Adds | Packages |
|---|---|---|
| `image` | `--image`: read the QR code from a photo | zxing-cpp, Pillow, pillow-heif |
| `png` | `-o`: write the repaired QR code as PNG | qrcode |
| `all` | both | |

## Usage

```bash
zwave-qr-fix CODE [options]          # repair a string read from the QR code
zwave-qr-fix --image PHOTO [options] # read it from a photo of the label
python -m zwave_qr_fix …             # same, without the console script
```

| Option | Meaning |
|---|---|
| `--dsk DSK` | DSK printed on the label. The tool aborts if the QR code's DSK differs. **Always use it.** |
| `-o FILE`, `--png FILE` | Write the repaired QR code to a PNG file. |
| `--check` | Only validate, don't repair. |
| `--app-version X.Y` | Override the application version in the ProductId TLV. |
| `--version` | Show the version. |

| Exit code | Meaning |
|---|---|
| `0` | Valid or repaired |
| `1` | Invalid and not repairable (or `--check` found a problem) |
| `2` | DSK mismatch, or invalid command-line arguments |

## How it works

A SmartStart QR code is a string of digits:

| Field | Digits | Notes |
|---|---|---|
| Lead-in | 2 | always `90` |
| Version | 2 | `00` = S2 only, `01` = SmartStart |
| Checksum | 5 | first 2 bytes of SHA-1 over everything after this field |
| Requested keys | 3 | bitmask of security classes |
| DSK | 40 | 8 blocks of 5 digits (block 1 = PIN) |
| TLVs | … | `type·2+critical` (2) + length (2) + value |

**The Heatit defect:** when the label was generated, the application version in the
ProductId TLV was apparently written as a floating-point number. The string therefore
ends in `…1010.9999999999999`: it contains a non-digit character, the ProductId TLV is
one digit short, and the checksum may no longer match.

**The repair:**

1. Cut everything from the first non-digit character.
2. Rebuild truncated ProductType/ProductId TLVs (or set the application version
   explicitly with `--app-version`).
3. Recompute the checksum.
4. **Leave the DSK untouched.** It is the only field the controller needs to identify and
   securely include the device, and it is correct on the label.

Every change is listed in the output (`•` lines). The test suite checks the output
against the reference parser of Z-Wave JS (`parseQRCodeString` from `@zwave-js/core`).

## FAQ

### Do I even need SmartStart?

No. SmartStart is a convenience. Classic **S2 inclusion with the PIN** works just as well
and doesn't need a QR code: start inclusion in Home Assistant / Z-Wave JS UI, put the
device into inclusion mode, and enter the **PIN** (the first 5 digits of the DSK
printed on the label) when asked.

### Is the repaired code safe to use?

The tool never changes the DSK, and with `--dsk` it verifies that the DSK in the QR
code matches the one printed on the label. If they differ, it refuses to output a code.

### Which devices are affected?

See [DEVICES.md](https://github.com/AMThie/zwave-qr-fix/blob/main/DEVICES.md). If you found another one, please
[report it](https://github.com/AMThie/zwave-qr-fix/issues/new?template=affected_device.yml),
and please report it to the manufacturer as well.

## Privacy

The DSK is part of S2 security. **Do not post the full codes or DSKs of your devices**
in issues or forums. Use placeholders such as `12345-12345-…` instead. The tool runs
entirely offline. See [SECURITY.md](https://github.com/AMThie/zwave-qr-fix/blob/main/SECURITY.md).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](https://github.com/AMThie/zwave-qr-fix/blob/main/CONTRIBUTING.md) and the
[changelog](https://github.com/AMThie/zwave-qr-fix/blob/main/CHANGELOG.md).

## Disclaimer

Unofficial tool, not affiliated with Heatit or the Z-Wave Alliance. Use at your
own risk. Please also report affected devices to the manufacturer.

## License

[MIT](https://github.com/AMThie/zwave-qr-fix/blob/main/LICENSE)
