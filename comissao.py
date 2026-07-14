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

# Estilização CSS para deixar o visual moderno e limpo
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Painel de Desempenho e Comissionamento")
st.subheader("Análise consolidada de faturamento, comissão por consultor e inteligência de processos.")

# =====================================================================
# FUNÇÃO DE DATA QUALITY E SEGURANÇA (Para Prevenção de Erros no Python)
# =====================================================================
def validar_e_limpar_dados(df_raw):
    erros = []
    alertas = []
    
    # 1. Limpeza Básica (Sanitização)
    # Remove espaços extras invisíveis no início/fim de textos que costumam quebrar PROCvs e filtros
    for col in ["CONSULTOR", "CATEGORIA DO PRODUTO", "PRODUTO", "CLIENTE"]:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].astype(str).str.strip()
            
    # 2. Verificação de Campos Nulos em colunas críticas
    colunas_criticas = ["CONSULTOR", "CATEGORIA DO PRODUTO", "valor total"]
    for col in colunas_criticas:
        nulos = df_raw[df_raw[col].isna() | (df_raw[col] == "") | (df_raw[col] == "nan")].shape[0]
        if nulos > 0:
            erros.append(f"❌ Detectamos **{nulos} linha(s)** com o campo **'{col}'** em branco ou inválido.")

    # 3. Verificação de Categorias Inválidas (Garante integridade com o modelo comercial)
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
    # Lê a planilha principal utilizando a nova aba "Planilha 1"
    df_vendas = pd.read_excel("versao final igor.xlsx", sheet_name="Planilha 1")
    
    # Garante que as colunas numéricas estejam corretas
    df_vendas["valor total"] = pd.to_numeric(df_vendas["valor total"], errors='coerce').fillna(0)
    df_vendas["comissão"] = pd.to_numeric(df_vendas["comissão"], errors='coerce').fillna(0)
    df_vendas["QUANTIDADE"] = pd.to_numeric(df_vendas["QUANTIDADE"], errors='coerce').fillna(0)
    df_vendas["Valor para Meta"] = pd.to_numeric(df_vendas["Valor para Meta"], errors='coerce').fillna(0)
    
    # Executa as regras de validação automática do Python
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
    st.write("Status do processamento e higienização automática de dados:")
    
    if len(erros) == 0:
        st.success("✅ **Dados 100% íntegros!** Nenhuma inconsistência técnica detectada na planilha de apoio.")
    else:
        st.error("🚨 **Inconsistências encontradas!**")
        for err in erros:
            st.write(err)
        st.warning("Ajuste os dados acima na planilha do Excel para garantir que os relatórios sejam gerados perfeitamente.")

# Métricas rápidas de cabeçalho
total_vendas_geral = df["valor total"].sum()
total_comissao_geral = df["comissão"].sum()
total_itens_vendidos = df["QUANTIDADE"].sum()

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric("Faturamento Geral (R$)", f"R$ {total_vendas_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col_kpi2:
    st.metric("Total Comissões Clientes (R$)", f"R$ {total_comissao_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col_kpi3:
    st.metric("Total de Produtos Vendidos", f"{int(total_itens_vendidos)} un")

st.markdown("---")

# 4. Navegação por Abas
tab1, tab2, tab3 = st.tabs(["👥 Performance de Vendas", "📦 Análise de Produtos", "📝 Respostas do Estudo de Caso"])

# ==========================================
# ABA 1: PERFORMANCE DE VENDAS
# ==========================================
with tab1:
    st.header("👥 Performance por Consultor")
    st.write("Visão detalhada do faturamento individual gerado para a empresa versus a comissão final calculada.")

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
        st.write("### Tabela Resumo")
        st.dataframe(df_exibicao, hide_index=True, use_container_width=True)
        st.caption("Nota: O atingimento de meta do Consultor 3 ficou abaixo do piso de R$ 2.000,00, classificando-o na Faixa 1 (0% de comissão na maioria das categorias).")

    with col_grafico:
        st.write("### Faturamento Gerado vs. Comissão Paga")
        fig_perf = px.bar(
            df_consultores,
            x="CONSULTOR",
            y=["Total_Faturamento", "Total_Comissao"],
            barmode="group",
            labels={"value": "Valor (R$)", "CONSULTOR": "Consultor", "variable": "Métrica"},
            color_discrete_map={"Total_Faturamento": "#1E3A8A", "Total_Comissao": "#F59E0B"},
            text_auto='.2s'
        )
        fig_perf.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_perf, use_container_width=True)

# ==========================================
# ABA 2: ANÁLISE DE PRODUTOS
# ==========================================
with tab2:
    st.header("📦 Distribuição e Receita por Categoria")
    st.write("Identificação das categorias de produtos mais relevantes em volume e faturamento total.")

    df_categoria = df.groupby("CATEGORIA DO PRODUTO").agg(
        Quantidade=("QUANTIDADE", "sum"),
        Faturamento=("valor total", "sum")
    ).reset_index()

    col_prod1, col_prod2 = st.columns(2)

    with col_prod1:
        st.write("### Volume de Vendas (Quantidade)")
        fig_qtd = px.bar(
            df_categoria,
            y="CATEGORIA DO PRODUTO",
            x="Quantidade",
            orientation="h",
            color_discrete_sequence=["#2563EB"],
            text_auto=True
        )
        fig_qtd.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Unidades Vendidas", yaxis_title=None)
        st.plotly_chart(fig_qtd, use_container_width=True)

    with col_prod2:
        st.write("### Faturamento Total por Categoria (R$)")
        fig_fat = px.bar(
            df_categoria,
            y="CATEGORIA DO PRODUTO",
            x="Faturamento",
            orientation="h",
            color_discrete_sequence=["#10B981"],
            text_auto='.3s'
        )
        fig_fat.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Faturamento (R$)", yaxis_title=None)
        st.plotly_chart(fig_fat, use_container_width=True)

# ==========================================
# ABA 3: RESPOSTAS DO ESTUDO DE CASO
# ==========================================
with tab3:
    st.header("📝 Respostas Oficiais - Estudo de Caso")
    
    st.markdown("""
    Abaixo constam as respostas oficiais para cada um dos pontos solicitados no roteiro de avaliação do processo seletivo:

    ---

    ### 📌 Pergunta 1: Volume de vendas de cada consultor e valor de comissão para pagamento.
    Com base nas regras de elegibilidade, metas de atingimento (piso e regras de abatimento/adição de produtos especiais) e matriz de comissionamento por faixa, os valores finais apurados são:

    | Consultor | Total de Vendas Realizadas | Valor P/ Meta Atingido | Faixa de Comissão | **Comissão a Pagar (R$)** |
    | :--- | :---: | :---: | :---: | :---: |
    | **CONSULTOR 1** | R$ 2.964,76 | R$ 2.964,76 | **Faixa 2** (R$ 2k a R$ 4k) | **R$ 2.973,75** |
    | **CONSULTOR 2** | R$ 4.063,73 | R$ 4.063,73 | **Faixa 3** (>= R$ 4k) | **R$ 6.270,60** |
    | **CONSULTOR 3** | R$ 1.374,92 | R$ 1.374,92 | **Faixa 1** (< R$ 2k) | **R$ 0,00** |
    | **TOTAL GERAL** | **R$ 8.403,41** | **R$ 8.403,41** | - | **R$ 9.244,35** |

    * **Análise de Performance:** * O **Consultor 2** obteve comissão superior ao seu próprio faturamento bruto total de vendas. Isso ocorre de forma legítima, pois na **Faixa 3**, categorias de alto valor agregado (como *Alta Voz - Base* e *Alta Voz - Fresh*) possuem taxas de comissão de **150%** e **200%** respectivamente, alavancando a remuneração por superação de metas.
      * O **Consultor 3** não atingiu o piso mínimo de meta de R$ 2.000,00, permanecendo na **Faixa 1** e, por consequência, sem direito a comissão na maior parte dos produtos vendidos.

    ---

    ### 📌 Pergunta 2: Segunda visualização além do arquivo tradicional.
    * A segunda visualização do projeto foi desenvolvida em ambiente de código utilizando **Python, Pandas, Plotly e Streamlit**, criando este Web Application interativo.
    * A escolha tecnológica visa substituir os relatórios estáticos por uma ferramenta em que a liderança pode filtrar, ordenar e tomar decisões dinâmicas sobre os dados em tempo real.

    ---

    ### 📌 Pergunta 3: Sugestões de melhorias de processo para prevenção de erros (Foco em Excel e Python).
    Para garantir a segurança e a integridade de ponta a ponta, propomos barreiras em duas frentes distintas:

    #### A. Segurança de Entrada (No Excel)
    1. **Validação de Dados na Origem:** Aplicação de listas suspensas (*Data Validation*) no Excel para as colunas de categorias e consultores. Isso previne que o usuário digite dados com erros gramaticais ou espaçamentos diferentes.
    2. **Proteção de Abas:** Ocultar e proteger a aba de "Matriz de Comissão" por meio de senha de administrador, para que regras de pagamentos não sejam editadas acidentalmente.

    #### B. Auditoria Programática e Higienização de Dados (No Python)
    Neste projeto, criamos uma rotina de **Auditoria Automatizada via Python (Data Quality)**. O sistema faz uma varredura nas planilhas faturadas de forma instantânea antes de processar qualquer conta. Ele executa:
    * **Limpeza e Higienização de Strings (Sanitização):** O código aplica funções automáticas do pandas para remover espaços em branco invisíveis (no início ou fim das células) e alinhar os nomes dos produtos. Isso impede que erros comuns no Excel quebrem o cálculo das comissões.
    * **Testes de Schema:** O código alerta imediatamente se a planilha contiver valores de venda negativos, nomes em branco ou se alguma nova venda contiver uma categoria que não foi previamente catalogada no modelo de remuneração da empresa. Qualquer anomalia é reportada em tempo real na barra lateral **"Central de Governança"** deste Dashboard.

    ---

    ### 📌 Pergunta 4: Proposta de automação do processo.
    Atualmente, o processo de calcular comissões exige retrabalho manual mensal. Propomos a seguinte arquitetura de automação moderna:
    * **Implementação de um pipeline de ETL com Power Query ou Python (Pandas):** * Em vez de montar fórmulas complexas no Excel manualmente a cada ciclo, as regras de negócios (fórmulas condicionais de meta e as taxas de comissão) são codificadas uma única vez no motor de faturamento em Python.
      * O analista operacional apenas faz o upload da listagem bruta de vendas do sistema de faturamento, e o pipeline realiza a higienização, cruzamento de dados e cálculo das comissões em segundos, reduzindo o tempo de processamento em até **95%** e eliminando o fator de erro humano.
    """)