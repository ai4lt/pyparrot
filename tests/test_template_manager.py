"""Tests for template manager pipeline templates."""

import pytest
import tempfile
from pathlib import Path

from pyparrot.template_manager import TemplateManager


def _services_for(pipeline_type: str):
    tm = TemplateManager()
    return tm.generate_compose_file(pipeline_type).get("services", {})


def test_end2end_pipeline_services_subset():
    """End2end should include middleware stack and ASR."""
    services = _services_for("end2end")
    expected = {"frontend", "streamingasr", "qbmediator"}
    missing = expected - services.keys()
    assert not missing, f"Missing services: {missing}"


def test_cascaded_pipeline_services_subset():
    """Cascaded should add MT on top of middleware+ASR."""
    services = _services_for("cascaded")
    expected = {"frontend", "streamingasr", "streamingmt"}
    missing = expected - services.keys()
    assert not missing, f"Missing services: {missing}"


def test_boom_pipeline_services_subset():
    """BOOM shares the middleware+ASR stack."""
    services = _services_for("BOOM")
    expected = {"frontend", "streamingasr", "qbmediator"}
    missing = expected - services.keys()
    assert not missing, f"Missing services: {missing}"


def test_dialog_pipeline_includes_dialog_services():
    """Dialog pipeline should pull dialog and TTS services."""
    services = _services_for("dialog")
    expected = {"bot", "kitmeetingbutler", "streamingtts"}
    missing = expected - services.keys()
    assert not missing, f"Missing services: {missing}"


def test_lt2025_pipeline_includes_markup_and_dialog_services():
    """LT.2025 pipeline should include markup and dialog stack."""
    services = _services_for("LT.2025")
    expected = {
        "streamingasr",
        "streamingmt",
        "streamingtts",
        "streamingtextstructurer",
        "streamingsummarizer",
        "streamingpostproduction",
        "bot",
        "kitmeetingbutler",
    }
    missing = expected - services.keys()
    assert not missing, f"Missing services: {missing}"


def test_unknown_pipeline_type_raises_value_error():
    tm = TemplateManager()
    with pytest.raises(ValueError):
        tm.generate_compose_file("does-not-exist")


def test_env_file_includes_hf_token():
    tm = TemplateManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        tm.generate_env_file(str(out_dir), pipeline_name="p", domain="d", http_port=1,
                             frontend_theme="t", hf_token="secret", repo_root=None)
        content = (out_dir / ".env").read_text()
        assert "HF_TOKEN=secret" in content
