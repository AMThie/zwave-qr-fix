"""Generate synthetic test vectors for the cross-check against Z-Wave JS.

Every vector says whether the reference parser (@zwave-js/core) must accept
the input and, if so, which fields it must report. The expectations come
from zwave_qr_fix, so a mismatch means the two parsers disagree.

All codes are synthetic: every DSK starts with the block 12345.

Usage: python crosscheck/generate_vectors.py > vectors.json
"""

from __future__ import annotations

import json
import random
import sys
from typing import Any

from zwave_qr_fix import QRError, SmartStartCode, parse

FLOAT_TAIL = ".9999999999999"  # the Heatit Z-TRM6 label defect
# Valid requested-keys bitmasks: S2 Unauthenticated/Authenticated/Access Control
# (bits 0-2) and S0 (bit 7). Z-Wave JS rejects all other bits.
KEY_MASKS = [0b001, 0b011, 0b111, 0b10000001, 0b10000111]


def fields(code: SmartStartCode) -> dict[str, Any]:
    """The fields Z-Wave JS reports, derived from our parse result."""
    out: dict[str, Any] = {
        "version": code.version,
        "requestedSecurityClasses": [b for b in range(8) if code.keys >> b & 1],
        "dsk": code.dsk_formatted,
    }
    for t in code.tlvs:
        v = t.value
        if t.type == 0:
            dc, icon = int(v[:5]), int(v[5:])
            out.update(
                genericDeviceClass=dc >> 8, specificDeviceClass=dc & 0xFF, installerIconType=icon
            )
        elif t.type == 1:
            m, pt, pid, av = (int(v[i : i + 5]) for i in range(0, 20, 5))
            out.update(
                manufacturerId=m,
                productType=pt,
                productId=pid,
                applicationVersion=f"{av >> 8}.{av & 0xFF}",
            )
        elif t.type == 2:
            out["maxInclusionRequestInterval"] = 128 * int(v)
    return out


def random_code(rng: random.Random) -> str:
    dsk = "12345" + "".join(f"{rng.randrange(65536):05d}" for _ in range(7))
    product_type = f"{rng.randrange(65536):05d}{rng.randrange(65536):05d}"
    product_id = "".join(f"{rng.randrange(65536):05d}" for _ in range(4))
    tlvs = "0010" + product_type
    if rng.random() < 0.3:
        tlvs += "0402" + f"{rng.randrange(5, 100):02d}"  # MaxInclusionRequestInterval
    tlvs += "0220" + product_id  # ProductId last, where the Heatit defect hits
    body = f"{rng.choice(KEY_MASKS):03d}{dsk}{tlvs}"
    version = rng.choice([0, 1])
    return f"90{version:02d}{SmartStartCode.compute_checksum(body)}{body}"


def vector(name: str, raw: str, *, accepted: bool, informational: bool = False) -> dict[str, Any]:
    v: dict[str, Any] = {"name": name, "input": raw, "accepted": accepted}
    if accepted:
        v["fields"] = fields(parse(raw)[0])
    if informational:
        v["informational"] = True
    return v


def main() -> None:
    rng = random.Random(1406)
    vectors = []
    for i in range(40):
        valid = random_code(rng)
        vectors.append(vector(f"valid-{i}", valid, accepted=True))

        defect = valid[:-1] + FLOAT_TAIL
        repaired = parse(defect, repair=True)[0].encode()
        vectors.append(vector(f"repaired-{i}", repaired, accepted=True))
        # Shows the original problem; not a failure if Z-Wave JS learns to cope
        vectors.append(vector(f"defect-{i}", defect, accepted=False, informational=True))

        broken = valid[:4] + f"{(int(valid[4:9]) + 1) % 65536:05d}" + valid[9:]
        vectors.append(vector(f"bad-checksum-{i}", broken, accepted=False))

    for raw in (v["input"] for v in vectors if not v["accepted"] and "informational" not in v):
        try:
            parse(raw)
        except QRError:
            continue
        sys.exit(f"zwave_qr_fix unexpectedly accepts {raw}")

    json.dump(vectors, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
