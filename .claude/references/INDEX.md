# Indice de Referencias

**Ultima atualizacao**: 17/02/2026

---

## Consulta Rapida

| Preciso de... | Documento |
|---------------|-----------|
| Regras CarteiraPrincipal / Separacao (listeners, status, gotchas) | [modelos/REGRAS_CARTEIRA_SEPARACAO.md](modelos/REGRAS_CARTEIRA_SEPARACAO.md) |
| Regras Embarque, Faturamento, etc. (status, gotchas, naming traps) | [modelos/REGRAS_MODELOS.md](modelos/REGRAS_MODELOS.md) |
| Campos e tipos de QUALQUER tabela | Schemas auto-gerados: `skills/consultando-sql/schemas/tables/{tabela}.json` |
| Queries SQL / JOINs | [modelos/QUERIES_MAPEAMENTO.md](modelos/QUERIES_MAPEAMENTO.md) |
| Cadeia Pedido -> Entrega (JOINs, estados, formulas) | [modelos/CADEIA_PEDIDO_ENTREGA.md](modelos/CADEIA_PEDIDO_ENTREGA.md) |
| Regras de negocio | [negocio/REGRAS_NEGOCIO.md](negocio/REGRAS_NEGOCIO.md) |
| Frete Real vs Teorico (4 valores, divergencias, conta corrente) | [negocio/FRETE_REAL_VS_TEORICO.md](negocio/FRETE_REAL_VS_TEORICO.md) |
| Margem e Custeio (formula margem, tabelas de custo) | [negocio/MARGEM_CUSTEIO.md](negocio/MARGEM_CUSTEIO.md) |
| Recebimento de materiais | [negocio/RECEBIMENTO_MATERIAIS.md](negocio/RECEBIMENTO_MATERIAIS.md) |
| Historico de decisoes | [negocio/historia_nacom.md](negocio/historia_nacom.md) |
| **OBRIGATORIO — Timezone (Brasil naive)** | [REGRAS_TIMEZONE.md](REGRAS_TIMEZONE.md) |
| **Routing de skills** | [ROUTING_SKILLS.md](ROUTING_SKILLS.md) |
| **Infraestrutura Render e Odoo** | [INFRAESTRUTURA.md](INFRAESTRUTURA.md) |
| **Confiabilidade de subagentes** | [SUBAGENT_RELIABILITY.md](SUBAGENT_RELIABILITY.md) |
| **Manual para CLAUDE.md de modulo** | [MANUAL_CLAUDE_MD.md](MANUAL_CLAUDE_MD.md) |
| **Capacidades MCP (versoes, features, gaps)** | [MCP_CAPABILITIES_2026.md](MCP_CAPABILITIES_2026.md) |

---

## Odoo

| Preciso de... | Documento |
|---------------|-----------|
| IDs fixos (Companies, Picking Types, Journals) | [odoo/IDS_FIXOS.md](odoo/IDS_FIXOS.md) |
| GOTCHAS criticos (timeouts, campos inexistentes) | [odoo/GOTCHAS.md](odoo/GOTCHAS.md) |
| Modelos Odoo (DFe, PO, SO, Stock, Financeiro) | [odoo/MODELOS_CAMPOS.md](odoo/MODELOS_CAMPOS.md) |
| Padroes avancados (auditoria, batch, locks) | [odoo/PADROES_AVANCADOS.md](odoo/PADROES_AVANCADOS.md) |
| Pipeline Recebimento (Fases 1-4) | [odoo/PIPELINE_RECEBIMENTO.md](odoo/PIPELINE_RECEBIMENTO.md) |
| Conversao de unidades (UoM) | [odoo/CONVERSAO_UOM.md](odoo/CONVERSAO_UOM.md) |
| Wizard vs API (reconciliacao extrato) | `scripts/analise_baixa_titulos/WIZARD_VS_API_ANALISE.md` |
| Analise multi-company extrato (teste UI) | `scripts/analise_baixa_titulos/ANALISE_CONCILIACAO_EXTRATO_MULTICOMPANY.md` |

---

## Design & Frontend

| Documento | Descricao |
|-----------|-----------|
| [design/MAPEAMENTO_CORES.md](design/MAPEAMENTO_CORES.md) | Tokens de cor, paleta, dark/light mode |

---

## Planejamento (fora de references — nao operacional)

Roadmaps e planejamento futuro foram movidos para `.planning/roadmaps/`:
- `FEATURES_AGENTE.md` — Features futuras do Agente Logistico
- `IMPLEMENTACAO_ODOO.md` — Status de implementacao Odoo

---

## Mapeamento Skill -> References

| Skill | References Utilizadas |
|-------|----------------------|
| `validacao-nf-po` | odoo/PIPELINE_RECEBIMENTO, odoo/GOTCHAS, odoo/IDS_FIXOS |
| `conciliando-odoo-po` | odoo/PIPELINE_RECEBIMENTO, odoo/GOTCHAS, odoo/MODELOS_CAMPOS |
| `recebimento-fisico-odoo` | odoo/PIPELINE_RECEBIMENTO, odoo/CONVERSAO_UOM, odoo/GOTCHAS |
| `executando-odoo-financeiro` | odoo/IDS_FIXOS, odoo/GOTCHAS, odoo/MODELOS_CAMPOS |
| `razao-geral-odoo` | odoo/MODELOS_CAMPOS |
| `integracao-odoo` | odoo/PADROES_AVANCADOS, odoo/IDS_FIXOS, odoo/GOTCHAS |
| `rastreando-odoo` | odoo/MODELOS_CAMPOS, odoo/IDS_FIXOS |
| `descobrindo-odoo-estrutura` | odoo/MODELOS_CAMPOS |
| `gerindo-expedicao` | modelos/REGRAS_CARTEIRA_SEPARACAO, negocio/REGRAS_NEGOCIO |
| `frontend-design` | design/MAPEAMENTO_CORES |
