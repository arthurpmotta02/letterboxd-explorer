"""Camada de modelagem: ridge analítico + KMeans/PCA (scikit-learn), sem I/O.

Um único modelo linear (ridge) responde quatro perguntas:
  A1  efeitos parciais sobre a sua nota (forest plot com IC);
  A6  generosidade ao longo do tempo controlada pela composição;
  B1  nota prevista para cada filme da watchlist;
  B2  importância de cada família de features (queda de R²).

O ridge é resolvido em forma fechada (numpy) em vez de
sklearn.linear_model.Ridge porque o sklearn não expõe os erros-padrão
dos coeficientes, e os intervalos de confiança são o ponto central do
relatório. Clustering e projeção 2D usam scikit-learn (KMeans, PCA).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ features


@dataclass
class FeatureSpec:
    """Especificação aprendida no treino e reaplicada em dados novos."""

    genres: list[str] = field(default_factory=list)
    decades: list[int] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    watch_years: list[int] = field(default_factory=list)
    runtime_mean: float = 100.0
    votes_mean: float = 3.0
    columns: list[str] = field(default_factory=list)
    families: dict[str, list[str]] = field(default_factory=dict)


def _multi_hot(series: pd.Series, vocab: list[str], prefix: str) -> pd.DataFrame:
    out = pd.DataFrame(0.0, index=series.index, columns=[f"{prefix}{v}" for v in vocab])
    for idx, vals in series.items():
        if isinstance(vals, (list, tuple, set)):
            for v in vals:
                col = f"{prefix}{v}"
                if col in out.columns:
                    out.at[idx, col] = 1.0
    return out


def _first_watch_year(films: pd.DataFrame, diary: pd.DataFrame | None) -> pd.Series:
    if diary is None or not len(diary):
        return pd.Series(pd.NA, index=films.index)
    first = (diary.dropna(subset=["Year"])
             .groupby(["Name", "Year"])["Watched Date"].min()
             .dt.year)
    keys = pd.MultiIndex.from_arrays([films["Name"], films["Year"]])
    return pd.Series(first.reindex(keys).values, index=films.index)


def build_spec(films: pd.DataFrame, diary: pd.DataFrame | None = None,
               min_genre: int = 10, min_director: int = 4,
               min_language: int = 10, min_year: int = 10) -> FeatureSpec:
    """Aprende o vocabulário de features nos filmes AVALIADOS."""
    rated = films.dropna(subset=["Rating"])
    spec = FeatureSpec()

    def _vocab(col, minimum):
        if col not in rated:
            return []
        vc = rated[col].dropna().explode().dropna().value_counts()
        return sorted(vc[vc >= minimum].index.tolist())

    spec.genres = _vocab("genres", min_genre)
    spec.directors = _vocab("directors", min_director)
    if "language" in rated:
        vc = rated["language"].dropna().value_counts()
        spec.languages = sorted(vc[vc >= min_language].index.tolist())
    if rated["Year"].notna().any():
        dec = rated["Year"].dropna().astype(int).floordiv(10).mul(10)
        vc = dec.value_counts()
        spec.decades = sorted(vc[vc >= min_genre].index.tolist())
    wy = _first_watch_year(rated, diary).dropna()
    if len(wy):
        vc = wy.astype(int).value_counts()
        spec.watch_years = sorted(vc[vc >= min_year].index.tolist())
    if "runtime" in rated:
        rt = pd.to_numeric(rated["runtime"], errors="coerce").dropna()
        rt = rt[rt > 0]
        if len(rt):
            spec.runtime_mean = float(rt.mean())
    if "tmdb_votes" in rated:
        lv = np.log10(pd.to_numeric(rated["tmdb_votes"], errors="coerce")
                      .dropna() + 1)
        if len(lv):
            spec.votes_mean = float(lv.mean())
    return spec


def transform(films: pd.DataFrame, spec: FeatureSpec,
              diary: pd.DataFrame | None = None) -> pd.DataFrame:
    """Matriz de features alinhada ao spec (linhas = filmes)."""
    parts: list[pd.DataFrame] = []
    fams: dict[str, list[str]] = {}

    if spec.genres and "genres" in films:
        g = _multi_hot(films["genres"], spec.genres, "gênero: ")
        parts.append(g)
        fams["gênero"] = list(g.columns)
    if spec.decades:
        dec = films["Year"].astype("Float64").floordiv(10).mul(10)
        d = pd.DataFrame({f"década: {int(v)}s":
                          dec.eq(v).fillna(False).astype(float)
                          for v in spec.decades}, index=films.index)
        parts.append(d)
        fams["década"] = list(d.columns)
    if spec.directors and "directors" in films:
        d = _multi_hot(films["directors"], spec.directors, "diretor: ")
        parts.append(d)
        fams["diretor"] = list(d.columns)
    if spec.languages and "language" in films:
        d = pd.DataFrame({f"idioma: {v}": films["language"].eq(v).astype(float)
                          for v in spec.languages}, index=films.index)
        parts.append(d)
        fams["idioma"] = list(d.columns)

    num = pd.DataFrame(index=films.index)
    if "runtime" in films:
        rt = pd.to_numeric(films["runtime"], errors="coerce")
        rt = rt.where(rt > 0)
        num["duração (por hora)"] = (rt.fillna(spec.runtime_mean)
                                     - spec.runtime_mean) / 60.0
    if "tmdb_votes" in films:
        lv = np.log10(pd.to_numeric(films["tmdb_votes"], errors="coerce")
                      .fillna(0) + 1)
        num["popularidade (×10 votos)"] = lv - spec.votes_mean
    if len(num.columns):
        parts.append(num)
        fams["filme"] = list(num.columns)

    if spec.watch_years:
        wy = _first_watch_year(films, diary)
        d = pd.DataFrame({f"visto em {int(v)}": wy.eq(v).astype(float)
                          for v in spec.watch_years}, index=films.index)
        parts.append(d)
        fams["ano em que viu"] = list(d.columns)

    X = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=films.index)
    X = X.fillna(0.0)  # Year/runtime ausentes não podem virar NaN na matriz
    spec.columns = list(X.columns)
    spec.families = fams
    return X


# ------------------------------------------------------------------ ridge


@dataclass
class RidgeFit:
    coef: pd.Series
    se: pd.Series
    intercept: float
    r2: float
    n: int
    alpha: float
    sigma: float


def ridge(X: pd.DataFrame, y: pd.Series, alpha: float = 3.0) -> RidgeFit:
    """Ridge com IC aproximado: Var(β) = σ² A⁻¹ XᵀX A⁻¹, A = XᵀX + αI.

    y é centrado; dummies não são padronizadas (coeficiente já é o efeito
    em ★). O encolhimento do ridge cumpre o papel do prior bayesiano.
    """
    Xv = X.values.astype(float)
    yv = y.values.astype(float)
    n, p = Xv.shape
    ybar = yv.mean()
    yc = yv - ybar
    A = Xv.T @ Xv + alpha * np.eye(p)
    Ainv = np.linalg.inv(A)
    beta = Ainv @ Xv.T @ yc
    resid = yc - Xv @ beta
    dof = max(n - p, 1)
    sigma2 = float(resid @ resid) / dof
    var = sigma2 * (Ainv @ (Xv.T @ Xv) @ Ainv)
    se = np.sqrt(np.clip(np.diag(var), 0, None))
    ss_tot = float(yc @ yc) or 1.0
    r2 = 1.0 - float(resid @ resid) / ss_tot
    return RidgeFit(coef=pd.Series(beta, index=X.columns),
                    se=pd.Series(se, index=X.columns),
                    intercept=float(ybar), r2=r2, n=n,
                    alpha=alpha, sigma=float(np.sqrt(sigma2)))


def predict(fit: RidgeFit, X: pd.DataFrame) -> pd.Series:
    Xv = X[fit.coef.index].values.astype(float)
    return pd.Series(fit.intercept + Xv @ fit.coef.values, index=X.index)


# ------------------------------------------------------------------ A1 + A6


def rating_model(films: pd.DataFrame, diary: pd.DataFrame | None = None,
                 min_n: int = 60, alpha: float = 3.0) -> dict | None:
    """Modelo da nota (A1). Retorna efeitos com IC, R², resíduo por ano (A6)
    e importância por família (B2). None se a amostra for pequena demais."""
    rated = films.dropna(subset=["Rating"]).copy()
    if len(rated) < min_n:
        return None
    spec = build_spec(rated, diary)
    X = transform(rated, spec, diary)
    if X.shape[1] < 3:
        return None
    y = rated["Rating"]
    fit = ridge(X, y, alpha=alpha)

    eff = pd.DataFrame({"coef": fit.coef, "se": fit.se})
    eff["lo"] = eff["coef"] - 1.96 * eff["se"]
    eff["hi"] = eff["coef"] + 1.96 * eff["se"]
    eff["family"] = ""
    for fam, cols in spec.families.items():
        eff.loc[cols, "family"] = fam

    # A6: resíduo (observado − previsto SEM os dummies de ano) por ano visto
    resid_by_year = None
    if spec.watch_years:
        year_cols = spec.families.get("ano em que viu", [])
        Xn = X.drop(columns=year_cols)
        fit_n = ridge(Xn, y, alpha=alpha)
        resid = y - predict(fit_n, Xn)
        wy = _first_watch_year(rated, diary)
        df = pd.DataFrame({"resid": resid, "year": wy}).dropna()
        if len(df):
            g = df.groupby(df["year"].astype(int))["resid"].agg(
                mean="mean", std="std", n="count")
            g = g[g["n"] >= 10]
            g["ci"] = 1.96 * g["std"].fillna(0) / np.sqrt(g["n"])
            if len(g) >= 2:
                resid_by_year = g[["mean", "ci", "n"]]

    # B2: importância = queda de R² ao remover a família
    importance = {}
    for fam, cols in spec.families.items():
        keep = [c for c in X.columns if c not in cols]
        if not keep:
            continue
        r2_sem = ridge(X[keep], y, alpha=alpha).r2
        importance[fam] = max(fit.r2 - r2_sem, 0.0)
    imp = pd.Series(importance).sort_values(ascending=False)

    return {"effects": eff, "r2": fit.r2, "n": fit.n, "sigma": fit.sigma,
            "spec": spec, "fit": fit, "resid_by_year": resid_by_year,
            "importance": imp}


# ------------------------------------------------------------------ B1


def rank_watchlist(films: pd.DataFrame, watchlist: pd.DataFrame,
                   diary: pd.DataFrame | None = None,
                   model: dict | None = None, top: int = 20) -> pd.DataFrame | None:
    """Ordena a watchlist pela nota que o modelo prevê que você daria.

    `watchlist` precisa estar enriquecida com TMDB (mesmas colunas de films).
    A incerteza reportada é o σ residual do modelo (não encolhe com n)."""
    if watchlist is None or not len(watchlist):
        return None
    model = model or rating_model(films, diary)
    if model is None:
        return None
    spec, fit = model["spec"], model["fit"]
    # nunca usa os dummies de "ano em que viu" para prever o futuro
    year_cols = spec.families.get("ano em que viu", [])
    Xw = transform(watchlist, FeatureSpec(
        genres=spec.genres, decades=spec.decades, directors=spec.directors,
        languages=spec.languages, watch_years=[],
        runtime_mean=spec.runtime_mean, votes_mean=spec.votes_mean))
    keep = [c for c in fit.coef.index if c not in year_cols]
    for c in keep:
        if c not in Xw.columns:
            Xw[c] = 0.0
    coef = fit.coef[keep]
    pred = fit.intercept + Xw[keep].values.astype(float) @ coef.values
    out = watchlist.copy()
    out["pred"] = np.clip(pred, 0.5, 5.0)
    out["known"] = Xw[keep].abs().sum(axis=1).values  # 0 = modelo às cegas
    out = out[out["known"] > 0].sort_values("pred", ascending=False)
    return out.head(top)


# ------------------------------------------------------------------ B4


def taste_clusters(films: pd.DataFrame, k: int | None = None,
                   min_n: int = 80, seed: int = 7) -> dict | None:
    """Arquétipos de filme: KMeans sobre gênero+década+idioma+keywords.

    Clustering e projeção 2D via scikit-learn (KMeans com init k-means++
    e PCA). Retorna dict com df (x, y da PCA, cluster), labels
    interpretáveis por cluster e resumo (n e nota média por cluster)."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA

    need = [c for c in ("genres",) if c in films]
    if not need or len(films) < min_n:
        return None
    spec = build_spec(films.assign(Rating=films.get("Rating", np.nan))
                      .fillna({"Rating": 3.0}),
                      None, min_genre=8, min_director=10**9, min_language=8)
    spec.directors = []
    base = films.copy()
    base["Rating"] = base.get("Rating", pd.Series(index=base.index, dtype=float))
    X = transform(base, spec, None)
    # keywords mais comuns como features binárias extras
    if "keywords" in films:
        kw = films["keywords"].dropna().explode().value_counts()
        kw = kw[kw >= max(6, int(len(films) * 0.02))].head(30)
        if len(kw):
            Xkw = _multi_hot(films["keywords"], list(kw.index), "kw: ")
            X = pd.concat([X, Xkw], axis=1)
    X = X.fillna(0.0)
    X = X.loc[:, X.std() > 0]
    if X.shape[1] < 5:
        return None
    Xs = np.nan_to_num(((X - X.mean()) / X.std()).values)

    if k is None:
        k = int(np.clip(round(np.sqrt(len(films) / 18)), 4, 7))
    lab = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(Xs)
    xy = PCA(n_components=2, random_state=seed).fit_transform(Xs)

    labels, summary = {}, []
    Xm = X.mean()
    Xstd = X.std().replace(0, 1)
    for j in range(k):
        mask = lab == j
        if not mask.any():
            continue
        zdiff = ((X[mask].mean() - Xm) / Xstd).sort_values(ascending=False)
        tops = [c.split(": ", 1)[-1] for c in zdiff.head(3).index]
        labels[j] = " · ".join(tops)
        r = films.loc[X.index[mask], "Rating"].dropna() \
            if "Rating" in films else pd.Series(dtype=float)
        summary.append({"cluster": j, "label": labels[j],
                        "n": int(mask.sum()),
                        "rating": float(r.mean()) if len(r) else np.nan})
    df = pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "cluster": lab},
                      index=X.index)
    df["Name"] = films.loc[X.index, "Name"]
    return {"df": df, "labels": labels,
            "summary": pd.DataFrame(summary).set_index("cluster")}
