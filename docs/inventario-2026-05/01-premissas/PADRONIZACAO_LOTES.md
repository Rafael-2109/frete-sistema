<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/01-premissas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Padronização de lotes — INVENTARIO_2026_05

**Criado**: 2026-05-18
**Status**: PROPOSTO (não executado)
**Escopo**: lotes de empresas em escopo (FB cid=1, CD cid=4, LF cid=5)

---

## 1. Padrão alvo (canônico)

```
MI ###-###/AA
```

- Prefixo: `MI` + ESPAÇO (obrigatório)
- 3 dígitos
- Separador interno: `-` (hífen, único permitido)
- 3 dígitos
- `/`
- 2 dígitos (ano AA)

**Exemplo**: `MI 027-098/26`

---

## 2. Regra de e-para

### Forma genérica

```
ENTRADA: {prefixo}{n1}{sep}{n2}/{aa}
  prefixo ∈ { "MI", "MI ", "" }
  n1      ∈ 3 dígitos
  sep     ∈ { "-", ".", "," }
  n2      ∈ 3 dígitos
  aa      ∈ 2 dígitos

SAÍDA: "MI " + n1 + "-" + n2 + "/" + aa
```

### Regex de captura (Python)

```python
import re

PATTERN = re.compile(
    r'^(?:MI\s*)?'      # prefixo opcional "MI" + espaços
    r'(\d{3})'          # n1 (3 dígitos)
    r'\s*[.,\-]\s*'     # separador . , - (com espaços tolerados)
    r'(\d{3})'          # n2 (3 dígitos)
    r'\s*/\s*'          # / (com espaços tolerados)
    r'(\d{2})$'         # AA (2 dígitos)
)

def normalizar(nome: str) -> str | None:
    """Retorna lote canônico 'MI ###-###/AA' ou None se não bater."""
    m = PATTERN.match(nome.strip())
    if not m:
        return None
    n1, n2, aa = m.groups()
    return f"MI {n1}-{n2}/{aa}"
```

### Casos cobertos (testar)

| Entrada | Saída canônica |
|---|---|
| `MI027-098/26` | `MI 027-098/26` |
| `MI 027-098/26` | `MI 027-098/26` |
| `MI  027-098/26` (duplo espaço) | `MI 027-098/26` |
| `027-098/26` (sem MI) | `MI 027-098/26` |
| `MI 025.091/26` (com ponto) | `MI 025-091/26` |
| `MI 025,091/26` (com vírgula) | `MI 025-091/26` |
| `MI 091 - 316/24` (espaços ao redor) | `MI 091-316/24` |
| `MI 46 - 197/24` (n1 só 2 dígitos) | **NÃO MATCH** → revisão manual |
| `135/26` (sem n1) | **NÃO MATCH** → só `n2/AA`, revisão manual (caso E10) |
| `MIGRAÇÃO` | **NÃO MATCH** → não é lote MI |
| `T20241014` | **NÃO MATCH** → não é lote MI |
| `2507/24` | **NÃO MATCH** → não é lote MI |

---

## 3. Variações observadas no Odoo FB hoje

Amostra observada na tabela `ajuste_estoque_inventario` (ciclo INVENTARIO_2026_05, company_id=1):

| Forma | Exemplo real | Cod | Saldo Odoo |
|---|---|---|---|
| `MI ###-###/AA` (canônico) | `MI 027-098/26` | 104000015 | 29.000,00 |
| `MI###-###/AA` (sem espaço) | `MI094-217/25` | 104000015 | 29.000,00 |
| `MI ### - ###/AA` (espaços ao redor de hífen) | `MI 091 - 316/24` | 104000015 | 41,93 |
| `MI### ###/AA` (sem separador) | (raro) | — | — |
| `### ### /AA` (sem MI) | `027-098/26` | 104000015 | 0 (qtd_inv=7000) |
| `MI ###.###/AA` (com ponto) | `MI 025.091/26` | 104000004 | 14,40 |
| `MI ##-###/AA` (n1=2 dígitos) | `MI 46 - 197/24` | 104000002 | 1.000,00 |
| Outros (não MI) | `MIGRAÇÃO`, `T20241014`, `2507/24`, `12892` | vários | vários |

---

## 4. Padronização parcial (sessão emergencial 2026-05-18)

Para os 9 lotes do ajuste emergencial FB de 2026-05-18, aplicar **apenas**:

- Adicionar **espaço após `MI`** quando ausente
- Trocar separador interno (`.` ou `,`) por `-`
- Adicionar prefixo `MI ` quando lote citado não tem mas é compatível com o padrão

Isso **não cobre** os casos `MI 46 - 197/24` (n1=2 dígitos), `MIGRAÇÃO`, lotes Odoo legados (`2507/24`, `12892`). Esses ficam para a padronização completa (ver `PENDENCIAS.md`).

---

## 5. Padronização completa (FUTURO — PENDENTE)

Ver `PENDENCIAS.md` item P1.

Plano resumido (não executar ainda):
1. Inventariar todos os `stock.lot` das 3 companies (FB/CD/LF) cujo nome bate em variantes do padrão
2. Identificar colisões (mesmo nome canônico apontando para múltiplos `stock.lot.id` distintos)
3. Para colisões: decisão caso a caso (merge via transferência interna ou manter diferenciado)
4. Aplicar normalização via `stock.lot.write({'name': canonico})` (operação reversível com snapshot)
5. Atualizar `ajuste_estoque_inventario.lote_odoo` e `lote_inventariado` em massa

**Pré-requisito**: ondas 1+2 D004 concluídas (renames e diferença líquida cross-company já materializados). Senão o rename direto colide com `RENOMEAR_LOTE` pendente.

---

## 6. Referências

- `SOT.md §7.4` — estratégia D004 (RENOMEAR_LOTE + diferença líquida)
- `AJUSTES_EMERGENCIAIS_FB.md` — uso da padronização parcial nos 9 ajustes 2026-05-18
- `PENDENCIAS.md` — pendência P1 (padronização completa)
