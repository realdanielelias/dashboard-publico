'''
PAINEL DE GESTAO E EFICIENCIA DA EDUCACAO MUNICIPAL
DESC: INTERFACE ANALITICA EXPANDIDA COM MULTIPLOS PONTOS DE ANALISE FISCAL, DEMOGRAFICA E PEDAGOGICA
FONTE: POSTGRESQL / SUPABASE (VIEWS ANALITICAS DA CAMADA GOLD)
'''

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

# Configurar layout e titulo da pagina
st.set_page_config(
    page_title="Painel de Eficiência da Educação Municipal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Conectar ao Supabase usando credenciais seguras
@st.cache_resource
def init_connection():
  url = st.secrets["supabase"]["url"]
  key = st.secrets["supabase"]["key"]
  return create_client(url, key)


supabase = init_connection()


# Carregar dados consolidados das views analiticas da camada Gold
@st.cache_data(ttl=600)
def carregar_dados_dw():
  # Consultar view de KPIs gerais
  res_kpis = (
      supabase.table("vw_fato_educacao_kpis")
      .select("*")
      .limit(5000)
      .execute()
  )
  df_kpis = pd.DataFrame(res_kpis.data)

  # Consultar view de benchmark municipal e estadual
  res_bench = (
      supabase.table("vw_benchmark_municipal_estadual")
      .select("*")
      .limit(5000)
      .execute()
  )
  df_bench = pd.DataFrame(res_bench.data)

  return df_kpis, df_bench


df_kpis, df_bench = carregar_dados_dw()

# Interromper execucao caso nao existam dados no banco
if df_kpis.empty or df_bench.empty:
  st.error(
      "⚠️ Não foi possível carregar os dados das Views Analíticas no Supabase."
  )
  st.info(
      "Verifique se o script DDL da Camada Gold foi executado com sucesso e se"
      " há dados carregados."
  )
  st.stop()

# Configurar filtros e navegacao na barra lateral
st.sidebar.title("🎓 Gestão Educacional")
st.sidebar.caption("Sistema de Apoio à Decisão Estratégica")

# Obter lista de municipios e definir Marilia como padrao
municipios_disponiveis = sorted(df_kpis["nome_municipio"].dropna().unique())
idx_padrao = (
    municipios_disponiveis.index("Marília")
    if "Marília" in municipios_disponiveis
    else 0
)

municipio_sel = st.sidebar.selectbox(
    "📍 Município em Análise:",
    options=municipios_disponiveis,
    index=idx_padrao,
)

# Filtrar anos disponiveis em ordem decrescente
anos_disponiveis = sorted(df_kpis["ano"].dropna().unique(), reverse=True)
ano_sel = st.sidebar.selectbox("📅 Exercício de Referência:", anos_disponiveis)

# Filtrar registros do municipio e ano selecionados para a rede municipal
df_mun_ano = df_kpis[
    (df_kpis["nome_municipio"] == municipio_sel)
    & (df_kpis["ano"] == ano_sel)
    & (df_kpis["nome_rede"] == "Municipal")
]

# Obter metadados cadastrais do municipio selecionado
info_mun = df_kpis[df_kpis["nome_municipio"] == municipio_sel].iloc[0]

# Exibir informacoes cadastrais na barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Grupo Analítico:** `{info_mun['grupo_analitico']}`")
st.sidebar.markdown(f"**Porte:** `{info_mun['porte_populacional']}`")
st.sidebar.markdown(
    f"**População (2022):** `{info_mun['populacao_censo_2022']:,} hab`"
)

# Exibir cabecalho executivo principal
st.title(f"📊 Painel de Eficiência e Inteligência da Educação: {municipio_sel}")
st.markdown(
    f"**Exercício:** {ano_sel} | **Grupo de Comparabilidade:**"
    f" {info_mun['grupo_analitico']} | **Recorte Amostral:** 26 Municípios de SP"
)

# Definir abas das tres camadas de decisao
tab_exec, tab_diag, tab_pedag = st.tabs([
    "🏛️ 1. Visão Executiva & Orçamento",
    "🎯 2. Diagnóstico & Peer Group",
    "🏫 3. Responsabilidade Federativa & SAEB",
])

# ==============================================================================
# ABA 1: VISAO EXECUTIVA E ORCAMENTO
# ==============================================================================
with tab_exec:
  st.subheader("Indicadores-Chave de Desempenho e Eficiência (KPIs)")

  if df_mun_ano.empty:
    st.warning(
        f"Dados não consolidados para a rede municipal de {municipio_sel} no"
        f" exercício {ano_sel}."
    )
  else:
    kpi = df_mun_ano.iloc[0]

    # Extrair valores fiscais e de custo
    desp_liq = kpi.get("despesa_liquidada_educacao") or 0
    desp_emp = kpi.get("despesa_empenhada_educacao") or 0
    custo_fund = kpi.get("custo_aluno_fundamental")
    custo_inf = kpi.get("custo_aluno_infantil")
    delta_ideb = kpi.get("delta_meta_iniciais")

    # Calcular taxa de execucao orcamentaria
    taxa_exec = (desp_liq / desp_emp * 100) if desp_emp > 0 else 0

    # Exibir cards executivos
    col1, col2, col3, col4 = st.columns(4)

    with col1:
      st.metric(
          label="Orçamento Liquidado (Total)",
          value=f"R$ {desp_liq:,.2f}".replace(",", "X")
          .replace(".", ",")
          .replace("X", "."),
          help="Despesa liquidada consolidada na Função 12 (Educação) - Siconfi",
      )
      st.caption(f"Taxa de Execução (Liq/Emp): {taxa_exec:.1f}%")

    with col2:
      v_fund = (
          f"R$ {custo_fund:,.2f}".replace(",", "X")
          .replace(".", ",")
          .replace("X", ".")
          if pd.notna(custo_fund)
          else "N/D"
      )
      st.metric(
          label="Custo Aluno Fundamental",
          value=v_fund,
          help="Subfunção 361 dividida pelas matrículas dos Anos Iniciais e Finais",
      )
      mat_fund_tot = kpi.get("mat_fundamental_total") or 0
      st.caption(f"Matrículas Atendidas: {int(mat_fund_tot):,} alunos")

    with col3:
      v_inf = (
          f"R$ {custo_inf:,.2f}".replace(",", "X")
          .replace(".", ",")
          .replace("X", ".")
          if pd.notna(custo_inf)
          else "N/D"
      )
      st.metric(
          label="Custo Aluno Infantil",
          value=v_inf,
          help="Subfunção 365 dividida por creche e pré-escola",
      )
      mat_inf_tot = kpi.get("mat_infantil_total") or 0
      st.caption(f"Matrículas Atendidas: {int(mat_inf_tot):,} alunos")

    with col4:
      if pd.notna(delta_ideb):
        st.metric(
            label="IDEB Anos Iniciais",
            value=f"{kpi.get('ideb_iniciais', 0):.1f}",
            delta=f"{delta_ideb:+.2f} pts meta",
        )
        st.caption(f"Meta INEP: {kpi.get('ideb_meta_iniciais', 0):.1f} pts")
      else:
        st.metric(
            label="IDEB Anos Iniciais",
            value="Interstício",
            help="Exercício sem ciclo SAEB",
        )
        st.caption("Aplicação Bienal")

    st.markdown("---")

    # Graficos em duas colunas: Execucao Orcamentaria e Composicao por Subfuncao
    c_g1, c_g2 = st.columns([3, 2])

    with c_g1:
      st.markdown("#### 1. Trajetória Orçamentária: Empenhado vs. Liquidado")
      df_mun_hist = df_kpis[
          (df_kpis["nome_municipio"] == municipio_sel)
          & (df_kpis["nome_rede"] == "Municipal")
      ].sort_values("ano")

      fig_exec = go.Figure()
      fig_exec.add_trace(
          go.Bar(
              x=df_mun_hist["ano"],
              y=df_mun_hist["despesa_empenhada_educacao"],
              name="Despesa Empenhada",
              marker_color="#93C5FD",
          )
      )
      fig_exec.add_trace(
          go.Bar(
              x=df_mun_hist["ano"],
              y=df_mun_hist["despesa_liquidada_educacao"],
              name="Despesa Liquidada",
              marker_color="#1E3A8A",
          )
      )
      fig_exec.update_layout(
          barmode="group",
          template="plotly_white",
          height=360,
          legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
          margin=dict(l=30, r=20, t=30, b=30),
      )
      st.plotly_chart(fig_exec, use_container_width=True)

    with c_g2:
      st.markdown(f"#### 2. Composição do Gasto por Subfunção ({ano_sel})")
      sub_fund = kpi.get("desp_liq_fundamental") or 0
      sub_inf = kpi.get("desp_liq_infantil") or 0
      sub_outras = max(0, desp_liq - sub_fund - sub_inf)

      if (sub_fund + sub_inf + sub_outras) > 0:
        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=[
                        "Fundamental (Subf. 361)",
                        "Infantil (Subf. 365)",
                        "Demais Ações / Adm.",
                    ],
                    values=[sub_fund, sub_inf, sub_outras],
                    hole=0.55,
                    marker_colors=["#1E40AF", "#10B981", "#9CA3AF"],
                )
            ]
        )
        fig_donut.update_layout(
            template="plotly_white",
            height=360,
            margin=dict(l=20, r=20, t=30, b=30),
            legend=dict(orientation="h", y=-0.1),
        )
        st.plotly_chart(fig_donut, use_container_width=True)
      else:
        st.info("Despesas por subfunção não discriminadas neste exercício.")

    # Densidade de Recursos e Insumos Escolares com verificacao defensiva
    st.markdown("#### 3. Densidade de Insumos: Alunos por Turma e por Docente")
    col_ins1, col_ins2, col_ins3, col_ins4 = st.columns(4)

    turmas_iniciais = kpi.get("turmas_iniciais") or 0
    mat_iniciais = kpi.get("mat_anos_iniciais") or 0
    doc_iniciais = kpi.get("docentes_iniciais") or 0

    turmas_finais = kpi.get("turmas_finais") or 0
    mat_finais = kpi.get("mat_anos_finais") or 0
    doc_finais = kpi.get("docentes_finais") or 0

    ratio_turma_ini = (mat_iniciais / turmas_iniciais) if turmas_iniciais > 0 else None
    ratio_doc_ini = (mat_iniciais / doc_iniciais) if doc_iniciais > 0 else None
    ratio_turma_fin = (mat_finais / turmas_finais) if turmas_finais > 0 else None
    ratio_doc_fin = (mat_finais / doc_finais) if doc_finais > 0 else None

    col_ins1.metric(
        "Alunos / Turma (Iniciais)",
        f"{ratio_turma_ini:.1f}" if ratio_turma_ini is not None else "N/D",
    )
    col_ins2.metric(
        "Alunos / Docente (Iniciais)",
        f"{ratio_doc_ini:.1f}" if ratio_doc_ini is not None else "N/D",
    )
    col_ins3.metric(
        "Alunos / Turma (Finais)",
        f"{ratio_turma_fin:.1f}" if ratio_turma_fin is not None else "N/D",
    )
    col_ins4.metric(
        "Alunos / Docente (Finais)",
        f"{ratio_doc_fin:.1f}" if ratio_doc_fin is not None else "N/D",
    )

# ==============================================================================
# ABA 2: DIAGNOSTICO E PEER GROUP
# ==============================================================================
with tab_diag:
  st.subheader("Matriz de Eficiência e Equidade Socioeconômica")

  # Controles de filtragem da amostra
  col_f1, col_f2 = st.columns([3, 2])
  with col_f1:
    grupos = ["Todos os Grupos"] + list(
        df_kpis["grupo_analitico"].dropna().unique()
    )
    grupo_filtro = st.selectbox("Filtrar Amostra por Grupo:", grupos, index=0)
  with col_f2:
    st.write("")
    st.write("")
    fixar_marilia = st.checkbox(
        "Fixar Marília como referência no gráfico",
        value=True,
        help="Garante que Marília permanece visível mesmo com grupos filtrados.",
    )

  df_base_ano = df_kpis[
      (df_kpis["ano"] == ano_sel) & (df_kpis["nome_rede"] == "Municipal")
  ].copy()

  if grupo_filtro != "Todos os Grupos":
    df_comp = df_base_ano[df_base_ano["grupo_analitico"] == grupo_filtro].copy()
    if fixar_marilia:
      reg_marilia = df_base_ano[df_base_ano["nome_municipio"] == "Marília"]
      if not reg_marilia.empty:
        df_comp = pd.concat([df_comp, reg_marilia]).drop_duplicates(
            subset=["cod_ibge"]
        )
  else:
    df_comp = df_base_ano.copy()

  df_scatter = df_comp.dropna(
      subset=["custo_aluno_fundamental", "ideb_iniciais"]
  ).copy()

  if df_scatter.empty:
    st.info(
        f"No exercício {ano_sel} não há registro concomitante de notas do IDEB"
        " (avaliação bienal) para gerar os quadrantes de eficiência."
    )
  else:
    # 4. Matriz Parametrica de Eficiencia (Custo x IDEB)
    st.markdown("#### 4. Matriz Paramétrica de Eficiência (Custo x IDEB)")
    media_custo = df_scatter["custo_aluno_fundamental"].mean()
    media_ideb = df_scatter["ideb_iniciais"].mean()

    # Identificar dados e classificar quadrante estrategico de Marilia
    dados_marilia = df_scatter[df_scatter["nome_municipio"] == "Marília"]
    tem_marilia = not dados_marilia.empty

    quadrante_marilia = "Não mapeado"
    if tem_marilia:
      c_mar = dados_marilia.iloc[0]["custo_aluno_fundamental"]
      i_mar = dados_marilia.iloc[0]["ideb_iniciais"]
      if c_mar <= media_custo and i_mar >= media_ideb:
        quadrante_marilia = "Alta Eficiência"
      elif c_mar > media_custo and i_mar >= media_ideb:
        quadrante_marilia = "Alto Investimento / Retorno"
      elif c_mar <= media_custo and i_mar < media_ideb:
        quadrante_marilia = "Restrição Orçamental"
      else:
        quadrante_marilia = "Alerta de Ineficiência"

    # Exibir cartoes de sintese da matriz
    with st.container(border=True):
      c_m1, c_m2, c_m3 = st.columns(3)
      c_m1.metric(
          "Custo Médio da Amostra",
          f"R$ {media_custo:,.2f}".replace(",", "X")
          .replace(".", ",")
          .replace("X", "."),
      )
      c_m2.metric("IDEB Médio da Amostra", f"{media_ideb:.2f} pts")
      c_m3.metric("Posição Estratégica (Marília)", quadrante_marilia)

    # Limites dinamicos dos eixos
    x_min = df_scatter["custo_aluno_fundamental"].min() * 0.88
    x_max = df_scatter["custo_aluno_fundamental"].max() * 1.12
    y_min = max(3.0, df_scatter["ideb_iniciais"].min() - 0.4)
    y_max = min(10.0, df_scatter["ideb_iniciais"].max() + 0.4)

    fig_disp = px.scatter(
        df_scatter,
        x="custo_aluno_fundamental",
        y="ideb_iniciais",
        text="nome_municipio",
        size="populacao_censo_2022",
        color="grupo_analitico",
        color_discrete_map={
            "Polo Central": "#2563EB",
            "Região Imediata": "#10B981",
            "Polo Centro-Oeste": "#F59E0B",
            "Peer Group Homólogo": "#6366F1",
        },
        labels={
            "custo_aluno_fundamental": "Custo Aluno-Ano Fundamental (R$)",
            "ideb_iniciais": "Nota IDEB Anos Iniciais",
            "grupo_analitico": "Grupo",
        },
    )

    # Sombreamento dos 4 quadrantes
    fig_disp.add_shape(
        type="rect",
        x0=x_min,
        x1=media_custo,
        y0=media_ideb,
        y1=y_max,
        fillcolor="rgba(16, 185, 129, 0.07)",
        layer="below",
        line_width=0,
    )
    fig_disp.add_shape(
        type="rect",
        x0=media_custo,
        x1=x_max,
        y0=media_ideb,
        y1=y_max,
        fillcolor="rgba(59, 130, 246, 0.05)",
        layer="below",
        line_width=0,
    )
    fig_disp.add_shape(
        type="rect",
        x0=x_min,
        x1=media_custo,
        y0=y_min,
        y1=media_ideb,
        fillcolor="rgba(245, 158, 11, 0.05)",
        layer="below",
        line_width=0,
    )
    fig_disp.add_shape(
        type="rect",
        x0=media_custo,
        x1=x_max,
        y0=y_min,
        y1=media_ideb,
        fillcolor="rgba(239, 68, 68, 0.07)",
        layer="below",
        line_width=0,
    )

    # Linhas de corte medio
    fig_disp.add_vline(
        x=media_custo,
        line_dash="dash",
        line_color="#6B7280",
        annotation_text="Custo Médio",
        annotation_position="top right",
    )
    fig_disp.add_hline(
        y=media_ideb,
        line_dash="dash",
        line_color="#6B7280",
        annotation_text="IDEB Médio",
        annotation_position="bottom right",
    )

    # Rotulos dos quadrantes
    fig_disp.add_annotation(
        x=x_min + (media_custo - x_min) * 0.1,
        y=y_max - 0.1,
        text="<b>ALTA EFICIÊNCIA</b>",
        showarrow=False,
        font=dict(size=11, color="#059669"),
    )
    fig_disp.add_annotation(
        x=x_max - (x_max - media_custo) * 0.1,
        y=y_max - 0.1,
        text="<b>ALTO INVESTIMENTO</b>",
        showarrow=False,
        font=dict(size=11, color="#2563EB"),
    )
    fig_disp.add_annotation(
        x=x_min + (media_custo - x_min) * 0.1,
        y=y_min + 0.1,
        text="<b>RESTRIÇÃO / RISCO</b>",
        showarrow=False,
        font=dict(size=11, color="#D97706"),
    )
    fig_disp.add_annotation(
        x=x_max - (x_max - media_custo) * 0.1,
        y=y_min + 0.1,
        text="<b>ALERTA DE INEFICIÊNCIA</b>",
        showarrow=False,
        font=dict(size=11, color="#DC2626"),
    )

    # Destaque de Marilia com estrela vermelha
    if tem_marilia:
      mar = dados_marilia.iloc[0]
      fig_disp.add_trace(
          go.Scatter(
              x=[mar["custo_aluno_fundamental"]],
              y=[mar["ideb_iniciais"]],
              mode="markers",
              marker=dict(
                  symbol="star",
                  size=22,
                  color="#DC2626",
                  line=dict(color="#FFFFFF", width=2),
              ),
              name="Marília (Alvo)",
          )
      )
      fig_disp.add_annotation(
          x=mar["custo_aluno_fundamental"],
          y=mar["ideb_iniciais"],
          text="<b>📍 Marília</b>",
          showarrow=True,
          arrowhead=2,
          arrowsize=1.2,
          arrowwidth=2,
          arrowcolor="#DC2626",
          ax=40,
          ay=-40,
          bgcolor="rgba(255, 255, 255, 0.9)",
          bordercolor="#DC2626",
          borderwidth=1,
          font=dict(color="#DC2626", size=12),
      )

    fig_disp.update_traces(
        textposition="top center",
        hovertemplate=(
            "<b>%{text}</b><br>"
            + "──────────────────────────<br>"
            + "<b>Custo Aluno-Ano:</b> R$ %{x:,.2f}<br>"
            + "<b>Nota IDEB:</b> %{y:.2f} pts<br>"
            + "<extra></extra>"
        ),
    )
    fig_disp.update_layout(
        template="plotly_white",
        height=540,
        xaxis=dict(
            range=[x_min, x_max],
            title="Custo Aluno-Ano Fundamental (R$)",
            tickformat=",.0f",
            gridcolor="#F3F4F6",
        ),
        yaxis=dict(
            range=[y_min, y_max],
            title="Nota IDEB (Anos Iniciais)",
            gridcolor="#F3F4F6",
        ),
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
        margin=dict(l=30, r=20, t=60, b=30),
    )
    st.plotly_chart(fig_disp, use_container_width=True)

    # 5. Grafico de Equidade e Nivel Socioeconomico (INSE x IDEB com carry-forward)
    st.markdown(
        "#### 5. Equidade Educacional: Superação da Vulnerabilidade (IDEB vs."
        " INSE)"
    )

    df_inse_comp = df_comp.copy()

    # Recuperar ultimo INSE valido por municipio para suprir lacuna de anos sem censo socioeconomico
    if "inse_score" in df_kpis.columns:
      df_ultimo_inse = (
          df_kpis.dropna(subset=["inse_score"])
          .sort_values("ano")
          .groupby("cod_ibge")
          .last()
          .reset_index()[["cod_ibge", "inse_score", "inse_classificacao"]]
      )

      if not df_ultimo_inse.empty:
        mapa_score = df_ultimo_inse.set_index("cod_ibge")["inse_score"]
        mapa_class = df_ultimo_inse.set_index("cod_ibge")["inse_classificacao"]

        df_inse_comp["inse_score"] = df_inse_comp["inse_score"].fillna(
            df_inse_comp["cod_ibge"].map(mapa_score)
        )
        df_inse_comp["inse_classificacao"] = df_inse_comp[
            "inse_classificacao"
        ].fillna(df_inse_comp["cod_ibge"].map(mapa_class))

    df_inse_scatter = df_inse_comp.dropna(
        subset=["inse_score", "ideb_iniciais"]
    ).copy()

    if not df_inse_scatter.empty:
      # Definir escala controlada de tamanho com base na populacao
      df_inse_scatter["tam_ponto"] = (
          df_inse_scatter["populacao_censo_2022"].fillna(10000).clip(lower=2000)
      )

      fig_inse = px.scatter(
          df_inse_scatter,
          x="inse_score",
          y="ideb_iniciais",
          text="nome_municipio",
          size="tam_ponto",
          size_max=24,
          color="inse_classificacao",
          hover_data={
              "inse_score": ":.2f",
              "ideb_iniciais": ":.2f",
              "tam_ponto": False,
              "populacao_censo_2022": True,
              "grupo_analitico": True,
          },
          labels={
              "inse_score": "Escore Contínuo INSE (Nível Socioeconômico)",
              "ideb_iniciais": "Nota IDEB Anos Iniciais",
              "inse_classificacao": "Classificação INSE",
          },
      )

      media_inse = df_inse_scatter["inse_score"].mean()
      media_ideb_inse = df_inse_scatter["ideb_iniciais"].mean()

      fig_inse.add_vline(
          x=media_inse,
          line_dash="dash",
          line_color="#9CA3AF",
          annotation_text="INSE Médio",
      )
      fig_inse.add_hline(
          y=media_ideb_inse,
          line_dash="dash",
          line_color="#9CA3AF",
          annotation_text="IDEB Médio",
      )

      # Destacar Marilia no grafico de equidade
      dados_marilia_inse = df_inse_scatter[
          df_inse_scatter["nome_municipio"] == "Marília"
      ]
      if not dados_marilia_inse.empty:
        mar_i = dados_marilia_inse.iloc[0]
        fig_inse.add_trace(
            go.Scatter(
                x=[mar_i["inse_score"]],
                y=[mar_i["ideb_iniciais"]],
                mode="markers",
                marker=dict(
                    symbol="star",
                    size=22,
                    color="#DC2626",
                    line=dict(color="#FFFFFF", width=2),
                ),
                name="Marília",
            )
        )

      fig_inse.update_traces(textposition="top center")
      fig_inse.update_layout(
          template="plotly_white",
          height=460,
          legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
          margin=dict(l=30, r=20, t=50, b=30),
      )
      st.plotly_chart(fig_inse, use_container_width=True)
    else:
      st.info(
          f"Dados de contexto socioeconômico (INSE) ou notas do IDEB não"
          f" disponíveis para {ano_sel}."
      )

  # 6. Benchmark de Inclusao e Composicao de Matriculas com tratamento defensivo
  st.markdown("#### 6. Compromisso Social: Taxa de Inclusão Escolar")

  # Extrair colunas com fallback defensivo para series de zeros
  mat_esp = df_comp.get(
      "mat_especial_classes_comuns", pd.Series(0, index=df_comp.index)
  ).fillna(0)
  mat_cr = df_comp.get("mat_creche", pd.Series(0, index=df_comp.index)).fillna(0)
  mat_pre = df_comp.get("mat_pre_escola", pd.Series(0, index=df_comp.index)).fillna(0)
  mat_ini = df_comp.get("mat_anos_iniciais", pd.Series(0, index=df_comp.index)).fillna(0)
  mat_fin = df_comp.get("mat_anos_finais", pd.Series(0, index=df_comp.index)).fillna(0)

  df_comp["mat_total_rede"] = mat_cr + mat_pre + mat_ini + mat_fin
  df_comp["tx_inclusao"] = np.where(
      df_comp["mat_total_rede"] > 0,
      (mat_esp / df_comp["mat_total_rede"]) * 100,
      0.0,
  )

  df_inc_rank = (
      df_comp[df_comp["mat_total_rede"] > 0]
      .sort_values("tx_inclusao", ascending=True)
      .tail(15)
  )

  if not df_inc_rank.empty and df_inc_rank["tx_inclusao"].sum() > 0:
    fig_inc = px.bar(
        df_inc_rank,
        x="tx_inclusao",
        y="nome_municipio",
        orientation="h",
        labels={
            "tx_inclusao": "Taxa de Matrículas em Educação Especial (%)",
            "nome_municipio": "Município",
        },
        color="tx_inclusao",
        color_continuous_scale="Blues",
    )
    fig_inc.update_layout(
        template="plotly_white",
        height=380,
        margin=dict(l=30, r=20, t=20, b=20),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_inc, use_container_width=True)
  else:
    st.info("Dados de educação especial não reportados para este exercício.")

# ==============================================================================
# ABA 3: RESPONSABILIDADE FEDERATIVA E SAEB
# ==============================================================================
with tab_pedag:
  st.subheader("Divisão Federativa e Diagnóstico Curricular Profundo (SAEB)")

  df_bench_mun = df_bench[
      (df_bench["nome_municipio"] == municipio_sel)
      & (df_bench["ano"] == ano_sel)
  ]

  if df_bench_mun.empty:
    st.warning("Dados comparativos federativos não disponíveis para este ano.")
  else:
    bench_data = df_bench_mun.iloc[0]

    # Cards comparativos federativos
    c_b1, c_b2, c_b3 = st.columns(3)
    c_b1.metric(
        "IDEB Municipal (Anos Iniciais)",
        f"{bench_data['ideb_iniciais_mun']:.2f}"
        if pd.notna(bench_data["ideb_iniciais_mun"])
        else "N/D",
    )
    c_b2.metric(
        "IDEB Estadual (Benchmark)",
        f"{bench_data['ideb_iniciais_est']:.2f}"
        if pd.notna(bench_data["ideb_iniciais_est"])
        else "N/D",
    )
    gap = bench_data.get("gap_ideb_mun_vs_est")
    c_b3.metric(
        "Diferencial Competitivo (Gap)",
        f"{gap:+.2f} pts" if pd.notna(gap) else "N/D",
    )

    st.markdown("---")

    # Graficos em duas colunas: Curricular e Transicao
    c_p1, c_p2 = st.columns(2)

    with c_p1:
      # 7. Diagnostico Curricular: Lingua Portuguesa vs Matematica
      st.markdown(
          f"#### 7. Proficiências SAEB: Português vs. Matemática ({municipio_sel})"
      )

      reg_fato = df_mun_ano.iloc[0] if not df_mun_ano.empty else {}
      lp_ini = reg_fato.get("saeb_lp_iniciais") or 0
      mat_ini = reg_fato.get("saeb_mat_iniciais") or 0
      lp_fin = reg_fato.get("saeb_lp_finais") or 0
      mat_fin = reg_fato.get("saeb_mat_finais") or 0

      if (lp_ini + mat_ini + lp_fin + mat_fin) > 0:
        fig_curr = go.Figure(
            data=[
                go.Bar(
                    name="Língua Portuguesa",
                    x=["Anos Iniciais (5º ano)", "Anos Finais (9º ano)"],
                    y=[lp_ini, lp_fin],
                    marker_color="#3B82F6",
                ),
                go.Bar(
                    name="Matemática",
                    x=["Anos Iniciais (5º ano)", "Anos Finais (9º ano)"],
                    y=[mat_ini, mat_fin],
                    marker_color="#10B981",
                ),
            ]
        )
        fig_curr.update_layout(
            barmode="group",
            template="plotly_white",
            height=380,
            yaxis=dict(title="Escala SAEB (0-500)", range=[150, 300]),
            margin=dict(l=30, r=20, t=30, b=30),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig_curr, use_container_width=True)
      else:
        st.info("Notas do SAEB por disciplina não disponíveis neste exercício.")

    with c_p2:
      # 8. Gargalo Transicional: Comparacao dos Anos Iniciais para os Finais
      st.markdown("#### 8. Gargalo Transicional (Anos Iniciais vs. Finais)")

      ideb_ini = reg_fato.get("ideb_iniciais")
      ideb_fin = reg_fato.get("ideb_finais")
      rend_ini = (
          (reg_fato.get("rendimento_iniciais") or 0) * 100
          if reg_fato.get("rendimento_iniciais")
          else None
      )
      rend_fin = (
          (reg_fato.get("rendimento_finais") or 0) * 100
          if reg_fato.get("rendimento_finais")
          else None
      )

      if pd.notna(ideb_ini) and pd.notna(ideb_fin):
        fig_trans = go.Figure()
        fig_trans.add_trace(
            go.Bar(
                x=["Anos Iniciais", "Anos Finais"],
                y=[ideb_ini, ideb_fin],
                name="IDEB Sintético",
                marker_color="#6366F1",
                yaxis="y",
            )
        )
        if rend_ini is not None and rend_fin is not None:
          fig_trans.add_trace(
              go.Scatter(
                  x=["Anos Iniciais", "Anos Finais"],
                  y=[rend_ini, rend_fin],
                  name="Taxa de Aprovação (%)",
                  mode="lines+markers+text",
                  text=[f"{rend_ini:.1f}%", f"{rend_fin:.1f}%"],
                  textposition="top center",
                  marker=dict(color="#EF4444", size=10),
                  yaxis="y2",
              )
          )
        fig_trans.update_layout(
            template="plotly_white",
            height=380,
            yaxis=dict(title="Nota IDEB", range=[0, 10], side="left"),
            yaxis2=dict(
                title="Aprovação (%)",
                range=[70, 105],
                side="right",
                overlaying="y",
                showgrid=False,
            ),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
            margin=dict(l=30, r=20, t=30, b=30),
        )
        st.plotly_chart(fig_trans, use_container_width=True)
      else:
        st.info("Dados de transição entre etapas não consolidados neste ano.")

    # 9. Trajetoria Historica de Gap Territorial
    st.markdown(
        f"#### 9. Série Histórica do Gap Competitivo: {municipio_sel} (Municipal"
        " vs. Estadual)"
    )
    df_bench_hist = df_bench[
        (df_bench["nome_municipio"] == municipio_sel)
    ].sort_values("ano")
    df_bench_hist_saeb = df_bench_hist.dropna(
        subset=["ideb_iniciais_mun", "ideb_iniciais_est"]
    )

    if not df_bench_hist_saeb.empty:
      fig_gap = go.Figure()
      fig_gap.add_trace(
          go.Scatter(
              x=df_bench_hist_saeb["ano"],
              y=df_bench_hist_saeb["ideb_iniciais_mun"],
              name="Rede Municipal (Prefeitura)",
              mode="lines+markers+text",
              text=df_bench_hist_saeb["ideb_iniciais_mun"].round(1),
              textposition="top center",
              line=dict(color="#2563EB", width=3),
              marker=dict(size=8),
          )
      )
      fig_gap.add_trace(
          go.Scatter(
              x=df_bench_hist_saeb["ano"],
              y=df_bench_hist_saeb["ideb_iniciais_est"],
              name="Rede Estadual (Benchmark)",
              mode="lines+markers+text",
              text=df_bench_hist_saeb["ideb_iniciais_est"].round(1),
              textposition="bottom center",
              line=dict(color="#DC2626", width=2, dash="dot"),
              marker=dict(size=6),
          )
      )
      fig_gap.update_layout(
          template="plotly_white",
          height=380,
          xaxis=dict(title="Ano do Ciclo SAEB", tickmode="linear", dtick=2),
          yaxis=dict(title="Nota Sintética do IDEB (0 a 10)", range=[3, 8]),
          legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
          margin=dict(l=30, r=20, t=30, b=30),
      )
      st.plotly_chart(fig_gap, use_container_width=True)

# Metadados e rodape tecnico
st.markdown("---")
with st.expander("ℹ️ Metodologia das Novas Métricas e Fontes"):
  st.markdown("""
    * **Taxa de Execução Orçamentária:** Proporção de despesas liquidadas em relação às empenhadas na Função 12 ($\text{Despesa Liquidada} / \text{Despesa Empenhada} \times 100$).
    * **Densidade de Insumos Escolares:** Média de alunos por turma ($\text{Matrículas} / \text{Turmas}$) e alunos atendidos por docente ($\text{Matrículas} / \text{Docentes}$).
    * **Equidade Socioeconômica:** Cruzamento da nota do IDEB com o escore contínuo do INSE (vulnerabilidade socioeconômica).
    * **Gargalo Transicional:** Diferença de proficiência e taxas de aprovação entre os Anos Iniciais (1º ao 5º ano) e Anos Finais (6º ao 9º ano).
    * **Escala SAEB:** Médias padronizadas de desempenho em Língua Portuguesa e Matemática (0 a 500 pontos).
    """)