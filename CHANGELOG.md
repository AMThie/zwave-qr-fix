# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 10/10/2026

First release.

### Added

- Repair of malformed Z-Wave SmartStart QR code strings: removes trailing
  garbage, rebuilds truncated ProductType/ProductId TLVs and recomputes the
  checksum. The DSK is never changed. Fixes the Heatit Z-TRM6 labels that
  end in `…1010.9999999999999` (`ZW1406` in Z-Wave JS).
- `--dsk` to verify the QR code against the DSK printed on the label.
- `--check` to validate without repairing.
- `--app-version` to set the application version in the ProductId TLV.
- `--image` to read the code from a photo (jpg/png/heic), `-o/--png` to
  write the repaired code as PNG. Both are optional extras
  (`zwave-qr-fix[image]`, `zwave-qr-fix[png]`, `zwave-qr-fix[all]`).
- Installable package with the `zwave-qr-fix` command, `python -m zwave_qr_fix`
  and `--version`; type information (`py.typed`) for the library API.
- List of known affected devices in `DEVICES.md`.

### Fixed

- No more `UnicodeEncodeError` on Windows when the output is redirected to a
  file or pipe.

[Unreleased]: https://github.com/AMThie/zwave-qr-fix/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AMThie/zwave-qr-fix/releases/tag/v0.1.0
