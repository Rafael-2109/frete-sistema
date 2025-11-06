# Implementação: Filtro de Tipos de Pedido de Compra

**Data:** 05/11/2025
**Objetivo:** Importar apenas pedidos relevantes para materiais armazenáveis
**Status:** ✅ IMPLEMENTADO

---

## 🎯 TIPOS IMPLEMENTADOS (8 tipos)

```python
TIPOS_PEDIDO_RELEVANTES = {
    'compra',                   # Compra normal - PRINCIPAL
    'importacao',               # Importação
    'comp-importacao',          # Complementar de importação
    'devolucao',                # Devolução de cliente
    'devolucao_compra',         # Devolução de venda
    'industrializacao',         # Retorno de industrialização
    'serv-industrializacao',    # ✅ Serviço de industrialização (produção terceirizada)
    'ent-bonificacao',          # Bonificação (brinde)
}
```

### ⚠️ IMPORTANTE - Serviço de Industrialização

`serv-industrializacao` é **INCLUÍDO** pois:
- Funciona como produção terceirizada
- Envia matéria-prima para terceiro processar
- Consome estrutura (BOM)
- Retorna produto acabado
- Sistema deve projetar consumo e entrada

---

## 📊 EXCLUSÕES

### ❌ Excluídos (30 tipos):
- Transferências entre filiais
- Remessas (não aumentam estoque próprio)
- Operações temporárias (comodato, demonstração, etc.)
- Serviços (exceto industrialização)
- Ativos imobilizados

---

## 💻 IMPLEMENTAÇÃO

### 1. Modelo Atualizado

**Arquivo:** [app/manufatura/models.py:239-242](app/manufatura/models.py#L239)

```python
class PedidoCompras(db.Model):
    # ... campos existentes ...

    # ✅ NOVO: Tipo de pedido (l10n_br_tipo_pedido do Odoo Brasil)
    tipo_pedido = db.Column(db.String(50), nullable=True, index=True)
```

---

### 2. Serviço de Importação

**Arquivo:** [app/odoo/services/pedido_compras_service.py](app/odoo/services/pedido_compras_service.py)

#### 2.1 Constante de Tipos Relevantes (linha 50-59)

```python
class PedidoComprasServiceOtimizado:
    # ✅ TIPOS DE PEDIDO RELEVANTES
    TIPOS_RELEVANTES = {
        'compra', 'importacao', 'comp-importacao',
        'devolucao', 'devolucao_compra',
        'industrializacao', 'serv-industrializacao',
        'ent-bonificacao'
    }
```

#### 2.2 Buscar Campo do Odoo (linha 192)

```python
campos_pedido = [
    # ... campos existentes ...
    'l10n_br_tipo_pedido'  # ✅ ADICIONADO
]
```

#### 2.3 Filtrar no Processamento (linha 396-404)

```python
def _processar_linha_otimizada(self, pedido_odoo, linha_odoo, ...):
    # ✅ PASSO 0: Verificar tipo de pedido
    tipo_pedido = pedido_odoo.get('l10n_br_tipo_pedido')

    if tipo_pedido and tipo_pedido not in self.TIPOS_RELEVANTES:
        self.logger.info(
            f"   Pedido {pedido_odoo['name']} tipo '{tipo_pedido}' "
            f"não é relevante para estoque - IGNORADA"
        )
        return {'processado': False, 'nova': False, 'atualizada': False}

    # Continuar processamento...
```

#### 2.4 Salvar Tipo ao Criar (linha 526)

```python
def _criar_pedido(self, pedido_odoo, linha_odoo, produto_odoo):
    novo_pedido = PedidoCompras(
        # ... campos existentes ...
        tipo_pedido=pedido_odoo.get('l10n_br_tipo_pedido'),
        # ...
    )
```

#### 2.5 Atualizar Tipo ao Modificar (linha 571-575)

```python
def _atualizar_pedido(self, pedido_existente, pedido_odoo, ...):
    # ✅ Verificar mudança de tipo de pedido
    novo_tipo = pedido_odoo.get('l10n_br_tipo_pedido')
    if pedido_existente.tipo_pedido != novo_tipo:
        pedido_existente.tipo_pedido = novo_tipo
        alterado = True
```

---

### 3. Migração do Banco

**Scripts criados:**
- ✅ [scripts/adicionar_tipo_pedido_pedido_compras.py](scripts/adicionar_tipo_pedido_pedido_compras.py)
- ✅ [scripts/adicionar_tipo_pedido_pedido_compras.sql](scripts/adicionar_tipo_pedido_pedido_compras.sql)

**SQL executado:**
```sql
ALTER TABLE pedido_compras
ADD COLUMN tipo_pedido VARCHAR(50);

CREATE INDEX ix_pedido_compras_tipo_pedido
ON pedido_compras(tipo_pedido);
```

**Status:** ✅ Executado localmente com sucesso

---

## 🔍 COMPORTAMENTO

### Antes da Implementação:
```
Pedido X - tipo: 'transf-filial'  → ✅ Importado (incorreto)
Pedido Y - tipo: 'servico'         → ✅ Importado (incorreto)
Pedido Z - tipo: 'compra'          → ✅ Importado (correto)

Total importados: 3
```

### Depois da Implementação:
```
Pedido X - tipo: 'transf-filial'  → ❌ IGNORADO (correto)
Pedido Y - tipo: 'servico'         → ❌ IGNORADO (correto)
Pedido Z - tipo: 'compra'          → ✅ Importado (correto)

Total importados: 1
Log: "Pedido X tipo 'transf-filial' não é relevante para estoque - IGNORADA"
Log: "Pedido Y tipo 'servico' não é relevante para estoque - IGNORADA"
```

---

## 📊 ESTATÍSTICAS

```
Total de tipos possíveis: 38

✅ Relevantes (importados):  8 tipos  (21%)
❌ Excluídos (ignorados):   30 tipos  (79%)
```

---

## 🧪 TESTES

### Cenário de Teste:

**Pedidos no Odoo:**
1. C2510701 - tipo: `compra` - produto: SAL
2. C2510702 - tipo: `transf-filial` - produto: AÇÚCAR
3. C2510703 - tipo: `serv-industrializacao` - produto: FRASCO (semi-acabado → acabado)
4. C2510704 - tipo: `servico` - produto: CONSULTORIA

**Resultado Esperado:**
```
✅ C2510701 (compra) → Importado
❌ C2510702 (transf-filial) → Ignorado
✅ C2510703 (serv-industrializacao) → Importado
❌ C2510704 (servico) → Ignorado

Registros na tabela: 2
Linhas ignoradas: 2
```

---

## 📋 PRÓXIMOS PASSOS

### Para Produção (Render):

1. **Executar Migração SQL:**
   ```bash
   # No Shell do Render:
   # Copiar e executar: scripts/adicionar_tipo_pedido_pedido_compras.sql
   ```

2. **Deploy:**
   ```bash
   git add .
   git commit -m "feat: Adiciona filtro de tipos de pedido de compra

   - Inclui apenas materiais armazenáveis
   - Exclui transferências e remessas
   - Inclui serviço de industrialização (produção terceirizada)
   - Total: 8 tipos relevantes de 38 possíveis"
   git push
   ```

3. **Testar:**
   - Acessar `/manufatura/pedidos-compras/sincronizar-manual`
   - Sincronizar últimos 7 dias
   - Verificar logs: "tipo 'X' não é relevante para estoque - IGNORADA"
   - Confirmar que apenas tipos relevantes foram importados

---

## 🔗 ARQUIVOS MODIFICADOS

1. **app/manufatura/models.py**
   - Linha 239-242: Campo `tipo_pedido` adicionado

2. **app/odoo/services/pedido_compras_service.py**
   - Linha 50-59: Constante `TIPOS_RELEVANTES`
   - Linha 192: Buscar campo `l10n_br_tipo_pedido`
   - Linha 396-404: Filtro no processamento
   - Linha 526: Salvar tipo ao criar
   - Linha 571-575: Atualizar tipo ao modificar

3. **Scripts criados:**
   - `scripts/adicionar_tipo_pedido_pedido_compras.py`
   - `scripts/adicionar_tipo_pedido_pedido_compras.sql`

---

## 📚 DOCUMENTAÇÃO

- **Análise Completa:** [ANALISE_TIPOS_PEDIDO_COMPRA.md](ANALISE_TIPOS_PEDIDO_COMPRA.md)
- **Justificativa de tipos:** Documento anexo com análise dos 38 tipos

---

## ✅ VALIDAÇÃO

- [x] Modelo atualizado
- [x] Serviço implementado
- [x] Migração criada
- [x] Migração executada localmente
- [x] Filtro testado mentalmente
- [x] Documentação criada
- [ ] Executar migração em produção
- [ ] Deploy em produção
- [ ] Testar sincronização real

---

**Responsável:** Claude Code
**Aprovado por:** Rafael Nascimento
**Data:** 05/11/2025
