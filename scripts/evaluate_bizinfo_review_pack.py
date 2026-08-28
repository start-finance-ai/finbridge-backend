#!/usr/bin/env python3
"""Evaluate the stratified Bizinfo eligibility Human Review Pack.

This script reports review-pack diagnostics for the existing regex baseline. It
does not estimate population precision, recall, or accuracy for all 273 items.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from build_bizinfo_review_pack import (  # noqa: E402
    REPOSITORY_ROOT,
    TARGET_CONDITION_KEYS,
)


DEFAULT_INPUT = Path("data/review/bizinfo_eligibility_review_48.csv")
EXPECTED_ROW_COUNT = 48

REQUIRED_COLUMNS = (
    "review_id",
    "condition_type",
    "condition_label",
    "selection_role",
    "category",
    "pblanc_id",
    "pblanc_name",
    "source_field",
    "regex_matched_text",
    "source_text",
    "human_label",
    "human_evidence_text",
    "human_note",
)

PREDICTION_BY_SELECTION_ROLE = {
    "REGEX_CANDIDATE": "predicted_positive",
    "NEGATIVE_CONTROL": "predicted_negative",
}

ACTUAL_BY_HUMAN_LABEL = {
    "SUPPORTED_CANDIDATE": "actual_positive",
    "FALSE_POSITIVE": "actual_negative",
    "NOT_PRESENT": "actual_negative",
    "AMBIGUOUS": None,
}

FAILURE_CASE_FIELDS = (
    "review_id",
    "condition_type",
    "pblanc_id",
    "pblanc_name",
    "selection_role",
    "regex_matched_text",
    "human_label",
    "human_evidence_text",
    "human_note",
)


def read_review_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("Review CSV header is missing")
        missing_columns = [
            column for column in REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
        if missing_columns:
            raise ValueError(
                f"Review CSV required columns missing: {', '.join(missing_columns)}"
            )
        return [dict(row) for row in reader]


def validate_rows(rows: Sequence[dict[str, str]]) -> None:
    if len(rows) != EXPECTED_ROW_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_ROW_COUNT} review rows, found {len(rows)}"
        )

    review_ids = [row["review_id"].strip() for row in rows]
    if any(not review_id for review_id in review_ids):
        raise ValueError("review_id must not be blank")
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("review_id values must be unique")

    invalid_roles = sorted(
        {
            row["selection_role"]
            for row in rows
            if row["selection_role"] not in PREDICTION_BY_SELECTION_ROLE
        }
    )
    if invalid_roles:
        raise ValueError(f"Unexpected selection_role values: {invalid_roles}")

    invalid_labels = sorted(
        {
            row["human_label"]
            for row in rows
            if row["human_label"] not in ACTUAL_BY_HUMAN_LABEL
        }
    )
    if invalid_labels:
        raise ValueError(f"Unexpected human_label values: {invalid_labels}")

    missing_supported_evidence = [
        row["review_id"]
        for row in rows
        if row["human_label"] == "SUPPORTED_CANDIDATE"
        and not row["human_evidence_text"].strip()
    ]
    if missing_supported_evidence:
        raise ValueError(
            "SUPPORTED_CANDIDATE rows require human_evidence_text: "
            + ", ".join(missing_supported_evidence)
        )

    actual_conditions = {row["condition_type"] for row in rows}
    expected_conditions = set(TARGET_CONDITION_KEYS)
    if actual_conditions != expected_conditions:
        missing = sorted(expected_conditions - actual_conditions)
        unexpected = sorted(actual_conditions - expected_conditions)
        raise ValueError(
            f"Condition types differ; missing={missing}, unexpected={unexpected}"
        )

    for condition_type in TARGET_CONDITION_KEYS:
        condition_rows = [
            row for row in rows if row["condition_type"] == condition_type
        ]
        role_counts = Counter(row["selection_role"] for row in condition_rows)
        if len(condition_rows) != 4 or role_counts != {
            "REGEX_CANDIDATE": 3,
            "NEGATIVE_CONTROL": 1,
        }:
            raise ValueError(
                f"Unexpected stratified sample shape for {condition_type}: "
                f"rows={len(condition_rows)}, roles={dict(role_counts)}"
            )


def ratio_metric(numerator: int, denominator: int) -> dict[str, Any]:
    value = numerator / denominator if denominator else None
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(value, 6) if value is not None else None,
        "percent": round(value * 100, 2) if value is not None else None,
    }


def confusion_bucket(row: dict[str, str]) -> str | None:
    prediction = PREDICTION_BY_SELECTION_ROLE[row["selection_role"]]
    actual = ACTUAL_BY_HUMAN_LABEL[row["human_label"]]
    if actual is None:
        return None
    return {
        ("predicted_positive", "actual_positive"): "TP",
        ("predicted_positive", "actual_negative"): "FP",
        ("predicted_negative", "actual_negative"): "TN",
        ("predicted_negative", "actual_positive"): "FN",
    }[(prediction, actual)]


def summarize_rows(rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    confusion = Counter(
        bucket for row in rows if (bucket := confusion_bucket(row)) is not None
    )
    label_counts = Counter(row["human_label"] for row in rows)
    role_counts = Counter(row["selection_role"] for row in rows)

    candidate_rows = [
        row for row in rows if row["selection_role"] == "REGEX_CANDIDATE"
    ]
    negative_rows = [
        row for row in rows if row["selection_role"] == "NEGATIVE_CONTROL"
    ]
    candidate_labels = Counter(row["human_label"] for row in candidate_rows)
    negative_labels = Counter(row["human_label"] for row in negative_rows)

    scored_rows = sum(confusion[key] for key in ("TP", "FP", "TN", "FN"))
    ambiguous_rows = label_counts["AMBIGUOUS"]
    if scored_rows + ambiguous_rows != len(rows):
        raise ValueError("Confusion matrix and ambiguous rows do not sum to total rows")

    summary = {
        "total_rows": len(rows),
        "scored_rows": scored_rows,
        "ambiguous_rows": ambiguous_rows,
        "TP": confusion["TP"],
        "FP": confusion["FP"],
        "TN": confusion["TN"],
        "FN": confusion["FN"],
        "human_label_counts": {
            label: label_counts[label] for label in ACTUAL_BY_HUMAN_LABEL
        },
        "regex_candidate_count": role_counts["REGEX_CANDIDATE"],
        "candidate_supported_candidate_count": candidate_labels[
            "SUPPORTED_CANDIDATE"
        ],
        "candidate_actual_negative_count": (
            candidate_labels["FALSE_POSITIVE"]
            + candidate_labels["NOT_PRESENT"]
        ),
        "candidate_actual_negative_label_counts": {
            "FALSE_POSITIVE": candidate_labels["FALSE_POSITIVE"],
            "NOT_PRESENT": candidate_labels["NOT_PRESENT"],
        },
        "candidate_ambiguous_count": candidate_labels["AMBIGUOUS"],
        "negative_control_count": role_counts["NEGATIVE_CONTROL"],
        "negative_control_supported_candidate_count": negative_labels[
            "SUPPORTED_CANDIDATE"
        ],
        "negative_control_actual_negative_count": (
            negative_labels["NOT_PRESENT"]
            + negative_labels["FALSE_POSITIVE"]
        ),
        "negative_control_actual_negative_label_counts": {
            "NOT_PRESENT": negative_labels["NOT_PRESENT"],
            "FALSE_POSITIVE": negative_labels["FALSE_POSITIVE"],
        },
        "negative_control_ambiguous_count": negative_labels["AMBIGUOUS"],
        "candidate_precision_proxy": ratio_metric(
            confusion["TP"], confusion["TP"] + confusion["FP"]
        ),
        "review_pack_negative_control_false_negative_rate": ratio_metric(
            confusion["FN"], confusion["FN"] + confusion["TN"]
        ),
    }
    if summary["TP"] + summary["FP"] + summary["TN"] + summary["FN"] != scored_rows:
        raise ValueError("Confusion matrix total differs from scored rows")
    return summary


def failure_case(row: dict[str, str]) -> dict[str, str]:
    return {field: row[field] for field in FAILURE_CASE_FIELDS}


def build_report(path: Path, rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    false_positives = [
        failure_case(row) for row in rows if confusion_bucket(row) == "FP"
    ]
    false_negatives = [
        failure_case(row) for row in rows if confusion_bucket(row) == "FN"
    ]

    return {
        "evaluation_scope": {
            "evaluation_set_type": "AI-assisted human-reviewed evaluation set",
            "alternate_description": "Human-reviewed Review Pack",
            "input_path": path.relative_to(REPOSITORY_ROOT).as_posix(),
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sampling_design": (
                "12 condition types x (3 REGEX_CANDIDATE + 1 NEGATIVE_CONTROL)"
            ),
            "scope_warning": (
                "Stratified Review Pack diagnostics only; not an independent random "
                "evaluation set and not population precision, recall, or accuracy for "
                "all 273 Bizinfo samples."
            ),
            "independent_financial_expert_gold_standard": False,
        },
        "explicit_scoring_mapping": {
            "selection_role_to_prediction": PREDICTION_BY_SELECTION_ROLE,
            "human_label_to_actual": ACTUAL_BY_HUMAN_LABEL,
            "ambiguous_handling": (
                "AMBIGUOUS is counted separately and excluded from scored metrics."
            ),
            "false_positive_label_note": (
                "The human label name FALSE_POSITIVE maps explicitly to "
                "actual_negative; it is not used as the prediction source."
            ),
        },
        "overall_review_pack_results": summarize_rows(rows),
        "condition_results": {
            condition_type: {
                "sample_note": (
                    "4 stratified rows (3 REGEX_CANDIDATE + 1 NEGATIVE_CONTROL); "
                    "not condition-level population performance."
                ),
                **summarize_rows(
                    [
                        row
                        for row in rows
                        if row["condition_type"] == condition_type
                    ]
                ),
            }
            for condition_type in TARGET_CONDITION_KEYS
        },
        "failure_cases": {
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        },
    }


def iter_all_summaries(report: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield report["overall_review_pack_results"]
    yield from report["condition_results"].values()


def validate_report(report: dict[str, Any]) -> None:
    for summary in iter_all_summaries(report):
        confusion_total = sum(summary[key] for key in ("TP", "FP", "TN", "FN"))
        if confusion_total != summary["scored_rows"]:
            raise ValueError("Report confusion matrix does not match scored rows")
        if summary["scored_rows"] + summary["ambiguous_rows"] != summary["total_rows"]:
            raise ValueError("Report scored and ambiguous rows do not match total rows")

    condition_total = sum(
        result["total_rows"] for result in report["condition_results"].values()
    )
    if condition_total != report["overall_review_pack_results"]["total_rows"]:
        raise ValueError("Condition row totals do not match overall total rows")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the labeled Bizinfo stratified Human Review Pack."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Review CSV path (default: {DEFAULT_INPUT.as_posix()})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input
    if not input_path.is_absolute():
        input_path = REPOSITORY_ROOT / input_path

    try:
        rows = read_review_rows(input_path)
        validate_rows(rows)
        report = build_report(input_path, rows)
        validate_report(report)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        print(f"Review Pack evaluation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
