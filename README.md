📊 Albion Market Arbitrage Analyzer

Ferramenta Open Source de inteligência de mercado para Albion Online. O objetivo é identificar oportunidades de arbitragem (comprar barato em uma cidade, vender caro em outra ou no Mercado Negro) utilizando dados da comunidade.

Nota: Este projeto foi desenvolvido com fins educacionais para demonstrar análise de dados financeiros em jogos MMO.

🎯 O Problema

O mercado do Albion é local. Um item em Martlock não tem o mesmo preço em Lymhurst. Encontrar margens de lucro exige verificar milhares de itens manualmente.

💡 A Solução

Este analisador conecta-se à API do Albion Data Project, baixa preços em tempo real e cruza dados de Venda (Sell Order) vs Compra (Buy Order) considerando:

Taxas de mercado (Premium vs Free).

Custos de transporte.

Taxa de retorno (ROI).

Recência dos dados (Confiança).

📸 Screenshots

<img width="1903" height="898" alt="image" src="https://github.com/user-attachments/assets/d1507da6-a37a-4bac-9094-d955d941e5cb" />


🚀 Funcionalidades

Scanner de Arbitragem: Verifica milhares de itens simultaneamente.

Filtros Inteligentes: Categoria, Tier, Encantamento e Qualidade.

Indicador de Liquidez: Alerta se o dado é muito antigo (risco de o item não vender).

Suporte ao Black Market: Analisa oportunidades para Caerleon.

Clean Data: Tratamento de erros para dados inconsistentes da API.

🛠️ Instalação e Uso Local

Clone o repositório:

git clone [https://github.com/seu-usuario/albion-market-analyzer.git](https://github.com/seu-usuario/albion-market-analyzer.git)
cd albion-market-analyzer


Instale as dependências:

pip install -r requirements.txt


Execute o Dashboard:

streamlit run app.py


📊 Estrutura do Código

app.py: Frontend (Streamlit). Gerencia a UI e interação.

arbitrage.py: O "cérebro". Contém a lógica matemática de lucro e ROI.

store.py: Camada de persistência (SQLite) com tratamento de dados brutos.

fetch_prices.py: Cliente HTTP para conexão com a API externa.

🤝 Contribuição e Dados

Esta ferramenta depende de dados enviados por jogadores usando o Albion Data Client.
Para saber como contribuir com dados, leia CAMPAIGN.md.

⚖️ Aviso Legal

Esta ferramenta apenas processa dados públicos. Ela não interage com o cliente do jogo, não lê memória e não automatiza ações (cliques/movimento). O uso é seguro e externo ao jogo.
