# Known affected devices

Devices whose SmartStart QR code label is malformed and rejected by
Z-Wave JS / Home Assistant. Not every unit of a model is necessarily
affected; it can depend on the production batch.

| Manufacturer | Model | Art. no. / EAN | Symptom | Status |
|---|---|---|---|---|
| Heatit | Z-TRM6 | Art. no. 54 305 68<br>EAN 7071236018087 | QR string ends in `…1010.9999999999999` (float artifact in the application version of the ProductId TLV); `ZW1406` | ✅ Confirmed by manufacturer, repaired by `zwave-qr-fix` |

**Status legend**

- ✅ **Confirmed by manufacturer**: the manufacturer acknowledged the defect.
- ☑️ **Confirmed**: reproduced by more than one user.
- ❔ **Reported**: a single report so far.

## Add your device

Open an issue with the
[**Affected device**](https://github.com/AMThie/zwave-qr-fix/issues/new?template=affected_device.yml)
template, or send a pull request that adds a row to the table.

**Do not include your DSK or the full QR string.** The manufacturer,
model, article number/EAN and the shape of the defect are all we need.
