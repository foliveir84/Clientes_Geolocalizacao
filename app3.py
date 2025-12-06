import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Vendas Farmacêuticas",
    page_icon="💊",
    layout="wide"
)

# --- Título ---
st.title("📊 Análise Geoespacial de Vendas")

# --- Carregamento de Dados ---
@st.cache_data
def load_data():
    file_path = "Ficheiro_final_trabalhar.csv"
    
    # Tentar ler com utf-8, fallback para latin-1
    try:
        df = pd.read_csv(file_path, sep=';', dtype=str, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=';', dtype=str, encoding='latin-1')

    # Lista de colunas numéricas (valores monetários e quantidades)
    # Converter vírgula para ponto
    numeric_cols = [
        'IVA', 'Valor_desconto', 'Qt', 'Valor_Pago', 'Valor_Credito', 
        'Total_Faturado', 'Total_Faturado_com_Desconto', 'PCU'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].str.replace(',', '.', regex=False), errors='coerce').fillna(0)

    # Tratamento de Coordenadas (Lat/Lon)
    coord_cols = ['LATITUDE', 'LONGITUDE']
    for col in coord_cols:
        if col in df.columns:
            df[col] = df[col].str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Remover linhas sem coordenadas válidas
    df = df.dropna(subset=['LATITUDE', 'LONGITUDE'])
    df = df[(df['LATITUDE'] != 0) & (df['LONGITUDE'] != 0)]

    # Tratamento de Datas
    if 'DT_NASC' in df.columns:
        df['DT_NASC'] = pd.to_datetime(df['DT_NASC'], format='%d/%m/%Y', errors='coerce')
        now = datetime.now()
        
        def calculate_age(born):
            if pd.isnull(born): return -1
            return now.year - born.year - ((now.month, now.day) < (born.month, born.day))

        df['Idade'] = df['DT_NASC'].apply(calculate_age)
        
        # Criar Faixas Etárias
        bins = [0, 18, 30, 45, 60, 75, 120]
        labels = ['0-18', '19-30', '31-45', '46-60', '61-75', '75+']
        df['Faixa_Etaria'] = pd.cut(df['Idade'], bins=bins, labels=labels, right=False)
        df['Faixa_Etaria'] = df['Faixa_Etaria'].cat.add_categories(['Desconhecido']).fillna('Desconhecido')

    # Garantir Ano como Inteiro
    if 'Ano' in df.columns:
        df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').fillna(0).astype(int)

    # Mapear Meses para Ordem Numérica
    meses_map = {
        'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4, 'Mai': 5, 'Jun': 6,
        'Jul': 7, 'Ago': 8, 'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12
    }
    if 'Nome do Mês' in df.columns:
        df['Mes_Num'] = df['Nome do Mês'].map(meses_map).fillna(0).astype(int)
    
    # Tratamento da Coluna Localidade (Novo)
    if 'Localidade' in df.columns:
        df['Localidade'] = df['Localidade'].fillna('Desconhecido').astype(str).str.strip()
    else:
        df['Localidade'] = 'Desconhecido'

    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro crítico ao carregar dados: {e}")
    st.stop()

# --- Sidebar: Configurações e Filtros ---
st.sidebar.header("⚙️ Filtros de Análise")

# 1. Seletor de Métrica Principal
metrica_selecionada = st.sidebar.radio(
    "Tamanho das Bolhas por:",
    options=["Total Faturado (€)", "Nº de Atendimentos (Tráfego)"]
)

# 2. Estilo do Mapa
estilo_mapa = st.sidebar.selectbox(
    "Estilo do Mapa",
    options=["Claro (Padrão)", "Escuro", "Satélite", "Detalhado (OpenStreet)"],
    index=1
)

# 3. Modo de Comparação
modo_comparativo = st.sidebar.checkbox("Comparar 2024 vs 2025", value=False)

# Filtros Dinâmicos
# Ano
if not modo_comparativo:
    anos_unicos = sorted(df['Ano'].unique())
    ano_selecionado = st.sidebar.multiselect("Selecionar Ano(s)", anos_unicos, default=anos_unicos)
else:
    st.sidebar.info("Modo Comparativo: A filtrar meses coincidentes entre 2024 e 2025.")
    ano_selecionado = [2024, 2025]

# Mês
meses_unicos_nomes = df[['Mes_Num', 'Nome do Mês']].dropna().drop_duplicates().sort_values('Mes_Num')['Nome do Mês'].tolist()
mes_filtro = st.sidebar.multiselect("Selecionar Mês", meses_unicos_nomes, default=meses_unicos_nomes)

# Filtro de Localidade (Novo)
with st.sidebar.expander("📍 Filtro de Localidade", expanded=True):
    localidades_unicas = sorted(df['Localidade'].unique())
    localidades_selecionadas = st.multiselect("Selecionar Localidade", localidades_unicas)

# Filtros de Produto e Outros
with st.sidebar.expander("📦 Filtros de Produto", expanded=False):
    categorias = st.multiselect("Categoria (CAT)", options=sorted(df['CAT'].dropna().unique()))
    subcategorias = st.multiselect("Subcategoria (CT1)", options=sorted(df['CT1'].dropna().unique()))
    genericos = st.radio("Genérico?", options=["Todos", "Sim (S)", "Não (N)"])
    marcas = st.multiselect("Marca", options=sorted(df['MARCA'].dropna().unique()))

with st.sidebar.expander("👥 Filtros Demográficos", expanded=False):
    sexo = st.multiselect("Sexo", options=sorted(df['SEXO'].dropna().unique()))
    faixa_etaria = st.multiselect("Faixa Etária", options=sorted(df['Faixa_Etaria'].unique().astype(str)))

with st.sidebar.expander("💳 Filtros de Transação", expanded=False):
    tipo_pagamento = st.multiselect("Pagamento", options=sorted(df['Pagamento'].dropna().unique()))
    grau_certeza = st.multiselect("Grau de Certeza (Geo)", options=sorted(df['GRAU_CERTEZA'].dropna().unique()))

# --- Aplicação dos Filtros ---
df_filtered = df.copy()

# Filtro Base de Ano
if not modo_comparativo:
    if ano_selecionado:
        df_filtered = df_filtered[df_filtered['Ano'].isin(ano_selecionado)]
    else:
        st.warning("Por favor selecione pelo menos um ano.")
        st.stop()

# Filtro de Mês
if mes_filtro:
    df_filtered = df_filtered[df_filtered['Nome do Mês'].isin(mes_filtro)]

# Filtro de Localidade (Novo)
if localidades_selecionadas:
    df_filtered = df_filtered[df_filtered['Localidade'].isin(localidades_selecionadas)]

# Filtros Gerais
if categorias:
    df_filtered = df_filtered[df_filtered['CAT'].isin(categorias)]
if subcategorias:
    df_filtered = df_filtered[df_filtered['CT1'].isin(subcategorias)]
if genericos != "Todos":
    val = 'S' if "Sim" in genericos else 'N'
    df_filtered = df_filtered[df_filtered['GEN'] == val]
if marcas:
    df_filtered = df_filtered[df_filtered['MARCA'].isin(marcas)]
if sexo:
    df_filtered = df_filtered[df_filtered['SEXO'].isin(sexo)]
if faixa_etaria:
    df_filtered = df_filtered[df_filtered['Faixa_Etaria'].astype(str).isin(faixa_etaria)]
if tipo_pagamento:
    df_filtered = df_filtered[df_filtered['Pagamento'].isin(tipo_pagamento)]
if grau_certeza:
    df_filtered = df_filtered[df_filtered['GRAU_CERTEZA'].isin(grau_certeza)]

# Lógica Especial Modo Comparativo
if modo_comparativo:
    # Obter meses presentes em 2025
    df_2025_check = df_filtered[df_filtered['Ano'] == 2025]
    meses_presentes_2025 = df_2025_check['Mes_Num'].unique()
    
    if len(meses_presentes_2025) == 0:
        st.warning("⚠️ Não existem dados para 2025 com os filtros selecionados. A comparação pode não mostrar resultados.")
    
    # Restringir o dataset para conter APENAS os meses que existem em 2025 (para comparar YTD real)
    # Mas mantemos os dados de 2024 e 2025
    df_filtered = df_filtered[
        (df_filtered['Ano'].isin([2024, 2025])) &
        (df_filtered['Mes_Num'].isin(meses_presentes_2025))
    ]
    
    nomes_meses_filtrados = sorted(df_filtered['Nome do Mês'].unique())
    if nomes_meses_filtrados:
        st.markdown(f"ℹ️ **Modo Comparativo:** Comparando meses coincidentes: **{', '.join(nomes_meses_filtrados)}**")

# Verificar se sobrou data
if df_filtered.empty:
    st.warning("Nenhum dado encontrado com os filtros atuais.")
    st.stop()

# --- Construção do Texto de Contexto (Filtros Ativos) ---
filtros_ativos = []

# Ano
if modo_comparativo:
    filtros_ativos.append("📅 Ano: Comparativo (2024 vs 2025)")
else:
    if len(ano_selecionado) < len(anos_unicos):
        filtros_ativos.append(f"📅 Ano: {', '.join(map(str, ano_selecionado))}")

# Mês
if mes_filtro and len(mes_filtro) < len(meses_unicos_nomes):
    if len(mes_filtro) <= 3:
        filtros_ativos.append(f"🗓️ Mês: {', '.join(mes_filtro)}")
    else:
        filtros_ativos.append(f"🗓️ Mês: {len(mes_filtro)} selecionados")

# Localidade
if localidades_selecionadas:
    if len(localidades_selecionadas) <= 3:
        filtros_ativos.append(f"📍 Loc: {', '.join(localidades_selecionadas)}")
    else:
        filtros_ativos.append(f"📍 Loc: {len(localidades_selecionadas)} selecionadas")

# Produtos
if categorias:
    filtros_ativos.append(f"📦 Cat: {len(categorias)} sel.")
if subcategorias:
    filtros_ativos.append(f"📦 SubCat: {len(subcategorias)} sel.")
if genericos != "Todos":
    filtros_ativos.append(f"💊 Genérico: {genericos}")
if marcas:
    filtros_ativos.append(f"🏷️ Marca: {len(marcas)} sel.")

# Demografia
if sexo:
    filtros_ativos.append(f"👥 Sexo: {', '.join(sexo)}")
if faixa_etaria:
    filtros_ativos.append(f"🎂 Idade: {len(faixa_etaria)} faixas")

# Transação
if tipo_pagamento:
    filtros_ativos.append(f"💳 Pag: {', '.join(tipo_pagamento)}")
if grau_certeza:
    filtros_ativos.append(f"🎯 Geo: {len(grau_certeza)} níveis")

texto_filtros = " | ".join(filtros_ativos) if filtros_ativos else "Todos os dados (Sem filtros restritivos)"

# --- Exibição do Contexto Global ---
st.markdown("### 🧭 Contexto da Análise")
st.info(f"**Filtros Aplicados:** {texto_filtros}")

# --- KPIs Principais ---
col1, col2, col3, col4 = st.columns(4)

total_faturado = df_filtered['Total_Faturado_com_Desconto'].sum()
num_atendimentos = df_filtered['Atendimento'].nunique()
num_vendas = df_filtered['Venda'].nunique()
ticket_medio = total_faturado / num_atendimentos if num_atendimentos > 0 else 0

col1.metric("💰 Total Faturado", f"{total_faturado:,.2f} €")
col2.metric("🧾 Nº Atendimentos", f"{num_atendimentos:,}")
col3.metric("🛒 Nº Vendas", f"{num_vendas:,}")
col4.metric("📈 Ticket Médio", f"{ticket_medio:,.2f} €")

# --- Agregação para o Mapa ---

if metrica_selecionada == "Total Faturado (€)":
    col_metrica_nome = 'Faturado'
    # Adicionamos {customdata[1]} para Localidade. Index 0 é métrica, Index 1 é Localidade.
    hover_template_base = "<b>%{customdata[1]}</b><br>Faturado: %{customdata[0]:.2f} €"
else:
    col_metrica_nome = 'Num_Atendimentos'
    hover_template_base = "<b>%{customdata[1]}</b><br>Atendimentos: %{customdata[0]}"

# Lógica de Agrupamento Diferenciada
# Adicionamos 'Localidade' ao agrupamento para garantir que aparece no tooltip corretamente
if modo_comparativo:
    # No modo comparativo, precisamos separar por Ano e Localidade
    group_cols = ['LATITUDE', 'LONGITUDE', 'Localidade', 'Ano']
else:
    # No modo normal, somamos tudo para aquela localização (independente do ano)
    group_cols = ['LATITUDE', 'LONGITUDE', 'Localidade']

df_grouped = df_filtered.groupby(group_cols).agg({
    'Total_Faturado_com_Desconto': 'sum',
    'Atendimento': 'nunique'
}).reset_index()

df_grouped.rename(columns={
    'Total_Faturado_com_Desconto': 'Faturado',
    'Atendimento': 'Num_Atendimentos'
}, inplace=True)

# Calcular Size Metric e garantir não-negatividade
if metrica_selecionada == "Total Faturado (€)":
    df_grouped['Size_Metric'] = df_grouped['Faturado'].clip(lower=0)
else:
    df_grouped['Size_Metric'] = df_grouped['Num_Atendimentos'].clip(lower=0)

# --- Mapa Plotly ---
st.subheader(f"🗺️ Mapa Geoespacial: {metrica_selecionada}")
st.caption(f"🔎 **Filtros neste mapa:** {texto_filtros}")

# Usar mediana do dataset filtrado (ponderado por ocorrência) para centrar onde há mais dados
lat_center = df_filtered['LATITUDE'].median()
lon_center = df_filtered['LONGITUDE'].median()

fig = go.Figure()

# Fator de escala para as bolhas
max_val = df_grouped['Size_Metric'].max()
if max_val == 0: max_val = 1 # Prevenir divisão por zero
sizeref_val = 2.0 * max_val / (40.**2)

if modo_comparativo:
    # Layer 2024
    df_2024 = df_grouped[df_grouped['Ano'] == 2024]
    if not df_2024.empty:
        fig.add_trace(go.Scattermap(
            lat=df_2024['LATITUDE'], lon=df_2024['LONGITUDE'], mode='markers',
            marker=go.scattermap.Marker(
                size=df_2024['Size_Metric'], sizemode='area', sizeref=sizeref_val,
                color='rgba(10, 100, 200, 0.6)', # Azul mais distinto e translúcido
                opacity=0.7
            ),
            # Passamos Metric e Localidade no customdata
            text=df_2024['Size_Metric'], 
            customdata=df_2024[[col_metrica_nome, 'Localidade']],
            name='2024 (Homólogo)',
            hovertemplate=f"<b>2024</b><br>{hover_template_base}<br>Lat: %{{lat}}<br>Lon: %{{lon}}<extra></extra>"
        ))

    # Layer 2025
    df_2025 = df_grouped[df_grouped['Ano'] == 2025]
    if not df_2025.empty:
        fig.add_trace(go.Scattermap(
            lat=df_2025['LATITUDE'], lon=df_2025['LONGITUDE'], mode='markers',
            marker=go.scattermap.Marker(
                size=df_2025['Size_Metric'], sizemode='area', sizeref=sizeref_val,
                color='rgba(255, 0, 0, 0.9)', # Vermelho puro e vivo
                opacity=0.9
            ),
            text=df_2025['Size_Metric'], 
            customdata=df_2025[[col_metrica_nome, 'Localidade']],
            name='2025 (Atual)',
            hovertemplate=f"<b>2025</b><br>{hover_template_base}<br>Lat: %{{lat}}<br>Lon: %{{lon}}<extra></extra>"
        ))

else:
    # Modo Unificado
    fig.add_trace(go.Scattermap(
        lat=df_grouped['LATITUDE'], lon=df_grouped['LONGITUDE'], mode='markers',
        marker=go.scattermap.Marker(
            size=df_grouped['Size_Metric'], sizemode='area', sizeref=sizeref_val,
            color=df_grouped['Size_Metric'], colorscale='Viridis', showscale=True,
            opacity=0.8
        ),
        text=df_grouped['Size_Metric'], 
        customdata=df_grouped[[col_metrica_nome, 'Localidade']],
        name='Vendas',
        hovertemplate=f"<b>Local</b><br>{hover_template_base}<br>Lat: %{{lat}}<br>Lon: %{{lon}}<extra></extra>"
    ))

# Configuração do Estilo do Mapa
map_config = dict(center=dict(lat=lat_center, lon=lon_center), zoom=6, uirevision='no_reset')
layout_args = dict(
    margin={"r":0,"t":0,"l":0,"b":0},
    height=600,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
    uirevision='no_reset' # Mantém o estado do zoom/pan entre atualizações
)

if estilo_mapa == "Satélite":
    map_config["style"] = "white-bg"
    map_config["layers"] = [
        {
            "below": 'traces',
            "sourcetype": "raster",
            "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]
        }
    ]
else:
    styles_map = {
        "Claro (Padrão)": "carto-positron",
        "Escuro": "carto-darkmatter",
        "Detalhado (OpenStreet)": "open-street-map"
    }
    map_config["style"] = styles_map.get(estilo_mapa, "carto-positron")

fig.update_layout(
    map=map_config,
    **layout_args
)

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- Função Auxiliar de Plotagem (Comparativo vs Normal) ---
def plot_top_analysis(df_in, group_col, value_col, label_col):
    """
    Gera um gráfico de barras (Top 10) inteligente.
    - Se Modo Comparativo: Top 10 baseados em 2025, mostrando barras agrupadas (2024 vs 2025).
    - Se Modo Normal: Top 10 baseados na soma total, barra simples.
    """
    if df_in.empty:
        return None

    if modo_comparativo:
        # 1. Identificar Top 10 com base APENAS em 2025
        df_2025 = df_in[df_in['Ano'] == 2025]
        if df_2025.empty:
            return None
        
        top_10_stats = df_2025.groupby(group_col)[value_col].sum().reset_index()
        top_10_names = top_10_stats.sort_values(value_col, ascending=False).head(10)[group_col].tolist()
        
        # 2. Filtrar o dataset original para incluir apenas esses nomes (trazendo dados de 2024 e 2025)
        df_chart = df_in[df_in[group_col].isin(top_10_names)].copy()
        
        # 3. Agrupar para garantir dados limpos para o gráfico
        df_chart_grouped = df_chart.groupby([group_col, 'Ano'])[value_col].sum().reset_index()
        
        # Garantir que 'Ano' é string para que o Plotly trate como categoria discreta (cores separadas e agrupamento)
        df_chart_grouped['Ano'] = df_chart_grouped['Ano'].astype(str)
        
        # 4. Plotar (Barras Agrupadas)
        fig = px.bar(
            df_chart_grouped, 
            x=value_col, 
            y=group_col, 
            color='Ano', 
            barmode='group',
            orientation='h',
            text_auto='.2s',
            category_orders={group_col: top_10_names}, # Garante a ordem do Top 10 de 2025
            labels={value_col: 'Faturação (€)', group_col: label_col},
            # Cores distintas para facilitar comparação
            color_discrete_map={'2024': '#1f77b4', '2025': '#d62728'}
        )
    else:
        # Modo Normal: Soma simples
        df_stats = df_in.groupby(group_col)[value_col].sum().reset_index()
        df_chart = df_stats.sort_values(value_col, ascending=False).head(10)
        
        fig = px.bar(
            df_chart, 
            x=value_col, 
            y=group_col, 
            orientation='h', 
            text_auto='.2s',
            labels={value_col: 'Faturação (€)', group_col: label_col}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
    
    return fig

# --- Gráficos Extra ---
st.markdown("---")
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("🏆 Top Categorias")
    st.caption(f"🔎 **Filtros:** {texto_filtros}")
    
    fig_cat = plot_top_analysis(df_filtered, 'CAT', 'Total_Faturado_com_Desconto', 'Categoria')
    
    if fig_cat:
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Sem dados para categorias.")

with col_g2:
    st.subheader("📅 Evolução Mensal")
    st.caption(f"🔎 **Filtros:** {texto_filtros}")
    
    monthly_sales = df_filtered.groupby(['Ano', 'Mes_Num', 'Nome do Mês'])['Total_Faturado_com_Desconto'].sum().reset_index()
    monthly_sales = monthly_sales.sort_values(['Ano', 'Mes_Num'])
    
    if not monthly_sales.empty:
        fig_line = px.line(monthly_sales, x='Nome do Mês', y='Total_Faturado_com_Desconto', color='Ano', markers=True,
                           labels={'Total_Faturado_com_Desconto': 'Faturação (€)'})
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Sem dados mensais suficientes.")

# --- Gráfico Top Marcas (Novo) ---
st.markdown("---")
st.subheader("🏷️ Top 10 Marcas (por Faturação)")
st.caption(f"🔎 **Filtros:** {texto_filtros}")
if modo_comparativo:
    st.markdown("*Ordenado pelo Top 10 de 2025 (Comparação 2024/2025)*")
else:
    st.markdown("*Filtrado pela seleção atual*")

fig_brand = plot_top_analysis(df_filtered, 'MARCA', 'Total_Faturado_com_Desconto', 'Marca')

if fig_brand:
    st.plotly_chart(fig_brand, use_container_width=True)
else:
    st.info("Sem dados de marca disponíveis para os filtros selecionados.")
