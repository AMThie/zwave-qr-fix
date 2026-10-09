# Security Policy

## Keep your DSK private

A Z-Wave device's **DSK** (Device Specific Key) is part of its S2 security.
Its first five digits are the **PIN** that authenticates S2 inclusion, and
the full DSK in the SmartStart QR code lets a controller recognise and
include the device. Anyone who knows it could add your device to *their*
controller's provisioning list or interfere with the inclusion.

Therefore:

- **Never post a real DSK, PIN or complete SmartStart string publicly**:
  not in GitHub issues, not in forums, not in screenshots of the label.
- Mask them, e.g. `xxxxx-xxxxx-…` or `9001xxxxx…`. For a bug report, the
  error message and the *shape* of the defect are enough.
- If you already posted one: edit or delete the post. The device itself
  cannot change its DSK, so treat it as known and keep the device in a
  network you control.

`zwave-qr-fix` runs entirely locally. It never sends your codes anywhere.

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please report security problems **privately** through
[GitHub private vulnerability reporting](https://github.com/AMThie/zwave-qr-fix/security/advisories/new),
not in a public issue. Examples:

- the tool changing the DSK or producing a code that belongs to a different device,
- the `--dsk` cross-check passing although the DSKs differ,
- anything that would expose codes beyond the local machine.

The maintainer aims to respond within a week. Once a fix is released, the advisory
is published with credit to the reporter (unless you prefer otherwise).
