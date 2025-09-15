2025-09-15 18:54:00,800 - app - INFO - ⏭️ Claude AI desabilitado por configuração
2025-09-15 18:54:00,882 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Iniciando processamento da integração 132
2025-09-15 18:54:00,882 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Total de CNPJs: 2
2025-09-15 18:54:00,882 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Usuário: Rafael de Carvalho Nascimento
2025-09-15 18:54:00,882 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Campos preservados: ['cnpj', 'data_agendamento', 'data_expedicao', 'protocolo', 'itens', 'peso_total', 'pallets_total', 'valor_total', 'tipo_fluxo']
2025-09-15 18:54:00,882 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] ✅ Estrutura completa preservada com 13 itens
2025-09-15 18:54:01,272 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Inicializando classes...
2025-09-15 18:54:01,272 - app.portal.sendas.consumir_agendas - INFO - 🚀 Ambiente de PRODUÇÃO detectado - Forçando headless=True
2025-09-15 18:54:01,272 - app.portal.sendas.consumir_agendas - INFO -    RENDER=True, IS_PRODUCTION=False, PATH=True
2025-09-15 18:54:01,272 - app.portal.sendas.consumir_agendas - INFO -    CWD=/opt/render/project/src
2025-09-15 18:54:01,272 - app.portal.sendas.sendas_playwright - WARNING - 🚀 PRODUÇÃO DETECTADA - Forçando headless=True (parâmetro era True)
2025-09-15 18:54:01,272 - app.portal.sendas.sendas_playwright - INFO - Portal Sendas inicializado - Headless: True
2025-09-15 18:54:01,272 - app.portal.sendas.sendas_playwright - INFO - Usuário configurado: danielle.vieira@nacomgoya.com.br
2025-09-15 18:54:01,272 - app.portal.sendas.sendas_playwright - INFO - Diretório de downloads: /opt/render/project/src/app/portal/sendas/downloads
2025-09-15 18:54:01,273 - app.portal.sendas.consumir_agendas - INFO - 📁 Diretório de downloads: /opt/render/project/src/app/portal/sendas/downloads/20250915
2025-09-15 18:54:01,273 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Iniciando fluxo unificado (navegador persistente)...
2025-09-15 18:54:01,273 - app.portal.sendas.consumir_agendas - INFO - ============================================================
2025-09-15 18:54:01,273 - app.portal.sendas.consumir_agendas - INFO - FLUXO COMPLETO SENDAS - NAVEGADOR PERSISTENTE
2025-09-15 18:54:01,273 - app.portal.sendas.consumir_agendas - INFO - ============================================================
2025-09-15 18:54:01,273 - app.portal.sendas.consumir_agendas - INFO - 🌐 Etapa 1/5: Iniciando navegador...
2025-09-15 18:54:01,273 - app.portal.sendas.sendas_playwright - INFO - Iniciando navegador...
2025-09-15 18:54:01,919 - app.portal.sendas.sendas_playwright - INFO - 📦 Carregando storage_state...
2025-09-15 18:54:02,181 - app.portal.sendas.sendas_playwright - INFO - ✅ Navegador iniciado com sucesso
2025-09-15 18:54:02,181 - app.portal.sendas.consumir_agendas - INFO - 🔐 Etapa 2/5: Realizando login...
2025-09-15 18:54:02,181 - app.portal.sendas.sendas_playwright - INFO - 🍪 Tentando usar cookies salvos...
2025-09-15 18:54:02,182 - app.portal.sendas.sendas_playwright - INFO - 📦 Carregando cookies de: /opt/render/project/src/app/portal/sendas/sessions/sendas_cookies.json
2025-09-15 18:54:02,182 - app.portal.sendas.sendas_playwright - INFO - ✅ 9 cookies carregados do arquivo
2025-09-15 18:54:02,185 - app.portal.sendas.sendas_playwright - INFO - ✅ 9 cookies adicionados ao navegador
2025-09-15 18:54:02,250 - app.portal.sendas.sendas_playwright - INFO - 💾 Sessão salva em /opt/render/project/src/app/portal/sendas/sendas_state.json
2025-09-15 18:54:02,250 - app.portal.sendas.sendas_playwright - INFO - 🔍 Verificando autenticação...
2025-09-15 18:54:11,010 - app.portal.sendas.sendas_playwright - INFO - 📍 URL atual: https://plataforma.trizy.com.br/#/terminal/painel
2025-09-15 18:54:11,010 - app.portal.sendas.sendas_playwright - INFO - ✅ Acesso autorizado à plataforma
2025-09-15 18:54:14,020 - app.portal.sendas.sendas_playwright - INFO - ✅ Login realizado com sucesso usando cookies salvos!
2025-09-15 18:54:14,020 - app.portal.sendas.consumir_agendas - INFO - ✅ Login realizado com sucesso!
2025-09-15 18:54:14,020 - app.portal.sendas.consumir_agendas - INFO - 📦 Etapa 3/5: Navegando para Gestão de Pedidos...
2025-09-15 18:54:14,020 - app.portal.sendas.consumir_agendas - INFO - 🔄 Navegando para Gestão de Pedidos...
2025-09-15 18:54:16,041 - app.portal.sendas.consumir_agendas - INFO - 📋 Clicando em Menu...
2025-09-15 18:54:16,041 - app.portal.sendas.consumir_agendas - DEBUG - 🔄 Tentativa 1/3 para Clique em Menu
2025-09-15 18:54:16,101 - app.portal.sendas.consumir_agendas - INFO - ✅ Clique em Menu realizado com sucesso
2025-09-15 18:54:19,104 - app.portal.sendas.consumir_agendas - INFO - 📦 Acessando Gestão de Pedidos...
2025-09-15 18:54:19,104 - app.portal.sendas.consumir_agendas - DEBUG - 🔄 Tentativa 1/3 para Clique em Gestão de Pedidos
2025-09-15 18:54:28,367 - rq.worker - DEBUG - Sent heartbeat to prevent worker timeout. Next one should arrive in 90 seconds.
2025-09-15 18:54:49,131 - app.portal.sendas.consumir_agendas - WARNING - ⏱️ Timeout ao tentar Clique em Gestão de Pedidos (tentativa 1/3)
2025-09-15 18:54:49,131 - app.portal.sendas.consumir_agendas - DEBUG - 🔍 Verificando presença de modal ou painel de releases...
2025-09-15 18:54:49,143 - app.portal.sendas.consumir_agendas - INFO - 📋 Painel de releases/novidades detectado
2025-09-15 18:54:49,147 - app.portal.sendas.consumir_agendas - DEBUG - Tentando remover releases-panel diretamente: Page.evaluate: TypeError: closeBtn.click is not a function
    at eval (eval at evaluate (:234:30), <anonymous>:6:46)
    at UtilityScript.evaluate (<anonymous>:241:19)
    at UtilityScript.<anonymous> (<anonymous>:1:44)
2025-09-15 18:54:49,152 - app.portal.sendas.consumir_agendas - INFO - 🔄 Modal fechado, tentando Clique em Gestão de Pedidos novamente...
2025-09-15 18:54:49,152 - app.portal.sendas.consumir_agendas - DEBUG - 🔄 Tentativa 2/3 para Clique em Gestão de Pedidos
2025-09-15 18:54:49,205 - app.portal.sendas.consumir_agendas - INFO - ✅ Clique em Gestão de Pedidos realizado com sucesso
2025-09-15 18:54:49,205 - app.portal.sendas.fechar_modal_releases - INFO - 🔍 Verificando modal de releases após Gestão de Pedidos...
2025-09-15 18:54:49,205 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Fase 1: Detecção rápida de modal...
2025-09-15 18:54:49,205 - app.portal.sendas.fechar_modal_releases - DEBUG - 🔍 Iniciando detecção rápida de modal (máx 5 tentativas, 200ms cada)
2025-09-15 18:54:49,235 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 1
2025-09-15 18:54:49,343 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:49,529 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 2
2025-09-15 18:54:49,639 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:49,781 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 3
2025-09-15 18:54:49,850 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:50,110 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 4
2025-09-15 18:54:50,154 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:50,339 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 5
2025-09-15 18:54:50,449 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:50,617 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Nenhum modal de releases em 1000ms - continuando
2025-09-15 18:54:50,617 - app.portal.sendas.fechar_modal_releases - DEBUG - 🔍 Fase 2: Verificação adicional...
2025-09-15 18:54:50,727 - app.portal.sendas.fechar_modal_releases - INFO - ⏳ Indicador de loading detectado, aguardando mais...
2025-09-15 18:54:50,727 - app.portal.sendas.fechar_modal_releases - DEBUG - 🔍 Iniciando detecção rápida de modal (máx 5 tentativas, 300ms cada)
2025-09-15 18:54:50,806 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 1
2025-09-15 18:54:50,929 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:51,125 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 2
2025-09-15 18:54:51,250 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:51,448 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 3
2025-09-15 18:54:51,611 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:51,812 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 4
2025-09-15 18:54:51,854 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:51,990 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 5
2025-09-15 18:54:52,028 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:52,157 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Nenhum modal de releases em 1500ms - continuando
2025-09-15 18:54:52,157 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Modal de releases não apareceu
2025-09-15 18:54:52,157 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Sem modal de releases após Gestão de Pedidos
2025-09-15 18:54:52,663 - app.portal.sendas.consumir_agendas - INFO - ✅ Navegação para Gestão de Pedidos concluída
2025-09-15 18:54:52,663 - app.portal.sendas.consumir_agendas - INFO - 📥 Etapa 4/5: Baixando planilha...
2025-09-15 18:54:52,663 - app.portal.sendas.consumir_agendas - INFO - 📥 Iniciando download da planilha...
2025-09-15 18:54:52,663 - app.portal.sendas.fechar_modal_releases - INFO - 🔍 Verificando modal de releases antes do download...
2025-09-15 18:54:52,663 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Fase 1: Detecção rápida de modal...
2025-09-15 18:54:52,664 - app.portal.sendas.fechar_modal_releases - DEBUG - 🔍 Iniciando detecção rápida de modal (máx 5 tentativas, 200ms cada)
2025-09-15 18:54:52,679 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 1
2025-09-15 18:54:52,717 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:52,846 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 2
2025-09-15 18:54:52,907 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:53,044 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 3
2025-09-15 18:54:53,122 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:53,267 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 4
2025-09-15 18:54:53,330 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:53,464 - app.portal.sendas.fechar_modal_releases - INFO - ⚡ Modal de releases detectado na tentativa 5
2025-09-15 18:54:53,512 - app.portal.sendas.fechar_modal_releases - DEBUG - ⚡ Tentando ESC para fechar modal
2025-09-15 18:54:53,625 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Nenhum modal de releases em 1000ms - continuando
2025-09-15 18:54:53,625 - app.portal.sendas.fechar_modal_releases - DEBUG - 🔍 Fase 2: Verificação adicional...
2025-09-15 18:54:53,647 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Modal de releases não apareceu
2025-09-15 18:54:53,647 - app.portal.sendas.fechar_modal_releases - DEBUG - ℹ️ Sem modal de releases antes do download
2025-09-15 18:54:53,647 - app.portal.sendas.consumir_agendas - INFO - 🔘 Clicando em AÇÕES...
2025-09-15 18:54:53,647 - app.portal.sendas.consumir_agendas - DEBUG - 🔄 Tentativa 1/3 para Clique em AÇÕES
2025-09-15 18:54:57,157 - app.portal.sendas.consumir_agendas - INFO - ✅ Clique em AÇÕES realizado com sucesso
2025-09-15 18:54:58,165 - app.portal.sendas.consumir_agendas - INFO - 📋 Selecionando CONSUMIR ITENS...
2025-09-15 18:54:58,165 - app.portal.sendas.consumir_agendas - DEBUG - 🔄 Tentativa 1/3 para Clique em CONSUMIR ITENS
2025-09-15 18:54:58,372 - rq.worker - DEBUG - Sent heartbeat to prevent worker timeout. Next one should arrive in 90 seconds.
2025-09-15 18:54:58,419 - app.portal.sendas.consumir_agendas - INFO - ✅ Clique em CONSUMIR ITENS realizado com sucesso
2025-09-15 18:54:59,424 - app.portal.sendas.consumir_agendas - INFO - 💾 Clicando em DOWNLOAD PLANILHA...
2025-09-15 18:54:59,424 - app.portal.sendas.consumir_agendas - DEBUG - 🔄 Tentativa 1/3 para Clique em DOWNLOAD PLANILHA
2025-09-15 18:54:59,503 - app.portal.sendas.consumir_agendas - INFO - ✅ Clique em DOWNLOAD PLANILHA realizado com sucesso
2025-09-15 18:55:00,506 - app.portal.sendas.consumir_agendas - INFO - ⏳ Aguardando download...
2025-09-15 18:55:00,506 - app.portal.sendas.consumir_agendas - INFO - 📥 Tentativa 1/3 de download...
2025-09-15 18:55:03,049 - app.portal.sendas.consumir_agendas - INFO - 📄 Arquivo original: planilha-modelo.xlsx
2025-09-15 18:55:03,080 - app.portal.sendas.consumir_agendas - INFO - ✅ Arquivo salvo: /opt/render/project/src/app/portal/sendas/downloads/20250915/sendas_agendamentos_20250915_185503_planilha-modelo.xlsx
2025-09-15 18:55:03,080 - app.portal.sendas.consumir_agendas - INFO - ✅ Planilha baixada: /opt/render/project/src/app/portal/sendas/downloads/20250915/sendas_agendamentos_20250915_185503_planilha-modelo.xlsx
2025-09-15 18:55:03,080 - app.portal.sendas.consumir_agendas - INFO - 🔧 Processando planilha...
2025-09-15 18:55:03,080 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Preenchendo planilha: /opt/render/project/src/app/portal/sendas/downloads/20250915/sendas_agendamentos_20250915_185503_planilha-modelo.xlsx
2025-09-15 18:55:03,080 - app.portal.sendas.preencher_planilha - INFO - 
================================================================================
2025-09-15 18:55:03,081 - app.portal.sendas.preencher_planilha - INFO - 🔄 PROCESSAMENTO DE MÚLTIPLOS CNPJs - PORTAL SENDAS
2025-09-15 18:55:03,081 - app.portal.sendas.preencher_planilha - INFO - ================================================================================
2025-09-15 18:55:03,081 - app.portal.sendas.preencher_planilha - INFO - 📋 Total de CNPJs a processar: 2
2025-09-15 18:55:03,447 - app.portal.sendas.preencher_planilha - INFO - ✅ Usando dados PRÉ-PROCESSADOS fornecidos (NÃO buscará do banco)
2025-09-15 18:55:03,447 - app.portal.sendas.preencher_planilha - INFO -    Total de grupos: 2
2025-09-15 18:55:03,447 - app.portal.sendas.preencher_planilha - INFO -    Primeiro grupo tem 13 itens
2025-09-15 18:55:03,447 - app.portal.sendas.preencher_planilha - INFO - 
  [1/2] Processando CNPJ: 06.057.223/0492-60
2025-09-15 18:55:03,447 - app.portal.sendas.preencher_planilha - INFO -     13 itens fornecidos
2025-09-15 18:55:03,465 - app.portal.sendas.preencher_planilha - INFO - 
  [2/2] Processando CNPJ: 06.057.223/0537-04
2025-09-15 18:55:03,465 - app.portal.sendas.preencher_planilha - INFO -     15 itens fornecidos
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO - 
📝 Preenchendo planilha com 2 CNPJs...
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO -   📋 Protocolo AG_2304_18092025_1853 → Demanda ID 1
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO -   📋 Protocolo AG_2305_18092025_1853 → Demanda ID 2
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO -   📌 CNPJ 06.057.223/0492-60 - Usando Demanda ID 1 (protocolo: AG_2304_18092025_1853)
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - WARNING -   ⚠️ CNPJ 06.057.223/0492-60 sem mapeamento de filial
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO -   📌 CNPJ 06.057.223/0537-04 - Usando Demanda ID 2 (protocolo: AG_2305_18092025_1853)
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - WARNING -   ⚠️ CNPJ 06.057.223/0537-04 sem mapeamento de filial
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO -   ✅ 0 linhas preenchidas no total
2025-09-15 18:55:03,467 - app.portal.sendas.preencher_planilha - INFO - 
🗑️ Removendo linhas não agendadas...
2025-09-15 18:55:03,555 - app.portal.sendas.preencher_planilha - INFO -   🗑️ 14997 linhas removidas (não agendadas)
2025-09-15 18:55:03,555 - app.portal.sendas.preencher_planilha - INFO -   ✅ 0 linhas mantidas (agendadas)
2025-09-15 18:55:03,564 - app.portal.sendas.preencher_planilha - INFO -   🔄 Convertendo para formato compatível com Sendas...
2025-09-15 18:55:03,595 - app.portal.sendas.preencher_planilha - INFO - 
💾 Planilha salva: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,595 - app.portal.sendas.preencher_planilha - INFO - 
================================================================================
2025-09-15 18:55:03,595 - app.portal.sendas.preencher_planilha - INFO - 📊 RESUMO DO PROCESSAMENTO MÚLTIPLO:
2025-09-15 18:55:03,595 - app.portal.sendas.preencher_planilha - INFO - ================================================================================
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO -   CNPJs processados: 2
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO -   Linhas preenchidas: 0
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO -   Linhas removidas: 14997
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO -   Peso total geral: 3053.98 kg
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO -   Tipo caminhão: Caminhão 3/4 (2 eixos) 16T
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO -   Protocolo: AG_2305_18092025_1853
2025-09-15 18:55:03,596 - app.portal.sendas.preencher_planilha - INFO - ================================================================================
2025-09-15 18:55:03,596 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] Planilha preenchida: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO - ✅ Planilha processada: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO - 📤 Etapa 5/5: Fazendo upload da planilha...
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO -    ℹ️ Normalização com LibreOffice será aplicada automaticamente dentro do upload
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO - 📤 Iniciando upload da planilha: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO - ✅ Arquivo válido: .xlsx, 0.01MB
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO - 🔧 Normalizando arquivo Excel para compatibilidade com o portal...
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO -    (Isso evita o erro 500 causado por formatação incompatível)
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO - 🔍 Análise do arquivo original:
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO -    Nome: sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO -    Tamanho: 6.2 KB
2025-09-15 18:55:03,596 - app.portal.sendas.consumir_agendas - INFO -    Caminho: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,597 - app.portal.sendas.consumir_agendas - INFO - 🎯 SOLUÇÃO DEFINITIVA: Normalizando com LibreOffice
2025-09-15 18:55:03,597 - app.portal.sendas.consumir_agendas - INFO -    (Simula abrir/salvar do Excel - converte para sharedStrings!)
2025-09-15 18:55:03,597 - app.portal.sendas.normalizar_com_libreoffice - INFO - 📥 Normalizando: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,597 - app.portal.sendas.normalizar_com_libreoffice - INFO - ============================================================
2025-09-15 18:55:03,597 - app.portal.sendas.normalizar_com_libreoffice - INFO - 🚀 NORMALIZAÇÃO COM LIBREOFFICE (ABRIR E SALVAR)
2025-09-15 18:55:03,597 - app.portal.sendas.normalizar_com_libreoffice - INFO - ============================================================
2025-09-15 18:55:03,598 - app.portal.sendas.normalizar_com_libreoffice - INFO - 📦 LibreOffice não encontrado. Instalando...
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - ERROR - ❌ Não foi possível instalar LibreOffice automaticamente
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO - Por favor, instale manualmente:
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO -   Ubuntu/Debian: sudo apt-get install libreoffice
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO -   CentOS/RHEL: sudo yum install libreoffice
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - ERROR - ❌ LibreOffice não disponível
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO - 🔄 Tentando com xlsxwriter...
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO - ============================================================
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO - 🚀 NORMALIZAÇÃO COM XLSXWRITER (FORÇA SHAREDSTRINGS)
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO - ============================================================
2025-09-15 18:55:03,599 - app.portal.sendas.normalizar_com_libreoffice - INFO - 📖 Lendo arquivo: /tmp/sendas_multi_20250915_185503.xlsx
2025-09-15 18:55:03,610 - app.portal.sendas.normalizar_com_libreoffice - INFO - 📊 Dados: 3 linhas x 61 colunas
2025-09-15 18:55:03,632 - app.portal.sendas.normalizar_com_libreoffice - INFO - ✏️ Escrevendo com xlsxwriter (sharedStrings)...
2025-09-15 18:55:03,639 - app.portal.sendas.normalizar_com_libreoffice - INFO - ✅ Arquivo criado: /tmp/tmppn_p0pry_normalizado.xlsx
2025-09-15 18:55:03,639 - app.portal.sendas.normalizar_com_libreoffice - INFO - 📏 Tamanho: 6.2 KB
2025-09-15 18:55:03,639 - app.portal.sendas.normalizar_com_libreoffice - INFO - ✅ Usando sharedStrings (compatível com Sendas)
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO - ✅ Arquivo normalizado com sucesso
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO -    Arquivo normalizado: tmppn_p0pry_normalizado.xlsx
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO -    Caminho completo: /tmp/tmppn_p0pry_normalizado.xlsx
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO -    Tamanho após normalização: 6.2 KB
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO -    Diferença: 0.0 KB
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO - ✅ Arquivo preparado com estrutura compatível com Sendas
2025-09-15 18:55:03,639 - app.portal.sendas.consumir_agendas - INFO - 🔄 USANDO ARQUIVO NORMALIZADO PARA UPLOAD
2025-09-15 18:55:04,143 - app.portal.sendas.consumir_agendas - INFO - 🔑 Obtendo token JWT para autenticação...
2025-09-15 18:55:04,148 - app.portal.sendas.consumir_agendas - INFO - ✅ Token JWT obtido do cookie trizy_access_token
2025-09-15 18:55:04,148 - app.portal.sendas.consumir_agendas - INFO - 📨 Enviando token JWT via postMessage para o iframe...
2025-09-15 18:55:04,965 - app.portal.sendas.consumir_agendas - INFO - ✅ Token enviado 2x para garantir recebimento
2025-09-15 18:55:04,965 - app.portal.sendas.consumir_agendas - INFO - 🎯 Preparando interceptação de resposta do upload...
2025-09-15 18:55:04,972 - app.portal.sendas.consumir_agendas - INFO - 🚀 Navegador persistente - já estamos na tela de upload
2025-09-15 18:55:04,972 - app.portal.sendas.consumir_agendas - INFO -    Após download, o botão UPLOAD PLANILHA já está visível
2025-09-15 18:55:05,477 - app.portal.sendas.consumir_agendas - INFO - 🔍 Procurando botão de Upload da planilha...
2025-09-15 18:55:05,488 - app.portal.sendas.consumir_agendas - INFO - ✅ Botão encontrado com seletor: button:has-text("Upload da planilha")
2025-09-15 18:55:05,488 - app.portal.sendas.consumir_agendas - INFO - ✅ Botão de upload encontrado
2025-09-15 18:55:05,597 - app.portal.sendas.consumir_agendas - INFO - 🖱️ Botão de upload clicado, aguardando modal...
2025-09-15 18:55:07,604 - app.portal.sendas.consumir_agendas - INFO - 🔍 Procurando modal de upload DENTRO DO IFRAME...
2025-09-15 18:55:07,613 - app.portal.sendas.consumir_agendas - INFO - 🎆 Modal de upload encontrado no IFRAME: [role="dialog"].rs-modal
2025-09-15 18:55:07,613 - app.portal.sendas.consumir_agendas - INFO - 🔍 Localizando o DevExtreme FileUploader DENTRO do modal...
2025-09-15 18:55:07,613 - app.portal.sendas.consumir_agendas - INFO - 🎯 Preparando para interceptar resposta do endpoint de upload...
2025-09-15 18:55:09,124 - app.portal.sendas.consumir_agendas - WARNING - ⚠️ Root do FileUploader não encontrado no modal. Tentando só pelos inputs.
2025-09-15 18:55:09,135 - app.portal.sendas.consumir_agendas - INFO - 📁 1 input(s) de arquivo encontrados no modal.
2025-09-15 18:55:09,147 - app.portal.sendas.consumir_agendas - INFO - 📝 Input[0] tem name='arquivoExcel'
2025-09-15 18:55:09,147 - app.portal.sendas.consumir_agendas - INFO - 📤 Tentando set_input_files no input[0] com campo name='arquivoExcel'...
2025-09-15 18:55:09,544 - app.portal.sendas.consumir_agendas - INFO - ✅ DevExtreme reconheceu o arquivo (saiu de 'dx-fileuploader-empty').
2025-09-15 18:55:09,552 - app.portal.sendas.consumir_agendas - INFO - ℹ️ Sem botão de upload — assumindo 'instant upload'.
2025-09-15 18:55:09,552 - app.portal.sendas.consumir_agendas - INFO - ⏳ Aguardando resposta do servidor após upload...
2025-09-15 18:55:09,776 - app.portal.sendas.consumir_agendas - INFO - 🎯 Capturado upload para: https://api.trizy.com.br/mro/empresa/demanda/consumoExcelUpload
2025-09-15 18:55:10,041 - app.portal.sendas.consumir_agendas - INFO - ✅ Upload confirmado pela API (statusCode: 200)
2025-09-15 18:55:10,041 - app.portal.sendas.consumir_agendas - INFO - 🛰️ Upload HTTP status: 200
2025-09-15 18:55:10,041 - app.portal.sendas.consumir_agendas - INFO - 🧾 Corpo da resposta: {'statusCode': 200, 'message': 'Consumo importado com sucesso!', 'data': []}
2025-09-15 18:55:10,108 - app.portal.sendas.consumir_agendas - INFO - ✅ Upload confirmado pela API com sucesso
2025-09-15 18:55:10,108 - app.portal.sendas.consumir_agendas - INFO -    📊 Status HTTP: 200
2025-09-15 18:55:10,203 - app.portal.sendas.consumir_agendas - INFO - ✅ Modal fechou automaticamente após upload bem-sucedido
2025-09-15 18:55:10,203 - app.portal.sendas.consumir_agendas - INFO - ⏳ Aguardando interface estabilizar após fechamento do modal...
2025-09-15 18:55:13,312 - app.portal.sendas.consumir_agendas - INFO - 🔍 Procurando botão CONFIRMAR DEMANDA na tela principal...
2025-09-15 18:55:13,313 - app.portal.sendas.consumir_agendas - INFO - 🔍 Iniciando busca pelo botão CONFIRMAR DEMANDA...
2025-09-15 18:55:13,313 - app.portal.sendas.consumir_agendas - INFO -    Contexto: Dentro do iframe #iframe-servico
2025-09-15 18:55:13,313 - app.portal.sendas.consumir_agendas - INFO - ⏳ Aguardando 2 segundos para botão aparecer...
2025-09-15 18:55:15,595 - app.portal.sendas.consumir_agendas - INFO - 📸 Screenshot antes de procurar botão: /tmp/sendas_antes_confirmar_20250915_185515.png
2025-09-15 18:55:15,595 - app.portal.sendas.consumir_agendas - INFO - 🔍 Listando botões disponíveis no iframe...
2025-09-15 18:55:15,630 - app.portal.sendas.consumir_agendas - INFO -    Total de botões visíveis: 6
2025-09-15 18:55:15,707 - app.portal.sendas.consumir_agendas - INFO -    Botão 4: 'CONFIRMAR DEMANDA'
2025-09-15 18:55:15,732 - app.portal.sendas.consumir_agendas - INFO -    Botão 5: 'CANCELAR'
2025-09-15 18:55:15,747 - app.portal.sendas.consumir_agendas - INFO - 🔍 Tentando seletor 1: button:has-text("CONFIRMAR DEMANDA")
2025-09-15 18:55:15,771 - app.portal.sendas.consumir_agendas - INFO - ✅ Botão encontrado: 'CONFIRMAR DEMANDA'
2025-09-15 18:55:16,506 - app.portal.sendas.consumir_agendas - INFO - 🖱️ Clicou em CONFIRMAR DEMANDA
2025-09-15 18:55:19,761 - app.portal.sendas.consumir_agendas - WARNING - ⚠️ Botão CONFIRMAR DEMANDA não encontrado ou confirmação não necessária
2025-09-15 18:55:19,761 - app.portal.sendas.consumir_agendas - INFO -    (Upload já foi realizado com sucesso)
2025-09-15 18:55:19,761 - app.portal.sendas.consumir_agendas - WARNING - ⚠️ Upload OK, mas sem confirmação. Considerando sucesso do upload.
2025-09-15 18:55:19,761 - app.portal.sendas.consumir_agendas - INFO - ============================================================
2025-09-15 18:55:19,761 - app.portal.sendas.consumir_agendas - INFO - ✅ FLUXO COMPLETO CONCLUÍDO COM SUCESSO!
2025-09-15 18:55:19,761 - app.portal.sendas.consumir_agendas - INFO - ============================================================
2025-09-15 18:55:19,907 - app.portal.sendas.sendas_playwright - INFO - ✅ Navegador fechado com sucesso
2025-09-15 18:55:19,907 - app.portal.sendas.consumir_agendas - INFO - 🔒 Navegador fechado
2025-09-15 18:55:19,907 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] ✅ Processamento concluído com sucesso
2025-09-15 18:55:19,911 - app.portal.sendas.retorno_agendamento - INFO - 📝 Processando retorno do agendamento - Protocolo: 185503, Fluxo: programacao_lote
2025-09-15 18:55:19,930 - app.portal.sendas.retorno_agendamento - INFO - ✅ FLUXO UNIFICADO - Atualizado 0 Separações com protocolo 185503
2025-09-15 18:55:19,930 - app.portal.sendas.retorno_agendamento - INFO -     0 mudaram de PREVISAO para ABERTO
2025-09-15 18:55:19,930 - app.portal.sendas.retorno_agendamento - INFO -     0 já existentes atualizadas com datas
2025-09-15 18:55:19,930 - app.portal.workers.sendas_jobs - INFO - [Worker Sendas] ✅ Protocolos salvos com sucesso
2025-09-15 18:55:19,940 - rq.worker - DEBUG - Finished performing Job ID 8614dec5-6759-45ff-98ea-5a36ea0bc5b4
2025-09-15 18:55:19,943 - rq.worker - DEBUG - Handling successful execution of job 8614dec5-6759-45ff-98ea-5a36ea0bc5b4
2025-09-15 18:55:19,945 - rq.worker - DEBUG - Saving job 8614dec5-6759-45ff-98ea-5a36ea0bc5b4's successful execution result
2025-09-15 18:55:19,945 - rq.worker - DEBUG - Removing job 8614dec5-6759-45ff-98ea-5a36ea0bc5b4 from StartedJobRegistry
2025-09-15 18:55:19,947 - rq.worker - DEBUG - Finished handling successful execution of job 8614dec5-6759-45ff-98ea-5a36ea0bc5b4
2025-09-15 18:55:19,947 - rq.worker - INFO - sendas: Job OK (8614dec5-6759-45ff-98ea-5a36ea0bc5b4)
2025-09-15 18:55:19,948 - rq.worker - DEBUG - Result: "{'status': 'success', 'message': 'Agendamentos processados com sucesso no Sendas', 'integracao_id': 132, 'total_cnpjs': 2, 'resultado': {'sucesso': True, 'arquivo_download': '/opt/render/project/src/app/portal/sendas/downloads/20250915/sendas_agendamentos_20250915_185503_planilha-modelo.xlsx', 'arquivo_upload': '/tmp/sendas_multi_20250915_185503.xlsx', 'upload_sucesso': True, 'mensagem': 'Fluxo completo executado com sucesso', 'timestamp': '2025-09-15T18:54:01.273306'}}"
2025-09-15 18:55:19,948 - rq.worker - INFO - Result is kept for 86400 seconds
2025-09-15 18:55:20,018 - rq.worker - DEBUG - Sent heartbeat to prevent worker timeout. Next one should arrive in 1860 seconds.
2025-09-15 18:55:20,018 - rq.worker - DEBUG - Sent heartbeat to prevent worker timeout. Next one should arrive in 1860 seconds.
2025-09-15 18:55:20,020 - rq.worker - DEBUG - *** Listening on atacadao,sendas,high,default...
2025-09-15 18:55:20,021 - rq.worker - DEBUG - Sent heartbeat to prevent worker timeout. Next one should arrive in 1860 seconds.
2025-09-15 18:55:20,021 - rq.worker - DEBUG - Dequeueing jobs on queues atacadao,sendas,high,default and timeout 1785
2025-09-15 18:55:20,021 - rq.queue - DEBUG - Starting BLPOP operation for queues rq:queue:atacadao, rq:queue:sendas, rq:queue:high, rq:queue:default with timeout of 1785

pip install -r requirements.txt && python -m playwright install chromium && bash install_libreoffice_render.sh