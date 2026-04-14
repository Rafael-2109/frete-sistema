# Padroes Backend — Helpers Compartilhados

**Ultima atualizacao**: 2026-04-14

Guia de padroes backend Python do Sistema de Fretes. Centraliza helpers e
utilitarios que resolvem problemas recorrentes — **usar ANTES de reinventar**.

> Quando criar um helper novo em `app/utils/`, adicionar entrada aqui com
> o motivo (bug/gotcha que motivou), QUANDO usar e QUANDO nao precisar.

---

## Indice

1. [JSON Sanitization (`sanitize_for_json`)](#1-json-sanitization)

---

## 1. JSON Sanitization

**Arquivo**: `app/utils/json_helpers.py`
**Funcao**: `sanitize_for_json(obj, decimal_as_str=False)`

### Problema que resolve

Colunas SQLAlchemy `db.Column(db.JSON)` / `db.Column(JSONB)` delegam
serializacao ao `json.dumps()` do Python, que NAO sabe serializar:

- `Decimal`     (muito comum — vem de `Numeric`/`DECIMAL` SQL, `CalculadoraFrete`, parsers XML)
- `datetime` / `date` / `time`
- `UUID`
- `bytes` / `bytearray`
- `set` / `frozenset` / `tuple`
- `Enum`

O erro so aparece no `db.session.flush()` / `commit()`, DEPOIS do ORM
marcar o objeto como sujo:

```
TypeError: Object of type Decimal is not JSON serializable
sqlalchemy.exc.PendingRollbackError: This Session's transaction has been
rolled back due to a previous exception during flush.
```

A transacao inteira e abortada — qualquer outro objeto modificado na
mesma session e descartado.

**Bug real que motivou o helper** (2026-04-14): ao criar nova cotacao
CarVia em `CotacaoV2Service.calcular_cotacao()`, o dict `detalhes` vindo
de `CalculadoraFrete.calcular_frete_unificado()` chegava com 11 Decimais
quantizados ao campo `CarviaCotacao.detalhes_calculo` (`db.JSON`) e
explodia o flush.

### Como usar

```python
from app.utils.json_helpers import sanitize_for_json

# ANTES (quebra):
cotacao.detalhes_calculo = resultado_calculadora

# DEPOIS (seguro):
cotacao.detalhes_calculo = sanitize_for_json(resultado_calculadora)
```

O helper e **idempotente**: dict ja JSON-safe passa sem efeito colateral.
Custo: microssegundos em dicts pequenos.

### Quando USAR (obrigatorio)

SEMPRE que atribuir a campo `db.JSON` / `JSONB` um valor vindo de:

1. **Queries SQLAlchemy** com colunas `Numeric`/`DECIMAL` (retornam `Decimal`)
2. **`CalculadoraFrete.calcular_frete_unificado()`** e correlatos (11 chaves Decimal)
3. **Servicos de cotacao/pricing** que usam `Decimal` para precisao monetaria
4. **ORM objects** (tem campos timestamp, UUIDs, Decimals juntos)
5. **APIs Odoo** (retornam `datetime`, `UUID`, valores monetarios `Decimal`)
6. **Parsers XML / PDF** que usam `Decimal` (NFe, CTe, DACTe, DANFe)
7. **Qualquer dict cuja fonte voce nao controla 100%**

### Quando NAO precisa

- Dict construido manualmente SO com `str`, `int`, `float`, `bool`, `None`
- Payloads `request.get_json()` (ja vem deserializado em tipos JSON-safe)
- Reset/limpeza (`cotacao.detalhes_calculo = None`)
- JSONB usado apenas com defaults estaticos (listas literais, etc.)

**Em caso de duvida: APLICAR.** E idempotente.

### Parametro `decimal_as_str`

```python
# Default: Decimal -> float (mais natural em JSON e frontend)
sanitize_for_json({'v': Decimal('123.45')})
# => {'v': 123.45}

# Opcional: Decimal -> str (preserva precisao exata para auditoria)
sanitize_for_json({'v': Decimal('123.456789012345')}, decimal_as_str=True)
# => {'v': '123.456789012345'}
```

Use `decimal_as_str=True` quando:
- Campo armazena VALOR MONETARIO CRITICO que sera re-lido e usado em novo calculo
- Auditoria regulatoria exige precisao exata
- Valor tem mais de 15 digitos significativos

Use `decimal_as_str=False` (default) quando:
- Campo armazena BREAKDOWN de calculo para exibicao no frontend
- Valor sera usado apenas para logs / debug / relatorios
- Frontend faz `JSON.parse()` e espera numbers

### Tipos suportados (tabela)

| Tipo Python           | Saida                                  |
|-----------------------|----------------------------------------|
| `None` / `bool` / `int` / `float` / `str` | passthrough            |
| `Decimal`             | `float` (ou `str` se `decimal_as_str`) |
| `datetime`            | ISO 8601 string (`"2026-04-14T10:30:00"`) |
| `date`                | ISO 8601 string (`"2026-04-14"`)       |
| `time`                | ISO 8601 string                        |
| `UUID`                | `str`                                  |
| `bytes` / `bytearray` | UTF-8 string (fallback base64)         |
| `Enum`                | `sanitize(enum.value)` (recursivo)     |
| `dict`                | recursao (chaves coercidas para `str`) |
| `list` / `tuple` / `set` / `frozenset` | lista recursiva       |
| objeto com `to_dict()` | `sanitize(obj.to_dict())`             |
| objeto com `__dict__` | `sanitize(obj.__dict__)` (fallback)    |
| outros                | `str(obj)` + log warning               |

### Padrao mental

> Campo `db.JSON` / `JSONB` recebendo dict vindo de calculo numerico,
> query SQLAlchemy ou API externa -> `sanitize_for_json()` antes.
> Sem excecoes.

### Callsites atuais

| Arquivo | Linha | Contexto |
|---------|-------|----------|
| `app/carvia/services/pricing/cotacao_v2_service.py` | 240 | `cotacao.detalhes_calculo` com output da `CalculadoraFrete` |
| `app/carvia/services/pricing/cotacao_v2_service.py` | 385 | `cotacao.detalhes_calculo` manual (defensivo) |

> Ao adicionar novo callsite, atualizar esta tabela.

---

## Futuros Helpers

Quando adicionar novos helpers a `app/utils/`:

1. Adicionar secao aqui com: Arquivo, Funcao, Problema, Como Usar, Quando USAR, Quando NAO precisa, Callsites
2. Atualizar INDEX.md com entrada no topo
3. Se for padrao obrigatorio (como JSON sanitize), mencionar em `~/.claude/CLAUDE.md`
