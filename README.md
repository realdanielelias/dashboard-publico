📊 Painel de Análise da Educação Municipal

Projeto de Engenharia de Dados e Business Intelligence desenvolvido para analisar a relação entre investimentos públicos, resultados educacionais e contexto socioeconômico de municípios paulistas.

A solução integra dados do Siconfi/STN, INEP/MEC e IBGE, utilizando arquitetura Medallion (Bronze/Silver/Gold) e Star Schema. Os dados tratados são armazenados em PostgreSQL (Supabase) e disponibilizados por meio de um dashboard desenvolvido com Streamlit e Plotly.

🔗 Acessar o Dashboard

🎯 Objetivo

Avaliar a eficiência dos investimentos municipais em educação básica, relacionando:

💰 Despesas públicas;

👨‍🎓 Matrículas e estrutura educacional;

📈 IDEB e SAEB;

🏫 Indicadores do Censo Escolar;

📊 Contexto socioeconômico (INSE);

🏙️ Características demográficas dos municípios.

O município de Marília (SP) é utilizado como estudo de caso, sendo comparado com 26 municípios paulistas selecionados por proximidade regional, porte populacional e características socioeconômicas.

🗺️ Recorte Territorial

A amostra é dividida em quatro grupos:

Grupo	Municípios
Polo Central	Marília
Região de Marília	13 municípios da região imediata
Polos Regionais	Bauru, Assis, Tupã, Ourinhos e Lins
Municípios Homólogos	Presidente Prudente, Araçatuba, São Carlos, Araraquara, Rio Claro, Botucatu e Jaú

Essa divisão permite realizar comparações entre municípios com características semelhantes, reduzindo distorções causadas por diferenças de escala populacional e capacidade financeira.

🏗️ Arquitetura

O projeto utiliza uma arquitetura Medallion, separando os dados em três níveis:

Fontes de Dados
│
├── Siconfi/STN → Dados fiscais
├── INEP/MEC    → Dados educacionais
└── IBGE        → Dados territoriais
        │
        ▼
┌─────────────────────┐
│ BRONZE / RAW        │
│ Dados originais     │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ SILVER / STAGING    │
│ Limpeza e tratamento│
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ GOLD / ANALYTICS    │
│ Star Schema         │
│ PostgreSQL          │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Views e KPIs        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Streamlit Dashboard │
└─────────────────────┘

⭐ Modelo Dimensional

A camada Gold utiliza um Star Schema, com uma tabela fato central e dimensões de apoio.

Dimensões

dim_municipio — informações territoriais, população e grupo de comparação.

dim_tempo — informações temporais e períodos de avaliação.

dim_rede — redes municipal, estadual, federal e total.

Tabela Fato

fato_execucao_educacional — concentra despesas, matrículas, docentes, turmas, escolas e indicadores educacionais.

As tabelas utilizam chaves substitutas (sk_) e registros sentinela para tratamento de dados ausentes.

📊 Principais KPIs

O modelo analítico disponibiliza indicadores como:

Despesa liquidada em educação;

Despesa empenhada;

Custo por aluno do Ensino Fundamental;

Custo por aluno da Educação Infantil;

Restos a Pagar Não Processados;

IDEB observado;

Meta projetada do IDEB;

Cumprimento da meta;

Matrículas;

Docentes;

Turmas;

Escolas;

Indicadores do SAEB;

Indicador socioeconômico (INSE).

Exemplo
Custo Aluno-Ano =
Despesa Liquidada ÷ Número de Matrículas


Esse indicador permite relacionar o volume de recursos investidos com a estrutura e os resultados educacionais.

📡 Fontes de Dados
Fonte	Dados
Siconfi / STN	Execução orçamentária
INEP – Censo Escolar	Matrículas, docentes, turmas e escolas
INEP – IDEB / SAEB	Desempenho educacional
INEP – INSE	Contexto socioeconômico
IBGE	Municípios e informações territoriais
🔄 Pipeline ETL

Os processos de ingestão e transformação estão organizados no diretório etl/.

Arquivo	Responsabilidade
entes.py	Dados cadastrais dos municípios
rreo.py	Extração das despesas do Siconfi
sinopse.py	Tratamento do Censo Escolar
ideb.py	IDEB, metas e SAEB
inse.py	Indicadores socioeconômicos
gold.py	Construção da camada analítica
load_gold_supabase.py	Carga no PostgreSQL/Supabase

Durante o tratamento são realizadas etapas de limpeza, padronização, normalização, tipagem e transformação dos dados.

🖥️ Dashboard

A interface em Streamlit está organizada em três áreas principais:

1. Visão Executiva

Apresenta os principais indicadores financeiros e educacionais do município.

2. Diagnóstico e Benchmark

Relaciona custo por aluno e desempenho educacional, permitindo comparar Marília com os municípios do grupo de controle.

3. Responsabilidade Federativa

Compara a evolução das redes municipal e estadual, utilizando indicadores de desempenho e aprovação.

📁 Estrutura do Projeto
├── app.py
├── schema.sql
├── requirements.txt
│
├── etl/
│   ├── entes.py
│   ├── rreo.py
│   ├── sinopse.py
│   ├── ideb.py
│   ├── inse.py
│   ├── gold.py
│   └── load_gold_supabase.py
│
└── data/
    ├── raw/
    ├── silver/
    └── gold/

🛠️ Tecnologias

Python

Pandas

PostgreSQL

Supabase

Streamlit

Plotly

APIs REST

SQL

Arquitetura Medallion

Star Schema / Dimensional Modeling

🚀 Resultado

O projeto transforma diferentes fontes de dados públicos fiscais, educacionais, demográficos e socioeconômicos em uma camada analítica integrada, permitindo investigar:

Quanto os municípios investem em educação, quanto custa cada aluno e quais resultados educacionais são obtidos a partir desses investimentos.

🔗 Links

Dashboard:
https://dashboard-publico-test.streamlit.app/

Repositório:
Este repositório contém os pipelines de ETL, modelo dimensional, scripts SQL e aplicação responsável pela visualização dos dados.
