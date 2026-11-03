"""Payroll domain rules, independent of the GUI and OCR engine."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import re

DAYS = ("SAT", "SUN", "MON", "TUE", "WED", "THU", "FRI")
DISPLAY = ("Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
TIME_FIELDS = ("in1", "out1", "in2", "out2")


def fully_reviewed(flags) -> bool:
    return isinstance(flags, list) and len(flags) == 14 and all(v is True for v in flags)


@dataclass
class ShiftDay:
    in1: str = ""
    out1: str = ""
    in2: str = ""
    out2: str = ""
    recognized: dict[str, str] = field(default_factory=dict)


@dataclass
class Sheet:
    source: str
    source_hash: str
    employee: str = ""
    period_start: str = ""  # YYYY-MM-DD, Saturday
    days: list[ShiftDay] = field(default_factory=lambda: [ShiftDay() for _ in range(14)])
    approved: bool = False
    reviewed_days: list[bool] = field(default_factory=lambda: [False] * 14)
    notes: str = ""
    scan_warnings: list[str] = field(default_factory=list)
    form_type: str = "legacy_two_pair"
    # Image bytes and file paths are intentionally NOT stored in the final payroll export.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, item: dict) -> "Sheet":
        return cls(source=item["source"], source_hash=item["source_hash"],
                   employee=item.get("employee", ""), period_start=item.get("period_start", ""),
                   days=[ShiftDay(**v) for v in item.get("days", [])],
                   approved=item.get("approved", False), reviewed_days=item.get("reviewed_days", [False]*14), notes=item.get("notes", ""),
                   scan_warnings=item.get("scan_warnings", []),
                   form_type=item.get("form_type", "legacy_two_pair"))


def normalize_time(raw: str) -> tuple[str, str]:
    """Return canonical HH:MM 24-hour time, or error description.

    No AM/PM guessing is performed. 12A is 00:00; 12P is 12:00.
    """
    val = re.sub(r"\s+", "", str(raw or "")).upper().replace(".", "")
    if not val:
        return "", ""
    val = val.replace("O", "0")
    # Ambiguous '230A' means 2:30 AM, '915P' 9:15 PM.
    m = re.fullmatch(r"(\d{1,2})(?::?(\d{2}))?(A|AM|P|PM)", val)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or "0")
        meridiem = m.group(3)[0]
        if not 1 <= hour <= 12 or minute > 59:
            return "", "Invalid time"
        return f"{(hour % 12) + (12 if meridiem == 'P' else 0):02d}:{minute:02d}", ""
    # Permit explicit 24-h inputs 00:00-23:59 when colon is included.
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", val)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if hh <= 23 and mm <= 59:
            if 1 <= hh <= 12 and len(m.group(1)) == 1:
                return "", "Add A or P (AM/PM), or use 24-hour notation with two digits"
            return f"{hh:02d}:{mm:02d}", ""
        return "", "Invalid 24-hour time"
    return "", "Enter AM or PM, e.g. 9:15P; or use 21:15"


def display_time(raw: str) -> str:
    t, error = normalize_time(raw)
    if not t:
        return raw.strip() if raw.strip() else ""
    hh, mm = map(int, t.split(":"))
    return f"{(hh % 12) or 12}:{mm:02d}{'P' if hh >= 12 else 'A'}"


def calculate_day(day: ShiftDay) -> tuple[float | None, list[str]]:
    errors: list[str] = []
    hours = 0.0
    intervals = []
    punches = [getattr(day, k).strip() for k in TIME_FIELDS]
    if not any(punches):
        return 0.0, []
    for pair in ((0, 1), (2, 3)):
        a, b = punches[pair[0]], punches[pair[1]]
        if not a and not b:
            continue
        if not a or not b:
            errors.append("Missing clock-in or clock-out")
            continue
        start, e1 = normalize_time(a)
        end, e2 = normalize_time(b)
        if e1 or e2:
            errors.append("; ".join(x for x in (e1, e2) if x))
            continue
        start_min = int(start[:2]) * 60 + int(start[3:])
        end_min = int(end[:2]) * 60 + int(end[3:])
        delta = (end_min - start_min) % 1440
        if delta == 0:
            errors.append("Identical in/out times; confirm shift")
            continue
        if intervals and start_min < intervals[0][0]:
            start_min += 1440
        intervals.append((start_min, start_min + delta))
        hours += delta / 60.0
        if delta > 16 * 60:
            errors.append("Shift longer than 16 hours; verify")
    if len(intervals) == 2 and intervals[1][0] < intervals[0][1]:
        errors.append("Split shifts overlap; verify clock times")
    if hours > 16:
        errors.append("More than 16 hours in one day; verify")
    if errors:
        return None, list(dict.fromkeys(errors))
    return round(hours, 4), []


def validate_sheet(sheet: Sheet) -> list[str]:
    warnings = []
    if not sheet.employee.strip():
        warnings.append("Employee name is missing")
    if not sheet.period_start.strip():
        warnings.append("First Saturday of pay period is missing")
    else:
        try:
            date = datetime.strptime(sheet.period_start, "%Y-%m-%d").date()
            if date.weekday() != 5:
                warnings.append("Pay period must begin on Saturday")
        except ValueError:
            warnings.append("Pay period date must be YYYY-MM-DD")
    for i, day in enumerate(sheet.days):
        _, errors = calculate_day(day)
        for msg in errors:
            warnings.append(f"Week {i // 7 + 1} {DISPLAY[i % 7]}: {msg}")
    if len(sheet.days) != 14:
        warnings.append("Exactly 14 timesheet rows are required")
    return warnings


def summarize(sheet: Sheet) -> dict:
    hours = [calculate_day(day)[0] for day in sheet.days]
    if any(v is None for v in hours):
        return {"week1": None, "week2": None, "total": None, "regular": None, "overtime": None}
    week1 = round(sum(hours[:7]), 2)
    week2 = round(sum(hours[7:]), 2)
    ot = round(max(week1 - 40, 0) + max(week2 - 40, 0), 2)
    return {"week1": week1, "week2": week2, "total": round(week1 + week2, 2),
            "regular": round(week1 + week2 - ot, 2), "overtime": ot}


def save_session(path: str, sheets: list[Sheet]) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "sheets": [s.to_dict() for s in sheets]}, indent=2), encoding="utf-8")
    tmp.replace(dest)


def load_session(path: str) -> list[Sheet]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("Unsupported saved session version")
    return [Sheet.from_dict(s) for s in data["sheets"]]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
