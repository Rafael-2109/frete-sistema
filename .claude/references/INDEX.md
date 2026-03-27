# Indice de Referencias

**Ultima atualizacao**: 27/03/2026

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
| Prioridades P1-P7, envio parcial, decisao de corte | [negocio/REGRAS_P1_P7.md](negocio/REGRAS_P1_P7.md) |
| Recebimento de materiais | [negocio/RECEBIMENTO_MATERIAIS.md](negocio/RECEBIMENTO_MATERIAIS.md) |
| Historico de decisoes | [negocio/historia_nacom.md](negocio/historia_nacom.md) |
| **OBRIGATORIO — Timezone (Brasil naive)** | [REGRAS_TIMEZONE.md](REGRAS_TIMEZONE.md) |
| **Routing de skills** | [ROUTING_SKILLS.md](ROUTING_SKILLS.md) |
| **Infraestrutura Render e Odoo** | [INFRAESTRUTURA.md](INFRAESTRUTURA.md) |
| **Confiabilidade de subagentes** | [SUBAGENT_RELIABILITY.md](SUBAGENT_RELIABILITY.md) |
| **Manual para CLAUDE.md de modulo** | [MANUAL_CLAUDE_MD.md](MANUAL_CLAUDE_MD.md) |
| **Capacidades MCP (versoes, features, gaps)** | [MCP_CAPABILITIES_2026.md](MCP_CAPABILITIES_2026.md) |
| **Protocolo de memoria do agente** | [MEMORY_PROTOCOL.md](MEMORY_PROTOCOL.md) |
| **Framework aristotelico (analise/planejamento)** | [FRAMEWORK_ARISTOTELICO.md](FRAMEWORK_ARISTOTELICO.md) |
| **Regras output agente (I1, I5, I6)** | [REGRAS_OUTPUT.md](REGRAS_OUTPUT.md) |
| **Best Practices Anthropic 2026 (caching, structured output, pgvector)** | [BEST_PRACTICES_2026.md](BEST_PRACTICES_2026.md) |
| **Roadmap SDK Client (migracao query→ClaudeSDKClient)** | [ROADMAP_SDK_CLIENT.md](ROADMAP_SDK_CLIENT.md) |
| **Evolucao do sistema de memoria do agente** | `memory/memory_evolution.md` (auto-memory) |
| **Gestao do Agente (memorias, sessoes, KG, diagnosticos)** | `.claude/skills/gerindo-agente/SKILL.md` |
| **Agente Teams (bot async, sessoes, diferencas)** | `app/agente/CLAUDE.md` secao "Export critico: Teams" |

---

## CarVia (Frete Subcontratado)

| Preciso de... | Documento |
|---------------|-----------|
| Guia de desenvolvimento CarVia (regras R1-R5, gotchas, modelos) | `app/carvia/CLAUDE.md` |
| Campos de tabelas CarVia | Schemas: `skills/consultando-sql/schemas/tables/carvia_*.json` |

---

## Financeiro

| Preciso de... | Documento |
|---------------|-----------|
| Fluxos de reconciliacao (CNAB, Extrato, Comprovante, Baixas) | `app/financeiro/FLUXOS_RECONCILIACAO.md` |
| Guia de desenvolvimento financeiro (gotchas A1-A10, O1-O12) | `app/financeiro/CLAUDE.md` |
| Gotchas detalhados (80+) | `app/financeiro/GOTCHAS.md` |
| Regras de negocio contas a receber | `app/financeiro/contas_a_receber.md` |

---

## Odoo

| Preciso de... | Documento |
|---------------|-----------|
| IDs fixos (Companies, Picking Types, Journals) | [odoo/IDS_FIXOS.md](odoo/IDS_FIXOS.md) |
| GOTCHAS criticos (timeouts, campos inexistentes) | [odoo/GOTCHAS.md](odoo/GOTCHAS.md) |
| Modelos Odoo (DFe, PO, SO, Stock, Financeiro) | [odoo/MODELOS_CAMPOS.md](odoo/MODELOS_CAMPOS.md) |
| Padroes avancados (auditoria, batch, locks) | [odoo/PADROES_AVANCADOS.md](odoo/PADROES_AVANCADOS.md) |
| Pipeline Recebimento de Compras (Fases 1-4) | [odoo/PIPELINE_RECEBIMENTO.md](odoo/PIPELINE_RECEBIMENTO.md) |
| Pipeline Recebimento LF (37 etapas, Playwright NF-e) | [odoo/PIPELINE_RECEBIMENTO_LF.md](odoo/PIPELINE_RECEBIMENTO_LF.md) |
| Conversao de unidades (UoM) | [odoo/CONVERSAO_UOM.md](odoo/CONVERSAO_UOM.md) |
| Wizard vs API (reconciliacao extrato) | `scripts/analise_baixa_titulos/WIZARD_VS_API_ANALISE.md` |
| Analise multi-company extrato (teste UI) | `scripts/analise_baixa_titulos/ANALISE_CONCILIACAO_EXTRATO_MULTICOMPANY.md` |

---

## Linx (Microvix/ERP)

| Preciso de... | Documento |
|---------------|-----------|
| APIs, WebServices, autenticacao, metodos (WS Saida, B2C, Entrada, REST) | [linx/INTEGRACOES.md](linx/INTEGRACOES.md) |
| Timestamp incremental (sincronizacao) | [linx/INTEGRACOES.md](linx/INTEGRACOES.md) secao 3 |
| API Faturas a Pagar (REST/JSON) | [linx/INTEGRACOES.md](linx/INTEGRACOES.md) secao 7 |
| B2CConsultaNFe — campos, XML completo, chave 44 digitos | [linx/INTEGRACOES.md](linx/INTEGRACOES.md) secao 5.1 |
| Gotcha estoque (deposito em Tools) | [linx/INTEGRACOES.md](linx/INTEGRACOES.md) secao 8 |
| Links de documentacao e manuais | [linx/INTEGRACOES.md](linx/INTEGRACOES.md) secao 13 |

---

## Design & Frontend

| Documento | Descricao |
|-----------|-----------|
| [design/MAPEAMENTO_CORES.md](design/MAPEAMENTO_CORES.md) | Tokens de cor, paleta, dark/light mode |
| [design/GUIA_COMPONENTES_UI.md](design/GUIA_COMPONENTES_UI.md) | Botoes, badges, cores — qual classe usar |

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
| `gerindo-carvia` | app/carvia/CLAUDE.md |
| `frontend-design` | design/MAPEAMENTO_CORES, design/GUIA_COMPONENTES_UI |
| `cotando-frete` | negocio/FRETE_REAL_VS_TEORICO, negocio/MARGEM_CUSTEIO |
| `monitorando-entregas` | modelos/CADEIA_PEDIDO_ENTREGA |
| `acessando-ssw` | ssw/ROUTING_SSW, ssw/CARVIA_STATUS, ssw/INDEX |
| `operando-ssw` | ssw/INDEX, ssw/ROUTING_SSW |
| `consultando-sentry` | INFRAESTRUTURA |
| `visao-produto` | modelos/CADEIA_PEDIDO_ENTREGA, negocio/REGRAS_NEGOCIO |
| `gerindo-agente` | MEMORY_PROTOCOL, REGRAS_OUTPUT |
| `resolvendo-entidades` | (sem references — consulta banco diretamente) |
