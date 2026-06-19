import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from io import StringIO
import re
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="AgroBasis · Curva do Dólar",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); color: #0f172a; }
    .block-container { padding: 0.9rem 2rem 2.0rem; max-width: 1450px; }
    #MainMenu, footer, header { visibility: hidden; }
    .stMetric { display: none; }
    div[data-testid="stDecoration"] { display:none; }
    .header-wrapper { display:flex; align-items:center; justify-content:space-between; background:#fff; border:1px solid #e2e8f0; border-radius:18px; padding:1.15rem 1.35rem; margin-bottom:1.1rem; box-shadow:0 10px 30px rgba(15,23,42,0.06); }
    .header-title { font-size:1.55rem; font-weight:800; letter-spacing:-0.6px; color:#0f172a; }
    .header-title span { color:#14532d; }
    .header-sub { margin-top:0.2rem; font-size:0.82rem; color:#64748b; font-weight:500; }
    .header-badge { font-family:'JetBrains Mono', monospace; font-size:0.72rem; background:#ecfdf5; border:1px solid #bbf7d0; padding:0.42rem 0.8rem; border-radius:999px; color:#166534; white-space:nowrap; }
    .kpi-card { background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:1.05rem 1.2rem; position:relative; overflow:hidden; box-shadow:0 10px 25px rgba(15,23,42,0.055); }
    .kpi-card::before { content:''; position:absolute; top:0; left:0; right:0; height:4px; }
    .kpi-card.green::before { background:linear-gradient(90deg,#14532d,#22c55e); }
    .kpi-card.blue::before { background:linear-gradient(90deg,#0f766e,#38bdf8); }
    .kpi-card.gold::before { background:linear-gradient(90deg,#d97706,#f59e0b); }
    .kpi-card.gray::before { background:linear-gradient(90deg,#475569,#94a3b8); }
    .kpi-label { font-size:0.68rem; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#64748b; margin-bottom:0.45rem; }
    .kpi-value { font-family:'JetBrains Mono', monospace; font-size:1.65rem; font-weight:700; color:#0f172a; line-height:1; }
    .kpi-sub { font-family:'JetBrains Mono', monospace; font-size:0.76rem; margin-top:0.42rem; color:#64748b; }
    .positive { color:#15803d !important; } .negative { color:#dc2626 !important; } .neutral { color:#64748b !important; }
    .panel { background:#fff; border:1px solid #e2e8f0; border-radius:18px; padding:1rem 1.15rem; box-shadow:0 10px 30px rgba(15,23,42,0.055); margin-top:1rem; }
    .section-title { font-size:0.74rem; font-weight:800; letter-spacing:1.4px; text-transform:uppercase; color:#14532d; margin:0.4rem 0 0.85rem; }
    .small-note { font-size:0.76rem; color:#64748b; margin-top:-0.35rem; margin-bottom:0.65rem; }
    .source-pill { display:inline-block; font-size:0.72rem; font-weight:700; color:#166534; background:#ecfdf5; border:1px solid #bbf7d0; border-radius:999px; padding:0.3rem 0.65rem; margin-right:0.35rem; margin-bottom:0.35rem; }
    .warn-pill { display:inline-block; font-size:0.72rem; font-weight:700; color:#92400e; background:#fffbeb; border:1px solid #fde68a; border-radius:999px; padding:0.3rem 0.65rem; margin-right:0.35rem; margin-bottom:0.35rem; }
    .stSlider label, .stNumberInput label, .stCheckbox label { color:#334155 !important; font-weight:700 !important; }
    .footer-box { margin-top:1.3rem; padding:0.9rem 1rem; border:1px solid #e2e8f0; border-radius:14px; background:#fff; font-size:0.74rem; color:#64748b; text-align:center; box-shadow:0 8px 20px rgba(15,23,42,0.04); }
</style>
""", unsafe_allow_html=True)

MONTH_CODES = {1:'F',2:'G',3:'H',4:'J',5:'K',6:'M',7:'N',8:'Q',9:'U',10:'V',11:'X',12:'Z'}
MESES_ABREV = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
CODE_TO_MONTH = {v:k for k,v in MONTH_CODES.items()}

@st.cache_data(ttl=900)
def fetch_cotacao_atual():
    try:
        r = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=8)
        r.raise_for_status()
        d = r.json()["USDBRL"]
        return {"bid":float(d["bid"]), "ask":float(d["ask"]), "high":float(d["high"]), "low":float(d["low"]), "pctchg":float(d["pctChange"]), "ts":datetime.fromtimestamp(int(d["timestamp"]))}
    except Exception as e:
        st.warning(f"Cotação em tempo real indisponível: {e}")
        return None

@st.cache_data(ttl=900)
def fetch_historico_resumo(dias:int=35):
    try:
        r = requests.get(f"https://economia.awesomeapi.com.br/json/daily/USD-BRL/{dias}", timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        df["data"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
        df["close"] = df["bid"].astype(float)
        return df[["data","close"]].sort_values("data").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

def gerar_datas_mensais(data_base: datetime, meses_proj: int) -> pd.DatetimeIndex:
    inicio_mes = pd.Timestamp(data_base).replace(day=1).normalize()
    return pd.date_range(start=inicio_mes, periods=meses_proj + 1, freq="BME")

def parse_float_br(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(".", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return np.nan

def vencimento_di1_para_data(venc):
    """Converte F27, JAN27 ou 202701 em data aproximada de vencimento: primeiro dia útil do mês."""
    s = str(venc).upper().strip()
    s = re.sub(r"[^A-Z0-9]", "", s)
    month_map_pt = {"JAN":1,"FEV":2,"MAR":3,"ABR":4,"MAI":5,"JUN":6,"JUL":7,"AGO":8,"SET":9,"OUT":10,"NOV":11,"DEZ":12}
    if re.match(r"^[FGHJKMNQUVXZ]\d{2}$", s):
        m = CODE_TO_MONTH[s[0]]
        y = 2000 + int(s[1:])
    elif re.match(r"^[A-Z]{3}\d{2,4}$", s):
        m = month_map_pt.get(s[:3])
        yy = int(s[3:])
        y = yy if yy > 100 else 2000 + yy
    elif re.match(r"^\d{6}$", s):
        y = int(s[:4]); m = int(s[4:6])
    else:
        return pd.NaT
    if not m:
        return pd.NaT
    return pd.bdate_range(pd.Timestamp(y, m, 1), periods=1)[0]

@st.cache_data(ttl=3600)
def fetch_di1_b3_ajustes(max_tentativas:int=7):
    """
    Tenta capturar DI1 no 'Sistema Pregão' da B3.
    A página pode mudar/bloquear; por isso há fallback manual no dashboard.
    Retorna taxas anuais implícitas estimadas a partir do PU de ajuste quando disponível.
    """
    hoje = datetime.now()
    headers = {"User-Agent":"Mozilla/5.0"}
    last_error = ""
    for i in range(max_tentativas):
        dia = hoje - timedelta(days=i)
        if dia.weekday() >= 5:
            continue
        data_str = dia.strftime("%d/%m/%Y")
        url = "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-sistema-pregao-ptBR.asp"
        try:
            resp = requests.get(url, params={"Data":data_str, "Mercadoria":"DI1"}, headers=headers, timeout=15)
            resp.raise_for_status()
            html = resp.text.replace("\xa0", " ")
            tables = pd.read_html(StringIO(html), decimal=",", thousands=".")
            candidatos = []
            for t in tables:
                cols_norm = [str(c).upper() for c in t.columns]
                if any("VEN" in c or "VCT" in c for c in cols_norm) and any("AJUST" in c or "PRE" in c for c in cols_norm):
                    candidatos.append(t)
            if not candidatos:
                last_error = f"Sem tabela DI1 em {data_str}"
                continue
            df = max(candidatos, key=len).copy()
            df.columns = [str(c).strip() for c in df.columns]
            ven_col = next((c for c in df.columns if "VEN" in c.upper() or "VCT" in c.upper()), df.columns[0])
            ajuste_cols = [c for c in df.columns if "AJUST" in c.upper() or "PREÇO" in c.upper() or "PRECO" in c.upper()]
            ajuste_col = ajuste_cols[-1] if ajuste_cols else df.columns[-1]
            out = df[[ven_col, ajuste_col]].rename(columns={ven_col:"Contrato", ajuste_col:"Ajuste"})
            out["vencimento"] = out["Contrato"].apply(vencimento_di1_para_data)
            out["pu"] = out["Ajuste"].apply(parse_float_br)
            out = out.dropna(subset=["vencimento", "pu"])
            out = out[out["vencimento"] > pd.Timestamp(dia)]
            # Se a coluna vier em taxa direta, usa como taxa; se vier PU, converte. DI1 normalmente vem como PU de ajuste.
            du = np.array([len(pd.bdate_range(pd.Timestamp(dia).normalize(), v)) for v in out["vencimento"]], dtype=float)
            out["du"] = du
            taxa_pu = ((100000 / out["pu"]) ** (252 / out["du"]) - 1) * 100
            taxa_direta = out["pu"]
            out["taxa_br"] = np.where((out["pu"] > 100) & (out["pu"] < 40_000), taxa_direta, taxa_pu)
            out = out[(out["taxa_br"] > 0) & (out["taxa_br"] < 35)]
            out = out.sort_values("vencimento")[["vencimento", "taxa_br", "Contrato"]].reset_index(drop=True)
            if len(out) >= 2:
                out.attrs["fonte"] = f"B3 DI1 · Ajustes {data_str}"
                return out, None
            last_error = f"Poucos contratos válidos em {data_str}"
        except Exception as e:
            last_error = str(e)
            continue
    return pd.DataFrame(), last_error or "Não foi possível carregar DI1 B3"


@st.cache_data(ttl=900)
def fetch_di1_advfn():
    """
    Fonte alternativa para DI Futuro via ADVFN.
    Página: https://br.advfn.com/investimentos/futuros/di-depositos-interfinanceiros/cotacoes

    A página normalmente publica linhas como:
    BMF:DI1N26 Julho 2026 14,153 -0,082 14,157 14,151 378.473
    O parser abaixo lê o HTML/texto e extrai: contrato, mês/ano e último preço/taxa.
    """
    url = "https://br.advfn.com/investimentos/futuros/di-depositos-interfinanceiros/cotacoes"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        html = r.text.replace("\xa0", " ")
        texto = re.sub(r"<[^>]+>", " ", html)
        texto = re.sub(r"\s+", " ", texto)

        meses_pt = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Marco": 3, "Abril": 4,
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, "Setembro": 9,
            "Outubro": 10, "Novembro": 11, "Dezembro": 12,
        }
        mes_regex = "|".join(meses_pt.keys())
        # Captura contrato, mês, ano e ULT. O valor VAB pode vir colado ao ULT, ex: 14,153-0,082.
        pattern = re.compile(
            rf"BMF:(DI1[FGHJKMNQUVXZ]\d{{2}})\s+({mes_regex})\s+(20\d{{2}})\s+([0-9]+,[0-9]+)",
            flags=re.IGNORECASE,
        )
        rows = []
        for m in pattern.finditer(texto):
            contrato = m.group(1).upper()
            mes_nome = m.group(2).capitalize()
            ano = int(m.group(3))
            taxa = parse_float_br(m.group(4))
            mes = meses_pt.get(mes_nome) or meses_pt.get(m.group(2))
            if mes and taxa and 0 < taxa < 35:
                venc = pd.bdate_range(pd.Timestamp(ano, mes, 1), periods=1)[0]
                rows.append({"vencimento": venc, "taxa_br": taxa, "Contrato": contrato})

        df = pd.DataFrame(rows).drop_duplicates(subset=["Contrato"]).sort_values("vencimento").reset_index(drop=True)
        df = df[df["vencimento"] >= pd.Timestamp(datetime.now().date())]
        if len(df) >= 2:
            df.attrs["fonte"] = "ADVFN · DI Futuro"
            return df, None
        return pd.DataFrame(), "ADVFN não retornou contratos DI suficientes"
    except Exception as e:
        return pd.DataFrame(), str(e)

def yahoo_chart_price(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    try:
        r = requests.get(url, params={"range":"5d", "interval":"1d"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return np.nan
        j = r.json()
        result = j.get("chart", {}).get("result")
        if not result:
            return np.nan
        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [x for x in closes if x is not None]
        return float(closes[-1]) if closes else np.nan
    except Exception:
        return np.nan

@st.cache_data(ttl=3600)
def fetch_fed_funds_yahoo(data_base_str:str, meses_proj:int):
    """
    Proxy automático para juros EUA via 30-Day Fed Funds Futures (Yahoo Finance quando disponível).
    Preço do contrato ≈ 100 - taxa implícita.
    Tickers tentados: ZQ{código}{ano}.CBT e ZQ{código}{ano}.CME.
    Se falhar, o dashboard usa curva manual/editável.
    """
    base = pd.Timestamp(data_base_str)
    datas = gerar_datas_mensais(base, meses_proj)
    rows = []
    for d in datas:
        code = MONTH_CODES[d.month]
        yy = str(d.year)[-2:]
        tickers = [f"ZQ{code}{yy}.CBT", f"ZQ{code}{yy}.CME"]
        price = np.nan; used = None
        for tk in tickers:
            price = yahoo_chart_price(tk)
            if not np.isnan(price):
                used = tk; break
        if not np.isnan(price):
            taxa = 100 - price
            if 0 <= taxa <= 15:
                rows.append({"vencimento": d, "taxa_eua": taxa, "Contrato": used})
    df = pd.DataFrame(rows)
    if len(df) >= 2:
        df.attrs["fonte"] = "Yahoo Finance · Fed Funds Futures (ZQ)"
        return df, None
    return pd.DataFrame(), "Fed Funds Futures não disponível via Yahoo neste momento"

def curva_manual_default(datas_mensais):
    n = len(datas_mensais)
    br_curve = np.linspace(13.75, 11.00, n)
    us_curve = np.linspace(5.25, 4.00, n)
    return pd.DataFrame({"Referência": [f"{MESES_ABREV[int(d.month)]}/{str(int(d.year))[-2:]}" for d in datas_mensais], "Data": datas_mensais.strftime("%d/%m/%Y"), "Juros BR implícito (% a.a.)":np.round(br_curve,2), "Juros EUA implícito (% a.a.)":np.round(us_curve,2)})

def montar_curva_base(datas_mensais, auto_br=True, auto_us=True):
    default = curva_manual_default(datas_mensais)
    fontes = []
    avisos = []
    br_auto = pd.DataFrame(); us_auto = pd.DataFrame()
    if auto_br:
        # 1ª tentativa: B3. 2ª tentativa: ADVFN. Se ambas falharem, fica manual/editável.
        br_auto, err_b3 = fetch_di1_b3_ajustes()
        fonte_br = "B3 DI1"
        if br_auto.empty:
            br_auto, err_advfn = fetch_di1_advfn()
            fonte_br = "ADVFN · DI Futuro"
        else:
            err_advfn = None

        if not br_auto.empty:
            x = pd.to_datetime(br_auto["vencimento"]).map(pd.Timestamp.toordinal).values
            y = br_auto["taxa_br"].astype(float).values
            xi = pd.Series(datas_mensais).map(pd.Timestamp.toordinal).values
            default["Juros BR implícito (% a.a.)"] = np.round(np.interp(xi, x, y, left=y[0], right=y[-1]), 2)
            fontes.append(br_auto.attrs.get("fonte", fonte_br))
        else:
            avisos.append(f"DI Brasil em fallback manual. B3: {err_b3}; ADVFN: {err_advfn}")
    if auto_us:
        us_auto, err = fetch_fed_funds_yahoo(str(datas_mensais[0].date()), len(datas_mensais)-1)
        if not us_auto.empty:
            x = pd.to_datetime(us_auto["vencimento"]).map(pd.Timestamp.toordinal).values
            y = us_auto["taxa_eua"].astype(float).values
            xi = pd.Series(datas_mensais).map(pd.Timestamp.toordinal).values
            default["Juros EUA implícito (% a.a.)"] = np.round(np.interp(xi, x, y, left=y[0], right=y[-1]), 2)
            fontes.append(us_auto.attrs.get("fonte", "Fed Funds Futures"))
        else:
            avisos.append(f"EUA em fallback manual: {err}")
    return default, fontes, avisos, br_auto, us_auto

def preparar_curva_juros(curva_editada, datas_mensais):
    df = curva_editada.copy()
    for col in ["Juros BR implícito (% a.a.)", "Juros EUA implícito (% a.a.)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").ffill().bfill()
    df["data"] = datas_mensais
    return df

def contar_dias_uteis(data_inicio, datas):
    """Conta dias úteis entre data_inicio e cada data alvo, excluindo a data base."""
    base = pd.Timestamp(data_inicio).normalize()
    out = []
    for d in pd.to_datetime(datas):
        d = pd.Timestamp(d).normalize()
        if d <= base:
            out.append(0)
        else:
            # bdate_range inclui as duas pontas; removemos a data base.
            out.append(max(len(pd.bdate_range(base, d)) - 1, 0))
    return np.array(out, dtype=float)


def calcular_dolar_teorico_curva(spot, du, juros_br_pct, juros_eua_pct):
    """
    Cálculo por dias úteis.
    t = DU / 252 para as duas curvas, mantendo a leitura simples do dashboard.
    """
    t = np.maximum(du, 0) / 252.0
    br = juros_br_pct / 100.0
    us = juros_eua_pct / 100.0
    return spot * ((1 + br) ** t) / ((1 + us) ** t)


def calcular_curva_diaria_e_mensal(spot, curva_juros, meses_proj, data_base):
    base = pd.Timestamp(data_base).normalize()
    datas_mensais = gerar_datas_mensais(base, meses_proj)
    data_final = datas_mensais[-1]

    # A linha usa apenas dias úteis para evitar quebras visuais nos fins de semana.
    # O hover continua disponível em cada dia útil da curva.
    datas_diarias = pd.bdate_range(start=base, end=data_final)
    du_diarios = contar_dias_uteis(base, datas_diarias)
    du_mensais = contar_dias_uteis(base, datas_mensais)

    br_m = curva_juros["Juros BR implícito (% a.a.)"].astype(float).values
    us_m = curva_juros["Juros EUA implícito (% a.a.)"].astype(float).values

    du_ref = np.array(du_mensais, dtype=float)
    br_ref = br_m.astype(float)
    us_ref = us_m.astype(float)

    if du_ref[0] > 0:
        du_ref = np.insert(du_ref, 0, 0.0)
        br_ref = np.insert(br_ref, 0, br_ref[0])
        us_ref = np.insert(us_ref, 0, us_ref[0])

    br_diario = np.interp(du_diarios, du_ref, br_ref)
    us_diario = np.interp(du_diarios, du_ref, us_ref)

    ndf_diario = calcular_dolar_teorico_curva(spot, du_diarios, br_diario, us_diario)
    ndf_upper = calcular_dolar_teorico_curva(spot, du_diarios, br_diario + 0.25, us_diario)
    ndf_lower = calcular_dolar_teorico_curva(spot, du_diarios, br_diario - 0.25, us_diario)

    curva_diaria = pd.DataFrame({
        "data": datas_diarias,
        "du": du_diarios,
        "juros_br": br_diario,
        "juros_eua": us_diario,
        "diferencial": br_diario - us_diario,
        "ndf": ndf_diario,
        "ndf_upper": ndf_upper,
        "ndf_lower": ndf_lower,
    })
    curva_diaria["var_pct"] = ((curva_diaria["ndf"] / spot) - 1) * 100
    curva_diaria["data_fmt"] = curva_diaria["data"].dt.strftime("%d/%m/%Y")

    mensal = curva_diaria[curva_diaria["data"].isin(datas_mensais)].copy()
    mensal["referencia"] = mensal["data"].apply(lambda d: f"{MESES_ABREV[int(d.month)]}/{str(int(d.year))[-2:]}")
    mensal["meses_a_frente"] = range(len(mensal))
    return curva_diaria, mensal

def build_curve_chart(curva_diaria, mensal, spot):
    fig = go.Figure()

    # Curva principal. A banda de sensibilidade foi removida para deixar o gráfico
    # mais limpo e mais apropriado para compartilhamento em redes sociais.
    fig.add_trace(go.Scatter(
        x=curva_diaria["data"],
        y=curva_diaria["ndf"],
        mode="lines",
        line=dict(color="#14532d", width=3.2),
        name="Curva teórica diária",
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Dólar teórico: R$ %{y:.4f}<br>"
            "Dias úteis: %{customdata[5]:.0f}<br>"
            "Juros BR: %{customdata[1]:.2f}% a.a.<br>"
            "Juros EUA: %{customdata[2]:.2f}% a.a.<br>"
            "Diferencial: %{customdata[3]:+.2f} p.p.<br>"
            "Variação vs spot: %{customdata[4]:+.2f}%"
            "<extra></extra>"
        ),
        customdata=np.stack([
            curva_diaria["data_fmt"],
            curva_diaria["juros_br"],
            curva_diaria["juros_eua"],
            curva_diaria["diferencial"],
            curva_diaria["var_pct"],
            curva_diaria["du"],
        ], axis=-1)
    ))

    mensal = mensal.copy()

    # Rótulos mensais:
    # - até 12 meses: mostra todos os pontos abaixo da curva, como referência direta para print/compartilhamento;
    # - acima de 12 meses: mantém rótulos alternados e o último ponto para evitar excesso visual.
    labels = []
    posicoes = []
    for i, r in mensal.iterrows():
        idx = int(r["meses_a_frente"]) if "meses_a_frente" in mensal.columns else i
        deve_rotular = (idx <= 12) or (idx % 2 == 0) or (i == len(mensal) - 1)
        if deve_rotular:
            labels.append(f"{r['referencia']}<br>R$ {r['ndf']:.2f}".replace('.', ','))
            posicoes.append("bottom center")
        else:
            labels.append("")
            posicoes.append("middle center")
    mensal["label_ponto"] = labels

    fig.add_trace(go.Scatter(
        x=mensal["data"],
        y=mensal["ndf"],
        mode="markers+text",
        text=mensal["label_ponto"],
        textposition=posicoes,
        textfont=dict(color="#0f172a", size=10, family="Inter, sans-serif"),
        marker=dict(size=10.5, color="#d97706", line=dict(width=2.4, color="#ffffff")),
        name="Último dia útil do mês",
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Data ref.: %{x|%d/%m/%Y}<br>"
            "Dólar teórico: R$ %{y:.4f}<br>"
            "Dias úteis: %{customdata[4]:.0f}<br>"
            "Juros BR: %{customdata[1]:.2f}% a.a.<br>"
            "Juros EUA: %{customdata[2]:.2f}% a.a.<br>"
            "Variação vs spot: %{customdata[3]:+.2f}%"
            "<extra></extra>"
        ),
        customdata=np.stack([
            mensal["referencia"],
            mensal["juros_br"],
            mensal["juros_eua"],
            mensal["var_pct"],
            mensal["du"],
        ], axis=-1)
    ))

    # Linha do spot atual, com box destacado no canto direito.
    fig.add_hline(
        y=spot,
        line_color="#0f766e",
        line_width=1.25,
        line_dash="dot"
    )

    fig.add_annotation(
        xref="paper",
        yref="y",
        x=0.995,
        y=spot,
        text=f"USD/BRL Spot<br><b>R$ {spot:.4f}</b>",
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
        font=dict(size=12, color="#0f766e"),
        bgcolor="rgba(255,255,255,0.96)",
        bordercolor="rgba(15,118,110,0.30)",
        borderwidth=1,
        borderpad=6
    )

    # Título discreto centralizado acima da área principal do gráfico.
    # Assim a imagem exportada fica autoexplicativa sem competir com a curva.
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.50,
        y=1.10,
        text="<b>Curva Projetada USD/BRL</b>",
        showarrow=False,
        xanchor="center",
        yanchor="top",
        align="center",
        font=dict(size=18, color="#0f172a"),
        bgcolor="rgba(255,255,255,0)",
        borderwidth=0,
        borderpad=0
    )

    # Destaque do insight principal: carrego acumulado em 12 meses.
    # Posicionado no canto superior direito para ficar mais equilibrado e profissional.
    idx_12m = min(12, len(mensal) - 1)
    ref_12m = mensal.iloc[idx_12m]
    carrego_12m = ((ref_12m["ndf"] / spot) - 1) * 100
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.985,
        y=1.055,
        text=(
            f"<span style='font-size:24px'><b>{carrego_12m:+.2f}%</b></span><br>"
            f"<span style='font-size:11px;color:#64748b'>Carrego 12 meses</span><br>"
            f"<span style='font-size:13px;color:#334155'>USD/BRL: <b>R$ {ref_12m['ndf']:.2f}</b></span>"
        ).replace('.', ','),
        showarrow=False,
        xanchor="right",
        yanchor="top",
        align="right",
        font=dict(size=13, color="#14532d"),
        bgcolor="rgba(248,250,252,0.96)",
        bordercolor="rgba(20,83,45,0.24)",
        borderwidth=1,
        borderpad=9
    )

    fig.add_annotation(
        text="AgroBasis",
        xref="paper", yref="paper",
        x=0.50, y=0.54,
        showarrow=False,
        font=dict(size=76, color="rgba(15,23,42,0.04)"),
        xanchor="center", yanchor="middle"
    )

    # Escala mais aberta para evitar inclinação visual exagerada.
    y_min = min(float(curva_diaria["ndf"].min()), float(spot))
    y_max = max(float(curva_diaria["ndf"].max()), float(spot))
    amplitude = max(y_max - y_min, 0.15)
    padding = amplitude * 0.22
    y_range = [y_min - padding, y_max + padding]

    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#0f172a", size=12),
        margin=dict(l=26, r=26, t=94, b=88),
        height=760,
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.045,
            xanchor="left", x=0,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=12, color="#0f172a")
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="rgba(100,116,139,0.55)",
            linewidth=1,
            tickfont=dict(size=11, color="#0f172a"),
            tickmode="array",
            tickvals=list(mensal["data"]),
            ticktext=list(mensal["referencia"]),
            rangebreaks=[dict(bounds=["sat", "mon"])],
            title=dict(text="Referência: último dia útil de cada mês", font=dict(size=12, color="#1e293b"))
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(148,163,184,0.18)",
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor="rgba(100,116,139,0.55)",
            linewidth=1,
            tickfont=dict(size=12, color="#0f172a"),
            tickprefix="R$ ",
            tickformat=".2f",
            range=y_range
        )
    )
    return fig

def main():
    now_str = datetime.now().strftime("%d/%m/%Y  %H:%M")

    st.markdown(f"""
    <div class="header-wrapper">
        <div>
            <div class="header-title">💵 USD / <span>BRL</span> · Curva do Dólar</div>
        </div>
        <div class="header-badge">Atualizado às {now_str} · cache 15min/1h</div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Buscando dólar e curvas de juros..."):
        cotacao = fetch_cotacao_atual()
        hist_resumo = fetch_historico_resumo(35)

    if cotacao:
        spot = cotacao["bid"]
    elif not hist_resumo.empty:
        spot = hist_resumo["close"].iloc[-1]
    else:
        st.error("Não foi possível carregar a cotação do dólar.")
        st.stop()

    pct = cotacao["pctchg"] if cotacao else 0
    hi = cotacao["high"] if cotacao else spot
    lo = cotacao["low"] if cotacao else spot
    pct_cls = "positive" if pct >= 0 else "negative"
    pct_fmt = f"{'▲' if pct >= 0 else '▼'} {abs(pct):.2f}% hoje"
    med_30d = hist_resumo["close"].tail(30).mean() if not hist_resumo.empty else spot
    dist = ((spot / med_30d) - 1) * 100 if med_30d else 0
    dist_cls = "positive" if dist >= 0 else "negative"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"<div class='kpi-card green'><div class='kpi-label'>Cotação atual BID</div><div class='kpi-value'>R$ {spot:.4f}</div><div class='kpi-sub {pct_cls}'>{pct_fmt}</div></div>", unsafe_allow_html=True)
    with k2:
        st.markdown(f"<div class='kpi-card blue'><div class='kpi-label'>Máxima / mínima do dia</div><div class='kpi-value' style='font-size:1.22rem'>R$ {hi:.4f}</div><div class='kpi-sub negative'>Mín R$ {lo:.4f}</div></div>", unsafe_allow_html=True)
    with k3:
        st.markdown(f"<div class='kpi-card gold'><div class='kpi-label'>Média móvel 30d</div><div class='kpi-value' style='font-size:1.35rem'>R$ {med_30d:.4f}</div><div class='kpi-sub {dist_cls}'>{'▲' if dist >= 0 else '▼'} {abs(dist):.2f}% da média</div></div>", unsafe_allow_html=True)
    with k4:
        ts = cotacao["ts"].strftime("%d/%m %H:%M") if cotacao else now_str
        st.markdown(f"<div class='kpi-card gray'><div class='kpi-label'>Fonte dólar</div><div class='kpi-value' style='font-size:1.15rem'>AwesomeAPI</div><div class='kpi-sub neutral'>Cotação: {ts}</div></div>", unsafe_allow_html=True)

    # Parâmetros mínimos antes do gráfico para evitar rolagem excessiva.
    c0, c1, c2, c3 = st.columns([1, 1, 1, 3])
    with c0:
        meses_proj = st.slider("Projeção (meses)", 3, 24, 12, 1)
    with c1:
        auto_br = st.checkbox("DI automático", value=True)
    with c2:
        auto_us = st.checkbox("EUA automático", value=True)

    data_base = cotacao["ts"] if cotacao else datetime.now()
    datas_mensais = gerar_datas_mensais(data_base, meses_proj)

    with st.spinner("Montando curva de juros..."):
        curva_default, fontes, avisos, br_auto, us_auto = montar_curva_base(datas_mensais, auto_br=auto_br, auto_us=auto_us)

    with c3:
        if fontes:
            st.markdown("".join([f"<span class='source-pill'>{f}</span>" for f in fontes]), unsafe_allow_html=True)
        if avisos:
            st.markdown("".join([f"<span class='warn-pill'>{a}</span>" for a in avisos]), unsafe_allow_html=True)

    # O cálculo inicial usa a curva automática/default. A tabela editável fica abaixo do gráfico.
    curva_juros = preparar_curva_juros(curva_default, datas_mensais)
    curva_diaria, mensal = calcular_curva_diaria_e_mensal(spot, curva_juros, meses_proj, data_base)

    idx_12m = min(12, len(mensal) - 1)
    dolar_12m = mensal.iloc[idx_12m]["ndf"]
    carrego_12m = ((dolar_12m / spot) - 1) * 100
    br_12m = mensal.iloc[idx_12m]["juros_br"]
    us_12m = mensal.iloc[idx_12m]["juros_eua"]

    # Gráfico logo após as cotações e KPIs.
    st.markdown('<div class="panel" style="margin-top:0.85rem;">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 Curva Projetada do Dólar</div>', unsafe_allow_html=True)
    st.markdown('<div class="small-note">Cálculo por dias úteis: DU/252. Pontos mensais exibem a cotação teórica no último dia útil de cada mês.</div>', unsafe_allow_html=True)
    fig = build_curve_chart(curva_diaria, mensal, spot)
    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
        "displaylogo": False,
        "locale": "pt-BR",
        "toImageButtonOptions": {
            "format": "png",
            "filename": "curva_dolar_agrobasis",
            "height": 900,
            "width": 1600,
            "scale": 2
        }
    })
    st.markdown('</div>', unsafe_allow_html=True)

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(f"<div class='kpi-card green' style='margin-top:0.6rem;'><div class='kpi-label'>Juros BR 12m</div><div class='kpi-value' style='font-size:1.25rem'>{br_12m:.2f}%</div></div>", unsafe_allow_html=True)
    with p2:
        st.markdown(f"<div class='kpi-card blue' style='margin-top:0.6rem;'><div class='kpi-label'>Juros EUA 12m</div><div class='kpi-value' style='font-size:1.25rem'>{us_12m:.2f}%</div></div>", unsafe_allow_html=True)
    with p3:
        st.markdown(f"<div class='kpi-card gold' style='margin-top:0.6rem;'><div class='kpi-label'>Diferencial 12m</div><div class='kpi-value' style='font-size:1.25rem'>{br_12m-us_12m:+.2f} p.p.</div><div class='kpi-sub neutral'>Curva usada</div></div>", unsafe_allow_html=True)
    with p4:
        st.markdown(f"<div class='kpi-card gray' style='margin-top:0.6rem;'><div class='kpi-label'>Dólar 12 meses</div><div class='kpi-value' style='font-size:1.25rem'>R$ {dolar_12m:.4f}</div><div class='kpi-sub {'positive' if carrego_12m>=0 else 'negative'}'>{carrego_12m:+.2f}% vs spot</div></div>", unsafe_allow_html=True)



    with st.expander("⚙️ Ver / editar curva de juros usada no cálculo"):
        curva_editada = st.data_editor(
            curva_default,
            use_container_width=True,
            hide_index=True,
            disabled=["Referência", "Data"],
            key="curva_juros_editor_auto",
            column_config={
                "Juros BR implícito (% a.a.)": st.column_config.NumberColumn("Juros BR implícito (% a.a.)", min_value=0.0, max_value=30.0, step=0.05, format="%.2f"),
                "Juros EUA implícito (% a.a.)": st.column_config.NumberColumn("Juros EUA implícito (% a.a.)", min_value=0.0, max_value=15.0, step=0.05, format="%.2f"),
            },
        )
        st.caption("Se você editar a tabela, clique em 'Rerun' no Streamlit ou altere qualquer parâmetro para recalcular a curva com os novos valores.")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Referências mensais</div>', unsafe_allow_html=True)
    tabela = mensal.copy()
    tabela["Referência"] = tabela["referencia"]
    tabela["Data"] = tabela["data"].dt.strftime("%d/%m/%Y")
    tabela["DU"] = tabela["du"].astype(int)
    tabela["Juros BR"] = tabela["juros_br"].map(lambda x: f"{x:.2f}%")
    tabela["Juros EUA"] = tabela["juros_eua"].map(lambda x: f"{x:.2f}%")
    tabela["Diferencial"] = tabela["diferencial"].map(lambda x: f"{x:+.2f} p.p.")
    tabela["Dólar Teórico"] = tabela["ndf"].map(lambda x: f"R$ {x:.4f}")
    tabela["Var. vs Spot"] = tabela["var_pct"].map(lambda x: f"{'▲' if x>=0 else '▼'} {abs(x):.2f}%")
    tabela["Sensib. Sup."] = tabela["ndf_upper"].map(lambda x: f"R$ {x:.4f}")
    tabela["Sensib. Inf."] = tabela["ndf_lower"].map(lambda x: f"R$ {x:.4f}")
    st.dataframe(tabela[["Referência", "Data", "DU", "Juros BR", "Juros EUA", "Diferencial", "Dólar Teórico", "Var. vs Spot", "Sensib. Sup.", "Sensib. Inf."]], use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("ℹ️ Metodologia, fontes e fallback"):
        st.markdown(f"""
**Fórmula base**

```
Dólar teórico(t) = Spot × (1 + Juros BR(t))^(DU/252) ÷ (1 + Juros EUA(t))^(DU/252)
```

- O cálculo usa dias úteis, com base DU/252.
- A curva BR tenta usar DI1 da B3; se falhar, tenta ADVFN; depois interpola para as referências mensais.
- A curva EUA tenta usar Fed Funds Futures via Yahoo Finance como proxy automático.
- Se alguma fonte falhar, o dashboard mantém uma curva editável.

**Fonte dólar:** AwesomeAPI.  
**Fontes juros usadas nesta execução:** {', '.join(fontes) if fontes else 'fallback manual/editável'}.

> ⚠️ Este dashboard é informativo e educacional. A curva apresentada é teórica e não representa recomendação, previsão de mercado nem preço negociável de NDF ou contrato futuro.
        """)

    st.markdown(f"<div class='footer-box'>AgroBasis · Curva Teórica USD/BRL · Cálculo por dias úteis · DI B3/ADVFN / Fed Funds proxy · Cache 15min/1h · {now_str}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
