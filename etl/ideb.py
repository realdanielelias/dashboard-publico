'''
ETL QUALIDADE EDUCACIONAL (IDEB E SAEB 2015-2025)
DESC: EXTRAI NOTAS DO IDEB, METAS, TAXAS DE RENDIMENTO E PROFICIENCIAS DO SAEB POR MUNICIPIO E REDE
FONTE: DADOS ABERTOS DO INEP (PLANILHAS DE RESULTADOS DO IDEB POR MUNICIPIO)
'''

from pathlib import Path
import re
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

# Definir anos de avaliacao e ciclos de metas
ANOS_AVALIACAO = [2015, 2017, 2019, 2021, 2023, 2025]
TODOS_ANOS_BIENAIS = [
    2005,
    2007,
    2009,
    2011,
    2013,
    2015,
    2017,
    2019,
    2021,
    2023,
    2025,
]
ANOS_METAS_CICLO1 = [2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021]


def limpar_numero(val: object) -> float:
  # Tratar caracteres especiais, valores vazios e converter para float
  if val is None:
    return np.nan
  if isinstance(val, (int, float)):
    return np.nan if np.isnan(val) else float(val)

  s = str(val).strip().replace(",", ".")
  if s in {"-", "ND", "*", "", "nan", "None", "<NA>"}:
    return np.nan
  try:
    return float(s)
  except (ValueError, TypeError):
    return np.nan


def localizar_arquivo(padroes: list[str]) -> Path | None:
  # Buscar arquivos compativeis na pasta raw
  for ext in ["ods", "xlsx", "xls"]:
    for padrao in padroes:
      arquivos = list(DIR_RAW.glob(f"*{padrao}*.{ext}"))
      if arquivos:
        return arquivos[0]
  return None


def localizar_linha_disciplinas(df_raw: pd.DataFrame) -> int:
  # Localizar linha de subcabecalho contendo as disciplinas
  for idx in range(min(20, len(df_raw))):
    linha = df_raw.iloc[idx].astype(str).tolist()
    if any(re.search(r"matem[aá]tica", c, re.IGNORECASE) for c in linha):
      return idx
  return 8


def obter_coluna_numerica(df: pd.DataFrame, col_idx: int | None) -> pd.Series:
  # Extrair e converter coluna numerica com tratamento de nulos
  if col_idx is None:
    return pd.Series(np.nan, index=df.index, dtype=float)
  return df.iloc[:, col_idx].map(limpar_numero)


def processar_planilha_ideb(
    caminho_arquivo: Path, sufixo_etapa: str
) -> pd.DataFrame:
  print(f"\n-> Processando {caminho_arquivo.name} ({sufixo_etapa})...")

  # Carregar arquivo com engine adequada
  engine = "calamine" if caminho_arquivo.suffix.lower() == ".ods" else None
  excel = (
      pd.ExcelFile(caminho_arquivo, engine=engine)
      if engine
      else pd.ExcelFile(caminho_arquivo)
  )

  df_raw = excel.parse(sheet_name=0, header=None)
  idx_disciplinas = localizar_linha_disciplinas(df_raw)
  limite_header = min(15, len(df_raw))

  # Localizar colunas de codigo IBGE e rede de ensino
  col_ibge, col_rede = None, None
  for r in range(limite_header):
    row_vals = df_raw.iloc[r].astype(str).tolist()
    for c_idx, val in enumerate(row_vals):
      val_clean = val.lower().strip()
      if col_ibge is None and (
          "código do município" in val_clean or "codigo do municipio" in val_clean
      ):
        col_ibge = c_idx
      if col_rede is None and val_clean == "rede":
        col_rede = c_idx

  col_ibge_idx = 1 if col_ibge is None else col_ibge
  col_rede_idx = 3 if col_rede is None else col_rede

  # Mapear colunas do SAEB (Matematica, Lingua Portuguesa e Padronizada)
  cols_mat = [
      c
      for c in range(df_raw.shape[1])
      if re.search(
          r"matem[aá]tica",
          str(df_raw.iloc[idx_disciplinas, c]),
          re.IGNORECASE,
      )
  ]

  mapa_saeb: dict[int, dict[str, int | None]] = {}
  for ano_b, c_mat in zip(TODOS_ANOS_BIENAIS, cols_mat):
    if ano_b in ANOS_AVALIACAO:
      mapa_saeb[ano_b] = {
          "mat": c_mat,
          "lp": c_mat + 1 if c_mat + 1 < df_raw.shape[1] else None,
          "padrao": c_mat + 2 if c_mat + 2 < df_raw.shape[1] else None,
      }

  # Mapear colunas do IDEB observado
  mapa_ideb: dict[int, int] = {}
  for ano in ANOS_AVALIACAO:
    ano_str = str(ano)
    for r in range(limite_header):
      for c_idx in range(4, df_raw.shape[1]):
        val = str(df_raw.iloc[r, c_idx]).strip()
        if (
            ano_str in val
            and re.search(r"ideb", val, re.IGNORECASE)
            and re.search(r"n\s*x\s*p|\(n", val, re.IGNORECASE)
        ):
          mapa_ideb[ano] = c_idx
          break
      if ano in mapa_ideb:
        break

  # Mapear colunas de taxa de rendimento
  cols_rend = [
      c
      for c in range(4, df_raw.shape[1])
      if any(
          re.search(r"rendimento", str(df_raw.iloc[r, c]), re.IGNORECASE)
          for r in range(limite_header)
      )
  ]

  mapa_rendimento: dict[int, int] = {}
  if len(cols_rend) >= len(TODOS_ANOS_BIENAIS):
    for ano_b, c_rend in zip(TODOS_ANOS_BIENAIS, cols_rend):
      if ano_b in ANOS_AVALIACAO:
        mapa_rendimento[ano_b] = c_rend
  else:
    # Usar fallback estrutural caso rendimento nao esteja explicito no cabecalho
    tam_bloco = 7 if sufixo_etapa == "iniciais" else 6
    offset_p = 6 if sufixo_etapa == "iniciais" else 5
    for idx_b, ano_b in enumerate(TODOS_ANOS_BIENAIS):
      if ano_b in ANOS_AVALIACAO:
        col_calc = (col_rede_idx + 1) + (idx_b * tam_bloco) + offset_p
        if col_calc < df_raw.shape[1]:
          mapa_rendimento[ano_b] = col_calc

  # Mapear colunas de metas projetadas do ciclo
  c_meta_start = None
  for r in range(limite_header):
    for c in range(4, df_raw.shape[1]):
      val = str(df_raw.iloc[r, c])
      if re.search(r"metas?.*ciclo|metas?.*ideb", val, re.IGNORECASE):
        c_meta_start = c
        break
    if c_meta_start is not None:
      break

  mapa_metas: dict[int, int] = {}
  if c_meta_start is not None:
    for offset in range(12):
      c_cand = c_meta_start + offset
      if c_cand < df_raw.shape[1]:
        for r in range(limite_header):
          sub_val = str(df_raw.iloc[r, c_cand]).strip()
          m = re.search(r"\b(20\d\d)\b", sub_val)
          if m:
            ano_m = int(m.group(1))
            if ano_m in ANOS_AVALIACAO:
              mapa_metas[ano_m] = c_cand
            break

  # Exibir diagnostico de mapeamento
  print(f"  -> Colunas Rendimento (P): {mapa_rendimento}")
  print(f"  -> Colunas Metas: {mapa_metas}")
  print(f"  -> Colunas IDEB: {mapa_ideb}")

  # Filtrar linhas validas de municipios pelo codigo IBGE
  dados = df_raw.iloc[idx_disciplinas + 1 :].copy()
  cod_series = pd.to_numeric(dados.iloc[:, col_ibge_idx], errors="coerce")
  mask_ibge = cod_series.between(1100000, 5399999)
  dados = dados.loc[mask_ibge].copy()

  dados["cod_ibge_clean"] = cod_series.loc[mask_ibge].astype(int)
  dados["rede_clean"] = (
      dados.iloc[:, col_rede_idx].astype(str).str.strip().str.capitalize()
  )

  # Filtrar apenas redes municipal e estadual
  mask_rede = dados["rede_clean"].isin(["Municipal", "Estadual"])
  dados = dados.loc[mask_rede].copy()

  # Montar registros anuais normalizados
  registros = []
  for ano in ANOS_AVALIACAO:
    col_ideb = mapa_ideb.get(ano)
    col_meta = mapa_metas.get(ano)
    col_rend = mapa_rendimento.get(ano)
    saeb_info = mapa_saeb.get(ano, {})

    df_ano = pd.DataFrame({
        "cod_ibge": dados["cod_ibge_clean"],
        "ano": ano,
        "rede": dados["rede_clean"],
        f"ideb_{sufixo_etapa}": obter_coluna_numerica(dados, col_ideb),
        f"ideb_meta_{sufixo_etapa}": obter_coluna_numerica(dados, col_meta),
        f"rendimento_{sufixo_etapa}": obter_coluna_numerica(dados, col_rend),
        f"saeb_mat_{sufixo_etapa}": obter_coluna_numerica(
            dados, saeb_info.get("mat")
        ),
        f"saeb_lp_{sufixo_etapa}": obter_coluna_numerica(
            dados, saeb_info.get("lp")
        ),
        f"saeb_nota_{sufixo_etapa}": obter_coluna_numerica(
            dados, saeb_info.get("padrao")
        ),
    })
    registros.append(df_ano)

  # Concatenar todos os anos da etapa
  return pd.concat(registros, ignore_index=True)


def executar_pipeline_qualidade():
  # Localizar arquivos de anos iniciais e finais
  arq_iniciais = localizar_arquivo(
      ["iniciais", "inicial", "1ao5", "anos_iniciais"]
  )
  arq_finais = localizar_arquivo(["finais", "final", "6ao9", "anos_finais"])

  if not arq_iniciais and not arq_finais:
    print("❌ Nenhum arquivo do IDEB encontrado em 'data/raw/'.")
    return

  # Processar dados de anos iniciais
  df_ini = (
      processar_planilha_ideb(arq_iniciais, "iniciais")
      if arq_iniciais
      else None
  )

  # Processar dados de anos finais
  df_fin = (
      processar_planilha_ideb(arq_finais, "finais") if arq_finais else None
  )

  # Unir etapas inicial e final em formato conformed
  if df_ini is not None and df_fin is not None:
    df_qualidade = pd.merge(
        df_ini, df_fin, on=["cod_ibge", "ano", "rede"], how="outer"
    )
  elif df_fin is not None:
    df_qualidade = df_fin
  elif df_ini is not None:
    df_qualidade = df_ini
  else:
    print("❌ Falha no processamento das etapas.")
    return

  # Ordenar base consolidada
  df_qualidade = df_qualidade.sort_values(by=["ano", "cod_ibge", "rede"])

  # Salvar CSV tratado na camada Silver
  caminho_csv = DIR_SILVER / "stg_inep_qualidade.csv"
  df_qualidade.to_csv(caminho_csv, index=False, encoding="utf-8")
  print(f"\n✅ Base Silver de Qualidade consolidada: {caminho_csv}")


if __name__ == "__main__":
  executar_pipeline_qualidade()