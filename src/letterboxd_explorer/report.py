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
) -> Path:
    """Monta o relatório. Sem `year`, gera abas: Tudo + um ano por aba."""
    diary, date_note = _activity(diary, frames)

    tabs: list[tuple[str, list, list, list]] = []
    label = f"Retrospectiva {year}" if year else "Tudo"
    cards, facts, sections = _build_content(films, diary, frames,
                                            main=year is None, note=date_note)
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
    return out


def _build_content(
    films: pd.DataFrame,
    diary: pd.DataFrame | None,
    frames: dict,
    main: bool = True,
    note: str = "",
):
    sections: list[tuple[str, str, str, str]] = []

    def add(grp, title, sub, fig, height=420):
        sections.append((grp, title, sub, _fig_html(fig, height)))

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
                x=m.index, y=m.values, mode="lines",
                line=dict(color=GREEN, width=2.5, shape="spline", smoothing=.6),
                fill="tozeroy", fillcolor="rgba(0,224,84,.12)",
                hovertemplate="%{x|%b %Y}: %{y} filmes<extra></extra>"))
            fig.update_layout(yaxis_title="filmes por mês")
            add(G, "Volume mensal", f"Filmes por mês{note}", fig, 370)

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
    if len(pf) >= 5:
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
        add(G, "Favoritos mais pessoais",
            f"Você deu 4.5★ ou 5★ a {n_top} filmes; ranqueá-los entre si não "
            "diz nada. O informativo é a distância da média: estes são os "
            "favoritos que mais dependem do <i>seu</i> gosto.", fig, 380)

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
            fig.update_xaxes(type="log", title="votos no TMDB (escala log)")
            fig.update_yaxes(title="sua nota", dtick=0.5)
            add(G, "Popularidade × avaliação",
                "Cada ponto é um filme; à esquerda, os menos conhecidos", fig, 460)

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
                "Boxplot nos 8 gêneros mais vistos (traço = mediana, "
                "losango = média)", fig, 460)

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
    ds = stats.director_stats(films, min_count=3)
    if len(ds) >= 5:
        fig = go.Figure(go.Scatter(
            x=ds["n"], y=ds["nota"], mode="markers+text",
            text=list(ds.index), textposition="top center",
            textfont=dict(size=11, color=MUTED),
            marker=dict(size=ds["n"] / ds["n"].max() * 26 + 10,
                        color=ds["nota"], cmin=max(0, ds["nota"].min() - .3),
                        colorscale=[[0, GRAD[ORANGE]], [1, GREEN]],
                        showscale=False, line=dict(width=1.5, color=CARD)),
            hovertemplate="%{text}: %{x} filmes, %{y:.2f}★<extra></extra>"))
        fig.update_layout(xaxis_title="filmes vistos", yaxis_title="sua nota média")
        add(G, "Diretores: volume × avaliação",
            "Mín. 3 filmes avaliados por diretor(a)", fig, 500)
    else:
        d = stats.explode_count(films, "directors", 15)
        if len(d):
            add(G, "Diretores mais vistos", "", _hbar(d, GREEN), 480)

    a = stats.explode_count(films, "cast", 15)
    if len(a):
        add(G, "Atores e atrizes mais frequentes",
            "Top 8 créditos de cada filme", _hbar(a, BLUE), 480)

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
                f"Escala logarítmica — top: {top5}", fig, 520)

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


def _render_tab(cards, facts, sections) -> str:
    cards_html = "".join(
        f'<div class="card"><div class="big">{v}</div><div class="lbl">{lbl}</div></div>'
        for v, lbl in cards
    )
    facts_html = ""
    if facts:
        items = "".join(f"<li>{f}</li>" for f in facts)
        facts_html = f'<section><h2>Insights</h2><ul class="facts">{items}</ul></section>'
    secs = ""
    current_group = None
    for grp, title, sub, body in sections:
        if grp != current_group:
            secs += f'<div class="group"><span>{grp}</span></div>\n'
            current_group = grp
        sub_html = f'<p class="sub">{sub}</p>' if sub else ""
        secs += (f'<section><h2>{title}</h2>{sub_html}'
                 f'<div class="plot">{body}</div></section>\n')
    return f'<div class="cards">{cards_html}</div>\n{facts_html}\n{secs}'


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
                       f"{_render_tab(cards, facts, sections)}</div>\n")

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
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🎬 {title}</h1>
    <p>{("@" + username + " · ") if username else ""}{len(films)} filmes · {n_enriched} enriquecidos via TMDB{(" · " + period) if period else ""}</p>
  </header>
  {nav_html}
  {panes_html}
  <footer>Gerado com <a href="https://github.com/arthurpmotta02/letterboxd-explorer">Letterboxd
    Explorer</a> · dados de filmes por <a href="https://www.themoviedb.org">TMDB</a>
    (este produto usa a API do TMDB mas não é endossado ou certificado pelo TMDB).</footer>
</div>
<script>
function showTab(i) {{
  document.querySelectorAll('.tabpane').forEach(function (el, j) {{
    el.style.display = (i === j) ? '' : 'none';
  }});
  document.querySelectorAll('.tabs button').forEach(function (b, j) {{
    b.classList.toggle('active', i === j);
  }});
  window.dispatchEvent(new Event('resize'));
}}
showTab(0);
</script>
</body>
</html>"""
    out.write_text(html, encoding="utf-8")
    return out
