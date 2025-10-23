# ⚠️ FUNÇÕES PENDENTES DE ATUALIZAÇÃO

## 📋 OCORRÊNCIAS ENCONTRADAS EM routes.py

Estas funções ainda usam o padrão antigo `observacoes.contains('Fatura:')` e precisam ser atualizadas para usar `fatura_frete_id`.

---

### 🔴 **CRÍTICAS (Quebram funcionalidade)**

#### 1. **Linha 1035** - `remover_frete_fatura()`
```python
# ANTES:
despesas = DespesaExtra.query.filter(
    DespesaExtra.observacoes.contains(f'Fatura: {fatura.numero_fatura}')
).all()

# DEPOIS:
despesas = DespesaExtra.query.filter_by(
    fatura_frete_id=fatura.id
).all()
```

#### 2. **Linha 1313** - `editar_fatura()`
```python
# ANTES:
despesas_antigas = DespesaExtra.query.filter(
    DespesaExtra.observacoes.contains(f'Fatura: {numero_fatura_antigo}')
).all()

# DEPOIS:
despesas_antigas = DespesaExtra.query.filter_by(
    fatura_frete_id=fatura.id
).all()
```

#### 3. **Linha 1421 e 1425** - `conferir_fatura()`
```python
# ANTES (2 ocorrências):
despesas_fatura = DespesaExtra.query.filter(
    DespesaExtra.observacoes.contains(f'Fatura: {fatura.numero_fatura}')
).all()

# DEPOIS:
despesas_fatura = DespesaExtra.query.filter_by(
    fatura_frete_id=fatura.id
).all()
```

#### 4. **Linha 2598 e 2606** - `gerenciar_despesas_extras()`
```python
# ANTES - Despesas sem fatura:
despesas_sem_fatura = DespesaExtra.query.filter(
    ~DespesaExtra.observacoes.contains('Fatura:')
).all()

# DEPOIS:
despesas_sem_fatura = DespesaExtra.query.filter(
    DespesaExtra.fatura_frete_id.is_(None)
).all()

# ANTES - Despesas com fatura:
despesas_com_fatura = DespesaExtra.query.filter(
    DespesaExtra.observacoes.contains('Fatura:')
).all()

# DEPOIS:
despesas_com_fatura = DespesaExtra.query.filter(
    DespesaExtra.fatura_frete_id.isnot(None)
).all()
```

#### 5. **Linha 2666** - `vincular_despesa_fatura()`
```python
# ANTES:
despesa.observacoes = f"Fatura: {fatura.numero_fatura} | {observacoes_original}"

# DEPOIS:
despesa.fatura_frete_id = fatura.id
despesa.observacoes = observacoes_original  # Remove "Fatura:" do padrão
```

#### 6. **Linha 2695, 2712, 2722-2728** - `desvincular_despesa_fatura()`
```python
# ANTES - Verificação:
if not despesa.observacoes or 'Fatura:' not in despesa.observacoes:
    flash('Esta despesa não está vinculada a nenhuma fatura.', 'warning')

# DEPOIS:
if despesa.fatura_frete_id is None:
    flash('Esta despesa não está vinculada a nenhuma fatura.', 'warning')

# ANTES - Remover vínculo:
despesa.observacoes = re.sub(r'^Fatura:\s*[^|]+\s*\|\s*', '', despesa.observacoes)
# ... (várias linhas de regex)

# DEPOIS:
despesa.fatura_frete_id = None
# Observações permanecem intactas
```

#### 7. **Linha 3298** - Função não identificada (provavelmente em `atualizar_despesa()`)
```python
# ANTES:
despesa.observacoes = f"{obs_atual} | Fatura: {nova_fatura.numero_fatura}".strip(' |')

# DEPOIS:
despesa.fatura_frete_id = nova_fatura.id
despesa.observacoes = obs_atual.strip(' |')
```

---

### 🟡 **INFORMATIVAS (Não quebram, mas devem ser atualizadas)**

#### 8. **Linha 1039** - Comentário explicativo
```python
# ATUALIZAR O COMENTÁRIO:
# ANTES:
# que fica armazenado no campo observacoes no formato "Fatura: NUMERO_FATURA | outras_obs"

# DEPOIS:
# que fica vinculado através do campo fatura_frete_id (FK para faturas_frete.id)
```

#### 9. **Linha 1099-1101** - `visualizar_fatura()` - Extração de info
```python
# ANTES:
if despesa.observacoes and 'Fatura:' in despesa.observacoes:
    # Extrai número da fatura das observações
    fatura_info = despesa.observacoes.split('Fatura:')[1].split('|')[0].strip()

# DEPOIS:
if despesa.fatura_frete_id:
    # Busca a fatura pelo ID
    fatura_vinculada = FaturaFrete.query.get(despesa.fatura_frete_id)
    fatura_info = fatura_vinculada.numero_fatura if fatura_vinculada else 'N/A'
```

---

## 📊 RESUMO

- **Total de ocorrências:** 17
- **Funções afetadas:** ~8 funções
- **Críticas (quebram):** 7 funções
- **Informativas:** 2 ocorrências

---

## 🚀 ORDEM RECOMENDADA DE ATUALIZAÇÃO

### **Prioridade ALTA (fazer primeiro):**
1. ✅ `criar_despesa_extra_frete()` - Linha 1489 (JÁ FEITO)
2. ✅ `salvar_despesa_sem_fatura()` - Linha 1595 (JÁ FEITO)
3. ✅ `nova_despesa_extra()` - Linha 1741 (JÁ FEITO)
4. ⚠️ `vincular_despesa_fatura()` - Linha 2666 (CRÍTICO)
5. ⚠️ `desvincular_despesa_fatura()` - Linha 2695+ (CRÍTICO)

### **Prioridade MÉDIA (fazer depois):**
6. ⚠️ `gerenciar_despesas_extras()` - Linha 2598, 2606
7. ⚠️ `remover_frete_fatura()` - Linha 1035
8. ⚠️ `editar_fatura()` - Linha 1313
9. ⚠️ `conferir_fatura()` - Linha 1421, 1425

### **Prioridade BAIXA (última):**
10. ⚠️ Comentários e informativas - Linha 1039, 1099

---

## ⚠️ ATENÇÃO

**NÃO FAÇA COMMIT PARCIAL!**

Se você atualizar apenas algumas funções e fizer commit, o sistema ficará **quebrado em produção** porque:
- Algumas funções usarão FK (novo)
- Outras usarão observações (antigo)
- Dados migrados terão FK preenchida
- Funções antigas não encontrarão as despesas

**ORDEM CORRETA:**
1. ✅ Migrar dados no banco (script 03)
2. ✅ Atualizar TODAS as funções
3. ✅ Testar localmente
4. ✅ Commit + Push

---

**Quer que eu atualize as 7 funções críticas restantes agora?**
