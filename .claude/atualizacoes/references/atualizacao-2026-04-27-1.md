# Atualizacao References 2026-04-27-1

**Data**: 2026-04-27
**Escopo**: Auditoria completa de `.claude/references/` (P0 raiz, P1 modelos+negocio, P2 odoo) + scan rapido P3-P4 (design, linx, ssw)
**Status**: PARCIAL — divergencias identificadas nao puderam ser corrigidas (sensitive file lock em `.claude/references/*.md` e `.claude/atualizacoes/references/`)

> Este relatorio identifica as divergencias com evidencia. As correcoes propostas seguem o mesmo padrao das auditorias 2026-04-06 e 2026-04-20 — aguardam revisao humana para aplicar quando os locks dos sensitive files forem liberados.
>
> **Local final esperado**: `.claude/atualizacoes/references/atualizacao-2026-04-27-1.md` (nao gravado por sensitive file lock; backup em `/tmp/manutencao-2026-04-27/references-atualizacao-2026-04-27-1.md`).

---

## Resumo

~30 arquivos revisados (P0 raiz: 22 files, P1 modelos+negocio: 10 files, P2 odoo: 8 files; P3 design/linx + P4 ssw: scan rapido).
Identificadas **5 divergencias factuais** em P0, todas decorrentes de evolucao do SDK (0.1.63 -> 0.1.66) e do system_prompt.md (v4.2.0 -> v4.3.2) desde a ultima auditoria. P1, P2 e P3 sem divergencias criticas. **Nenhum caminho quebrado.** Implementacao (listeners Separacao, IDs Odoo, S3 callsites, scripts Odoo) confere com o que esta documentado.

---

## Divergencias Encontradas

### P0 — Raiz

#### 1. `BEST_PRACTICES_2026.md` (DIVERGENCIA — versao SDK)
- **Arquivo**: linhas 3 e 14-15
- **Header**: "Atualizado: 20/04/2026" — desatualizado (7 dias)
- **Documentado**: `claude-agent-sdk==0.1.63` (CLI 2.1.114)
- **Real em `requirements.txt:65`**: `claude-agent-sdk==0.1.66` (CLI 2.1.119)
- **Releases pulados**:
  - 0.1.64: SessionStore protocol (6 metodos) + transcript mirroring via `--session-mirror` + `materialize_resume_session` + 9 helpers async store-backed + conformance harness 13 contratos + CLI 2.1.116
  - 0.1.65: `ThinkingConfig.display` (`--thinking-display`) override para Opus 4.7 default "omitted" + `ServerToolUseBlock`/`ServerToolResultBlock` parser fix (antes: `AssistantMessage(content=[])` silencioso) + `fold_session_summary`/`import_session_to_store` helpers + bounded retry mirror append + UUID idempotency + CLI 2.1.118
  - 0.1.66: atual

#### 2. `MCP_CAPABILITIES_2026.md` (DIVERGENCIA — versao SDK + header obsoleto)
- **Arquivo**: linhas 1 e 11
- **Header titulo**: "Estado do Sistema (Mar/2026)" — desatualizado (1+ mes)
- **Header data**: "Atualizado: 2026-04-20"
- **Documentado**: `claude-agent-sdk 0.1.63` CLI 2.1.114
- **Real em `requirements.txt:65`**: `0.1.66` CLI 2.1.119
- **Spec MCP documentada (2025-11-25)** continua correta (`mcp==1.26.0` no requirements)

#### 3. `MEMORY_PROTOCOL.md` (DIVERGENCIA — linha de funcao)
- **Arquivo**: linha 33
- **Documentado**: `app/agente/sdk/memory_injection.py:173` para `_calculate_category_decay`
- **Real**: funcao definida na linha **271** (verificado via grep)
- Discrepancia provavelmente decorrente de edicoes em `memory_injection.py` desde a ultima auditoria

#### 4. `ROUTING_SKILLS.md` (DIVERGENCIA — contagem skills + 5 skills HORA ausentes do inventario)
- **Arquivo**: linha 129 e secao "Skills — Inventario Completo"
- **Documentado**: "25 invocaveis em `.claude/skills/`"
- **Real**: **30 invocaveis** em `.claude/skills/` (excluindo `SKILL_IMPROVEMENT_ROADMAP.md` que e doc, nao skill)
- **5 skills HORA novas nao listadas no inventario**:
  - `acompanhando-pedido` (Lojas HORA — pedidos pendentes)
  - `conferindo-recebimento` (Lojas HORA — conferencia em andamento)
  - `consultando-estoque-loja` (Lojas HORA — estoque por loja)
  - `consultando-pecas-faltando` (Lojas HORA — pecas faltando registradas)
  - `rastreando-chassi` (Lojas HORA — historico de UM chassi)
- **Nota**: O Passo 1 (linhas 36-41) JA cita as skills LOJAS HORA na tabela de routing, apenas o inventario quantitativo final (linhas 129+) esta defasado.
- Acao recomendada: adicionar secao "Skills Lojas HORA (5)" no inventario, ajustar contagem total

#### 5. `STUDY_PROMPT_ENGINEERING_2026.md` (DIVERGENCIA — versao SDK + system_prompt)
- **Arquivo**: linha 25
- **Documentado**: `claude-agent-sdk==0.1.55` + `anthropic==0.84.0`
- **Real**: SDK e **0.1.66** (anthropic 0.84.0 confere)
- **Documentado**: `app/agente/prompts/system_prompt.md` v4.2.0 (2026-03-28)
- **Real**: `system_prompt.md` agora **v4.3.2** (verificado: `head -1` retorna `<system_prompt version="4.3.2">`)
- **Nota historica**: O proprio `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` ja registra que findings foram aplicados em 2026-04-12 elevando o prompt para v4.3.0 — STUDY_PROMPT nao foi atualizado em consequencia. Versao avancou novamente para v4.3.2 desde entao.
- Acao recomendada: atualizar contexto do projeto (linha 25) com SDK 0.1.66 e system_prompt v4.3.2; adicionar nota no header sobre revisao

#### 6. `INDEX.md` (MENOR — header desatualizado)
- **Arquivo**: linha 3
- **Header**: "Ultima atualizacao: 20/04/2026"
- Conteudo OK; entradas ja cobrem todos os arquivos do diretorio (verificado contra `ls`)
- Acao recomendada: atualizar header se algum dos itens P0 acima for atualizado nesta sessao

### P0 — VERIFICADOS OK (sem divergencias)

| Arquivo | Verificado |
|---------|-----------|
| `INFRAESTRUTURA.md` | header 22/04/2026, recente. Servicos Render conferem com IDs reais |
| `S3_STORAGE.md` | header 16/04/2026. 25 modulos catalogados — `app/utils/file_storage.py` existe. Mapa folders cobre uso real |
| `PADROES_BACKEND.md` | header 14/04/2026. `app/utils/json_helpers.py` existe; callsites em `cotacao_v2_service.py:240,385` validados |
| `REGRAS_OUTPUT.md` | header 31/03/2026. I1, I5, I6 ainda fazem sentido — `system_prompt.md` v4.3.2 mantem I2-I4 inline |
| `REGRAS_TIMEZONE.md` | header 12/02/2026. `app/utils/timezone.py` existe; hook `ban_datetime_now.py` existe |
| `SUBAGENT_RELIABILITY.md` | header 13/02/2026 + atualizacao 17/04 (M1.1 SDK 0.1.60+). Padrao mantido. M1.1 cita SDK 0.1.60+ (validamente — feature continua em 0.1.66) |
| `AGENT_DESIGN_GUIDE.md` | header 09/04/2026. Frontmatter docs OK |
| `AGENT_TEMPLATES.md` | header 09/04/2026. 12 subagents referenciam — paths OK |
| `MANUAL_CLAUDE_MD.md` | header 14/02/2026. Hierarquia oficial Anthropic mantida |
| `FRAMEWORK_ARISTOTELICO.md` | sem header de data; conceitual, atemporal |
| `PROMPT_INJECTION_HARDENING.md` | header 12/04/2026. Defesas em camadas OK |
| `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` | header 12/04/2026 com nota de update aplicada — coerente |
| `ROADMAP_PROMPT_ENGINEERING_2026.md` | versao 1.3 (12/04/2026). P0 100% resolvido + Q1-Q8 |
| `ROADMAP_SDK_CLIENT.md` | header 04/04/2026. Status pausado coerente — Fases 4-5 pendentes |

### P1 — modelos/ (4 files)

Sem divergencias criticas. Verificado:
- `REGRAS_CARTEIRA_SEPARACAO.md` (07/02/2026): linhas dos listeners (208, 244, 293, 326) em `app/separacao/models.py` **conferem exatamente** (verificado via grep). Campos documentados (CarteiraPrincipal sem `separacao_lote_id`/`expedicao`/`agendamento`; Separacao com `qtd_saldo` nao `qtd_saldo_produto_pedido`) confirmados nos schemas
- `REGRAS_MODELOS.md` (07/02/2026): regras de Pedido (view), PreSeparacaoItem (deprecated), Embarque (status, tipos de carga), EmbarqueItem batem com codigo
- `CADEIA_PEDIDO_ENTREGA.md`: cadeia CarteiraPrincipal->Separacao->EmbarqueItem->Embarque consistente com schemas
- `QUERIES_MAPEAMENTO.md`: 20 queries representativas (Q1-Q20) — referencias a scripts em `.claude/skills/consultando-sql/queries/` OK

### P1 — negocio/ (6 files)

Sem divergencias criticas. Verificado:
- `REGRAS_NEGOCIO.md` (07/03/2026): regras de Nacom Goya, grupos empresariais por CNPJ, agendamento, lead time
- `REGRAS_P1_P7.md`: hierarquia P1-P7 consistente; nota de SYNC com `system_prompt.md` e `analista-carteira.md` valida (regras vivem aqui)
- `FRETE_REAL_VS_TEORICO.md`: 4 valores (cotado/cte/considerado/pago) consistentes com tabela `fretes`
- `MARGEM_CUSTEIO.md`: formulas margem bruta e liquida documentadas
- `RECEBIMENTO_MATERIAIS.md` (07/03/2026): Fases 1-4 IMPLEMENTADAS, Fase 5 pendente. Coerente com `app/recebimento/services/`
- `historia_nacom.md`: documento historico (sem header de data) — referencia memorial

### P2 — odoo/ (8 files)

Sem divergencias criticas novas. Verificado:
- `IDS_FIXOS.md`: companies (FB=1, SC=3, CD=4, LF=5), picking types (1, 8, 13, 16), journals (883, 885, 886, 879, 1066) — consistentes. Pendencia historica: `product_tmpl_id ~34~ VERIFICAR` ainda aberto desde 31/Jan/2026 (mesma pendencia da auditoria anterior)
- `MODELOS_CAMPOS.md`: mapeamento `l10n_br_fiscal.*` (NAO EXISTE) -> `l10n_br_ciel_it_account.*` (correto) consistente
- `GOTCHAS.md`: timeouts, campos inexistentes, commit preventivo — patterns continuam validos
- `ROUTING_ODOO.md`: arvore de decisao Odoo coerente com skills disponiveis
- `AGENT_BOILERPLATE.md`: scripts referenciados existem:
  - `.claude/skills/rastreando-odoo/scripts/rastrear.py` ✓
  - `.claude/skills/rastreando-odoo/scripts/auditoria_faturas_compra.py` ✓
  - `.claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py` ✓
- `PIPELINE_RECEBIMENTO.md`: 4 fases consistentes com `app/recebimento/services/`
- `PIPELINE_RECEBIMENTO_LF.md` (21/02/2026): 37 etapas LF
- `CONVERSAO_UOM.md` (14/01/2026): fluxo MILHAR/UN documentado
- `PADROES_AVANCADOS.md`: auditoria por etapa, batch, retry — patterns aplicados

### P3 — design/ (2 files)

Sem divergencias criticas. Verificado:
- `MAPEAMENTO_CORES.md` (18/12/2025 — antigo, mas conteudo continua valido): paths atualizados na auditoria 2026-04-20 (`base/_bootstrap-overrides.css`) confirmados via `ls /app/static/css/base/`
- `GUIA_COMPONENTES_UI.md` (02/03/2026): tabela de botoes/badges coerente com classes CSS

### P3 — linx/ (1 file)

- `INTEGRACOES.md` (23/02/2026): 5 interfaces de integracao (WS Saida, WS B2C, WS Entrada, ERP REST, API Faturas) — sem alteracoes recentes

### P4 — ssw/ (309 files .md)

Scan rapido — sem anomalias evidentes. Diretorios principais: cadastros, comercial, contabilidade, edi, embarcador, financeiro, fiscal, fluxos, logistica, operacional, pops, relatorios.
Volume alto, estabilidade alta. Sem divergencias triggadas pelos signals do README (sinais de atencao nao apareceram).

---

## Pendencias Historicas (carregadas de auditorias anteriores)

1. **`odoo/IDS_FIXOS.md` linha 80**: Flag `product_tmpl_id ~34~ VERIFICAR` aberto desde 31/Jan/2026 — requer consulta MCP Odoo ao modelo `product.product` para confirmar `product_tmpl_id` real do produto FRETE (ID=29993). NAO resolvido nesta sessao (sem evidencia direta de qual e o `product_tmpl_id` correto).

---

## Acoes Recomendadas (a aplicar quando lock de sensitive file for liberado)

| # | Arquivo | Acao | Severidade |
|---|---------|------|------------|
| 1 | `BEST_PRACTICES_2026.md` | Header 20/04 -> 27/04 + SDK 0.1.63 -> 0.1.66 (com nota das releases 0.1.64, 0.1.65, 0.1.66) | MEDIA |
| 2 | `MCP_CAPABILITIES_2026.md` | Titulo "Mar/2026" -> "Abr/2026"; header 2026-04-20 -> 2026-04-27; SDK 0.1.63 -> 0.1.66 | MEDIA |
| 3 | `MEMORY_PROTOCOL.md` | Linha 33: `memory_injection.py:173` -> `:271` | BAIXA |
| 4 | `ROUTING_SKILLS.md` | Contagem 25 -> 30; adicionar secao "Skills Lojas HORA (5)" no inventario; header 20/04 -> 27/04 | MEDIA |
| 5 | `STUDY_PROMPT_ENGINEERING_2026.md` | Linha 25: SDK 0.1.55 -> 0.1.66; system_prompt v4.2.0 -> v4.3.2 | BAIXA (study, doc historico) |
| 6 | `INDEX.md` | Header 20/04 -> 27/04 (se itens 1-5 forem aplicados) | BAIXA |
| 7 | `odoo/IDS_FIXOS.md` | Pendencia historica `product_tmpl_id ~34~ VERIFICAR` | BAIXA (requer MCP Odoo) |

---

## Historico

- Auditoria 2026-04-06: 6 divergencias identificadas, nao corrigidas (sensitive file lock).
- Auditoria 2026-04-20: 7 divergencias, 6 corrigidas apos liberacao manual, 1 pendente (item 7 acima).
- Auditoria 2026-04-27 (esta): **5 divergencias novas + 1 pendencia historica**, todas decorrentes de evolucao SDK/prompt desde 20/04. **Aguardando liberacao manual de sensitive files** para aplicar correcoes.

Nenhum caminho quebrado critico. Sem deletar ou renomear arquivos.

---

## Estatisticas

- **Arquivos revisados (full)**: 30 (22 P0 + 4 P1 modelos + 6 P1 negocio + 8 P2 odoo)
- **Arquivos com scan rapido**: ~313 (3 P3 design+linx + ~310 P4 ssw)
- **Arquivos com divergencia**: 5 (4 P0 com SDK/inventario stale + 1 minor INDEX)
- **Arquivos corrigidos**: 0 (sensitive file lock — proposta de correcoes documentada)
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 1 (`product_tmpl_id` Odoo desde Jan/2026)
