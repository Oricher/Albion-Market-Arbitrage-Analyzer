import pandas as pd
from datetime import datetime, timezone

def find_arbitrage(df_prices: pd.DataFrame, fee_pct: float, transport_cost: int = 0, top_n: int = 50) -> pd.DataFrame:
    """
    Motor de cálculo de arbitragem. Cruza dados de compra e venda para achar lucro.

    Args:
        df_prices: DataFrame com dados brutos do DB.
        fee_pct: Taxa do mercado (ex: 4.5%). Subtraída do valor de VENDA.
        transport_cost: Custo fixo em prata subtraído do lucro final.
        top_n: Limite de linhas retornadas.

    Returns:
        DataFrame com as colunas de lucro calculado e indicadores de confiança.
    """
    if df_prices.empty:
        return pd.DataFrame()

    # 1. Preparação e Tipagem
    df = df_prices.copy()
    cols_num = ['sell_price_min', 'buy_price_max']
    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Garante datas em UTC
    cols_time = ['timestamp_sell_min', 'timestamp_buy_max']
    for col in cols_time:
        df[col] = pd.to_datetime(df[col], utc=True, errors='coerce')

    # Filtra registros inválidos (sem data ou preço zerado)
    df = df.dropna(subset=cols_time)
    df = df[(df['sell_price_min'] > 0) & (df['buy_price_max'] > 0)]

    if df.empty:
        return pd.DataFrame()

    # 2. Cálculo de Score de Confiança (Baseado em Recência)
    # Lógica: Quanto mais antigo o dado, menor a chance do preço ser real.
    # Dados com mais de 72h (3 dias) tem confiança zero.
    now_utc = datetime.now(timezone.utc)
    MAX_AGE_HOURS = 72.0 

    df['age_hours_buy'] = (now_utc - df['timestamp_sell_min']).dt.total_seconds() / 3600
    df['confidence_buy'] = (1.0 - (df['age_hours_buy'] / MAX_AGE_HOURS)).clip(0, 1)

    df['age_hours_sell'] = (now_utc - df['timestamp_buy_max']).dt.total_seconds() / 3600
    df['confidence_sell'] = (1.0 - (df['age_hours_sell'] / MAX_AGE_HOURS)).clip(0, 1)

    # Chave única para o Join (Item + Qualidade)
    df['item_key'] = df['item_id'] + '_Q' + df['quality'].astype(str)

    # 3. Separação dos DataFrames (Self-Join Logic)
    
    # Cenário A: Onde comprar? (Procuramos o menor sell_price_min dos vendedores)
    df_buy = df.rename(columns={
        'city': 'buy_city',
        'sell_price_min': 'buy_price',
        'timestamp_sell_min': 'timestamp_buy',
        'confidence_buy': 'confidence_buy'
    })[['item_key', 'buy_city', 'buy_price', 'timestamp_buy', 'confidence_buy']]

    # Cenário B: Onde vender? (Procuramos o maior buy_price_max dos compradores)
    df_sell = df.rename(columns={
        'city': 'sell_city',
        'buy_price_max': 'sell_price',
        'timestamp_buy_max': 'timestamp_sell',
        'confidence_sell': 'confidence_sell'
    })[['item_key', 'sell_city', 'sell_price', 'timestamp_sell', 'confidence_sell']]

    # 4. Cruzamento (Todas as cidades contra todas as cidades)
    df_arb = pd.merge(df_buy, df_sell, on='item_key')

    # 5. Filtros de Negócio
    # Remover compra e venda na mesma cidade
    df_arb = df_arb[df_arb['buy_city'] != df_arb['sell_city']]

    # 6. Cálculos Financeiros
    df_arb['gross_profit'] = df_arb['sell_price'] - df_arb['buy_price']
    
    # Lucro Líquido = (Preço Venda * (1 - Taxa)) - Preço Compra - Custo Transporte
    fee_multiplier = 1.0 - (fee_pct / 100.0)
    df_arb['net_profit'] = (df_arb['sell_price'] * fee_multiplier) - df_arb['buy_price'] - transport_cost

    # Filtrar prejuízos
    df_arb = df_arb[df_arb['net_profit'] > 0]

    if df_arb.empty:
        return pd.DataFrame()

    # ROI (Retorno sobre Investimento) em %
    # Fórmula: (Lucro Líquido / Custo Inicial) * 100
    df_arb['profit_pct'] = (df_arb['net_profit'] / df_arb['buy_price']) * 100.0

    # Confiança Média da Transação
    df_arb['confidence_score'] = (df_arb['confidence_buy'] + df_arb['confidence_sell']) / 2.0
    
    # 7. Formatação Final
    df_final = df_arb[[
        'item_key', 'buy_city', 'sell_city', 'buy_price', 'sell_price',
        'gross_profit', 'net_profit', 'profit_pct', 'confidence_score',
        'timestamp_buy', 'timestamp_sell'
    ]]
    
    df_final = df_final.rename(columns={'item_key': 'item_id_quality'})

    # Retorna as Top N (ordenação será feita no front-end se necessário)
    return df_final.sort_values(by='net_profit', ascending=False).head(top_n).reset_index(drop=True)