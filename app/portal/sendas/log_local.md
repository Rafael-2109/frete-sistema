2025-09-10 11:41:36,051 - frete_sistema - INFO - 🌐 POST /carteira/programacao-lote/api/processar-agendamento-sendas | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
[2025-09-10 11:41:36,070] INFO in routes: 📅 Processando 2 CNPJs com datas válidas
2025-09-10 11:41:36,070 - app.carteira.routes.programacao_em_lote.routes - INFO - 📅 Processando 2 CNPJs com datas válidas
[2025-09-10 11:41:36,071] INFO in routes: 📥 Baixando planilha modelo do portal Sendas...
2025-09-10 11:41:36,071 - app.carteira.routes.programacao_em_lote.routes - INFO - 📥 Baixando planilha modelo do portal Sendas...
[2025-09-10 11:41:36,071] INFO in consumir_agendas: 💻 Ambiente de desenvolvimento - headless=False
2025-09-10 11:41:36,071 - app.portal.sendas.consumir_agendas - INFO - 💻 Ambiente de desenvolvimento - headless=False
[2025-09-10 11:41:36,071] INFO in sendas_playwright: Portal Sendas inicializado - Headless: False
2025-09-10 11:41:36,071 - app.portal.sendas.sendas_playwright - INFO - Portal Sendas inicializado - Headless: False
[2025-09-10 11:41:36,071] INFO in sendas_playwright: Usuário configurado: danielle.vieira@nacomgoya.com.br
2025-09-10 11:41:36,071 - app.portal.sendas.sendas_playwright - INFO - Usuário configurado: danielle.vieira@nacomgoya.com.br
[2025-09-10 11:41:36,071] INFO in sendas_playwright: Diretório de downloads: /home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/downloads
2025-09-10 11:41:36,071 - app.portal.sendas.sendas_playwright - INFO - Diretório de downloads: /home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/downloads
[2025-09-10 11:41:36,071] INFO in consumir_agendas: 📁 Diretório de downloads: /home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/downloads/20250910
2025-09-10 11:41:36,071 - app.portal.sendas.consumir_agendas - INFO - 📁 Diretório de downloads: /home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/downloads/20250910
[2025-09-10 11:41:36,071] INFO in consumir_agendas: 🚀 Executando download em processo separado...
2025-09-10 11:41:36,071 - app.portal.sendas.consumir_agendas - INFO - 🚀 Executando download em processo separado...
[2025-09-10 11:42:36,666] INFO in consumir_agendas: ✅ Download concluído: /home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/downloads/20250910/sendas_agendamentos_20250910_114236_planilha-modelo.xlsx
2025-09-10 11:42:36,666 - app.portal.sendas.consumir_agendas - INFO - ✅ Download concluído: /home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/downloads/20250910/sendas_agendamentos_20250910_114236_planilha-modelo.xlsx
[2025-09-10 11:42:36,666] INFO in routes: 📝 Preenchendo planilha com 2 CNPJs...
2025-09-10 11:42:36,666 - app.carteira.routes.programacao_em_lote.routes - INFO - 📝 Preenchendo planilha com 2 CNPJs...
[2025-09-10 11:42:36,667] INFO in preencher_planilha: 
================================================================================
2025-09-10 11:42:36,667 - app.portal.sendas.preencher_planilha - INFO - 
================================================================================
[2025-09-10 11:42:36,667] INFO in preencher_planilha: 🔄 PROCESSAMENTO DE MÚLTIPLOS CNPJs - PORTAL SENDAS
2025-09-10 11:42:36,667 - app.portal.sendas.preencher_planilha - INFO - 🔄 PROCESSAMENTO DE MÚLTIPLOS CNPJs - PORTAL SENDAS
[2025-09-10 11:42:36,667] INFO in preencher_planilha: ================================================================================
2025-09-10 11:42:36,667 - app.portal.sendas.preencher_planilha - INFO - ================================================================================
[2025-09-10 11:42:36,667] INFO in preencher_planilha: 📋 Total de CNPJs a processar: 2
2025-09-10 11:42:36,667 - app.portal.sendas.preencher_planilha - INFO - 📋 Total de CNPJs a processar: 2
[2025-09-10 11:42:36,872] INFO in preencher_planilha: 
  [1/2] Coletando dados do CNPJ: 06.057.223/0294-04
2025-09-10 11:42:36,872 - app.portal.sendas.preencher_planilha - INFO - 
  [1/2] Coletando dados do CNPJ: 06.057.223/0294-04
[2025-09-10 11:42:36,873] INFO in preencher_planilha: 📊 Buscando dados para CNPJ: 06.057.223/0294-04
2025-09-10 11:42:36,873 - app.portal.sendas.preencher_planilha - INFO - 📊 Buscando dados para CNPJ: 06.057.223/0294-04
[2025-09-10 11:42:36,873] INFO in preencher_planilha:   📦 Buscando em CarteiraPrincipal...
2025-09-10 11:42:36,873 - app.portal.sendas.preencher_planilha - INFO -   📦 Buscando em CarteiraPrincipal...
[2025-09-10 11:42:36,874] WARNING in preencher_planilha:   ⚠️ Conexão SSL perdida, reconectando...
2025-09-10 11:42:36,874 - app.portal.sendas.preencher_planilha - WARNING -   ⚠️ Conexão SSL perdida, reconectando...
✅ [POOL] Tipos PostgreSQL registrados na conexão 132267238812352
[2025-09-10 11:42:36,881] INFO in preencher_planilha:   ✅ Reconexão bem-sucedida
2025-09-10 11:42:36,881 - app.portal.sendas.preencher_planilha - INFO -   ✅ Reconexão bem-sucedida
[2025-09-10 11:42:36,881] INFO in preencher_planilha:     Encontrados 2 pedidos
2025-09-10 11:42:36,881 - app.portal.sendas.preencher_planilha - INFO -     Encontrados 2 pedidos
✅ [POOL] Tipos PostgreSQL registrados na conexão 132267122245312
[2025-09-10 11:42:36,892] INFO in preencher_planilha:   📋 Buscando em Separacao...
2025-09-10 11:42:36,892 - app.portal.sendas.preencher_planilha - INFO -   📋 Buscando em Separacao...
[2025-09-10 11:42:36,895] INFO in preencher_planilha:     Encontradas 0 separações
2025-09-10 11:42:36,895 - app.portal.sendas.preencher_planilha - INFO -     Encontradas 0 separações
[2025-09-10 11:42:36,896] INFO in preencher_planilha:   📄 Buscando NFs no CD...
2025-09-10 11:42:36,896 - app.portal.sendas.preencher_planilha - INFO -   📄 Buscando NFs no CD...
[2025-09-10 11:42:36,897] INFO in preencher_planilha:     Encontradas 0 NFs no CD
2025-09-10 11:42:36,897 - app.portal.sendas.preencher_planilha - INFO -     Encontradas 0 NFs no CD
[2025-09-10 11:42:36,897] INFO in preencher_planilha:   ✅ Total: 8 itens, Peso: 418.98 kg
2025-09-10 11:42:36,897 - app.portal.sendas.preencher_planilha - INFO -   ✅ Total: 8 itens, Peso: 418.98 kg
[2025-09-10 11:42:36,898] INFO in preencher_planilha: 
  [2/2] Coletando dados do CNPJ: 06.057.223/0339-32
2025-09-10 11:42:36,898 - app.portal.sendas.preencher_planilha - INFO - 
  [2/2] Coletando dados do CNPJ: 06.057.223/0339-32
[2025-09-10 11:42:36,898] INFO in preencher_planilha: 📊 Buscando dados para CNPJ: 06.057.223/0339-32
2025-09-10 11:42:36,898 - app.portal.sendas.preencher_planilha - INFO - 📊 Buscando dados para CNPJ: 06.057.223/0339-32
[2025-09-10 11:42:36,899] INFO in preencher_planilha:   📦 Buscando em CarteiraPrincipal...
2025-09-10 11:42:36,899 - app.portal.sendas.preencher_planilha - INFO -   📦 Buscando em CarteiraPrincipal...
[2025-09-10 11:42:36,900] INFO in preencher_planilha:     Encontrados 2 pedidos
2025-09-10 11:42:36,900 - app.portal.sendas.preencher_planilha - INFO -     Encontrados 2 pedidos
[2025-09-10 11:42:36,907] INFO in preencher_planilha:   📋 Buscando em Separacao...
2025-09-10 11:42:36,907 - app.portal.sendas.preencher_planilha - INFO -   📋 Buscando em Separacao...
[2025-09-10 11:42:36,909] INFO in preencher_planilha:     Encontradas 4 separações
2025-09-10 11:42:36,909 - app.portal.sendas.preencher_planilha - INFO -     Encontradas 4 separações
[2025-09-10 11:42:36,911] INFO in preencher_planilha:   📄 Buscando NFs no CD...
2025-09-10 11:42:36,911 - app.portal.sendas.preencher_planilha - INFO -   📄 Buscando NFs no CD...
[2025-09-10 11:42:36,912] INFO in preencher_planilha:     Encontradas 0 NFs no CD
2025-09-10 11:42:36,912 - app.portal.sendas.preencher_planilha - INFO -     Encontradas 0 NFs no CD
[2025-09-10 11:42:36,912] INFO in preencher_planilha:   ✅ Total: 20 itens, Peso: 1317.85 kg
2025-09-10 11:42:36,912 - app.portal.sendas.preencher_planilha - INFO -   ✅ Total: 20 itens, Peso: 1317.85 kg
[2025-09-10 11:42:36,913] INFO in preencher_planilha: 
📝 Preenchendo planilha com 2 CNPJs...
2025-09-10 11:42:36,913 - app.portal.sendas.preencher_planilha - INFO - 
📝 Preenchendo planilha com 2 CNPJs...
[2025-09-10 11:42:36,913] INFO in preencher_planilha:   📌 Processando CNPJ 06.057.223/0294-04 - Filial: 059 PRAIA GRANDE SHOP
2025-09-10 11:42:36,913 - app.portal.sendas.preencher_planilha - INFO -   📌 Processando CNPJ 06.057.223/0294-04 - Filial: 059 PRAIA GRANDE SHOP
[2025-09-10 11:42:37,045] INFO in preencher_planilha:   📌 Processando CNPJ 06.057.223/0339-32 - Filial: 104 PRAIA GRANDE GLORIA
2025-09-10 11:42:37,045 - app.portal.sendas.preencher_planilha - INFO -   📌 Processando CNPJ 06.057.223/0339-32 - Filial: 104 PRAIA GRANDE GLORIA
[2025-09-10 11:42:37,066] INFO in preencher_planilha:   ✅ 24 linhas preenchidas no total
2025-09-10 11:42:37,066 - app.portal.sendas.preencher_planilha - INFO -   ✅ 24 linhas preenchidas no total
[2025-09-10 11:42:37,066] INFO in preencher_planilha: 
🗑️ Removendo linhas não agendadas...
2025-09-10 11:42:37,066 - app.portal.sendas.preencher_planilha - INFO - 
🗑️ Removendo linhas não agendadas...
[2025-09-10 11:42:37,153] INFO in preencher_planilha:   🗑️ 14973 linhas removidas (não agendadas)
2025-09-10 11:42:37,153 - app.portal.sendas.preencher_planilha - INFO -   🗑️ 14973 linhas removidas (não agendadas)
[2025-09-10 11:42:37,153] INFO in preencher_planilha:   ✅ 24 linhas mantidas (agendadas)
2025-09-10 11:42:37,153 - app.portal.sendas.preencher_planilha - INFO -   ✅ 24 linhas mantidas (agendadas)
[2025-09-10 11:42:37,161] INFO in preencher_planilha: 
💾 Planilha salva: /tmp/sendas_multi_20250910_114237.xlsx
2025-09-10 11:42:37,161 - app.portal.sendas.preencher_planilha - INFO - 
💾 Planilha salva: /tmp/sendas_multi_20250910_114237.xlsx
[2025-09-10 11:42:37,161] INFO in preencher_planilha: 
================================================================================
2025-09-10 11:42:37,161 - app.portal.sendas.preencher_planilha - INFO - 
================================================================================
[2025-09-10 11:42:37,161] INFO in preencher_planilha: 📊 RESUMO DO PROCESSAMENTO MÚLTIPLO:
2025-09-10 11:42:37,161 - app.portal.sendas.preencher_planilha - INFO - 📊 RESUMO DO PROCESSAMENTO MÚLTIPLO:
[2025-09-10 11:42:37,162] INFO in preencher_planilha: ================================================================================
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO - ================================================================================
[2025-09-10 11:42:37,162] INFO in preencher_planilha:   CNPJs processados: 2
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO -   CNPJs processados: 2
[2025-09-10 11:42:37,162] INFO in preencher_planilha:   Linhas preenchidas: 24
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO -   Linhas preenchidas: 24
[2025-09-10 11:42:37,162] INFO in preencher_planilha:   Linhas removidas: 14973
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO -   Linhas removidas: 14973
[2025-09-10 11:42:37,162] INFO in preencher_planilha:   Peso total geral: 1736.83 kg
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO -   Peso total geral: 1736.83 kg
[2025-09-10 11:42:37,162] INFO in preencher_planilha:   Tipo caminhão: Caminhão VUC 3/4
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO -   Tipo caminhão: Caminhão VUC 3/4
[2025-09-10 11:42:37,162] INFO in preencher_planilha:   Observação: AG_MULTI_20250910_114236
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO -   Observação: AG_MULTI_20250910_114236
[2025-09-10 11:42:37,162] INFO in preencher_planilha: ================================================================================
2025-09-10 11:42:37,162 - app.portal.sendas.preencher_planilha - INFO - ================================================================================
[2025-09-10 11:42:37,162] INFO in routes: 📤 Fazendo upload da planilha no portal Sendas...
2025-09-10 11:42:37,162 - app.carteira.routes.programacao_em_lote.routes - INFO - 📤 Fazendo upload da planilha no portal Sendas...
[2025-09-10 11:42:37,162] INFO in consumir_agendas: 🚀 Executando upload em processo separado: /tmp/sendas_multi_20250910_114237.xlsx
2025-09-10 11:42:37,162 - app.portal.sendas.consumir_agendas - INFO - 🚀 Executando upload em processo separado: /tmp/sendas_multi_20250910_114237.xlsx
[2025-09-10 11:43:39,850] INFO in consumir_agendas: ✅ Upload concluído com sucesso
2025-09-10 11:43:39,850 - app.portal.sendas.consumir_agendas - INFO - ✅ Upload concluído com sucesso
[2025-09-10 11:43:39,851] INFO in routes: 🗂️ Gerando separações para todos os CNPJs...
2025-09-10 11:43:39,851 - app.carteira.routes.programacao_em_lote.routes - INFO - 🗂️ Gerando separações para todos os CNPJs...
[2025-09-10 11:43:39,851] INFO in routes:   Processando separações para CNPJ 06.057.223/0294-04
2025-09-10 11:43:39,851 - app.carteira.routes.programacao_em_lote.routes - INFO -   Processando separações para CNPJ 06.057.223/0294-04
[2025-09-10 11:43:39,853] WARNING in routes:   ⚠️ Erro na conexão do banco para CNPJ 06.057.223/0294-04: (psycopg2.OperationalError) SSL connection has been closed unexpectedly

[SQL: SELECT carteira_principal.id AS carteira_principal_id, carteira_principal.num_pedido AS carteira_principal_num_pedido, carteira_principal.cod_produto AS carteira_principal_cod_produto, carteira_principal.pedido_cliente AS carteira_principal_pedido_cliente, carteira_principal.data_pedido AS carteira_principal_data_pedido, carteira_principal.data_atual_pedido AS carteira_principal_data_atual_pedido, carteira_principal.status_pedido AS carteira_principal_status_pedido, carteira_principal.cnpj_cpf AS carteira_principal_cnpj_cpf, carteira_principal.raz_social AS carteira_principal_raz_social, carteira_principal.raz_social_red AS carteira_principal_raz_social_red, carteira_principal.municipio AS carteira_principal_municipio, carteira_principal.estado AS carteira_principal_estado, carteira_principal.vendedor AS carteira_principal_vendedor, carteira_principal.equipe_vendas AS carteira_principal_equipe_vendas, carteira_principal.nome_produto AS carteira_principal_nome_produto, carteira_principal.unid_medida_produto AS carteira_principal_unid_medida_produto, carteira_principal.embalagem_produto AS carteira_principal_embalagem_produto, carteira_principal.materia_prima_produto AS carteira_principal_materia_prima_produto, carteira_principal.categoria_produto AS carteira_principal_categoria_produto, carteira_principal.qtd_produto_pedido AS carteira_principal_qtd_produto_pedido, carteira_principal.qtd_saldo_produto_pedido AS carteira_principal_qtd_saldo_produto_pedido, carteira_principal.qtd_cancelada_produto_pedido AS carteira_principal_qtd_cancelada_produto_pedido, carteira_principal.preco_produto_pedido AS carteira_principal_preco_produto_pedido, carteira_principal.cond_pgto_pedido AS carteira_principal_cond_pgto_pedido, carteira_principal.forma_pgto_pedido AS carteira_principal_forma_pgto_pedido, carteira_principal.incoterm AS carteira_principal_incoterm, carteira_principal.metodo_entrega_pedido AS carteira_principal_metodo_entrega_pedido, carteira_principal.data_entrega_pedido AS carteira_principal_data_entrega_pedido, carteira_principal.cliente_nec_agendamento AS carteira_principal_cliente_nec_agendamento, carteira_principal.observ_ped_1 AS carteira_principal_observ_ped_1, carteira_principal.cnpj_endereco_ent AS carteira_principal_cnpj_endereco_ent, carteira_principal.empresa_endereco_ent AS carteira_principal_empresa_endereco_ent, carteira_principal.cep_endereco_ent AS carteira_principal_cep_endereco_ent, carteira_principal.nome_cidade AS carteira_principal_nome_cidade, carteira_principal.cod_uf AS carteira_principal_cod_uf, carteira_principal.bairro_endereco_ent AS carteira_principal_bairro_endereco_ent, carteira_principal.rua_endereco_ent AS carteira_principal_rua_endereco_ent, carteira_principal.endereco_ent AS carteira_principal_endereco_ent, carteira_principal.telefone_endereco_ent AS carteira_principal_telefone_endereco_ent, carteira_principal.expedicao AS carteira_principal_expedicao, carteira_principal.data_entrega AS carteira_principal_data_entrega, carteira_principal.agendamento AS carteira_principal_agendamento, carteira_principal.hora_agendamento AS carteira_principal_hora_agendamento, carteira_principal.protocolo AS carteira_principal_protocolo, carteira_principal.agendamento_confirmado AS carteira_principal_agendamento_confirmado, carteira_principal.roteirizacao AS carteira_principal_roteirizacao, carteira_principal.menor_estoque_produto_d7 AS carteira_principal_menor_estoque_produto_d7, carteira_principal.saldo_estoque_pedido AS carteira_principal_saldo_estoque_pedido, carteira_principal.saldo_estoque_pedido_forcado AS carteira_principal_saldo_estoque_pedido_forcado, carteira_principal.separacao_lote_id AS carteira_principal_separacao_lote_id, carteira_principal.qtd_saldo AS carteira_principal_qtd_saldo, carteira_principal.valor_saldo AS carteira_principal_valor_saldo, carteira_principal.pallet AS carteira_principal_pallet, carteira_principal.peso AS carteira_principal_peso, carteira_principal.rota AS carteira_principal_rota, carteira_principal.sub_rota AS carteira_principal_sub_rota, carteira_principal.valor_saldo_total AS carteira_principal_valor_saldo_total, carteira_principal.pallet_total AS carteira_principal_pallet_total, carteira_principal.peso_total AS carteira_principal_peso_total, carteira_principal.valor_cliente_pedido AS carteira_principal_valor_cliente_pedido, carteira_principal.pallet_cliente_pedido AS carteira_principal_pallet_cliente_pedido, carteira_principal.peso_cliente_pedido AS carteira_principal_peso_cliente_pedido, carteira_principal.qtd_total_produto_carteira AS carteira_principal_qtd_total_produto_carteira, carteira_principal.estoque AS carteira_principal_estoque, carteira_principal.estoque_d0 AS carteira_principal_estoque_d0, carteira_principal.estoque_d1 AS carteira_principal_estoque_d1, carteira_principal.estoque_d2 AS carteira_principal_estoque_d2, carteira_principal.estoque_d3 AS carteira_principal_estoque_d3, carteira_principal.estoque_d4 AS carteira_principal_estoque_d4, carteira_principal.estoque_d5 AS carteira_principal_estoque_d5, carteira_principal.estoque_d6 AS carteira_principal_estoque_d6, carteira_principal.estoque_d7 AS carteira_principal_estoque_d7, carteira_principal.estoque_d8 AS carteira_principal_estoque_d8, carteira_principal.estoque_d9 AS carteira_principal_estoque_d9, carteira_principal.estoque_d10 AS carteira_principal_estoque_d10, carteira_principal.estoque_d11 AS carteira_principal_estoque_d11, carteira_principal.estoque_d12 AS carteira_principal_estoque_d12, carteira_principal.estoque_d13 AS carteira_principal_estoque_d13, carteira_principal.estoque_d14 AS carteira_principal_estoque_d14, carteira_principal.estoque_d15 AS carteira_principal_estoque_d15, carteira_principal.estoque_d16 AS carteira_principal_estoque_d16, carteira_principal.estoque_d17 AS carteira_principal_estoque_d17, carteira_principal.estoque_d18 AS carteira_principal_estoque_d18, carteira_principal.estoque_d19 AS carteira_principal_estoque_d19, carteira_principal.estoque_d20 AS carteira_principal_estoque_d20, carteira_principal.estoque_d21 AS carteira_principal_estoque_d21, carteira_principal.estoque_d22 AS carteira_principal_estoque_d22, carteira_principal.estoque_d23 AS carteira_principal_estoque_d23, carteira_principal.estoque_d24 AS carteira_principal_estoque_d24, carteira_principal.estoque_d25 AS carteira_principal_estoque_d25, carteira_principal.estoque_d26 AS carteira_principal_estoque_d26, carteira_principal.estoque_d27 AS carteira_principal_estoque_d27, carteira_principal.estoque_d28 AS carteira_principal_estoque_d28, carteira_principal.forma_agendamento AS carteira_principal_forma_agendamento, carteira_principal.created_at AS carteira_principal_created_at, carteira_principal.updated_at AS carteira_principal_updated_at, carteira_principal.created_by AS carteira_principal_created_by, carteira_principal.updated_by AS carteira_principal_updated_by, carteira_principal.ativo AS carteira_principal_ativo 
FROM carteira_principal 
WHERE carteira_principal.cnpj_cpf = %(cnpj_cpf_1)s AND carteira_principal.qtd_saldo_produto_pedido > %(qtd_saldo_produto_pedido_1)s]
[parameters: {'cnpj_cpf_1': '06.057.223/0294-04', 'qtd_saldo_produto_pedido_1': 0}]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
2025-09-10 11:43:39,853 - app.carteira.routes.programacao_em_lote.routes - WARNING -   ⚠️ Erro na conexão do banco para CNPJ 06.057.223/0294-04: (psycopg2.OperationalError) SSL connection has been closed unexpectedly

[SQL: SELECT carteira_principal.id AS carteira_principal_id, carteira_principal.num_pedido AS carteira_principal_num_pedido, carteira_principal.cod_produto AS carteira_principal_cod_produto, carteira_principal.pedido_cliente AS carteira_principal_pedido_cliente, carteira_principal.data_pedido AS carteira_principal_data_pedido, carteira_principal.data_atual_pedido AS carteira_principal_data_atual_pedido, carteira_principal.status_pedido AS carteira_principal_status_pedido, carteira_principal.cnpj_cpf AS carteira_principal_cnpj_cpf, carteira_principal.raz_social AS carteira_principal_raz_social, carteira_principal.raz_social_red AS carteira_principal_raz_social_red, carteira_principal.municipio AS carteira_principal_municipio, carteira_principal.estado AS carteira_principal_estado, carteira_principal.vendedor AS carteira_principal_vendedor, carteira_principal.equipe_vendas AS carteira_principal_equipe_vendas, carteira_principal.nome_produto AS carteira_principal_nome_produto, carteira_principal.unid_medida_produto AS carteira_principal_unid_medida_produto, carteira_principal.embalagem_produto AS carteira_principal_embalagem_produto, carteira_principal.materia_prima_produto AS carteira_principal_materia_prima_produto, carteira_principal.categoria_produto AS carteira_principal_categoria_produto, carteira_principal.qtd_produto_pedido AS carteira_principal_qtd_produto_pedido, carteira_principal.qtd_saldo_produto_pedido AS carteira_principal_qtd_saldo_produto_pedido, carteira_principal.qtd_cancelada_produto_pedido AS carteira_principal_qtd_cancelada_produto_pedido, carteira_principal.preco_produto_pedido AS carteira_principal_preco_produto_pedido, carteira_principal.cond_pgto_pedido AS carteira_principal_cond_pgto_pedido, carteira_principal.forma_pgto_pedido AS carteira_principal_forma_pgto_pedido, carteira_principal.incoterm AS carteira_principal_incoterm, carteira_principal.metodo_entrega_pedido AS carteira_principal_metodo_entrega_pedido, carteira_principal.data_entrega_pedido AS carteira_principal_data_entrega_pedido, carteira_principal.cliente_nec_agendamento AS carteira_principal_cliente_nec_agendamento, carteira_principal.observ_ped_1 AS carteira_principal_observ_ped_1, carteira_principal.cnpj_endereco_ent AS carteira_principal_cnpj_endereco_ent, carteira_principal.empresa_endereco_ent AS carteira_principal_empresa_endereco_ent, carteira_principal.cep_endereco_ent AS carteira_principal_cep_endereco_ent, carteira_principal.nome_cidade AS carteira_principal_nome_cidade, carteira_principal.cod_uf AS carteira_principal_cod_uf, carteira_principal.bairro_endereco_ent AS carteira_principal_bairro_endereco_ent, carteira_principal.rua_endereco_ent AS carteira_principal_rua_endereco_ent, carteira_principal.endereco_ent AS carteira_principal_endereco_ent, carteira_principal.telefone_endereco_ent AS carteira_principal_telefone_endereco_ent, carteira_principal.expedicao AS carteira_principal_expedicao, carteira_principal.data_entrega AS carteira_principal_data_entrega, carteira_principal.agendamento AS carteira_principal_agendamento, carteira_principal.hora_agendamento AS carteira_principal_hora_agendamento, carteira_principal.protocolo AS carteira_principal_protocolo, carteira_principal.agendamento_confirmado AS carteira_principal_agendamento_confirmado, carteira_principal.roteirizacao AS carteira_principal_roteirizacao, carteira_principal.menor_estoque_produto_d7 AS carteira_principal_menor_estoque_produto_d7, carteira_principal.saldo_estoque_pedido AS carteira_principal_saldo_estoque_pedido, carteira_principal.saldo_estoque_pedido_forcado AS carteira_principal_saldo_estoque_pedido_forcado, carteira_principal.separacao_lote_id AS carteira_principal_separacao_lote_id, carteira_principal.qtd_saldo AS carteira_principal_qtd_saldo, carteira_principal.valor_saldo AS carteira_principal_valor_saldo, carteira_principal.pallet AS carteira_principal_pallet, carteira_principal.peso AS carteira_principal_peso, carteira_principal.rota AS carteira_principal_rota, carteira_principal.sub_rota AS carteira_principal_sub_rota, carteira_principal.valor_saldo_total AS carteira_principal_valor_saldo_total, carteira_principal.pallet_total AS carteira_principal_pallet_total, carteira_principal.peso_total AS carteira_principal_peso_total, carteira_principal.valor_cliente_pedido AS carteira_principal_valor_cliente_pedido, carteira_principal.pallet_cliente_pedido AS carteira_principal_pallet_cliente_pedido, carteira_principal.peso_cliente_pedido AS carteira_principal_peso_cliente_pedido, carteira_principal.qtd_total_produto_carteira AS carteira_principal_qtd_total_produto_carteira, carteira_principal.estoque AS carteira_principal_estoque, carteira_principal.estoque_d0 AS carteira_principal_estoque_d0, carteira_principal.estoque_d1 AS carteira_principal_estoque_d1, carteira_principal.estoque_d2 AS carteira_principal_estoque_d2, carteira_principal.estoque_d3 AS carteira_principal_estoque_d3, carteira_principal.estoque_d4 AS carteira_principal_estoque_d4, carteira_principal.estoque_d5 AS carteira_principal_estoque_d5, carteira_principal.estoque_d6 AS carteira_principal_estoque_d6, carteira_principal.estoque_d7 AS carteira_principal_estoque_d7, carteira_principal.estoque_d8 AS carteira_principal_estoque_d8, carteira_principal.estoque_d9 AS carteira_principal_estoque_d9, carteira_principal.estoque_d10 AS carteira_principal_estoque_d10, carteira_principal.estoque_d11 AS carteira_principal_estoque_d11, carteira_principal.estoque_d12 AS carteira_principal_estoque_d12, carteira_principal.estoque_d13 AS carteira_principal_estoque_d13, carteira_principal.estoque_d14 AS carteira_principal_estoque_d14, carteira_principal.estoque_d15 AS carteira_principal_estoque_d15, carteira_principal.estoque_d16 AS carteira_principal_estoque_d16, carteira_principal.estoque_d17 AS carteira_principal_estoque_d17, carteira_principal.estoque_d18 AS carteira_principal_estoque_d18, carteira_principal.estoque_d19 AS carteira_principal_estoque_d19, carteira_principal.estoque_d20 AS carteira_principal_estoque_d20, carteira_principal.estoque_d21 AS carteira_principal_estoque_d21, carteira_principal.estoque_d22 AS carteira_principal_estoque_d22, carteira_principal.estoque_d23 AS carteira_principal_estoque_d23, carteira_principal.estoque_d24 AS carteira_principal_estoque_d24, carteira_principal.estoque_d25 AS carteira_principal_estoque_d25, carteira_principal.estoque_d26 AS carteira_principal_estoque_d26, carteira_principal.estoque_d27 AS carteira_principal_estoque_d27, carteira_principal.estoque_d28 AS carteira_principal_estoque_d28, carteira_principal.forma_agendamento AS carteira_principal_forma_agendamento, carteira_principal.created_at AS carteira_principal_created_at, carteira_principal.updated_at AS carteira_principal_updated_at, carteira_principal.created_by AS carteira_principal_created_by, carteira_principal.updated_by AS carteira_principal_updated_by, carteira_principal.ativo AS carteira_principal_ativo 
FROM carteira_principal 
WHERE carteira_principal.cnpj_cpf = %(cnpj_cpf_1)s AND carteira_principal.qtd_saldo_produto_pedido > %(qtd_saldo_produto_pedido_1)s]
[parameters: {'cnpj_cpf_1': '06.057.223/0294-04', 'qtd_saldo_produto_pedido_1': 0}]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
✅ [POOL] Tipos PostgreSQL registrados na conexão 132267238812352
[2025-09-10 11:43:39,861] INFO in routes:   ✅ Reconexão bem-sucedida para CNPJ 06.057.223/0294-04
2025-09-10 11:43:39,861 - app.carteira.routes.programacao_em_lote.routes - INFO -   ✅ Reconexão bem-sucedida para CNPJ 06.057.223/0294-04
[2025-09-10 11:43:39,861] INFO in routes:     Processando pedido VCD2543373 com 4 itens
2025-09-10 11:43:39,861 - app.carteira.routes.programacao_em_lote.routes - INFO -     Processando pedido VCD2543373 com 4 itens
[2025-09-10 11:43:39,865] INFO in routes:       Criando separação para 4320147: 32.0 unidades
2025-09-10 11:43:39,865 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4320147: 32.0 unidades
[2025-09-10 11:43:39,871] INFO in routes:       Criando separação para 4360147: 10.0 unidades
2025-09-10 11:43:39,871 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4360147: 10.0 unidades
[2025-09-10 11:43:39,884] INFO in routes:       Criando separação para 4310176: 2.0 unidades
2025-09-10 11:43:39,884 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4310176: 2.0 unidades
[2025-09-10 11:43:39,890] INFO in routes:       Criando separação para 4070176: 3.0 unidades
2025-09-10 11:43:39,890 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4070176: 3.0 unidades
[2025-09-10 11:43:39,896] INFO in routes:     Processando pedido VCD2543466 com 4 itens
2025-09-10 11:43:39,896 - app.carteira.routes.programacao_em_lote.routes - INFO -     Processando pedido VCD2543466 com 4 itens
[2025-09-10 11:43:39,898] INFO in routes:       Criando separação para 4320162: 2.0 unidades
2025-09-10 11:43:39,898 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4320162: 2.0 unidades
[2025-09-10 11:43:39,904] INFO in routes:       Criando separação para 4360162: 2.0 unidades
2025-09-10 11:43:39,904 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4360162: 2.0 unidades
[2025-09-10 11:43:39,910] INFO in routes:       Criando separação para 4070162: 2.0 unidades
2025-09-10 11:43:39,910 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4070162: 2.0 unidades
[2025-09-10 11:43:39,914] INFO in routes:       Criando separação para 4100161: 2.0 unidades
2025-09-10 11:43:39,914 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4100161: 2.0 unidades
[2025-09-10 11:43:39,925] INFO in routes:   ✅ CNPJ 06.057.223/0294-04: 0 separações atualizadas, 8 novas criadas
2025-09-10 11:43:39,925 - app.carteira.routes.programacao_em_lote.routes - INFO -   ✅ CNPJ 06.057.223/0294-04: 0 separações atualizadas, 8 novas criadas
[2025-09-10 11:43:39,925] INFO in routes:   Processando separações para CNPJ 06.057.223/0339-32
2025-09-10 11:43:39,925 - app.carteira.routes.programacao_em_lote.routes - INFO -   Processando separações para CNPJ 06.057.223/0339-32
✅ [POOL] Tipos PostgreSQL registrados na conexão 132267097971968
[2025-09-10 11:43:39,932] INFO in routes:     Processando pedido VCD2543212 com 9 itens
2025-09-10 11:43:39,932 - app.carteira.routes.programacao_em_lote.routes - INFO -     Processando pedido VCD2543212 com 9 itens
[2025-09-10 11:43:39,935] INFO in routes:       Criando separação para 4210165: 2.0 unidades
2025-09-10 11:43:39,935 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4210165: 2.0 unidades
[2025-09-10 11:43:39,940] INFO in routes:       Criando separação para 4320162: 3.0 unidades
2025-09-10 11:43:39,940 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4320162: 3.0 unidades
[2025-09-10 11:43:39,946] INFO in routes:       Criando separação para 4360162: 3.0 unidades
2025-09-10 11:43:39,946 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4360162: 3.0 unidades
[2025-09-10 11:43:39,952] INFO in routes:       Criando separação para 4030156: 10.0 unidades
2025-09-10 11:43:39,952 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4030156: 10.0 unidades
[2025-09-10 11:43:39,964] INFO in routes:       Criando separação para 4350162: 2.0 unidades
2025-09-10 11:43:39,964 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4350162: 2.0 unidades
[2025-09-10 11:43:39,970] INFO in routes:       Criando separação para 4070162: 2.0 unidades
2025-09-10 11:43:39,970 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4070162: 2.0 unidades
[2025-09-10 11:43:39,974] INFO in routes:       Criando separação para 4100161: 2.0 unidades
2025-09-10 11:43:39,974 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4100161: 2.0 unidades
[2025-09-10 11:43:39,979] INFO in routes:       Criando separação para 4050156: 2.0 unidades
2025-09-10 11:43:39,979 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4050156: 2.0 unidades
[2025-09-10 11:43:39,985] INFO in routes:       Criando separação para 4510156: 2.0 unidades
2025-09-10 11:43:39,985 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4510156: 2.0 unidades
[2025-09-10 11:43:39,993] INFO in routes:     Processando pedido VCD2543389 com 7 itens
2025-09-10 11:43:39,993 - app.carteira.routes.programacao_em_lote.routes - INFO -     Processando pedido VCD2543389 com 7 itens
[2025-09-10 11:43:39,995] INFO in routes:       Criando separação para 4310152: 7.0 unidades
2025-09-10 11:43:39,995 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4310152: 7.0 unidades
[2025-09-10 11:43:40,000] INFO in routes:       Criando separação para 4360147: 35.0 unidades
2025-09-10 11:43:40,000 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4360147: 35.0 unidades
[2025-09-10 11:43:40,007] INFO in routes:       Criando separação para 4510145: 7.0 unidades
2025-09-10 11:43:40,007 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4510145: 7.0 unidades
[2025-09-10 11:43:40,013] INFO in routes:       Criando separação para 4520145: 20.0 unidades
2025-09-10 11:43:40,013 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4520145: 20.0 unidades
[2025-09-10 11:43:40,018] INFO in routes:       Criando separação para 4310176: 3.0 unidades
2025-09-10 11:43:40,018 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4310176: 3.0 unidades
[2025-09-10 11:43:40,023] INFO in routes:       Criando separação para 4310177: 10.0 unidades
2025-09-10 11:43:40,023 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4310177: 10.0 unidades
[2025-09-10 11:43:40,028] INFO in routes:       Criando separação para 4070176: 6.0 unidades
2025-09-10 11:43:40,028 - app.carteira.routes.programacao_em_lote.routes - INFO -       Criando separação para 4070176: 6.0 unidades
[2025-09-10 11:43:40,039] INFO in routes:   ✅ CNPJ 06.057.223/0339-32: 0 separações atualizadas, 16 novas criadas
2025-09-10 11:43:40,039 - app.carteira.routes.programacao_em_lote.routes - INFO -   ✅ CNPJ 06.057.223/0339-32: 0 separações atualizadas, 16 novas criadas
2025-09-10 11:43:40,039 - frete_sistema - INFO - ⏱️ POST /carteira/programacao-lote/api/processar-agendamento-sendas | Status: 200 | Tempo: 123.988s
2025-09-10 11:43:40,039 - frete_sistema - INFO - ⏱️ POST /carteira/programacao-lote/api/processar-agendamento-sendas | Status: 200 | Tempo: 123.988s
2025-09-10 11:43:40,039 - frete_sistema - WARNING - 🐌 REQUISIÇÃO LENTA: /carteira/programacao-lote/api/processar-agendamento-sendas em 123.988s
2025-09-10 11:43:40,039 - frete_sistema - WARNING - 🐌 REQUISIÇÃO LENTA: /carteira/programacao-lote/api/processar-agendamento-sendas em 123.988s
127.0.0.1 - - [10/Sep/2025 11:43:40] "POST /carteira/programacao-lote/api/processar-agendamento-sendas HTTP/1.1" 200 -
2025-09-10 11:43:40,040 - werkzeug - INFO - 127.0.0.1 - - [10/Sep/2025 11:43:40] "POST /carteira/programacao-lote/api/processar-agendamento-sendas HTTP/1.1" 200 -
2025-09-10 11:43:40,325 - frete_sistema - INFO - 🌐 GET /carteira/programacao-lote/api/download-planilha-sendas/sendas_multi_20250910_114237.xlsx | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-10 11:43:40,325 - frete_sistema - INFO - 🌐 GET /carteira/programacao-lote/api/download-planilha-sendas/sendas_multi_20250910_114237.xlsx | User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb...
2025-09-10 11:43:40,327 - frete_sistema - INFO - ⏱️ GET /carteira/programacao-lote/api/download-planilha-sendas/sendas_multi_20250910_114237.xlsx | Status: 200 | Tempo: 0.002s
2025-09-10 11:43:40,327 - frete_sistema - INFO - ⏱️ GET /carteira/programacao-lote/api/download-planilha-sendas/sendas_multi_20250910_114237.xlsx | Status: 200 | Tempo: 0.002s
127.0.0.1 - - [10/Sep/2025 11:43:40] "GET /carteira/programacao-lote/api/download-planilha-sendas/sendas_multi_20250910_114237.xlsx HTTP/1.1" 200 -
2025-09-10 11:43:40,328 - werkzeug - INFO - 127.0.0.1 - - [10/Sep/2025 11:43:40] "GET /carteira/programacao-lote/api/download-planilha-sendas/sendas_multi_20250910_114237.xlsx HTTP/1.1" 200 -
