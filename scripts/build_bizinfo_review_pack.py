#!/usr/bin/env python3
"""Build a deterministic, unlabeled Bizinfo eligibility review pack.

The output is a sampling aid for human review. Regex hits and negative controls
are not eligibility labels, and this script never populates the human columns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from analyze_bizinfo_samples import (  # noqa: E402
    CONDITION_DEFINITIONS,
    REPOSITORY_ROOT,
    SOURCES,
    PatternDefinition,
    iter_rows,
    load_samples,
    matched_fields,
    text_value,
)


DEFAULT_OUTPUT = Path("data/review/bizinfo_eligibility_review_48.csv")
CANDIDATES_PER_CONDITION = 3
NEGATIVE_CONTROLS_PER_CONDITION = 1

TARGET_CONDITION_KEYS = (
    "region_or_location",
    "explicit_numeric_age",
    "pre_founder",
    "business_registration_status",
    "business_age",
    "industry",
    "business_type",
    "sales_or_income",
    "employee_count",
    "gender",
    "qualification_or_certification",
    "education_completion",
)

CSV_FIELDS = (
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

HUMAN_INPUT_FIELDS = (
    "human_label",
    "human_evidence_text",
    "human_note",
)


@dataclass(frozen=True)
class ReviewCandidate:
    category_key: str
    item: dict[str, Any]
    source_field: str
    matched_text: str
    source_text: str

    @property
    def program_id(self) -> str:
        return text_value(self.item.get("pblancId"))


def stable_score(*parts: str) -> str:
    value = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def target_definitions() -> tuple[PatternDefinition, ...]:
    definitions_by_key = {
        definition.key: definition for definition in CONDITION_DEFINITIONS
    }
    missing = [key for key in TARGET_CONDITION_KEYS if key not in definitions_by_key]
    if missing:
        raise ValueError(f"Analyzer condition definitions missing: {', '.join(missing)}")
    return tuple(definitions_by_key[key] for key in TARGET_CONDITION_KEYS)


def preferred_match(
    definition: PatternDefinition,
    matches: Sequence[tuple[str, Any, str]],
) -> tuple[str, Any, str]:
    return min(
        matches,
        key=lambda value: (
            0 if value[0] == "bsnsSumryCn" else 1,
            definition.fields.index(value[0]),
        ),
    )


def build_pools(
    by_category: dict[str, list[dict[str, Any]]],
    definition: PatternDefinition,
) -> tuple[list[ReviewCandidate], list[ReviewCandidate]]:
    pattern = definition.compile()
    regex_candidates: list[ReviewCandidate] = []
    negative_controls: list[ReviewCandidate] = []

    for category_key, item in iter_rows(by_category):
        matches = matched_fields(item, definition, pattern)
        if matches:
            field, match, normalized_text = preferred_match(definition, matches)
            regex_candidates.append(
                ReviewCandidate(
                    category_key=category_key,
                    item=item,
                    source_field=field,
                    matched_text=match.group(0),
                    source_text=normalized_text,
                )
            )
            continue

        source_field = "bsnsSumryCn"
        source_text = text_value(item.get(source_field))
        if not source_text:
            for field in definition.fields:
                source_text = text_value(item.get(field))
                if source_text:
                    source_field = field
                    break
        negative_controls.append(
            ReviewCandidate(
                category_key=category_key,
                item=item,
                source_field=source_field,
                matched_text="",
                source_text=source_text,
            )
        )

    return regex_candidates, negative_controls


def candidate_sort_key(
    candidate: ReviewCandidate,
    condition_key: str,
    role: str,
    used_program_ids: set[str],
) -> tuple[bool, str]:
    return (
        candidate.program_id in used_program_ids,
        stable_score(
            condition_key,
            role,
            candidate.category_key,
            candidate.program_id,
        ),
    )


def select_regex_candidates(
    pool: Sequence[ReviewCandidate],
    definition: PatternDefinition,
    used_program_ids: set[str],
) -> list[ReviewCandidate]:
    selected: list[ReviewCandidate] = []
    selected_ids: set[str] = set()

    # Prefer one candidate from each available category before filling gaps.
    for source in SOURCES:
        category_pool = [item for item in pool if item.category_key == source.key]
        if not category_pool:
            continue
        chosen = min(
            category_pool,
            key=lambda item: candidate_sort_key(
                item,
                definition.key,
                "REGEX_CANDIDATE",
                used_program_ids,
            ),
        )
        selected.append(chosen)
        selected_ids.add(chosen.program_id)
        if len(selected) == CANDIDATES_PER_CONDITION:
            return selected

    remaining = [item for item in pool if item.program_id not in selected_ids]
    remaining.sort(
        key=lambda item: candidate_sort_key(
            item,
            definition.key,
            "REGEX_CANDIDATE",
            used_program_ids,
        )
    )
    selected.extend(remaining[: CANDIDATES_PER_CONDITION - len(selected)])
    return selected


def select_negative_controls(
    pool: Sequence[ReviewCandidate],
    definition: PatternDefinition,
    used_program_ids: set[str],
    category_counts: Counter[str],
) -> list[ReviewCandidate]:
    selected: list[ReviewCandidate] = []
    selected_ids: set[str] = set()

    categories = sorted(
        SOURCES,
        key=lambda source: (category_counts[source.key], source.key),
    )
    for source in categories:
        category_pool = [item for item in pool if item.category_key == source.key]
        if not category_pool:
            continue
        category_pool.sort(
            key=lambda item: candidate_sort_key(
                item,
                definition.key,
                "NEGATIVE_CONTROL",
                used_program_ids,
            )
        )
        for candidate in category_pool:
            if candidate.program_id in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(candidate.program_id)
            break
        if len(selected) == NEGATIVE_CONTROLS_PER_CONDITION:
            break
    return selected


def make_row(
    review_number: int,
    definition: PatternDefinition,
    role: str,
    candidate: ReviewCandidate,
) -> dict[str, str]:
    category_names = {source.key: source.name for source in SOURCES}
    return {
        "review_id": f"BIZ-ELIG-{review_number:03d}",
        "condition_type": definition.key,
        "condition_label": definition.label,
        "selection_role": role,
        "category": category_names[candidate.category_key],
        "pblanc_id": candidate.program_id,
        "pblanc_name": text_value(candidate.item.get("pblancNm")),
        "source_field": candidate.source_field,
        "regex_matched_text": candidate.matched_text,
        "source_text": candidate.source_text,
        "human_label": "",
        "human_evidence_text": "",
        "human_note": "",
    }


def build_review_rows(
    by_category: dict[str, list[dict[str, Any]]],
) -> list[dict[str, str]]:
    definitions = target_definitions()
    pools = {
        definition.key: build_pools(by_category, definition)
        for definition in definitions
    }
    selected_by_condition: dict[
        str, tuple[list[ReviewCandidate], list[ReviewCandidate]]
    ] = {}
    used_program_ids: set[str] = set()
    category_counts: Counter[str] = Counter()

    # Reserve scarce regex pools first so broad conditions do not consume their
    # few category-specific programs. Rows are emitted later in the requested
    # condition order.
    selection_order = sorted(
        definitions,
        key=lambda definition: (len(pools[definition.key][0]), definition.key),
    )
    for definition in selection_order:
        candidate_pool, _ = pools[definition.key]
        selected_candidates = select_regex_candidates(
            candidate_pool, definition, used_program_ids
        )
        for candidate in selected_candidates:
            used_program_ids.add(candidate.program_id)
            category_counts[candidate.category_key] += 1
        selected_by_condition[definition.key] = (selected_candidates, [])

    # Negative controls are chosen only after all regex candidates are reserved,
    # reducing cross-condition program reuse without treating controls as labels.
    for definition in definitions:
        _, negative_pool = pools[definition.key]
        selected_negatives = select_negative_controls(
            negative_pool,
            definition,
            used_program_ids,
            category_counts,
        )
        for candidate in selected_negatives:
            used_program_ids.add(candidate.program_id)
            category_counts[candidate.category_key] += 1
        selected_candidates, _ = selected_by_condition[definition.key]
        selected_by_condition[definition.key] = (
            selected_candidates,
            selected_negatives,
        )

    rows: list[dict[str, str]] = []
    for definition in definitions:
        selected_candidates, selected_negatives = selected_by_condition[
            definition.key
        ]
        for role, selected in (
            ("REGEX_CANDIDATE", selected_candidates),
            ("NEGATIVE_CONTROL", selected_negatives),
        ):
            for candidate in selected:
                rows.append(
                    make_row(
                        len(rows) + 1,
                        definition,
                        role,
                        candidate,
                    )
                )

    return rows


def validate_rows(rows: Sequence[dict[str, str]]) -> None:
    review_ids = [row["review_id"] for row in rows]
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("review_id values must be unique")
    if any(row[field] for row in rows for field in HUMAN_INPUT_FIELDS):
        raise ValueError("Human input columns must remain blank")
    if any(row["selection_role"] not in {"REGEX_CANDIDATE", "NEGATIVE_CONTROL"} for row in rows):
        raise ValueError("Unexpected selection_role value")


def write_csv(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def print_summary(path: Path, rows: Sequence[dict[str, str]]) -> None:
    role_counts = Counter(
        (row["condition_type"], row["selection_role"]) for row in rows
    )
    category_counts = Counter(row["category"] for row in rows)

    print(f"Review rows: {len(rows)}")
    for definition in target_definitions():
        print(
            f"{definition.key}: "
            f"REGEX_CANDIDATE={role_counts[(definition.key, 'REGEX_CANDIDATE')]}, "
            f"NEGATIVE_CONTROL={role_counts[(definition.key, 'NEGATIVE_CONTROL')]}"
        )
    print(
        "Categories: "
        + ", ".join(
            f"{source.name}={category_counts[source.name]}" for source in SOURCES
        )
    )
    print(f"Saved: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic, unlabeled Bizinfo eligibility review CSV."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.as_posix()})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output
    if not output_path.is_absolute():
        output_path = REPOSITORY_ROOT / output_path

    try:
        by_category, _ = load_samples()
        rows = build_review_rows(by_category)
        validate_rows(rows)
        write_csv(output_path, rows)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        print(f"Review pack build failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print_summary(output_path, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
