"""Leitura do export do Letterboxd (ZIP ou pasta com CSVs)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

WANTED = ["diary", "watched", "ratings", "watchlist", "reviews", "profile",
          "comments"]

# colunas mínimas esperadas por arquivo do export oficial; se o formato do
# Letterboxd mudar, falhamos cedo com mensagem clara em vez de KeyError
REQUIRED_COLS = {
    "watched": {"Name", "Year"},
    "diary": {"Name", "Year", "Watched Date"},
    "ratings": {"Name", "Year", "Rating"},
    "watchlist": {"Name", "Year"},
    "reviews": {"Name", "Review"},
}


class ExportError(Exception):
    """Export inválido ou incompleto."""


def validate_schema(frames: dict[str, pd.DataFrame]) -> None:
    """Confere as colunas mínimas de cada CSV presente no export."""
    problemas = []
    for name, need in REQUIRED_COLS.items():
        df = frames.get(name)
        if df is None:
            continue
        faltam = need - set(df.columns)
        if faltam:
            problemas.append(f"{name}.csv sem coluna(s): "
                             + ", ".join(sorted(faltam)))
    if problemas:
        raise ExportError(
            "O export não tem o formato esperado do Letterboxd: "
            + "; ".join(problemas)
            + ". O formato mudou? Abra uma issue no repositório."
        )


def parse_dates(s: pd.Series) -> pd.Series:
    """Datas do export: ISO (AAAA-MM-DD) ou pt-BR (DD/MM/AAAA).

    O export oficial usa ISO, mas arquivos que passaram pelo Excel podem
    vir em DD/MM/AAAA; detectamos pelo que parseia melhor.
    """
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    if iso.notna().mean() >= 0.5:
        return iso
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


def read_export(path: Path) -> dict[str, pd.DataFrame]:
    """Lê os CSVs do export (ZIP ou pasta). Retorna dict {nome: DataFrame}."""
    frames: dict[str, pd.DataFrame] = {}
    path = Path(path)

    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                stem = Path(info.filename).stem.lower()
                # só a raiz do ZIP: subpastas como likes/reviews.csv e
                # deleted/diary.csv têm outro formato e não podem
                # sobrescrever os arquivos principais
                if "/" in info.filename.replace("\\", "/"):
                    continue
                if stem in WANTED and info.filename.endswith(".csv"):
                    with z.open(info) as f:
                        frames[stem] = pd.read_csv(io.TextIOWrapper(f, "utf-8"))
    elif path.is_dir():
        for name in WANTED:
            f = path / f"{name}.csv"
            if f.exists():
                frames[name] = pd.read_csv(f)
    else:
        raise ExportError(f"Caminho não encontrado ou inválido: {path}")

    if "watched" not in frames and "diary" not in frames:
        raise ExportError("Não encontrei watched.csv nem diary.csv no export.")
    validate_schema(frames)
    return frames


def build_films(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabela única de filmes assistidos, com a nota do usuário (se houver)."""
    watched = frames.get("watched")
    if watched is None:
        watched = frames["diary"][["Name", "Year", "Letterboxd URI"]].drop_duplicates()

    films = watched[["Name", "Year"]].drop_duplicates().copy()
    films["Year"] = pd.to_numeric(films["Year"], errors="coerce").astype("Int64")

    ratings = frames.get("ratings")
    if ratings is not None and "Rating" in ratings:
        r = ratings.copy()
        r["Year"] = pd.to_numeric(r["Year"], errors="coerce").astype("Int64")
        r = r.drop_duplicates(subset=["Name", "Year"], keep="last")
        films = films.merge(r[["Name", "Year", "Rating"]], on=["Name", "Year"], how="left")
    else:
        films["Rating"] = pd.NA
    return films


def build_diary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    """Diário com datas parseadas e flag de rewatch normalizada."""
    diary = frames.get("diary")
    if diary is None or diary.empty:
        return None

    d = diary.copy()
    d["Watched Date"] = parse_dates(d["Watched Date"])
    d = d.dropna(subset=["Watched Date"])
    d["Year"] = pd.to_numeric(d["Year"], errors="coerce").astype("Int64")
    if "Rewatch" in d:
        d["Rewatch"] = d["Rewatch"].fillna("No").astype(str).str.lower().eq("yes")
    else:
        d["Rewatch"] = False
    if "Rating" in d:
        d["Rating"] = pd.to_numeric(d["Rating"], errors="coerce")
    else:
        d["Rating"] = pd.NA
    return d


def filter_year(films: pd.DataFrame, diary: pd.DataFrame | None, year: int):
    """Modo retrospectiva: restringe o diário (e os filmes) a um ano-calendário."""
    if diary is None:
        raise ExportError("--year exige diary.csv no export.")
    d = diary[diary["Watched Date"].dt.year == year]
    if d.empty:
        raise ExportError(f"Nenhum registro no diário em {year}.")
    keys = set(zip(d["Name"], d["Year"]))
    f = films[[(n, y) in keys for n, y in zip(films["Name"], films["Year"])]]
    return f.reset_index(drop=True), d.reset_index(drop=True)
