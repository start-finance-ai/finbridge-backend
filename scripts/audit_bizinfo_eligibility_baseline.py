#!/usr/bin/env python3
"""Audit the local 20-row Bizinfo snapshot and deterministic extractor.

Raw expression counts are audit candidates, not verified eligibility labels.
This script performs no network requests and does not write any files.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import DEFAULT_BIZINFO_SNAPSHOT  # noqa: E402
from app.data.program_repository import ProgramRepository  # noqa: E402
from app.eligibility.extractor import (  # noqa: E402
    EligibilityExtractor,
    _extract_age,
    _extract_business_age,
    _extract_existing_business,
    _extract_pre_founder,
    _extract_region,
    _plain_text,
    _target_section,
)


RAW_AUDIT_PATTERNS = {
    "BUSINESS_REGISTRATION": re.compile(
        r"사업자\s*등록(?:증)?|사업자등록(?:증)?"
    ),
    "BUSINESS_ENTITY_TYPE": re.compile(
        r"법인(?:창업|사업자|기업)|개인\s*사업자"
    ),
    "INDUSTRY": re.compile(
        r"AI|ICT|바이오|콘텐츠|제조|신산업|GovTech|"
        r"물안전|물환경|물이용|스마트팜|농업"
    ),
    "GLOBAL_EXCLUSION": re.compile(r"제외\s*(?:대상|업종|기업|법인)?"),
    "REFERENCE": re.compile(
        r"공고문\s*(?:참조|확인)|별첨\s*(?:참조|확인)|신청자격\s*상이"
    ),
}


def _all_conditions(eligibility):
    return [
        *eligibility.common_conditions,
        *(
            condition
            for group in eligibility.eligibility_groups
            for condition in group.conditions
        ),
        *eligibility.global_exclusions,
    ]


def build_report() -> dict[str, object]:
    programs = ProgramRepository(DEFAULT_BIZINFO_SNAPSHOT).list()
    raw_hits: dict[str, list[str]] = {
        key: []
        for key in (
            "REGION",
            "AGE",
            "PRE_FOUNDER",
            "STARTUP_BUSINESS",
            "BUSINESS_AGE",
            *RAW_AUDIT_PATTERNS,
        )
    }

    extractor = EligibilityExtractor()
    extracted_rows = []
    status_counts: Counter[str] = Counter()
    condition_type_counts: Counter[str] = Counter()

    for program in programs:
        summary = _plain_text(program.summary_raw)
        target = _target_section(summary)
        checks = {
            "REGION": _extract_region(target) is not None,
            "AGE": bool(_extract_age(target)),
            "PRE_FOUNDER": _extract_pre_founder(target) is not None,
            "STARTUP_BUSINESS": _extract_existing_business(target) is not None,
            "BUSINESS_AGE": bool(_extract_business_age(target)),
            **{
                key: bool(pattern.search(summary if key == "REFERENCE" else target))
                for key, pattern in RAW_AUDIT_PATTERNS.items()
            },
        }
        for key, matched in checks.items():
            if matched:
                raw_hits[key].append(program.program_id)

        eligibility = extractor.extract(program)
        conditions = _all_conditions(eligibility)
        status = eligibility.eligibility_extraction_status.value
        status_counts[status] += 1
        condition_type_counts.update(
            condition.condition_type.value for condition in conditions
        )
        extracted_rows.append(
            {
                "program_id": program.program_id,
                "program_name": program.program_name,
                "program_status": status,
                "condition_count": len(conditions),
            }
        )

    return {
        "methodology": {
            "scope": str(DEFAULT_BIZINFO_SNAPSHOT.relative_to(REPOSITORY_ROOT)),
            "raw_expression_counts_are_eligibility_labels": False,
            "hashtags_used": False,
            "trgetNm_used": False,
            "network_used": False,
            "files_written": False,
        },
        "raw_audit_candidate_counts": {
            key: {"count": len(program_ids), "program_ids": program_ids}
            for key, program_ids in raw_hits.items()
        },
        "extraction_coverage": {
            "total_programs": len(programs),
            "programs_with_conditions": sum(
                row["condition_count"] > 0 for row in extracted_rows
            ),
            "program_status_counts": dict(sorted(status_counts.items())),
            "condition_type_counts": dict(sorted(condition_type_counts.items())),
        },
        "programs": extracted_rows,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
