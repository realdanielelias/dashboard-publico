'''
ETL CAMADA GOLD (STAR SCHEMA - KIMBALL)
DESC: CRUZA AS BASES SILVER, GERA AS DIMENSOES E A TABELA FATO CENTRAL CONSOLIDADA
FONTE: BASES TRATADAS DA CAMADA SILVER (SICONFI, CENSO ESCOLAR, IDEB E INSE)
'''

import itertools
from pathlib import Path
import numpy as np
import pandas as pd

# Definir diretorios de trabalho
BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if "__file__" in locals()
    else Path.cwd()
)
DIR_SILVER = BASE_DIR / "data" / "silver"
DIR_GOLD = BASE_DIR / "data" / "gold"
DIR_GOLD.mkdir(parents=True, exist_ok=True)

# Definir amostra metodologica de 26 municipios
MUNICIPIOS_AMOSTRA = {
    3529005: {
        "nome": "Marília",
        "grupo": "Polo Central",
        "porte": "Médio-Grande Porte",
        "pop": 237627,
    },
    3516705: {
        "nome": "Garça",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte II",
        "pop": 42110,
    },
    3540002: {
        "nome": "Pompeia",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 20196,
    },
    3556602: {
        "nome": "Vera Cruz",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 10193,
    },
    3534005: {
        "nome": "Oriente",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 6176,
    },
    3514403: {
        "nome": "Echaporã",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 6005,
    },
    3533700: {
        "nome": "Ocauçu",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 4038,
    },
    3527702: {
        "nome": "Lupércio",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 3981,
    },
    3501400: {
        "nome": "Álvaro de Carvalho",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 4824,
    },
    3501509: {
        "nome": "Alvinlândia",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 3000,
    },
    3517703: {
        "nome": "Guaimbê",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 5429,
    },
    3526001: {
        "nome": "Júlio Mesquita",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 4430,
    },
    3541703: {
        "nome": "Quintana",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 6296,
    },
    3516606: {
        "nome": "Gália",
        "grupo": "Região Imediata",
        "porte": "Pequeno Porte I",
        "pop": 6380,
    },
    3506003: {
        "nome": "Bauru",
        "grupo": "Polo Centro-Oeste",
        "porte": "Grande Porte",
        "pop": 379146,
    },
    3504008: {
        "nome": "Assis",
        "grupo": "Polo Centro-Oeste",
        "porte": "Médio-Grande Porte",
        "pop": 101409,
    },
    3555000: {
        "nome": "Tupã",
        "grupo": "Polo Centro-Oeste",
        "porte": "Médio Porte",
        "pop": 63928,
    },
    3534708: {
        "nome": "Ourinhos",
        "grupo": "Polo Centro-Oeste",
        "porte": "Médio-Grande Porte",
        "pop": 103970,
    },
    3527108: {
        "nome": "Lins",
        "grupo": "Polo Centro-Oeste",
        "porte": "Médio Porte",
        "pop": 74779,
    },
    3541406: {
        "nome": "Presidente Prudente",
        "grupo": "Peer Group Homólogo",
        "porte": "Médio-Grande Porte",
        "pop": 225668,
    },
    3502804: {
        "nome": "Araçatuba",
        "grupo": "Peer Group Homólogo",
        "porte": "Médio-Grande Porte",
        "pop": 200124,
    },
    3548906: {
        "nome": "São Carlos",
        "grupo": "Peer Group Homólogo",
        "porte": "Grande Porte",
        "pop": 254484,
    },
    3503208: {
        "nome": "Araraquara",
        "grupo": "Peer Group Homólogo",
        "porte": "Grande Porte",
        "pop": 242228,
    },
    3543907: {
        "nome": "Rio Claro",
        "grupo": "Peer Group Homólogo",
        "porte": "Médio-Grande Porte",
        "pop": 201418,
    },
    3507506: {
        "nome": "Botucatu",
        "grupo": "Peer Group Homólogo",
        "porte": "Médio-Grande Porte",
        "pop": 145155,
    },
    3525300: {
        "nome": "Jaú",
        "grupo": "Peer Group Homólogo",
        "porte": "Médio-Grande Porte",
        "pop": 133448,
    },
}

# Definir catalogo da dimensao rede
REDES_CATALOGO = [
    {
        "sk_rede": 1,
        "cod_rede": 1,
        "nome_rede": "Federal",
        "esfera_governamental": "Pública Federal",
    },
    {
        "sk_rede": 2,
        "cod_rede": 2,
        "nome_rede": "Estadual",
        "esfera_governamental": "Pública Estadual",
    },
    {
        "sk_rede": 3,
        "cod_rede": 3,
        "nome_rede": "Municipal",
        "esfera_governamental": "Pública Municipal",
    },
    {
        "sk_rede": 4,
        "cod_rede": 0,
        "nome_rede": "Total",
        "esfera_governamental": "Consolidado do Território",
    },
]

ANOS_ANALISE = list(range(2015, 2026))


def gerar_dimensoes():
  print("-> Gerando tabelas de dimensão...")

  # Gerar Dimensao Municipio
  linhas_mun = []
  for cod_ibge, meta in MUNICIPIOS_AMOSTRA.items():
    linhas_mun.append({
        "sk_municipio": cod_ibge,
        "cod_ibge": cod_ibge,
        "nome_municipio": meta["nome"],
        "sigla_uf": "SP",
        "regiao": "Sudeste",
        "populacao_censo_2022": meta["pop"],
        "porte_populacional": meta["porte"],
        "grupo_analitico": meta["grupo"],
    })
  df_dim_mun = pd.DataFrame(linhas_mun)
  df_dim_mun.to_csv(DIR_GOLD / "dim_municipio.csv", index=False)

  # Gerar Dimensao Tempo
  linhas_tempo = []
  for ano in ANOS_ANALISE:
    eh_saeb = (ano % 2 != 0) and (ano >= 2005)
    linhas_tempo.append({
        "sk_tempo": ano,
        "ano": ano,
        "eh_ano_saeb": eh_saeb,
        "ciclo_avaliacao": "Ciclo SAEB" if eh_saeb else "Interstício",
        "decada": (ano // 10) * 10,
        "quinquenio": f"{ano // 5 * 5}-{ano // 5 * 5 + 4}",
    })
  df_dim_tempo = pd.DataFrame(linhas_tempo)
  df_dim_tempo.to_csv(DIR_GOLD / "dim_tempo.csv", index=False)

  # Gerar Dimensao Rede
  df_dim_rede = pd.DataFrame(REDES_CATALOGO)
  df_dim_rede.to_csv(DIR_GOLD / "dim_rede.csv", index=False)

  print("   ✓ Dimensões salvas na pasta Gold!")
  return df_dim_mun, df_dim_tempo, df_dim_rede


def gerar_fato_central():
  print("\n-> Consolidando a Tabela Fato Central (fato_execucao_educacional)...")

  # Gerar matriz cartesiana do grao atomico (Municipio x Ano x Rede)
  cods_ibge = list(MUNICIPIOS_AMOSTRA.keys())
  redes_analise = [2, 3]  # Foco analitico: 2 = Estadual, 3 = Municipal

  produto = list(itertools.product(cods_ibge, ANOS_ANALISE, redes_analise))
  df_fato = pd.DataFrame(
      produto, columns=["sk_municipio", "sk_tempo", "sk_rede"]
  )

  # Adicionar cod_ibge e ano para cruzamento com bases silver
  df_fato["cod_ibge"] = df_fato["sk_municipio"]
  df_fato["ano"] = df_fato["sk_tempo"]
  df_fato["nome_rede"] = df_fato["sk_rede"].map({2: "Estadual", 3: "Municipal"})

  # Cruzar dados fiscais do Siconfi
  path_siconfi = DIR_SILVER / "stg_siconfi_despesas.csv"
  if path_siconfi.exists():
    df_siconfi = pd.read_csv(path_siconfi)
    cols_fiscais = [
        "despesa_liquidada_educacao",
        "desp_liq_fundamental",
        "desp_liq_infantil",
        "despesa_empenhada_educacao",
        "desp_emp_fundamental",
        "desp_emp_infantil",
    ]

    # Mesclar dados fiscais
    df_fato = df_fato.merge(
        df_siconfi[["cod_ibge", "ano"] + cols_fiscais],
        on=["cod_ibge", "ano"],
        how="left",
    )

    # Anular despesas para a rede estadual (regra anti-duplicacao)
    for col in cols_fiscais:
      df_fato.loc[df_fato["sk_rede"] != 3, col] = np.nan
  else:
    print("   ! Aviso: stg_siconfi_despesas.csv não encontrado na Silver.")

  # Cruzar dados de infraestrutura da Sinopse do Censo Escolar
  path_censo = DIR_SILVER / "stg_censo_sinopse.csv"
  if path_censo.exists():
    df_censo = pd.read_csv(path_censo)

    # Separar colunas da rede municipal
    mapa_mun = {
        "mat_creche": "mat_creche",
        "mat_pre_escola": "mat_pre_escola",
        "mat_anos_iniciais": "mat_anos_iniciais",
        "mat_anos_finais": "mat_anos_finais",
        "mat_especial_classes_comuns": "mat_especial_classes_comuns",
        "docentes_iniciais": "docentes_iniciais",
        "docentes_finais": "docentes_finais",
        "turmas_iniciais": "turmas_iniciais",
        "turmas_finais": "turmas_finais",
        "escolas_creche": "escolas_creche",
        "escolas_pre_escola": "escolas_pre_escola",
        "escolas_iniciais": "escolas_iniciais",
        "escolas_finais": "escolas_finais",
    }

    # Separar colunas da rede estadual
    mapa_est = {
        "mat_creche_estadual": "mat_creche",
        "mat_pre_escola_estadual": "mat_pre_escola",
        "mat_anos_iniciais_estadual": "mat_anos_iniciais",
        "mat_anos_finais_estadual": "mat_anos_finais",
        "escolas_creche_estadual": "escolas_creche",
        "escolas_pre_escola_estadual": "escolas_pre_escola",
        "escolas_iniciais_estadual": "escolas_iniciais",
        "escolas_finais_estadual": "escolas_finais",
    }

    cols_base = ["cod_ibge", "ano"]

    # Mesclar dados censitarios municipais
    cols_mun_exist = [c for c in mapa_mun.keys() if c in df_censo.columns]
    df_censo_mun = df_censo[cols_base + cols_mun_exist].copy()
    df_censo_mun["sk_rede"] = 3
    df_censo_mun = df_censo_mun.rename(columns=mapa_mun)

    # Mesclar dados censitarios estaduais
    cols_est_exist = [c for c in mapa_est.keys() if c in df_censo.columns]
    df_censo_est = df_censo[cols_base + cols_est_exist].copy()
    df_censo_est["sk_rede"] = 2
    df_censo_est = df_censo_est.rename(columns=mapa_est)

    df_censo_longo = pd.concat(
        [df_censo_mun, df_censo_est], ignore_index=True
    ).drop_duplicates(subset=["cod_ibge", "ano", "sk_rede"])

    cols_censo_join = [
        c for c in df_censo_longo.columns if c not in cols_base + ["sk_rede"]
    ]
    df_fato = df_fato.merge(
        df_censo_longo, on=["cod_ibge", "ano", "sk_rede"], how="left"
    )

    # Preencher metricas de contagem vazias com zero
    for c in cols_censo_join:
      df_fato[c] = df_fato[c].fillna(0).astype(int)
  else:
    print("   ! Aviso: stg_censo_sinopse.csv não encontrado na Silver.")

  # Cruzar dados de qualidade do IDEB e SAEB
  path_qual = DIR_SILVER / "stg_inep_qualidade.csv"
  if path_qual.exists():
    df_qual = pd.read_csv(path_qual)
    cols_qual = [
        c
        for c in df_qual.columns
        if c not in ["cod_ibge", "ano", "rede", "municipio", "uf"]
    ]

    df_fato = df_fato.merge(
        df_qual,
        left_on=["cod_ibge", "ano", "nome_rede"],
        right_on=["cod_ibge", "ano", "rede"],
        how="left",
    )
    df_fato = df_fato.drop(
        columns=[c for c in ["rede", "municipio", "uf"] if c in df_fato.columns]
    )
  else:
    print("   ! Aviso: stg_inep_qualidade.csv não encontrado na Silver.")

  # Cruzar dados socioeconomicos do INSE
  path_inse = DIR_SILVER / "stg_inep_inse.csv"
  if path_inse.exists():
    df_inse = pd.read_csv(path_inse)
    cols_inse = ["inse_score", "inse_classificacao", "qtd_alunos_inse"]

    df_fato = df_fato.merge(
        df_inse[["cod_ibge", "ano", "rede"] + cols_inse],
        left_on=["cod_ibge", "ano", "nome_rede"],
        right_on=["cod_ibge", "ano", "rede"],
        how="left",
    )
    df_fato = df_fato.drop(
        columns=[c for c in ["rede"] if c in df_fato.columns]
    )
  else:
    print("   ! Aviso: stg_inep_inse.csv não encontrado na Silver.")

  # Remover colunas auxiliares de juncao
  df_fato = df_fato.drop(columns=["cod_ibge", "ano", "nome_rede"])

  # Ordenar linhas pelo grao
  df_fato = df_fato.sort_values(by=["sk_tempo", "sk_municipio", "sk_rede"])

  # Salvar arquivo da tabela fato na camada Gold
  caminho_fato = DIR_GOLD / "fato_execucao_educacional.csv"
  df_fato.to_csv(caminho_fato, index=False)
  print(
      f"   ✓ Fato consolidada com sucesso: {caminho_fato} ({len(df_fato)}"
      " registros)"
  )


if __name__ == "__main__":
  gerar_dimensoes()
  gerar_fato_central()