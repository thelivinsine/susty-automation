"""
test_access_gating.py — proves the "open tool, paid AI behind sign-in" rule.

The tool is free for everyone on the offline explainer; the paid model is only
reached for approved, signed-in users. The gate is one boolean threaded from the
app down to the explainer (`use_ai` -> `force_offline`). These tests prove that:

  1. With an API key set, `force_offline=True` STILL uses the offline explainer,
     so a visitor can never spend the key.
  2. The whole pipeline honours `use_ai=False` for every explanation it produces.
  3. The approval rules (who may use the AI) behave as documented.

They never make a network call: offline output is asserted by its labels.
"""

import os

import pandas as pd
import pytest

from explain import explain_change, active_backend, NO_REASON
from pipeline import run_pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH = os.path.join(ROOT, "data", "synthetic")


def _is_offline(reason: str) -> bool:
    """Offline reasons are either the grounded 'no reason' sentinel or the clearly
    labelled '[offline mode ...]' extract. A real model answer is neither."""
    return reason == NO_REASON or reason.startswith("[offline mode")


@pytest.fixture()
def fake_key(monkeypatch):
    """Pretend a Claude key is configured, without a real one."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)


def test_active_backend_respects_force_offline(fake_key):
    # Key is set, so unforced the backend is live...
    assert active_backend(force_offline=False)["live"] is True
    # ...but forcing offline overrides that (this is the free tier).
    assert active_backend(force_offline=True)["live"] is False


def test_force_offline_does_not_call_the_model(fake_key):
    # Even with a key set, force_offline must return an offline-labelled reason,
    # which is only possible if no model was called.
    out = explain_change(
        material="Diesel",
        old=1.0,
        new=1.2,
        pct=20.0,
        retrieved_text="DEFRA updated the diesel factor for 2026.",
        context={"breaches_baseline": True},
        force_offline=True,
    )
    assert _is_offline(out["plain_english_reason"])


def test_pipeline_use_ai_false_keeps_every_explanation_offline(fake_key):
    results = run_pipeline(
        os.path.join(SYNTH, "defra_2025.xlsx"),
        os.path.join(SYNTH, "defra_2026.xlsx"),
        os.path.join(SYNTH, "changes_2026.pdf"),
        pd.read_csv(os.path.join(SYNTH, "sample_bom.csv")),
        "2025",
        "2026",
        use_ai=False,
    )
    explained = results["explanations"] + results["relabel_explanations"]
    assert explained, "expected at least one explanation to check"
    for e in explained:
        assert _is_offline(e["plain_english_reason"]), e["plain_english_reason"]


# ---- Approval rules --------------------------------------------------------
def test_approval_blocks_anonymous():
    from auth import approval

    assert approval(None)["allowed"] is False


def test_approval_open_when_no_list(monkeypatch):
    import auth

    monkeypatch.setattr(auth, "_secrets_section", lambda name: {})
    out = auth.approval("anyone@example.com")
    assert out["allowed"] is True
    assert out["reason"] == "open"


def test_approval_honours_email_and_domain_lists(monkeypatch):
    import auth

    monkeypatch.setattr(
        auth,
        "_secrets_section",
        lambda name: {"emails": ["Boss@Example.com"], "domains": ["Client.com"]}
        if name == "access"
        else {},
    )
    assert auth.approval("boss@example.com")["allowed"] is True      # listed email (case-folded)
    assert auth.approval("someone@client.com")["allowed"] is True    # allowed domain
    assert auth.approval("stranger@nope.com")["allowed"] is False    # neither
