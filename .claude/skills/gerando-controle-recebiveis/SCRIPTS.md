<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# Scripts — gerando-controle-recebiveis

> **Papel:** referencia dos scripts da skill gerando-controle-recebiveis.

## `scripts/gerar_controle_recebiveis.py`

Gera o `.xlsx` de controle de titulos a receber e salva na pasta de download do
agente (`/tmp/agente_files/<session_id>/`).

### Argumentos

| Arg | Descricao |
|-----|-----------|
| `--cliente` | CNPJ/raiz (>= 6 digitos) OU nome (ILIKE). **Repetivel** (OR entre eles). |
| `--gestor` | Filtra por gestor/equipe de vendas (ILIKE). Ex.: `DENISE`, `MILER`. |
| `--empresa` | `1`=FB, `2`=SC, `3`=CD. |
| `--apenas-vencidos` | So titulos vencidos e nao pagos. |
| `--desde` | `vencimento >= YYYY-MM-DD`. Default: ultimos 365 dias **se** nao houver `--cliente`/`--gestor` (evita varrer a tabela inteira). |
| `--session-id` | **Obrigatorio na pratica** — session do agente, define a pasta de download. Sem ele cai em `default` -> 404 (gotcha #787). |
| `--nome` | Nome base do arquivo (default `controle_recebiveis`). |

### Retorno (stdout, JSON)

```json
{"sucesso": true, "arquivo": "<id>_controle_recebiveis.xlsx",
 "url": "/agente/api/files/<sid>/<arquivo>",
 "resumo": {"total": N, "confirmado": X, "vencido": Y, "em_aberto": Z,
            "gestores": [...], "valor_vencido": 0.0},
 "nota": "..."}
```

`sucesso:false` com `erro` quando a consulta falha ou nenhum titulo casa o filtro.

### Estrutura interna (testabilidade)

- `buscar_titulos(filtros)` — toca o banco (`from app import create_app, db`); roda a
  query parametrizada (contas_a_receber + gestor por CNPJ via faturamento_produto +
  vendedor via entregas_monitoradas; situacao derivada em SQL).
- `gerar_excel(titulos, filepath)` — **PURO** (recebe `list[dict]`), gera as 2 abas +
  formatacao + agrupamento por gestor. Coberto por `tests/skills/test_gerar_controle_recebiveis.py`
  (situacao, agrupamento, subtotais, drop de coluna vazia).

### Gotchas

- A pasta de download espelha `app/agente/routes/_constants.py` (`/tmp/agente_files`);
  **nao** usar `tempfile.gettempdir()` (TMPDIR do CLI != dir servido pelo gunicorn).
- `CONFIRMADO` = `parcela_paga` do Odoo. Delta do extrato Grafeno nao baixado fica
  como Vencido/Em Aberto (ver SKILL.md "Limite conhecido").

## Fontes
- `scripts/gerar_controle_recebiveis.py` (este pacote)
- Schema: `.claude/skills/consultando-sql/schemas/tables/contas_a_receber.json`
- `SKILL.md` (mesma skill)
