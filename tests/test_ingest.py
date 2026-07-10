import zipfile

import pytest

from letterboxd_explorer import ingest


def test_read_export_dir(export_dir):
    frames = ingest.read_export(export_dir)
    assert {"watched", "ratings", "diary"} <= set(frames)


def test_read_export_zip(export_dir, tmp_path):
    zpath = tmp_path / "export.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for f in export_dir.glob("*.csv"):
            z.write(f, f.name)
    frames = ingest.read_export(zpath)
    assert "watched" in frames


def test_read_export_invalid(tmp_path):
    with pytest.raises(ingest.ExportError):
        ingest.read_export(tmp_path / "nao-existe")


def test_build_films_merges_ratings(export_dir):
    frames = ingest.read_export(export_dir)
    films = ingest.build_films(frames)
    assert len(films) == 2
    assert films.loc[films["Name"] == "A", "Rating"].iloc[0] == 5.0
    assert films.loc[films["Name"] == "B", "Rating"].isna().all()


def test_build_diary_parses_dates(export_dir):
    frames = ingest.read_export(export_dir)
    diary = ingest.build_diary(frames)
    assert diary["Watched Date"].dt.year.iloc[0] == 2024
    assert not diary["Rewatch"].iloc[0]


def test_filter_year(export_dir):
    frames = ingest.read_export(export_dir)
    films = ingest.build_films(frames)
    diary = ingest.build_diary(frames)
    f, d = ingest.filter_year(films, diary, 2024)
    assert len(f) == 1 and len(d) == 1
    with pytest.raises(ingest.ExportError):
        ingest.filter_year(films, diary, 1990)
