# Painel de Análise e Eficiência da Educação Municipal

Solução de Engenharia de Dados e *Business Intelligence* voltada à auditoria, correlação e avaliação da eficiência dos investimentos públicos municipais em educação básica frente aos resultados de qualidade pedagógica e ao contexto socioeconômico em municípios paulistas.

O projeto implementa uma **Arquitetura Medalhão (Bronze/Silver/Gold)** articulada a um **Modelo Dimensional (Star Schema)** desenhado segundo as diretrizes de Ralph Kimball, integrando dados fiscais e orçamentários (Siconfi/STN), demográficos e avaliativos (INEP/MEC) e territoriais/cadastrais (IBGE). A camada analítica é persistida em **PostgreSQL (Supabase)** e consumida por uma interface em **Streamlit**.

🔗 **Link para teste:** https://dashboard-publico-test.streamlit.app/

---

## 🎯 Recorte Territorial e Metodologia de Pareamento

Para viabilizar comparações justas e neutralizar disparidades de escala demográfica e capacidade arrecadatória, a pesquisa adota o município de **Marília (SP)** como objeto de estudo central e delimita uma amostra de controle de **26 municípios paulistas**, estratificados em 4 agrupamentos analíticos:

1. **Polo Central:** Marília (núcleo da investigação).
2. **Região Imediata de Marília (13 municípios lindeiros):** Garça, Pompeia, Vera Cruz, Oriente, Echaporã, Ocauçu, Lupércio, Álvaro de Carvalho, Alvinlândia, Guaimbê, Júlio Mesquita, Quintana e Gália.
3. **Polos Regionais da Macrorregião Centro-Oeste (5 municípios):** Bauru, Assis, Tupã, Ourinhos e Lins.
4. **Pares Homólogos Estaduais (7 municípios de controle):** Municípios selecionados por convergência de porte populacional (130 mil a 260 mil habitantes), receita orçamentária *per capita* e perfil socioeconômico semelhante como Presidente Prudente, Araçatuba, São Carlos, Araraquara, Rio Claro, Botucatu e Jaú.

---

## 🏗️ Arquitetura de Dados (Medallion Architecture)

O fluxo de processamento organiza-se em três camadas de maturidade:

* **Camada Raw (Bronze / Dados Brutos):** Repositório local dos arquivos originais não modificados (`data/raw/`), compreendendo extrações em `.json` da API do Siconfi, planilhas heterogêneas `.ods` do INEP.
* **Camada Staging (Silver / Dados Higienizados):** Tabelas normalizadas e limpas (`data/silver/stg_*.csv`), onde são resolvidos problemas de células mescladas, inconsistências de tipo, variações de nomenclatura contábil e conversão de formatos amplos (*wide*) para longos (*tidy*).
* **Camada Analytics (Gold / Dados Para Consumo):** Estrutura modelada em Esquema Estrela no PostgreSQL, composta por dimensões conformes desnormalizadas, tabela fato de snapshot consolidada, chaves substitutas inteiras (`sk_`), registros sentinela (`-1`) e *views* analíticas para pré-computação de KPIs.

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
```
## 🏛️ Modelagem Dimensional

A modelagem segue estritamente os princípios do Capítulo 2 do *The Data Warehouse Toolkit* (Kimball & Ross):

### 1. Tabelas de Dimensão
* **`dim_municipio`:** Dimensão territorial desnormalizada. Reúne código IBGE, nome do município, UF, região geográfica, população recenseada no Censo 2022, faixas de porte populacional e os rótulos de grupo analítico
* **`dim_tempo`:** Dimensão temporal anual abrangendo a série de 2015 a 2025, incorporando marcadores de ciclo bienal do SAEB, década e quinquênio.
* **`dim_rede`:** Dimensão com as esferas administrativas analisadas (Municipal, Estadual, Federal e Total Consolidado do Território).

### 2. Tabela Fato Central: `fato_execucao_educacional`
* **Fatos Totalmente Aditivos:** Valores empenhados e liquidados na Função 12, Subfunção 361 (Ensino Fundamental) e Subfunção 365 (Educação Infantil); total de alunos avaliados no INSE.  
  *Regra de Governança Fiscal:* As despesas orçamentárias municipais só possuem valor quando `sk_rede = 3` (Municipal). Para as redes Estadual e Total, os valores são gravados estritamente como `NULL`, prevenindo duplicações de valores (*double counting*) em operações `SUM()`.
* **Fatos Semi-Aditivos:** Contagens de capacidade física e estoque censitário — matrículas por etapa (creche, pré-escola, anos iniciais e finais), corpos docentes, turmas e escolas ativas.
* **Fatos Não Aditivos e Índices:** Notas observadas do IDEB, metas projetadas, taxas de rendimento escolar ($P$), médias padronizadas do SAEB ($N$) e escore socioeconômico contínuo do INSE.

### 3. Camada Semântica
Para evitar cálculos pesados e falhas matemáticas na interface visual, duas *views* foram implementadas no banco:
* **`vw_fato_educacao_kpis`:** Calcula dinamicamente o Custo Aluno-Ano por etapa completa (evitando divisão por zero via `NULLIF`), os Restos a Pagar Não Processados (RPNP) potenciais e a distância em relação às metas do IDEB:
* **`vw_benchmark_municipal_estadual`:** Pivota os indicadores no mesmo município e ano, alinhando a rede municipal e a rede estadual lado a lado para viabilizar comparações territoriais imediatas no Streamlit.

---

## 📡 Fontes de Dados e Pipelines de ETL

As rotinas de extração residem no diretório `etl/`:

| Fonte | Módulo ETL | Formato Origem | Procedimentos Técnicos |
| :--- | :--- | :--- | :--- |
| **Siconfi / STN** | `rreo.py` | API REST (JSON) | Coleta das despesas do RREO Anexo 02 (6º bimestre) com *checkpointing* em disco para retomada automática de falhas de conexão e expressões regulares para isolamento de rubricas contábeis. |
| **Sinopse Escolar / INEP** | `sinopse.py` | Planilhas `.ods` | Leitura das Sinopses Estatísticas da Educação Básica com *engine* `calamine`, compatibilizando quebras históricas de layout e agregando matrículas, turmas, docentes e escolas. |
| **IDEB & SAEB / INEP** | `ideb.py` | Planilhas `.xlsx` / `.ods` | Resolução de cabeçalhos hierárquicos e células mescladas por *forward fill* horizontal, transpondo séries de avaliação de formato largo para registros normalizados. |
| **INSE / INEP** | `inse.py` | `.parquet` / `.csv` | Filtragem para o total municipal consolidado (`tipo_localizacao = 0`) e classificação do escore contínuo em 8 faixas de valor (*Value Bands* do Nível I ao VIII). |
| **Entes / IBGE** | `entes.py` | API REST (JSON) | Obtenção do cadastro de entes federativos, padronização do código IBGE de 7 dígitos e mapeamento geográfico base. |

---

## 🖥️ Estado Atual da Interface Visual (Dashboard como Prova de Conceito)

O painel analítico (`app.py`) foi estruturado em Streamlit com Plotly em torno de 3 camadas de decisão:

1. **Visão Executiva (Mandato & Orçamento):** Apresenta métricas consolidadas de despesa liquidada na Educação, saldo potencial de Restos a Pagar Não Processados (RPNP), Custos Aluno-Ano por etapa e taxa de cumprimento da meta do IDEB.
2. **Diagnóstico & Peer Group (Custo x Resultado):** Gráfico de dispersão espacial interativo relacionando Custo Aluno Fundamental e nota do IDEB, ponderado pelo tamanho populacional e categorizado por grupo de controle e nível INSE.
3. **Responsabilidade Federativa & SAEB:** Séries temporais comparando a trajetória de proficiência e aprovação da rede municipal frente à rede estadual inserida no mesmo município.

---

## 📁 Estrutura do Repositório

```text
├── app.py                          # Aplicação interativa em Streamlit
├── requirements.txt                # Dependências homologadas do ecossistema Python
├── schema.sql                      # Script DDL completo: Dimensões, Fato, Sentinelas e Views
├── etl/
│   ├── entes.py                    # Extração cadastral de municípios (IBGE)
│   ├── rreo.py                     # Ingestão do RREO Anexo 02 (Siconfi/STN)
│   ├── sinopse.py                  # Processamento das Sinopses Estatísticas (INEP)
│   ├── ideb.py                     # Extração do IDEB, Metas e SAEB (INEP)
│   ├── inse.py                     # Extração e categorização do INSE (INEP)
│   ├── gold.py                     # Criação dos artefatos da modelagem dimensional
│   └── load_gold_supabase.py       # Carga e persistência no banco PostgreSQL (Supabase)
└── data/
    ├── raw/                        # Repositório de dados brutos (Camada Bronze)
    ├── silver/                     # Bases limpas e normalizadas em CSV (Camada Staging)
    └── gold/                       # Artefatos exportados da modelagem final (Camada Gold)
```

Consegue simplificar isso daqui
