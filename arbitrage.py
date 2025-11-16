import pandas as pd
from datetime import datetime, timezone

def find_arbitrage(df_prices, fee_pct, transport_cost=0, top_n=50):
    """
    Encontra oportunidades de arbitragem (comprar na cidade A, vender na cidade B)
    a partir de um DataFrame de preços de mercado.

    Args:
        df_prices (pd.DataFrame): DataFrame contendo os dados de mercado.
        fee_pct (float): Taxa de mercado em porcentagem (ex: 4.5 para 4.5%).
        transport_cost (int): Custo fixo de transporte.
        top_n (int): Número de
    """
    if df_prices.empty:
        return pd.DataFrame()

    # Garantir que os tipos de dados estão corretos
    df = df_prices.copy()
    df['sell_price_min'] = pd.to_numeric(df['sell_price_min'], errors='coerce')
    df['buy_price_max'] = pd.to_numeric(df['buy_price_max'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')

    # Remover linhas onde não temos preços de compra ou venda, ou timestamp
    df = df.dropna(subset=['sell_price_min', 'buy_price_max', 'timestamp'])
    
    # Manter apenas registros com preços válidos (maiores que 0)
    df = df[(df['sell_price_min'] > 0) & (df['buy_price_max'] > 0)]

    if df.empty:
        return pd.DataFrame()

    # --- Cálculo de Confiança (Recência) ---
    # Calcula a idade do registro em horas
    now_utc = datetime.now(timezone.utc)
    df['age_hours'] = (now_utc - df['timestamp']).dt.total_seconds() / 3600
    
    # Score de confiança simples: 100% se for recente, decaindo linearmente
    # até 0% após 72 horas (3 dias).
    max_age_hours = 72.0
    df['confidence'] = (1.0 - (df['age_hours'] / max_age_hours)).clip(0, 1)

    # Identificador único para cada item (id + qualidade)
    # Tier já está incluído no item_id (ex: T4_ORE)
    df['item_key'] = df['item_id'] + '_Q' + df['quality'].astype(str)

    # --- Preparação para o "Cross Join" ---
    
    # 1. Dados de Compra: Onde podemos COMPRAR (preço mais baixo)
    # Nós compramos pelo 'sell_price_min' de alguém
    df_buy = df.rename(columns={
        'city': 'buy_city',
        'sell_price_min': 'buy_price',
        'timestamp': 'timestamp_buy',
        'confidence': 'confidence_buy'
    })
    # Selecionamos apenas as colunas que precisamos
    df_buy = df_buy[['item_key', 'buy_city', 'buy_price', 'timestamp_buy', 'confidence_buy']]

    # 2. Dados de Venda: Onde podemos VENDER (preço mais alto)
    # Nós vendemos pelo 'buy_price_max' (ordem de compra) de alguém
    df_sell = df.rename(columns={
        'city': 'sell_city',
        'buy_price_max': 'sell_price',
        'timestamp': 'timestamp_sell',
        'confidence': 'confidence_sell'
    })
    df_sell = df_sell[['item_key', 'sell_city', 'sell_price', 'timestamp_sell', 'confidence_sell']]

    # --- Cruzamento de Dados ---
    # Compara cada cidade de compra com cada cidade de venda para o mesmo item
    df_arb = pd.merge(df_buy, df_sell, on='item_key')

    # --- Filtragem ---
    
    # 1. Remover transações na mesma cidade
    df_arb = df_arb[df_arb['buy_city'] != df_arb['sell_city']]

    # 2. Calcular Lucro Bruto
    df_arb['gross_profit'] = df_arb['sell_price'] - df_arb['buy_price']

    # 3. Calcular Lucro Líquido
    # Lucro = (Receita da Venda) - (Custo de Compra) - (Custos Extras)
    # Receita da Venda = sell_price * (1 - (fee_pct / 100))
    # Custo de Compra = buy_price
    # Custos Extras = transport_cost
    fee_multiplier = 1.0 - (fee_pct / 100.0)
    df_arb['net_profit'] = (df_arb['sell_price'] * fee_multiplier) - df_arb['buy_price'] - transport_cost

    # 4. Filtrar apenas lucrativos
    df_arb = df_arb[df_arb['net_profit'] > 0]

    if df_arb.empty:
        return pd.DataFrame()

    # --- Finalização ---

    # Calcular score de confiança combinado (média)
    df_arb['confidence_score'] = (df_arb['confidence_buy'] + df_arb['confidence_sell']) / 2.0

    # Ordenar pelo maior lucro líquido
    df_arb = df_arb.sort_values(by='net_profit', ascending=False)

    # Limpar e reordenar colunas
    df_final = df_arb[[
        'item_key', 'buy_city', 'sell_city', 'buy_price', 'sell_price',
        'gross_profit', 'net_profit', 'confidence_score',
        'timestamp_buy', 'timestamp_sell'
    ]]
    
    # Renomear 'item_key' de volta para 'item_id' (simplificado)
    df_final = df_final.rename(columns={'item_key': 'item_id_quality'})

    return df_final.head(top_n).reset_index(drop=True)