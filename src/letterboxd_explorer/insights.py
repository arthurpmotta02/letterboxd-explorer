"""Insights automáticos em texto, o "Wrapped" do seu Letterboxd."""

from __future__ import annotations

import pandas as pd

from letterboxd_explorer import stats

PT_WEEKDAYS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]


def generate(films: pd.DataFrame, diary: pd.DataFrame | None,
             frames: dict | None = None) -> list[str]:
    """Gera frases-insight a partir dos dados. Cada frase é HTML simples."""
    out: list[str] = []
    rated = films.dropna(subset=["Rating"])

    if diary is not None and len(diary):
        wd = diary["Watched Date"].dt.dayofweek.value_counts().idxmax()
        out.append(f"Seu dia de cinema é <b>{PT_WEEKDAYS[wd]}</b>.")

        streak, start = stats.longest_streak(diary["Watched Date"])
        if streak >= 3:
            out.append(
                f"Sua maior maratona: <b>{streak} dias seguidos</b> com filme, "
                f"começando em {start:%d/%m/%Y}."
            )

        day, n = stats.busiest_day(diary)
        if n >= 3:
            out.append(f"Recorde em um dia: <b>{n} filmes</b> em {day:%d/%m/%Y}.")

        rw = stats.most_rewatched(diary, top=1)
        if len(rw):
            out.append(
                f"Filme-conforto: <b>{rw.index[0]}</b>, registrado {rw.iloc[0]} vezes."
            )

        gap = stats.watch_gap(films, diary)
        if len(gap):
            out.append(
                f"Em média você assiste filmes <b>{gap.mean():.0f} anos</b> "
                "depois do lançamento."
            )

    if len(rated):
        mode = rated["Rating"].mode().iloc[0]
        out.append(f"Sua nota mais comum é <b>{mode:g}★</b>.")

    her = stats.heresies(films)
    if len(her) >= 10:
        gen = her["diff"].mean()
        adj = "mais generoso" if gen > 0 else "mais exigente"
        out.append(f"Você é <b>{abs(gen):.2f}★ {adj}</b> que a média do TMDB.")

    hip = stats.hipster_index(films)
    if hip is not None and hip >= 0.15:
        out.append(
            f"Coeficiente cult: <b>{hip:.0%}</b> dos seus filmes têm menos de "
            "1000 votos no TMDB."
        )

    ng = stats.nostalgia_gap(films)
    if ng is not None and abs(ng) >= 0.2:
        if ng > 0:
            out.append(
                f"Saudosismo: você avalia filmes pré-1980 <b>+{ng:.1f}★</b> "
                "acima dos pós-2000. Antigamente era melhor?"
            )
        else:
            out.append(
                f"Zero saudosismo: você dá <b>{-ng:.1f}★ a mais</b> "
                "para filmes pós-2000 do que para os pré-1980."
            )

    contrast = stats.genre_rating_contrast(films)
    if contrast and contrast[2] >= 0.3:
        hi, lo, d = contrast
        out.append(
            f"Você avalia <b>{hi}</b> {d:.1f}★ acima de <b>{lo}</b> "
            "(mín. 10 filmes por gênero)."
        )

    dec = stats.decade_counts(films)
    if len(dec):
        out.append(f"Sua década do coração: <b>anos {int(dec.idxmax())}</b>.")

    directors = stats.explode_count(films, "directors", top=1)
    if len(directors):
        out.append(
            f"Diretor(a) da sua vida: <b>{directors.index[0]}</b> "
            f"({directors.iloc[0]} filmes)."
        )

    if frames:
        reviews = frames.get("reviews")
        if reviews is not None and "Review" in reviews:
            n_rev = int(reviews["Review"].notna().sum())
            lr = stats.longest_review(reviews)
            if n_rev >= 5 and lr:
                out.append(
                    f"Você escreveu <b>{n_rev} resenhas</b>; a mais longa tem "
                    f"{lr[1]} palavras ({lr[0]})."
                )
        comments = frames.get("comments")
        if comments is not None and len(comments) >= 5:
            out.append(f"Você deixou <b>{len(comments)} comentários</b> por aí.")

    if "runtime" in films and films["runtime"].notna().any():
        curtas = int((films["runtime"].dropna() <= 40).sum())
        if curtas >= 10:
            out.append(f"Você já viu <b>{curtas} curtas-metragens</b> (≤40 min).")
        hours = films["runtime"].dropna().sum() / 60
        if hours >= 24:
            out.append(
                f"Você já passou <b>{hours / 24:.0f} dias inteiros</b> "
                "em frente à tela."
            )
    return out
