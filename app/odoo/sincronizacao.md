INFO:app.odoo.routes.sincronizacao_integrada:📊 Carregando dashboard de sincronização integrada...
14:58:59 | INFO     | app.odoo.routes.sincronizacao_integrada | 📊 Carregando dashboard de sincronização integrada...
INFO:app.odoo.services.sincronizacao_integrada_service:🔍 Verificando status atual do sistema...
14:58:59 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔍 Verificando status atual do sistema...
2025-09-05 14:58:59,516 - frete_sistema - INFO - ⏱️ GET /odoo/sync-integrada/ | Status: 200 | Tempo: 0.054s
INFO:frete_sistema:⏱️ GET /odoo/sync-integrada/ | Status: 200 | Tempo: 0.054s
14:58:59 | INFO     | frete_sistema | ⏱️ GET /odoo/sync-integrada/ | Status: 200 | Tempo: 0.054s
10.214.237.14 - - [05/Sep/2025:14:58:59 +0000] "GET /odoo/sync-integrada/ HTTP/1.1" 200 52400 "https://sistema-fretes.onrender.com/carteira/workspace" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
10.214.201.45 - - [05/Sep/2025:14:58:59 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/odoo/sync-integrada/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="6b71f37e-a46e-4687" responseTimeMS=5 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="201.63.40.74" requestID="4598388b-21cf-460a" responseTimeMS=6 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
10.214.242.63 - - [05/Sep/2025:14:59:00 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/odoo/sync-integrada/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
2025-09-05 14:59:00,144 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
14:59:00 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
2025-09-05 14:59:00,147 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
14:59:00 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
10.214.145.106 - - [05/Sep/2025:14:59:00 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/odoo/sync-integrada/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
2025-09-05 14:59:02,334 - frete_sistema - INFO - 🌐 POST /odoo/sync-integrada/executar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 POST /odoo/sync-integrada/executar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
14:59:02 | INFO     | frete_sistema | 🌐 POST /odoo/sync-integrada/executar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:app.odoo.routes.sincronizacao_integrada:🚀 INICIANDO sincronização integrada segura (filtro carteira: True)
14:59:02 | INFO     | app.odoo.routes.sincronizacao_integrada | 🚀 INICIANDO sincronização integrada segura (filtro carteira: True)
INFO:app.odoo.services.sincronizacao_integrada_service:🚀 INICIANDO SINCRONIZAÇÃO INTEGRADA SEGURA (FATURAMENTO → CARTEIRA)
14:59:02 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🚀 INICIANDO SINCRONIZAÇÃO INTEGRADA SEGURA (FATURAMENTO → CARTEIRA)
INFO:app.odoo.services.sincronizacao_integrada_service:📊 ETAPA 1/3: Sincronizando FATURAMENTO (prioridade de segurança)...
14:59:02 | INFO     | app.odoo.services.sincronizacao_integrada_service | 📊 ETAPA 1/3: Sincronizando FATURAMENTO (prioridade de segurança)...
INFO:app.odoo.services.sincronizacao_integrada_service:📊 Executando sincronização completa de faturamento + estoque...
14:59:02 | INFO     | app.odoo.services.sincronizacao_integrada_service | 📊 Executando sincronização completa de faturamento + estoque...
INFO:app.odoo.services.faturamento_service:🚀 SINCRONIZAÇÃO INCREMENTAL + INTEGRAÇÃO COMPLETA
14:59:02 | INFO     | app.odoo.services.faturamento_service | 🚀 SINCRONIZAÇÃO INCREMENTAL + INTEGRAÇÃO COMPLETA
INFO:app.odoo.services.faturamento_service:🚀 Busca faturamento otimizada: filtro_postado=True, limite=0
14:59:02 | INFO     | app.odoo.services.faturamento_service | 🚀 Busca faturamento otimizada: filtro_postado=True, limite=0
INFO:app.odoo.services.faturamento_service:📋 Buscando linhas de faturamento...
14:59:02 | INFO     | app.odoo.services.faturamento_service | 📋 Buscando linhas de faturamento...
INFO:app.odoo.services.faturamento_service:🔄 Usando sincronização limitada...
14:59:02 | INFO     | app.odoo.services.faturamento_service | 🔄 Usando sincronização limitada...
INFO:app.odoo.utils.connection:✅ Conexão common estabelecida com Odoo
14:59:02 | INFO     | app.odoo.utils.connection | ✅ Conexão common estabelecida com Odoo
INFO:app.odoo.utils.connection:✅ Autenticado no Odoo com UID: 42
14:59:03 | INFO     | app.odoo.utils.connection | ✅ Autenticado no Odoo com UID: 42
INFO:app.odoo.utils.connection:✅ Conexão models estabelecida com Odoo
14:59:03 | INFO     | app.odoo.utils.connection | ✅ Conexão models estabelecida com Odoo
INFO:app.odoo.services.faturamento_service:📊 Total carregado: 20000 registros (limitado para performance)
14:59:09 | INFO     | app.odoo.services.faturamento_service | 📊 Total carregado: 20000 registros (limitado para performance)
INFO:app.odoo.services.faturamento_service:🚀 Processando faturamento com método REALMENTE otimizado...
14:59:09 | INFO     | app.odoo.services.faturamento_service | 🚀 Processando faturamento com método REALMENTE otimizado...
INFO:app.odoo.services.faturamento_service:📊 Filtrando 20000 linhas brutas...
14:59:09 | INFO     | app.odoo.services.faturamento_service | 📊 Filtrando 20000 linhas brutas...
INFO:app.odoo.services.faturamento_service:📈 Resultado filtragem: 1798 válidas, 18202 descartadas
14:59:09 | INFO     | app.odoo.services.faturamento_service | 📈 Resultado filtragem: 1798 válidas, 18202 descartadas
INFO:app.odoo.services.faturamento_service:📊 Coletados: 138 faturas, 122 clientes, 125 produtos
14:59:09 | INFO     | app.odoo.services.faturamento_service | 📊 Coletados: 138 faturas, 122 clientes, 125 produtos
INFO:app.odoo.services.faturamento_service:🔍 Query 1/6: Buscando faturas...
14:59:09 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 1/6: Buscando faturas...
INFO:app.odoo.services.faturamento_service:🔍 Query 2/6: Buscando 122 clientes...
14:59:10 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 2/6: Buscando 122 clientes...
INFO:app.odoo.services.faturamento_service:🔍 Query 3/6: Buscando 125 produtos...
14:59:11 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 3/6: Buscando 125 produtos...
INFO:app.odoo.services.faturamento_service:🔍 Query 4/6: Buscando 125 templates...
14:59:11 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 4/6: Buscando 125 templates...
INFO:app.odoo.services.faturamento_service:🔍 Query 5/6: Buscando 73 municípios...
14:59:12 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 5/6: Buscando 73 municípios...
INFO:app.odoo.services.faturamento_service:🔍 Query 6/6: Buscando 23 vendedores...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 6/6: Buscando 23 vendedores...
INFO:app.odoo.services.faturamento_service:🧠 Caches criados, fazendo JOIN em memória...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 🧠 Caches criados, fazendo JOIN em memória...
INFO:app.odoo.services.faturamento_service:✅ OTIMIZAÇÃO FATURAMENTO COMPLETA:
14:59:13 | INFO     | app.odoo.services.faturamento_service | ✅ OTIMIZAÇÃO FATURAMENTO COMPLETA:
INFO:app.odoo.services.faturamento_service:   📊 1798 itens processados
14:59:13 | INFO     | app.odoo.services.faturamento_service |    📊 1798 itens processados
INFO:app.odoo.services.faturamento_service:   ⚡ 6 queries executadas (vs 340000 do método antigo)
14:59:13 | INFO     | app.odoo.services.faturamento_service |    ⚡ 6 queries executadas (vs 340000 do método antigo)
INFO:app.odoo.services.faturamento_service:   🚀 56666x mais rápido
14:59:13 | INFO     | app.odoo.services.faturamento_service |    🚀 56666x mais rápido
INFO:app.odoo.services.faturamento_service:📊 Processando 1798 registros do Odoo...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 📊 Processando 1798 registros do Odoo...
INFO:app.odoo.services.faturamento_service:🧹 Sanitizando dados de faturamento...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 🧹 Sanitizando dados de faturamento...
INFO:app.odoo.services.faturamento_service:🔍 Carregando índice de registros existentes...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 🔍 Carregando índice de registros existentes...
INFO:app.odoo.services.faturamento_service:📋 Índice criado com 11927 registros existentes
14:59:13 | INFO     | app.odoo.services.faturamento_service | 📋 Índice criado com 11927 registros existentes
INFO:app.odoo.services.faturamento_service:✅ Sincronização principal concluída: 5 novos, 0 atualizados
14:59:13 | INFO     | app.odoo.services.faturamento_service | ✅ Sincronização principal concluída: 5 novos, 0 atualizados
INFO:app.odoo.services.faturamento_service:🔍 Verificando consistência de NFs CANCELADAS...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 🔍 Verificando consistência de NFs CANCELADAS...
INFO:app.odoo.services.faturamento_service:🔄 Iniciando consolidação para RelatorioFaturamentoImportado...
14:59:13 | INFO     | app.odoo.services.faturamento_service | 🔄 Iniciando consolidação para RelatorioFaturamentoImportado...
INFO:app.odoo.services.faturamento_service:Consolidando dados para RelatorioFaturamentoImportado
14:59:13 | INFO     | app.odoo.services.faturamento_service | Consolidando dados para RelatorioFaturamentoImportado
INFO:app.odoo.services.faturamento_service:Consolidação concluída: 1798 itens processados, 2 relatórios criados
14:59:14 | INFO     | app.odoo.services.faturamento_service | Consolidação concluída: 1798 itens processados, 2 relatórios criados
INFO:app.odoo.services.faturamento_service:✅ Consolidação concluída: 2 relatórios processados
14:59:14 | INFO     | app.odoo.services.faturamento_service | ✅ Consolidação concluída: 2 relatórios processados
INFO:app.odoo.services.faturamento_service:🏭 Iniciando processamento de movimentações de estoque...
14:59:14 | INFO     | app.odoo.services.faturamento_service | 🏭 Iniciando processamento de movimentações de estoque...
INFO:app.odoo.services.faturamento_service:📊 Processando 2 NFs específicas da sincronização
14:59:14 | INFO     | app.odoo.services.faturamento_service | 📊 Processando 2 NFs específicas da sincronização
INFO:app.faturamento.services.processar_faturamento:🧹 Limpando inconsistências anteriores...
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 🧹 Limpando inconsistências anteriores...
INFO:app.faturamento.services.processar_faturamento:✅ 148 inconsistências não resolvidas removidas antes do processamento
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 148 inconsistências não resolvidas removidas antes do processamento
INFO:app.faturamento.services.processar_faturamento:🎯 Processando 2 NFs específicas...
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 🎯 Processando 2 NFs específicas...
INFO:app.faturamento.services.processar_faturamento:📊 Total de NFs para processar: 2
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📊 Total de NFs para processar: 2
INFO:app.faturamento.services.processar_faturamento:📋 Processando NF 139075 - Pedido VCD2543306
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📋 Processando NF 139075 - Pedido VCD2543306
INFO:app.faturamento.services.processar_faturamento:✅ Único EmbarqueItem encontrado - usando lote LOTE_20250904_160603_314
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ Único EmbarqueItem encontrado - usando lote LOTE_20250904_160603_314
INFO:app.faturamento.services.processar_faturamento:📦 Processando NF 139075 com lote LOTE_20250904_160603_314
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📦 Processando NF 139075 com lote LOTE_20250904_160603_314
INFO:app.faturamento.services.processar_faturamento:✅ 4 Separações marcadas como sincronizadas
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 4 Separações marcadas como sincronizadas
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ FaturamentoProduto marcado como status_nf='Lançado' para NF 139075
INFO:app.faturamento.services.processar_faturamento:✅ FaturamentoProduto marcado como status_nf='Lançado' para NF 139075
INFO:app.faturamento.services.processar_faturamento:📦 Criando 4 movimentações com lote LOTE_20250904_160603_314 para NF 139075
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📦 Criando 4 movimentações com lote LOTE_20250904_160603_314 para NF 139075
INFO:app.faturamento.services.processar_faturamento:✅ 4 movimentações com lote preparadas para NF 139075
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 4 movimentações com lote preparadas para NF 139075
INFO:app.faturamento.services.processar_faturamento:✅ 4 Separações atualizadas para status FATURADO
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 4 Separações atualizadas para status FATURADO
INFO:app.faturamento.services.processar_faturamento:📋 Processando NF 139072 - Pedido VCD2543298
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📋 Processando NF 139072 - Pedido VCD2543298
INFO:app.faturamento.services.processar_faturamento:✅ Único EmbarqueItem encontrado - usando lote LOTE_20250903_191842_704
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ Único EmbarqueItem encontrado - usando lote LOTE_20250903_191842_704
INFO:app.faturamento.services.processar_faturamento:📦 Processando NF 139072 com lote LOTE_20250903_191842_704
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📦 Processando NF 139072 com lote LOTE_20250903_191842_704
INFO:app.faturamento.services.processar_faturamento:✅ 1 Separações marcadas como sincronizadas
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 1 Separações marcadas como sincronizadas
INFO:app.faturamento.services.processar_faturamento:✅ FaturamentoProduto marcado como status_nf='Lançado' para NF 139072
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ FaturamentoProduto marcado como status_nf='Lançado' para NF 139072
INFO:app.faturamento.services.processar_faturamento:📦 Criando 1 movimentações com lote LOTE_20250903_191842_704 para NF 139072
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📦 Criando 1 movimentações com lote LOTE_20250903_191842_704 para NF 139072
INFO:app.faturamento.services.processar_faturamento:✅ 1 movimentações com lote preparadas para NF 139072
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 1 movimentações com lote preparadas para NF 139072
INFO:app.faturamento.services.processar_faturamento:✅ 1 Separações atualizadas para status FATURADO
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | ✅ 1 Separações atualizadas para status FATURADO
INFO:app.faturamento.services.processar_faturamento:🔄 Atualizando status das separações para FATURADO...
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 🔄 Atualizando status das separações para FATURADO...
INFO:app.faturamento.services.processar_faturamento:📊 Encontradas 15278 separações com NF mas sem status FATURADO
14:59:14 | INFO     | app.faturamento.services.processar_faturamento | 📊 Encontradas 15278 separações com NF mas sem status FATURADO
INFO:app.faturamento.services.processar_faturamento:🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...
14:59:28 | INFO     | app.faturamento.services.processar_faturamento | 🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...
INFO:app.faturamento.services.processar_faturamento:✅ Total: 11612 separações atualizadas para FATURADO
15:02:22 | INFO     | app.faturamento.services.processar_faturamento | ✅ Total: 11612 separações atualizadas para FATURADO
INFO:app.faturamento.services.processar_faturamento:✅ 11612 separações atualizadas para status FATURADO
15:02:22 | INFO     | app.faturamento.services.processar_faturamento | ✅ 11612 separações atualizadas para status FATURADO
INFO:app.faturamento.services.processar_faturamento:✅ Processamento completo: 2 NFs processadas
15:02:22 | INFO     | app.faturamento.services.processar_faturamento | ✅ Processamento completo: 2 NFs processadas
INFO:app.faturamento.services.processar_faturamento:📊 Movimentações criadas: 5
15:02:22 | INFO     | app.faturamento.services.processar_faturamento | 📊 Movimentações criadas: 5
INFO:app.odoo.services.faturamento_service:✅ Processamento de estoque concluído:
                    - NFs processadas: 2
                    - Já processadas: 0 
                    - Canceladas: 0
                    - Com embarque: 0
                    - Sem separação: 0
                    - Movimentações criadas: 5
                    - Embarques atualizados: 0
                    
15:02:22 | INFO     | app.odoo.services.faturamento_service | ✅ Processamento de estoque concluído:
                    - NFs processadas: 2
                    - Já processadas: 0 
                    - Canceladas: 0
                    - Com embarque: 0
                    - Sem separação: 0
                    - Movimentações criadas: 5
                    - Embarques atualizados: 0
                    
INFO:app.odoo.services.faturamento_service:🔄 Sincronizando entregas para 2 NFs...
15:02:22 | INFO     | app.odoo.services.faturamento_service | 🔄 Sincronizando entregas para 2 NFs...
INFO:app.odoo.services.faturamento_service:🔄 Re-validando embarques pendentes para 5 NFs novas...
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310341632
[SYNC] ✅ separacao_lote_id preenchido: LOTE_20250903_191842_704
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
[SYNC] ✅ separacao_lote_id preenchido: LOTE_20250904_160603_314
15:02:22 | INFO     | app.odoo.services.faturamento_service | 🔄 Re-validando embarques pendentes para 5 NFs novas...
INFO:app.odoo.services.faturamento_service:🔄 Sincronizando NFs pendentes em embarques...
🔄 RE-VALIDANDO EMBARQUES PENDENTES após importação de 5 NFs
📦 Embarque 1327: ✅ Todos os requisitos atendidos! 2 NF(s) validada(s) com sucesso
✅ 1 embarques re-validados, 0 NFs divergentes corrigidas
15:02:22 | INFO     | app.odoo.services.faturamento_service | 🔄 Sincronizando NFs pendentes em embarques...
INFO:app.odoo.services.faturamento_service:🔄 Processando lançamento automático de fretes para 122 CNPJs...
[DEBUG] 🔍 Buscando NFs de embarques que precisam ser sincronizadas...
[DEBUG] 📦 Total de NFs únicas em embarques ativos: 2308
[DEBUG] 📊 Total de NFs no monitoramento: 8997
[DEBUG] ⚠️ NFs pendentes de sincronização: 147
[DEBUG] 🎯 NFs em embarques COM faturamento que precisam sincronizar: 100
[DEBUG] 🔄 Sincronizando NF de embarque: 136159
[DEBUG] 🔄 Sincronizando NF de embarque: 138612
[DEBUG] 🔄 Sincronizando NF de embarque: 137699
[DEBUG] 🔄 Sincronizando NF de embarque: 136857
[DEBUG] 🔄 Sincronizando NF de embarque: 136948
[DEBUG] 🔄 Sincronizando NF de embarque: 136880
[DEBUG] 🔄 Sincronizando NF de embarque: 137844
[DEBUG] 🔄 Sincronizando NF de embarque: 137828
[DEBUG] 🔄 Sincronizando NF de embarque: 138902
[DEBUG] 🔄 Sincronizando NF de embarque: 138476
[DEBUG] 🔄 Sincronizando NF de embarque: 139068
[DEBUG] 🔄 Sincronizando NF de embarque: 138282
[DEBUG] 🔄 Sincronizando NF de embarque: 137534
[DEBUG] 🔄 Sincronizando NF de embarque: 137900
[DEBUG] 🔄 Sincronizando NF de embarque: 136704
[DEBUG] 🔄 Sincronizando NF de embarque: 136605
[DEBUG] 🔄 Sincronizando NF de embarque: 137476
[DEBUG] 🔄 Sincronizando NF de embarque: 136202
[DEBUG] 🔄 Sincronizando NF de embarque: 137026
[DEBUG] 🔄 Sincronizando NF de embarque: 136858
[DEBUG] 🔄 Sincronizando NF de embarque: 138903
[DEBUG] 🔄 Sincronizando NF de embarque: 138811
[DEBUG] 🔄 Sincronizando NF de embarque: 137063
[DEBUG] 🔄 Sincronizando NF de embarque: 136859
[DEBUG] 🔄 Sincronizando NF de embarque: 138630
[DEBUG] 🔄 Sincronizando NF de embarque: 138376
[DEBUG] 🔄 Sincronizando NF de embarque: 136788
[DEBUG] 🔄 Sincronizando NF de embarque: 138766
[DEBUG] 🔄 Sincronizando NF de embarque: 136860
[DEBUG] 🔄 Sincronizando NF de embarque: 137874
[DEBUG] 🔄 Sincronizando NF de embarque: 137784
[DEBUG] 🔄 Sincronizando NF de embarque: 137524
[DEBUG] 🔄 Sincronizando NF de embarque: 136203
[DEBUG] 🔄 Sincronizando NF de embarque: 137530
[DEBUG] 🔄 Sincronizando NF de embarque: 138970
[DEBUG] 🔄 Sincronizando NF de embarque: 137188
[DEBUG] 🔄 Sincronizando NF de embarque: 136613
[DEBUG] 🔄 Sincronizando NF de embarque: 137787
[DEBUG] 🔄 Sincronizando NF de embarque: 138430
[DEBUG] 🔄 Sincronizando NF de embarque: 138574
[DEBUG] 🔄 Sincronizando NF de embarque: 137083
[DEBUG] 🔄 Sincronizando NF de embarque: 137823
[DEBUG] 🔄 Sincronizando NF de embarque: 136489
[DEBUG] 🔄 Sincronizando NF de embarque: 136063
[DEBUG] 🔄 Sincronizando NF de embarque: 139062
[DEBUG] 🔄 Sincronizando NF de embarque: 138283
[DEBUG] 🔄 Sincronizando NF de embarque: 138900
[DEBUG] 🔄 Sincronizando NF de embarque: 139048
[DEBUG] 🔄 Sincronizando NF de embarque: 137257
[DEBUG] 🔄 Sincronizando NF de embarque: 137793
[DEBUG] 🔄 Sincronizando NF de embarque: 138183
[DEBUG] 🔄 Sincronizando NF de embarque: 137783
[DEBUG] 🔄 Sincronizando NF de embarque: 137881
[DEBUG] 🔄 Sincronizando NF de embarque: 137532
[DEBUG] 🔄 Sincronizando NF de embarque: 138475
[DEBUG] 🔄 Sincronizando NF de embarque: 137838
[DEBUG] 🔄 Sincronizando NF de embarque: 137873
[DEBUG] 🔄 Sincronizando NF de embarque: 137666
[DEBUG] 🔄 Sincronizando NF de embarque: 136856
[DEBUG] 🔄 Sincronizando NF de embarque: 136530
[DEBUG] 🔄 Sincronizando NF de embarque: 136099
[DEBUG] 🔄 Sincronizando NF de embarque: 138812
[DEBUG] 🔄 Sincronizando NF de embarque: 137526
[DEBUG] 🔄 Sincronizando NF de embarque: 136319
[DEBUG] 🔄 Sincronizando NF de embarque: 137698
[DEBUG] 🔄 Sincronizando NF de embarque: 138751
[DEBUG] 🔄 Sincronizando NF de embarque: 137525
[DEBUG] 🔄 Sincronizando NF de embarque: 137906
[DEBUG] 🔄 Sincronizando NF de embarque: 138829
[DEBUG] 🔄 Sincronizando NF de embarque: 138527
[DEBUG] 🔄 Sincronizando NF de embarque: 137521
[DEBUG] 🔄 Sincronizando NF de embarque: 138575
[DEBUG] 🔄 Sincronizando NF de embarque: 137027
[DEBUG] 🔄 Sincronizando NF de embarque: 138105
[DEBUG] 🔄 Sincronizando NF de embarque: 137667
[DEBUG] 🔄 Sincronizando NF de embarque: 136789
[DEBUG] 🔄 Sincronizando NF de embarque: 137795
[DEBUG] 🔄 Sincronizando NF de embarque: 138627
[DEBUG] 🔄 Sincronizando NF de embarque: 137533
[DEBUG] 🔄 Sincronizando NF de embarque: 136855
[DEBUG] 🔄 Sincronizando NF de embarque: 136067
[DEBUG] 🔄 Sincronizando NF de embarque: 136611
[DEBUG] 🔄 Sincronizando NF de embarque: 137049
[DEBUG] 🔄 Sincronizando NF de embarque: 136068
[DEBUG] 🔄 Sincronizando NF de embarque: 139039
[DEBUG] 🔄 Sincronizando NF de embarque: 136212
[DEBUG] 🔄 Sincronizando NF de embarque: 135995
[DEBUG] 🔄 Sincronizando NF de embarque: 138838
[DEBUG] 🔄 Sincronizando NF de embarque: 136278
[DEBUG] 🔄 Sincronizando NF de embarque: 136211
[DEBUG] 🔄 Sincronizando NF de embarque: 91937
[DEBUG] 🔄 Sincronizando NF de embarque: 137788
[DEBUG] 🔄 Sincronizando NF de embarque: 138876
[DEBUG] 🔄 Sincronizando NF de embarque: 135970
[DEBUG] 🔄 Sincronizando NF de embarque: 136059
[DEBUG] 🔄 Sincronizando NF de embarque: 137529
[DEBUG] 🔄 Sincronizando NF de embarque: 136640
[DEBUG] 🔄 Sincronizando NF de embarque: 136697
[DEBUG] 🔄 Sincronizando NF de embarque: 136279
[DEBUG] 🔄 Sincronizando NF de embarque: 136078
[DEBUG] ✅ Total de NFs de embarques sincronizadas: 100
15:02:23 | INFO     | app.odoo.services.faturamento_service | 🔄 Processando lançamento automático de fretes para 122 CNPJs...
INFO:app.odoo.services.faturamento_service:   ✅ SINCRONIZAÇÃO INCREMENTAL COMPLETA CONCLUÍDA:
15:02:27 | INFO     | app.odoo.services.faturamento_service |    ✅ SINCRONIZAÇÃO INCREMENTAL COMPLETA CONCLUÍDA:
INFO:app.odoo.services.faturamento_service:   ➕ 5 novos registros inseridos
INFO:app.odoo.services.faturamento_service:   ✏️ 0 registros atualizados
15:02:27 | INFO     | app.odoo.services.faturamento_service |    ➕ 5 novos registros inseridos
INFO:app.odoo.services.faturamento_service:   📋 2 relatórios consolidados
15:02:27 | INFO     | app.odoo.services.faturamento_service |    ✏️ 0 registros atualizados
15:02:27 | INFO     | app.odoo.services.faturamento_service |    📋 2 relatórios consolidados
15:02:27 | INFO     | app.odoo.services.faturamento_service |    🔄 2 entregas sincronizadas
15:02:27 | INFO     | app.odoo.services.faturamento_service |    📦 5 embarques re-validados
15:02:27 | INFO     | app.odoo.services.faturamento_service |    🚚 100 NFs de embarques sincronizadas
15:02:27 | INFO     | app.odoo.services.faturamento_service |    💰 9 fretes lançados automaticamente
15:02:27 | INFO     | app.odoo.services.faturamento_service |    ⏱️ Tempo execução: 204.74s
15:02:27 | INFO     | app.odoo.services.faturamento_service |    ❌ 0 erros principais + 0 erros de sincronização
INFO:app.odoo.services.faturamento_service:   🔄 2 entregas sincronizadas
INFO:app.odoo.services.faturamento_service:   📦 5 embarques re-validados
INFO:app.odoo.services.faturamento_service:   🚚 100 NFs de embarques sincronizadas
INFO:app.odoo.services.faturamento_service:   💰 9 fretes lançados automaticamente
INFO:app.odoo.services.faturamento_service:   ⏱️ Tempo execução: 204.74s
INFO:app.odoo.services.faturamento_service:   ❌ 0 erros principais + 0 erros de sincronização
INFO:app.odoo.services.sincronizacao_integrada_service:✅ Faturamento sincronizado: 5 registros, 5 movimentações de estoque
15:02:27 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ Faturamento sincronizado: 5 registros, 5 movimentações de estoque
INFO:app.odoo.services.sincronizacao_integrada_service:🔍 ETAPA 2/3: Validação de integridade pós-faturamento...
15:02:27 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔍 ETAPA 2/3: Validação de integridade pós-faturamento...
INFO:app.odoo.services.sincronizacao_integrada_service:🔍 Validando integridade após sincronização de faturamento...
15:02:27 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔍 Validando integridade após sincronização de faturamento...
INFO:app.odoo.services.sincronizacao_integrada_service:✅ 11932 registros de faturamento encontrados
15:02:27 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ 11932 registros de faturamento encontrados
INFO:app.odoo.services.sincronizacao_integrada_service:🔄 ETAPA 2.5/4: Atualizando status FATURADO dos pedidos...
15:02:27 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔄 ETAPA 2.5/4: Atualizando status FATURADO dos pedidos...
INFO:app.faturamento.services.processar_faturamento:📊 Encontradas 15278 separações com NF mas sem status FATURADO
15:02:27 | INFO     | app.faturamento.services.processar_faturamento | 📊 Encontradas 15278 separações com NF mas sem status FATURADO
INFO:app.faturamento.services.processar_faturamento:🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...
15:02:42 | INFO     | app.faturamento.services.processar_faturamento | 🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="201.63.40.74" requestID="ec5004d4-c66a-44ff" responseTimeMS=16 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/pedidos/lista_pedidosclientIP="201.63.40.74" requestID="bb0c4917-1e0e-4d34" responseTimeMS=2694 responseBytes=333888 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/api/alertas-separacao/card-htmlclientIP="201.63.40.74" requestID="8d345561-563a-4b1d" responseTimeMS=23 responseBytes=389 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
2025-09-05 15:05:18,480 - frete_sistema - INFO - 🌐 GET /pedidos/lista_pedidos | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /pedidos/lista_pedidos | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:05:18 | INFO     | frete_sistema | 🌐 GET /pedidos/lista_pedidos | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310348992
INFO:frete_sistema:⏱️ GET /pedidos/lista_pedidos | Status: 200 | Tempo: 1.983s
2025-09-05 15:05:20,463 - frete_sistema - INFO - ⏱️ GET /pedidos/lista_pedidos | Status: 200 | Tempo: 1.983s
15:05:20 | INFO     | frete_sistema | ⏱️ GET /pedidos/lista_pedidos | Status: 200 | Tempo: 1.983s
10.214.145.106 - - [05/Sep/2025:15:05:21 +0000] "GET /pedidos/lista_pedidos HTTP/1.1" 200 16345410 "https://sistema-fretes.onrender.com/odoo/sync-integrada/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310339072
10.214.242.63 - - [05/Sep/2025:15:05:21 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/pedidos/lista_pedidos" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
2025-09-05 15:05:21,862 - frete_sistema - INFO - 🌐 GET /api/alertas-separacao/card-html | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /api/alertas-separacao/card-html | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:05:21 | INFO     | frete_sistema | 🌐 GET /api/alertas-separacao/card-html | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
INFO:frete_sistema:⏱️ GET /api/alertas-separacao/card-html | Status: 204 | Tempo: 0.018s
2025-09-05 15:05:21,880 - frete_sistema - INFO - ⏱️ GET /api/alertas-separacao/card-html | Status: 204 | Tempo: 0.018s
15:05:21 | INFO     | frete_sistema | ⏱️ GET /api/alertas-separacao/card-html | Status: 204 | Tempo: 0.018s
10.214.170.28 - - [05/Sep/2025:15:05:21 +0000] "GET /api/alertas-separacao/card-html HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/pedidos/lista_pedidos" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
10.214.170.28 - - [05/Sep/2025:15:05:28 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/pedidos/lista_pedidos" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="c1eec531-4577-4ddf" responseTimeMS=33 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
INFO:app.faturamento.services.processar_faturamento:✅ Total: 11612 separações atualizadas para FATURADO
15:05:50 | INFO     | app.faturamento.services.processar_faturamento | ✅ Total: 11612 separações atualizadas para FATURADO
INFO:app.odoo.services.sincronizacao_integrada_service:✅ 11612 pedidos atualizados para status FATURADO
15:05:50 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ 11612 pedidos atualizados para status FATURADO
INFO:app.odoo.services.sincronizacao_integrada_service:💾 Status FATURADO salvo no banco antes de processar carteira
15:05:50 | INFO     | app.odoo.services.sincronizacao_integrada_service | 💾 Status FATURADO salvo no banco antes de processar carteira
INFO:app.odoo.services.sincronizacao_integrada_service:🔄 ETAPA 3/4: Sincronizando CARTEIRA (com faturamento protegido)...
15:05:50 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔄 ETAPA 3/4: Sincronizando CARTEIRA (com faturamento protegido)...
INFO:app.odoo.services.carteira_service:🚀 INICIANDO SINCRONIZAÇÃO OPERACIONAL COMPLETA COM GESTÃO INTELIGENTE
15:05:50 | INFO     | app.odoo.services.carteira_service | 🚀 INICIANDO SINCRONIZAÇÃO OPERACIONAL COMPLETA COM GESTÃO INTELIGENTE
INFO:app.odoo.services.carteira_service:📊 Fase 1: Analisando estado atual da carteira e calculando saldos...
15:05:50 | INFO     | app.odoo.services.carteira_service | 📊 Fase 1: Analisando estado atual da carteira e calculando saldos...
INFO:app.odoo.services.carteira_service:   📦 Carregando carteira atual...
15:05:50 | INFO     | app.odoo.services.carteira_service |    📦 Carregando carteira atual...
INFO:app.odoo.services.carteira_service:   ✅ 4052 itens carregados
INFO:app.odoo.services.carteira_service:   📦 Carregando todos os faturamentos...
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
15:05:50 | INFO     | app.odoo.services.carteira_service |    ✅ 4052 itens carregados
15:05:50 | INFO     | app.odoo.services.carteira_service |    📦 Carregando todos os faturamentos...
INFO:app.odoo.services.carteira_service:   ✅ 11555 faturamentos carregados
INFO:app.odoo.services.carteira_service:   📦 Carregando todas as separações não sincronizadas...
15:05:50 | INFO     | app.odoo.services.carteira_service |    ✅ 11555 faturamentos carregados
15:05:50 | INFO     | app.odoo.services.carteira_service |    📦 Carregando todas as separações não sincronizadas...
INFO:app.odoo.services.carteira_service:   ✅ 2530 separações carregadas
INFO:app.odoo.services.carteira_service:   🔄 Processando cálculos em memória...
15:05:50 | INFO     | app.odoo.services.carteira_service |    ✅ 2530 separações carregadas
15:05:50 | INFO     | app.odoo.services.carteira_service |    🔄 Processando cálculos em memória...
INFO:app.odoo.services.carteira_service:✅ 4052 registros Odoo indexados com saldos calculados
15:05:50 | INFO     | app.odoo.services.carteira_service | ✅ 4052 registros Odoo indexados com saldos calculados
INFO:app.odoo.services.carteira_service:🛡️ 0 registros não-Odoo protegidos
15:05:50 | INFO     | app.odoo.services.carteira_service | 🛡️ 0 registros não-Odoo protegidos
INFO:app.odoo.services.carteira_service:🔄 Fase 2: Buscando dados atualizados do Odoo...
15:05:50 | INFO     | app.odoo.services.carteira_service | 🔄 Fase 2: Buscando dados atualizados do Odoo...
INFO:app.odoo.services.carteira_service:Buscando carteira pendente do Odoo com filtro inteligente...
15:05:50 | INFO     | app.odoo.services.carteira_service | Buscando carteira pendente do Odoo com filtro inteligente...
INFO:app.odoo.services.carteira_service:📋 Coletando pedidos existentes na carteira para filtro...
15:05:50 | INFO     | app.odoo.services.carteira_service | 📋 Coletando pedidos existentes na carteira para filtro...
INFO:app.odoo.services.carteira_service:✅ 572 pedidos Odoo existentes serão incluídos no filtro
15:05:50 | INFO     | app.odoo.services.carteira_service | ✅ 572 pedidos Odoo existentes serão incluídos no filtro
INFO:app.odoo.services.carteira_service:🔍 Usando filtro combinado: (qty_saldo > 0) OU (pedidos existentes)
15:05:50 | INFO     | app.odoo.services.carteira_service | 🔍 Usando filtro combinado: (qty_saldo > 0) OU (pedidos existentes)
INFO:app.odoo.services.carteira_service:📡 Executando query no Odoo com filtro inteligente...
15:05:50 | INFO     | app.odoo.services.carteira_service | 📡 Executando query no Odoo com filtro inteligente...
INFO:app.odoo.utils.connection:✅ Conexão common estabelecida com Odoo
15:05:50 | INFO     | app.odoo.utils.connection | ✅ Conexão common estabelecida com Odoo
INFO:app.odoo.utils.connection:✅ Autenticado no Odoo com UID: 42
15:05:51 | INFO     | app.odoo.utils.connection | ✅ Autenticado no Odoo com UID: 42
INFO:app.odoo.utils.connection:✅ Conexão models estabelecida com Odoo
15:05:51 | INFO     | app.odoo.utils.connection | ✅ Conexão models estabelecida com Odoo
INFO:app.odoo.services.carteira_service:✅ SUCESSO: 5454 registros encontrados
15:05:55 | INFO     | app.odoo.services.carteira_service | ✅ SUCESSO: 5454 registros encontrados
INFO:app.odoo.services.carteira_service:🚀 Processando carteira com método REALMENTE otimizado...
15:05:55 | INFO     | app.odoo.services.carteira_service | 🚀 Processando carteira com método REALMENTE otimizado...
INFO:app.odoo.services.carteira_service:📊 Coletados: 573 pedidos, 193 produtos
15:05:55 | INFO     | app.odoo.services.carteira_service | 📊 Coletados: 573 pedidos, 193 produtos
INFO:app.odoo.services.carteira_service:🔍 Query 1/5: Buscando pedidos...
15:05:55 | INFO     | app.odoo.services.carteira_service | 🔍 Query 1/5: Buscando pedidos...
INFO:app.odoo.services.carteira_service:🔍 Query 2/5: Buscando 396 partners...
15:05:56 | INFO     | app.odoo.services.carteira_service | 🔍 Query 2/5: Buscando 396 partners...
INFO:app.odoo.services.carteira_service:🔍 Query 3/5: Buscando 193 produtos...
15:05:56 | INFO     | app.odoo.services.carteira_service | 🔍 Query 3/5: Buscando 193 produtos...
INFO:app.odoo.services.carteira_service:🔍 Query 4/5: Buscando 71 categorias...
15:05:57 | INFO     | app.odoo.services.carteira_service | 🔍 Query 4/5: Buscando 71 categorias...
INFO:app.odoo.services.carteira_service:🔍 Query 5/5: Buscando 21 categorias parent...
15:05:57 | INFO     | app.odoo.services.carteira_service | 🔍 Query 5/5: Buscando 21 categorias parent...
INFO:app.odoo.services.carteira_service:🧠 Caches criados, fazendo JOIN em memória...
15:05:58 | INFO     | app.odoo.services.carteira_service | 🧠 Caches criados, fazendo JOIN em memória...
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - R SAO LAZARO
15:05:59 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - R SAO LAZARO
     [POST]499sistema-fretes.onrender.com/odoo/sync-integrada/executarclientIP="201.63.40.74" requestID="c8cf0450-d2e2-4ae0" responseTimeMS=416452 responseBytes=29 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
2025-09-05 15:06:00,997 - frete_sistema - INFO - 🌐 GET /portaria/historico | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:06:00 | INFO     | frete_sistema | 🌐 GET /portaria/historico | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /portaria/historico | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - AV PAPA JOAO PAULO I
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310341632
15:06:02 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - AV PAPA JOAO PAULO I
2025-09-05 15:06:02,472 - frete_sistema - INFO - ⏱️ GET /portaria/historico | Status: 200 | Tempo: 1.475s
INFO:frete_sistema:⏱️ GET /portaria/historico | Status: 200 | Tempo: 1.475s
15:06:02 | INFO     | frete_sistema | ⏱️ GET /portaria/historico | Status: 200 | Tempo: 1.475s
10.214.242.63 - - [05/Sep/2025:15:06:02 +0000] "GET /portaria/historico HTTP/1.1" 200 2460392 "https://sistema-fretes.onrender.com/portaria/detalhes_veiculo/1416" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/portaria/historicoclientIP="138.97.242.51" requestID="e571a861-0851-4267" responseTimeMS=1513 responseBytes=72630 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - AV GUINLE
15:06:02 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - AV GUINLE
10.214.214.165 - - [05/Sep/2025:15:06:03 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/portaria/historico" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="138.97.242.51" requestID="68c714a1-424a-422b" responseTimeMS=7 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:06:06,622 - frete_sistema - INFO - 🌐 GET /portaria/ | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /portaria/ | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:06:06 | INFO     | frete_sistema | 🌐 GET /portaria/ | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
2025-09-05 15:06:06,728 - frete_sistema - INFO - ⏱️ GET /portaria/ | Status: 200 | Tempo: 0.106s
INFO:frete_sistema:⏱️ GET /portaria/ | Status: 200 | Tempo: 0.106s
15:06:06 | INFO     | frete_sistema | ⏱️ GET /portaria/ | Status: 200 | Tempo: 0.106s
10.214.214.165 - - [05/Sep/2025:15:06:06 +0000] "GET /portaria/ HTTP/1.1" 200 83072 "https://sistema-fretes.onrender.com/portaria/historico" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
10.214.242.63 - - [05/Sep/2025:15:06:07 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/portaria/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - R CECILIA ROIZEN
15:06:07 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - R CECILIA ROIZEN
     [GET]200sistema-fretes.onrender.com/portaria/clientIP="138.97.242.51" requestID="74426ef4-6412-4283" responseTimeMS=127 responseBytes=14227 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="138.97.242.51" requestID="9d748d4e-22bc-4fa2" responseTimeMS=9 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="138.97.242.51" requestID="ede54f07-11fa-45fb" responseTimeMS=7 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:06:08,413 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:06:08 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:06:08,418 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.004s
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.004s
15:06:08 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.004s
10.214.237.14 - - [05/Sep/2025:15:06:08 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/portaria/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - ROD FERNAO DIAS
15:06:08 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - ROD FERNAO DIAS
10.214.201.45 - - [05/Sep/2025:15:06:08 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/portaria/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - RUA NESTOR DE HOLANDA
15:06:08 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - RUA NESTOR DE HOLANDA
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="138.97.242.51" requestID="5a14fffc-8c05-4df6" responseTimeMS=12 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - R BIRIGUI
15:06:09 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - R BIRIGUI
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - RUA BELA VISTA DO PARAISO
15:06:14 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - RUA BELA VISTA DO PARAISO
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - R HEROIS DA F.E.B.
15:06:14 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - R HEROIS DA F.E.B.
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO:  - False
15:06:17 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO:  - False
INFO:app.odoo.services.carteira_service:✅ OTIMIZAÇÃO COMPLETA:
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ OTIMIZAÇÃO COMPLETA:
INFO:app.odoo.services.carteira_service:   📊 5454 itens processados
15:06:21 | INFO     | app.odoo.services.carteira_service |    📊 5454 itens processados
INFO:app.odoo.services.carteira_service:   ⚡ 5 queries executadas (vs 103626 do método antigo)
15:06:21 | INFO     | app.odoo.services.carteira_service |    ⚡ 5 queries executadas (vs 103626 do método antigo)
INFO:app.odoo.services.carteira_service:   🚀 20725x mais rápido
15:06:21 | INFO     | app.odoo.services.carteira_service |    🚀 20725x mais rápido
INFO:app.odoo.services.carteira_service:✅ 4049 registros obtidos do Odoo
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ 4049 registros obtidos do Odoo
INFO:app.odoo.services.carteira_service:🔍 Fase 3: Calculando saldos e identificando diferenças...
15:06:21 | INFO     | app.odoo.services.carteira_service | 🔍 Fase 3: Calculando saldos e identificando diferenças...
INFO:app.odoo.services.carteira_service:📊 Calculando saldos para itens importados do Odoo...
15:06:21 | INFO     | app.odoo.services.carteira_service | 📊 Calculando saldos para itens importados do Odoo...
WARNING:app.utils.database_helpers:⚠️ Conexão perdida, tentando reconectar: (psycopg2.OperationalError) SSL connection has been closed unexpectedly
[SQL: SELECT 1]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
15:06:21 | WARNING  | app.utils.database_helpers | ⚠️ Conexão perdida, tentando reconectar: (psycopg2.OperationalError) SSL connection has been closed unexpectedly
[SQL: SELECT 1]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:app.utils.database_helpers:✅ Conexão restabelecida com sucesso
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310341632
15:06:21 | INFO     | app.utils.database_helpers | ✅ Conexão restabelecida com sucesso
INFO:app.odoo.services.carteira_service:🔍 Buscando faturamentos para 571 pedidos únicos...
15:06:21 | INFO     | app.odoo.services.carteira_service | 🔍 Buscando faturamentos para 571 pedidos únicos...
INFO:app.odoo.services.carteira_service:✅ 1486 faturamentos carregados em UMA query!
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ 1486 faturamentos carregados em UMA query!
WARNING:app.odoo.services.carteira_service:⚠️ Saldo negativo detectado: VCD2521039/4856125 = -40.00
15:06:21 | WARNING  | app.odoo.services.carteira_service | ⚠️ Saldo negativo detectado: VCD2521039/4856125 = -40.00
INFO:app.odoo.services.carteira_service:📊 Diferenças identificadas:
15:06:21 | INFO     | app.odoo.services.carteira_service | 📊 Diferenças identificadas:
INFO:app.odoo.services.carteira_service:   📉 2 reduções
15:06:21 | INFO     | app.odoo.services.carteira_service |    📉 2 reduções
INFO:app.odoo.services.carteira_service:   📈 2 aumentos
15:06:21 | INFO     | app.odoo.services.carteira_service |    📈 2 aumentos
INFO:app.odoo.services.carteira_service:   ➕ 1 novos itens
15:06:21 | INFO     | app.odoo.services.carteira_service |    ➕ 1 novos itens
INFO:app.odoo.services.carteira_service:   ➖ 5 itens removidos
15:06:21 | INFO     | app.odoo.services.carteira_service |    ➖ 5 itens removidos
WARNING:app.odoo.services.carteira_service:   ⚠️ 1 itens com saldo negativo (NF devolvida?)
15:06:21 | WARNING  | app.odoo.services.carteira_service |    ⚠️ 1 itens com saldo negativo (NF devolvida?)
INFO:app.odoo.services.carteira_service:📦 Fase 3.2: Garantindo CadastroPalletizacao para todos os produtos...
15:06:21 | INFO     | app.odoo.services.carteira_service | 📦 Fase 3.2: Garantindo CadastroPalletizacao para todos os produtos...
INFO:app.odoo.services.carteira_service:📦 Iniciando garantia de CadastroPalletizacao para 4049 registros
15:06:21 | INFO     | app.odoo.services.carteira_service | 📦 Iniciando garantia de CadastroPalletizacao para 4049 registros
INFO:app.odoo.services.carteira_service:📊 178 produtos únicos identificados
15:06:21 | INFO     | app.odoo.services.carteira_service | 📊 178 produtos únicos identificados
INFO:app.odoo.services.carteira_service:✅ CadastroPalletizacao garantido:
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ CadastroPalletizacao garantido:
INFO:app.odoo.services.carteira_service:   - 0 produtos criados
15:06:21 | INFO     | app.odoo.services.carteira_service |    - 0 produtos criados
INFO:app.odoo.services.carteira_service:   - 0 produtos atualizados
15:06:21 | INFO     | app.odoo.services.carteira_service |    - 0 produtos atualizados
15:06:21 | INFO     | app.odoo.services.carteira_service |    - 178 já existentes
INFO:app.odoo.services.carteira_service:   - 178 já existentes
WARNING:app.odoo.services.carteira_service:🛡️ PROTEÇÃO: Pedido VCD2543298 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
15:06:21 | WARNING  | app.odoo.services.carteira_service | 🛡️ PROTEÇÃO: Pedido VCD2543298 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
WARNING:app.odoo.services.carteira_service:🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
15:06:21 | WARNING  | app.odoo.services.carteira_service | 🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
WARNING:app.odoo.services.carteira_service:🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
15:06:21 | WARNING  | app.odoo.services.carteira_service | 🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
WARNING:app.odoo.services.carteira_service:🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
15:06:21 | WARNING  | app.odoo.services.carteira_service | 🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
WARNING:app.odoo.services.carteira_service:🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
15:06:21 | WARNING  | app.odoo.services.carteira_service | 🛡️ PROTEÇÃO: Pedido VCD2543306 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
INFO:app.odoo.services.carteira_service:📦 Processando pedido alterado: VCD2543437
15:06:21 | INFO     | app.odoo.services.carteira_service | 📦 Processando pedido alterado: VCD2543437
INFO:app.odoo.services.ajuste_sincronizacao_service:🔄 Processando pedido alterado: VCD2543437
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 🔄 Processando pedido alterado: VCD2543437
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2543437 não tem separações alteráveis
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2543437 não tem separações alteráveis
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2543437 não tem separações alteráveis
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2543437 não tem separações alteráveis
INFO:app.odoo.services.carteira_service:✅ Pedido VCD2543437 processado: SEM_SEPARACAO
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ Pedido VCD2543437 processado: SEM_SEPARACAO
INFO:app.odoo.services.carteira_service:📦 Processando pedido alterado: VCD2543436
15:06:21 | INFO     | app.odoo.services.carteira_service | 📦 Processando pedido alterado: VCD2543436
INFO:app.odoo.services.ajuste_sincronizacao_service:🔄 Processando pedido alterado: VCD2543436
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 🔄 Processando pedido alterado: VCD2543436
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2543436 não tem separações alteráveis
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2543436 não tem separações alteráveis
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2543436 não tem separações alteráveis
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2543436 não tem separações alteráveis
INFO:app.odoo.services.carteira_service:✅ Pedido VCD2543436 processado: SEM_SEPARACAO
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ Pedido VCD2543436 processado: SEM_SEPARACAO
INFO:app.odoo.services.carteira_service:📦 Processando pedido alterado: VCD2563349
15:06:21 | INFO     | app.odoo.services.carteira_service | 📦 Processando pedido alterado: VCD2563349
INFO:app.odoo.services.ajuste_sincronizacao_service:🔄 Processando pedido alterado: VCD2563349
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 🔄 Processando pedido alterado: VCD2563349
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2563349 não tem separações alteráveis
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2563349 não tem separações alteráveis
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2563349 não tem separações alteráveis
15:06:21 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2563349 não tem separações alteráveis
INFO:app.odoo.services.carteira_service:✅ Pedido VCD2563349 processado: SEM_SEPARACAO
15:06:21 | INFO     | app.odoo.services.carteira_service | ✅ Pedido VCD2563349 processado: SEM_SEPARACAO
INFO:app.odoo.services.carteira_service:💾 Fase 7: Atualizando carteira principal...
15:06:21 | INFO     | app.odoo.services.carteira_service | 💾 Fase 7: Atualizando carteira principal...
INFO:app.odoo.services.carteira_service:🧹 Sanitizando dados...
15:06:21 | INFO     | app.odoo.services.carteira_service | 🧹 Sanitizando dados...
INFO:app.odoo.services.carteira_service:🔍 Tratando duplicatas dos dados do Odoo...
15:06:22 | INFO     | app.odoo.services.carteira_service | 🔍 Tratando duplicatas dos dados do Odoo...
WARNING:app.odoo.services.carteira_service:⚠️ Duplicata consolidada: VCD2543437/4639556 - Qtds somadas: 20.0 + existente
15:06:22 | WARNING  | app.odoo.services.carteira_service | ⚠️ Duplicata consolidada: VCD2543437/4639556 - Qtds somadas: 20.0 + existente
WARNING:app.odoo.services.carteira_service:🔄 1 itens duplicados consolidados (quantidades somadas)
15:06:22 | WARNING  | app.odoo.services.carteira_service | 🔄 1 itens duplicados consolidados (quantidades somadas)
INFO:app.odoo.services.carteira_service:🛡️ Preservando 0 registros não-Odoo...
15:06:22 | INFO     | app.odoo.services.carteira_service | 🛡️ Preservando 0 registros não-Odoo...
INFO:app.odoo.services.carteira_service:🔄 Usando estratégia UPSERT para evitar erros de chave duplicada...
15:06:22 | INFO     | app.odoo.services.carteira_service | 🔄 Usando estratégia UPSERT para evitar erros de chave duplicada...
INFO:app.odoo.services.carteira_service:📊 4052 registros Odoo existentes encontrados
15:06:22 | INFO     | app.odoo.services.carteira_service | 📊 4052 registros Odoo existentes encontrados
INFO:app.odoo.services.carteira_service:🗑️ 5 registros Odoo obsoletos removidos
15:06:22 | INFO     | app.odoo.services.carteira_service | 🗑️ 5 registros Odoo obsoletos removidos
INFO:app.odoo.services.carteira_service:🔄 Processando 4048 registros em operação única otimizada...
15:06:22 | INFO     | app.odoo.services.carteira_service | 🔄 Processando 4048 registros em operação única otimizada...
INFO:app.odoo.services.carteira_service:   💾 Salvando 1 inserções e 4047 atualizações...
15:06:23 | INFO     | app.odoo.services.carteira_service |    💾 Salvando 1 inserções e 4047 atualizações...
INFO:app.odoo.services.carteira_service:   ✅ SUCESSO! Todos os registros salvos em UM commit!
15:06:25 | INFO     | app.odoo.services.carteira_service |    ✅ SUCESSO! Todos os registros salvos em UM commit!
INFO:app.odoo.services.carteira_service:✅ 1 novos registros inseridos
15:06:25 | INFO     | app.odoo.services.carteira_service | ✅ 1 novos registros inseridos
INFO:app.odoo.services.carteira_service:🔄 4047 registros atualizados
15:06:25 | INFO     | app.odoo.services.carteira_service | 🔄 4047 registros atualizados
INFO:app.odoo.services.carteira_service:💾 Fase 8: Todas as alterações já salvas incrementalmente
15:06:25 | INFO     | app.odoo.services.carteira_service | 💾 Fase 8: Todas as alterações já salvas incrementalmente
INFO:app.odoo.services.carteira_service:🔄 Fase 9: Atualizando dados de Separação/Pedido...
15:06:25 | INFO     | app.odoo.services.carteira_service | 🔄 Fase 9: Atualizando dados de Separação/Pedido...
INFO:app.carteira.services.atualizar_dados_service:🔄 Iniciando atualização de dados baseado na CarteiraPrincipal...
15:06:25 | INFO     | app.carteira.services.atualizar_dados_service | 🔄 Iniciando atualização de dados baseado na CarteiraPrincipal...
INFO:app.carteira.services.atualizar_dados_service:📋 Encontrados 339 pedidos com separações não sincronizadas
15:06:25 | INFO     | app.carteira.services.atualizar_dados_service | 📋 Encontrados 339 pedidos com separações não sincronizadas
2025-09-05 15:06:25,473 - frete_sistema - INFO - 🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:06:25 | INFO     | frete_sistema | 🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.019s
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588510530304
2025-09-05 15:06:25,492 - frete_sistema - INFO - ⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.019s
15:06:25 | INFO     | frete_sistema | ⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.019s
10.214.242.63 - - [05/Sep/2025:15:06:25 +0000] "POST /portaria/buscar_motorista HTTP/1.1" 200 85 "https://sistema-fretes.onrender.com/portaria/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [POST]200sistema-fretes.onrender.com/portaria/buscar_motoristaclientIP="138.97.242.51" requestID="142b4636-e9d8-4bbf" responseTimeMS=24 responseBytes=460 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:06:28,591 - frete_sistema - INFO - 🌐 GET /portaria/cadastrar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /portaria/cadastrar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:06:28 | INFO     | frete_sistema | 🌐 GET /portaria/cadastrar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:06:28,641 - frete_sistema - INFO - ⏱️ GET /portaria/cadastrar_motorista | Status: 200 | Tempo: 0.050s
INFO:frete_sistema:⏱️ GET /portaria/cadastrar_motorista | Status: 200 | Tempo: 0.050s
15:06:28 | INFO     | frete_sistema | ⏱️ GET /portaria/cadastrar_motorista | Status: 200 | Tempo: 0.050s
10.214.145.106 - - [05/Sep/2025:15:06:28 +0000] "GET /portaria/cadastrar_motorista?from=portaria HTTP/1.1" 200 43936 "https://sistema-fretes.onrender.com/portaria/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
10.214.170.28 - - [05/Sep/2025:15:06:29 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portaria" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portariaclientIP="138.97.242.51" requestID="0055046f-7cc3-40a3" responseTimeMS=57 responseBytes=11281 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:06:29,873 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:06:29 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
2025-09-05 15:06:29,876 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
15:06:29 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
10.214.242.63 - - [05/Sep/2025:15:06:29 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portaria" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
10.214.201.45 - - [05/Sep/2025:15:06:30 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portaria" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="138.97.242.51" requestID="1ef1caba-a670-4984" responseTimeMS=5 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="138.97.242.51" requestID="cb466a0c-cf2b-4f52" responseTimeMS=8 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="138.97.242.51" requestID="eaea2376-3a52-4556" responseTimeMS=9 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
INFO:app.carteira.services.atualizar_dados_service:
                ✅ ATUALIZAÇÃO DE DADOS CONCLUÍDA:
                - Pedidos processados: 255
                - Separações atualizadas: 0
                - Erros encontrados: 0
            
15:06:33 | INFO     | app.carteira.services.atualizar_dados_service | 
                ✅ ATUALIZAÇÃO DE DADOS CONCLUÍDA:
                - Pedidos processados: 255
                - Separações atualizadas: 0
                - Erros encontrados: 0
            
INFO:app.odoo.services.carteira_service:✅ Dados atualizados: 255 pedidos, 0 separações
15:06:33 | INFO     | app.odoo.services.carteira_service | ✅ Dados atualizados: 255 pedidos, 0 separações
INFO:app.odoo.services.carteira_service:🔍 Fase 10: Verificação pós-sincronização...
15:06:33 | INFO     | app.odoo.services.carteira_service | 🔍 Fase 10: Verificação pós-sincronização...
INFO:app.odoo.services.carteira_service:🔍 Verificando impactos pós-sincronização...
15:06:33 | INFO     | app.odoo.services.carteira_service | 🔍 Verificando impactos pós-sincronização...
WARNING:app.odoo.services.carteira_service:🚨 48 alertas críticos pós-sincronização detectados
INFO:app.odoo.services.carteira_service:🧹 Fase 10.5: Limpeza de SaldoStandby...
15:07:16 | WARNING  | app.odoo.services.carteira_service | 🚨 48 alertas críticos pós-sincronização detectados
15:07:16 | INFO     | app.odoo.services.carteira_service | 🧹 Fase 10.5: Limpeza de SaldoStandby...
INFO:app.odoo.services.carteira_service:   ✅ Nenhum registro para remover de SaldoStandby
INFO:app.odoo.services.carteira_service:📞 Fase 10.6: Verificação de Contatos de Agendamento...
15:07:16 | INFO     | app.odoo.services.carteira_service |    ✅ Nenhum registro para remover de SaldoStandby
15:07:16 | INFO     | app.odoo.services.carteira_service | 📞 Fase 10.6: Verificação de Contatos de Agendamento...
INFO:app.odoo.services.carteira_service:   ✅ Todos os contatos de agendamento já estão configurados corretamente
15:07:16 | INFO     | app.odoo.services.carteira_service |    ✅ Todos os contatos de agendamento já estão configurados corretamente
INFO:app.odoo.services.carteira_service:📝 Fase 10.7: Atualizando forma de agendamento na carteira...
15:07:16 | INFO     | app.odoo.services.carteira_service | 📝 Fase 10.7: Atualizando forma de agendamento na carteira...
INFO:app.odoo.services.carteira_service:   ✅ 1 registros atualizados com forma de agendamento
15:07:16 | INFO     | app.odoo.services.carteira_service |    ✅ 1 registros atualizados com forma de agendamento
INFO:app.odoo.services.carteira_service:✅ SINCRONIZAÇÃO OPERACIONAL COMPLETA CONCLUÍDA:
15:07:16 | INFO     | app.odoo.services.carteira_service | ✅ SINCRONIZAÇÃO OPERACIONAL COMPLETA CONCLUÍDA:
INFO:app.odoo.services.carteira_service:   📊 1 registros inseridos
INFO:app.odoo.services.carteira_service:   🔄 4047 registros atualizados
15:07:16 | INFO     | app.odoo.services.carteira_service |    📊 1 registros inseridos
15:07:16 | INFO     | app.odoo.services.carteira_service |    🔄 4047 registros atualizados
INFO:app.odoo.services.carteira_service:   🗑️ 5 registros Odoo removidos
15:07:16 | INFO     | app.odoo.services.carteira_service |    🗑️ 5 registros Odoo removidos
INFO:app.odoo.services.carteira_service:   🛡️ 0 registros não-Odoo preservados
15:07:16 | INFO     | app.odoo.services.carteira_service |    🛡️ 0 registros não-Odoo preservados
INFO:app.odoo.services.carteira_service:   📉 0 reduções aplicadas
15:07:16 | INFO     | app.odoo.services.carteira_service |    📉 0 reduções aplicadas
INFO:app.odoo.services.carteira_service:   📈 0 aumentos aplicados
15:07:16 | INFO     | app.odoo.services.carteira_service |    📈 0 aumentos aplicados
INFO:app.odoo.services.carteira_service:   ➖ 0 remoções processadas
15:07:16 | INFO     | app.odoo.services.carteira_service |    ➖ 0 remoções processadas
INFO:app.odoo.services.carteira_service:   ➕ 1 novos itens
15:07:16 | INFO     | app.odoo.services.carteira_service |    ➕ 1 novos itens
INFO:app.odoo.services.carteira_service:   🚨 48 alertas pós-sincronização
15:07:16 | INFO     | app.odoo.services.carteira_service |    🚨 48 alertas pós-sincronização
INFO:app.odoo.services.carteira_service:   ⏱️ 86.27 segundos de execução
15:07:16 | INFO     | app.odoo.services.carteira_service |    ⏱️ 86.27 segundos de execução
INFO:app.odoo.services.sincronizacao_integrada_service:✅ SINCRONIZAÇÃO INTEGRADA CONCLUÍDA COM SUCESSO em 494.1s
15:07:16 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ SINCRONIZAÇÃO INTEGRADA CONCLUÍDA COM SUCESSO em 494.1s
INFO:frete_sistema:⏱️ POST /odoo/sync-integrada/executar | Status: 302 | Tempo: 494.146s
2025-09-05 15:07:16,480 - frete_sistema - INFO - ⏱️ POST /odoo/sync-integrada/executar | Status: 302 | Tempo: 494.146s
15:07:16 | INFO     | frete_sistema | ⏱️ POST /odoo/sync-integrada/executar | Status: 302 | Tempo: 494.146s
WARNING:frete_sistema:🐌 REQUISIÇÃO LENTA: /odoo/sync-integrada/executar em 494.146s
2025-09-05 15:07:16,480 - frete_sistema - WARNING - 🐌 REQUISIÇÃO LENTA: /odoo/sync-integrada/executar em 494.146s
15:07:16 | WARNING  | frete_sistema | 🐌 REQUISIÇÃO LENTA: /odoo/sync-integrada/executar em 494.146s
10.214.145.106 - - [05/Sep/2025:15:07:16 +0000] "POST /odoo/sync-integrada/executar HTTP/1.1" 302 229 "https://sistema-fretes.onrender.com/odoo/sync-integrada/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
2025-09-05 15:07:26,988 - frete_sistema - INFO - 🌐 POST /portaria/cadastrar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 POST /portaria/cadastrar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:07:26 | INFO     | frete_sistema | 🌐 POST /portaria/cadastrar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:07:27,000 - frete_sistema - INFO - ⏱️ POST /portaria/cadastrar_motorista | Status: 302 | Tempo: 0.012s
15:07:27 | INFO     | frete_sistema | ⏱️ POST /portaria/cadastrar_motorista | Status: 302 | Tempo: 0.012s
INFO:frete_sistema:⏱️ POST /portaria/cadastrar_motorista | Status: 302 | Tempo: 0.012s
10.214.242.63 - - [05/Sep/2025:15:07:27 +0000] "POST /portaria/cadastrar_motorista?from=portaria HTTP/1.1" 302 265 "https://sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portaria" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:07:27,472 - frete_sistema - INFO - 🌐 GET /portaria/ | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /portaria/ | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:07:27 | INFO     | frete_sistema | 🌐 GET /portaria/ | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:07:27,578 - frete_sistema - INFO - ⏱️ GET /portaria/ | Status: 200 | Tempo: 0.106s
INFO:frete_sistema:⏱️ GET /portaria/ | Status: 200 | Tempo: 0.106s
15:07:27 | INFO     | frete_sistema | ⏱️ GET /portaria/ | Status: 200 | Tempo: 0.106s
10.214.158.26 - - [05/Sep/2025:15:07:27 +0000] "GET /portaria/?motorista_cpf=334.450.952-72 HTTP/1.1" 200 83172 "https://sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portaria" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
10.214.201.45 - - [05/Sep/2025:15:07:28 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/portaria/?motorista_cpf=334.450.952-72" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [POST]302sistema-fretes.onrender.com/portaria/cadastrar_motorista?from=portariaclientIP="138.97.242.51" requestID="a0dbf7b6-79a4-4e68" responseTimeMS=17 responseBytes=602 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="138.97.242.51" requestID="ffef239a-fabf-4ee1" responseTimeMS=5 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/portaria/?motorista_cpf=334.450.952-72clientIP="138.97.242.51" requestID="bcbf9071-d8ee-4216" responseTimeMS=116 responseBytes=14399 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:07:28,792 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:07:28 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:07:28,796 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.004s
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.004s
15:07:28 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.004s
10.214.214.165 - - [05/Sep/2025:15:07:28 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/portaria/?motorista_cpf=334.450.952-72" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
10.214.237.162 - - [05/Sep/2025:15:07:29 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/portaria/?motorista_cpf=334.450.952-72" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="138.97.242.51" requestID="1456f858-be78-47a4" responseTimeMS=6 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="138.97.242.51" requestID="dfac4bd6-533b-45d2" responseTimeMS=9 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:07:36,236 - frete_sistema - INFO - 🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:07:36 | INFO     | frete_sistema | 🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.004s
2025-09-05 15:07:36,240 - frete_sistema - INFO - ⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.004s
15:07:36 | INFO     | frete_sistema | ⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.004s
10.214.214.165 - - [05/Sep/2025:15:07:36 +0000] "POST /portaria/buscar_motorista HTTP/1.1" 200 151 "https://sistema-fretes.onrender.com/portaria/?motorista_cpf=334.450.952-72" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [POST]200sistema-fretes.onrender.com/portaria/buscar_motoristaclientIP="138.97.242.51" requestID="d9d4f1ae-42a9-48f5" responseTimeMS=9 responseBytes=513 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [POST]200sistema-fretes.onrender.com/portaria/buscar_motoristaclientIP="138.97.242.51" requestID="99bd8692-3c1a-47da" responseTimeMS=11 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
2025-09-05 15:07:46,289 - frete_sistema - INFO - 🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:07:46 | INFO     | frete_sistema | 🌐 POST /portaria/buscar_motorista | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.005s
2025-09-05 15:07:46,294 - frete_sistema - INFO - ⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.005s
15:07:46 | INFO     | frete_sistema | ⏱️ POST /portaria/buscar_motorista | Status: 200 | Tempo: 0.005s
10.214.255.103 - - [05/Sep/2025:15:07:46 +0000] "POST /portaria/buscar_motorista HTTP/1.1" 200 147 "https://sistema-fretes.onrender.com/portaria/?motorista_cpf=334.450.952-72" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="39e21c70-e6aa-4cbb" responseTimeMS=12 responseBytes=158 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
10.214.145.106 - - [05/Sep/2025:15:09:04 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/fretes/listar?csrf_token=IjYzMzE4ODhjMmE4MGRiOWVhYmVkM2Y1ZjlmZjZmMDFjYjIwYWZkZmYi.aLr2YQ.G9Vuaw1K8edhB07LwuYG4xHZwVQ&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=137545&transportadora_id=&status=&data_inicio=&data_fim=" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
10.214.237.162 - - [05/Sep/2025:15:09:06 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/fretes/listar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="64bffd2a-8500-45dc" responseTimeMS=5 responseBytes=158 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
INFO:frete_sistema:🌐 GET /fretes/listar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:09:09,153 - frete_sistema - INFO - 🌐 GET /fretes/listar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:09 | INFO     | frete_sistema | 🌐 GET /fretes/listar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ GET /fretes/listar | Status: 200 | Tempo: 0.090s
2025-09-05 15:09:09,243 - frete_sistema - INFO - ⏱️ GET /fretes/listar | Status: 200 | Tempo: 0.090s
15:09:09 | INFO     | frete_sistema | ⏱️ GET /fretes/listar | Status: 200 | Tempo: 0.090s
10.214.237.162 - - [05/Sep/2025:15:09:09 +0000] "GET /fretes/listar HTTP/1.1" 200 188571 "https://sistema-fretes.onrender.com/fretes/listar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310348992
10.214.237.14 - - [05/Sep/2025:15:09:09 +0000] "GET /static/style.css HTTP/1.1" 200 0 "https://sistema-fretes.onrender.com/fretes/listar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:09,795 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:09 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:09:09,800 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.005s
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.005s
15:09:09 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.005s
10.214.214.165 - - [05/Sep/2025:15:09:09 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/fretes/listar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
10.214.170.28 - - [05/Sep/2025:15:09:09 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/fretes/listar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="201.63.40.74" requestID="8a88d1a0-17e6-40f7" responseTimeMS=9 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/static/style.cssclientIP="201.63.40.74" requestID="6616f3b3-b4a9-45dd" responseTimeMS=13 responseBytes=1663 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/fretes/listarclientIP="201.63.40.74" requestID="31c84740-51cd-4ad7" responseTimeMS=98 responseBytes=17852 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="b9ea933a-78bc-4487" responseTimeMS=5 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/fretes/listar?csrf_token=ImE5NWE5MGVkOGI0OTI5Y2Y2MDFiOGZjZjk4MDM3YTRmMzc1YmFhYzki.aLr9FQ.iCPDHCzEmKqBaHxZHls4uy9Q9Vo&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=138663&transportadora_id=&status=&data_inicio=&data_fim=clientIP="201.63.40.74" requestID="22dc219d-0b1a-4364" responseTimeMS=50 responseBytes=14161 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="201.63.40.74" requestID="87d5709d-c8a6-4897" responseTimeMS=6 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="bd275118-3555-4a75" responseTimeMS=4 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="201.63.40.74" requestID="da4a82f2-250f-4d43" responseTimeMS=7 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/fretes/2226/editarclientIP="201.63.40.74" requestID="8d6a9666-9089-4f15" responseTimeMS=61 responseBytes=13304 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="201.63.40.74" requestID="08bff4dc-6013-4742" responseTimeMS=17 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="75117cea-d869-4dd0" responseTimeMS=3 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="201.63.40.74" requestID="5b70296e-68cf-4fbb" responseTimeMS=15 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:20,078 - frete_sistema - INFO - 🌐 GET /fretes/listar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /fretes/listar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:20 | INFO     | frete_sistema | 🌐 GET /fretes/listar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-05 15:09:20,121 - frete_sistema - INFO - ⏱️ GET /fretes/listar | Status: 200 | Tempo: 0.044s
15:09:20 | INFO     | frete_sistema | ⏱️ GET /fretes/listar | Status: 200 | Tempo: 0.044s
INFO:frete_sistema:⏱️ GET /fretes/listar | Status: 200 | Tempo: 0.044s
10.214.237.162 - - [05/Sep/2025:15:09:20 +0000] "GET /fretes/listar?csrf_token=ImE5NWE5MGVkOGI0OTI5Y2Y2MDFiOGZjZjk4MDM3YTRmMzc1YmFhYzki.aLr9FQ.iCPDHCzEmKqBaHxZHls4uy9Q9Vo&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=138663&transportadora_id=&status=&data_inicio=&data_fim= HTTP/1.1" 200 59346 "https://sistema-fretes.onrender.com/fretes/listar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
10.214.158.26 - - [05/Sep/2025:15:09:20 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/fretes/listar?csrf_token=ImE5NWE5MGVkOGI0OTI5Y2Y2MDFiOGZjZjk4MDM3YTRmMzc1YmFhYzki.aLr9FQ.iCPDHCzEmKqBaHxZHls4uy9Q9Vo&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=138663&transportadora_id=&status=&data_inicio=&data_fim=" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:20,634 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:20 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
2025-09-05 15:09:20,637 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
15:09:20 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
10.214.255.103 - - [05/Sep/2025:15:09:20 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/fretes/listar?csrf_token=ImE5NWE5MGVkOGI0OTI5Y2Y2MDFiOGZjZjk4MDM3YTRmMzc1YmFhYzki.aLr9FQ.iCPDHCzEmKqBaHxZHls4uy9Q9Vo&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=138663&transportadora_id=&status=&data_inicio=&data_fim=" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
10.214.158.26 - - [05/Sep/2025:15:09:20 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/fretes/listar?csrf_token=ImE5NWE5MGVkOGI0OTI5Y2Y2MDFiOGZjZjk4MDM3YTRmMzc1YmFhYzki.aLr9FQ.iCPDHCzEmKqBaHxZHls4uy9Q9Vo&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=138663&transportadora_id=&status=&data_inicio=&data_fim=" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:23,682 - frete_sistema - INFO - 🌐 GET /fretes/2226/editar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /fretes/2226/editar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:23 | INFO     | frete_sistema | 🌐 GET /fretes/2226/editar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ GET /fretes/2226/editar | Status: 200 | Tempo: 0.055s
2025-09-05 15:09:23,736 - frete_sistema - INFO - ⏱️ GET /fretes/2226/editar | Status: 200 | Tempo: 0.055s
15:09:23 | INFO     | frete_sistema | ⏱️ GET /fretes/2226/editar | Status: 200 | Tempo: 0.055s
10.214.145.106 - - [05/Sep/2025:15:09:23 +0000] "GET /fretes/2226/editar HTTP/1.1" 200 58628 "https://sistema-fretes.onrender.com/fretes/listar?csrf_token=ImE5NWE5MGVkOGI0OTI5Y2Y2MDFiOGZjZjk4MDM3YTRmMzc1YmFhYzki.aLr9FQ.iCPDHCzEmKqBaHxZHls4uy9Q9Vo&embarque_numero=&cnpj_cliente=&nome_cliente=&numero_cte=&numero_fatura=&numero_nf=138663&transportadora_id=&status=&data_inicio=&data_fim=" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310341632
10.214.201.45 - - [05/Sep/2025:15:09:23 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/fretes/2226/editar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:24,248 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:24 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310338752
2025-09-05 15:09:24,261 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.013s
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.013s
15:09:24 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.013s
10.214.214.165 - - [05/Sep/2025:15:09:24 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/fretes/2226/editar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
10.214.214.165 - - [05/Sep/2025:15:09:24 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/fretes/2226/editar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:31,786 - frete_sistema - INFO - 🌐 GET /fretes/analise-diferencas/2226 | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /fretes/analise-diferencas/2226 | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:31 | INFO     | frete_sistema | 🌐 GET /fretes/analise-diferencas/2226 | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
============================================================
DEBUG - VALORES RECEBIDOS DA CALCULADORA:
INFO:frete_sistema:⏱️ GET /fretes/analise-diferencas/2226 | Status: 200 | Tempo: 0.060s
  peso_para_calculo: 26228.64
  frete_base: 0.0
  gris: 0
  adv: 302.03
  rca: 0
  pedagio: 0
  componentes_antes_minimo: 302.03
  frete_liquido_antes_minimo: 302.03
============================================================
2025-09-05 15:09:31,846 - frete_sistema - INFO - ⏱️ GET /fretes/analise-diferencas/2226 | Status: 200 | Tempo: 0.060s
15:09:31 | INFO     | frete_sistema | ⏱️ GET /fretes/analise-diferencas/2226 | Status: 200 | Tempo: 0.060s
10.214.237.162 - - [05/Sep/2025:15:09:31 +0000] "GET /fretes/analise-diferencas/2226 HTTP/1.1" 200 111268 "https://sistema-fretes.onrender.com/fretes/2226/editar" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
✅ [POOL] Tipos PostgreSQL registrados na conexão 127588310339072
10.214.158.26 - - [05/Sep/2025:15:09:32 +0000] "GET /static/style.css HTTP/1.1" 304 0 "https://sistema-fretes.onrender.com/fretes/analise-diferencas/2226" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
2025-09-05 15:09:32,619 - frete_sistema - INFO - 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
15:09:32 | INFO     | frete_sistema | 🌐 GET /claude-ai/api/health | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
2025-09-05 15:09:32,622 - frete_sistema - INFO - ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
15:09:32 | INFO     | frete_sistema | ⏱️ GET /claude-ai/api/health | Status: 200 | Tempo: 0.003s
10.214.201.45 - - [05/Sep/2025:15:09:32 +0000] "GET /claude-ai/api/health HTTP/1.1" 200 159 "https://sistema-fretes.onrender.com/fretes/analise-diferencas/2226" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
10.214.237.162 - - [05/Sep/2025:15:09:32 +0000] "GET /favicon.ico HTTP/1.1" 204 0 "https://sistema-fretes.onrender.com/fretes/analise-diferencas/2226" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]304sistema-fretes.onrender.com/static/style.cssclientIP="201.63.40.74" requestID="b3f4e876-64c7-410d" responseTimeMS=14 responseBytes=416 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/fretes/analise-diferencas/2226clientIP="201.63.40.74" requestID="96f21670-8caa-43f2" responseTimeMS=68 responseBytes=16057 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]200sistema-fretes.onrender.com/claude-ai/api/healthclientIP="201.63.40.74" requestID="85cf395a-2c8e-422b" responseTimeMS=7 responseBytes=507 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
     [GET]204sistema-fretes.onrender.com/favicon.icoclientIP="201.63.40.74" requestID="52ad9d1d-be84-4962" responseTimeMS=5 responseBytes=344 userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0