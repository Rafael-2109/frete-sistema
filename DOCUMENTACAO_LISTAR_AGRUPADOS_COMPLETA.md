# 📋 Documentação Completa - Template `listar_agrupados.html`

**Data**: 22/07/2025 - **Última Atualização**: 22/07/2025 18:30  
**Análise**: Interface de usuário, funcionalidades e modais da tela de carteira agrupada  
**Status**: ✅ Correções principais aplicadas - Modal Agendamento, botões e dropdowns corrigidos

---

## 🎯 1. FUNCIONALIDADES ACESSÍVEIS AO USUÁRIO

### 1.1 🔄 Expansão e Visualização de Dados

#### **Expandir/Colapsar Itens do Pedido**
- **Botão**: Seta à esquerda do número do pedido
- **Função**: `togglePedidoItens(numPedido)`
- **Funcionalidade**: Expande dropdown mostrando todos os itens do pedido em tabela editável
- **Endpoint**: `/carteira/api/pedido/{numPedido}/itens-editaveis`
- **Features**: Auto-save, validação, cálculo automático de valores


#### **Expandir/Colapsar Separações do Pedido**
- **Botão**: Ícone na coluna "Saldo"
- **Função**: `toggleSeparacoesPedido(numPedido)`
- **Funcionalidade**: Mostra separações existentes com detalhes completos
- **Endpoint**: `/carteira/api/pedido/{numPedido}/separacoes`
- **Dados**: Produto, quantidades, valores, estoque, produção, datas

### 1.2 📦 Gestão de Separações

#### **Criar Nova Separação** ✅ CORRIGIDO
- **Botão**: "📦 Criar Separação"
- **Função**: `criarSeparacao(numPedido)` ✅ **VALIDADO**
- **Funcionalidade**: Abre modal específico para criar separação selecionando itens
- **Endpoint**: `POST /carteira/api/pedido/{numPedido}/criar-separacao`
- **Validação**: Todos itens devem ter data de expedição válida
- **Modal**: `modalCriarSeparacao` ✅ **CRIADO/VALIDADO**
- **Correções Aplicadas**: 
  - ✅ Corrigido erro toLocaleString
  - ✅ Abre modal correto (não modalAvaliarEstoques)
  - ✅ Função `carregarItensParaSeparacao()` implementada

#### **Ver Detalhes da Separação**
- **Botão**: Ícone "olho" no dropdown de separações
- **Função**: `verDetalhesSeparacao(loteId)`
- **Funcionalidade**: Modal com detalhes completos da separação
- **Endpoint**: `/carteira/api/separacao/{loteId}/detalhes`
- **Dados**: Itens, embarque, transportadora, status

#### **Editar Separação**
- **Botão**: Ícone "editar" no dropdown de separações
- **Função**: `editarSeparacao(loteId)`
- **Funcionalidade**: Modal para editar dados da separação
- **Endpoint**: `POST /carteira/api/separacao/{loteId}/editar`

### 1.3 📊 Análise de Estoques

#### **Estoque D0/D7 (7 dias)**
- **Botão**: "📊 Estoque D0/D7" (dropdown)
- **Função**: `calcularEstoqueD0D7(numPedido)`
- **Funcionalidade**: Modal com análise de ruptura em 7 dias
- **Endpoint**: `/carteira/api/pedido/{numPedido}/estoque-d0-d7`
- **Dados**: Estoque atual, projeção 7 dias, alertas de ruptura

#### **Avaliar Estoques (28 dias)** ✅ CORRIGIDO
- **Botão**: "📊 Avaliar Estoques" (botão direto - dropdown removido)
- **Função**: `abrirModalAvaliarEstoques(numPedido)` ✅ **VALIDADO**
- **Funcionalidade**: Modal com projeção completa de 28 dias
- **Endpoint**: `/carteira/api/pedido/{numPedido}/estoque-projetado-28-dias`
- **Features**: Seleção de itens, configuração envio total/parcial
- **Correções Aplicadas**:
  - ✅ Convertido de dropdown para botão direto
  - ✅ Removida redundância de interface

#### **Exportar Análise de Estoque**
- **Botão**: "Exportar" nos modais de estoque
- **Função**: `exportarAnaliseEstoque()`
- **Funcionalidade**: Download Excel com análise completa
- **Endpoint**: `/carteira/api/export-excel/estoque-analise/{numPedido}`

### 1.4 🗓️ Agendamento

#### **Solicitar Agendamento** ✅ CORRIGIDO
- **Botão**: "🗓️ Agendar"
- **Função**: `solicitarAgendamento(numPedido)` ✅ **VALIDADO**
- **Funcionalidade**: Modal para agendar entrega do pedido com dados pré-preenchidos
- **Endpoint Principal**: `POST /carteira/item/{itemId}/agendamento`
- **Endpoint Auxiliar**: `GET /carteira/api/pedido/{numPedido}/agendamento-existente` ✅ **CRIADO**
- **Campos**: Data/hora agendamento, data expedição, protocolo, observações, confirmação
- **Correções Aplicadas**:
  - ✅ Campos pré-preenchidos com dados existentes
  - ✅ Salvamento correto no campo `expedicao` (não `data_entrega_pedido`)
  - ✅ Badge de confirmação visual (✅ Confirmado / ⏳ Pendente)
  - ✅ Função `mostrarBadgeConfirmacao()` implementada
  - ✅ API `buscar_agendamento_existente()` criada

### 1.5 ℹ️ Informações Adicionais

#### **Ver Endereço de Entrega**
- **Botão**: Badge do Incoterm (ex: "CIF", "FOB")
- **Função**: `abrirModalEndereco(numPedido)`
- **Funcionalidade**: Modal com dados completos do endereço
- **Endpoint**: `/carteira/item/{numPedido}/endereco`
- **Dados**: Cliente, município, UF, endereço de entrega

---

## 🎛️ 2. MODAIS DISPONÍVEIS

### 2.1 📅 Modal de Agendamento (`modalAgendamento`) ✅ VALIDADO
**Acesso**: Botão "🗓️ Agendar"  
**Função de Abertura**: `solicitarAgendamento(numPedido)` ✅ **VALIDADO**
**Função de Carregamento**: `carregarDadosAgendamento(numPedido)` ✅ **CORRIGIDO**
**Função de Salvamento**: `salvarAgendamento()` ✅ **CORRIGIDO**
**Função de Badge**: `mostrarBadgeConfirmacao(confirmado)` ✅ **CRIADO**
**Campos**:
- Data de Agendamento (obrigatório) ✅ Pré-preenchido
- Hora de Agendamento ✅ Pré-preenchido
- Data de Expedição ✅ Pré-preenchido
- Protocolo ✅ Pré-preenchido
- Observações ✅ Pré-preenchido
- Checkbox confirmação ✅ Pré-preenchido + Badge visual
**Status**: ✅ **TOTALMENTE FUNCIONAL**

### 2.2 📊 Modal Estoque D0/D7 (`modalEstoqueD0D7`)
**Acesso**: Menu "📊 Estoque D0/D7"  
**Componentes**:
- Resumo de alertas (produtos OK, ruptura D0, ruptura D7)
- Tabela por produto com estoque atual e projeção
- Status colorido por produto
- Botão exportar Excel

### 2.3 🏠 Modal de Endereço (`modalEndereco`)
**Acesso**: Badge Incoterm  
**Dados**:
- Dados do cliente (CNPJ, razão social)
- Localização (UF, município) 
- Endereço de entrega completo
- Informações de contato

### 2.4 📈 Modal Avaliar Estoques (`modalAvaliarEstoques`)
**Acesso**: Menu "📊 Avaliar Estoques"  
**Features**:
- Seleção múltipla de itens
- Configuração envio total/parcial
- Projeção de 28 dias
- Campos justificativa (quando parcial)
- Tabela editável com ações

### 2.5 📦 Modal Criar Separação (`modalCriarSeparacao`) ✅ CRIADO/VALIDADO
**Acesso**: Botão "📦 Criar Separação"  
**Função**: `criarSeparacao(numPedido)` ✅ **VALIDADO**
**Função Auxiliar**: `carregarItensParaSeparacao(numPedido)` ✅ **IMPLEMENTADO**
**Dados**:
- Seleção de itens do pedido para separação
- Campos de quantidade disponível e quantidade a separar
- Data de expedição por item
- Validação de itens selecionados
**Status**: ✅ **TOTALMENTE FUNCIONAL**

### 2.6 📦 Modal Consultar Separações (`modalConsultarSeparacoes`) ⚠️ NÃO VALIDADO
**Acesso**: Menu "📦 Ver Separações" (REMOVIDO - botão "Consultar" era redundante)
**Dados**:
- Lista de todas as separações do pedido
- Status de cada separação
- Ações de visualizar/editar
- Totais e contadores
**Status**: ❓ **PRECISAR VALIDAR SE AINDA É NECESSÁRIO**

---

## ⚠️ 3. PROBLEMAS IDENTIFICADOS E STATUS DE CORREÇÃO

### 3.1 🔄 Funcionalidades Duplicadas ✅ PARCIALMENTE CORRIGIDAS

#### **Modal EstoqueD0D7 Duplicado** ❓ PENDENTE
- **Problema**: Modal definido **2 vezes** no HTML (linhas 455 e 894)
- **Impacto**: Conflito de IDs, comportamento inconsistente
- **Solução**: Remover uma das definições ❓ **PENDENTE VALIDAÇÃO**

#### **Botão "Estoque D0/D7" Duplicado** ❓ PENDENTE
- **Problema**: Aparece 2 vezes no mesmo dropdown (linhas 182 e 197)
- **Impacto**: Confusão na interface
- **Solução**: Manter apenas uma instância ❓ **PENDENTE VALIDAÇÃO**

#### **Funções de Estoque Similares** ❓ PRECISAM REVISÃO
- **`calcularEstoqueD0D7()`** vs **`carregarEstoqueD0D7()`** - fazem a mesma coisa ❓ **AVALIAR UNIFICAÇÃO**
- **`exportarAnaliseEstoque()`** vs **`exportarDadosEstoque()`** - muito similares ❓ **AVALIAR UNIFICAÇÃO**
- **Solução**: Unificar funcionalidades ❓ **PENDENTE ANÁLISE**

### 3.2 🚫 Funcionalidades Não Acessíveis

#### **Funções JavaScript Definidas mas Sem Acesso** ❓ PRECISAM REVISÃO
- **`editarPreSeparacaoCompleta()`** - função incompleta ❓ **AVALIAR SE REMOVER**
- **`dividirLinhaDropdown()`** - placeholder não implementado ❓ **AVALIAR SE REMOVER**
- **`unificarLinhaDropdown()`** - placeholder não implementado ❓ **AVALIAR SE REMOVER**
- **`sugerirAlternativa(codProduto)`** - chamada mas não implementada ❓ **AVALIAR SE REMOVER**

#### **Modal Sem Acesso** ❓ PRECISAM REVISÃO
- **`modalEditarPreSeparacao`** - definido mas sem botão para abrir ❓ **AVALIAR SE REMOVER**

---

## 📡 4. ENDPOINTS DE API UTILIZADOS

### 4.1 🔍 Consultas (GET)
| Endpoint | Funcionalidade |
|----------|----------------|
| `/carteira/api/pedido/{numPedido}/itens-editaveis` | Busca itens editáveis do pedido |
| `/carteira/api/pedido/{numPedido}/separacoes` | Busca separações do pedido |
| `/carteira/api/pedido/{numPedido}/estoque-d0-d7` | Calcula estoque D0/D7 |
| `/carteira/api/pedido/{numPedido}/estoque-projetado-28-dias` | Projeção 28 dias |
| `/carteira/api/separacao/{loteId}/detalhes` | Detalhes da separação |
| `/carteira/item/{numPedido}/endereco` | Endereço de entrega |
| `/carteira/api/pre-separacao/{preSeparacaoId}` | Detalhes pré-separação |
| `/carteira/api/pedido/{numPedido}/agendamento-existente` | ✅ Buscar agendamento existente ✅ **CRIADO** |

### 4.2 ✏️ Ações (POST)
| Endpoint | Funcionalidade |
|----------|----------------|
| `/carteira/api/pedido/{numPedido}/criar-separacao` | Criar separação |
| `/carteira/api/pedido/{numPedido}/salvar-avaliacoes` | Salvar avaliações |
| `/carteira/item/{itemId}/agendamento` | Salvar agendamento |
| `/carteira/api/separacao/{loteId}/editar` | Editar separação |
| `/carteira/api/item/{itemId}/salvar-alteracao` | Salvar alteração |
| `/carteira/api/pre-separacao/{preSeparacaoId}/editar` | Editar pré-separação |
| `/carteira/api/pre-separacao/{preSeparacaoId}/cancelar` | Cancelar pré-separação |

### 4.3 📤 Exportações (GET)
| Endpoint | Funcionalidade |
|----------|----------------|
| `/carteira/api/export-excel/estoque-analise/{numPedido}` | Excel análise estoque |
| `/carteira/api/export-excel/produto-detalhes/{codProduto}` | Excel detalhes produto |
| `/carteira/api/export-excel/estoque-dados/{numPedido}` | Excel dados estoque |

---

## 🛠️ 5. FUNCIONALIDADES AVANÇADAS

### 5.1 ✏️ Edição Inline no Dropdown
- **Auto-save**: Alterações salvas automaticamente ao sair do campo
*Funciona apenas ao recarregar a página
- **Validação**: Data expedição não pode ser no passado
*Não está funcionando
- **Recálculo**: Valores recalculados automaticamente
*Peso e pallet não estão sendo recalculados e quebram ao alterar a qtd
- **Replicação**: Campos podem ser replicados para itens selecionados
*Funciona corretamente

### 5.2 🔄 Cache e Performance
- **Cache local**: Dados de itens mantidos em memória
- **Loading states**: Indicadores visuais durante carregamento
- **Debounce**: Evita múltiplas chamadas em edições rápidas

### 5.3 📊 Sistema de Alertas
- **Estoque**: Alertas visuais para ruptura D0 e D7
- **Validação**: Mensagens de erro em campos obrigatórios
- **Status**: Códigos de cor para diferentes status

---

## 📈 6. MÉTRICAS DE INTERFACE

### 6.1 📊 Contadores
- **Total de pedidos**: Exibido no cabeçalho
- **Itens por pedido**: Contados dinamicamente
- **Separações**: Quantidade mostrada em badge
- **Produtos em alerta**: Contabilizados nos modais

### 6.2 🎨 Elementos Visuais
- **Badges coloridos**: Status de pedidos e separações
- **Linhas verdes**: Pedidos totalmente em separação
- **Ícones intuitivos**: Para cada tipo de ação
- **Tooltips**: Explicações em hover

---

## 🚀 7. RECOMENDAÇÕES DE MELHORIAS

### 7.1 🔧 Correções Urgentes - STATUS ATUALIZADO
1. **Remover modal duplicado** de EstoqueD0D7 ❓ **PENDENTE**
2. **Remover botão duplicado** de Estoque D0/D7 ❓ **PENDENTE**
3. **Implementar funções incompletas** ou removê-las ❓ **AVALIAR CADA FUNÇÃO**
4. **Adicionar acesso ao modal** EditarPreSeparacao ou removê-lo ❓ **AVALIAR SE REMOVER**

### 7.1.1 ✅ Correções Já Aplicadas
1. ✅ **Modal Agendamento**: Campos pré-preenchidos, salvamento correto, badges visuais
2. ✅ **Botão Criar Separação**: Erro toLocaleString corrigido, modal correto
3. ✅ **Botão Consultar**: Redundância removida
4. ✅ **Botão Avaliar**: Convertido de dropdown para botão direto

### 7.2 📊 Otimizações
1. **Unificar funções similares** de estoque
2. **Consolidar endpoints** de exportação
3. **Implementar lazy loading** para dropdowns
4. **Adicionar confirmações** para ações destrutivas

### 7.3 🎯 Novas Funcionalidades
1. **Busca/filtro** nos dropdowns expandidos
2. **Ações em lote** para múltiplos pedidos  
3. **Histórico de alterações** nos itens
4. **Notificações push** para atualizações

---

---

## 📋 8. STATUS DE VALIDAÇÃO DAS FUNCIONALIDADES

### ✅ FUNCIONALIDADES VALIDADAS E FUNCIONAIS
1. **`togglePedidoItens(numPedido)`** - Expansão de itens ✅ **VALIDADO**
2. **`toggleSeparacoesPedido(numPedido)`** - Expansão de separações ✅ **VALIDADO**
3. **`criarSeparacao(numPedido)`** - Criar nova separação ✅ **CORRIGIDO/VALIDADO**
4. **`solicitarAgendamento(numPedido)`** - Modal agendamento ✅ **CORRIGIDO/VALIDADO**
5. **`abrirModalAvaliarEstoques(numPedido)`** - Avaliar estoques ✅ **CORRIGIDO/VALIDADO**
6. **`abrirModalEndereco(numPedido)`** - Ver endereço ✅ **VALIDADO**
7. **`mostrarBadgeConfirmacao(confirmado)`** - Badge agendamento ✅ **CRIADO/VALIDADO**

### ❓ FUNCIONALIDADES A VALIDAR/AVALIAR
1. **`verDetalhesSeparacao(loteId)`** - Ver detalhes separação ❓ **VALIDAR**
2. **`editarSeparacao(loteId)`** - Editar separação ❓ **VALIDAR**
3. **`calcularEstoqueD0D7(numPedido)`** - Estoque D0/D7 ❓ **VALIDAR**
4. **`exportarAnaliseEstoque()`** - Export Excel ❓ **VALIDAR**
5. **`editarPreSeparacaoCompleta()`** - Editar pré-separação ❓ **AVALIAR SE REMOVER**
6. **`dividirLinhaDropdown()`** - Dividir linha ❓ **AVALIAR SE REMOVER**
7. **`unificarLinhaDropdown()`** - Unificar linha ❓ **AVALIAR SE REMOVER**
8. **`sugerirAlternativa(codProduto)`** - Sugestão alternativa ❓ **AVALIAR SE REMOVER**

### 🗑️ FUNCIONALIDADES PROVAVELMENTE INÚTEIS (CANDIDATAS À REMOÇÃO)
1. **`modalEditarPreSeparacao`** - Modal sem acesso ❓ **CANDIDATO À REMOÇÃO**
2. **Botão "Consultar" duplicado** - Redundante ✅ **REMOVIDO**
3. **Dropdown "Avaliar" não funcional** - Convertido para botão ✅ **CORRIGIDO**

---

**📝 Nota**: Esta documentação reflete o estado atual do template em 22/07/2025. ✅ **Principais correções aplicadas**: Modal Agendamento totalmente funcional, botões corrigidos, endpoints criados. ❓ **Próxima fase**: Validar funcionalidades restantes e remover código inútil.