2025-09-03 12:10:32,721 - frete_sistema - INFO - 🌐 POST /odoo/sync-integrada/executar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:frete_sistema:🌐 POST /odoo/sync-integrada/executar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
12:10:32 | INFO     | frete_sistema | 🌐 POST /odoo/sync-integrada/executar | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
INFO:app.odoo.routes.sincronizacao_integrada:🚀 INICIANDO sincronização integrada segura (filtro carteira: True)
12:10:32 | INFO     | app.odoo.routes.sincronizacao_integrada | 🚀 INICIANDO sincronização integrada segura (filtro carteira: True)
INFO:app.odoo.services.sincronizacao_integrada_service:🚀 INICIANDO SINCRONIZAÇÃO INTEGRADA SEGURA (FATURAMENTO → CARTEIRA)
12:10:32 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🚀 INICIANDO SINCRONIZAÇÃO INTEGRADA SEGURA (FATURAMENTO → CARTEIRA)
INFO:app.odoo.services.sincronizacao_integrada_service:📊 ETAPA 1/3: Sincronizando FATURAMENTO (prioridade de segurança)...
12:10:32 | INFO     | app.odoo.services.sincronizacao_integrada_service | 📊 ETAPA 1/3: Sincronizando FATURAMENTO (prioridade de segurança)...
INFO:app.odoo.services.sincronizacao_integrada_service:📊 Executando sincronização completa de faturamento + estoque...
12:10:32 | INFO     | app.odoo.services.sincronizacao_integrada_service | 📊 Executando sincronização completa de faturamento + estoque...
INFO:app.odoo.services.faturamento_service:🚀 SINCRONIZAÇÃO INCREMENTAL + INTEGRAÇÃO COMPLETA
12:10:32 | INFO     | app.odoo.services.faturamento_service | 🚀 SINCRONIZAÇÃO INCREMENTAL + INTEGRAÇÃO COMPLETA
INFO:app.odoo.services.faturamento_service:🚀 Busca faturamento otimizada: filtro_postado=True, limite=0
12:10:32 | INFO     | app.odoo.services.faturamento_service | 🚀 Busca faturamento otimizada: filtro_postado=True, limite=0
INFO:app.odoo.services.faturamento_service:📋 Buscando linhas de faturamento...
12:10:32 | INFO     | app.odoo.services.faturamento_service | 📋 Buscando linhas de faturamento...
INFO:app.odoo.services.faturamento_service:🔄 Usando sincronização limitada...
12:10:32 | INFO     | app.odoo.services.faturamento_service | 🔄 Usando sincronização limitada...
INFO:app.odoo.utils.connection:✅ Conexão common estabelecida com Odoo
12:10:32 | INFO     | app.odoo.utils.connection | ✅ Conexão common estabelecida com Odoo
INFO:app.odoo.utils.connection:✅ Autenticado no Odoo com UID: 42
12:10:33 | INFO     | app.odoo.utils.connection | ✅ Autenticado no Odoo com UID: 42
INFO:app.odoo.utils.connection:✅ Conexão models estabelecida com Odoo
12:10:33 | INFO     | app.odoo.utils.connection | ✅ Conexão models estabelecida com Odoo
INFO:app.odoo.services.faturamento_service:📊 Total carregado: 20000 registros (limitado para performance)
12:10:39 | INFO     | app.odoo.services.faturamento_service | 📊 Total carregado: 20000 registros (limitado para performance)
12:10:39 | INFO     | app.odoo.services.faturamento_service | 🚀 Processando faturamento com método REALMENTE otimizado...
INFO:app.odoo.services.faturamento_service:🚀 Processando faturamento com método REALMENTE otimizado...
12:10:39 | INFO     | app.odoo.services.faturamento_service | 📊 Filtrando 20000 linhas brutas...
INFO:app.odoo.services.faturamento_service:📊 Filtrando 20000 linhas brutas...
INFO:app.odoo.services.faturamento_service:📈 Resultado filtragem: 1874 válidas, 18126 descartadas
12:10:39 | INFO     | app.odoo.services.faturamento_service | 📈 Resultado filtragem: 1874 válidas, 18126 descartadas
INFO:app.odoo.services.faturamento_service:📊 Coletados: 216 faturas, 178 clientes, 147 produtos
12:10:39 | INFO     | app.odoo.services.faturamento_service | 📊 Coletados: 216 faturas, 178 clientes, 147 produtos
INFO:app.odoo.services.faturamento_service:🔍 Query 1/6: Buscando faturas...
12:10:39 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 1/6: Buscando faturas...
INFO:app.odoo.services.faturamento_service:🔍 Query 2/6: Buscando 178 clientes...
12:10:41 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 2/6: Buscando 178 clientes...
12:10:41 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 3/6: Buscando 147 produtos...
INFO:app.odoo.services.faturamento_service:🔍 Query 3/6: Buscando 147 produtos...
INFO:app.odoo.services.faturamento_service:🔍 Query 4/6: Buscando 147 templates...
12:10:43 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 4/6: Buscando 147 templates...
12:10:43 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 5/6: Buscando 101 municípios...
INFO:app.odoo.services.faturamento_service:🔍 Query 5/6: Buscando 101 municípios...
INFO:app.odoo.services.faturamento_service:🔍 Query 6/6: Buscando 27 vendedores...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🔍 Query 6/6: Buscando 27 vendedores...
INFO:app.odoo.services.faturamento_service:🧠 Caches criados, fazendo JOIN em memória...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🧠 Caches criados, fazendo JOIN em memória...
INFO:app.odoo.services.faturamento_service:✅ OTIMIZAÇÃO FATURAMENTO COMPLETA:
12:10:44 | INFO     | app.odoo.services.faturamento_service | ✅ OTIMIZAÇÃO FATURAMENTO COMPLETA:
INFO:app.odoo.services.faturamento_service:   📊 1853 itens processados
12:10:44 | INFO     | app.odoo.services.faturamento_service |    📊 1853 itens processados
INFO:app.odoo.services.faturamento_service:   ⚡ 6 queries executadas (vs 340000 do método antigo)
12:10:44 | INFO     | app.odoo.services.faturamento_service |    ⚡ 6 queries executadas (vs 340000 do método antigo)
INFO:app.odoo.services.faturamento_service:   🚀 56666x mais rápido
12:10:44 | INFO     | app.odoo.services.faturamento_service |    🚀 56666x mais rápido
INFO:app.odoo.services.faturamento_service:📊 Processando 1853 registros do Odoo...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 📊 Processando 1853 registros do Odoo...
INFO:app.odoo.services.faturamento_service:🧹 Sanitizando dados de faturamento...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🧹 Sanitizando dados de faturamento...
INFO:app.odoo.services.faturamento_service:🔍 Carregando índice de registros existentes...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🔍 Carregando índice de registros existentes...
INFO:app.odoo.services.faturamento_service:📋 Índice criado com 11110 registros existentes
12:10:44 | INFO     | app.odoo.services.faturamento_service | 📋 Índice criado com 11110 registros existentes
INFO:app.odoo.services.faturamento_service:✅ Sincronização principal concluída: 1 novos, 0 atualizados
12:10:44 | INFO     | app.odoo.services.faturamento_service | ✅ Sincronização principal concluída: 1 novos, 0 atualizados
INFO:app.odoo.services.faturamento_service:🔍 Verificando consistência de NFs CANCELADAS...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🔍 Verificando consistência de NFs CANCELADAS...
INFO:app.odoo.services.faturamento_service:🔄 Iniciando consolidação para RelatorioFaturamentoImportado...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🔄 Iniciando consolidação para RelatorioFaturamentoImportado...
INFO:app.odoo.services.faturamento_service:Consolidando dados para RelatorioFaturamentoImportado
12:10:44 | INFO     | app.odoo.services.faturamento_service | Consolidando dados para RelatorioFaturamentoImportado
INFO:app.odoo.services.faturamento_service:Consolidação concluída: 1853 itens processados, 1 relatórios criados
12:10:44 | INFO     | app.odoo.services.faturamento_service | Consolidação concluída: 1853 itens processados, 1 relatórios criados
INFO:app.odoo.services.faturamento_service:✅ Consolidação concluída: 1 relatórios processados
12:10:44 | INFO     | app.odoo.services.faturamento_service | ✅ Consolidação concluída: 1 relatórios processados
INFO:app.odoo.services.faturamento_service:🏭 Iniciando processamento de movimentações de estoque...
12:10:44 | INFO     | app.odoo.services.faturamento_service | 🏭 Iniciando processamento de movimentações de estoque...
INFO:app.odoo.services.faturamento_service:📊 Processando 1 NFs específicas da sincronização
12:10:44 | INFO     | app.odoo.services.faturamento_service | 📊 Processando 1 NFs específicas da sincronização
INFO:app.faturamento.services.processar_faturamento:🧹 Limpando inconsistências anteriores...
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 🧹 Limpando inconsistências anteriores...
INFO:app.faturamento.services.processar_faturamento:✅ 79 inconsistências não resolvidas removidas antes do processamento
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | ✅ 79 inconsistências não resolvidas removidas antes do processamento
INFO:app.faturamento.services.processar_faturamento:🎯 Processando 1 NFs específicas...
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 🎯 Processando 1 NFs específicas...
INFO:app.faturamento.services.processar_faturamento:📊 Total de NFs para processar: 1
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 📊 Total de NFs para processar: 1
INFO:app.faturamento.services.processar_faturamento:📋 Processando NF 138995 - Pedido VCD2520818
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 📋 Processando NF 138995 - Pedido VCD2520818
INFO:app.faturamento.services.processar_faturamento:✅ Único EmbarqueItem encontrado - usando lote LOTE_20250814_182425_978
INFO:app.faturamento.services.processar_faturamento:📦 Processando NF 138995 com lote LOTE_20250814_182425_978
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | ✅ Único EmbarqueItem encontrado - usando lote LOTE_20250814_182425_978
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 📦 Processando NF 138995 com lote LOTE_20250814_182425_978
INFO:app.faturamento.services.processar_faturamento:✅ EmbarqueItem atualizado com NF 138995
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | ✅ EmbarqueItem atualizado com NF 138995
INFO:app.faturamento.services.processar_faturamento:✅ 1 Separações marcadas como sincronizadas
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | ✅ 1 Separações marcadas como sincronizadas
INFO:app.faturamento.services.processar_faturamento:📦 Criando 1 movimentações com lote LOTE_20250814_182425_978 para NF 138995
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 📦 Criando 1 movimentações com lote LOTE_20250814_182425_978 para NF 138995
INFO:app.faturamento.services.processar_faturamento:✅ 1 movimentações com lote preparadas para NF 138995
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | ✅ 1 movimentações com lote preparadas para NF 138995
INFO:app.faturamento.services.processar_faturamento:✅ 1 Separações atualizadas para status FATURADO
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | ✅ 1 Separações atualizadas para status FATURADO
INFO:app.faturamento.services.processar_faturamento:🔄 Atualizando status das separações para FATURADO...
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 🔄 Atualizando status das separações para FATURADO...
INFO:app.faturamento.services.processar_faturamento:📊 Encontradas 7 separações com NF mas sem status FATURADO
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 📊 Encontradas 7 separações com NF mas sem status FATURADO
INFO:app.faturamento.services.processar_faturamento:🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...
12:10:44 | INFO     | app.faturamento.services.processar_faturamento | 🔍 Verificando EmbarqueItems com NF para garantir Separações FATURADAS...
INFO:app.faturamento.services.processar_faturamento:✅ Total: 7 separações atualizadas para FATURADO
12:10:48 | INFO     | app.faturamento.services.processar_faturamento | ✅ Total: 7 separações atualizadas para FATURADO
INFO:app.faturamento.services.processar_faturamento:✅ 7 separações atualizadas para status FATURADO
12:10:49 | INFO     | app.faturamento.services.processar_faturamento | ✅ 7 separações atualizadas para status FATURADO
INFO:app.faturamento.services.processar_faturamento:✅ Processamento completo: 1 NFs processadas
12:10:49 | INFO     | app.faturamento.services.processar_faturamento | ✅ Processamento completo: 1 NFs processadas
12:10:49 | INFO     | app.faturamento.services.processar_faturamento | 📊 Movimentações criadas: 1
INFO:app.faturamento.services.processar_faturamento:📊 Movimentações criadas: 1
INFO:app.faturamento.services.processar_faturamento:📦 EmbarqueItems atualizados: 1
12:10:49 | INFO     | app.faturamento.services.processar_faturamento | 📦 EmbarqueItems atualizados: 1
INFO:app.odoo.services.faturamento_service:✅ Processamento de estoque concluído:
                    - NFs processadas: 1
                    - Já processadas: 0 
                    - Canceladas: 0
                    - Com embarque: 0
                    - Sem separação: 0
                    - Movimentações criadas: 1
                    - Embarques atualizados: 1
                    
12:10:49 | INFO     | app.odoo.services.faturamento_service | ✅ Processamento de estoque concluído:
                    - NFs processadas: 1
                    - Já processadas: 0 
                    - Canceladas: 0
                    - Com embarque: 0
                    - Sem separação: 0
                    - Movimentações criadas: 1
                    - Embarques atualizados: 1
                    
INFO:app.odoo.services.faturamento_service:🔄 Sincronizando entregas para 1 NFs...
12:10:49 | INFO     | app.odoo.services.faturamento_service | 🔄 Sincronizando entregas para 1 NFs...
INFO:app.odoo.services.faturamento_service:🔄 Re-validando embarques pendentes para 1 NFs novas...
12:10:49 | INFO     | app.odoo.services.faturamento_service | 🔄 Re-validando embarques pendentes para 1 NFs novas...
INFO:app.odoo.services.faturamento_service:🔄 Sincronizando NFs pendentes em embarques...
🔄 RE-VALIDANDO EMBARQUES PENDENTES após importação de 1 NFs
12:10:49 | INFO     | app.odoo.services.faturamento_service | 🔄 Sincronizando NFs pendentes em embarques...
INFO:app.odoo.services.faturamento_service:🔄 Processando lançamento automático de fretes para 177 CNPJs...
[DEBUG] 🔍 Buscando NFs de embarques que precisam ser sincronizadas...
[DEBUG] 📦 Total de NFs únicas em embarques ativos: 2256
[DEBUG] 📊 Total de NFs no monitoramento: 8947
[DEBUG] ⚠️ NFs pendentes de sincronização: 142
[DEBUG] 🎯 NFs em embarques COM faturamento que precisam sincronizar: 96
[DEBUG] 🔄 Sincronizando NF de embarque: 136063
[DEBUG] 🔄 Sincronizando NF de embarque: 138105
[DEBUG] 🔄 Sincronizando NF de embarque: 137795
[DEBUG] 🔄 Sincronizando NF de embarque: 136697
[DEBUG] 🔄 Sincronizando NF de embarque: 138838
[DEBUG] 🔄 Sincronizando NF de embarque: 136858
[DEBUG] 🔄 Sincronizando NF de embarque: 136704
[DEBUG] 🔄 Sincronizando NF de embarque: 137906
[DEBUG] 🔄 Sincronizando NF de embarque: 135970
[DEBUG] 🔄 Sincronizando NF de embarque: 136611
[DEBUG] 🔄 Sincronizando NF de embarque: 138475
[DEBUG] 🔄 Sincronizando NF de embarque: 137874
[DEBUG] 🔄 Sincronizando NF de embarque: 136067
[DEBUG] 🔄 Sincronizando NF de embarque: 136211
[DEBUG] 🔄 Sincronizando NF de embarque: 136788
[DEBUG] 🔄 Sincronizando NF de embarque: 136860
[DEBUG] 🔄 Sincronizando NF de embarque: 136530
[DEBUG] 🔄 Sincronizando NF de embarque: 136948
[DEBUG] 🔄 Sincronizando NF de embarque: 138282
[DEBUG] 🔄 Sincronizando NF de embarque: 137532
[DEBUG] 🔄 Sincronizando NF de embarque: 137900
[DEBUG] 🔄 Sincronizando NF de embarque: 136212
[DEBUG] 🔄 Sincronizando NF de embarque: 137844
[DEBUG] 🔄 Sincronizando NF de embarque: 138376
[DEBUG] 🔄 Sincronizando NF de embarque: 136605
[DEBUG] 🔄 Sincronizando NF de embarque: 138876
[DEBUG] 🔄 Sincronizando NF de embarque: 137063
[DEBUG] 🔄 Sincronizando NF de embarque: 138812
[DEBUG] 🔄 Sincronizando NF de embarque: 137257
[DEBUG] 🔄 Sincronizando NF de embarque: 137476
[DEBUG] 🔄 Sincronizando NF de embarque: 137525
[DEBUG] 🔄 Sincronizando NF de embarque: 137530
[DEBUG] 🔄 Sincronizando NF de embarque: 136855
[DEBUG] 🔄 Sincronizando NF de embarque: 138575
[DEBUG] 🔄 Sincronizando NF de embarque: 137787
[DEBUG] 🔄 Sincronizando NF de embarque: 136202
[DEBUG] 🔄 Sincronizando NF de embarque: 137698
[DEBUG] 🔄 Sincronizando NF de embarque: 137533
[DEBUG] 🔄 Sincronizando NF de embarque: 136489
[DEBUG] 🔄 Sincronizando NF de embarque: 137188
[DEBUG] 🔄 Sincronizando NF de embarque: 91937
[DEBUG] 🔄 Sincronizando NF de embarque: 138527
[DEBUG] 🔄 Sincronizando NF de embarque: 137784
[DEBUG] 🔄 Sincronizando NF de embarque: 138183
[DEBUG] 🔄 Sincronizando NF de embarque: 136279
[DEBUG] 🔄 Sincronizando NF de embarque: 138430
[DEBUG] 🔄 Sincronizando NF de embarque: 137793
[DEBUG] 🔄 Sincronizando NF de embarque: 138970
[DEBUG] 🔄 Sincronizando NF de embarque: 136203
[DEBUG] 🔄 Sincronizando NF de embarque: 136856
[DEBUG] 🔄 Sincronizando NF de embarque: 137838
[DEBUG] 🔄 Sincronizando NF de embarque: 136613
[DEBUG] 🔄 Sincronizando NF de embarque: 137788
[DEBUG] 🔄 Sincronizando NF de embarque: 137783
[DEBUG] 🔄 Sincronizando NF de embarque: 137534
[DEBUG] 🔄 Sincronizando NF de embarque: 138902
[DEBUG] 🔄 Sincronizando NF de embarque: 137873
[DEBUG] 🔄 Sincronizando NF de embarque: 137526
[DEBUG] 🔄 Sincronizando NF de embarque: 137881
[DEBUG] 🔄 Sincronizando NF de embarque: 138829
[DEBUG] 🔄 Sincronizando NF de embarque: 137666
[DEBUG] 🔄 Sincronizando NF de embarque: 136319
[DEBUG] 🔄 Sincronizando NF de embarque: 138811
[DEBUG] 🔄 Sincronizando NF de embarque: 136859
[DEBUG] 🔄 Sincronizando NF de embarque: 137049
[DEBUG] 🔄 Sincronizando NF de embarque: 136159
[DEBUG] 🔄 Sincronizando NF de embarque: 136278
[DEBUG] 🔄 Sincronizando NF de embarque: 138900
[DEBUG] 🔄 Sincronizando NF de embarque: 138766
[DEBUG] 🔄 Sincronizando NF de embarque: 137823
[DEBUG] 🔄 Sincronizando NF de embarque: 138903
[DEBUG] 🔄 Sincronizando NF de embarque: 138612
[DEBUG] 🔄 Sincronizando NF de embarque: 137083
[DEBUG] 🔄 Sincronizando NF de embarque: 137667
[DEBUG] 🔄 Sincronizando NF de embarque: 136059
[DEBUG] 🔄 Sincronizando NF de embarque: 137521
[DEBUG] 🔄 Sincronizando NF de embarque: 137828
[DEBUG] 🔄 Sincronizando NF de embarque: 138574
[DEBUG] 🔄 Sincronizando NF de embarque: 136857
[DEBUG] 🔄 Sincronizando NF de embarque: 136789
[DEBUG] 🔄 Sincronizando NF de embarque: 137529
[DEBUG] 🔄 Sincronizando NF de embarque: 135995
[DEBUG] 🔄 Sincronizando NF de embarque: 138630
[DEBUG] 🔄 Sincronizando NF de embarque: 138751
[DEBUG] 🔄 Sincronizando NF de embarque: 136099
[DEBUG] 🔄 Sincronizando NF de embarque: 136078
[DEBUG] 🔄 Sincronizando NF de embarque: 136640
[DEBUG] 🔄 Sincronizando NF de embarque: 138476
[DEBUG] 🔄 Sincronizando NF de embarque: 136068
[DEBUG] 🔄 Sincronizando NF de embarque: 138627
[DEBUG] 🔄 Sincronizando NF de embarque: 138283
[DEBUG] 🔄 Sincronizando NF de embarque: 137524
[DEBUG] 🔄 Sincronizando NF de embarque: 137026
[DEBUG] 🔄 Sincronizando NF de embarque: 137699
[DEBUG] 🔄 Sincronizando NF de embarque: 137027
[DEBUG] 🔄 Sincronizando NF de embarque: 136880
[DEBUG] ✅ Total de NFs de embarques sincronizadas: 96
12:10:49 | INFO     | app.odoo.services.faturamento_service | 🔄 Processando lançamento automático de fretes para 177 CNPJs...
INFO:app.odoo.services.faturamento_service:   ✅ SINCRONIZAÇÃO INCREMENTAL COMPLETA CONCLUÍDA:
INFO:app.odoo.services.faturamento_service:   ➕ 1 novos registros inseridos
✅ [POOL] Tipos PostgreSQL registrados na conexão 132263110052096
✅ [POOL] Tipos PostgreSQL registrados na conexão 132263279275968
12:10:55 | INFO     | app.odoo.services.faturamento_service |    ✅ SINCRONIZAÇÃO INCREMENTAL COMPLETA CONCLUÍDA:
12:10:55 | INFO     | app.odoo.services.faturamento_service |    ➕ 1 novos registros inseridos
INFO:app.odoo.services.faturamento_service:   ✏️ 0 registros atualizados
12:10:55 | INFO     | app.odoo.services.faturamento_service |    ✏️ 0 registros atualizados
INFO:app.odoo.services.faturamento_service:   📋 1 relatórios consolidados
12:10:55 | INFO     | app.odoo.services.faturamento_service |    📋 1 relatórios consolidados
INFO:app.odoo.services.faturamento_service:   🔄 1 entregas sincronizadas
12:10:55 | INFO     | app.odoo.services.faturamento_service |    🔄 1 entregas sincronizadas
INFO:app.odoo.services.faturamento_service:   📦 0 embarques re-validados
12:10:55 | INFO     | app.odoo.services.faturamento_service |    📦 0 embarques re-validados
INFO:app.odoo.services.faturamento_service:   🚚 96 NFs de embarques sincronizadas
INFO:app.odoo.services.faturamento_service:   💰 10 fretes lançados automaticamente
12:10:55 | INFO     | app.odoo.services.faturamento_service |    🚚 96 NFs de embarques sincronizadas
12:10:55 | INFO     | app.odoo.services.faturamento_service |    💰 10 fretes lançados automaticamente
INFO:app.odoo.services.faturamento_service:   ⏱️ Tempo execução: 22.90s
12:10:55 | INFO     | app.odoo.services.faturamento_service |    ⏱️ Tempo execução: 22.90s
INFO:app.odoo.services.faturamento_service:   ❌ 0 erros principais + 0 erros de sincronização
12:10:55 | INFO     | app.odoo.services.faturamento_service |    ❌ 0 erros principais + 0 erros de sincronização
INFO:app.odoo.services.sincronizacao_integrada_service:✅ Faturamento sincronizado: 1 registros, 1 movimentações de estoque
12:10:55 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ Faturamento sincronizado: 1 registros, 1 movimentações de estoque
INFO:app.odoo.services.sincronizacao_integrada_service:🔍 ETAPA 2/3: Validação de integridade pós-faturamento...
12:10:55 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔍 ETAPA 2/3: Validação de integridade pós-faturamento...
12:10:55 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔍 Validando integridade após sincronização de faturamento...
INFO:app.odoo.services.sincronizacao_integrada_service:🔍 Validando integridade após sincronização de faturamento...
INFO:app.odoo.services.sincronizacao_integrada_service:✅ 11111 registros de faturamento encontrados
12:10:55 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ 11111 registros de faturamento encontrados
INFO:app.odoo.services.sincronizacao_integrada_service:🔄 ETAPA 2.5/4: Atualizando status FATURADO dos pedidos...
12:10:55 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔄 ETAPA 2.5/4: Atualizando status FATURADO dos pedidos...
ERROR:app.odoo.services.sincronizacao_integrada_service:⚠️ Erro ao atualizar status FATURADO: 'ProcessadorFaturamento' object has no attribute '_atualizar_status_pedidos_faturados'
12:10:55 | ERROR    | app.odoo.services.sincronizacao_integrada_service | ⚠️ Erro ao atualizar status FATURADO: 'ProcessadorFaturamento' object has no attribute '_atualizar_status_pedidos_faturados'
INFO:app.odoo.services.sincronizacao_integrada_service:🔄 ETAPA 3/4: Sincronizando CARTEIRA (com faturamento protegido)...
12:10:55 | INFO     | app.odoo.services.sincronizacao_integrada_service | 🔄 ETAPA 3/4: Sincronizando CARTEIRA (com faturamento protegido)...
INFO:app.odoo.services.carteira_service:🚀 INICIANDO SINCRONIZAÇÃO OPERACIONAL COMPLETA COM GESTÃO INTELIGENTE
12:10:55 | INFO     | app.odoo.services.carteira_service | 🚀 INICIANDO SINCRONIZAÇÃO OPERACIONAL COMPLETA COM GESTÃO INTELIGENTE
INFO:app.odoo.services.carteira_service:📊 Fase 1: Analisando estado atual da carteira e calculando saldos...
12:10:55 | INFO     | app.odoo.services.carteira_service | 📊 Fase 1: Analisando estado atual da carteira e calculando saldos...
INFO:app.odoo.services.carteira_service:✅ 3501 registros Odoo indexados com saldos calculados
12:11:02 | INFO     | app.odoo.services.carteira_service | ✅ 3501 registros Odoo indexados com saldos calculados
INFO:app.odoo.services.carteira_service:🛡️ 0 registros não-Odoo protegidos
12:11:02 | INFO     | app.odoo.services.carteira_service | 🛡️ 0 registros não-Odoo protegidos
INFO:app.odoo.services.carteira_service:🔄 Fase 2: Buscando dados atualizados do Odoo...
12:11:02 | INFO     | app.odoo.services.carteira_service | 🔄 Fase 2: Buscando dados atualizados do Odoo...
INFO:app.odoo.services.carteira_service:Buscando carteira pendente do Odoo com filtro inteligente...
12:11:02 | INFO     | app.odoo.services.carteira_service | Buscando carteira pendente do Odoo com filtro inteligente...
INFO:app.odoo.services.carteira_service:📋 Coletando pedidos existentes na carteira para filtro...
12:11:02 | INFO     | app.odoo.services.carteira_service | 📋 Coletando pedidos existentes na carteira para filtro...
INFO:app.odoo.services.carteira_service:✅ 353 pedidos Odoo existentes serão incluídos no filtro
12:11:02 | INFO     | app.odoo.services.carteira_service | ✅ 353 pedidos Odoo existentes serão incluídos no filtro
INFO:app.odoo.services.carteira_service:🔍 Usando filtro combinado: (qty_saldo > 0) OU (pedidos existentes)
12:11:02 | INFO     | app.odoo.services.carteira_service | 🔍 Usando filtro combinado: (qty_saldo > 0) OU (pedidos existentes)
INFO:app.odoo.services.carteira_service:📡 Executando query no Odoo com filtro inteligente...
12:11:02 | INFO     | app.odoo.services.carteira_service | 📡 Executando query no Odoo com filtro inteligente...
INFO:app.odoo.utils.connection:✅ Conexão common estabelecida com Odoo
12:11:02 | INFO     | app.odoo.utils.connection | ✅ Conexão common estabelecida com Odoo
INFO:app.odoo.utils.connection:✅ Autenticado no Odoo com UID: 42
12:11:03 | INFO     | app.odoo.utils.connection | ✅ Autenticado no Odoo com UID: 42
INFO:app.odoo.utils.connection:✅ Conexão models estabelecida com Odoo
12:11:03 | INFO     | app.odoo.utils.connection | ✅ Conexão models estabelecida com Odoo
INFO:app.odoo.services.carteira_service:✅ SUCESSO: 4256 registros encontrados
INFO:app.odoo.services.carteira_service:🚀 Processando carteira com método REALMENTE otimizado...
12:11:06 | INFO     | app.odoo.services.carteira_service | ✅ SUCESSO: 4256 registros encontrados
12:11:06 | INFO     | app.odoo.services.carteira_service | 🚀 Processando carteira com método REALMENTE otimizado...
INFO:app.odoo.services.carteira_service:📊 Coletados: 354 pedidos, 185 produtos
12:11:06 | INFO     | app.odoo.services.carteira_service | 📊 Coletados: 354 pedidos, 185 produtos
INFO:app.odoo.services.carteira_service:🔍 Query 1/5: Buscando pedidos...
12:11:06 | INFO     | app.odoo.services.carteira_service | 🔍 Query 1/5: Buscando pedidos...
INFO:app.odoo.services.carteira_service:🔍 Query 2/5: Buscando 282 partners...
12:11:07 | INFO     | app.odoo.services.carteira_service | 🔍 Query 2/5: Buscando 282 partners...
INFO:app.odoo.services.carteira_service:🔍 Query 3/5: Buscando 185 produtos...
12:11:07 | INFO     | app.odoo.services.carteira_service | 🔍 Query 3/5: Buscando 185 produtos...
INFO:app.odoo.services.carteira_service:🔍 Query 4/5: Buscando 73 categorias...
12:11:08 | INFO     | app.odoo.services.carteira_service | 🔍 Query 4/5: Buscando 73 categorias...
INFO:app.odoo.services.carteira_service:🔍 Query 5/5: Buscando 21 categorias parent...
12:11:08 | INFO     | app.odoo.services.carteira_service | 🔍 Query 5/5: Buscando 21 categorias parent...
INFO:app.odoo.services.carteira_service:🧠 Caches criados, fazendo JOIN em memória...
12:11:08 | INFO     | app.odoo.services.carteira_service | 🧠 Caches criados, fazendo JOIN em memória...
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543298 é REDESPACHO - buscando endereço da transportadora 1006
12:11:08 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543298 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - ROD FERNAO DIAS
12:11:09 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): D2 LOGISTICA LTDA
12:11:09 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - ROD FERNAO DIAS
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543295 é REDESPACHO - buscando endereço da transportadora 1248
12:11:09 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543295 é REDESPACHO - buscando endereço da transportadora 1248
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): EXPRESSO RIO VERMELHO TRANSPORTES LTDA
12:11:09 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): EXPRESSO RIO VERMELHO TRANSPORTES LTDA
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - RUA NESTOR DE HOLANDA
12:11:09 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - RUA NESTOR DE HOLANDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
12:11:09 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
12:11:10 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): NETUS TRANSP LTDA ME
12:11:10 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO:  - False
12:11:10 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO:  - False
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:10 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
12:11:10 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
12:11:11 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:11 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
12:11:11 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:11 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:11 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
12:11:11 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543303 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:11 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:11 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:11 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:11 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:12 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:12 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:12 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:12 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:12 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:12 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:12 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:12 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:12 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:12 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:13 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
12:11:13 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543302 é REDESPACHO - buscando endereço da transportadora 1028
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
12:11:13 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): NETUS TRANSP LTDA ME
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543287 é REDESPACHO - buscando endereço da transportadora 1006
12:11:13 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543287 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:13 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543286 é REDESPACHO - buscando endereço da transportadora 1006
12:11:13 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543286 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:13 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:13 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - R BIRIGUI
12:11:14 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): EXPRESSO SANTA CLAUDIA
12:11:14 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - R BIRIGUI
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:14 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:14 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:14 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:14 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:14 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:14 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:14 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:14 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:14 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:15 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:15 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:15 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:15 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:15 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:15 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:15 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
12:11:15 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542804 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:15 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:15 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:16 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:16 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:16 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:16 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:16 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:16 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:16 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:16 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:16 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:16 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:17 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:17 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:17 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:17 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:17 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:17 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:17 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
12:11:17 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542803 é REDESPACHO - buscando endereço da transportadora 1070
12:11:17 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): EXPRESSO SANTA CLAUDIA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543235 é REDESPACHO - buscando endereço da transportadora 1006
12:11:17 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543235 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:18 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:18 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543237 é REDESPACHO - buscando endereço da transportadora 1020
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543237 é REDESPACHO - buscando endereço da transportadora 1020
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VOO TRANSPORTES
12:11:18 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VOO TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543124 é REDESPACHO - buscando endereço da transportadora 1014
12:11:18 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543124 é REDESPACHO - buscando endereço da transportadora 1014
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): EHC TRANSP E LOG EIRELI EPP
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO:  - False
12:11:18 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): EHC TRANSP E LOG EIRELI EPP
12:11:18 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO:  - False
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:18 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: São Paulo (SP) - R HEROIS DA F.E.B.
12:11:19 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): VIEIRA TRANSPORTES
12:11:19 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: São Paulo (SP) - R HEROIS DA F.E.B.
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:19 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:19 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:19 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:19 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:19 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:19 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:19 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:19 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:19 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:20 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
12:11:20 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543184 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:20 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
12:11:20 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - RUA BENEDITO CLIMERIO DE SANTANA
12:11:20 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:20 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - RUA BENEDITO CLIMERIO DE SANTANA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
12:11:20 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:20 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
12:11:20 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:21 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
12:11:21 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543155 é REDESPACHO - buscando endereço da transportadora 1186
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:21 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543111 é REDESPACHO - buscando endereço da transportadora 1006
12:11:21 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543111 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:21 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543110 é REDESPACHO - buscando endereço da transportadora 1006
12:11:21 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543110 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:21 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543109 é REDESPACHO - buscando endereço da transportadora 1006
12:11:21 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543109 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:22 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543073 é REDESPACHO - buscando endereço da transportadora 1044
12:11:22 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543073 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (query): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:22 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (query): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:   📍 Endereço REDESPACHO: Guarulhos (SP) - R ITAPE
12:11:22 | INFO     | app.odoo.services.carteira_service |    📍 Endereço REDESPACHO: Guarulhos (SP) - R ITAPE
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543073 é REDESPACHO - buscando endereço da transportadora 1044
12:11:22 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543073 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:22 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543073 é REDESPACHO - buscando endereço da transportadora 1044
12:11:22 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543073 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:22 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
12:11:22 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
12:11:23 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:23 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:23 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
12:11:23 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:23 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
12:11:23 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2543072 é REDESPACHO - buscando endereço da transportadora 1044
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
12:11:23 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): TOCANTINS TRANSPORTES E LOGISTICA LTDA-E
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
12:11:23 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:23 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
12:11:23 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
12:11:24 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
12:11:24 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542784 é REDESPACHO - buscando endereço da transportadora 1302
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): VIEIRA TRANSPORTES
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2542875 é REDESPACHO - buscando endereço da transportadora 1247
12:11:24 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2542875 é REDESPACHO - buscando endereço da transportadora 1247
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): ANDORINHA CARGAS
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): ANDORINHA CARGAS
INFO:app.odoo.services.carteira_service:🚛 Pedido VCD2521544 é REDESPACHO - buscando endereço da transportadora 1006
12:11:24 | INFO     | app.odoo.services.carteira_service | 🚛 Pedido VCD2521544 é REDESPACHO - buscando endereço da transportadora 1006
INFO:app.odoo.services.carteira_service:✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ Usando endereço da transportadora (cache): D2 LOGISTICA LTDA
INFO:app.odoo.services.carteira_service:✅ OTIMIZAÇÃO COMPLETA:
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ OTIMIZAÇÃO COMPLETA:
INFO:app.odoo.services.carteira_service:   📊 4256 itens processados
12:11:24 | INFO     | app.odoo.services.carteira_service |    📊 4256 itens processados
INFO:app.odoo.services.carteira_service:   ⚡ 5 queries executadas (vs 80864 do método antigo)
12:11:24 | INFO     | app.odoo.services.carteira_service |    ⚡ 5 queries executadas (vs 80864 do método antigo)
INFO:app.odoo.services.carteira_service:   🚀 16172x mais rápido
12:11:24 | INFO     | app.odoo.services.carteira_service |    🚀 16172x mais rápido
INFO:app.odoo.services.carteira_service:✅ 3508 registros obtidos do Odoo
12:11:24 | INFO     | app.odoo.services.carteira_service | ✅ 3508 registros obtidos do Odoo
INFO:app.odoo.services.carteira_service:🔍 Fase 3: Calculando saldos e identificando diferenças...
12:11:24 | INFO     | app.odoo.services.carteira_service | 🔍 Fase 3: Calculando saldos e identificando diferenças...
INFO:app.odoo.services.carteira_service:📊 Calculando saldos para itens importados do Odoo...
12:11:24 | INFO     | app.odoo.services.carteira_service | 📊 Calculando saldos para itens importados do Odoo...
WARNING:app.odoo.services.carteira_service:⚠️ Saldo negativo detectado: VCD2521039/4856125 = -40.00
12:11:25 | WARNING  | app.odoo.services.carteira_service | ⚠️ Saldo negativo detectado: VCD2521039/4856125 = -40.00
INFO:app.odoo.services.carteira_service:📊 Diferenças identificadas:
12:11:28 | INFO     | app.odoo.services.carteira_service | 📊 Diferenças identificadas:
INFO:app.odoo.services.carteira_service:   📉 2 reduções
12:11:28 | INFO     | app.odoo.services.carteira_service |    📉 2 reduções
INFO:app.odoo.services.carteira_service:   📈 0 aumentos
INFO:app.odoo.services.carteira_service:   ➕ 8 novos itens
12:11:28 | INFO     | app.odoo.services.carteira_service |    📈 0 aumentos
12:11:28 | INFO     | app.odoo.services.carteira_service |    ➕ 8 novos itens
INFO:app.odoo.services.carteira_service:   ➖ 1 itens removidos
12:11:28 | INFO     | app.odoo.services.carteira_service |    ➖ 1 itens removidos
WARNING:app.odoo.services.carteira_service:   ⚠️ 1 itens com saldo negativo (NF devolvida?)
12:11:28 | WARNING  | app.odoo.services.carteira_service |    ⚠️ 1 itens com saldo negativo (NF devolvida?)
INFO:app.odoo.services.carteira_service:📦 Fase 3.2: Garantindo CadastroPalletizacao para todos os produtos...
12:11:28 | INFO     | app.odoo.services.carteira_service | 📦 Fase 3.2: Garantindo CadastroPalletizacao para todos os produtos...
INFO:app.odoo.services.carteira_service:📦 Iniciando garantia de CadastroPalletizacao para 3508 registros
12:11:28 | INFO     | app.odoo.services.carteira_service | 📦 Iniciando garantia de CadastroPalletizacao para 3508 registros
INFO:app.odoo.services.carteira_service:📊 169 produtos únicos identificados
12:11:28 | INFO     | app.odoo.services.carteira_service | 📊 169 produtos únicos identificados
INFO:app.odoo.services.carteira_service:✅ Cadastros de palletização salvos com sucesso
12:11:28 | INFO     | app.odoo.services.carteira_service | ✅ Cadastros de palletização salvos com sucesso
INFO:app.odoo.services.carteira_service:✅ CadastroPalletizacao garantido:
12:11:28 | INFO     | app.odoo.services.carteira_service | ✅ CadastroPalletizacao garantido:
INFO:app.odoo.services.carteira_service:   - 0 produtos criados
12:11:28 | INFO     | app.odoo.services.carteira_service |    - 0 produtos criados
INFO:app.odoo.services.carteira_service:   - 111 produtos atualizados
12:11:28 | INFO     | app.odoo.services.carteira_service |    - 111 produtos atualizados
INFO:app.odoo.services.carteira_service:   - 58 já existentes
12:11:28 | INFO     | app.odoo.services.carteira_service |    - 58 já existentes
WARNING:app.odoo.services.carteira_service:🛡️ PROTEÇÃO: Pedido VCD2520818 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
12:11:28 | WARNING  | app.odoo.services.carteira_service | 🛡️ PROTEÇÃO: Pedido VCD2520818 removido mas NÃO será processado (todas as separações já sincronizadas/faturadas)
INFO:app.odoo.services.carteira_service:📦 Processando pedido alterado: VCD2543243
12:11:28 | INFO     | app.odoo.services.carteira_service | 📦 Processando pedido alterado: VCD2543243
INFO:app.odoo.services.ajuste_sincronizacao_service:🔄 Processando pedido alterado: VCD2543243
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 🔄 Processando pedido alterado: VCD2543243
INFO:app.odoo.services.ajuste_sincronizacao_service:Encontrada Separacao com lote LOTE_20250901_122936_036 (status: ABERTO, sincronizado_nf: False)
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Encontrada Separacao com lote LOTE_20250901_122936_036 (status: ABERTO, sincronizado_nf: False)
INFO:app.odoo.services.ajuste_sincronizacao_service:Total de 1 lotes para processar
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Total de 1 lotes para processar
INFO:app.odoo.services.ajuste_sincronizacao_service:📋 Processando pedido VCD2543243 com 1 lotes:
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 📋 Processando pedido VCD2543243 com 1 lotes:
INFO:app.odoo.services.ajuste_sincronizacao_service:   - Lote LOTE_20250901_122936_036 status ABERTO
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service |    - Lote LOTE_20250901_122936_036 status ABERTO
INFO:app.odoo.services.ajuste_sincronizacao_service:Processando lote LOTE_20250901_122936_036 (status: ABERTO)
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Processando lote LOTE_20250901_122936_036 (status: ABERTO)
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Processando SUBSTITUIÇÃO TOTAL do lote LOTE_20250901_122936_036
INFO:app.odoo.services.ajuste_sincronizacao_service:Processando SUBSTITUIÇÃO TOTAL do lote LOTE_20250901_122936_036
INFO:app.odoo.services.ajuste_sincronizacao_service:🗑️ Removidos itens antigos do lote LOTE_20250901_122936_036
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 🗑️ Removidos itens antigos do lote LOTE_20250901_122936_036
INFO:app.odoo.services.ajuste_sincronizacao_service:➕ Adicionado 4230162 com qtd 7.0
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | ➕ Adicionado 4230162 com qtd 7.0
INFO:app.odoo.services.ajuste_sincronizacao_service:➕ Adicionado 4320162 com qtd 10.0
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | ➕ Adicionado 4320162 com qtd 10.0
INFO:app.odoo.services.ajuste_sincronizacao_service:➕ Adicionado 4070162 com qtd 7.0
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | ➕ Adicionado 4070162 com qtd 7.0
ERROR:app.odoo.services.ajuste_sincronizacao_service:❌ Erro ao commitar alterações: (psycopg2.errors.NotNullViolation) null value in column "cod_uf" of relation "separacao" violates not-null constraint
DETAIL:  Failing row contains (18615, LOTE_20250901_122936_036, VCD2543243, null, 49.534.045/0001-35, META DISTRIBUIDORA, null, null, 4230162, AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO, 7, 2581.25, null, null, null, null, null, null, null, null, , 2025-09-03 12:11:28.45102, total, f, f, null, null, f, null, null, ABERTO, f, null, null, null, null, f, null, null, null).
[SQL: INSERT INTO separacao (separacao_lote_id, num_pedido, data_pedido, cnpj_cpf, raz_social_red, nome_cidade, cod_uf, cod_produto, nome_produto, qtd_saldo, valor_saldo, pallet, peso, rota, sub_rota, observ_ped_1, roteirizacao, expedicao, agendamento, age ... 3537 characters truncated ...  p35, p36, p37, p38, sen_counter) ORDER BY sen_counter RETURNING separacao.id, separacao.id AS id__1]
[parameters: {'cnpj_cpf__0': '49.534.045/0001-35', 'data_sincronizacao__0': None, 'cotacao_id__0': None, 'cod_produto__0': '4230162', 'criado_em__0': datetime.datetime(2025, 9, 3, 12, 11, 28, 451020), 'cidade_normalizada__0': None, 'cod_uf__0': None, 'separacao_impressa_por__0': None, 'uf_normalizada__0': None, 'zerado_por_sync__0': False, 'observ_ped_1__0': None, 'peso__0': None, 'roteirizacao__0': None, 'agendamento_confirmado__0': False, 'data_zeragem__0': None, 'raz_social_red__0': 'META DISTRIBUIDORA', 'sincronizado_nf__0': False, 'separacao_lote_id__0': 'LOTE_20250901_122936_036', 'data_embarque__0': None, 'agendamento__0': None, 'tipo_envio__0': 'total', 'num_pedido__0': 'VCD2543243', 'rota__0': None, 'numero_nf__0': None, 'nf_cd__0': False, 'separacao_impressa__0': False, 'qtd_saldo__0': 7.0, 'separacao_impressa_em__0': None, 'nome_produto__0': 'AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO', 'pedido_cliente__0': None, 'status__0': 'ABERTO', 'codigo_ibge__0': None, 'pallet__0': None, 'data_pedido__0': None, 'nome_cidade__0': None, 'protocolo__0': '', 'expedicao__0': None, 'valor_saldo__0': 2581.25, 'sub_rota__0': None, 'cnpj_cpf__1': '49.534.045/0001-35', 'data_sincronizacao__1': None, 'cotacao_id__1': None, 'cod_produto__1': '4320162', 'criado_em__1': datetime.datetime(2025, 9, 3, 12, 11, 28, 451021), 'cidade_normalizada__1': None, 'cod_uf__1': None, 'separacao_impressa_por__1': None, 'uf_normalizada__1': None, 'zerado_por_sync__1': False, 'observ_ped_1__1': None ... 17 parameters truncated ... 'nome_produto__1': 'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO', 'pedido_cliente__1': None, 'status__1': 'ABERTO', 'codigo_ibge__1': None, 'pallet__1': None, 'data_pedido__1': None, 'nome_cidade__1': None, 'protocolo__1': '', 'expedicao__1': None, 'valor_saldo__1': 2875.4, 'sub_rota__1': None, 'cnpj_cpf__2': '49.534.045/0001-35', 'data_sincronizacao__2': None, 'cotacao_id__2': None, 'cod_produto__2': '4070162', 'criado_em__2': datetime.datetime(2025, 9, 3, 12, 11, 28, 451022), 'cidade_normalizada__2': None, 'cod_uf__2': None, 'separacao_impressa_por__2': None, 'uf_normalizada__2': None, 'zerado_por_sync__2': False, 'observ_ped_1__2': None, 'peso__2': None, 'roteirizacao__2': None, 'agendamento_confirmado__2': False, 'data_zeragem__2': None, 'raz_social_red__2': 'META DISTRIBUIDORA', 'sincronizado_nf__2': False, 'separacao_lote_id__2': 'LOTE_20250901_122936_036', 'data_embarque__2': None, 'agendamento__2': None, 'tipo_envio__2': 'total', 'num_pedido__2': 'VCD2543243', 'rota__2': None, 'numero_nf__2': None, 'nf_cd__2': False, 'separacao_impressa__2': False, 'qtd_saldo__2': 7.0, 'separacao_impressa_em__2': None, 'nome_produto__2': 'PIMENTA BIQUINHO - BD 6X2 KG - CAMPO BELO', 'pedido_cliente__2': None, 'status__2': 'ABERTO', 'codigo_ibge__2': None, 'pallet__2': None, 'data_pedido__2': None, 'nome_cidade__2': None, 'protocolo__2': '', 'expedicao__2': None, 'valor_saldo__2': 2375.52, 'sub_rota__2': None}]
(Background on this error at: https://sqlalche.me/e/20/gkpj)
12:11:28 | ERROR    | app.odoo.services.ajuste_sincronizacao_service | ❌ Erro ao commitar alterações: (psycopg2.errors.NotNullViolation) null value in column "cod_uf" of relation "separacao" violates not-null constraint
DETAIL:  Failing row contains (18615, LOTE_20250901_122936_036, VCD2543243, null, 49.534.045/0001-35, META DISTRIBUIDORA, null, null, 4230162, AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO, 7, 2581.25, null, null, null, null, null, null, null, null, , 2025-09-03 12:11:28.45102, total, f, f, null, null, f, null, null, ABERTO, f, null, null, null, null, f, null, null, null).
[SQL: INSERT INTO separacao (separacao_lote_id, num_pedido, data_pedido, cnpj_cpf, raz_social_red, nome_cidade, cod_uf, cod_produto, nome_produto, qtd_saldo, valor_saldo, pallet, peso, rota, sub_rota, observ_ped_1, roteirizacao, expedicao, agendamento, age ... 3537 characters truncated ...  p35, p36, p37, p38, sen_counter) ORDER BY sen_counter RETURNING separacao.id, separacao.id AS id__1]
[parameters: {'cnpj_cpf__0': '49.534.045/0001-35', 'data_sincronizacao__0': None, 'cotacao_id__0': None, 'cod_produto__0': '4230162', 'criado_em__0': datetime.datetime(2025, 9, 3, 12, 11, 28, 451020), 'cidade_normalizada__0': None, 'cod_uf__0': None, 'separacao_impressa_por__0': None, 'uf_normalizada__0': None, 'zerado_por_sync__0': False, 'observ_ped_1__0': None, 'peso__0': None, 'roteirizacao__0': None, 'agendamento_confirmado__0': False, 'data_zeragem__0': None, 'raz_social_red__0': 'META DISTRIBUIDORA', 'sincronizado_nf__0': False, 'separacao_lote_id__0': 'LOTE_20250901_122936_036', 'data_embarque__0': None, 'agendamento__0': None, 'tipo_envio__0': 'total', 'num_pedido__0': 'VCD2543243', 'rota__0': None, 'numero_nf__0': None, 'nf_cd__0': False, 'separacao_impressa__0': False, 'qtd_saldo__0': 7.0, 'separacao_impressa_em__0': None, 'nome_produto__0': 'AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO', 'pedido_cliente__0': None, 'status__0': 'ABERTO', 'codigo_ibge__0': None, 'pallet__0': None, 'data_pedido__0': None, 'nome_cidade__0': None, 'protocolo__0': '', 'expedicao__0': None, 'valor_saldo__0': 2581.25, 'sub_rota__0': None, 'cnpj_cpf__1': '49.534.045/0001-35', 'data_sincronizacao__1': None, 'cotacao_id__1': None, 'cod_produto__1': '4320162', 'criado_em__1': datetime.datetime(2025, 9, 3, 12, 11, 28, 451021), 'cidade_normalizada__1': None, 'cod_uf__1': None, 'separacao_impressa_por__1': None, 'uf_normalizada__1': None, 'zerado_por_sync__1': False, 'observ_ped_1__1': None ... 17 parameters truncated ... 'nome_produto__1': 'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO', 'pedido_cliente__1': None, 'status__1': 'ABERTO', 'codigo_ibge__1': None, 'pallet__1': None, 'data_pedido__1': None, 'nome_cidade__1': None, 'protocolo__1': '', 'expedicao__1': None, 'valor_saldo__1': 2875.4, 'sub_rota__1': None, 'cnpj_cpf__2': '49.534.045/0001-35', 'data_sincronizacao__2': None, 'cotacao_id__2': None, 'cod_produto__2': '4070162', 'criado_em__2': datetime.datetime(2025, 9, 3, 12, 11, 28, 451022), 'cidade_normalizada__2': None, 'cod_uf__2': None, 'separacao_impressa_por__2': None, 'uf_normalizada__2': None, 'zerado_por_sync__2': False, 'observ_ped_1__2': None, 'peso__2': None, 'roteirizacao__2': None, 'agendamento_confirmado__2': False, 'data_zeragem__2': None, 'raz_social_red__2': 'META DISTRIBUIDORA', 'sincronizado_nf__2': False, 'separacao_lote_id__2': 'LOTE_20250901_122936_036', 'data_embarque__2': None, 'agendamento__2': None, 'tipo_envio__2': 'total', 'num_pedido__2': 'VCD2543243', 'rota__2': None, 'numero_nf__2': None, 'nf_cd__2': False, 'separacao_impressa__2': False, 'qtd_saldo__2': 7.0, 'separacao_impressa_em__2': None, 'nome_produto__2': 'PIMENTA BIQUINHO - BD 6X2 KG - CAMPO BELO', 'pedido_cliente__2': None, 'status__2': 'ABERTO', 'codigo_ibge__2': None, 'pallet__2': None, 'data_pedido__2': None, 'nome_cidade__2': None, 'protocolo__2': '', 'expedicao__2': None, 'valor_saldo__2': 2375.52, 'sub_rota__2': None}]
(Background on this error at: https://sqlalche.me/e/20/gkpj)
ERROR:app.odoo.services.carteira_service:❌ Erro ao processar pedido VCD2543243: ['Erro ao salvar: (psycopg2.errors.NotNullViolation) null value in column "cod_uf" of relation "separacao" violates not-null constraint\nDETAIL:  Failing row contains (18615, LOTE_20250901_122936_036, VCD2543243, null, 49.534.045/0001-35, META DISTRIBUIDORA, null, null, 4230162, AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO, 7, 2581.25, null, null, null, null, null, null, null, null, , 2025-09-03 12:11:28.45102, total, f, f, null, null, f, null, null, ABERTO, f, null, null, null, null, f, null, null, null).\n\n[SQL: INSERT INTO separacao (separacao_lote_id, num_pedido, data_pedido, cnpj_cpf, raz_social_red, nome_cidade, cod_uf, cod_produto, nome_produto, qtd_saldo, valor_saldo, pallet, peso, rota, sub_rota, observ_ped_1, roteirizacao, expedicao, agendamento, age ... 3537 characters truncated ...  p35, p36, p37, p38, sen_counter) ORDER BY sen_counter RETURNING separacao.id, separacao.id AS id__1]\n[parameters: {\'cnpj_cpf__0\': \'49.534.045/0001-35\', \'data_sincronizacao__0\': None, \'cotacao_id__0\': None, \'cod_produto__0\': \'4230162\', \'criado_em__0\': datetime.datetime(2025, 9, 3, 12, 11, 28, 451020), \'cidade_normalizada__0\': None, \'cod_uf__0\': None, \'separacao_impressa_por__0\': None, \'uf_normalizada__0\': None, \'zerado_por_sync__0\': False, \'observ_ped_1__0\': None, \'peso__0\': None, \'roteirizacao__0\': None, \'agendamento_confirmado__0\': False, \'data_zeragem__0\': None, \'raz_social_red__0\': \'META DISTRIBUIDORA\', \'sincronizado_nf__0\': False, \'separacao_lote_id__0\': \'LOTE_20250901_122936_036\', \'data_embarque__0\': None, \'agendamento__0\': None, \'tipo_envio__0\': \'total\', \'num_pedido__0\': \'VCD2543243\', \'rota__0\': None, \'numero_nf__0\': None, \'nf_cd__0\': False, \'separacao_impressa__0\': False, \'qtd_saldo__0\': 7.0, \'separacao_impressa_em__0\': None, \'nome_produto__0\': \'AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO\', \'pedido_cliente__0\': None, \'status__0\': \'ABERTO\', \'codigo_ibge__0\': None, \'pallet__0\': None, \'data_pedido__0\': None, \'nome_cidade__0\': None, \'protocolo__0\': \'\', \'expedicao__0\': None, \'valor_saldo__0\': 2581.25, \'sub_rota__0\': None, \'cnpj_cpf__1\': \'49.534.045/0001-35\', \'data_sincronizacao__1\': None, \'cotacao_id__1\': None, \'cod_produto__1\': \'4320162\', \'criado_em__1\': datetime.datetime(2025, 9, 3, 12, 11, 28, 451021), \'cidade_normalizada__1\': None, \'cod_uf__1\': None, \'separacao_impressa_por__1\': None, \'uf_normalizada__1\': None, \'zerado_por_sync__1\': False, \'observ_ped_1__1\': None ... 17 parameters truncated ... \'nome_produto__1\': \'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO\', \'pedido_cliente__1\': None, \'status__1\': \'ABERTO\', \'codigo_ibge__1\': None, \'pallet__1\': None, \'data_pedido__1\': None, \'nome_cidade__1\': None, \'protocolo__1\': \'\', \'expedicao__1\': None, \'valor_saldo__1\': 2875.4, \'sub_rota__1\': None, \'cnpj_cpf__2\': \'49.534.045/0001-35\', \'data_sincronizacao__2\': None, \'cotacao_id__2\': None, \'cod_produto__2\': \'4070162\', \'criado_em__2\': datetime.datetime(2025, 9, 3, 12, 11, 28, 451022), \'cidade_normalizada__2\': None, \'cod_uf__2\': None, \'separacao_impressa_por__2\': None, \'uf_normalizada__2\': None, \'zerado_por_sync__2\': False, \'observ_ped_1__2\': None, \'peso__2\': None, \'roteirizacao__2\': None, \'agendamento_confirmado__2\': False, \'data_zeragem__2\': None, \'raz_social_red__2\': \'META DISTRIBUIDORA\', \'sincronizado_nf__2\': False, \'separacao_lote_id__2\': \'LOTE_20250901_122936_036\', \'data_embarque__2\': None, \'agendamento__2\': None, \'tipo_envio__2\': \'total\', \'num_pedido__2\': \'VCD2543243\', \'rota__2\': None, \'numero_nf__2\': None, \'nf_cd__2\': False, \'separacao_impressa__2\': False, \'qtd_saldo__2\': 7.0, \'separacao_impressa_em__2\': None, \'nome_produto__2\': \'PIMENTA BIQUINHO - BD 6X2 KG - CAMPO BELO\', \'pedido_cliente__2\': None, \'status__2\': \'ABERTO\', \'codigo_ibge__2\': None, \'pallet__2\': None, \'data_pedido__2\': None, \'nome_cidade__2\': None, \'protocolo__2\': \'\', \'expedicao__2\': None, \'valor_saldo__2\': 2375.52, \'sub_rota__2\': None}]\n(Background on this error at: https://sqlalche.me/e/20/gkpj)']
12:11:28 | ERROR    | app.odoo.services.carteira_service | ❌ Erro ao processar pedido VCD2543243: ['Erro ao salvar: (psycopg2.errors.NotNullViolation) null value in column "cod_uf" of relation "separacao" violates not-null constraint\nDETAIL:  Failing row contains (18615, LOTE_20250901_122936_036, VCD2543243, null, 49.534.045/0001-35, META DISTRIBUIDORA, null, null, 4230162, AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO, 7, 2581.25, null, null, null, null, null, null, null, null, , 2025-09-03 12:11:28.45102, total, f, f, null, null, f, null, null, ABERTO, f, null, null, null, null, f, null, null, null).\n\n[SQL: INSERT INTO separacao (separacao_lote_id, num_pedido, data_pedido, cnpj_cpf, raz_social_red, nome_cidade, cod_uf, cod_produto, nome_produto, qtd_saldo, valor_saldo, pallet, peso, rota, sub_rota, observ_ped_1, roteirizacao, expedicao, agendamento, age ... 3537 characters truncated ...  p35, p36, p37, p38, sen_counter) ORDER BY sen_counter RETURNING separacao.id, separacao.id AS id__1]\n[parameters: {\'cnpj_cpf__0\': \'49.534.045/0001-35\', \'data_sincronizacao__0\': None, \'cotacao_id__0\': None, \'cod_produto__0\': \'4230162\', \'criado_em__0\': datetime.datetime(2025, 9, 3, 12, 11, 28, 451020), \'cidade_normalizada__0\': None, \'cod_uf__0\': None, \'separacao_impressa_por__0\': None, \'uf_normalizada__0\': None, \'zerado_por_sync__0\': False, \'observ_ped_1__0\': None, \'peso__0\': None, \'roteirizacao__0\': None, \'agendamento_confirmado__0\': False, \'data_zeragem__0\': None, \'raz_social_red__0\': \'META DISTRIBUIDORA\', \'sincronizado_nf__0\': False, \'separacao_lote_id__0\': \'LOTE_20250901_122936_036\', \'data_embarque__0\': None, \'agendamento__0\': None, \'tipo_envio__0\': \'total\', \'num_pedido__0\': \'VCD2543243\', \'rota__0\': None, \'numero_nf__0\': None, \'nf_cd__0\': False, \'separacao_impressa__0\': False, \'qtd_saldo__0\': 7.0, \'separacao_impressa_em__0\': None, \'nome_produto__0\': \'AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO\', \'pedido_cliente__0\': None, \'status__0\': \'ABERTO\', \'codigo_ibge__0\': None, \'pallet__0\': None, \'data_pedido__0\': None, \'nome_cidade__0\': None, \'protocolo__0\': \'\', \'expedicao__0\': None, \'valor_saldo__0\': 2581.25, \'sub_rota__0\': None, \'cnpj_cpf__1\': \'49.534.045/0001-35\', \'data_sincronizacao__1\': None, \'cotacao_id__1\': None, \'cod_produto__1\': \'4320162\', \'criado_em__1\': datetime.datetime(2025, 9, 3, 12, 11, 28, 451021), \'cidade_normalizada__1\': None, \'cod_uf__1\': None, \'separacao_impressa_por__1\': None, \'uf_normalizada__1\': None, \'zerado_por_sync__1\': False, \'observ_ped_1__1\': None ... 17 parameters truncated ... \'nome_produto__1\': \'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO\', \'pedido_cliente__1\': None, \'status__1\': \'ABERTO\', \'codigo_ibge__1\': None, \'pallet__1\': None, \'data_pedido__1\': None, \'nome_cidade__1\': None, \'protocolo__1\': \'\', \'expedicao__1\': None, \'valor_saldo__1\': 2875.4, \'sub_rota__1\': None, \'cnpj_cpf__2\': \'49.534.045/0001-35\', \'data_sincronizacao__2\': None, \'cotacao_id__2\': None, \'cod_produto__2\': \'4070162\', \'criado_em__2\': datetime.datetime(2025, 9, 3, 12, 11, 28, 451022), \'cidade_normalizada__2\': None, \'cod_uf__2\': None, \'separacao_impressa_por__2\': None, \'uf_normalizada__2\': None, \'zerado_por_sync__2\': False, \'observ_ped_1__2\': None, \'peso__2\': None, \'roteirizacao__2\': None, \'agendamento_confirmado__2\': False, \'data_zeragem__2\': None, \'raz_social_red__2\': \'META DISTRIBUIDORA\', \'sincronizado_nf__2\': False, \'separacao_lote_id__2\': \'LOTE_20250901_122936_036\', \'data_embarque__2\': None, \'agendamento__2\': None, \'tipo_envio__2\': \'total\', \'num_pedido__2\': \'VCD2543243\', \'rota__2\': None, \'numero_nf__2\': None, \'nf_cd__2\': False, \'separacao_impressa__2\': False, \'qtd_saldo__2\': 7.0, \'separacao_impressa_em__2\': None, \'nome_produto__2\': \'PIMENTA BIQUINHO - BD 6X2 KG - CAMPO BELO\', \'pedido_cliente__2\': None, \'status__2\': \'ABERTO\', \'codigo_ibge__2\': None, \'pallet__2\': None, \'data_pedido__2\': None, \'nome_cidade__2\': None, \'protocolo__2\': \'\', \'expedicao__2\': None, \'valor_saldo__2\': 2375.52, \'sub_rota__2\': None}]\n(Background on this error at: https://sqlalche.me/e/20/gkpj)']
INFO:app.odoo.services.carteira_service:📦 Processando pedido alterado: VCD2543307
12:11:28 | INFO     | app.odoo.services.carteira_service | 📦 Processando pedido alterado: VCD2543307
INFO:app.odoo.services.ajuste_sincronizacao_service:🔄 Processando pedido alterado: VCD2543307
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | 🔄 Processando pedido alterado: VCD2543307
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2543307 não tem separações alteráveis
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2543307 não tem separações alteráveis
INFO:app.odoo.services.ajuste_sincronizacao_service:Pedido VCD2543307 não tem separações alteráveis
12:11:28 | INFO     | app.odoo.services.ajuste_sincronizacao_service | Pedido VCD2543307 não tem separações alteráveis
INFO:app.odoo.services.carteira_service:✅ Pedido VCD2543307 processado: SEM_SEPARACAO
12:11:28 | INFO     | app.odoo.services.carteira_service | ✅ Pedido VCD2543307 processado: SEM_SEPARACAO
INFO:app.odoo.services.carteira_service:💾 Fase 7: Atualizando carteira principal...
12:11:28 | INFO     | app.odoo.services.carteira_service | 💾 Fase 7: Atualizando carteira principal...
INFO:app.odoo.services.carteira_service:🧹 Sanitizando dados...
12:11:28 | INFO     | app.odoo.services.carteira_service | 🧹 Sanitizando dados...
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 112633404011263340496626362402
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 112633404011263340496626362402
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 62 para 50 caracteres: (07.353.826/0002-64) EXPRESSO SANTA CLAUDIA  ASDA SILVA TRANSP
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 58 para 50 caracteres: 07.655.407/0002-87(EXPRESSO RIO VERMELHO TRANSPORTES LTDA)
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 53 para 50 caracteres: (08.192.055/0002-33) REIS TRANSP E MUDANCAS LTDA  EPP
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 53 para 50 caracteres: (08.192.055/0002-33) REIS TRANSP E MUDANCAS LTDA  EPP
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 70 para 50 caracteres: (03.301.398/0002-75) PANAMERICANO TRANSPORTE RODOVIARIO DE CARGAS LTDA
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 30 para 20 caracteres: 623207424562326414831176908903
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 6635731887 6696729898
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 9821083547 9821083535
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (07.784.847/0008-20) TOCANTINS TRANSP E LOG LTDA  ME
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 31 para 20 caracteres: +55 13 3203-3132 (13) 3203-3132
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 31 para 20 caracteres: +55 13 3203-3132 (13) 3203-3132
WARNING:app.odoo.services.carteira_service:Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo metodo_entrega_pedido truncado de 52 para 50 caracteres: (06.237.779/0001-40)JOAQUIM MARIO VIEIRA TRANSPORTES
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 22 para 20 caracteres: 43 3317-7100 RAMAL 274
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 22 para 20 caracteres: 43 3317-7100 RAMAL 274
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 4733412600 4733412601
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 4733412600 4733412601
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 4733412600 4733412601
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 4733412600 4733412601
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 4733412600 4733412601
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 4733412600 4733412601
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 23 para 20 caracteres: 11-21480450 11-21480455
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
WARNING:app.odoo.services.carteira_service:Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
12:11:28 | WARNING  | app.odoo.services.carteira_service | Campo telefone_endereco_ent truncado de 21 para 20 caracteres: 5133025955 5133025959
INFO:app.odoo.services.carteira_service:🔍 Tratando duplicatas dos dados do Odoo...
12:11:28 | INFO     | app.odoo.services.carteira_service | 🔍 Tratando duplicatas dos dados do Odoo...
INFO:app.odoo.services.carteira_service:🛡️ Preservando 0 registros não-Odoo...
12:11:28 | INFO     | app.odoo.services.carteira_service | 🛡️ Preservando 0 registros não-Odoo...
INFO:app.odoo.services.carteira_service:🔄 Usando estratégia UPSERT para evitar erros de chave duplicada...
12:11:28 | INFO     | app.odoo.services.carteira_service | 🔄 Usando estratégia UPSERT para evitar erros de chave duplicada...
INFO:app.odoo.services.carteira_service:📊 3501 registros Odoo existentes encontrados
12:11:28 | INFO     | app.odoo.services.carteira_service | 📊 3501 registros Odoo existentes encontrados
INFO:app.odoo.services.carteira_service:🗑️ 1 registros Odoo obsoletos removidos
12:11:28 | INFO     | app.odoo.services.carteira_service | 🗑️ 1 registros Odoo obsoletos removidos
INFO:app.odoo.services.carteira_service:🔄 Processando 3508 registros em lotes de 10...
12:11:28 | INFO     | app.odoo.services.carteira_service | 🔄 Processando 3508 registros em lotes de 10...
INFO:app.odoo.services.carteira_service:✅ 8 novos registros inseridos
12:11:49 | INFO     | app.odoo.services.carteira_service | ✅ 8 novos registros inseridos
INFO:app.odoo.services.carteira_service:🔄 3500 registros atualizados
12:11:49 | INFO     | app.odoo.services.carteira_service | 🔄 3500 registros atualizados
INFO:app.odoo.services.carteira_service:💾 Fase 8: Todas as alterações já salvas incrementalmente
12:11:49 | INFO     | app.odoo.services.carteira_service | 💾 Fase 8: Todas as alterações já salvas incrementalmente
INFO:app.odoo.services.carteira_service:🔄 Fase 9: Atualizando dados de Separação/Pedido...
12:11:49 | INFO     | app.odoo.services.carteira_service | 🔄 Fase 9: Atualizando dados de Separação/Pedido...
INFO:app.carteira.services.atualizar_dados_service:🔄 Iniciando atualização de dados baseado na CarteiraPrincipal...
12:11:49 | INFO     | app.carteira.services.atualizar_dados_service | 🔄 Iniciando atualização de dados baseado na CarteiraPrincipal...
INFO:app.carteira.services.atualizar_dados_service:📋 Encontrados 2113 pedidos com separações não sincronizadas
12:11:49 | INFO     | app.carteira.services.atualizar_dados_service | 📋 Encontrados 2113 pedidos com separações não sincronizadas
INFO:app.carteira.services.atualizar_dados_service:✅ Alterações salvas no banco de dados
12:12:00 | INFO     | app.carteira.services.atualizar_dados_service | ✅ Alterações salvas no banco de dados
INFO:app.carteira.services.atualizar_dados_service:
                ✅ ATUALIZAÇÃO DE DADOS CONCLUÍDA:
                - Pedidos processados: 140
                - Separações atualizadas: 46
                - Erros encontrados: 0
            
12:12:00 | INFO     | app.carteira.services.atualizar_dados_service | 
                ✅ ATUALIZAÇÃO DE DADOS CONCLUÍDA:
                - Pedidos processados: 140
                - Separações atualizadas: 46
                - Erros encontrados: 0
            
INFO:app.odoo.services.carteira_service:✅ Dados atualizados: 140 pedidos, 46 separações
12:12:00 | INFO     | app.odoo.services.carteira_service | ✅ Dados atualizados: 140 pedidos, 46 separações
INFO:app.odoo.services.carteira_service:🔍 Fase 10: Verificação pós-sincronização...
12:12:00 | INFO     | app.odoo.services.carteira_service | 🔍 Fase 10: Verificação pós-sincronização...
INFO:app.odoo.services.carteira_service:🔍 Verificando impactos pós-sincronização...
12:12:00 | INFO     | app.odoo.services.carteira_service | 🔍 Verificando impactos pós-sincronização...
WARNING:app.odoo.services.carteira_service:🚨 70 alertas críticos pós-sincronização detectados
12:12:05 | WARNING  | app.odoo.services.carteira_service | 🚨 70 alertas críticos pós-sincronização detectados
INFO:app.odoo.services.carteira_service:🧹 Fase 10.5: Limpeza de SaldoStandby...
12:12:05 | INFO     | app.odoo.services.carteira_service | 🧹 Fase 10.5: Limpeza de SaldoStandby...
INFO:app.odoo.services.carteira_service:   ✅ Nenhum registro para remover de SaldoStandby
12:12:05 | INFO     | app.odoo.services.carteira_service |    ✅ Nenhum registro para remover de SaldoStandby
INFO:app.odoo.services.carteira_service:📞 Fase 10.6: Verificação de Contatos de Agendamento...
12:12:05 | INFO     | app.odoo.services.carteira_service | 📞 Fase 10.6: Verificação de Contatos de Agendamento...
INFO:app.odoo.services.carteira_service:   ✅ Todos os contatos de agendamento já estão configurados corretamente
12:12:05 | INFO     | app.odoo.services.carteira_service |    ✅ Todos os contatos de agendamento já estão configurados corretamente
INFO:app.odoo.services.carteira_service:📝 Fase 10.7: Atualizando forma de agendamento na carteira...
12:12:05 | INFO     | app.odoo.services.carteira_service | 📝 Fase 10.7: Atualizando forma de agendamento na carteira...
INFO:app.odoo.services.carteira_service:   ✅ 8 registros atualizados com forma de agendamento
12:12:05 | INFO     | app.odoo.services.carteira_service |    ✅ 8 registros atualizados com forma de agendamento
INFO:app.odoo.services.carteira_service:✅ SINCRONIZAÇÃO OPERACIONAL COMPLETA CONCLUÍDA:
12:12:05 | INFO     | app.odoo.services.carteira_service | ✅ SINCRONIZAÇÃO OPERACIONAL COMPLETA CONCLUÍDA:
INFO:app.odoo.services.carteira_service:   📊 8 registros inseridos
12:12:05 | INFO     | app.odoo.services.carteira_service |    📊 8 registros inseridos
INFO:app.odoo.services.carteira_service:   🔄 3500 registros atualizados
12:12:05 | INFO     | app.odoo.services.carteira_service |    🔄 3500 registros atualizados
INFO:app.odoo.services.carteira_service:   🗑️ 1 registros Odoo removidos
12:12:05 | INFO     | app.odoo.services.carteira_service |    🗑️ 1 registros Odoo removidos
INFO:app.odoo.services.carteira_service:   🛡️ 0 registros não-Odoo preservados
12:12:05 | INFO     | app.odoo.services.carteira_service |    🛡️ 0 registros não-Odoo preservados
INFO:app.odoo.services.carteira_service:   📉 0 reduções aplicadas
12:12:05 | INFO     | app.odoo.services.carteira_service |    📉 0 reduções aplicadas
INFO:app.odoo.services.carteira_service:   📈 0 aumentos aplicados
12:12:05 | INFO     | app.odoo.services.carteira_service |    📈 0 aumentos aplicados
INFO:app.odoo.services.carteira_service:   ➖ 0 remoções processadas
12:12:05 | INFO     | app.odoo.services.carteira_service |    ➖ 0 remoções processadas
INFO:app.odoo.services.carteira_service:   ➕ 8 novos itens
12:12:05 | INFO     | app.odoo.services.carteira_service |    ➕ 8 novos itens
INFO:app.odoo.services.carteira_service:   🚨 70 alertas pós-sincronização
12:12:05 | INFO     | app.odoo.services.carteira_service |    🚨 70 alertas pós-sincronização
INFO:app.odoo.services.carteira_service:   ⏱️ 70.13 segundos de execução
12:12:05 | INFO     | app.odoo.services.carteira_service |    ⏱️ 70.13 segundos de execução
INFO:app.odoo.services.sincronizacao_integrada_service:✅ SINCRONIZAÇÃO INTEGRADA CONCLUÍDA COM SUCESSO em 93.1s
12:12:05 | INFO     | app.odoo.services.sincronizacao_integrada_service | ✅ SINCRONIZAÇÃO INTEGRADA CONCLUÍDA COM SUCESSO em 93.1s
INFO:frete_sistema:⏱️ POST /odoo/sync-integrada/executar | Status: 302 | Tempo: 93.068s
2025-09-03 12:12:05,789 - frete_sistema - INFO - ⏱️ POST /odoo/sync-integrada/executar | Status: 302 | Tempo: 93.068s
12:12:05 | INFO     | frete_sistema | ⏱️ POST /odoo/sync-integrada/executar | Status: 302 | Tempo: 93.068s
2025-09-03 12:12:05,789 - frete_sistema - WARNING - 🐌 REQUISIÇÃO LENTA: /odoo/sync-integrada/executar em 93.068s
WARNING:frete_sistema:🐌 REQUISIÇÃO LENTA: /odoo/sync-integrada/executar em 93.068s
12:12:05 | WARNING  | frete_sistema | 🐌 REQUISIÇÃO LENTA: /odoo/sync-integrada/executar em 93.068s
10.214.214.162 - - [03/Sep/2025:12:12:05 +0000] "POST /odoo/sync-integrada/executar HTTP/1.1" 302 229 "https://sistema-fretes.onrender.com/odoo/sync-integrada/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"