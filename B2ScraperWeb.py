import streamlit as st
import requests
import json
import google.generativeai as genai
import time

# Configuração da página
st.set_page_config(page_title="Dossiê ABM | Raio-X de Empresas", page_icon="🕵️", layout="wide")

# ==========================================
# 🔑 PUXANDO CHAVES COM SEGURANÇA (SECRETS)
# ==========================================
try:
    CHAVE_SERPER_PADRAO = st.secrets["CHAVE_SERPER"]
    CHAVE_GEMINI_PADRAO = st.secrets["CHAVE_GEMINI"]
except Exception:
    CHAVE_SERPER_PADRAO = ""
    CHAVE_GEMINI_PADRAO = ""

# --- Layout do Cabeçalho (O HUB) ---
col_titulo, col_botoes1, col_botoes2 = st.columns([3, 1, 1])
with col_titulo:
    st.title("🕵️ Dossiê ABM (Raio-X)")
    st.markdown("Estudo de conta instantâneo para calls High-Ticket. Digite o nome e o site da empresa, e a IA monta seu roteiro tático.")
with col_botoes1:
    st.write("")
    st.write("")
    st.link_button("💼 B2Scraper LinkedIn", "https://b2scraper.streamlit.app/", use_container_width=True)
with col_botoes2:
    st.write("")
    st.write("")
    st.link_button("📸 Qualificador Insta", "https://b2scraperinsta.streamlit.app/", use_container_width=True)

st.divider()

# --- Configurações na Barra Lateral ---
with st.sidebar:
    st.header("⚙️ Chaves de Acesso")
    
    if "api_key_serper" not in st.session_state:
        st.session_state["api_key_serper"] = CHAVE_SERPER_PADRAO
    if "api_key_gemini" not in st.session_state:
        st.session_state["api_key_gemini"] = CHAVE_GEMINI_PADRAO

    api_key_serper = st.text_input("API Key do Serper:", type="password", value=st.session_state["api_key_serper"])
    api_key_gemini = st.text_input("API Key do Google Gemini:", type="password", value=st.session_state["api_key_gemini"])
    
    st.session_state["api_key_serper"] = api_key_serper
    st.session_state["api_key_gemini"] = api_key_gemini

# --- FUNÇÕES DE BUSCA E IA ---
def buscar_dados_empresa(empresa, site, api_serper):
    # 1. Busca Orgânica (Para entender o que a empresa faz)
    url_search = "https://google.serper.dev/search"
    query_search = f'"{empresa}" OR site:{site} sobre nós OR about us'
    payload_search = json.dumps({"q": query_search, "num": 4, "gl": "br", "hl": "pt-br"})
    
    # 2. Busca de Notícias (Para pegar o "momento" da empresa)
    url_news = "https://google.serper.dev/news"
    payload_news = json.dumps({"q": empresa, "num": 3, "gl": "br", "hl": "pt-br"})
    
    headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
    
    dados_compilados = f"DADOS COLETADOS SOBRE A EMPRESA: {empresa} ({site})\n\n"
    
    try:
        # Fazendo a busca orgânica
        res_search = requests.post(url_search, headers=headers, data=payload_search)
        if res_search.ok:
            organic = res_search.json().get("organic", [])
            dados_compilados += "--- INFORMAÇÕES GERAIS ---\n"
            for item in organic:
                dados_compilados += f"- {item.get('snippet', '')}\n"
        
        # Fazendo a busca de notícias
        res_news = requests.post(url_news, headers=headers, data=payload_news)
        if res_news.ok:
            news = res_news.json().get("news", [])
            dados_compilados += "\n--- NOTÍCIAS RECENTES ---\n"
            if not news:
                dados_compilados += "Nenhuma notícia recente encontrada.\n"
            else:
                for item in news:
                    dados_compilados += f"- {item.get('title', '')}: {item.get('snippet', '')}\n"
                    
        return dados_compilados
    except Exception as e:
        return f"Erro ao buscar no Google: {e}"

def gerar_dossie_abm(dados_coletados, api_gemini):
    try:
        genai.configure(api_key=api_gemini)
        
        # Seleciona o melhor modelo disponível
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not modelos:
            return "Erro: Chave do Gemini sem acesso a modelos de texto."
            
        modelo_escolhido = modelos[0]
        for nome in modelos:
            if 'flash' in nome or 'pro' in nome:
                modelo_escolhido = nome
                break
                
        nome_limpo = modelo_escolhido.replace("models/", "")
        modelo = genai.GenerativeModel(nome_limpo)
        
        prompt = f"""
        Você é um estrategista de Account-Based Marketing (ABM) e especialista em vendas B2B High-Ticket.
        Sua missão é municiar um BDR (Business Development Representative) com informações cirúrgicas antes dele entrar em uma call de R$ 40.000,00 com o dono/diretor da empresa alvo.

        Aqui estão os dados brutos extraídos do Google (Busca orgânica e Notícias recentes):
        {dados_coletados}

        Baseado exclusivamente nesses dados e na sua inteligência de mercado sobre o nicho em que essa empresa atua, crie um "Dossiê Tático" estruturado EXATAMENTE com os 4 tópicos abaixo. 
        Use formatação em Markdown para deixar bonito e legível.

        1. 🎯 **O que a empresa faz**: Resuma de forma direta e comercial em 1 ou 2 linhas no máximo. Sem jargões corporativos vazios.
        2. ⚠️ **Prováveis dores e gargalos atuais**: Baseado no nicho da empresa e nas notícias (se houver), liste 3 problemas comuns que esse tipo de negócio enfrenta para escalar, faturar mais ou ter mais lucro.
        3. 💡 **3 Ângulos de abordagem para a Call**: Escreva 3 ideias práticas de como o BDR pode iniciar a conversa ou puxar assunto na reunião, gerando valor imediato. Ex: "Citar a notícia X e perguntar como isso afetou o setor Y".
        4. ⚔️ **Principais concorrentes (Radar de Mercado)**: Cite 3 concorrentes lógicos (reais do mercado ou perfis de empresas idênticas) para o BDR citar e gerar autoridade ("Fulano, imagino que vocês disputem mercado muito forte com a Empresa X e Y...").

        Seja direto, persuasivo e tático. Não invente notícias que não estão nos dados, mas use seu conhecimento de mundo para deduzir concorrentes e gargalos do nicho.
        """
        
        resposta = modelo.generate_content(prompt)
        return resposta.text
        
    except Exception as e:
        return f"Erro na IA ao gerar dossiê: {e}"

# --- INTERFACE DE AÇÃO ---
with st.form("form_abm"):
    col1, col2 = st.columns(2)
    with col1:
        empresa_alvo = st.text_input("🏢 Nome da Empresa:", placeholder="Ex: Resultados Digitais, ContaAzul...")
    with col2:
        site_alvo = st.text_input("🌐 Site da Empresa (Opcional, mas recomendado):", placeholder="Ex: rdstation.com")
        
    btn_pesquisar = st.form_submit_button("Gerar Dossiê Tático ⚡", type="primary", use_container_width=True)

if btn_pesquisar:
    if not st.session_state["api_key_serper"] or not st.session_state["api_key_gemini"]:
        st.error("⚠️ Preencha suas chaves API na barra lateral antes de começar!")
    elif not empresa_alvo:
        st.warning("⚠️ Digite pelo menos o nome da empresa.")
    else:
        site_limpo = site_alvo.replace("https://", "").replace("http://", "").replace("www.", "").strip()
        
        with st.status("🕵️ Investigando a conta...", expanded=True) as status:
            st.write("🔎 Varrendo o Google atrás de dados institucionais e notícias...")
            dados_brutos = buscar_dados_empresa(empresa_alvo, site_limpo, st.session_state["api_key_serper"])
            
            st.write("🧠 Enviando dados para o Estrategista de IA (Gemini)...")
            dossie = gerar_dossie_abm(dados_brutos, st.session_state["api_key_gemini"])
            
            status.update(label="✅ Dossiê concluído!", state="complete", expanded=False)
            
        st.success(f"Dossiê Tático gerado para: **{empresa_alvo}**")
        
        with st.container(border=True):
            st.markdown(dossie)