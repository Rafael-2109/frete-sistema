# 🗺️ MAPEAMENTO COMPLETO - listar_agrupados.html

**Arquivo**: `app/templates/carteira/listar_agrupados.html`  
**Data de Criação**: 22/07/2025  
**Objetivo**: Mapeamento completo de todas as funções JavaScript e suas conexões com APIs/Backend

---

## 📋 ÍNDICE
1. [Funções de Toggle/Expansão](#1-funções-de-toggleexpansão)
2. [Funções de Carregamento de Dados](#2-funções-de-carregamento-de-dados)
3. [Funções de Processamento e Edição](#3-funções-de-processamento-e-edição)
4. [Funções de Cálculo e Validação](#4-funções-de-cálculo-e-validação)
5. [Funções de Modais](#5-funções-de-modais)
6. [Funções de Separação](#6-funções-de-separação)
7. [Funções de Exportação](#7-funções-de-exportação)
8. [Funções de Pré-Separação](#8-funções-de-pré-separação)
9. [Funções Auxiliares](#9-funções-auxiliares)

---

## 1. FUNÇÕES DE TOGGLE/EXPANSÃO

### `togglePedidoItens(numPedido)`
**Linha**: ~1067  
**Descrição**: Alterna visualização de itens de um pedido (dropdown)  
**API**: Não utiliza API diretamente  
**Comportamento**: Manipula DOM para mostrar/ocultar linha de itens

### `toggleSeparacoesPedido(numPedido)`
**Linha**: ~1663  
**Descrição**: Alterna visualização de separações de um pedido  
**API**: Não utiliza API diretamente  
**Comportamento**: Manipula DOM para mostrar/ocultar separações

### `toggleTodosItensDropdown(numPedido, selectAll)`
**Linha**: ~1449  
**Descrição**: Marca/desmarca todos checkboxes de itens do pedido  
**API**: Não utiliza API diretamente

### `toggleTodosItensEditaveis(selectAll)`
**Linha**: ~4802  
**Descrição**: Marca/desmarca todos checkboxes no modal de itens editáveis  
**API**: Não utiliza API diretamente

### `toggleTodosItens(masterCheckbox)`
**Linha**: ~2900  
**Descrição**: Marca/desmarca todos checkboxes no modal de avaliação  
**API**: Não utiliza API diretamente

### `toggleTodosAgrupamentos(checkbox)`
**Linha**: ~4098  
**Descrição**: Marca/desmarca todos checkboxes de agrupamentos  
**API**: Não utiliza API diretamente

### `toggleTodosItensSeparacao(masterCheckbox)`
**Linha**: ~3851  
**Descrição**: Marca/desmarca todos checkboxes no modal de criação de separação  
**API**: Não utiliza API diretamente

---

## 2. FUNÇÕES DE CARREGAMENTO DE DADOS

### `carregarItensPedido(numPedido)`
**Linha**: ~1092  
**API**: `/carteira/api/pedido/${numPedido}/itens-editaveis`  
**Backend**: `api_pedido_itens_editaveis()` - routes.py:2757  
**Método**: GET  
**Retorno**: JSON com itens do pedido e pré-separações

### `carregarSeparacoesPedidoInline(numPedido)`
**Linha**: ~1688  
**API**: `/carteira/api/pedido/${numPedido}/separacoes`  
**Backend**: `api_separacoes_pedido()` - routes.py:1030  
**Método**: GET  
**Retorno**: JSON com separações do pedido

### `carregarDadosModal(numPedido)`
**Linha**: ~2238  
**API**: `/carteira/api/pedido/${numPedido}/estoque-projetado-28-dias`  
**Backend**: `api_estoque_projetado_28_dias()` - routes.py:3373  
**Método**: GET  
**Retorno**: JSON com projeção de estoque 28 dias

### `carregarDadosAgendamento(numPedido)`
**Linha**: ~2449  
**APIs**:
- `/carteira/api/pedido/${numPedido}/itens` - routes.py:925
- `/carteira/api/pedido/${numPedido}/agendamento-existente` - routes.py:4187  
**Método**: GET  
**Retorno**: Dados de itens e agendamento existente

### `carregarEstoqueD0D7(numPedido)`
**Linha**: ~2672  
**API**: `/carteira/api/pedido/${numPedido}/estoque-d0-d7`  
**Backend**: `api_estoque_d0_d7_pedido()` - routes.py:1203  
**Método**: GET  
**Retorno**: JSON com análise de estoque D0/D7

### `carregarDadosEstoque(numPedido)`
**Linha**: ~3152  
**API**: `/carteira/api/pedido/${numPedido}/estoque-d0-d7`  
**Backend**: `api_estoque_d0_d7_pedido()` - routes.py:1203  
**Método**: GET  
**Retorno**: JSON com dados de estoque

### `carregarSeparacoesPedido(numPedido)`
**Linha**: ~3401  
**API**: `/carteira/api/pedido/${numPedido}/separacoes`  
**Backend**: `api_separacoes_pedido()` - routes.py:1030  
**Método**: GET  
**Retorno**: JSON com separações do pedido

### `carregarDadosModalEditavel(numPedido)`
**Linha**: ~4314  
**API**: `/carteira/api/pedido/${numPedido}/itens-editaveis`  
**Backend**: `api_pedido_itens_editaveis()` - routes.py:2757  
**Método**: GET  
**Retorno**: JSON com itens editáveis e pré-separações

### `carregarItensParaSeparacao(numPedido)`
**Linha**: ~3791  
**API**: `/carteira/api/pedido/${numPedido}/itens-editaveis`  
**Backend**: `api_pedido_itens_editaveis()` - routes.py:2757  
**Método**: GET  
**Retorno**: JSON com itens para criar separação

### `carregarItensEPreSeparacoes(numPedido)`
**Linha**: ~3926  
**APIs**:
- `/carteira/api/pedido/${numPedido}/itens-editaveis` - routes.py:2757
- `/carteira/api/pedido/${numPedido}/pre-separacoes-agrupadas` - routes.py:3502  
**Método**: GET  
**Retorno**: Itens e pré-separações agrupadas

---

## 3. FUNÇÕES DE PROCESSAMENTO E EDIÇÃO

### `processarAlteracaoQuantidadeDropdown(input)`
**Linha**: ~1299  
**Comportamento**: Processa alteração de quantidade no dropdown  
**API**: Não chama API diretamente (apenas validações locais)

### `processarAlteracaoDataExpedicaoDropdown(input)`
**Linha**: ~1334  
**Comportamento**: Processa alteração de data expedição no dropdown  
**API**: Não chama API diretamente

### `processarAlteracaoAgendamentoDropdown(input)`
**Linha**: ~1357  
**Comportamento**: Processa alteração de agendamento no dropdown  
**API**: Não chama API diretamente

### `processarAlteracaoProtocoloDropdown(input)`
**Linha**: ~1372  
**Comportamento**: Processa alteração de protocolo no dropdown  
**API**: Não chama API diretamente

### `processarAlteracaoQuantidade(input)`
**Linha**: ~4448  
**Comportamento**: Processa alteração de quantidade no modal editável  
**API**: Não chama API diretamente (validações locais)

### `processarAlteracaoDataExpedicao(input)`
**Linha**: ~4540  
**Comportamento**: Processa alteração de data expedição  
**API**: Não chama API diretamente

### `processarAlteracaoAgendamento(input)`
**Linha**: ~4822  
**Comportamento**: Processa alteração de agendamento  
**API**: Não chama API diretamente

### `processarAlteracaoProtocolo(input)`
**Linha**: ~4836  
**Comportamento**: Processa alteração de protocolo  
**API**: Não chama API diretamente

### `salvarAlteracaoAutomatica(itemId, campo, valor)`
**Linha**: ~4770  
**API**: `/carteira/api/item/${itemId}/salvar-alteracao`  
**Backend**: `api_salvar_alteracao_item()` - routes.py:3845  
**Método**: POST  
**Dados**: { campo, valor }

### `editarCampoPreSeparacao(element, campo)`
**Linha**: ~4956  
**API**: `/carteira/api/pre-separacao/${preSeparacaoId}/editar`  
**Backend**: `api_editar_pre_separacao()` - routes.py:3129  
**Método**: POST  
**Dados**: { campo, valor }

### `editarQuantidadePreSeparacao(element)`
**Linha**: ~5004  
**Comportamento**: Edita quantidade de pré-separação  
**API**: Chama `editarCampoPreSeparacao()`

### `editarDataPreSeparacao(element, campo)`
**Linha**: ~4997  
**Comportamento**: Edita data de pré-separação  
**API**: Chama `editarCampoPreSeparacao()`

---

## 4. FUNÇÕES DE CÁLCULO E VALIDAÇÃO

### `atualizarContadoresDropdown(numPedido)`
**Linha**: ~1159  
**Descrição**: Atualiza contadores de itens selecionados no dropdown  
**API**: Não utiliza API

### `recalcularTotaisDropdown(numPedido)`
**Linha**: ~1209  
**Descrição**: Recalcula totais (valor, peso, pallets) no dropdown  
**API**: Não utiliza API

### `recalcularValoresDropdown(input)`
**Linha**: ~1255  
**Descrição**: Recalcula valores ao alterar quantidade no dropdown  
**API**: Não utiliza API

### `recalcularEstoquesBaseadoD0Dropdown(itemId, dataExpedicao, numPedido)`
**Linha**: ~1413  
**API**: `/carteira/api/item/${itemId}/recalcular-estoques`  
**Backend**: `api_recalcular_estoques_item()` - routes.py:3751  
**Método**: POST  
**Dados**: { data_expedicao }

### `recalcularEstoquesBaseadoD0(itemId, dataExpedicao)`
**Linha**: ~4562  
**API**: `/carteira/api/item/${itemId}/recalcular-estoques`  
**Backend**: `api_recalcular_estoques_item()` - routes.py:3751  
**Método**: POST  
**Dados**: { data_expedicao }

### `validarQuantidade(input)`
**Linha**: ~2911  
**Descrição**: Valida quantidade máxima permitida  
**API**: Não utiliza API

### `calcularTotaisModal()`
**Linha**: ~2940  
**Descrição**: Calcula totais no modal de avaliação  
**API**: Não utiliza API

### `atualizarCalculosItem(input)`
**Linha**: ~2393  
**Descrição**: Atualiza cálculos ao alterar quantidade  
**API**: Não utiliza API

### `recalcularValoresItem(itemId, qtdNova)`
**Linha**: ~4850  
**Descrição**: Recalcula valores de um item  
**API**: Não utiliza API

### `validarEnvioParcial()`
**Linha**: ~3741  
**Descrição**: Valida envio parcial de separação  
**API**: Não utiliza API

### `atualizarContadoresModalEditavel()`
**Linha**: ~4626  
**Descrição**: Atualiza contadores no modal editável  
**API**: Não utiliza API

### `atualizarValidacaoEnvioSeparacao()`
**Linha**: ~4645  
**Descrição**: Valida condições para envio à separação  
**API**: Não utiliza API

### `atualizarContadorAgrupamentos()`
**Linha**: ~4109  
**Descrição**: Atualiza contador de agrupamentos selecionados  
**API**: Não utiliza API

---

## 5. FUNÇÕES DE MODAIS

### `abrirModalAvaliarEstoques(numPedido)`
**Linha**: ~2180  
**Descrição**: Abre modal de avaliação de estoques  
**API**: Carrega dados via `carregarDadosModal()`

### `abrirModalEndereco(numPedido)`
**Linha**: ~4261  
**API**: `/carteira/item/${numPedido}/endereco`  
**Backend**: `buscar_endereco_pedido()` - routes.py:1300  
**Método**: GET  
**Retorno**: JSON com dados de endereço

### `solicitarAgendamento(numPedido)`
**Linha**: ~4249  
**Descrição**: Abre modal de agendamento  
**API**: Carrega dados via `carregarDadosAgendamento()`

### `calcularEstoqueD0D7(numPedido)`
**Linha**: ~3128  
**Descrição**: Abre modal de estoque D0/D7  
**API**: Carrega dados via `carregarEstoqueD0D7()`

### `consultarSeparacoes(numPedido)`
**Linha**: ~3383  
**Descrição**: Abre modal de separações  
**API**: Carrega dados via `carregarSeparacoesPedido()`

### `criarSeparacao(numPedido)`
**Linha**: ~3775  
**Descrição**: Abre modal para criar separação  
**API**: Carrega dados via `carregarItensParaSeparacao()`

### `editarItem(itemId)`
**Linha**: ~2160  
**Descrição**: Abre modal de edição de item  
**Comportamento**: Busca pedido e abre modal

### `recarregarModalItens()`
**Linha**: ~3116  
**Descrição**: Recarrega modal de itens  
**API**: Chama `carregarDadosModal()`

### `recarregarModalEstoque()`
**Linha**: ~3320  
**Descrição**: Recarrega modal de estoque  
**API**: Chama `carregarDadosEstoque()`

### `recarregarModalSeparacoes()`
**Linha**: ~3474  
**Descrição**: Recarrega modal de separações  
**API**: Chama `carregarSeparacoesPedido()`

### `recarregarModalEditavel()`
**Linha**: ~4813  
**Descrição**: Recarrega modal editável  
**API**: Chama `carregarDadosModalEditavel()`

---

## 6. FUNÇÕES DE SEPARAÇÃO

### `enviarParaSeparacaoDropdown(numPedido)`
**Linha**: ~1460  
**API**: `/carteira/api/pedido/${numPedido}/criar-separacao`  
**Backend**: `api_criar_separacao_pedido()` - routes.py:4062  
**Método**: POST  
**Dados**: { itens_selecionados, tipo_envio, observacoes }

### `enviarParaSeparacao()`
**Linha**: ~4678  
**API**: `/carteira/api/pedido/${numPedidoEditavel}/criar-separacao`  
**Backend**: `api_criar_separacao_pedido()` - routes.py:4062  
**Método**: POST  
**Dados**: { itens_selecionados, tipo_envio, observacoes }

### `confirmarCriacaoSeparacao()`
**Linha**: ~3858  
**API**: `/carteira/api/pedido/${numPedido}/criar-separacao`  
**Backend**: `api_criar_separacao_pedido()` - routes.py:4062  
**Método**: POST  
**Dados**: { itens_selecionados, tipo_envio, observacoes }

### `criarPreSeparacaoItem(itemId, qtdUtilizada, numPedido)`
**Linha**: ~4916  
**API**: `/carteira/api/pedido/${numPedido}/criar-pre-separacao`  
**Backend**: `api_criar_pre_separacao()` - routes.py:3030  
**Método**: POST  
**Dados**: { item_id, quantidade }

### `verDetalhesSeparacao(loteId)`
**Linha**: ~3484  
**API**: `/carteira/api/separacao/${loteId}/detalhes`  
**Backend**: `api_separacao_detalhes()` - routes.py:2404  
**Método**: GET  
**Retorno**: JSON com detalhes da separação

### `editarSeparacao(loteId)`
**Linha**: ~3552  
**APIs**:
- `/carteira/api/separacao/${loteId}/detalhes` - routes.py:2404
- `/carteira/api/separacao/${loteId}/editar` - routes.py:2512  
**Método**: GET/POST  
**Comportamento**: Carrega dados e permite edição

### `cancelarPreSeparacao(preSeparacaoId)`
**Linha**: ~5029  
**API**: `/carteira/api/pre-separacao/${preSeparacaoId}/cancelar`  
**Backend**: `api_cancelar_pre_separacao()` - routes.py:3235  
**Método**: POST

### `enviarPreSeparacaoParaSeparacao(preSeparacaoId)`
**Linha**: ~5071  
**API**: `/carteira/api/pre-separacao/${preSeparacaoId}/enviar-separacao`  
**Backend**: `api_enviar_pre_separacao_para_separacao()` - routes.py:3290  
**Método**: POST  
**Dados**: { observacoes }

### `enviarAgrupamentosParaSeparacao(numPedido)`
**Linha**: ~4162  
**API**: `/carteira/api/agrupamentos/enviar-separacao`  
**Backend**: `api_enviar_agrupamentos_para_separacao()` - routes.py:3633  
**Método**: POST  
**Dados**: { agrupamentos_ids, num_pedido }

---

## 7. FUNÇÕES DE EXPORTAÇÃO

### `exportarAnaliseEstoque()`
**Linha**: ~2816  
**API**: `/carteira/api/export-excel/estoque-analise/${numPedidoEstoque}`  
**Backend**: `api_export_excel_estoque_analise()` - routes.py:2073  
**Método**: GET  
**Retorno**: Arquivo Excel

### `verDetalhesEstoque(codProduto)`
**Linha**: ~2858  
**API**: `/carteira/api/export-excel/produto-detalhes/${codProduto}`  
**Backend**: `api_export_excel_produto_detalhes()` - routes.py:2280  
**Método**: GET  
**Retorno**: Arquivo Excel

### `exportarDadosEstoque()`
**Linha**: ~3330  
**API**: `/carteira/api/export-excel/estoque-dados/${numPedidoEstoque}`  
**Backend**: `api_export_excel_estoque_dados()` - routes.py:2174  
**Método**: GET  
**Retorno**: Arquivo Excel

### `salvarAgendamento()`
**Linha**: ~2558  
**APIs**:
- `/carteira/api/pedido/${numPedido}/itens` - routes.py:925
- `/carteira/item/${itemId}/agendamento` - routes.py:382  
**Método**: GET/POST  
**Comportamento**: Salva agendamento de itens

### `salvarAvaliacoes()`
**Linha**: ~2980  
**API**: `/carteira/api/pedido/${numPedidoModal}/salvar-avaliacoes`  
**Backend**: `api_salvar_avaliacoes()` - routes.py:1574  
**Método**: POST  
**Dados**: { avaliacoes }

---

## 8. FUNÇÕES DE PRÉ-SEPARAÇÃO

### `dividirLinhaDropdown(itemId, qtdUtilizada, qtdOriginal, numPedido)`
**Linha**: ~1639  
**Descrição**: Divide linha no dropdown  
**Comportamento**: Lógica local de divisão

### `unificarLinhaDropdown(itemId, numPedido)`
**Linha**: ~1648  
**Descrição**: Unifica linha no dropdown  
**Comportamento**: Lógica local de unificação

### `dividirLinhaItem(itemId, qtdUtilizada, qtdOriginal)`
**Linha**: ~4483  
**API**: `/carteira/api/item/${itemId}/dividir-linha`  
**Backend**: `api_dividir_linha_item()` - routes.py:3941  
**Método**: POST  
**Dados**: { qtd_utilizada }

### `unificarLinhaItem(itemId)`
**Linha**: ~4874  
**Descrição**: Unifica linha de item  
**Comportamento**: Remove flags de divisão

### `criarNovaLinhaItem(itemIdOriginal, qtdRestante)`
**Linha**: ~4500  
**Descrição**: Cria nova linha após divisão  
**Comportamento**: Clona linha no DOM

### `mostrarDetalhesAgrupamento(agrupamentoId)`
**Linha**: ~4127  
**Descrição**: Mostra detalhes de agrupamento  
**Comportamento**: Manipula DOM para exibir detalhes

### `editarPreSeparacao(preSeparacaoId)`
**Linha**: ~5129  
**Descrição**: Placeholder para edição completa  
**Status**: TODO - não implementado

---

## 9. FUNÇÕES AUXILIARES

### `replicarCampoParaItensAmarradosDropdown(numPedido, classeCampo, valor)`
**Linha**: ~1387  
**Descrição**: Replica valor para itens marcados no dropdown  
**Comportamento**: Atualiza múltiplos campos simultaneamente

### `replicarCamposAmarradosDropdown(numPedido)`
**Linha**: ~1558  
**Descrição**: Replica todos os campos amarrados no dropdown  
**Comportamento**: Copia valores entre itens selecionados

### `replicarCampoParaItensAmarrados(classeCampo, valor)`
**Linha**: ~4600  
**Descrição**: Replica campo para itens amarrados no modal  
**Comportamento**: Atualiza múltiplos campos

### `atualizarTipoEnvio()`
**Linha**: ~3675  
**Descrição**: Atualiza interface baseado no tipo de envio  
**Comportamento**: Mostra/oculta campos condicionalmente

### `getStatusClass(status)`
**Linha**: ~3290  
**Descrição**: Retorna classe CSS baseada no status  
**Retorno**: String com classe CSS

### `formatarStatus(status)`
**Linha**: ~3305  
**Descrição**: Formata texto do status  
**Retorno**: String formatada

### `showNotification(message, type)`
**Linha**: ~5137  
**Descrição**: Exibe notificação ao usuário  
**Implementação**: Básica com alert()

### `formatarData(data)`
**Linha**: ~5207  
**Descrição**: Formata data para exibição  
**Formato**: DD/MM/YYYY

### `formatarMoeda(valor)`
**Linha**: ~5217  
**Descrição**: Formata valor monetário  
**Formato**: R$ X.XXX,XX

---

## 10. FUNÇÕES GERADORAS DE HTML

### `gerarHtmlItens(data)`
**Linha**: ~1903  
**Descrição**: Gera HTML para tabela de itens do pedido  
**Retorno**: HTML string

### `gerarHtmlSeparacoes(data)`
**Linha**: ~1772  
**Descrição**: Gera HTML para tabela de separações  
**Retorno**: HTML string

### `gerarHtmlItensModal(data)`
**Linha**: ~2294  
**Descrição**: Gera HTML para modal de avaliação  
**Retorno**: Popula tbody diretamente

### `gerarTabelaAgendamento(data)`
**Linha**: ~2538  
**Descrição**: Gera tabela de agendamento  
**Retorno**: Popula tbody diretamente

### `gerarTabelaEstoqueReal(itens)`
**Linha**: ~2731  
**Descrição**: Gera tabela de estoque real  
**Retorno**: Popula tbody diretamente

### `gerarHtmlEstoqueProdutos(data)`
**Linha**: ~3202  
**Descrição**: Gera HTML para produtos com estoque  
**Retorno**: Popula tbody diretamente

### `gerarTabelaItensEditaveis(data)`
**Linha**: ~4366  
**Descrição**: Gera tabela de itens editáveis  
**Retorno**: Popula tbody diretamente

### `gerarTabelaItensSeparacao(itens, numPedido)`
**Linha**: ~3808  
**Descrição**: Gera tabela para criação de separação  
**Retorno**: Popula tbody diretamente

### `adicionarSecaoPreSeparacoesAgrupadas(agrupamentos, numPedido)`
**Linha**: ~3987  
**Descrição**: Adiciona seção de pré-separações agrupadas  
**Retorno**: Adiciona HTML ao modal

---

## 11. FUNÇÕES DE ATUALIZAÇÃO DE RESUMO

### `atualizarResumoModal(data)`
**Linha**: ~2382  
**Descrição**: Atualiza resumo no modal de avaliação  
**Elementos**: total_itens, qtd_total, valor_total

### `atualizarResumoEstoque(data)`
**Linha**: ~3268  
**Descrição**: Atualiza resumo de estoque  
**Elementos**: Estatísticas de disponibilidade

### `atualizarResumoSeparacoes(data)`
**Linha**: ~3465  
**Descrição**: Atualiza resumo de separações  
**Elementos**: total_separacoes, qtd_total, valor_total

---

## 📊 RESUMO DE INTEGRAÇÕES

### Endpoints Mais Utilizados:
1. **`/carteira/api/pedido/{id}/itens-editaveis`** - 4 utilizações
2. **`/carteira/api/pedido/{id}/criar-separacao`** - 3 utilizações
3. **`/carteira/api/pedido/{id}/separacoes`** - 3 utilizações
4. **`/carteira/api/pedido/{id}/estoque-d0-d7`** - 2 utilizações
5. **`/carteira/api/item/{id}/recalcular-estoques`** - 2 utilizações

### Padrões de Nomenclatura:
- Funções com sufixo `Dropdown`: Operam no dropdown inline
- Funções com sufixo `Modal`: Operam em modais
- Funções com prefixo `gerar`: Criam HTML dinamicamente
- Funções com prefixo `atualizar`: Atualizam interface/cálculos
- Funções com prefixo `processar`: Processam alterações de dados
- Funções com prefixo `carregar`: Fazem requisições AJAX

### Fluxos Principais:
1. **Visualização**: Toggle → Carregar → Gerar HTML → Exibir
2. **Edição**: Processar → Validar → Salvar (auto ou manual)
3. **Separação**: Selecionar → Validar → Criar → Recarregar
4. **Exportação**: Configurar → Requisitar → Download

---

## 🔧 NOTAS TÉCNICAS

### Gerenciamento de Estado:
- **Variables globais**: 
  - `numPedidoModal`, `numPedidoEstoque`, `numPedidoSeparacoes`
  - `numPedidoEditavel`, `pedidoAtualSeparacao`
  - `dadosModalAtual`, `agrupamentosData`

### Validações Importantes:
- Quantidade máxima baseada em `data-max`
- Divisão de linha quando qtd < original
- Tipo de envio (total/parcial) afeta validações
- Campos obrigatórios para separação

### Otimizações:
- Uso de Promise.all para requisições paralelas
- Debounce implícito em algumas alterações
- Cache de dados em variáveis globais

---

**🚨 IMPORTANTE**: Este mapeamento deve ser atualizado sempre que houver mudanças significativas em listar_agrupados.html ou routes.py

---

## 🔍 ANÁLISE CRÍTICA - VALIDAÇÃO DE FUNCIONALIDADE

**Data da Análise**: 22/07/2025  
**Contexto**: Avaliação no contexto de fluxo de processo de supply chain

### ✅ CAMPOS UTILIZADOS CORRETAMENTE

Após análise detalhada comparando com CLAUDE.md, os seguintes campos estão sendo usados corretamente:
- `expedicao` ✅ (não data_expedicao_pedido)
- `agendamento` ✅ (não data_agendamento_pedido)
- `protocolo` ✅
- `observ_ped_1` ✅
- `qtd_produto_pedido` ✅
- `qtd_saldo_produto_pedido` ✅
- `data_entrega_pedido` ✅

### 🔴 REDUNDÂNCIAS IDENTIFICADAS

#### 1. **Funções de Recálculo de Estoque Duplicadas**
- `recalcularEstoquesBaseadoD0Dropdown()` (linha ~1413)
- `recalcularEstoquesBaseadoD0()` (linha ~4562)

**Problema**: Mesma funcionalidade implementada duas vezes para contextos diferentes (dropdown vs modal)  
**Solução**: Criar função única `recalcularEstoquesBaseadoD0(itemId, dataExpedicao, callback)`

#### 2. **Funções de Processamento de Alterações**
- 8 funções `processar*` que não chamam API diretamente
- Todas fazem apenas validação local

**Problema**: Lógica de validação duplicada sem persistência  
**Solução**: Centralizar validações e garantir salvamento automático

#### 3. **Múltiplas Funções de Toggle**
- 7 funções diferentes de toggle fazendo essencialmente a mesma coisa

**Problema**: Código repetitivo  
**Solução**: Função genérica `toggleCheckboxes(containerSelector, masterCheckbox)`

#### 4. **Carregamento de Estoque D0/D7**
- `carregarEstoqueD0D7()` (linha ~2672)
- `carregarDadosEstoque()` (linha ~3152)

**Problema**: Ambas chamam a mesma API  
**Solução**: Unificar em uma única função

### 🟡 PROBLEMAS FUNCIONAIS NO CONTEXTO SUPPLY CHAIN

#### 1. **Falta de Validação de Datas Críticas**
**Problema**: Não há validação se data de expedição < data de agendamento  
**Impacto**: Pode gerar inconsistências no planejamento logístico

#### 2. **Cálculo de Estoque sem Considerar Lead Time**
**Problema**: `recalcularEstoquesBaseadoD0()` não considera tempo de produção/transporte  
**Impacto**: Promessas de entrega irreais

#### 3. **Divisão de Linha sem Rastreabilidade**
**Problema**: `dividirLinhaItem()` não mantém histórico de divisões  
**Impacto**: Perda de rastreabilidade para auditoria

#### 4. **Notificações Básicas com alert()**
**Problema**: `showNotification()` usa alert() nativo  
**Impacto**: UX ruim, bloqueia interface

#### 5. **Salvamento Automático sem Feedback**
**Problema**: `salvarAlteracaoAutomatica()` não indica sucesso/falha visualmente  
**Impacto**: Usuário não sabe se alteração foi salva

### 🟠 INCONSISTÊNCIAS DE FLUXO

#### 1. **Estados de Separação Não Sincronizados**
- Múltiplas funções criam separações mas não atualizam estado global
- Risco de criar separações duplicadas

#### 2. **Validação de Quantidade Disponível**
- Validação apenas no frontend
- Backend deveria revalidar para evitar overselling

#### 3. **Agrupamento de Pré-Separações**
- Lógica complexa sem documentação clara
- Dificulta manutenção e pode gerar erros de agrupamento

### 💡 RECOMENDAÇÕES PARA OTIMIZAÇÃO

#### 1. **Implementar Service Layer JavaScript**
```javascript
// Exemplo de centralização
const CarteiraService = {
    recalcularEstoque: async (itemId, dataExpedicao) => {
        // Lógica única
    },
    
    validarDatasLogisticas: (expedicao, agendamento) => {
        // Validação centralizada
    }
};
```

#### 2. **Adicionar Cache Inteligente**
- Implementar cache com TTL para dados de estoque
- Reduzir chamadas desnecessárias à API

#### 3. **Melhorar Feedback Visual**
- Substituir alert() por toast notifications
- Indicadores de loading em todas operações assíncronas

#### 4. **Implementar Audit Trail**
- Log de todas alterações críticas
- Histórico de divisões/unificações de linha

#### 5. **Validação Dupla (Frontend + Backend)**
- Manter validações frontend para UX
- Backend sempre revalidar dados críticos

### 📊 MÉTRICAS DE COMPLEXIDADE

- **Total de Funções**: 90+
- **Funções Redundantes**: ~15 (16%)
- **Funções sem Persistência**: ~12 (13%)
- **APIs Mais Chamadas**: 
  - `itens-editaveis`: 4x (possível otimização com cache)
  - `criar-separacao`: 3x (OK - diferentes contextos)

### 🚨 RISCOS CRÍTICOS

1. **Concorrência**: Múltiplos usuários editando mesmo pedido
2. **Integridade**: Validações apenas frontend
3. **Performance**: Muitas chamadas AJAX sem cache
4. **Manutenibilidade**: Código duplicado dificulta evolução

### ✅ PONTOS POSITIVOS

1. **Nomenclatura Consistente**: Padrões claros (Dropdown, Modal, etc)
2. **Separação de Contextos**: Funções específicas por contexto
3. **Uso Correto de Campos**: Alinhado com CLAUDE.md
4. **Documentação Inline**: Comentários explicativos

### 🎯 PRÓXIMOS PASSOS RECOMENDADOS

1. **Refatoração Prioritária**:
   - Unificar funções de recálculo de estoque
   - Centralizar validações de datas
   - Implementar service layer

2. **Melhorias de UX**:
   - Sistema de notificações moderno
   - Feedback visual de salvamento
   - Loading states consistentes

3. **Segurança e Integridade**:
   - Validação backend obrigatória
   - Controle de concorrência
   - Audit trail completo

4. **Performance**:
   - Implementar cache estratégico
   - Batch de operações similares
   - Lazy loading de dados pesados

---

## 🚫 FUNÇÕES NÃO UTILIZADAS OU COM PROBLEMAS

### Funções Declaradas mas Não Chamadas:
1. **`mostrarBadgeConfirmacao()`** - Referenciada mas não implementada
2. **`sugerirAlternativa()`** - Botão existe mas função não implementada
3. **`criarNovaSeparacao()`** - Declarada na linha ~5313 mas não mapeada
4. **`salvarEdicaoPreSeparacao()`** - Declarada na linha ~5583 mas não mapeada
5. **`gerarTabelaEstoque()`** - Alias antigo para `gerarTabelaEstoqueReal()`

### Funções com Implementação Incompleta (TODO):
1. **`dividirLinhaDropdown()`** - Apenas console.log, sem lógica real
2. **`unificarLinhaDropdown()`** - Apenas console.log, sem lógica real
3. **`editarPreSeparacao()`** - TODO completo, sem implementação

### Funções Duplicadas (Redundantes):
1. **`gerarTabelaEstoque()` vs `gerarTabelaEstoqueReal()`** - Mesma função, nomes diferentes

---

## ⚠️ FALHAS OPERACIONAIS CRÍTICAS

### 1. **Divisão de Linha no Dropdown Não Funciona**
**Problema**: `dividirLinhaDropdown()` e `unificarLinhaDropdown()` são chamadas mas não têm implementação real
**Impacto**: Usuário pensa que dividiu o pedido mas nada acontece no backend
**Correção**: Implementar lógica real ou remover feature

### 2. **Funções de Sugestão Inexistentes**
**Problema**: Botão "Sugerir alternativa" chama `sugerirAlternativa()` que não existe
**Impacto**: Erro JavaScript ao clicar no botão
**Correção**: Implementar função ou remover botão

### 3. **Badge de Confirmação Quebrado**
**Problema**: `mostrarBadgeConfirmacao()` é chamada mas não existe
**Impacto**: Erro ao marcar checkbox de agendamento confirmado
**Correção**: Implementar função de badge

### 4. **Modal de Nova Separação Incompleto**
**Problema**: `criarNovaSeparacao()` existe mas não está mapeada/documentada
**Impacto**: Funcionalidade oculta ou não testada
**Correção**: Mapear e testar função

### 5. **Edição de Pré-Separação Falsa**
**Problema**: Botão chama `editarPreSeparacao()` que só tem TODO
**Impacto**: Usuário clica e nada acontece
**Correção**: Implementar ou ocultar botão

### 6. **Salvamento de Edição Órfão**
**Problema**: `salvarEdicaoPreSeparacao()` existe mas sem contexto de uso
**Impacto**: Código morto ou fluxo incompleto
**Correção**: Verificar se é usado ou remover

### 7. **Alias de Função Confuso**
**Problema**: `gerarTabelaEstoque()` é apenas um alias para compatibilidade
**Impacto**: Confusão na manutenção
**Correção**: Remover alias e usar nome único


1- Chama a odoo/routes/sincronizacao_integrada.py    │
│   que chama                                            │
│   odoo/services/sincronizacao_integrada_service.py     │
│   que por sua vez chama primeiro                       │
│   faturamento_service.py para importar os dados do     │
│   faturamento do Odoo, verifica se a NF está           │
│   registrada na movimentação de estoque, caso esteja   │
│   verifica se o status da nf é "Cancelado", se for     │
│   ele apaga a movimentação de estoque, se estiver      │
│   registrado e a nf não estiver como "Cancelado" não   │
│   faz nada pois é uma nf já sincronizada, agora se     │
│   não estiver como "Cancelado" e não estiver           │
│   registrada na movimentação de estoque, verifica      │
│   através de EmbarqueItem.erro_validacao em            │
│   validar_nf_cliente se está como                      │
│   item_embarque.erro_validacao=None, se não estiver    │
│   valida através de                                    │
│   faturamento/services/processar_faturamento.py        │
│   ProcessadorFaturamento para vincular a nf correta    │
│   no EmbarqueItem e gravar a movimentação de estoque,  │
│   depois disso atualiza o FaturamentoProduto e         │
│   consolida as atualizações em                         │
│   RelatorioFaturmanentoImportado.\\                    │
│   Dessa parte acima o problema que vi até agora é que  │
│   as movimentações de estoque não estão todas sendo    │
│   gravadas, eu vi apenas algumas pouquissimas, pode    │
│   ser que esteja gravando apenas o que não encontrou   │
│   em EmbarqueItem, o que no caso está errado conforme  │
│   descrevi acima.\                                     │
│                                                        │
│   Depois roda o carteira_service.py para importar a    │
│   carteira do Odoo, substitui a CarteiraPrincipal, e   │
│   depois recompõe as informações operacionais através  │
│   da PreSeparacaoItem, para casos que haja aumento     │
│   de pedido, deverá ver se há uma separação com        │
│   tipo_envio total, se houver e estiver com status     │
│   "ABERTO", atualiza a Separacao, caso esteja          │
│   "COTADO" deverá gerar um alerta através de           │
│   carteira/alert_system.py (nem cheguei nessa parte    │
│   pra te confirmar se funciona), agora se houver uma   │
│   alteração no pedido que diminua a qtd, deverá        │
│   reduzir essa qtd "diminuida" através de uma          │
│   sequencia descrita em carteira/models.py apartir     │
│   das linhas 905.\                                     │
│   \    



