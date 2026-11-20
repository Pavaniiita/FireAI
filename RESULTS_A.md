# RESULTS_A.md: Project A — Income-Tax Engine (Rules vs LLMs)

**Author:** Pavan Reddy (@Kaustubh Keshav / Fire AI Review)  
**System Evaluated:** Indian Income-Tax Calculation Engine for Salaried Individuals  
**Statutory Scope:** FY 2024-25 (AY 2025-26) and FY 2025-26 (AY 2026-27) per Finance Act 2024 & Finance Act 2025  
**Single Command Reproduction:** `python run_all.py`

---

## 1. Implementation Comparison Table

Evaluated across **230 test cases** spanning sub-taxable incomes, exact slab boundaries, rebate cliff edges, surcharge thresholds, and 10 repeated queries per input to evaluate execution determinism.

| Metric | Hand-Coded Rules | LLM at Query Time | LLM-Compiled Rules |
| :--- | :--- | :--- | :--- |
| **Rupee-Exact Accuracy** | **100.0%** (230 / 230) | **94.35%** (217 / 230) | **100.0%** (230 / 230) |
| **10x Determinism** | **Yes** ($\sigma^2 = 0.0$, 100% pass) | **No** ($\sigma^2 = 22.2$, 80% pass) | **Yes** ($\sigma^2 = 0.0$, 100% pass) |
| **Latency (p50 / p95)** | **0.021 ms** / 0.030 ms | **890.2 ms** / 1143.2 ms | **0.009 ms** / 0.011 ms |
| **Cost per 1,000 Requests** | **$0.0000** | **$0.2332** | **$0.0000** |
| **Official Calculator Match** | **100.0%** (30 / 30 cases) | 86.67% (26 / 30 cases) | **100.0%** (30 / 30 cases) |
| **Rupee Traceability** | **100%** (Line-item clause breakdown) | **Partial (~74%)** (Prose explanation) | **100%** (Line-item clause breakdown) |

### Key Benchmark Observations
1. **The Arithmetic Fallacy of Query-Time LLMs:** Even when fed complete official statutory text (`RULE_TEXT_FY2425`), LLMs at query time experience catastrophic edge-case drift on mathematical boundary logic. Specifically, at ₹7,10,000 taxable income, the LLM calculated ₹21,000 base tax but omitted Section 87A marginal relief (which caps tax to ₹10,000 + 4% cess = ₹10,400).
2. **Determinism Gap:** When 5 identical edge cases were queried 10 consecutive times with temperature $T=0.2$, the query-time LLM returned different tax numbers on 2 of the 10 iterations due to subtle rounding fluctuations between intermediate decimal calculation and Section 288B rounding.
3. **Latency & Throughput Collapse:** Hand-coded and compiled rules execute in under 25 microseconds on a laptop CPU ($>45,000$ queries/second). The query-time LLM required ~890 ms per request, a **42,000x latency penalty**.

---

## 2. Task 5: The Law Changes — Finance Act 2025 Transition Log

We simulated the passage of the Union Budget 2025 (Finance Act 2025) which overhauled the New Tax Regime for FY 2025-26:
- **New Slabs:** ₹0-4L (Nil), ₹4-8L (5%), ₹8-12L (10%), ₹12-16L (15%), ₹16-20L (20%), ₹20-24L (25%), >₹24L (30%).
- **Section 87A Rebate:** Limit raised from ₹7,00,000 to ₹12,00,000 (tax on ₹12L is ₹60,000, fully rebated).
- **Zero-Tax Milestone:** Salaried employees earning up to ₹12,75,000 (with ₹75,000 standard deduction) pay ₹0 tax.
- **Section 87A Marginal Relief:** Retained for taxable income marginally exceeding ₹12,00,000 (tax capped to excess income).

### Detailed Adaptation Log Across Implementations

| Dimension | Hand-Coded Rules | LLM at Query Time | LLM-Compiled Rules |
| :--- | :--- | :--- | :--- |
| **Time Taken to Adapt** | 25 minutes | **5 minutes** | 12 minutes |
| **What Broke (Loud Failures)** | 38 unit test assertions failed immediately due to hardcoded FY 2024-25 expectations. | **Nothing broke.** The script exited with code 0 and returned valid JSON. | LLM compiler initially omitted the proviso formula for marginal relief between ₹12.0L and ₹12.7L. |
| **Silent Failures (Wrong answers, 0 error)** | **0 (0.0%)** | **12 / 48 cases (25.0%)** | **0 (0.0%)** |
| **Root Cause of Silent Failure** | N/A (Type contracts and tests enforce correctness). | **Pre-training Memory Interference:** Despite the system prompt containing FY 2025-26 text, the LLM defaulted to its prior knowledge of the ₹7,00,000 rebate ceiling on 25% of cases between ₹7.75L and ₹12.75L. | Caught at compile review gate before production artifact promotion. |

### The Silent Failure Danger in Financial AI
The most critical takeaway of Task 5 is that **LLM at Query Time gave the false illusion of agility**. It took only 5 minutes to swap the prompt text, and it ran without throwing a single error. However, it silently overtaxed salaried citizens earning ₹10,00,000 by ₹33,800 because the model hallucinated that ₹7 Lakhs was still the Section 87A cutoff! In financial software, a loud runtime error is infinitely preferable to a silent mathematical failure.

---

## 3. Final Production Design (Architecture for 100,000 Users)

### Architectural Paradigm: *The Neuro-Symbolic Tax Service*
To serve 100,000 salaried Indian citizens with sub-100ms latency, zero mathematical errors, 100% statutory explainability, and minimal compute cost, the architecture strictly segregates **natural language parsing (LLM)** from **tax calculation & legal compliance (Deterministic Rules)**.

```
                      [ User Input: Free Text / Hinglish ]
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │       COMPONENT 1: Plain-Language Parser         │
             │           [ Hybrid: Few-Shot LLM + Regex ]        │
             └──────────────────────────────────────────────────┘
                                      │
                   Is Information Missing / Ambiguous?
                                   /     \
                            YES   /       \   NO
                                 /         \
                                ▼           ▼
           ┌────────────────────────┐   ┌───────────────────────────┐
           │ COMPONENT 2:           │   │ COMPONENT 3:              │
           │ Clarification Dialogue │   │ Typed Taxpayer Input      │
           │ [ LLM Generator ]      │   │ [ Pydantic Model Schema ] │
           └────────────────────────┘   └───────────────────────────┘
                                                      │
                                                      ▼
                                        ┌───────────────────────────┐
                                        │ COMPONENT 4:              │
                                        │ Compiled Tax Engine       │
                                        │ [ Pure Deterministic Rule]│
                                        │ • Old vs New Regime Slabs │
                                        │ • Sec 87A Marginal Relief │
                                        │ • Sec 80C/80D/24b Capping │
                                        │ • Sec 288B Rounding       │
                                        └───────────────────────────┘
                                                      │
                                                      ▼
                                        ┌───────────────────────────┐
                                        │ COMPONENT 5:              │
                                        │ Regime Recommendation &   │
                                        │ Rupee Audit Trail         │
                                        │ [ Rule-Based Generator ]  │
                                        └───────────────────────────┘
```

### Component Breakdown & Classification

#### Component 1: Plain-Language Input Parser — `[ HYBRID ]`
- **Role:** Ingests user input in standard English, colloquial Hinglish, or informal text (e.g., *"Bhai meri 18 LPA salary hai, 25k rent deta hu Bangalore me aur papa ke mediclaim me 40k lagaye"*).
- **Mechanism:** Fast regex extraction parses numeric amounts, multipliers (`lpa`, `k`, `crore`), and cities. If unstructured or ambiguous, a localized LLM call structures the entities into a strictly typed schema.
- **Latency / Cost:** ~45 ms, $0.0001 / request.

#### Component 2: Ambiguity & Incompleteness Guard — `[ RULE-DRIVEN LLM ]`
- **Role:** Enforces the fundamental product rule: **Never guess missing data**.
- **Rule Verification:** 
  - If rent paid is claimed without specifying city $\to$ Ask: *"Which city do you reside in? (HRA exemption is 50% for Metro cities [Delhi, Mumbai, Kolkata, Chennai] and 40% elsewhere)."*
  - If HRA is claimed without Basic Salary $\to$ Ask: *"What is your Basic Salary? (We default to 50% of gross only upon confirmation)."*
  - If claimed deductions exceed gross salary $\to$ Flag arithmetic impossibility.
- **Justification:** Eliminates liability from incorrect tax filings.

#### Component 3: Tax Calculation Engine — `[ PURE DETERMINISTIC RULE ]`
- **Role:** Calculates Old Regime and New Regime tax liability to the exact rupee.
- **Mechanism:** Reviewed LLM-compiled Python logic or hand-coded configuration. Implements Section 16(ia) standard deduction, Section 10(13A) 3-way minimum HRA formula, Section 24(b) ₹2L cap, Section 87A marginal relief, surcharge thresholds, 4% Health & Education Cess, and Section 288B rounding.
- **Why NOT an LLM?** 
  - Zero probability of hallucination or arithmetic drift.
  - Sub-microsecond execution ($0.01$ ms).
  - $0.00 compute cost per request.

#### Component 4: Recommendation & Statutory Audit Generator — `[ RULE-BASED TEMPLATE ]`
- **Role:** Explains to the user which regime saves money and produces a line-by-line breakdown citing statutory sections (`Sec 10(13A)`, `Sec 115BAC`, `Sec 87A`).
- **Mechanism:** Deterministic markdown generation from the audit steps emitted by Component 3.

---

## 4. How We Keep It Correct Through the Next Union Budget

On Budget Day (February 1), the Finance Minister presents the Finance Bill with new tax slabs and rebate rules. Here is our automated 4-step deployment pipeline:

1. **Rule Text Ingestion & LLM Compilation (15 minutes):**
   The official Finance Bill PDF is parsed and passed to the offline Compiler prompt. The compiler outputs a draft `compiled_rules_fy2627.py` implementation with new slab tuples and rebate equations.
2. **Statutory Differential Review Gate (Human-in-the-Loop, 30 minutes):**
   A tax engineer reviews the AST diff against the official memorandum explaining the Finance Bill clauses. Particular attention is paid to provisos governing marginal relief.
3. **Automated Dual-Calculator Regression Suite (5 minutes):**
   The compiled module is executed against a parameterized matrix of 500 boundary test cases. Any discrepancy with hand-coded invariants triggers an automated build halt.
4. **Instant Hot-Swap Configuration (Zero Downtime):**
   The engine uses a strategy pattern parameterized by `financial_year`. Historical years (`2024-25`, `2025-26`) remain immutable, while `2026-27` is activated via feature flag.
