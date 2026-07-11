"""Camada de modelagem: ridge analítico + KMeans/PCA (scikit-learn), sem I/O.

Um único modelo linear (ridge) responde várias perguntas:
  A1  efeitos parciais sobre a sua nota (forest plot com intervalo);
  A6  generosidade ao longo do tempo controlada pela composição;
  B1  nota prevista para cada filme da watchlist (com intervalo de previsão);
  B2  importância de cada família de features (queda de R² VALIDADA);
  2.3 curva de calibração predito×real (fora da amostra).

O ridge é resolvido em forma fechada (numpy) em vez de
sklearn.linear_model.Ridge porque o sklearn não expõe a covariância dos
coeficientes, e os intervalos são o ponto central do relatório.

Honestidade estatística (revisão v3.1):
  - o `alpha` é escolhido por validação cruzada, não fixado;
  - R², MAE e importância por família são medidos FORA da amostra (k-fold),
    não no treino, para não inflar números;
  - os intervalos dos coeficientes são de VARIÂNCIA do estimador encolhido,
    não corrigidos pelo viés do ridge (rótulo honesto no relatório);
  - a previsão da watchlist propaga a covariância dos coeficientes + o ruído
    residual, então cold-starts (poucas features casadas) saem com intervalo
    largo em vez de falsa confiança.
Clustering e projeção 2D usam scikit-learn (KMeans, PCA, silhueta).
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
    cov: np.ndarray | None = None  # covariância dos coeficientes (p×p)


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
                    alpha=alpha, sigma=float(np.sqrt(sigma2)), cov=var)


def predict(fit: RidgeFit, X: pd.DataFrame) -> pd.Series:
    Xv = X[fit.coef.index].values.astype(float)
    return pd.Series(fit.intercept + Xv @ fit.coef.values, index=X.index)


# ------------------------------------------------------------ validação cruzada


def _kfold(n: int, k: int, seed: int = 0) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return np.array_split(rng.permutation(n), k)


def cross_val_ridge(X: pd.DataFrame, y: pd.Series, alpha: float = 3.0,
                    k: int = 5, seed: int = 0) -> dict:
    """R² e MAE fora da amostra (k-fold): os números honestos do modelo.

    Retorna cv_r2, cv_mae, o k efetivo e as previsões out-of-fold (`pred`),
    usadas pela curva de calibração.
    """
    Xv = X.values.astype(float)
    yv = y.values.astype(float)
    n, p = Xv.shape
    k = int(min(k, n))
    if k < 2:
        return {"cv_r2": float("nan"), "cv_mae": float("nan"), "k": 0,
                "pred": None}
    preds = np.full(n, np.nan)
    for test in _kfold(n, k, seed):
        train = np.setdiff1d(np.arange(n), test)
        if len(train) < 2:
            continue
        Xt, yt = Xv[train], yv[train]
        ybar = yt.mean()
        A = Xt.T @ Xt + alpha * np.eye(p)
        beta = np.linalg.solve(A, Xt.T @ (yt - ybar))
        preds[test] = ybar + Xv[test] @ beta
    m = ~np.isnan(preds)
    if m.sum() < 2:
        return {"cv_r2": float("nan"), "cv_mae": float("nan"), "k": k,
                "pred": None}
    err = yv[m] - preds[m]
    ss_res = float(err @ err)
    ss_tot = float(((yv[m] - yv[m].mean()) ** 2).sum()) or 1.0
    return {"cv_r2": 1.0 - ss_res / ss_tot,
            "cv_mae": float(np.abs(err).mean()), "k": k,
            "pred": pd.Series(preds, index=X.index)}


def select_alpha(X: pd.DataFrame, y: pd.Series,
                 alphas: tuple[float, ...] = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0),
                 k: int = 5, seed: int = 0) -> tuple[float, float]:
    """Escolhe o encolhimento por CV-R² (em vez de fixar alpha arbitrário)."""
    best, best_r2 = alphas[0], -np.inf
    for a in alphas:
        r2 = cross_val_ridge(X, y, alpha=a, k=k, seed=seed)["cv_r2"]
        if np.isfinite(r2) and r2 > best_r2:
            best_r2, best = r2, a
    return best, best_r2


# ------------------------------------------------------------------ A1 + A6


def rating_model(films: pd.DataFrame, diary: pd.DataFrame | None = None,
                 min_n: int = 60, alpha: float | None = None,
                 cv_k: int = 5) -> dict | None:
    """Modelo da nota (A1). Retorna efeitos com intervalo, R² de treino e de
    validação cruzada, MAE fora da amostra, resíduo por ano (A6), importância
    por família VALIDADA (B2) e previsões out-of-fold. None se a amostra for
    pequena demais.

    `alpha=None` escolhe o encolhimento por CV (recomendado)."""
    rated = films.dropna(subset=["Rating"]).copy()
    if len(rated) < min_n:
        return None
    spec = build_spec(rated, diary)
    X = transform(rated, spec, diary)
    if X.shape[1] < 3:
        return None
    y = rated["Rating"]
    k = int(np.clip(cv_k, 2, max(2, len(rated) // 10)))
    if alpha is None:
        alpha, _ = select_alpha(X, y, k=k)
    fit = ridge(X, y, alpha=alpha)
    cv = cross_val_ridge(X, y, alpha=alpha, k=k)

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

    # B2: importância = queda de R² FORA DA AMOSTRA ao remover a família.
    # Medir no treino inflaria famílias com muitos dummies (diretor, gênero).
    base_cv = cv["cv_r2"]
    importance = {}
    for fam, cols in spec.families.items():
        keep = [c for c in X.columns if c not in cols]
        if not keep:
            continue
        r2_sem = cross_val_ridge(X[keep], y, alpha=alpha, k=k)["cv_r2"]
        if np.isfinite(base_cv) and np.isfinite(r2_sem):
            importance[fam] = max(base_cv - r2_sem, 0.0)
    imp = pd.Series(importance, dtype=float).sort_values(ascending=False)

    return {"effects": eff, "r2": fit.r2, "cv_r2": cv["cv_r2"],
            "cv_mae": cv["cv_mae"], "cv_pred": cv["pred"], "alpha": alpha,
            "n": fit.n, "sigma": fit.sigma, "spec": spec, "fit": fit,
            "resid_by_year": resid_by_year, "importance": imp}


# ------------------------------------------------------------------ B1


def _mmr_order(scores: np.ndarray, feats: np.ndarray, lam: float,
               top: int) -> list[int]:
    """Maximal Marginal Relevance: seleção gulosa que equilibra nota prevista
    (relevância) e diversidade no espaço de features. lam=1 → só relevância."""
    norm = np.linalg.norm(feats, axis=1, keepdims=True)
    fn = feats / np.where(norm == 0, 1.0, norm)
    sim = fn @ fn.T
    rel = scores - scores.min()
    rel = rel / (rel.max() or 1.0)
    chosen: list[int] = []
    pool = list(range(len(scores)))
    while pool and len(chosen) < top:
        best = max(pool, key=lambda c: lam * rel[c] - (1 - lam) * (
            max((sim[c, s] for s in chosen), default=0.0)))
        chosen.append(best)
        pool.remove(best)
    return chosen


def rank_watchlist(films: pd.DataFrame, watchlist: pd.DataFrame,
                   diary: pd.DataFrame | None = None,
                   model: dict | None = None, top: int = 20,
                   diversify: float = 0.0) -> pd.DataFrame | None:
    """Ordena a watchlist pela nota que o modelo prevê que você daria.

    `watchlist` precisa estar enriquecida com TMDB (mesmas colunas de films).
    Cada filme sai com um intervalo de previsão (`pred_lo`/`pred_hi`) que soma
    a incerteza dos coeficientes ao ruído residual: filmes com poucas features
    casadas (`known` baixo, ex.: diretor fora do vocabulário) recebem faixa
    larga em vez de falsa confiança.

    `diversify` em (0, 1) reordena por MMR sobre um pool dos melhores, para não
    devolver vários filmes quase idênticos; 0 mantém a ordem pura por nota."""
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
    Xk = Xw[keep].values.astype(float)
    pred = fit.intercept + Xk @ coef.values

    # intervalo de previsão: Var = xᵀ Cov(β) x + σ² (parâmetros + ruído)
    var_param = np.zeros(len(Xk))
    if fit.cov is not None:
        pos = {c: i for i, c in enumerate(fit.coef.index)}
        idx = [pos[c] for c in keep]
        sub = fit.cov[np.ix_(idx, idx)]
        var_param = np.einsum("ij,jk,ik->i", Xk, sub, Xk)
    se_pred = np.sqrt(np.clip(var_param, 0, None) + fit.sigma ** 2)

    out = watchlist.copy()
    out["pred"] = np.clip(pred, 0.5, 5.0)
    out["pred_lo"] = np.clip(pred - 1.96 * se_pred, 0.5, 5.0)
    out["pred_hi"] = np.clip(pred + 1.96 * se_pred, 0.5, 5.0)
    out["known"] = Xw[keep].abs().sum(axis=1).values  # 0 = modelo às cegas
    out = out[out["known"] > 0].sort_values("pred", ascending=False)
    if 0.0 < diversify < 1.0 and len(out) > top:
        pool = out.head(top * 3)
        feats = Xw.loc[pool.index, keep].values.astype(float)
        order = _mmr_order(pool["pred"].values, feats, diversify, top)
        return pool.iloc[order]
    return out.head(top)


# ----------------------------------------------------- 2.1 benchmark não-linear


def nonlinear_benchmark(films: pd.DataFrame, diary: pd.DataFrame | None = None,
                        model: dict | None = None, k: int = 5,
                        min_n: int = 80) -> dict | None:
    """Compara o CV-R² do ridge (aditivo) com o de um gradient boosting, que
    captura interações. O ganho mede quanto do seu gosto NÃO é linear
    (ex.: gostar de drama longo mas não de comédia longa)."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import cross_val_score

    rated = films.dropna(subset=["Rating"]).copy()
    if len(rated) < min_n:
        return None
    model = model or rating_model(films, diary, cv_k=k)
    if model is None:
        return None
    X = transform(rated, model["spec"], diary)
    y = rated["Rating"].values.astype(float)
    kk = int(np.clip(k, 2, max(2, len(rated) // 10)))
    gbm = HistGradientBoostingRegressor(
        max_depth=3, learning_rate=0.08, max_iter=200, random_state=0)
    try:
        r2 = float(np.mean(cross_val_score(
            gbm, X.values, y, cv=kk, scoring="r2")))
    except Exception:
        return None
    ridge_r2 = float(model["cv_r2"])
    return {"ridge_cv_r2": ridge_r2, "gbm_cv_r2": r2,
            "gain": r2 - ridge_r2, "n": len(rated)}


# ------------------------------------------------------------------ 2.3 calibração


def rating_calibration(films: pd.DataFrame, diary: pd.DataFrame | None = None,
                       model: dict | None = None, bins: int = 6,
                       cv_k: int = 5) -> pd.DataFrame | None:
    """Curva de calibração: nota prevista FORA DA AMOSTRA × nota real, em bins.

    Usa as previsões out-of-fold do modelo (sem vazamento). Colunas:
    pred (média prevista do bin), real (média observada), lo/hi (IC95 da média
    real) e n. Um modelo bem calibrado fica sobre a diagonal."""
    rated = films.dropna(subset=["Rating"]).copy()
    model = model or rating_model(films, diary, cv_k=cv_k)
    if model is None or model.get("cv_pred") is None:
        return None
    pred = model["cv_pred"].reindex(rated.index)
    df = pd.DataFrame({"pred": pred.values, "real": rated["Rating"].values})
    df = df.dropna()
    if len(df) < bins * 4:
        return None
    df["bin"] = pd.qcut(df["pred"], q=bins, duplicates="drop")
    g = df.groupby("bin", observed=True).agg(
        pred=("pred", "mean"), real=("real", "mean"),
        std=("real", "std"), n=("real", "count"))
    g["ci"] = 1.96 * g["std"].fillna(0) / np.sqrt(g["n"])
    g["lo"] = g["real"] - g["ci"]
    g["hi"] = g["real"] + g["ci"]
    return g[["pred", "real", "lo", "hi", "n"]].reset_index(drop=True)


# ------------------------------------------------------------------ B4


def taste_clusters(films: pd.DataFrame, k: int | None = None,
                   min_n: int = 80, seed: int = 7) -> dict | None:
    """Arquétipos de filme: KMeans sobre gênero+década+idioma+keywords.

    Clustering e projeção 2D via scikit-learn. Só as features CONTÍNUAS são
    padronizadas; as binárias (0/1) ficam como estão, para não superpesar
    categorias raras (um dummy raro z-scored viraria um valor enorme). O nº de
    clusters `k` é escolhido pela maior silhueta, não por heurística. Retorna
    dict com df (x, y da PCA, cluster), labels interpretáveis, resumo (n e nota
    média por cluster), k e silhueta."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score

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
    # padroniza SO as continuas (familia "filme"); binarias ficam 0/1 para nao
    # superpesar categorias raras (critica de rare-category overweighting)
    cont = set(spec.families.get("filme", []))
    Xc = X.copy()
    for c in [c for c in X.columns if c in cont]:
        sd = float(X[c].std())
        if sd > 0:
            Xc[c] = (X[c] - X[c].mean()) / sd
    Xs = np.nan_to_num(Xc.values.astype(float))

    sil = float("nan")
    if k is None:
        best_k, best_s = 4, -1.0
        for kk in range(4, 8):
            if kk >= len(Xs):
                break
            lab_try = KMeans(n_clusters=kk, n_init=10,
                             random_state=seed).fit_predict(Xs)
            if len(set(lab_try)) < 2:
                continue
            s = float(silhouette_score(Xs, lab_try))
            if s > best_s:
                best_s, best_k = s, kk
        k, sil = best_k, best_s
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
    return {"df": df, "labels": labels, "k": int(k), "silhouette": sil,
            "summary": pd.DataFrame(summary).set_index("cluster")}
