"""Tests for the command-line interface: exit codes and output handling."""

from __future__ import annotations

import builtins
import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from zwave_qr_fix import __version__, main

from .helpers import build
from .test_regression import DEFECT_A, DSK, FIXED_A, VALID


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(argv)
    return rc, capsys.readouterr().out


# ---------- exit codes ----------


def test_exit_0_for_valid_code(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([VALID], capsys)
    assert rc == 0
    assert out.endswith("✓ Code is already valid\n")


def test_exit_0_after_repair(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([DEFECT_A], capsys)
    assert rc == 0
    assert f"Fixed:  {FIXED_A}" in out


def test_exit_1_for_invalid_code(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run(["1234"], capsys)
    assert rc == 1
    assert "✗ Invalid: too short" in out


def test_exit_2_for_dsk_mismatch(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([VALID, "--dsk", "12345-" * 7 + "12345"], capsys)
    assert rc == 2
    assert "Fixed:" not in out


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param([], id="no-input"),
        pytest.param([VALID, "--image", "label.png"], id="code-and-image"),
        pytest.param([VALID, "--unknown"], id="unknown-option"),
    ],
)
def test_exit_2_for_usage_errors(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out == f"zwave-qr-fix {__version__}\n"


# ---------- --check ----------


def test_check_accepts_valid_code(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([VALID, "--check"], capsys)
    assert rc == 0
    assert out.endswith("✓ Code is already valid\n")


def test_check_does_not_repair_checksum(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([VALID[:4] + "00000" + VALID[9:], "--check"], capsys)
    assert rc == 1
    assert "✗ Invalid: checksum mismatch" in out


# ---------- --dsk ----------


@pytest.mark.parametrize(
    "printed",
    [
        pytest.param(DSK, id="dashes"),
        pytest.param(DSK.replace("-", " "), id="spaces"),
        pytest.param(DSK.replace("-", ""), id="digits-only"),
    ],
)
def test_dsk_match_accepts_any_separator(printed: str, capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([DEFECT_A, "--dsk", printed], capsys)
    assert rc == 0
    assert "✓ DSK matches the printed label" in out


def test_dsk_partial_input_is_a_mismatch(capsys: pytest.CaptureFixture[str]) -> None:
    rc, _ = run([VALID, "--dsk", "12345-23456"], capsys)
    assert rc == 2


# ---------- --app-version ----------


def test_app_version_changes_output(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = run([VALID, "--app-version", "1.0"], capsys)
    assert rc == 0
    assert "• Application version set to 1.0" in out
    assert "app version 1.0" in out
    assert "Fixed:" in out


# ---------- optional dependencies ----------


def _block_import(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.split(".")[0] in names:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_png_without_qrcode_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _block_import(monkeypatch, "qrcode")
    with pytest.raises(SystemExit) as exc:
        main([VALID, "-o", str(tmp_path / "out.png")])
    assert exc.value.code == "PNG output needs: pip install qrcode[pil]"
    assert not (tmp_path / "out.png").exists()


def test_image_without_zxing_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    _block_import(monkeypatch, "zxingcpp")
    with pytest.raises(SystemExit) as exc:
        main(["--image", "label.png"])
    assert exc.value.code == (
        "Image input needs: pip install zxing-cpp pillow (and pillow-heif for .heic)"
    )


def test_png_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("qrcode")
    pytest.importorskip("zxingcpp")
    png = tmp_path / "fixed.png"
    assert main([DEFECT_A, "-o", str(png)]) == 0
    assert capsys.readouterr().out.endswith(f"PNG written to {png}\n")
    assert main(["--image", str(png)]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"Input:  {FIXED_A}\n")
    assert out.endswith("✓ Code is already valid\n")


def test_image_without_zwave_code(tmp_path: Path) -> None:
    qrcode = pytest.importorskip("qrcode")
    pytest.importorskip("zxingcpp")
    png = tmp_path / "other.png"
    qrcode.make("https://example.com").save(str(png))
    with pytest.raises(SystemExit) as exc:
        main(["--image", str(png)])
    assert exc.value.code == f"No Z-Wave QR code found in {png}"


# ---------- packaging ----------


def test_core_needs_no_third_party_modules() -> None:
    code = (
        "import sys, zwave_qr_fix\n"
        "loaded = {'PIL', 'qrcode', 'zxingcpp', 'pillow_heif'} & set(sys.modules)\n"
        "assert not loaded, loaded\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_python_m_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "zwave_qr_fix", build()],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.endswith("✓ Code is already valid\n")


def test_non_utf8_stdout_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    # Redirected output on Windows uses the ANSI code page, e.g. cp1252,
    # which cannot encode the ✓/✗/• markers.
    raw = io.BytesIO()
    stdout = io.TextIOWrapper(raw, encoding="cp1252", newline="\n")
    monkeypatch.setattr("sys.stdout", stdout)
    assert main([VALID]) == 0
    stdout.flush()
    assert raw.getvalue().decode("cp1252").endswith("? Code is already valid\n")
