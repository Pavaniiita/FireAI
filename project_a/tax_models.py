"""
Tax Data Models for Indian Salaried Taxpayers (Income-tax Act, 1961).
Defines schemas for taxpayer inputs, deductions, step-by-step audit breakdown,
and comparison results between Old and New Regimes.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


class TaxRegime(str, Enum):
    OLD = "OLD"
    NEW = "NEW"


class FinancialYear(str, Enum):
    FY2024_25 = "2024-25"  # AY 2025-26
    FY2025_26 = "2025-26"  # AY 2026-27


@dataclass
class TaxpayerInput:
    gross_salary: float
    basic_salary: float = 0.0
    hra_received: float = 0.0
    rent_paid: float = 0.0
    is_metro: bool = False
    
    # Chapter VI-A & Other deductions (applicable for Old Regime)
    sec_80c: float = 0.0           # EPF, PPF, ELSS, Life Insurance, etc. (max 1.5L)
    sec_80ccd_1b: float = 0.0      # NPS self contribution (max 50k)
    sec_80d_self: float = 0.0      # Health insurance self/family (max 25k or 50k if senior)
    sec_80d_parents: float = 0.0   # Health insurance parents (max 25k or 50k if senior)
    home_loan_interest: float = 0.0 # Sec 24(b) self-occupied home loan interest (max 2.0L)
    professional_tax: float = 0.0   # Sec 16(iii) professional tax (max 2,500)
    other_exemptions: float = 0.0   # Other Sec 10 allowances (e.g. LTA)
    
    # Metadata / Context
    age: int = 35                  # Standard individual (<60), Senior (60-80), Super Senior (80+)
    parents_senior: bool = False   # True if parents are >= 60 yrs
    
    def __post_init__(self):
        # Default basic salary to 50% of gross if not specified
        if self.basic_salary <= 0 and self.gross_salary > 0:
            self.basic_salary = round(self.gross_salary * 0.50, 2)


@dataclass
class AuditStep:
    step_name: str
    clause_ref: str
    amount: float
    running_total: float
    description: str


@dataclass
class TaxBreakdown:
    regime: TaxRegime
    financial_year: FinancialYear
    gross_salary: float
    standard_deduction: float
    hra_exemption: float
    sec_24b_loss: float
    chapter_vi_a: float
    total_deductions: float
    taxable_income: float
    base_tax: float
    rebate_87a: float
    tax_after_rebate: float
    surcharge: float
    marginal_relief_surcharge: float
    cess: float
    total_tax_payable: int  # Rounded to nearest 10 per Sec 288B
    audit_trail: List[AuditStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["regime"] = self.regime.value
        d["financial_year"] = self.financial_year.value
        return d


@dataclass
class RegimeComparison:
    taxpayer_input: TaxpayerInput
    old_regime: TaxBreakdown
    new_regime: TaxBreakdown
    recommended_regime: TaxRegime
    tax_difference: int
    recommendation_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_regime_tax": self.old_regime.total_tax_payable,
            "new_regime_tax": self.new_regime.total_tax_payable,
            "recommended_regime": self.recommended_regime.value,
            "tax_saved": abs(self.tax_difference),
            "recommendation_reason": self.recommendation_reason,
            "breakdown_old": self.old_regime.to_dict(),
            "breakdown_new": self.new_regime.to_dict(),
        }
