"""Funções de análise — puras e testáveis, sem I/O nem plotagem."""

from __future__ import annotations

import pandas as pd


def explode_count(df: pd.DataFrame, col: str, top: int = 15) -> pd.Series:
    """Contagem de valores em uma coluna de listas (gêneros, diretores...)."""
    if col not in df:
        return pd.Series(dtype=int)
    s = df[col].dropna().explode().dropna()
    return s.value_counts().head(top)


def rating_distribution(films: pd.DataFrame) -> pd.Series:
    return films["Rating"].dropna().value_counts().sort_index()


def decade_counts(films: pd.DataFrame) -> pd.Series:
    years = films["Year"].dropna().astype(int)
    return years.floordiv(10).mul(10).value_counts().sort_index()


def group_rating(films: pd.DataFrame, col: str, min_count: int) -> pd.DataFrame:
    """Nota média do usuário por valor de `col` (coluna de listas)."""
    if col not in films:
        return pd.DataFrame(columns=["mean", "count"])
    g = (
        films.dropna(subset=["Rating"])
        .explode(col)
        .dropna(subset=[col])
        .groupby(col)["Rating"]
        .agg(["mean", "count"])
    )
    return g[g["count"] >= min_count]


def heresies(films: pd.DataFrame, min_votes: int = 30) -> pd.DataFrame:
    """Filmes onde sua nota mais diverge do TMDB (diff = sua nota − TMDB/2)."""
    if "tmdb_rating" not in films:
        return pd.DataFrame()
    both = films.dropna(subset=["Rating", "tmdb_rating"]).copy()
    both = both[both["tmdb_votes"].fillna(0) >= min_votes]
    both["tmdb_5"] = both["tmdb_rating"] / 2
    both["diff"] = both["Rating"] - both["tmdb_5"]
    return both


def longest_streak(dates: pd.Series) -> tuple[int, pd.Timestamp | None]:
    """Maior sequência de dias consecutivos com filme. Retorna (dias, início)."""
    days = pd.Series(sorted(dates.dt.normalize().unique()))
    if days.empty:
        return 0, None
    gaps = days.diff().dt.days.ne(1).cumsum()
    runs = days.groupby(gaps).agg(["size", "first"])
    best = runs.loc[runs["size"].idxmax()]
    return int(best["size"]), best["first"]


def busiest_day(diary: pd.DataFrame) -> tuple[pd.Timestamp | None, int]:
    per_day = diary.groupby(diary["Watched Date"].dt.normalize()).size()
    if per_day.empty:
        return None, 0
    return per_day.idxmax(), int(per_day.max())


def most_rewatched(diary: pd.DataFrame, top: int = 10) -> pd.Series:
    """Filmes com mais entradas no diário (assistidos 2+ vezes)."""
    counts = diary.groupby("Name").size()
    return counts[counts >= 2].sort_values(ascending=False).head(top)


def rating_over_time(diary: pd.DataFrame, films: pd.DataFrame) -> pd.Series:
    """Nota média por ano em que você assistiu (você está ficando mais generoso?)."""
    d = diary.copy()
    if d["Rating"].isna().all():
        d = d.drop(columns=["Rating"]).merge(
            films[["Name", "Year", "Rating"]], on=["Name", "Year"], how="left"
        )
    d = d.dropna(subset=["Rating"])
    if d.empty:
        return pd.Series(dtype=float)
    yearly = d.groupby(d["Watched Date"].dt.year)["Rating"].agg(["mean", "count"])
    return yearly[yearly["count"] >= 10]["mean"]


def genre_trend(diary: pd.DataFrame, films: pd.DataFrame, top_n: int = 6) -> pd.DataFrame:
    """Participação dos gêneros mais vistos, por ano do diário."""
    if "genres" not in films:
        return pd.DataFrame()
    merged = diary.merge(
        films[["Name", "Year", "genres"]], on=["Name", "Year"], how="left"
    )
    merged = merged.dropna(subset=["genres"]).explode("genres")
    if merged.empty:
        return pd.DataFrame()
    top = merged["genres"].value_counts().head(top_n).index
    merged = merged[merged["genres"].isin(top)]
    ct = pd.crosstab(merged["Watched Date"].dt.year, merged["genres"])
    return ct.div(ct.sum(axis=1), axis=0)  # proporção por ano


def watch_gap(films: pd.DataFrame, diary: pd.DataFrame) -> pd.Series:
    """Quantos anos depois do lançamento você assiste (idade do filme ao ver)."""
    merged = diary.dropna(subset=["Year"]).copy()
    gap = merged["Watched Date"].dt.year - merged["Year"].astype(int)
    return gap[gap >= 0]
