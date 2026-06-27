<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-27
-->
# HORA — Handoff da sessão 2026-06-27 (validação em sessão limpa)

> **Papel:** guia para validar/auditar TUDO que foi feito na sessão de 2026-06-27 no módulo HORA — código (main + branch) e operações de dados em produção. Cada item traz **onde está**, **como validar** e **status**.

## Indice

- [Resumo executivo](#resumo-executivo)
- [Como validar (sessão limpa)](#como-validar-sessão-limpa)
- [Frente 1-3 — Código na MAIN](#frente-1-3--código-na-main)
- [Frente 4 — Feature recebimento sem NF (branch)](#frente-4--feature-recebimento-sem-nf-branch-não-finalizada)
- [Frentes 5-8 — Operações em PRODUÇÃO](#frentes-5-8--operações-em-produção-dados-já-executadas--verificadas)
- [Próximos passos](#próximos-passos-ordem-sugerida)

## Resumo executivo

| # | Frente | Onde | Estado | Pendência |
|---|--------|------|--------|-----------|
| 1 | Hotfix: autocomplete de NF por permissão de recebimento | main `fd43416c7` | **em `origin/main`** (deploy via Render) | confirmar deploy |
| 2 | Hotfix: guarda anti-recebimento-duplicado | main `f930dd759` | **em `origin/main`** (deploy via Render) | confirmar deploy |
| 3 | Doc: CLAUDE.md §32 + este handoff | main (commit local) | **commitado, SEM push** | push (opcional) |
| 4 | Feature: recebimento por filial sem NF | branch `worktree-hora-recebimento-sem-nf` | **rebaseada, 353 testes verdes, NÃO finalizada** | decisões A/B + merge/deploy + migration `hora_57` |
| 5 | PROD: NF fake pedido #139 → 42 motos SANTANA | banco prod | **executado + verificado** | reconciliar quando NF real chegar |
| 6 | PROD: NF vazia para recebimento aberto | banco prod | **executado** | reconciliar / limpar |
| 7 | PROD: permissões Isabela → Otavio | banco prod | **executado + verificado** | — |
| 8 | PROD: correção da moto 988 (duplicata → avaria) | banco prod | **executado + verificado** | — |

**Os hotfixes 1-2 JÁ estão em `origin/main`** (pushados nesta data; Render auto-deploya — confirmar). A doc (3) está **local sem push**; a feature na branch (4) e as operações de PROD (5-8, em **dados**) também não foram pushadas.

## Como validar (sessão limpa)

```bash
# Código — branch de feature (353 testes)
cd /home/rafaelnascimento/projetos/frete_sistema/.claude/worktrees/hora-recebimento-sem-nf
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
python -m pytest tests/hora/ -q

# Código — main (hotfixes; 344+ testes)
cd /home/rafaelnascimento/projetos/frete_sistema
python -m pytest tests/hora/ -q
git log --oneline -4            # ver os hotfixes não-pushados (ahead de origin/main)

# Dados de PROD — via MCP Render (read-only) ou psql "$DATABASE_URL_PROD"
#   (postgresId=dpg-d13m38vfte5s738t6p50-a)
```

## Frente 1-3 — Código na MAIN

Os 2 hotfixes desta sessão **já estão em `origin/main`** (pushados; Render auto-deploya). A doc (§32 + handoff) está local sem push. Commits:

- **`fd43416c7`** `fix(hora): autocomplete de NF aceita operador de recebimento` — `routes/autocomplete.py:72`: `/autocomplete/nf-entrada` passou de `nfs/ver` para `require_hora_perm_any(('nfs','ver'),('recebimentos','criar'))`. Resolve "o autocomplete de NF não aparece" para operador de recebimento (ex.: Isabela, user 84).
- **`f930dd759`** `fix(hora): guarda anti-recebimento-duplicado` — `recebimento_service.py`: bloqueio + aviso + pré-filtro automático. Impede conferir um chassi já recebido em outro recebimento. `tests/hora/test_recebimento_anti_duplicata.py` (5).
- **este commit** — `CLAUDE.md §32` documentando os 2 fixes + este handoff.

**Validar:** `pytest tests/hora/test_recebimento_anti_duplicata.py -q` (5 ✓) e `git show fd43416c7 f930dd759`. **Deploy:** os 2 hotfixes já estão em `origin/main` — **confirmar o deploy no Render** (`mcp__render__list_deploys`). Após o deploy, o autocomplete destrava os operadores em prod (hoje eles usam o usuário admin).

## Frente 4 — Feature recebimento sem NF (branch, NÃO finalizada)

**Branch:** `worktree-hora-recebimento-sem-nf` · worktree em `.claude/worktrees/hora-recebimento-sem-nf` · HEAD `b11d7d35f` · **13 commits acima da main** · **backup** em `backup-sem-nf-pre-rebase`.

- **O quê:** receber selecionando só a loja. NF `PROVISORIA` (mantém `nf_id` NOT NULL) com gabarito = snapshot dos pedidos pendentes da filial (`hora_recebimento_esperado`); NF real anexada depois promove `PROVISORIA→REAL` e reprocessa divergências; conferência é SOT.
- **Spec:** `docs/superpowers/specs/2026-06-26-hora-recebimento-sem-nf-design.md` (decisões D1–D9, riscos R1–R4).
- **Plano:** `docs/superpowers/plans/2026-06-26-hora-recebimento-sem-nf.md` (10 tasks TDD).
- **Migration:** `scripts/migrations/hora_57_recebimento_sem_nf.{sql,py}` — renomeada de `hora_55` (colisão pós-rebase com `hora_55_perfis`). **Rodada no banco LOCAL; NÃO em prod.**
- **Validar:** `pytest tests/hora/` na worktree = **353 ✓** (inclui `test_recebimento_sem_nf` + a guarda anti-duplicata `test_recebimento_anti_duplicata`, provando que coexistem no mesmo `registrar_conferencia_cega`).

### Decisões pendentes (do dono) — bloqueiam a finalização
- **Gap A (in-scope, Medium):** anexar a NF real **não avança o status fiscal do pedido** — a NF provisória nasce sem `pedido_id` (snapshot é multi-pedido), então o `if nf.pedido_id` em `anexar_nf_real_ao_recebimento` é inerte. Efeito 2º: itens reaparecem em snapshots futuros. Resolver = matching NF→pedido por chassi (≈ 1 task).
- **Gap B (Medium, defensável):** anexar a NF real **não gera `MOTO_FALTANDO`** para chassi faturado mas nunca conferido.

### Para finalizar (quando aprovado)
1. Decidir A/B (implementar agora vs follow-up documentado).
2. Merge/PR + deploy → rodar `hora_57` em prod.
3. **Atenção (numeração CLAUDE.md):** a main passou a ter **§32 = hotfixes de recebimento**; a seção da feature no CLAUDE.md da branch também é **§32 (sem-NF)** → ao mergear, **renumerar a sem-NF para §33** (índice + corpo).

## Frentes 5-8 — Operações em PRODUÇÃO (dados; já executadas + verificadas)

> Contexto: inauguração da loja **SANTANA** (id 6) em 2026-06-27, sem NF disponível.
> Scripts em `scratchpad/` (efêmeros): `receber_pedido_139_paliativo.py`, `criar_nf_vazia_santana.py`, `copiar_perms_isabela_otavio.py`, `corrigir_988.py` — todos dry-run por padrão, `--confirmar` para gravar, contra `DATABASE_URL_PROD`.

### 5 — NF fake do pedido #139 (paliativo de recebimento)
Criada `HoraNfEntrada` **id=160** (`FAKE-139`, `parser_usado=MANUAL_FAKE_PALIATIVO`, valor 261.909,80, 42 itens, `loja_destino_id=6`) + recebimento automático **id=120** → **42 motos `RECEBIDA`** na loja 6 (disponíveis para venda).
**Auditar:**
```sql
SELECT id, numero_nf, parser_usado, valor_total, pedido_id FROM hora_nf_entrada WHERE id=160;
SELECT status FROM hora_recebimento WHERE id=120;  -- CONCLUIDO
```
**Pendência:** quando a **NF real** chegar, **NÃO** importar o DANFE pelo fluxo normal (criaria 2ª NF do mesmo pedido) — reconciliar (atualizar a 160 ou apagar e reimportar).

### 6 — NF vazia (recebimento aberto)
Criada `HoraNfEntrada` **id=161** (`VAZIA-SANTANA`, `MANUAL_VAZIA`, 0 itens, `pedido_id=NULL`) para o operador iniciar recebimento aberto pela tela. Efeito conhecido: cada moto conferida vira `CHASSI_EXTRA` (sem gabarito), mas entra em estoque (`CONFERIDA`).
**Auditar:** `SELECT id, numero_nf, parser_usado FROM hora_nf_entrada WHERE id=161;`

### 7 — Permissões Isabela → Otavio
Copiados **18 pares** de `hora_user_permissao` de **Isabela (id 84)** para **Otávio (id 92)** — ambos `vendedor`, `loja_hora_id=NULL`. Aditivo (Otávio tinha 0). Perfil/escopo não tocados.
**Auditar:**
```sql
SELECT count(*) FROM hora_user_permissao WHERE user_id=92 AND (pode_ver OR pode_criar OR pode_editar);  -- 18
```

### 8 — Correção da moto 988 (duplicata → avaria)
A `92WMCX113SM000988` (X11-12) fora conferida nos recebimentos 120 e 121 (a 2ª só para marcar avaria) → não era moto perdida, era **a mesma contada 2×**. Correção: conf **835** (rec 121) marcada `substituida=True` (anulada, histórico preservado) + avaria registrada no módulo Avarias (**`hora_avaria` id=1**, status ABERTA, evento `AVARIADA`). Rec 121 ficou com **10** conferências ativas. **Estoque inalterado (50).**
**Auditar:**
```sql
SELECT status FROM hora_avaria WHERE numero_chassi='92WMCX113SM000988';   -- ABERTA
SELECT count(*) FROM hora_recebimento_conferencia WHERE recebimento_id=121 AND substituida=false;  -- 10
-- Estoque atual loja 6 (deve ser 50):
WITH ult AS (SELECT DISTINCT ON (numero_chassi) numero_chassi, tipo, loja_id
             FROM hora_moto_evento ORDER BY numero_chassi, id DESC)
SELECT count(*) FROM ult WHERE loja_id=6 AND tipo IN
 ('RECEBIDA','CONFERIDA','TRANSFERIDA','CANCELADA','AVARIADA','FALTANDO_PECA','EMPRESTIMO_ENTRADA','RESSARCIMENTO_SAIDA');
```

## Próximos passos (ordem sugerida)
1. **Confirmar o deploy** dos hotfixes (já em `origin/main`) no Render — destrava os operadores em prod e fecha o bug de recebimento duplicado.
2. **Decidir Gap A/B** da feature sem-NF; finalizar a branch (merge + `hora_57` em prod + renumerar §32→§33).
3. **Reconciliar** a NF fake (160) e a NF vazia (161) quando as NFs reais da Motochefe chegarem.
