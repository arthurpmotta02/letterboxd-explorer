"""Geração do relatório HTML interativo (arquivo único, Plotly via CDN)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from letterboxd_explorer import insights, stats

# ------------------------------------------------------------------- tema

BG, CARD, TEXT, MUTED = "#14181c", "#1b2228", "#dfe7ef", "#99aabb"
ORANGE, GREEN, BLUE = "#ff8000", "#00e054", "#40bcf4"
PALETTE = [GREEN, ORANGE, BLUE, "#f4d35e", "#ee6c4d", "#9b5de5",
           "#00bbf9", "#f15bb5", "#8ac926", "#ff595e"]
PT_MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
PT_WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

pio.templates["lb"] = go.layout.Template(
    layout=dict(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, Helvetica, Arial, sans-serif"),
        colorway=PALETTE,
        xaxis=dict(gridcolor="#2c3440", zerolinecolor="#2c3440"),
        yaxis=dict(gridcolor="#2c3440", zerolinecolor="#2c3440"),
        margin=dict(l=50, r=20, t=50, b=45),
    )
)
pio.templates.default = "lb"

ISO2_TO_ISO3 = {
    "US": "USA", "GB": "GBR", "FR": "FRA", "DE": "DEU", "IT": "ITA", "ES": "ESP",
    "BR": "BRA", "JP": "JPN", "KR": "KOR", "CN": "CHN", "HK": "HKG", "TW": "TWN",
    "IN": "IND", "MX": "MEX", "AR": "ARG", "CL": "CHL", "CO": "COL", "PE": "PER",
    "UY": "URY", "PT": "PRT", "CA": "CAN", "AU": "AUS", "NZ": "NZL", "IE": "IRL",
    "SE": "SWE", "NO": "NOR", "DK": "DNK", "FI": "FIN", "IS": "ISL", "NL": "NLD",
    "BE": "BEL", "CH": "CHE", "AT": "AUT", "PL": "POL", "CZ": "CZE", "SK": "SVK",
    "HU": "HUN", "RO": "ROU", "BG": "BGR", "GR": "GRC", "TR": "TUR", "RU": "RUS",
    "UA": "UKR", "IL": "ISR", "IR": "IRN", "IQ": "IRQ", "SA": "SAU", "AE": "ARE",
    "EG": "EGY", "MA": "MAR", "DZ": "DZA", "TN": "TUN", "ZA": "ZAF", "NG": "NGA",
    "KE": "KEN", "ET": "ETH", "SN": "SEN", "TH": "THA", "VN": "VNM", "PH": "PHL",
    "ID": "IDN", "MY": "MYS", "SG": "SGP", "PK": "PAK", "BD": "BGD", "LK": "LKA",
    "NP": "NPL", "KZ": "KAZ", "GE": "GEO", "AM": "ARM", "RS": "SRB", "HR": "HRV",
    "SI": "SVN", "BA": "BIH", "MK": "MKD", "AL": "ALB", "EE": "EST", "LV": "LVA",
    "LT": "LTU", "BY": "BLR", "MD": "MDA", "CU": "CUB", "DO": "DOM", "GT": "GTM",
    "CR": "CRI", "PA": "PAN", "VE": "VEN", "BO": "BOL", "PY": "PRY", "EC": "ECU",
    "SU": "RUS", "XC": "CZE", "CS": "SRB", "YU": "SRB", "DD": "DEU",
}


def _fig_html(fig, height=420):
    fig.update_layout(height=height)
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=False,
        config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )


# ------------------------------------------------------------------ seções


def build_report(
    films: pd.DataFrame,
    diary: pd.DataFrame | None,
    frames: dict,
    out: Path,
    year: int | None = None,
) -> Path:
    sections: list[tuple[str, str, str]] = []

    def add(title, sub, fig, height=420):
        sections.append((title, sub, _fig_html(fig, height)))

    rated = films.dropna(subset=["Rating"])
    hours = films["runtime"].dropna().sum() / 60 if "runtime" in films else 0

    # ---------- cards
    cards = [
        (f"{len(films):,}".replace(",", "."), "filmes assistidos"),
        (f"{hours:,.0f} h".replace(",", "."), f"de tela (≈ {hours / 24:.0f} dias)"),
        (f"{rated['Rating'].mean():.2f} ★" if len(rated) else "—", "nota média"),
    ]
    if diary is not None and len(diary):
        cards.append((str(int(diary["Rewatch"].sum())), "rewatches no diário"))
        per_year = diary.groupby(diary["Watched Date"].dt.year).size()
        if len(per_year) and year is None:
            cards.append((str(int(per_year.max())), f"recorde em um ano ({per_year.idxmax()})"))
    if "watchlist" in frames and year is None:
        cards.append((f"{len(frames['watchlist']):,}".replace(",", "."), "na watchlist"))

    # ---------- ritmo
    if diary is not None and len(diary):
        m = diary.set_index("Watched Date").resample("ME").size()
        fig = px.area(x=m.index, y=m.values, labels={"x": "", "y": "filmes"})
        fig.update_traces(line_color=GREEN, fillcolor="rgba(0,224,84,.15)")
        add("Ritmo de visualização", "Filmes registrados no diário por mês", fig, 380)

        hm = pd.crosstab(diary["Watched Date"].dt.dayofweek, diary["Watched Date"].dt.month)
        hm = hm.reindex(index=range(7), columns=range(1, 13), fill_value=0)
        fig = go.Figure(go.Heatmap(
            z=hm.values, x=PT_MONTHS, y=PT_WEEKDAYS,
            colorscale=[[0, CARD], [1, GREEN]], showscale=False))
        add("Quando você assiste", "Dia da semana × mês", fig, 340)

    # ---------- notas
    if len(rated):
        dist = stats.rating_distribution(films)
        fig = px.bar(x=dist.index, y=dist.values, labels={"x": "nota (★)", "y": "filmes"})
        fig.update_traces(marker_color=ORANGE)
        add("Distribuição das suas notas",
            f"{len(rated)} filmes avaliados — mediana {rated['Rating'].median():.1f}★",
            fig, 380)

    # ---------- generosidade ao longo do tempo
    if diary is not None and len(diary):
        yearly = stats.rating_over_time(diary, films)
        if len(yearly) >= 2:
            fig = px.line(x=yearly.index, y=yearly.values, markers=True,
                          labels={"x": "ano", "y": "nota média"})
            fig.update_traces(line_color=ORANGE)
            add("Você está ficando mais generoso?",
                "Nota média por ano em que assistiu (mín. 10 notas/ano)", fig, 360)

    # ---------- você × TMDB
    her = stats.heresies(films)
    if len(her) >= 10:
        fig = px.scatter(her, x="tmdb_5", y="Rating", hover_name="Name", opacity=.6,
                         labels={"tmdb_5": "nota TMDB (0–5)", "Rating": "sua nota"})
        fig.add_shape(type="line", x0=0, y0=0, x1=5, y1=5,
                      line=dict(color=MUTED, dash="dot"))
        fig.update_traces(marker_color=BLUE)
        over = ", ".join(her.nlargest(5, "diff")["Name"])
        under = ", ".join(her.nsmallest(5, "diff")["Name"])
        add("Você × crítica (TMDB)",
            "Acima da linha = você gostou mais que a média. "
            f"Defende: <b>{over}</b>. Não perdoa: <b>{under}</b>.",
            fig, 480)

    # ---------- décadas
    dec = stats.decade_counts(films)
    if len(dec):
        fig = px.bar(x=dec.index, y=dec.values, labels={"x": "década", "y": "filmes"})
        add("Décadas", "Ano de lançamento dos filmes que você viu", fig, 380)

    # ---------- idade do filme ao assistir
    if diary is not None and len(diary):
        gap = stats.watch_gap(films, diary)
        if len(gap) >= 20:
            fig = px.histogram(gap, nbins=40, labels={"value": "anos após o lançamento"})
            fig.update_traces(marker_color="#9b5de5")
            fig.update_layout(showlegend=False, yaxis_title="registros")
            add("Caçador de lançamentos ou arqueólogo?",
                f"Idade do filme quando você o assistiu — mediana {gap.median():.0f} anos",
                fig, 380)

    # ---------- gêneros
    g = stats.explode_count(films, "genres", 20)
    if len(g):
        fig = px.bar(x=g.values[::-1], y=g.index[::-1], orientation="h",
                     labels={"x": "filmes", "y": ""})
        fig.update_traces(marker_color=GREEN)
        add("Gêneros", "Contagem por gênero (TMDB)", fig, 520)

        gr = stats.group_rating(films, "genres", min_count=5).sort_values("mean")
        if len(gr):
            fig = px.bar(gr, x="mean", y=gr.index, orientation="h",
                         hover_data=["count"], labels={"mean": "nota média", "genres": ""})
            fig.update_traces(marker_color=ORANGE)
            fig.update_xaxes(range=[max(0, gr["mean"].min() - .5), 5])
            add("Qual gênero você mais ama",
                "Nota média por gênero (mín. 5 filmes avaliados)", fig, 480)

    # ---------- evolução dos gêneros
    if diary is not None and len(diary):
        trend = stats.genre_trend(diary, films)
        if len(trend) >= 3:
            fig = go.Figure()
            for i, col in enumerate(trend.columns):
                fig.add_trace(go.Scatter(
                    x=trend.index, y=trend[col], name=col, stackgroup="one",
                    line=dict(width=.5, color=PALETTE[i % len(PALETTE)])))
            fig.update_layout(yaxis_tickformat=".0%", yaxis_title="participação",
                              xaxis_title="ano")
            add("Suas fases", "Participação dos gêneros mais vistos, ano a ano", fig, 420)

    # ---------- microgêneros
    k = stats.explode_count(films, "keywords", 30)
    if len(k):
        fig = px.bar(x=k.values[::-1], y=k.index[::-1], orientation="h",
                     labels={"x": "filmes", "y": ""})
        fig.update_traces(marker_color=BLUE)
        add("Microgêneros", "Keywords do TMDB mais frequentes no que você vê", fig, 700)

    # ---------- diretores
    d = stats.explode_count(films, "directors", 20)
    if len(d):
        fig = px.bar(x=d.values[::-1], y=d.index[::-1], orientation="h",
                     labels={"x": "filmes", "y": ""})
        fig.update_traces(marker_color=GREEN)
        add("Diretores mais vistos", "", fig, 520)

        dr = stats.group_rating(films, "directors", min_count=3)
        dr = dr.sort_values("mean", ascending=False).head(15)
        if len(dr):
            fig = px.bar(dr.iloc[::-1], x="mean", y=dr.index[::-1], orientation="h",
                         hover_data=["count"],
                         labels={"mean": "nota média", "directors": ""})
            fig.update_traces(marker_color=ORANGE)
            fig.update_xaxes(range=[max(0, dr["mean"].min() - .5), 5])
            add("Diretores favoritos", "Nota média (mín. 3 filmes avaliados)", fig, 460)

    # ---------- atores
    a = stats.explode_count(films, "cast", 20)
    if len(a):
        fig = px.bar(x=a.values[::-1], y=a.index[::-1], orientation="h",
                     labels={"x": "filmes", "y": ""})
        fig.update_traces(marker_color=BLUE)
        add("Rostos mais frequentes", "Atores/atrizes (top 8 créditos por filme)", fig, 520)

    # ---------- mapa
    if "countries" in films:
        c = films["countries"].dropna().explode().dropna().value_counts()
        if len(c):
            dfc = pd.DataFrame({"iso2": c.index, "n": c.values})
            dfc["iso3"] = dfc["iso2"].map(ISO2_TO_ISO3)
            dfc = dfc.dropna(subset=["iso3"])
            fig = go.Figure(go.Choropleth(
                locations=dfc["iso3"], z=dfc["n"],
                colorscale=[[0, "#2c3440"], [.4, "#0e7a3a"], [1, GREEN]],
                marker_line_color=BG,
                colorbar=dict(title="filmes", tickfont=dict(color=TEXT))))
            fig.update_geos(bgcolor=CARD, showframe=False, coastlinecolor="#2c3440",
                            landcolor="#232b32", showland=True,
                            projection_type="natural earth")
            top5 = ", ".join(f"{i} ({v})" for i, v in c.head(5).items())
            add("Mapa do seu cinema", f"País de produção — top: {top5}", fig, 520)

    # ---------- idiomas
    if "language" in films:
        lang = films["language"].dropna().value_counts().head(12)
        if len(lang):
            fig = px.pie(values=lang.values, names=lang.index, hole=.55)
            fig.update_traces(textinfo="label+percent")
            add("Idiomas originais", "", fig, 420)

    # ---------- duração
    if "runtime" in films:
        rt = films["runtime"].dropna()
        rt = rt[rt > 0]
        if len(rt):
            fig = px.histogram(rt, nbins=40, labels={"value": "minutos"})
            fig.update_traces(marker_color=ORANGE)
            fig.update_layout(showlegend=False, yaxis_title="filmes")
            longest = films.loc[films["runtime"].idxmax()]
            add("Duração",
                f"Mediana {rt.median():.0f} min — mais longo: <b>{longest['Name']}</b> "
                f"({int(longest['runtime'])} min)", fig, 380)

    # ---------- rewatches
    if diary is not None and len(diary):
        rw = stats.most_rewatched(diary)
        if len(rw):
            fig = px.bar(x=rw.values[::-1], y=rw.index[::-1], orientation="h",
                         labels={"x": "vezes no diário", "y": ""})
            fig.update_traces(marker_color="#f15bb5")
            add("Filmes-conforto", "Os que você mais revê", fig, 380)

    # ---------- obscurômetro
    if "tmdb_votes" in films and films["tmdb_votes"].notna().any():
        v = films.dropna(subset=["tmdb_votes"])
        obscure = v[v["tmdb_votes"] < 200].sort_values("tmdb_votes").head(10)
        if len(obscure):
            fig = px.bar(obscure[::-1], x="tmdb_votes", y="Name", orientation="h",
                         labels={"tmdb_votes": "votos no TMDB", "Name": ""})
            fig.update_traces(marker_color="#9b5de5")
            add("Obscurômetro",
                "Os filmes mais desconhecidos que você já viu (menos votos no TMDB)",
                fig, 420)

    facts = insights.generate(films, diary)
    _write_html(cards, facts, sections, films, diary, out, year)
    return out


# ------------------------------------------------------------------ template


def _write_html(cards, facts, sections, films, diary, out: Path, year):
    cards_html = "".join(
        f'<div class="card"><div class="big">{v}</div><div class="lbl">{l}</div></div>'
        for v, l in cards
    )
    facts_html = ""
    if facts:
        items = "".join(f"<li>{f}</li>" for f in facts)
        facts_html = f'<section><h2>Insights</h2><ul class="facts">{items}</ul></section>'

    secs = ""
    for title, sub, body in sections:
        sub_html = f'<p class="sub">{sub}</p>' if sub else ""
        secs += f'<section><h2>{title}</h2>{sub_html}<div class="plot">{body}</div></section>\n'

    n_enriched = films["tmdb_id"].notna().sum() if "tmdb_id" in films else 0
    period = ""
    if diary is not None and len(diary):
        period = (f'{diary["Watched Date"].min():%d/%m/%Y} — '
                  f'{diary["Watched Date"].max():%d/%m/%Y}')
    title = f"Retrospectiva {year}" if year else "Letterboxd Explorer"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:{BG}; color:{TEXT};
         font-family: Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 24px 16px 80px; }}
  header {{ text-align:center; padding: 40px 0 10px; }}
  header h1 {{ font-size: 2.2rem; margin: 0;
    background: linear-gradient(90deg, {ORANGE}, {GREEN}, {BLUE});
    -webkit-background-clip: text; background-clip: text; color: transparent; }}
  header p {{ color:{MUTED}; margin-top: 8px; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:12px; justify-content:center;
            margin: 28px 0 8px; }}
  .card {{ background:{CARD}; border-radius:12px; padding:18px 22px;
           min-width:150px; text-align:center; border:1px solid #2c3440; }}
  .card .big {{ font-size:1.7rem; font-weight:700; color:{GREEN}; }}
  .card .lbl {{ color:{MUTED}; font-size:.85rem; margin-top:4px; }}
  section {{ margin-top: 42px; }}
  h2 {{ font-size:1.25rem; border-left:4px solid {ORANGE};
        padding-left:10px; margin-bottom:4px; }}
  .sub {{ color:{MUTED}; font-size:.9rem; margin:4px 0 12px 14px; }}
  .plot {{ background:{CARD}; border-radius:12px; padding:8px;
           border:1px solid #2c3440; }}
  .facts {{ list-style:none; padding:0; margin:12px 0 0; display:grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:10px; }}
  .facts li {{ background:{CARD}; border:1px solid #2c3440; border-radius:12px;
               padding:14px 16px; font-size:.95rem; }}
  .facts b {{ color:{GREEN}; }}
  footer {{ margin-top:60px; text-align:center; color:{MUTED}; font-size:.8rem; }}
  footer a {{ color:{BLUE}; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🎬 {title}</h1>
    <p>{len(films)} filmes · {n_enriched} enriquecidos via TMDB{(" · " + period) if period else ""}</p>
  </header>
  <div class="cards">{cards_html}</div>
  {facts_html}
  {secs}
  <footer>Gerado com <a href="https://github.com/arthurmotta/letterboxd-explorer">Letterboxd
    Explorer</a> · dados de filmes por <a href="https://www.themoviedb.org">TMDB</a>
    (este produto usa a API do TMDB mas não é endossado ou certificado pelo TMDB).</footer>
</div>
</body>
</html>"""
    out.write_text(html, encoding="utf-8")
    return out
