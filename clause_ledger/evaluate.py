"""Deterministic rule-fixture agreement, not a semantic NLP benchmark."""
import argparse
import json
from pathlib import Path

from .analysis import analyze
from .models import Policy
from .samples import SAMPLES


def evaluate():
    cases = [(sample["id"], sample["text"], expected) for sample, expected in zip(SAMPLES, [(5, 0, 0), (1, 3, 1), (4, 1, 0)])]
    cases += [
        ("alternate-supported-payment", "Supplier invoices are paid within 45 days. Other commitments need review.", (1, 0, 4)),
        ("unsupported-wording", "We settle invoices promptly and provide excellent service. Our clients can inspect our records.", (0, 0, 5)),
        ("invalid-availability", "Availability target: 105%. This is intentionally impossible.", (0, 1, 4)),
    ]
    rows = []
    for name, text, expected in cases:
        result = analyze([text], Policy())
        actual = tuple(result["counts"][key] for key in ("clear", "attention", "missing"))
        evidence_valid = all(text[item["start"]:item["end"]] == item["quote"] for finding in result["findings"] for item in finding["evidence"])
        rows.append({"case": name, "expected_counts": list(expected), "actual_counts": list(actual), "passed": actual == expected and evidence_valid, "exact_evidence_valid": evidence_valid})
    return {"scope": "Six authored deterministic extraction/rule fixtures, including three UI examples. Not an independent semantic extraction benchmark.", "passed": sum(row["passed"] for row in rows), "cases": len(rows), "details": rows, "limitations": "Narrow supported patterns; no OCR, LLM, legal adequacy, or real-contract accuracy evaluation."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = evaluate()
    target = Path(__file__).resolve().parent.parent / "docs" / "evaluation.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(args.check and report["passed"] != report["cases"])


if __name__ == "__main__":
    raise SystemExit(main())
