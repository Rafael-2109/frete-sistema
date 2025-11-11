# Correção do Bug de tipo_envio em Separações

**Data**: 2025-01-11
**Autor**: Sistema de Fretes
**Tipo**: Bug Fix Crítico

---

## 🔴 PROBLEMA IDENTIFICADO

### Sintoma:
Sincronização do Odoo estava adicionando **TODOS os produtos do pedido** em Separações que deveriam ter apenas **ALGUNS produtos selecionados**.

**Exemplo real:**
- Pedido VCD2564291: Tinha 6 produtos na Separação
- Após sincronização: 40 produtos (adicionou 34 indevidos)

### Causa Raiz:
Separações estavam sendo criadas com `tipo_envio='total'` **INCORRETAMENTE** quando deveriam ser `'parcial'`.

---

## 📊 DEFINIÇÃO CORRETA DE tipo_envio

### tipo_envio='total'
Uma Separação só deve ter `tipo_envio='total'` quando:
1. Contém **TODOS os produtos** do pedido
2. Com as **quantidades COMPLETAS** de cada produto

**Exemplo:**
```
Pedido VCD123 tem:
- Produto A: 100 unidades
- Produto B: 200 unidades
- Produto C: 50 unidades

Separação TOTAL deve ter:
- Produto A: 100 unidades ✅
- Produto B: 200 unidades ✅
- Produto C: 50 unidades ✅
```

### tipo_envio='parcial'
Qualquer Separação que:
1. Não contém TODOS os produtos, OU
2. Contém quantidades menores que o total

**Exemplo:**
```
Separação PARCIAL pode ter:
- Produto A: 50 unidades (parcial)
- Produto B: 200 unidades (total deste produto)
- [Produto C não está nesta separação]
```

---

## 🔧 CORREÇÕES APLICADAS

### 1. [carteira_simples_api.py](app/carteira/routes/carteira_simples_api.py)

**Antes (INCORRETO):**
```python
tipo_envio='total',  # Pode ser ajustado conforme lógica
```

**Depois (CORRETO):**
```python
# Determinar tipo_envio corretamente
from app.carteira.utils.separacao_utils import determinar_tipo_envio

produtos_carteira = {}
for item in CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, ativo=True).all():
    produtos_carteira[item.cod_produto] = item

tipo_envio_correto = determinar_tipo_envio(num_pedido, produtos, produtos_carteira)

# Usar na criação:
tipo_envio=tipo_envio_correto,  # 🔧 CORRIGIDO
```

### 2. [importar_agendamentos.py](app/carteira/routes/programacao_em_lote/importar_agendamentos.py)

**Antes (INCORRETO):**
```python
tipo_envio='total',
```

**Depois (CORRETO):**
```python
# Determinar tipo_envio corretamente
tipo_envio_correto = determinar_tipo_envio(num_pedido, produtos_lote, produtos_carteira)

# Usar na criação:
tipo_envio=tipo_envio_correto,  # 🔧 CORRIGIDO
```

### 3. [separacao_api.py](app/carteira/routes/separacao_api.py)

**Status:** ✅ JÁ ESTAVA CORRETO
- Este arquivo já usa `tipo_envio='total'` corretamente porque realmente separa TODOS os produtos do pedido.

---

## 🛠️ FUNÇÃO DE VALIDAÇÃO

A função `determinar_tipo_envio()` em [separacao_utils.py](app/carteira/utils/separacao_utils.py) já existia e faz a verificação correta:

```python
def determinar_tipo_envio(num_pedido, produtos_lote, produtos_carteira):
    """
    Determina se o envio é 'total' ou 'parcial' baseado nas quantidades

    Retorna:
    - 'total': Se está separando TODOS os produtos com quantidades COMPLETAS
    - 'parcial': Caso contrário
    """
```

---

## 🔄 CÓDIGO DE SINCRONIZAÇÃO

O código em [ajuste_sincronizacao_service.py](app/odoo/services/ajuste_sincronizacao_service.py) está **CORRETO**.

Ele adiciona produtos novos quando `tipo_envio='total'` porque essa é a lógica correta:
- Se a Separação tem `tipo_envio='total'`, ela DEVE ser espelho completo do pedido
- Se o Odoo adicionar um produto novo, a Separação DEVE incluí-lo

**O problema não era o código de sincronização, era a criação incorreta de Separações com tipo_envio='total'!**

---

## 📝 SCRIPT DE CORREÇÃO

Criado: [scripts/corrigir_tipo_envio_separacoes.py](scripts/corrigir_tipo_envio_separacoes.py)

### Como usar:

1. **Simular (DRY-RUN):**
```bash
python scripts/corrigir_tipo_envio_separacoes.py
```

2. **Executar correções:**
```bash
python scripts/corrigir_tipo_envio_separacoes.py --execute
```

### O que o script faz:

1. Busca todas as Separações com `tipo_envio='total'` e `sincronizado_nf=False`
2. Para cada lote:
   - Compara produtos da Separação vs produtos do pedido
   - Verifica se tem TODOS os produtos
   - Verifica se as quantidades são COMPLETAS
3. Se não for realmente total, corrige para `'parcial'`

---

## ⚠️ IMPACTO

### Separações afetadas:
- Todas criadas por `carteira_simples_api.py/gerar_separacao()` com produtos parciais
- Todas criadas por importação de agendamentos com produtos parciais

### Não afetadas:
- Separações criadas por `separacao_api.py/gerar_separacao_completa_pedido` (já estavam corretas)
- Separações já sincronizadas (`sincronizado_nf=True`)
- Separações com `tipo_envio='parcial'` (já estavam corretas)

---

## ✅ CHECKLIST DE VALIDAÇÃO

Antes de considerar a correção completa, validar:

- [x] Código corrigido em `carteira_simples_api.py`
- [x] Código corrigido em `importar_agendamentos.py`
- [x] Script de correção criado
- [ ] Script executado em ambiente de desenvolvimento (DRY-RUN)
- [ ] Script executado em produção (DRY-RUN)
- [ ] Validação dos resultados
- [ ] Script executado em produção (--execute)
- [ ] Validação final pós-correção

---

## 🔍 COMO VERIFICAR SE O BUG FOI CORRIGIDO

### Query para encontrar Separações incorretas:

```sql
-- Buscar lotes que têm tipo_envio='total' mas não contêm todos os produtos
WITH lotes_total AS (
    SELECT DISTINCT separacao_lote_id, num_pedido
    FROM separacao
    WHERE tipo_envio = 'total'
      AND sincronizado_nf = FALSE
),
produtos_sep AS (
    SELECT
        s.separacao_lote_id,
        s.num_pedido,
        COUNT(DISTINCT s.cod_produto) as qtd_produtos_sep
    FROM separacao s
    INNER JOIN lotes_total lt ON s.separacao_lote_id = lt.separacao_lote_id
    WHERE s.sincronizado_nf = FALSE
    GROUP BY s.separacao_lote_id, s.num_pedido
),
produtos_ped AS (
    SELECT
        lt.separacao_lote_id,
        cp.num_pedido,
        COUNT(DISTINCT cp.cod_produto) as qtd_produtos_ped
    FROM carteira_principal cp
    INNER JOIN lotes_total lt ON cp.num_pedido = lt.num_pedido
    WHERE cp.ativo = TRUE
    GROUP BY lt.separacao_lote_id, cp.num_pedido
)
SELECT
    ps.separacao_lote_id,
    ps.num_pedido,
    ps.qtd_produtos_sep,
    pp.qtd_produtos_ped,
    (pp.qtd_produtos_ped - ps.qtd_produtos_sep) as produtos_faltando
FROM produtos_sep ps
INNER JOIN produtos_ped pp ON ps.separacao_lote_id = pp.separacao_lote_id
WHERE ps.qtd_produtos_sep < pp.qtd_produtos_ped
ORDER BY produtos_faltando DESC;
```

**Resultado esperado após correção:** 0 linhas

---

## 📚 APRENDIZADOS

1. **tipo_envio é atributo do LOTE**, não do item individual
2. Um pedido pode ter múltiplos lotes (parcial + complemento)
3. A validação de `tipo_envio` deve ser feita na **CRIAÇÃO** da Separação, não na sincronização
4. Sempre usar `determinar_tipo_envio()` ao criar Separações

---

## 🔗 ARQUIVOS MODIFICADOS

1. `app/carteira/routes/carteira_simples_api.py` - Corrigido
2. `app/carteira/routes/programacao_em_lote/importar_agendamentos.py` - Corrigido
3. `scripts/corrigir_tipo_envio_separacoes.py` - Criado
4. `CORRECAO_TIPO_ENVIO.md` - Este documento

---

## 📞 CONTATO

Em caso de dúvidas sobre esta correção:
- Consultar: [CLAUDE.md](CLAUDE.md) e [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)
- Verificar logs do sistema durante sincronização
- Executar query de validação acima
