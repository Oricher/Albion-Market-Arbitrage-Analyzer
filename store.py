import sqlite3
import pandas as pd

DB_FILE = "albion_market.db"
TABLE_NAME = "market_prices"

def init_db(db_file=DB_FILE):
    """
    Cria a tabela de preços de mercado se ela não existir.
    Usa 'UNIQUE' e 'ON CONFLICT REPLACE' para lidar com atualizações
    e evitar duplicatas exatas.
    """
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        item_id TEXT NOT NULL,
        city TEXT NOT NULL,
        quality INTEGER NOT NULL,
        sell_price_min INTEGER,
        buy_price_max INTEGER,
        timestamp TEXT NOT NULL,
        tier INTEGER,
        PRIMARY KEY (item_id, city, quality, timestamp)
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

    # Garantir que o DataFrame tenha apenas as colunas da tabela
    # e na ordem correta
    expected_cols = ['item_id', 'city', 'quality', 'sell_price_min', 'buy_price_max', 'timestamp', 'tier']
    
    # Adiciona colunas faltantes com None (embora o 'load_sample_data' já faça isso)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
            
    # Filtra apenas para as colunas esperadas
    df_to_insert = df[expected_cols].copy()

    # Converter colunas numéricas para tipos que o SQLite entende
    df_to_insert['quality'] = pd.to_numeric(df_to_insert['quality'], errors='coerce').fillna(0).astype(int)
    df_to_insert['tier'] = pd.to_numeric(df_to_insert['tier'], errors='coerce').fillna(0).astype(int)
    df_to_insert['sell_price_min'] = pd.to_numeric(df_to_insert['sell_price_min'], errors='coerce').fillna(0).astype(int)
    df_to_insert['buy_price_max'] = pd.to_numeric(df_to_insert['buy_price_max'], errors='coerce').fillna(0).astype(int)

    # Remover linhas onde a chave primária (item, city, quality, timestamp) é nula
    df_to_insert = df_to_insert.dropna(subset=['item_id', 'city', 'quality', 'timestamp'])

    if df_to_insert.empty:
        print("Nenhum dado válido para inserir após a limpeza.")
        return 0

    try:
        with sqlite3.connect(db_file) as con:
            # Usamos 'replace' que ativa o 'ON CONFLICT REPLACE'
            # (ou 'ON CONFLICT IGNORE' se usarmos 'append' e uma constraint 'UNIQUE')
            # A forma mais robusta é usar tuplas e executemany
            
            # Criar a declaração INSERT com ON CONFLICT
            # Como a PRIMARY KEY já está definida, 'to_sql' com 'if_exists='append''
            # falhará em duplicatas, ou 'if_exists='replace'' apagará a tabela.
            
            # Usamos a forma manual para ter controle total com ON CONFLICT
            
            data_tuples = [tuple(x) for x in df_to_insert.to_records(index=False)]
            
            insert_query = f"""
            INSERT INTO {TABLE_NAME} (
                item_id, city, quality, sell_price_min, buy_price_max, timestamp, tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id, city, quality, timestamp) DO UPDATE SET
                sell_price_min = excluded.sell_price_min,
                buy_price_max = excluded.buy_price_max,
                tier = excluded.tier;
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
    try:
        with sqlite3.connect(db_file) as con:
            # Ordenar pelos mais recentes primeiro
            query = f"SELECT * FROM {TABLE_NAME} ORDER BY timestamp DESC"
            df = pd.read_sql_query(query, con)
            return df
    except sqlite3.Error as e:
        print(f"Erro ao buscar dados: {e}")
        # Retorna DF vazio se a tabela não existir
        return pd.DataFrame()