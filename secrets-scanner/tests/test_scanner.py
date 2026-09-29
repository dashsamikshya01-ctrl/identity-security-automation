"""Fixtures are assembled at runtime so this repo never contains a string that looks like a live secret."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner import scan_text  # noqa: E402

FAKE_AWS = "AKIA" + "Z" * 16
FAKE_PEM = "-----BEGIN " + "RSA PRIVATE KEY-----"
FAKE_CS = "Server=db;User Id=app;Pass" + "word=NotARealOne!9;"


def rules(text):
    return {f["rule"] for f in scan_text(text, "x")}


def test_aws_key():
    assert "AWS access key" in rules(f"aws_key = '{FAKE_AWS}'")


def test_pem():
    assert "Private key (PEM)" in rules(FAKE_PEM)


def test_connection_string():
    assert "Connection string with password" in rules(FAKE_CS)


def test_allow_marker_skips_documented_test_values():
    assert rules(f"key='{FAKE_AWS}'  # secrets-scanner:allow") == set()


def test_plain_code_is_clean():
    assert rules("def add(a, b):\n    return a + b") == set()
