---
name: auditando-sped-contabil
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. Audita aspectos contabeis
  do SPED ECD parseado: equacionalidade de saldos (I155), hierarquia do
  plano de contas (I050), cross-ref I050<->I250. Matematica pura — zero
  falso positivo. Use apos parseando-sped-ecd. Detecta: saldo inicial +
  debitos - creditos != saldo final, COD_CTA_SUP orfao, ciclo na arvore
  de contas, COD_NAT divergente entre pai/filha, conta sintetica
  movimentada em I250.
allowed-tools: Read, Bash
---

# auditando-sped-contabil — Auditoria Contabil SPED

## Quando usar

Sempre apos `parseando-sped-ecd`. Detecta erros estruturais NAO cobertos
pelo `sped_ecd_validator.py` interno (que valida formato, nao matematica).

## Como usar

```bash
source .venv/bin/activate

# 1. Equacionalidade saldo I155
python .claude/skills/auditando-sped-contabil/scripts/audit_balance.py \
    /tmp/sped-parsed-v21.json

# 2. Hierarquia I050 + cross-ref I250
python .claude/skills/auditando-sped-contabil/scripts/audit_hierarchy.py \
    /tmp/sped-parsed-v21.json
```

## Output

Cada script retorna JSON com:
```json
{
  "total_i155": 1234,
  "findings_count": 3,
  "findings_por_tipo": {...},
  "findings": [
    {"categoria": "batimento_contabil", "tipo": "equacionalidade_saldo",
     "cod_cta": "11101", "severidade": "BLOQUEANTE",
     "descricao": "...", "malformed": false, ...}
  ]
}
```

## Categorias de finding

| Tipo | Severidade | O que detecta |
|---|---|---|
| `equacionalidade_saldo` | BLOQUEANTE | signed(saldo_fin) != signed(saldo_ini) + deb - cred |
| `registro_malformado` | WARNING | Campo ausente ou valor decimal invalido em I155 |
| `orfao_cod_sup` | BLOQUEANTE | COD_CTA_SUP nao existe em I050 |
| `ciclo_hierarquia` | BLOQUEANTE | Ciclo na arvore I050 (DFS deduplicado) |
| `cod_nat_divergente` | BLOQUEANTE | Filha tem COD_NAT diferente do pai |
| `i250_conta_inexistente` | BLOQUEANTE | Lancamento em conta nao declarada |
| `i250_conta_sintetica` | BLOQUEANTE | Lancamento em sintetica (so analiticas) |

## Tolerancia

`audit_balance.py` aceita parametro `tolerance` (default 0,01). Diferencas
menores ignoradas (arredondamento). Use `tolerance=0` para modo estrito.

## Algoritmos

- **Equacionalidade**: matematica Decimal pura. signed(saldo) aplica sinal
  conforme IND_DC (D=+, C=-). Comparacao com tolerance evita falsos por
  arredondamento.
- **Hierarquia I050**: DFS com `path_set` O(1) membership + dedup de ciclos
  via `tuple(sorted(set(cycle)))` para detectar mesmo ciclo iniciado de
  nos diferentes.
- **Cross-ref I250**: lookup em dict de COD_CTA. Sintetica detectada via
  `IND_CTA=S`.

## NAO usar quando

- Auditoria de formato/campo (usar `auditando-sped-vs-manual`)
- Comparacao com SPED contadora (usar `comparando-sped-ground-truth`)
- Validacao pre-upload (validator interno em `sped_ecd_validator.py`)
