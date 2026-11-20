"""
Statutory Rule Text from Official Sources:
Income-tax Act, 1961, Finance Act 2024 (FY 2024-25 / AY 2025-26),
and Finance Act 2025 (FY 2025-26 / AY 2026-27).
Used by LLM Query Engine and LLM Compiled Engine.
"""

RULE_TEXT_FY2425 = """
INCOME-TAX RULES FOR SALARIED INDIVIDUALS - FY 2024-25 (AY 2025-26)
Source: Income Tax Department of India & Finance (No. 2) Act, 2024.

PART I: OLD TAX REGIME
1. Scope & Standard Deduction:
   - For a salaried individual, Standard Deduction under Section 16(ia) is ₹50,000 or the gross salary, whichever is less.
   - Professional Tax under Section 16(iii) is deductible up to actual paid (max ₹2,500).

2. House Rent Allowance (HRA) Exemption under Section 10(13A) read with Rule 2A:
   - Minimum of the following three amounts is exempt from tax:
     (a) Actual HRA received from employer.
     (b) Rent paid minus 10% of Basic Salary (+ dearness allowance, if any).
     (c) 50% of Basic Salary if accommodation is located in Mumbai, Kolkata, Delhi, or Chennai (Metro); or 40% of Basic Salary in any other city (Non-Metro).
   - If rent paid does not exceed 10% of Basic Salary, exemption is Nil.

3. Interest on Housing Loan (Self-Occupied House) under Section 24(b):
   - Deduction up to ₹2,00,000 is allowed against salary income for interest on loan for self-occupied residential house property.

4. Chapter VI-A Deductions:
   - Section 80C: Deductions for EPF, PPF, ELSS, Life Insurance premium, Principal repayment of housing loan, etc., capped at ₹1,50,000.
   - Section 80CCD(1B): Additional deduction for self-contribution to National Pension System (NPS), capped at ₹50,000.
   - Section 80D: Health insurance premium:
     * For self, spouse, and dependent children: up to ₹25,000 (up to ₹50,000 if self/spouse is a Senior Citizen aged 60+).
     * For parents: up to ₹25,000 (up to ₹50,000 if parents are Senior Citizens aged 60+).
   - Total Chapter VI-A deductions cannot exceed Gross Total Income.

5. Tax Slabs (Old Regime - Resident Individual age < 60 years):
   - Up to ₹2,50,000: Nil
   - ₹2,50,001 to ₹5,00,000: 5% of amount exceeding ₹2,50,000.
   - ₹5,00,001 to ₹10,00,000: ₹12,500 + 20% of amount exceeding ₹5,00,000.
   - Above ₹10,00,000: ₹1,12,500 + 30% of amount exceeding ₹10,00,000.

6. Rebate under Section 87A (Old Regime):
   - A resident individual whose total taxable income does not exceed ₹5,00,000 is eligible for a rebate of 100% of income-tax payable or ₹12,500, whichever is less. (Net tax becomes Nil).

7. Surcharge & Marginal Relief (Old Regime):
   - Total taxable income > ₹50,00,000 and <= ₹1,00,00,000: Surcharge at 10%.
   - Total taxable income > ₹1,00,00,000 and <= ₹2,00,00,000: Surcharge at 15%.
   - Total taxable income > ₹2,00,00,000 and <= ₹5,00,00,000: Surcharge at 25%.
   - Total taxable income > ₹5,00,00,000: Surcharge at 37%.
   - Marginal Relief on Surcharge: Total tax + surcharge shall not exceed tax on the threshold + excess income over the threshold.

8. Health and Education Cess:
   - 4% on the aggregate of income-tax and surcharge.

9. Rounding Off:
   - Taxable income rounded to nearest ₹10 (Section 288A).
   - Total tax payable rounded to nearest ₹10 (Section 288B).

---
PART II: NEW TAX REGIME (Section 115BAC)
1. Deductions Allowed:
   - Standard Deduction under Section 16(ia): ₹75,000 (as amended by Finance (No. 2) Act, 2024).
   - Employer contribution to NPS under Section 80CCD(2).
   - No HRA exemption, no Section 24(b) loss on self-occupied house, no 80C, no 80D, no 80CCD(1B).

2. Tax Slabs (FY 2024-25 as amended):
   - Up to ₹3,00,000: Nil
   - ₹3,00,001 to ₹7,00,000: 5%
   - ₹7,00,001 to ₹10,00,000: 10%
   - ₹10,00,001 to ₹12,00,000: 15%
   - ₹12,00,001 to ₹15,00,000: 20%
   - Above ₹15,00,000: 30%

3. Rebate under Section 87A (New Regime):
   - Total taxable income does not exceed ₹7,00,000: Full rebate of income-tax payable (up to ₹25,000). Tax is Nil.
   - Marginal Relief under Proviso to Section 87A:
     Where total taxable income exceeds ₹7,00,000, tax payable shall not exceed the amount by which total taxable income exceeds ₹7,00,000.

4. Surcharge (New Regime):
   - > ₹50,00,000 to ₹1,00,00,000: 10%
   - > ₹1,00,00,000 to ₹2,00,00,000: 15%
   - > ₹2,00,00,000: 25% (highest rate capped at 25% under Section 115BAC).
   - Marginal relief applies at each threshold.

5. Health & Education Cess:
   - 4% on aggregate of tax and surcharge. Total payable rounded to nearest ₹10 (Sec 288B).
"""

RULE_TEXT_FY2526 = """
INCOME-TAX RULES FOR SALARIED INDIVIDUALS - FY 2025-26 (AY 2026-27)
Source: Finance Act 2025.

PART I: OLD TAX REGIME
- Standard Deduction: ₹50,000.
- Slabs, HRA, 80C, 80D, 24(b), and surcharge remain unchanged from FY 2024-25.

PART II: NEW TAX REGIME (Section 115BAC - Revised under Finance Act 2025)
1. Standard Deduction:
   - Retained at ₹75,000 for salaried employees.

2. Revised Tax Slabs (FY 2025-26):
   - Up to ₹4,00,000: Nil
   - ₹4,00,001 to ₹8,00,000: 5%
   - ₹8,00,001 to ₹12,00,000: 10%
   - ₹12,00,001 to ₹16,00,000: 15%
   - ₹16,00,001 to ₹20,00,000: 20%
   - ₹20,00,001 to ₹24,00,000: 25%
   - Above ₹24,00,000: 30%

3. Section 87A Rebate (FY 2025-26):
   - Rebate limit increased to ₹12,00,000!
   - Taxable income up to ₹12,00,000 pays Nil tax (Rebate up to ₹60,000).
   - Marginal relief under Section 87A: Where taxable income exceeds ₹12,00,000, tax payable cannot exceed excess income over ₹12,00,000.

4. Surcharge:
   - Capped at 25% for taxable income > ₹2,00,00,000.
   - Surcharge marginal relief applies at ₹50L, ₹1Cr, and ₹2Cr thresholds.

5. Health & Education Cess:
   - 4% on aggregate of tax + surcharge. Rounded to nearest ₹10 per Section 288B.
"""
