'''
CARGA DA CAMADA GOLD PARA O SUPABASE (POSTGRESQL)
DESC: CARREGA OS ARQUIVOS CSV DA PASTA DATA/GOLD NAS TABELAS DIMENSAO E FATO DO BANCO
FONTE: ARQUIVOS CONSOLIDADOS EM DATA/GOLD/
'''

from pathlib import Path
import tomllib
import numpy as np
import pandas as pd
from supabase import create_client

# Definir diretorios de trabalho
BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"
DIR_GOLD = BASE_DIR / "data" / "gold"

if not SECRETS_PATH.exists():
  print(f"Arquivo de credenciais não encontrado em: {SECRETS_PATH}")
  exit(1)

with open(SECRETS_PATH, "rb") as f:
  secrets = tomllib.load(f)

supabase = create_client(secrets["supabase"]["url"], secrets["supabase"]["key"])

# Lista exata de todas as colunas INT na fato_execucao_educacional
COLUNAS_INTEIRAS = {
    "sk_municipio",
    "sk_tempo",
    "sk_rede",
    "mat_creche",
    "mat_pre_escola",
    "mat_anos_iniciais",
    "mat_anos_finais",
    "mat_especial_classes_comuns",
    "docentes_iniciais",
    "docentes_finais",
    "turmas_iniciais",
    "turmas_finais",
    "escolas_creche",
    "escolas_pre_escola",
    "escolas_iniciais",
    "escolas_finais",
    "qtd_alunos_inse",
}


def tratar_valor(coluna: str, valor):
  # Tratar nulos do pandas/numpy
  if pd.isna(valor) or valor is None:
    return None

  # Forçar conversão estrita para INT nativo
  if coluna in COLUNAS_INTEIRAS:
    try:
      return int(float(valor))
    except (ValueError, TypeError):
      return None

  # Tratar floats decimais normais (despesas, notas do IDEB, etc)
  if isinstance(valor, (float, np.floating)):
    return float(valor)

  return valor


def carregar_tabela(nome_tabela: str, nome_csv: str, batch_size: int = 200):
  caminho = DIR_GOLD / nome_csv
  if not caminho.exists():
    print(f"Arquivo {nome_csv} não encontrado em {DIR_GOLD}. Pulei.")
    return

  df = pd.read_csv(caminho)

  # Sanitizar dicionario linha por linha
  registros_brutos = df.to_dict(orient="records")
  registros = []
  for linha in registros_brutos:
    # str(k) resolve o conflito de tipo Hashable -> str e garante chaves validas para JSON
    linha_limpa = {str(k): tratar_valor(str(k), v) for k, v in linha.items()}
    registros.append(linha_limpa)

  total = len(registros)
  print(f"\n-> Inserindo {total} registros na tabela '{nome_tabela}'...")

  # Enviar em lotes de 200 para evitar timeout e validar cada bloco
  sucessos = 0
  for i in range(0, total, batch_size):
    lote = registros[i : i + batch_size]
    try:
      supabase.table(nome_tabela).upsert(lote).execute()
      sucessos += len(lote)
      print(
          f"   ✓ Lote {i // batch_size + 1} enviado ({len(lote)} registros -"
          f" Total: {sucessos}/{total})"
      )
    except Exception as e:
      print(f" Erro ao enviar lote {i // batch_size + 1}: {e}")


def executar_carga():
  # As dimensoes ja foram carregadas, mas o upsert garante idempotencia
  carregar_tabela("dim_tempo", "dim_tempo.csv", batch_size=50)
  carregar_tabela("dim_municipio", "dim_municipio.csv", batch_size=50)
  carregar_tabela("dim_rede", "dim_rede.csv", batch_size=50)

  # Carregar a tabela fato completa
  carregar_tabela(
      "fato_execucao_educacional",
      "fato_execucao_educacional.csv",
      batch_size=200,
  )
  print("\n Processo de carga finalizado!")


if __name__ == "__main__":
  executar_carga()