# QUICK START — Nova Sessao Inventario 2026-05 (TESTE PILOTO)

**Data do checkpoint:** 2026-05-17 fim do dia
**Branch:** `main`
**Estado anterior:** F7.1-7.4 concluidos + refator D004/D005 aplicado. 23.639 ajustes PROPOSTO.

---

## 🎯 PROMPT PRONTO PARA COLAR NA NOVA SESSAO

```
Retomando inventario 2026-05. Estado completo em
docs/inventario-2026-05/CHECKPOINT_2026_05_17_FIM_DIA.md.

OBJETIVO DESTA SESSAO: executar teste piloto end-to-end com produto
210030325 LF (6 ajustes ja propostos no DB, ids 139003-139008):
- 4 RENOMEAR_LOTE consolidando 82.300 un em lote 26014 na LF
- 2 PERDA_LF_FB (1 NF CFOP 5903 LF -> FB lote MIGRACAO, 66.532 un, R$ 42.806,69)
- Depois extrair estado pos-execucao do Odoo para validar.
- Extrator deve ser REPLICAVEL para todos os outros produtos da LF.

Antes de qualquer execucao REAL no Odoo, validar:
1. pytest tests/odoo/ -p no:randomly  (deve retornar 97 passed)
2. Estado DB conforme checkpoint (6 ajustes para 210030325 LF)
3. Ler CHECKPOINT_2026_05_17_FIM_DIA.md (estado completo)
4. Ler 00-decisoes/D004 e D005 (logica nova)
5. Ler prompt_inventario.md (intencao original) e SOT §7.4 (refator)

CONSTRUIR (nesta ordem):
1. Script teste piloto `scripts/inventario_2026_05/teste_210030325_lf.py`
   - Flag --dry-run OBRIGATORIA na primeira execucao
   - Orquestra: aprovacao onda → 4x StockLotService.renomear → 1x criar_picking
     LF->FB 2 linhas → f5b validar → f5c liberar → f5d aguardar invoice CIEL IT
     (~3min) → f5e Playwright SEFAZ
   - Persiste a cada etapa em ajuste_estoque_inventario.fase_pipeline + chave_nfe

2. Script extrator `scripts/inventario_2026_05/08_extrair_pos_execucao.py`
   - Input: ciclo + company_id (filial)
   - Para cada ajuste EXECUTADO, consulta Odoo (lotes renomeados,
     stock.quant atual, account.move emitido, chave SEFAZ) e gera Excel:
     antes/depois/status + diff vs proposta.
   - REPLICAVEL: aceita --company-id=N para rodar em qualquer filial.

3. Antes de executar REAL: rodar canary (F7.6 conceitual) com 1 NF de
   referencia historica (NF 13075 PERDA LF->FB) — comparar campos da
   nossa NF proposta vs essa NF aprovada para confirmar
   fiscal_position/CFOP.

4. Aprovacao formal: --aprovar-onda=1 --hash=<sha> --usuario=rafael
   (apos canary OK e validacao do usuario)

5. Execucao DRY-RUN do wrapper teste piloto.
6. Apos confirmacao do usuario: execucao REAL.
7. Rodar extrator e apresentar comparativo proposto vs realizado.

ATENCAO CRITICA — operacao parcialmente IRREVERSIVEL:
- RENAME: reversivel
- Picking + invoice CIEL IT: cancelavel ate validacao
- TRANSMISSAO SEFAZ via Playwright: irreversivel apos autorizacao
  (precisa NF cancelamento em ate 24h, ou Carta de Correcao)

PAUSE antes da etapa 6 (execucao real) para confirmacao explicita do
usuario, mesmo apos dry-run OK.
```

---

## ✅ Estado atual (snapshot completo em CHECKPOINT_2026_05_17_FIM_DIA.md)

### Services prontos
- F2 `StockLotService` (renomear, inativar, reativar)
- F3 `StockPickingService` (criar/validar picking + liberar_faturamento)
- F4 `InventarioPipelineService` (f5a..f5e batch)
- F5 `IndisponibilizacaoEstoqueService` (canary + indispor)
- 97 tests passing

### Logica F7.3/F7.4 (D004/D005 aplicada)
- D004 rename + diferenca liquida + custo medio dos outros lotes (so LF ainda)
- D005 lote MIGRACAO consolida fantasmas na FB
- Migration aplicada local — pendente build.sh item 22

### DB
- 23.639 ajustes PROPOSTO (Ondas 1: 1071, 2: 2558, 3: 19366, 4: 644)
- Caso piloto 210030325 LF: 6 ajustes ids 139003-139008

---

## 🆕 O que ESTA SESSAO precisa CONSTRUIR

### 1. Script wrapper teste piloto: `teste_210030325_lf.py`
Orquestrador especifico para o caso 210030325 LF. Encadeia F2 (rename)
+ F3 (picking) + F4 (batch f5a-f5e) com checkpoints e --dry-run.

**Pontos de atencao**:
- F4 `InventarioPipelineService.f5a_*` recebe `List[AjusteEstoqueInventario]`
  (desvio do plano original que esperava `List[int]` — ver SOT §desvios F4).
- Lotes a renomear precisam existir no Odoo. Verificar via
  `StockLotService.buscar_por_nome()` antes.
- Lote `26014` NAO existe no Odoo — sera criado pelos renames.
- Onda 1 do AjusteEstoqueInventario precisa ter `status='APROVADO'`
  ANTES de chamar F4. Aprovar via 04_propor_ajustes.py.
- Caso piloto = 6 registros. Filtrar com `AjusteEstoqueInventario.query.filter_by(cod_produto='210030325', company_id=5, status='APROVADO')`.
- `picking_type_id` para LF→FB perda: consultar `IDS_FIXOS.md` ou usar
  `constants/picking_types.py` (G002 — picking_type LF divergente,
  validar antes).

### 2. Script extrator pos-execucao: `08_extrair_pos_execucao.py`
**Replicavel por filial** (`--company-id=N`). Deve:

- Buscar ajustes `status IN ('EXECUTADO', 'FALHA')` da onda dada
- Para cada ajuste:
  - Consultar `stock.lot` atual no Odoo (foi renomeado? ativo?)
  - Consultar `stock.quant` atual (saldo pos-ajuste bate com proposta?)
  - Buscar `account.move` via `picking_id_odoo` (NF emitida? chave SEFAZ?)
- Comparar proposto vs realizado e gerar Excel:
  - Status (EXECUTADO/FALHA/DIVERGENCIA)
  - Antes (qty_odoo da proposta)
  - Depois (qty_odoo atual)
  - Diferenca esperada vs observada
  - chave_nfe + link Odoo
- Reusar pattern do `01_extrair_estoque_odoo.py` (paginacao, batch read).

### 3. Canary F7.6 (conceitual — pode ser inline no teste piloto)
- Buscar NF historica de referencia: PERDA LF→FB = `NF 13075`
  (`account_move_id_referencia=...` em MATRIZ_INTERCOMPANY)
- Comparar campos relevantes (fiscal_position_id, l10n_br_tipo_pedido,
  CFOP nas linhas) entre NF 13075 e a NF que seria gerada para 210030325
- Apenas relatorio — sem executar nada se divergir

---

## ⚠️ Pre-requisitos manuais antes de operacao REAL

| Item | Como verificar |
|---|---|
| Conexao XML-RPC Odoo | `python -c "from app.odoo.utils.connection import get_odoo_connection; from app import create_app; c=create_app(); c.app_context().push(); o=get_odoo_connection(); print(o.uid)"` deve printar `42` |
| Playwright + Chromium | `playwright install chromium` (se necessario) |
| Credenciais Playwright | env vars `ODOO_USER`, `ODOO_PASSWORD` populadas |
| Certificado SEFAZ valido | confirmar com Tamiris/contadora antes de transmitir |
| Robo CIEL IT online | Verificar Odoo modulo `l10n_br_ciel_it_account` |
| Backup do estado atual | Recomendado: `pg_dump --table=ajuste_estoque_inventario --table=operacao_odoo_auditoria` antes do teste |

---

## 🚨 Pontos de irreversibilidade (PAUSE OBRIGATORIO antes)

| Etapa | Reversivel? | Como reverter |
|---|---|---|
| StockLotService.renomear | Sim | renomear de volta |
| Criar picking | Sim | `cancelar()` do F3 |
| Validar picking | Sim com restricoes | desfazer movimentacoes manualmente no Odoo UI |
| Liberar para faturamento | Sim antes invoice criado | desfazer no Odoo UI |
| Invoice criada por CIEL IT | Sim antes SEFAZ | cancelar invoice no Odoo |
| **Transmissao SEFAZ autorizada** | **NAO** (apos retorno 100) | NF de cancelamento em <24h OU Carta de Correcao |

**Workflow item 10 do prompt**: "Operacoes sem possibilidade de rollback deverao ser aprovadas."

---

## 📚 Leitura ordenada para nova sessao

1. **Este arquivo** — entender objetivo da sessao
2. `CHECKPOINT_2026_05_17_FIM_DIA.md` — snapshot exato do estado
3. `00-decisoes/D004-rename-lote-diferenca-liquida.md` — logica rename
4. `00-decisoes/D005-lote-migracao-consolidador-fantasmas.md` — MIGRACAO
5. `app/agente/prompts/prompt_inventario.md` — intencao do usuario, workflow itens 7-10
6. `SOT.md` §7.4 — resumo do refator
7. `.claude/references/odoo/IDS_FIXOS.md` — picking types, journals
8. `02-gotchas/G002-picking-type-LF-divergente.md` — picking_type LF
9. `02-gotchas/G004-padrao-real-eh-picking-robo-CIEL-IT.md` — padrao NACOM

---

## 📂 Comandos prontos (em ordem)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Validar baseline (deve retornar 97 passed)
pytest tests/odoo/ -p no:randomly -q

# 2. Validar DB (deve retornar 23639 PROPOSTO + 6 do caso piloto)
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema \
  -c "SELECT COUNT(*) FROM ajuste_estoque_inventario WHERE ciclo='INVENTARIO_2026_05';"

# 3. Confirmar caso piloto
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT id, acao_decidida, lote_origem, lote_destino, qtd_ajuste, custo_medio
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND cod_produto='210030325' AND company_id=5
ORDER BY id;
"

# 4. CONSTRUIR scripts (teste piloto + extrator) — TAREFA DA SESSAO

# 5. Listar onda 1 atual + capturar hash
python scripts/inventario_2026_05/04_propor_ajustes.py --listar-onda=1 | head -5

# 6. Apos canary OK + revisao usuario: aprovar onda 1
# python scripts/inventario_2026_05/04_propor_ajustes.py \
#     --aprovar-onda=1 --hash=<sha> --usuario=rafael

# 7. Dry-run teste piloto (NAO ainda construido)
# python scripts/inventario_2026_05/teste_210030325_lf.py --dry-run

# 8. EXECUCAO REAL — PAUSAR para confirmacao explicita do usuario
# python scripts/inventario_2026_05/teste_210030325_lf.py --confirmar

# 9. Extrair resultado
# python scripts/inventario_2026_05/08_extrair_pos_execucao.py \
#     --ciclo=INVENTARIO_2026_05 --company-id=5
```

---

## 🔚 Pos-teste piloto (criterio de sucesso)

Considera teste piloto OK se:
1. 4 lotes na LF foram renomeados para `26014` (`stock.lot.name` mudou)
2. `stock.quant` na LF mostra cod 210030325 com 82.300 un em lote `26014`
3. Picking LF→FB validado, com 2 move.lines (-32.032 MIGRAÇÃO, -34.500 24715)
4. `account.move` emitida no Odoo (CFOP 5903, valor R$ 42.806,69)
5. Chave SEFAZ retornada (44 digitos) — registrada em `ajuste.chave_nfe`
6. FB tem cod 210030325 com +66.532 un em lote `MIGRACAO`
7. `operacao_odoo_auditoria` tem ~12 rows (4 rename + 5 F5a-e + 3 outros)
8. Extrator gera Excel com tudo isso comparado lado a lado (proposto vs realizado)

Se OK → generalizar para resto da LF (1.071 ajustes da onda 1).
Se nao OK → analise + ajuste antes de outros casos.
