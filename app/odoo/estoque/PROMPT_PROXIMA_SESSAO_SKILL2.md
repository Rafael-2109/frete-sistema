# PROMPT_PROXIMA_SESSAO_SKILL2 — capinar Skill 2 `transferindo-interno-odoo` + executar transferências reais

> Sessão dedicada a **maturar a Skill 2** (`transferindo-interno-odoo`) a partir de uma demanda real de transferências do Rafael. **A capinagem dos ~13 scripts vivos da Skill 2 deve ser BEM AVALIADA** — cada um pode enriquecer o fluxo de transferência interna com pattern novo (wildcards, planilha, multi-empresa, ROLE-back). Capinagem só vale se preserva todos os patterns únicos.

> Copie tudo entre `---BEGIN---` e `---END---` como prompt inicial. **Antes de qualquer ação, Rafael enviará a relação de transferências necessárias** — não começar capinagem sem isso.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **commits ao fim de v9: bf53ea84 (v7) + 507e5e36 (v7-extras) + 4e30c468 (v8) + 6a73c6fa (v9 Skill 6 orchestrator) + 9fc7e712 (v9 code-review fixes) + 448ea62e (v9 docs PROMPT) sobre `main`@b4f7b24c**). `main` continua VIVO em paralelo — verificar avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## 🎯 OBJETIVO desta sessão

**Capinar a Skill 2 `transferindo-interno-odoo` 🟡 → ✅ MATURADA** a partir de demanda real de transferências do Rafael. Sessão tem 3 fases:

1. **FASE A** (read-only): receber relação de transferências do Rafael + avaliar situação total cross Odoo (saldos reais, lotes existentes, locations, etc.).
2. **FASE B** (capinagem): avaliar QUAIS dos ~13 scripts vivos da Skill 2 merecem capinar para enriquecer o fluxo. Capinar.
3. **FASE C** (execução): executar as transferências da demanda real (canary → sub-piloto → bulk).

**Se não couber em 1 sessão**: dividir. Fase A+B na 1ª sessão (capinar bem), Fase C na 2ª. Rafael avisou que pode executar depois. **Não pular avaliação para acelerar capinagem** — qualidade > velocidade (regra inviolável CLAUDE.md).

## 📋 PROTOCOLO DA SESSÃO

### 🔵 FASE A — Receber demanda + avaliar situação total (PRIMEIRO PASSO)

**ANTES de qualquer outra coisa**: aguardar Rafael enviar a relação de transferências (planilha, lista, descrição livre). Pode incluir:
- De → Para (lote, location, company)
- Quantidades
- Cods de produto
- Justificativa / contexto operacional

**Após receber a relação**:

1. **Mapear estrutura da demanda** (criar arquivo `/tmp/demanda_transferencias_<data>.md`):
   - Quantos cods envolvidos
   - Quantas linhas / transferências distintas
   - Quais empresas (FB cid=1 / CD cid=4 / LF cid=3)
   - Quais tipos: lote→lote (modo A), location→location (modo B), MIGRAÇÃO↔Indisponível (modo C), wildcard sub-locais (modo "planilha pasta22/D013")
   - Há dependências entre linhas? (lote destino precisa ser criado antes?)
   - Há ajustes positivos puros embutidos (sem doador)?

2. **Avaliar situação Odoo cross-referenciada** (Skill 9 `consultando-quant-odoo`):
   ```python
   # Para cada cod da demanda, listar quants ao vivo
   python .claude/skills/consultando-quant-odoo/scripts/consultar_quants.py \
       --modo quants --cods "COD1,COD2,..." --empresas "FB,CD" --com-lote --quiet
   ```
   - Saldo atual nos lotes origem
   - Lotes destino existem? Em qual location?
   - Há reservas ativas bloqueando? (regra inviolável v7 #21 — PRE-CHECK reserva ANTES Skill 2)

3. **Decidir ESTRATÉGIA**:
   - Demanda simples (1-poucos cods, sem MIGRAÇÃO bloqueada): aplicar Skill 2 já existente (modo A/B/C atuais) sem capinar nada
   - Demanda média (10+ cods, padrão repetível): capinar 1-2 orquestradores que cobrem o padrão
   - Demanda complexa (planilha 100+ linhas, wildcards, multi-empresa): avaliar capinar `transferir_lote.py` (gold) + `ajuste_fb_cd_indisponivel.py` (D013) + `transferir_local_pasta22.py`

### 🟢 FASE B — Avaliar e capinar scripts vivos da Skill 2

**Inventário dos ~13 scripts vivos da Skill 2** (ler INTEGRAL cada antes de decidir capinar):

| # | Script | Padrão único | Tamanho | Prioridade capinagem |
|---|--------|-------------|---------|---------------------|
| 1 | **`transferir_lote.py`** | **GOLD genérico** — planilha `diff_qtd` net-zero por filial/produto; PROMOVER | a ler | ALTA (gold) |
| 2 | `13_transferencia_migracao_fb.py` | MIGRAÇÃO→lote canônico (lista de cods) | a ler | MÉDIA |
| 3 | `15_transferencia_para_migracao.py` | Semântica D010: `diff>0 → lote→MIGRAÇÃO` (4.888 linhas histórico) | a ler | ALTA (D010) |
| 4 | `15r_transferencia_reversa.py` | Semântica D010 INVERSA: `diff>0 → MIGRAÇÃO→lote` | a ler | ALTA (D010) |
| 5 | `15_transferir_preprod_para_estoque_fb.py` | Pré-Prod→Estoque (já argparse) | a ler | MÉDIA (fundir c/ 17) |
| 6 | `17_transferir_preprod_lf_para_estoque.py` | idem LF | a ler | MÉDIA (fundir c/ 15) |
| 7 | **`ajuste_fb_cd_indisponivel.py`** | **D013**: De-Local/De-Lote→Para + WILDCARD sub-locais; checkpoint incremental | a ler | ALTA (D013 wildcard) |
| 8 | **`transferir_local_pasta22.py`** | **De/Para LOCAL+LOTE Pasta22**, multi-empresa, wildcard, 3 premissas explícitas | a ler | ALTA (multi-empresa) |
| 9 | `transferir_indisp_para_estoque_p15_cd.py` | Indisponível→Estoque/P-15/05 CD; guard quant_id; hard-fail saldo insuficiente | a ler | MÉDIA |
| 10 | `substituir_lote_205030410_fb.py` | unreserve+transfer+reassign (cross-skill 2.4+2+2.4) | a ler | BAIXA (cross-skill) |
| 11 | `consolidar_lote_104000015_sal_fb.py` | consolidar 2 grafias literais de lote ESPECÍFICAS | a ler | BAIXA (caso pontual) |
| 12 | `recuperar_aumentos_falhos.py` | **GOTCHA G031 origem**: `lot_id` empresa errada quebra AUMENTO | a ler | MÉDIA (gotcha) |
| 13 | `mover_migracao_para_indisponivel.py` | 3 filiais (B+A), quants com reserva pulam → CSV (liga a Skill 2.4) | a ler | MÉDIA |
| 14 | `relotar_migracao_para_lotes_fb.py` | MIGRAÇÃO→lotes reais + envio Estoque (inv-adjust 2 passos) | a ler | BAIXA (refazer via modo C) |
| 15 | `transferir_fluxo_c.py` | **FLUXO C**: 2 NFs canceladas → FB/Indisponível/MIGRAÇÃO | a ler | BAIXA (caso específico) |
| 16 | `executar_fluxo_b_vivas.py` | **fluxo composto cross-skill**: cancel invoice + return picking + transfer (Skill 7+5+2) | a ler | NÃO CAPINAR (cross-skill, espera Skill 7/5) |

**REGRAS DE AVALIAÇÃO (não negociáveis)**:

1. **Ler INTEGRAL** cada script candidato a capinar (não inferir do MAPA). Demanda + script real revelam o que vai virar átomo / parâmetro novo / folha de fluxo.
2. **Critério para capinar AGORA** (1 script vira capinagem):
   - Padrão repete na demanda do Rafael (≥ 2 linhas usando esse padrão)
   - OU é gold genérico que cobre 80% dos casos restantes (ex.: `transferir_lote.py`)
   - OU codifica gotcha único que ninguém mais codifica (ex.: G031 em `recuperar_aumentos_falhos.py`)
3. **Critério para NÃO capinar** (preserva ad-hoc VIVO):
   - Caso ESPECÍFICO de 1 cod só (ex.: `consolidar_lote_104000015_sal_fb`)
   - Cross-skill cobrindo skills NÃO IMPLEMENTADAS (ex.: `executar_fluxo_b_vivas` espera Skill 7+5)
   - Padrão não aparece na demanda atual (deferir para sessão futura)
4. **Pattern fluxos>>skills** (inviolável CLAUDE.md §4): caso novo = folha de fluxo, NÃO skill nova. Se o padrão da demanda cabe em modo A/B/C atual da Skill 2 + nova folha, fazer isso.

**Como capinar bem** (lições v6+v9):
- Service permanece puro (algoritmo) + helpers top-level no MESMO arquivo
- Composição via Skills 1+2 com `delta_esperado` propagado
- CLI thin wrapper (`--modo` exclusive, `--dry-run` default, exit codes 0/1/2/4)
- Output JSON estruturado (regra v7)
- Contadores com semântica distinta (real/dry/anomalia — CR-BUG-2 v9 Decisão 7)
- Auditoria via `OperacaoOdooAuditoria.registrar` (lazy import)
- Pytest baseline ANTES + DEPOIS (regra inviolável #13)
- Pyright sem novos warnings funcionais

### 🟡 FASE C — Executar transferências da demanda (canary → bulk)

**Pre-cond**: FASE A+B completas. Plano dry-run gerado para TODA a demanda.

**Sequência obrigatória**:
1. **Canary** (1 transferência): `--dry-run` + revisar JSON + `--confirmar` + verificar Odoo direto
2. **Sub-piloto** (5-10 transferências): mesmo padrão, valida lotes em batch
3. **Bulk** (todas restantes): com `--max-workers 5` se Skill 2 suportar paralelização (verificar)
4. **Auditoria pós-execução**: Skill 9 `consultando-quant-odoo --modo quants` cross-ref com plano

**Critério de PARADA imediata** (não continuar bulk):
- ≥ 1 FALHA no canary
- ≥ 2 FALHAS no sub-piloto
- Qualquer FALHA_AUMENTO (estado parcial — origem reduzida, destino não creditado)
- Reserved bloqueando (fluxo 2.6 — pre-check reserva inviolável v7)

**Se não couber em 1 sessão**:
- Fase C migra para sessão posterior
- Rafael executa via CLI sozinho (já capinada) OU spawnar `gestor-estoque-odoo` em sessão futura
- Documentar no log o que foi capinado vs o que falta executar

## ⚠️ REGRAS INVIOLÁVEIS (TODAS herdadas v7+v8+v9 + 3 NOVAS v9 do CR)

1-27. (todas as 27 anteriores — ver `app/odoo/estoque/PROMPT_PROXIMA_SESSAO.md`)

**Decisões-chave v9 (CR — Decisão 6/7/8) — APLICAR em capinagem da Skill 2**:

28. **(v9 Decisão 6) Dry-run NUNCA simula no quant errado para parecer OK** — se incerteza (lote não existe), retornar status específico (ex.: `DRY_RUN_OK_LOTE_A_CRIAR`), nunca `lot_id=None` "como se fosse igual".

29. **(v9 Decisão 7) Contadores com semântica DISTINTA**: `*_ok` reais, `*_dry` dry-run, `produtos_sem_ajuste` anomalia. NUNCA colapsar "tudo zero" em `produtos_ok` (semanticamente engana).

30. **(v9 Decisão 8) Constantes single-source**: cruzam módulos = UM lugar só. Importar via `from`, nunca duplicar. Use gerador programático a partir da fonte.

## LEITURAS OBRIGATÓRIAS ANTES DE AGIR (ordem)

1. **APÓS receber demanda do Rafael**: este arquivo (Fase A).
2. `app/odoo/estoque/CLAUDE.md` — constituição.
3. `app/odoo/estoque/scripts/transfer.py` (1073 LOC) — service atual da Skill 2 (modo A/B/C v2 com guards). **LER INTEGRAL**.
4. `.claude/skills/transferindo-interno-odoo/SKILL.md` — contrato atual + receitas + armadilhas.
5. `app/odoo/estoque/fluxos/2.2-realocar-saldo.md` — folha atual.
6. `app/odoo/estoque/fluxos/2.6-tratar-reserva-bloqueia-transferencia.md` — pre-cond Skill 2 (5 caminhos).
7. `app/odoo/estoque/VALIDACAO_FINAL_SESSAO.md` §13+§14+§15 (sessões v7+v8+v9 — pattern + pre-mortem).
8. `.claude/agents/gestor-estoque-odoo.md` — 30 invariantes (5 originais + 22 v7-v8-v9 + 3 novas Decisões 6/7/8).
9. Memórias-chave (`mcp__memory__view_memories`):
   - `[[skill2_transfer_interno_pattern]]` — pattern atual Skill 2 (modo A/B/C, gotchas G021/G022/G027/G031)
   - `[[skill6_planejar_pre_etapa_pattern]]` — pattern orchestrator C3 macro v9 (reaproveitável)
   - `[[fluxo_2_6_pattern]]` — 5 caminhos pre-transfer
   - `[[gotcha_lote_multiempresa_company_filter]]` — G021 filter company_id
   - `[[gotcha_g030_quant_id_store_false]]` — G030 cross-ref tupla
   - `[[regra_direcao_migracao_diff_qtd]]` — D010 inviolável
   - `[[feedback_ajuste_planilha_wildcard]]` — D013 wildcard
   - `[[feedback_parametrizar_scripts_existentes]]` — generalizar vs criar novo
   - `[[feedback_skills_demanda_driven]]` — skills nascem de demanda
   - `[[arquitetura_orquestrador_odoo]]` — princípio fluxos>>skills

## ARQUITETURA — árvore de decisão (Skill 2 destaque)

```
2  Estoque (SEM NF)
   2.1 ajuste de saldo (1 quant)              → Skill 1 ✅ MATURADA
   2.2 realocar saldo (lote↔lote / loc↔loc / MIGRA↔Indisp)
                                               → Skill 2 🟡 (ESTA SESSÃO — maturar)
       FOLHAS atuais:
         2.2.A lote→lote mesma loc            (atual)
         2.2.B loc→loc mesmo lote              (atual)
         2.2.C MIGRAÇÃO↔Indisponível atomico   (v4)
       FOLHAS NOVAS POSSÍVEIS (se demanda + capinagem indicar):
         2.2.D010 planilha diff_qtd net-zero  (TBD — capinar transferir_lote?)
         2.2.D013 wildcard sub-locais         (TBD — capinar ajuste_fb_cd_indisponivel?)
         2.2.Pasta22 multi-empresa            (TBD — capinar transferir_local_pasta22?)
         2.2.Pre-Prod→Estoque                 (TBD — fundir 15+17?)
         2.2.G031-recovery                    (TBD — recuperar_aumentos_falhos?)
   2.3 transferir saldo entre CÓDIGOS        → ⬜ (não nesta sessão)
   2.4 reservas/cirurgia ML/unreserve         → Skill 2.4 🟡 ✅
   2.5 cancelar/validar/devolver picking      → Skill 5 🟡 ✅
   2.6 TRATAR reserva ATIVA pré-transferência (PRE-COND Skill 2)
                                               → fluxo 2.6 (5 caminhos)
   2.9 CONSULTA AO VIVO (quants/MLs/pickings) → Skill 9 🟡 ✅
```

## CHECKLIST DA SESSÃO (Skill 2 — capinar + executar)

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main: git fetch origin main && git log --oneline 9fc7e712..origin/main
[ ] Se main avançou: rebase incremental
[ ] Pytest baseline: 258 verdes esperado (rodar full suite estoque)

FASE A (read-only — após Rafael enviar relação):
[ ] AGUARDAR Rafael enviar relação de transferências
[ ] Criar /tmp/demanda_transferencias_<data>.md mapeando estrutura
[ ] Avaliar Odoo cross-referenciado (Skill 9 modo quants + pickings)
[ ] Decidir ESTRATÉGIA (simples / média / complexa)
[ ] AskUserQuestion: confirmar estratégia + escopo + dividir sessão (sim/não)

FASE B (capinagem — opcional se demanda simples):
[ ] Ler INTEGRAL os scripts vivos S2 candidatos (1-3 baseado em demanda)
[ ] Decidir quais capinar (critérios: padrão repete / gold genérico / gotcha único)
[ ] C1: mineração dos escolhidos
[ ] C2: extender transfer.py + helpers + 5-10 testes pytest novos
[ ] C3-C5: contrato em SKILL.md + CLI thin wrapper
[ ] C6: smokes dry-run vs Odoo PROD
[ ] C7-C10: cross-refs + folha de fluxo (2.2.D010/D013/etc) + scripts SUPERADOS + memória

FASE C (executar transferências — se houver tempo):
[ ] Canary 1 transferência (--dry-run + revisar + --confirmar + verificar Odoo)
[ ] Sub-piloto 5-10 transferências
[ ] Bulk restantes (com --max-workers 5 se suportado)
[ ] Auditoria pós-execução (Skill 9 cross-ref com plano)

FECHAMENTO:
[ ] Code-review paralelo (2 reviewers) ao fim
[ ] Atualizar ROADMAP_SKILLS HANDOFF + VALIDACAO §16 + memórias
[ ] Commit consolidado
[ ] **DECIDIR PROXIMO PROMPT** (informar Rafael EXPLICITAMENTE):
    - Se FASE A+B+C 100% concluidas (capinou + executou TUDO da relacao):
      [ ] Arquivar este arquivo (mover para `_validados/` OU renomear para
          `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_<data>.md`)
      [ ] Atualizar `PROMPT_PROXIMA_SESSAO.md` para v11 incorporando o feito
      [ ] DIZER PARA RAFAEL: "Proxima sessao = abrir PROMPT_PROXIMA_SESSAO.md (v11)"
    - Se FASE C ficou parcial (executou so X de Y transferencias):
      [ ] Atualizar ESTE arquivo na seção "Pendente para proxima sessao":
          - Quantas transferencias sobraram
          - Quais cods especificos
          - Estado atual (estatus dos ajustes no banco local)
      [ ] DIZER PARA RAFAEL: "Proxima sessao = abrir PROMPT_PROXIMA_SESSAO_SKILL2.md
          (atualizado) para continuar FASE C"
    - Se FASE B + C nao iniciaram (so Fase A — demanda recebida mas capinagem
      decidida para sessao futura):
      [ ] Atualizar este arquivo com estrategia confirmada
      [ ] DIZER PARA RAFAEL: "Proxima sessao = continuar SKILL2.md (Fase B+C)"
```

## NÃO-FAZER (red flags Skill 2 + v9)

- ❌ Começar capinagem ANTES de receber relação do Rafael — premissa inviolada
- ❌ Capinar TODOS os 13 scripts S2 vivos "para fechar a Skill 2" — viola demanda-driven (regra 4 inviolável)
- ❌ Capinar `executar_fluxo_b_vivas` antes de Skills 7+5 prontas (cross-skill inviável agora)
- ❌ Capinar caso específico (1 cod) — preservar ad-hoc VIVO
- ❌ Adicionar `--lot-id-origem`/`--lot-id-destino` à CLI atual de Skill 2 SEM caso real (especulativo)
- ❌ Skip `--dry-run` antes do real (regra inviolável 1)
- ❌ Skip PRE-CHECK reserva via Skill 9 antes de Skill 2 (regra inviolável 21 v7)
- ❌ Cancelar picking inteiro sem listar TODAS as MLs (regra inviolável 26 v8)
- ❌ Compor átomos sem propagar `delta_esperado` (regra inviolável 11)
- ❌ Dry-run que simula no quant errado para parecer OK (regra v9 Decisão 6)
- ❌ Contadores que colapsam dry-run em `produtos_ok` (regra v9 Decisão 7)
- ❌ Duplicar constantes que cruzam módulos (regra v9 Decisão 8)

---END---

## NOTAS PARA RAFAEL (não fazem parte do prompt)

### Sobre a demanda

- **Não envie a relação para mim agora** — envie no início da próxima sessão. O agente vai aguardar antes de qualquer ação.
- **Formato livre** — planilha, lista, descrição. O agente vai mapear a estrutura.
- **Se cobrir múltiplos padrões** (alguns lote→lote + alguns wildcard + alguns multi-empresa), o agente vai propor capinar 2-3 scripts S2 que cubram esses padrões + executar.

### Sobre o tempo

- ~13 scripts S2 vivos, mas **NÃO precisa capinar todos**. Só os que enriquecem o fluxo da demanda.
- Sessão pode dividir em 2: capinagem na 1ª, execução real na 2ª. Se a demanda for grande, melhor dividir.
- Canary OBRIGATÓRIO antes de bulk — não vai pular mesmo com pressa (regra v9 #30).

### Quando reabrir

Após receber resposta do agente (estratégia + estimativa de capinagem + tempo), você decide:
- "Capinar X scripts agora + executar tudo nesta sessão" (se demanda pequena)
- "Capinar X scripts agora + execução na próxima sessão" (se demanda grande mas patterns claros)
- "Cancelar capinagem, executar com Skill 2 atual" (se demanda cabe em modo A/B/C existente)
