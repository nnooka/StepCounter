"""
MI Fitness (Xiaomi) health data parser.
Supports ZIP exports, CSV files, and JSON files.
"""

import io
import json
import zipfile
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Supported date formats for parsing
_DATE_FORMATS = ["%Y-%m-%d", "%Y%m%d", "%m/%d/%Y"]

# Step count clipping bounds used during sample data generation
_MIN_DAILY_STEPS = 500
_MAX_DAILY_STEPS = 25000

# Columns we care about after normalization
_REQUIRED_COLS = {"date", "steps"}
_OPTIONAL_COLS = {"distance", "calories"}


def _parse_date(value: str) -> datetime:
    """Try each known date format and return a datetime object."""
    value = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {value!r}")


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a raw DataFrame to the canonical schema:
      date (datetime64), steps (int), distance (float, km), calories (float)
    """
    # Lower-case all column names and strip whitespace
    df.columns = [c.strip().lower() for c in df.columns]

    # Rename common MI Fitness column variants
    rename_map = {
        "active_time": None,  # drop
        "step_count": "steps",
        "total_steps": "steps",
        "dist": "distance",
        "cal": "calories",
        "kcal": "calories",
    }
    for old, new in rename_map.items():
        if old in df.columns:
            if new is None:
                df = df.drop(columns=[old])
            else:
                df = df.rename(columns={old: new})

    if "date" not in df.columns:
        raise ValueError("Data has no 'date' column.")
    if "steps" not in df.columns:
        raise ValueError("Data has no 'steps' column.")

    # Parse dates
    df["date"] = df["date"].apply(_parse_date)
    df["date"] = pd.to_datetime(df["date"])

    # Coerce numeric columns
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0).astype(int)

    if "distance" not in df.columns:
        df["distance"] = 0.0
    else:
        df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0.0).astype(float)

    if "calories" not in df.columns:
        df["calories"] = 0.0
    else:
        df["calories"] = pd.to_numeric(df["calories"], errors="coerce").fillna(0.0).astype(float)

    # Keep only canonical columns and drop duplicates / sort
    df = df[["date", "steps", "distance", "calories"]]
    df = df.drop_duplicates(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _parse_csv_bytes(data: bytes) -> pd.DataFrame:
    """Parse CSV bytes into a normalized DataFrame."""
    text = data.decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    return _normalize_df(df)


def _parse_json_bytes(data: bytes) -> pd.DataFrame:
    """Parse JSON bytes (list of dicts) into a normalized DataFrame."""
    records = json.loads(data.decode("utf-8", errors="replace"))
    if isinstance(records, dict):
        # Maybe wrapped: {"data": [...]}
        for key in ("data", "steps", "records"):
            if key in records and isinstance(records[key], list):
                records = records[key]
                break
    df = pd.DataFrame(records)
    return _normalize_df(df)


def _parse_zip_bytes(data: bytes) -> pd.DataFrame:
    """
    Parse a MI Fitness ZIP export.
    Looks for ACTIVITY_STAGE_DATA.csv first, then any CSV with 'step' in the name,
    then any CSV file.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()

        # Priority order for finding step data
        candidates = []
        for name in names:
            lower = name.lower()
            if name.endswith(".csv") or name.endswith(".CSV"):
                if "activity_stage_data" in lower:
                    candidates.insert(0, name)
                elif "step" in lower:
                    candidates.append(name)
                else:
                    candidates.append(name)

        if not candidates:
            raise ValueError("No CSV files found inside the ZIP archive.")

        last_err = None
        for candidate in candidates:
            try:
                with zf.open(candidate) as f:
                    return _parse_csv_bytes(f.read())
            except Exception as exc:
                last_err = exc
                continue

        raise ValueError(f"Could not parse any CSV in ZIP: {last_err}")


def parse_file(file_storage) -> pd.DataFrame:
    """
    Parse an uploaded file (werkzeug FileStorage or file-like with .filename/.read()).
    Supports .zip, .csv, .json.
    Returns a normalized DataFrame.
    """
    filename = getattr(file_storage, "filename", "") or ""
    data = file_storage.read()

    lower = filename.lower()
    if lower.endswith(".zip"):
        return _parse_zip_bytes(data)
    elif lower.endswith(".csv"):
        return _parse_csv_bytes(data)
    elif lower.endswith(".json"):
        return _parse_json_bytes(data)
    else:
        # Try to auto-detect
        try:
            return _parse_zip_bytes(data)
        except Exception:
            pass
        try:
            return _parse_csv_bytes(data)
        except Exception:
            pass
        return _parse_json_bytes(data)


def generate_sample_data(start_year: int = 2022, end_year: int = 2024) -> pd.DataFrame:
    """
    Generate realistic sample step data covering start_year through end_year (inclusive).
    Step counts follow a sinusoidal seasonal pattern with random noise.
    """
    rng = np.random.default_rng(42)

    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    dates = pd.date_range(start, end, freq="D")
    n = len(dates)

    # Seasonal variation: more steps in summer months
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    seasonal = 1500 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Base + seasonal + noise
    base = 8000
    noise = rng.normal(0, 1200, n)
    steps = (base + seasonal + noise).astype(int)
    steps = np.clip(steps, _MIN_DAILY_STEPS, _MAX_DAILY_STEPS)

    # Occasional rest days (< 1000 steps)
    rest_days = rng.choice(n, size=int(n * 0.05), replace=False)
    steps[rest_days] = rng.integers(200, 1000, size=len(rest_days))

    # Derive distance (avg ~0.0008 km per step) and calories
    distance = np.round(steps * 0.00078, 2)
    calories = np.round(steps * 0.04, 1)

    df = pd.DataFrame(
        {
            "date": dates,
            "steps": steps,
            "distance": distance,
            "calories": calories,
        }
    )
    return df


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with total/avg steps per year."""
    df = df.copy()
    df["year"] = df["date"].dt.year
    summary = (
        df.groupby("year")
        .agg(
            total_steps=("steps", "sum"),
            avg_steps=("steps", "mean"),
            total_distance=("distance", "sum"),
            total_calories=("calories", "sum"),
            days=("steps", "count"),
        )
        .reset_index()
    )
    summary["avg_steps"] = summary["avg_steps"].round(0).astype(int)
    summary["total_distance"] = summary["total_distance"].round(2)
    summary["total_calories"] = summary["total_calories"].round(1)
    return summary


def monthly_summary(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Return monthly step totals for the given year."""
    df = df.copy()
    df = df[df["date"].dt.year == year]
    df["month"] = df["date"].dt.month
    summary = (
        df.groupby("month")
        .agg(
            total_steps=("steps", "sum"),
            avg_steps=("steps", "mean"),
            total_distance=("distance", "sum"),
            total_calories=("calories", "sum"),
            days=("steps", "count"),
        )
        .reset_index()
    )
    summary["avg_steps"] = summary["avg_steps"].round(0).astype(int)
    # Ensure all 12 months present
    all_months = pd.DataFrame({"month": range(1, 13)})
    summary = all_months.merge(summary, on="month", how="left").fillna(0)
    for col in ["total_steps", "avg_steps", "days"]:
        summary[col] = summary[col].astype(int)
    return summary
