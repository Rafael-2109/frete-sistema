# Auditoria Crítica das Skills — 2026-05-29

> Workflow de 12 agentes (8 clusters + 4 cross-cutting), ~1.5M tokens, 691 tool calls.
> Vários agentes **se autocorrigiram** (retrataram hipóteses iniciais erradas). Findings brutos: `/tmp/subagent-findings/skills-audit/`.
> Escopo: 50 skills em `.claude/skills/` + 7 **slash commands** em `.claude/commands/` (que eu inicialmente confundi com "skills de subagente").

## Panorama

| Métrica | Valor |
|---|---|
| Skills reais em `.claude/skills/` | 50 (`consultando-sql` sem SKILL.md por design; +2 `.md` soltos que são docs, não skills) |
| Conformidade de nome (gerúndio PT-BR) | 92% — só 4 fora do padrão |
| Distribuição de scripts | operando-ssw=22 · rastreando-odoo=8 · gerindo-expedicao=8 (7 CLIs + 1 library) · resolvendo-entidades=7 · gerindo-agente=7 · … · maioria=1 · ~11 com 0 (código em `app/`) |
| Paradigma de teste | **3 coexistem**: `evals/` (skill-creator) ~21 skills · `pytest` (cluster estoque-odoo + SPED) · `none` (clusters HORA, Assai, +2 financeiras WRITE) |

## 1. Nomenclatura

**Convenção = gerúndio PT-BR. 92% conformes.** O problema NÃO é o gerúndio — é a **assimetria de sufixo entre clusters espelhados**.

**4 fora do padrão (substantivos, todas do lote 2026-02-26):**
- `visao-produto` → `consultando-visao-produto`
- `validacao-nf-po` → `validando-nf-po`
- `razao-geral-odoo` → `exportando-razao-geral-odoo`
- `recebimento-fisico-odoo` → `operando-recebimento-fisico-odoo`

**Assimetria HORA (sem sufixo) vs Assai (com `-assai`) — risco de colisão de roteamento:**
| HORA (sem sufixo) | Assai (com -assai) | Recomendado |
|---|---|---|
| `rastreando-chassi` | `rastreando-chassi-assai` | `rastreando-chassi-hora` |
| `consultando-estoque-loja` | `consultando-estoque-assai` | `consultando-estoque-hora` |
| `acompanhando-pedido` | `acompanhando-pedido-compra-assai` | `acompanhando-pedido-hora` |
| `conferindo-recebimento` | `conferindo-recibo-assai` | alinhar raiz recebimento/recibo + sufixo |

> Renomear exige checklist completo (ROUTING_SKILLS.md + tool_skill_mapper.py + skills_whitelist.py + evals + cross-refs "NÃO USAR PARA"). Custo real — priorizar P2.

## 2. Sobreposições

### REDUNDÂNCIA/DRIFT REAL (corrigir)
1. **`resolver_entidades.py` (library de gerindo-expedicao, 1458L) ⇄ skill `resolvendo-entidades` (7 CLIs por-tipo).** NÃO é cópia literal — são **duas implementações da mesma capacidade que DIVERGIRAM**: `gerindo-expedicao` recebeu refactor `BLOB+AND` (commit `e0ba4f6e`, 2026-05-26) em `resolver_produto`; `resolvendo-entidades` ainda usa `ABREVIACOES_PRODUTO`+ILIKE antigo. **Resultados de match podem diferir entre as duas.** Pior que cópia literal (que ao menos sincroniza trivial). `visao-produto` importa direto da library de gerindo-expedicao via `sys.path` hardcoded → quebra silenciosa se GE mudar. **Verdict: fronteira-borrada + drift.** → consolidar em UMA fonte (módulo em `app/`).
2. **Templates de comunicação PCP/Comercial + tabela Cliente→Gestor TRIPLICADOS**: `.claude/commands/comunicar-*.md` + inline em `analista-carteira.md` (linhas 59-134) + `references/communication.md`. Editar um gestor exige sincronizar 3 lugares.
3. **`vincular_extrato_fatura_excel.py` mal posicionado**: é WRITE (cria account.payment + reconcilia) mas vive em `rastreando-odoo`, cuja própria description diz "não usar para criar pagamento". Deveria estar em `executando-odoo-financeiro`.
4. **operando-ssw**: 3 scripts órfãos (`investigar_903_475_fase2.py`, `investigar_903_certificado.py`, `gravar_emissao_cte.py`) no diretório de produção, não documentados → agente pode tentar usá-los.

### SOBREPOSIÇÃO POR DESIGN (manter — confirmado pelos agentes)
- **7 slash commands** (`analise-carteira`, `criar-separacao`, `consultar-estoque`, `verificar-disponibilidade`, `comunicar-*`, `fp-lojas-motochefe`) são **wrappers finos** que DELEGAM aos scripts de gerindo-expedicao (grep confirmou: `criar-separacao.md:19 → criando_separacao_pedidos.py` etc.). **1 motor, 3 superfícies** (slash command / skill agente web / subagente analista-carteira). SEM duplicação de lógica.
- Cluster estoque-odoo (átomos compostos por `gestor-estoque-odoo`); `faturando` (saída) ⇄ `escriturando` (entrada); `operando-reservas` ⇄ `operando-picking` (cancel duplicado intencional p/ não trocar de skill mid-flow); pipeline SPED; `acessando-ssw` (READ) ⇄ `operando-ssw` (WRITE); `lendo-arquivos` ⇄ `lendo-documentos`; `gerando-artifact` ⇄ `frontend-design` (contextos distintos).

## 3. Gaps

### Skills faltando (operação real em produção SEM skill)
| Sev | Gap | Evidência |
|---|---|---|
| ALTA | **HORA M3 venda** — `registrando-venda`/`registrando-venda-loja` referenciadas mas inexistentes; `hora_venda` está LIVE em prod (40+ campos, venda_service ativo) | `skills_whitelist.py:19` "# M3 (futuro)"; refs em consultando-estoque-loja, rastreando-chassi, registrando-evento-moto-assai |
| ALTA | **Assai carregamento** — `assai_carregamento`/`_item` (etapa física Sep→NF) sem nenhuma skill | nenhuma skill do cluster cobre |
| MÉDIA | HORA: sem skill p/ `hora_transferencia`, `hora_avaria`, `hora_emprestimo_moto`, `hora_devolucao_venda` (tabelas ativas) | cluster lojas-hora |
| MÉDIA | `transferencia-saldo-codigo` — operação "transferir saldo entre CÓDIGOS de produto" não tem skill, mas é citada como destino em 2 skills | `ajustando-quant-odoo:13`, `transferindo-interno-odoo:21` |

### Testes ausentes
| Sev | Gap |
|---|---|
| ALTA | `conciliando-transferencias-internas` — skill WRITE sobre extratos bancários de PROD, ZERO testes (nem evals nem pytest) |
| ALTA | `operando-ssw` — CT-e (scripts fiscais mais críticos: emitir_004, cancelar_004, fatura_437, complementar_222) SEM nenhum eval/trigger_eval |
| MÉDIA | `gerando-baseline-conciliacao` (uso diário Marcus), `consultando-sentry`, `gerando-artifact` — sem evals |
| BAIXA | Clusters HORA (5) e Assai (6) inteiros sem testes formais |

### Refs a tools/recursos inexistentes
| Sev | Gap |
|---|---|
| ALTA | `consultando-sentry` documenta `mcp__sentry__get_issue_details` e `get_trace_details` que **não existem** no MCP server — o passo 2 do workflow principal aponta p/ tool fantasma |
| MÉDIA | `operando-portal-atacadao` cita MCP tool `browser_atacadao_login (C5)` inexistente; e `impressao_protocolo.py` não é CLI standalone (é módulo Flask) |

## 4. Staleness (bugs concretos, com file:line)

| Sev | Skill | Problema |
|---|---|---|
| **CRÍTICA** | `consultando-estoque-loja` | script (L183) classifica como estoque só `tipo=='RECEBIDA'`, mas `EVENTOS_EM_ESTOQUE=(RECEBIDA,CONFERIDA,TRANSFERIDA,CANCELADA)` → **contagens erradas** p/ lojas que usam transferência. **É bug de código, não só doc.** |
| ALTA | `acompanhando-pedido-compra-assai` | documenta status EM_PRODUCAO/SEPARANDO/FATURADO_PARCIAL **removidos em 2026-05-13** (Big Bang Task 19); omite PARCIALMENTE_FATURADO (doc-only; script ok) |
| MÉDIA | `rastreando-chassi` (HORA) | não trata eventos novos AVARIADA/EM_TRANSITO/TRANSFERIDA/RESERVADA/NF_EMITIDA (caem em fallback genérico) |
| MÉDIA | `diagnosticando-banco` | `postgresId` hardcoded (L237) — quebra se banco recriado |
| MÉDIA | `faturando-odoo` | 623L (>500): seções ANTIPADROES (~63L) + CHECKLIST (~55L) duplicam docs externos → mover p/ references/ |
| BAIXA | `monitorando-entregas` | SCRIPTS.md diz tabela `monitoramento_entregas`; real é `entregas_monitoradas` |
| BAIXA | `acessando-ssw` | "228 docs" — real são 309 .md |
| BAIXA | `razao-geral-odoo` | exemplo `company_ids=[4,1,3]` omite LF (company_id=5) |
| BAIXA | `parseando-sped-ecd` | exemplo fixo em V21; corrente é V36 |
| BAIXA | `gerindo-agente` | flag `MEMORY_SEMANTIC_SEARCH` duplicada (L151/155); model IDs hardcoded |
| BAIXA | `validacao-nf-po` | ref `recebimento-fisico` sem `-odoo`; labels "NOVO Jan/2026" |

### Drift de infraestrutura (NÃO corrompida — agente retratou alarme falso)
- `ROUTING_SKILLS.md` e `tool_skill_mapper.py` **compilam e estão íntegros** (idênticos a HEAD).
- Contagem de skills inconsistente: cabeçalho "49" vs seção "48" vs disco "50"; `faturando-odoo` na árvore mas fora do inventário.
- `tool_skill_mapper.py` (lookup de telemetria, NÃO roteador) falta ~12 skills novas (HORA, SPED, faturando-odoo, gerando-artifact, gerindo-agente, consultando-sentry) + chave obsoleta `buscando-rotas` → dashboard de domínios sub-conta.

## 5. gerindo-expedicao + fat-skill vs atômica (resposta à observação)

**Veredito dos agentes: a "gordura" é ACEITÁVEL/correta. NÃO fatiar.**

`gerindo-expedicao` = **7 tools-CLI de domínio + 1 library** (`resolver_entidades.py`) — não um monolito de 8 ferramentas. Os 7 scripts importam a library (grep confirmou). É uma *fat-skill* deliberada = **1 skill = 1 domínio logístico pré-faturamento**, contrastando com **1 skill = 1 átomo** do estoque-odoo. Os dois padrões são legítimos:

- **Fat-skill** (gerindo-expedicao, operando-ssw): gatilho do usuário é por DOMÍNIO ("tem pedido?", "quanto de palmito?", "emite CT-e"). Fatiar explodiria o trigger-space com gatilhos quase-sinônimos → PIOR triggering. Maioria READ + 1 WRITE controlado → risco baixo.
- **Atômica** (estoque-odoo): WRITE perigoso de ERP que exige composição programática + guards + dry-run + idempotência por átomo. Atomicidade = SEGURANÇA.

Problemas reais de gerindo-expedicao (não a gordura):
1. Library `resolver_entidades.py` divergiu da skill canônica `resolvendo-entidades` (item 2.1).
2. `resolvendo-entidades` SKILL.md = 596L (>500).
3. `visao-produto` importa a library via `sys.path` hardcoded sem documentar (quebra silenciosa).

`operando-ssw` (22 scripts) = saudável; só os 3 órfãos a remover.

## 6. Recomendações priorizadas

**P0 (corrigir já — alto valor, baixo risco):**
- Corrigir bug de classificação de estoque em `consultando-estoque-loja` (CRÍTICA — contagens erradas em prod).
- Corrigir `consultando-sentry` (remover/substituir os 2 MCP tools inexistentes no workflow).
- Atualizar status em `acompanhando-pedido-compra-assai` (3 status mortos).
- Decidir SoT de resolução de entidades: extrair para módulo único em `app/` que GE e `resolvendo-entidades` importam (mede o drift `BLOB+AND` primeiro).

**P1:**
- Cobertura de teste nas 2 skills WRITE financeiras sem testes (`conciliando-transferencias-internas` ALTA) + CT-e em `operando-ssw`.
- Mover `vincular_extrato_fatura_excel.py` p/ `executando-odoo-financeiro`.
- Construir ou remover refs de `registrando-venda` (HORA M3 está em prod sem skill de leitura) e skill de carregamento Assai.
- Reconciliar contagem do ROUTING_SKILLS.md (50 incl. faturando-odoo) + atualizar tool_skill_mapper.py.
- Remover 3 scripts órfãos de `operando-ssw`.

**P2:**
- Renomear 4 substantivos → gerúndio; padronizar sufixo `-hora` simétrico ao `-assai`.
- `faturando-odoo`: mover ANTIPADROES+CHECKLIST p/ references/ (−118L).
- De-duplicar templates de comunicação PCP/Comercial (3 lugares → 1).

**P3:**
- Documentar a POLÍTICA fat-skill vs atômica (parar a confusão arquitetural).
- Limpar hardcodes (postgresId, model IDs, V21, company_ids); corrigir flag duplicada gerindo-agente.
