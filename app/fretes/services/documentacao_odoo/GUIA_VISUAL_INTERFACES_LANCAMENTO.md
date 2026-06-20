<!-- doc:meta
tipo: how-to
camada: L2
sot_de: —
hub: app/fretes/CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->

> **Papel:** guia visual (wireframes ASCII) das interfaces do botao "Lancar no Odoo": estados, modal, feedback.

# 🎨 GUIA VISUAL - Interfaces de Lançamento no Odoo

**Data:** 14/11/2025
**Objetivo:** Explicar VISUALMENTE como o usuário interage com o sistema

---

## 📍 **1. ACESSO À INTERFACE**

### **Caminho de Navegação:**
```
Login → Menu Fretes → Listar Fretes → Clica em um Frete → Tela de Visualização
```

### **URL:**
```
/fretes/123   (onde 123 é o ID do frete)
```

### **Permissão:**
- ✅ Qualquer usuário logado pode **visualizar**
- ✅ Apenas usuários **Financeiro** podem **lançar no Odoo** (`@require_financeiro()`)

---

## 🖼️ **2. TELA PRINCIPAL - Visualizar Frete**

### **Aparência Atual:**

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Frete #123 [BADGE STATUS]                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [← Voltar]  [✏️ Editar]  [🚚 Ver Embarque]                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  ☁️ LANÇAR NO ODOO  ← NOVO BOTÃO VERDE              │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  [⚠️ Cancelar CTe]  [🗑️ Excluir Tudo]                          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DADOS DO FRETE:                                                │
│  • Cliente: FULANO LTDA                                         │
│  • Transportadora: TRANSPORTES XYZ                              │
│  • Valor CTe: R$ 1.500,00                                       │
│  • Vencimento: 30/11/2025                                       │
│  ...                                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ **3. ESTADOS DO BOTÃO "LANÇAR NO ODOO"**

### **ESTADO 1: Frete NÃO Lançado**
```html
┌────────────────────────────────────┐
│  ☁️  LANÇAR NO ODOO               │  ← BOTÃO VERDE (btn-success)
└────────────────────────────────────┘
```

**Quando aparece:**
- Frete existe
- Campo `odoo_invoice_id` é NULL
- Usuário tem permissão de Financeiro

**Ao clicar:** Abre o modal de lançamento

---

### **ESTADO 2: Frete JÁ Lançado**
```html
┌────────────────────────────────────┐
│  ✅  LANÇADO NO ODOO              │  ← BOTÃO VERDE DESABILITADO
└────────────────────────────────────┘
      (botão cinza, não clicável)
```

**Quando aparece:**
- Campo `odoo_invoice_id` tem valor (ex: 405941)

**Tooltip ao passar o mouse:**
```
"Já lançado no Odoo"
```

---

## 🎯 **4. MODAL DE LANÇAMENTO (INTERFACE PRINCIPAL)**

Quando o usuário clica em "Lançar no Odoo", abre este modal:

```
╔═══════════════════════════════════════════════════════════════╗
║  ☁️  Lançar Frete no Odoo                              [X]   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ ℹ️  PROCESSO AUTOMATIZADO                             │   ║
║  │                                                         │   ║
║  │ Este processo executará automaticamente 16 etapas:     │   ║
║  │ • Lançamento no DF-e (6 etapas)                        │   ║
║  │ • Criação e confirmação do Purchase Order (5 etapas)   │   ║
║  │ • Criação da Invoice (2 etapas)                        │   ║
║  │ • Confirmação final da Invoice (3 etapas)              │   ║
║  └────────────────────────────────────────────────────────┘   ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ ✅ Vencimento atual do frete: 30/11/2025              │   ║
║  └────────────────────────────────────────────────────────┘   ║
║                                                                ║
║  📅 Data de Vencimento:                                       ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │  [  30/11/2025  ]  ← Campo de data                    │   ║
║  └────────────────────────────────────────────────────────┘   ║
║     Data em que o frete deverá ser pago no Odoo               ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │  [Barra de Progresso]  ← Oculta inicialmente          │   ║
║  └────────────────────────────────────────────────────────┘   ║
║                                                                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                ║
║      [Cancelar]              [☁️  Lançar no Odoo]            ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
```

### **Elementos do Modal:**

1. **Título:** "☁️ Lançar Frete no Odoo"
2. **Info Box (Azul):** Explica as 16 etapas
3. **Alert Verde:** Mostra vencimento atual do frete (se existir)
4. **Campo de Data:**
   - Pré-preenchido com vencimento do frete
   - Editável pelo usuário
   - Obrigatório
5. **Barra de Progresso:** Oculta inicialmente
6. **Botões:**
   - "Cancelar" (cinza) - Fecha o modal
   - "Lançar no Odoo" (verde) - Inicia o processo

---

## ⚙️ **5. FLUXO DE LANÇAMENTO - PASSO A PASSO**

### **PASSO 1: Usuário Clica em "Lançar no Odoo" (no botão do modal)**

**O que acontece visualmente:**

```
Botão muda para:
┌────────────────────────────────────┐
│  ⏳  Lançando...                  │  ← Spinner animado
└────────────────────────────────────┘

Barra de progresso aparece:
┌─────────────────────────────────────────────────────┐
│ ▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%  │
└─────────────────────────────────────────────────────┘
│ Iniciando lançamento...
```

---

### **PASSO 2: Durante a Execução (15-60 segundos)**

**A barra de progresso NÃO atualiza em tempo real** (pois é uma requisição única).

O usuário vê:
```
┌────────────────────────────────────┐
│  ⏳  Lançando...                  │  ← Botão desabilitado
└────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%  │ ← Barra animada
└─────────────────────────────────────────────────────┘
│ Iniciando lançamento...
```

**Backend está executando:**
- Etapa 1/16: Buscar DFe...
- Etapa 2/16: Atualizar data de entrada...
- Etapa 3/16: Atualizar tipo pedido...
- ...
- Etapa 16/16: Atualizar frete local...

---

### **PASSO 3: SUCESSO! ✅**

**Barra de progresso atualiza:**
```
┌─────────────────────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  100% │ ← Verde
└─────────────────────────────────────────────────────┘
│ ✅ Lançamento concluído com sucesso! 16/16 etapas
```

**Alert popup aparece:**
```
┌────────────────────────────────────────────────┐
│  ✅ Lançamento concluído com sucesso!         │
│                                                 │
│  Etapas: 16/16                                 │
│  DFe ID: 32639                                 │
│  PO ID: 31089                                  │
│  Invoice ID: 405941                            │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

**Após clicar "OK":**
- Modal fecha automaticamente
- Página recarrega (2 segundos)
- Botão muda para "✅ Lançado no Odoo" (desabilitado)

---

### **PASSO 4: ERRO ❌**

**Se algo der errado em alguma etapa:**

**Barra de progresso fica vermelha:**
```
┌─────────────────────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  37% │ ← Vermelho
└─────────────────────────────────────────────────────┘
│ ❌ Erro na etapa 6: CTe não encontrado no Odoo
```

**Alert popup de erro:**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro no lançamento:                       │
│                                                 │
│  Erro na etapa 6: CTe não encontrado no Odoo  │
│                                                 │
│  Detalhes: Chave 332511203419...não existe    │
│                                                 │
│  Etapas concluídas: 6/16                       │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

**Modal permanece aberto** com botão "Lançar no Odoo" reabilitado para tentar novamente.

---

## 📊 **6. INFORMAÇÕES DE SUCESSO - O QUE O USUÁRIO VÊ**

### **Confirmação Visual Imediata:**

1. **Alert popup com detalhes:**
   ```
   ✅ Lançamento concluído com sucesso!

   Etapas: 16/16
   DFe ID: 32639
   PO ID: 31089
   Invoice ID: 405941
   ```

2. **Botão muda de estado:**
   ```
   ANTES:  [☁️  Lançar no Odoo]  (verde, clicável)
   DEPOIS: [✅  Lançado no Odoo] (cinza, desabilitado)
   ```

3. **Página recarrega automaticamente** (2 segundos após fechar o alert)

---

### **Confirmação no Sistema:**

Após recarregar, o usuário pode verificar:

**No card de dados do frete (se adicionarmos):**
```
┌─────────────────────────────────────────────────┐
│  DADOS DO ODOO:                                 │
│  • DFe ID: 32639                                │
│  • Purchase Order ID: 31089                     │
│  • Invoice ID: 405941                           │
│  • Lançado em: 14/11/2025 15:30                │
│  • Lançado por: rafael                          │
└─────────────────────────────────────────────────┘
```

---

### **Confirmação no Odoo:**

O usuário pode acessar o Odoo e verificar:

1. **DF-e criado:** `https://odoo.nacomgoya.com.br/web#id=32639&model=l10n_br_ciel_it_account.dfe`
2. **Purchase Order:** `https://odoo.nacomgoya.com.br/web#id=31089&model=purchase.order`
3. **Invoice confirmada:** `https://odoo.nacomgoya.com.br/web#id=405941&model=account.move`

---

## 🔍 **7. AUDITORIA - COMO VERIFICAR O QUE FOI FEITO**

### **Opção 1: Via Interface Admin (se criarmos)**

```
/fretes/123/auditoria-odoo

┌─────────────────────────────────────────────────────────────┐
│  📋 Auditoria do Lançamento - Frete #123                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Lançado em: 14/11/2025 15:30:25                           │
│  Lançado por: rafael (IP: 192.168.1.100)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Etapa 1/16: Buscar DFe pela chave                  │   │
│  │  Status: ✅ SUCESSO                                  │   │
│  │  Tempo: 523ms                                        │   │
│  │  Modelo: l10n_br_ciel_it_account.dfe                │   │
│  │  Ação: search_read                                   │   │
│  │  DFe ID encontrado: 32639                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Etapa 2/16: Atualizar data de entrada              │   │
│  │  Status: ✅ SUCESSO                                  │   │
│  │  Tempo: 187ms                                        │   │
│  │  Modelo: l10n_br_ciel_it_account.dfe                │   │
│  │  Ação: write                                         │   │
│  │  Campo alterado: l10n_br_data_entrada = 2025-11-14  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ... (continua para todas as 16 etapas)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### **Opção 2: Via Banco de Dados**

```sql
-- Ver todas as etapas de um frete
SELECT
    etapa,
    etapa_descricao,
    status,
    tempo_execucao_ms,
    executado_em
FROM lancamento_frete_odoo_auditoria
WHERE frete_id = 123
ORDER BY etapa;
```

**Resultado:**
```
etapa | etapa_descricao                    | status  | tempo_ms | executado_em
------+------------------------------------+---------+----------+---------------------
1     | Buscar DFe pela chave             | SUCESSO | 523      | 2025-11-14 15:30:25
2     | Atualizar data de entrada         | SUCESSO | 187      | 2025-11-14 15:30:26
3     | Atualizar tipo pedido             | SUCESSO | 145      | 2025-11-14 15:30:26
...
16    | Atualizar frete no sistema local  | SUCESSO | 98       | 2025-11-14 15:31:05
```

---

## 🚨 **8. MENSAGENS DE ERRO POSSÍVEIS**

### **Erro 1: Frete Já Lançado**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro                                       │
│                                                 │
│  Frete já foi lançado no Odoo                 │
│                                                 │
│  Invoice ID: 405941                            │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

---

### **Erro 2: CTe Não Encontrado**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro no lançamento                        │
│                                                 │
│  Nenhum CTe relacionado encontrado            │
│                                                 │
│  É necessário ter um CTe vinculado para       │
│  lançar no Odoo                                │
│                                                 │
│  Etapas concluídas: 0/16                       │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

---

### **Erro 3: Múltiplos CTes**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro no lançamento                        │
│                                                 │
│  Múltiplos CTes encontrados (3)               │
│                                                 │
│  Por favor, vincule manualmente o CTe         │
│  correto antes de lançar                       │
│                                                 │
│  Etapas concluídas: 0/16                       │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

---

### **Erro 4: Chave Inválida**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro no lançamento                        │
│                                                 │
│  Chave do CTe inválida                        │
│                                                 │
│  Chave possui 40 caracteres (esperado 44)     │
│                                                 │
│  Etapas concluídas: 0/16                       │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

---

### **Erro 5: Data Inválida**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro                                       │
│                                                 │
│  Data de vencimento inválida                  │
│                                                 │
│  Formato esperado: YYYY-MM-DD                  │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

---

### **Erro 6: Falha em Etapa Intermediária**
```
┌────────────────────────────────────────────────┐
│  ❌ Erro no lançamento:                       │
│                                                 │
│  Erro na etapa 9: Falha ao confirmar PO       │
│                                                 │
│  Detalhes: Operação fiscal não pertence à     │
│  empresa CD                                    │
│                                                 │
│  Etapas concluídas: 8/16                       │
│                                                 │
│              [OK]                               │
└────────────────────────────────────────────────┘
```

---

## 💡 **9. MELHORIAS FUTURAS SUGERIDAS**

### **Adicionar Card de Status Odoo na Tela de Visualização:**

```html
┌─────────────────────────────────────────────────┐
│  ☁️  STATUS ODOO                                │
├─────────────────────────────────────────────────┤
│                                                  │
│  {% if frete.odoo_invoice_id %}                 │
│                                                  │
│  ✅ Lançado no Odoo                             │
│                                                  │
│  • DFe ID: {{ frete.odoo_dfe_id }}              │
│  • Purchase Order: {{ frete.odoo_po_id }}       │
│  • Invoice: {{ frete.odoo_invoice_id }}         │
│                                                  │
│  Lançado em: {{ frete.lancado_odoo_em }}        │
│  Por: {{ frete.lancado_odoo_por }}              │
│                                                  │
│  [Ver Auditoria Completa]                       │
│                                                  │
│  {% else %}                                      │
│                                                  │
│  ⚠️ Ainda não lançado no Odoo                   │
│                                                  │
│  {% endif %}                                     │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

### **Criar Página de Auditoria Completa:**

**URL:** `/fretes/123/auditoria-odoo`

Mostrando:
- Timeline das 16 etapas
- Tempo de execução de cada uma
- Dados antes/depois (JSON colapsável)
- Mensagens de erro (se houver)
- Possibilidade de baixar log completo

---

## 📱 **10. RESPONSIVIDADE**

O modal funciona bem em:
- ✅ Desktop (Bootstrap modal padrão)
- ✅ Tablet (se ajusta automaticamente)
- ✅ Mobile (modal ocupa tela inteira)

---

## ✅ **RESUMO - O QUE O USUÁRIO VÊ**

1. **Botão verde** "Lançar no Odoo" na tela de visualização do frete
2. **Modal** explicativo ao clicar (16 etapas, data de vencimento)
3. **Barra de progresso animada** durante execução
4. **Alert de sucesso** com IDs do Odoo (DFe, PO, Invoice)
5. **Botão muda para "Lançado"** (desabilitado) após sucesso
6. **Mensagens de erro claras** se algo falhar
7. **Auditoria completa** gravada no banco (consultável)

---

**FIM DO GUIA VISUAL**

Todas as interfaces estão prontas e funcionais! 🎉
