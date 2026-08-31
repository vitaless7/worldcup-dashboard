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
# Paleta — cada cor tem um trabalho. Espelhada em image.png (preto puro, cartao
# quase-preto, um accent rosa) e validada contra a superficie do cartao:
# banda OKLCH, piso de croma, separacao CVD (protan/deutan) e contraste WCAG.
# --------------------------------------------------------------------------- #
# É o CARTÃO, não a página: é sobre ele que as marcas ficam, então é contra
# ele que a paleta foi validada e é dele a cor dos vãos de 2px entre marcas.
SUPERFICIE = "#131313"

# Categórica (identidade). Ordem fixa, nunca ciclada — a ordem É o mecanismo
# de segurança CVD. Slot 1 no rosa do accent: é assim que a referência
# trabalha, um tom só carregando quase todo gráfico. Slot 2 no AZUL, não no
# aqua: aqua ao lado do rosa colapsa sob deuteranopia (ΔE 3,0).
# Validada em dataviz/scripts/validate_palette.py --mode dark --surface #131313:
# adjacente CVD 8,4 · piso de visão normal 19,8 · 3 primeiros --pairs all 8,8/18,2.
SERIE = ["#e44161", "#3987e5", "#c98500", "#199e70", "#9085e9", "#008300", "#00a0b4", "#b06a00"]

# Divergente (polaridade): dois polos opostos + cinza neutro no meio.
# Rosa<->azul: CVD 20,7, e mantém a tela em dois cromáticos só (o accent e o
# azul), que é a economia de cor da referência.
# Verde<->vermelho está fora: colapsa sob deuteranopia.
POLO_POS, POLO_NEG = "#e44161", "#3987e5"
DIVERGENTE = [[0.0, POLO_NEG], [0.5, "#6f6f6f"], [1.0, POLO_POS]]
NEUTRO = "#6f6f6f"

# Ordinal (categorias ordenadas): rampa de um tom só. Pódio 1º > 2º > 3º.
# Neutra, não rosa: ao lado do accent a rampa rosada virava a mesma cor com
# saturações diferentes. Aqui o rosa segue sendo o único cromático da tela.
# Validada --ordinal --surface #131313: L monótono, ΔL >= 0.06, ponta 3.64:1.
PODIO = {"1º — Campeão": "#dcdcdc", "2º — Vice": "#a5a5a5", "3º — Terceiro": "#6e6e6e"}

# Status (estado). Tokens reservados — nunca viram "série 4". O vermelho saiu
# de #d03b3b para um tijolo: contra um accent rosa o vermelho antigo ficava a
# ΔE 6,1 do accent (indistinguível); #c94f22 abre para 9,3.
AMARELO, VERMELHO = "#fab219", "#c94f22"

# Cromo do gráfico — neutro, medido na referência (rótulos cinza-claro, eixos
# mais recuados ainda). Nada de branco puro nas marcas: só o título usa.
TINTA, TINTA2, MUTED = "#f2f2f2", "#a5a5a5", "#7d7d7d"
GRADE = "#1c1c1c"

st.set_page_config(
    page_title="Copa do Mundo — Dashboard",
    page_icon=":material/sports_soccer:",
    layout="wide",
)


# --------------------------------------------------------------------------- #
# Cromo de cartão — traduzido de image.png. A referência é um dark UI de time
# de produto: página preta, cartões quase-pretos com raio grande e SEM borda
# dura, tipografia apertada, um accent rosa que aparece pouco e sempre em
# traço, texto ou pílula — nunca como área grande com texto em cima.
#
# O tema (cores, fonte, raio base) vive em .streamlit/config.toml; aqui fica só
# o que o config não alcança: elevação, o gradiente do herói, a régua de
# tipografia e a barra de abas em pílula.
#
# Contraste: o accent #e44161 dá 4,63:1 sobre o cartão e 5,23:1 sobre a
# página — passa AA para texto pequeno. Preencher uma pílula inteira de rosa
# com texto branco daria 3,1:1 e NÃO passa; por isso a aba ativa é branca com
# texto preto (a pílula da referência), e não rosa.
# --------------------------------------------------------------------------- #
HERO_A, HERO_B = "#1d1114", "#121011"   # brasa: rosa quase apagado -> neutro
ACCENT = "#e44161"      # accent: traço, número e texto
ACCENT_HI = "#f04467"   # o passo claro, para hover e link
CARTAO = "#131313"
CARTAO_HOVER = "#181818"

st.html(f"""
<style>
/* ---------------------------------------------------------------- cartões */
/* Na referência a separação vem do TOM (cartão #131313 sobre página #000),
   com uma sombra difusa fazendo o cartão flutuar — não de borda desenhada. */
[class*="st-key-cartao"], [data-testid="stMetric"] {{
    background: {CARTAO};
    border-color: transparent;
    box-shadow: 0 1px 1px rgba(0,0,0,.6), 0 10px 30px -22px rgba(0,0,0,.9);
    transition: background .18s ease, box-shadow .18s ease;
}}
[class*="st-key-cartao"]:hover, [data-testid="stMetric"]:hover {{
    background: {CARTAO_HOVER};
    box-shadow: 0 1px 1px rgba(0,0,0,.6), 0 16px 40px -24px rgba(0,0,0,1);
}}
[class*="st-key-cartao"] {{ padding: 14px 16px; }}

/* -------------------------------------------------------------- métricas */
/* Número grande e apertado: é o KPI que carrega o cartão, não o rótulo. */
[data-testid="stMetric"] {{ padding: 18px 20px; }}
[data-testid="stMetricValue"] {{
    font-size: 32px; font-weight: 700; letter-spacing: -.035em; color: {TINTA};
}}
[data-testid="stMetricLabel"] p {{
    font-size: 12px; font-weight: 500; color: {MUTED}; letter-spacing: .005em;
}}
/* O ícone do metric ganha o accent — é o ponto colorido que a referência põe
   ao lado de cada linha de lista. Um por cartão, nunca mais. */
[data-testid="stMetricIcon"] {{ color: {ACCENT}; }}
/* A faísca do metric é um Vega embed, e o Streamlit escreve a cor de fundo da
   PÁGINA no atributo style do próprio SVG. Com a página preta e o cartão não,
   isso abria um retângulo preto dentro do cartão. Transparente: a faísca passa
   a flutuar sobre a superfície do cartão, como todo o resto.
   (Nada de "menor-que" em comentário de CSS aqui: o sanitizador do st.html
   descarta o bloco inteiro se achar o que parece uma tag dentro dele.) */
[data-testid="stMetricChart"] .marks {{ background-color: transparent !important; }}
/* O Streamlit amarra a cor da faísca à do delta: subiu vira verde, caiu vira
   vermelho. Isso gasta o token de status numa linha que não é um estado — a
   série histórica é a mesma coisa em todo cartão, então tem que ter uma cor
   só. A faísca volta para o accent da paleta e o verde/vermelho fica onde
   significa alguma coisa: na porcentagem, que é o que compara duas edições. */
[data-testid="stMetricChart"] .mark-line path {{ stroke: {ACCENT} !important; }}

/* ---------------------------------------------------------------- herói */
/* Cartão escuro com brasa rosa no canto, e o accent só na onda e nos números.
   Fundo chapado de rosa com texto branco daria 3,1:1; assim fica 5,2:1. */
.st-key-heroi {{
    background:
        radial-gradient(120% 140% at 0% 0%, rgba(228,65,97,.16) 0%, rgba(228,65,97,0) 55%),
        linear-gradient(150deg, {HERO_A} 0%, {HERO_B} 70%);
    border: 1px solid rgba(228,65,97,.16);
    padding: 22px 24px 18px;
}}
/* O metric do herói é o único sem casca no app: nada de fundo, sombra ou padding. */
.st-key-heroi [data-testid="stMetric"] {{
    background: transparent; box-shadow: none; padding: 0;
}}
.st-key-heroi [data-testid="stMetric"]:hover {{ background: transparent; }}
.st-key-heroi [data-testid="stMetricValue"] {{
    font-size: 50px; letter-spacing: -.04em; color: {TINTA};
}}
.st-key-heroi [data-testid="stMetricLabel"] p {{ color: {MUTED}; }}
.st-key-heroi strong {{ color: {ACCENT}; font-size: 20px; letter-spacing: -.02em; }}
.st-key-heroi p {{ color: {TINTA2}; }}

/* ----------------------------------------------------------- tipografia */
/* Quatro níveis e só: título da página, rótulo de seção, título de cartão,
   legenda. A referência aperta o tracking dos títulos e afrouxa o dos
   micro-rótulos em caixa-alta — é o que dá a "cara de kit de UI". */
h1 {{ letter-spacing: -.035em; }}
h5 {{
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: .11em; text-transform: uppercase;
    color: {MUTED} !important; margin-bottom: 2px;
}}
[class*="st-key-cabecalho-"] {{ margin-bottom: 6px; }}
[class*="st-key-cabecalho-"] [data-testid="stMarkdownContainer"] p {{
    font-size: 15px; font-weight: 600; letter-spacing: -.015em; color: {TINTA};
}}
/* A legenda do cartão é `stCaptionContainer`, não `stMarkdownContainer` — sem
   essa distinção ela herdava o peso do título e virava uma segunda manchete. */
[class*="st-key-cabecalho-"] [data-testid="stCaptionContainer"] p {{
    font-size: 12.5px; font-weight: 400; letter-spacing: 0; color: {MUTED};
}}

/* ---------------------------------------------------------------- marca */
/* Selo + assinatura. Vai num bloco de HTML só — um lockup de marca não tem
   equivalente nativo, e aninhar containers para montá-lo deixa o selo à mercê
   do flex do Streamlit (ele colapsava para 7px). */
.marca {{ display: flex; align-items: center; gap: 11px; margin: 2px 0 18px; }}
.marca-selo {{
    background: linear-gradient(145deg, {ACCENT} 0%, #b8304c 100%);
    border-radius: 14px;
    width: 40px; height: 40px; flex: 0 0 40px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 6px 18px -8px rgba(228,65,97,.75);
}}
/* Único lugar do app com área grande de accent: o ícone é uma forma, não
   texto corrido, então a regra de contraste de texto não se aplica. */
.marca-icone {{
    font-family: "Material Symbols Rounded"; font-size: 22px; color: #ffffff;
    line-height: 1;
}}
.marca-nome {{ font-weight: 700; font-size: 15px; color: {TINTA};
              letter-spacing: -.02em; line-height: 1.25; }}
.marca-sub {{ font-size: 12px; color: {MUTED}; line-height: 1.25; }}

/* ----------------------------------------------------------------- abas */
/* A barra vira um grupo segmentado em pílula, não uma régua sublinhada. */
[data-testid="stTabs"] [role="tablist"] {{
    gap: 4px; padding: 5px;
    background: {CARTAO};
    border: none;
    border-radius: 999px;
    width: fit-content;
    border-bottom: none;
}}
[data-testid="stTab"] {{
    border-radius: 999px; padding: 7px 16px;
    font-size: 13px; font-weight: 500;
}}
[data-testid="stTab"] p, [data-testid="stTab"] span {{ color: {TINTA2}; }}
[data-testid="stTab"]:hover {{ background: #202020; }}
/* Aba ativa: pílula branca com texto preto — é exatamente como a referência
   marca o item selecionado (o botão "Download", o dia do calendário). Rosa
   chapado com texto branco em cima daria 3,1:1 e não passaria. */
[data-testid="stTab"][aria-selected="true"] {{ background: {TINTA}; }}
[data-testid="stTab"][aria-selected="true"] p,
[data-testid="stTab"][aria-selected="true"] span,
[data-testid="stTab"][aria-selected="true"] [data-testid="stIconMaterial"],
[data-testid="stTab"][aria-selected="true"] span[translate="no"] {{
    color: #0a0a0a !important;
}}
/* Sublinhado da aba ativa: a pílula já marca a seleção. */
.react-aria-SelectionIndicator {{ display: none; }}

/* --------------------------------------------------------------- avisos */
/* O padrão do Streamlit pinta a faixa inteira com o tom do status — uma banda
   azul saturada de 1400px que rouba a tela do accent. A referência nunca usa
   área grande de cor: aqui o aviso vira cartão neutro com um filete e o ícone
   no tom do status. O status segue legível por ícone + texto, nunca por cor só. */
[data-testid="stAlertContainer"] {{
    background: {CARTAO} !important;
    border: 1px solid #1e1e1e;
    border-left: 3px solid currentColor;
    border-radius: 14px;
}}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {{ color: {TINTA2}; }}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] strong {{ color: {TINTA}; }}

/* ------------------------------------------------------------- controles */
/* Pílulas e botões seguem a mesma gramática das abas: fundo branco quando
   selecionado, cinza recuado quando não. */
[data-testid="stBaseButton-pillsActive"] {{
    background: {TINTA}; color: #0a0a0a; border-color: {TINTA};
}}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
    border-color: {ACCENT}; color: {ACCENT_HI};
}}
</style>
""")

_cartoes = 0


def cartao(pai=st, titulo=None, legenda=None, **kw):
    """Container com borda, `key` e cabeçalho próprio.

    A key dá a classe .st-key-cartao-N, que é o gancho estável do CSS de sombra.
    O título fica no cabeçalho do cartão, não dentro do gráfico: assim todo
    cartão do app — gráfico, tabela ou KPI — abre do mesmo jeito.
    """
    global _cartoes
    _cartoes += 1
    box = pai.container(border=True, key=f"cartao-{_cartoes}", **kw)
    if titulo:
        with box.container(key=f"cabecalho-{_cartoes}", gap=None):
            st.markdown(f"**{titulo}**")
            if legenda:
                st.caption(legenda)
    return box


def br(n, casas=0):
    """Formata número no padrão pt-BR (1.234,56)."""
    return f"{n:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def estilo(fig, altura=400, legenda=True, grade="auto"):
    """Cromo dos gráficos — um lugar só, para todos terem a mesma cara.

    Da referência de design vem: barra de canto arredondado, linha em spline,
    grade só no eixo que carrega a medida e tipografia recessiva. O eixo de
    categoria não ganha grade: ele não tem escala para ler contra.

    grade: "auto" põe grade só no eixo da medida (deduzido da orientação das
    marcas); "ambos" para dispersões, onde os dois eixos são quantitativos.
    """
    horizontal = any(getattr(t, "orientation", None) == "h" for t in fig.data)
    eixo_medida = "x" if horizontal else "y"

    for t in fig.data:
        if t.type == "scatter" and "lines" in (t.mode or "lines"):
            # Spline com pouca tensão: a curva da referência sem inventar
            # ondulação entre pontos que estão em linha reta.
            t.line.shape = "spline"
            t.line.smoothing = 0.6

    fig.update_layout(
        height=altura,
        font=dict(color=TINTA2, size=12),
        # Nada de title/title_font aqui: o título é o cabeçalho do cartão. Qualquer
        # objeto `title` no layout — mesmo vazio, mesmo `title=None`, que serializa
        # como {} — faz o Plotly 7 desenhar a string "undefined" dentro do gráfico.
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # Sem título dentro do plot, a margem de topo só precisa caber a legenda.
        margin=dict(l=8, r=8, t=30 if legenda else 4, b=8),
        showlegend=legenda,
        legend=dict(orientation="h", y=1.14, x=0, title_text="",
                    bgcolor="rgba(0,0,0,0)", itemsizing="constant",
                    font=dict(color=MUTED, size=12)),
        hoverlabel=dict(bgcolor="#1c1c1c", bordercolor="#2a2a2a",
                        font=dict(color=TINTA, size=12)),
        bargap=0.45,          # marcas finas: barra grossa e saturada lê como bloco
        bargroupgap=0.12,
        barcornerradius=6,    # no layout, não na marca: em barra empilhada
                              # arredonda as pontas da pilha, não cada segmento
    )

    eixo = dict(zeroline=False, showline=False, ticks="",
                gridcolor=GRADE, gridwidth=1,
                tickfont=dict(color=MUTED, size=12),
                title_font=dict(color=MUTED, size=12))
    fig.update_xaxes(**eixo, showgrid=grade == "ambos" or eixo_medida == "x")
    fig.update_yaxes(**eixo, showgrid=grade == "ambos" or eixo_medida == "y")
    return fig


# Barra de ferramentas do Plotly desligada: ela aparecia flutuando por cima do
# cartão no hover, com um cromo (ícones, borda, fundo) que não é o do app. O
# que ela dava — baixar os dados — a aba Dados dá melhor.
PLOTLY = {"displayModeBar": False}


def area_gradiente(fig, cor):
    """Preenchimento que some para baixo — a onda da referência.

    Serve só para série única: com duas séries sobrepostas o degradê vira
    uma terceira cor que não representa nada.
    """
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    fig.update_traces(
        fill="tozeroy",
        fillgradient=dict(type="vertical",
                          colorscale=[[0, f"rgba({r},{g},{b},0)"],
                                      [1, f"rgba({r},{g},{b},.22)"]]),
    )
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

# Marca. O gradiente é o mesmo do herói e da aba ativa: é o que amarra barra
# lateral, cabeçalho e abas como uma coisa só.
sb.html(
    '<div class="marca">'
    '<div class="marca-selo"><span class="marca-icone">sports_soccer</span></div>'
    '<div><div class="marca-nome">Copa do Mundo</div>'
    '<div class="marca-sub">FIFA · 1930–2014</div></div>'
    "</div>"
)

# Filtros num cartão — mesma casca dos cartões do conteúdo, para a barra
# lateral não parecer uma região de outro app.
with sb.container(border=True, key="cartao-filtros"):
    st.markdown("##### Filtros")

    st.pills("Atalhos", list(ATALHOS), key="atalho", on_change=aplicar_atalho,
             label_visibility="collapsed")
    # value= define que é um slider de intervalo; com a key presente no session_state,
    # é ela que manda (é assim que os atalhos conseguem mover o slider).
    ini, fim = st.select_slider("Período", options=ANOS, key="periodo",
                                value=st.session_state.periodo)

    unif = st.toggle(
        "Unificar Alemanha", key="unif", value=True,
        help="Os CSVs trazem `Germany FR` e `Germany` separados. Ligado, os dois "
             "viram uma seleção só — sem isso a Alemanha some do topo dos rankings.",
    )

    with st.expander("Recortar partidas", icon=":material/filter_list:"):
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
selo = [f":gray-badge[:material/date_range: {ini}–{fim}]"]
if fase_sel != "Tudo":
    selo.append(f":primary-badge[:material/filter_list: {fase_sel}]")
if times_sel:
    rotulo = ", ".join(times_sel[:3]) + ("…" if len(times_sel) > 3 else "")
    selo.append(f":primary-badge[:material/groups: {rotulo}]")
if unif:
    selo.append(":gray-badge[Alemanha unificada]")

# Título à esquerda, contexto do recorte à direita — a barra de topo da
# referência, sem inventar um botão que o app não tem.
with st.container(horizontal=True, horizontal_alignment="distribute",
                  vertical_alignment="center"):
    st.title("Copa do Mundo FIFA", width="content")
    st.markdown(" ".join(selo), width="content")

if m.empty:
    st.warning("Nenhuma partida atende a esses filtros. Use **Limpar filtros** na "
               "barra lateral.", icon=":material/search_off:")
    st.stop()

# KPIs do recorte — um herói e uma grade de apoio, a divisão da referência de
# design. O herói fica com a medida que carrega a página (gols); o resto vira
# cartão pequeno em vez de disputar a mesma altura visual.
gols_ano = m.groupby("Year")["TotalGols"].sum()
gols_casa = int(m["Home Team Goals"].sum())
gols_fora = int(m["Away Team Goals"].sum())
total_gols = gols_casa + gols_fora

col_heroi, col_kpis = st.columns([2, 3], gap="medium")

with col_heroi.container(border=True, key="heroi", height="stretch"):
    st.metric("Gols no período", br(total_gols))

    # A onda do herói: mesma série do número acima, sem eixos — é textura de
    # apoio, não gráfico de leitura. Quem quiser o valor tem o hover.
    onda = go.Figure()
    onda.add_scatter(
        x=gols_ano.index, y=gols_ano.values, mode="lines",
        line=dict(color=ACCENT, width=2, shape="spline"),
        fill="tozeroy",
        fillgradient=dict(type="vertical",
                          colorscale=[[0, "rgba(228,65,97,0)"],
                                      [1, "rgba(228,65,97,.32)"]]),
        hovertemplate="%{x}: %{y} gols<extra></extra>",
    )
    onda.update_layout(
        height=104, margin=dict(l=0, r=0, t=6, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False, rangemode="tozero"),
        hoverlabel=dict(bgcolor="#1c1c1c", bordercolor="#2a2a2a",
                        font=dict(color=TINTA, size=12)),
    )
    st.plotly_chart(onda, width="stretch", key="onda_heroi", config=PLOTLY)

    # Divisão percentual do próprio número do herói — mandante e visitante somam
    # o total de gols. Só entra aqui o que reparte a mesma medida.
    casa_pct = gols_casa / total_gols * 100 if total_gols else 0
    with st.container(horizontal=True, gap="large"):
        for pct, rotulo in ((casa_pct, "mandante"), (100 - casa_pct, "visitante")):
            with st.container(width="content"):
                st.markdown(f"**{br(pct, 1)}%**")
                st.caption(rotulo)

with col_kpis.container(horizontal=True, gap="medium"):
    st.metric("Edições", br(c["Year"].nunique()), icon=":material/trophy:", border=True)
    st.metric("Partidas", br(len(m)), icon=":material/sports_soccer:", border=True)
    st.metric("Gols por jogo", br(m["TotalGols"].mean(), 2),
              icon=":material/query_stats:", border=True)
    st.metric("Público médio", br(m["Attendance"].mean()),
              icon=":material/groups:", border=True)
    st.metric("Jogadores", br(p["Player Name"].nunique()),
              icon=":material/person:", border=True)
    # Sexto cartão fecha a grade em 3x2 — com cinco, a segunda linha estica
    # dois cartões no dobro da largura dos de cima.
    st.metric("Países-sede", br(c["Country"].nunique()),
              icon=":material/location_on:", border=True)

st.space("small")

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

        with cartao(esq, "Títulos mundiais"):
            titulos = c["Winner"].value_counts().reset_index()
            titulos.columns = ["Seleção", "Títulos"]
            # Série única -> uma cor. Colorir por altura duplicaria o que a barra já mostra.
            fig = px.bar(titulos.sort_values("Títulos"), x="Títulos", y="Seleção",
                         orientation="h", text="Títulos")
            # textangle=0: com barra fina o Plotly gira o rótulo interno em 90°.
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{y}: %{x} títulos<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 420, legenda=False), width="stretch", config=PLOTLY)

        with cartao(dir_, "Pódios acumulados"):
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
                         color_discrete_map=PODIO)
            # Gap de 2px na cor da superfície separa os segmentos — sem contorno nas marcas.
            fig.update_traces(marker_line_width=2, marker_line_color=SUPERFICIE,
                              hovertemplate="%{y} · %{fullData.name}: %{x}×<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 420), width="stretch", config=PLOTLY)

        anfitriao = c[c["AnfitriaoCampeao"]]
        if not anfitriao.empty:
            anos_txt = ", ".join(f"{r.Country} ({int(r.Year)})" for r in anfitriao.itertuples())
            st.info(
                f"**Jogar em casa ajuda.** O anfitrião levou a taça em "
                f"{len(anfitriao)} das {len(c)} edições do período: {anos_txt}.",
                icon=":material/home:",
            )

        with cartao(titulo="Todas as edições"):
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
        with cartao(titulo="Média de gols por partida, por edição",
                    legenda="Uma medida, um eixo — escalas sobrepostas inventam correlação."):
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
            # Eixo sem título: o cabeçalho do cartão já diz o que é a medida.
            fig.update_yaxes(rangemode="tozero")
            area_gradiente(fig, SERIE[0])
            st.plotly_chart(estilo(fig, 400, legenda=False), width="stretch", config=PLOTLY)

        st.info(
            "**O futebol ficou menos goleador.** A média caiu de 5,38 (1954) para "
            "2,21 (1990) — queda de 59%. O total de gols subiu no mesmo período, mas "
            "apenas porque o torneio cresceu de 18 para 64 partidas. É por isso que as "
            "duas medidas ficam em gráficos separados: sobrepostas em eixos diferentes, "
            "inventariam uma correlação que não existe.",
            icon=":material/trending_down:",
        )

        with cartao(titulo="Volume do torneio por edição"):
            # Volume do torneio: duas contagens comparáveis, um eixo só.
            fig = go.Figure()
            for nome, col, cor in (("Gols", "GoalsScored", SERIE[0]),
                                   ("Partidas", "MatchesPlayed", SERIE[1])):
                fig.add_bar(x=c["Year"], y=c[col], name=nome, marker_color=cor,
                            hovertemplate="%{x}: %{y} " + nome.lower() + "<extra></extra>")
            fig.update_layout(barmode="group")
            st.plotly_chart(estilo(fig, 340), width="stretch", config=PLOTLY)

        e1, e2 = st.columns(2)
        with cartao(e1, "Público total por edição"):
            fig = px.bar(c, x="Year", y="Attendance",
                         labels={"Attendance": "Público", "Year": "Ano"})
            fig.update_traces(marker_color=SERIE[0],
                              hovertemplate="%{x}: %{y:,.0f} pessoas<extra></extra>")
            st.plotly_chart(estilo(fig, 360, legenda=False), width="stretch", config=PLOTLY)

        with cartao(e2, "Público médio por partida"):
            media_pub = m.groupby("Year")["Attendance"].mean().reset_index()
            fig = px.line(media_pub, x="Year", y="Attendance", markers=True,
                          labels={"Attendance": "Público médio", "Year": "Ano"})
            fig.update_traces(line=dict(color=SERIE[0], width=2),
                              marker=dict(size=7, color=SERIE[0]),
                              hovertemplate="%{x}: %{y:,.0f} por jogo<extra></extra>")
            area_gradiente(fig, SERIE[0])
            st.plotly_chart(estilo(fig, 360, legenda=False), width="stretch", config=PLOTLY)

# --------------------------------------------------------------------------- #
if aba_selecoes.open:
    with aba_selecoes:
        rank = tabela_selecoes(m, unif)
        topn = st.slider("Quantas seleções mostrar", 5, 40, min(15, len(rank)), key="topn")
        top = rank.head(topn)

        with cartao(titulo=f"Vitórias, empates e derrotas — top {topn}"):
            # Vitória/empate/derrota é polaridade -> divergente: dois polos opostos com
            # cinza neutro no meio. Azul/vermelho em vez do verde/vermelho convencional,
            # que os dois polos colapsam sob deuteranopia.
            fig = px.bar(
                top.melt(id_vars="Selecao", value_vars=["V", "E", "D"],
                         var_name="Resultado", value_name="Jogos"),
                x="Jogos", y="Selecao", color="Resultado", orientation="h",
                category_orders={"Selecao": list(top.sort_values("J")["Selecao"]),
                                 "Resultado": ["V", "E", "D"]},
                color_discrete_map={"V": POLO_POS, "E": NEUTRO, "D": POLO_NEG},
            )
            fig.update_traces(marker_line_width=2, marker_line_color=SUPERFICIE,
                              hovertemplate="%{y} · %{fullData.name}: %{x}<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, max(400, topn * 26)), width="stretch", config=PLOTLY)

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
        with cartao(s1, "Experiência × aproveitamento",
                    "Mínimo de 10 jogos. A bolha é o total de gols marcados."):
            # Saldo de gols tem zero natural -> escala divergente ancorada em 0.
            fig = px.scatter(
                rank[rank.J >= 10], x="J", y="Aprov%", size="GP", color="SG",
                hover_name="Selecao", color_continuous_scale=DIVERGENTE,
                color_continuous_midpoint=0, size_max=42,
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
            st.plotly_chart(estilo(fig, 470, legenda=False, grade="ambos"),
                            width="stretch", config=PLOTLY)

        with cartao(s2, "Ranking completo"):
            st.dataframe(
                rank[["Selecao", "J", "V", "E", "D", "GP", "GC", "SG", "Aprov%"]]
                .rename(columns={"Selecao": "Seleção"}),
                width="stretch", hide_index=True, height=430,
                column_config={"Aprov%": st.column_config.ProgressColumn(
                    "Aproveitamento", format="%.1f%%", min_value=0, max_value=100)},
            )

        with cartao(titulo="Confronto direto"):
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

        with cartao(p1, "Distribuição de gols por partida"):
            dist = m["TotalGols"].value_counts().sort_index().reset_index()
            dist.columns = ["Gols na partida", "Partidas"]
            fig = px.bar(dist, x="Gols na partida", y="Partidas", text="Partidas",
)
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{x} gols: %{y} partidas<extra></extra>")
            st.plotly_chart(estilo(fig, 380, legenda=False), width="stretch", config=PLOTLY)

        with cartao(p2, "Média de gols por fase", "Fases com pelo menos 5 jogos."):
            fase = m.groupby("Fase").agg(Jogos=("TotalGols", "size"),
                                         Media=("TotalGols", "mean")).reset_index()
            fase = fase[fase.Jogos >= 5].sort_values("Media")
            fig = px.bar(fase, x="Media", y="Fase", orientation="h",
                         text=fase["Media"].round(2),
                         labels={"Media": "Gols por jogo"})
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{y}: %{x:.2f} gols por jogo<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 380, legenda=False), width="stretch", config=PLOTLY)

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

        with cartao(r1, "Maiores goleadas"):
            st.dataframe(m.nlargest(10, "Saldo")[["Year", "Placar", "Saldo"]]
                         .rename(columns={"Year": "Ano"}), width="stretch",
                         hide_index=True, column_config=cfg_ano)
        with cartao(r2, "Mais gols numa partida"):
            st.dataframe(m.nlargest(10, "TotalGols")[["Year", "Placar", "TotalGols"]]
                         .rename(columns={"Year": "Ano", "TotalGols": "Gols"}),
                         width="stretch", hide_index=True, column_config=cfg_ano)
        with cartao(r3, "Maiores públicos"):
            st.dataframe(
                m.nlargest(10, "Attendance")[["Year", "Placar", "Attendance"]]
                .rename(columns={"Year": "Ano", "Attendance": "Público"}),
                width="stretch", hide_index=True,
                column_config={**cfg_ano,
                               "Público": st.column_config.NumberColumn(format="localized")},
            )

        with cartao(titulo="Estádios mais usados"):
            est = (m.groupby(["Stadium", "City"])
                   .agg(Jogos=("MatchID", "size"), PublicoMedio=("Attendance", "mean"))
                   .reset_index().nlargest(15, "Jogos"))
            fig = px.scatter(est, x="Jogos", y="PublicoMedio", size="Jogos",
                             hover_name="Stadium", text="Stadium",
                             labels={"PublicoMedio": "Público médio"})
            fig.update_traces(
                marker=dict(color=SERIE[0], line=dict(width=2, color=SUPERFICIE)),
                textposition="top center", textfont=dict(color=MUTED, size=11),
                hovertemplate="<b>%{hovertext}</b><br>%{x} jogos · %{y:,.0f} de média<extra></extra>")
            st.plotly_chart(estilo(fig, 450, legenda=False, grade="ambos"),
                            width="stretch", config=PLOTLY)

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

        with cartao(titulo="Top 20 artilheiros"):
            art = (ev.groupby("Player Name")[["Gols", "Penaltis", "TotalGols"]].sum()
                   .sort_values("TotalGols", ascending=False).head(20).reset_index())
            fig = px.bar(
                art.melt(id_vars="Player Name", value_vars=["Gols", "Penaltis"],
                         var_name="Tipo", value_name="Qtd"),
                x="Qtd", y="Player Name", color="Tipo", orientation="h",
                category_orders={"Player Name": list(art.sort_values("TotalGols")["Player Name"])},
                color_discrete_map={"Gols": SERIE[0], "Penaltis": SERIE[1]},
            )
            fig.update_traces(marker_line_width=2, marker_line_color=SUPERFICIE,
                              hovertemplate="%{y} · %{fullData.name}: %{x}<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 620), width="stretch", config=PLOTLY)

        g1, g2 = st.columns(2)
        with cartao(g1, "Cartões por edição",
                    "Registrados só a partir de 1970. Vermelhos incluem o segundo amarelo."):
            # Duas séries, não três: o segundo amarelo entra no vermelho (é o que ele é
            # em campo). Como três hues, amarelo e laranja ficavam a ΔE 13,6 — abaixo do
            # piso de 15 em que dois tons deixam de ser distinguíveis mesmo com visão normal.
            cartoes = ev.groupby("Year")[["Amarelos", "VermelhosDiretos", "SegundoAmarelo"]].sum()
            cartoes["Vermelhos"] = cartoes["VermelhosDiretos"] + cartoes["SegundoAmarelo"]
            cartoes = cartoes.reset_index()
            fig = px.area(cartoes, x="Year", y=["Amarelos", "Vermelhos"],
                          labels={"value": "Cartões", "Year": "Ano"},
                          color_discrete_map={"Amarelos": AMARELO, "Vermelhos": VERMELHO})
            fig.update_traces(line_width=2,
                              hovertemplate="%{x} · %{fullData.name}: %{y}<extra></extra>")
            st.plotly_chart(estilo(fig, 380), width="stretch", config=PLOTLY)

        with cartao(g2, "Técnicos com mais partidas"):
            tec = (p.drop_duplicates(subset=["MatchID", "Coach Name"])["Coach Name"]
                   .value_counts().head(15).reset_index())
            tec.columns = ["Técnico", "Jogos"]
            fig = px.bar(tec.sort_values("Jogos"), x="Jogos", y="Técnico",
                         orientation="h", text="Jogos")
            fig.update_traces(marker_color=SERIE[0], textfont_color=TINTA2,
                              textposition="outside", textangle=0, cliponaxis=False,
                              hovertemplate="%{y}: %{x} jogos<extra></extra>")
            fig.update_layout(yaxis_title=None)
            st.plotly_chart(estilo(fig, 380, legenda=False), width="stretch", config=PLOTLY)

        with cartao(titulo="Buscar jogador"):
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
