from letterboxd_explorer import insights, report


def test_build_report_creates_html(films, diary, tmp_path):
    out = tmp_path / "r.html"
    report.build_report(films, diary, {}, out)
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>") and html.rstrip().endswith("</html>")
    assert "Letterboxd Explorer" in html


def test_build_report_year_mode(films, diary, tmp_path):
    out = tmp_path / "r.html"
    report.build_report(films, diary, {}, out, year=2024)
    assert "Retrospectiva 2024" in out.read_text(encoding="utf-8")


def test_insights_generate(films, diary):
    facts = insights.generate(films, diary)
    assert isinstance(facts, list) and len(facts) >= 3


def test_insights_no_diary(films):
    facts = insights.generate(films, None)
    assert isinstance(facts, list)


def test_report_structural_snapshot(films, diary, tmp_path):
    """Snapshot estrutural: elementos de layout que não podem sumir."""
    out = tmp_path / "r.html"
    report.build_report(films, diary, {}, out)
    html = out.read_text(encoding="utf-8")
    for marker in ["sidenav", "totop", "sharecard", "downloadCard",
                   "class=\"cards\"", "IntersectionObserver", "showTab"]:
        assert marker in html, f"sumiu do template: {marker}"


def test_report_schema_error_is_clear(tmp_path):
    import pandas as pd

    from letterboxd_explorer import ingest

    pd.DataFrame({"Filme": ["A"]}).to_csv(tmp_path / "watched.csv", index=False)
    try:
        ingest.read_export(tmp_path)
        raise AssertionError("deveria ter levantado ExportError")
    except ingest.ExportError as e:
        assert "watched.csv" in str(e)


def test_iso_map_covers_africa():
    from letterboxd_explorer.report import ISO2_TO_ISO3

    for code in ["BF", "ML", "CI", "CM", "AO", "MZ", "SN", "EG", "ET", "CD"]:
        assert code in ISO2_TO_ISO3
