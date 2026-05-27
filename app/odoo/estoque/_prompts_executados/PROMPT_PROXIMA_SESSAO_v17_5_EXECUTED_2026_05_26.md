Continue o trabalho do orquestrador-Odoo. Worktree: /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo (branch feat/estoque-odoo). main continua VIVO em paralelo. Verificar se avancou e considerar rebase ANTES de iniciar.

## Setup OBRIGATORIO (worktree sem .env)

    cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
    source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
    set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
    git fetch origin main && git log --oneline HEAD..origin/main

## CONTEXTO CRITICO — v17 fez PIPELINE A-F LIVE mas com DESVIO ARQUITETURAL

Sessao v17 (commit e0a29f21 +3069/-379) entregou pipeline A-F funcional + 11 fixes pos-3 reviewers paralelos. **MAS** Rafael detectou que ETAPA E violou a constituicao §6:
- Constituicao: `faturando-odoo` = SO SAIDA (NF->SEFAZ); `escriturando-odoo` = SO ENTRADA (escritura)
- v17 colocou logica RecebimentoLf inline no orchestrator Skill 8 (Fluxo>>Skills violado)
- ETAPA E deveria invocar atomo da **Skill 7 `escriturando-odoo`** (a ser criada)

**Decisao Rafael 2026-05-26**: v17.5 ISOLADA — REVERT ETAPA E + criar Skill 7 antes de prosseguir.

## PRIORIDADE v17.5 — REVERT ETAPA E + criar Skill 7 escriturando-odoo + ETAPA F expandido

### Sub-objetivo S1: REVERT executar_etapa_e (Task #15)

Reverter `executar_etapa_e` no `app/odoo/estoque/orchestrators/faturamento_pipeline.py`:
- Manter a interface publica + constants imports (ACOES_ENTRADA_FB, ACAO_PARA_CFOP_ENTRADA)
- Logica de criar RecebimentoLf + agg lotes + invoke service externo: MOVIDA para Skill 7
- Orchestrator passa a invocar atomo Skill 7 por invoice

Antes de remover, mover testes existentes para nao perder cobertura:
- 4 testes ETAPA E v17 atuais + 1 pos-fix HIGH-3 = 5 testes
- Migrar para `tests/odoo/services/test_escrituracao_lf_service.py` (testar atomo Skill 7 diretamente)
- Adicionar testes novos para `executar_etapa_e` apos-revert: validar invocacao do atomo Skill 7

### Sub-objetivo S2: Criar Skill 7 `escriturando-odoo` (Task #16)

Localizacao: `app/odoo/estoque/scripts/escrituracao.py` (NOVO).

Classe principal: `EscrituracaoLfService` com atomo:

```python
def criar_recebimento_lf_orchestrado(
    self,
    *,
    invoice_id: int,
    ajustes: List[AjusteEstoqueInventario],  # ou lista de dicts pre-snapshot
    ciclo: str,
    usuario: str,
    dry_run: bool = True,
    cnpj_emitente: str = '18.467.441/0001-63',  # LF default; aceitar arg
    company_id_recebedor: int = 1,  # FB default
) -> Dict[str, Any]:
    """ATOMO Skill 7: cria RecebimentoLf + agg lotes + invoke service externo.

    Encapsula:
    - Idempotencia G-RECLF-3 via UK odoo_lf_invoice_id (UK aplicada v17)
    - HIGH-3 status='processando' RETOMA via service externo
    - HIGH-4 svc instanciado fresh (nao reusa)
    - HIGH-5 produto_tracking via fetch batch (anti-D-OPS-5)
    - G-RECLF-2 transfer_status='erro' aceito como parcial OK
    - D17 ACAO_PARA_CFOP_ENTRADA 5xxx->1xxx
    - Re-fetch ajustes via safe_session_get apos commits internos do service
    - commit_resilient antes/dentro do loop

    Retorna:
      {
        'status': CRIADO | IDEMPOTENT_PROCESSADO | RETOMADO | PARCIAL | FALHA,
        'rec_id': int | None,
        'odoo_invoice_id_fb': int | None,  # PO/Picking/Invoice FB
        'transfer_status': str | None,
        'tempo_ms': int,
      }
    """
```

SKILL.md em `.claude/skills/escriturando-odoo/SKILL.md`:
- Contrato obrigatorio (objeto: `recebimento_lf` + `account.move` no destino; input/output/pre/pos/gotchas-invariante/modos)
- Receitas:
  1. Criar RecLf orchestrado a partir de NF SEFAZ-OK (1 invoice)
  2. Retry FASE 6+7 (transfer FB->CD) via `processar_transfer_only` (delegado direto ao service externo)
  3. Cancelar RecLf orfao (idempotencia falha)
- Trade-offs: SEQUENCIAL por design (decisao 10.7); G-RECLF-1 50-100h/onda 100 aceito por idempotencia
- Cross-refs: subagente gestor-estoque-odoo + ROUTING_SKILLS + tool_skill_mapper

Pytest: 5+ verdes em `tests/odoo/services/test_escrituracao_lf_service.py`:
- dry-run com 1 invoice planejado
- real-run sucesso (mock svc externo)
- idempotencia status='processado' skip
- retomar status='processando'
- produto_tracking='none' D-OPS-5 fix
- G-RECLF-2 parcial (transfer_status='erro')

### Sub-objetivo S3: ETAPA E reescrita delegando Skill 7 (Task #17 part A)

`executar_etapa_e` pos-revert chama atomo Skill 7 por invoice:

```python
def executar_etapa_e(self, *, ciclo, company_origem_id, dry_run, usuario, cod_produto, ...):
    from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService

    # Filtro identico (ACOES_ENTRADA_FB + F5e_SEFAZ_OK)
    ajustes = _carregar_ajustes(...)
    ajustes_entrada_fb = [a for a in ajustes if a.acao_decidida in ACOES_ENTRADA_FB and a.chave_nfe]

    # Agrupa por invoice
    ajustes_por_invoice = defaultdict(list)
    for a in ajustes_entrada_fb:
        ajustes_por_invoice[a.invoice_id_odoo].append(a)

    if dry_run:
        return {...planejamento...}

    # G016 commit pre-loop
    if not _commit_resilient(): return {..FALHA_COMMIT..}

    escrituracao_svc = EscrituracaoLfService(odoo=self.odoo)  # ou injetado

    for invoice_id, ajs in ajustes_por_invoice.items():
        # DELEGA atomo Skill 7
        resultado = escrituracao_svc.criar_recebimento_lf_orchestrado(
            invoice_id=invoice_id,
            ajustes=ajs,
            ciclo=ciclo,
            usuario=usuario,
            dry_run=False,  # ja' validado em dry-run acima
        )
        # Mapear status para contadores
        ...
```

### Sub-objetivo S4: ETAPA F expandida para outras direcoes FB->X (Task #17 part B)

Audit Odoo 2026-05-26 descobriu **picking_types e locations**:

| Direcao | LOCATION origem | LOCATION destino | PICKING_TYPE | Hist. PROD | Action |
|---------|----------------|------------------|--------------|------------|--------|
| INDUSTRIALIZACAO_FB_LF | 26489 (Em Trans. Industr.) | 42 (LF/Estoque) | **19** (LF Recebimento) | ✅ 317306, 317316, 320476, 320467 (4 pickings PROD) | MANTER ID 19 |
| DEV_FB_LF | 26489 (Em Trans. Industr.) | 42 (LF/Estoque) | **64** (LF/RECEB/IND) ou **19** | INVESTIGAR | Buscar account.move com partner=LF + l10n_br_cfop_codigo=1949 |
| TRANSFERIR_FB_CD | 6 (Em Trans. Filiais) | 32 (CD/Estoque) | **50** (CD/IN/INTER) — 2 historicos `NACOM/CD/IN/INTER/00001-00002` | 🟡 historico nao-INV | Pre-validar caso real antes de habilitar |

Atualizar `app/odoo/constants/picking_types.py`:

```python
ACOES_ENTRADA_DESTINO_MANUAL: FrozenSet[str] = frozenset({
    'INDUSTRIALIZACAO_FB_LF',   # FB->LF — validado (4 pickings PROD)
    'DEV_FB_LF',                # FB->LF — habilitado v17.5 apos validacao
    'TRANSFERIR_FB_CD',         # FB->CD — habilitado v17.5
})

PICKING_TYPE_ENTRADA_DESTINO_MANUAL: Dict[int, int] = {
    5: 19,   # LF: Recebimento
    4: 50,   # CD: Recebimentos Entre Filiais
}

# NOVO v17.5: location_origem varia por direcao
# (INDUSTR/DEV_FB_LF usam 26489; TRANSF_FB_CD usa 6)
LOCATION_ORIGEM_POR_DIRECAO: Dict[str, int] = {
    'INDUSTRIALIZACAO_FB_LF': 26489,  # Em Trans. Industr.
    'DEV_FB_LF':              26489,  # Em Trans. Industr. (ou outro — confirmar)
    'TRANSFERIR_FB_CD':       6,      # Em Trans. Filiais
}
```

`executar_etapa_f` adaptado para usar `LOCATION_ORIGEM_POR_DIRECAO[acao]` em vez de `LOCATION_ORIGEM_ENTRADA_INDUSTR` hardcoded. Atomo Skill 5 `criar_picking_entrada_destino_manual` ja aceita location_origem_id como arg (sem mudancas no atomo).

**CRITICO v17.5**: ANTES de habilitar DEV_FB_LF + TRANSFERIR_FB_CD, validar via Odoo XML-RPC:
- Buscar 1 NF historica de cada direcao
- Conferir CFOP da invoice (esperado: PERDA_LF_FB=5903, DEV_LF_FB=5949, TRANSFERIR_CD_FB=5152, INDUSTR_FB_LF=5124 saida → entrada 1124?)
- Conferir picking de entrada manual correspondente (se existir) — picking_type, location_origem/dest, partner_id
- Documentar IDs validados em `app/odoo/constants/picking_types.py` com referencias

### Sub-objetivo S5: Docs + commit v17.5 (Task #18)

- CLAUDE.md estoque §6 catalogo (Skill 7 LIVE; status pipeline mudou)
- ROADMAP HANDOFF v17.5 (entry NOVA acima da v17)
- PLANEJAMENTO §0 (status + decisoes ABERTAS atualizadas) + §7 (C24 NOVO criar Skill 7 + atualizar C12) + §12 trilha v17.5
- Memoria `skill7_escriturando_pattern.md` (NOVA — pattern criacao Skill 7)
- Commit consolidado v17.5

## INVESTIGACOES PENDENTES v17.5 (executar ANTES de implementar S4)

1. **DEV_FB_LF picking_type**: buscar pickings done com:
   - partner_id=35 (NACOM GOYA - FB) ou partner em LF
   - location_dest=42 (LF/Estoque)
   - origin LIKE '%RNA%' ou '%DEV%' ou similar
   - cross-referencing com l10n_br_cfop_codigo da invoice
   
2. **TRANSFERIR_FB_CD picking_type validacao**:
   - Os 2 pickings PT 50 (NACOM/CD/IN/INTER/00001-00002) tem origin=False. NAO foram criados via INV-INVENTARIO_2026_05.
   - Verificar se essas entradas tem invoice associada (account.move) com CFOP 1152
   - Confirmar que partner_id=34 (NACOM GOYA - CD) eh adequado

3. **CFOP de entrada por direcao**: confirmar ACAO_PARA_CFOP_ENTRADA atual:
   ```
   PERDA_LF_FB:      '1903',  # entrada retorno N. Aplicado (saida LF 5903)
   TRANSFERIR_CD_FB: '1152',  # entrada transferencia entre filiais (saida CD 5152)
   DEV_LF_FB:        '1949',  # entrada devolucao industrializacao (saida LF 5949)
   DEV_CD_LF:        '1949',  # entrada devolucao industrializacao (saida CD 5949)
   ```
   Adicionar entradas para FB->X (que sao da ETAPA F, nao E):
   ```
   INDUSTRIALIZACAO_FB_LF: '1124'?  # entrada industrializacao (saida FB 5124)
   DEV_FB_LF:              '1949'?  # entrada devolucao
   TRANSFERIR_FB_CD:       '1152'?  # entrada transferencia
   ```

## LEITURAS OBRIGATORIAS (ordem)

1. app/odoo/estoque/CLAUDE.md (constituicao §3 Fluxo>>Skills + §6 catalogo + §7 distincao Skill 8 saida vs Skill 7 entrada)
2. app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md (regra inviolavel 0):
   - §0 cabecalho (status v17)
   - §10.6 atomos Skill 5 (pattern delegacao)
   - §12 trilha v17 INTEIRA (entender o que foi feito e o desvio detectado)
3. ROADMAP_SKILLS HANDOFF v17 (esta sessao terminou)
4. Memoria [[skill8-pipeline-completo-v17]] (status v17 com 11 fixes)
5. app/odoo/estoque/orchestrators/faturamento_pipeline.py (linhas executar_etapa_e atuais — a refatorar)
6. app/recebimento/services/recebimento_lf_odoo_service.py header (interface processar_recebimento — NAO MEXER)
7. app/odoo/constants/picking_types.py (expandir conforme audit v17.5)

## CHECKLIST v17.5

[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v17 (commit e0a29f21)
[ ] Pytest baseline: 502 verdes esperado
[ ] Investigacoes Odoo PROD (1-3 acima) — IDs + CFOPs descobertos
[ ] AskUserQuestion confirmar IDs descobertos + escopo S1-S5
[ ] S1 REVERT executar_etapa_e + migrar 5 testes
[ ] S2 Criar Skill 7 escriturando-odoo (service + SKILL.md + 5+ pytest)
[ ] S3 ETAPA E delega atomo Skill 7
[ ] S4 ETAPA F expandido (constants + executar_etapa_f sem hardcode)
[ ] Pytest baseline pos-v17.5: >=510 verdes esperado
[ ] Smokes dry-run PROD: ETAPA E via Skill 7 + ETAPA F 3 direcoes
[ ] >=2 code-reviewers paralelos (Skill 7 architecture + ETAPA F expansion)
[ ] S5 Atualizar docs + commit v17.5
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v18 (recovery + SKILL.md Skill 8 + canary)

## REGRAS INVIOLAVEIS NOVAS v17.5

94. (v17.5 ARQ-1) `faturando-odoo` (Skill 8) = SO SAIDA (NF->SEFAZ). NUNCA inclui logica de criar RecebimentoLf ou escriturar entrada. Quem une saida (D) + entrada (E) e' o FLUXO L3.

95. (v17.5 ARQ-2) `escriturando-odoo` (Skill 7) = SO ENTRADA (RecLf + DFe->PO->Picking->Invoice no destino). Encapsula tudo que era inline na ETAPA E do orchestrator pre-v17.5.

96. (v17.5 LOC-1) `LOCATION_ORIGEM_ENTRADA_INDUSTR` (26489) substituida por `LOCATION_ORIGEM_POR_DIRECAO` dict (varia por acao: INDUSTR/DEV_FB_LF=26489; TRANSF_FB_CD=6).

97. (v17.5 PT-1) `PICKING_TYPE_ENTRADA_DESTINO_MANUAL` expandido para CD=50 (TRANSFERIR_FB_CD). DEV_FB_LF picking_type a CONFIRMAR pre-S4.

## NAO-FAZER (red flags v17.5)

X Implementar Skill 7 SEM criar SKILL.md primeiro (skill nasce do contrato, nao do codigo)
X Mover logica para escrituracao.py mas manter chamada INLINE no orchestrator (defeita o proposito)
X Adicionar DEV_FB_LF ou TRANSFERIR_FB_CD em ACOES_ENTRADA_DESTINO_MANUAL SEM validar IDs via audit Odoo
X Mexer no RecebimentoLfOdooService (NAO MEXER — 4562 LOC validados PROD)
X Mexer no script 09 (NAO MEXER — regra v14a-ops)
X Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque §6)

## CRONOGRAMA REVISADO (apos v17.5)

v17 (concluida 2026-05-25): pipeline A-F LIVE + 11 fixes | commit e0a29f21
**v17.5 (proxima)**: REVERT ETAPA E + criar Skill 7 + ETAPA F expandido | S1-S5 | Risco Medio
v18: C14 recovery `--resume` (Skill 8) + C15 SKILL.md Skill 8 + C17 smokes | Risco Medio
v19: C18 folhas fluxos (1.1 faturamento completo) + C19 cross-refs + C20 canary REAL PROD | Risco Alto
v20+: C21 bulk REAL PROD + C22 code-review final + C23 commit + arquivar 09_* | Risco Alto

Total restante: 4 sessoes (v17.5 -> v20+).

## ESTADO ATUAL — apos v17 (PIPELINE COMPLETO A-F LIVE)

Ver historico detalhado em `PROMPT_PROXIMA_SESSAO_v17_EXECUTED_2026_05_25.md` (arquivado).

Resumo:
- Pipeline A-F funcional (commit e0a29f21)
- 502 pytest verdes
- 13/24 checkpoints concluidos
- Migration v17 UK aplicada PROD
- **DESVIO DETECTADO**: ETAPA E inline no Skill 8 (deveria ser Skill 7 — corrigir em v17.5)
- ETAPA F V1 STRICT (deveria expandir para outras direcoes — corrigir em v17.5)

## REFERENCIAS RAPIDAS

- Commit v17: e0a29f21
- Baseline pytest: 502 verdes em 14.51s
- UK constraint: `recebimento_lf.uq_recebimento_lf_invoice_id` aplicada PROD 2026-05-25
- Audit Odoo 2026-05-26: PT 19 (LF Receb), PT 64 (LF/RECEB/IND), PT 50 (CD/IN/INTER) descobertos
- Memoria v17: [[skill8-pipeline-completo-v17]]
