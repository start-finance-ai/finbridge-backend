from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class ConditionType(str, Enum):
    REGION_OR_LOCATION = "region_or_location"
    AGE = "age"
    PRE_FOUNDER = "pre_founder"
    BUSINESS_REGISTRATION_STATUS = "business_registration_status"
    BUSINESS_AGE = "business_age"
    INDUSTRY = "industry"
    BUSINESS_TYPE = "business_type"
    SALES_OR_INCOME = "sales_or_income"
    EMPLOYEE_COUNT = "employee_count"
    GENDER = "gender"
    QUALIFICATION_OR_CERTIFICATION = "qualification_or_certification"
    EDUCATION_COMPLETION = "education_completion"


class Subject(str, Enum):
    APPLICANT = "APPLICANT"
    REPRESENTATIVE = "REPRESENTATIVE"
    BUSINESS = "BUSINESS"
    PRODUCT = "PRODUCT"
    ORGANIZATION = "ORGANIZATION"
    FACILITY = "FACILITY"
    PROGRAM = "PROGRAM"


class Operator(str, Enum):
    EQ = "EQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    BETWEEN = "BETWEEN"
    IN = "IN"
    EXISTS = "EXISTS"


class Unit(str, Enum):
    NONE = "NONE"
    YEAR = "YEAR"
    MONTH = "MONTH"
    PERSON = "PERSON"
    KRW = "KRW"
    PERCENT = "PERCENT"


class Polarity(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConditionRole(str, Enum):
    ELIGIBILITY_REQUIRED = "ELIGIBILITY_REQUIRED"
    ELIGIBILITY_EXCEPTION = "ELIGIBILITY_EXCEPTION"
    CALCULATION_ONLY = "CALCULATION_ONLY"
    POST_SELECTION = "POST_SELECTION"
    CONTEXT_ONLY = "CONTEXT_ONLY"


class ExtractionMethod(str, Enum):
    STRUCTURED = "STRUCTURED"
    REGEX = "REGEX"
    LLM = "LLM"
    HUMAN = "HUMAN"


class ExtractionStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


class ProgramExtractionStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


ScalarValue = str | int | float | bool


_MATCHING_ROLES = {
    ConditionRole.ELIGIBILITY_REQUIRED,
    ConditionRole.ELIGIBILITY_EXCEPTION,
}
_NON_MATCHING_ROLES = {
    ConditionRole.CALCULATION_ONLY,
    ConditionRole.POST_SELECTION,
    ConditionRole.CONTEXT_ONLY,
}
_MATCHING_SUBJECTS: dict[ConditionType, set[Subject]] = {
    ConditionType.REGION_OR_LOCATION: {
        Subject.APPLICANT,
        Subject.REPRESENTATIVE,
        Subject.BUSINESS,
    },
    ConditionType.AGE: {Subject.APPLICANT, Subject.REPRESENTATIVE},
    ConditionType.PRE_FOUNDER: {Subject.APPLICANT},
    ConditionType.BUSINESS_REGISTRATION_STATUS: {Subject.BUSINESS},
    ConditionType.BUSINESS_AGE: {Subject.BUSINESS},
    ConditionType.INDUSTRY: {Subject.BUSINESS, Subject.PRODUCT},
    ConditionType.BUSINESS_TYPE: {Subject.BUSINESS},
    ConditionType.SALES_OR_INCOME: {Subject.APPLICANT, Subject.BUSINESS},
    ConditionType.EMPLOYEE_COUNT: {Subject.BUSINESS},
    ConditionType.GENDER: {Subject.APPLICANT, Subject.REPRESENTATIVE},
    ConditionType.QUALIFICATION_OR_CERTIFICATION: {
        Subject.APPLICANT,
        Subject.BUSINESS,
        Subject.PRODUCT,
    },
    ConditionType.EDUCATION_COMPLETION: {
        Subject.APPLICANT,
        Subject.REPRESENTATIVE,
    },
}


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    condition_id: str = Field(min_length=1)
    condition_type: ConditionType
    subject: Subject
    operator: Operator
    raw_value: str = Field(min_length=1)
    value: ScalarValue | None = None
    values: list[ScalarValue] | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: Unit
    polarity: Polarity
    condition_role: ConditionRole
    evidence_text: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    evidence_start: int | None = Field(default=None, ge=0)
    evidence_end: int | None = Field(default=None, ge=1)
    extraction_method: ExtractionMethod
    extraction_status: ExtractionStatus

    @model_validator(mode="after")
    def validate_condition(self) -> "Condition":
        if self.evidence_start is not None and self.evidence_end is not None:
            if self.evidence_end <= self.evidence_start:
                raise ValueError("evidence_end must be greater than evidence_start")

        if self.operator in {
            Operator.EQ,
            Operator.GT,
            Operator.GTE,
            Operator.LT,
            Operator.LTE,
        }:
            if self.value is None:
                raise ValueError(f"{self.operator.value} requires value")
            if any(
                operand is not None
                for operand in (self.values, self.min_value, self.max_value)
            ):
                raise ValueError(f"{self.operator.value} only accepts value")
        elif self.operator is Operator.IN:
            if not self.values:
                raise ValueError("IN requires a non-empty values list")
            if any(
                operand is not None
                for operand in (self.value, self.min_value, self.max_value)
            ):
                raise ValueError("IN only accepts values")
        elif self.operator is Operator.BETWEEN:
            if self.min_value is None or self.max_value is None:
                raise ValueError("BETWEEN requires min_value and max_value")
            if self.min_value > self.max_value:
                raise ValueError("BETWEEN min_value must not exceed max_value")
            if self.value is not None or self.values is not None:
                raise ValueError("BETWEEN only accepts min_value and max_value")
        elif self.operator is Operator.EXISTS:
            if any(
                operand is not None
                for operand in (
                    self.value,
                    self.values,
                    self.min_value,
                    self.max_value,
                )
            ):
                raise ValueError("EXISTS does not accept operands")

        if self.condition_role in _MATCHING_ROLES:
            if self.polarity is Polarity.NOT_APPLICABLE:
                raise ValueError("matching roles cannot use NOT_APPLICABLE")
            allowed_subjects = _MATCHING_SUBJECTS[self.condition_type]
            if self.subject not in allowed_subjects:
                raise ValueError(
                    "condition_type and subject are incompatible for matching"
                )
        elif self.condition_role in _NON_MATCHING_ROLES:
            if self.polarity is not Polarity.NOT_APPLICABLE:
                raise ValueError("non-matching roles require NOT_APPLICABLE")

        if (
            self.condition_role is ConditionRole.ELIGIBILITY_EXCEPTION
            and self.polarity is not Polarity.INCLUDE
        ):
            raise ValueError("ELIGIBILITY_EXCEPTION is positive-path metadata only")

        return self


class EligibilityGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    group_id: str = Field(min_length=1)
    conditions: list[Condition] = Field(min_length=1)


class ProgramEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    eligibility_schema_version: Literal["0.1"] = "0.1"
    program_id: str = Field(min_length=1)
    source_url: AnyHttpUrl | None = None
    eligibility_extraction_status: ProgramExtractionStatus
    common_conditions: list[Condition] = Field(default_factory=list)
    eligibility_groups: list[EligibilityGroup] = Field(default_factory=list)
    global_exclusions: list[Condition] = Field(default_factory=list)
    non_eligibility_conditions: list[Condition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_program_eligibility(self) -> "ProgramEligibility":
        for condition in self.common_conditions:
            if condition.condition_role is ConditionRole.ELIGIBILITY_EXCEPTION:
                raise ValueError("ELIGIBILITY_EXCEPTION is only valid inside a group")
            if condition.polarity is not Polarity.INCLUDE:
                raise ValueError("common conditions must use INCLUDE")

        for group in self.eligibility_groups:
            for condition in group.conditions:
                if condition.condition_role not in _MATCHING_ROLES:
                    raise ValueError("group conditions must use a matching role")
                if condition.polarity is not Polarity.INCLUDE:
                    raise ValueError("group conditions must use INCLUDE")

        for condition in self.global_exclusions:
            if condition.condition_role is not ConditionRole.ELIGIBILITY_REQUIRED:
                raise ValueError("global exclusions must use ELIGIBILITY_REQUIRED")
            if condition.polarity is not Polarity.EXCLUDE:
                raise ValueError("global exclusions must use EXCLUDE")

        for condition in self.non_eligibility_conditions:
            if condition.condition_role not in _NON_MATCHING_ROLES:
                raise ValueError("non-eligibility conditions require a non-matching role")
            if condition.polarity is not Polarity.NOT_APPLICABLE:
                raise ValueError("non-eligibility conditions require NOT_APPLICABLE")

        matching_conditions = [
            *self.common_conditions,
            *(condition for group in self.eligibility_groups for condition in group.conditions),
            *self.global_exclusions,
        ]
        all_conditions = [*matching_conditions, *self.non_eligibility_conditions]
        condition_ids = [condition.condition_id for condition in all_conditions]
        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError("condition_id must be unique within a program")

        if self.eligibility_extraction_status is ProgramExtractionStatus.SUPPORTED:
            if any(
                condition.extraction_status is not ExtractionStatus.SUPPORTED
                for condition in matching_conditions
            ):
                raise ValueError(
                    "a SUPPORTED program cannot contain unresolved matching conditions"
                )

        return self


def enum_or_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value
