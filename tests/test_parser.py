"""
Unit tests for parser/mi_fitness.py
"""

import io
import json
import os
import zipfile
from datetime import datetime

import pandas as pd
import pytest

# Add repo root to path so we can import parser
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser.mi_fitness import (
    _parse_date,
    _normalize_df,
    _parse_csv_bytes,
    _parse_json_bytes,
    _parse_zip_bytes,
    generate_sample_data,
    yearly_summary,
    monthly_summary,
)

# ---------------------------------------------------------------------------
# Sample data fixture
# ---------------------------------------------------------------------------

SAMPLE_CSV = """date,steps,distance,calories
2024-01-01,8500,6.63,340.0
2024-01-02,7200,5.62,288.0
2024-01-03,9100,7.10,364.0
"""

SAMPLE_JSON = json.dumps([
    {"date": "2024-02-01", "steps": 8000, "distance": 6.24, "calories": 320.0},
    {"date": "2024-02-02", "steps": 6500, "distance": 5.07, "calories": 260.0},
])


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

class TestParseDateFormats:
    def test_iso_format(self):
        assert _parse_date("2024-03-15") == datetime(2024, 3, 15)

    def test_compact_format(self):
        assert _parse_date("20240315") == datetime(2024, 3, 15)

    def test_us_format(self):
        assert _parse_date("03/15/2024") == datetime(2024, 3, 15)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")

    def test_strips_whitespace(self):
        assert _parse_date("  2024-01-01  ") == datetime(2024, 1, 1)


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

class TestCSVParsing:
    def test_basic_csv(self):
        df = _parse_csv_bytes(SAMPLE_CSV.encode())
        assert len(df) == 3
        assert list(df.columns) == ["date", "steps", "distance", "calories"]
        assert df["steps"].tolist() == [8500, 7200, 9100]

    def test_date_type(self):
        df = _parse_csv_bytes(SAMPLE_CSV.encode())
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_steps_int_type(self):
        df = _parse_csv_bytes(SAMPLE_CSV.encode())
        assert df["steps"].dtype == int

    def test_missing_distance_defaults_zero(self):
        csv = "date,steps\n2024-01-01,5000\n"
        df = _parse_csv_bytes(csv.encode())
        assert df["distance"].iloc[0] == 0.0

    def test_missing_calories_defaults_zero(self):
        csv = "date,steps\n2024-01-01,5000\n"
        df = _parse_csv_bytes(csv.encode())
        assert df["calories"].iloc[0] == 0.0

    def test_sorted_by_date(self):
        csv = "date,steps\n2024-01-03,100\n2024-01-01,200\n2024-01-02,300\n"
        df = _parse_csv_bytes(csv.encode())
        assert df["date"].iloc[0] == pd.Timestamp("2024-01-01")

    def test_compact_date_format(self):
        csv = "date,steps\n20240101,5000\n"
        df = _parse_csv_bytes(csv.encode())
        assert df["date"].iloc[0] == pd.Timestamp("2024-01-01")

    def test_us_date_format(self):
        csv = "date,steps\n01/15/2024,7000\n"
        df = _parse_csv_bytes(csv.encode())
        assert df["date"].iloc[0] == pd.Timestamp("2024-01-15")

    def test_no_date_column_raises(self):
        csv = "foo,steps\n2024-01-01,5000\n"
        with pytest.raises(ValueError, match="date"):
            _parse_csv_bytes(csv.encode())

    def test_no_steps_column_raises(self):
        csv = "date,distance\n2024-01-01,6.0\n"
        with pytest.raises(ValueError, match="steps"):
            _parse_csv_bytes(csv.encode())


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

class TestJSONParsing:
    def test_basic_json(self):
        df = _parse_json_bytes(SAMPLE_JSON.encode())
        assert len(df) == 2
        assert df["steps"].tolist() == [8000, 6500]

    def test_wrapped_json(self):
        wrapped = json.dumps({"data": [
            {"date": "2024-03-01", "steps": 9000, "distance": 7.02, "calories": 360.0},
        ]})
        df = _parse_json_bytes(wrapped.encode())
        assert len(df) == 1
        assert df["steps"].iloc[0] == 9000

    def test_date_type(self):
        df = _parse_json_bytes(SAMPLE_JSON.encode())
        assert pd.api.types.is_datetime64_any_dtype(df["date"])


# ---------------------------------------------------------------------------
# ZIP parsing
# ---------------------------------------------------------------------------

class TestZIPParsing:
    def _make_zip(self, filename: str, content: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(filename, content)
        return buf.getvalue()

    def test_activity_stage_data_csv(self):
        zb = self._make_zip("ACTIVITY_STAGE_DATA.csv", SAMPLE_CSV)
        df = _parse_zip_bytes(zb)
        assert len(df) == 3

    def test_generic_step_csv(self):
        zb = self._make_zip("my_step_data.csv", SAMPLE_CSV)
        df = _parse_zip_bytes(zb)
        assert len(df) == 3

    def test_any_csv_fallback(self):
        zb = self._make_zip("export.csv", SAMPLE_CSV)
        df = _parse_zip_bytes(zb)
        assert len(df) == 3

    def test_no_csv_raises(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "hello")
        with pytest.raises(ValueError, match="No CSV"):
            _parse_zip_bytes(buf.getvalue())

    def test_nested_path_csv(self):
        zb = self._make_zip("folder/steps.csv", SAMPLE_CSV)
        df = _parse_zip_bytes(zb)
        assert len(df) == 3


# ---------------------------------------------------------------------------
# Sample data generation
# ---------------------------------------------------------------------------

class TestSampleDataGeneration:
    def test_returns_dataframe(self):
        df = generate_sample_data()
        assert isinstance(df, pd.DataFrame)

    def test_covers_full_years(self):
        df = generate_sample_data(2022, 2024)
        years = df["date"].dt.year.unique().tolist()
        assert 2022 in years and 2023 in years and 2024 in years

    def test_column_schema(self):
        df = generate_sample_data()
        assert list(df.columns) == ["date", "steps", "distance", "calories"]

    def test_no_negative_steps(self):
        df = generate_sample_data()
        assert (df["steps"] >= 0).all()

    def test_reasonable_step_range(self):
        df = generate_sample_data()
        # Step counts are clipped to [_MIN_DAILY_STEPS, _MAX_DAILY_STEPS];
        # rest days use integers in [200, 1000) which are within that range.
        assert df["steps"].max() <= 25000
        assert df["steps"].min() >= 200

    def test_3_years_length(self):
        df = generate_sample_data(2022, 2024)
        # 2022 (365) + 2023 (365) + 2024 (366 leap) = 1096 days
        assert len(df) == 1096


# ---------------------------------------------------------------------------
# Yearly / Monthly aggregation helpers
# ---------------------------------------------------------------------------

class TestYearlySummary:
    def _sample(self):
        return _parse_csv_bytes(SAMPLE_CSV.encode())

    def test_returns_dataframe(self):
        df = yearly_summary(self._sample())
        assert isinstance(df, pd.DataFrame)

    def test_year_column_present(self):
        df = yearly_summary(self._sample())
        assert "year" in df.columns

    def test_total_steps(self):
        df = yearly_summary(self._sample())
        assert df.loc[df["year"] == 2024, "total_steps"].iloc[0] == 8500 + 7200 + 9100

    def test_avg_steps(self):
        df = yearly_summary(self._sample())
        expected_avg = round((8500 + 7200 + 9100) / 3)
        assert df.loc[df["year"] == 2024, "avg_steps"].iloc[0] == expected_avg


class TestMonthlySummary:
    def _sample(self):
        return _parse_csv_bytes(SAMPLE_CSV.encode())

    def test_returns_12_months(self):
        df = monthly_summary(self._sample(), 2024)
        assert len(df) == 12

    def test_january_total(self):
        df = monthly_summary(self._sample(), 2024)
        jan = df[df["month"] == 1]
        assert jan["total_steps"].iloc[0] == 8500 + 7200 + 9100

    def test_empty_months_are_zero(self):
        df = monthly_summary(self._sample(), 2024)
        # Only Jan has data, all other months should be 0
        for month in range(2, 13):
            assert df.loc[df["month"] == month, "total_steps"].iloc[0] == 0

    def test_nonexistent_year_returns_zeros(self):
        df = monthly_summary(self._sample(), 2020)
        assert df["total_steps"].sum() == 0


# ---------------------------------------------------------------------------
# Sample file on disk
# ---------------------------------------------------------------------------

class TestSampleFile:
    SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "steps.csv")

    def test_sample_file_exists(self):
        assert os.path.exists(self.SAMPLE_PATH)

    def test_sample_file_parseable(self):
        with open(self.SAMPLE_PATH, "rb") as f:
            df = _parse_csv_bytes(f.read())
        assert len(df) == 30
        assert list(df.columns) == ["date", "steps", "distance", "calories"]
