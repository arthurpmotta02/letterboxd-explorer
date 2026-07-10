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


def test_weekly_calendar(diary):
    cal = stats.weekly_calendar(diary)
    assert cal.values.sum() == len(diary)
    assert list(cal.columns) == list(range(1, 54))


def test_cumulative_films(diary):
    c = stats.cumulative_films(diary)
    assert c.iloc[-1] == len(diary)
    assert c.is_monotonic_increasing


def test_rating_by_decade(films):
    rd = stats.rating_by_decade(films, min_count=1)
    assert rd.loc[1990, "mean"] == 5.0
    assert rd.loc[2010, "count"] == 1  # só "D" tem nota em 2010


def test_rating_by_runtime(films):
    rr = stats.rating_by_runtime(films, min_count=1)
    assert rr["count"].sum() == 3  # A, B, D têm nota e duração


def test_personal_favorites(films):
    pf = stats.personal_favorites(films, min_rating=3.0)
    # diff: A = 5.0-4.4 = 0.6 ; D = 4.0-2.5 = 1.5 ; B = 3.5-3.0 = 0.5
    assert list(pf["Name"]) == ["D", "A", "B"]


def test_personal_favorites_excludes_zero_votes(films):
    films = films.copy()
    films.loc[0, "tmdb_rating"] = 0.0   # "média" sem votos
    films.loc[0, "tmdb_votes"] = 0
    pf = stats.personal_favorites(films, min_rating=3.0)
    assert "A" not in list(pf["Name"])  # diff +5.0 falso não entra


def test_budget_buckets_empty(films):
    assert stats.budget_buckets(films).empty  # fixture sem coluna budget


def test_hipster_and_nostalgia_none_on_small(films):
    assert stats.hipster_index(films) is None  # menos de 20 filmes
    assert stats.nostalgia_gap(films) is None  # menos de 5 por grupo


def test_genre_month(films, diary):
    gm = stats.genre_month(diary, films)
    assert (gm.sum(axis=1).round(6) == 1).all()


def test_director_stats(films):
    ds = stats.director_stats(films, min_count=2, top=10)
    assert list(ds.index) == ["X"] and ds.loc["X", "n"] == 3


def test_review_words_and_longest():
    reviews = pd.DataFrame({
        "Name": ["A", "B"],
        "Review": ["cinema lindo cinema poesia", "cinema brutal e visceral demais"],
    })
    w = stats.review_words(reviews)
    assert w.index[0] == "cinema" and w.iloc[0] == 3
    name, n = stats.longest_review(reviews)
    assert name == "B" and n == 5


def test_watchlist_oldest_and_growth():
    wl = pd.DataFrame({
        "Name": ["X", "Y"], "Year": [2000, 2010],
        "AddedDate": pd.to_datetime(["2022-01-09", "2024-06-01"]),
    })
    old = stats.watchlist_oldest(wl, today="2026-01-09", top=5)
    assert old.iloc[0]["Name"] == "X" and old.iloc[0]["dias"] == 1461
    g = stats.watchlist_growth(wl)
    assert g.iloc[-1] == 2


def test_bayesian_shrinks_small_samples():
    g = pd.DataFrame({"mean": [5.0, 4.0], "count": [1, 40]}, index=["novato", "veterano"])
    b = stats.bayesian_rating(g, prior_mean=3.0, m=5)
    # 1 filme 5★ encolhe muito para o prior; 40 filmes 4★ quase não se movem
    assert b["novato"] < 3.5 and b["veterano"] > 3.85


def test_director_stats_full(films):
    ds = stats.director_stats_full(films, min_count=2)
    assert ds.loc["X", "n"] == 3 and ds.loc["X", "std"] > 0
    # fórmula: (n*nota + 5*prior)/(n+5); aqui prior == nota de X (só X tem notas)
    n, nota = ds.loc["X", "n"], ds.loc["X", "nota"]
    assert abs(ds.loc["X", "bayes"] - (n * nota + 5 * nota) / (n + 5)) < 1e-9


def test_release_vs_watch(films, diary):
    rv = stats.release_vs_watch(films, diary)
    assert (rv["watch_year"] >= rv["release_year"]).all()


def test_genre_rating_contrast(films):
    out = stats.genre_rating_contrast(films, min_count=1)
    assert out is not None and out[2] >= 0


def test_collaboration_edges():
    films = pd.DataFrame({
        "Name": ["f1", "f2", "f3", "f4"],
        "directors": [["Fassbinder"], ["Fassbinder"], ["Fassbinder"], ["Outro"]],
        "cast": [["Schygulla", "X"], ["Schygulla"], ["Y"], ["Z"]],
    })
    pairs = stats.collaboration_edges(films, min_films=2)
    assert pairs.loc[("Fassbinder", "Schygulla")] == 2
    assert ("Outro", "Z") not in pairs.index  # só 1 filme juntos
