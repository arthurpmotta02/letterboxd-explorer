"""Geração do relatório HTML interativo (arquivo único, Plotly via CDN)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from letterboxd_explorer import insights, stats
from letterboxd_explorer.ingest import parse_dates

# ------------------------------------------------------------------- tema

BG, CARD, TEXT, MUTED = "#14181c", "#1b2228", "#dfe7ef", "#99aabb"
GRID = "#242c34"
ORANGE, GREEN, BLUE = "#ff8000", "#00e054", "#40bcf4"
PURPLE, PINK, YELLOW, RED = "#9b5de5", "#f15bb5", "#f4d35e", "#ff5c5c"
PALETTE = [GREEN, ORANGE, BLUE, YELLOW, "#ee6c4d", PURPLE,
           "#00bbf9", PINK, "#8ac926", RED]
GRAD = {
    GREEN: "#0e4429", ORANGE: "#5c2e00", BLUE: "#0f3a52",
    PURPLE: "#2e1b4d", PINK: "#4d1230", YELLOW: "#4d3f00",
}
PT_MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
PT_WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
LANG_NAMES = {
    "en": "Inglês", "pt": "Português", "es": "Espanhol", "fr": "Francês",
    "it": "Italiano", "de": "Alemão", "ja": "Japonês", "ko": "Coreano",
    "zh": "Mandarim", "cn": "Cantonês", "ru": "Russo", "hi": "Hindi",
    "fa": "Persa", "sv": "Sueco", "da": "Dinamarquês", "no": "Norueguês",
    "fi": "Finlandês", "pl": "Polonês", "cs": "Tcheco", "tr": "Turco",
    "ar": "Árabe", "he": "Hebraico", "th": "Tailandês", "id": "Indonésio",
    "nl": "Holandês", "el": "Grego", "hu": "Húngaro", "ro": "Romeno",
}

pio.templates["lb"] = go.layout.Template(
    layout=dict(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, Helvetica, Arial, sans-serif", size=13),
        colorway=PALETTE,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, automargin=True,
                   title_standoff=14, ticks="outside", tickcolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, automargin=True,
                   title_standoff=14, ticks="outside", tickcolor=GRID),
        bargap=0.3,
        hoverlabel=dict(bgcolor="#0e1216", bordercolor="#2c3440",
                        font=dict(color=TEXT, size=13)),
        margin=dict(l=60, r=26, t=30, b=54),
    )
)
pio.templates.default = "lb"

ISO2_TO_ISO3 = {
    # África
    "DZ": "DZA", "AO": "AGO", "BJ": "BEN", "BW": "BWA", "BF": "BFA", "BI": "BDI",
    "CV": "CPV", "CM": "CMR", "CF": "CAF", "TD": "TCD", "KM": "COM", "CG": "COG",
    "CD": "COD", "CI": "CIV", "DJ": "DJI", "EG": "EGY", "GQ": "GNQ", "ER": "ERI",
    "SZ": "SWZ", "ET": "ETH", "GA": "GAB", "GM": "GMB", "GH": "GHA", "GN": "GIN",
    "GW": "GNB", "KE": "KEN", "LS": "LSO", "LR": "LBR", "LY": "LBY", "MG": "MDG",
    "MW": "MWI", "ML": "MLI", "MR": "MRT", "MU": "MUS", "MA": "MAR", "MZ": "MOZ",
    "NA": "NAM", "NE": "NER", "NG": "NGA", "RW": "RWA", "ST": "STP", "SN": "SEN",
    "SC": "SYC", "SL": "SLE", "SO": "SOM", "ZA": "ZAF", "SS": "SSD", "SD": "SDN",
    "TZ": "TZA", "TG": "TGO", "TN": "TUN", "UG": "UGA", "ZM": "ZMB", "ZW": "ZWE",
    # Américas
    "AG": "ATG", "BS": "BHS", "BB": "BRB", "BZ": "BLZ", "CA": "CAN", "CR": "CRI",
    "CU": "CUB", "DM": "DMA", "DO": "DOM", "SV": "SLV", "GD": "GRD", "GT": "GTM",
    "HT": "HTI", "HN": "HND", "JM": "JAM", "MX": "MEX", "NI": "NIC", "PA": "PAN",
    "KN": "KNA", "LC": "LCA", "VC": "VCT", "TT": "TTO", "US": "USA", "PR": "PRI",
    "AR": "ARG", "BO": "BOL", "BR": "BRA", "CL": "CHL", "CO": "COL", "EC": "ECU",
    "GY": "GUY", "PY": "PRY", "PE": "PER", "SR": "SUR", "UY": "URY", "VE": "VEN",
    "GL": "GRL",
    # Ásia e Oriente Médio
    "AF": "AFG", "AM": "ARM", "AZ": "AZE", "BH": "BHR", "BD": "BGD", "BT": "BTN",
    "BN": "BRN", "KH": "KHM", "CN": "CHN", "CY": "CYP", "GE": "GEO", "IN": "IND",
    "ID": "IDN", "IR": "IRN", "IQ": "IRQ", "IL": "ISR", "JP": "JPN", "JO": "JOR",
    "KZ": "KAZ", "KW": "KWT", "KG": "KGZ", "LA": "LAO", "LB": "LBN", "MY": "MYS",
    "MV": "MDV", "MN": "MNG", "MM": "MMR", "NP": "NPL", "KP": "PRK", "OM": "OMN",
    "PK": "PAK", "PS": "PSE", "PH": "PHL", "QA": "QAT", "SA": "SAU", "SG": "SGP",
    "KR": "KOR", "LK": "LKA", "SY": "SYR", "TW": "TWN", "TJ": "TJK", "TH": "THA",
    "TL": "TLS", "TR": "TUR", "TM": "TKM", "AE": "ARE", "UZ": "UZB", "VN": "VNM",
    "YE": "YEM", "HK": "HKG", "MO": "MAC",
    # Europa
    "AL": "ALB", "AD": "AND", "AT": "AUT", "BY": "BLR", "BE": "BEL", "BA": "BIH",
    "BG": "BGR", "HR": "HRV", "CZ": "CZE", "DK": "DNK", "EE": "EST", "FI": "FIN",
    "FR": "FRA", "DE": "DEU", "GR": "GRC", "HU": "HUN", "IS": "ISL", "IE": "IRL",
    "IT": "ITA", "LV": "LVA", "LI": "LIE", "LT": "LTU", "LU": "LUX", "MT": "MLT",
    "MD": "MDA", "MC": "MCO", "ME": "MNE", "NL": "NLD", "MK": "MKD", "NO": "NOR",
    "PL": "POL", "PT": "PRT", "RO": "ROU", "RU": "RUS", "SM": "SMR", "RS": "SRB",
    "SK": "SVK", "SI": "SVN", "ES": "ESP", "SE": "SWE", "CH": "CHE", "UA": "UKR",
    "GB": "GBR",
    # Oceania
    "AU": "AUS", "FJ": "FJI", "KI": "KIR", "MH": "MHL", "FM": "FSM", "NR": "NRU",
    "NZ": "NZL", "PW": "PLW", "PG": "PNG", "WS": "WSM", "SB": "SLB", "TO": "TON",
    "TV": "TUV", "VU": "VUT",
    # códigos históricos usados pelo TMDB
    "SU": "RUS", "XC": "CZE", "CS": "SRB", "YU": "SRB", "DD": "DEU", "XG": "DEU",
}


def _fig_html(fig, height=420):
    fig.update_layout(height=height)
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=False,
        config={"displaylogo": False, "responsive": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )


def _hbar(series, color, unit="filmes"):
    s = series[::-1]
    fig = go.Figure(go.Bar(
        x=s.values, y=list(s.index), orientation="h",
        marker=dict(color=list(s.values),
                    colorscale=[[0, GRAD.get(color, color)], [1, color]],
                    line_width=0),
        hovertemplate="%{y}: %{x} " + unit + "<extra></extra>"))
    fig.update_layout(xaxis_title=unit, bargap=0.35)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def _kde(values, n_hist_bins=40):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 15 or v.std() == 0:
        return None
    bw = 1.06 * v.std() * len(v) ** -0.2
    xs = np.linspace(v.min(), v.max(), 240)
    dens = np.exp(-0.5 * ((xs[:, None] - v[None, :]) / bw) ** 2).sum(axis=1)
    dens /= len(v) * bw * np.sqrt(2 * np.pi)
    binw = (v.max() - v.min()) / n_hist_bins
    return xs, dens * len(v) * binw


SAVE_FIGS = {
    "Perfil por gênero": "perfil_por_genero",
    "Volume mensal": "volume_mensal",
    "Calendário de atividade": "calendario_atividade",
    "Padrão semanal e mensal": "padrao_semanal",
    "Distribuição das notas": "distribuicao_notas",
    "Sua nota × nota TMDB": "voce_vs_tmdb",
    "Maiores divergências vs. TMDB": "maiores_divergencias",
    "Lançamento × visualização": "lancamento_x_visualizacao",
    "Popularidade × avaliação": "popularidade_x_avaliacao",
    "Distribuição das notas por gênero": "boxplot_generos",
    "Evolução dos gêneros": "evolucao_generos",
    "Sazonalidade dos gêneros": "sazonalidade_generos",
    "Keywords (microgêneros)": "keywords_microgeneros",
    "Diretores: volume × avaliação × consistência": "diretores_volume_avaliacao",
    "Rede de colaborações diretor–ator": "rede_colaboracoes",
    "Países de produção": "mapa_paises",
}

POSTER_BASE = "https://image.tmdb.org/t/p/w185"


def _poster_grid(items) -> str:
    """Grade de pôsteres (HTML puro). items: dicts com name/year/poster/lines/badge."""
    cells = ""
    for it in items:
        img = (f'<img src="{POSTER_BASE}{it["poster"]}" alt="" loading="lazy">'
               if it.get("poster") else '<div class="noposter">🎬</div>')
        badge = f'<span class="badge">{it["badge"]}</span>' if it.get("badge") else ""
        meta = "".join(f'<div class="pmeta">{ln}</div>' for ln in it.get("lines", []))
        cells += (f'<figure class="pcell">{badge}{img}<figcaption>'
                  f'<div class="pname">{it["name"]} ({it["year"]})</div>{meta}'
                  "</figcaption></figure>")
    return f'<div class="postergrid">{cells}</div>'


def _hist_kde(values, color, xlabel):
    fig = px.histogram(values, nbins=40, labels={"value": xlabel})
    fig.update_traces(marker=dict(color=color, opacity=.75, line_width=0))
    kde = _kde(values)
    if kde:
        xs, ys = kde
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="densidade",
                                 line=dict(color=TEXT, width=2, shape="spline")))
    fig.update_layout(showlegend=False, yaxis_title="filmes")
    return fig


def _network_fig(pairs: pd.Series):
    """Diagrama bipartido diretor–ator: espessura = filmes juntos."""
    directors = pairs.groupby(level=0).sum().sort_values(ascending=False)
    actors = pairs.groupby(level=1).sum().sort_values(ascending=False)
    yd = {d: i / max(len(directors) - 1, 1) for i, d in enumerate(directors.index)}
    ya = {a: i / max(len(actors) - 1, 1) for i, a in enumerate(actors.index)}
    fig = go.Figure()
    for (d, a), w in pairs.items():
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[yd[d], ya[a]], mode="lines",
            line=dict(width=1 + w * 1.4, color="rgba(0,224,84,.28)"),
            hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=[0] * len(directors), y=[yd[d] for d in directors.index],
        mode="markers+text", text=list(directors.index),
        textposition="middle left", textfont=dict(size=11.5, color=TEXT),
        marker=dict(size=directors.values / directors.max() * 18 + 9,
                    color=ORANGE, line=dict(width=1.5, color=CARD)),
        customdata=directors.values,
        hovertemplate="%{text}: %{customdata} colaborações<extra></extra>",
        showlegend=False))
    fig.add_trace(go.Scatter(
        x=[1] * len(actors), y=[ya[a] for a in actors.index],
        mode="markers+text", text=list(actors.index),
        textposition="middle right", textfont=dict(size=11.5, color=TEXT),
        marker=dict(size=actors.values / actors.max() * 18 + 9,
                    color=BLUE, line=dict(width=1.5, color=CARD)),
        customdata=actors.values,
        hovertemplate="%{text}: %{customdata} colaborações<extra></extra>",
        showlegend=False))
    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.75, 1.75]),
        yaxis=dict(visible=False, range=[-0.08, 1.08]),
        margin=dict(l=10, r=10, t=20, b=20))
    return fig


def _activity(diary: pd.DataFrame | None, frames: dict):
    """Base temporal do relatório.

    Usa o diário quando ele tem volume; caso contrário cai para as datas de
    watched.csv (dia em que o filme foi marcado como visto), descartando dias
    de importação em massa que distorceriam a série.
    """
    if diary is not None and len(diary) >= 30:
        return diary, ""
    w = frames.get("watched")
    if w is None or "Date" not in w:
        return diary, ""
    w = w.copy()
    w["Watched Date"] = parse_dates(w["Date"])
    w = w.dropna(subset=["Watched Date"])
    w["Year"] = pd.to_numeric(w["Year"], errors="coerce").astype("Int64")
    w["Rewatch"] = False
    w["Rating"] = pd.NA
    per_day = w.groupby(w["Watched Date"].dt.normalize()).size()
    bulk_days = per_day[per_day > max(15, int(len(w) * 0.08))].index
    w = w[~w["Watched Date"].dt.normalize().isin(bulk_days)]
    if len(w) > (0 if diary is None else len(diary)):
        cols = ["Name", "Year", "Watched Date", "Rewatch", "Rating"]
        return w[cols].reset_index(drop=True), \
            " · datas em que os filmes foram marcados como assistidos"
    return diary, ""


# ------------------------------------------------------------------ seções


def build_report(
    films: pd.DataFrame,
    diary: pd.DataFrame | None,
    frames: dict,
    out: Path,
    year: int | None = None,
    save_figs: Path | None = None,
) -> Path:
    """Monta o relatório. Sem `year`, gera abas: Tudo + um ano por aba."""
    diary, date_note = _activity(diary, frames)

    registry: dict = {}
    tabs: list[tuple[str, list, list, list]] = []
    label = f"Retrospectiva {year}" if year else "Tudo"
    cards, facts, sections = _build_content(films, diary, frames,
                                            main=year is None, note=date_note,
                                            registry=registry)
    tabs.append((label, cards, facts, sections))

    if year is None and diary is not None and len(diary):
        years = sorted(diary["Watched Date"].dt.year.unique(), reverse=True)
        years = [y for y in years
                 if (diary["Watched Date"].dt.year == y).sum() >= 5][:8]
        if len(years) >= 2:
            for y in years:
                d = diary[diary["Watched Date"].dt.year == y].reset_index(drop=True)
                keys = set(zip(d["Name"], d["Year"]))
                f = films[[(n, yy) in keys
                           for n, yy in zip(films["Name"], films["Year"])]]
                c, fa, se = _build_content(f.reset_index(drop=True), d, frames,
                                           main=False, note=date_note)
                tabs.append((str(y), c, fa, se))

    _write_html(tabs, films, diary, frames, out, year)
    if save_figs:
        _export_figs(registry, Path(save_figs))
    return out


def _export_figs(registry: dict, folder: Path) -> None:
    """Exporta as figuras principais como PNG (requer o pacote kaleido)."""
    folder.mkdir(parents=True, exist_ok=True)
    try:
        for name, (fig, height) in registry.items():
            fig.write_image(str(folder / f"{name}.png"),
                            width=1000, height=height, scale=2)
        print(f"✔ {len(registry)} figuras salvas em {folder.resolve()}")
    except Exception as e:
        print("! Não foi possível exportar PNGs. Instale: pip install kaleido "
              "(requer Google Chrome) ou, sem Chrome: "
              f"pip install kaleido==0.2.1  ({e})")


def _build_content(
    films: pd.DataFrame,
    diary: pd.DataFrame | None,
    frames: dict,
    main: bool = True,
    note: str = "",
    registry: dict | None = None,
):
    sections: list[tuple[str, str, str, str]] = []

    def add(grp, title, sub, fig, height=420):
        if registry is not None and title in SAVE_FIGS:
            registry[SAVE_FIGS[title]] = (fig, height)
        sections.append((grp, title, sub, _fig_html(fig, height)))

    def add_html(grp, title, sub, html):
        sections.append((grp, title, sub, html))

    rated = films.dropna(subset=["Rating"])
    hours = films["runtime"].dropna().sum() / 60 if "runtime" in films else 0
    has_diary = diary is not None and len(diary) >= 5

    # ================================================== cards
    cards = [
        (f"{len(films):,}".replace(",", "."), "filmes assistidos"),
        (f"{hours:,.0f} h".replace(",", "."), f"de tela (≈ {hours / 24:.0f} dias)"),
        (f"{rated['Rating'].mean():.2f} ★" if len(rated) else "—", "nota média"),
    ]
    if has_diary:
        per_year = diary.groupby(diary["Watched Date"].dt.year).size()
        if len(per_year) and main:
            cards.append((str(int(per_year.max())),
                          f"recorde em um ano ({per_year.idxmax()})"))
        n_rw = int(diary["Rewatch"].sum())
        if n_rw:
            cards.append((str(n_rw), "rewatches no diário"))
    if "watchlist" in frames and main:
        cards.append((f"{len(frames['watchlist']):,}".replace(",", "."),
                      "na watchlist"))

    # ================================================== visão geral
    G = "Visão geral"
    g_all = stats.explode_count(films, "genres", 8)
    if len(g_all) >= 3:
        vals = (g_all / g_all.max()).tolist()
        theta = list(g_all.index)
        fig = go.Figure(go.Scatterpolar(
            r=vals + vals[:1], theta=theta + theta[:1],
            fill="toself", line=dict(color=GREEN, width=2.5),
            fillcolor="rgba(0,224,84,.18)",
            hovertemplate="%{theta}<extra></extra>"))
        fig.update_layout(
            polar=dict(bgcolor=CARD,
                       radialaxis=dict(visible=False, range=[0, 1.02]),
                       angularaxis=dict(gridcolor=GRID, linecolor=GRID)),
            showlegend=False, margin=dict(l=80, r=80, t=40, b=40))
        add(G, "Perfil por gênero", "Volume relativo dos seus 8 gêneros mais vistos",
            fig, 440)

    # ================================================== linha do tempo
    G = "Linha do tempo"
    if has_diary:
        if len(diary) >= 10:
            m = diary.set_index("Watched Date").resample("ME").size()
            fig = go.Figure(go.Scatter(
                x=m.index, y=m.values, mode="lines", name="mensal",
                line=dict(color=GREEN, width=1.5, shape="spline", smoothing=.6),
                fill="tozeroy", fillcolor="rgba(0,224,84,.10)",
                hovertemplate="%{x|%b %Y}: %{y} filmes<extra></extra>"))
            if len(m) >= 6:
                roll = m.rolling(3, center=True).mean()
                fig.add_trace(go.Scatter(
                    x=roll.index, y=roll.values, mode="lines",
                    name="média móvel (3 meses)",
                    line=dict(color=TEXT, width=2.5),
                    hovertemplate="%{x|%b %Y}: %{y:.1f}<extra>média móvel</extra>"))
            fig.update_layout(yaxis_title="filmes por mês",
                              legend=dict(orientation="h", y=1.12))
            add(G, "Volume mensal",
                f"Filmes por mês; a linha clara suaviza picos de maratona{note}",
                fig, 370)

        cal = stats.weekly_calendar(diary)
        if len(cal) and cal.values.sum() >= 20:
            fig = go.Figure(go.Heatmap(
                z=cal.values, x=list(cal.columns), y=[str(y) for y in cal.index],
                colorscale=[[0, "#20262c"], [.01, "#0e4429"],
                            [.4, "#26a641"], [1, "#39d353"]],
                zmin=0, showscale=False, xgap=2.5, ygap=5,
                hovertemplate="semana %{x} de %{y}: %{z} filmes<extra></extra>"))
            fig.update_layout(xaxis_title="semana do ano",
                              yaxis=dict(autorange="reversed"))
            add(G, "Calendário de atividade", f"Filmes por semana{note}",
                fig, max(230, 140 + 44 * len(cal)))

        cum = stats.cumulative_films(diary)
        fig = go.Figure(go.Scatter(
            x=cum.index, y=cum.values, mode="lines",
            line=dict(color=BLUE, width=2.5),
            fill="tozeroy", fillcolor="rgba(64,188,244,.10)",
            hovertemplate="%{x|%d/%m/%Y}: %{y} filmes<extra></extra>"))
        fig.update_layout(yaxis_title="total acumulado")
        add(G, "Acumulado de visualizações", f"Total acumulado{note}", fig, 360)

        if len(diary) >= 30:
            hm = pd.crosstab(diary["Watched Date"].dt.dayofweek,
                             diary["Watched Date"].dt.month)
            hm = hm.reindex(index=range(7), columns=range(1, 13), fill_value=0)
            fig = go.Figure(go.Heatmap(
                z=hm.values, x=PT_MONTHS, y=PT_WEEKDAYS,
                colorscale=[[0, "#20262c"], [.01, "#0e4429"], [1, "#39d353"]],
                showscale=False, xgap=3, ygap=3,
                hovertemplate="%{y}, %{x}: %{z} filmes<extra></extra>"))
            add(G, "Padrão semanal e mensal", f"Dia da semana × mês{note}", fig, 340)

    # ================================================== suas notas
    G = "Suas notas"
    if len(rated) >= 5:
        dist = stats.rating_distribution(films)
        media = rated["Rating"].mean()
        fig = go.Figure(go.Bar(
            x=dist.index, y=dist.values,
            marker=dict(color=list(dist.values),
                        colorscale=[[0, GRAD[ORANGE]], [1, ORANGE]], line_width=0),
            hovertemplate="%{x}★: %{y} filmes<extra></extra>"))
        fig.add_vline(x=media, line_dash="dot", line_color=TEXT,
                      annotation_text=f"média {media:.2f}",
                      annotation_font_color=TEXT)
        fig.update_layout(xaxis_title="nota (★)", yaxis_title="filmes",
                          xaxis=dict(dtick=0.5))
        add(G, "Distribuição das notas",
            f"{len(rated)} filmes avaliados · mediana {rated['Rating'].median():.1f}★",
            fig, 380)

    if has_diary:
        yearly = stats.rating_over_time(diary, films)
        if len(yearly) >= 2:
            fig = go.Figure(go.Scatter(
                x=yearly.index, y=yearly.values, mode="lines+markers",
                line=dict(color=ORANGE, width=2.5),
                marker=dict(size=9, color=ORANGE, line=dict(width=2, color=CARD)),
                hovertemplate="%{x}: %{y:.2f}★<extra></extra>"))
            fig.update_layout(xaxis_title="ano", yaxis_title="nota média",
                              xaxis=dict(dtick=1))
            add(G, "Evolução da nota média",
                "Nota média por ano em que assistiu (mín. 10 notas/ano)", fig, 350)

    her = stats.heresies(films)
    if len(her) >= 10:
        fig = px.scatter(
            her, x="tmdb_5", y="Rating", hover_name="Name",
            color="diff", color_continuous_scale=[RED, "#5a6672", GREEN],
            opacity=.75, marginal_x="histogram", marginal_y="histogram",
            labels={"tmdb_5": "nota TMDB (0 a 5)", "Rating": "sua nota"})
        fig.add_shape(type="line", x0=0, y0=0, x1=5, y1=5,
                      line=dict(color=MUTED, dash="dot"))
        fig.update_layout(coloraxis_showscale=False)
        add(G, "Sua nota × nota TMDB",
            "Acima da linha pontilhada = você avalia melhor que a média", fig, 520)

        her10 = pd.concat([her.nlargest(6, "diff"),
                           her.nsmallest(6, "diff")]).sort_values("diff")
        fig = go.Figure(go.Bar(
            x=her10["diff"], y=her10["Name"], orientation="h",
            marker=dict(color=[GREEN if d > 0 else RED for d in her10["diff"]],
                        line_width=0),
            hovertemplate="%{y}: %{x:+.1f}★ vs TMDB<extra></extra>"))
        fig.add_vline(x=0, line_color=MUTED)
        fig.update_layout(xaxis_title="sua nota − nota TMDB (★)", bargap=0.35)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        add(G, "Maiores divergências vs. TMDB",
            "À direita: você avalia acima da média. À esquerda: abaixo.", fig, 440)

    pf = stats.personal_favorites(films)
    n_top = int((rated["Rating"] >= 4.5).sum()) if len(rated) else 0
    pf_sub = (f"Você deu 4.5★ ou 5★ a {n_top} filmes; ranqueá-los entre si não "
              "diz nada. O informativo é a distância da média: estes são os "
              "favoritos que mais dependem do <i>seu</i> gosto (30+ votos no TMDB).")
    if len(pf) >= 5 and "poster" in pf and pf["poster"].notna().sum() >= 5:
        items = [dict(name=r.Name, year=r.Year, poster=r.poster,
                      lines=[f"sua {r.Rating:g}★ · TMDB {r.tmdb_rating / 2:.1f}★",
                             f"Δ +{r.diff:.1f}"])
                 for r in pf.itertuples()]
        add_html(G, "Favoritos mais pessoais", pf_sub, _poster_grid(items))
    elif len(pf) >= 5:
        fig = go.Figure(go.Table(
            columnwidth=[3, 1, 1, 1, 1],
            header=dict(values=["<b>Filme</b>", "<b>Ano</b>", "<b>Sua nota</b>",
                                "<b>TMDB</b>", "<b>Δ</b>"],
                        fill_color="#2c3440", font=dict(color=TEXT, size=13),
                        align="left", height=30),
            cells=dict(values=[pf["Name"], pf["Year"].astype(str),
                               pf["Rating"].map(lambda x: f"{x:g}★"),
                               pf["tmdb_rating"].map(lambda x: f"{x / 2:.1f}★"),
                               pf["diff"].map(lambda x: f"+{x:.1f}")],
                       fill_color=[[CARD, "#1e262d"] * 5],
                       font=dict(color=TEXT, size=12.5),
                       align="left", height=28)))
        fig.update_layout(margin=dict(l=8, r=8, t=8, b=8))
        add(G, "Favoritos mais pessoais", pf_sub, fig, 380)

    if "poster" in films and "genres" in films and films["poster"].notna().any():
        expl_g = rated.explode("genres").dropna(subset=["genres"])
        if len(expl_g):
            champs, used = [], set()
            for gen in expl_g["genres"].value_counts().head(6).index:
                grp_df = expl_g[(expl_g["genres"] == gen) & ~expl_g["Name"].isin(used)]
                if grp_df.empty:
                    continue
                if "tmdb_votes" in grp_df:
                    grp_df = grp_df.sort_values(["Rating", "tmdb_votes"],
                                                ascending=False)
                else:
                    grp_df = grp_df.sort_values("Rating", ascending=False)
                best = grp_df.iloc[0]
                used.add(best["Name"])
                champs.append(dict(name=best["Name"], year=best["Year"],
                                   poster=best.get("poster"), badge=gen,
                                   lines=[f"{best['Rating']:g}★"]))
            if len(champs) >= 4:
                add_html(G, "Melhor avaliado por gênero",
                         "Sua maior nota em cada um dos gêneros mais vistos",
                         _poster_grid(champs))

    if "poster" in films and "tmdb_votes" in films:
        gems = films.dropna(subset=["Rating", "tmdb_votes"])
        gems = gems[(gems["Rating"] >= 4.5) & (gems["tmdb_votes"].between(30, 1500))]
        gems = gems.sort_values("tmdb_votes").head(8)
        if len(gems) >= 4 and gems["poster"].notna().sum() >= 4:
            items = [dict(name=r.Name, year=r.Year, poster=r.poster,
                          lines=[f"{r.Rating:g}★ · {int(r.tmdb_votes)} votos"])
                     for r in gems.itertuples()]
            add_html(G, "Joias escondidas",
                     "Nota 4.5★+ sua em filmes que pouca gente viu "
                     "(30 a 1500 votos no TMDB)", _poster_grid(items))

    if "tmdb_votes" in films:
        pop = films.dropna(subset=["tmdb_votes", "Rating"])
        pop = pop[pop["tmdb_votes"] > 0]
        if len(pop) >= 30:
            fig = go.Figure(go.Scatter(
                x=pop["tmdb_votes"], y=pop["Rating"], mode="markers",
                text=pop["Name"],
                marker=dict(size=7, color=pop["Rating"],
                            colorscale=[[0, GRAD[PURPLE]], [1, GREEN]],
                            showscale=False, opacity=.7, line_width=0),
                hovertemplate="%{text}: %{y}★, %{x} votos<extra></extra>"))
            trend = stats.binned_trend(np.log10(pop["tmdb_votes"]), pop["Rating"])
            if trend:
                xs, ys = trend
                fig.add_trace(go.Scatter(
                    x=10 ** xs, y=ys, mode="lines+markers", name="tendência",
                    line=dict(color=TEXT, width=2.5),
                    marker=dict(size=6, color=TEXT),
                    hovertemplate="nota média %{y:.2f}<extra>tendência</extra>"))
            fig.update_xaxes(type="log", title="votos no TMDB (escala log)")
            fig.update_yaxes(title="sua nota", dtick=0.5)
            fig.update_layout(showlegend=False)
            add(G, "Popularidade × avaliação",
                "Cada ponto é um filme; a linha clara é a nota média por faixa "
                "de popularidade. Ela sobe ou desce com a fama?", fig, 460)

    # ================================================== o que você assiste
    G = "O que você assiste"
    dec = stats.decade_counts(films)
    if len(dec):
        fig = go.Figure(go.Bar(
            x=[str(d) for d in dec.index], y=dec.values,
            marker=dict(color=list(dec.values),
                        colorscale=[[0, GRAD[GREEN]], [1, GREEN]], line_width=0),
            hovertemplate="anos %{x}: %{y} filmes<extra></extra>"))
        fig.update_layout(xaxis_title="década de lançamento", yaxis_title="filmes")
        add(G, "Filmes por década de lançamento", "", fig, 370)

    rd = stats.rating_by_decade(films)
    if len(rd) >= 3:
        fig = go.Figure(go.Scatter(
            x=[str(d) for d in rd.index], y=rd["mean"], mode="lines+markers",
            line=dict(color=ORANGE, width=2.5),
            marker=dict(size=(rd["count"] / rd["count"].max() * 22 + 8),
                        color=ORANGE, line=dict(width=2, color=CARD)),
            customdata=rd["count"],
            hovertemplate="anos %{x}: %{y:.2f}★ (%{customdata} filmes)<extra></extra>"))
        fig.update_layout(xaxis_title="década de lançamento",
                          yaxis_title="sua nota média")
        add(G, "Avaliação por década de lançamento",
            "Bolha maior = mais filmes avaliados naquela década", fig, 360)

    if has_diary:
        gap = stats.watch_gap(films, diary)
        if len(gap) >= 30:
            fig = _hist_kde(gap, PURPLE, "anos entre lançamento e visualização")
            add(G, "Defasagem lançamento → visualização",
                f"Mediana de {gap.median():.0f} anos{note}", fig, 380)

    if has_diary:
        rv = stats.release_vs_watch(films, diary)
        if len(rv) >= 30:
            rv_r = rv.dropna(subset=["Rating"])
            rv_n = rv[rv["Rating"].isna()]
            fig = go.Figure()
            if len(rv_n):
                fig.add_trace(go.Scatter(
                    x=rv_n["release_year"], y=rv_n["watch_year"], mode="markers",
                    text=rv_n["Name"], marker=dict(size=6, color="#4a5762",
                                                   opacity=.5, line_width=0),
                    name="sem nota",
                    hovertemplate="%{text} (%{x})<extra></extra>"))
            if len(rv_r):
                fig.add_trace(go.Scatter(
                    x=rv_r["release_year"], y=rv_r["watch_year"], mode="markers",
                    text=rv_r["Name"],
                    marker=dict(size=7, color=rv_r["Rating"], cmin=0.5, cmax=5,
                                colorscale=[[0, RED], [.5, YELLOW], [1, GREEN]],
                                opacity=.85, line_width=0,
                                colorbar=dict(title="nota", outlinewidth=0,
                                              tickfont=dict(color=TEXT))),
                    name="com nota",
                    hovertemplate="%{text} (%{x}): %{marker.color}★<extra></extra>"))
            fig.update_layout(xaxis_title="ano de lançamento",
                              yaxis_title="ano em que você assistiu",
                              showlegend=False)
            add(G, "Lançamento × visualização",
                "Faixas horizontais revelam fases: o ano em que você mergulhou "
                f"numa década ou cineasta específico{note}", fig, 480)

    g = stats.explode_count(films, "genres", 15)
    if len(g):
        add(G, "Filmes por gênero", "Fonte: TMDB", _hbar(g, GREEN), 480)

        expl = rated.explode("genres").dropna(subset=["genres"]) \
            if "genres" in films else pd.DataFrame()
        if len(expl) >= 30:
            top8 = expl["genres"].value_counts().head(8).index
            expl8 = expl[expl["genres"].isin(top8)]
            order = expl8.groupby("genres")["Rating"].median().sort_values().index
            fig = go.Figure()
            for i, gen in enumerate(order):
                fig.add_trace(go.Box(
                    x=expl8.loc[expl8["genres"] == gen, "Rating"], name=gen,
                    marker_color=PALETTE[i % len(PALETTE)], boxmean=True,
                    orientation="h", boxpoints=False))
            fig.update_layout(showlegend=False, xaxis_title="sua nota (★)",
                              xaxis=dict(dtick=0.5))
            fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
            add(G, "Distribuição das notas por gênero",
                "Boxplot nos 8 gêneros mais vistos (traço central = mediana, "
                "linha tracejada = média)", fig, 460)

    if has_diary:
        trend = stats.genre_trend(diary, films)
        if len(trend) >= 3:
            fig = go.Figure()
            for i, col in enumerate(trend.columns):
                fig.add_trace(go.Scatter(
                    x=trend.index, y=trend[col], name=col, stackgroup="one",
                    line=dict(width=.5, color=PALETTE[i % len(PALETTE)]),
                    hovertemplate="%{y:.0%}<extra>" + str(col) + "</extra>"))
            fig.update_layout(yaxis_tickformat=".0%", yaxis_title="participação",
                              xaxis_title="ano", xaxis=dict(dtick=1),
                              legend=dict(orientation="h", y=-0.25))
            add(G, "Evolução dos gêneros",
                f"Participação dos gêneros mais vistos, ano a ano{note}", fig, 460)

        gm = stats.genre_month(diary, films)
        if len(gm) >= 3 and len(diary) >= 60:
            fig = go.Figure(go.Heatmap(
                z=gm.values, x=PT_MONTHS, y=list(gm.index),
                colorscale=[[0, "#20262c"], [1, ORANGE]], showscale=False,
                xgap=3, ygap=3,
                hovertemplate="%{y} em %{x}: %{z:.0%}<extra></extra>"))
            add(G, "Sazonalidade dos gêneros",
                "Distribuição de cada gênero ao longo do ano "
                "(cada linha soma 100%)", fig, 380)

    k = stats.explode_count(films, "keywords", 25)
    if len(k):
        add(G, "Keywords (microgêneros)", "Fonte: TMDB", _hbar(k, BLUE), 620)

    if "runtime" in films:
        rt = films["runtime"].dropna()
        rt = rt[rt > 0]
        if len(rt) >= 15:
            fig = _hist_kde(rt, ORANGE, "minutos")
            longest = films.loc[films["runtime"].idxmax()]
            add(G, "Distribuição de duração",
                f"Mediana {rt.median():.0f} min · mais longo: "
                f"<b>{longest['Name']}</b> ({int(longest['runtime'])} min)",
                fig, 380)

    rr = stats.rating_by_runtime(films)
    if len(rr) >= 3:
        fig = go.Figure(go.Bar(
            x=[str(i) for i in rr.index], y=rr["mean"],
            marker=dict(color=list(rr["mean"]),
                        colorscale=[[0, GRAD[BLUE]], [1, BLUE]], line_width=0),
            customdata=rr["count"],
            hovertemplate="%{x}: %{y:.2f}★ (%{customdata} filmes)<extra></extra>"))
        fig.update_yaxes(range=[max(0, rr["mean"].min() - .5),
                                min(5, rr["mean"].max() + .3)])
        fig.update_layout(xaxis_title="duração", yaxis_title="nota média")
        add(G, "Avaliação por faixa de duração",
            "Mín. 5 filmes avaliados por faixa", fig, 360)

    bb = stats.budget_buckets(films)
    if len(bb) and bb.sum() >= 20:
        fig = go.Figure(go.Bar(
            x=[str(i) for i in bb.index], y=bb.values,
            marker=dict(color=list(bb.values),
                        colorscale=[[0, GRAD[YELLOW]], [1, YELLOW]], line_width=0),
            hovertemplate="%{x}: %{y} filmes<extra></extra>"))
        fig.update_layout(yaxis_title="filmes")
        add(G, "Distribuição por orçamento de produção",
            "Quando informado no TMDB", fig, 360)

    if "tmdb_votes" in films and films["tmdb_votes"].notna().any():
        v = films.dropna(subset=["tmdb_votes"])
        zero = v[v["tmdb_votes"] == 0]
        obscure = v[(v["tmdb_votes"] > 0) & (v["tmdb_votes"] < 200)]
        obscure = obscure.sort_values("tmdb_votes").head(10)
        if len(obscure) >= 3:
            sub = "Menos votos no TMDB"
            if len(zero):
                sub += (f" · além destes, <b>{len(zero)} filmes</b> do seu "
                        "histórico não receberam voto nenhum")
            s = pd.Series(obscure["tmdb_votes"].values, index=obscure["Name"])
            add(G, "Filmes menos conhecidos do seu histórico", sub,
                _hbar(s[::-1], PURPLE, unit="votos"), 400)

    if has_diary:
        rw = stats.most_rewatched(diary)
        if len(rw) >= 3:
            add(G, "Rewatches mais frequentes", "Entradas repetidas no diário",
                _hbar(rw, PINK, unit="vezes"), 380)

    # ================================================== watchlist e resenhas
    if main:
        G = "Watchlist e resenhas"
        wl = frames.get("watchlist")
        if wl is not None and "Date" in wl and len(wl) >= 10:
            wl = wl.copy()
            wl["AddedDate"] = parse_dates(wl["Date"])
            growth = stats.watchlist_growth(wl)
            if len(growth) >= 10:
                fig = go.Figure(go.Scatter(
                    x=growth.index, y=growth.values, mode="lines",
                    line=dict(color=YELLOW, width=2.5),
                    fill="tozeroy", fillcolor="rgba(244,211,94,.10)",
                    hovertemplate="%{x|%d/%m/%Y}: %{y} filmes<extra></extra>"))
                fig.update_layout(yaxis_title="filmes na watchlist")
                add(G, "Crescimento da watchlist",
                    f"{len(wl)} filmes esperando · acumulado por data de adição",
                    fig, 360)

            old = stats.watchlist_oldest(wl)
            if len(old) >= 5:
                s = pd.Series(old["dias"].values,
                              index=[f"{n} ({y})" for n, y in
                                     zip(old["Name"], old["Year"])])
                add(G, "Mais antigos na watchlist",
                    "Dias desde que você adicionou e ainda não assistiu",
                    _hbar(s[::-1], YELLOW, unit="dias"), 400)

        reviews = frames.get("reviews")
        if reviews is not None and "Review" in reviews:
            words = stats.review_words(reviews)
            if len(words) >= 10:
                add(G, "Vocabulário das resenhas",
                    f"Palavras mais frequentes nas suas {len(reviews)} resenhas "
                    "(sem stopwords)", _hbar(words, PINK, unit="ocorrências"), 620)

    # ================================================== pessoas e lugares
    G = "Pessoas e lugares"
    ds = stats.director_stats_full(films, min_count=3)
    if len(ds) >= 5:
        fig = go.Figure(go.Scatter(
            x=ds["n"], y=ds["nota"], mode="markers+text",
            text=list(ds.index), textposition="top center",
            textfont=dict(size=11, color=MUTED),
            error_y=dict(type="data", array=ds["std"], visible=True,
                         color="rgba(153,170,187,.45)", thickness=1.5, width=4),
            customdata=np.stack([ds["std"], ds["bayes"]], axis=-1),
            marker=dict(size=ds["n"] / ds["n"].max() * 26 + 10,
                        color=ds["bayes"], cmin=max(0, ds["bayes"].min() - .3),
                        colorscale=[[0, GRAD[ORANGE]], [1, GREEN]],
                        showscale=False, line=dict(width=1.5, color=CARD)),
            hovertemplate=("%{text}: %{x} filmes, %{y:.2f}★ ± %{customdata[0]:.2f}"
                           "<br>média bayesiana %{customdata[1]:.2f}★"
                           "<extra></extra>")))
        fig.update_layout(xaxis_title="filmes vistos", yaxis_title="sua nota média")
        add(G, "Diretores: volume × avaliação × consistência",
            "Barra vertical = desvio-padrão (curta = consistente, longa = "
            "ama-ou-odeia); cor = média bayesiana, que desconta amostras pequenas",
            fig, 520)
    else:
        d = stats.explode_count(films, "directors", 15)
        if len(d):
            add(G, "Diretores mais vistos", "", _hbar(d, GREEN), 480)

    a = stats.explode_count(films, "cast", 15)
    if len(a):
        add(G, "Atores e atrizes mais frequentes",
            "Top 8 créditos de cada filme", _hbar(a, BLUE), 480)

    pairs = stats.collaboration_edges(films)
    if len(pairs) >= 5:
        add(G, "Rede de colaborações diretor–ator",
            "Parcerias com 2+ filmes no seu histórico; espessura da linha = "
            "filmes juntos. As \"panelinhas\" do seu cinema.",
            _network_fig(pairs), max(420, 40 * max(
                pairs.index.get_level_values(0).nunique(),
                pairs.index.get_level_values(1).nunique()) + 120))

    if "countries" in films:
        c = films["countries"].dropna().explode().dropna().value_counts()
        if len(c) >= 3:
            dfc = pd.DataFrame({"iso2": c.index, "n": c.values})
            dfc["iso3"] = dfc["iso2"].map(ISO2_TO_ISO3)
            dfc = dfc.dropna(subset=["iso3"])
            dfc["logn"] = np.log10(dfc["n"])
            ticks = [1, 3, 10, 30, 100, 300, 1000, 3000]
            ticks = [t for t in ticks if t <= dfc["n"].max()]
            fig = go.Figure(go.Choropleth(
                locations=dfc["iso3"], z=dfc["logn"], customdata=dfc["n"],
                colorscale=[[0, "#2c3440"], [.35, "#0e5a34"],
                            [.7, "#16b356"], [1, "#39d353"]],
                marker_line_color=BG, marker_line_width=.4,
                hovertemplate="%{location}: %{customdata} filmes<extra></extra>",
                colorbar=dict(title="filmes", tickvals=np.log10(ticks).tolist(),
                              ticktext=[str(t) for t in ticks],
                              tickfont=dict(color=TEXT), outlinewidth=0)))
            fig.update_geos(bgcolor=CARD, showframe=False, coastlinecolor=GRID,
                            landcolor="#232b32", showland=True,
                            projection_type="natural earth")
            fig.update_layout(margin=dict(l=8, r=8, t=8, b=8))
            top5 = ", ".join(f"{i} ({v})" for i, v in c.head(5).items())
            add(G, "Países de produção",
                f"Escala logarítmica · top: {top5}", fig, 520)

    if "language" in films:
        lang = films["language"].dropna().value_counts()
        if len(lang) >= 3:
            top = lang.head(8)
            outros = lang.iloc[8:].sum()
            names = [LANG_NAMES.get(cd, cd) for cd in top.index]
            vals = list(top.values)
            if outros:
                names.append("outros")
                vals.append(int(outros))
            fig = go.Figure(go.Pie(
                labels=names, values=vals, hole=.6,
                marker=dict(colors=PALETTE, line=dict(color=CARD, width=2)),
                textinfo="label+percent", textfont=dict(size=12.5),
                hovertemplate="%{label}: %{value} filmes<extra></extra>"))
            fig.update_layout(showlegend=False,
                              annotations=[dict(text="idiomas", showarrow=False,
                                                font=dict(color=MUTED, size=15))])
            add(G, "Idiomas originais", "", fig, 430)

    facts = insights.generate(films, diary, frames)
    return cards, facts, sections


# ------------------------------------------------------------------ template


def _render_tab(cards, facts, sections, idx: int = 0) -> str:
    cards_html = "".join(
        f'<div class="card"><div class="big">{v}</div><div class="lbl">{lbl}</div></div>'
        for v, lbl in cards
    )
    facts_html = ""
    if facts:
        items = "".join(f"<li>{f}</li>" for f in facts)
        facts_html = f'<section><h2>Insights</h2><ul class="facts">{items}</ul></section>'
    groups = list(dict.fromkeys(grp for grp, *_ in sections))
    nav = ""
    if len(groups) >= 3:
        links = " · ".join(f'<a href="#t{idx}-g{k}">{g}</a>'
                           for k, g in enumerate(groups))
        nav = f'<div class="quicknav">Ir para: {links}</div>'
    secs = ""
    current_group = None
    for grp, title, sub, body in sections:
        if grp != current_group:
            k = groups.index(grp)
            secs += f'<div class="group" id="t{idx}-g{k}"><span>{grp}</span></div>\n'
            current_group = grp
        sub_html = f'<p class="sub">{sub}</p>' if sub else ""
        secs += (f'<section><h2>{title}</h2>{sub_html}'
                 f'<div class="plot">{body}</div></section>\n')
    return f'<div class="cards">{cards_html}</div>\n{nav}\n{facts_html}\n{secs}'


def _write_html(tabs, films, diary, frames, out: Path, year):
    username = ""
    prof = frames.get("profile")
    if prof is not None and "Username" in prof and len(prof):
        username = str(prof["Username"].iloc[0])
    nav_html = ""
    panes_html = ""
    if len(tabs) > 1:
        nav_html = '<nav class="tabs">' + "".join(
            f'<button onclick="showTab({i})">{label}</button>'
            for i, (label, *_rest) in enumerate(tabs)
        ) + "</nav>"
    for i, (_label, cards, facts, sections) in enumerate(tabs):
        panes_html += (f'<div class="tabpane" id="tab-{i}">'
                       f"{_render_tab(cards, facts, sections, i)}</div>\n")

    n_enriched = films["tmdb_id"].notna().sum() if "tmdb_id" in films else 0
    period = ""
    if diary is not None and len(diary):
        period = (f'{diary["Watched Date"].min():%d/%m/%Y} a '
                  f'{diary["Watched Date"].max():%d/%m/%Y}')
    title = f"Retrospectiva {year}" if year else "Letterboxd Explorer"

    lead = ""
    top_g = stats.explode_count(films, "genres", 1)
    top_d = stats.explode_count(films, "directors", 1)
    rated_all = films.dropna(subset=["Rating"])
    if len(top_g) and len(top_d) and len(rated_all):
        lead = (f'<p class="lead">Um acervo dominado por <b>{top_g.index[0]}</b>, '
                f"com <b>{top_d.index[0]}</b> como presença mais constante e "
                f'nota média de <b>{rated_all["Rating"].mean():.2f}★</b>.</p>')

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
  .group {{ margin-top: 72px; padding-bottom: 8px;
            border-bottom: 1px solid #2c3440; }}
  .group span {{ color:{MUTED}; text-transform: uppercase;
                 letter-spacing: .14em; font-size: .78rem; font-weight: 600; }}
  section {{ margin-top: 34px; }}
  h2 {{ font-size:1.2rem; border-left:4px solid {ORANGE};
        padding-left:10px; margin-bottom:4px; }}
  .sub {{ color:{MUTED}; font-size:.9rem; margin:4px 0 12px 14px; }}
  .plot {{ background:{CARD}; border-radius:12px; padding:8px;
           border:1px solid #2c3440; }}
  .facts {{ list-style:none; padding:0; margin:12px 0 0; display:grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:10px; }}
  .facts li {{ background:{CARD}; border:1px solid #2c3440; border-radius:12px;
               padding:14px 16px; font-size:.95rem; }}
  .facts b {{ color:{GREEN}; }}
  .postergrid {{ display:grid; gap:14px; padding:10px;
                 grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }}
  .pcell {{ margin:0; position:relative; }}
  .pcell img {{ width:100%; border-radius:10px; display:block;
                border:1px solid #2c3440; }}
  .noposter {{ width:100%; aspect-ratio:2/3; border-radius:10px;
               background:#232b32; display:flex; align-items:center;
               justify-content:center; font-size:2rem;
               border:1px solid #2c3440; }}
  .badge {{ position:absolute; top:8px; left:8px; background:{GREEN};
            color:{BG}; font-size:.72rem; font-weight:700;
            padding:3px 9px; border-radius:12px; z-index:1; }}
  .pname {{ font-size:.85rem; font-weight:600; margin-top:7px; }}
  .pmeta {{ font-size:.78rem; color:{MUTED}; margin-top:2px; }}
  footer {{ margin-top:60px; text-align:center; color:{MUTED}; font-size:.8rem; }}
  footer a {{ color:{BLUE}; }}
  .tabs {{ position: sticky; top: 0; z-index: 10; background:{BG};
           display:flex; flex-wrap:wrap; gap:8px; justify-content:center;
           margin: 26px 0 6px; padding: 10px 0; }}
  .tabs button {{ background:{CARD}; color:{TEXT}; border:1px solid #2c3440;
                  border-radius:20px; padding:8px 18px; font-size:.95rem;
                  cursor:pointer; transition: all .15s; }}
  .tabs button:hover {{ border-color:{GREEN}; }}
  .tabs button.active {{ background:{GREEN}; color:{BG}; font-weight:700;
                         border-color:{GREEN}; }}
  html {{ scroll-behavior: smooth; }}
  .lead {{ color:{TEXT}; font-size:1.02rem; max-width:640px;
           margin: 14px auto 0; }}
  .lead b {{ color:{GREEN}; }}
  .quicknav {{ text-align:center; color:{MUTED}; font-size:.88rem;
               margin: 20px 0 4px; }}
  .quicknav a {{ color:{BLUE}; text-decoration:none; }}
  .quicknav a:hover {{ text-decoration:underline; }}
  #sidenav {{ position:fixed; left:18px; top:50%; transform:translateY(-50%);
              z-index:15; display:none; flex-direction:column; gap:6px;
              max-width:180px; }}
  @media (min-width: 1400px) {{ #sidenav {{ display:flex; }} }}
  #sidenav a {{ background:{CARD}; color:{MUTED}; border:1px solid #2c3440;
                border-radius:10px; padding:7px 12px; font-size:.8rem;
                text-decoration:none; transition:.15s; }}
  #sidenav a:hover {{ color:{TEXT}; border-color:{GREEN}; }}
  #totop {{ position:fixed; right:22px; bottom:22px; z-index:20;
            background:{CARD}; color:{TEXT}; border:1px solid #2c3440;
            border-radius:50%; width:44px; height:44px; font-size:1.2rem;
            cursor:pointer; opacity:0; pointer-events:none; transition:.2s; }}
  #totop.show {{ opacity:.92; pointer-events:auto; }}
  #totop:hover {{ border-color:{GREEN}; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🎬 {title}</h1>
    <p>{("@" + username + " · ") if username else ""}{len(films)} filmes · {n_enriched} enriquecidos via TMDB{(" · " + period) if period else ""}</p>
  {lead}
  </header>
  {nav_html}
  {panes_html}
  <footer>Gerado com <a href="https://github.com/arthurpmotta02/letterboxd-explorer">Letterboxd
    Explorer</a> · dados de filmes por <a href="https://www.themoviedb.org">TMDB</a>
    (este produto usa a API do TMDB mas não é endossado ou certificado pelo TMDB).</footer>
</div>
<nav id="sidenav" aria-label="atalhos"></nav>
<button id="totop" title="voltar ao topo"
  onclick="window.scrollTo({{top:0, behavior:'smooth'}})">↑</button>
<script>
window.addEventListener('scroll', function () {{
  document.getElementById('totop').classList.toggle('show', window.scrollY > 600);
}});
function buildSideNav(i) {{
  var nav = document.getElementById('sidenav');
  nav.innerHTML = '';
  var top = document.createElement('a');
  top.textContent = '↑ topo';
  top.href = '#';
  top.onclick = function (e) {{
    e.preventDefault();
    window.scrollTo({{top: 0, behavior: 'smooth'}});
  }};
  nav.appendChild(top);
  document.querySelectorAll('#tab-' + i + ' .group').forEach(function (g) {{
    var a = document.createElement('a');
    a.textContent = g.querySelector('span').textContent;
    a.href = '#' + g.id;
    nav.appendChild(a);
  }});
}}
function showTab(i) {{
  document.querySelectorAll('.tabpane').forEach(function (el, j) {{
    el.style.display = (i === j) ? '' : 'none';
  }});
  document.querySelectorAll('.tabs button').forEach(function (b, j) {{
    b.classList.toggle('active', i === j);
  }});
  buildSideNav(i);
  window.dispatchEvent(new Event('resize'));
}}
showTab(0);
</script>
</body>
</html>"""
    out.write_text(html, encoding="utf-8")
    return out
