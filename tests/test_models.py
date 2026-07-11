"""Testes de propriedade da camada de modelagem (models.py)."""

import numpy as np
import pandas as pd
import pytest

from letterboxd_explorer import models, stats


def _big_films(n=200, seed=1):
    rng = np.random.default_rng(seed)
    genres = ["Drama", "Comédia", "Terror", "Ação"]
    langs = ["en", "pt", "fr"]
    g = [list(rng.choice(genres, size=rng.integers(1, 3), replace=False))
         for _ in range(n)]
    year = rng.integers(1960, 2026, n)
    runtime = rng.integers(70, 180, n)
    votes = rng.integers(10, 100_000, n)
    lang = rng.choice(langs, n)
    base = 3.0 + 0.6 * np.array(["Drama" in x for x in g]) \
        - 0.4 * np.array(["Ação" in x for x in g]) \
        + rng.normal(0, 0.4, n)
    return pd.DataFrame({
        "Name": [f"F{i}" for i in range(n)],
        "Year": pd.array(year, dtype="Int64"),
        "Rating": np.clip(np.round(base * 2) / 2, 0.5, 5.0),
        "genres": g,
        "directors": [[f"D{i % 12}"] for i in range(n)],
        "language": lang,
        "runtime": runtime,
        "tmdb_votes": votes,
        "tmdb_rating": rng.uniform(4, 9, n),
        "keywords": [["noir"] if i % 3 == 0 else ["space"] for i in range(n)],
    })


# ------------------------------------------------------------------ ridge


def test_ridge_recovers_signal():
    films = _big_films()
    m = models.rating_model(films)
    assert m is not None
    eff = m["effects"]
    drama = eff.loc["gênero: Drama", "coef"]
    acao = eff.loc["gênero: Ação", "coef"]
    assert drama > acao  # sinal plantado nos dados
    assert 0 <= m["r2"] <= 1


def test_ridge_ci_positive_and_shrinks_with_n():
    films = _big_films(400)
    m = models.rating_model(films)
    assert (m["effects"]["se"] >= 0).all()


def test_rating_model_small_sample_returns_none():
    films = _big_films(30)
    assert models.rating_model(films) is None


def test_importance_nonnegative():
    m = models.rating_model(_big_films())
    assert (m["importance"] >= 0).all()


def test_cv_metrics_present_and_sane():
    m = models.rating_model(_big_films(300))
    assert np.isfinite(m["cv_r2"]) and np.isfinite(m["cv_mae"])
    assert m["cv_mae"] >= 0
    assert m["cv_r2"] <= m["r2"] + 1e-9  # fora da amostra não supera o treino
    assert m["alpha"] in (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)  # veio do grid de CV
    assert m["cv_pred"].index.equals(
        _big_films(300).dropna(subset=["Rating"]).index)


def test_select_alpha_returns_from_grid():
    films = _big_films(200)
    spec = models.build_spec(films)
    X = models.transform(films, spec)
    a, r2 = models.select_alpha(X, films["Rating"])
    assert a in (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)


# ------------------------------------------------------------------ B1


def test_rank_watchlist_within_scale():
    films = _big_films()
    wl = _big_films(40, seed=9).drop(columns=["Rating"])
    wl["Rating"] = pd.NA
    ranked = models.rank_watchlist(films, wl)
    assert ranked is not None
    assert ranked["pred"].between(0.5, 5.0).all()
    # ordenada de forma decrescente
    assert ranked["pred"].is_monotonic_decreasing


def test_rank_watchlist_empty():
    films = _big_films()
    assert models.rank_watchlist(films, pd.DataFrame()) is None


def test_rank_watchlist_prediction_interval():
    films = _big_films()
    wl = _big_films(40, seed=9).drop(columns=["Rating"])
    wl["Rating"] = pd.NA
    ranked = models.rank_watchlist(films, wl)
    assert {"pred_lo", "pred_hi"} <= set(ranked.columns)
    assert (ranked["pred_lo"] <= ranked["pred"] + 1e-9).all()
    assert (ranked["pred"] <= ranked["pred_hi"] + 1e-9).all()
    assert (ranked["pred_hi"] >= ranked["pred_lo"]).all()


def test_rank_watchlist_diversify_valid():
    films = _big_films(200)
    wl = _big_films(80, seed=9).drop(columns=["Rating"])
    wl["Rating"] = pd.NA
    ranked = models.rank_watchlist(films, wl, top=10, diversify=0.3)
    assert ranked is not None
    assert len(ranked) <= 10
    assert ranked["pred"].between(0.5, 5.0).all()
    assert {"pred_lo", "pred_hi"} <= set(ranked.columns)


def test_mmr_pure_relevance_matches_topk():
    # lam=1 (só relevância) deve escolher os top-k por score, em ordem
    scores = np.array([0.1, 0.9, 0.5, 0.7])
    feats = np.eye(4)
    order = models._mmr_order(scores, feats, lam=1.0, top=2)
    assert order[0] == 1 and order[1] == 3


def test_rating_calibration_shape():
    cal = models.rating_calibration(_big_films(300))
    assert cal is not None
    assert {"pred", "real", "lo", "hi", "n"} <= set(cal.columns)
    assert (cal["hi"] >= cal["lo"]).all()
    assert int(cal["n"].sum()) > 0


def test_nonlinear_benchmark_keys():
    b = models.nonlinear_benchmark(_big_films(200))
    assert b is not None
    assert {"ridge_cv_r2", "gbm_cv_r2", "gain", "n"} <= set(b)
    assert b["gain"] == pytest.approx(b["gbm_cv_r2"] - b["ridge_cv_r2"])


# ------------------------------------------------------------------ B4


def test_taste_clusters_shapes():
    films = _big_films(120)
    cl = models.taste_clusters(films)
    assert cl is not None
    assert {"x", "y", "cluster"} <= set(cl["df"].columns)
    assert len(cl["labels"]) >= 2
    # todo filme pertence a exatamente um cluster e o resumo bate
    assert len(cl["df"]) == 120
    assert int(cl["summary"]["n"].sum()) == 120


def test_taste_clusters_reproducible():
    films = _big_films(100)
    a = models.taste_clusters(films, seed=7)["df"]["cluster"]
    b = models.taste_clusters(films, seed=7)["df"]["cluster"]
    assert (a == b).all()


# ------------------------------------------------------------- stats: propriedades


def test_shrinkage_never_extrapolates():
    films = _big_films()
    g = stats.shrunk_group(films, "genres", min_count=3)
    prior = films["Rating"].dropna().mean()
    for _, row in g.iterrows():
        lo, hi = sorted([row["mean"], prior])
        assert lo - 1e-9 <= row["bayes"] <= hi + 1e-9


def test_entropy_bounds():
    assert stats.shannon_entropy([]) == 0.0
    assert stats.shannon_entropy([5]) == 0.0
    k = 7
    h = stats.shannon_entropy([1] * k)
    assert h == pytest.approx(np.log(k))
    assert 0 <= stats.shannon_entropy([3, 1, 1]) <= np.log(3)


def test_calibration_separates_scale_from_taste(films):
    big = _big_films()
    cal = stats.calibration(big, min_votes=0)
    assert cal is not None
    assert -1 <= cal["spearman"] <= 1
    assert abs(cal["df"]["z_user"].mean()) < 1e-9  # padronizado


def test_seasonality_test_needs_volume(films, diary):
    assert stats.seasonality_test(diary, films) is None  # amostra pequena


def test_sentiment_score_bounds():
    reviews = pd.DataFrame({
        "Name": [f"F{i}" for i in range(12)],
        "Year": [2000] * 12,
        "Rating": [4.5, 1.0] * 6,
        "Review": ["amazing beautiful perfect", "boring awful terrible"] * 6,
    })
    s = stats.review_sentiment(reviews)
    assert s is not None
    assert s["score"].between(-1, 1).all()
    assert s.loc[s["Rating"] >= 4, "score"].mean() > \
        s.loc[s["Rating"] <= 2, "score"].mean()


def test_signature_words_spread_beats_burst():
    reviews = pd.DataFrame({
        "Name": [f"F{i}" for i in range(8)],
        "Year": [2000] * 8,
        # "cinema" aparece 1x em cada resenha; "zumbi" 8x numa só
        "Review": ["cinema clássico sempre"] * 7
        + ["cinema " + "zumbi " * 8],
    })
    sig = stats.signature_words(reviews, min_reviews=2)
    assert sig is not None
    assert sig.index[0] == "cinema"
