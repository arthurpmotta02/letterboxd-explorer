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
    merged = merged.reset_index(drop=True)  # explode duplica índices (pandas 3.x)
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


def weekly_calendar(diary: pd.DataFrame) -> pd.DataFrame:
    """Filmes por (ano, semana ISO), para o calendário de atividade."""
    iso = diary["Watched Date"].dt.isocalendar()
    ct = pd.crosstab(iso["year"], iso["week"])
    return ct.reindex(columns=range(1, 54), fill_value=0)


def cumulative_films(diary: pd.DataFrame) -> pd.Series:
    """Total acumulado de registros no diário ao longo do tempo."""
    return diary.sort_values("Watched Date").groupby("Watched Date").size().cumsum()


def genre_month(diary: pd.DataFrame, films: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Sazonalidade: distribuição de cada gênero pelos meses (linha soma 1)."""
    if "genres" not in films:
        return pd.DataFrame()
    merged = diary.merge(films[["Name", "Year", "genres"]], on=["Name", "Year"], how="left")
    merged = merged.dropna(subset=["genres"]).explode("genres")
    merged = merged.reset_index(drop=True)  # explode duplica índices (pandas 3.x)
    if merged.empty:
        return pd.DataFrame()
    top = merged["genres"].value_counts().head(top_n).index
    merged = merged[merged["genres"].isin(top)]
    ct = pd.crosstab(merged["genres"], merged["Watched Date"].dt.month)
    ct = ct.reindex(columns=range(1, 13), fill_value=0)
    return ct.div(ct.sum(axis=1), axis=0)


def rating_by_decade(films: pd.DataFrame, min_count: int = 5) -> pd.DataFrame:
    """Sua nota média por década de lançamento (viés de nostalgia)."""
    rated = films.dropna(subset=["Rating"])
    rated = rated[rated["Year"].notna()]
    if rated.empty:
        return pd.DataFrame(columns=["mean", "count"])
    dec = rated["Year"].astype(int).floordiv(10).mul(10)
    g = rated.groupby(dec)["Rating"].agg(["mean", "count"])
    return g[g["count"] >= min_count]


def rating_by_runtime(films: pd.DataFrame, min_count: int = 5) -> pd.DataFrame:
    """Nota média por faixa de duração."""
    if "runtime" not in films:
        return pd.DataFrame(columns=["mean", "count"])
    rated = films.dropna(subset=["Rating", "runtime"])
    rated = rated[rated["runtime"] > 0]
    if rated.empty:
        return pd.DataFrame(columns=["mean", "count"])
    bins = [0, 40, 90, 120, 150, 180, float("inf")]
    labels = ["curta (≤40 min)", "40 a 90", "90 a 120", "120 a 150",
              "150 a 180", "mais de 180"]
    faixa = pd.cut(rated["runtime"], bins=bins, labels=labels)
    g = rated.groupby(faixa, observed=False)["Rating"].agg(["mean", "count"])
    return g[g["count"] >= min_count]


def personal_favorites(films: pd.DataFrame, top: int = 10,
                       min_rating: float = 4.5, min_votes: int = 30) -> pd.DataFrame:
    """Entre suas maiores notas, os filmes mais distantes da nota TMDB.

    Ranquear os 5 estrelas entre si não faz sentido (empate). O que é
    informativo é: dos filmes que você ama, quais o resto do mundo avalia
    bem abaixo de você — os favoritos que são genuinamente seus.
    """
    rated = films.dropna(subset=["Rating"])
    rated = rated[rated["Rating"] >= min_rating]
    if "tmdb_rating" not in films or rated.empty:
        return rated.head(0)
    rated = rated.dropna(subset=["tmdb_rating"]).copy()
    # nota TMDB com poucos votos não é comparável (0 votos => média 0.0)
    if "tmdb_votes" in rated:
        rated = rated[rated["tmdb_votes"].fillna(0) >= min_votes]
    rated["diff"] = rated["Rating"] - rated["tmdb_rating"] / 2
    return rated.sort_values("diff", ascending=False).head(top)


def budget_buckets(films: pd.DataFrame) -> pd.Series:
    """Quantos filmes por faixa de orçamento de produção."""
    if "budget" not in films:
        return pd.Series(dtype=int)
    b = pd.to_numeric(films["budget"], errors="coerce").fillna(0)
    b = b[b > 0]
    if b.empty:
        return pd.Series(dtype=int)
    bins = [0, 1e6, 20e6, 100e6, float("inf")]
    labels = ["indie (< $1M)", "médio ($1M a $20M)",
              "grande ($20M a $100M)", "blockbuster (> $100M)"]
    return pd.cut(b, bins=bins, labels=labels).value_counts().reindex(labels, fill_value=0)


def hipster_index(films: pd.DataFrame, vote_cut: int = 1000) -> float | None:
    """Fração dos seus filmes com poucos votos no TMDB."""
    if "tmdb_votes" not in films:
        return None
    v = films["tmdb_votes"].dropna()
    if len(v) < 20:
        return None
    return float((v < vote_cut).mean())


def nostalgia_gap(films: pd.DataFrame) -> float | None:
    """Diferença de nota média: filmes pré-1980 menos filmes pós-2000."""
    rated = films.dropna(subset=["Rating"])
    rated = rated[rated["Year"].notna()]
    old = rated[rated["Year"].astype(int) < 1980]["Rating"]
    new = rated[rated["Year"].astype(int) >= 2000]["Rating"]
    if len(old) >= 5 and len(new) >= 5:
        return float(old.mean() - new.mean())
    return None


def director_stats(films: pd.DataFrame, min_count: int = 3, top: int = 25) -> pd.DataFrame:
    """Por diretor: quantos filmes você viu e sua nota média (para scatter)."""
    if "directors" not in films:
        return pd.DataFrame(columns=["n", "nota"])
    ds = films.explode("directors").dropna(subset=["directors"])
    agg = ds.groupby("directors").agg(n=("Name", "count"), nota=("Rating", "mean"))
    agg = agg.dropna(subset=["nota"])
    return agg[agg["n"] >= min_count].nlargest(top, "n")


STOPWORDS = {
    # pt
    "que", "não", "nao", "com", "uma", "por", "para", "mais", "the", "and",
    "dos", "das", "ele", "ela", "isso", "esse", "essa", "este", "esta",
    "mas", "como", "muito", "bem", "ser", "tem", "foi", "era", "são", "sao",
    "você", "voce", "seu", "sua", "meu", "minha", "nos", "nós", "até", "ate",
    "quando", "porque", "sobre", "depois", "ainda", "coisa", "filme", "filmes",
    "aqui", "todo", "toda", "todos", "todas", "só", "las", "los", "des", "num",
    "numa", "pra", "pro", "vai", "ver", "assistir", "assisti", "ficou", "fica",
    # en
    "this", "that", "with", "for", "was", "are", "but", "not", "you", "his",
    "her", "have", "has", "one", "all", "its", "movie", "film", "just",
    "like", "really", "very", "what", "when", "there", "they", "out", "about",
    "from", "would", "been", "were", "more", "some", "can", "much", "get",
}


def review_words(reviews: pd.DataFrame, top: int = 25) -> pd.Series:
    """Palavras mais frequentes nas suas resenhas (sem stopwords pt/en)."""
    import re

    if reviews is None or "Review" not in reviews:
        return pd.Series(dtype=int)
    text = " ".join(reviews["Review"].dropna().astype(str)).lower()
    words = re.findall(r"[a-zà-üá-ú]{3,}", text)
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return pd.Series(dtype=int)
    return pd.Series(words).value_counts().head(top)


def longest_review(reviews: pd.DataFrame):
    """(nome do filme, nº de palavras) da resenha mais longa."""
    if reviews is None or "Review" not in reviews:
        return None
    r = reviews.dropna(subset=["Review"]).copy()
    if r.empty:
        return None
    r["_w"] = r["Review"].astype(str).str.split().str.len()
    best = r.loc[r["_w"].idxmax()]
    return str(best["Name"]), int(best["_w"])


def watchlist_growth(watchlist: pd.DataFrame) -> pd.Series:
    """Crescimento acumulado da watchlist (por data de adição)."""
    if watchlist is None or "AddedDate" not in watchlist:
        return pd.Series(dtype=int)
    w = watchlist.dropna(subset=["AddedDate"])
    return w.sort_values("AddedDate").groupby("AddedDate").size().cumsum()


def watchlist_oldest(watchlist: pd.DataFrame, today=None, top: int = 10) -> pd.DataFrame:
    """Filmes há mais tempo esperando na watchlist (dias desde a adição)."""
    if watchlist is None or "AddedDate" not in watchlist:
        return pd.DataFrame()
    today = pd.Timestamp(today) if today else pd.Timestamp.now().normalize()
    w = watchlist.dropna(subset=["AddedDate"]).copy()
    w["dias"] = (today - w["AddedDate"]).dt.days
    return w.nlargest(top, "dias")[["Name", "Year", "dias"]]


def bayesian_rating(g: pd.DataFrame, prior_mean: float, m: int = 5) -> pd.Series:
    """Média bayesiana: encolhe médias de amostras pequenas para a média global.

    score = (n * média + m * média_global) / (n + m)
    """
    return (g["count"] * g["mean"] + m * prior_mean) / (g["count"] + m)


def director_stats_full(films: pd.DataFrame, min_count: int = 3,
                        top: int = 25) -> pd.DataFrame:
    """Por diretor: n, nota média, desvio-padrão e média bayesiana."""
    if "directors" not in films:
        return pd.DataFrame(columns=["n", "nota", "std", "bayes"])
    ds = films.explode("directors").dropna(subset=["directors"])
    rated = ds.dropna(subset=["Rating"])
    if rated.empty:
        return pd.DataFrame(columns=["n", "nota", "std", "bayes"])
    agg = rated.groupby("directors")["Rating"].agg(
        n="count", nota="mean", std="std")
    agg["std"] = agg["std"].fillna(0)
    prior = rated["Rating"].mean()
    agg["bayes"] = (agg["n"] * agg["nota"] + 5 * prior) / (agg["n"] + 5)
    return agg[agg["n"] >= min_count].nlargest(top, "n")


def release_vs_watch(films: pd.DataFrame, diary: pd.DataFrame) -> pd.DataFrame:
    """Ano de lançamento × ano em que você assistiu, com nota quando houver."""
    d = diary.dropna(subset=["Year"]).copy()
    d["watch_year"] = d["Watched Date"].dt.year
    d["release_year"] = d["Year"].astype(int)
    d = d[d["watch_year"] >= d["release_year"]]
    if d["Rating"].isna().all():
        d = d.drop(columns=["Rating"]).merge(
            films[["Name", "Year", "Rating"]], on=["Name", "Year"], how="left")
    return d[["Name", "release_year", "watch_year", "Rating"]]


def genre_rating_contrast(films: pd.DataFrame, min_count: int = 10):
    """(gênero_top, gênero_bottom, diferença) por nota média bayesiana."""
    g = group_rating(films, "genres", min_count=min_count)
    if len(g) < 2:
        return None
    rated = films.dropna(subset=["Rating"])
    bayes = bayesian_rating(g, prior_mean=rated["Rating"].mean())
    hi, lo = bayes.idxmax(), bayes.idxmin()
    return hi, lo, float(g.loc[hi, "mean"] - g.loc[lo, "mean"])


def binned_trend(x: pd.Series, y: pd.Series, bins: int = 8):
    """Tendência por quantis de x (robusta, sem dependência extra): médias por faixa."""
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(df) < bins * 4:
        return None
    df["bin"] = pd.qcut(df["x"], q=bins, duplicates="drop")
    g = df.groupby("bin", observed=True).agg(x=("x", "median"), y=("y", "mean"))
    return g["x"].values, g["y"].values


def collaboration_edges(films: pd.DataFrame, min_films: int = 2,
                        top_directors: int = 12, top_actors: int = 18) -> pd.Series:
    """Parcerias diretor–ator no seu histórico: (diretor, ator) -> nº de filmes.

    Filtrado para ficar legível: só parcerias com `min_films`+ filmes, entre os
    diretores e atores mais recorrentes nessas parcerias.
    """
    if "directors" not in films or "cast" not in films:
        return pd.Series(dtype=int)
    e = films[["Name", "directors", "cast"]].dropna(subset=["directors", "cast"])
    e = e.explode("directors").explode("cast").dropna()
    if e.empty:
        return pd.Series(dtype=int)
    pairs = e.groupby(["directors", "cast"]).size()
    pairs = pairs[pairs >= min_films]
    if pairs.empty:
        return pairs
    keep_d = pairs.groupby(level=0).sum().nlargest(top_directors).index
    pairs = pairs[pairs.index.get_level_values(0).isin(keep_d)]
    keep_a = pairs.groupby(level=1).sum().nlargest(top_actors).index
    return pairs[pairs.index.get_level_values(1).isin(keep_a)]
