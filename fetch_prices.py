import pandas as pd
import json
import argparse
import requests # Apenas para o futuro; não usado no load_sample_data

# URL base da API pública (exemplo, pode mudar)
# TODO: Verificar os endpoints corretos do Albion Data Project
# Exemplo: https://www.albion-online-data.com/api/v2/stats/prices/
# Exemplo de dump: https://github.com/broderickhyman/albiondata-client/blob/master/dump.go
BASE_API_URL = "https://www.albion-online-data.com/api/v2/stats/prices"

def load_sample_data(filepath='sample_data.json'):
    """
    Carrega dados de um arquivo JSON de amostra e retorna um DataFrame.
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Garantir que as colunas esperadas existam
        expected_cols = ['item_id', 'city', 'sell_price_min', 'buy_price_max', 'timestamp', 'quality', 'tier']
        for col in expected_cols:
            if col not in df.columns:
                # Adiciona coluna com None se estiver faltando
                df[col] = None
        
        # Adiciona 'tier' baseado no 'item_id' (ex: T4_ORE -> 4)
        # Esta é uma simplificação, pode não ser perfeita para todos os itens
        df['tier'] = df['item_id'].str.extract(r'T(\d)')[0].fillna(0).astype(int)

        print(f"Dados de amostra carregados com sucesso de {filepath}.")
        return df

    except FileNotFoundError:
        print(f"Erro: Arquivo de amostra '{filepath}' não encontrado.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Erro ao carregar dados de amostra: {e}")
        return pd.DataFrame()

def fetch_prices_real(items, cities):
    """
    (NÃO IMPLEMENTADO NO MVP)
    Busca preços reais da API do Albion Data Project.
    """
    print(f"Buscando preços para itens: {items} nas cidades: {cities}")
    
    # TODO: Implementar a lógica de request para a API real.
    # Isso exigirá 'requests' e 'pandas.read_json' ou similar.
    # Exemplo de como poderia ser:
    #
    # item_list = ",".join(items)
    # city_list = ",".join(cities)
    # params = {
    #     'items': item_list,
    #     'locations': city_list,
    #     'qualities': '1,2,3,4,5' # Exemplo
    # }
    # try:
    #     response = requests.get(f"{BASE_API_URL}/{item_list}", params=params)
    #     response.raise_for_status() # Lança erro se a request falhar
    #     data = response.json()
    #     
    #     # TODO: Normalizar o JSON da API em um DataFrame
    #     # O formato da API pode ser complexo e exigir normalização.
    #     # Ex: pd.json_normalize(data)
    #
    #     df = pd.DataFrame() # Placeholder
    #     return df
    #
    # except requests.RequestException as e:
    #     print(f"Erro ao buscar dados da API: {e}")
    #     return pd.DataFrame()

    print("--- ATENÇÃO: Usando dados de amostra (fetch_prices_real não implementado) ---")
    # Fallback para dados de amostra no MVP
    df = load_sample_data()
    # Filtra o sample data para simular a chamada de API
    if items:
        df = df[df['item_id'].isin(items)]
    if cities:
        df = df[df['city'].isin(cities)]
        
    return df


if __name__ == "__main__":
    # Este 'main' é para testes e para o futuro.
    # O app.py chama as funções load_sample_data() diretamente.
    
    parser = argparse.ArgumentParser(description="Albion Market Data Fetcher")
    parser.add_argument(
        "--items",
        type=str,
        help="Itens para buscar (separados por vírgula). Ex: T4_ORE,T5_WOOD"
    )
    parser.add_argument(
        "--cities",
        type=str,
        help="Cidades para buscar (separadas por vírgula). Ex: Bridgewatch,Martlock"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Força o uso do arquivo sample_data.json"
    )

    args = parser.parse_args()

    items_list = args.items.split(',') if args.items else []
    cities_list = args.cities.split(',') if args.cities else []

    if args.sample:
        print("Forçando uso de dados de amostra...")
        prices_df = load_sample_data()
        if items_list:
            prices_df = prices_df[prices_df['item_id'].isin(items_list)]
        if cities_list:
            prices_df = prices_df[prices_df['city'].isin(cities_list)]
    else:
        print("Modo API (atualmente usa dados de amostra como fallback)...")
        # No futuro, isso chamará a API real
        prices_df = fetch_prices_real(items_list, cities_list)

    if not prices_df.empty:
        print("\n--- Dados Coletados ---")
        print(prices_df.head())
        
        # TODO: Adicionar lógica para salvar no DB (store.py)
        # store.init_db()
        # store.insert_prices(prices_df)
        # print("\nDados inseridos no banco de dados.")
    else:
        print("Nenhum dado encontrado.")