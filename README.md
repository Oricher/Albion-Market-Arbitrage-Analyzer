Albion Market Arbitrage Analyzer (MVP)

Este é um protótipo (MVP) de uma ferramenta para analisar o mercado do jogo Albion Online e identificar oportunidades de "arbitragem" (comprar barato em uma cidade e vender caro em outra).

Versão Atual (MVP): Esta ferramenta usa um arquivo local (sample_data.json) para simular dados de mercado e não se conecta à API real do Albion Data Project.

Aviso Ético e Limitações

Esta ferramenta NÃO é um bot.

Ela não automatiza nenhuma ação dentro do jogo.

Ela não lê a memória do cliente nem interage com o processo do jogo.

O objetivo é apenas análise de dados para ajudar na tomada de decisão manual.

O uso de ferramentas automatizadas de compra/venda viola os Termos de Serviço do Albion Online. Use esta ferramenta apenas para análise.

Qualidade dos Dados (Importante!)

Os dados de mercado de fontes comunitárias (como o Albion Data Project) dependem de jogadores que rodam o cliente de coleta.

Os dados podem estar desatualizados, incompletos ou esparsos.

Sempre verifique o confidence_score e os timestamps antes de tomar uma decisão de mercado. Uma oportunidade com "lucro" de 200% pode ser baseada em um preço de 3 dias atrás.

Funcionalidades (MVP)

Carrega dados de mercado (atualmente de um JSON local).

Armazena o histórico de preços em um banco de dados SQLite local.

Calcula oportunidades de arbitragem entre cidades, incluindo taxas de mercado configuráveis.

Exibe as melhores oportunidades em um dashboard interativo (Streamlit).

Permite a exportação dos resultados para CSV.

Instalação

Clone este repositório:

git clone [https://github.com/seu-usuario/albion_market_analyzer.git](https://github.com/seu-usuario/albion_market_analyzer.git)
cd albion_market_analyzer


Crie um ambiente virtual (recomendado):

python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate


Instale as dependências:

pip install -r requirements.txt


Como Rodar

Execute o dashboard Streamlit:

streamlit run app.py


Abra o navegador no endereço local fornecido (geralmente http://localhost:8501).

No dashboard:

Clique no botão "Carregar Sample Data e Atualizar DB" para popular o banco de dados local.

Ajuste os parâmetros (taxa de mercado, custo de transporte) na barra lateral.

Filtre os itens que deseja analisar.

Visualize os preços e as principais oportunidades.

Clique em "Exportar Oportunidades (CSV)" para baixar os dados.

Exemplo de Uso (Futuro, com API real)

O script fetch_prices.py está preparado para receber argumentos de linha de comando. Quando a API real for integrada, você poderá usá-lo assim:

python fetch_prices.py --items T4_ORE,T5_WOOD --cities Bridgewatch,Martlock

Linha de Raciocínio: 
Estrutura de Pastas (Tree)

albion_market_analyzer/
├── .gitignore
├── README.md
├── app.py
├── arbitrage.py
├── fetch_prices.py
├── requirements.txt
├── sample_data.json
└── store.py
