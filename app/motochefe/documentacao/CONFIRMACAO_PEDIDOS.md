# 🎯 Sistema de Confirmação de Pedidos - MotoChefe

## 📋 Visão Geral

Sistema de aprovação em duas etapas para **inserção** e **cancelamento** de pedidos no módulo MotoChefe.

### Objetivo
Adicionar camada de aprovação gerencial antes de efetivar mudanças críticas em pedidos de venda.

---

## 🔄 Fluxos Implementados

### 1️⃣ INSERÇÃO (Novo Pedido)

```
┌─────────────────────────────────────────────────────────────┐
│ USUÁRIO: Cria novo pedido via "Novo Pedido"                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SISTEMA: Cria pedido com:                                   │
│  - ativo = False          (não aparece na lista)            │
│  - status = 'PENDENTE'    (aguardando aprovação)            │
│  + Cria PedidoVendaAuditoria com acao='INSERCAO'            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ GESTOR: Acessa "Confirmação de Pedidos"                    │
└─────────────────────────────────────────────────────────────┘
                    ↓             ↓
           ┌────────┴────────┬─────────┐
           ↓                 ↓         ↓
    [APROVAR]          [REJEITAR]
           ↓                 ↓
  ativo = True      status = 'REJEITADO'
  status = 'APROVADO'  (permanece inativo)
```

### 2️⃣ CANCELAMENTO (Pedido Existente)

```
┌─────────────────────────────────────────────────────────────┐
│ USUÁRIO: Clica "Cancelar" em pedido existente              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SISTEMA: IMEDIATAMENTE altera pedido:                       │
│  - ativo = False          (some da lista AGORA)             │
│  - status = 'CANCELADO'   (marcado como cancelado)          │
│  + Cria PedidoVendaAuditoria com acao='CANCELAMENTO'        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ GESTOR: Acessa "Confirmação de Pedidos"                    │
└─────────────────────────────────────────────────────────────┘
                    ↓             ↓
           ┌────────┴────────┬─────────┐
           ↓                 ↓         ↓
    [APROVAR]          [REJEITAR]
           ↓                 ↓
  Mantém cancelado    REVERTE:
  (confirmação)       ativo = True
                      status = 'APROVADO'
                      (pedido volta!)
```

---

## 🗄️ Estrutura de Dados

### Modelo: `PedidoVendaMoto` (Modificado)

**Campo Adicionado:**
```python
status = db.Column(db.String(20), default='APROVADO', nullable=False, index=True)
# Valores: 'PENDENTE', 'APROVADO', 'REJEITADO', 'CANCELADO'
```

**Compatibilidade:**
- Default = 'APROVADO' mantém pedidos existentes funcionando normalmente
- Validações adicionadas em `faturar_pedido_completo()` para garantir que apenas pedidos aprovados sejam faturados

### Modelo: `PedidoVendaAuditoria` (Novo)

```python
class PedidoVendaAuditoria(db.Model):
    id                  # PK
    pedido_id           # FK para PedidoVendaMoto
    acao                # 'INSERCAO' | 'CANCELAMENTO'
    observacao          # Motivo/justificativa
    solicitado_por      # Nome do usuário solicitante
    solicitado_em       # Timestamp da solicitação
    confirmado          # Boolean (aprovado)
    rejeitado           # Boolean (rejeitado)
    motivo_rejeicao     # Texto (obrigatório se rejeitado=True)
    confirmado_por      # Nome do gestor que confirmou/rejeitou
    confirmado_em       # Timestamp da confirmação/rejeição
```

**Índices:**
- `idx_auditoria_pedido`: pedido_id
- `idx_auditoria_acao`: acao
- `idx_auditoria_pendente`: confirmado, rejeitado
- `idx_auditoria_acao_status`: acao, confirmado, rejeitado

---

## 📁 Arquivos Modificados/Criados

### Backend (Models)
- ✅ `app/motochefe/models/vendas.py` - Adicionado campo `status` e modelo `PedidoVendaAuditoria`
- ✅ `app/motochefe/models/__init__.py` - Exportar `PedidoVendaAuditoria`

### Backend (Services)
- ✅ `app/motochefe/services/pedido_service.py` - Modificado `criar_pedido_completo()` e `faturar_pedido_completo()`

### Backend (Routes)
- ✅ `app/motochefe/routes/vendas.py` - Adicionadas rotas:
  - `GET /motochefe/confirmacao-pedidos` - Lista pendências
  - `GET /motochefe/confirmacao-pedidos/historico` - Histórico de confirmações
  - `POST /motochefe/pedidos/<id>/solicitar-cancelamento` - Solicita cancelamento
  - `POST /motochefe/pedidos/auditoria/<id>/aprovar` - Aprova ação
  - `POST /motochefe/pedidos/auditoria/<id>/rejeitar` - Rejeita ação

- ✅ `app/motochefe/routes/__init__.py` - Context processor local (templates motochefe)
- ✅ `app/__init__.py` - Context processor global (navbar com contador)

### Frontend (Templates)
- ✅ `app/templates/motochefe/vendas/pedidos/confirmacao_pedidos.html` - Tela de pendências
- ✅ `app/templates/motochefe/vendas/pedidos/historico_confirmacoes.html` - Tela de histórico
- ✅ `app/templates/motochefe/vendas/pedidos/listar.html` - Adicionado botão "Cancelar"
- ✅ `app/templates/motochefe/dashboard_motochefe.html` - Link com badge
- ✅ `app/templates/base.html` - Link no navbar MotoChefe com badge de contador

### Migrations
- ✅ `app/motochefe/scripts/migration_confirmacao_pedidos_local.py` - Script Python
- ✅ `app/motochefe/scripts/migration_confirmacao_pedidos_render.sql` - Script SQL

---

## 🚀 Como Usar

### Para Usuários (Criação de Pedido)

1. Acesse **Novo Pedido**
2. Preencha o formulário normalmente
3. Ao salvar:
   - ✅ Pedido é criado com sucesso
   - ⚠️ **Não aparece na lista** (está pendente)
   - 📧 Mensagem: "Aguardando aprovação na tela Confirmação de Pedidos"

### Para Usuários (Cancelamento)

1. Acesse **Pedidos de Venda**
2. Clique em **Cancelar** no pedido desejado
3. Digite o motivo do cancelamento
4. Ao confirmar:
   - ❌ Pedido **SOME** da lista imediatamente
   - ⚠️ Aguarda aprovação do gestor

### Para Gestores (Aprovação)

**Como acessar:**
- **Opção 1**: Menu navbar → **MotoChefe** → **Confirmação de Pedidos** (badge vermelho mostra quantidade)
- **Opção 2**: Dashboard MotoChefe → Card "Vendas" → **Confirmação de Pedidos** (badge vermelho)
- **URL direta**: `/motochefe/confirmacao-pedidos`

**Fluxo de aprovação:**
1. Acesse **Confirmação de Pedidos**
2. Visualize todas as ações pendentes na tabela
3. Para cada ação:
   - 👁️ **Ver** - Abre detalhes do pedido em nova aba
   - ✅ **Aprovar** - Modal de confirmação → Efetiva a ação
   - ❌ **Rejeitar** - Modal com campo obrigatório de motivo → Reverte ou mantém inativo
4. **Ver Histórico** - Acesse o histórico completo de todas as confirmações processadas

---

## 🔧 Instalação

### Passo 1: Rodar Migration Localmente

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python3 app/motochefe/scripts/migration_confirmacao_pedidos_local.py
```

**Saída esperada:**
```
============================================================
MIGRATION: Sistema de Confirmação de Pedidos
============================================================

PASSO 1: Adicionar campo 'status' em PedidoVendaMoto
------------------------------------------------------------
✅ Campo 'status' adicionado com sucesso!
✅ Índice idx_pedido_status criado com sucesso!

PASSO 2: Criar tabela PedidoVendaAuditoria
------------------------------------------------------------
✅ Tabela 'pedido_venda_auditoria' criada com sucesso!
✅ Todos os índices criados com sucesso!

============================================================
✅ MIGRATION CONCLUÍDA COM SUCESSO!
============================================================
```

### Passo 2: Testar Localmente

1. ✅ Criar novo pedido → Verificar se fica PENDENTE
2. ✅ Aprovar pedido → Verificar se aparece na lista
3. ✅ Cancelar pedido → Verificar se some da lista
4. ✅ Rejeitar cancelamento → Verificar se volta

### Passo 3: Rodar no Render (Produção)

1. Acessar Shell do PostgreSQL no Render
2. Copiar e colar o conteúdo de `migration_confirmacao_pedidos_render.sql`
3. Executar

---

## 🎨 Interface

### Tela 1: Confirmação de Pedidos (Pendentes)

```
╔════════════════════════════════════════════════════════════╗
║ 🎯 Confirmação de Pedidos                    [Voltar]      ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║ ⚠️ 3 ação(ões) aguardando confirmação                      ║
║                                                             ║
║ ┌─────────────────────────────────────────────────────┐   ║
║ │ Ação    │ Pedido  │ Cliente │ Valor │ Solicitado │ │   ║
║ ├─────────────────────────────────────────────────────┤   ║
║ │ 🔵 INS  │ MC 1234 │ Cliente │ R$... │ João 10/01 ││   ║
║ │ [✅ Aprovar] [❌ Rejeitar] [👁️ Ver]               ││   ║
║ ├─────────────────────────────────────────────────────┤   ║
║ │ 🔴 CANC │ MC 1235 │ Cliente │ R$... │ Maria 09/01││   ║
║ │ [✅ Aprovar] [❌ Rejeitar] [👁️ Ver]               ││   ║
║ └─────────────────────────────────────────────────────┘   ║
╚════════════════════════════════════════════════════════════╝
```

### Tela 2: Histórico de Confirmações

**Acesso:** Botão "Ver Histórico" na tela de Confirmação de Pedidos

**Recursos:**
- ✅ Filtros por: Ação (Inserção/Cancelamento), Status (Aprovado/Rejeitado), Data Início/Fim
- ✅ Paginação (50 registros por página)
- ✅ Modal com detalhes completos de cada auditoria
- ✅ Link direto para ver o pedido completo

**Campos exibidos no modal de detalhes:**
```
📄 DADOS DO PEDIDO
- Número, Data, Cliente
- Valor Total, Qtd Motos
- Status Atual do Pedido

⚙️ DADOS DA AÇÃO
- Tipo de Ação (Inserção/Cancelamento)
- Resultado (Aprovado/Rejeitado)
- ID da Auditoria
- Pedido está Ativo?

👤 SOLICITAÇÃO
- Solicitado por: [Nome]
- Data/Hora: [dd/mm/yyyy às hh:mm:ss]
- Observação: [Motivo/Justificativa]

✅ CONFIRMAÇÃO/REJEIÇÃO
- Confirmado por: [Nome]
- Data/Hora: [dd/mm/yyyy às hh:mm:ss]
- Motivo da Rejeição: [Se rejeitado]
```

### Badge no Dashboard

```
Vendas
├── 📄 Pedidos de Venda
├── ⚠️ Confirmação de Pedidos [🔴 3]  ← NOVO
├── 🧾 Títulos a Receber
└── 💰 Comissões
```

---

## ✅ Validações Implementadas

### Ao Faturar Pedido
```python
❌ Pedido com status != 'APROVADO' não pode ser faturado
❌ Pedido inativo não pode ser faturado
✅ Apenas pedidos APROVADOS e ATIVOS podem ser faturados
```

### Ao Cancelar Pedido
```python
❌ Pedido já cancelado não pode ser cancelado novamente
❌ Pedido faturado não pode ser cancelado
✅ Motivo do cancelamento é obrigatório
```

### Ao Aprovar/Rejeitar
```python
❌ Ação já aprovada não pode ser aprovada novamente
❌ Ação já rejeitada não pode ser rejeitada novamente
✅ Motivo da rejeição é obrigatório
```

---

## 🔍 Consultas Úteis (SQL)

### Ver todas as pendências
```sql
SELECT
    a.id,
    a.acao,
    p.numero_pedido,
    a.solicitado_por,
    a.solicitado_em,
    a.observacao
FROM pedido_venda_auditoria a
JOIN pedido_venda_moto p ON a.pedido_id = p.id
WHERE a.confirmado = FALSE
AND a.rejeitado = FALSE
ORDER BY a.solicitado_em DESC;
```

### Ver pedidos pendentes de aprovação
```sql
SELECT
    numero_pedido,
    status,
    ativo,
    valor_total_pedido,
    criado_em
FROM pedido_venda_moto
WHERE status = 'PENDENTE'
AND ativo = FALSE;
```

### Histórico de aprovações/rejeições
```sql
SELECT
    a.acao,
    p.numero_pedido,
    a.solicitado_por,
    a.solicitado_em,
    CASE
        WHEN a.confirmado THEN 'APROVADO'
        WHEN a.rejeitado THEN 'REJEITADO'
        ELSE 'PENDENTE'
    END as resultado,
    a.confirmado_por,
    a.confirmado_em
FROM pedido_venda_auditoria a
JOIN pedido_venda_moto p ON a.pedido_id = p.id
ORDER BY a.confirmado_em DESC NULLS LAST
LIMIT 20;
```

---

## 📊 Impactos em Código Existente

### ✅ Compatibilidade Mantida

1. **Pedidos Existentes**: Todos recebem `status='APROVADO'` automaticamente
2. **Queries `ativo=True`**: Continuam funcionando normalmente
3. **Campo `faturado`**: Não foi alterado, continua funcionando
4. **Campo `enviado`**: Não foi alterado, continua funcionando

### 🆕 Mudanças de Comportamento

1. **Novos Pedidos**: Agora são criados com `ativo=False`, `status='PENDENTE'`
2. **Cancelamento**: Agora é imediato (pedido some da lista antes da aprovação)
3. **Faturamento**: Apenas pedidos com `status='APROVADO'` podem ser faturados

---

## 🐛 Troubleshooting

### Pedido não aparece na lista após criação
✅ **ESPERADO** - Pedido aguarda aprovação na tela "Confirmação de Pedidos"

### Não consigo faturar pedido
❌ Verificar se `status='APROVADO'` e `ativo=True`

### Badge não aparece no dashboard
❌ Verificar se context_processor está registrado
❌ Verificar se `count_pendentes_motochefe` está disponível no template

---

## 👥 Autores

- **Desenvolvedor**: Claude AI (Anthropic)
- **Solicitante**: Rafael Nascimento
- **Data**: 11/01/2025

---

## 📝 Notas Importantes

1. ⚠️ **Permissões**: Qualquer usuário com acesso ao MotoChefe pode solicitar inserção/cancelamento
2. ⚠️ **Aprovação**: Qualquer usuário com acesso ao MotoChefe pode aprovar (ajustar se necessário)
3. ✅ **Auditoria**: Todas as ações são registradas com usuário e timestamp
4. ✅ **Reversível**: Rejeitar cancelamento REVERTE o pedido ao estado normal

---

## 🔮 Melhorias Futuras (Opcional)

- [ ] Adicionar permissão específica para aprovar (ex: `pode_aprovar_pedidos`)
- [ ] Notificações por email quando há pendências
- [ ] Filtros por tipo de ação na tela de confirmação
- [ ] Histórico completo de auditoria por pedido
- [ ] Dashboard com métricas de aprovações/rejeições

---

**FIM DA DOCUMENTAÇÃO**
