"""Funções de análise: puras e testáveis, sem I/O nem plotagem."""

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
    """Filmes por (ano, semana ISO), para o calendário de atividade.

    Anos sem nenhum filme entram como linhas de zeros: sem isso o eixo
    pula anos e as células parecem se fundir no heatmap.
    """
    iso = diary["Watched Date"].dt.isocalendar()
    ct = pd.crosstab(iso["year"], iso["week"])
    if len(ct):
        anos = range(int(ct.index.min()), int(ct.index.max()) + 1)
        ct = ct.reindex(anos, fill_value=0)
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
    bem abaixo de você: os favoritos que são genuinamente seus.
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


# léxico compacto pt/en — heurístico; o relatório sinaliza a limitação
SENT_POS = {
    "ótimo", "otimo", "excelente", "lindo", "linda", "incrível", "incrivel",
    "maravilhoso", "maravilhosa", "perfeito", "perfeita", "adorei", "amei",
    "amo", "bom", "boa", "melhor", "genial", "belíssimo", "belissimo",
    "emocionante", "divertido", "divertida", "impecável", "impecavel",
    "obra-prima", "sensacional", "espetacular", "brilhante", "encantador",
    "delicado", "delicada", "favorito", "favorita", "gostei", "surpreendente",
    "great", "amazing", "beautiful", "brilliant", "perfect", "masterpiece",
    "love", "loved", "wonderful", "excellent", "stunning", "incredible",
    "fantastic", "gorgeous", "delightful", "favorite", "best", "good",
    "charming", "moving", "touching", "fun", "enjoyable", "superb",
}
SENT_NEG = {
    "ruim", "péssimo", "pessimo", "horrível", "horrivel", "chato", "chata",
    "fraco", "fraca", "pior", "terrível", "terrivel", "decepcionante",
    "decepção", "decepcao", "cansativo", "cansativa", "arrastado",
    "arrastada", "sem-graça", "odiei", "detestei", "raso", "rasa",
    "previsível", "previsivel", "confuso", "confusa", "entediante", "bobo",
    "boba", "preguiçoso", "preguicoso", "vazio", "vazia", "mediocre",
    "medíocre", "bad", "worst", "terrible", "awful", "boring", "bland",
    "disappointing", "disappointment", "mess", "weak", "dull", "annoying",
    "mediocre", "predictable", "tedious", "pointless", "shallow", "hate",
    "hated", "lazy", "forgettable", "flat", "poor",
}


def _tokenize(text: str) -> list[str]:
    import re

    return re.findall(r"[a-zà-üá-ú]{3,}", str(text).lower())


def review_sentiment(reviews: pd.DataFrame,
                     films: pd.DataFrame | None = None) -> pd.DataFrame | None:
    """Sentimento léxico por resenha × sua nota (calibração texto↔estrela).

    score em [-1, 1]: (positivas − negativas) / (positivas + negativas).
    Retorna DataFrame com Name, Rating, score, n_words. None se faltar dado.
    """
    if reviews is None or "Review" not in reviews:
        return None
    r = reviews.dropna(subset=["Review"]).copy()
    if "Rating" in r:
        r["Rating"] = pd.to_numeric(r["Rating"], errors="coerce")
    if ("Rating" not in r or r["Rating"].isna().all()) and films is not None:
        r = r.drop(columns=["Rating"], errors="ignore").merge(
            films[["Name", "Year", "Rating"]], on=["Name", "Year"], how="left")
    r = r.dropna(subset=["Rating"])
    if len(r) < 10:
        return None
    rows = []
    for t in r.itertuples():
        words = _tokenize(t.Review)
        pos = sum(w in SENT_POS for w in words)
        neg = sum(w in SENT_NEG for w in words)
        if pos + neg == 0:
            continue
        rows.append({"Name": t.Name, "Rating": float(t.Rating),
                     "score": (pos - neg) / (pos + neg),
                     "n_words": len(words)})
    if len(rows) < 10:
        return None
    return pd.DataFrame(rows)


def signature_words(reviews: pd.DataFrame, top: int = 20,
                    min_reviews: int = 3) -> pd.DataFrame | None:
    """Palavras-assinatura: frequentes E espalhadas por muitas resenhas.

    score = ocorrências × log(1 + nº de resenhas em que aparece); evita que
    uma única resenha longa domine o ranking (diferente da contagem crua).
    """
    import numpy as np

    if reviews is None or "Review" not in reviews:
        return None
    texts = reviews["Review"].dropna().astype(str)
    if len(texts) < min_reviews * 2:
        return None
    tf: dict[str, int] = {}
    df: dict[str, int] = {}
    for t in texts:
        words = [w for w in _tokenize(t) if w not in STOPWORDS]
        for w in words:
            tf[w] = tf.get(w, 0) + 1
        for w in set(words):
            df[w] = df.get(w, 0) + 1
    rows = [{"word": w, "tf": c, "df": df[w],
             "score": c * np.log1p(df[w])}
            for w, c in tf.items() if df[w] >= min_reviews]
    if not rows:
        return None
    out = pd.DataFrame(rows).sort_values("score", ascending=False).head(top)
    return out.set_index("word")


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


# ------------------------------------------------------------------
# Encolhimento bayesiano com incerteza (A3)
# ------------------------------------------------------------------


def shrunk_group(films: pd.DataFrame, col: str, min_count: int = 3,
                 m: int = 5, top: int = 12) -> pd.DataFrame:
    """Nota média por grupo com encolhimento bayesiano e IC aproximado.

    Retorna colunas: n, mean (crua), bayes (encolhida) e ci (meia-largura de
    um intervalo ~95% da média posterior: sigma_global / sqrt(n + m)).
    O encolhimento nunca extrapola o intervalo [mean, prior].
    """
    cols = ["n", "mean", "bayes", "ci"]
    if col not in films:
        return pd.DataFrame(columns=cols)
    rated = films.dropna(subset=["Rating"])
    if rated.empty:
        return pd.DataFrame(columns=cols)
    e = rated.explode(col).dropna(subset=[col])
    if e.empty:
        return pd.DataFrame(columns=cols)
    g = e.groupby(col)["Rating"].agg(n="count", mean="mean")
    g = g[g["n"] >= min_count]
    if g.empty:
        return pd.DataFrame(columns=cols)
    prior = float(rated["Rating"].mean())
    sigma = float(rated["Rating"].std()) or 0.5
    g["bayes"] = (g["n"] * g["mean"] + m * prior) / (g["n"] + m)
    g["ci"] = 1.96 * sigma / (g["n"] + m) ** 0.5
    return g.sort_values("bayes", ascending=False).head(top)


# ------------------------------------------------------------------
# Calibração você × TMDB (A2)
# ------------------------------------------------------------------


def calibration(films: pd.DataFrame, min_votes: int = 30) -> dict | None:
    """Separa calibração de régua de discordância de gosto.

    Retorna dict com: spearman (rho, p), offset médio bruto (em ★),
    e um DataFrame `df` com as notas padronizadas (z_user, z_tmdb, z_diff).
    """
    from scipy import stats as sps

    if "tmdb_rating" not in films:
        return None
    both = films.dropna(subset=["Rating", "tmdb_rating"]).copy()
    if "tmdb_votes" in both:
        both = both[both["tmdb_votes"].fillna(0) >= min_votes]
    if len(both) < 20:
        return None
    u, t = both["Rating"], both["tmdb_rating"]
    if u.std() == 0 or t.std() == 0:
        return None
    rho, p = sps.spearmanr(u, t)
    both["z_user"] = (u - u.mean()) / u.std()
    both["z_tmdb"] = (t - t.mean()) / t.std()
    both["z_diff"] = both["z_user"] - both["z_tmdb"]
    return {
        "spearman": float(rho), "p": float(p),
        "offset": float((u - t / 2).mean()),
        "n": len(both), "df": both,
    }


# ------------------------------------------------------------------
# Sazonalidade testada (A5)
# ------------------------------------------------------------------


def seasonality_test(diary: pd.DataFrame, films: pd.DataFrame,
                     top_n: int = 8) -> dict | None:
    """Qui-quadrado gênero × mês + lift observado/esperado por célula.

    Retorna dict: lift (DataFrame gênero × mês), resid (residuais
    padronizados), chi2, p, dof, n.
    """
    from scipy.stats import chi2_contingency

    if "genres" not in films:
        return None
    merged = diary.merge(films[["Name", "Year", "genres"]],
                         on=["Name", "Year"], how="left")
    merged = merged.dropna(subset=["genres"]).explode("genres")
    merged = merged.reset_index(drop=True)
    if len(merged) < 100:
        return None
    top = merged["genres"].value_counts().head(top_n).index
    merged = merged[merged["genres"].isin(top)]
    ct = pd.crosstab(merged["genres"], merged["Watched Date"].dt.month)
    ct = ct.loc[:, ct.sum(axis=0) > 0]  # meses sem filme ficam fora do teste
    if ct.shape[0] < 2 or ct.shape[1] < 2 or (ct.sum(axis=1) == 0).any():
        return None
    chi2, p, dof, expected = chi2_contingency(ct.values)
    expected = pd.DataFrame(expected, index=ct.index, columns=ct.columns)
    lift = (ct / expected).reindex(columns=range(1, 13))
    resid = ((ct - expected) / expected.pow(0.5)).reindex(columns=range(1, 13))
    return {"lift": lift, "resid": resid, "chi2": float(chi2),
            "p": float(p), "dof": int(dof), "n": int(ct.values.sum())}


# ------------------------------------------------------------------
# Exploração × explotação (B3)
# ------------------------------------------------------------------


def shannon_entropy(counts) -> float:
    """Entropia de Shannon em nats. Sempre em [0, log(k)]."""
    import numpy as np

    v = np.asarray(counts, dtype=float)
    v = v[v > 0]
    if len(v) == 0:
        return 0.0
    ps = v / v.sum()
    return float(-(ps * np.log(ps)).sum())


def exploration_by_year(diary: pd.DataFrame, films: pd.DataFrame,
                        min_per_year: int = 15) -> pd.DataFrame:
    """Por ano do diário: entropia normalizada de gêneros e taxa de novidade.

    entropy: H(gêneros)/log(k) em [0, 1] (repertório do ano é variado?).
    novel_*: fração de diretores/países vistos pela 1ª vez naquele ano.
    """
    import numpy as np

    cols = ["n", "entropy", "novel_directors", "novel_countries"]
    meta = [c for c in ("genres", "directors", "countries") if c in films]
    if not meta:
        return pd.DataFrame(columns=cols)
    d = diary.merge(films[["Name", "Year"] + meta], on=["Name", "Year"],
                    how="left")
    d["_y"] = d["Watched Date"].dt.year
    seen: dict[str, set] = {"directors": set(), "countries": set()}
    rows = []
    for y in sorted(d["_y"].unique()):
        dy = d[d["_y"] == y]
        row: dict = {"year": int(y), "n": len(dy)}
        if "genres" in dy:
            counts = dy["genres"].dropna().explode().value_counts()
            k = len(counts)
            row["entropy"] = (shannon_entropy(counts) / np.log(k)
                              if k > 1 else 0.0)
        for col in ("directors", "countries"):
            if col not in dy:
                continue
            vals = set(dy[col].dropna().explode().dropna())
            if vals:
                new = vals - seen[col]
                row[f"novel_{col}"] = len(new) / len(vals)
                seen[col] |= vals
        rows.append(row)
    out = pd.DataFrame(rows).set_index("year")
    return out[out["n"] >= min_per_year]


# ------------------------------------------------------------------
# Índice mainstream ↔ cult como série (B7)
# ------------------------------------------------------------------


def obscurity_by_year(diary: pd.DataFrame, films: pd.DataFrame,
                      min_per_year: int = 15) -> pd.DataFrame:
    """Obscuridade média por ano do diário: -log10(votos TMDB + 1).

    Quanto maior, mais nichado o ano. Colunas: mean, ci (IC95), n.
    """
    import numpy as np

    if "tmdb_votes" not in films:
        return pd.DataFrame(columns=["mean", "ci", "n"])
    d = diary.merge(films[["Name", "Year", "tmdb_votes"]],
                    on=["Name", "Year"], how="left")
    d = d.dropna(subset=["tmdb_votes"])
    if d.empty:
        return pd.DataFrame(columns=["mean", "ci", "n"])
    d["obsc"] = -np.log10(d["tmdb_votes"].astype(float) + 1)
    g = d.groupby(d["Watched Date"].dt.year)["obsc"].agg(
        mean="mean", std="std", n="count")
    g = g[g["n"] >= min_per_year]
    g["ci"] = 1.96 * g["std"].fillna(0) / g["n"] ** 0.5
    return g[["mean", "ci", "n"]]


# ------------------------------------------------------------------
# Descoberta e retenção de diretores (B8)
# ------------------------------------------------------------------


def director_retention(films: pd.DataFrame) -> pd.DataFrame | None:
    """Quantos diretores você viu 1×, 2×, 3×... (curva de retenção).

    Retorna DataFrame indexado pelo nº de filmes vistos com a contagem
    de diretores em cada degrau.
    """
    if "directors" not in films:
        return None
    e = films.explode("directors").dropna(subset=["directors"])
    if e.empty:
        return None
    per_dir = e.groupby("directors").size()
    steps = per_dir.value_counts().sort_index()
    steps.index.name = "filmes_vistos"
    return steps.to_frame("diretores")


def hooked_directors(films: pd.DataFrame, diary: pd.DataFrame | None,
                     min_films: int = 3, top: int = 10) -> pd.DataFrame:
    """Diretores que 'fisgaram': 3+ filmes, com data da descoberta se houver."""
    if "directors" not in films:
        return pd.DataFrame()
    e = films.explode("directors").dropna(subset=["directors"])
    agg = e.groupby("directors").agg(n=("Name", "count"),
                                     nota=("Rating", "mean"))
    agg = agg[agg["n"] >= min_films].nlargest(top, "n")
    if diary is not None and len(diary) and "directors" in films:
        d = diary.merge(films[["Name", "Year", "directors"]],
                        on=["Name", "Year"], how="left")
        d = d.explode("directors").dropna(subset=["directors"])
        first = d.groupby("directors")["Watched Date"].min()
        agg["descoberta"] = first.reindex(agg.index)
    return agg


# ------------------------------------------------------------------
# Percentil do gosto (B10)
# ------------------------------------------------------------------


def taste_outlier_share(films: pd.DataFrame, min_votes: int = 30) -> dict | None:
    """Quão fora da curva você é: % de filmes onde sua nota padronizada
    diverge da do TMDB em mais de 1 desvio."""
    cal = calibration(films, min_votes)
    if cal is None:
        return None
    z = cal["df"]["z_diff"]
    return {
        "outlier_share": float((z.abs() > 1).mean()),
        "above_share": float((z > 0).mean()),
        "n": int(len(z)),
    }


# ------------------------------------------------------------------
# Efeito rewatch e mudança de regime (B11)
# ------------------------------------------------------------------


def rewatch_effect(diary: pd.DataFrame) -> dict | None:
    """Rewatch vs. primeira sessão: médias, n e teste t de Welch."""
    from scipy import stats as sps

    d = diary.dropna(subset=["Rating"])
    rw, first = d[d["Rewatch"]], d[~d["Rewatch"]]
    if len(rw) < 5 or len(first) < 5:
        return None
    t, p = sps.ttest_ind(rw["Rating"], first["Rating"], equal_var=False)
    return {"rewatch_mean": float(rw["Rating"].mean()),
            "first_mean": float(first["Rating"].mean()),
            "n_rewatch": len(rw), "n_first": len(first), "p": float(p)}


def activity_changepoint(diary: pd.DataFrame) -> dict | None:
    """Ponto único de mudança de regime no volume mensal (segmentação binária).

    Retorna o mês da quebra e as médias antes/depois, se a diferença for
    significativa (teste t, p < 0.05) e cada segmento tiver 6+ meses.
    """
    from scipy import stats as sps

    m = diary.set_index("Watched Date").resample("ME").size()
    if len(m) < 12:
        return None
    best, best_stat = None, 0.0
    vals = m.values.astype(float)
    for i in range(6, len(m) - 6):
        a, b = vals[:i], vals[i:]
        denom = (a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) ** 0.5
        if denom == 0:
            continue
        stat = abs(a.mean() - b.mean()) / denom
        if stat > best_stat:
            best_stat, best = stat, i
    if best is None:
        return None
    a, b = vals[:best], vals[best:]
    t, p = sps.ttest_ind(a, b, equal_var=False)
    if p >= 0.05:
        return None
    return {"date": m.index[best], "before": float(a.mean()),
            "after": float(b.mean()), "p": float(p)}


# ------------------------------------------------------------------
# Representação de gênero (B6) — requer cache TMDB com campo gender
# ------------------------------------------------------------------


def gender_representation(films: pd.DataFrame, diary: pd.DataFrame | None,
                          min_per_year: int = 15) -> pd.DataFrame | None:
    """% de filmes com direção feminina por ano do diário + cobertura.

    O campo `gender` do TMDB é incompleto e binário-centrado; a coluna
    `coverage` informa a fração de filmes com o dado preenchido.
    """
    if "directors_gender" not in films or diary is None or not len(diary):
        return None
    d = diary.merge(films[["Name", "Year", "directors_gender"]],
                    on=["Name", "Year"], how="left")
    d["_known"] = d["directors_gender"].map(
        lambda g: isinstance(g, list) and any(x in (1, 2, 3) for x in g))
    d["_fem"] = d["directors_gender"].map(
        lambda g: isinstance(g, list) and 1 in g)
    g = d.groupby(d["Watched Date"].dt.year).agg(
        n=("_known", "size"), known=("_known", "sum"), fem=("_fem", "sum"))
    g = g[g["n"] >= min_per_year]
    if g.empty or g["known"].sum() == 0:
        return None
    g["pct_fem"] = g["fem"] / g["known"].replace(0, pd.NA)
    g["coverage"] = g["known"] / g["n"]
    return g


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
