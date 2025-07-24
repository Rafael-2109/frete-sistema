# 🚨 ROTAS FALTANTES NO BACKEND - ANÁLISE CRÍTICA

**Data de Análise**: 24/07/2025  
**Prioridade**: ALTA - Várias funcionalidades críticas do frontend não funcionam por falta destas rotas

---

## 🔴 ROTAS CRÍTICAS DA CARTEIRA (PRIORIDADE MÁXIMA)

### 1. Rotas de Separação - CRÍTICAS PARA DRAG & DROP
```
❌ /carteira/api/separacao/{loteId}/detalhes - GET
❌ /carteira/api/separacao/{loteId}/editar - POST  
❌ /carteira/api/separacao/criar - POST
```
**Impacto**: Sistema de drag & drop não funciona sem estas rotas. Usuários não conseguem visualizar ou editar separações.

### 2. Rotas de Avaliação e Análise
```
❌ /carteira/api/pedido/{numPedido}/salvar-avaliacoes - POST
❌ /carteira/api/export-excel/estoque-analise/{numPedido} - GET
```
**Impacto**: Funcionalidades de avaliação e exportação de análises não funcionam.

### 3. Rotas de Endereço de Entrega
```
❌ /carteira/item/{itemId}/endereco - GET
❌ /carteira/item/{numPedido}/endereco - GET (duplicada/confusa com api/pedido)
```
**Impacto**: Informações de endereço não são exibidas corretamente.

### 4. Rotas de Agendamento Item Individual  
```
❌ /carteira/item/{itemId}/agendamento - GET
❌ /carteira/item/{itemId}/agendamento - DELETE
```
**Impacto**: Gerenciamento individual de agendamentos não funciona completamente.

### 5. Rotas de Pré-Separação
```
❌ /carteira/api/pre-separacao/{preSeparacaoId}/remover - POST (deveria ser DELETE)
```
**Impacto**: Remoção de pré-separações pode falhar.

---

## 🟡 ROTAS IMPORTANTES DE OUTROS MÓDULOS

### Módulo Embarques
```
❌ /embarques/excluir_item/{itemId} - DELETE
❌ /embarques/registrar_impressao - POST
```

### Módulo Faturamento
```
❌ /faturamento/api/modal-vinculacao - GET
❌ /faturamento/api/modal-justificativa - GET
❌ /faturamento/api/modal-nova-justificativa - GET
❌ /faturamento/inativar_nfs - POST
```

### Módulo Monitoramento
```
❌ /monitoramento/{entregaId}/upload_canhoto - POST
❌ /monitoramento/{entregaId}/historico_agendamentos - GET
❌ /monitoramento/{entregaId}/adicionar_agendamento - POST
❌ /monitoramento/confirmar_agendamento/{agendamentoId} - POST
❌ /monitoramento/{entregaId}/historico_data_prevista - GET
❌ /monitoramento/{entregaId}/alterar_data_prevista - POST
```

### Módulo Financeiro
```
❌ /financeiro/pendencias/{nf}/responder - POST
```

### Módulo Fretes
```
❌ /fretes/verificar_cte_embarque/{embarqueId} - GET
```

---

## 🟢 ROTAS EXISTENTES (CONFIRMADAS)

### Carteira - APIs Funcionando
```
✅ /carteira/api/item/{id} - GET
✅ /carteira/api/item/{itemId}/recalcular-estoques - POST
✅ /carteira/api/item/{itemId}/salvar-alteracao - POST
✅ /carteira/api/pedido/{numPedido}/itens - GET
✅ /carteira/api/pedido/{numPedido}/itens-editaveis - GET
✅ /carteira/api/pedido/{numPedido}/separacoes - GET
✅ /carteira/api/pedido/{numPedido}/criar-separacao - POST
✅ /carteira/api/pedido/{numPedido}/detalhes - GET
✅ /carteira/api/pedido/{numPedido}/workspace - GET
✅ /carteira/api/pedido/{numPedido}/estoque-d0-d7 - GET
✅ /carteira/api/pedido/{numPedido}/estoque-projetado-28-dias - GET
✅ /carteira/api/produto/{codProduto}/estoque-d0-d7 - GET
✅ /carteira/api/produto/{codProduto}/cardex - GET
✅ /carteira/api/pedido/{numPedido}/agendamento-existente - GET
✅ /carteira/api/pedido/{numPedido}/agendamento-info - GET
✅ /carteira/api/pedido/{numPedido}/salvar-agendamento - POST
✅ /carteira/api/pedido/{numPedido}/endereco - GET
✅ /carteira/api/pedido/{numPedido}/pre-separacoes-agrupadas - GET
✅ /carteira/api/pedido/{numPedido}/criar-pre-separacao - POST
✅ /carteira/api/pre-separacao/{preSeparacaoId} - GET
✅ /carteira/api/pre-separacao/{preSeparacaoId}/editar - POST
✅ /carteira/api/pre-separacao/{preSeparacaoId}/cancelar - POST
✅ /carteira/api/pre-separacao/{preSeparacaoId}/enviar-separacao - POST
✅ /carteira/api/agrupamentos/enviar-separacao - POST
✅ /carteira/item/{itemId}/agendamento - POST (apenas POST existe)
✅ /carteira/item/{numPedido}/endereco - GET
```

---

## 📋 RECOMENDAÇÕES DE IMPLEMENTAÇÃO

### PRIORIDADE 1 - CRÍTICA (Implementar IMEDIATAMENTE)
1. **Rotas de Separação** - Sistema drag & drop depende disso
   - `/carteira/api/separacao/{loteId}/detalhes`
   - `/carteira/api/separacao/{loteId}/editar`
   - `/carteira/api/separacao/criar`

2. **Rota de Avaliações** - Funcionalidade importante
   - `/carteira/api/pedido/{numPedido}/salvar-avaliacoes`

### PRIORIDADE 2 - ALTA
1. **Export Excel Análise**
   - `/carteira/api/export-excel/estoque-analise/{numPedido}`

2. **Agendamento Item Individual** (completar CRUD)
   - GET e DELETE para `/carteira/item/{itemId}/agendamento`

### PRIORIDADE 3 - MÉDIA
1. Rotas dos módulos Embarques, Faturamento e Monitoramento
2. Corrigir método HTTP de `/carteira/api/pre-separacao/{id}/remover` para DELETE

---

## 🔧 AÇÕES SUGERIDAS

1. **Criar arquivo** `app/carteira/routes/separacao_detalhes_api.py` com as rotas faltantes
2. **Implementar lógica** de detalhes e edição de separações
3. **Adicionar validações** de permissões e dados
4. **Testar integração** com o frontend drag & drop
5. **Documentar** as novas rotas implementadas

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **Inconsistência de Nomenclatura**: Algumas rotas têm nomes confusos (ex: dois endpoints diferentes para endereço)
2. **Métodos HTTP Incorretos**: Algumas rotas usam POST quando deveriam usar DELETE
3. **Falta de Padronização**: Mistura de `/api/` e rotas diretas no mesmo módulo
4. **Dependências Críticas**: O drag & drop é uma funcionalidade core que está quebrada

---

**URGÊNCIA**: As rotas de separação devem ser implementadas com máxima prioridade pois afetam diretamente a operação do sistema.