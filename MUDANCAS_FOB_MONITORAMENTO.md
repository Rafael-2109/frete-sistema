# 📋 MUDANÇAS: Monitoramento de NFs FOB

**Data:** 13/10/2025
**Objetivo:** Incluir NFs com incoterm FOB no monitoramento de entregas, mesmo que o frete seja por conta do cliente.

---

## 🎯 RESUMO DA MUDANÇA

### Comportamento ANTERIOR (❌):
- NFs FOB **NÃO** eram registradas em `EntregaMonitorada`
- Filtro em `sincronizar_entregas.py` impedia criação
- Não havia monitoramento de embarques FOB

### Comportamento NOVO (✅):
- NFs FOB **SÃO** registradas em `EntregaMonitorada`
- `data_hora_entrega_realizada` = `Embarque.data_embarque` (preenchimento automático)
- `data_entrega_prevista` = `Embarque.data_prevista_embarque`
- `entregue` = `True` (quando tem `data_embarque`)
- `status_finalizacao` = `'FOB - Embarcado no CD'`

---

## 📝 ARQUIVOS MODIFICADOS

### 1. [app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py)

#### **Modificação 1: Remoção do filtro FOB (linhas 80-89)**
```python
# ❌ CÓDIGO REMOVIDO:
# 🚫 FILTRO 1: NFs FOB (frete por conta do cliente)
if getattr(current_app.config, 'FILTRAR_FOB_MONITORAMENTO', True):
    incoterm = getattr(fat, 'incoterm', '') or ''
    if 'FOB' in incoterm.upper():
        # Se a NF é FOB, remove do monitoramento se existir
        entrega_existente = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
        if entrega_existente:
            db.session.delete(entrega_existente)
            db.session.commit()
        return
```

#### **Modificação 2: Adição de lógica especial para FOB (após linha 219)**
```python
# ✅ CÓDIGO ADICIONADO:
# 🆕 TRATAMENTO ESPECIAL PARA FOB
# FOB = Frete por conta do cliente, entrega considerada realizada no embarque
incoterm = getattr(fat, 'incoterm', '') or ''
if 'FOB' in incoterm.upper():
    if embarque:
        # Para FOB, usar data_prevista_embarque como data_entrega_prevista
        if embarque.data_prevista_embarque:
            entrega.data_entrega_prevista = embarque.data_prevista_embarque

        # Para FOB, data_hora_entrega_realizada = data_embarque (entrega ocorre no CD)
        if embarque.data_embarque:
            entrega.data_hora_entrega_realizada = datetime.combine(
                embarque.data_embarque,
                datetime.min.time()
            )
            entrega.entregue = True
            entrega.status_finalizacao = 'FOB - Embarcado no CD'
            print(f"[SYNC] 🚚 FOB: NF {numero_nf} marcada como entregue em {embarque.data_embarque}")
```

**Linhas modificadas:**
- **Removido:** Linhas 80-89 (filtro FOB)
- **Adicionado:** Linhas 221-238 (lógica especial FOB)

---

## 🔧 SCRIPTS CRIADOS

### 1. Script Python - Sincronização Retroativa
**Arquivo:** [scripts/sincronizar_nfs_fob_retroativo.py](scripts/sincronizar_nfs_fob_retroativo.py)

**Como rodar localmente:**
```bash
python scripts/sincronizar_nfs_fob_retroativo.py
```

**O que faz:**
- Busca todas as NFs FOB ativas sem `EntregaMonitorada`
- Usa a função `sincronizar_entrega_por_nf()` para cada NF
- Gera relatório detalhado de sucesso/erros
- Solicita confirmação antes de executar

### 2. Script SQL - Para Shell do Render
**Arquivo:** [scripts/sincronizar_nfs_fob_retroativo.sql](scripts/sincronizar_nfs_fob_retroativo.sql)

**Como rodar no Shell do Render:**
1. Acesse o Shell do banco de dados no Render
2. Execute cada etapa do script sequencialmente:
   - **Etapa 1:** Listar NFs FOB sem monitoramento (verificação)
   - **Etapa 2:** Inserir registros em `entregas_monitoradas`
   - **Etapa 3:** Contar quantas foram criadas
   - **Etapa 4:** Listar EntregaMonitorada criadas
   - **Etapa 5:** Estatísticas finais

**⚠️ ATENÇÃO:** Execute a Etapa 1 primeiro para verificar quantas NFs serão afetadas!

---

## 🔍 REGRAS DE NEGÓCIO - FOB

### O que é FOB?
**FOB (Free On Board)** = Frete por conta do **cliente**. A responsabilidade da transportadora é do comprador.

### Comportamento no Sistema:

| Campo | Comportamento FOB |
|-------|-------------------|
| `EntregaMonitorada` | ✅ **Criada normalmente** |
| `data_entrega_prevista` | `Embarque.data_prevista_embarque` |
| `data_hora_entrega_realizada` | `Embarque.data_embarque` (automático) |
| `entregue` | `True` (se tem `data_embarque`) |
| `status_finalizacao` | `'FOB - Embarcado no CD'` |
| `transportadora` | Do embarque (se houver) |

### Por que marcar como "entregue" automaticamente?
- Para FOB, a **entrega ocorre no CD** quando embarcado
- O cliente é responsável pelo transporte a partir deste ponto
- Não faz sentido monitorar entrega ao cliente final

---

## 📊 IMPACTO NO BANCO DE DADOS

### Tabelas Afetadas:
1. **`entregas_monitoradas`** - Novos registros para NFs FOB
2. **`relatorio_faturamento_importado`** - Nenhuma mudança (continua com `ativo=True` para FOB)
3. **`embarques`** - Nenhuma mudança
4. **`embarque_item`** - Nenhuma mudança

### Campos de `entregas_monitoradas` preenchidos para FOB:

```sql
SELECT
    numero_nf,                      -- Da NF
    cliente,                        -- Da NF
    cnpj_cliente,                   -- Da NF
    data_faturamento,               -- Da NF
    data_embarque,                  -- De Embarque
    data_entrega_prevista,          -- De Embarque.data_prevista_embarque
    data_hora_entrega_realizada,    -- De Embarque.data_embarque (automático)
    entregue,                       -- TRUE (automático se tem data_embarque)
    status_finalizacao,             -- 'FOB - Embarcado no CD' (automático)
    transportadora,                 -- De Embarque.transportadora
    separacao_lote_id               -- De EmbarqueItem
FROM entregas_monitoradas;
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

### Após aplicar as mudanças:

- [ ] **1. Código modificado**
  - [ ] [app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py) - Filtro FOB removido
  - [ ] [app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py) - Lógica FOB adicionada

- [ ] **2. Scripts executados**
  - [ ] Rodar script Python localmente OU
  - [ ] Rodar script SQL no Shell do Render

- [ ] **3. Validação**
  - [ ] Verificar quantas EntregaMonitorada FOB foram criadas
  - [ ] Conferir se `data_hora_entrega_realizada` está preenchida
  - [ ] Conferir se `entregue = TRUE` para FOB com embarque
  - [ ] Conferir se `status_finalizacao = 'FOB - Embarcado no CD'`

- [ ] **4. Teste com NF FOB nova**
  - [ ] Importar uma NF FOB nova via Odoo
  - [ ] Verificar se EntregaMonitorada é criada automaticamente
  - [ ] Verificar se campos FOB estão corretos

---

## 🚨 POSSÍVEIS PROBLEMAS E SOLUÇÕES

### Problema 1: NFs FOB antigas não têm `data_embarque`
**Solução:** O script verifica se existe `Embarque` antes de preencher. Se não houver embarque, campos ficam NULL.

### Problema 2: NF FOB sem `EmbarqueItem`
**Solução:** Script SQL usa `INNER JOIN`, então só cria EntregaMonitorada se houver EmbarqueItem. Script Python usa `sincronizar_entrega_por_nf()` que trata isso.

### Problema 3: Duplicação de EntregaMonitorada
**Solução:** Ambos os scripts verificam `NOT EXISTS` antes de criar. Não há risco de duplicação.

---

## 📞 CONTATO

**Responsável:** Rafael Nascimento
**Data:** 13/10/2025
**Issue/Ticket:** Monitoramento FOB - Incluir embarques FOB no rastreamento

---

## 🔗 REFERÊNCIAS

- **Modelo EntregaMonitorada:** [app/monitoramento/models.py](app/monitoramento/models.py)
- **Modelo RelatorioFaturamentoImportado:** [app/faturamento/models.py](app/faturamento/models.py)
- **Modelo Embarque:** [app/embarques/models.py](app/embarques/models.py)
- **Função de Sincronização:** [app/utils/sincronizar_entregas.py](app/utils/sincronizar_entregas.py)
