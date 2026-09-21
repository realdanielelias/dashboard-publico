'''
ETL SICONFI EDUCACAO (MARILIA, CENTRO-OESTE E PEER GROUP 2015-2025)
DESC: EXTRAI DESPESAS LIQUIDADAS E EMPENHADAS DA EDUCACAO (FUNCAO 12, SUBFUNCOES 361 E 365)
FONTE: HTTPS://APIDATALAKE.TESOURO.GOV.BR/ORDS/SICONFI/TT/RREO (SICONFI / STN)
'''

from pathlib import Path
import time
import pandas as pd
import requests

# Definir diretorios de trabalho e parametros da API
BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if "__file__" in locals()
    else Path.cwd()
)
DIR_SILVER = BASE_DIR / "data" / "silver"
DIR_SILVER.mkdir(parents=True, exist_ok=True)

URL_API_RREO = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
ARQUIVO_SAIDA = DIR_SILVER / "stg_siconfi_despesas.csv"
ANOS_COLETA = list(range(2015, 2026))

# Definir amostra metodologica de 26 municipios e peer groups
MUNICIPIOS_AMOSTRA = {
    # Polo Central
    3529005: {"nome": "Marília", "grupo": "Polo Central"},
    # Regiao Imediata de Marilia
    3516705: {"nome": "Garça", "grupo": "Região Imediata"},
    3540002: {"nome": "Pompeia", "grupo": "Região Imediata"},
    3556602: {"nome": "Vera Cruz", "grupo": "Região Imediata"},
    3534005: {"nome": "Oriente", "grupo": "Região Imediata"},
    3514403: {"nome": "Echaporã", "grupo": "Região Imediata"},
    3533700: {"nome": "Ocauçu", "grupo": "Região Imediata"},
    3527702: {"nome": "Lupércio", "grupo": "Região Imediata"},
    3501400: {"nome": "Álvaro de Carvalho", "grupo": "Região Imediata"},
    3501509: {"nome": "Alvinlândia", "grupo": "Região Imediata"},
    3517703: {"nome": "Guaimbê", "grupo": "Região Imediata"},
    3526001: {"nome": "Júlio Mesquita", "grupo": "Região Imediata"},
    3541703: {"nome": "Quintana", "grupo": "Região Imediata"},
    3516606: {"nome": "Gália", "grupo": "Região Imediata"},
    # Polos Regionais do Centro-Oeste Paulista
    3506003: {"nome": "Bauru", "grupo": "Polo Centro-Oeste"},
    3504008: {"nome": "Assis", "grupo": "Polo Centro-Oeste"},
    3555000: {"nome": "Tupã", "grupo": "Polo Centro-Oeste"},
    3534708: {"nome": "Ourinhos", "grupo": "Polo Centro-Oeste"},
    3527108: {"nome": "Lins", "grupo": "Polo Centro-Oeste"},
    # Pares Homologos Estaduais
    3541406: {"nome": "Presidente Prudente", "grupo": "Peer Group Homólogo"},
    3502804: {"nome": "Araçatuba", "grupo": "Peer Group Homólogo"},
    3548906: {"nome": "São Carlos", "grupo": "Peer Group Homólogo"},
    3503208: {"nome": "Araraquara", "grupo": "Peer Group Homólogo"},
    3543907: {"nome": "Rio Claro", "grupo": "Peer Group Homólogo"},
    3507506: {"nome": "Botucatu", "grupo": "Peer Group Homólogo"},
    3525300: {"nome": "Jaú", "grupo": "Peer Group Homólogo"},
}


def obter_chaves_processadas(caminho_csv: Path) -> set[tuple[int, int]]:
  # Verificar registros ja processados para carga incremental (checkpoint)
  if not caminho_csv.exists():
    return set()
  try:
    df_existente = pd.read_csv(
        caminho_csv, usecols=["cod_ibge", "ano"], dtype=int
    )
    return set(zip(df_existente["cod_ibge"], df_existente["ano"]))
  except Exception:
    return set()


def extrair_siconfi_ano_ente(
    session: requests.Session,
    ano: int,
    cod_ibge: int,
    tentativas_max: int = 3,
) -> dict | None:
  # Configurar parametros da consulta para o 6º bimestre (fechamento anual)
  params = {
      "an_exercicio": ano,
      "nr_periodo": 6,
      "co_tipo_demonstrativo": "RREO",
      "no_anexo": "RREO-Anexo 02",
      "co_esfera": "M",
      "id_ente": cod_ibge,
  }

  for tentativa in range(1, tentativas_max + 1):
    try:
      # Puxar dados da API
      resp = session.get(URL_API_RREO, params=params, timeout=30)
      if resp.status_code == 200:
        items = resp.json().get("items", [])
        if not items:
          return None

        df = pd.DataFrame(items)
        if "coluna" not in df.columns or "conta" not in df.columns:
          return None

        # Filtrar linhas de despesas liquidadas e empenhadas ate o bimestre
        mask_liq = df["coluna"].str.contains(
            "LIQUIDADAS ATÉ O BIMESTRE", case=False, na=False
        )
        mask_emp = df["coluna"].str.contains(
            "EMPENHADAS ATÉ O BIMESTRE", case=False, na=False
        )

        def obter_valor(df_sub, regex_conta):
          # Extrair valor numerico por expressao regular na conta contabil
          linha = df_sub[
              df_sub["conta"].str.contains(regex_conta, case=False, na=False)
          ]
          return float(linha["valor"].iloc[0]) if not linha.empty else 0.0

        df_liq = df[mask_liq]
        df_emp = df[mask_emp]

        # Montar registro com valores liquidados e empenhados por subfuncao
        return {
            "ano": ano,
            "cod_ibge": cod_ibge,
            # Despesas liquidadas
            "despesa_liquidada_educacao": obter_valor(
                df_liq, r"^12\b|^educação$|^educacao$"
            ),
            "desp_liq_fundamental": obter_valor(df_liq, r"fundamental"),
            "desp_liq_infantil": obter_valor(df_liq, r"infantil"),
            # Despesas empenhadas
            "despesa_empenhada_educacao": obter_valor(
                df_emp, r"^12\b|^educação$|^educacao$"
            ),
            "desp_emp_fundamental": obter_valor(df_emp, r"fundamental"),
            "desp_emp_infantil": obter_valor(df_emp, r"infantil"),
        }

      # Aguardar em caso de limite de requisicoes ou instabilidade do servidor
      elif resp.status_code in [429, 502, 503, 504]:
        time.sleep(2 * tentativa)
      else:
        return None

    # Tratar falhas de conexao com espera progressiva
    except requests.exceptions.RequestException:
      time.sleep(1.5 * tentativa)

  return None


def salvar_incremental(registro: dict, caminho_csv: Path) -> None:
  # Salvar registro incrementalmente no arquivo CSV
  df_linha = pd.DataFrame([registro])
  arquivo_existe = caminho_csv.exists() and caminho_csv.stat().st_size > 0
  df_linha.to_csv(
      caminho_csv,
      mode="a",
      header=not arquivo_existe,
      index=False,
      encoding="utf-8",
  )


def executar_pipeline():
  print("=" * 80)
  print("🚀 INICIANDO COLETA SICONFI - MARÍLIA, CENTRO-OESTE E PEER GROUP (SP)")
  print("=" * 80)

  total_mun = len(MUNICIPIOS_AMOSTRA)
  # Carregar chaves concluidas para controle de checkpoint
  chaves_concluidas = obter_chaves_processadas(ARQUIVO_SAIDA)

  if chaves_concluidas:
    print(f"-> Checkpoint ativo: {len(chaves_concluidas)} registros já salvos.")

  # Inicializar sessao HTTP para reaproveitar conexoes
  session = requests.Session()

  # Iterar pelos municipios e anos da amostra
  for idx, (cod_ibge, meta) in enumerate(MUNICIPIOS_AMOSTRA.items(), 1):
    nome = meta["nome"]
    grupo = meta["grupo"]

    print(f"\n[{idx}/{total_mun}] {nome} ({cod_ibge}) — [{grupo}]")

    for ano in ANOS_COLETA:
      # Pular registro se ja foi processado anteriormente
      if (cod_ibge, ano) in chaves_concluidas:
        continue

      dado = extrair_siconfi_ano_ente(session, ano, cod_ibge)
      if dado:
        # Salvar registro no disco e atualizar checkpoint
        salvar_incremental(dado, ARQUIVO_SAIDA)
        chaves_concluidas.add((cod_ibge, ano))
        print(f"   ✓ Exercício {ano}: OK")
      else:
        print(f"   - Exercício {ano}: Sem dados")

      # Pausa defensiva entre requisicoes
      time.sleep(0.3)

  print("\n" + "=" * 80)
  print("✅ Coleta da amostra finalizada com sucesso!")
  print(f"📁 Base consolidada em: {ARQUIVO_SAIDA}")
  print("=" * 80)


if __name__ == "__main__":
  executar_pipeline()