import streamlit as st
import pandas as pd
import os
import re

# Módulos internos do projeto
import fetch_prices
import store
import arbitrage
import items_data  # Módulo de categorias

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Albion Market Analyzer")

st.title("📊 Albion Market Analyzer (MVP)")
st.caption(f"Status do Banco de Dados: {'Conectado' if os.path.exists(store.DB_FILE) else 'Não iniciado'} (`{store.DB_FILE}`)")

# --- Constantes Globais ---
CIDADES_REAIS = ["Thetford", "Fort Sterling", "Lymhurst", "Bridgewatch", "Martlock", "Caerleon"]
CIDADES_PORTAIS = ["Merlyn's Rest", "Arthur's Rest", "Morgana's Rest"]

# --- Helpers: Formatação Visual ---
def format_quality_name(q_id):
    try:
        q_id = int(q_id)
    except:
        pass
    mapping = {1: "Normal", 2: "Bom", 3: "Excepcional", 4: "Excelente", 5: "Obra-Prima"}
    return mapping.get(q_id, str(q_id))

def format_item_name_pt(item_id):
    if not isinstance(item_id, str): return str(item_id)
    
    translations = {
        'ORE': 'Minério', 'WOOD': 'Madeira', 'HIDE': 'Pelego', 'FIBER': 'Fibra', 'ROCK': 'Pedra',
        'BAR': 'Barra', 'PLANKS': 'Tábuas', 'LEATHER': 'Couro', 'CLOTH': 'Tecido', 'STONEBLOCK': 'Bloco Pedra',
        'METALBAR': 'Barra Metal', 'BAG': 'Bolsa', 'CAPE': 'Capa', 'MOUNT': 'Montaria', 
        'JOURNAL': 'Diário', 'POTION': 'Poção', 'MEAL': 'Comida'
    }
    
    parts = item_id.split('_')
    tier = ""
    enchant = ""
    name_parts = []

    for part in parts:
        if part.startswith('T') and part[1:].isdigit():
            tier = f"Tier {part[1:]}"
        elif part.startswith('@') and part[1:].isdigit():
            enchant = f".{part[1:]}"
        elif "LEVEL" in part:
            pass 
        elif part in translations:
            name_parts.append(translations[part])
        else:
            name_parts.append(part.title())
            
    base_name = " ".join(name_parts)
    final_name = f"{base_name} {tier}{enchant}".strip()
    return final_name if base_name else item_id


# ==========================================
# BARRA LATERAL (SIDEBAR) - Controles
# ==========================================
st.sidebar.title("⚙️ Parâmetros")

st.sidebar.subheader("Economia")
DEFAULT_FEE_PCT = 4.5
DEFAULT_TRANSPORT_COST = 500

fee_pct = st.sidebar.number_input("Taxa de Mercado (%)", 0.0, 20.0, DEFAULT_FEE_PCT, step=0.5)
transport_cost = st.sidebar.number_input("Custo Transporte (Prata)", 0, value=DEFAULT_TRANSPORT_COST, step=100)

st.sidebar.markdown("---")

st.sidebar.subheader("Estratégia")
min_profit_pct = st.sidebar.slider("Lucro Mínimo (ROI %)", 0, 200, 10)
sort_by = st.sidebar.selectbox("Ordenar Resultados por:", ["Lucro Total (Prata)", "Margem de Lucro (%)"])

st.sidebar.markdown("---")

# 3. Coleta de Dados (API)
st.sidebar.subheader("Atualizar Dados")

with st.sidebar.expander("📡 Buscar na API (Albion Data)", expanded=True):
    
    tab_menu, tab_manual = st.tabs(["📂 Seleção Visual", "📝 Lista Manual"])
    final_items_list = []

    # --- ABA 1: MENU VISUAL ---
    with tab_menu:
        st.info("Gere itens automaticamente selecionando categorias.")
        cat_options = list(items_data.CATEGORIES.keys())
        selected_cat = st.selectbox("Categoria", cat_options)
        sub_options = items_data.CATEGORIES[selected_cat] 
        selected_sub_names = st.multiselect("Itens Específicos", list(sub_options.keys()), default=list(sub_options.keys())[:1])
        
        col_tier, col_ench = st.columns(2)
        selected_tiers = col_tier.multiselect("Tiers", [3, 4, 5, 6, 7, 8], default=[4, 5])
        selected_enchants = col_ench.multiselect("Encantamento", [0, 1, 2, 3, 4], default=[0], format_func=lambda x: "Flat (.0)" if x==0 else f".{x}")
        
        if selected_sub_names and selected_tiers:
            subset_dict = {k: v for k, v in sub_options.items() if k in selected_sub_names}
            generated_ids = items_data.generate_item_list(subset_dict, selected_tiers, selected_enchants)
            st.caption(f"Serão buscados {len(generated_ids)} itens.")
            with st.expander("Ver lista gerada"):
                st.write(generated_ids)
            final_items_list = generated_ids

    # --- ABA 2: MANUAL ---
    with tab_manual:
        st.info("Digite IDs manualmente para itens específicos.")
        manual_input = st.text_area("IDs (ex: T4_BAG, T7_ORE)", "")
        if manual_input:
            final_items_list = [i.strip().upper() for i in re.split(r'[,\s\n]+', manual_input) if i.strip()]

    st.markdown("---")
    city_input = st.multiselect("Cidades", CIDADES_REAIS + CIDADES_PORTAIS, default=CIDADES_REAIS)
    quality_input = st.multiselect("Qualidade Mínima", [1, 2, 3, 4, 5], default=[1])

    if st.button("📥 Baixar Dados e Atualizar DB"):
        if not final_items_list:
            st.sidebar.error("Nenhum item selecionado.")
        elif not city_input:
            st.sidebar.error("Selecione cidades.")
        else:
            with st.spinner(f"Consultando {len(final_items_list)} itens..."):
                api_df = fetch_prices.fetch_prices_real(final_items_list, city_input, quality_input)
                if api_df.empty:
                    st.sidebar.warning("API sem dados.")
                else:
                    store.init_db()
                    count = store.insert_prices(api_df)
                    st.sidebar.success(f"Sucesso! {count} registros atualizados.")
                    st.rerun()

# 4. Administração
with st.sidebar.expander("🛠️ Admin / Debug"):
    if st.button("Carregar Sample Data"):
        try:
            sample_df = fetch_prices.load_sample_data('sample_data.json')
            store.init_db()
            store.insert_prices(sample_df)
            st.sidebar.success("Dados de teste carregados.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))
    
    if st.button("Limpar Banco de Dados"):
        if os.path.exists(store.DB_FILE):
            os.remove(store.DB_FILE)
            st.sidebar.success("DB Limpo.")
            st.rerun()

# ==========================================
# ÁREA PRINCIPAL (MAIN)
# ==========================================

try:
    all_prices_df = store.get_prices()
except Exception as e:
    st.error(f"Erro crítico ao ler banco de dados: {e}")
    all_prices_df = pd.DataFrame()

if all_prices_df.empty:
    st.warning("⚠️ O Banco de Dados está vazio. Utilize o menu lateral para buscar dados na API.")
else:
    st.header("🏆 Oportunidades Identificadas")
    
    opportunities_df = arbitrage.find_arbitrage(
        all_prices_df,
        fee_pct=fee_pct,
        transport_cost=transport_cost,
        top_n=300
    )

    if opportunities_df.empty:
        st.info("Sem oportunidades lucrativas encontradas com os parâmetros atuais.")
    else:
        filtered_opps = opportunities_df[opportunities_df['profit_pct'] >= min_profit_pct].copy()
        
        if sort_by == "Margem de Lucro (%)":
            filtered_opps = filtered_opps.sort_values(by='profit_pct', ascending=False)
        else:
            filtered_opps = filtered_opps.sort_values(by='net_profit', ascending=False)
            
        final_view = filtered_opps.head(50)

        if final_view.empty:
            st.warning(f"Existem oportunidades, mas nenhuma supera {min_profit_pct}% de ROI.")
        else:
            col1, col2, col3 = st.columns(3)
            best_silver = final_view.iloc[0]['net_profit']
            best_pct = final_view.iloc[0]['profit_pct']
            
            col1.metric("Melhor Lucro", f"{best_silver:,.0f}", delta="Prata")
            col2.metric("Melhor ROI", f"{best_pct:.1f}%", delta="%")
            col3.metric("Qtd. Oportunidades", len(final_view))

            display_df = final_view.copy()
            
            # Lógica Visual de Risco/Liquidez
            def get_confidence_icon(score):
                if score > 0.8: return "🟢 Alta (Líquido)"
                if score > 0.5: return "🟡 Média"
                return "🔴 Risco (Travado?)"
            
            display_df['Confiança'] = display_df['confidence_score'].apply(get_confidence_icon)

            # Formatação
            display_df['Lucro Líquido'] = display_df['net_profit'].map('{:,.0f}'.format)
            display_df['ROI (%)'] = display_df['profit_pct'].map('{:.1f}%'.format)
            display_df['Compra'] = display_df['buy_price'].map('{:,.0f}'.format)
            display_df['Venda'] = display_df['sell_price'].map('{:,.0f}'.format)
            
            display_df['Item'] = display_df['item_id_quality'].apply(lambda x: format_item_name_pt(x.split('_Q')[0]))
            
            cols_final = ['Item', 'buy_city', 'sell_city', 'Compra', 'Venda', 'Lucro Líquido', 'ROI (%)', 'Confiança']
            
            st.dataframe(
                display_df[cols_final].rename(columns={'buy_city': 'Origem', 'sell_city': 'Destino'}),
                use_container_width=True,
                hide_index=True
            )

    st.divider()
    
    with st.expander("🔍 Ver Dados Brutos"):
        if not all_prices_df.empty:
            visual_df = all_prices_df.copy()
            visual_df['sell_price_min'] = pd.to_numeric(visual_df['sell_price_min'], errors='coerce').fillna(0)
            visual_df['buy_price_max'] = pd.to_numeric(visual_df['buy_price_max'], errors='coerce').fillna(0)
            
            visual_df['Item'] = visual_df['item_id'].apply(format_item_name_pt)
            visual_df['Qualidade'] = visual_df['quality'].apply(format_quality_name)
            visual_df['Venda'] = visual_df['sell_price_min'].map('{:,.0f}'.format)
            visual_df['Compra'] = visual_df['buy_price_max'].map('{:,.0f}'.format)
            
            for col in ['timestamp_sell_min', 'timestamp_buy_max']:
                visual_df[col] = pd.to_datetime(visual_df[col], errors='coerce')
            
            visual_df['Data Venda'] = visual_df['timestamp_sell_min'].dt.strftime('%d/%m %H:%M')
            visual_df['Data Compra'] = visual_df['timestamp_buy_max'].dt.strftime('%d/%m %H:%M')
            
            cols_show = ['Item', 'city', 'Qualidade', 'tier', 'Venda', 'Data Venda', 'Compra', 'Data Compra']
            st.dataframe(visual_df[cols_show].rename(columns={'city': 'Cidade', 'tier': 'Tier'}), use_container_width=True)