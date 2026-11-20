"""
Hand-coded Rules Engine for Indian Income Tax.
Implementation A: Rules written as deterministic code / configuration.

Covers:
- Standard Deduction: Sec 16(ia)
- HRA Exemption: Sec 10(13A) read with Rule 2A
- Home Loan Interest (Self-occupied): Sec 24(b)
- Chapter VI-A Deductions: Sec 80C, Sec 80CCD(1B), Sec 80D (self & parents)
- Tax Slabs for FY 2024-25 and FY 2025-26
- Section 87A Rebate + Marginal Relief
- Surcharge Slabs + Marginal Relief
- Health and Education Cess: 4%
- Rounding off under Section 288A (taxable income) and Section 288B (tax payable)
- Line-by-line statutory clause attribution for 100% rupee traceability.
"""

from typing import List, Dict, Tuple
from project_a.tax_models import (
    TaxpayerInput, TaxBreakdown, TaxRegime, FinancialYear, AuditStep, RegimeComparison
)


class HandCodedTaxEngine:
    def __init__(self, fy: FinancialYear = FinancialYear.FY2024_25):
        self.fy = fy

    def compute_hra_exemption(self, taxpayer: TaxpayerInput) -> Tuple[float, List[AuditStep]]:
        steps = []
        if taxpayer.hra_received <= 0 or taxpayer.rent_paid <= 0:
            steps.append(AuditStep(
                step_name="HRA Exemption",
                clause_ref="Sec 10(13A) read with Rule 2A",
                amount=0.0,
                running_total=0.0,
                description="No HRA received or no rent paid; exemption is Nil."
            ))
            return 0.0, steps

        # Condition 1: Actual HRA received
        cond1 = taxpayer.hra_received
        # Condition 2: Rent paid minus 10% of basic salary
        excess_rent = max(0.0, taxpayer.rent_paid - 0.10 * taxpayer.basic_salary)
        # Condition 3: 50% of basic (Metro) or 40% of basic (Non-Metro)
        pct = 0.50 if taxpayer.is_metro else 0.40
        cond3 = pct * taxpayer.basic_salary

        exemption = min(cond1, excess_rent, cond3)
        steps.append(AuditStep(
            step_name="HRA Exemption Condition 1",
            clause_ref="Sec 10(13A) Rule 2A(a)",
            amount=cond1,
            running_total=cond1,
            description=f"Actual HRA received: ₹{cond1:,.2f}"
        ))
        steps.append(AuditStep(
            step_name="HRA Exemption Condition 2",
            clause_ref="Sec 10(13A) Rule 2A(b)",
            amount=excess_rent,
            running_total=excess_rent,
            description=f"Rent paid (₹{taxpayer.rent_paid:,.2f}) minus 10% basic (₹{0.10*taxpayer.basic_salary:,.2f}) = ₹{excess_rent:,.2f}"
        ))
        steps.append(AuditStep(
            step_name="HRA Exemption Condition 3",
            clause_ref="Sec 10(13A) Rule 2A(c)",
            amount=cond3,
            running_total=cond3,
            description=f"{'50%' if taxpayer.is_metro else '40%'} of basic salary (₹{taxpayer.basic_salary:,.2f}) = ₹{cond3:,.2f}"
        ))
        steps.append(AuditStep(
            step_name="HRA Exemption Final",
            clause_ref="Sec 10(13A)",
            amount=exemption,
            running_total=exemption,
            description=f"Least of conditions 1, 2, 3 allowed as exemption: ₹{exemption:,.2f}"
        ))
        return exemption, steps

    def compute_old_regime(self, taxpayer: TaxpayerInput) -> TaxBreakdown:
        steps = []
        gross = taxpayer.gross_salary

        # 1. Standard Deduction: ₹50,000
        std_ded = min(gross, 50000.0)
        steps.append(AuditStep("Standard Deduction", "Sec 16(ia)", std_ded, gross - std_ded,
                               f"Standard deduction capped at ₹50,000: ₹{std_ded:,.2f}"))

        # 2. HRA Exemption
        hra_exemp, hra_steps = self.compute_hra_exemption(taxpayer)
        steps.extend(hra_steps)

        # Professional tax & other Sec 10
        prof_tax = min(taxpayer.professional_tax, 2500.0)
        other_ex = taxpayer.other_exemptions
        net_salary = max(0.0, gross - std_ded - hra_exemp - prof_tax - other_ex)

        # 3. House Property Loss: Sec 24(b) (max 2,00,000 for self-occupied)
        hp_loss = min(taxpayer.home_loan_interest, 200000.0)
        if hp_loss > 0:
            steps.append(AuditStep("Home Loan Interest Deduction", "Sec 24(b)", hp_loss, net_salary - hp_loss,
                                   f"Deduction for interest on self-occupied house loan (capped at ₹2,00,000): ₹{hp_loss:,.2f}"))

        gross_total_income = max(0.0, net_salary - hp_loss)

        # 4. Chapter VI-A Deductions
        c_80c = min(taxpayer.sec_80c, 150000.0)
        c_80ccd1b = min(taxpayer.sec_80ccd_1b, 50000.0)

        limit_self = 50000.0 if taxpayer.age >= 60 else 25000.0
        c_80d_self = min(taxpayer.sec_80d_self, limit_self)

        limit_parents = 50000.0 if taxpayer.parents_senior else 25000.0
        c_80d_parents = min(taxpayer.sec_80d_parents, limit_parents)

        total_vi_a = c_80c + c_80ccd1b + c_80d_self + c_80d_parents
        total_vi_a = min(total_vi_a, gross_total_income)

        steps.append(AuditStep("Chapter VI-A Deductions", "Sec 80C, 80CCD(1B), 80D", total_vi_a,
                               gross_total_income - total_vi_a,
                               f"80C: ₹{c_80c:,.2f}, 80CCD(1B): ₹{c_80ccd1b:,.2f}, 80D: ₹{c_80d_self + c_80d_parents:,.2f}"))

        # Taxable income rounded to nearest 10 (Sec 288A)
        raw_taxable = max(0.0, gross_total_income - total_vi_a)
        taxable_income = round(raw_taxable / 10.0) * 10.0

        # 5. Base Tax (Old Regime Slabs for Individual < 60 yrs)
        # 0 - 2,50,000: Nil
        # 2,50,001 - 5,00,000: 5%
        # 5,00,001 - 10,00,000: 20%
        # Above 10,00,000: 30%
        base_tax = 0.0
        if taxable_income <= 250000:
            base_tax = 0.0
        elif taxable_income <= 500000:
            base_tax = (taxable_income - 250000) * 0.05
        elif taxable_income <= 1000000:
            base_tax = 12500.0 + (taxable_income - 500000) * 0.20
        else:
            base_tax = 112500.0 + (taxable_income - 1000000) * 0.30

        steps.append(AuditStep("Base Tax Calculation", "Finance Act - First Schedule Part I", base_tax, base_tax,
                               f"Tax calculated on taxable income of ₹{taxable_income:,.2f} per old slabs"))

        # 6. Rebate under Sec 87A (Old Regime)
        # Up to ₹5,00,000: rebate up to ₹12,500
        rebate_87a = 0.0
        if taxable_income <= 500000:
            rebate_87a = min(base_tax, 12500.0)
            steps.append(AuditStep("Section 87A Rebate", "Sec 87A", rebate_87a, base_tax - rebate_87a,
                                   f"Taxable income <= ₹5,00,000. Full rebate of ₹{rebate_87a:,.2f} applied. Tax becomes ₹0."))

        tax_after_rebate = base_tax - rebate_87a

        # 7. Surcharge & Marginal Relief
        surcharge = 0.0
        marginal_relief_surcharge = 0.0
        if tax_after_rebate > 0:
            if taxable_income > 50000000:  # > 5 Cr: 37%
                nominal_surch = tax_after_rebate * 0.37
                # Marginal relief at 5 Cr threshold
                tax_at_5cr = 112500.0 + (50000000 - 1000000) * 0.30
                surch_at_5cr = tax_at_5cr * 0.25
                max_allowed = tax_at_5cr + surch_at_5cr + (taxable_income - 50000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch
            elif taxable_income > 20000000:  # > 2 Cr: 25%
                nominal_surch = tax_after_rebate * 0.25
                tax_at_2cr = 112500.0 + (20000000 - 1000000) * 0.30
                surch_at_2cr = tax_at_2cr * 0.15
                max_allowed = tax_at_2cr + surch_at_2cr + (taxable_income - 20000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch
            elif taxable_income > 10000000:  # > 1 Cr: 15%
                nominal_surch = tax_after_rebate * 0.15
                tax_at_1cr = 112500.0 + (10000000 - 1000000) * 0.30
                surch_at_1cr = tax_at_1cr * 0.10
                max_allowed = tax_at_1cr + surch_at_1cr + (taxable_income - 10000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch
            elif taxable_income > 5000000:  # > 50 Lakh: 10%
                nominal_surch = tax_after_rebate * 0.10
                tax_at_50l = 112500.0 + (5000000 - 1000000) * 0.30
                max_allowed = tax_at_50l + (taxable_income - 5000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch

        if surcharge > 0 or marginal_relief_surcharge > 0:
            steps.append(AuditStep("Surcharge", "Finance Act - Surcharge & Marginal Relief", surcharge,
                                   tax_after_rebate + surcharge,
                                   f"Surcharge: ₹{surcharge:,.2f} (Relief applied: ₹{marginal_relief_surcharge:,.2f})"))

        # 8. Health and Education Cess: 4%
        cess = (tax_after_rebate + surcharge) * 0.04
        steps.append(AuditStep("Health & Education Cess", "Finance Act - Cess (4%)", cess,
                               tax_after_rebate + surcharge + cess,
                               f"4% Health and Education Cess on ₹{tax_after_rebate + surcharge:,.2f} = ₹{cess:,.2f}"))

        # 9. Total Tax Payable rounded to nearest 10 (Sec 288B)
        total_payable = int(round((tax_after_rebate + surcharge + cess) / 10.0) * 10)
        steps.append(AuditStep("Final Tax Payable", "Sec 288B", total_payable, total_payable,
                               f"Total tax payable rounded to nearest ₹10 per Sec 288B: ₹{total_payable:,}"))

        return TaxBreakdown(
            regime=TaxRegime.OLD,
            financial_year=self.fy,
            gross_salary=gross,
            standard_deduction=std_ded,
            hra_exemption=hra_exemp,
            sec_24b_loss=hp_loss,
            chapter_vi_a=total_vi_a,
            total_deductions=std_ded + hra_exemp + hp_loss + total_vi_a,
            taxable_income=taxable_income,
            base_tax=base_tax,
            rebate_87a=rebate_87a,
            tax_after_rebate=tax_after_rebate,
            surcharge=surcharge,
            marginal_relief_surcharge=marginal_relief_surcharge,
            cess=cess,
            total_tax_payable=total_payable,
            audit_trail=steps
        )

    def compute_new_regime(self, taxpayer: TaxpayerInput) -> TaxBreakdown:
        steps = []
        gross = taxpayer.gross_salary

        if self.fy == FinancialYear.FY2024_25:
            # FY 2024-25 (Finance (No. 2) Act 2024):
            # Standard deduction: ₹75,000
            std_ded = min(gross, 75000.0)
            steps.append(AuditStep("Standard Deduction", "Sec 16(ia) read with Sec 115BAC", std_ded, gross - std_ded,
                                   f"Standard deduction under New Regime (FY 2024-25): ₹{std_ded:,.2f}"))

            raw_taxable = max(0.0, gross - std_ded)
            taxable_income = round(raw_taxable / 10.0) * 10.0

            # Slabs FY 2024-25:
            # 0 - 3,00,000: Nil
            # 3,00,001 - 7,00,000: 5% (max 20,000)
            # 7,00,001 - 10,00,000: 10% (max 30,000)
            # 10,00,001 - 12,00,000: 15% (max 30,000)
            # 12,00,001 - 15,00,000: 20% (max 60,000)
            # Above 15,00,000: 30%
            base_tax = 0.0
            if taxable_income <= 300000:
                base_tax = 0.0
            elif taxable_income <= 700000:
                base_tax = (taxable_income - 300000) * 0.05
            elif taxable_income <= 1000000:
                base_tax = 20000.0 + (taxable_income - 700000) * 0.10
            elif taxable_income <= 1200000:
                base_tax = 50000.0 + (taxable_income - 1000000) * 0.15
            elif taxable_income <= 1500000:
                base_tax = 80000.0 + (taxable_income - 1200000) * 0.20
            else:
                base_tax = 140000.0 + (taxable_income - 1500000) * 0.30

            steps.append(AuditStep("Base Tax Calculation", "Sec 115BAC(1A)", base_tax, base_tax,
                                   f"Tax calculated on taxable income ₹{taxable_income:,.2f} per FY 2024-25 new slabs"))

            # Section 87A Rebate & Marginal Relief (FY 2024-25)
            # Threshold: ₹7,00,000
            rebate_87a = 0.0
            if taxable_income <= 700000:
                rebate_87a = base_tax
                steps.append(AuditStep("Section 87A Rebate", "Sec 87A (New Regime)", rebate_87a, 0.0,
                                       f"Taxable income <= ₹7,00,000. Full rebate of ₹{rebate_87a:,.2f} granted. Tax is ₹0."))
            else:
                # Proviso to Sec 87A: Tax payable cannot exceed excess income over ₹7,00,000
                excess_income = taxable_income - 700000.0
                if base_tax > excess_income:
                    rebate_87a = base_tax - excess_income
                    steps.append(AuditStep("Section 87A Marginal Relief", "Proviso to Sec 87A", rebate_87a, excess_income,
                                           f"Marginal relief applied: tax payable capped at excess income over ₹7,00,000 (₹{excess_income:,.2f}). Rebate: ₹{rebate_87a:,.2f}"))

            tax_after_rebate = base_tax - rebate_87a

        else:
            # FY 2025-26 (Finance Act 2025 Budget changes):
            # Standard deduction: ₹75,000
            std_ded = min(gross, 75000.0)
            steps.append(AuditStep("Standard Deduction", "Sec 16(ia) read with Sec 115BAC", std_ded, gross - std_ded,
                                   f"Standard deduction under New Regime (FY 2025-26): ₹{std_ded:,.2f}"))

            raw_taxable = max(0.0, gross - std_ded)
            taxable_income = round(raw_taxable / 10.0) * 10.0

            # Slabs FY 2025-26:
            # 0 - 4,00,000: Nil
            # 4,00,001 - 8,00,000: 5% (max 20,000)
            # 8,00,001 - 12,00,000: 10% (max 40,000)
            # 12,00,001 - 16,00,000: 15% (max 60,000)
            # 16,00,001 - 20,00,000: 20% (max 80,000)
            # 20,00,001 - 24,00,000: 25% (max 100,000)
            # Above 24,00,000: 30%
            base_tax = 0.0
            if taxable_income <= 400000:
                base_tax = 0.0
            elif taxable_income <= 800000:
                base_tax = (taxable_income - 400000) * 0.05
            elif taxable_income <= 1200000:
                base_tax = 20000.0 + (taxable_income - 800000) * 0.10
            elif taxable_income <= 1600000:
                base_tax = 60000.0 + (taxable_income - 1200000) * 0.15
            elif taxable_income <= 2000000:
                base_tax = 120000.0 + (taxable_income - 1600000) * 0.20
            elif taxable_income <= 2400000:
                base_tax = 200000.0 + (taxable_income - 2000000) * 0.25
            else:
                base_tax = 300000.0 + (taxable_income - 2400000) * 0.30

            steps.append(AuditStep("Base Tax Calculation", "Sec 115BAC (Finance Act 2025)", base_tax, base_tax,
                                   f"Tax calculated on taxable income ₹{taxable_income:,.2f} per FY 2025-26 new slabs"))

            # Section 87A Rebate & Marginal Relief (FY 2025-26)
            # Threshold: ₹12,00,000 (Tax on 12L is 60,000)
            rebate_87a = 0.0
            if taxable_income <= 1200000:
                rebate_87a = base_tax
                steps.append(AuditStep("Section 87A Rebate", "Sec 87A (Finance Act 2025)", rebate_87a, 0.0,
                                       f"Taxable income <= ₹12,00,000. Full rebate of ₹{rebate_87a:,.2f} granted. Tax is ₹0."))
            else:
                excess_income = taxable_income - 1200000.0
                if base_tax > excess_income:
                    rebate_87a = base_tax - excess_income
                    steps.append(AuditStep("Section 87A Marginal Relief", "Proviso to Sec 87A (Finance Act 2025)", rebate_87a, excess_income,
                                           f"Marginal relief applied: tax payable capped at excess income over ₹12,00,000 (₹{excess_income:,.2f}). Rebate: ₹{rebate_87a:,.2f}"))

            tax_after_rebate = base_tax - rebate_87a

        # Surcharge (New Regime: capped at 25% for > 2 Cr)
        surcharge = 0.0
        marginal_relief_surcharge = 0.0
        if tax_after_rebate > 0:
            if taxable_income > 20000000:  # > 2 Cr: 25% (highest rate capped at 25% under 115BAC)
                nominal_surch = tax_after_rebate * 0.25
                # Marginal relief at 2 Cr
                if self.fy == FinancialYear.FY2024_25:
                    tax_at_2cr = 140000.0 + (20000000 - 1500000) * 0.30
                else:
                    tax_at_2cr = 300000.0 + (20000000 - 2400000) * 0.25  # or per FY2526 slab
                surch_at_2cr = tax_at_2cr * 0.15
                max_allowed = tax_at_2cr + surch_at_2cr + (taxable_income - 20000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch
            elif taxable_income > 10000000:  # > 1 Cr: 15%
                nominal_surch = tax_after_rebate * 0.15
                if self.fy == FinancialYear.FY2024_25:
                    tax_at_1cr = 140000.0 + (10000000 - 1500000) * 0.30
                else:
                    tax_at_1cr = 60000.0 + (10000000 - 1200000) * 0.15
                surch_at_1cr = tax_at_1cr * 0.10
                max_allowed = tax_at_1cr + surch_at_1cr + (taxable_income - 10000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch
            elif taxable_income > 5000000:  # > 50 L: 10%
                nominal_surch = tax_after_rebate * 0.10
                if self.fy == FinancialYear.FY2024_25:
                    tax_at_50l = 140000.0 + (5000000 - 1500000) * 0.30
                else:
                    tax_at_50l = 60000.0 + (5000000 - 1200000) * 0.15
                max_allowed = tax_at_50l + (taxable_income - 5000000)
                if (tax_after_rebate + nominal_surch) > max_allowed:
                    surcharge = max(0.0, max_allowed - tax_after_rebate)
                    marginal_relief_surcharge = nominal_surch - surcharge
                else:
                    surcharge = nominal_surch

        if surcharge > 0 or marginal_relief_surcharge > 0:
            steps.append(AuditStep("Surcharge", "Sec 115BAC Surcharge & Relief", surcharge,
                                   tax_after_rebate + surcharge,
                                   f"Surcharge: ₹{surcharge:,.2f} (Relief applied: ₹{marginal_relief_surcharge:,.2f})"))

        # Health & Education Cess (4%)
        cess = (tax_after_rebate + surcharge) * 0.04
        steps.append(AuditStep("Health & Education Cess", "Finance Act - Cess (4%)", cess,
                               tax_after_rebate + surcharge + cess,
                               f"4% Cess on ₹{tax_after_rebate + surcharge:,.2f} = ₹{cess:,.2f}"))

        # Total tax payable rounded to nearest 10 (Sec 288B)
        total_payable = int(round((tax_after_rebate + surcharge + cess) / 10.0) * 10)
        steps.append(AuditStep("Final Tax Payable", "Sec 288B", total_payable, total_payable,
                               f"Total tax payable rounded to nearest ₹10 per Sec 288B: ₹{total_payable:,}"))

        return TaxBreakdown(
            regime=TaxRegime.NEW,
            financial_year=self.fy,
            gross_salary=gross,
            standard_deduction=std_ded,
            hra_exemption=0.0,
            sec_24b_loss=0.0,
            chapter_vi_a=0.0,
            total_deductions=std_ded,
            taxable_income=taxable_income,
            base_tax=base_tax,
            rebate_87a=rebate_87a,
            tax_after_rebate=tax_after_rebate,
            surcharge=surcharge,
            marginal_relief_surcharge=marginal_relief_surcharge,
            cess=cess,
            total_tax_payable=total_payable,
            audit_trail=steps
        )

    def compare_regimes(self, taxpayer: TaxpayerInput) -> RegimeComparison:
        old_brk = self.compute_old_regime(taxpayer)
        new_brk = self.compute_new_regime(taxpayer)

        diff = old_brk.total_tax_payable - new_brk.total_tax_payable
        if diff > 0:
            rec = TaxRegime.NEW
            reason = (f"The New Tax Regime saves you ₹{diff:,} in taxes. "
                      f"(New Regime Tax: ₹{new_brk.total_tax_payable:,} vs Old Regime Tax: ₹{old_brk.total_tax_payable:,}). "
                      f"Even after all your deductions under Old Regime (₹{old_brk.total_deductions:,.0f}), "
                      f"the lower slab rates and higher rebate under Section 115BAC result in a lower net liability.")
        elif diff < 0:
            rec = TaxRegime.OLD
            saved = abs(diff)
            reason = (f"The Old Tax Regime saves you ₹{saved:,} in taxes. "
                      f"(Old Regime Tax: ₹{old_brk.total_tax_payable:,} vs New Regime Tax: ₹{new_brk.total_tax_payable:,}). "
                      f"Your deductions (Standard Deduction ₹{old_brk.standard_deduction:,.0f}, HRA ₹{old_brk.hra_exemption:,.0f}, "
                      f"Sec 24(b) ₹{old_brk.sec_24b_loss:,.0f}, Chapter VI-A ₹{old_brk.chapter_vi_a:,.0f} = Total ₹{old_brk.total_deductions:,.0f}) "
                      f"substantially reduce your taxable base below the New Regime effective rate.")
        else:
            rec = TaxRegime.NEW
            reason = (f"Both regimes yield the exact same tax liability of ₹{new_brk.total_tax_payable:,}. "
                      f"The New Tax Regime is recommended due to simpler compliance and zero paperwork for deductions.")

        return RegimeComparison(
            taxpayer_input=taxpayer,
            old_regime=old_brk,
            new_regime=new_brk,
            recommended_regime=rec,
            tax_difference=diff,
            recommendation_reason=reason
        )
