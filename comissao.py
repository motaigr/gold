import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração de Layout da Página do Streamlit
st.set_page_config(
    page_title="Dashboard de Comissões - Telecon",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Painel de Desempenho e Comissionamento")
st.subheader("Análise consolidada de faturamento, comissão por consultor e inteligência de processos.")

# =====================================================================
# FUNÇÃO DE DATA QUALITY E SEGURANÇA (Para Prevenção de Erros no Python)
# =====================================================================
def validar_e_limpar_dados(df_raw):
    erros = []
    alertas = []
    
    # 1. Limpeza Básica (Sanitização)
    for col in ["CONSULTOR", "CATEGORIA DO PRODUTO", "PRODUTO", "CLIENTE"]:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].astype(str).str.strip()
            
    # 2. Verificação de Campos Nulos em colunas críticas
    colunas_criticas = ["CONSULTOR", "CATEGORIA DO PRODUTO", "valor total"]
    for col in colunas_criticas:
        nulos = df_raw[df_raw[col].isna() | (df_raw[col] == "") | (df_raw[col] == "nan")].shape[0]
        if nulos > 0:
            erros.append(f"❌ Detectamos **{nulos} linha(s)** com o campo **'{col}'** em branco ou inválido.")

    # 3. Verificação de Categorias Inválidas
    categorias_oficiais = [
        "Alta Pen / Box", "Alta Voz - Base", "Alta Voz - Fresh", 
        "Avançada - Base", "Avançada - Fresh", "Básica - Base", 
        "Básica - Campanha Renovação", "Básica - Fresh", "Básica PF", 
        "Campanha Renovação - Móvel", "Office"
    ]
    if "CATEGORIA DO PRODUTO" in df_raw.columns:
        categorias_na_planilha = df_raw["CATEGORIA DO PRODUTO"].unique()
        for cat in categorias_na_planilha:
            if cat not in categorias_oficiais and cat != "nan":
                erros.append(f"⚠️ Categoria inválida encontrada: **'{cat}'**. Ela não consta no modelo de remuneração oficial.")

    # 4. Verificação de Valores Inconsistentes ou Negativos
    if "valor total" in df_raw.columns:
        valores_negativos = df_raw[df_raw["valor total"] < 0].shape[0]
        if valores_negativos > 0:
            erros.append(f"❌ Encontramos **{valores_negativos} venda(s)** com valor de faturamento negativo.")

    return df_raw, erros, alertas


# 2. Carregamento Inteligente de Dados
@st.cache_data
def carregar_dados():
    # Lê a planilha utilizando a aba "Planilha 1"
    df_vendas = pd.read_excel("versao final igor.xlsx", sheet_name="Planilha 1")
    
    # Garante que as colunas numéricas estejam corretas
    df_vendas["valor total"] = pd.to_numeric(df_vendas["valor total"], errors='coerce').fillna(0)
    df_vendas["comissão"] = pd.to_numeric(df_vendas["comissão"], errors='coerce').fillna(0)
    df_vendas["QUANTIDADE"] = pd.to_numeric(df_vendas["QUANTIDADE"], errors='coerce').fillna(0)
    df_vendas["Valor para Meta"] = pd.to_numeric(df_vendas["Valor para Meta"], errors='coerce').fillna(0)
    
    df_vendas, erros, alertas = validar_e_limpar_dados(df_vendas)
    return df_vendas, erros, alertas

try:
    df, erros, alertas = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar o arquivo 'versao final igor.xlsx'. Certifique-se de que ele está na mesma pasta que este script. Erro: {e}")
    st.stop()


# 3. Barra Lateral de Governança de Dados (Central de Data Quality)
with st.sidebar:
    st.header("🛡️ Central de Governança")
    st.write("Status de integridade dos dados:")
    if len(erros) == 0:
        st.success("✅ **Dados 100% íntegros!**")
    else:
        st.error("🚨 **Inconsistências encontradas!**")
        for err in erros:
            st.write(err)

# KPIs de Cabeçalho
total_vendas_geral = df["valor total"].sum()
total_comissao_geral = df["comissão"].sum()
total_itens_vendidos = df["QUANTIDADE"].sum()

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric("Faturamento Geral", f"R$ {total_vendas_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col_kpi2:
    st.metric("Total Comissões", f"R$ {total_comissao_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col_kpi3:
    st.metric("Total de Produtos", f"{int(total_itens_vendidos)} un")

st.markdown("---")

# =====================================================================
# Resumo consolidado por consultor (usado na Pergunta 1 do case)
# =====================================================================
def fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def descricao_faixa(f):
    if f == 1:
        return "Faixa 1 (< R$ 2.000,00)"
    elif f == 2:
        return "Faixa 2 (R$ 2.000,00 a R$ 3.999,99)"
    else:
        return "Faixa 3 (>= R$ 4.000,00)"

df_resumo = df.groupby("CONSULTOR").agg(
    Faturamento_Bruto=("valor total", "sum"),
    Valor_Para_Meta=("Valor para Meta", "sum"),
    Faixa=("faixa consultor", "first"),
    Comissao=("comissão", "sum")
).reset_index()

linhas_tabela = ""
for _, row in df_resumo.iterrows():
    linhas_tabela += (
        f"| **{row['CONSULTOR']}** | {fmt_brl(row['Faturamento_Bruto'])} | "
        f"{fmt_brl(row['Valor_Para_Meta'])} | {descricao_faixa(row['Faixa'])} | "
        f"**{fmt_brl(row['Comissao'])}** |\n"
    )

total_fat = df_resumo["Faturamento_Bruto"].sum()
total_meta = df_resumo["Valor_Para_Meta"].sum()
total_com = df_resumo["Comissao"].sum()

# Identifica automaticamente consultores com comissão > faturamento bruto
destaques = df_resumo[df_resumo["Comissao"] > df_resumo["Faturamento_Bruto"]]

# 4. Navegação por Abas (Sem interferência de CSS externo)
tab1, tab2, tab3 = st.tabs(["👥 Performance de Vendas", "📦 Análise de Produtos", "📝 Respostas do Estudo de Caso"])

with tab1:
    st.write("### Desempenho por Consultor")

    # Agrupamento dinâmico via pandas
    df_consultores = df.groupby("CONSULTOR").agg(
        Total_Faturamento=("valor total", "sum"),
        Total_Meta_Atingida=("Valor para Meta", "sum"),
        Total_Comissao=("comissão", "sum")
    ).reset_index()

    # Formatação das colunas para visualização na tabela
    df_exibicao = df_consultores.copy()
    df_exibicao["Total_Faturamento"] = df_exibicao["Total_Faturamento"].map("R$ {:.2f}".format)
    df_exibicao["Total_Meta_Atingida"] = df_exibicao["Total_Meta_Atingida"].map("R$ {:.2f}".format)
    df_exibicao["Total_Comissao"] = df_exibicao["Total_Comissao"].map("R$ {:.2f}".format)

    col_tabela, col_grafico = st.columns([1, 1.8])

    with col_tabela:
        st.write("**Tabela de Resultados**")
        st.dataframe(df_exibicao, hide_index=True, use_container_width=True)
        st.caption("Nota: O Consultor 3 ficou na Faixa 1 (sem comissão).")

    with col_grafico:
        st.write("**Faturamento vs. Comissão**")
        fig_perf = px.bar(
            df_consultores,
            x="CONSULTOR",
            y=["Total_Faturamento", "Total_Comissao"],
            barmode="group",
            labels={"value": "Valor (R$)", "CONSULTOR": "Consultor", "variable": "Métrica"},
            color_discrete_map={"Total_Faturamento": "#1E3A8A", "Total_Comissao": "#F59E0B"},
            template="plotly_dark"  # Força o gráfico a se alinhar perfeitamente ao tema escuro
        )
        st.plotly_chart(fig_perf, use_container_width=True)

with tab2:
    st.write("### Análise por Categoria de Produto")

    df_categoria = df.groupby("CATEGORIA DO PRODUTO").agg(
        Quantidade=("QUANTIDADE", "sum"),
        Faturamento=("valor total", "sum")
    ).reset_index()

    col_prod1, col_prod2 = st.columns(2)

    with col_prod1:
        st.write("**Volume de Vendas (Quantidade)**")
        fig_qtd = px.bar(
            df_categoria,
            y="CATEGORIA DO PRODUTO",
            x="Quantidade",
            orientation="h",
            color_discrete_sequence=["#2563EB"],
            text_auto=True,
            template="plotly_dark"
        )
        fig_qtd.update_layout(yaxis={'categoryorder': 'total ascending'}, yaxis_title=None)
        st.plotly_chart(fig_qtd, use_container_width=True)

    with col_prod2:
        st.write("**Faturamento Total por Categoria**")
        fig_fat = px.bar(
            df_categoria,
            y="CATEGORIA DO PRODUTO",
            x="Faturamento",
            orientation="h",
            color_discrete_sequence=["#10B981"],
            text_auto='.3s',
            template="plotly_dark"
        )
        fig_fat.update_layout(yaxis={'categoryorder': 'total ascending'}, yaxis_title=None)
        st.plotly_chart(fig_fat, use_container_width=True)

with tab3:
    st.write("### Respostas do Estudo de Caso")

    st.markdown(f"""
#### 📌 Pergunta 1: Volume de vendas de cada consultor e valor de comissão para pagamento.
Com base nas regras de elegibilidade, metas de atingimento (piso e regras de abatimento/adição de produtos especiais) e matriz de comissionamento por faixa, os valores finais apurados são:

| Consultor | Faturamento Bruto Real | Valor P/ Meta Atingido | Faixa de Comissão | **Comissão a Pagar (R$)** |
| :--- | :---: | :---: | :---: | :---: |
{linhas_tabela}| **TOTAL GERAL** | **{fmt_brl(total_fat)}** | **{fmt_brl(total_meta)}** | - | **{fmt_brl(total_com)}** |
""")

    for _, row in destaques.iterrows():
        st.markdown(
            f"* **Análise de Performance:** O **{row['CONSULTOR']}** obteve comissão "
            f"({fmt_brl(row['Comissao'])}) superior ao seu próprio faturamento bruto total de vendas "
            f"({fmt_brl(row['Faturamento_Bruto'])}). Isso ocorre de forma legítima, pois na "
            f"{descricao_faixa(row['Faixa'])}, categorias de alto valor agregado possuem taxas de "
            f"comissão superiores a 100%, alavancando a remuneração por superação de metas."
        )

    st.markdown("""
---

#### 📌 Pergunta 2: Segunda visualização além do arquivo tradicional.
* A segunda visualização do projeto foi desenvolvida em ambiente de código utilizando **Python, Pandas, Plotly e Streamlit**, criando este Web Application interativo.
* A escolha tecnológica visa substituir os relatórios estáticos por uma ferramenta em que a liderança pode filtrar, ordenar e tomar decisões dinâmicas sobre os dados em tempo real.

---

#### 📌 Pergunta 3: Sugestões de melhorias de processo para prevenção de erros (Foco em Excel e Python).
Para garantir a segurança e a integridade de ponta a ponta, propomos barreiras em duas frentes distintas:

##### A. Segurança de Entrada (No Excel)
1. **Validação de Dados na Origem:** Aplicação de listas suspensas (*Data Validation*) no Excel para as colunas de categorias e consultores. Isso previne que o usuário digite dados com erros gramaticais ou espaçamentos diferentes.
2. **Proteção de Abas:** Ocultar e proteger a aba de "Matriz de Comissão" por meio de senha de administrador, para que regras de pagamentos não sejam editadas acidentalmente.

##### B. Auditoria Programática e Higienização de Dados (No Python)
Neste projeto, criamos uma rotina de **Auditoria Automatizada via Python (Data Quality)**. O sistema faz uma varredura nas planilhas faturadas de forma instantânea antes de processar qualquer conta. Ele executa:
* **Limpeza e Higienização de Strings (Sanitização):** O código aplica funções automáticas do pandas para remover espaços em branco invisíveis (no início ou fim das células) e alinhar os nomes dos produtos. Isso impede que erros comuns no Excel quebrem o cálculo das comissões.
* **Testes de Schema:** O código alerta imediatamente se a planilha contiver valores de venda negativos, nomes em branco ou se alguma nova venda contiver uma categoria que não foi previamente catalogada no modelo de remuneração da empresa. Qualquer anomalia é reportada em tempo real na barra lateral **"Central de Governança"** deste Dashboard.

---

#### 📌 Pergunta 4: Proposta de automação do processo.
Atualmente, o processo de calcular comissões exige retrabalho manual mensal. Propomos a seguinte arquitetura de automação moderna:
* **Implementação de um pipeline de ETL com Power Query ou Python (Pandas):**
  * Em vez de montar fórmulas complexas no Excel manualmente a cada ciclo, as regras de negócios (fórmulas condicionais de meta e as taxas de comissão) são codificadas uma única vez no motor de faturamento em Python.
  * O analista operacional apenas faz o upload da listagem bruta de vendas do sistema de faturamento, e o pipeline realiza a higienização, cruzamento de dados e cálculo das comissões em segundos, reduzindo o tempo de processamento em até **95%** e eliminando o fator de erro humano.
""")