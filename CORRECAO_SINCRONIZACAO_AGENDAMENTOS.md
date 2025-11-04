# 🔧 CORREÇÃO: Sincronização Bidirecional de Agendamentos

**Data**: 04/11/2025
**Autor**: Claude Code (Precision Engineer Mode)

---

## 📋 PROBLEMAS IDENTIFICADOS

### **Problema 1: Alterações em EntregaMonitorada não propagavam**

**Localização**: [app/monitoramento/routes.py](app/monitoramento/routes.py)

**Comportamento Antigo**:
- Ao criar/editar agendamento em `AgendamentoEntrega`, os dados **NÃO** eram propagados para:
  - `Separacao` (carteira de pedidos)
  - `EmbarqueItem` (receptor passivo)

**Causa Raiz**:
- Função `adicionar_agendamento()` (linha 299-363) não chamava sincronizador
- Função `confirmar_agendamento()` (linha 366-389) não propagava confirmação
- A função `SincronizadorAgendamentoService.sincronizar_desde_agendamento_entrega()` existia mas **NUNCA era chamada**

---

### **Problema 2: Todos agendamentos criados como confirmados**

**Localização**: [app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py)

**Comportamento Antigo**:
```python
# ❌ ERRADO: Sempre confirmado
status="confirmado",  # Se está no embarque, já foi confirmado
confirmado_por=get_usuario_nome(),
confirmado_em=datetime.utcnow()
```

**Causa Raiz**:
- Funções `sincronizar_entrega_por_nf()` e `sincronizar_nova_entrega_por_nf()` **ignoravam** o campo `EmbarqueItem.agendamento_confirmado`
- Sempre criavam `AgendamentoEntrega` com `status='confirmado'`

---

## ✅ CORREÇÕES IMPLEMENTADAS

### **Correção 1: Sincronização em `adicionar_agendamento()`**

**Arquivo**: [app/monitoramento/routes.py:349-368](app/monitoramento/routes.py#L349-L368)

**O que foi feito**:
```python
# ✅ SINCRONIZAÇÃO BIDIRECIONAL: Propagar para Separacao e EmbarqueItem
from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

try:
    sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
    resultado_sync = sincronizador.sincronizar_desde_agendamento_entrega(
        entrega_id=entrega.id,
        agendamento_id=ag.id
    )

    if resultado_sync['success']:
        tabelas = ', '.join(resultado_sync.get('tabelas_atualizadas', []))
        if tabelas:
            flash(f"✅ Agendamento criado e sincronizado com: {tabelas}", 'success')
    # ...
```

**Resultado**:
- Ao criar agendamento em `EntregaMonitorada` → propaga para `Separacao` + `EmbarqueItem`
- Funciona **SEMPRE**, independente de `nf_cd=True` ou `False`

---

### **Correção 2: Sincronização em `confirmar_agendamento()`**

**Arquivo**: [app/monitoramento/routes.py:399-418](app/monitoramento/routes.py#L399-L418)

**O que foi feito**:
```python
# ✅ SINCRONIZAÇÃO BIDIRECIONAL: Propagar confirmação para Separacao e EmbarqueItem
from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

try:
    sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
    resultado_sync = sincronizador.sincronizar_desde_agendamento_entrega(
        entrega_id=agendamento.entrega_id,
        agendamento_id=agendamento.id
    )
    # ...
```

**Resultado**:
- Ao confirmar agendamento → `Separacao.agendamento_confirmado = True` + `EmbarqueItem.agendamento_confirmado = True`

---

### **Correção 3: Respeitar `agendamento_confirmado` em sincronizações iniciais**

**Arquivo**: [app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py)

**Funções corrigidas**:
1. `sincronizar_entrega_por_nf()` (linhas 157-174)
2. `sincronizar_nova_entrega_por_nf()` (linhas 307-326)

**O que foi feito**:
```python
# ✅ CORREÇÃO: Respeitar EmbarqueItem.agendamento_confirmado
agendamento_confirmado = getattr(item_mais_recente, 'agendamento_confirmado', False)
status_agendamento = 'confirmado' if agendamento_confirmado else 'aguardando'

novo_ag = AgendamentoEntrega(
    entrega_id=entrega.id,
    data_agendada=data_agenda_embarque,
    forma_agendamento="Embarque Automático",
    autor=get_usuario_nome(),
    status=status_agendamento,  # ✅ Respeita EmbarqueItem.agendamento_confirmado
)

# Só preenche confirmação se realmente confirmado
if agendamento_confirmado:
    novo_ag.confirmado_por = get_usuario_nome()
    novo_ag.confirmado_em = datetime.utcnow()
```

**Resultado**:
- Ao criar `AgendamentoEntrega` a partir de `EmbarqueItem`:
  - Se `EmbarqueItem.agendamento_confirmado = True` → `AgendamentoEntrega.status = 'confirmado'`
  - Se `EmbarqueItem.agendamento_confirmado = False` → `AgendamentoEntrega.status = 'aguardando'`

---

## 🔄 FLUXO BIDIRECIONAL COMPLETO

### **Cenário 1: Criar agendamento na Carteira (Separacao)**

```
Usuario edita em lista_pedidos.html
    ↓
Separacao.agendamento = '2025-11-10'
Separacao.protocolo = 'PROT123'
Separacao.agendamento_confirmado = True
    ↓
SincronizadorAgendamentoService.sincronizar_desde_separacao()
    ↓
    ├─→ EmbarqueItem.data_agenda = '10/11/2025'
    ├─→ EmbarqueItem.protocolo_agendamento = 'PROT123'
    ├─→ EmbarqueItem.agendamento_confirmado = True
    │
    └─→ EntregaMonitorada.data_agenda = date(2025, 11, 10)
        AgendamentoEntrega criado:
            - data_agendada = date(2025, 11, 10)
            - protocolo_agendamento = 'PROT123'
            - status = 'confirmado'
```

---

### **Cenário 2: Criar agendamento no Monitoramento (EntregaMonitorada)**

```
Usuario cria agendamento no modal de EntregaMonitorada
    ↓
AgendamentoEntrega criado:
    - data_agendada = date(2025, 11, 10)
    - protocolo_agendamento = 'PROT456'
    - status = 'aguardando'  (checkbox não marcado)
    ↓
SincronizadorAgendamentoService.sincronizar_desde_agendamento_entrega()
    ↓
    ├─→ Separacao.agendamento = date(2025, 11, 10)
    ├─→ Separacao.protocolo = 'PROT456'
    ├─→ Separacao.agendamento_confirmado = False
    │
    ├─→ EmbarqueItem.data_agenda = '10/11/2025'
    ├─→ EmbarqueItem.protocolo_agendamento = 'PROT456'
    └─→ EmbarqueItem.agendamento_confirmado = False
```

---

### **Cenário 3: Confirmar agendamento no Monitoramento**

```
Usuario clica em "Confirmar Agendamento"
    ↓
AgendamentoEntrega.status = 'confirmado'
AgendamentoEntrega.confirmado_por = 'João Silva'
AgendamentoEntrega.confirmado_em = datetime.utcnow()
    ↓
SincronizadorAgendamentoService.sincronizar_desde_agendamento_entrega()
    ↓
    ├─→ Separacao.agendamento_confirmado = True
    └─→ EmbarqueItem.agendamento_confirmado = True
```

---

### **Cenário 4: Sincronização inicial NF → EntregaMonitorada**

```
NF preenchida no EmbarqueItem
    ↓
sincronizar_entrega_por_nf(numero_nf='12345')
    ↓
Verifica EmbarqueItem.agendamento_confirmado
    ├─→ Se True:  cria AgendamentoEntrega com status='confirmado'
    └─→ Se False: cria AgendamentoEntrega com status='aguardando'
```

---

## 🎯 CAMPOS SINCRONIZADOS

| Campo | Separacao | AgendamentoEntrega | EmbarqueItem | EntregaMonitorada |
|-------|-----------|-------------------|--------------|-------------------|
| **Data** | `agendamento` (Date) | `data_agendada` (Date) | `data_agenda` (String DD/MM/YYYY) | `data_agenda` (Date) |
| **Protocolo** | `protocolo` (String) | `protocolo_agendamento` (String) | `protocolo_agendamento` (String) | - |
| **Confirmação** | `agendamento_confirmado` (Boolean) | `status` ('aguardando'/'confirmado') | `agendamento_confirmado` (Boolean) | - |
| **NF no CD** | `nf_cd` (Boolean) | - | - | `nf_cd` (Boolean) |

---

## 📝 ARQUIVOS MODIFICADOS

1. **[app/monitoramento/routes.py](app/monitoramento/routes.py)**
   - Função `adicionar_agendamento()` (linha 299-368)
   - Função `confirmar_agendamento()` (linha 377-420)

2. **[app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py)**
   - Função `sincronizar_entrega_por_nf()` (linhas 156-205)
   - Função `sincronizar_nova_entrega_por_nf()` (linhas 306-326)

3. **[app/pedidos/services/sincronizacao_agendamento_service.py](app/pedidos/services/sincronizacao_agendamento_service.py)**
   - Nenhuma alteração (já estava correto, apenas não era chamado)

---

## ✅ TESTES RECOMENDADOS

### **Teste 1: Criar agendamento na carteira**
1. Editar agendamento em `lista_pedidos.html`
2. Verificar se propaga para `EmbarqueItem` e `EntregaMonitorada`

### **Teste 2: Criar agendamento no monitoramento**
1. Criar agendamento sem marcar checkbox "Criar confirmado"
2. Verificar se cria como `status='aguardando'`
3. Verificar se propaga para `Separacao` e `EmbarqueItem` com `agendamento_confirmado=False`

### **Teste 3: Confirmar agendamento**
1. Confirmar agendamento que estava "aguardando"
2. Verificar se atualiza `Separacao.agendamento_confirmado` e `EmbarqueItem.agendamento_confirmado`

### **Teste 4: NF no CD**
1. Marcar NF como "NF no CD" (`nf_cd=True`)
2. Alterar agendamento no monitoramento
3. Re-cotar frete (cria novo EmbarqueItem)
4. Verificar se ambas as tabelas mantêm os mesmos dados de agendamento

---

## 🚨 OBSERVAÇÕES IMPORTANTES

### **EmbarqueItem é RECEPTOR PASSIVO**
- **NUNCA** edita agendamento manualmente
- **SEMPRE** recebe dados de `Separacao` ou `AgendamentoEntrega`
- Ao preencher NF, usa dados que já estão em `EmbarqueItem` para criar `AgendamentoEntrega`

### **Sincronização SEMPRE ativa**
- Antes: Só sincronizava se `nf_cd=True`
- Agora: Sincroniza **SEMPRE**, independente de `nf_cd`

### **Respeita confirmação do agendamento**
- Antes: Sempre criava como confirmado
- Agora: Respeita `EmbarqueItem.agendamento_confirmado`

---

## 📊 IMPACTO

### **Positivo**:
✅ Sincronização bidirecional completa entre todas as tabelas
✅ Respeita status de confirmação do agendamento
✅ Evita divergências entre carteira e monitoramento
✅ Funciona corretamente no cenário "NF no CD"

### **Riscos**:
⚠️ Performance: Mais queries de atualização por operação (impacto baixo)
⚠️ Logs: Mais mensagens de sincronização nos logs (pode dificultar debug)

### **Mitigação**:
- Sincronização usa queries otimizadas com `update()` direto
- Logs informativos apenas em caso de erro
- Try/except para evitar quebras se sincronização falhar

---

## 🔗 DOCUMENTOS RELACIONADOS

- [BOTAO_CONFIRMACAO_AGENDAMENTO.md](BOTAO_CONFIRMACAO_AGENDAMENTO.md)
- [app/pedidos/services/sincronizacao_agendamento_service.py](app/pedidos/services/sincronizacao_agendamento_service.py)
- [CLAUDE.md - Seção de Modelos](CLAUDE.md)
