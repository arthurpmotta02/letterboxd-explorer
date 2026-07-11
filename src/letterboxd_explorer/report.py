"""Geração do relatório HTML interativo (arquivo único, Plotly via CDN)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from letterboxd_explorer import insights, models, stats
from letterboxd_explorer.ingest import parse_dates

# ------------------------------------------------------------------- tema

BG, CARD, TEXT, MUTED = "#14181c", "#1b2228", "#dfe7ef", "#99aabb"
GRID = "#242c34"

# ------- sistema de cor com significado, na estética Letterboxd -------
# O trio da marca: verde = volume/contagem, laranja = suas notas,
# azul = tempo/fila/neutro.
ORANGE, GREEN, BLUE = "#ff8000", "#00e054", "#40bcf4"
# divergência ("acima/abaixo do esperado"): o próprio azul ↔ laranja da
# marca, que por sorte é seguro para daltônicos. Usada SÓ em você×TMDB
# e desvios vs. baseline.
DIV_POS, DIV_NEG, DIV_MID = ORANGE, BLUE, "#39424d"
DIV_SCALE = [[0, DIV_NEG], [0.5, DIV_MID], [1, DIV_POS]]
# escala sequencial única para intensidade (calendário, heatmaps)
SEQ_SCALE = [[0, "#20262c"], [0.01, "#0e4429"], [0.4, "#26a641"],
             [1, "#39d353"]]
# categórica derivada da família da marca (verde/laranja/azul + tons):
# gêneros, clusters, idiomas — distintas entre si, sem sair da estética.
CAT = [GREEN, ORANGE, BLUE, "#f4d35e", "#00a875", "#ffb473",
       "#1b6e9e", "#99aabb"]
# gradiente de nota (baixa -> alta): laranja -> amarelo -> verde, o mesmo
# sentido do slider de estrelas do Letterboxd
RATING_SCALE = [[0, "#ff8000"], [0.5, "#f4d35e"], [1, "#00e054"]]
PALETTE = CAT
PURPLE, PINK, YELLOW, RED = "#1b6e9e", "#ffb473", "#f4d35e", DIV_NEG
GRAD = {
    GREEN: "#0e4429", ORANGE: "#5c2e00", BLUE: "#0f3a52",
    PURPLE: "#0d2f42", PINK: "#4d2a12", YELLOW: "#4d3f00",
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
    # ISO 3166-1 completo (alpha-2 -> alpha-3), todos os 249 códigos
    "AD": "AND", "AE": "ARE", "AF": "AFG", "AG": "ATG", "AI": "AIA", "AL": "ALB",
    "AM": "ARM", "AO": "AGO", "AQ": "ATA", "AR": "ARG", "AS": "ASM", "AT": "AUT",
    "AU": "AUS", "AW": "ABW", "AX": "ALA", "AZ": "AZE", "BA": "BIH", "BB": "BRB",
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BH": "BHR", "BI": "BDI",
    "BJ": "BEN", "BL": "BLM", "BM": "BMU", "BN": "BRN", "BO": "BOL", "BQ": "BES",
    "BR": "BRA", "BS": "BHS", "BT": "BTN", "BV": "BVT", "BW": "BWA", "BY": "BLR",
    "BZ": "BLZ", "CA": "CAN", "CC": "CCK", "CD": "COD", "CF": "CAF", "CG": "COG",
    "CH": "CHE", "CI": "CIV", "CK": "COK", "CL": "CHL", "CM": "CMR", "CN": "CHN",
    "CO": "COL", "CR": "CRI", "CU": "CUB", "CV": "CPV", "CW": "CUW", "CX": "CXR",
    "CY": "CYP", "CZ": "CZE", "DE": "DEU", "DJ": "DJI", "DK": "DNK", "DM": "DMA",
    "DO": "DOM", "DZ": "DZA", "EC": "ECU", "EE": "EST", "EG": "EGY", "EH": "ESH",
    "ER": "ERI", "ES": "ESP", "ET": "ETH", "FI": "FIN", "FJ": "FJI", "FK": "FLK",
    "FM": "FSM", "FO": "FRO", "FR": "FRA", "GA": "GAB", "GB": "GBR", "GD": "GRD",
    "GE": "GEO", "GF": "GUF", "GG": "GGY", "GH": "GHA", "GI": "GIB", "GL": "GRL",
    "GM": "GMB", "GN": "GIN", "GP": "GLP", "GQ": "GNQ", "GR": "GRC", "GS": "SGS",
    "GT": "GTM", "GU": "GUM", "GW": "GNB", "GY": "GUY", "HK": "HKG", "HM": "HMD",
    "HN": "HND", "HR": "HRV", "HT": "HTI", "HU": "HUN", "ID": "IDN", "IE": "IRL",
    "IL": "ISR", "IM": "IMN", "IN": "IND", "IO": "IOT", "IQ": "IRQ", "IR": "IRN",
    "IS": "ISL", "IT": "ITA", "JE": "JEY", "JM": "JAM", "JO": "JOR", "JP": "JPN",
    "KE": "KEN", "KG": "KGZ", "KH": "KHM", "KI": "KIR", "KM": "COM", "KN": "KNA",
    "KP": "PRK", "KR": "KOR", "KW": "KWT", "KY": "CYM", "KZ": "KAZ", "LA": "LAO",
    "LB": "LBN", "LC": "LCA", "LI": "LIE", "LK": "LKA", "LR": "LBR", "LS": "LSO",
    "LT": "LTU", "LU": "LUX", "LV": "LVA", "LY": "LBY", "MA": "MAR", "MC": "MCO",
    "MD": "MDA", "ME": "MNE", "MF": "MAF", "MG": "MDG", "MH": "MHL", "MK": "MKD",
    "ML": "MLI", "MM": "MMR", "MN": "MNG", "MO": "MAC", "MP": "MNP", "MQ": "MTQ",
    "MR": "MRT", "MS": "MSR", "MT": "MLT", "MU": "MUS", "MV": "MDV", "MW": "MWI",
    "MX": "MEX", "MY": "MYS", "MZ": "MOZ", "NA": "NAM", "NC": "NCL", "NE": "NER",
    "NF": "NFK", "NG": "NGA", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NP": "NPL",
    "NR": "NRU", "NU": "NIU", "NZ": "NZL", "OM": "OMN", "PA": "PAN", "PE": "PER",
    "PF": "PYF", "PG": "PNG", "PH": "PHL", "PK": "PAK", "PL": "POL", "PM": "SPM",
    "PN": "PCN", "PR": "PRI", "PS": "PSE", "PT": "PRT", "PW": "PLW", "PY": "PRY",
    "QA": "QAT", "RE": "REU", "RO": "ROU", "RS": "SRB", "RU": "RUS", "RW": "RWA",
    "SA": "SAU", "SB": "SLB", "SC": "SYC", "SD": "SDN", "SE": "SWE", "SG": "SGP",
    "SH": "SHN", "SI": "SVN", "SJ": "SJM", "SK": "SVK", "SL": "SLE", "SM": "SMR",
    "SN": "SEN", "SO": "SOM", "SR": "SUR", "SS": "SSD", "ST": "STP", "SV": "SLV",
    "SX": "SXM", "SY": "SYR", "SZ": "SWZ", "TC": "TCA", "TD": "TCD", "TF": "ATF",
    "TG": "TGO", "TH": "THA", "TJ": "TJK", "TK": "TKL", "TL": "TLS", "TM": "TKM",
    "TN": "TUN", "TO": "TON", "TR": "TUR", "TT": "TTO", "TV": "TUV", "TW": "TWN",
    "TZ": "TZA", "UA": "UKR", "UG": "UGA", "UM": "UMI", "US": "USA", "UY": "URY",
    "UZ": "UZB", "VA": "VAT", "VC": "VCT", "VE": "VEN", "VG": "VGB", "VI": "VIR",
    "VN": "VNM", "VU": "VUT", "WF": "WLF", "WS": "WSM", "YE": "YEM", "YT": "MYT",
    "ZA": "ZAF", "ZM": "ZMB", "ZW": "ZWE",
    # códigos históricos/extras usados pelo TMDB (fora da ISO atual)
    "SU": "RUS", "XC": "CZE", "CS": "SRB", "YU": "SRB", "DD": "DEU", "XG": "DEU",
    "XK": "XKX", "AN": "NLD", "ZR": "COD", "BU": "MMR", "TP": "TLS",
}


def _fig_html(fig, height=420):
    fig.update_layout(height=height)
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=False,
        config={"displaylogo": False, "responsive": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )


def _hbar(series, color, unit="filmes"):
    """Ranking horizontal em estilo lollipop (haste fina + ponto)."""
    s = series[::-1]
    xs, ys = [], []
    for name, v in s.items():
        xs += [0, v, None]
        ys += [name, name, None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines",
        line=dict(color="rgba(153,170,187,.30)", width=2),
        hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=list(s.values), y=list(s.index), mode="markers",
        marker=dict(size=11, color=list(s.values),
                    colorscale=[[0, GRAD.get(color, color)], [1, color]],
                    line=dict(width=1.5, color=CARD)),
        hovertemplate="%{y}: %{x} " + unit + "<extra></extra>",
        showlegend=False))
    fig.update_layout(xaxis_title=unit)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    vals = pd.Series(s.values)
    if len(vals) and vals.max() <= 12 and (vals % 1 == 0).all():
        fig.update_xaxes(dtick=1, tickformat="d")
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
    "Evolução dos gêneros": "evolucao_generos",
    "Sazonalidade dos gêneros, testada": "sazonalidade_generos",
    "Keywords (microgêneros)": "keywords_microgeneros",
    "Diretores: volume × avaliação × consistência": "diretores_volume_avaliacao",
    "Rede de colaborações diretor–ator": "rede_colaboracoes",
    "Países de produção": "mapa_paises",
    # v3: modelo do gosto e novas séries
    "O que de fato eleva a sua nota": "modelo_do_gosto",
    "Anatomia do seu 5★": "anatomia_5_estrelas",
    "Generosidade real ao longo do tempo": "generosidade_real",
    "Arquétipos do seu gosto": "arquetipos_gosto",
    "Nota por gênero, com incerteza": "nota_genero_incerteza",
    "Quem te fisgou: retenção de diretores": "retencao_diretores",
    "Exploração × explotação": "exploracao_explotacao",
    "Mainstream ↔ cult ao longo do tempo": "mainstream_cult",
    "O que você escreve × a nota que você dá": "sentimento_resenhas",
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
            line=dict(width=1.5 + w * 1.6, color="rgba(0,224,84,.45)"),
            hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=[0] * len(directors), y=[yd[d] for d in directors.index],
        mode="markers+text", text=list(directors.index),
        textposition="middle left", textfont=dict(size=11.5, color=TEXT),
        marker=dict(size=directors.values / directors.max() * 16 + 12,
                    color=ORANGE, line=dict(width=1.5, color=CARD)),
        customdata=directors.values,
        hovertemplate="%{text}: %{customdata} colaborações<extra></extra>",
        showlegend=False))
    fig.add_trace(go.Scatter(
        x=[1] * len(actors), y=[ya[a] for a in actors.index],
        mode="markers+text", text=list(actors.index),
        textposition="middle right", textfont=dict(size=11.5, color=TEXT),
        marker=dict(size=actors.values / actors.max() * 16 + 12,
                    color=BLUE, line=dict(width=1.5, color=CARD)),
        customdata=actors.values,
        hovertemplate="%{text}: %{customdata} colaborações<extra></extra>",
        showlegend=False))
    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.75, 1.75]),
        yaxis=dict(visible=False, range=[-0.08, 1.08]),
        margin=dict(l=10, r=10, t=20, b=20))
    return fig



def _top_person(films: pd.DataFrame, col: str, pcol: str) -> dict | None:
    """Pessoa mais recorrente em `col`, com foto (pcol) e sua nota média."""
    if col not in films:
        return None
    from collections import Counter, defaultdict

    cnt: Counter = Counter()
    prof: dict = {}
    notas = defaultdict(list)
    has_prof = pcol in films
    for _, row in films.iterrows():
        names = row.get(col)
        if not isinstance(names, list):
            continue
        profs = row.get(pcol) if has_prof else None
        for i, nm in enumerate(names):
            cnt[nm] += 1
            if (isinstance(profs, list) and i < len(profs)
                    and profs[i] and nm not in prof):
                prof[nm] = profs[i]
            r = row.get("Rating")
            if pd.notna(r):
                notas[nm].append(float(r))
    if not cnt:
        return None
    nm, n = cnt.most_common(1)[0]
    if n < 2:
        return None
    rs = notas.get(nm) or []
    return {"name": nm, "n": int(n),
            "rating": sum(rs) / len(rs) if rs else None,
            "profile": prof.get(nm)}


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
    """Exporta as figuras como PNG (requer kaleido). Falha por figura,
    nunca em bloco: uma figura problemática não impede as demais."""
    folder.mkdir(parents=True, exist_ok=True)
    ok, falhas = 0, []
    for name, (fig, height) in registry.items():
        try:
            fig.write_image(str(folder / f"{name}.png"),
                            width=1000, height=height, scale=2)
            ok += 1
        except Exception as e:
            falhas.append((name, str(e)))
    print(f"✔ {ok}/{len(registry)} figuras salvas em {folder.resolve()}")
    if ok == 0:
        print("! Nenhuma figura exportada. Instale: pip install kaleido "
              "(requer Google Chrome) ou, sem Chrome: "
              "pip install kaleido==0.2.1")
    for name, err in falhas[:6]:
        print(f"  ! falhou {name}: {err[:90]}")


def _build_content(
    films: pd.DataFrame,
    diary: pd.DataFrame | None,
    frames: dict,
    main: bool = True,
    note: str = "",
    registry: dict | None = None,
):
    sections: list[tuple[str, str, str, str, bool]] = []

    def add(grp, title, sub, fig, height=420, secondary=False):
        if registry is not None and title in SAVE_FIGS:
            registry[SAVE_FIGS[title]] = (fig, height)
        sections.append((grp, title, sub, _fig_html(fig, height), secondary))

    def add_html(grp, title, sub, html, secondary=False):
        sections.append((grp, title, sub, html, secondary))

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
                       radialaxis=dict(range=[0, 1.02], showticklabels=False,
                                       gridcolor=GRID, griddash="dot",
                                       tickvals=[0.25, 0.5, 0.75, 1.0]),
                       angularaxis=dict(gridcolor=GRID, linecolor=GRID,
                                        tickfont=dict(size=12.5, color=TEXT))),
            showlegend=False, margin=dict(l=80, r=80, t=40, b=40))
        add(G, "Perfil por gênero",
            "Volume relativo dos seus 8 gêneros mais vistos; cada anel "
            "pontilhado = 25% do gênero mais visto", fig, 440)

    # ================================================== modelo do gosto
    G = "Modelo do gosto"
    model = models.rating_model(films, diary)
    if model is not None and main:
        eff = model["effects"]
        fam_color = {f: CAT[i % len(CAT)]
                     for i, f in enumerate(dict.fromkeys(eff["family"]))}
        show = eff[eff["family"] != "ano em que viu"].copy()
        show["abs"] = show["coef"].abs()
        show = pd.concat([
            show[show["family"] == fam].nlargest(6, "abs")
            for fam in dict.fromkeys(show["family"])
        ]).sort_values("coef")
        fig = go.Figure()
        for fam in dict.fromkeys(show["family"]):
            e = show[show["family"] == fam]
            fig.add_trace(go.Scatter(
                x=e["coef"], y=e.index, mode="markers", name=fam,
                error_x=dict(type="data", array=1.96 * e["se"],
                             color="rgba(153,170,187,.5)", thickness=1.5,
                             width=4),
                marker=dict(size=10, color=fam_color[fam],
                            line=dict(width=1.5, color=CARD)),
                hovertemplate="%{y}: %{x:+.2f}★ (IC95 ±"
                              "%{error_x.array:.2f})<extra></extra>"))
        fig.add_vline(x=0, line_color=MUTED, line_dash="dot")
        fig.update_layout(xaxis_title="efeito parcial na sua nota (★)",
                          legend=dict(orientation="h", y=1.08),
                          margin=dict(l=10))
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11.5))
        cv_txt = (f", validação cruzada {model['cv_r2']:.0%}, erro médio "
                  f"±{model['cv_mae']:.1f}★"
                  if model.get("cv_r2") == model.get("cv_r2") else "")
        add(G, "O que de fato eleva a sua nota",
            f"Efeitos parciais de um modelo ridge sobre {model['n']} filmes "
            f"avaliados (R² de treino {model['r2']:.0%}{cv_txt}). Cada efeito é "
            "controlado pelos demais: é o \"bônus\" da característica, não a "
            "média marginal. A barra é o intervalo de variância do estimador "
            "encolhido (não corrigido pelo viés do ridge).",
            fig, max(420, 24 * len(show) + 140))

        imp = model["importance"]
        imp = imp[imp > 0.001]
        if len(imp) >= 3:
            fig = go.Figure(go.Bar(
                x=imp.values[::-1], y=list(imp.index)[::-1], orientation="h",
                marker=dict(color=[fam_color.get(f, BLUE)
                                   for f in imp.index[::-1]], line_width=0),
                hovertemplate="%{y}: %{x:.1%} do R²<extra></extra>"))
            fig.update_layout(
                xaxis_title="queda de R² fora da amostra ao remover a família",
                xaxis_tickformat=".0%", bargap=0.4)
            fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
            add(G, "Anatomia do seu 5★",
                "O que mais move a sua avaliação: quanto o modelo piora, "
                "em validação cruzada, quando cada família de características "
                "é removida. Medir fora da amostra evita premiar famílias com "
                "muitos rótulos (diretor, gênero) só por decorarem o treino.",
                fig, 340)

        bench = models.nonlinear_benchmark(films, diary, model=model)
        if bench is not None:
            fig = go.Figure(go.Bar(
                x=[bench["ridge_cv_r2"], bench["gbm_cv_r2"]],
                y=["linear (ridge)", "não-linear (boosting)"],
                orientation="h",
                marker=dict(color=[BLUE, GREEN], line_width=0),
                hovertemplate="%{y}: CV-R² %{x:.1%}<extra></extra>"))
            fig.update_layout(xaxis_tickformat=".0%",
                              xaxis_title="R² em validação cruzada", bargap=0.5)
            fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
            g_txt = ("há sinal em combinações de características (ex.: você "
                     "gosta de drama longo, mas não de comédia longa)"
                     if bench["gain"] > 0.03 else
                     "pouco: seu gosto é bem descrito por efeitos aditivos")
            add(G, "Seu gosto é linear?",
                f"Quanto um modelo que capta interações supera o linear. "
                f"Ganho de {bench['gain']:+.0%} — {g_txt}.",
                fig, 240)

        rby = model["resid_by_year"]
        if rby is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(rby.index) + list(rby.index)[::-1],
                y=list(rby["mean"] + rby["ci"])
                + list((rby["mean"] - rby["ci"])[::-1]),
                fill="toself", fillcolor="rgba(255,128,0,.12)",
                line=dict(width=0), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(
                x=rby.index, y=rby["mean"], mode="lines+markers",
                line=dict(color=ORANGE, width=2.5),
                marker=dict(size=9, color=ORANGE,
                            line=dict(width=2, color=CARD)),
                customdata=rby["n"],
                hovertemplate="%{x}: %{y:+.2f}★ (%{customdata} filmes)"
                              "<extra></extra>", showlegend=False))
            fig.add_hline(y=0, line_color=MUTED, line_dash="dot")
            fig.update_layout(xaxis=dict(dtick=1, title="ano em que assistiu"),
                              yaxis_title="generosidade além do esperado (★)")
            add(G, "Generosidade real ao longo do tempo",
                "Resíduo do modelo: sua nota menos a nota prevista pelas "
                "características do filme. Acima de zero = você foi mais "
                "generoso do que o seu padrão para aquele tipo de filme, "
                "descontado o efeito de \"escolher melhor\".", fig, 380)

        cal_fit = models.rating_calibration(films, diary, model=model)
        if cal_fit is not None and len(cal_fit) >= 3:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[0.5, 5], y=[0.5, 5], mode="lines",
                line=dict(color=MUTED, dash="dot"),
                hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(
                x=cal_fit["pred"], y=cal_fit["real"], mode="lines+markers",
                error_y=dict(type="data", symmetric=False,
                             array=cal_fit["hi"] - cal_fit["real"],
                             arrayminus=cal_fit["real"] - cal_fit["lo"],
                             color="rgba(153,170,187,.5)", thickness=1.5,
                             width=4),
                line=dict(color=GREEN, width=2.5),
                marker=dict(size=9, color=GREEN,
                            line=dict(width=2, color=CARD)),
                customdata=cal_fit["n"],
                hovertemplate="prevista %{x:.1f}★ → real %{y:.2f}★ "
                              "(%{customdata} filmes)<extra></extra>",
                showlegend=False))
            fig.update_layout(
                xaxis_title="nota prevista (fora da amostra)",
                yaxis_title="nota real média")
            add(G, "O modelo está bem calibrado?",
                "Cada ponto agrupa filmes com nota prevista parecida, usando "
                "previsões de validação cruzada (sem espiar a resposta). Sobre "
                "a linha pontilhada = a previsão bate com a realidade.",
                fig, 380)

    if main:
        wl_enr = frames.get("watchlist_enriched")
        ranked = models.rank_watchlist(films, wl_enr, diary, model=model,
                                       diversify=0.3) \
            if model is not None and wl_enr is not None else None
        if ranked is not None and len(ranked) >= 5:
            sub = (f"As maiores notas que o modelo prevê que <i>você</i> "
                   f"daria, entre {len(wl_enr)} filmes da watchlist. Cada "
                   "filme traz a faixa provável (intervalo de previsão de 95%); "
                   "filmes com poucas pistas conhecidas saem com faixa mais "
                   "larga, e a seleção prioriza variedade para não repetir o "
                   "mesmo tipo de filme. Como o modelo só aprende com o que "
                   "você já avaliou, ele tende ao que você conhece.")
            if "poster" in ranked and ranked["poster"].notna().sum() >= 5:
                items = [dict(name=r.Name, year=r.Year, poster=r.poster,
                              badge=f"{r.pred:.1f}★",
                              lines=[f"prevista {r.pred:.1f}★",
                                     f"faixa {r.pred_lo:.1f}–{r.pred_hi:.1f}★"])
                         for r in ranked.head(12).itertuples()]
                add_html(G, "Watchlist rankeada pelo seu gosto", sub,
                         _poster_grid(items))
            else:
                s = pd.Series(ranked["pred"].round(2).values,
                              index=[f"{n} ({y})" for n, y in
                                     zip(ranked["Name"], ranked["Year"])])
                add(G, "Watchlist rankeada pelo seu gosto", sub,
                    _hbar(s[::-1][-15:], ORANGE, unit="★ prevista"), 480)

    if main:
        cl = models.taste_clusters(films)
        if cl is not None:
            df, labels = cl["df"], cl["labels"]
            summ = cl["summary"]
            fig = go.Figure()
            for j, lab in labels.items():
                d = df[df["cluster"] == j]
                extra = ""
                if j in summ.index and pd.notna(summ.loc[j, "rating"]):
                    extra = f" · {summ.loc[j, 'rating']:.2f}★"
                fig.add_trace(go.Scatter(
                    x=d["x"], y=d["y"], mode="markers",
                    name=f"{lab} ({len(d)}{extra})",
                    text=d["Name"],
                    marker=dict(size=7, color=CAT[j % len(CAT)], opacity=.8,
                                line_width=0),
                    hovertemplate="%{text}<extra>" + lab + "</extra>"))
            fig.update_layout(
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                legend=dict(orientation="h", y=-0.06,
                            font=dict(size=11.5)))
            add(G, "Arquétipos do seu gosto",
                "Filmes agrupados por gênero, década, idioma e keywords "
                "(k-means; projeção 2D). O rótulo de cada grupo traz os "
                "traços que mais o distinguem, com tamanho e nota média.",
                fig, 520)

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
            cp = stats.activity_changepoint(diary)
            sub_cp = ""
            if cp:
                fig.add_vline(x=cp["date"], line_dash="dash",
                              line_color=MUTED)
                fig.add_annotation(x=cp["date"], y=1, yref="paper",
                                   text="mudança de ritmo", showarrow=False,
                                   font=dict(color=MUTED, size=11),
                                   xanchor="left")
                direc = "acelerou" if cp["after"] > cp["before"] else "desacelerou"
                sub_cp = (f" · em {cp['date']:%b/%Y} seu ritmo {direc}: de "
                          f"{cp['before']:.1f} para {cp['after']:.1f} "
                          f"filmes/mês (p = {cp['p']:.3f})")
            fig.update_layout(yaxis_title="filmes por mês",
                              legend=dict(orientation="h", y=1.12))
            add(G, "Volume mensal",
                f"Filmes por mês; a linha clara suaviza picos de "
                f"maratona{note}{sub_cp}", fig, 370)

        cal = stats.weekly_calendar(diary)
        if len(cal) and cal.values.sum() >= 20:
            fig = go.Figure(go.Heatmap(
                z=cal.values, x=list(cal.columns), y=[str(y) for y in cal.index],
                colorscale=[[0, "#20262c"], [.01, "#0e4429"],
                            [.4, "#26a641"], [1, "#39d353"]],
                zmin=0, showscale=False, xgap=2.5, ygap=5,
                hovertemplate="semana %{x} de %{y}: %{z} filmes<extra></extra>"))
            # type="category": sem isso o Plotly lê "2019" como número e
            # funde visualmente os anos quando algum fica sem atividade
            fig.update_layout(xaxis_title="semana do ano",
                              yaxis=dict(autorange="reversed",
                                         type="category"))
            add(G, "Calendário de atividade", f"Filmes por semana{note}",
                fig, max(230, 140 + 44 * len(cal)))

        if len(diary) >= 30:
            hm = pd.crosstab(diary["Watched Date"].dt.dayofweek,
                             diary["Watched Date"].dt.month)
            hm = hm.reindex(index=range(7), columns=range(1, 13), fill_value=0)
            fig = go.Figure(go.Heatmap(
                z=hm.values, x=PT_MONTHS, y=PT_WEEKDAYS,
                colorscale=SEQ_SCALE,
                showscale=False, xgap=3, ygap=3,
                hovertemplate="%{y}, %{x}: %{z} filmes<extra></extra>"))
            add(G, "Padrão semanal e mensal", f"Dia da semana × mês{note}",
                fig, 340, secondary=True)

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

    her = stats.heresies(films)
    if len(her) >= 10:
        cal = stats.calibration(films)
        cal_sub = ("Acima da linha pontilhada = você avalia melhor que a "
                   "média.")
        if cal:
            rho = cal["spearman"]
            grau = ("concorda muito" if rho >= 0.6 else
                    "concorda em parte" if rho >= 0.35 else "discorda")
            cal_sub += (f" Separando régua de gosto: seu <i>ranking</i> "
                        f"{grau} com o do TMDB (Spearman ρ = {rho:.2f}) e "
                        f"sua régua é {abs(cal['offset']):.2f}★ "
                        f"{'acima' if cal['offset'] > 0 else 'abaixo'} da "
                        f"deles em média ({cal['n']} filmes, 30+ votos).")
        fig = px.scatter(
            her, x="tmdb_5", y="Rating", hover_name="Name",
            color="diff",
            color_continuous_scale=[DIV_NEG, DIV_MID, DIV_POS],
            opacity=.75, marginal_x="histogram", marginal_y="histogram",
            labels={"tmdb_5": "nota TMDB (0 a 5)", "Rating": "sua nota"})
        fig.add_shape(type="line", x0=0, y0=0, x1=5, y1=5,
                      line=dict(color=MUTED, dash="dot"))
        fig.update_layout(coloraxis_showscale=False)
        add(G, "Sua nota × nota TMDB", cal_sub, fig, 520)

        her10 = pd.concat([her.nlargest(6, "diff"),
                           her.nsmallest(6, "diff")]).sort_values("diff")
        fig = go.Figure(go.Bar(
            x=her10["diff"], y=her10["Name"], orientation="h",
            marker=dict(color=[DIV_POS if d > 0 else DIV_NEG
                               for d in her10["diff"]], line_width=0),
            hovertemplate="%{y}: %{x:+.1f}★ vs TMDB<extra></extra>"))
        fig.add_vline(x=0, line_color=MUTED)
        fig.update_layout(xaxis_title="sua nota − nota TMDB (★)", bargap=0.35)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        add(G, "Maiores divergências vs. TMDB",
            "Laranja: você avalia acima da média. Azul: abaixo.", fig, 440)

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
                     "Nota 4.5★+ sua em filmes pouco votados no TMDB "
                     "(30 a 1500 votos)", _poster_grid(items))

    if "tmdb_votes" in films:
        pop = films.dropna(subset=["tmdb_votes", "Rating"])
        pop = pop[pop["tmdb_votes"] > 0]
        if len(pop) >= 30:
            fig = go.Figure(go.Scatter(
                x=pop["tmdb_votes"], y=pop["Rating"], mode="markers",
                text=pop["Name"],
                marker=dict(size=7, color=pop["Rating"],
                            colorscale=RATING_SCALE,
                            showscale=False, opacity=.6, line_width=0),
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
                "de votos. Ela sobe ou desce com a popularidade?", fig, 460)

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
        sigma = rated["Rating"].std() if len(rated) > 1 else 0.5
        ci = 1.96 * sigma / np.sqrt(rd["count"] + 5)
        fig = go.Figure(go.Scatter(
            x=[str(d) for d in rd.index], y=rd["mean"], mode="lines+markers",
            line=dict(color=ORANGE, width=2.5),
            error_y=dict(type="data", array=ci,
                         color="rgba(153,170,187,.5)", thickness=1.5, width=4),
            marker=dict(size=(rd["count"] / rd["count"].max() * 22 + 8),
                        color=ORANGE, line=dict(width=2, color=CARD)),
            customdata=rd["count"],
            hovertemplate="anos %{x}: %{y:.2f}★ (%{customdata} filmes)<extra></extra>"))
        fig.update_layout(xaxis_title="década de lançamento",
                          yaxis_title="sua nota média")
        add(G, "Avaliação por década de lançamento",
            "Bolha maior = mais filmes avaliados; a barra é o IC de 95%: "
            "décadas com poucas notas têm médias pouco confiáveis", fig, 360)

    if has_diary:
        gap = stats.watch_gap(films, diary)
        if len(gap) >= 30:
            fig = _hist_kde(gap, BLUE, "anos entre lançamento e visualização")
            add(G, "Defasagem lançamento → visualização",
                f"Mediana de {gap.median():.0f} anos{note}", fig, 380,
                secondary=True)

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
                                colorscale=RATING_SCALE,
                                opacity=.8, line_width=0,
                                colorbar=dict(title="nota", outlinewidth=0,
                                              tickfont=dict(color=TEXT))),
                    name="com nota",
                    hovertemplate="%{text} (%{x}): %{marker.color}★<extra></extra>"))
            span = rv["watch_year"].max() - rv["watch_year"].min()
            fig.update_layout(xaxis_title="ano de lançamento",
                              yaxis_title="ano em que você assistiu",
                              showlegend=False)
            fig.update_yaxes(tickformat="d", dtick=1 if span <= 15 else None)
            fig.update_xaxes(tickformat="d")
            add(G, "Lançamento × visualização",
                "Faixas horizontais revelam fases: o ano em que você mergulhou "
                f"numa década ou cineasta específico{note}", fig, 480)

    g = stats.explode_count(films, "genres", 15)
    if len(g):
        add(G, "Filmes por gênero", "Fonte: TMDB", _hbar(g, GREEN), 480)

        sg = stats.shrunk_group(films, "genres", min_count=5, top=12)
        if len(sg) >= 4:
            sg = sg.sort_values("bayes")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sg["mean"], y=list(sg.index), mode="markers",
                name="média crua",
                marker=dict(size=7, color=MUTED, symbol="circle-open",
                            line=dict(width=1.5)),
                hovertemplate="%{y}: %{x:.2f}★ crua<extra></extra>"))
            fig.add_trace(go.Scatter(
                x=sg["bayes"], y=list(sg.index), mode="markers",
                name="média ajustada",
                error_x=dict(type="data", array=sg["ci"],
                             color="rgba(153,170,187,.5)", thickness=1.5,
                             width=4),
                marker=dict(size=11, color=ORANGE,
                            line=dict(width=1.5, color=CARD)),
                customdata=sg["n"],
                hovertemplate="%{y}: %{x:.2f}★ ± %{error_x.array:.2f} "
                              "(%{customdata} filmes)<extra></extra>"))
            prior = rated["Rating"].mean()
            fig.add_vline(x=prior, line_dash="dot", line_color=MUTED,
                          annotation_text=f"sua média {prior:.2f}",
                          annotation_font_color=MUTED)
            fig.update_layout(xaxis_title="sua nota média (★)",
                              legend=dict(orientation="h", y=1.08))
            fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
            add(G, "Nota por gênero, com incerteza",
                "Média com encolhimento bayesiano (amostras pequenas são "
                "puxadas para a sua média global) e IC de 95%. Onde as "
                "barras se sobrepõem, a diferença entre gêneros não é "
                "conclusiva.", fig, 440)

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

        seas = stats.seasonality_test(diary, films)
        if seas is not None:
            lift = seas["lift"]
            fig = go.Figure(go.Heatmap(
                z=lift.values, x=PT_MONTHS, y=list(lift.index),
                colorscale=DIV_SCALE, zmid=1,
                zmin=0, zmax=max(2.0, float(np.nanmax(lift.values))),
                xgap=3, ygap=3,
                colorbar=dict(title="obs./esp.", outlinewidth=0,
                              tickfont=dict(color=TEXT)),
                hovertemplate="%{y} em %{x}: %{z:.1f}× o esperado"
                              "<extra></extra>"))
            pico = lift.stack()
            (pg, pm), pv = pico.idxmax(), pico.max()
            sig = ("A associação gênero × mês é estatisticamente "
                   f"significativa (χ², p = {seas['p']:.3f})"
                   if seas["p"] < 0.05 else
                   "O teste χ² NÃO confirma sazonalidade além do acaso "
                   f"(p = {seas['p']:.2f})")
            add(G, "Sazonalidade dos gêneros, testada",
                f"Laranja = mais que o esperado para o mês; azul = menos. "
                f"Pico: {pg} em {PT_MONTHS[pm - 1]} ({pv:.1f}× o baseline). "
                f"{sig} · n = {seas['n']}.", fig, 400)
        else:
            gm = stats.genre_month(diary, films)
            if len(gm) >= 3 and len(diary) >= 60:
                fig = go.Figure(go.Heatmap(
                    z=gm.values, x=PT_MONTHS, y=list(gm.index),
                    colorscale=SEQ_SCALE, showscale=False,
                    xgap=3, ygap=3,
                    hovertemplate="%{y} em %{x}: %{z:.0%}<extra></extra>"))
                add(G, "Sazonalidade dos gêneros",
                    "Distribuição de cada gênero ao longo do ano "
                    "(cada linha soma 100%) · amostra pequena para teste χ²",
                    fig, 380)

    k = stats.explode_count(films, "keywords", 25)
    if len(k):
        add(G, "Keywords (microgêneros)", "Fonte: TMDB", _hbar(k, GREEN), 620,
            secondary=True)

    if "runtime" in films:
        rt = films["runtime"].dropna()
        rt = rt[rt > 0]
        if len(rt) >= 15:
            fig = _hist_kde(rt, ORANGE, "minutos")
            longest = films.loc[films["runtime"].idxmax()]
            add(G, "Distribuição de duração",
                f"Mediana {rt.median():.0f} min · mais longo: "
                f"<b>{longest['Name']}</b> ({int(longest['runtime'])} min)",
                fig, 380, secondary=True)

    if ("tmdb_votes" in films and "poster" in films
            and films["tmdb_votes"].notna().any()):
        v = films.dropna(subset=["tmdb_votes"])
        zero = int((v["tmdb_votes"] == 0).sum())
        rare = v[v["tmdb_votes"] > 0].nsmallest(12, "tmdb_votes")
        rare = rare[rare["tmdb_votes"] < 200]
        if len(rare) >= 4 and rare["poster"].notna().sum() >= 4:
            sub = "Os registros com menos votos no TMDB em todo o seu histórico"
            if zero:
                sub += (f" · além destes, <b>{zero} filmes</b> seus não "
                        "receberam voto nenhum")
            items = [dict(name=r.Name, year=r.Year, poster=r.poster,
                          lines=[f"{int(r.tmdb_votes)} voto"
                                 + ("s" if r.tmdb_votes > 1 else "")])
                     for r in rare.itertuples()]
            add_html(G, "Raridades do acervo", sub, _poster_grid(items))

    if has_diary:
        rw = stats.most_rewatched(diary)
        if len(rw) >= 3:
            rw_sub = "Entradas repetidas no diário"
            rwe = stats.rewatch_effect(diary)
            if rwe:
                comp = ("acima das" if rwe["rewatch_mean"] > rwe["first_mean"]
                        else "abaixo das")
                conf = ("diferença significativa"
                        if rwe["p"] < 0.05 else "diferença não conclusiva")
                rw_sub += (f" · você dá {rwe['rewatch_mean']:.2f}★ em "
                           f"rewatches, {comp} primeiras sessões "
                           f"({rwe['first_mean']:.2f}★), {conf} "
                           f"(p = {rwe['p']:.2f})")
            add(G, "Rewatches mais frequentes", rw_sub,
                _hbar(rw, GREEN, unit="vezes"), 380, secondary=True)

    # ================================================== exploração e nicho
    if has_diary:
        G = "Exploração e nicho"
        exp = stats.exploration_by_year(diary, films)
        if len(exp) >= 3 and "entropy" in exp:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=exp.index, y=exp["entropy"], mode="lines+markers",
                name="variedade de gêneros (entropia)",
                line=dict(color=CAT[0], width=2.5),
                marker=dict(size=8, line=dict(width=2, color=CARD)),
                hovertemplate="%{x}: %{y:.0%}<extra>variedade</extra>"))
            for col, nm, ci in (("novel_directors", "diretores inéditos", 1),
                                ("novel_countries", "países inéditos", 2)):
                if col in exp and exp[col].notna().any():
                    fig.add_trace(go.Scatter(
                        x=exp.index, y=exp[col], mode="lines+markers",
                        name=nm, line=dict(color=CAT[ci], width=2,
                                           dash="dot"),
                        marker=dict(size=7, line=dict(width=2, color=CARD)),
                        hovertemplate="%{x}: %{y:.0%}<extra>" + nm +
                                      "</extra>"))
            fig.update_layout(yaxis_tickformat=".0%",
                              yaxis=dict(range=[0, 1.05],
                                         title="quanto do máximo possível"),
                              xaxis=dict(dtick=1),
                              legend=dict(orientation="h", y=1.12))
            tese = ""
            if len(exp) >= 2:
                d_ent = exp["entropy"].iloc[-1] - exp["entropy"].iloc[0]
                tese = ("Seu repertório está " +
                        ("se abrindo" if d_ent > 0.03 else
                         "se fechando" if d_ent < -0.03 else "estável") +
                        ". ")
            add(G, "Exploração × explotação",
                f"{tese}Entropia = variedade de gêneros no ano (100% = "
                "todos por igual); linhas pontilhadas = % de diretores/"
                "países vistos pela primeira vez.", fig, 420)

        obs = stats.obscurity_by_year(diary, films)
        if len(obs) >= 3:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(obs.index) + list(obs.index)[::-1],
                y=list(obs["mean"] + obs["ci"])
                + list((obs["mean"] - obs["ci"])[::-1]),
                fill="toself", fillcolor="rgba(0,224,84,.10)",
                line=dict(width=0), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(
                x=obs.index, y=obs["mean"], mode="lines+markers",
                line=dict(color=GREEN, width=2.5),
                marker=dict(size=8, color=GREEN,
                            line=dict(width=2, color=CARD)),
                customdata=obs["n"],
                hovertemplate="%{x}: %{y:.2f} (%{customdata} filmes)"
                              "<extra></extra>", showlegend=False))
            rumo = ("rumo ao nicho"
                    if obs["mean"].iloc[-1] > obs["mean"].iloc[0]
                    else "rumo ao mainstream")
            fig.update_layout(xaxis=dict(dtick=1),
                              yaxis_title="obscuridade média "
                                          "(−log₁₀ votos TMDB)")
            add(G, "Mainstream ↔ cult ao longo do tempo",
                f"Seu gosto está migrando {rumo}. Quanto mais alto, menos "
                "votados no TMDB são os filmes daquele ano; a faixa é o IC "
                "de 95%.", fig, 380)

        ret = stats.director_retention(films)
        hooked = stats.hooked_directors(films, diary, top=12)
        if ret is not None and hooked is not None and len(hooked) >= 3:
            n1 = int(ret.loc[1, "diretores"]) if 1 in ret.index else 0
            n3 = int(ret[ret.index >= 3]["diretores"].sum())
            h = hooked.sort_values("n")
            fig = go.Figure(go.Scatter(
                x=h["n"], y=list(h.index), mode="markers",
                marker=dict(size=12, color=h["nota"].fillna(h["nota"].mean()),
                            colorscale=RATING_SCALE,
                            colorbar=dict(title="nota", outlinewidth=0,
                                          tickfont=dict(color=TEXT)),
                            line=dict(width=1.5, color=CARD)),
                customdata=h["nota"],
                hovertemplate="%{y}: %{x} filmes · sua média "
                              "%{customdata:.2f}★<extra></extra>"))
            for name, row in h.iterrows():
                fig.add_shape(type="line", x0=0, x1=row["n"], y0=name,
                              y1=name, line=dict(width=2,
                              color="rgba(153,170,187,.30)"))
            fig.update_layout(xaxis_title="filmes vistos")
            fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
            add(G, "Quem te fisgou: retenção de diretores",
                f"Diretores com 3+ filmes no seu histórico, coloridos pela "
                f"sua nota média. Contexto: {n1} diretores ficaram no "
                f"experimento único; só {n3} te fisgaram de verdade.",
                fig, max(360, 30 * len(h) + 120))

        gr = stats.gender_representation(films, diary)
        if gr is not None and len(gr) >= 3:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=gr.index, y=gr["pct_fem"], mode="lines+markers",
                line=dict(color=CAT[4], width=2.5),
                marker=dict(size=9, color=CAT[4],
                            line=dict(width=2, color=CARD)),
                customdata=np.stack([gr["fem"], gr["known"]], axis=-1),
                hovertemplate="%{x}: %{y:.0%} (%{customdata[0]}/"
                              "%{customdata[1]})<extra></extra>",
                showlegend=False))
            fig.update_layout(yaxis_tickformat=".0%", xaxis=dict(dtick=1),
                              yaxis_title="% com direção feminina")
            cov = gr["coverage"].mean()
            add(G, "Direção feminina ao longo do tempo",
                f"Entre os filmes com dado de gênero no TMDB (cobertura "
                f"média {cov:.0%}; o campo é incompleto e binário-"
                "centrado; leia como aproximação).", fig, 380)

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
                    line=dict(color=GREEN, width=2.5),
                    fill="tozeroy", fillcolor="rgba(0,224,84,.10)",
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
                    _hbar(s[::-1], BLUE, unit="dias"), 400, secondary=True)

        reviews = frames.get("reviews")
        if reviews is not None and "Review" in reviews:
            sent = stats.review_sentiment(reviews, films)
            if sent is not None and len(sent) >= 12:
                from scipy import stats as sps

                rho_s, p_s = sps.spearmanr(sent["Rating"], sent["score"])
                rng = np.random.default_rng(3)
                jit = rng.uniform(-0.08, 0.08, len(sent))
                fig = go.Figure(go.Scatter(
                    x=sent["Rating"] + jit, y=sent["score"], mode="markers",
                    text=sent["Name"],
                    marker=dict(size=8, color=sent["score"], cmin=-1, cmax=1,
                                colorscale=DIV_SCALE, opacity=.8,
                                line_width=0),
                    hovertemplate="%{text}: nota %{x:.1f}★, tom %{y:.2f}"
                                  "<extra></extra>"))
                fig.add_hline(y=0, line_color=MUTED, line_dash="dot")
                fig.update_layout(
                    xaxis=dict(title="sua nota (★)", dtick=0.5),
                    yaxis=dict(title="tom do texto (− crítico · + elogioso)",
                               range=[-1.15, 1.15]))
                acordo = ("acompanha" if rho_s >= 0.35 else
                          "acompanha pouco" if rho_s >= 0.15 else
                          "quase não acompanha")
                add(G, "O que você escreve × a nota que você dá",
                    f"Sentimento léxico (heurístico, pt/en) de cada resenha "
                    f"contra a estrela. Seu texto {acordo} sua nota "
                    f"(ρ = {rho_s:.2f}). Pontos abaixo de zero com nota "
                    "alta = elogia com as estrelas, reclama com as palavras.",
                    fig, 440)

            sig = stats.signature_words(reviews)
            if sig is not None and len(sig) >= 8:
                s = pd.Series(sig["tf"].values, index=sig.index)
                add(G, "Suas palavras-assinatura",
                    f"Frequentes E espalhadas por muitas das suas "
                    f"{int(reviews['Review'].notna().sum())} resenhas; uma "
                    "resenha longa sozinha não domina o ranking.",
                    _hbar(s[::-1], BLUE, unit="ocorrências"), 560,
                    secondary=True)

    # ================================================== pessoas e lugares
    G = "Pessoas e lugares"
    top_dir = _top_person(films, "directors", "directors_profile")
    top_act = _top_person(films, "cast", "cast_profile")
    if top_dir or top_act:
        cells = ""
        for role, pp in (("diretor(a) mais visto(a)", top_dir),
                         ("rosto mais frequente", top_act)):
            if not pp:
                continue
            img = (f'<img src="{POSTER_BASE}{pp["profile"]}" alt="" '
                   'loading="lazy">' if pp.get("profile")
                   else '<div class="noface">🎬</div>')
            meta = f'{pp["n"]} filmes'
            if pp.get("rating") is not None:
                meta += f' · sua média {pp["rating"]:.2f}★'
            cells += (f'<figure class="person">{img}<figcaption>'
                      f'<div class="prole">{role}</div>'
                      f'<div class="peoplename">{pp["name"]}</div>'
                      f'<div class="pmeta">{meta}</div></figcaption></figure>')
        add_html(G, "Os rostos do seu cinema",
                 "Quem mais aparece na direção e na tela neste recorte "
                 "(fotos via TMDB)",
                 f'<div class="peoplecards">{cells}</div>')

    ds = stats.director_stats_full(films, min_count=3)
    if len(ds) >= 5:
        destaque = (set(ds.nlargest(8, "n").index)
                    | set(ds.nlargest(2, "nota").index)
                    | set(ds.nsmallest(2, "nota").index))
        labels = [n if n in destaque else "" for n in ds.index]
        fig = go.Figure(go.Scatter(
            x=ds["n"], y=ds["nota"], mode="markers+text",
            text=labels, hovertext=list(ds.index), textposition="top center",
            textfont=dict(size=11, color=MUTED),
            error_y=dict(type="data", array=ds["std"], visible=True,
                         color="rgba(153,170,187,.45)", thickness=1.5, width=4),
            customdata=np.stack([ds["std"], ds["bayes"]], axis=-1),
            marker=dict(size=ds["n"] / ds["n"].max() * 26 + 10,
                        color=ds["bayes"], cmin=max(0, ds["bayes"].min() - .3),
                        colorscale=RATING_SCALE,
                        colorbar=dict(title="média<br>bayesiana",
                                      outlinewidth=0, thickness=14,
                                      tickfont=dict(color=TEXT)),
                        showscale=True, line=dict(width=1.5, color=CARD)),
            hovertemplate=("%{hovertext}: %{x} filmes, %{y:.2f}★ ± "
                           "%{customdata[0]:.2f}<br>média bayesiana "
                           "%{customdata[1]:.2f}★<extra></extra>")))
        fig.update_layout(xaxis_title="filmes vistos", yaxis_title="sua nota média")
        fig.update_xaxes(range=[max(0, ds["n"].min() - 2), ds["n"].max() + 2.5])
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
            "Top 8 créditos de cada filme", _hbar(a, GREEN), 480,
            secondary=True)

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
            add(G, "Idiomas originais", "", fig, 430, secondary=True)

    # narrativa do relatório: panorama -> quando -> o quê -> como avalia ->
    # o modelo (síntese e predição) -> tendências -> pessoas -> o que vem.
    # sort estável: a ordem interna de cada bloco é preservada.
    ordem = ["Visão geral", "Linha do tempo", "O que você assiste",
             "Suas notas", "Modelo do gosto", "Exploração e nicho",
             "Pessoas e lugares", "Watchlist e resenhas"]
    rank = {g: i for i, g in enumerate(ordem)}
    sections.sort(key=lambda s: rank.get(s[0], len(ordem)))

    facts = insights.generate(films, diary, frames)
    return cards, facts, sections


# ------------------------------------------------------------------ template


def _section_html(title, sub, body) -> str:
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return (f'<section><h2>{title}</h2>{sub_html}'
            f'<div class="plot">{body}</div></section>\n')


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
        links = "".join(f'<a href="#t{idx}-g{k}">{g}</a>'
                        for k, g in enumerate(groups))
        nav = f'<nav class="quicknav">{links}</nav>'

    # curadoria (D2): o essencial abre expandido; o secundário de cada
    # bloco vai para um <details> "mais análises"
    secs = ""
    current_group = None
    extra_buf: list[str] = []

    def _flush_extras():
        nonlocal secs, extra_buf
        if extra_buf:
            secs += ('<details class="more"><summary>mais análises '
                     f'({len(extra_buf)})</summary>'
                     + "".join(extra_buf) + "</details>\n")
            extra_buf = []

    for grp, title, sub, body, secondary in sections:
        if grp != current_group:
            _flush_extras()
            k = groups.index(grp)
            secs += f'<div class="group" id="t{idx}-g{k}"><span>{grp}</span></div>\n'
            current_group = grp
        piece = _section_html(title, sub, body)
        if secondary:
            extra_buf.append(piece)
        else:
            secs += piece
    _flush_extras()
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

    # ------- card compartilhável 9:16 (D4) -------
    hours_all = films["runtime"].dropna().sum() / 60 if "runtime" in films else 0
    fav_img = ""
    pf = stats.personal_favorites(films, top=1)
    if len(pf) and "poster" in pf and pd.notna(pf["poster"].iloc[0]):
        fav_img = (f'<img class="scposter" '
                   f'src="{POSTER_BASE}{pf["poster"].iloc[0]}" alt="">'
                   f'<div class="sclbl">favorito mais seu: '
                   f'{pf["Name"].iloc[0]}</div>')
    share_rows = "".join(
        f'<div class="scrow"><div class="scbig">{v}</div>'
        f'<div class="sclbl">{lb}</div></div>'
        for v, lb in [
            (f"{len(films):,}".replace(",", "."), "filmes"),
            (f"{hours_all:,.0f} h".replace(",", "."), "de tela"),
            (f'{rated_all["Rating"].mean():.2f} ★' if len(rated_all) else "—",
             "nota média"),
            (top_g.index[0] if len(top_g) else "—", "gênero nº 1"),
            (top_d.index[0] if len(top_d) else "—", "diretor da vida"),
        ])
    share_html = f"""
<div id="shareoverlay" onclick="if(event.target===this)toggleShare(false)">
  <div id="sharebox">
    <div id="sharecard">
      <div class="schead">🎬 {("@" + username) if username else title}</div>
      {share_rows}
      {fav_img}
      <div class="scfoot">letterboxd-explorer</div>
    </div>
    <div class="scbtns">
      <button onclick="downloadCard()">⬇ baixar PNG (9:16)</button>
      <button onclick="toggleShare(false)">fechar</button>
    </div>
  </div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
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
  .quicknav {{ position:sticky; top:58px; z-index:9; display:flex;
               flex-wrap:wrap; gap:8px; justify-content:center;
               padding:10px 0 12px; margin:16px 0 4px; background:{BG}; }}
  .quicknav a {{ color:{TEXT}; background:{CARD}; border:1px solid #2c3440;
                 border-radius:16px; padding:6px 14px; font-size:.82rem;
                 text-decoration:none; transition:.15s; }}
  .quicknav a:hover {{ border-color:{GREEN}; color:{GREEN}; }}
  .peoplecards {{ display:flex; flex-wrap:wrap; gap:20px;
                  justify-content:center; padding:22px 10px; }}
  .person {{ margin:0; text-align:center; width:170px; }}
  .person img {{ width:120px; height:120px; border-radius:50%;
                 object-fit:cover; border:2px solid #2c3440; }}
  .noface {{ width:120px; height:120px; border-radius:50%; margin:0 auto;
             background:#232b32; display:flex; align-items:center;
             justify-content:center; font-size:2.4rem;
             border:2px solid #2c3440; }}
  .prole {{ color:{MUTED}; text-transform:uppercase; letter-spacing:.1em;
            font-size:.68rem; font-weight:600; margin-top:10px; }}
  .peoplename {{ font-size:1.05rem; font-weight:700; margin-top:3px; }}
  #sidenav {{ position:fixed; left:26px; top:50%; transform:translateY(-50%);
              z-index:15; display:none; flex-direction:column;
              max-width:180px; }}
  @media (min-width: 1400px) {{ #sidenav {{ display:flex; }} }}
  #sidenav a {{ color:{MUTED}; border-left:2px solid #2c3440;
                padding:6px 0 6px 12px; font-size:.8rem; line-height:1.25;
                text-decoration:none; transition:.15s; }}
  #sidenav a:hover {{ color:{TEXT}; border-left-color:{GREEN}; }}
  #totop {{ position:fixed; right:22px; bottom:22px; z-index:20;
            background:{CARD}; color:{TEXT}; border:1px solid #2c3440;
            border-radius:50%; width:44px; height:44px; font-size:1.2rem;
            cursor:pointer; opacity:0; pointer-events:none; transition:.2s; }}
  #totop.show {{ opacity:.92; pointer-events:auto; }}
  #totop:hover {{ border-color:{GREEN}; }}
  #sidenav a.active {{ color:{GREEN}; border-left-color:{GREEN};
                       font-weight:600; }}
  details.more {{ margin-top:28px; }}
  details.more > summary {{ cursor:pointer; color:{MUTED}; font-size:.9rem;
    padding:10px 16px; background:{CARD}; border:1px dashed #2c3440;
    border-radius:12px; user-select:none; transition:.15s; }}
  details.more > summary:hover {{ color:{TEXT}; border-color:{GREEN}; }}
  details.more[open] > summary {{ margin-bottom:6px; }}
  #sharebtn {{ position:fixed; right:22px; bottom:76px; z-index:20;
    background:{CARD}; color:{TEXT}; border:1px solid #2c3440;
    border-radius:22px; padding:10px 16px; font-size:.9rem;
    cursor:pointer; transition:.2s; }}
  #sharebtn:hover {{ border-color:{GREEN}; }}
  #shareoverlay {{ display:none; position:fixed; inset:0; z-index:40;
    background:rgba(0,0,0,.72); align-items:center; justify-content:center; }}
  #shareoverlay.open {{ display:flex; }}
  #sharecard {{ width:324px; height:576px; background:
    linear-gradient(160deg, #17242b 0%, {BG} 55%, #101b13 100%);
    border:1px solid #2c3440; border-radius:18px; padding:28px 26px;
    display:flex; flex-direction:column; justify-content:space-between; }}
  .schead {{ font-size:1.05rem; font-weight:700; color:{TEXT}; }}
  .scrow .scbig {{ font-size:1.5rem; font-weight:800; color:{GREEN};
                   line-height:1.15; }}
  .scrow .sclbl, .sclbl {{ color:{MUTED}; font-size:.78rem; }}
  .scposter {{ width:96px; border-radius:8px; border:1px solid #2c3440;
               margin-top:4px; }}
  .scfoot {{ color:{MUTED}; font-size:.72rem; letter-spacing:.12em;
             text-transform:uppercase; }}
  .scbtns {{ display:flex; gap:10px; justify-content:center; margin-top:14px; }}
  .scbtns button {{ background:{CARD}; color:{TEXT}; border:1px solid #2c3440;
    border-radius:18px; padding:8px 16px; cursor:pointer; }}
  .scbtns button:hover {{ border-color:{GREEN}; }}
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
<button id="sharebtn" onclick="toggleShare(true)">📤 card</button>
{share_html}
<script>
window.addEventListener('scroll', function () {{
  document.getElementById('totop').classList.toggle('show', window.scrollY > 600);
}});
var spy = null;
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
  if (spy) spy.disconnect();
  spy = new IntersectionObserver(function (entries) {{
    entries.forEach(function (en) {{
      if (!en.isIntersecting) return;
      nav.querySelectorAll('a').forEach(function (a) {{
        a.classList.toggle('active',
          a.getAttribute('href') === '#' + en.target.id);
      }});
    }});
  }}, {{rootMargin: '-15% 0px -70% 0px'}});
  document.querySelectorAll('#tab-' + i + ' .group').forEach(function (g) {{
    var a = document.createElement('a');
    a.textContent = g.querySelector('span').textContent;
    a.href = '#' + g.id;
    nav.appendChild(a);
    spy.observe(g);
  }});
}}
function showTab(i, keepHash) {{
  document.querySelectorAll('.tabpane').forEach(function (el, j) {{
    el.style.display = (i === j) ? '' : 'none';
  }});
  document.querySelectorAll('.tabs button').forEach(function (b, j) {{
    b.classList.toggle('active', i === j);
  }});
  buildSideNav(i);
  if (!keepHash) history.replaceState(null, '', '#aba-' + i);
  window.dispatchEvent(new Event('resize'));
}}
// estado da aba persiste na URL (#aba-N)
var m = (location.hash || '').match(/^#aba-(\\d+)$/);
showTab(m ? Math.min(+m[1],
  document.querySelectorAll('.tabpane').length - 1) : 0, !m);
// Plotly precisa de resize quando um <details> abre
document.querySelectorAll('details.more').forEach(function (d) {{
  d.addEventListener('toggle', function () {{
    if (d.open) window.dispatchEvent(new Event('resize'));
  }});
}});
function toggleShare(open) {{
  document.getElementById('shareoverlay').classList.toggle('open', open);
}}
function downloadCard() {{
  if (typeof html2canvas === 'undefined') {{
    alert('Sem internet para carregar o gerador de imagem.'); return;
  }}
  html2canvas(document.getElementById('sharecard'),
              {{scale: 3.33, backgroundColor: null, useCORS: true}})
    .then(function (canvas) {{
      var a = document.createElement('a');
      a.download = 'letterboxd-card.png';
      a.href = canvas.toDataURL('image/png');
      a.click();
    }});
}}
</script>
</body>
</html>"""
    out.write_text(html, encoding="utf-8")
    return out
