# Índice de Referências

**Última atualização**: 24/01/2026

Este é o ponto de entrada para toda documentação de referência do projeto.

---

## Consulta Rápida (Uso Frequente)

| Preciso de... | Documento |
|---------------|-----------|
| Campos de modelos (Embarque, ContasAReceber, etc.) | [MODELOS_CAMPOS.md](MODELOS_CAMPOS.md) |
| Queries SQL mapeadas | [QUERIES_MAPEAMENTO.md](QUERIES_MAPEAMENTO.md) |
| Regras de negócio (bonificação, roteirização, etc.) | [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) |
| Conversão de unidades Odoo | [CONVERSAO_UOM_ODOO.md](CONVERSAO_UOM_ODOO.md) |
| Recebimento de materiais | [RECEBIMENTO_MATERIAIS.md](RECEBIMENTO_MATERIAIS.md) |

**Nota**: Campos de CarteiraPrincipal e Separacao estão no **CLAUDE.md** (raiz do projeto).

---

## Integração Odoo (NOVO)

| Preciso de... | Documento |
|---------------|-----------|
| IDs fixos (Companies, Picking Types, Operações, Journals) | [ODOO_IDS_FIXOS.md](ODOO_IDS_FIXOS.md) |
| GOTCHAS críticos (timeouts, campos inexistentes, comportamentos) | [ODOO_GOTCHAS.md](ODOO_GOTCHAS.md) |
| Modelos Odoo (DFe, PO, SO, Stock, Financeiro) | [ODOO_MODELOS_CAMPOS.md](ODOO_MODELOS_CAMPOS.md) |
| Padrões avançados (auditoria, batch, locks, retomada) | [ODOO_PADROES_AVANCADOS.md](ODOO_PADROES_AVANCADOS.md) |
| Pipeline Recebimento (Fases 1-4) | [ODOO_PIPELINE_RECEBIMENTO.md](ODOO_PIPELINE_RECEBIMENTO.md) |

---

## Design & Frontend

| Documento | Descrição |
|-----------|-----------|
| [MAPEAMENTO_CORES.md](MAPEAMENTO_CORES.md) | Tokens de cor, paleta, dark/light mode |

---

## Roadmaps Ativos

| Documento | Descrição |
|-----------|-----------|
| [ROADMAP_FEATURES_AGENTE.md](ROADMAP_FEATURES_AGENTE.md) | Features futuras do Agente Logístico |
| [ROADMAP_IMPLEMENTACAO.md](ROADMAP_IMPLEMENTACAO.md) | Status de implementação Odoo |

---

## Contexto & Histórico

| Documento | Descrição |
|-----------|-----------|
| [historia_organizada.md](historia_organizada.md) | Contexto da empresa Nacom Goya, decisões históricas |

---

## Cookbooks (Exemplos Anthropic)

Exemplos de padrões do Claude/Agent SDK em [cookbooks/](cookbooks/):

- `BUILDING_EVALS.md` - Construção de avaliações
- `CONTEXT_COMPACTION.md` - Compactação de contexto
- `METAPROMPT.md` - Meta-prompts
- `PROMPT_CACHING.md` - Cache de prompts

---

## Skills do Projeto

As skills estão documentadas em `.claude/skills/`. Principais:

| Skill | Propósito |
|-------|-----------|
| `gerindo-expedicao` | Consultas logísticas, estoque, separações |
| `rastreando-odoo` | Rastreamento de fluxos documentais |
| `integracao-odoo` | Desenvolvimento de integrações |
| `descobrindo-odoo-estrutura` | Explorar modelos desconhecidos |
| `exportando-arquivos` | Gerar Excel/CSV/JSON |
| `lendo-arquivos` | Processar uploads |
| `frontend-design` | Interfaces web |
| `memoria-usuario` | Memória persistente |
