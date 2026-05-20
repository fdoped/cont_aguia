"""
Controladoria — DRE e Balanço Patrimonial Moderno
Sistema de árvore contábil interativa com auto-resize do iframe (sem corte).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import glob
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL CLEAN
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Controladoria Executiva",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Syne:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; background-color: #faf9f7; }

.block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }

/* Força os iframes das tabelas a ocuparem a largura total da coluna sem quebrar */
iframe {
    width: 100% !important;
    min-width: 100% !important;
}

.main-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem; font-weight: 400;
    color: #0f0e0d; letter-spacing: -.5px; margin-bottom: 2px;
}
.main-sub { color: #7a7873; font-size: .85rem; margin-bottom: 1.5rem; }

.kpi-card {
    background: #ffffff; border: 0.5px solid #e8e5e0;
    border-radius: 12px; padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,.03); margin-bottom: 4px;
}
.kpi-label { font-size:.68rem; font-weight:700; letter-spacing:.7px;
    text-transform:uppercase; color:#7a7873; margin-bottom:4px; }
.kpi-value { font-family:'DM Mono',monospace; font-size:1.25rem; font-weight:500; }
.kpi-sub   { font-size:.75rem; color:#7a7873; margin-top:3px; }
.kpi-pos   { color:#1e6b3e; }
.kpi-neg   { color:#c0392b; }
.kpi-neu   { color:#0f0e0d; }

.result-banner { border-radius:12px; padding:16px 20px; margin-bottom:18px;
    display:flex; align-items:center; gap:14px; }
.result-lucro    { background:#edf7f1; border:0.5px solid #52b788; }
.result-prejuizo { background:#fdf0ee; border:0.5px solid #e57373; }
.result-label { font-size:.7rem; font-weight:700; letter-spacing:.7px; text-transform:uppercase; }
.result-value { font-family:'DM Mono',monospace; font-size:1.4rem; font-weight:500; }
.label-lucro    { color:#1e6b3e; }
.label-prejuizo { color:#c0392b; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# FUNÇÕES DE TRATAMENTO DE DADOS
# ─────────────────────────────────────────────────────────
def to_float(s) -> float:
    if pd.isna(s) or str(s).strip() == "": return 0.0
    if isinstance(s, (int, float)): return float(s)
    s_str = str(s).strip()
    if "," in s_str: s_str = s_str.replace(".", "").replace(",", ".")
    return float(s_str)

def fmt_brl(v: float) -> str:
    if pd.isna(v) or v is None: return "R$ 0,00"
    neg = v < 0
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {s}" if neg else f"R$ {s}"

def detectar_nivel(codigo: str) -> int:
    n = len(str(codigo).strip())
    if n <= 1: return 1
    if n <= 2: return 2
    if n <= 4: return 3
    if n <= 6: return 4
    return 5

def carregar_csv_local(caminho_arquivo: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_arquivo, sep=";", encoding="latin1", dtype=str)
    
    # ... (manter a limpeza de colunas igual ao que você já tem) ...
    df.columns = (df.columns.str.lower().str.strip().str.replace(r"[áàâãä]", "a", regex=True)
                  .str.replace(r"[éèêë]", "e", regex=True)
                  .str.replace(r"[íìîï]", "i", regex=True)
                  .str.replace(r"[óòôõö]", "o", regex=True)
                  .str.replace(r"[úùûü]", "u", regex=True)
                  .str.replace(r"[ç]", "c", regex=True)
                  .str.replace(r"\s+", "_", regex=True))

    col_conta  = next((c for c in df.columns if "codigo_do_plano" in c or "conta" in c), df.columns[0])
    col_desc   = next((c for c in df.columns if "descric" in c or "descri" in c or "nome" in c), df.columns[1])
    col_ant    = next((c for c in df.columns if "anterior" in c), None)
    col_deb    = next((c for c in df.columns if "debito" in c), None)
    col_cred   = next((c for c in df.columns if "credito" in c), None)
    col_atual  = next((c for c in df.columns if "atual" in c or "saldo" in c), None)
    col_tipo   = next((c for c in df.columns if c == "tipo"), None)

    out = pd.DataFrame()
    out["conta"]     = df[col_conta].astype(str).str.strip()
    out["descricao"] = df[col_desc].astype(str).str.strip().str.title()
    
    # A ALTERAÇÃO ESTÁ AQUI:
    if col_ant and col_ant in df.columns:
        # Primeiro limpa, depois força o tipo numérico do Pandas
        out["anterior"] = df[col_ant].astype(str).str.replace(".", "").str.replace(",", ".").astype(float)
    else:
        out["anterior"] = 0.0

    out["debito"]    = df[col_deb].apply(to_float) if col_deb else 0.0
    out["credito"]   = df[col_cred].apply(to_float) if col_cred else 0.0
    out["atual"]     = df[col_atual].apply(to_float) if col_atual else 0.0
    out["tipo"]      = df[col_tipo].astype(int) if col_tipo else 1
    out["nivel"]     = out["conta"].apply(detectar_nivel)
    out["raiz"]      = out["conta"].str[0]

    out = out[out["conta"].str.match(r"^\d+$")]
    out = out.drop_duplicates(subset="conta").reset_index(drop=True)
    out = out.sort_values("conta").reset_index(drop=True)
    
    todos_codigos = out["conta"].tolist()
    def buscar_pai(cod):
        candidatos = [c for c in todos_codigos if cod.startswith(c) and c != cod]
        return max(candidatos, key=len) if candidatos else ""
        
    out["parent"] = out["conta"].apply(buscar_pai)
    return out
    
def formatar_num_br(v: float) -> str:
    """Formata número no padrão brasileiro (123.456,78) sem símbolo de moeda."""
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    
def verificar_consistencia_contabil(df):
    """Realiza críticas contabilísticas no DataFrame carregado, com apuramento dinâmico de resultados."""
    criticas = []
    
    # 1. Captura os saldos absolutos das raízes
    ativo = df.loc[df['conta'] == '1', 'atual'].sum()
    passivo = df.loc[df['conta'] == '2', 'atual'].sum()
    
    rec = df.loc[df['conta'] == '3', 'atual'].sum()
    desp = df.loc[df['conta'] == '4', 'atual'].sum()
    custo = df.loc[df['conta'] == '5', 'atual'].sum()
    
    # 2. Correção da Matemática da DRE (Como tudo vem positivo: Receitas - Despesas - Custos)
    resultado_dre = rec - desp - custo
    
    # Verificação de Fechamento de DRE
    if abs(resultado_dre) > 1.0:
        criticas.append(f"🔍 **DRE Aberta:** O exercício possui um resultado (Lucro/Prejuízo) de {formatar_num_br(resultado_dre)} que ainda não foi transferido para o Património Líquido.")
        
    # 3. Equilíbrio Patrimonial Inteligente (Ativo vs Passivo + Resultado)
    # Se a DRE estiver aberta, o Balanço só fecha se somarmos o Resultado ao Passivo.
    diferenca = ativo - (passivo + resultado_dre)
    
    if abs(diferenca) > 0.05:
        criticas.append(f"⚠️ **Desequilíbrio Patrimonial Grave:** Mesmo considerando o resultado da DRE, há uma diferença de {formatar_num_br(abs(diferenca))} entre as origens e aplicações.")
    
    # 4. Verificação de contas Caixa/Bancos negativas
    caixa_negativo = df[(df['conta'].str.startswith('11')) & (df['atual'] < 0) & (df['tipo'] == 2)]
    for _, row in caixa_negativo.iterrows():
        criticas.append(f"❌ **Conta Negativa (Ativo Circulante):** {row['conta']} - {row['descricao']} está com saldo {formatar_num_br(row['atual'])}")
        
    return criticas


# ─────────────────────────────────────────────────────────
# COMBOBOX DE ARQUIVOS LOCAIS
# ─────────────────────────────────────────────────────────
csvs_locais = glob.glob("*.csv")

if not csvs_locais:
    st.error("📂 Nenhum arquivo CSV detectado na pasta do aplicativo.")
    st.stop()

c_tit, c_sel = st.columns([2, 2])

with c_tit:
    st.markdown('<div class="main-title">📊 Contabilidade</div>', unsafe_allow_html=True)
with c_sel:
    arquivo_escolhido = st.selectbox("📂 Selecione o Balancete:", csvs_locais, index=0)

if "arquivo_atual" not in st.session_state or st.session_state.arquivo_atual != arquivo_escolhido:
    st.session_state.df = carregar_csv_local(arquivo_escolhido)
    st.session_state.arquivo_atual = arquivo_escolhido
    st.session_state.periodo = arquivo_escolhido.replace(".csv", "")
    lista_criticas = verificar_consistencia_contabil(st.session_state.df)
    if lista_criticas:
        with st.expander("🚨 Auditoria Contábil (Alertas encontrados)", expanded=True):
            for aviso in lista_criticas:
                st.markdown(aviso)
    else:
        st.success("✅ Auditoria Contábil: Nenhuma inconsistência grave encontrada.")

df = st.session_state.df
todos_codigos = df["conta"].tolist()



st.markdown(f'<div class="main-sub">Demonstrações Consolidadas — {st.session_state.periodo}</div>', unsafe_allow_html=True)
st.markdown("---")


# ─────────────────────────────────────────────────────────
# APURAÇÃO DE INDICADORES
# ─────────────────────────────────────────────────────────
def soma_analiticas(raizes: list, prefixo: str = None) -> float:
    mask = df["raiz"].isin([str(r) for r in raizes]) & (df["tipo"] == 2)
    if prefixo:
        mask &= df["conta"].str.startswith(str(prefixo))
    return df[mask]["atual"].sum()

rec_bruta   = soma_analiticas([3], "31")
outras_rec  = soma_analiticas([3], "32")
rec_total   = soma_analiticas([3])
desp_total  = soma_analiticas([4])
lucro       = rec_total - desp_total

ativo_total  = df[(df["raiz"] == "1") & (df["nivel"] == 1)]["atual"].sum()
ativ_circ    = df[(df["conta"].str.startswith("11")) & (df["nivel"] == 2)]["atual"].sum()
pass_circ    = abs(df[(df["conta"].str.startswith("21")) & (df["nivel"] == 2)]["atual"].sum())
pass_ncirc   = abs(df[(df["conta"].str.startswith("22")) & (df["nivel"] == 2)]["atual"].sum())
pl_total     = abs(df[(df["conta"].str.startswith("23")) & (df["nivel"] == 2)]["atual"].sum())

margem  = lucro / rec_total * 100 if rec_total else 0
lc      = ativ_circ / pass_circ if pass_circ else 0
endiv   = (pass_circ + pass_ncirc) / ativo_total * 100 if ativo_total else 0

def kpi_html(label, valor, sub="", cls="kpi-neu"):
    return f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {cls}">{valor}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_html("Receita Consolidada", fmt_brl(rec_total), f"Operacional: {fmt_brl(rec_bruta)}"), unsafe_allow_html=True)
with c2: st.markdown(kpi_html("Resultado Líquido", fmt_brl(lucro), f"Margem: {margem:.1f}%", "kpi-pos" if lucro >= 0 else "kpi-neg"), unsafe_allow_html=True)
with c3: st.markdown(kpi_html("Custos e Despesas", fmt_brl(desp_total), f"{abs(desp_total/rec_total*100):.1f}% da Rec." if rec_total else "", "kpi-neg"), unsafe_allow_html=True)
with c4: st.markdown(kpi_html("Ativo Controlado", fmt_brl(ativo_total), f"Circulante: {fmt_brl(ativ_circ)}"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# ENGINE HTML+JS (COM A SOLUÇÃO DE RESIZE DO SEU ARQUIVO)
# ─────────────────────────────────────────────────────────
def gerar_componente_arvore(raizes: list, show_dc: bool, busca: str = "", acao: str = "default") -> str:
    df_base = df[df["raiz"].isin([str(r) for r in raizes])].sort_values("conta").copy()
    
    html_rows = ""
    for _, row in df_base.iterrows():
        codigo = str(row["conta"])
        desc = str(row["descricao"])
        atual = row["atual"]
        nivel = row["nivel"]
        parent = row["parent"]
        
        has_children = any(c.startswith(codigo) and c != codigo for c in todos_codigos)
        seta = "▶" if has_children else "·"
        
        indent = (nivel - 1) * 16
        row_classes = f"acc-l{min(nivel, 5)} acc-row"
        if has_children: row_classes += " pai-node"
        
        val_color = "val-pos" if atual > 0 else ("val-neg" if atual < 0 else "")
        td_anterior = f"<td class='acc-saldo'>{fmt_brl(float(row['anterior']))}</td>" if show_dc else ""
        td_colunas_dc = f"<td class='acc-saldo'>{fmt_brl(row['debito'])}</td><td class='acc-saldo'>{fmt_brl(row['credito'])}</td>" if show_dc else ""
        
        match_search = "true"
        if busca and (busca.lower() not in codigo.lower() and busca.lower() not in desc.lower()):
            match_search = "false"
            
        html_rows += f"""
        <tr class="{row_classes}" data-code="{codigo}" data-parent="{parent}" data-nivel="{nivel}" data-match="{match_search}">
            <td class="acc-code" style="padding-left:{8+indent}px"><span class="tree-arrow">{seta}</span> {codigo}</td>
            <td class="acc-desc">{desc}</td>
            {td_anterior} 
            {td_colunas_dc}
            <td class="acc-saldo {val_color}">{fmt_brl(atual)}</td>
        </tr>
        """

    th_dc = "<th class='num'>Ant.</th><th class='num'>Débito</th><th class='num'>Crédito</th>" if show_dc else ""
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body { font-family: 'Syne', sans-serif; margin: 0; padding: 0; background-color: transparent; color: #0f0e0d; }
        
        /* O contêiner agora é 100% livre. O documento body vai crescer empurrando o Streamlit. */
        .table-container { width: 100%; }
        
        .acc-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.82rem; }
        .acc-table th { 
            font-size: 0.65rem; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; 
            color: #7a7873; padding: 8px; border-bottom: 1px solid #e8e5e0; 
            background: #ffffff; text-align: left; 
        }
        .acc-table th.num { text-align: right; }
        .acc-l1 { background: #f4f3f0; font-weight: 700; color: #0f0e0d; }
        .acc-l2 { background: #faf9f6; font-weight: 600; color: #1a1a18; }
        .acc-l3 { background: #ffffff; font-weight: 500; color: #3a3835; }
        .acc-l4 { background: #ffffff; color: #3a3835; }
        .acc-l5 { background: #ffffff; color: #6b7280; font-size: 0.78rem; }
        .acc-table td { padding: 8px 10px; border-bottom: 0.5px solid #f3f4f6; vertical-align: middle; }
        .acc-row.pai-node { cursor: pointer; }
        .acc-row.pai-node:hover { background-color: #f9fafb; }
        .acc-code { font-family: 'DM Mono', monospace; font-size: 0.72rem; white-space: nowrap; }
        .tree-arrow { display: inline-block; width: 12px; font-size: 0.7rem; color: #9ca3af; margin-right: 4px; text-align: center; }
        .acc-saldo { font-family: 'DM Mono', monospace; text-align: right; white-space: nowrap; }
        .val-pos { color: #1e6b3e; }
        .val-neg { color: #c0392b; }
    </style>
    </head>
    <body>
    <div class="table-container">
        <table class="acc-table">
            <thead><tr><th style="width:130px">Código</th><th>Descrição</th>__TH_DC__<th class="num">Saldo Atual</th></tr></thead>
            <tbody>__HTML_ROWS__</tbody>
        </table>
    </div>
    
    <script>
        // -------------------------------------------------------------
        // Solução de Altura Dinâmica Extraída do arquivo `dre_aguia.py`
        // -------------------------------------------------------------
        (function() {
            function r() {
                try { window.parent.document.querySelectorAll('iframe').forEach(function(f) {
                    if (f.contentWindow === window) { 
                        f.style.width='100%'; 
                        if(f.parentElement) f.parentElement.style.width='100%'; 
                    }
                }); } catch(e) {}
            }
            document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', r) : r();
            window.addEventListener('load', r);

            function sendHeight() {
                var h = document.body.scrollHeight;
                try {
                    window.parent.document.querySelectorAll('iframe').forEach(function(f) {
                        if (f.contentWindow === window) { 
                            f.style.height = (h + 10) + 'px'; // +10px de margem de folga
                        }
                    });
                } catch(e) {}
            }
            window.addEventListener('load', sendHeight);
            
            if (typeof ResizeObserver !== 'undefined') {
                new ResizeObserver(sendHeight).observe(document.body);
            }
        })();

        // -------------------------------------------------------------
        // Engine de Expansão Contábil
        // -------------------------------------------------------------
        document.addEventListener("DOMContentLoaded", function() {
            const rows = document.querySelectorAll(".acc-table tbody tr");
            const isSearching = __IS_SEARCHING__;
            const globalAction = "__ACTION__";
            
            if (isSearching) {
                rows.forEach(row => {
                    if (row.getAttribute("data-match") === "true") {
                        row.style.display = "table-row";
                        let pCode = row.getAttribute("data-parent");
                        while(pCode) {
                            const pRow = document.querySelector(`tr[data-code="${pCode}"]`);
                            if (pRow) {
                                pRow.style.display = "table-row";
                                pRow.classList.add("expanded");
                                const arr = pRow.querySelector(".tree-arrow");
                                if (arr && arr.textContent === "▶") arr.textContent = "▼";
                                pCode = pRow.getAttribute("data-parent");
                            } else { pCode = null; }
                        }
                    } else { row.style.display = "none"; }
                });
            } else if (globalAction === "expand_all") {
                rows.forEach(row => {
                    row.style.display = "table-row";
                    if (row.classList.contains("pai-node")) {
                        row.classList.add("expanded");
                        const arr = row.querySelector(".tree-arrow");
                        if (arr) arr.textContent = "▼";
                    }
                });
            } else if (globalAction === "collapse_all") {
                rows.forEach(row => {
                    const level = parseInt(row.getAttribute("data-nivel"));
                    row.style.display = level === 1 ? "table-row" : "none";
                    if (row.classList.contains("pai-node")) {
                        row.classList.remove("expanded");
                        const arr = row.querySelector(".tree-arrow");
                        if (arr) arr.textContent = "▶";
                    }
                });
            } else {
                rows.forEach(row => {
                    const level = parseInt(row.getAttribute("data-nivel"));
                    if (level > 2) {
                        row.style.display = "none";
                    } else if (level === 2) {
                        const pCode = row.getAttribute("data-parent");
                        const pRow = document.querySelector(`tr[data-code="${pCode}"]`);
                        if (pRow) {
                            pRow.classList.add("expanded");
                            const arr = pRow.querySelector(".tree-arrow");
                            if (arr) arr.textContent = "▼";
                        }
                    }
                });
            }
            
            rows.forEach(row => {
                if (row.classList.contains("pai-node")) {
                    row.addEventListener("click", function() {
                        const code = this.getAttribute("data-code");
                        const isExpanded = this.classList.contains("expanded");
                        const arr = this.querySelector(".tree-arrow");
                        
                        if (isExpanded) {
                            this.classList.remove("expanded");
                            if (arr) arr.textContent = "▶";
                            rows.forEach(r => {
                                if (r.getAttribute("data-code").startsWith(code) && r !== row) {
                                    r.style.display = "none";
                                    r.classList.remove("expanded");
                                    const rArr = r.querySelector(".tree-arrow");
                                    if (rArr && rArr.textContent === "▼") rArr.textContent = "▶";
                                }
                            });
                        } else {
                            this.classList.add("expanded");
                            if (arr) arr.textContent = "▼";
                            expandirFilhosDirectos(code);
                        }
                    });
                }
            });
            
            function expandirFilhosDirectos(parentCode) {
                rows.forEach(r => {
                    if (r.getAttribute("data-parent") === parentCode) {
                        r.style.display = "table-row";
                        if (r.classList.contains("expanded")) {
                            expandirFilhosDirectos(r.getAttribute("data-code"));
                        }
                    }
                });
            }
        });
    </script>
    </body>
    </html>
    """
    
    html_final = html_template.replace("__TH_DC__", th_dc)
    html_final = html_final.replace("__HTML_ROWS__", html_rows)
    html_final = html_final.replace("__IS_SEARCHING__", str(bool(busca)).lower())
    html_final = html_final.replace("__ACTION__", acao)
    
    return html_final

def criar_barra_ferramentas(key: str):
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 3.4])
    with c1: exp = st.button("⊞ Expandir Tudo", key=f"btn_exp_{key}", use_container_width=True)
    with c2: col = st.button("⊟ Recolher Tudo", key=f"btn_col_{key}", use_container_width=True)
    with c3: exibir_dc = st.toggle("Visualizar D/C", value=False, key=f"tgl_{key}")
    with c4: busca = st.text_input("Filtro:", placeholder="🔍 Filtrar...", key=f"inp_{key}", label_visibility="collapsed")
            
    
    acao = "default"
    if exp: acao = "expand_all"
    elif col: acao = "collapse_all"
    
    return exibir_dc, busca, acao


# ─────────────────────────────────────────────────────────
# INTERFACE DE ABAS CORPORATIVAS
# ─────────────────────────────────────────────────────────
tab_dre, tab_bp, tab_analise = st.tabs([
    "📊 Demonstração de Resultado (DRE)",
    "🏛️ Balanço Patrimonial",
    "📈 Análise de Indicadores",
])

# ─── ABA DRE ───
with tab_dre:
    banner_class = "result-lucro" if lucro >= 0 else "result-prejuizo"
    label_class = "label-lucro" if lucro >= 0 else "label-prejuizo"
    st.markdown(f"""
    <div class="result-banner {banner_class}">
        <span style="font-size:1.8rem">{"📈" if lucro >= 0 else "📉"}</span>
        <div>
            <div class="result-label {label_class}">Resultado Líquido do Exercício</div>
            <div class="result-value {label_class}">{fmt_brl(lucro)}</div>
        </div>
        <div style="margin-left:auto; text-align:right;">
            <div style="font-size:.7rem; color:#7a7873; margin-bottom:2px">Margem de Lucro</div>
            <div style="font-family:'DM Mono',monospace; font-size:1.2rem; font-weight:500;" class="{label_class}">{margem:.2f}%</div>
        </div>
    </div>""", unsafe_allow_html=True)

    show_dc, busca_dre, acao_dre = criar_barra_ferramentas("dre")
    
    col_rec, col_desp = st.columns(2)
    with col_rec:
        st.markdown(f"**Estrutura de Receitas**")
        html_r = gerar_componente_arvore([3], show_dc, busca_dre, acao_dre)
        # Com o ResizeObserver configurado, a altura inicial aqui não limita a expansão
        components.html(html_r, height=400, scrolling=False)
        
    with col_desp:
        st.markdown(f"**Estrutura de Custos e Despesas**")
        html_d = gerar_componente_arvore([4, 5], show_dc, busca_dre, acao_dre)
        components.html(html_d, height=400, scrolling=False)


# ─── ABA BALANÇO PATRIMONIAL ───
with tab_bp:
    show_dc_bp, busca_bp, acao_bp = criar_barra_ferramentas("bp")
    
    col_ativo, col_passivo = st.columns(2)
    with col_ativo:
        st.markdown(f"**ATIVO CONSOLIDADO**")
        html_a = gerar_componente_arvore([1], show_dc_bp, busca_bp, acao_bp)
        components.html(html_a, height=400, scrolling=False)
        
    with col_passivo:
        st.markdown(f"**PASSIVO & PATRIMÔNIO LÍQUIDO**")
        html_p = gerar_componente_arvore([2], show_dc_bp, busca_bp, acao_bp)
        components.html(html_p, height=400, scrolling=False)


# ─── ABA ANÁLISE CORPORATIVA ───
with tab_analise:
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Composição Patrimonial de Saldos**")
        fig_bp = go.Figure(go.Bar(
            x=["Ativ. Circ.", "Pass. Circ.", "Pass. N.Circ.", "Patrimônio Líquido"],
            y=[ativ_circ, pass_circ, pass_ncirc, pl_total],
            marker_color=["#1e6b3e", "#c0392b", "#e57373", "#185fa5"],
            marker_line_width=0,
        ))
        fig_bp.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_family="Syne", showlegend=False, yaxis=dict(tickformat=",.0f", gridcolor="#f3f4f6"))
        st.plotly_chart(fig_bp, use_container_width=True)
        
    with g2:
        st.markdown("**Representatividade de Receitas**")
        df_rec_pie = df[(df["raiz"] == "3") & (df["tipo"] == 2) & (df["atual"] > 0)]
        if not df_rec_pie.empty:
            # Lista manual de cores (HEX) verde-esmeralda, garantindo que não dê o erro 'Emerald' do Plotly.
            cores = ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45", "#006d2c", "#00441b"]
            fig_pie = px.pie(df_rec_pie, values="atual", names="descricao", hole=0.4, color_discrete_sequence=cores)
            fig_pie.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", font_family="Syne")
            fig_pie.update_traces(textinfo="percent")
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.markdown("**Análise Vertical Sumarizada da DRE**")
    resumo_matriz = {
        "Faturamento Bruto de Serviços": rec_bruta,
        "Outras Receitas e Entradas": outras_rec,
        "(=) Receita Bruta Total": rec_total,
        "(-) Custos e Despesas Operacionais": -desp_total,
        "(=) RESULTADO LÍQUIDO DO PERÍODO": lucro
    }
    df_resumo = pd.DataFrame([{
        "Grupo Indicador": k,
        "Montante": fmt_brl(v),
        "Representatividade (AV%)": f"{(v/rec_total*100):.2f}%" if rec_total and not k.startswith("=") else "—"
    } for k, v in resumo_matriz.items()])
    st.dataframe(df_resumo, hide_index=True, use_container_width=True)
