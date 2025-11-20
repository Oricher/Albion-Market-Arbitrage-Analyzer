import streamlit as st
import pandas as pd
import fetch_prices
import store
import arbitrage
import os
import re

st.set_page_config(layout="wide", page_title="Albion Market Analyzer")

st.title("📊 Albion Market Analyzer (MVP)")
st.caption(f"Usando banco de dados local: `{store.DB_FILE}`")

# --- Constantes ---
CIDADES_REAIS = ["Thetford", "Fort Sterling", "Lymhurst", "Bridgewatch", "Martlock", "Caerleon"]
CIDADES_PORTAIS = ["Merlyn's Rest", "Arthur's Rest", "Morgana's Rest"]

# --- Barra Lateral ---
st.sidebar.title("Filtros de Lucratividade")

DEFAULT_FEE_PCT = 4.5
DEFAULT_TRANSPORT_COST = 500

# Inputs Econômicos
fee_pct = st.sidebar.number_input("Taxa de Mercado (%)", 0.0, 20.0, DEFAULT_FEE_PCT, step=0.5)
transport_cost = st.sidebar.number_input("Custo Transporte (Prata)", 0, value=DEFAULT_TRANSPORT_COST, step=100)

st.sidebar.markdown("---")

# NOVO: Filtros de Estratégia
min_profit_pct = st.sidebar.slider("Mínimo de Lucro (%)", 0, 200, 10, help="Filtra oportunidades com ROI baixo.")
sort_by = st.sidebar.selectbox("Ordenar Oportunidades por:", ["Lucro Total (Prata)", "Margem de Lucro (%)"])

st.sidebar.title("Dados (API/DB)")

# --- API Real ---
with st.sidebar.expander("Buscar Dados da API", expanded=True):
    st.info("Busque dados da API pública.")
    item_input = st.text_area("Itens (Ex: T4_ORE, T7_BAG)", "T4_ORE,T5_WOOD,T6_HIDE,T4_FIBER,T8_BAG")
    city_input = st.multiselect("Cidades", CIDADES_REAIS + CIDADES_PORTAIS, default=CIDADES_REAIS)
    quality_input = st.multiselect("Qualidades", [1, 2, 3, 4, 5], default=[1])
    
    if st.button("Buscar na API e Atualizar"):
        if not item_input or not city_input:
            st.sidebar.error("Preencha itens e cidades.")
        else:
            items_clean = [i.strip().upper() for i in re.split(r'[,\s\n]+', item_input) if i.strip()]
            if not items_clean:
                 st.sidebar.error("Itens inválidos.")
            else:
                with st.spinner("Consultando Albion Data Project..."):
                    api_df = fetch_prices.fetch_prices_real(items_clean, city_input, quality_input)
                    if api_df.empty:
                        st.sidebar.warning("Sem dados encontrados na API.")
                    else:
                        store.init_db()
                        count = store.insert_prices(api_df)
                        st.sidebar.success(f"Sucesso! {count} registros atualizados.")
                        st.rerun()

# --- Controles Admin ---
with st.sidebar.expander("Opções Avançadas"):
    if st.button("Carregar Sample Data"):
        try:
            sample_df = fetch_prices.load_sample_data('sample_data.json')
            store.init_db()
            store.insert_prices(sample_df)
            st.sidebar.success("Sample data carregado!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))

    if st.button("Limpar DB"):
        if os.path.exists(store.DB_FILE):
            os.remove(store.DB_FILE)
            st.sidebar.success("DB Limpo.")
            st.rerun()

# --- Main Area ---

try:
    all_prices_df = store.get_prices()
except Exception as e:
    st.error(f"Erro no DB: {e}")
    all_prices_df = pd.DataFrame()

if all_prices_df.empty:
    st.warning("DB Vazio. Busque dados na barra lateral.")
else:
    # --- Cálculo de Oportunidades ---
    st.header("🏆 Top Oportunidades")
    
    opportunities_df = arbitrage.find_arbitrage(
        all_prices_df,
        fee_pct=fee_pct,
        transport_cost=transport_cost,
        top_n=200 # Busca mais para filtrar depois
    )

    if opportunities_df.empty:
        st.info("Sem oportunidades de arbitragem lucrativas.")
    else:
        # Aplicar Filtro de Porcentagem
        filtered_opps = opportunities_df[opportunities_df['profit_pct'] >= min_profit_pct].copy()
        
        # Aplicar Ordenação
        if sort_by == "Margem de Lucro (%)":
            filtered_opps = filtered_opps.sort_values(by='profit_pct', ascending=False)
        else:
            filtered_opps = filtered_opps.sort_values(by='net_profit', ascending=False)
            
        # Mostrar Top 50 após filtros
        final_view = filtered_opps.head(50)

        if final_view.empty:
            st.warning(f"Existem oportunidades, mas nenhuma com lucro acima de {min_profit_pct}%. Tente baixar o filtro.")
        else:
            # Métricas de Resumo
            best_silver = final_view.iloc[0]['net_profit']
            best_pct = final_view.iloc[0]['profit_pct']
            st.metric("Melhor Lucro (Prata)", f"{best_silver:,.0f}", delta="Líquido")
            st.metric("Melhor Margem (%)", f"{best_pct:.1f}%", delta="ROI")

            # Formatação Visual
            display_df = final_view.copy()
            
            # Adicionar ícone de alerta se a confiança for baixa (Volume baixo/Dado velho)
            def get_confidence_icon(score):
                if score > 0.8: return "🟢 Alta"
                if score > 0.5: return "🟡 Média"
                return "🔴 Baixa (Risco)"
            
            display_df['Confiança (Recência)'] = display_df['confidence_score'].apply(get_confidence_icon)

            display_df['Lucro Líquido'] = display_df['net_profit'].map('{:,.0f}'.format)
            display_df['% Lucro'] = display_df['profit_pct'].map('{:.1f}%'.format)
            display_df['Investimento (Compra)'] = display_df['buy_price'].map('{:,.0f}'.format)
            display_df['Venda Estimada'] = display_df['sell_price'].map('{:,.0f}'.format)
            
            # Seleção de colunas finais
            cols = [
                'item_id_quality', 'buy_city', 'sell_city', 
                'Investimento (Compra)', 'Venda Estimada', 
                'Lucro Líquido', '% Lucro', 'Confiança (Recência)'
            ]
            
            st.dataframe(
                display_df[cols],
                use_container_width=True,
                hide_index=True
            )
            
            st.caption("Nota sobre Volume: A API de preços rápidos não informa a quantidade de itens vendidos. Use a coluna 'Confiança' como indicador: se for '🟢 Alta', o item foi negociado recentemente, indicando maior liquidez.")

    st.divider()
    
    with st.expander("Ver Tabela Bruta de Preços"):
        st.dataframe(all_prices_df)