# 📋 CARD DE SEPARAÇÃO - DOCUMENTAÇÃO TÉCNICA COMPLETA

## 🎯 OBJETIVO
Este documento detalha o funcionamento completo dos cards de separação e separações compactas no sistema de carteira agrupada, garantindo compreensão clara entre sessões de desenvolvimento.

## 📊 CONCEITOS FUNDAMENTAIS

### 1. MODELO ÚNICO - Separacao
- **NÃO EXISTE MAIS PreSeparacaoItem** - DEPRECATED, não usar
- Tudo é `Separacao` com diferentes valores de `status`
- Localização: `app/separacao/models.py`

### 2. CAMPOS CRÍTICOS DO MODELO

#### Campo `status` (String)
Valores possíveis e suas origens:
- **`PREVISAO`**: Criado pelo usuário, ainda não confirmado (era pré-separação)
- **`ABERTO`**: Confirmado pelo usuário, pronto para cotação
- **`COTADO`**: Tem cotação de frete associada
- **`EMBARCADO`**: Foi embarcado
- **`FATURADO`**: Gerado automaticamente via importação Odoo quando NF é emitida
- **`NF no CD`**: NF voltou para o CD

#### Campo `sincronizado_nf` (Boolean)
- **`False`**: Item SEMPRE aparece na carteira, SEMPRE projeta estoque
- **`True`**: Foi faturado (tem NF), NÃO aparece na carteira, NÃO projeta estoque
- Acionado automaticamente pela importação de NFs do Odoo
- Gatilho principal para projeção de saídas de estoque

### 3. DIFERENÇA ENTRE `status` E `sincronizado_nf`
- **`status='FATURADO'`**: Indica que foi faturado (ação do sistema)
- **`sincronizado_nf=True`**: Indica sincronização com NF e movimentação de estoque
- Podem existir casos onde `status='FATURADO'` mas `sincronizado_nf=False` temporariamente

## 🔄 REGRAS DE RENDERIZAÇÃO

### Cards de Separação
- **Localização**: Renderizados no workspace de montagem
- **Vínculo**: Por `num_pedido`
- **Filtro**: `Separacao.sincronizado_nf=False`
- **Agrupamento**: 1 card por `separacao_lote_id`

### Separações Compactas
- **Localização**: Abaixo do pedido agrupado na carteira
- **Visibilidade**: Aparecem mesmo com pedido não expandido
- **Filtros**: Respeitam filtros aplicados na carteira
- **Agrupamento**: 1 linha por `separacao_lote_id`

## 🎨 DIFERENÇAS VISUAIS POR STATUS

### Layout Compartilhado
- Todos os cards compartilham o mesmo layout base
- Diferenças limitam-se a cores e botões disponíveis

### Mapeamento de Cores (definido em lote-manager.js)
```javascript
const configStatus = {
    'PREVISAO': { cor: 'secondary' },  // Cinza
    'ABERTO': { cor: 'warning' },      // Amarelo
    'COTADO': { cor: 'primary' },      // Azul
    'EMBARCADO': { cor: 'success' },   // Verde
    'FATURADO': { cor: 'info' },       // Azul claro
    'NF no CD': { cor: 'danger' }      // Vermelho
}
```

## 🔘 BOTÕES POR STATUS

### Legenda de Marcação
- **&** = Aparece também na separação compacta
- Sem marcação = Aparece apenas no card completo

### Status: PREVISAO / ABERTO

#### A& - Botão Datas
- **Campos editáveis**:
  - Data expedição: `Separacao.expedicao`
  - Data agendamento: `Separacao.agendamento`
  - Protocolo: `Separacao.protocolo`
  - Confirmação checkbox: `Separacao.agendamento_confirmado`
- **Comportamento**: Abre modal para edição
- **Aparece em**: Card e Compacta

#### B - Excluir Separação
- **Ação**: Remove todas as separações do lote
- **API**: `/carteira/api/separacao/<lote_id>/excluir`
- **Aparece em**: Apenas Card

#### C& - Previsão/Confirmar
- **PREVISAO → ABERTO**: Botão "Confirmar" (verde)
- **ABERTO → PREVISAO**: Botão "Previsão" (amarelo)
- **API**: `/carteira/api/separacao/<lote_id>/alterar-status`
- **Aparece em**: Card e Compacta

#### D - Adicionar
- **Função**: Adicionar produtos do workspace ao card
- **Processo**: 
  1. Usuário seleciona checkboxes dos produtos
  2. Opcionalmente altera quantidade
  3. Clica em "Adicionar" no card desejado
- **Aparece em**: Apenas Card

### TODOS OS STATUS

#### A& - Agendar
- **Verificações**:
  1. Verifica se há `Separacao.agendamento` preenchido
  2. Se `agendamento_confirmado=True`, muda para `False`
  3. Identifica portal via prefixo CNPJ
- **Mapeamento Portal**: `app.portal.utils.grupo_empresarial.GrupoEmpresarial`
- **De-Para Produtos**: `app.portal.atacadao.models.ProdutoDeParaAtacadao`
- **API Async**: `app/portal/routes_async.py`
- **Grava**: Protocolo em `Separacao.protocolo`
- **Aparece em**: Card e Compacta

#### B& - Ver. Protocolo
- **Condição**: Apenas se `protocolo` preenchido
- **Ação**: Verifica status do agendamento no portal
- **Aparece em**: Card e Compacta

## 🔧 MÉTODOS UNIFICADOS

### Alteração de Status
```javascript
// Método único para todas as mudanças de status
alterarStatus(loteId, novoStatus)
// Valores: 'PREVISAO' ou 'ABERTO'
```

### Edição de Datas
```javascript
// Método único baseado no status
editarDatas(loteId, status)
// Determina tipo: 'pre-separacao' ou 'separacao'
```

### Exclusão
```javascript
// Método único para qualquer status
excluirSeparacao(loteId, numPedido)
```

## 📁 ESTRUTURA DE ARQUIVOS

### APIs Backend
- `/app/carteira/routes/separacao_api.py` - APIs principais
- `/app/carteira/routes/pre_separacao_api.py` - APIs de compatibilidade (redireciona)
- `/app/portal/routes_async.py` - Agendamento assíncrono

### JavaScript Frontend
- `/app/templates/carteira/js/carteira-agrupada.js` - Controlador principal
- `/app/templates/carteira/js/separacao-manager.js` - Gerenciador de separações
- `/app/templates/carteira/js/workspace-montagem.js` - Workspace de montagem
- `/app/templates/carteira/js/lote-manager.js` - Renderização de cards

### Templates HTML
- `/app/templates/carteira/agrupados_balanceado.html` - Template principal

## ⚠️ REGRAS IMPORTANTES

### Formatação
- **Datas**: Sempre exibir em formato `dd/mm/yyyy`
- **Valores**: Padrão brasileiro ("." para milhar, "," para decimal)

### Padronização
- Todos os botões da compacta devem ter o mesmo comportamento dos cards
- Preferir modais para edição (padronização UX)
- Eliminar redundâncias e funções de compatibilidade

### Relação Pedido/Lote
- 1 pedido pode ter N lotes
- 1 lote pertence a apenas 1 pedido
- 0% de risco de 1 `separacao_lote_id` referenciar mais de 1 pedido

## 🚫 MÉTODOS REMOVIDOS (NÃO USAR)

### carteira-agrupada.js (✅ LIMPO)
- ✅ REMOVIDO: `editarDatasPreSeparacaoComDados()` - Usar `abrirModalEdicaoDatasDireto()`
- ✅ REMOVIDO: `confirmarPreSeparacao()` - Usar `alterarStatusSeparacao()`

### separacao-manager.js (✅ LIMPO)
- ✅ REMOVIDO: `transformarLoteEmSeparacao()` - Usar `alterarStatus()`
- ✅ REMOVIDO: `excluirPreSeparacao()` - Usar `excluirSeparacao()`

### workspace-montagem.js (✅ LIMPO)
- ✅ REMOVIDO: `renderizarLotesExistentesOBSOLETO()`
- ✅ REMOVIDO: `renderizarSeparacoesConfirmadas()` - Usar `renderizarSeparacoesNaAreaUnificada()`
- ✅ REMOVIDO: `gerarSeparacao()` - Usar `alterarStatus()`
- ✅ REMOVIDO: `voltarParaPrevisao()` - Usar `alterarStatusSeparacao()`
- ✅ REMOVIDO: `reverterSeparacao()` - Usar `alterarStatusSeparacao()`
- ✅ REMOVIDO: `editarDatasSeparacao()` - Usar `editarDatas()`
- ✅ REMOVIDO: `editarDatasPreSeparacao()` - Usar `editarDatas()`
- ✅ REMOVIDO: `editarDatasSeparacaoComDados()`
- ✅ REMOVIDO: `editarDatasPreSeparacaoComDados()`

### lote-manager.js (✅ LIMPO)
- ✅ REMOVIDO: `_renderizarCardPreSeparacaoOLD()` - Usar `renderizarCardUniversal()`
- ✅ REMOVIDO: `renderizarProdutosDaPreSeparacao()` - Usar `renderizarProdutosUniversal()`
- ✅ REMOVIDO: `removerLote()` - Usar `workspace.excluirLote()`
- ⚠️ TODO: `gerarNovoLoteId()` - Migrar para `app.utils.lote_utils.gerar_lote_id()` do backend

## 📌 PONTOS DE ATENÇÃO

### Sincronização com Odoo
- O campo `sincronizado_nf` é acionado automaticamente
- Mantém sincronização: Separações × Faturamento × Estoque
- Movimentação de estoque ocorre apenas quando `sincronizado_nf=True`

### Regras de Negócio
- Items com `status='PREVISAO'` não aparecem para roteirizar (regra de negócio)
- Apenas `sincronizado_nf=False` aparece na carteira
- Agendamento no portal atualmente implementado apenas para Atacadão

## 🔄 FLUXO DE STATUS

```
PREVISAO (usuário cria)
    ↓ [Confirmar]
ABERTO (pronto para cotação)
    ↓ [Cotar]
COTADO (tem cotação)
    ↓ [Embarcar]
EMBARCADO (foi embarcado)
    ↓ [Sistema/Odoo]
FATURADO (NF emitida + sincronizado_nf=True)
    ↓ [Se necessário]
NF no CD (NF retornou)
```

## 📝 NOTAS DE IMPLEMENTAÇÃO

1. **Sempre** verificar `sincronizado_nf=False` para itens da carteira
2. **Sempre** usar métodos unificados, não criar novos aliases
3. **Sempre** manter compatibilidade com status existentes
4. **Nunca** referenciar PreSeparacaoItem (deprecated)
5. **Nunca** criar métodos redundantes "para compatibilidade"

---

**Última Atualização**: Janeiro 2025
**Mantido por**: Sistema de Carteira de Pedidos
**Versão**: 2.1 (Limpeza de Redundâncias e Unificação de Métodos)