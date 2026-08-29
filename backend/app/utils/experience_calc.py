"""Shared experience duration calculation utilities."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def parse_experience_date(value: Any) -> datetime | None:
    """Parse common resume experience date formats."""
    if not value:
        return None

    value = str(value).strip()

    if value.lower() in {"present", "current", "now", "ongoing"}:
        return datetime.utcnow()

    # Handle combined ranges stored in a single field, e.g. "Jan 2024 – Present"
    range_match = re.match(
        r"^(.+?)\s*[–—-]\s*(.+)$",
        value,
    )
    if range_match:
        value = range_match.group(1).strip()

    formats = [
        "%b %Y",
        "%B %Y",
        "%Y-%m-%d",
        "%Y-%m",
        "%m/%Y",
        "%Y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    return None


def _merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    merged = [sorted_intervals[0]]

    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def calculate_experience_years(
    experiences: list[dict[str, Any]],
) -> float:
    """Calculate total professional experience without double-counting overlaps."""
    intervals: list[tuple[datetime, datetime]] = []

    for experience in experiences:
        if not experience or not experience.get("company"):
            continue

        start_date = parse_experience_date(
            experience.get("start_date"),
        )
        if start_date is None:
            continue

        end_date = parse_experience_date(
            experience.get("end_date"),
        )
        if end_date is None:
            end_date = datetime.utcnow()

        if end_date < start_date:
            continue

        intervals.append((start_date, end_date))

    merged = _merge_intervals(intervals)
    total_months = 0

    for start, end in merged:
        months = (
            (end.year - start.year) * 12
            + (end.month - start.month)
            + 1
        )
        total_months += months

    return round(total_months / 12, 2)