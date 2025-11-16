import streamlit as st
import pandas as pd
import fetch_prices
import store
import arbitrage
import os

# Configuração da página (deve ser o primeiro comando Streamlit)
st.set_page_config(layout="wide", page_title="Albion Market Analyzer")

st.title("📊 Albion Market Arbitrage Analyzer (MVP)")
st.caption(f"Usando banco de dados local: `{store.DB_FILE}`")

# --- Barra Lateral (Configurações) ---
st.sidebar.title("Configurações")
st.sidebar.info("Ajuste os parâmetros para o cálculo de lucro líquido.")

DEFAULT_FEE_PCT = 4.5
DEFAULT_TRANSPORT_COST = 500

# Parâmetros de cálculo
fee_pct = st.sidebar.number_input(
    "Taxa de Mercado (%)",
    min_value=0.0,
    max_value=20.0,
    value=DEFAULT_FEE_PCT,
    step=0.1,
    help="Taxa percentual cobrada sobre a venda (setup fee + market fee). Default: 4.5%"
)

transport_cost = st.sidebar.number_input(
    "Custo de Transporte (Prata)",
    min_value=0,
    value=DEFAULT_TRANSPORT_COST,
    step=50,
    help="Custo fixo estimado para transportar o item entre cidades."
)

st.sidebar.title("Controles de Dados")

# Botão para carregar dados de sample e atualizar o DB
if st.sidebar.button("Carregar Sample Data e Atualizar DB"):
    try:
        # 1. Carregar dados do arquivo de sample
        st.sidebar.write("Carregando sample_data.json...")
        sample_df = fetch_prices.load_sample_data('sample_data.json')

        # 2. Inicializar o DB (criar tabela se não existir)
        store.init_db()

        # 3. Inserir dados no DB
        count = store.insert_prices(sample_df)
        st.sidebar.success(f"Banco de dados atualizado! {count} novos registros inseridos.")
        st.toast("Banco de dados atualizado com sucesso!", icon="✅")
        # Força o recarregamento dos dados na sessão
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar dados: {e}")

if st.sidebar.button("Limpar Banco de Dados Local"):
    if os.path.exists(store.DB_FILE):
        os.remove(store.DB_FILE)
        st.sidebar.success(f"{store.DB_FILE} limpo.")
        st.toast("Banco de dados limpo.", icon="🗑️")
        st.experimental_rerun()
    else:
        st.sidebar.info("Banco de dados já está limpo.")


# --- Painel Principal ---

# Tenta carregar os dados do DB
try:
    all_prices_df = store.get_prices()
except Exception as e:
    st.error(f"Não foi possível carregar dados do banco de dados `{store.DB_FILE}`. Erro: {e}")
    st.info(f"O arquivo `{store.DB_FILE}` existe? {os.path.exists(store.DB_FILE)}. Clique em 'Carregar Sample Data' na barra lateral.")
    all_prices_df = pd.DataFrame() # Cria um dataframe vazio para evitar que o resto quebre

if all_prices_df.empty:
    st.warning("O banco de dados está vazio. Clique em 'Carregar Sample Data e Atualizar DB' na barra lateral para começar.")
else:
    st.header("Explorador de Preços")

    # --- Filtros ---
    col1, col2 = st.columns(2)
    
    # Filtro de Item
    all_items = sorted(all_prices_df['item_id'].unique())
    selected_items = col1.multiselect(
        "Filtrar por Item ID",
        options=all_items,
        default=all_items[:3] # Default para os 3 primeiros itens
    )

    # Filtro de Tier
    all_tiers = sorted(all_prices_df['tier'].unique())
    selected_tiers = col2.multiselect(
        "Filtrar por Tier",
        options=all_tiers,
        default=all_tiers
    )

    # Aplicar filtros
    if not selected_items:
        filtered_prices_df = all_prices_df[all_prices_df['tier'].isin(selected_tiers)]
    elif not selected_tiers:
        filtered_prices_df = all_prices_df[all_prices_df['item_id'].isin(selected_items)]
    else:
        filtered_prices_df = all_prices_df[
            (all_prices_df['item_id'].isin(selected_items)) &
            (all_prices_df['tier'].isin(selected_tiers))
        ]

    st.dataframe(filtered_prices_df, use_container_width=True)

    # --- Cálculo de Arbitragem ---
    st.header("Top Oportunidades de Arbitragem")
    
    # Calcular oportunidades com base nos dados filtrados
    opportunities_df = arbitrage.find_arbitrage(
        filtered_prices_df,
        fee_pct=fee_pct,
        transport_cost=transport_cost,
        top_n=100
    )

    if opportunities_df.empty:
        st.info("Nenhuma oportunidade de arbitragem encontrada com os filtros e parâmetros atuais.")
    else:
        st.info(f"Encontradas {len(opportunities_df)} oportunidades. Exibindo as melhores:")
        
        # Formatar colunas para melhor visualização
        opportunities_df['net_profit'] = opportunities_df['net_profit'].map('{:,.0f}'.format)
        opportunities_df['buy_price'] = opportunities_df['buy_price'].map('{:,.0f}'.format)
        opportunities_df['sell_price'] = opportunities_df['sell_price'].map('{:,.0f}'.format)
        opportunities_df['confidence_score'] = opportunities_df['confidence_score'].map('{:.2%}'.format)

        st.dataframe(opportunities_df, use_container_width=True)

        # --- Botão de Exportar ---
        csv_data = opportunities_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Exportar Oportunidades (CSV)",
            data=csv_data,
            file_name="albion_arbitrage_opportunities.csv",
            mime="text/csv",
        )