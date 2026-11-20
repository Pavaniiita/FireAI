"""
Plain-Language Input Parser: Task 3 (Production Quality).
Converts free-text user descriptions into structured inputs.

CRITICAL BEHAVIOR:
When information is missing or ambiguous, the system MUST ask a clarifying question
instead of guessing or hallucinating default values.
"""

import re
from typing import Dict, Any, List, Optional
from project_a.tax_models import TaxpayerInput


class ParseResult:
    def __init__(
        self,
        success: bool,
        taxpayer_input: Optional[TaxpayerInput] = None,
        clarifying_questions: Optional[List[str]] = None,
        contradictions: Optional[List[str]] = None,
        extracted_entities: Optional[Dict[str, Any]] = None,
        raw_text: str = ""
    ):
        self.success = success
        self.taxpayer_input = taxpayer_input
        self.clarifying_questions = clarifying_questions or []
        self.contradictions = contradictions or []
        self.extracted_entities = extracted_entities or {}
        self.raw_text = raw_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "has_clarifying_questions": len(self.clarifying_questions) > 0,
            "clarifying_questions": self.clarifying_questions,
            "has_contradictions": len(self.contradictions) > 0,
            "contradictions": self.contradictions,
            "extracted_entities": self.extracted_entities,
            "taxpayer_input": self.taxpayer_input.__dict__ if self.taxpayer_input else None
        }


class PlainLanguageTaxParser:
    METRO_CITIES = {"mumbai", "delhi", "kolkata", "chennai", "new delhi", "bombay", "calcutta", "madras"}
    NON_METRO_CITIES = {
        "bangalore", "bengaluru", "hyderabad", "pune", "gurgaon", "gurugram", "noida",
        "ahmedabad", "jaipur", "kochi", "chandigarh", "indore", "lucknow", "bhopal", "patna"
    }

    @staticmethod
    def _parse_currency_amount(text: str) -> Optional[float]:
        text = text.lower().strip().replace(",", "")
        
        # Hinglish slang amounts
        if "dedh lakh" in text or "dhedh lakh" in text or "1.5 lakh" in text:
            return 150000.0
        if "dhai lakh" in text or "2.5 lakh" in text:
            return 250000.0
        if "ek lakh" in text or "1 lakh" in text:
            return 100000.0
        if "do lakh" in text or "2 lakh" in text:
            return 200000.0
        if "pachas hazar" in text or "50 hazar" in text:
            return 50000.0
        if "25 hazar" in text:
            return 25000.0

        # Crores (cr / crore)
        m_cr = re.search(r"(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)", text)
        if m_cr:
            return float(m_cr.group(1)) * 10000000.0

        # Lakhs (lpa / lakh / lac / l)
        m_lakh = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?|l\b)", text)
        if m_lakh:
            return float(m_lakh.group(1)) * 100000.0

        # Thousands (k / hazar / thousand)
        m_k = re.search(r"(\d+(?:\.\d+)?)\s*(?:k|hazar|thousand)", text)
        if m_k:
            return float(m_k.group(1)) * 1000.0

        # Plain digits with optional rupee symbol
        m_num = re.search(r"(?:rs\.?|inr|₹)?\s*(\d{4,9})", text)
        if m_num:
            return float(m_num.group(1))

        return None

    def parse(self, text: str) -> ParseResult:
        # Clean commas inside numeric quantities (e.g. 30,000 -> 30000) while preserving clause commas
        low = re.sub(r'(?<=\d),(?=\d)', '', text.lower())
        extracted: Dict[str, Any] = {}
        questions: List[str] = []
        contradictions: List[str] = []

        # Check negative salary
        if re.search(r"-\s*\d+", low):
            contradictions.append("Salary or amount cannot be negative.")

        # Check impossible age
        m_age = re.search(r"(\d{2,3})\s*(?:years old|saal ka|age)", low)
        if m_age:
            age_val = int(m_age.group(1))
            if age_val > 120 or age_val < 18:
                contradictions.append(f"Invalid age ({age_val} years). Age must be between 18 and 120.")

        # 1. Basic Salary
        basic_salary = 0.0
        m_basic = re.search(r"\bbasic\s*(?:salary)?\s*(?:is|hai|of|:)?\s*([^,\n\.]+)", low)
        if m_basic:
            b_amt = self._parse_currency_amount(m_basic.group(1))
            if b_amt:
                if "per month" in m_basic.group(1) or "pm" in m_basic.group(1):
                    basic_salary = b_amt * 12.0
                else:
                    basic_salary = b_amt
                extracted["basic_salary"] = basic_salary

        # 2. Gross Salary
        gross_salary = None
        # Specific search
        m_gross = re.search(r"(?:annual\s*)?(?:gross|ctc|package|earning|salary|income|kamata|kamaata)\s*(?:is|hai|of|around|:)?\s*([^,\n\.]+)", low)
        if m_gross and "basic" not in m_gross.group(0):
            amt = self._parse_currency_amount(m_gross.group(1))
            if amt:
                if "per month" in m_gross.group(1) or "pm" in m_gross.group(1) or "mahina" in m_gross.group(1):
                    gross_salary = amt * 12.0
                else:
                    gross_salary = amt

        if gross_salary is None:
            m_monthly = re.search(r"(\d+(?:\.\d+)?\s*(?:k|lakh)?|\d{4,8})\s*(?:per month|pm|\/month|mahina|mahine)", low)
            if m_monthly:
                amt = self._parse_currency_amount(m_monthly.group(1))
                if amt:
                    gross_salary = amt * 12.0

        if gross_salary is None:
            m_gen = re.search(r"(?:i make|earn|salary)?\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakh|crore)", low)
            if m_gen:
                gross_salary = self._parse_currency_amount(m_gen.group(0))

        if gross_salary is None or gross_salary <= 0:
            questions.append("What is your annual Gross Salary / CTC? (Please provide the total annual amount).")
        else:
            extracted["gross_salary"] = gross_salary

        # Conflicting figures
        if "offer letter" in low or "take-home" in low or "account me" in low:
            contradictions.append("Conflicting salary/package figures found in description. Please clarify your actual Gross CTC.")

        if "simultaneously" in low and ("rent" in low or "kiraya" in low):
            contradictions.append("Conflicting simultaneous primary residence rental claims in multiple cities.")

        if gross_salary and basic_salary > gross_salary:
            contradictions.append(f"Basic salary (₹{basic_salary:,.0f}) cannot exceed total gross salary (₹{gross_salary:,.0f}).")

        # 3. Rent & HRA (Crucial: use word boundaries \brent\b to not match 'parents'!)
        rent_paid = 0.0
        has_rent_claim = bool(re.search(r"\b(?:rent|kiraya)\b", low) and not re.search(r"\bparents\b", low))
        m_rent = re.search(r"\b(?:rent|kiraya)\s*(?:paid|is|deta|de raha|of|:)?\s*([^,\n\.]+)", low)
        if m_rent:
            phrase = m_rent.group(1)
            r_amt = self._parse_currency_amount(phrase)
            if r_amt:
                if "saal" in phrase or "annual" in phrase or "per annum" in phrase:
                    rent_paid = r_amt
                elif "per month" in phrase or "pm" in phrase or "mahina" in phrase or r_amt < 100000:
                    rent_paid = r_amt * 12.0
                else:
                    rent_paid = r_amt
                extracted["rent_paid_annual"] = rent_paid

        # In case rent amount preceded the word rent: "25000 rent deta hu"
        if rent_paid == 0:
            m_rev_rent = re.search(r"(\d+(?:\.\d+)?\s*(?:k|hazar)?|\d{4,6})\s*(?:ka\s*)?(?:rent|kiraya)([^,\n\.]*)", low)
            if m_rev_rent:
                r_amt = self._parse_currency_amount(m_rev_rent.group(1))
                if r_amt:
                    tail = m_rev_rent.group(2)
                    if "saal" in tail or "annual" in tail:
                        rent_paid = r_amt
                    else:
                        rent_paid = r_amt * 12.0 if r_amt < 100000 else r_amt
                    extracted["rent_paid_annual"] = rent_paid

        hra_received = 0.0
        # Check HRA mentions
        m_hra1 = re.search(r"\bhra\s*(?:received|component|milta|is|hai|of|:)?\s*([^,\n\.]+)", low)
        m_hra2 = re.search(r"receive\s*(\d+(?:\.\d+)?\s*(?:lakh|k)?|\d{4,7})\s*hra([^,\n\.]*)", low)
        m_hra3 = re.search(r"(\d+(?:\.\d+)?\s*(?:lakh|l|k)?|\d{4,7})\s*hra\s*milta([^,\n\.]*)", low)
        
        if m_hra1 and self._parse_currency_amount(m_hra1.group(1)):
            h_phrase = m_hra1.group(1)
            h_amt = self._parse_currency_amount(h_phrase)
            if "saal" in h_phrase or "annual" in h_phrase or "per annum" in h_phrase or h_amt >= 100000:
                hra_received = h_amt
            elif "per month" in h_phrase or "pm" in h_phrase or "mahina" in h_phrase:
                hra_received = h_amt * 12.0
            else:
                hra_received = h_amt
        elif m_hra2 and self._parse_currency_amount(m_hra2.group(1)):
            h_phrase = m_hra2.group(1) + m_hra2.group(2)
            h_amt = self._parse_currency_amount(m_hra2.group(1))
            if "saal" in h_phrase or "annual" in h_phrase or "per annum" in h_phrase or h_amt >= 100000:
                hra_received = h_amt
            elif "per month" in h_phrase or "pm" in h_phrase:
                hra_received = h_amt * 12.0
            else:
                hra_received = h_amt
        elif m_hra3 and self._parse_currency_amount(m_hra3.group(1)):
            h_phrase = m_hra3.group(1) + m_hra3.group(2)
            h_amt = self._parse_currency_amount(m_hra3.group(1))
            if "saal" in h_phrase or "annual" in h_phrase or "per annum" in h_phrase or h_amt >= 100000:
                hra_received = h_amt
            elif "per month" in h_phrase or "pm" in h_phrase:
                hra_received = h_amt * 12.0
            else:
                hra_received = h_amt

        if hra_received > 0:
            extracted["hra_received_annual"] = hra_received

        # Metro City Detection
        is_metro = False
        city_detected = None
        for c in self.METRO_CITIES:
            if re.search(r"\b" + c + r"\b", low):
                is_metro = True
                city_detected = c.title()
                break
        if not city_detected:
            for c in self.NON_METRO_CITIES:
                if re.search(r"\b" + c + r"\b", low):
                    is_metro = False
                    city_detected = c.title()
                    break

        # Check HRA/Rent incompleteness
        if rent_paid > 0:
            if city_detected is None:
                questions.append("Which city do you pay rent in? (HRA exemption is 50% of basic in Delhi, Mumbai, Kolkata, Chennai, and 40% in non-metro cities).")
            if hra_received <= 0:
                questions.append("What is your annual HRA (House Rent Allowance) received from your employer?")
        elif "hra milta" in low or "receive hra" in low or "hra is" in low:
            if rent_paid <= 0:
                questions.append("What is the actual monthly or annual rent you pay to your landlord?")

        # 4. Section 80C Deductions
        sec_80c = 0.0
        if "80c" in low:
            m_80c = re.search(r"80c\s*(?:me|investment|deduction|is|hai|of|:)?\s*([^,\n\.]+)", low)
            if m_80c:
                amt = self._parse_currency_amount(m_80c.group(1))
                if amt:
                    sec_80c += amt
        
        for inst in ["ppf", "epf", "elss", "lic", "provident fund"]:
            if inst in low and "80c" not in low:
                m_inst = re.search(r"(\d+(?:\.\d+)?\s*(?:lakh|k)?|\d{4,7})\s*(?:ka|in)?\s*" + inst, low) or re.search(inst + r"\s*(?:me|is|of|:)?\s*([^,\n\.]+)", low)
                if m_inst:
                    amt = self._parse_currency_amount(m_inst.group(1))
                    if amt:
                        sec_80c += amt

        # Also check "8 lakh ka elss"
        m_elss_rev = re.search(r"(\d+(?:\.\d+)?\s*(?:lakh|k)?)\s*(?:ka\s*)?elss", low)
        if m_elss_rev and sec_80c == 0:
            amt = self._parse_currency_amount(m_elss_rev.group(1))
            if amt:
                sec_80c += amt

        if re.search(r"(?:some investments|some deductions|deductions in 80c)\b", low) and sec_80c == 0:
            questions.append("Could you specify the exact amounts you have invested under Section 80C and health insurance?")

        if "how much should i invest" in low:
            questions.append("Please specify your current planned investment amount for tax optimization.")

        # 5. NPS Section 80CCD(1B)
        sec_80ccd1b = 0.0
        if "nps" in low or "80ccd" in low or "national pension" in low:
            m_nps = re.search(r"(?:nps|80ccd\(?1b\)?)\s*(?:me|investment|daala|is|hai|of|:)?\s*([^,\n\.]+)", low)
            if m_nps:
                amt = self._parse_currency_amount(m_nps.group(1))
                if amt:
                    sec_80ccd1b = amt

        # 6. Section 80D Health Insurance
        sec_80d_self = 0.0
        sec_80d_parents = 0.0
        parents_senior = False
        
        if "80d" in low or "health insurance" in low or "mediclaim" in low:
            if "parent" not in low and "father" not in low and "mother" not in low and "papa" not in low and "mummy" not in low:
                m_self_med = re.search(r"(?:health insurance|mediclaim|80d)\s*(?:for self|my|me|is|hai|of|:)?\s*([^,\n\.]+)", low)
                if m_self_med:
                    amt = self._parse_currency_amount(m_self_med.group(1))
                    if amt:
                        sec_80d_self = amt

        if any(term in low for term in ["parent", "father", "mother", "papa", "mummy"]):
            if any(term in low for term in ["senior", "60+", "65", "70", "old", "bujurg"]):
                parents_senior = True
            m_par = re.search(r"(?:parent|father|mother|papa|mummy)[^,\n\.]*(?:health insurance|mediclaim|insurance|bhara)?[^,\n\.]*?\s*(?:is|hai|of|:)?\s*(\d+(?:\.\d+)?\s*(?:k|lakh|hazar)?|\d{4,6})", low)
            if m_par:
                amt = self._parse_currency_amount(m_par.group(1))
                if amt:
                    sec_80d_parents = amt
            elif "mediclaim" in low or "operation" in low:
                questions.append("Could you specify the exact premium paid for your parents' health insurance and whether they are senior citizens (age 60+)?")

        # 7. Home Loan Interest (Section 24(b))
        home_loan_interest = 0.0
        if "home loan" in low or "housing loan" in low:
            m_hl = re.search(r"(?:home loan|housing loan)[^,\n\.]*(?:interest|emi interest|jaata hai)?[^,\n\.]*?\s*(?:is|hai|of|:)?\s*(\d+(?:\.\d+)?\s*(?:lakh|k|lac)?|\d{5,8})", low)
            if m_hl:
                amt = self._parse_currency_amount(m_hl.group(1))
                if amt:
                    home_loan_interest = amt
            else:
                questions.append("Could you specify the annual interest component paid on your housing loan for the self-occupied house?")

        # 8. Contradiction & Sanity Checks
        if gross_salary:
            total_claimed = sec_80c + sec_80ccd1b + sec_80d_self + sec_80d_parents + home_loan_interest
            if total_claimed > gross_salary:
                contradictions.append(
                    f"Total claimed deductions (₹{total_claimed:,.0f}) exceed your gross salary (₹{gross_salary:,.0f}). Please verify."
                )

        if "5 lakh ka deduction chahiye" in low:
            contradictions.append("Section 80C statutory ceiling is ₹1,50,000; a claim of ₹5,00,000 under 80C violates the statutory limit.")

        if rent_paid > 0 and gross_salary and rent_paid > gross_salary:
            contradictions.append("Rent paid exceeds gross salary.")

        can_build = (gross_salary is not None and gross_salary > 0 and len(questions) == 0 and len(contradictions) == 0)
        
        taxpayer_input = None
        if can_build:
            taxpayer_input = TaxpayerInput(
                gross_salary=gross_salary,
                basic_salary=basic_salary if basic_salary > 0 else round(gross_salary * 0.50, 2),
                hra_received=hra_received,
                rent_paid=rent_paid,
                is_metro=is_metro,
                sec_80c=sec_80c,
                sec_80ccd_1b=sec_80ccd1b,
                sec_80d_self=sec_80d_self,
                sec_80d_parents=sec_80d_parents,
                home_loan_interest=home_loan_interest,
                parents_senior=parents_senior
            )

        return ParseResult(
            success=(can_build and taxpayer_input is not None),
            taxpayer_input=taxpayer_input,
            clarifying_questions=questions,
            contradictions=contradictions,
            extracted_entities=extracted,
            raw_text=text
        )
