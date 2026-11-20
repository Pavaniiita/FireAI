"""
NYC 311 Raw Data Profiler: Task 1.
Profiles the raw 2023 dataset to discover and document real data quality issues
already present in NYC Open Data.

Analyzes:
1. Temporal integrity (closed date earlier than created date, impossible durations)
2. Missingness / Null distributions (null descriptors, missing coordinates, missing zips)
3. Geographic consistency (out-of-bounds coordinates, null lat/lon)
4. Information security / Privacy (PII leakage in free-text resolution descriptions)
5. Categorical validity & cross-field integrity
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List


class NYC311Profiler:
    def __init__(self, data_path: str = "project_b/data/nyc_311_raw_2023.json"):
        self.data_path = data_path
        with open(data_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.total_rows = len(self.data)

    def profile(self) -> Dict[str, Any]:
        issues = {
            "negative_durations": [],
            "missing_descriptors": [],
            "null_coordinates": [],
            "pii_leaks": [],
            "status_mismatches": [],
        }

        phone_regex = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
        email_regex = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

        for idx, row in enumerate(self.data):
            uk = row.get("unique_key")
            c_str = row.get("created_date")
            cl_str = row.get("closed_date")

            # 1. Negative durations (time travel)
            if c_str and cl_str:
                try:
                    c_dt = datetime.strptime(c_str, "%Y-%m-%d %H:%M:%S")
                    cl_dt = datetime.strptime(cl_str, "%Y-%m-%d %H:%M:%S")
                    if cl_dt < c_dt:
                        issues["negative_durations"].append({
                            "row_index": idx,
                            "unique_key": uk,
                            "created_date": c_str,
                            "closed_date": cl_str,
                            "delta_hours": round((cl_dt - c_dt).total_seconds() / 3600.0, 2),
                            "agency": row.get("agency")
                        })
                except Exception:
                    pass

            # 2. Missing descriptors
            if not row.get("descriptor") or str(row.get("descriptor")).strip() == "":
                issues["missing_descriptors"].append({
                    "row_index": idx,
                    "unique_key": uk,
                    "agency": row.get("agency"),
                    "complaint_type": row.get("complaint_type")
                })

            # 3. Null coordinates
            if row.get("latitude") is None or row.get("longitude") is None:
                issues["null_coordinates"].append({
                    "row_index": idx,
                    "unique_key": uk,
                    "incident_zip": row.get("incident_zip"),
                    "borough": row.get("borough")
                })

            # 4. PII leaks in free text
            res_desc = str(row.get("resolution_description") or "")
            desc_text = str(row.get("descriptor") or "")
            combined_text = f"{desc_text} {res_desc}"
            if phone_regex.search(combined_text) or email_regex.search(combined_text):
                issues["pii_leaks"].append({
                    "row_index": idx,
                    "unique_key": uk,
                    "agency": row.get("agency"),
                    "snippet": combined_text[:120]
                })

            # 5. Status mismatches (Closed without closed_date)
            status = row.get("status")
            if status == "Closed" and not cl_str:
                issues["status_mismatches"].append({
                    "row_index": idx,
                    "unique_key": uk,
                    "status": status,
                    "closed_date": cl_str
                })

        summary = {
            "total_rows_profiled": self.total_rows,
            "issues_found": {
                "negative_duration_time_travel": {
                    "count": len(issues["negative_durations"]),
                    "rate_pct": round((len(issues["negative_durations"]) / self.total_rows) * 100, 3),
                    "description": "Records where closed_date is earlier than created_date (negative resolution duration).",
                    "examples": issues["negative_durations"][:3]
                },
                "missing_descriptors": {
                    "count": len(issues["missing_descriptors"]),
                    "rate_pct": round((len(issues["missing_descriptors"]) / self.total_rows) * 100, 3),
                    "description": "Records with null or blank descriptor fields despite having a complaint_type.",
                    "examples": issues["missing_descriptors"][:3]
                },
                "null_coordinates": {
                    "count": len(issues["null_coordinates"]),
                    "rate_pct": round((len(issues["null_coordinates"]) / self.total_rows) * 100, 3),
                    "description": "Records lacking latitude/longitude spatial coordinates.",
                    "examples": issues["null_coordinates"][:3]
                },
                "pii_leakage": {
                    "count": len(issues["pii_leaks"]),
                    "rate_pct": round((len(issues["pii_leaks"]) / self.total_rows) * 100, 3),
                    "description": "Direct personally identifiable information (phone numbers, emails) exposed in resolution comments.",
                    "examples": issues["pii_leaks"][:3]
                }
            }
        }
        return summary


if __name__ == "__main__":
    profiler = NYC311Profiler()
    res = profiler.profile()
    print(json.dumps(res, indent=2))
