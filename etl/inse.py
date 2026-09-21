'''
ETL NIVEL SOCIOECONOMICO (INSE - INEP)
DESC: EXTRAI E PADRONIZA O INDICADOR DE NIVEL SOCIOECONOMICO MUNICIPAL POR REDE DE ENSINO
FONTE: DADOS ABERTOS DO INEP (INDICADORES EDUCACIONAIS - INSE)
'''

from pathlib import Path
import numpy as np
import pandas as pd

# Definir diretorios de trabalho
BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if "__file__" in locals()
    else Path.cwd()
)
DIR_RAW = BASE_DIR / "data" / "raw"
DIR_SILVER = BASE_DIR / "data" / "silver"
DIR_SILVER.mkdir(parents=True, exist_ok=True)

# Mapear codigos de rede para nomes analiticos padronizados
MAPA_REDES = {
    0: "Total",
    "0": "Total",
    2: "Estadual",
    "2": "Estadual",
    3: "Municipal",
    "3": "Municipal",
}


def localizar_arquivo_inse() -> Path | None:
  # Buscar arquivos compativeis nas extensoes suportadas
  for ext in ["csv", "parquet", "xlsx", "ods"]:
    arquivos = list(DIR_RAW.glob(f"*inse*.{ext}"))
    if arquivos:
      return arquivos[0]
  return None


def carregar_dataframe(caminho: Path) -> pd.DataFrame:
  # Carregar arquivo respeitando a extensao correspondente
  sufixo = caminho.suffix.lower()
  if sufixo == ".parquet":
    return pd.read_parquet(caminho)
  if sufixo in [".xlsx", ".ods"]:
    engine = "calamine" if sufixo == ".ods" else None
    return pd.read_excel(caminho, engine=engine)

  # Detectar separador e carregar arquivo CSV
  try:
    return pd.read_csv(caminho, sep=",", low_memory=False)
  except Exception:
    return pd.read_csv(caminho, sep=";", low_memory=False)


def classificar_faixa_inse(escore: float) -> str:
  # Classificar escore continuo nos 8 niveis oficiais do INEP
  if np.isnan(escore):
    return "Não Informado"
  if escore < 3.86:
    return "Nível I"
  if escore < 4.39:
    return "Nível II"
  if escore < 4.92:
    return "Nível III"
  if escore < 5.45:
    return "Nível IV"
  if escore < 5.98:
    return "Nível V"
  if escore < 6.51:
    return "Nível VI"
  if escore < 7.04:
    return "Nível VII"
  return "Nível VIII"


def executar_pipeline_inse():
  # Localizar arquivo bruto na pasta raw
  caminho_arquivo = localizar_arquivo_inse()
  if not caminho_arquivo:
    print("❌ Nenhum arquivo de INSE encontrado em 'data/raw/'.")
    return

  print(f"-> Processando base de INSE: {caminho_arquivo.name}...")
  df_raw = carregar_dataframe(caminho_arquivo)

  # Padronizar nomes das colunas em minusculo
  df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]

  # Localizar coluna identificadora do municipio
  col_ibge = next(
      (
          c
          for c in df_raw.columns
          if c in ["id_municipio", "cod_ibge", "codigo_municipio"]
      ),
      None,
  )
  if not col_ibge:
    print(
        "❌ Coluna de identificação do município não localizada no arquivo de"
        " INSE."
    )
    return

  # Filtrar apenas registros consolidados do municipio (urbano e rural)
  if "tipo_localizacao" in df_raw.columns:
    df_raw = df_raw[df_raw["tipo_localizacao"].astype(str).str.strip() == "0"]

  # Filtrar e padronizar redes municipal, estadual e total
  if "rede" in df_raw.columns:
    df_raw = df_raw[df_raw["rede"].isin(MAPA_REDES.keys())].copy()
    df_raw["rede"] = df_raw["rede"].map(MAPA_REDES)
  else:
    df_raw["rede"] = "Total"

  # Filtrar e validar codigos IBGE validos
  cod_series = pd.to_numeric(df_raw[col_ibge], errors="coerce")
  mask_ibge = cod_series.between(1100000, 5399999)
  df_clean = df_raw.loc[mask_ibge].copy()

  # Converter chaves territoriais e temporais para inteiro
  df_clean["cod_ibge"] = cod_series.loc[mask_ibge].astype(int)
  df_clean["ano"] = pd.to_numeric(df_clean["ano"], errors="coerce").astype(int)

  # Converter escore para float e aplicar classificacao em faixas
  df_clean["inse_score"] = pd.to_numeric(
      df_clean["inse"].astype(str).str.replace(",", "."), errors="coerce"
  )
  df_clean["inse_classificacao"] = df_clean["inse_score"].apply(
      classificar_faixa_inse
  )

  # Tratar quantidade de alunos avaliados quando disponivel
  if "quantidade_alunos_inse" in df_clean.columns:
    df_clean["qtd_alunos_inse"] = (
        pd.to_numeric(df_clean["quantidade_alunos_inse"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
  else:
    df_clean["qtd_alunos_inse"] = np.nan

  # Selecionar e ordenar colunas finais da camada Silver
  colunas_finais = [
      "cod_ibge",
      "ano",
      "rede",
      "inse_score",
      "inse_classificacao",
      "qtd_alunos_inse",
  ]

  df_silver = df_clean[colunas_finais].sort_values(
      by=["ano", "cod_ibge", "rede"]
  )

  # Salvar CSV tratado na camada Silver
  caminho_csv = DIR_SILVER / "stg_inep_inse.csv"
  df_silver.to_csv(caminho_csv, index=False, encoding="utf-8")
  print(
      f"✅ Base Silver de INSE consolidada: {caminho_csv} ({len(df_silver)}"
      " registros)"
  )


if __name__ == "__main__":
  executar_pipeline_inse()