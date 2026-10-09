"""Golden-output regression tests for the Heatit Z-TRM6 defect.

The expected values below were captured from the original single-file
implementation (commit 07168d5) and must never change unintentionally:
the repaired code, the notes and the CLI output are part of the contract.

All data is synthetic. The DSK is made up and belongs to no real device.
"""

from __future__ import annotations

import pytest

from zwave_qr_fix import main, parse

DSK = "12345-23456-34567-45678-56789-65535-10101-20202"

# A valid synthetic code with Heatit-like ProductType/ProductId TLVs
VALID = "900157552003123452345634567456785678965535101012020200100205404608022000411000481228901010"

# Defect A: last digit of the application version replaced by a float tail
DEFECT_A = (
    "90015755200312345234563456745678567896553510101202020010020540460802200041100048122890101"
    ".9999999999999"
)
FIXED_A = "900149142003123452345634567456785678965535101012020200100205404608022000411000481228900101"

# Defect B: same shape as the real label tail "...122891010.9999999999999"
DEFECT_B = (
    "90015755200312345234563456745678567896553510101202020010020540460802200041100048122891010"
    ".9999999999999"
)

DESCRIBE_HEAD = [
    "Version:          1 (SmartStart)",
    "Security classes: S2 Unauthenticated, S2 Authenticated",
    "DSK:              12345-23456-34567-45678-56789-65535-10101-20202",
    "PIN:              12345",
    "ProductType:      generic 0x08, specific 0x06, icon 0x1200",
]

REPAIR_NOTES = [
    "Removed garbage starting at position 89: '.9999999999999'",
    "ProductId truncated (19/20 digits) – rebuilding application version",
]

DESCRIBE_A = (
    "Version:          1 (SmartStart)\n"
    "Security classes: S2 Unauthenticated, S2 Authenticated\n"
    "DSK:              12345-23456-34567-45678-56789-65535-10101-20202\n"
    "PIN:              12345\n"
    "ProductType:      generic 0x08, specific 0x06, icon 0x1200\n"
    "ProductId:        manufacturer 0x019B, type 0x0030, id 0x3001, app version 0.101\n"
)
REPAIR_OUTPUT_A = (
    f"Input:  {DEFECT_A}\n"
    "\n"
    "• Removed garbage starting at position 89: '.9999999999999'\n"
    "• ProductId truncated (19/20 digits) – rebuilding application version\n"
    "• Checksum recomputed: 57552 -> 49142\n"
    "\n" + DESCRIBE_A + "\n"
)


def test_parse_repair_defect_a() -> None:
    code, notes = parse(DEFECT_A, repair=True)
    assert code.encode() == FIXED_A
    assert notes == [*REPAIR_NOTES, "Checksum recomputed: 57552 -> 49142"]
    assert code.describe() == [
        *DESCRIBE_HEAD,
        "ProductId:        manufacturer 0x019B, type 0x0030, id 0x3001, app version 0.101",
    ]


def test_parse_repair_defect_b_restores_original() -> None:
    code, notes = parse(DEFECT_B, repair=True)
    assert code.encode() == VALID
    assert notes == REPAIR_NOTES
    assert code.describe() == [
        *DESCRIBE_HEAD,
        "ProductId:        manufacturer 0x019B, type 0x0030, id 0x3001, app version 3.242",
    ]


@pytest.mark.parametrize(
    ("argv", "rc", "expected"),
    [
        pytest.param([DEFECT_A], 0, REPAIR_OUTPUT_A + f"Fixed:  {FIXED_A}\n", id="repair"),
        pytest.param(
            [DEFECT_A, "--check"],
            1,
            f"Input:  {DEFECT_A}\n\n✗ Invalid: invalid character '.' at position 89\n",
            id="check",
        ),
        pytest.param(
            [DEFECT_A, "--dsk", DSK],
            0,
            REPAIR_OUTPUT_A + f"✓ DSK matches the printed label\nFixed:  {FIXED_A}\n",
            id="dsk-match",
        ),
        pytest.param(
            [DEFECT_A, "--dsk", "12345-12345-12345-12345-12345-12345-12345-12345"],
            2,
            REPAIR_OUTPUT_A
            + "✗ DSK in QR code does NOT match the printed DSK – do not use this code!\n",
            id="dsk-mismatch",
        ),
        pytest.param(
            [VALID],
            0,
            f"Input:  {VALID}\n"
            "\n\n" + "\n".join(DESCRIBE_HEAD) + "\n"
            "ProductId:        manufacturer 0x019B, type 0x0030, id 0x3001, app version 3.242\n"
            "\n✓ Code is already valid\n",
            id="already-valid",
        ),
        pytest.param(
            [DEFECT_B, "--app-version", "1.1"],
            0,
            f"Input:  {DEFECT_B}\n"
            "\n"
            "• Removed garbage starting at position 89: '.9999999999999'\n"
            "• ProductId truncated (19/20 digits) – rebuilding application version\n"
            "• Application version set to 1.1\n"
            "\n" + "\n".join(DESCRIBE_HEAD) + "\n"
            "ProductId:        manufacturer 0x019B, type 0x0030, id 0x3001, app version 1.1\n"
            "\n"
            "Fixed:  900156554003123452345634567456785678965535101012020200100205404608022000411000481228900257\n",
            id="app-version",
        ),
    ],
)
def test_cli_golden_output(
    argv: list[str], rc: int, expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == rc
    assert capsys.readouterr().out == expected
