"""Small, inspectable extraction baseline. Presence is not legal adequacy."""
import re
from .models import Policy

# Each pattern accepts a narrow, documented wording. No semantic inference.
PATTERNS = {
    "payment_days": re.compile(r"(?:payment\s+terms?\s*:\s*(?:net\s*)?|paid\s+within\s+)(\d{1,3})\s*days?", re.I),
    "breach_hours": re.compile(r"(?:breach\s+notification\s*:\s*(?:within\s*)?|notify\s+(?:the\s+)?customer\s+(?:of\s+(?:a\s+)?breach\s+)?within\s+)(\d{1,3})\s*hours?", re.I),
    "uptime_percent": re.compile(r"(?:uptime|availability)(?:\s+(?:target|commitment|guarantee))?\s*:\s*(\d{2,3}(?:\.\d{1,4})?)\s*%", re.I),
    "termination": re.compile(r"(?:either party|the customer|customer)\s+may\s+terminate\b[^\n.]*", re.I),
    "audit": re.compile(r"(?:the customer|customer)\s+(?:may|has the right to)\s+audit\b[^\n.]*", re.I),
}


def analyze(pages: list[str], policy: Policy) -> dict:
    fields = {}
    for name, pattern in PATTERNS.items():
        matches = []
        for number, page in enumerate(pages, 1):
            for match in pattern.finditer(page):
                start, end = match.span()
                value = float(match.group(1)) if name == "uptime_percent" else int(match.group(1)) if name.endswith(("days", "hours")) else True
                line_start = page.rfind("\n", 0, start) + 1
                line_end = page.find("\n", end)
                context = page[line_start:line_end if line_end != -1 else len(page)]
                # A narrow lexical baseline must not silently approve a match
                # embedded in an explicitly negative sentence. This cautious
                # flag is not a general negation/semantic understanding claim.
                negated = bool(re.search(r"\b(?:no|not|never|without|neither|excluded|unavailable)\b", context, re.I))
                matches.append({"value": value, "page": number, "start": start, "end": end, "quote": page[start:end], "negation_flag": negated})
        # Ambiguous clauses never silently select the most favourable value.
        values = {str(match["value"]) for match in matches}
        fields[name] = {"value": matches[0]["value"] if len(values) == 1 else None,
                        "ambiguous": len(values) > 1, "negation_flag": any(item["negation_flag"] for item in matches), "evidence": matches}
    definitions = [
        ("payment_days", "Payment window", f"At most {policy.max_payment_days} days", lambda v: v <= policy.max_payment_days, True),
        ("breach_hours", "Breach notification", f"At most {policy.max_breach_hours} hours", lambda v: v <= policy.max_breach_hours, True),
        ("uptime_percent", "Availability commitment", f"At least {policy.min_uptime_percent:g}% uptime", lambda v: v >= policy.min_uptime_percent and v <= 100, True),
        ("termination", "Termination wording", "Explicit customer/either-party termination wording", bool, policy.require_termination),
        ("audit", "Audit wording", "Explicit customer audit wording", bool, policy.require_audit),
    ]
    findings = []
    for key, label, target, check, required in definitions:
        field = fields[key]
        if not required:
            state, reason = "not_required", "Disabled in the submitted policy."
        elif field["ambiguous"]:
            state, reason = "attention", "Conflicting values were found; resolve the clauses manually."
        elif field["negation_flag"]:
            state, reason = "attention", "Potential negation appears on the same source line. A reviewer must interpret the clause."
        elif field["value"] is None:
            state, reason = "missing", "No supported wording found. Inspect the original document; the clause may use another form."
        elif not check(field["value"]):
            state, reason = "attention", "The extracted value falls outside this review policy."
        else:
            state, reason = "clear", "Supported wording matches this rule. Legal adequacy still requires a reviewer."
        findings.append({"key": key, "label": label, "target": target, "state": state, "reason": reason, **field})
    counts = {state: sum(item["state"] == state for item in findings) for state in ("clear", "attention", "missing", "not_required")}
    return {"engine": "deterministic-extraction.v1", "policy": policy.model_dump(), "findings": findings,
            "counts": counts, "requires_review": True,
            "limitations": "Pattern-based extraction, not legal advice or an AI judgment. 'Missing' means unrecognized wording, not proven absence. PDF pages are parsed text; scanned documents require OCR, which is not implemented."}
