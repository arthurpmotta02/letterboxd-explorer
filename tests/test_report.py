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
