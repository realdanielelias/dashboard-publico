import streamlit as st
import pandas as pd
import subprocess  
from supabase import create_client

# conecta o Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# painel lateral
st.sidebar.header("⚙️ Administração do Sistema")

# botao para baixar as informacoes
if st.sidebar.button("🔄 Baixar dados do Siconfi"):
    with st.sidebar.status("Obtendo dados...", expanded=True) as status:
        try:
            resultado = subprocess.run(
                ["python", "etl/siconfi.py"], 
                capture_output=True, 
                text=True,
                check=True
            )
            
            st.code(resultado.stdout)
            status.update(label="✅ Download finalizado!", state="complete", expanded=False)
            
            # limpa o cache para atualizar a tela do banco
            st.cache_data.clear()
            st.rerun()
            
        except subprocess.CalledProcessError as e:
            st.error(f"Erro ao executar: {e.stderr}")
            status.update(label="❌ Erro no download", state="error")

st.title("📊 Painel de Análise Fiscal - Educação")
st.markdown("Dados extraídos diretamente do Siconfi (RREO Anexo 08)")

# puxa os dados da tabela cria data frames
@st.cache_data(ttl=600)
def carregar_dados():
    res_mun = supabase.table("dim_municipio").select("*").execute()
    df_mun = pd.DataFrame(res_mun.data)
    
    res_fis = supabase.table("fato_siconfi_fiscal").select("*").execute()
    df_fis = pd.DataFrame(res_fis.data)
    
    res_con = supabase.table("dim_legislacao_contas").select("cod_conta", "nome_conta").execute()
    df_con = pd.DataFrame(res_con.data)
    
    if not df_mun.empty and not df_fis.empty:
        df_unido = pd.merge(df_fis, df_mun, on="id_ibge")
        if not df_con.empty:
            df_unido = pd.merge(df_unido, df_con, on="cod_conta", how="left")
            df_unido["nome_conta"] = df_unido["nome_conta"].fillna(df_unido["cod_conta"])
        else:
            df_unido["nome_conta"] = df_unido["cod_conta"]
        return df_unido
    return pd.DataFrame()

df_completo = carregar_dados()

if df_completo.empty:
    st.warning("⚠️ Nenhum dado encontrado. Use o botão na barra lateral para baixar dados!")
else:
    # elementos visuais
    cidades = df_completo["nome_municipio"].unique()
    cidade_selecionada = st.selectbox("Selecione o Município para análise:", cidades)
    
    # filtra cidade
    df_cidade = df_completo[df_completo["nome_municipio"] == cidade_selecionada]
    
    info_cidade = df_cidade.iloc[0]
    
    # extrai ano
    ano_detectado = str(info_cidade["id_tempo"])[:4]
    
    # Filtra apenas o acumulado "Até o Bimestre" e ignora a conta 'educacao' mãe para somar apenas os detalhes reais
    df_calculo_real = df_cidade[
        (df_cidade['estagio_orcamentario'].str.contains('ATÉ O BIMESTRE', case=False, na=False)) & 
        (df_cidade['cod_conta'] != 'educacao') &
        (df_cidade['cod_conta'] != 'RREO2TotalDespesas') &
        (df_cidade['cod_conta'] != 'RREO2TotalDespesasIntra')
    ]
    
    # se o filtro detalhado retornar vazio, usa o bloco "No Bimestre" ou a conta cheia como fallback
    if df_calculo_real.empty:
        df_fallback = df_cidade[
            (df_cidade['cod_conta'] == 'educacao') | 
            (df_cidade['cod_conta'] == 'RREO2TotalDespesas') | 
            (df_cidade['cod_conta'] == 'RREO2TotalDespesasIntra')
        ]
        total_mde = df_fallback[df_fallback['estagio_orcamentario'].str.contains('ATÉ O BIMESTRE', case=False, na=False)]["valor"].sum()
        if total_mde == 0:
            total_mde = df_fallback["valor"].sum() / 2 if not df_fallback.empty else 0
    else:
        total_mde = df_calculo_real["valor"].sum()
    
    st.subheader(f"Resultados de {cidade_selecionada} - Ano {ano_detectado}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="População Estimada", value=f"{info_cidade['populacao']:,} hab")
        st.caption(f"Porte do Município: {info_cidade['porte_municipio']}")
        
    with col2:
        st.metric(
            label="Total Investido em Educação (MDE)", 
            value=f"R$ {total_mde:,.2f}"
        )
    
    st.markdown("---")
    st.subheader("💡 Distribuição de Gastos por Categoria")
    
    df_categorias_filtrado = df_cidade[
        (df_cidade['estagio_orcamentario'].str.contains('ATÉ O BIMESTRE', case=False, na=False)) & 
        (df_cidade['cod_conta'] != 'educacao') &
        (df_cidade['cod_conta'] != 'RREO2TotalDespesas') &
        (df_cidade['cod_conta'] != 'RREO2TotalDespesasIntra')
    ]
    if df_categorias_filtrado.empty:
        df_categorias_filtrado = df_cidade
        
    df_categorias = df_categorias_filtrado.groupby('nome_conta', as_index=False)['valor'].sum()
    df_categorias = df_categorias.rename(columns={
        'nome_conta': 'Categoria de Despesa',
        'valor': 'Total (R$)'
    })
    
    st.bar_chart(data=df_categorias, x='Categoria de Despesa', y='Total (R$)')
    
    with st.expander("📄 Ver detalhamento em tabela"):
        st.dataframe(
            df_categorias.style.format({'Total (R$)': 'R$ {:,.2f}'}),
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("---")
    st.subheader("Comparação de Investimento entre as Cidades")
    
    df_grafico_filtrado = df_completo[
        (df_completo['estagio_orcamentario'].str.contains('ATÉ O BIMESTRE', case=False, na=False)) & 
        (df_completo['cod_conta'] != 'educacao') &
        (df_completo['cod_conta'] != 'RREO2TotalDespesas') &
        (df_completo['cod_conta'] != 'RREO2TotalDespesasIntra')
    ]
    if df_grafico_filtrado.empty:
        df_grafico_filtrado = df_completo
        
    df_grafico = pd.DataFrame(df_grafico_filtrado.groupby('nome_municipio', as_index=False)['valor'].sum())
    df_grafico = df_grafico.rename(columns={
        'nome_municipio': 'Município', 
        'valor': 'Total Liquidado (R$)'
    })
    
    st.bar_chart(data=df_grafico, x='Município', y='Total Liquidado (R$)')