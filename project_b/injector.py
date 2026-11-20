"""
Corruption Injector: Task 2.
Injects each of the 12 problem types into clean batches at a controlled rate,
so detection performance (Recall and FPR) can be rigorously measured.

12 Problem Types:
a. Renamed or dropped column
b. Column type change (e.g. numbers arriving as strings or strings arriving as numbers)
c. Date format switch partway through a batch
d. Latitude and longitude swapped
e. Exact duplicates
f. Near-duplicates (same request, slightly altered timestamp or text)
g. Null spike in one agency's records
h. Closed date earlier than created date
i. ZIP code inconsistent with borough
j. Complaint Type inconsistent with Descriptor
k. Resolution Description contradicting Status
l. Personal data (phone numbers, emails, names) inside free-text fields
"""

import copy
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


class CorruptionInjector:
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def inject_a_dropped_renamed_column(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem A: Renamed or dropped column (batch-level / schema-level)."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        
        # Drops or renames 'incident_zip' -> 'postal_code' or drops 'borough'
        targets = ["incident_zip", "borough", "descriptor"]
        col = random.choice(targets)
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                if random.random() < 0.5:
                    if col in data[idx]:
                        del data[idx][col]
                else:
                    if col in data[idx]:
                        data[idx][f"{col}_renamed"] = data[idx].pop(col)
        return data, labels

    def inject_b_column_type_change(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem B: Column type change (e.g. numeric latitude/longitude arriving as malformed string 'NaN' / 'N/A' or unique_key corrupted)."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                choice = random.choice(["string_nan", "nested_dict", "raw_boolean"])
                if choice == "string_nan":
                    data[idx]["latitude"] = "N/A"
                    data[idx]["longitude"] = "ERR_VAL"
                elif choice == "nested_dict":
                    data[idx]["unique_key"] = {"id": data[idx]["unique_key"]}
                else:
                    data[idx]["incident_zip"] = True
        return data, labels

    def inject_c_date_format_switch(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem C: Date format switch partway through a batch (e.g. YYYY-MM-DD -> DD/MM/YYYY or MM/DD/YYYY)."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                c_str = data[idx].get("created_date")
                if c_str:
                    try:
                        dt = datetime.strptime(c_str, "%Y-%m-%d %H:%M:%S")
                        data[idx]["created_date"] = dt.strftime("%d/%m/%Y %I:%M:%S %p")
                    except Exception:
                        pass
        return data, labels

    def inject_d_lat_long_swapped(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem D: Latitude and Longitude swapped (Lat ~40.7, Lon ~-73.9 becomes Lat ~-73.9, Lon ~40.7)."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if random.random() < rate:
                if data[idx].get("latitude") and data[idx].get("longitude"):
                    labels[idx] = True
                    temp = data[idx]["latitude"]
                    data[idx]["latitude"] = data[idx]["longitude"]
                    data[idx]["longitude"] = temp
        return data, labels

    def inject_e_exact_duplicates(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem E: Exact duplicate rows."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        num_dups = int(len(data) * rate)
        dup_source_indices = random.sample(range(len(data) // 2), num_dups)
        for src in dup_source_indices:
            insert_pos = random.randint(len(data) // 2, len(data) - 1)
            dup_record = copy.deepcopy(data[src])
            data.insert(insert_pos, dup_record)
            labels.insert(insert_pos, True)
        return data, labels

    def inject_f_near_duplicates(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem F: Near-duplicates (same request, slightly altered timestamp by a few seconds or slightly altered text)."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        num_dups = int(len(data) * rate)
        sources = random.sample(range(len(data) // 2), num_dups)
        for src in sources:
            rec = copy.deepcopy(data[src])
            # Alter unique_key and shift created_date by 5-30 seconds
            rec["unique_key"] = str(int(rec["unique_key"]) + 9000000)
            try:
                dt = datetime.strptime(rec["created_date"], "%Y-%m-%d %H:%M:%S")
                rec["created_date"] = (dt + timedelta(seconds=random.randint(5, 30))).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            # Slightly alter descriptor with typo or extra space
            if rec.get("descriptor"):
                rec["descriptor"] = rec["descriptor"] + " "
            insert_pos = random.randint(len(data) // 2, len(data) - 1)
            data.insert(insert_pos, rec)
            labels.insert(insert_pos, True)
        return data, labels

    def inject_g_null_spike(self, batch: List[Dict[str, Any]], target_agency: str = "NYPD", rate: float = 0.85, null_rate: float = None) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem G: Sudden Null spike in one specific agency's records (e.g. NYPD descriptor becomes null in 85% of records)."""
        actual_rate = null_rate if null_rate is not None else rate
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if data[idx].get("agency") == target_agency:
                if random.random() < actual_rate:
                    labels[idx] = True
                    data[idx]["descriptor"] = None
                    data[idx]["incident_address"] = None
        return data, labels

    def inject_h_closed_earlier_than_created(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem H: Closed date earlier than created date (time travel / negative resolution time)."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if random.random() < rate:
                c_str = data[idx].get("created_date")
                if c_str:
                    try:
                        c_dt = datetime.strptime(c_str, "%Y-%m-%d %H:%M:%S")
                        labels[idx] = True
                        data[idx]["closed_date"] = (c_dt - timedelta(hours=random.randint(4, 72))).strftime("%Y-%m-%d %H:%M:%S")
                        data[idx]["status"] = "Closed"
                    except Exception:
                        pass
        return data, labels

    def inject_i_zip_inconsistent_with_borough(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem I: ZIP code inconsistent with borough (e.g. Manhattan ZIP 10001 labeled as 'BROOKLYN')."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                curr_b = data[idx].get("borough", "MANHATTAN")
                other_b = "BROOKLYN" if curr_b != "BROOKLYN" else "QUEENS"
                data[idx]["borough"] = other_b
        return data, labels

    def inject_j_complaint_inconsistent_with_descriptor(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem J: Complaint Type inconsistent with Descriptor (e.g. 'Noise - Residential' with 'Pothole in roadway')."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        absurd_descriptors = [
            "Pothole in roadway", "Cave-in on street", "Catch Basin Clogged",
            "Broken Hydrant", "Branch Cracked and Will Fall", "Dead Animal on Highway"
        ]
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                data[idx]["complaint_type"] = "Noise - Residential"
                data[idx]["descriptor"] = random.choice(absurd_descriptors)
        return data, labels

    def inject_k_resolution_contradicting_status(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem K: Resolution Description contradicting Status."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                if random.random() < 0.5:
                    # Status says Closed, but description says active investigation / unassigned
                    data[idx]["status"] = "Closed"
                    data[idx]["resolution_description"] = "The Police Department is currently investigating this condition and has not resolved it."
                else:
                    # Status says Open, but resolution says inspected, corrected and closed
                    data[idx]["status"] = "Open"
                    data[idx]["closed_date"] = None
                    data[idx]["resolution_description"] = "The Department has inspected the condition, completed all necessary repairs, and successfully resolved the issue."
        return data, labels

    def inject_l_personal_data_pii(self, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        """Problem L: Personal data (phone numbers, emails, personal full names) inside free-text fields."""
        data = copy.deepcopy(batch)
        labels = [False] * len(data)
        names = ["Suresh Nair", "Priya Sharma", "David Miller", "Michael Chang", "Emily Watson"]
        for idx in range(len(data)):
            if random.random() < rate:
                labels[idx] = True
                phone = f"{random.randint(201, 917)}-{random.randint(200, 899)}-{random.randint(1000, 9999)}"
                email = f"{random.choice(names).lower().replace(' ', '.')}_{random.randint(10, 99)}@gmail.com"
                name = random.choice(names)
                data[idx]["resolution_description"] = (
                    f"Complainant {name} called from {phone} (email: {email}) requesting immediate callback. "
                    + str(data[idx].get("resolution_description", ""))
                )
        return data, labels

    def inject_problem(self, problem_key: str, batch: List[Dict[str, Any]], rate: float = 0.10) -> Tuple[List[Dict[str, Any]], List[bool]]:
        dispatch = {
            "a": self.inject_a_dropped_renamed_column,
            "b": self.inject_b_column_type_change,
            "c": self.inject_c_date_format_switch,
            "d": self.inject_d_lat_long_swapped,
            "e": self.inject_e_exact_duplicates,
            "f": self.inject_f_near_duplicates,
            "g": self.inject_g_null_spike,
            "h": self.inject_h_closed_earlier_than_created,
            "i": self.inject_i_zip_inconsistent_with_borough,
            "j": self.inject_j_complaint_inconsistent_with_descriptor,
            "k": self.inject_k_resolution_contradicting_status,
            "l": self.inject_l_personal_data_pii,
        }
        if problem_key not in dispatch:
            raise ValueError(f"Unknown problem key '{problem_key}'. Valid: a-l")
        return dispatch[problem_key](batch, rate=rate)
