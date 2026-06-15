<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Status de agendamento por item de embarque (badge clicável + modal de confirmação) e sua sincronização para Separacao/EntregaMonitorada/AgendamentoEntrega
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 📅 Botão de Confirmação de Agendamento - EmbarqueItem

> **Papel:** explica o controle de status de agendamento exibido em cada item de embarque (badge clicável + modal) e a sincronização automática que ele dispara para outras entidades.

## Contexto

Cada item de embarque exibe um indicador compacto do status de agendamento que abre um modal de confirmação. Ao salvar, o sistema sincroniza data e confirmação para `Separacao`, `EntregaMonitorada` e `AgendamentoEntrega`. Este documento descreve o comportamento, a UI, o fluxo backend/frontend e onde tocar para customizar.

## Indice

- [Objetivo](#-objetivo)
- [Funcionalidades](#-funcionalidades)
- [Arquivos modificados](#-arquivos-modificados)
- [Layout](#-layout)
- [Impressão](#️-impressão)
- [Fluxo completo](#-fluxo-completo)
- [Exemplos de uso](#-exemplos-de-uso)
- [Troubleshooting](#-troubleshooting)
- [Logs](#-logs)
- [Customização](#-customização)
- [Checklist de implementação](#-checklist-de-implementação)
- [Próximos passos (opcional)](#-próximos-passos-opcional)

**Data:** 2025-01-06
**Status:** ✅ Implementado e pronto para uso

---

## 🎯 OBJETIVO

Adicionar visualização compacta do status de agendamento nos itens de embarque, com possibilidade de confirmar agendamento através de um modal simples.

---

## ✨ FUNCIONALIDADES

### 1. Badge Visual com 3 Estados

A UI real é um `<span class="badge ... agendamento-badge">` clicável dentro de um `<div class="agendamento-status">` (não um `<button>` standalone). Cada badge dispara `abrirModalConfirmacao(...)` no clique. A funcionalidade dos 3 estados é a descrita abaixo.

#### 🔵 Estado: Confirmado (Azul)
- **Quando:** `agendamento_confirmado=True` E `data_agenda` preenchida
- **Visual:**
  ```
  ✓
  ```
- **Classe:** `badge bg-primary agendamento-badge`

#### 🟡 Estado: Aguardando (Amarelo)
- **Quando:** `data_agenda` preenchida MAS `agendamento_confirmado=False`
- **Visual:**
  ```
  ⏳
  ```
- **Classe:** `badge bg-warning agendamento-badge`

#### ⚪ Estado: Agendar (Cinza)
- **Quando:** `data_agenda` vazia/NULL
- **Visual:**
  ```
  📅
  ```
- **Classe:** `badge bg-secondary agendamento-badge`

---

### 2. Modal de Confirmação

**Ao clicar no badge**, abre modal compacto com:

- **Campo:** Data de Agendamento (DD/MM/AAAA)
- **Checkbox:** Agendamento Confirmado
- **Botões:** Cancelar / Salvar

**Validação:**
- Data obrigatória para salvar
- Máscara automática DD/MM/AAAA

---

### 3. Sincronização Automática

Ao salvar a confirmação, **sincroniza automaticamente** com:

1. ✅ `Separacao` → `agendamento`, `agendamento_confirmado`
2. ✅ `EntregaMonitorada` → `data_agenda`
3. ✅ `AgendamentoEntrega` → Cria registro histórico

**Service usado:** `SincronizadorAgendamentoService`

---

## 📁 ARQUIVOS MODIFICADOS

### 1. Template
**Arquivo:** `app/templates/embarques/visualizar_embarque.html`

**Mudanças (linhas aproximadas — o template cresceu desde a implementação inicial):**
- Badge/estados (3 estados) dentro de `div.agendamento-status`: ~403-430
- Função JavaScript `abrirModalConfirmacao`: linha ~921
- Modal de confirmação (`#modalConfirmarAgendamento`): linha ~1106

> As linhas exatas variam conforme o template é editado; use os identificadores (`agendamento-status`, `abrirModalConfirmacao`, `modalConfirmarAgendamento`) para localizar os blocos.

### 2. Backend
**Arquivo:** `app/embarques/routes.py`

**Endpoint novo:**
```python
POST /embarques/item/<int:item_id>/confirmar_agendamento

Payload:
{
    "data_agenda": "DD/MM/AAAA",
    "agendamento_confirmado": true/false
}
```

---

## 🎨 LAYOUT

### Tabela de Itens do Embarque

```
| Cliente | Pedido | NF | Protocolo | Data Agenda | Confirmação | Volumes | ... |
|---------|--------|----|-----------
|-------------|-------------|---------|-----|
| João SA | 12345  | 98 | PROTO123  | 01/01/2025  | [ ✓ ]       |   10    | ... |
```

**Badge compacto:**
- Renderizado dentro da célula do item, no bloco `agendamento-status`
- Indicador minimalista (ícone de estado) clicável
- Padding mínimo para economizar espaço

---

## 🖨️ IMPRESSÃO

A coluna "Confirmação" é **automaticamente ocultada na impressão**.

**CSS aplicado:**
```css
.no-print {
    display: none !important;  /* Na impressão */
}
```

**Resultado:** Layout de impressão permanece igual ao anterior, sem a coluna de confirmação.

---

## 🔄 FLUXO COMPLETO

### 1. Usuário Clica no Badge
```javascript
onclick="abrirModalConfirmacao('{{ item.id }}', '{{ item.data_agenda or '' }}', true, {{ 'true' if _eh_cv else 'false' }}, '{{ _hora }}')"
```

### 2. Modal Abre Pré-preenchido
- Data atual do item (se houver)
- Checkbox marcado se já confirmado

### 3. Usuário Altera e Salva
```javascript
fetch('/embarques/item/123/confirmar_agendamento', {
    method: 'POST',
    body: JSON.stringify({
        data_agenda: '01/01/2025',
        agendamento_confirmado: true
    })
})
```

### 4. Backend Processa
```python
# 1. Atualiza EmbarqueItem
item.data_agenda = '01/01/2025'
item.agendamento_confirmado = True

# 2. Sincroniza outras tabelas
sincronizador.sincronizar_agendamento(...)

# 3. Salva no banco
db.session.commit()
```

### 5. Frontend Atualiza
- Fecha modal
- Mostra mensagem de sucesso
- **Recarrega página** para atualizar o badge

---

## 📊 EXEMPLOS DE USO

### Cenário 1: Agendar pela primeira vez
1. Badge está **cinza** ("📅")
2. Usuário clica
3. Preenche data: `15/01/2025`
4. Deixa checkbox desmarcado (aguardando confirmação do cliente)
5. Salva
6. **Badge vira amarelo** ("⏳ Aguardando")

### Cenário 2: Confirmar agendamento existente
1. Badge está **amarelo** ("⏳ Aguardando")
2. Cliente confirma agendamento por telefone
3. Usuário clica no badge
4. Marca checkbox "Agendamento Confirmado"
5. Salva
6. **Badge vira azul** ("✓ Confirmado")

### Cenário 3: Alterar data de agendamento confirmado
1. Badge está **azul** ("✓ Confirmado")
2. Cliente pede para remarcar
3. Usuário clica no badge
4. Altera data: `20/01/2025`
5. Desmarca checkbox (aguardando nova confirmação)
6. Salva
7. **Badge vira amarelo** com nova data

---

## 🐛 TROUBLESHOOTING

### Problema: Badge não muda de cor após salvar
**Solução:** A página é recarregada automaticamente. Verificar se `window.location.reload()` está funcionando.

### Problema: Erro "Data obrigatória"
**Solução:** Preencher campo "Data de Agendamento" antes de clicar em Salvar.

### Problema: Coluna aparece na impressão
**Solução:** Verificar se classe `no-print` está na tag `<th>` e `<td>`:
```html
<th class="no-print">Confirmação</th>
<td class="no-print">...</td>
```

### Problema: Sincronização falha
**Solução:**
1. Verificar logs do console: `[CONFIRMAÇÃO AGENDAMENTO] ...`
2. Confirmar que `SincronizadorAgendamentoService` está importado
3. Verificar se `separacao_lote_id` está preenchido no EmbarqueItem

---

## 📝 LOGS

### Backend
```python
[CONFIRMAÇÃO AGENDAMENTO] Item 123 atualizado: data=01/01/2025, confirmado=True
[CONFIRMAÇÃO AGENDAMENTO] Item 123: Separacao, EntregaMonitorada, AgendamentoEntrega
```

### Frontend (Console do navegador)
```javascript
Salvando confirmação para item 123...
✅ Agendamento atualizado com sucesso!
Recarregando página...
```

---

## 🎨 CUSTOMIZAÇÃO

### Alterar cores dos badges

**Arquivo:** `app/templates/embarques/visualizar_embarque.html` (bloco `agendamento-status`, ~403-430)

```html
<!-- Confirmado: Trocar bg-primary por bg-success (verde) -->
<span class="badge bg-success agendamento-badge">

<!-- Aguardando: Trocar bg-warning por bg-info (azul claro) -->
<span class="badge bg-info agendamento-badge">

<!-- Agendar: Trocar bg-secondary por bg-light text-dark -->
<span class="badge bg-light text-dark agendamento-badge">
```

### Alterar tamanho do badge

```html
<!-- Ajustar style inline no badge -->
style="font-size: 0.7rem; padding: 0.2rem 0.3rem;"

<!-- Aumentar: -->
style="font-size: 0.9rem; padding: 0.4rem 0.5rem;"

<!-- Diminuir: -->
style="font-size: 0.6rem; padding: 0.1rem 0.2rem;"
```

### Alterar conteúdo do badge

O conteúdo de cada estado é o ícone dentro do `<span>` (`✓`, `⏳`, `📅`). Para usar texto, substituir o ícone pelo rótulo desejado em cada um dos três ramos do bloco condicional.

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [x] Coluna adicionada na tabela
- [x] Badge com 3 estados implementado
- [x] Modal de confirmação criado
- [x] JavaScript funcionando
- [x] Endpoint backend criado
- [x] Sincronização automática integrada
- [x] CSS para ocultar na impressão
- [x] Validação de data
- [x] Logs implementados
- [x] Documentação criada

---

## 🚀 PRÓXIMOS PASSOS (OPCIONAL)

Melhorias futuras candidatas (não implementadas):

1. **Notificação por email** quando agendamento for confirmado
2. **Histórico de alterações** de agendamento
3. **Filtro na listagem** para mostrar apenas confirmados/pendentes
4. **Dashboard** com estatísticas de agendamentos
5. **Integração com calendário** (Google Calendar, Outlook)

---

**Implementado por:** Claude Code
**Data:** 2025-01-06
**Versão:** 1.0
