"""Cliente TMDB com cache em disco, retry e suporte a chave v3 / token v4.

O export do Letterboxd traz só título, ano, nota e data — todo o resto
(gêneros, diretores, países, keywords...) vem daqui.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

TMDB_BASE = "https://api.themoviedb.org/3"
DEFAULT_CACHE = Path("tmdb_cache.json")


class TmdbClient:
    def __init__(self, key: str):
        self.session = requests.Session()
        if key and len(key) > 40:  # Read Access Token (v4)
            self.session.headers["Authorization"] = f"Bearer {key}"
            self.base_params: dict = {}
        else:  # API key (v3)
            self.base_params = {"api_key": key}

    def _get(self, path: str, **params) -> dict:
        for attempt in range(3):
            try:
                r = self.session.get(
                    f"{TMDB_BASE}/{path}", params={**self.base_params, **params}, timeout=15
                )
                if r.status_code == 429:  # rate limit
                    time.sleep(float(r.headers.get("Retry-After", 2)))
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        return {}

    def fetch_movie(self, name: str, year) -> dict | None:
        """Busca um filme e retorna os campos usados nas análises."""
        params: dict = {"query": name, "include_adult": "false"}
        if pd.notna(year):
            params["year"] = int(year)
        try:
            results = self._get("search/movie", **params).get("results", [])
            if not results and "year" in params:  # ano do Letterboxd às vezes diverge
                params.pop("year")
                results = self._get("search/movie", **params).get("results", [])
            if not results:
                return None
            m = self._get(f"movie/{results[0]['id']}", append_to_response="credits,keywords")
        except requests.RequestException as e:
            print(f"  ! erro em '{name}': {e}", file=sys.stderr)
            return None

        return {
            "tmdb_id": m["id"],
            "genres": [g["name"] for g in m.get("genres", [])],
            "keywords": [k["name"] for k in m.get("keywords", {}).get("keywords", [])],
            "countries": [c["iso_3166_1"] for c in m.get("production_countries", [])],
            "language": m.get("original_language"),
            "runtime": m.get("runtime"),
            "tmdb_rating": m.get("vote_average"),
            "tmdb_votes": m.get("vote_count"),
            "popularity": m.get("popularity"),
            "directors": [
                c["name"] for c in m.get("credits", {}).get("crew", []) if c.get("job") == "Director"
            ],
            "cast": [c["name"] for c in m.get("credits", {}).get("cast", [])[:8]],
            "budget": m.get("budget"),
            "revenue": m.get("revenue"),
            "release_date": m.get("release_date"),
        }


def load_cache(path: Path = DEFAULT_CACHE) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict, path: Path = DEFAULT_CACHE) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def enrich(
    films: pd.DataFrame,
    key: str | None,
    offline: bool = False,
    cache_path: Path = DEFAULT_CACHE,
) -> pd.DataFrame:
    """Anexa metadados TMDB a cada filme, usando/alimentando o cache local."""
    cache = load_cache(cache_path)
    missing = [
        (r.Name, r.Year) for r in films.itertuples() if f"{r.Name}|{r.Year}" not in cache
    ]

    if missing and not offline:
        if not key:
            raise SystemExit(
                "Há filmes fora do cache e nenhuma chave TMDB foi informada.\n"
                "Use --tmdb-key, defina TMDB_API_KEY, ou rode com --offline."
            )
        client = TmdbClient(key)
        print(f"Buscando {len(missing)} filmes no TMDB ({len(cache)} já em cache)...")
        for i, (name, year) in enumerate(missing, 1):
            cache[f"{name}|{year}"] = client.fetch_movie(name, year)
            if i % 25 == 0 or i == len(missing):
                print(f"  {i}/{len(missing)}")
                save_cache(cache, cache_path)
            time.sleep(0.05)  # ~20 req/s, abaixo do limite do TMDB
        save_cache(cache, cache_path)
    elif missing:
        print(
            f"--offline: {len(missing)} filmes sem metadados serão ignorados "
            "nas análises enriquecidas."
        )

    meta = films.apply(lambda r: cache.get(f"{r.Name}|{r.Year}") or {}, axis=1)
    return pd.concat([films.reset_index(drop=True), pd.DataFrame(list(meta))], axis=1)
