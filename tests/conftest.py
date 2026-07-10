import pandas as pd
import pytest


@pytest.fixture
def films():
    return pd.DataFrame({
        "Name": ["A", "B", "C", "D"],
        "Year": pd.array([1994, 2001, 2019, 2019], dtype="Int64"),
        "Rating": [5.0, 3.5, None, 4.0],
        "genres": [["Drama"], ["Drama", "Crime"], ["Terror"], ["Drama"]],
        "directors": [["X"], ["X"], ["Y"], ["X"]],
        "tmdb_rating": [8.8, 6.0, 7.0, 5.0],
        "tmdb_votes": [1000, 500, 10, 800],
        "runtime": [142, 90, 100, 120],
        "tmdb_id": [1, 2, 3, 4],
    })


@pytest.fixture
def diary():
    return pd.DataFrame({
        "Name": ["A", "B", "A", "C", "D"],
        "Year": pd.array([1994, 2001, 1994, 2019, 2019], dtype="Int64"),
        "Rating": [5.0, 3.5, 4.5, None, 4.0],
        "Rewatch": [False, False, True, False, False],
        "Watched Date": pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-03-10", "2025-06-01"]
        ),
    })


@pytest.fixture
def export_dir(tmp_path):
    pd.DataFrame({
        "Date": "2026-01-01", "Name": ["A", "B"], "Year": [1994, 2001],
        "Letterboxd URI": "x",
    }).to_csv(tmp_path / "watched.csv", index=False)
    pd.DataFrame({
        "Date": "2026-01-01", "Name": ["A"], "Year": [1994],
        "Letterboxd URI": "x", "Rating": [5.0],
    }).to_csv(tmp_path / "ratings.csv", index=False)
    pd.DataFrame({
        "Date": "2026-01-01", "Name": ["A"], "Year": [1994], "Letterboxd URI": "x",
        "Rating": [5.0], "Rewatch": ["No"], "Tags": "",
        "Watched Date": ["2024-05-05"],
    }).to_csv(tmp_path / "diary.csv", index=False)
    return tmp_path
