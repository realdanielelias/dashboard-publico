# Painel de Análise e Eficiência da Educação Municipal

Solução de Engenharia de Dados e *Business Intelligence* voltada à auditoria, correlação e avaliação da eficiência dos investimentos públicos municipais em educação básica frente aos resultados de qualidade pedagógica e ao contexto socioeconômico em municípios paulistas.

O projeto implementa uma **Arquitetura Medalhão (Bronze/Silver/Gold)** articulada a um **Modelo Dimensional (Star Schema)** desenhado segundo as diretrizes clássicas de Ralph Kimball, integrando dados fiscais e orçamentários (Siconfi/STN), demográficos e avaliativos (INEP/MEC) e territoriais/cadastrais (IBGE). A camada analítica é persistida em **PostgreSQL (Supabase)** e consumida por uma interface em **Streamlit** com **Plotly**.

🔗 **Link para teste:** https://dashboard-publico-test.streamlit.app/

---

## 🎯 Recorte Territorial e Metodologia de Pareamento

Para viabilizar comparações justas e neutralizar disparidades de escala demográfica e capacidade arrecadatória, a pesquisa adota o município de **Marília (SP)** como estudo de caso central e delimita uma amostra de controle de **26 municípios paulistas**, estratificados em 4 agrupamentos analíticos:

1. **Polo Central:** Marília (núcleo da investigação).
2. **Região Imediata de Marília (13 municípios lindeiros):** Garça, Pompeia, Vera Cruz, Oriente, Echaporã, Ocauçu, Lupércio, Álvaro de Carvalho, Alvinlândia, Guaimbê, Júlio Mesquita, Quintana e Gália.
3. **Polos Regionais da Macrorregião Centro-Oeste (5 municípios):** Bauru, Assis, Tupã, Ourinhos e Lins.
4. **Pares Homólogos Estaduais (7 municípios de controle):** Municípios selecionados por convergência de porte populacional (130 mil a 260 mil habitantes), receita orçamentária *per capita* e perfil socioeconômico semelhante — Presidente Prudente, Araçatuba, São Carlos, Araraquara, Rio Claro, Botucatu e Jaú.

---

## 🏗️ Arquitetura de Dados (Medallion Architecture)

O fluxo de processamento organiza-se em três camadas de maturidade:

* **Camada Raw (Bronze / Dados Brutos):** Repositório local dos arquivos originais não modificados (`data/raw/`), compreendendo extrações em `.json` da API do Siconfi, planilhas heterogêneas `.ods` do INEP.
* **Camada Staging (Silver / Dados Higienizados):** Tabelas normalizadas e limpas (`data/silver/stg_*.csv`), onde são resolvidos problemas de células mescladas, inconsistências de tipo, variações de nomenclatura contábil e conversão de formatos amplos (*wide*) para longos (*tidy*).
* **Camada Analytics (Gold / Data Warehouse Dimensional):** Estrutura modelada em Esquema Estrela no PostgreSQL, composta por dimensões conformes desnormalizadas, tabela fato de snapshot consolidada, chaves substitutas inteiras (`sk_`), registros sentinela (`-1`) e *views* analíticas para pré-computação de KPIs.

```text
[ Siconfi (API) ]    [ Censo INEP (.ods) ]    [ IDEB/SAEB (.xlsx) ]    [ INSE (.parquet) ]
        │                     │                         │                       │
        ▼                     ▼                         ▼                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       CAMADA SILVER (data/silver/stg_*.csv)                            │
│       Limpeza, Regex contábil, Forward-Fill, normalização longa e tipagem estrita       │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                    CAMADA GOLD / POSTGRESQL (Star Schema - Kimball)                    │
│                                                                                        │
│    dim_tempo              fato_execucao_educacional                   dim_rede         │
│  ┌────────────┐        ┌──────────────────────────────┐            ┌─────────────┐     │
│  │ sk_tempo   │◄──┐    │ sk_municipio (FK)            │     ┌─────►│ sk_rede     │     │
│  └────────────┘   │    │ sk_tempo (FK)                │     │      └─────────────┘     │
│                   ├────┤ sk_rede (FK)                 ├─────┤                          │
│  dim_municipio    │    │ ---------------------------- │                                │
│  ┌────────────┐   │    │ Despesas (Liq/Emp por Subf.) │                                │
│  │sk_municipio├───┘    │ Matrículas, Docentes, Turmas │                                │
│  └────────────┘        │ IDEB, Metas, SAEB, INSE      │                                │
│                        └──────────────┬───────────────┘                                │
└───────────────────────────────────────┼────────────────────────────────────────────────┘
                                        │
                                        ▼
                       [ VIEWS ANALÍTICAS & KPIS ]
                       ├── vw_fato_educacao_kpis
                       └── vw_benchmark_municipal_estadual
                                        │
                                        ▼
                         [ STREAMLIT DASHBOARD (app.py) ]
                       ├── 1. Visão Executiva (Mandato & Orçamento)
                       ├── 2. Diagnóstico & Peer Group (Custo x IDEB)
                       └── 3. Responsabilidade Federativa & SAEB
