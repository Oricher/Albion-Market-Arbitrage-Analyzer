import pandas as pd
import json
import argparse
import requests # <-- AQUI: A biblioteca 'requests' é usada para fazer as chamadas HTTP
from datetime import datetime

# URL base da API pública
BASE_API_URL = "https://www.albion-online-data.com/api/v2/stats/prices" # <-- AQUI: O endereço da API

# Data "zero" do Albion (para timestamps nulos da API)
NULL_TIMESTAMP = "0001-01-01T00:00:00"

def load_sample_data(filepath='sample_data.json'):
    # ... (código do sample data, não relevante para a API real) ...
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if 'timestamp' in df.columns:
            df['timestamp_sell_min'] = df['timestamp']
            df['timestamp_buy_max'] = df['timestamp']
            df = df.drop(columns=['timestamp'])
        df['tier'] = df['item_id'].str.extract(r'T(\d)')[0].fillna(0).astype(int)
        print(f"Dados de amostra (compatibilidade) carregados de {filepath}.")
        return df
    except FileNotFoundError:
        print(f"Erro: Arquivo de amostra '{filepath}' não encontrado.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Erro ao carregar dados de amostra: {e}")
        return pd.DataFrame()

def fetch_prices_real(items, cities, qualities):
    """
    Busca preços reais da API do Albion Data Project.
    """
    if not items or not cities:
        print("API: Itens e Cidades são necessários.")
        return pd.DataFrame()

    item_list = ",".join(items).upper()
    city_list = ",".join(cities)
    quality_list = ",".join(map(str, qualities))

    params = {
        'locations': city_list,
        'qualities': quality_list
    }
    
    # A API usa os itens na URL
    url = f"{BASE_API_URL}/{item_list}"
    
    # <-- AQUI: PONTO DE CHECAGEM 1
    # Esta linha DEVE aparecer no seu terminal ao clicar o botão.
    print(f"Buscando dados da API: {url} (Cidades: {city_list})")
    
    try:
        # <-- AQUI: PONTO DE CHECAGEM 2 (A CONEXÃO REAL)
        # Esta é a linha que efetivamente se conecta à internet e "baixa" os dados.
        response = requests.get(url, params=params, timeout=10)
        
        # Lança um erro se a API retornar 404 (Não encontrado) ou 500 (Erro de servidor)
        response.raise_for_status() 
        data = response.json()
        
        if not data:
            print("API não retornou dados.") # A conexão funcionou, mas a API não tem dados.
            return pd.DataFrame()

        # ... (Restante da normalização dos dados) ...
        df = pd.DataFrame(data)
        df = df.rename(columns={
            'sell_price_min_date': 'timestamp_sell_min',
            'buy_price_max_date': 'timestamp_buy_max'
        })
        df['tier'] = df['item_id'].str.extract(r'T(\d)')[0].fillna(0).astype(int)
        df['timestamp_sell_min'] = df['timestamp_sell_min'].replace(NULL_TIMESTAMP, pd.NaT)
        df['timestamp_buy_max'] = df['timestamp_buy_max'].replace(NULL_TIMESTAMP, pd.NaT)
        expected_cols = [
            'item_id', 'city', 'quality', 
            'sell_price_min', 'timestamp_sell_min',
            'buy_price_max', 'timestamp_buy_max',
            'tier'
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        return df[expected_cols]

    # <-- AQUI: PONTO DE CHECAGEM 3 (Possíveis Falhas)
    except requests.Timeout:
        # Se a API demorar mais de 10 segundos
        print(f"Erro ao buscar dados da API: Timeout (demorou mais de 10s)")
        return pd.DataFrame()
    except requests.RequestException as e:
        # Qualquer outro erro de conexão (DNS, 404, 503, etc.)
        print(f"Erro ao buscar dados da API: {e}")
        return pd.DataFrame()

# ... (código do 'if __name__ == "__main__"') ...

if __name__ == "__main__":
    # Script para testes via linha de comando
    parser = argparse.ArgumentParser(description="Albion Market Data Fetcher")
    parser.add_argument(
        "--items",
        type=str,
        default="T4_ORE,T5_WOOD",
        help="Itens para buscar (separados por vírgula). Ex: T4_ORE,T5_WOOD"
    )
    parser.add_argument(
        "--cities",
        type=str,
        default="Bridgewatch,Martlock,Lymhurst,Thetford,Fort Sterling,Caerleon",
        help="Cidades para buscar (separadas por vírgula)."
    )
    parser.add_argument(
        "--qualities",
        type=str,
        default="1,2,3",
        help="Qualidades para buscar (separadas por vírgula)."
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Força o uso do arquivo sample_data.json"
    )

    args = parser.parse_args()

    items_list = args.items.split(',') if args.items else []
    cities_list = args.cities.split(',') if args.cities else []
    qualities_list = [int(q) for q in args.qualities.split(',')] if args.qualities else []

    if args.sample:
        print("Forçando uso de dados de amostra...")
        prices_df = load_sample_data()
        if items_list:
            prices_df = prices_df[prices_df['item_id'].isin(items_list)]
    else:
        print("Modo API...")
        prices_df = fetch_prices_real(items_list, cities_list, qualities_list)

    if not prices_df.empty:
        print("\n--- Dados Coletados ---")
        print(prices_df.head())
        
        # Teste de inserção no DB
        print("\nTestando inserção no DB...")
        store.init_db()
        count = store.insert_prices(prices_df)
        print(f"{count} registros inseridos/atualizados.")
        
        print("\nLendo dados do DB...")
        db_data = store.get_prices()
        print(db_data.head())
    else:
        print("Nenhum dado encontrado.")