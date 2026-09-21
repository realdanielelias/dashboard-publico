-- Dimensão de Tempo pra acompanhar a evolução dos anos e os ciclos do SAEB/IDEB
CREATE TABLE dim_tempo (
    sk_tempo            INT PRIMARY KEY,           -- Chave substituta (ex: 2023)
    ano                 INT NOT NULL UNIQUE,       -- Ano do exercício
    eh_ano_saeb         BOOLEAN NOT NULL,          -- Indica se teve aplicação do SAEB (anos ímpares)
    ciclo_avaliacao     VARCHAR(30) NOT NULL,      -- 'Ciclo SAEB' ou 'Interstício'
    decada              INT NOT NULL,
    quinquenio          VARCHAR(10) NOT NULL
);

-- Dimensão Município com dados cadastrais do IBGE e agrupamentos de análise
CREATE TABLE dim_municipio (
    sk_municipio        INT PRIMARY KEY,           -- Chave substituta (ex: 3529005)
    cod_ibge            INT NOT NULL UNIQUE,       -- Código IBGE de 7 dígitos
    nome_municipio      VARCHAR(100) NOT NULL,
    sigla_uf            CHAR(2) NOT NULL,
    regiao              VARCHAR(30) NOT NULL,
    populacao_censo_2022 INT,                      -- População do Censo 2022
    porte_populacional  VARCHAR(50) NOT NULL,      -- Faixa populacional do município
    grupo_analitico     VARCHAR(50) NOT NULL       -- Categoria pra comparar com municípios similares
);

-- Dimensão pra separar os dados por esfera administrativa
CREATE TABLE dim_rede (
    sk_rede              INT PRIMARY KEY,          -- Chave substituta
    cod_rede             INT NOT NULL UNIQUE,      -- Código da rede (1=Federal, 2=Estadual, 3=Municipal, 0=Total)
    nome_rede            VARCHAR(30) NOT NULL,
    esfera_governamental VARCHAR(50) NOT NULL
);

-- Registros genéricos pra quando o dado de origem não tiver vínculo definido
INSERT INTO dim_tempo (sk_tempo, ano, eh_ano_saeb, ciclo_avaliacao, decada, quinquenio)
VALUES (-1, -1, FALSE, 'Não Aplicável', 0, 'N/A');

INSERT INTO dim_municipio (sk_municipio, cod_ibge, nome_municipio, sigla_uf, regiao, populacao_censo_2022, porte_populacional, grupo_analitico)
VALUES (-1, -1, 'Município Não Identificado', 'NA', 'Não Identificada', 0, 'Não Aplicável', 'Outros');

INSERT INTO dim_rede (sk_rede, cod_rede, nome_rede, esfera_governamental)
VALUES (-1, -1, 'Não Informada', 'Não Informada');

-- Carga inicial das redes de ensino
INSERT INTO dim_rede (sk_rede, cod_rede, nome_rede, esfera_governamental) VALUES
(1, 1, 'Federal', 'Pública Federal'),
(2, 2, 'Estadual', 'Pública Estadual'),
(3, 3, 'Municipal', 'Pública Municipal'),
(4, 0, 'Total', 'Consolidado do Território');

CREATE TABLE fato_execucao_educacional (
    -- Chaves estrangeiras
    sk_municipio                INT NOT NULL REFERENCES dim_municipio(sk_municipio),
    sk_tempo                    INT NOT NULL REFERENCES dim_tempo(sk_tempo),
    sk_rede                     INT NOT NULL REFERENCES dim_rede(sk_rede),

    -- Dados orçamentários (SICONFI)
    despesa_liquidada_educacao  NUMERIC(15,2),
    desp_liq_fundamental        NUMERIC(15,2),
    desp_liq_infantil           NUMERIC(15,2),
    despesa_empenhada_educacao  NUMERIC(15,2),
    desp_emp_fundamental        NUMERIC(15,2),
    desp_emp_infantil           NUMERIC(15,2),

    -- Dados de estrutura e contagem de alunos (Censo Escolar/INEP)
    mat_creche                  INT DEFAULT 0,
    mat_pre_escola              INT DEFAULT 0,
    mat_anos_iniciais           INT DEFAULT 0,
    mat_anos_finais             INT DEFAULT 0,
    mat_especial_classes_comuns INT DEFAULT 0,
    docentes_iniciais           INT DEFAULT 0,
    docentes_finais             INT DEFAULT 0,
    turmas_iniciais             INT DEFAULT 0,
    turmas_finais               INT DEFAULT 0,
    escolas_creche              INT DEFAULT 0,
    escolas_pre_escola          INT DEFAULT 0,
    escolas_iniciais            INT DEFAULT 0,
    escolas_finais              INT DEFAULT 0,

    -- Indicador socioeconômico (INSE/INEP)
    inse_score                  NUMERIC(5,4),      -- Score médio (não dá pra somar direto)
    inse_classificacao          VARCHAR(30),       -- Classificação textual da faixa socioeconômica
    qtd_alunos_inse             INT,               -- Total de alunos respondentes

    -- Resultados do IDEB e SAEB (Anos Iniciais)
    ideb_iniciais               NUMERIC(4,2),
    ideb_meta_iniciais          NUMERIC(4,2),
    rendimento_iniciais         NUMERIC(5,4),      -- Taxa de aprovação (0 a 1)
    saeb_mat_iniciais           NUMERIC(6,2),
    saeb_lp_iniciais            NUMERIC(6,2),
    saeb_nota_iniciais          NUMERIC(6,2),      -- Média padronizada

    -- Resultados do IDEB e SAEB (Anos Finais)
    ideb_finais                 NUMERIC(4,2),
    ideb_meta_finais            NUMERIC(4,2),
    rendimento_finais           NUMERIC(5,4),
    saeb_mat_finais             NUMERIC(6,2),
    saeb_lp_finais              NUMERIC(6,2),
    saeb_nota_finais            NUMERIC(6,2),

    CONSTRAINT pk_fato_execucao PRIMARY KEY (sk_municipio, sk_tempo, sk_rede)
);

CREATE INDEX idx_fato_tempo ON fato_execucao_educacional(sk_tempo);
CREATE INDEX idx_fato_municipio ON fato_execucao_educacional(sk_municipio);
CREATE INDEX idx_fato_rede ON fato_execucao_educacional(sk_rede);
CREATE INDEX idx_mun_grupo ON dim_municipio(grupo_analitico, porte_populacional);

-- 5.1 View principal de KPIs e custos por aluno
CREATE OR REPLACE VIEW vw_fato_educacao_kpis AS
SELECT 
    m.cod_ibge,
    m.nome_municipio,
    m.sigla_uf,
    m.grupo_analitico,
    m.porte_populacional,
    m.populacao_censo_2022,
    t.ano,
    t.eh_ano_saeb,
    r.nome_rede,
    
    -- Financeiro e sobra orçamentária estimada
    f.despesa_liquidada_educacao,
    f.despesa_empenhada_educacao,
    (f.despesa_empenhada_educacao - f.despesa_liquidada_educacao) AS potencial_rpnp,
    
    -- Totais de matriculados agrupados por etapa
    (COALESCE(f.mat_creche, 0) + COALESCE(f.mat_pre_escola, 0)) AS mat_infantil_total,
    (COALESCE(f.mat_anos_iniciais, 0) + COALESCE(f.mat_anos_finais, 0)) AS mat_fundamental_total,
    (COALESCE(f.mat_creche, 0) + COALESCE(f.mat_pre_escola, 0) + 
     COALESCE(f.mat_anos_iniciais, 0) + COALESCE(f.mat_anos_finais, 0) + 
     COALESCE(f.mat_especial_classes_comuns, 0)) AS mat_geral_rede,

    -- Custo por aluno (calculado só pra rede municipal pra evitar divisões erradas no consolidado)
    CASE 
        WHEN r.cod_rede = 3 
        THEN ROUND(f.desp_liq_infantil / NULLIF(COALESCE(f.mat_creche, 0) + COALESCE(f.mat_pre_escola, 0), 0), 2)
        ELSE NULL 
    END AS custo_aluno_infantil,

    CASE 
        WHEN r.cod_rede = 3 
        THEN ROUND(f.desp_liq_fundamental / NULLIF(COALESCE(f.mat_anos_iniciais, 0) + COALESCE(f.mat_anos_finais, 0), 0), 2)
        ELSE NULL 
    END AS custo_aluno_fundamental,

    CASE 
        WHEN r.cod_rede = 3 AND m.populacao_censo_2022 > 0 
        THEN ROUND(f.despesa_liquidada_educacao / m.populacao_censo_2022, 2)
        ELSE NULL 
    END AS gasto_educacao_per_capita,

    -- Cumprimento das metas do IDEB
    f.ideb_iniciais,
    f.ideb_meta_iniciais,
    ROUND(f.ideb_iniciais - f.ideb_meta_iniciais, 2) AS delta_meta_iniciais,
    CASE 
        WHEN f.ideb_iniciais >= f.ideb_meta_iniciais THEN 'Atingiu a Meta'
        WHEN f.ideb_iniciais < f.ideb_meta_iniciais THEN 'Abaixo da Meta'
        ELSE 'Sem Avaliação no Exercício'
    END AS status_meta_iniciais,

    f.ideb_finais,
    f.ideb_meta_finais,
    ROUND(f.ideb_finais - f.ideb_meta_finais, 2) AS delta_meta_finais,

    -- Contexto e desempenho
    f.inse_score,
    f.inse_classificacao,
    f.rendimento_iniciais,
    f.saeb_nota_iniciais
FROM fato_execucao_educacional f
JOIN dim_municipio m ON f.sk_municipio = m.sk_municipio
JOIN dim_tempo t     ON f.sk_tempo = t.sk_tempo
JOIN dim_rede r      ON f.sk_rede = r.sk_rede;

-- 5.2 View pra comparar o desempenho do Município diretamente com o Estado
CREATE OR REPLACE VIEW vw_benchmark_municipal_estadual AS
SELECT 
    m.cod_ibge,
    m.nome_municipio,
    m.grupo_analitico,
    t.ano,
    
    -- Indicadores da Rede Municipal
    f_mun.despesa_liquidada_educacao AS orcamento_educacao_mun,
    ROUND(f_mun.desp_liq_fundamental / NULLIF(COALESCE(f_mun.mat_anos_iniciais, 0) + COALESCE(f_mun.mat_anos_finais, 0), 0), 2) AS custo_aluno_fund_mun,
    f_mun.ideb_iniciais AS ideb_iniciais_mun,
    f_mun.saeb_nota_iniciais AS saeb_nota_iniciais_mun,
    f_mun.rendimento_iniciais AS taxa_aprovacao_iniciais_mun,
    
    -- Indicadores da Rede Estadual no mesmo município
    f_est.ideb_iniciais AS ideb_iniciais_est,
    f_est.saeb_nota_iniciais AS saeb_nota_iniciais_est,
    f_est.rendimento_iniciais AS taxa_aprovacao_iniciais_est,
    
    -- Diferença entre as duas redes (Municipal - Estadual)
    ROUND(f_mun.ideb_iniciais - f_est.ideb_iniciais, 2) AS gap_ideb_mun_vs_est,
    
    -- Perfil socioeconômico da rede municipal
    f_mun.inse_score AS inse_score_mun,
    f_mun.inse_classificacao AS inse_classificacao_mun
FROM dim_municipio m
CROSS JOIN dim_tempo t
-- Busca os dados do município (sk_rede = 3)
LEFT JOIN fato_execucao_educacional f_mun 
       ON f_mun.sk_municipio = m.sk_municipio 
      AND f_mun.sk_tempo = t.sk_tempo 
      AND f_mun.sk_rede = 3
-- Busca os dados do estado (sk_rede = 2)
LEFT JOIN fato_execucao_educacional f_est 
       ON f_est.sk_municipio = m.sk_municipio 
      AND f_est.sk_tempo = t.sk_tempo 
      AND f_est.sk_rede = 2
WHERE m.sk_municipio <> -1 
  AND t.sk_tempo <> -1;