import streamlit as st
from supabase import create_client, Client

st.title("Dashboard")

# conecta no supabase. precisa de .streamlit/secrets.toml 
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
    st.success("OK")
    
    response = supabase.table("dim_municipio").select("*").execute()
    st.write("Teste:", response.data)
except Exception as e:
    st.error(f"Erro: {e}")