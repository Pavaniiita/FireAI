"""
Family A: Declarative Rules & Schema Detectors.
Deterministic, rule-based, and schema-driven data-quality checks for all 12 problem types.

Attributes:
- O(1) or O(N) evaluation time.
- Sub-microsecond latency per row.
- Zero dollar cost.
- 100% deterministic.
"""

import re
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple


EXPECTED_SCHEMA = [
    "unique_key", "created_date", "closed_date", "agency", "agency_name",
    "complaint_type", "descriptor", "location_type", "incident_zip",
    "incident_address", "city", "borough", "status", "resolution_description",
    "latitude", "longitude"
]

NYC_ZIP_BOROUGH_MAP = {
    # Manhattan
    "10001": "MANHATTAN", "10002": "MANHATTAN", "10003": "MANHATTAN", "10011": "MANHATTAN",
    "10016": "MANHATTAN", "10019": "MANHATTAN", "10025": "MANHATTAN", "10036": "MANHATTAN",
    # Brooklyn
    "11201": "BROOKLYN", "11211": "BROOKLYN", "11215": "BROOKLYN", "11222": "BROOKLYN",
    "11226": "BROOKLYN", "11238": "BROOKLYN",
    # Queens
    "11101": "QUEENS", "11355": "QUEENS", "11372": "QUEENS", "11375": "QUEENS", "11432": "QUEENS",
    # Bronx
    "10451": "BRONX", "10458": "BRONX", "10467": "BRONX", "10468": "BRONX",
    # Staten Island
    "10301": "STATEN ISLAND", "10306": "STATEN ISLAND", "10314": "STATEN ISLAND",
}

VALID_COMPLAINT_TAXONOMY = {
    "Noise - Residential": {"Banging/Pounding", "Loud Music/Party", "Loud Television", "Loud Talking"},
    "Blocked Driveway": {"No Access", "Partial Access"},
    "Illegal Parking": {"Blocked Hydrant", "Double Parked", "Posted Parking Sign Violation", "Commercial Overnight"},
    "Noise - Street/Sidewalk": {"Loud Music/Party", "Loud Talking"},
    "Dirty Condition": {"Trash", "Sidewalk Cleaning", "Illegal Dumping"},
    "Sanitation Condition": {"Rat Sighting", "Overflowing Litter Basket", "Garbage Spillage"},
    "Missed Collection": {"Regular Collection", "Recycling Collection"},
    "Street Condition": {"Pothole", "Cave-in", "Defective Hardware"},
    "Traffic Signal Condition": {"Controller", "Post", "Lamp Out"},
    "Sidewalk Condition": {"Broken Sidewalk", "Cracked Sidewalk"},
    "HEAT/HOT WATER": {"ENTIRE BUILDING", "APARTMENT ONLY"},
    "PLUMBING": {"WATER LEAK", "BASIN/SINK", "TOILET"},
    "PAINT/PLASTER": {"CEILING", "WALLS"},
    "Noise": {"Noise: Construction Before/After Hours (NM1)", "Noise: Jack Hammering (NC2)"},
    "Water System": {"Leak (Use Comments) (WA2)", "Hydrant Running (WC1)", "Dirty Water (WA1)"},
    "Sewer": {"Catch Basin Clogged/Flooding (SC)", "Sewer Backup (SA)"},
    "Damaged Tree": {"Branch Cracked and Will Fall", "Tree Leaning"},
    "Overgrown Tree/Branches": {"Hitting Power Lines", "Blocking Sign"},
}


class DeclarativeRulesDetector:
    def __init__(self):
        self.phone_regex = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
        self.email_regex = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    def detect_a_schema(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """A: Checks for missing or renamed expected columns."""
        alerts = []
        expected_set = set(EXPECTED_SCHEMA)
        for idx, row in enumerate(batch):
            missing = expected_set - set(row.keys())
            if missing:
                alerts.append({
                    "row_index": idx,
                    "flagged": True,
                    "problem": "a_schema",
                    "explanation": f"Schema violation: missing required columns {list(missing)}"
                })
            else:
                alerts.append({"row_index": idx, "flagged": False, "problem": "a_schema", "explanation": "Schema valid"})
        return alerts

    def detect_b_column_types(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """B: Checks column data types (e.g. lat/lon must be float or None, unique_key must be string/int)."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            reasons = []
            lat = row.get("latitude")
            lon = row.get("longitude")
            uk = row.get("unique_key")
            
            if lat is not None and not isinstance(lat, (float, int)):
                flagged = True
                reasons.append(f"Latitude type '{type(lat).__name__}' invalid (expected float)")
            if lon is not None and not isinstance(lon, (float, int)):
                flagged = True
                reasons.append(f"Longitude type '{type(lon).__name__}' invalid (expected float)")
            if uk is not None and not isinstance(uk, (str, int)):
                flagged = True
                reasons.append(f"Unique Key type '{type(uk).__name__}' invalid")
            if isinstance(row.get("incident_zip"), bool):
                flagged = True
                reasons.append("ZIP code received as boolean")

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "b_column_type",
                "explanation": "; ".join(reasons) if flagged else "Types valid"
            })
        return alerts

    def detect_c_date_format(self, batch: List[Dict[str, Any]], expected_fmt: str = "%Y-%m-%d %H:%M:%S") -> List[Dict[str, Any]]:
        """C: Checks date format adherence."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            c_str = row.get("created_date")
            if c_str:
                try:
                    datetime.strptime(c_str, expected_fmt)
                except ValueError:
                    flagged = True
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "c_date_format",
                "explanation": f"Timestamp '{c_str}' does not conform to expected format '{expected_fmt}'" if flagged else "Format valid"
            })
        return alerts

    def detect_d_lat_long_swapped(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """D: Checks if Latitude and Longitude are swapped using NYC geographic boundaries."""
        # NYC boundaries: Latitude roughly 40.45 to 40.95; Longitude roughly -74.30 to -73.65
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            lat = row.get("latitude")
            lon = row.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                # If latitude is negative and longitude is positive, they are clearly swapped
                if lat < 0 and lon > 0:
                    flagged = True
                elif not (40.40 <= lat <= 41.05) or not (-74.35 <= lon <= -73.60):
                    # Check if swapping them fixes the bounds
                    if (40.40 <= lon <= 41.05) and (-74.35 <= lat <= -73.60):
                        flagged = True
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "d_lat_long_swapped",
                "explanation": f"Inverted spatial coordinates: Lat {lat}, Lon {lon} (swapped coordinates)" if flagged else "Coordinates valid"
            })
        return alerts

    def detect_e_exact_duplicates(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """E: Detects exact duplicates using hash table."""
        seen = set()
        alerts = []
        for idx, row in enumerate(batch):
            row_repr = json.dumps(row, sort_keys=True)
            h = hashlib.sha256(row_repr.encode("utf-8")).hexdigest()
            flagged = False
            if h in seen:
                flagged = True
            else:
                seen.add(h)
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "e_exact_duplicates",
                "explanation": "Exact duplicate row detected" if flagged else "Unique record"
            })
        return alerts

    def detect_f_near_duplicates(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """F: Rule-based near-duplicate detection (matching agency, address, complaint type with created_date delta < 60s)."""
        alerts = []
        spatial_buckets: Dict[Tuple[str, str, str], List[Tuple[int, datetime]]] = {}
        for idx, row in enumerate(batch):
            flagged = False
            agency = row.get("agency", "")
            addr = row.get("incident_address", "")
            ctype = row.get("complaint_type", "")
            c_str = row.get("created_date", "")
            key = (agency, addr, ctype)
            
            try:
                dt = datetime.strptime(c_str, "%Y-%m-%d %H:%M:%S")
                if key in spatial_buckets:
                    for prev_idx, prev_dt in spatial_buckets[key]:
                        if abs((dt - prev_dt).total_seconds()) <= 60:
                            flagged = True
                            break
                    spatial_buckets[key].append((idx, dt))
                else:
                    spatial_buckets[key] = [(idx, dt)]
            except Exception:
                pass

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "f_near_duplicates",
                "explanation": "Near-duplicate service request within 60s window at identical location" if flagged else "Unique request"
            })
        return alerts

    def detect_g_null_spike(self, batch: List[Dict[str, Any]], threshold: float = 0.50) -> List[Dict[str, Any]]:
        """G: Declarative static threshold rule: flags rows if agency null descriptor rate in batch exceeds threshold."""
        agency_counts: Dict[str, int] = {}
        agency_nulls: Dict[str, int] = {}
        for row in batch:
            ag = row.get("agency", "UNKNOWN")
            agency_counts[ag] = agency_counts.get(ag, 0) + 1
            if not row.get("descriptor"):
                agency_nulls[ag] = agency_nulls.get(ag, 0) + 1

        flagged_agencies = {
            ag for ag, count in agency_counts.items()
            if count >= 10 and (agency_nulls.get(ag, 0) / count) > threshold
        }

        alerts = []
        for idx, row in enumerate(batch):
            ag = row.get("agency", "UNKNOWN")
            is_spike = ag in flagged_agencies and not row.get("descriptor")
            alerts.append({
                "row_index": idx,
                "flagged": is_spike,
                "problem": "g_null_spike",
                "explanation": f"Null descriptor in agency '{ag}' exceeding {int(threshold*100)}% batch null ceiling" if is_spike else "Normal null profile"
            })
        return alerts

    def detect_h_closed_earlier_than_created(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """H: Checks closed_date >= created_date."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            c_str = row.get("created_date")
            cl_str = row.get("closed_date")
            if c_str and cl_str:
                try:
                    c_dt = datetime.strptime(c_str, "%Y-%m-%d %H:%M:%S")
                    cl_dt = datetime.strptime(cl_str, "%Y-%m-%d %H:%M:%S")
                    if cl_dt < c_dt:
                        flagged = True
                except Exception:
                    pass
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "h_closed_earlier",
                "explanation": f"Temporal violation: closed_date ({cl_str}) is earlier than created_date ({c_str})" if flagged else "Chronology valid"
            })
        return alerts

    def detect_i_zip_borough_inconsistency(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """I: Checks ZIP code against deterministic NYC Borough dictionary."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            z = str(row.get("incident_zip", "")).strip()
            b = str(row.get("borough", "")).strip().upper()
            if z in NYC_ZIP_BOROUGH_MAP:
                expected_b = NYC_ZIP_BOROUGH_MAP[z]
                if b and b != expected_b:
                    flagged = True
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "i_zip_borough_mismatch",
                "explanation": f"Cross-field inconsistency: ZIP {z} belongs to '{NYC_ZIP_BOROUGH_MAP.get(z)}', but received '{b}'" if flagged else "Borough-ZIP aligned"
            })
        return alerts

    def detect_j_complaint_descriptor_inconsistency(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """J: Checks taxonomy validity between complaint_type and descriptor."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            ctype = row.get("complaint_type", "")
            desc = row.get("descriptor", "")
            if ctype in VALID_COMPLAINT_TAXONOMY and desc:
                valid_set = VALID_COMPLAINT_TAXONOMY[ctype]
                if desc not in valid_set:
                    flagged = True
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "j_complaint_descriptor_mismatch",
                "explanation": f"Taxonomy violation: descriptor '{desc}' is invalid for complaint_type '{ctype}'" if flagged else "Taxonomy valid"
            })
        return alerts

    def detect_k_status_resolution_contradiction(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """K: Keyword-based status and resolution description contradiction check."""
        alerts = []
        investigating_keywords = ["currently investigating", "not resolved", "in progress", "pending inspection", "action has been scheduled"]
        resolved_keywords = ["completed all necessary repairs", "successfully resolved", "inspected and found to be resolved", "took action"]
        
        for idx, row in enumerate(batch):
            flagged = False
            status = row.get("status", "")
            res = str(row.get("resolution_description", "")).lower()
            
            if status == "Closed" and any(kw in res for kw in investigating_keywords):
                flagged = True
            elif status == "Open" and any(kw in res for kw in resolved_keywords):
                flagged = True

            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "k_status_contradiction",
                "explanation": f"Semantic contradiction: status is '{status}', but resolution text indicates opposite state" if flagged else "Status consistent"
            })
        return alerts

    def detect_l_pii(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """L: Regex detector for personal data (phone numbers, emails) in free text fields."""
        alerts = []
        for idx, row in enumerate(batch):
            flagged = False
            res = str(row.get("resolution_description", ""))
            desc = str(row.get("descriptor", ""))
            combined = f"{desc} {res}"
            
            has_phone = bool(self.phone_regex.search(combined))
            has_email = bool(self.email_regex.search(combined))
            
            if has_phone or has_email:
                flagged = True
            alerts.append({
                "row_index": idx,
                "flagged": flagged,
                "problem": "l_pii_leak",
                "explanation": "Unmasked PII detected in free-text: phone number or email address exposed" if flagged else "Clean text"
            })
        return alerts

    def detect_problem(self, problem_key: str, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dispatch = {
            "a": self.detect_a_schema,
            "b": self.detect_b_column_types,
            "c": self.detect_c_date_format,
            "d": self.detect_d_lat_long_swapped,
            "e": self.detect_e_exact_duplicates,
            "f": self.detect_f_near_duplicates,
            "g": self.detect_g_null_spike,
            "h": self.detect_h_closed_earlier_than_created,
            "i": self.detect_i_zip_borough_inconsistency,
            "j": self.detect_j_complaint_descriptor_inconsistency,
            "k": self.detect_k_status_resolution_contradiction,
            "l": self.detect_l_pii,
        }
        if problem_key not in dispatch:
            raise ValueError(f"Unknown problem key: {problem_key}")
        return dispatch[problem_key](batch)
