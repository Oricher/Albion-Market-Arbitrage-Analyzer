import pandas as pd
from datetime import datetime, timezone

def find_arbitrage(df_prices, fee_pct, transport_cost=0, top_n=50):
    """
    Encontra oportunidades de arbitragem.
    Atualizado para calcular % de Lucro (ROI).
    """
    if df_prices.empty:
        return pd.DataFrame()

    # Garantir tipos e cópia segura
    df = df_prices.copy()
    df['sell_price_min'] = pd.to_numeric(df['sell_price_min'], errors='coerce')
    df['buy_price_max'] = pd.to_numeric(df['buy_price_max'], errors='coerce')
    
    # Timestamps
    df['timestamp_sell_min'] = pd.to_datetime(df['timestamp_sell_min'], utc=True, errors='coerce')
    df['timestamp_buy_max'] = pd.to_datetime(df['timestamp_buy_max'], utc=True, errors='coerce')

    # Remover dados inválidos
    df = df.dropna(subset=['timestamp_sell_min', 'timestamp_buy_max'])
    df = df[(df['sell_price_min'] > 0) & (df['buy_price_max'] > 0)]

    if df.empty:
        return pd.DataFrame()

    # --- Confiança (Recência) ---
    now_utc = datetime.now(timezone.utc)
    max_age_hours = 72.0 # 3 dias

    df['age_hours_buy'] = (now_utc - df['timestamp_sell_min']).dt.total_seconds() / 3600
    df['confidence_buy'] = (1.0 - (df['age_hours_buy'] / max_age_hours)).clip(0, 1)

    df['age_hours_sell'] = (now_utc - df['timestamp_buy_max']).dt.total_seconds() / 3600
    df['confidence_sell'] = (1.0 - (df['age_hours_sell'] / max_age_hours)).clip(0, 1)

    df['item_key'] = df['item_id'] + '_Q' + df['quality'].astype(str)

    # --- Cross Join (Compra vs Venda) ---
    
    # 1. Onde comprar (sell_price_min)
    df_buy = df.rename(columns={
        'city': 'buy_city',
        'sell_price_min': 'buy_price',
        'timestamp_sell_min': 'timestamp_buy',
        'confidence_buy': 'confidence_buy'
    })[['item_key', 'buy_city', 'buy_price', 'timestamp_buy', 'confidence_buy']]

    # 2. Onde vender (buy_price_max)
    df_sell = df.rename(columns={
        'city': 'sell_city',
        'buy_price_max': 'sell_price',
        'timestamp_buy_max': 'timestamp_sell',
        'confidence_sell': 'confidence_sell'
    })[['item_key', 'sell_city', 'sell_price', 'timestamp_sell', 'confidence_sell']]

    # Merge
    df_arb = pd.merge(df_buy, df_sell, on='item_key')

    # --- Filtros e Cálculos ---
    
    # Remover mesma cidade
    df_arb = df_arb[df_arb['buy_city'] != df_arb['sell_city']]

    # Lucro Bruto e Líquido
    df_arb['gross_profit'] = df_arb['sell_price'] - df_arb['buy_price']
    
    fee_multiplier = 1.0 - (fee_pct / 100.0)
    df_arb['net_profit'] = (df_arb['sell_price'] * fee_multiplier) - df_arb['buy_price'] - transport_cost

    # Filtrar apenas lucrativos (lucro líquido > 0)
    df_arb = df_arb[df_arb['net_profit'] > 0]

    if df_arb.empty:
        return pd.DataFrame()

    # NOVO: Calcular Porcentagem de Lucro (ROI)
    # Evitar divisão por zero
    df_arb['profit_pct'] = (df_arb['net_profit'] / df_arb['buy_price']) * 100.0

    # Score de Confiança Médio
    df_arb['confidence_score'] = (df_arb['confidence_buy'] + df_arb['confidence_sell']) / 2.0
    
    # Limpeza final
    df_final = df_arb[[
        'item_key', 'buy_city', 'sell_city', 'buy_price', 'sell_price',
        'gross_profit', 'net_profit', 'profit_pct', 'confidence_score',
        'timestamp_buy', 'timestamp_sell'
    ]]
    
    df_final = df_final.rename(columns={'item_key': 'item_id_quality'})

    # A ordenação final é feita no app.py agora, ou retornamos por net_profit padrão
    return df_final.sort_values(by='net_profit', ascending=False).head(top_n).reset_index(drop=True)