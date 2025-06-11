# 📋 Guia - Sistema de Gerenciamento de Pedidos

## 🎯 Funcionalidades Implementadas

Este documento descreve as funcionalidades implementadas para permitir **editar** e **excluir** pedidos com sincronização automática com a separação.

---

## ✅ O Que Foi Implementado

### 1. 📝 **Formulário de Edição**
- **Arquivo**: `app/pedidos/forms.py`
- **Classe**: `EditarPedidoForm`
- **Campos editáveis**:
  - ✏️ **Data de Expedição**: Quando o pedido será expedido
  - ✏️ **Data de Agendamento**: Quando será entregue/coletado
  - ✏️ **Protocolo**: Número do protocolo de agendamento

### 2. 🛣️ **Novas Rotas**
- **Arquivo**: `app/pedidos/routes.py`
- **Rotas adicionadas**:
  - `GET/POST /pedidos/editar/<id>` - Edita um pedido
  - `POST /pedidos/excluir/<id>` - Exclui um pedido

### 3. 🎨 **Interface do Usuário**
- **Template de edição**: `app/templates/pedidos/editar_pedido.html`
- **Lista modificada**: `app/templates/pedidos/lista_pedidos.html`
- **Nova coluna "Ações"** na tabela de pedidos

### 4. 🔄 **Sincronização Automática**
- Alterações nos pedidos são **automaticamente aplicadas** na separação
- Utiliza `separacao_lote_id` como chave principal
- Fallback por chave composta se necessário

---

## 🔐 Regras de Negócio

### ✅ **Pedidos Editáveis**
- **Status permitido**: Apenas `ABERTO`
- **Campos**: agenda, protocolo, expedição
- **Ação**: Exibe botões de editar/excluir

### 🚫 **Pedidos NÃO Editáveis**
- **Status bloqueados**: `COTADO`, `EMBARCADO`, `FATURADO`, `NF no CD`
- **Ação**: Exibe ícone de cadeado 🔒
- **Motivo**: Pedidos já processados não podem ser alterados

---

## 🖥️ Como Usar o Sistema

### 1. **Acessar Lista de Pedidos**
```
URL: /pedidos/lista_pedidos
```
- Procure pela nova coluna **"Ações"** na tabela

### 2. **Editar um Pedido**
1. 🔍 Localize um pedido com status **"ABERTO"**
2. 👆 Clique no botão **editar** (ícone lápis) na coluna "Ações"
3. 📝 Modifique os campos desejados:
   - **Data de Expedição**
   - **Data de Agendamento**
   - **Protocolo**
4. 💾 Clique em **"Salvar Alterações"**
5. ✅ Sistema sincroniza automaticamente com separação

### 3. **Excluir um Pedido**
1. 🔍 Localize um pedido com status **"ABERTO"**
2. 👆 Clique no botão **excluir** (ícone lixeira) na coluna "Ações"
3. ⚠️ **Confirme a exclusão** (ação irreversível)
4. ✅ Sistema remove pedido e **todas as separações relacionadas**

---

## 🔄 Relação Pedidos ↔ Separação

### **Como Funciona a Ligação**
```
📊 Pedido (1) ←→ Separação (N)
```

### **Estratégia de Sincronização**
1. **Primary**: Busca por `separacao_lote_id`
2. **Fallback**: Busca por chave composta:
   - `num_pedido`
   - `expedicao`
   - `agendamento`
   - `protocolo`

### **Campos Sincronizados**
| Campo | Tabela Pedidos | Tabela Separação |
|-------|---------------|------------------|
| Expedição | ✅ `expedicao` | ✅ `expedicao` |
| Agendamento | ✅ `agendamento` | ✅ `agendamento` |
| Protocolo | ✅ `protocolo` | ✅ `protocolo` |

---

## 🛡️ Validações e Segurança

### ✅ **Validações Implementadas**
- 🔐 **Status check**: Só permite editar/excluir pedidos "ABERTO"
- 🛡️ **CSRF protection**: Tokens em todos os formulários
- 📅 **Data validation**: Agendamento ≥ Expedição
- 🔄 **Rollback automático**: Em caso de erro
- 📝 **Logs detalhados**: Para auditoria

### ⚠️ **Mensagens de Erro**
- Tentativa de editar pedido processado
- Problemas na sincronização
- Erros de validação de dados

---

## 🎯 Fluxo de Dados

### **Edição de Pedido**
```
1. 👤 Usuário clica "Editar"
2. 🔒 Sistema valida status = "ABERTO"
3. 📝 Exibe formulário pré-preenchido
4. 👤 Usuário modifica e submete
5. 💾 Atualiza campos no pedido
6. 🔍 Busca separações relacionadas
7. 🔄 Sincroniza campos na separação
8. ✅ Confirma operação
```

### **Exclusão de Pedido**
```
1. 👤 Usuário clica "Excluir"
2. ⚠️ JavaScript exibe confirmação
3. 🔒 Sistema valida status = "ABERTO"
4. 🔍 Busca separações relacionadas
5. 🗑️ Remove todas as separações
6. 🗑️ Remove o pedido
7. ✅ Confirma operação
```

---

## 📁 Arquivos Modificados/Criados

### **Novos Arquivos**
- ✨ `app/templates/pedidos/editar_pedido.html`
- ✨ `script_gerenciar_pedidos.py`
- ✨ `GUIA_GERENCIAR_PEDIDOS.md`

### **Arquivos Modificados**
- 🔧 `app/pedidos/forms.py` - Adicionado `EditarPedidoForm`
- 🔧 `app/pedidos/routes.py` - Adicionadas rotas de edição/exclusão
- 🔧 `app/templates/pedidos/lista_pedidos.html` - Nova coluna "Ações"

---

## 🚨 Pontos de Atenção

### ⚠️ **Exclusão é Irreversível**
- ❌ **Não há** função de "desfazer"
- 🗑️ Remove **pedido** e **todas as separações**
- 💡 **Recomendação**: Sempre confirmar antes de excluir

### 🔄 **Sincronização Automática**
- ✅ Alterações são aplicadas em **ambas as tabelas**
- 📊 Relatório mostra quantos itens foram atualizados
- 🔍 Busca inteligente por lote ou chave composta

### 🔐 **Restrições de Status**
- 📋 Apenas pedidos **"ABERTO"** podem ser editados/excluídos
- 🔒 Pedidos processados ficam **protegidos** contra alterações
- ✅ Garante **integridade** dos dados do sistema

---

## 🎉 Resumo

### ✅ **Funcionalidades Entregues**
- [x] Formulário para editar agenda, protocolo e expedição
- [x] Botão de exclusão de pedidos
- [x] Sincronização automática com separação
- [x] Restrições por status ("ABERTO" apenas)
- [x] Interface intuitiva com validações
- [x] Confirmações de segurança

### 🚀 **Sistema Pronto para Uso**
O sistema agora permite o gerenciamento completo de pedidos com status "ABERTO", mantendo a sincronização automática com a separação e garantindo a integridade dos dados.

---

*Implementado em: Junho/2025*  
*Status: ✅ Concluído* 