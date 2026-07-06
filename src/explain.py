"""
explain.py — the moat. Turn one flagged factor change into a defensible,
client-ready explanation, GROUNDED in the DEFRA changes report.

    explain_change(material, old, new, pct, retrieved_text, context=None) -> dict
        {
          "plain_english_reason": "...",   # 2-3 sentences, non-expert readable
          "methodology_note":     "...",   # 1-2 sentences, GHGP/ISO tone
          "target_impact_flag":   "...",   # e.g. "would breach a flat baseline"
        }

GROUNDING RULES (non-negotiable — these are the whole credibility of the tool):
  - Only use the numbers passed in. NEVER invent or estimate a factor.
  - If `retrieved_text` is empty / does not explain the change, the reason MUST be
    exactly: "No official reason found in the DEFRA changes report."
  - Methodology framing stays consistent with GHG Protocol / ISO 14064.
  - Output is strictly the three fields above.

Two backends:
  - If ANTHROPIC_API_KEY is set -> real Claude call (model claude-sonnet-5).
  - Otherwise -> a deterministic OFFLINE explainer that obeys the same grounding
    rules, so the demo (and the trap test) run without a key. Offline reasons are
    clearly labelled so they're never mistaken for model output.
"""

from __future__ import annotations

import os
import json

MODEL = "claude-sonnet-5"
NO_REASON = "No official reason found in the DEFRA changes report."

SYSTEM_PROMPT = f"""You are a GHG accounting methodology assistant. You explain
why a single emission factor changed between two annual DEFRA/DESNZ conversion-
factor releases, for a client report that must be defensible under the GHG
Protocol and ISO 14064.

STRICT RULES:
- Use ONLY the numbers given in the user message. NEVER invent, estimate, or
  recall an emission factor from memory.
- Base the reason ONLY on the provided "DEFRA changes report excerpt". If that
  excerpt is empty or does not actually explain THIS change, set
  plain_english_reason to exactly: "{NO_REASON}" — do not speculate.
- Keep methodology_note consistent with GHG Protocol / ISO 14064 language.
- Respond with STRICT JSON only, with exactly these keys:
  "plain_english_reason", "methodology_note", "target_impact_flag".
  No prose outside the JSON.
"""


def _target_flag(pct: float, context: dict | None) -> str:
    """
    Deterministic target-impact wording. Respects BOTH this factor's own
    direction and the product-level result, so a factor that fell is never
    described as "contributing to an increase".
    """
    context = context or {}
    breaches = context.get("breaches_baseline")
    rose = pct is not None and pct > 0
    fell = pct is not None and pct < 0

    if rose and breaches:
        return (
            "This factor increased, adding to a product footprint rise that would "
            "breach a flat baseline — flag for target review."
        )
    if rose:
        return "This factor increased; product footprint stays within a flat baseline."
    if fell:
        return "This factor decreased, easing the product footprint."
    if pct is not None and abs(pct) >= 10:
        return "Material factor change — check headroom against active targets."
    return "Immaterial at the product level."


def _direction(pct: float) -> str:
    if pct is None:
        return "changed"
    return "rose" if pct > 0 else "fell"


def _offline_explain(material, old, new, pct, retrieved_text, context) -> dict:
    """Deterministic, grounding-respecting explanation for when there's no API key."""
    if not retrieved_text or not retrieved_text.strip():
        reason = NO_REASON
    else:
        # We must not paraphrase without a model, so we surface the official text
        # verbatim, clearly labelled as an extract rather than a generated reason.
        snippet = " ".join(retrieved_text.split())
        if len(snippet) > 600:
            snippet = snippet[:600].rsplit(" ", 1)[0] + "…"
        reason = (
            f"[offline mode — extract from DEFRA changes report, not model-"
            f"generated] The factor {_direction(pct)} "
            f"{abs(pct):.1f}% ({old:g} → {new:g}). Official note: {snippet}"
        )
    methodology = (
        "Reported under the same GHG Protocol scope classification; the change is "
        "a factor-version update, so year-over-year comparisons should note the "
        "DEFRA release year (ISO 14064 comparability)."
    )
    return {
        "plain_english_reason": reason,
        "methodology_note": methodology,
        "target_impact_flag": _target_flag(pct, context),
    }


def _online_explain(material, old, new, pct, retrieved_text, context) -> dict:
    """Real Claude call. Falls back to offline on any error so the demo never dies."""
    try:
        import anthropic

        client = anthropic.Anthropic()
        user = {
            "material": material,
            "kg_co2e_old": old,
            "kg_co2e_new": new,
            "pct_change": pct,
            "defra_changes_report_excerpt": retrieved_text or "",
            "product_context": context or {},
            "instruction": (
                "Explain this single factor change. Remember: if the excerpt does "
                f'not explain it, plain_english_reason must be exactly "{NO_REASON}".'
            ),
        }
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(user)}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        data = _parse_json(text)
        # Safety net: enforce grounding even if the model drifts.
        if not (retrieved_text or "").strip():
            data["plain_english_reason"] = NO_REASON
        # Always trust our deterministic target flag over the model's.
        data["target_impact_flag"] = _target_flag(pct, context)
        return {
            "plain_english_reason": data.get("plain_english_reason", NO_REASON),
            "methodology_note": data.get("methodology_note", ""),
            "target_impact_flag": data["target_impact_flag"],
        }
    except Exception as exc:  # network, auth, parse — degrade gracefully
        result = _offline_explain(material, old, new, pct, retrieved_text, context)
        result["methodology_note"] += f"  (Note: API call failed — {type(exc).__name__}.)"
        return result


def _parse_json(text: str) -> dict:
    """Pull the first JSON object out of the model's reply."""
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("No JSON object in model response")


def explain_change(
    material: str,
    old: float,
    new: float,
    pct: float,
    retrieved_text: str,
    context: dict | None = None,
) -> dict:
    """Explain one flagged factor change, grounded in the DEFRA changes report."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return _online_explain(material, old, new, pct, retrieved_text, context)
    return _offline_explain(material, old, new, pct, retrieved_text, context)
