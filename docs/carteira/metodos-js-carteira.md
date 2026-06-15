<!-- doc:meta
tipo: explanation
camada: L2
sot_de: mapa de referência dos métodos JavaScript dos arquivos do front-end da Carteira de Pedidos (lote-manager, workspace-montagem, carteira-agrupada) e suas chamadas inter-arquivos
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# MAPEAMENTO COMPLETO DE MÉTODOS - SISTEMA CARTEIRA DE PEDIDOS

> **Papel:** catálogo de referência dos métodos JS do front-end da Carteira (o que cada função faz e quem a chama), por arquivo.

## Contexto

Mapeia os métodos públicos dos três arquivos JavaScript que compõem a tela da Carteira de Pedidos (`lote-manager.js`, `workspace-montagem.js`, `carteira-agrupada.js`), além das funções globais e das principais chamadas entre arquivos. Serve de guia rápido para localizar responsabilidades e dependências antes de alterar o front-end da Carteira.

## Indice

- [📁 lote-manager.js](#-lote-managerjs)
- [📁 workspace-montagem.js](#-workspace-montagemjs)
- [📁 carteira-agrupada.js](#-carteira-agrupadajs)
- [FUNÇÕES GLOBAIS](#funções-globais)
- [CHAMADAS INTER-ARQUIVOS PRINCIPAIS](#chamadas-inter-arquivos-principais)

## 📁 lote-manager.js

### constructor(workspace)
**Função**: Inicializa o LoteManager com referência ao workspace
**Chamado por**: WorkspaceMontagem.init()

### init()
**Função**: Inicialização básica, apenas log
**Chamado por**: constructor()

### gerarNovoLoteId()
**Função**: Gera ID único para lote (formato: LOTE_YYYYMMDD_HHMMSS_RRR)
**Chamado por**: criarNovoLote()
**Observação**: Temporário - migrar para backend

### criarNovoLote(numPedido)
**Função**: Cria novo lote com ID gerado automaticamente
**Chamado por**: Botões UI

### criarLote(numPedido, loteId)
**Função**: Cria lote com ID específico e renderiza card
**Chamado por**: criarNovoLote(), WorkspaceMontagem

### renderizarCardLote(loteId)
**Função**: Obtém dados do lote e chama renderizarCardUniversal
**Chamado por**: criarLote(), atualizarCardLote()

### obterPermissoes(status)
**Função**: Retorna objeto com permissões baseadas no status
**Chamado por**: renderizarCardUniversal()

### renderizarCardUniversal(loteData)
**Função**: Renderiza HTML completo do card de separação
**Chamado por**: renderizarCardLote()

### formatarDataDisplay(data)
**Função**: Converte data para formato dd/mm/yyyy
**Chamado por**: renderizarCardUniversal()

### renderizarProdutosUniversal(produtos, loteId, podeRemover)
**Função**: Renderiza lista de produtos com opção de remoção
**Chamado por**: renderizarCardUniversal()

### adicionarProdutoNoLote(loteId, dadosProduto)
**Função**: Adiciona/atualiza produto no lote via API
**Chamado por**: WorkspaceMontagem.adicionarProdutosSelecionados()

### obterDataExpedicaoDefault()
**Função**: Retorna data padrão (amanhã)
**Chamado por**: adicionarProdutoNoLote()

### recalcularTotaisLote(loteId)
**Função**: Recalcula valor, peso e pallet do lote
**Chamado por**: adicionarProdutoNoLote(), removerProdutoDoLote()

### atualizarCardLote(loteId)
**Função**: Re-renderiza card completo
**Chamado por**: adicionarProdutoNoLote(), removerProdutoDoLote(), WorkspaceMontagem.salvarEdicaoDatas()

### removerProdutoDoLote(loteId, codProduto)
**Função**: Remove produto do lote via API
**Chamado por**: Botão remover no card (onclick)

### formatarMoeda(valor)
**Função**: Formata valor monetário BRL
**Chamado por**: renderizarCardUniversal()

### formatarPeso(peso)
**Função**: Formata peso em kg
**Chamado por**: renderizarCardUniversal()

### formatarPallet(pallet)
**Função**: Formata quantidade de pallets
**Chamado por**: renderizarCardUniversal()

### salvarSeparacaoAPI(numPedido, codProduto, loteId, quantidade, dataExpedicao)
**Função**: Salva separação via API /carteira/api/separacao/salvar
**Chamado por**: adicionarProdutoNoLote()

### getCSRFToken()
**Função**: Obtém token CSRF de múltiplas fontes
**Chamado por**: salvarSeparacaoAPI(), removerProdutoDoLote()

---

## 📁 workspace-montagem.js

### constructor()
**Função**: Inicializa WorkspaceMontagem com Maps e variáveis
**Chamado por**: carteiraAgrupada.initWorkspace()

### init()
**Função**: Configura workspace e event listeners
**Chamado por**: constructor()

### setupEventListeners()
**Função**: Configura eventos de seleção e checkboxes
**Chamado por**: init()

### limparDadosAnteriores()
**Função**: Limpa Maps, cancela requests e reseta estado
**Chamado por**: abrirWorkspace()

### abrirWorkspace(numPedido)
**Função**: Carrega produtos e separações do pedido
**Chamado por**: carteiraAgrupada.expandirDetalhes(), Botão expandir

### renderizarTodasSeparacoes(numPedido)
**Função**: Renderiza área de separações com lotes existentes
**Chamado por**: abrirWorkspace()

### renderizarWorkspace(numPedido, data)
**Função**: Renderiza HTML completo do workspace
**Chamado por**: abrirWorkspace()

### renderizarTabelaProdutos(produtos)
**Função**: Delega renderização para workspaceTabela
**Chamado por**: renderizarWorkspace()

### renderizarSeparacoesNaAreaUnificada()
**Função**: Renderiza todas separações (PREVISAO e confirmadas)
**Chamado por**: abrirWorkspace()

### getStatusClass(status)
**Função**: Retorna classe CSS baseada no status
**Chamado por**: renderizarSeparacoesNaAreaUnificada()

### formatarQuantidade(qtd)
**Função**: Formata quantidade inteira
**Chamado por**: Renderização de produtos

### formatarData(data)
**Função**: Converte data ISO para dd/mm/yyyy
**Chamado por**: Múltiplos locais de renderização

### calcularStatusDisponibilidade(produto)
**Função**: Calcula status baseado em estoque
**Chamado por**: Renderização de produtos

### calcularDiasAte(dataStr)
**Função**: Calcula dias até data futura
**Chamado por**: calcularStatusDisponibilidade()

### calcularSaldoDisponivel(produto)
**Função**: Calcula saldo disponível do produto
**Chamado por**: Renderização de produtos

### gerarNovoLoteId()
**Função**: Gera ID único (deprecated - usar loteManager)
**Chamado por**: criarNovoLote()

### criarNovoLote(numPedido)
**Função**: Cria novo lote vazio
**Chamado por**: Botão criar lote

### configurarCheckboxes(numPedido)
**Função**: Configura eventos de checkboxes de seleção
**Chamado por**: renderizarWorkspace()

### toggleProdutoSelecionado(codProduto, selecionado)
**Função**: Adiciona/remove produto da seleção
**Chamado por**: Event listener checkbox

### atualizarSelectAll(workspaceElement)
**Função**: Atualiza estado do checkbox "selecionar todos"
**Chamado por**: toggleProdutoSelecionado()

### adicionarProdutosSelecionados(loteId)
**Função**: Adiciona produtos selecionados ao lote
**Chamado por**: Botão "Adicionar" no card

### coletarDadosProdutosDaTabela()
**Função**: Coleta dados de produtos do DOM (fallback)
**Chamado por**: adicionarProdutosSelecionados()

### limparSelecao()
**Função**: Desmarca todos checkboxes
**Chamado por**: adicionarProdutosSelecionados()

### mostrarFeedback(mensagem, tipo)
**Função**: Exibe toast notification
**Chamado por**: Múltiplas ações de usuário

### obterNumeroPedido()
**Função**: Retorna número do pedido atual
**Chamado por**: adicionarProdutoNoLote()

### resetarQuantidadeProduto(codProduto)
**Função**: Reseta quantidade para valor original
**Chamado por**: Não usado atualmente

### atualizarSaldoNaTabela(codProduto)
**Função**: Atualiza saldo disponível na tabela
**Chamado por**: Não usado (comentado)

### abrirCardex(codProduto)
**Função**: Abre modal cardex do produto
**Chamado por**: Botão cardex

### atualizarQuantidadeProduto(input)
**Função**: Atualiza quantidade via workspaceQuantidades
**Chamado por**: Event listener input

### atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto)
**Função**: Atualiza colunas calculadas via workspaceQuantidades
**Chamado por**: Event listener quantidade

### recalcularTotaisLotesComProduto(codProduto)
**Função**: Recalcula totais via workspaceQuantidades
**Chamado por**: Event listener quantidade

### exportarCardex(codProduto)
**Função**: Exporta cardex para Excel
**Chamado por**: Botão exportar cardex

### excluirLote(loteId)
**Função**: Exclui lote via separacaoManager
**Chamado por**: Botão excluir no card

### confirmarSeparacao(loteId)
**Função**: Confirma separação (PREVISAO→ABERTO)
**Chamado por**: Botão confirmar (deprecated)

### confirmarAgendamentoLote(loteId, tipo)
**Função**: Confirma agendamento do lote
**Chamado por**: Botão confirmar agendamento

### reverterAgendamentoLote(loteId, tipo)
**Função**: Reverte confirmação de agendamento
**Chamado por**: Botão reverter agendamento

### abrirDetalhesLote(loteId)
**Função**: Expande card para mostrar detalhes
**Chamado por**: Botão detalhes

### removerLote(loteId)
**Função**: Remove lote (deprecated)
**Chamado por**: Não usado

### removerProdutoDoLote(loteId, codProduto)
**Função**: Remove produto (deprecated - usar loteManager)
**Chamado por**: Não usado

### renderizarErroWorkspace(numPedido, mensagem)
**Função**: Renderiza mensagem de erro
**Chamado por**: abrirWorkspace() em caso de erro

### formatarMoeda(valor)
**Função**: Formata valor monetário
**Chamado por**: Renderização de valores

### formatarPeso(peso)
**Função**: Formata peso via workspaceQuantidades
**Chamado por**: Renderização de pesos

### formatarPallet(pallet)
**Função**: Formata pallets via workspaceQuantidades
**Chamado por**: Renderização de pallets

### toggleProdutosSeparacao(loteId)
**Função**: Expande/colapsa produtos do lote
**Chamado por**: Botão toggle produtos

### alterarStatusSeparacao(loteId, novoStatus)
**Função**: Altera status da separação via API
**Chamado por**: Botões confirmar/reverter no card

### getCSRFToken()
**Função**: Obtém token CSRF
**Chamado por**: Todas chamadas API

### editarDatasSeparacao(loteId)
**Função**: Abre modal edição para separação
**Chamado por**: editarDatas()

### editarDatasPreSeparacao(loteId)
**Função**: Abre modal edição para pré-separação
**Chamado por**: editarDatas()

### editarDatas(loteId, status)
**Função**: Determina tipo e abre modal de edição
**Chamado por**: Botão "Datas" no card

### abrirModalEdicaoDatasDireto(tipo, loteId, dadosAtuais)
**Função**: Renderiza e abre modal de datas
**Chamado por**: editarDatas(), abrirModalDatas()

### abrirModalDatas(loteId, dadosAtuais = {})
**Função**: Abre modal de datas com dados atuais (assinatura distinta da homônima em carteira-agrupada.js)
**Chamado por**: editarDatas(), atualizarViewCompactaDireto() (via onclick)

### salvarEdicaoDatas(tipo, loteId)
**Função**: Salva datas editadas via API
**Chamado por**: Botão salvar no modal

### imprimirSeparacao(loteId)
**Função**: Abre página de impressão
**Chamado por**: Botão imprimir

### agendarNoPortal(loteId, dataAgendamento)
**Função**: Agenda no portal do cliente
**Chamado por**: Botão agendar portal

### verificarPortal(loteId)
**Função**: Verifica status no portal
**Chamado por**: Botão verificar portal

### verificarProtocoloNoPortal(loteId, protocolo)
**Função**: Verifica protocolo específico
**Chamado por**: Botão verificar protocolo

### mostrarToast(mensagem, tipo)
**Função**: Exibe toast via SweetAlert2
**Chamado por**: Múltiplas ações

### carregarDadosEstoqueAssincrono(numPedido)
**Função**: Carrega estoque dos produtos
**Chamado por**: Expansão de pedido

### atualizarViewCompactaDireto(loteId, expedicao, agendamento, protocolo, agendamentoConfirmado)
**Função**: Atualiza view compacta sem re-renderizar
**Chamado por**: salvarEdicaoDatas()

---

## 📁 carteira-agrupada.js

### constructor()
**Função**: Inicializa CarteiraAgrupada com configurações
**Chamado por**: Instanciação global

### init()
**Função**: Inicializa componentes e event listeners
**Chamado por**: DOMContentLoaded

### initWorkspace()
**Função**: Cria instância do WorkspaceMontagem
**Chamado por**: init()

### setupEventListeners()
**Função**: Configura eventos globais
**Chamado por**: init()

### setupFiltros()
**Função**: Configura eventos de filtros
**Chamado por**: setupEventListeners()

### initBadgesFiltros()
**Função**: Inicializa badges de filtros
**Chamado por**: init()

### toggleBadgeFiltro(badge)
**Função**: Ativa/desativa badge de filtro
**Chamado por**: Click em badge

### verificarSubrotasSP()
**Função**: Verifica se deve mostrar subrotas SP
**Chamado por**: toggleBadgeFiltro()

### mostrarSubrotasSP()
**Função**: Exibe container de subrotas SP
**Chamado por**: verificarSubrotasSP()

### esconderSubrotasSP()
**Função**: Oculta container de subrotas SP
**Chamado por**: verificarSubrotasSP()

### atualizarBotoesLimpar()
**Função**: Atualiza visibilidade botões limpar
**Chamado por**: toggleBadgeFiltro()

### toggleAgendamento(badge, valor)
**Função**: Gerencia filtro de agendamento
**Chamado por**: toggleBadgeFiltro()

### limparFiltrosRotas()
**Função**: Limpa filtros de rotas
**Chamado por**: Botão limpar rotas

### limparFiltrosSubrotas()
**Função**: Limpa filtros de subrotas
**Chamado por**: Botão limpar subrotas

### limparFiltrosAgendamento()
**Função**: Limpa filtros de agendamento
**Chamado por**: Botão limpar agendamento

### mostrarAlerta(mensagem)
**Função**: Exibe alerta temporário
**Chamado por**: toggleBadgeFiltro()

### setupExpandirColapsar()
**Função**: Configura botões expandir/colapsar
**Chamado por**: setupEventListeners()

### setupDetalhesExpansao()
**Função**: Configura expansão de detalhes
**Chamado por**: setupEventListeners()

### initDropdownSeparacoes()
**Função**: Inicializa dropdown de separações
**Chamado por**: init()

### aplicarFiltros()
**Função**: Aplica todos filtros ativos
**Chamado por**: Mudanças em filtros

### popularFiltroEquipes()
**Função**: Popula dropdown de equipes
**Chamado por**: init()

### atualizarContador(totalVisiveis)
**Função**: Atualiza contador de pedidos visíveis
**Chamado por**: aplicarFiltros()

### atualizarValorTotal()
**Função**: Calcula e exibe valor total visível
**Chamado por**: aplicarFiltros()

### expandirTodos()
**Função**: Expande todos pedidos
**Chamado por**: Botão expandir todos

### colapsarTodos()
**Função**: Colapsa todos pedidos
**Chamado por**: Botão colapsar todos

### toggleDetalhes(numPedido)
**Função**: Alterna expansão de detalhes
**Chamado por**: Click no pedido

### expandirDetalhes(numPedido, detalhesRow, icon)
**Função**: Expande detalhes e carrega workspace
**Chamado por**: toggleDetalhes()

### colapsarDetalhes(detalhesRow, icon)
**Função**: Colapsa detalhes do pedido
**Chamado por**: toggleDetalhes()

### formatarMoeda(valor)
**Função**: Formata valor monetário BRL
**Chamado por**: Renderização de valores

### formatarQuantidade(qtd)
**Função**: Formata quantidade com separador de milhar
**Chamado por**: Renderização de quantidades

### isPedidoVisivel(numPedido)
**Função**: Verifica se pedido está visível
**Chamado por**: Verificações de visibilidade

### cancelarTodasRequisicoes()
**Função**: Cancela requests pendentes
**Chamado por**: Navegação/fechamento

### formatarData(data)
**Função**: Converte data para dd/mm/yyyy
**Chamado por**: Renderização de datas

### formatarPeso(peso)
**Função**: Formata peso via workspaceQuantidades
**Chamado por**: Renderização de pesos

### formatarPallet(pallet)
**Função**: Formata pallets via workspaceQuantidades
**Chamado por**: Renderização de pallets

### carregarSeparacoesEmLoteUnico(pedidos)
**Função**: Carrega separações em batch
**Chamado por**: carregarTodasSeparacoesCompactas()

### renderizarSeparacaoDoCache(numPedido)
**Função**: Renderiza separações do cache
**Chamado por**: carregarSeparacoesEmLoteUnico()

### carregarTodasSeparacoesCompactas()
**Função**: Carrega todas separações compactas
**Chamado por**: init()

### carregarSeparacoesCompactasVisiveis()
**Função**: Carrega separações dos pedidos visíveis
**Chamado por**: aplicarFiltros()

### renderizarSeparacoesCompactas(separacoesData)
**Função**: Renderiza HTML de separações compactas
**Chamado por**: renderizarSeparacaoDoCache()

### renderizarLinhaSeparacaoCompacta(item)
**Função**: Renderiza linha individual de separação
**Chamado por**: renderizarSeparacoesCompactas()

### carregarEstoqueAssincrono(numPedido, itens)
**Função**: Carrega estoque dos itens
**Chamado por**: expandirDetalhes()

### abrirModalDatas(loteId, isSeparacao, expedicao, agendamento, protocolo, agendamentoConfirmado)
**Função**: Abre modal de edição de datas
**Chamado por**: Botão datas compacta

### alterarStatusSeparacao(loteId, novoStatus)
**Função**: Altera status via API
**Chamado por**: Botão confirmar/reverter compacta

### agendarPortal(loteId, dataAgendamento)
**Função**: Agenda no portal via workspace
**Chamado por**: Botão agendar compacta

### verificarAgendamento(loteId, protocolo)
**Função**: Verifica protocolo via workspace
**Chamado por**: Botão verificar protocolo compacta

### verificarAgendasEmLote()
**Função**: Verifica múltiplos protocolos
**Chamado por**: Botão verificar em lote

### iniciarPollingVerificacao(taskId)
**Função**: Polling de task assíncrona
**Chamado por**: verificarAgendasEmLote()

### atualizarContadorProtocolos()
**Função**: Atualiza contador de protocolos pendentes
**Chamado por**: init(), após verificações

### atualizarContadorPendentesTotal()
**Função**: Atualiza contador total de pendentes
**Chamado por**: atualizarContadorProtocolos()

### verificarTodosProtocolosPendentes()
**Função**: Verifica todos protocolos pendentes
**Chamado por**: Botão verificar todos

### iniciarPollingVerificacaoDetalhado(taskId)
**Função**: Polling com detalhes em modal
**Chamado por**: verificarTodosProtocolosPendentes()

### carregarEstoqueComPrioridade(numPedido, itens, prioridade)
**Função**: Adiciona à fila de estoque com prioridade
**Chamado por**: expandirDetalhes()

### processarFilaEstoque()
**Função**: Processa fila de carregamento de estoque
**Chamado por**: carregarEstoqueComPrioridade()

### setupInterceptadorBotoes()
**Função**: Intercepta clicks para pausar processamento
**Chamado por**: init()

### atualizarSeparacaoCompacta(loteId, dadosAtualizados)
**Função**: Atualiza dados da separação compacta em memória
**Chamado por**: workspace.atualizarViewCompactaDireto()

---

## FUNÇÕES GLOBAIS

### excluirSeparacaoGlobal(loteId)
**Função**: Exclui separação com confirmação
**Chamado por**: Botão excluir UI

### confirmarSeparacaoGlobal(loteId)
**Função**: Confirma separação via separacaoManager
**Chamado por**: Botão confirmar UI

### abrirProdutosExpandido(numPedido)
**Função**: Expande workspace se detalhes visível
**Chamado por**: Botão expandir produtos

### abrirModalEndereco(numPedido)
**Função**: Abre modal de endereço
**Chamado por**: Botão endereço

---

## CHAMADAS INTER-ARQUIVOS PRINCIPAIS

1. **carteiraAgrupada → workspace**:
   - initWorkspace()
   - expandirDetalhes() → abrirWorkspace()
   - agendarPortal() → agendarNoPortal()
   - verificarAgendamento() → verificarProtocoloNoPortal()

2. **workspace → loteManager**:
   - init() → new LoteManager()
   - adicionarProdutosSelecionados() → adicionarProdutoNoLote()
   - salvarEdicaoDatas() → atualizarCardLote()

3. **loteManager → workspace**:
   - removerProdutoDoLote() → onclick handler
   - Botões do card → métodos do workspace

4. **workspace → carteiraAgrupada**:
   - atualizarViewCompactaDireto() → atualizarSeparacaoCompacta()

5. **Dependências externas**:
   - window.workspaceQuantidades (cálculos)
   - window.separacaoManager (operações)
   - window.modalSeparacoes (modais)
   - window.DropdownSeparacoes (UI)
