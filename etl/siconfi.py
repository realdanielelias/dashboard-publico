import os
import sys
import requests
import pandas as pd
from supabase import create_client, Client

# configurar .streamlit/secrets.toml. Painel do Supa para gerar credentiais. URL e Anon Key
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st

# conecta no supabase.
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        print(f"Erro ao conectar no Supabase: {e}")
        sys.exit(1)

def extrair_municipios(supabase: Client, municipios: list):
    print("Entes do siconfi...")
    url = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Erro ao acessar endpoint de Entes: {response.status_code}")
        return

    dados_brutos = response.json().get("items", [])
    df = pd.DataFrame(dados_brutos)
    
    # filtra dados de municipios e organiza informacoes
    df = df[df['esfera'] == 'M']
    df = df.rename(columns={
        'cod_ibge': 'id_ibge',
        'ente': 'nome_municipio',
        'uf': 'uf',
        'populacao': 'populacao',
        'cnpj': 'cnpj'
    })
    
    #tratamento para campos nulos
    df['id_ibge'] = pd.to_numeric(df['id_ibge'], errors='coerce')
    df = df.dropna(subset=['id_ibge'])
    df['id_ibge'] = df['id_ibge'].astype(int)
    df = df[df['id_ibge'].isin(municipios)]
    
    #tratamento para converter campo da populacao para numero
    df['populacao'] = pd.to_numeric(df['populacao'], errors='coerce').fillna(0).astype(int)

    #porte definido por populacao fonte: https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/desenvolvimento-urbano-e-metropolitano/politica-nacional-de-desenvolvimento-urbano/tipologias-urbanas
    def definir_porte(pop):
        if pop < 20000: return "Muito Pequeno"
        elif pop < 100000: return "Pequeno"
        elif pop < 750000: return "Médio"
        else: return "Grande"
    
    # definir porte do municipio por extenso
    df['porte_municipio'] = df['populacao'].apply(definir_porte)
    df_final = df[['id_ibge', 'nome_municipio', 'uf', 'populacao', 'porte_municipio', 'cnpj']]
    
    # organizar e subir/att para o supabase
    registros = df_final.to_dict(orient="records")
    if registros:
        try:
            supabase.table("dim_municipio").upsert(registros).execute()
            print("dim_municipio atualizada no Supabase")
        except Exception as e:
            print(f"Erro ao salvar municípios no Supabase: {e}")

def extrair_rreo_educacao(id_ibge: int, ano: int, periodo: int):
    url = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
    
    params = {
        "an_exercicio": ano,
        "nr_periodo": periodo,
        "co_tipo_demonstrativo": "RREO",
        "id_ente": id_ibge,
    }
    
    print(f"RREO-Anexo 08 para Município {id_ibge} (Ano: {ano}, Bimestre: {periodo})")
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        print(f"Erro no RREO para {id_ibge}: Status {response.status_code}")
        return []

def garantir_dim_tempo(supabase: Client, ano: int, periodo: int) -> int:
    id_tempo = int(f"{ano}{periodo:02d}")
    rotulo = "Anual (DCA)" if periodo == 0 else f"{periodo}º Bimestre (RREO)"
    
    registro_tempo = {
        "id_tempo": id_tempo,
        "ano": ano,
        "periodo_cod": periodo,
        "periodo_rotulo": rotulo
    }
    try:
        supabase.table("dim_tempo").upsert(registro_tempo).execute()
        return id_tempo
    except Exception as e:
        print(f"Erro ao garantir dim_tempo ({id_tempo}): {e}")
        return id_tempo

# remove registros duplicados
def garantir_dim_contas(supabase: Client, df_educacao: pd.DataFrame, col_codigo: str):
    contas_unicas = df_educacao[[col_codigo, 'conta']].drop_duplicates(subset=[col_codigo])
    registros_contas = []
    
    for _, linha in contas_unicas.iterrows():
        registros_contas.append({
            "cod_conta": str(linha[col_codigo]),
            "nome_conta": str(linha['conta'])
        })
    if registros_contas:
        try:
            supabase.table("dim_legislacao_contas").upsert(registros_contas, on_conflict="cod_conta").execute()
        except Exception as e:
            print(f"Aviso ao atualizar dim_legislacao_contas: {e}")

def extrair_fiscal(supabase: Client, dados_brutos: list, id_ibge: int, ano: int, periodo: int):
    if not dados_brutos:
        print(f"API do RREO retornou sem dados para municipio {id_ibge} em {ano}.")
        return
        
    df = pd.DataFrame(dados_brutos)
    print(f"Qtd. de linhas recebidas: {len(df)}") 
    
    #forcar string
    df['coluna'] = df['coluna'].astype(str).str.strip()
    df['conta'] = df['conta'].astype(str).str.strip()

    #procurar apenas despesas liquidada
    df_Despesas = df[df['coluna'].str.contains('Despesas Liquidadas', case=False, na=False)]
    print(f"Qtd. linhas de 'Despesas Liquidadas': {len(df_Despesas)}")  
    
    # nome da coluna muda de acordo com o endpoint
    coluna_codigo = 'cod_conta' if 'cod_conta' in df_Despesas.columns else ('co_conta' if 'co_conta' in df_Despesas.columns else None)
    
    if not coluna_codigo:
        print(f"Erro: Coluna de código de conta não localizada para o município {id_ibge}.")
        return

    df_Despesas[coluna_codigo] = df_Despesas[coluna_codigo].astype(str).str.strip()
    
    # buscar gasto total com manutencao
    df_educacao = df_Despesas[df_Despesas['conta'].str.contains('EDUCAÇÃO|ENSINO|INFANTIL|CRECHE|FUNDEB|MDE', case=False, na=False)]
    
    # Cria uma chave única baseada no texto descritivo da conta para evitar o agrupamento genérico do Siconfi
    df_educacao['cod_conta_real'] = df_educacao['conta'].str.lower() \
        .str.replace(r'[^a-z0-9\s]', '', regex=True) \
        .str.replace(r'\s+', '_', regex=True) \
        .str.strip()
    
    # Filtra e remove os totais brutos que geram duplicidade nos somatórios gráficos
    df_detalhado = df_educacao[~df_educacao[coluna_codigo].isin(['RREO2TotalDespesas', 'RREO2TotalDespesasIntra'])]
    
    if df_detalhado.empty:
        df_final_filtro = df_educacao
    else:
        df_final_filtro = df_detalhado
    
    print(f"Linhas de Educação restadas: {len(df_final_filtro)}") 
    
    if df_final_filtro.empty:
        print(f"Nenhuma despesa de educação identificada neste município {id_ibge}.")
        return

    # popula pai antes do filho
    garantir_dim_contas(supabase, df_final_filtro, 'cod_conta_real')
    id_tempo_resolvido = garantir_dim_tempo(supabase, ano, periodo)

    registros_fato = []
    
    for _, linha in df_final_filtro.iterrows():
        valor_limpo = pd.to_numeric(linha['valor'], errors='coerce')
        if pd.isna(valor_limpo) or valor_limpo == 0:
            continue
        
        #valida nome da coluna e codigo final
        codigo_final = str(linha['cod_conta_real']) if pd.notna(linha['cod_conta_real']) else 'NOT_FOUND'
        
        registro = {
            "id_ibge": int(id_ibge),
            "id_tempo": id_tempo_resolvido,
            "cod_conta": codigo_final,
            "anexo_origem": "RREO-Anexo 08",
            "estagio_orcamentario": str(linha['coluna']),
            "valor": float(valor_limpo)
        }
        registros_fato.append(registro)

    if not registros_fato:
        print(f"Nenhum registro válido com valor acima de zero para o município {id_ibge}.")
        return
    
    try:
        supabase.table("fato_siconfi_fiscal").insert(registros_fato).execute()
        print(f"Tabela fiscal salva para município {id_ibge}. Qtd. de registros inseridos: {len(registros_fato)}")
    except Exception as e:
        print(f"Erro ao salvar tabela fiscal do município {id_ibge}: {e}")
        
if __name__ == "__main__":
    # Marília (3529005), Bauru (3506003), Sorocaba (3552205) -- codigos ibge
    CIDADES_ALVO = [3529005, 3506003, 3552205]
    ANO_EXERCICIO = 2023  # ano com dados consolidados
    BIMESTRE_FECHAMENTO = 1 
    
    client_supabase = init_connection()
    
    extrair_municipios(client_supabase, CIDADES_ALVO)
    print("--------------------------------------------------")
    
    for ibge in CIDADES_ALVO:
        dados_api = extrair_rreo_educacao(ibge, ANO_EXERCICIO, BIMESTRE_FECHAMENTO)
        extrair_fiscal(client_supabase, dados_api, ibge, ANO_EXERCICIO, BIMESTRE_FECHAMENTO)
        print("--------------------------------------------------")
        
    print("\nConcluído sucesso!")