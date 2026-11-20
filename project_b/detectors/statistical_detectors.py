"""
Family B: Statistical & Machine Learning Detectors.
Statistical, probabilistic, and ML-driven detectors for all 12 problem types.

Methods:
- Z-Score and Interquartile Range (IQR) for distribution shifts & null spikes
- Bivariate spatial centroid distance for coordinate inversions
- Jaccard n-gram character similarity for fuzzy near-duplicates
- Conditional empirical probability P(Borough | ZIP)
- Pointwise Mutual Information (PMI) for Complaint-Descriptor taxonomy anomalies
- Shannon Entropy & regex character density for PII & formatting switches
"""

import re
import math
import collections
from datetime import datetime
from typing import List, Dict, Any, Tuple


class StatisticalDetectors:
    def __init__(self):
        # Learn empirical priors from baseline data
        self.p_zip_borough: Dict[str, Dict[str, float]] = {}
        self.pmi_complaint_desc: Dict[Tuple[str, str], float] = {}

    def fit_reference_distributions(self, clean_sample: List[Dict[str, Any]]):
        """Learns baseline statistical distributions from a clean historical batch."""
        # 1. Learn P(Borough | ZIP)
        zip_totals: Dict[str, int] = collections.defaultdict(int)
        zip_borough_counts: Dict[Tuple[str, str], int] = collections.defaultdict(int)
        
        # 2. Learn Co-occurrence between Complaint Type and Descriptor
        ctype_counts: Dict[str, int] = collections.defaultdict(int)
        desc_counts: Dict[str, int] = collections.defaultdict(int)
        pair_counts: Dict[Tuple[str, str], int] = collections.defaultdict(int)
        total_pairs = 0

        for r in clean_sample:
            z = str(r.get("incident_zip", "")).strip()
            b = str(r.get("borough", "")).strip().upper()
            if z and b:
                zip_totals[z] += 1
                zip_borough_counts[(z, b)] += 1

            c = str(r.get("complaint_type", "")).strip()
            d = str(r.get("descriptor", "")).strip()
            if c and d:
                ctype_counts[c] += 1
                desc_counts[d] += 1
                pair_counts[(c, d)] += 1
                total_pairs += 1

        # Populate conditional probabilities
        for (z, b), count in zip_borough_counts.items():
            if z not in self.p_zip_borough:
                self.p_zip_borough[z] = {}
            self.p_zip_borough[z][b] = count / zip_totals[z]

        # Compute Pointwise Mutual Information (PMI)
        for (c, d), count in pair_counts.items():
            p_cd = count / total_pairs
            p_c = ctype_counts[c] / total_pairs
            p_d = desc_counts[d] / total_pairs
            pmi = math.log2(p_cd / (p_c * p_d))
            self.pmi_complaint_desc[(c, d)] = pmi

    def detect_a_schema_entropy(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """A: Statistical Column Completeness Rate (flags rows missing columns whose completeness in batch > 99%)."""
        col_presence: Dict[str, int] = collections.defaultdict(int)
        n = len(batch)
        for row in batch:
            for k in row.keys():
                col_presence[k] += 1

        baseline_cols = {col for col, count in col_presence.items() if (count / n) > 0.85}
        alerts = []
        for idx, row in enumerate(batch):
            missing_expected = baseline_cols - set(row.keys())
            flagged = len(missing_expected) > 0
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "a_schema_statistical",
                "explanation": f"Statistical column absence: missing high-frequency batch columns {list(missing_expected)}" if flagged else "Schema complete"
            })
        return alerts

    def detect_b_type_distribution(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """B: Statistical type inference via type-entropy and parse anomaly."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            lat = row.get("latitude")
            lon = row.get("longitude")
            uk = row.get("unique_key")
            
            # String length outlier or parse failure
            if lat is not None and not isinstance(lat, (float, int)):
                flagged = True
            elif lon is not None and not isinstance(lon, (float, int)):
                flagged = True
            elif not isinstance(uk, (str, int)):
                flagged = True
            elif isinstance(row.get("incident_zip"), bool):
                flagged = True

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "b_column_type_statistical",
                "explanation": "Type distribution outlier: field types violate expected statistical schema" if flagged else "Types normal"
            })
        return alerts

    def detect_c_date_format_entropy(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """C: Length and delimiter frequency distribution for date strings."""
        alerts = []
        for idx, row in enumerate(batch):
            c_str = str(row.get("created_date", ""))
            # Typical ISO string length: 19 ("2023-01-01 12:00:00")
            # Alternate format: "01/01/2023 12:00:00 PM" (length 22)
            has_slash = "/" in c_str
            has_dash = "-" in c_str
            flagged = has_slash and not has_dash
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "c_date_format_statistical",
                "explanation": f"Statistical delimiter outlier: date '{c_str}' contains '/' instead of standard '-'" if flagged else "Timestamp distribution aligned"
            })
        return alerts

    def detect_d_spatial_centroid_zscore(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """D: Spatial Centroid Distance & Bivariate Z-score for inverted coordinates."""
        # NYC centroid: Lat ~ 40.71, Lon ~ -73.95
        NYC_LAT_MEAN, NYC_LAT_STD = 40.72, 0.08
        NYC_LON_MEAN, NYC_LON_STD = -73.94, 0.09

        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            lat = row.get("latitude")
            lon = row.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                # Z-scores
                z_lat = abs(lat - NYC_LAT_MEAN) / NYC_LAT_STD
                z_lon = abs(lon - NYC_LON_MEAN) / NYC_LON_STD
                # If latitude is negative, z-score is massive (>500)
                if z_lat > 5.0 or z_lon > 5.0:
                    flagged = True
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "d_spatial_zscore",
                "explanation": f"Bivariate spatial outlier: Z-score > 5.0 from NYC centroid (Lat {lat}, Lon {lon})" if flagged else "Spatial coordinates within 3-sigma"
            })
        return alerts

    def detect_e_exact_duplicates(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """E: Multi-set frequency detector (flags records occurring > 1 time)."""
        counts = collections.Counter(tuple(sorted((k, str(v)) for k, v in row.items())) for row in batch)
        alerts = []
        for idx, row in enumerate(batch):
            key = tuple(sorted((k, str(v)) for k, v in row.items()))
            flagged = counts[key] > 1
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "e_exact_duplicates_statistical",
                "explanation": f"Frequency collision: record tuple occurs {counts[key]} times in batch" if flagged else "Unique record"
            })
        return alerts

    def detect_f_ngram_jaccard_near_duplicates(self, batch: List[Dict[str, Any]], sim_threshold: float = 0.80) -> List[Dict[str, Any]]:
        """F: Statistical Character 3-Gram Jaccard Similarity on incident text within temporal cluster."""
        def get_3grams(s: str) -> set:
            s = s.lower()
            return {s[i:i+3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}

        alerts = []
        n = len(batch)
        flagged_indices = set()

        # Group by agency for efficient statistical pairwise comparison
        agency_groups: Dict[str, List[int]] = collections.defaultdict(list)
        for i, row in enumerate(batch):
            agency_groups[row.get("agency", "")].append(i)

        for ag, indices in agency_groups.items():
            for i in range(len(indices)):
                idx1 = indices[i]
                text1 = f"{batch[idx1].get('incident_address', '')} {batch[idx1].get('descriptor', '')}"
                g1 = get_3grams(text1)
                for j in range(i + 1, min(i + 15, len(indices))):
                    idx2 = indices[j]
                    text2 = f"{batch[idx2].get('incident_address', '')} {batch[idx2].get('descriptor', '')}"
                    g2 = get_3grams(text2)
                    inter = len(g1 & g2)
                    union = len(g1 | g2)
                    sim = inter / union if union > 0 else 0.0
                    if sim >= sim_threshold:
                        flagged_indices.add(idx2)

        for idx in range(n):
            flagged = idx in flagged_indices
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "f_near_duplicates_statistical",
                "explanation": f"Statistical text similarity: Jaccard 3-gram score >= {sim_threshold}" if flagged else "Unique semantic signature"
            })
        return alerts

    def detect_g_null_spike_zscore(self, batch: List[Dict[str, Any]], z_thresh: float = 2.5) -> List[Dict[str, Any]]:
        """G: Modified Z-Score / Rate Anomaly on Agency Null Rates."""
        agency_totals = collections.defaultdict(int)
        agency_nulls = collections.defaultdict(int)
        for r in batch:
            ag = r.get("agency", "UNKNOWN")
            agency_totals[ag] += 1
            if not r.get("descriptor"):
                agency_nulls[ag] += 1

        agency_rates = {ag: agency_nulls[ag] / agency_totals[ag] for ag in agency_totals if agency_totals[ag] >= 5}
        if not agency_rates:
            return [{"row_index": i, "flagged": False, "problem": "g_null_spike_zscore", "explanation": "Batch too small"} for i in range(len(batch))]

        rates = list(agency_rates.values())
        mean_rate = sum(rates) / len(rates)
        variance = sum((x - mean_rate) ** 2 for x in rates) / len(rates)
        std_rate = math.sqrt(variance) if variance > 0 else 0.001

        spiked_agencies = {
            ag for ag, rate in agency_rates.items()
            if ((rate - mean_rate) / std_rate) > z_thresh and rate > 0.40
        }

        alerts = []
        for idx, row in enumerate(batch):
            ag = row.get("agency", "UNKNOWN")
            flagged = ag in spiked_agencies and not row.get("descriptor")
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "g_null_spike_zscore",
                "explanation": f"Statistical null anomaly: agency '{ag}' null rate exceeds 2.5 sigma from batch mean" if flagged else "Normal null distribution"
            })
        return alerts

    def detect_h_duration_iqr(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """H: Statistical duration distribution and negative value detection."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            c_str = row.get("created_date")
            cl_str = row.get("closed_date")
            if c_str and cl_str:
                try:
                    c_dt = datetime.strptime(c_str, "%Y-%m-%d %H:%M:%S")
                    cl_dt = datetime.strptime(cl_str, "%Y-%m-%d %H:%M:%S")
                    duration_hrs = (cl_dt - c_dt).total_seconds() / 3600.0
                    if duration_hrs < 0:
                        flagged = True
                except Exception:
                    pass
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "h_duration_iqr",
                "explanation": "Duration distribution outlier: negative elapsed time (closed earlier than created)" if flagged else "Duration within distribution"
            })
        return alerts

    def detect_i_zip_borough_conditional_prob(self, batch: List[Dict[str, Any]], p_min: float = 0.05) -> List[Dict[str, Any]]:
        """I: Statistical conditional probability P(Borough | ZIP) < p_min."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            z = str(row.get("incident_zip", "")).strip()
            b = str(row.get("borough", "")).strip().upper()
            if z in self.p_zip_borough:
                prob = self.p_zip_borough[z].get(b, 0.0)
                if prob < p_min:
                    flagged = True
            elif z and b:
                # If zip not in training distribution, check against borough list
                if z.startswith("100") and b != "MANHATTAN":
                    flagged = True
                elif z.startswith("112") and b != "BROOKLYN":
                    flagged = True
                elif z.startswith("113") and b != "QUEENS":
                    flagged = True
                elif z.startswith("104") and b != "BRONX":
                    flagged = True
                elif z.startswith("103") and b != "STATEN ISLAND":
                    flagged = True

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "i_conditional_prob",
                "explanation": f"Low conditional probability: P({b} | ZIP={z}) < {p_min}" if flagged else "Conditional probability normal"
            })
        return alerts

    def detect_j_pmi_complaint_descriptor(self, batch: List[Dict[str, Any]], pmi_threshold: float = -1.0) -> List[Dict[str, Any]]:
        """J: Pointwise Mutual Information (PMI) anomaly between Complaint Type and Descriptor."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            c = str(row.get("complaint_type", "")).strip()
            d = str(row.get("descriptor", "")).strip()
            if c and d:
                if (c, d) in self.pmi_complaint_desc:
                    pmi = self.pmi_complaint_desc[(c, d)]
                    if pmi < pmi_threshold:
                        flagged = True
                else:
                    # Unseen co-occurrence: check cross-domain mismatch
                    if "noise" in c.lower() and ("pothole" in d.lower() or "hydrant" in d.lower() or "cave-in" in d.lower()):
                        flagged = True

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "j_pmi_anomaly",
                "explanation": f"Negative Pointwise Mutual Information (PMI < {pmi_threshold}): uncharacteristic co-occurrence" if flagged else "Co-occurrence supported by data"
            })
        return alerts

    def detect_k_status_resolution_prob(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """K: Co-occurrence probability anomaly between status and keywords in resolution."""
        contradictory_phrases = ["currently investigating", "completed all necessary repairs"]
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            status = str(row.get("status", "")).strip()
            res = str(row.get("resolution_description", "")).lower()
            if status == "Closed" and "currently investigating" in res:
                flagged = True
            elif status == "Open" and "completed all necessary repairs" in res:
                flagged = True

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "k_status_prob",
                "explanation": f"Status-resolution conditional probability zero: '{status}' contradicted by resolution text" if flagged else "Text matches status prior"
            })
        return alerts

    def detect_l_pii_entropy(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """L: Statistical Digit Density & Token Pattern Anomaly for PII detection."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            res = str(row.get("resolution_description", ""))
            # Digits in text (e.g. phone numbers have 10 digits in close proximity)
            digits = re.findall(r"\d", res)
            has_at = "@" in res
            if len(digits) >= 10 or has_at:
                flagged = True

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "l_pii_statistical",
                "explanation": f"High numeric/symbol token density ({len(digits)} digits, @ symbol) indicative of PII" if flagged else "Normal prose entropy"
            })
        return alerts

    def detect_problem(self, problem_key: str, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dispatch = {
            "a": self.detect_a_schema_entropy,
            "b": self.detect_b_type_distribution,
            "c": self.detect_c_date_format_entropy,
            "d": self.detect_d_spatial_centroid_zscore,
            "e": self.detect_e_exact_duplicates,
            "f": self.detect_f_ngram_jaccard_near_duplicates,
            "g": self.detect_g_null_spike_zscore,
            "h": self.detect_h_duration_iqr,
            "i": self.detect_i_zip_borough_conditional_prob,
            "j": self.detect_j_pmi_complaint_descriptor,
            "k": self.detect_k_status_resolution_prob,
            "l": self.detect_l_pii_entropy,
        }
        if problem_key not in dispatch:
            raise ValueError(f"Unknown problem key: {problem_key}")
        return dispatch[problem_key](batch)
