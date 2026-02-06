# Indice de Referencias

**Ultima atualizacao**: 06/02/2026
**Gerado por**: Reestruturacao arquitetural

---

## Consulta Rapida

| Preciso de... | Documento |
|---------------|-----------|
| Campos CarteiraPrincipal / Separacao | [modelos/CAMPOS_CARTEIRA_SEPARACAO.md](modelos/CAMPOS_CARTEIRA_SEPARACAO.md) |
| Campos Embarque, Faturamento, etc. | [modelos/MODELOS_CAMPOS.md](modelos/MODELOS_CAMPOS.md) |
| Queries SQL / JOINs | [modelos/QUERIES_MAPEAMENTO.md](modelos/QUERIES_MAPEAMENTO.md) |
| Cadeia Pedido -> Entrega (JOINs, estados, formulas) | [modelos/CADEIA_PEDIDO_ENTREGA.md](modelos/CADEIA_PEDIDO_ENTREGA.md) |
| Regras de negocio | [negocio/REGRAS_NEGOCIO.md](negocio/REGRAS_NEGOCIO.md) |
| Frete Real vs Teorico (4 valores, divergencias, conta corrente) | [negocio/FRETE_REAL_VS_TEORICO.md](negocio/FRETE_REAL_VS_TEORICO.md) |
| Margem e Custeio (formula margem, tabelas de custo) | [negocio/MARGEM_CUSTEIO.md](negocio/MARGEM_CUSTEIO.md) |
| Recebimento de materiais | [negocio/RECEBIMENTO_MATERIAIS.md](negocio/RECEBIMENTO_MATERIAIS.md) |
| Historico de decisoes | [negocio/historia_organizada.md](negocio/historia_organizada.md) |

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

---

## Design & Frontend

| Documento | Descricao |
|-----------|-----------|
| [design/MAPEAMENTO_CORES.md](design/MAPEAMENTO_CORES.md) | Tokens de cor, paleta, dark/light mode |

---

## Roadmaps

| Documento | Descricao |
|-----------|-----------|
| [roadmaps/FEATURES_AGENTE.md](roadmaps/FEATURES_AGENTE.md) | Features futuras do Agente Logistico |
| [roadmaps/IMPLEMENTACAO_ODOO.md](roadmaps/IMPLEMENTACAO_ODOO.md) | Status de implementacao Odoo |

---

## Cookbooks (Exemplos Anthropic)

Em [cookbooks/](cookbooks/):
- `BUILDING_EVALS.md` - Construcao de avaliacoes
- `CONTEXT_COMPACTION.md` - Compactacao de contexto
- `METAPROMPT.md` - Meta-prompts
- `PROMPT_CACHING.md` - Cache de prompts

---

## Mapeamento Skill -> References

Quais references cada skill consome:

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
| `gerindo-expedicao` | modelos/CAMPOS_CARTEIRA_SEPARACAO, negocio/REGRAS_NEGOCIO |
| `frontend-design` | design/MAPEAMENTO_CORES |

---

## Skills por Dominio

### Agente Web (Render/Producao)
- `gerindo-expedicao` - Consultas logisticas, estoque, separacoes
- `memoria-usuario` - Memoria persistente entre sessoes

### Claude Code (Desenvolvimento)
- Odoo: rastreando-odoo, executando-odoo-financeiro, descobrindo-odoo-estrutura, integracao-odoo, validacao-nf-po, conciliando-odoo-po, recebimento-fisico-odoo, razao-geral-odoo
- Dev: frontend-design, skill_creator, ralph-wiggum, prd-generator

### Compartilhados (ambos dominios)
- `exportando-arquivos`, `lendo-arquivos`
