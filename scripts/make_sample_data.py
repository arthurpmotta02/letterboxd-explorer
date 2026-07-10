"""Gera um export de exemplo do Letterboxd + cache TMDB fictício.

Permite testar o pipeline inteiro sem chave de API:

    python scripts/make_sample_data.py
    letterboxd-explorer sample-export --offline -o demo.html
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)
OUT = Path("sample-export")
OUT.mkdir(exist_ok=True)

GENRES = ["Drama", "Comédia", "Terror", "Ficção científica", "Ação",
          "Romance", "Thriller", "Animação", "Documentário", "Crime"]
KEYWORDS = ["coming of age", "time travel", "slow burn", "revenge", "heist",
            "dystopia", "road movie", "body horror", "neo-noir", "found footage",
            "small town", "based on novel", "anthology", "one location",
            "unreliable narrator", "satire", "surrealism", "haunted house"]
DIRECTORS = ["Denis Villeneuve", "Greta Gerwig", "Bong Joon-ho", "Agnès Varda",
             "Kleber Mendonça Filho", "David Lynch", "Céline Sciamma",
             "Park Chan-wook", "Coen Brothers", "Lucrecia Martel",
             "Hirokazu Koreeda", "Jordan Peele"]
ACTORS = ["Toni Collette", "Song Kang-ho", "Adam Driver", "Fernanda Montenegro",
          "Tilda Swinton", "Wagner Moura", "Florence Pugh", "Choi Min-sik",
          "Isabelle Huppert", "Lakeith Stanfield", "Sônia Braga", "Willem Dafoe"]
COUNTRIES = ["US", "BR", "KR", "FR", "JP", "GB", "AR", "DE", "IR", "PT"]
LANGS = ["en", "pt", "ko", "fr", "ja", "es", "de", "fa"]

films, cache = [], {}
for i in range(320):
    name, year = f"Filme Exemplo {i + 1}", random.choice(range(1950, 2026))
    films.append((name, year))
    cache[f"{name}|{year}"] = {
        "tmdb_id": 10000 + i,
        "genres": random.sample(GENRES, k=random.randint(1, 3)),
        "keywords": random.sample(KEYWORDS, k=random.randint(2, 6)),
        "countries": random.sample(COUNTRIES, k=random.randint(1, 2)),
        "language": random.choice(LANGS),
        "runtime": random.randint(75, 210),
        "tmdb_rating": round(random.uniform(4.5, 8.8), 1),
        "tmdb_votes": random.choice([15, 80, 400, 2000, 15000]),
        "popularity": round(random.uniform(1, 80), 2),
        "directors": [random.choice(DIRECTORS)],
        "cast": random.sample(ACTORS, k=4),
        "budget": random.choice([0, 500_000, 5_000_000, 30_000_000, 150_000_000]), "revenue": 0, "release_date": f"{year}-06-01",
    }

pd.DataFrame({
    "Date": "2026-01-01", "Name": [f[0] for f in films],
    "Year": [f[1] for f in films], "Letterboxd URI": "https://boxd.it/xxxx",
}).to_csv(OUT / "watched.csv", index=False)

rated = random.sample(films, 260)
pd.DataFrame({
    "Date": "2026-01-01", "Name": [f[0] for f in rated],
    "Year": [f[1] for f in rated], "Letterboxd URI": "https://boxd.it/xxxx",
    "Rating": [random.choice([1, 1.5, 2, 2.5, 3, 3, 3.5, 3.5, 4, 4, 4.5, 5])
               for _ in rated],
}).to_csv(OUT / "ratings.csv", index=False)

start = date(2023, 1, 1)
diary_films = random.choices(films, k=400)
pd.DataFrame({
    "Date": "2026-01-01", "Name": [f[0] for f in diary_films],
    "Year": [f[1] for f in diary_films], "Letterboxd URI": "https://boxd.it/xxxx",
    "Rating": "", "Rewatch": [random.choice(["Yes"] + ["No"] * 7) for _ in diary_films],
    "Tags": "",
    "Watched Date": [(start + timedelta(days=random.randint(0, 1250))).isoformat()
                     for _ in diary_films],
}).to_csv(OUT / "diary.csv", index=False)

wl_start = date(2022, 1, 1)
pd.DataFrame({
    "Date": [(wl_start + timedelta(days=random.randint(0, 1600))).isoformat()
             for _ in range(85)],
    "Name": [f"Na Lista {i}" for i in range(85)],
    "Year": 2024, "Letterboxd URI": "x",
}).to_csv(OUT / "watchlist.csv", index=False)

WORDS = ("atmosfera fotografia trilha ritmo roteiro atuacao montagem cores "
         "tensao delicado brutal poesia melancolia catarse absurdo genial").split()
rev_films = random.sample(films, 60)
pd.DataFrame({
    "Date": "2026-01-01", "Name": [f[0] for f in rev_films],
    "Year": [f[1] for f in rev_films], "Letterboxd URI": "x",
    "Rating": [random.choice([2, 3, 3.5, 4, 4.5, 5]) for _ in rev_films],
    "Rewatch": "", "Review": [" ".join(random.choices(WORDS, k=random.randint(5, 60)))
                              for _ in rev_films],
    "Tags": "", "Watched Date": "2025-06-01",
}).to_csv(OUT / "reviews.csv", index=False)

pd.DataFrame({"Date Joined": ["2022-01-09"], "Username": ["cinefilo_exemplo"],
              "Given Name": ["Exemplo"]}).to_csv(OUT / "profile.csv", index=False)

Path("tmdb_cache.json").write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
print("Dados de exemplo criados em ./sample-export + tmdb_cache.json")
