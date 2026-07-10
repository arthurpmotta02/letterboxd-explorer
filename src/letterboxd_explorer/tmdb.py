"""Cliente TMDB com cache em disco, retry, requisições paralelas e
suporte a chave v3 / token v4.

O export do Letterboxd traz só título, ano, nota e data. Todo o resto
(gêneros, diretores, países, keywords...) vem daqui.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

TMDB_BASE = "https://api.themoviedb.org/3"
DEFAULT_CACHE = Path("tmdb_cache.json")
WORKERS = 8  # requisições em paralelo (limite do TMDB é ~50/s)


class TmdbClient:
    def __init__(self, key: str):
        self._key = key
        self._is_v4 = bool(key) and len(key) > 40
        self._local = threading.local()  # uma Session por thread

    @property
    def session(self) -> requests.Session:
        s = getattr(self._local, "s", None)
        if s is None:
            s = requests.Session()
            if self._is_v4:
                s.headers["Authorization"] = f"Bearer {self._key}"
            self._local.s = s
        return s

    @property
    def base_params(self) -> dict:
        return {} if self._is_v4 else {"api_key": self._key}

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
        # include_adult: sem isso, títulos adultos do histórico simplesmente
        # não são encontrados e ficam fora de TODAS as análises
        params: dict = {"query": name, "include_adult": "true"}
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
            "poster": m.get("poster_path"),
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
    retry_misses: bool = False,
    refresh: list[str] | None = None,
) -> pd.DataFrame:
    """Anexa metadados TMDB a cada filme, usando/alimentando o cache local.

    As consultas rodam em paralelo (WORKERS threads); o cache é salvo
    periodicamente, então interromper no meio não perde progresso.
    """
    cache = load_cache(cache_path)

    if refresh:  # força rebuscar títulos casados com o filme errado
        alvos = [t.lower() for t in refresh]
        drop = [k for k in cache
                if any(t in k.rsplit("|", 1)[0].lower() for t in alvos)]
        for k in drop:
            del cache[k]
        print(f"--refresh: {len(drop)} filmes serão rebuscados do zero")

    def _pending(r):
        k = f"{r.Name}|{r.Year}"
        if k not in cache:
            return True
        return retry_misses and cache[k] is None  # rebusca os não-encontrados

    missing = [(r.Name, r.Year) for r in films.itertuples() if _pending(r)]

    if missing and not offline:
        if not key:
            raise SystemExit(
                "Há filmes fora do cache e nenhuma chave TMDB foi informada.\n"
                "Use --tmdb-key, defina TMDB_API_KEY, ou rode com --offline."
            )
        client = TmdbClient(key)
        print(f"Buscando {len(missing)} filmes no TMDB "
              f"({len(cache)} já em cache, {WORKERS} requisições em paralelo)...")
        done = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(client.fetch_movie, n, y): (n, y) for n, y in missing}
            for fut in as_completed(futures):
                n, y = futures[fut]
                try:
                    cache[f"{n}|{y}"] = fut.result()
                except Exception as e:  # nunca deixa uma falha derrubar o lote
                    print(f"  ! erro em '{n}': {e}", file=sys.stderr)
                    cache[f"{n}|{y}"] = None
                done += 1
                if done % 50 == 0 or done == len(missing):
                    print(f"  {done}/{len(missing)}")
                    save_cache(cache, cache_path)
        save_cache(cache, cache_path)

    # caches criados antes da v1.6 não têm pôster; completa só esse campo
    stale = [(k, v["tmdb_id"]) for k, v in cache.items()
             if v and "poster" not in v and v.get("tmdb_id")]
    if stale and not offline and key:
        client = TmdbClient(key)
        print(f"Baixando pôsteres de {len(stale)} filmes já em cache...")

        def _poster(mid):
            try:
                return client._get(f"movie/{mid}").get("poster_path")
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(_poster, mid): k for k, mid in stale}
            for i, fut in enumerate(as_completed(futures), 1):
                cache[futures[fut]]["poster"] = fut.result()
                if i % 200 == 0:
                    save_cache(cache, cache_path)
        save_cache(cache, cache_path)
    elif missing:
        print(
            f"--offline: {len(missing)} filmes sem metadados serão ignorados "
            "nas análises enriquecidas."
        )

    meta = films.apply(lambda r: cache.get(f"{r.Name}|{r.Year}") or {}, axis=1)
    return pd.concat([films.reset_index(drop=True), pd.DataFrame(list(meta))], axis=1)
