'''
ETL MUNICIPIOS USANDO ENDPOINT DE ENTES DO SICONFI
DESC: PUXA DADOS COMO CODIGO NO IBGE, NOME, POPULACAO, UF E REGIAO
FONTE: https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes (SICONFI)
'''

import json
import pandas as pd
import requests
from pathlib import Path

DIRETORIO_BASE = Path(__file__).resolve().parent.parent
DIRETORIO_RAW = DIRETORIO_BASE / 'data' / 'raw' / 'entes.json'
DIRETORIO_SILVER = DIRETORIO_BASE / 'data' / 'silver' / 'stg_entes.csv'
ENDPOINT = 'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes'

def extrair_entes():
    try:
        # Puxar dados da API
        resposta = requests.get(ENDPOINT, timeout=60)

        if resposta.status_code == 200:
            arquivo_json = resposta.json()

            # Salvar arquivo no disco preservando formatação e acentuação
            with open(DIRETORIO_RAW, 'w', encoding='utf-8') as arquivo:
                json.dump(arquivo_json, arquivo, ensure_ascii=False, indent=4)

            # Extrai lista de dicionários para criar o .csv
            lista_itens = arquivo_json.get('items', [])

            if not lista_itens:
                print('API respondeu, mas a lista de itens veio vazia.')
                return

            # Converter informações para .csv
            df = pd.DataFrame(lista_itens)

            # Filtra apenas municipios
            df = df[df['esfera'].str.strip().str.upper() == 'M']

            # Renomear coluna de entes para municipio
            renomear_coluna = {'ente': 'municipio'}
            df = df.rename(columns=renomear_coluna)

            # Descartar dados desnecessarios
            colunas_para_remover = ['esfera', 'cnpj', 'capital', 'exercicio']
            df = df.drop(columns=[col for col in colunas_para_remover if col in df.columns])

            # Converte para inteiro sem quebrar caso existam valores em float ou nulos
            df['cod_ibge'] = pd.to_numeric(df['cod_ibge'], errors='coerce').astype('Int64')

            # Salvar CSV tratado na camada Silver
            df.to_csv(DIRETORIO_SILVER, index=False, encoding='utf-8')
            print("Processo concluído com sucesso!")

        else:
            print(f'Erro na resposta da API. Código: {resposta.status_code}')

    except requests.exceptions.RequestException as erro:
        print(f'Erro ao tentar conectar: {erro}')

if __name__ == '__main__':
    extrair_entes()