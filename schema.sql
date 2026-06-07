ALTER DATABASE postgres SET timezone TO 'America/Sao_Paulo'; -- corrigir timezone do supabase

ALTER ROLE postgres SET timezone TO 'America/Sao_Paulo'; -- corrige a timezone do user admin

CREATE TABLE dim_municipio (
    id_ibge INT PRIMARY KEY, -- id do endpoint de entes do siconfi (usa dado do IBGE)
    nome_municipio VARCHAR(100) NOT NULL, -- nome presente no endpoint do siconfi 
    uf VARCHAR(2) NOT NULL, 
    populacao INT,
    porte_municipio VARCHAR(50), -- porte muito pequeno ate 20k, pequeno de 20 ate 100k, medio de 100k ate 750k, grande mais de 750k 
    -- fonte: https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/desenvolvimento-urbano-e-metropolitano/politica-nacional-de-desenvolvimento-urbano/tipologias-urbanas
    cnpj VARCHAR(14)
);

CREATE TABLE dim_tempo (
    id_tempo INT PRIMARY KEY, --formato AAAAPP
    ano INT NOT NULL, -- campo 'exercicio' no siconfi
    periodo_cod INT NOT NULL, -- campo 'periodo' no siconfi (0 para DCA / 1 a 6 para RREO)
    periodo_rotulo VARCHAR(30) NOT NULL -- nome se e bimestral ou anual
);

CREATE TABLE dim_legislacao_contas (
    cod_conta VARCHAR(100) PRIMARY KEY, --cd_conta do siconfi
    nome_conta TEXT NOT NULL, --nome da conta no siconfi
    is_base_receita_25 BOOLEAN DEFAULT FALSE,-- marcador para calculo dos 25% da educacao
    is_despesa_mde BOOLEAN DEFAULT FALSE, -- despesas em infra e manutencao do ensino
    is_fundeb_70 BOOLEAN DEFAULT FALSE, -- gasto com professores
    is_despesa_saude BOOLEAN DEFAULT FALSE, -- marcador pra calculo dos 15% da saude
    is_bloco_assistencia BOOLEAN DEFAULT FALSE, --marcado para gastos  de assistencia
    is_gasto_pessoal BOOLEAN DEFAULT FALSE --marcador se folha de pagamento (RH)
);

CREATE TABLE fato_siconfi_fiscal (
    id_fato BIGSERIAL PRIMARY KEY,
    id_ibge INT REFERENCES dim_municipio(id_ibge) ON DELETE CASCADE,
    id_tempo INT REFERENCES dim_tempo(id_tempo) ON DELETE CASCADE,
    cod_conta VARCHAR(100) REFERENCES dim_legislacao_contas(cod_conta),
    anexo_origem VARCHAR(50), --campo anexo siconfi
    estagio_orcamentario VARCHAR(50),-- campo coluna siconfi
    valor NUMERIC(20, 2) NOT NULL
);

CREATE TABLE fato_indicadores_desempenho (
    id_desempenho SERIAL PRIMARY KEY,
    id_ibge INT REFERENCES dim_municipio(id_ibge) ON DELETE CASCADE,
    ano INT NOT NULL,
    total_matriculas_rede_municipal INT,
    nota_ideb_anos_iniciais NUMERIC(3,1),
    nota_ideb_anos_finais NUMERIC(3,1),
    taxa_aprovacao_media NUMERIC(5,2),
    nivel_socioeconomico_inse NUMERIC(4,2), --medidor contexto social
    cobertura_atencao_basica NUMERIC(5,2),
    idhm_longevidade NUMERIC(4,3),
    familias_cadastro_unico INT,
    total_servidores_ativos INT,
    CONSTRAINT unique_municipio_ano UNIQUE (id_ibge, ano)
);

CREATE INDEX idx_fiscal_cruzamento ON fato_siconfi_fiscal(id_ibge, id_tempo);