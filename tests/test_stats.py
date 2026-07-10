import pandas as pd

from letterboxd_explorer import stats


def test_explode_count(films):
    g = stats.explode_count(films, "genres")
    assert g["Drama"] == 3
    assert stats.explode_count(films, "inexistente").empty


def test_decade_counts(films):
    d = stats.decade_counts(films)
    assert d[1990] == 1 and d[2010] == 2


def test_group_rating_min_count(films):
    g = stats.group_rating(films, "directors", min_count=2)
    assert list(g.index) == ["X"]
    assert g.loc["X", "mean"] == (5.0 + 3.5 + 4.0) / 3


def test_heresies_filters_low_votes(films):
    h = stats.heresies(films, min_votes=30)
    assert "C" not in set(h["Name"])          # sem nota do usuário
    d = h.set_index("Name")["diff"]
    assert d["A"] == 5.0 - 4.4                # 8.8/2
    assert d["D"] == 4.0 - 2.5


def test_longest_streak(diary):
    n, start = stats.longest_streak(diary["Watched Date"])
    assert n == 3
    assert start == pd.Timestamp("2024-01-01")


def test_longest_streak_empty():
    n, start = stats.longest_streak(pd.Series([], dtype="datetime64[ns]"))
    assert n == 0 and start is None


def test_busiest_day(diary):
    day, n = stats.busiest_day(diary)
    assert n == 1


def test_most_rewatched(diary):
    rw = stats.most_rewatched(diary)
    assert rw["A"] == 2 and "B" not in rw


def test_rating_over_time(films, diary):
    # min_count padrão é 10; aqui só valida que não explode e retorna Series
    s = stats.rating_over_time(diary, films)
    assert isinstance(s, pd.Series)


def test_genre_trend(films, diary):
    t = stats.genre_trend(diary, films)
    assert not t.empty
    # proporções somam 1 em cada ano
    assert (t.sum(axis=1).round(6) == 1).all()


def test_watch_gap(films, diary):
    g = stats.watch_gap(films, diary)
    assert (g >= 0).all()
    assert g.max() == 2024 - 1994
