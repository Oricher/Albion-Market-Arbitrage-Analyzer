import sqlite3
import pandas as pd
import os

DB_FILE = "albion_market.db"
TABLE_NAME = "market_prices"

def init_db(db_file=DB_FILE):
    """
    Cria a tabela de preços de mercado se ela não existir.
    
    A PRIMARY KEY (item_id, city, quality) garante que temos apenas
    um registro por item/cidade/qualidade.
    
    Usamos 'ON CONFLICT REPLACE' para que novos dados sempre
    substituam os antigos.
    """
    # Garantir que o diretório exista (se o DB_FILE for um caminho)
    os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)
    
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        item_id TEXT NOT NULL,
        city TEXT NOT NULL,
        quality INTEGER NOT NULL,
        sell_price_min INTEGER,
        timestamp_sell_min TEXT,
        buy_price_max INTEGER,
        timestamp_buy_max TEXT,
        tier INTEGER,
        PRIMARY KEY (item_id, city, quality)
    ) WITHOUT ROWID;
    """
    # Criar um índice para consultas rápidas por item
    create_index_query = f"""
    CREATE INDEX IF NOT EXISTS idx_item_id
    ON {TABLE_NAME} (item_id);
    """
    
    try:
        with sqlite3.connect(db_file) as con:
            con.execute(create_table_query)
            con.execute(create_index_query)
        print(f"Banco de dados '{db_file}' e tabela '{TABLE_NAME}' inicializados.")
    except sqlite3.Error as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

def insert_prices(df, db_file=DB_FILE):
    """
    Insere um DataFrame de preços no banco de dados SQLite.
    Usa 'ON CONFLICT REPLACE' para atualizar registros existentes.
    """
    if df.empty:
        print("DataFrame vazio, nada para inserir.")
        return 0

    # Colunas esperadas pelo novo schema do DB
    expected_cols = [
        'item_id', 'city', 'quality', 
        'sell_price_min', 'timestamp_sell_min',
        'buy_price_max', 'timestamp_buy_max',
        'tier'
    ]
    
    # Adiciona colunas faltantes com None (ex: se o sample_data for usado)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
            
    # Filtra apenas para as colunas esperadas
    df_to_insert = df[expected_cols].copy()

    # --- Limpeza de Dados ---
    # Garantir que a chave primária não seja nula
    df_to_insert = df_to_insert.dropna(subset=['item_id', 'city', 'quality'])
    # Remover itens sem ID (comuns em dados de API)
    df_to_insert = df_to_insert[df_to_insert['item_id'] != ""]

    # Converter tipos
    df_to_insert['quality'] = pd.to_numeric(df_to_insert['quality'], errors='coerce').fillna(0).astype(int)
    df_to_insert['tier'] = pd.to_numeric(df_to_insert['tier'], errors='coerce').fillna(0).astype(int)
    df_to_insert['sell_price_min'] = pd.to_numeric(df_to_insert['sell_price_min'], errors='coerce').fillna(0).astype(int)
    df_to_insert['buy_price_max'] = pd.to_numeric(df_to_insert['buy_price_max'], errors='coerce').fillna(0).astype(int)
    
    # Preencher timestamps nulos com string vazia
    df_to_insert['timestamp_sell_min'] = df_to_insert['timestamp_sell_min'].fillna("")
    df_to_insert['timestamp_buy_max'] = df_to_insert['timestamp_buy_max'].fillna("")


    if df_to_insert.empty:
        print("Nenhum dado válido para inserir após a limpeza.")
        return 0

    try:
        with sqlite3.connect(db_file) as con:
            # Usar 'replace' ativa o 'ON CONFLICT REPLACE' definido na PRIMARY KEY
            data_tuples = [tuple(x) for x in df_to_insert.to_records(index=False)]
            
            insert_query = f"""
            INSERT OR REPLACE INTO {TABLE_NAME} (
                item_id, city, quality, 
                sell_price_min, timestamp_sell_min,
                buy_price_max, timestamp_buy_max,
                tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """
            
            cursor = con.cursor()
            cursor.executemany(insert_query, data_tuples)
            con.commit()
            
            print(f"Inseridos/Atualizados {cursor.rowcount} registros no DB.")
            return cursor.rowcount

    except sqlite3.Error as e:
        print(f"Erro ao inserir dados no banco de dados: {e}")
        return 0

def get_prices(db_file=DB_FILE):
    """
    Busca todos os preços do banco de dados.
    """
    if not os.path.exists(db_file):
        print(f"Arquivo de banco de dados não encontrado: {db_file}")
        return pd.DataFrame()
        
    try:
        with sqlite3.connect(db_file) as con:
            # Ordenar pelos mais recentes (melhor timestamp entre compra e venda)
            query = f"SELECT * FROM {TABLE_NAME} ORDER BY MAX(timestamp_sell_min, timestamp_buy_max) DESC"
            df = pd.read_sql_query(query, con)
            
            # Converter timestamps de volta para datetime
            df['timestamp_sell_min'] = pd.to_datetime(df['timestamp_sell_min'], utc=True, errors='coerce')
            df['timestamp_buy_max'] = pd.to_datetime(df['timestamp_buy_max'], utc=True, errors='coerce')
            
            return df
    except sqlite3.Error as e:
        print(f"Erro ao buscar dados: {e}")
        # Retorna DF vazio se a tabela não existir
        return pd.DataFrame()