"""Tests for the command-line interface: exit codes and output handling."""

from __future__ import annotations

import io

import pytest

from zwave_qr_fix import main

from .test_regression import VALID


def test_non_utf8_stdout_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    # Redirected output on Windows uses the ANSI code page, e.g. cp1252,
    # which cannot encode the ✓/✗/• markers.
    raw = io.BytesIO()
    stdout = io.TextIOWrapper(raw, encoding="cp1252", newline="\n")
    monkeypatch.setattr("sys.stdout", stdout)
    assert main([VALID]) == 0
    stdout.flush()
    assert raw.getvalue().decode("cp1252").endswith("? Code is already valid\n")
