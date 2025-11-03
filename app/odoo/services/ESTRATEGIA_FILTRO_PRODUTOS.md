# 🎯 Estratégia de Filtro de Produtos - Compras e Estoque

**Data**: 31/10/2025
**Objetivo**: Importar APENAS produtos relacionados à produção (não importar todos os produtos do Odoo)

---

## 🔍 DESCOBERTAS DO TESTE

### 1. Campos Disponíveis em product.product (Odoo):

```python
{
  "id": 27692,
  "name": "COGUMELO FATIADO - IND",
  "default_code": "101001001",  # ✅ CÓDIGO DO PRODUTO
  "type": "product",             # product, consu, service
  "detailed_type": "product",
  "categ_id": [100, "TODOS / MATERIA PRIMA / MP IMP / COGUMELO"],
  "purchase_ok": True,           # ✅ Pode ser comprado
  "sale_ok": True                # ✅ Pode ser vendido
}
```

### 2. Categorias Encontradas no Odoo:

- ✅ `MATERIA PRIMA` - Produtos para produção
- ✅ `PRODUTO ACABADO` - Produtos finalizados
- ❌ `ATIVO FIXO` - Não relacionado à produção
- ❌ `DESPESAS` - Não relacionado à produção
- ❌ `COBRANÇA TRANSPORTADORA` - Não relacionado à produção

### 3. Situação Atual no Sistema Local:

```
⚠️  Total de produtos com produto_comprado=True: 0
```

**CRÍTICO**: Não há produtos cadastrados localmente ainda com `produto_comprado=True`.
Precisamos POPULAR o CadastroPalletizacao antes de importar requisições/pedidos.

---

## 🎯 4 ESTRATÉGIAS POSSÍVEIS

### ESTRATÉGIA 1: Filtro por purchase_ok=True (no Odoo)

#### Como Funciona:
```python
# Na importação do Odoo:
produtos = conn.search_read(
    'purchase.request.line',
    [
        ['request_id.state', 'in', ['approved', 'done']],
        ['product_id.purchase_ok', '=', True]  # ← FILTRO
    ]
)
```

#### ✅ VANTAGENS:
- Menos dados trafegados do Odoo
- Filtro executado no banco do Odoo (mais rápido)

#### ❌ DESVANTAGENS:
- **Inclui TODOS os produtos compráveis** (ativos fixos, despesas, etc.)
- Sem controle fino sobre o que importar
- Pode importar milhares de produtos desnecessários

#### 📊 AVALIAÇÃO: **NÃO RECOMENDADO** - muito genérico

---

### ESTRATÉGIA 2: Filtro por Categoria (no Odoo)

#### Como Funciona:
```python
# Identificar categorias de produção:
CATEGORIAS_PRODUCAO = [100, 114]  # MATERIA PRIMA, PRODUTO ACABADO

# Na importação:
produtos = conn.search_read(
    'purchase.request.line',
    [
        ['request_id.state', 'in', ['approved', 'done']],
        ['product_id.categ_id', 'in', CATEGORIAS_PRODUCAO]  # ← FILTRO
    ]
)
```

#### ✅ VANTAGENS:
- Filtro semântico (por tipo de produto)
- Menos dados trafegados do Odoo
- Excluir ativos fixos, despesas, etc.

#### ❌ DESVANTAGENS:
- **Precisa manter lista de categorias manualmente**
- Se criar nova categoria no Odoo, precisa atualizar código
- Difícil manutenção
- Categoria pode mudar no Odoo sem aviso

#### 📊 AVALIAÇÃO: **POSSÍVEL MAS FRÁGIL** - manutenção complexa

---

### ESTRATÉGIA 3: Importar Tudo + Filtro Local (RECOMENDADO)

#### Como Funciona:
```python
# PASSO 1: Importar requisições SEM filtro de produto
requisicoes_odoo = conn.search_read(
    'purchase.request',
    [['state', 'in', ['approved', 'done']]]
)

# PASSO 2: Para cada linha, validar localmente
for linha_odoo in requisicao['line_ids']:
    # Extrair default_code
    default_code = extrair_codigo_produto(linha_odoo['product_id'][1])

    # PASSO 3: Verificar se existe localmente com produto_comprado=True
    produto_local = CadastroPalletizacao.query.filter_by(
        cod_produto=default_code,
        produto_comprado=True,
        ativo=True
    ).first()

    # PASSO 4: Decidir se importa
    if not produto_local:
        logger.info(f"Produto {default_code} NÃO é comprado - IGNORADO")
        continue  # ← PULA este produto

    # PASSO 5: Importar normalmente
    importar_linha_requisicao(linha_odoo, produto_local)
```

#### ✅ VANTAGENS:
- **Controle TOTAL no cadastro local** ← PRINCIPAL VANTAGEM
- Flexibilidade para mudar critérios sem tocar no Odoo
- Cadastro local é fonte única da verdade
- Fácil auditoria (vê quais produtos foram ignorados nos logs)
- Pode adicionar/remover produtos do controle a qualquer momento

#### ❌ DESVANTAGENS:
- Mais dados trafegados do Odoo (mas queries já são limitadas)
- Validação em tempo de importação (pequeno overhead)
- **Precisa popular CadastroPalletizacao ANTES** de importar

#### 📊 AVALIAÇÃO: **✅ RECOMENDADO** - máximo controle e flexibilidade

---

### ESTRATÉGIA 4: Híbrido (Filtro Odoo + Validação Local)

#### Como Funciona:
```python
# PASSO 1: Filtro AMPLO no Odoo (purchase_ok=True)
produtos_odoo = conn.search_read(
    'purchase.request.line',
    [
        ['request_id.state', 'in', ['approved', 'done']],
        ['product_id.purchase_ok', '=', True]  # ← Filtro no Odoo
    ]
)

# PASSO 2: Filtro FINO no sistema local
for linha_odoo in produtos_odoo:
    default_code = extrair_codigo_produto(linha_odoo['product_id'][1])

    # Validação local (mesmo da Estratégia 3)
    produto_local = CadastroPalletizacao.query.filter_by(
        cod_produto=default_code,
        produto_comprado=True
    ).first()

    if not produto_local:
        continue

    importar_linha_requisicao(linha_odoo, produto_local)
```

#### ✅ VANTAGENS:
- Reduz dados trafegados (purchase_ok=True já elimina serviços, etc.)
- Mantém controle local

#### ❌ DESVANTAGENS:
- Lógica mais complexa (dois filtros)
- Ganho marginal de performance
- purchase_ok=True ainda traz muita coisa desnecessária

#### 📊 AVALIAÇÃO: **POSSÍVEL MAS COMPLEXO** - ganho marginal

---

## ✅ ESTRATÉGIA RECOMENDADA: #3 (Filtro Local)

### Justificativa:

1. **Controle Total**: CadastroPalletizacao é fonte única da verdade
2. **Flexibilidade**: Adicionar/remover produtos do controle é trivial
3. **Auditoria**: Logs claros de produtos ignorados
4. **Manutenção**: Não precisa sincronizar com mudanças no Odoo
5. **Performance**: Queries Odoo já são limitadas (limit, filtros de state)

### Desvantagens Aceitáveis:

- **Overhead de validação**: Desprezível (query rápida em índice local)
- **Dados "extras" trafegados**: Aceitável (requisições já vêm limitadas)

---

## 🚀 IMPLEMENTAÇÃO DA ESTRATÉGIA RECOMENDADA

### PASSO 1: Popular CadastroPalletizacao

**ANTES de importar qualquer coisa do Odoo**, precisa:

```python
# Script para popular produtos comprados:
from app.producao.models import CadastroPalletizacao
from app.odoo.utils.connection import get_odoo_connection

def popular_produtos_comprados():
    """
    Popula CadastroPalletizacao com produtos comprados do Odoo
    """
    conn = get_odoo_connection()

    # Buscar produtos de matéria-prima do Odoo
    produtos_odoo = conn.search_read(
        'product.product',
        [
            ['categ_id', 'in', [100]],  # MATERIA PRIMA
            ['purchase_ok', '=', True],
            ['active', '=', True]
        ],
        fields=['id', 'default_code', 'name']
    )

    for prod_odoo in produtos_odoo:
        default_code = prod_odoo.get('default_code')

        if not default_code:
            continue

        # Criar ou atualizar CadastroPalletizacao
        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=default_code
        ).first()

        if not produto:
            produto = CadastroPalletizacao(
                cod_produto=default_code,
                nome_produto=prod_odoo['name'],
                produto_comprado=True,  # ← MARCA COMO COMPRADO
                palletizacao=1.0,       # Valores padrão
                peso_bruto=1.0
            )
            db.session.add(produto)

    db.session.commit()
```

### PASSO 2: Função de Validação

```python
def deve_importar_produto(default_code: str) -> bool:
    """
    Verifica se produto deve ser importado

    Args:
        default_code: Código do produto no Odoo

    Returns:
        True se deve importar, False caso contrário
    """
    from app.producao.models import CadastroPalletizacao

    if not default_code:
        return False

    produto = CadastroPalletizacao.query.filter_by(
        cod_produto=default_code,
        produto_comprado=True,
        ativo=True
    ).first()

    return produto is not None
```

### PASSO 3: Uso na Importação

```python
def importar_requisicao_odoo(requisicao_odoo):
    """Importa requisição do Odoo com filtro local"""

    # Buscar linhas
    linhas_odoo = conn.read(
        'purchase.request.line',
        requisicao_odoo['line_ids'],
        fields=['id', 'product_id', 'product_qty', ...]
    )

    linhas_importadas = 0
    linhas_ignoradas = 0

    for linha_odoo in linhas_odoo:
        # Extrair código do produto
        product_name = linha_odoo['product_id'][1]  # "[109000055] OLEO DE SOJA"
        default_code = extrair_codigo_produto(product_name)

        # FILTRO LOCAL
        if not deve_importar_produto(default_code):
            logger.info(f"Produto {default_code} não é comprado - IGNORADO")
            linhas_ignoradas += 1
            continue

        # Importar linha
        criar_requisicao_compras(linha_odoo, default_code)
        linhas_importadas += 1

    logger.info(f"Requisição {requisicao_odoo['name']}: "
                f"{linhas_importadas} importadas, {linhas_ignoradas} ignoradas")
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### Fase Preparação:
- [ ] Identificar categorias de produtos de produção no Odoo
- [ ] Criar script para popular CadastroPalletizacao
- [ ] Executar script e validar produtos cadastrados
- [ ] Conferir campo `produto_comprado=True` está correto

### Fase Importação:
- [ ] Implementar `extrair_codigo_produto()` (regex ou usar default_code)
- [ ] Implementar `deve_importar_produto()`
- [ ] Aplicar validação em `importar_requisicao_odoo()`
- [ ] Aplicar validação em `importar_pedido_compras_odoo()`
- [ ] Aplicar validação em `importar_recebimento_odoo()`
- [ ] Adicionar logging para produtos ignorados

### Fase Testes:
- [ ] Testar importação com produto comprado (deve importar)
- [ ] Testar importação com produto NÃO comprado (deve ignorar)
- [ ] Validar logs de produtos ignorados
- [ ] Verificar contadores de linhas importadas vs ignoradas

---

## 🔧 CÓDIGO DO PRODUTO: default_code vs Regex

### Você perguntou sobre 2 formas de obter o código:

#### FORMA 1: Usar default_code do Odoo (RECOMENDADO)

```python
# Buscar produto com campos completos:
produto_odoo = conn.read(
    'product.product',
    [linha_odoo['product_id'][0]],
    fields=['id', 'default_code', 'name']
)[0]

default_code = produto_odoo['default_code']  # "109000055"
```

**✅ VANTAGENS**:
- Mais confiável (campo oficial do Odoo)
- Não depende de formato de nome
- Robusto a mudanças

**❌ DESVANTAGENS**:
- Requer query adicional ao Odoo
- Mais lento (1 query por produto)

#### FORMA 2: Extrair do Nome com Regex

```python
import re

def extrair_codigo_produto(nome_odoo: str) -> str:
    """Extrai [109000055] de '[109000055] OLEO DE SOJA'"""
    match = re.search(r'\[(\d+)\]', nome_odoo)
    return match.group(1) if match else None

# Uso:
product_name = linha_odoo['product_id'][1]  # "[109000055] OLEO DE SOJA"
default_code = extrair_codigo_produto(product_name)  # "109000055"
```

**✅ VANTAGENS**:
- Rápido (não precisa query adicional)
- Já vem nos dados de linha

**❌ DESVANTAGENS**:
- Depende de formato `[CÓDIGO]` no nome
- Se mudar formato, quebra

### 🎯 RECOMENDAÇÃO:

**Use REGEX inicialmente** (Forma 2) porque:
1. Formato `[CÓDIGO]` é padrão no seu Odoo
2. Evita queries adicionais (melhor performance)
3. Se quebrar no futuro, fácil ajustar para Forma 1

---

## 📊 EXEMPLO COMPLETO DE FLUXO

```python
# 1. Buscar requisições do Odoo (SEM filtro de produto)
requisicoes = conn.search_read(
    'purchase.request',
    [['state', 'in', ['approved', 'done']]],
    fields=['id', 'name', 'line_ids', ...]
)

for req in requisicoes:
    # 2. Buscar linhas
    linhas = conn.read(
        'purchase.request.line',
        req['line_ids'],
        fields=['product_id', 'product_qty', 'date_required', ...]
    )

    for linha in linhas:
        # 3. Extrair código (REGEX)
        product_name = linha['product_id'][1]  # "[210639522] ROTULO..."
        cod_produto = extrair_codigo_produto(product_name)

        # 4. VALIDAR LOCALMENTE
        if not deve_importar_produto(cod_produto):
            logger.info(f"⏭️  Produto {cod_produto} ignorado (não é comprado)")
            continue

        # 5. IMPORTAR
        requisicao_compras = RequisicaoCompras(
            num_requisicao=req['name'],
            cod_produto=cod_produto,
            qtd_produto_requisicao=linha['product_qty'],
            data_necessidade=linha['date_required'],
            ...
        )
        db.session.add(requisicao_compras)

db.session.commit()
logger.info("✅ Importação concluída com filtro local")
```

---

## 🎯 RESUMO EXECUTIVO

| Aspecto | Decisão |
|---------|---------|
| **Estratégia Filtro** | Estratégia 3 - Filtro Local |
| **Fonte da Verdade** | CadastroPalletizacao.produto_comprado=True |
| **Extração Código** | Regex (Forma 2) inicialmente |
| **Filtro no Odoo** | Nenhum - importar todas as linhas |
| **Validação** | Tempo de importação (local) |
| **Pré-requisito** | Popular CadastroPalletizacao ANTES |

---

**Status**: ESTRATÉGIA DEFINIDA - PRONTA PARA IMPLEMENTAÇÃO
**Autor**: Sistema de Fretes
**Próximo Passo**: Popular CadastroPalletizacao com produtos comprados
