'''
ETL SINOPSE ESTATISTICA DA EDUCACAO BASICA (INEP 2015-2025)
DESC: EXTRAI MATRICULAS, DOCENTES, TURMAS E ESCOLAS POR ETAPA E REDE DE ENSINO
FONTE: DADOS ABERTOS DO INEP (SINOPSES ESTATISTICAS DA EDUCACAO BASICA)
'''

from collections.abc import Sequence
from pathlib import Path
import re
import unicodedata
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

# Definir lista de metricas esperadas da camada Silver
METRICAS_ESPERADAS = [
    "mat_creche",
    "mat_creche_estadual",
    "mat_pre_escola",
    "mat_pre_escola_estadual",
    "mat_anos_iniciais",
    "mat_anos_iniciais_estadual",
    "mat_anos_finais",
    "mat_anos_finais_estadual",
    "docentes_iniciais",
    "docentes_finais",
    "turmas_iniciais",
    "turmas_finais",
    "mat_especial_classes_comuns",
    "escolas_creche",
    "escolas_creche_estadual",
    "escolas_pre_escola",
    "escolas_pre_escola_estadual",
    "escolas_iniciais",
    "escolas_iniciais_estadual",
    "escolas_finais",
    "escolas_finais_estadual",
]


def normalizar_texto(txt: object) -> str:
  # Normalizar texto removendo acentos e caracteres especiais
  txt_nfkd = unicodedata.normalize("NFKD", str(txt).lower())
  return "".join([c for c in txt_nfkd if not unicodedata.combining(c)])


def confirmar_codigo_ibge(valor: object) -> bool:
  # Validar se o valor corresponde a um codigo IBGE valido
  try:
    num = int(float(str(valor).strip()))
    return 1100000 <= num <= 5399999
  except (ValueError, TypeError, OverflowError):
    return False


def encontrar_aba(
    nomes_abas: Sequence[str | int], padrao_num: str, palavra_chave: str = ""
) -> str | None:
  # Localizar nome exato da aba na planilha por numero e palavra-chave
  padroes = padrao_num.split("|")
  palavra_norm = normalizar_texto(palavra_chave) if palavra_chave else ""

  for padrao in padroes:
    # Tratar separadores de numeracao de aba
    partes = [re.escape(p) for p in re.split(r"[._\s\-]", padrao) if p]
    miolo = r"[._\s\-]+"
    regex_exata = rf"(?:^|\D){miolo.join(partes)}(?:\D|$)"

    # Priorizar combinacao de palavra-chave e numero
    if palavra_norm:
      for nome in nomes_abas:
        nome_str = str(nome)
        nome_norm = normalizar_texto(nome_str)
        if palavra_norm in nome_norm and re.search(
            regex_exata, nome_str, re.IGNORECASE
        ):
          return nome_str

    # Buscar apenas pelo numero exato da aba
    for nome in nomes_abas:
      nome_str = str(nome)
      if re.search(regex_exata, nome_str, re.IGNORECASE):
        return nome_str

  return None


def extrair_metrica_df(
    df_raw: pd.DataFrame,
    col_alvo: int | list[int],
    nome_metrica: str,
    linha_skip: int,
) -> pd.DataFrame:
  # Pular linhas de cabecalho estrutural
  dados = df_raw.iloc[linha_skip:].reset_index(drop=True)

  # Filtrar municipios por codigo IBGE valido
  col_ibge = dados.iloc[:, 3]
  mascara_ibge = col_ibge.apply(confirmar_codigo_ibge)
  df_filtrado = dados[mascara_ibge].copy()

  # Inicializar dataframe com codigo IBGE tratado
  resultado = pd.DataFrame()
  resultado["cod_ibge"] = pd.to_numeric(
      col_ibge[mascara_ibge], errors="coerce"
  ).astype(int)

  # Validar existencia das colunas no arquivo
  cols = [col_alvo] if isinstance(col_alvo, int) else col_alvo
  num_colunas = df_filtrado.shape[1]
  cols_validas = [c for c in cols if c < num_colunas]

  if not cols_validas:
    resultado[nome_metrica] = 0
    return resultado

  # Converter metricas para numerico e somar quando houver multiplas colunas
  dados_metricas = (
      df_filtrado.iloc[:, cols_validas].apply(pd.to_numeric, errors="coerce").fillna(0)
  )
  resultado[nome_metrica] = dados_metricas.sum(axis=1).astype(int)

  return resultado


def processar_ano(caminho_arquivo: Path) -> pd.DataFrame | None:
  # Identificar ano no nome do arquivo
  match_ano = re.search(r"\d{4}", caminho_arquivo.name)
  if not match_ano:
    return None

  ano = int(match_ano.group(0))
  if not (2015 <= ano <= 2025):
    return None

  print(f"-> Processando Censo Escolar {ano}...")
  # Carregar arquivo com engine calamine
  excel = pd.ExcelFile(caminho_arquivo, engine="calamine")
  nomes_abas: list[str] = [str(s) for s in excel.sheet_names]

  # Definir salto de linhas de cabecalho por ano
  linha_skip = 14 if ano == 2025 else 11

  # Localizar aba base de ensino fundamental
  aba_base = (
      encontrar_aba(nomes_abas, "1.20", "fund")
      if ano == 2025
      else encontrar_aba(nomes_abas, "1.14", "fund")
  )
  if not aba_base:
    for nome in nomes_abas:
      if "fund" in normalizar_texto(nome):
        aba_base = nome
        break
  if not aba_base:
    aba_base = nomes_abas[0]

  # Extrair base municipal inicial com codigo IBGE, UF e nome
  df_base_raw = excel.parse(sheet_name=aba_base, header=None).iloc[linha_skip:]
  mask_ibge = df_base_raw.iloc[:, 3].apply(confirmar_codigo_ibge)
  df_base = df_base_raw[mask_ibge].copy()

  df_consolidado = pd.DataFrame({
      "ano": ano,
      "cod_ibge": pd.to_numeric(df_base.iloc[:, 3], errors="coerce").astype(
          int
      ),
      "uf": df_base.iloc[:, 1].astype(str).str.strip(),
      "municipio": df_base.iloc[:, 2].astype(str).str.strip(),
  }).drop_duplicates("cod_ibge")

  # Definir mapa de abas e colunas para 2025
  if ano == 2025:
    config_metricas = [
        (
            "1.8",
            "infantil",
            [
                (17, "mat_creche_estadual"),
                (18, "mat_creche"),
                (27, "mat_pre_escola_estadual"),
                (28, "mat_pre_escola"),
            ],
        ),
        (
            "1.20",
            "fund",
            [
                (17, "mat_anos_iniciais_estadual"),
                (18, "mat_anos_iniciais"),
                (27, "mat_anos_finais_estadual"),
                (28, "mat_anos_finais"),
            ],
        ),
        ("2.26", "", [(8, "docentes_iniciais")]),
        ("2.31", "", [(8, "docentes_finais")]),
        ("4.18", "", [([9, 19, 29, 39, 49, 59], "turmas_iniciais")]),
        ("4.22", "", [([9, 19, 29, 39, 49], "turmas_finais")]),
        ("1.61", "", [(8, "mat_especial_classes_comuns")]),
        (
            "3.5",
            "infantil",
            [
                (17, "escolas_creche_estadual"),
                (18, "escolas_creche"),
                (27, "escolas_pre_escola_estadual"),
                (28, "escolas_pre_escola"),
            ],
        ),
        (
            "3.15",
            "fund",
            [
                (17, "escolas_iniciais_estadual"),
                (18, "escolas_iniciais"),
                (27, "escolas_finais_estadual"),
                (28, "escolas_finais"),
            ],
        ),
    ]
  # Definir mapa de abas e colunas para anos anteriores a 2025
  else:
    config_metricas = [
        (
            "1.5",
            "infantil",
            [
                (7, "mat_creche_estadual"),
                (8, "mat_creche"),
                (12, "mat_pre_escola_estadual"),
                (13, "mat_pre_escola"),
            ],
        ),
        (
            "1.14",
            "fund",
            [
                (7, "mat_anos_iniciais_estadual"),
                (8, "mat_anos_iniciais"),
                (12, "mat_anos_finais_estadual"),
                (13, "mat_anos_finais"),
            ],
        ),
        ("2.21", "", [(8, "docentes_iniciais")]),
        ("2.25|2.26", "", [(8, "docentes_finais")]),
        ("4.8", "", [([8, 13, 18, 23, 28, 33], "turmas_iniciais")]),
        ("4.10", "", [([8, 13, 18, 23, 28], "turmas_finais")]),
        ("1.40|1.41", "", [([8, 13], "mat_especial_classes_comuns")]),
        (
            "3.4",
            "infantil",
            [
                (7, "escolas_creche_estadual"),
                (8, "escolas_creche"),
                (12, "escolas_pre_escola_estadual"),
                (13, "escolas_pre_escola"),
            ],
        ),
        (
            "3.10",
            "fund",
            [
                (7, "escolas_iniciais_estadual"),
                (8, "escolas_iniciais"),
                (12, "escolas_finais_estadual"),
                (13, "escolas_finais"),
            ],
        ),
    ]

  # Extrair metricas de cada aba configurada e mesclar na base municipal
  for padrao_num, palavra, lista_cols in config_metricas:
    aba = encontrar_aba(nomes_abas, padrao_num, palavra)
    if aba:
      df_raw_aba = excel.parse(sheet_name=aba, header=None)
      for col, metrica in lista_cols:
        df_metrica = extrair_metrica_df(
            df_raw_aba, col, metrica, linha_skip
        ).drop_duplicates("cod_ibge")
        df_consolidado = df_consolidado.merge(
            df_metrica, on="cod_ibge", how="left"
        )

  return df_consolidado


def executar_pipeline():
  # Localizar arquivos de sinopse na pasta raw
  arquivos = sorted(DIR_RAW.glob("*sinopse*.ods"))
  dfs_anos = []

  # Processar cada ano da serie historica
  for arq in arquivos:
    df_ano = processar_ano(arq)
    if df_ano is not None:
      dfs_anos.append(df_ano)

  if not dfs_anos:
    print("Nenhum arquivo ODS válido processado.")
    return

  # Concatenar todos os anos processados
  df_final = pd.concat(dfs_anos, ignore_index=True)

  # Preencher metricas ausentes com zero e converter para inteiro
  for col in METRICAS_ESPERADAS:
    if col not in df_final.columns:
      df_final[col] = 0
    df_final[col] = df_final[col].fillna(0).astype(int)

  # Ordenar base consolidada por ano e municipio
  df_final.sort_values(by=["ano", "cod_ibge"], inplace=True)

  # Salvar CSV tratado na camada Silver
  caminho_csv = DIR_SILVER / "stg_censo_sinopse.csv"
  df_final.to_csv(caminho_csv, index=False, encoding="utf-8")
  print(f"\n✅ Base Silver (2015-2025) consolidada: {caminho_csv}")


if __name__ == "__main__":
  executar_pipeline()