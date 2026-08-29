"""
Dashboard interativo da Copa do Mundo (1930-2014).

Execute com:
    streamlit run dashboard.py

Fontes: data/WorldCups.csv, data/WorldCupMatches.csv, data/WorldCupPlayers.csv
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "data"
sys.path.insert(0, str(DATA))
from nomes_corrigidos import JOGADORES, TECNICOS  # noqa: E402

# Alemanha Ocidental e Alemanha unificada aparecem como entradas separadas nos CSVs.
ALEMANHA = {"Germany FR": "Germany", "West Germany": "Germany", "Germany DR": "Germany"}

# --------------------------------------------------------------------------- #
# Paleta — cada cor tem um trabalho. Validada contra a superfície #1a1a19:
# banda OKLCH, piso de croma, separação CVD (protan/deutan) e contraste WCAG.
# --------------------------------------------------------------------------- #
SUPERFICIE = "#1a1a19"

# Categórica (identidade). Ordem fixa, nunca ciclada.
SERIE = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]

# Divergente (polaridade): dois polos opostos + cinza neutro no meio.
# Azul<->vermelho em vez de verde<->vermelho: o par verde/vermelho colapsa
# sob deuteranopia (ΔE 4.1, piso 8) — é o erro de daltonismo mais comum em dashboards.
DIVERGENTE = [[0.0, "#e66767"], [0.5, "#8a8a86"], [1.0, "#3987e5"]]
NEUTRO = "#8a8a86"

# Ordinal (categorias ordenadas): rampa de um tom só. Pódio 1º > 2º > 3º,
# na família âmbar para preservar a leitura de medalha.
PODIO = {"1º — Campeão": "#f0c05a", "2º — Vice": "#c9922b", "3º — Terceiro": "#8f6416"}

# Status (estado). Tokens reservados — nunca viram "série 4".
AMARELO, VERMELHO = "#fab219", "#d03b3b"

# Cromo do gráfico
TINTA, TINTA2, MUTED = "#ffffff", "#c3c2b7", "#898781"
GRADE = "#2c2c2a"

st.set_page_config(
    page_title="Copa do Mundo — Dashboard",
    page_icon=":material/sports_soccer:",
    layout="wide",
)


def br(n, casas=0):
    """Formata número no padrão pt-BR (1.234,56)."""
    return f"{n:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def estilo(fig, altura=400, legenda=True):
    """Cromo recessivo: grade hairline, sem linha de eixo pesada, legenda no topo."""
    fig.update_layout(
        height=altura,
        font=dict(color=TINTA2, size=13),
        title_font=dict(color=TINTA, size=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=52, b=8),
        showlegend=legenda,
        legend=dict(orientation="h", y=1.06, x=0, title_text="",
                    bgcolor="rgba(0,0,0,0)", font=dict(color=TINTA2)),
        hoverlabel=dict(bgcolor="#242422", bordercolor=GRADE,
                        font=dict(color=TINTA, size=12)),
        bargap=0.45,        # marcas finas: barra grossa e saturada lê como bloco
        bargroupgap=0.12,
    )
    eixo = dict(showgrid=True, gridcolor=GRADE, gridwidth=1, zeroline=False,
                showline=False, ticks="", tickfont=dict(color=MUTED, size=12),
                title_font=dict(color=MUTED, size=12))
    fig.update_xaxes(**eixo)
    fig.update_yaxes(**eixo)
    return fig


# --------------------------------------------------------------------------- #
# Carga e tratamento
# --------------------------------------------------------------------------- #
@st.cache_data
def carregar():
    cups = pd.read_csv(DATA / "WorldCups.csv")
    matches = pd.read_csv(DATA / "WorldCupMatches.csv")
    players = pd.read_csv(DATA / "WorldCupPlayers.csv")

    # Attendance vem como texto com ponto de milhar: "3.386.810"
    cups["Attendance"] = (
        cups["Attendance"].astype(str).str.replace(".", "", regex=False).astype(float)
    )
    cups["GolsPorJogo"] = cups["GoalsScored"] / cups["MatchesPlayed"]
    cups["AnfitriaoCampeao"] = cups["Country"] == cups["Winner"]

    # WorldCupMatches tem 3.720 linhas totalmente vazias e 3.735 MatchID duplicados.
    matches = matches.dropna(how="all").drop_duplicates(subset="MatchID").copy()
    matches["Year"] = matches["Year"].astype(int)
    for col in ("Home Team Name", "Away Team Name", "Stage", "Stadium", "City"):
        matches[col] = matches[col].str.strip()
    matches["TotalGols"] = matches["Home Team Goals"] + matches["Away Team Goals"]
    matches["Saldo"] = (matches["Home Team Goals"] - matches["Away Team Goals"]).abs()
    matches["Placar"] = (
        matches["Home Team Name"] + " "
        + matches["Home Team Goals"].astype(int).astype(str) + " x "
        + matches["Away Team Goals"].astype(int).astype(str) + " "
        + matches["Away Team Name"]
    )
    matches["Fase"] = matches["Stage"].apply(
        lambda s: "Fase de grupos"
        if s.lower().startswith(("group", "first round", "preliminary")) else s
    )
    matches["Mataquem"] = matches["Fase"].apply(
        lambda f: "Fase de grupos" if f == "Fase de grupos" else "Mata-mata"
    )

    # Ano de cada partida para poder filtrar jogadores por período.
    players = players.merge(
        matches[["MatchID", "Year"]], on="MatchID", how="inner", validate="many_to_one"
    )
    # Acentos vieram corrompidos da fonte (U+FFFD). Mapa curado em
    # data/nomes_corrigidos.py; nomes incertos ficam como estão, de propósito.
    players["Player Name"] = players["Player Name"].str.strip().replace(JOGADORES)
    players["Coach Name"] = players["Coach Name"].str.strip().replace(TECNICOS)

    return cups, matches, players


def unificar(serie: pd.Series, ativo: bool) -> pd.Series:
    return serie.replace(ALEMANHA) if ativo else serie


def tabela_selecoes(matches: pd.DataFrame, unif: bool) -> pd.DataFrame:
    """Empilha mandante e visitante para tratar toda partida do ponto de vista da seleção."""
    casa = matches.rename(
        columns={"Home Team Name": "Selecao", "Home Team Goals": "GP", "Away Team Goals": "GC"}
    )[["Selecao", "GP", "GC", "Year"]]
    fora = matches.rename(
        columns={"Away Team Name": "Selecao", "Away Team Goals": "GP", "Home Team Goals": "GC"}
    )[["Selecao", "GP", "GC", "Year"]]

    df = pd.concat([casa, fora], ignore_index=True)
    df["Selecao"] = unificar(df["Selecao"], unif)
    df["V"] = (df.GP > df.GC).astype(int)
    df["E"] = (df.GP == df.GC).astype(int)
    df["D"] = (df.GP < df.GC).astype(int)

    agg = df.groupby("Selecao").agg(
        J=("GP", "size"), V=("V", "sum"), E=("E", "sum"), D=("D", "sum"),
        GP=("GP", "sum"), GC=("GC", "sum"), Copas=("Year", "nunique"),
    )
    agg["SG"] = agg.GP - agg.GC
    agg["Aprov%"] = ((agg.V * 3 + agg.E) / (agg.J * 3) * 100).round(1)
    agg["Gols/jogo"] = (agg.GP / agg.J).round(2)
    return agg.reset_index().sort_values(["V", "SG"], ascending=False)


def eventos(players: pd.DataFrame) -> pd.DataFrame:
    """Decodifica a coluna Event: G=gol, P=pênalti, MP=pênalti perdido, Y=amarelo,
    R=vermelho direto, RSY=vermelho por 2º amarelo."""
    ev = players.dropna(subset=["Event"]).copy()
    conta = lambda padrao: ev["Event"].str.count(padrao)  # noqa: E731
    ev["Gols"] = conta(r"(?<!MP)(?<!O)G\d+")
    ev["Penaltis"] = conta(r"(?<!M)P\d+")
    ev["Amarelos"] = conta(r"(?<!RS)Y\d+")
    ev["VermelhosDiretos"] = conta(r"(?<!RS)R\d+")
    ev["SegundoAmarelo"] = conta(r"RSY\d+")
    ev["TotalGols"] = ev["Gols"] + ev["Penaltis"]
    return ev


cups, matches, players = carregar()
ANOS = sorted(cups["Year"].unique())

# --------------------------------------------------------------------------- #
# Sidebar — filtros
# --------------------------------------------------------------------------- #
ATALHOS = {
    "Tudo": (ANOS[0], ANOS[-1]),
    "Era 32 seleções": (1998, 2014),
    "Século XXI": (2002, 2014),
    "Últimas 3": (2006, 2014),
}

st.session_state.setdefault("periodo", (ANOS[0], ANOS[-1]))


def aplicar_atalho():
    """Um atalho apenas move o slider — ele continua sendo a fonte da verdade."""
    if st.session_state.atalho:
        st.session_state.periodo = ATALHOS[st.session_state.atalho]


def limpar():
    st.session_state.periodo = (ANOS[0], ANOS[-1])
    st.session_state.atalho = None
    st.session_state.mataquem = "Tudo"
    st.session_state.times = []


sb = st.sidebar
sb.markdown("### :material/tune: Filtros")

sb.pills("Atalhos", list(ATALHOS), key="atalho", on_change=aplicar_atalho,
         label_visibility="collapsed")
# value= define que é um slider de intervalo; com a key presente no session_state,
# é ela que manda (é assim que os atalhos conseguem mover o slider).
ini, fim = sb.select_slider("Período", options=ANOS, key="periodo",
                            value=st.session_state.periodo)

unif = sb.toggle(
    "Unificar Alemanha", key="unif", value=True,
    help="Os CSVs trazem `Germany FR` e `Germany` separados. Ligado, os dois "
         "viram uma seleção só — sem isso a Alemanha some do topo dos rankings.",
)

with sb.expander("Recortar partidas", icon=":material/filter_list:"):
    st.caption("Vale para as abas Seleções, Partidas e Jogadores. "
               "O Panorama sempre mostra a edição inteira.")
    fase_sel = st.segmented_control("Fase", ["Tudo", "Fase de grupos", "Mata-mata"],
                                    key="mataquem", default="Tudo") or "Tudo"
    times_sel = st.multiselect(
        "Seleções", sorted(unificar(matches["Home Team Name"], True).unique()),
        key="times", placeholder="Todas as seleções",
        help="Mantém apenas partidas em que ao menos uma destas seleções jogou.",
    )

# --------------------------------------------------------------------------- #
# Aplicação dos filtros
# --------------------------------------------------------------------------- #
c = cups[cups["Year"].between(ini, fim)].copy()
for col in ("Winner", "Runners-Up", "Third", "Fourth", "Country"):
    c[col] = unificar(c[col], unif)

m = matches[matches["Year"].between(ini, fim)].copy()
if fase_sel != "Tudo":
    m = m[m["Mataquem"] == fase_sel]
if times_sel:
    casa = unificar(m["Home Team Name"], unif)
    fora = unificar(m["Away Team Name"], unif)
    m = m[casa.isin(times_sel) | fora.isin(times_sel)]

p = players[players["MatchID"].isin(m["MatchID"])].copy()

recortado = fase_sel != "Tudo" or bool(times_sel)

sb.divider()
sb.button("Limpar filtros", icon=":material/restart_alt:", on_click=limpar,
          width="stretch", disabled=not (recortado or (ini, fim) != (ANOS[0], ANOS[-1])))
sb.caption(
    "**Limpeza aplicada**\n\n"
    "- 3.720 linhas vazias e 3.735 `MatchID` duplicados removidos\n"
    "- `Attendance` convertida de texto (`3.386.810`) para número\n"
    "- Acentos corrompidos na fonte (U+FFFD) restaurados por mapa curado"
)

# --------------------------------------------------------------------------- #
# Cabeçalho
# --------------------------------------------------------------------------- #
st.title("Copa do Mundo FIFA")

selo = [f":blue-badge[:material/date_range: {ini}–{fim}]"]
if fase_sel != "Tudo":
    selo.append(f":orange-badge[:material/filter_list: {fase_sel}]")
if times_sel:
    rotulo = ", ".join(times_sel[:3]) + ("…" if len(times_sel) > 3 else "")
    selo.append(f":orange-badge[:material/groups: {rotulo}]")
if unif:
    selo.append(":gray-badge[Alemanha unificada]")
st.markdown(" ".join(selo))

if m.empty:
    st.warning("Nenhuma partida atende a esses filtros. Use **Limpar filtros** na "
               "barra lateral.", icon=":material/search_off:")
    st.stop()

# KPIs agregados do recorte
with st.container(horizontal=True):
    st.metric("Edições", br(c["Year"].nunique()), icon=":material/trophy:", border=True)
    st.metric("Partidas", br(len(m)), icon=":material/sports_soccer:", border=True)
    st.metric("Gols", br(m["TotalGols"].sum()), icon=":material/target:", border=True)
    st.metric("Gols por jogo", br(m["TotalGols"].mean(), 2),
              icon=":material/query_stats:", border=True)
    st.metric("Público médio", br(m["Attendance"].mean()),
              icon=":material/groups:", border=True)
    st.metric("Jogadores", br(p["Player Name"].nunique()),
              icon=":material/person:", border=True)

# KPIs de tendência: última edição do recorte contra a anterior.
# É aqui que a seta verde/vermelha ganha sentido — comparar duas edições vizinhas.
por_ano = (
    m.groupby("Year")
    .agg(GolsJogo=("TotalGols", "mean"), Publico=("Attendance", "mean"),
         Partidas=("MatchID", "size"), Gols=("TotalGols", "sum"))
    .join(c.set_index("Year")[["QualifiedTeams"]])
    .reset_index()
)

if len(por_ano) >= 2:
    ult, ant = por_ano.iloc[-1], por_ano.iloc[-2]
    st.markdown(f"##### Edição de {int(ult.Year)} · variação sobre {int(ant.Year)}")

    def tendencia(rotulo, campo, casas=0, icone="", ajuda=None):
        atual, antes = ult[campo], ant[campo]
        var = (atual - antes) / antes * 100 if antes else 0
        # Delta é string: o Streamlit decide a seta pelo sinal, então "+0,0%"
        # renderizaria seta verde para cima num valor que não mudou. Sem delta.
        parado = abs(var) < 0.05
        st.metric(
            rotulo, br(atual, casas),
            delta=None if parado else f"{var:+.1f}%".replace(".", ","),
            delta_description=f"igual a {int(ant.Year)}" if parado else f"vs {int(ant.Year)}",
            chart_data=por_ano[campo].tolist(), chart_type="line",
            icon=icone, border=True, help=ajuda,
        )

    with st.container(horizontal=True):
        tendencia("Gols por jogo", "GolsJogo", 2, ":material/query_stats:")
        tendencia("Público médio", "Publico", 0, ":material/groups:")
        tendencia("Partidas", "Partidas", 0, ":material/sports_soccer:")
        tendencia("Seleções", "QualifiedTeams", 0, ":material/flag:",
                  "Seleções classificadas para a fase final — não depende do recorte de partidas.")
    st.caption("A linha em cada cartão é a série completa do período selecionado.")

# --------------------------------------------------------------------------- #
# Abas — `on_change="rerun"` faz só a aba aberta calcular
# --------------------------------------------------------------------------- #
abas = st.tabs(
    [":material/trophy: Panorama", ":material/trending_down: Evolução",
     ":material/public: Seleções", ":material/stadium: Partidas",
     ":material/person: Jogadores", ":material/table_chart: Dados"],
    on_change="rerun",
)
aba_panorama, aba_evolucao, aba_selecoes, aba_partidas, aba_jogadores, aba_dados = abas

# --------------------------------------------------------------------------- #
if aba_panorama.open:
    with aba_panorama:
        if recortado:
            st.info("Esta aba usa sempre a edição inteira — o recorte de fase e "
                    "seleções não se aplica a campeões e pódios.",
                    icon=":material/info:")

        esq, dir_ = st.columns(2)

        with esq.container(border=True):
            titulos = c["Winner"].value_counts().reset_index()
            titulos.columns = ["Seleção", "Títulos"]
            # Série única -> uma cor. Colorir por altura duplicaria o que a barra já mostra.
            fig = px.bar(titulos.sort_values("Títulos"), x="Títulos", y="Seleção",
                         orientation="h", text="Títulos", title="Títulos mundiais")
            # textangle=0: com barra fina o Plotly gira o rótulo interno em 90°.
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{y}: %{x} títulos<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 420, legenda=False), width="stretch")

        with dir_.container(border=True):
            podio = (
                pd.concat([
                    c["Winner"].rename("Seleção").to_frame().assign(Posição="1º — Campeão"),
                    c["Runners-Up"].rename("Seleção").to_frame().assign(Posição="2º — Vice"),
                    c["Third"].rename("Seleção").to_frame().assign(Posição="3º — Terceiro"),
                ])
                .groupby(["Seleção", "Posição"]).size().reset_index(name="Vezes")
            )
            ordem = podio.groupby("Seleção")["Vezes"].sum().sort_values().index
            # Posição é categoria ordenada -> rampa de um tom (âmbar), não hues avulsas.
            fig = px.bar(podio, x="Vezes", y="Seleção", color="Posição", orientation="h",
                         category_orders={"Seleção": list(ordem), "Posição": list(PODIO)},
                         color_discrete_map=PODIO, title="Pódios acumulados")
            # Gap de 2px na cor da superfície separa os segmentos — sem contorno nas marcas.
            fig.update_traces(marker_line_width=2, marker_line_color=SUPERFICIE,
                              hovertemplate="%{y} · %{fullData.name}: %{x}×<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 420), width="stretch")

        anfitriao = c[c["AnfitriaoCampeao"]]
        if not anfitriao.empty:
            anos_txt = ", ".join(f"{r.Country} ({int(r.Year)})" for r in anfitriao.itertuples())
            st.info(
                f"**Jogar em casa ajuda.** O anfitrião levou a taça em "
                f"{len(anfitriao)} das {len(c)} edições do período: {anos_txt}.",
                icon=":material/home:",
            )

        with st.container(border=True):
            st.markdown("**Todas as edições**")
            tabela = c[["Year", "Country", "Winner", "Runners-Up", "Third", "Fourth",
                        "GoalsScored", "MatchesPlayed", "GolsPorJogo", "QualifiedTeams",
                        "Attendance"]]
            tabela.columns = ["Ano", "Sede", "Campeão", "Vice", "3º", "4º",
                              "Gols", "Jogos", "Gols/jogo", "Seleções", "Público"]
            st.dataframe(
                tabela, width="stretch", hide_index=True,
                column_config={
                    "Ano": st.column_config.NumberColumn(format="%d"),
                    "Público": st.column_config.NumberColumn(format="localized"),
                    "Gols/jogo": st.column_config.ProgressColumn(
                        format="%.2f", min_value=0,
                        max_value=float(tabela["Gols/jogo"].max())),
                },
            )

# --------------------------------------------------------------------------- #
if aba_evolucao.open:
    with aba_evolucao:
        with st.container(border=True):
            # Uma medida, um eixo. Antes isto era um eixo duplo (gols totais + gols/jogo),
            # cuja sobreposição de escalas inventa uma correlação que não está nos dados.
            fig = go.Figure()
            fig.add_scatter(
                x=c["Year"], y=c["GolsPorJogo"], mode="lines+markers", name="Gols por jogo",
                line=dict(color=SERIE[0], width=2), marker=dict(size=8, color=SERIE[0]),
                hovertemplate="%{x}: %{y:.2f} gols por jogo<extra></extra>",
            )
            # Rótulo direto só nos extremos — um número em cada ponto vira ruído.
            if not c.empty:
                for rotulo, linha in (("máx", c.loc[c["GolsPorJogo"].idxmax()]),
                                      ("mín", c.loc[c["GolsPorJogo"].idxmin()])):
                    fig.add_annotation(
                        x=linha["Year"], y=linha["GolsPorJogo"],
                        text=f"<b>{linha['GolsPorJogo']:.2f}</b> ({rotulo}. {int(linha['Year'])})",
                        showarrow=False, yshift=20, font=dict(color=TINTA, size=12),
                    )
            fig.update_yaxes(title="Gols por jogo", rangemode="tozero")
            fig.update_layout(title="Média de gols por partida, por edição")
            st.plotly_chart(estilo(fig, 400, legenda=False), width="stretch")

        st.info(
            "**O futebol ficou menos goleador.** A média caiu de 5,38 (1954) para "
            "2,21 (1990) — queda de 59%. O total de gols subiu no mesmo período, mas "
            "apenas porque o torneio cresceu de 18 para 64 partidas. É por isso que as "
            "duas medidas ficam em gráficos separados: sobrepostas em eixos diferentes, "
            "inventariam uma correlação que não existe.",
            icon=":material/trending_down:",
        )

        with st.container(border=True):
            # Volume do torneio: duas contagens comparáveis, um eixo só.
            fig = go.Figure()
            for nome, col, cor in (("Gols", "GoalsScored", SERIE[0]),
                                   ("Partidas", "MatchesPlayed", SERIE[1])):
                fig.add_bar(x=c["Year"], y=c[col], name=nome, marker_color=cor,
                            hovertemplate="%{x}: %{y} " + nome.lower() + "<extra></extra>")
            fig.update_layout(barmode="group", title="Volume do torneio por edição")
            st.plotly_chart(estilo(fig, 340), width="stretch")

        e1, e2 = st.columns(2)
        with e1.container(border=True):
            fig = px.bar(c, x="Year", y="Attendance", title="Público total por edição",
                         labels={"Attendance": "Público", "Year": "Ano"})
            fig.update_traces(marker_color=SERIE[0],
                              hovertemplate="%{x}: %{y:,.0f} pessoas<extra></extra>")
            st.plotly_chart(estilo(fig, 360, legenda=False), width="stretch")

        with e2.container(border=True):
            media_pub = m.groupby("Year")["Attendance"].mean().reset_index()
            fig = px.line(media_pub, x="Year", y="Attendance", markers=True,
                          title="Público médio por partida",
                          labels={"Attendance": "Público médio", "Year": "Ano"})
            fig.update_traces(line=dict(color=SERIE[0], width=2),
                              marker=dict(size=8, color=SERIE[0]),
                              hovertemplate="%{x}: %{y:,.0f} por jogo<extra></extra>")
            st.plotly_chart(estilo(fig, 360, legenda=False), width="stretch")

# --------------------------------------------------------------------------- #
if aba_selecoes.open:
    with aba_selecoes:
        rank = tabela_selecoes(m, unif)
        topn = st.slider("Quantas seleções mostrar", 5, 40, min(15, len(rank)), key="topn")
        top = rank.head(topn)

        with st.container(border=True):
            # Vitória/empate/derrota é polaridade -> divergente: dois polos opostos com
            # cinza neutro no meio. Azul/vermelho em vez do verde/vermelho convencional,
            # que os dois polos colapsam sob deuteranopia.
            fig = px.bar(
                top.melt(id_vars="Selecao", value_vars=["V", "E", "D"],
                         var_name="Resultado", value_name="Jogos"),
                x="Jogos", y="Selecao", color="Resultado", orientation="h",
                category_orders={"Selecao": list(top.sort_values("J")["Selecao"]),
                                 "Resultado": ["V", "E", "D"]},
                color_discrete_map={"V": SERIE[0], "E": NEUTRO, "D": SERIE[7]},
                title=f"Vitórias, empates e derrotas — top {topn}",
            )
            fig.update_traces(marker_line_width=2, marker_line_color=SUPERFICIE,
                              hovertemplate="%{y} · %{fullData.name}: %{x}<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, max(400, topn * 26)), width="stretch")

        # Callout automático: a seleção com melhor aproveitamento e nenhum título.
        titulos_por_sel = c["Winner"].value_counts()
        sem_titulo = rank[(rank.J >= 20) & (~rank.Selecao.isin(titulos_por_sel.index))]
        if not sem_titulo.empty:
            azarao = sem_titulo.nlargest(1, "Aprov%").iloc[0]
            st.warning(
                f"**{azarao.Selecao} é a anomalia do recorte.** "
                f"{azarao['Aprov%']}% de aproveitamento em {int(azarao.J)} jogos "
                f"e saldo de {int(azarao.SG):+d} — sem nenhum título.",
                icon=":material/priority_high:",
            )

        s1, s2 = st.columns([3, 2])
        with s1.container(border=True):
            # Saldo de gols tem zero natural -> escala divergente ancorada em 0.
            fig = px.scatter(
                rank[rank.J >= 10], x="J", y="Aprov%", size="GP", color="SG",
                hover_name="Selecao", color_continuous_scale=DIVERGENTE,
                color_continuous_midpoint=0, size_max=42,
                title="Experiência × aproveitamento (mín. 10 jogos)",
                labels={"J": "Partidas disputadas", "Aprov%": "Aproveitamento (%)",
                        "SG": "Saldo"},
            )
            # Anel de 2px na cor da superfície separa marcas sobrepostas.
            fig.update_traces(
                marker=dict(line=dict(width=2, color=SUPERFICIE)),
                hovertemplate="<b>%{hovertext}</b><br>%{x} jogos · %{y:.1f}%<extra></extra>")
            fig.add_hline(y=50, line_width=1, line_color=GRADE)
            fig.update_layout(coloraxis_colorbar=dict(
                title="Saldo", thickness=10, len=0.6,
                tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=11)))
            st.plotly_chart(estilo(fig, 470, legenda=False), width="stretch")

        with s2.container(border=True):
            st.markdown("**Ranking completo**")
            st.dataframe(
                rank[["Selecao", "J", "V", "E", "D", "GP", "GC", "SG", "Aprov%"]]
                .rename(columns={"Selecao": "Seleção"}),
                width="stretch", hide_index=True, height=430,
                column_config={"Aprov%": st.column_config.ProgressColumn(
                    "Aproveitamento", format="%.1f%%", min_value=0, max_value=100)},
            )

        with st.container(border=True):
            st.markdown("**Confronto direto**")
            times = sorted(rank["Selecao"])
            d1, d2 = st.columns(2)
            ta = d1.selectbox("Seleção A", times,
                              index=times.index("Brazil") if "Brazil" in times else 0)
            tb = d2.selectbox("Seleção B", times,
                              index=times.index("Italy") if "Italy" in times else min(1, len(times) - 1))

            ma = m.copy()
            ma["H"] = unificar(ma["Home Team Name"], unif)
            ma["A"] = unificar(ma["Away Team Name"], unif)
            duelo = ma[((ma.H == ta) & (ma.A == tb)) | ((ma.H == tb) & (ma.A == ta))]

            if duelo.empty:
                st.caption(f"{ta} e {tb} nunca se enfrentaram em Copas dentro deste recorte.")
            else:
                va = int(((duelo.H == ta) & (duelo["Home Team Goals"] > duelo["Away Team Goals"])).sum()
                         + ((duelo.A == ta) & (duelo["Away Team Goals"] > duelo["Home Team Goals"])).sum())
                emp = int((duelo["Home Team Goals"] == duelo["Away Team Goals"]).sum())
                with st.container(horizontal=True):
                    st.metric(f"Vitórias {ta}", va, border=True)
                    st.metric("Empates", emp, border=True)
                    st.metric(f"Vitórias {tb}", len(duelo) - va - emp, border=True)
                st.dataframe(
                    duelo[["Year", "Stage", "Placar", "Stadium", "City", "Attendance"]]
                    .rename(columns={"Year": "Ano", "Stage": "Fase", "Stadium": "Estádio",
                                     "City": "Cidade", "Attendance": "Público"})
                    .sort_values("Ano"),
                    width="stretch", hide_index=True,
                    column_config={
                        "Ano": st.column_config.NumberColumn(format="%d"),
                        "Público": st.column_config.NumberColumn(format="localized")},
                )

# --------------------------------------------------------------------------- #
if aba_partidas.open:
    with aba_partidas:
        p1, p2 = st.columns(2)

        with p1.container(border=True):
            dist = m["TotalGols"].value_counts().sort_index().reset_index()
            dist.columns = ["Gols na partida", "Partidas"]
            fig = px.bar(dist, x="Gols na partida", y="Partidas", text="Partidas",
                         title="Distribuição de gols por partida")
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{x} gols: %{y} partidas<extra></extra>")
            st.plotly_chart(estilo(fig, 380, legenda=False), width="stretch")

        with p2.container(border=True):
            fase = m.groupby("Fase").agg(Jogos=("TotalGols", "size"),
                                         Media=("TotalGols", "mean")).reset_index()
            fase = fase[fase.Jogos >= 5].sort_values("Media")
            fig = px.bar(fase, x="Media", y="Fase", orientation="h",
                         text=fase["Media"].round(2),
                         title="Média de gols por fase (mín. 5 jogos)",
                         labels={"Media": "Gols por jogo"})
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{y}: %{x:.2f} gols por jogo<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 380, legenda=False), width="stretch")

        recorde = m.nlargest(1, "Attendance").iloc[0]
        st.info(
            f"**Maior público do recorte:** {recorde.Placar} em {int(recorde.Year)}, "
            f"no {recorde.Stadium} ({recorde.City}) — "
            f"{br(recorde.Attendance)} pessoas.",
            icon=":material/groups:",
        )

        st.markdown("##### Recordes")
        r1, r2, r3 = st.columns(3)
        cfg_ano = {"Ano": st.column_config.NumberColumn(format="%d")}

        with r1.container(border=True):
            st.markdown("**Maiores goleadas**")
            st.dataframe(m.nlargest(10, "Saldo")[["Year", "Placar", "Saldo"]]
                         .rename(columns={"Year": "Ano"}), width="stretch",
                         hide_index=True, column_config=cfg_ano)
        with r2.container(border=True):
            st.markdown("**Mais gols numa partida**")
            st.dataframe(m.nlargest(10, "TotalGols")[["Year", "Placar", "TotalGols"]]
                         .rename(columns={"Year": "Ano", "TotalGols": "Gols"}),
                         width="stretch", hide_index=True, column_config=cfg_ano)
        with r3.container(border=True):
            st.markdown("**Maiores públicos**")
            st.dataframe(
                m.nlargest(10, "Attendance")[["Year", "Placar", "Attendance"]]
                .rename(columns={"Year": "Ano", "Attendance": "Público"}),
                width="stretch", hide_index=True,
                column_config={**cfg_ano,
                               "Público": st.column_config.NumberColumn(format="localized")},
            )

        with st.container(border=True):
            est = (m.groupby(["Stadium", "City"])
                   .agg(Jogos=("MatchID", "size"), PublicoMedio=("Attendance", "mean"))
                   .reset_index().nlargest(15, "Jogos"))
            fig = px.scatter(est, x="Jogos", y="PublicoMedio", size="Jogos",
                             hover_name="Stadium", text="Stadium",
                             title="Estádios mais usados",
                             labels={"PublicoMedio": "Público médio"})
            fig.update_traces(
                marker=dict(color=SERIE[0], line=dict(width=2, color=SUPERFICIE)),
                textposition="top center", textfont=dict(color=MUTED, size=11),
                hovertemplate="<b>%{hovertext}</b><br>%{x} jogos · %{y:,.0f} de média<extra></extra>")
            st.plotly_chart(estilo(fig, 450, legenda=False), width="stretch")

# --------------------------------------------------------------------------- #
if aba_jogadores.open:
    with aba_jogadores:
        ev = eventos(p)

        with st.container(horizontal=True):
            st.metric("Gols (jogo aberto)", br(ev["Gols"].sum()),
                      icon=":material/sports_soccer:", border=True)
            st.metric("Gols de pênalti", br(ev["Penaltis"].sum()),
                      icon=":material/target:", border=True)
            st.metric("Cartões amarelos", br(ev["Amarelos"].sum()),
                      icon=":material/style:", border=True)
            st.metric("Vermelhos", br(ev["VermelhosDiretos"].sum() + ev["SegundoAmarelo"].sum()),
                      icon=":material/dangerous:", border=True,
                      help="Vermelhos diretos + segundo amarelo")

        with st.container(border=True):
            art = (ev.groupby("Player Name")[["Gols", "Penaltis", "TotalGols"]].sum()
                   .sort_values("TotalGols", ascending=False).head(20).reset_index())
            fig = px.bar(
                art.melt(id_vars="Player Name", value_vars=["Gols", "Penaltis"],
                         var_name="Tipo", value_name="Qtd"),
                x="Qtd", y="Player Name", color="Tipo", orientation="h",
                category_orders={"Player Name": list(art.sort_values("TotalGols")["Player Name"])},
                color_discrete_map={"Gols": SERIE[0], "Penaltis": SERIE[1]},
                title="Top 20 artilheiros",
            )
            fig.update_traces(marker_line_width=2, marker_line_color=SUPERFICIE,
                              hovertemplate="%{y} · %{fullData.name}: %{x}<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 620), width="stretch")

        g1, g2 = st.columns(2)
        with g1.container(border=True):
            # Duas séries, não três: o segundo amarelo entra no vermelho (é o que ele é
            # em campo). Como três hues, amarelo e laranja ficavam a ΔE 13,6 — abaixo do
            # piso de 15 em que dois tons deixam de ser distinguíveis mesmo com visão normal.
            cartoes = ev.groupby("Year")[["Amarelos", "VermelhosDiretos", "SegundoAmarelo"]].sum()
            cartoes["Vermelhos"] = cartoes["VermelhosDiretos"] + cartoes["SegundoAmarelo"]
            cartoes = cartoes.reset_index()
            fig = px.area(cartoes, x="Year", y=["Amarelos", "Vermelhos"],
                          title="Cartões por edição",
                          labels={"value": "Cartões", "Year": "Ano"},
                          color_discrete_map={"Amarelos": AMARELO, "Vermelhos": VERMELHO})
            fig.update_traces(line_width=2,
                              hovertemplate="%{x} · %{fullData.name}: %{y}<extra></extra>")
            st.plotly_chart(estilo(fig, 380), width="stretch")
            st.caption("Cartões só passaram a ser registrados a partir de 1970. "
                       "Vermelhos incluem o segundo amarelo.")

        with g2.container(border=True):
            tec = (p.drop_duplicates(subset=["MatchID", "Coach Name"])["Coach Name"]
                   .value_counts().head(15).reset_index())
            tec.columns = ["Técnico", "Jogos"]
            fig = px.bar(tec.sort_values("Jogos"), x="Jogos", y="Técnico",
                         orientation="h", text="Jogos", title="Técnicos com mais partidas")
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{y}: %{x} jogos<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 380, legenda=False), width="stretch")

        with st.container(border=True):
            st.markdown("**Buscar jogador**")
            busca = st.text_input("Nome (parcial)", placeholder="ex.: RONALDO, KLOSE, PELÉ",
                                  label_visibility="collapsed")
            if busca:
                achou = ev[ev["Player Name"].str.contains(busca, case=False, na=False)]
                if achou.empty:
                    st.caption("Nenhum jogador encontrado.")
                else:
                    st.dataframe(
                        achou.groupby(["Player Name", "Team Initials"])
                        .agg(Jogos=("MatchID", "nunique"), Gols=("TotalGols", "sum"),
                             Amarelos=("Amarelos", "sum"), Copas=("Year", "nunique"))
                        .sort_values("Gols", ascending=False).reset_index()
                        .rename(columns={"Player Name": "Jogador", "Team Initials": "Seleção"}),
                        width="stretch", hide_index=True,
                    )

# --------------------------------------------------------------------------- #
if aba_dados.open:
    with aba_dados:
        escolha = st.segmented_control(
            "Tabela", ["Edições", "Partidas", "Jogadores"], default="Edições",
            label_visibility="collapsed") or "Edições"
        df = {"Edições": c, "Partidas": m, "Jogadores": p}[escolha]
        st.caption(f"{br(len(df))} linhas × {df.shape[1]} colunas "
                   "(após limpeza e filtros aplicados).")
        st.dataframe(df, width="stretch", height=520)
        st.download_button(
            f"Baixar {escolha.lower()} em CSV", icon=":material/download:",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"copa_{escolha.lower()}_{ini}_{fim}.csv",
            mime="text/csv",
        )

# --------------------------------------------------------------------------- #
# Rodapé — fora das abas, aparece em todas.
# Emoji aqui é deliberado: é o único ponto do app onde ele cabe.
# --------------------------------------------------------------------------- #
st.space("large")
st.caption(
    "✨ Feito com ❤️ por **Felipe Vital** e **Claudinho** — "
    "[vitaless7](https://github.com/vitaless7) · "
    "[código no GitHub](https://github.com/vitaless7/worldcup-dashboard)",
    text_alignment="center",
)
