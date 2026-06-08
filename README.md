# Painel de Análise Fiscal - Educação Municipal

Este projeto consiste em um dashboard  interativo desenvolvido com **Streamlit** e integrado ao **Supabase (PostgreSQL)**. O objetivo principal é consolidar, cruzar e analisar dados de investimentos fiscais em educação (provenientes da API do Siconfi) com indicadores de qualidade educacional e contexto socioeconômico (provenientes das bases do INEP).

O painel permite que gestores públicos, pesquisadores e cidadãos auditem a eficiência da aplicação dos recursos constitucionais mínimos de 25% em Manutenção e Desenvolvimento do Ensino (MDE) e compreendam seus impactos diretos nos resultados escolares.

---

## Arquitetura do Banco de Dados (a ser revisto)

- **`dim_municipio`**: Cadastro de entes federativos, população, porte municipal e CNPJ.
- **`dim_tempo`**: Mapeamento cronológico granularizado por ano e períodos bimestrais (formato `AAAAPP`).
- **`dim_legislacao_contas`**: Catálogo de códigos contábeis do Siconfi mapeados por subfunções de gasto.
- **`fato_siconfi_fiscal`**: Armazena os valores numéricos liquidados de despesas organizados por estágio orçamentário.
- **`fato_indicators_desempenho`**: Consolida notas do IDEB, taxas de aprovação, dados censitários e o Indicador de Nível Socioeconômico (INSE).

---

## Fontes de Dados e Endpoints Utilizados

### 1. Siconfi (em andamento)
Os dados fiscais de despesas e receitas educacionais são extraídos em tempo real a partir da API pública do Siconfi.
- **Anexo Alvo:** RREO Anexo 08 (Relatório Resumido da Execução Orçamentária - Receitas e Despesas com Manutenção e Desenvolvimento do Ensino).
- **Endpoint Utilizado:**
  `https://apidatalake.tesouro.gov.br/subsidios/siconfi/api/v1/rreo`
- **Parâmetros de Consulta:** `an_exercicio`, `id_ente` (ID IBGE), `periodo`, `co_anexo=RREO-Anexo 08`.

---

### 2. INEP (nao estruturado ainda)
Os dados de desempenho e infraestrutura estao na tabela `fato_indicadores_desempenho` para permitir o cruzamento Custo-Aluno vs. Aprendizado.

#### Bases a serem utilizadas
- **IDEB (Índice de Desenvolvimento da Educação Básica):** Notas consolidadas dos Anos Iniciais e Anos Finais da rede municipal.
- **Censo Escolar (Matrículas e Docentes):** Total de matrículas na rede pública municipal para cálculo do indicador de gasto per capita (Custo-Aluno).
- **Indicador de Nível Socioeconômico (INSE):** Utilizado  para contextualizar os resultados do IDEB, permitindo comparar municípios de perfis sociais semelhantes.
- **Taxa de Rendimento Escolar:** Índices de aprovação, reprovação e abandono por ano letivo.

---

## Como o Painel Funciona Atualmente

### O que funciona no momento
- **Extração Siconfi:** O script `etl/siconfi.py` extrai com sucesso os dados do RREO Anexo 08, remove os caracteres especiais e gera chaves de texto exclusivas (`cod_conta_real`) para popular a dimensão sem misturar duplicidades orçamentárias.
- - **Execução via Streamlit Local:**
- - **Execução via Streamlit Cloud:** https://dashboard-publico-alpha.streamlit.app/  (arrumado)

### O que NÃO está Funcionando

- **Extracao de Indicadores INEP:** Diferente do Siconfi que possui API estruturada, as bases do INEP exigem download manual de planilhas de portais de dados abertos e tratamento prévio via scripts locais (arquivos `.csv`) para posterior injeção na tabela `fato_indicadores_desempenho`. O painel ainda não possui um botão de "downlaod automático" para o INEP.

---