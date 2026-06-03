<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D007 — Pre-etapa CD/FB para minimizar NFs inter-filial

> **Papel:** D007 — Pre-etapa CD/FB para minimizar NFs inter-filial.

## Indice

- [Problema](#problema)
- [Decisao](#decisao)
  - [Algoritmo pre-etapa por (cod_produto, company_id=CD)](#algoritmo-pre-etapa-por-cod_produto-company_idcd)
  - [Estado final esperado no CD](#estado-final-esperado-no-cd)
- [Novas acoes em `acao_decidida`](#novas-acoes-em-acao_decidida)
  - [Convencao de campos](#convencao-de-campos)
- [Onda 5 — semantica](#onda-5-semantica)
- [Generalizacao para FB (futuro)](#generalizacao-para-fb-futuro)
- [Restricao temporal de doador (regra critica)](#restricao-temporal-de-doador-regra-critica)
- [Por que MIGRAÇÃO com cedilha (e nao MIGRACAO)](#por-que-migração-com-cedilha-e-nao-migracao)
- [Servico novo](#servico-novo)
- [Tests TDD (cobertura)](#tests-tdd-cobertura)
- [Scripts novos (paralelos, evitam conflito com outra sessao)](#scripts-novos-paralelos-evitam-conflito-com-outra-sessao)
- [Volume esperado pos-regeneracao](#volume-esperado-pos-regeneracao)
- [Rollback](#rollback)
- [Referencias](#referencias)
- [Contexto](#contexto)

**Data**: 2026-05-18
**Status**: aprovado, em implementacao (CD agora, FB apos outra sessao finalizar)
**Fonte**: instrucao usuario apos analise de valor anormal das NFs FB↔CD
(R$ 887 mi onda 2 antes da regeneracao D004 generalizada).

> **CONTEXTO DE SESSAO**: este documento foi criado em sessao paralela.
> NAO modifica D004/D005/D006/SOT.md/QUICK_START_NEXT_SESSION.md por
> precaucao com race condition. Os ajustes sugeridos para esses
> documentos ficam em
> `D007-PATCHES-PARA-DOCS-EXISTENTES.md` (mesmo diretorio).

---

## Problema

Apos D004 generalizada (2026-05-18), o CD (cid=4) tinha 6.753 ajustes
PROPOSTO incluindo:

| Acao | Qtd | Valor BRL | Implicacao fiscal |
|---|---|---|---|
| INDISPONIBILIZAR_LOTE | 5.470 | R$ 60,5 mi | Marca lote inativo (sem NF, mas saldo permanece) |
| INDISPONIBILIZAR_LOCAL | 107 | R$ 340,3 mi | Marca location inativa |
| RENOMEAR_LOTE (=TRANSFERIR D006) | 791 | R$ 0 | Transfer interno (ja resolvido) |
| **TRANSFERIR_CD_FB** | **356** | **R$ 32,9 mi** | **NF CFOP 5151 inter-filial** |
| **TRANSFERIR_FB_CD** | **29** | **R$ 0,5 mi** | **NF CFOP 5152 inter-filial** |

Os R$ 32,9 mi em TRANSFERIR_CD_FB representam transferencia de valor
**anormal** entre filiais — precisa validacao da contadora. O usuario
optou por **substituir** essa abordagem por uma pre-etapa interna
ao CD.

Adicionalmente, INDISPONIBILIZAR_* tem caracter de "esconder fantasma"
— o saldo continua no Odoo, so nao aparece em faturamento. A nova
logica consolida tudo isso no lote MIGRAÇÃO do CD, com semantica
identica (saldo isolado para tratamento contabil posterior) mas
mecanismo unificado (apenas inventory adjustment, sem `active=False`).

---

## Decisao

**Inserir uma nova ONDA 5 (pre-etapa) executada ANTES da onda 2**,
contendo apenas transferencias internas + ajustes positivos puros
no CD. As acoes INDISPONIBILIZAR_LOTE/LOCAL e TRANSFERIR_CD_FB para
o CD sao substituidas pela nova logica.

### Algoritmo pre-etapa por (cod_produto, company_id=CD)

Por produto com divergencia:

1. **Mapear estado**: quants atuais Odoo CD (todas locations internas)
   + lotes inventariados desejados (do diff).
2. **Garantir lote alvo**: para cada lote inventariado, criar no CD via
   `StockLotService.criar_se_nao_existe(nome, product_id, cid_cd)`. Para
   linhas inv sem lote, agregar por produto e usar nome `P-15/05`.
3. **Transferencias internas POSITIVAS** (preencher lotes alvo):
   - Para cada lote alvo do inv, transferir de qualquer outro lote do CD
     do mesmo produto → lote alvo (FIFO por quant_id, exaurir
     nao-alvo) ate cobrir qty_desejada.
   - Operacao: `StockInternalTransferService.transferir_entre_lotes()`
     (ja existe — sem NF).
4. **Apos exaurir nao-alvo do CD** (residual):
   - **Sobrou** (CD tinha mais que inv): consolidar resto em lote
     `MIGRAÇÃO` do CD (criar se nao existir). Operacao interna.
   - **Faltou** (CD tinha menos): cascata:
     - 4a. **Tentar pegar da FB** (qualquer lote, FIFO): gera NF FB→CD
       CFOP 5152 (acao `TRANSFERIR_FB_CD` ja existente, mas reduzida).
       Restricao temporal: enquanto FB ainda nao passou pela propria
       pre-etapa, qualquer lote da FB pode doar. Depois da pre-etapa
       FB, so o lote MIGRAÇÃO da FB pode doar (preserva corretude FB).
     - 4b. **Se FB nao cobre**: `AJUSTE_CD_POSITIVO_PURO` —
       inventory adjustment direto, sem origem fiscal.

### Estado final esperado no CD

- Cada lote inventariado do CD com a qty correta (= inventario fisico)
- Toda divergencia consolidada no lote `MIGRAÇÃO` do CD
- ZERO emissao de TRANSFERIR_CD_FB (eliminado)
- ZERO emissao de INDISPONIBILIZAR_LOTE/LOCAL para o CD (substituido)
- Apenas TRANSFERIR_FB_CD residual (R$ ~0,5 mi vs R$ 33 mi antes)

---

## Novas acoes em `acao_decidida`

`VARCHAR(40)` sem constraint check — sem migration DDL.

| Acao | Onda | qty_ajuste | Operacao | NF? |
|---|---|---|---|---|
| `AJUSTE_CD_TRANSF_INTERNA_POS` | **5** | =0 (interno) | StockInternalTransferService: lote_X (CD) → lote_alvo (CD) | NAO |
| `AJUSTE_CD_TRANSF_INTERNA_NEG` | **5** | =0 (interno) | StockInternalTransferService: lote_X (CD) → MIGRAÇÃO (CD) | NAO |
| `AJUSTE_CD_POSITIVO_PURO` | **5** | >0 | `stock.quant.action_apply_inventory` direto, sem origem | NAO |
| `TRANSFERIR_FB_CD` (mantem) | 2 | >0 | NF FB→CD CFOP 5152 (residual) | SIM |

### Convencao de campos

| Campo do ajuste | TRANSF_INTERNA_POS | TRANSF_INTERNA_NEG | POSITIVO_PURO |
|---|---|---|---|
| `lote_origem` | nome lote do CD que doa | nome lote do CD que doa | NULL |
| `lote_destino` | lote_inventariado (ou `P-15/05`) | `MIGRAÇÃO` | lote_inventariado (ou `P-15/05`) |
| `qtd_ajuste` | 0 | 0 | qty residual a criar |
| `qtd_inventario` | qty transferida (info) | qty transferida (info) | qty residual |
| `qtd_odoo` | qty transferida (info) | qty transferida (info) | 0 |
| `custo_medio` | media ponderada cod (D004) | media ponderada cod (D004) | media ponderada cod |

---

## Onda 5 — semantica

- **Onda 0**: SEM_ACAO (mantem)
- **Onda 1**: LF↔FB NF (mantem — industrializacao, perda, dev)
- **Onda 2**: FB↔CD NF transferencia (mantem, **drasticamente reduzida** — so TRANSFERIR_FB_CD residual)
- **Onda 3**: INDISPONIBILIZAR (mantem para FB; **CD nao usa mais**)
- **Onda 4**: RENOMEAR_LOTE (mantem para FB/LF; **CD agora redundante via Onda 5**)
- **Onda 5**: pre-etapa CD interna (NOVA) — executa ANTES da Onda 2

**Dependencia**: Onda 2 (TRANSFERIR_FB_CD) so executa apos Onda 5 CD
estar `EXECUTADO` 100%. O wrapper `09b_executar_pre_etapa.py` deixa
explicito; e o bulk Onda 2 (futuro) deve checar.

---

## Generalizacao para FB (futuro)

A mesma logica e aplicavel para FB (cid=1) **APOS** a outra sessao
finalizar e CD ja ter executado a Onda 5. Diferencas:

| Aspecto | CD (Onda 5) | FB (Onda 6 futura) |
|---|---|---|
| Doador residual positivo | qualquer lote da FB (cid=1) | qualquer lote da LF (cid=5) ou CD MIGRAÇÃO (cid=4) |
| Restricao pos-pre-etapa | CD so deixa MIGRAÇÃO doar | FB so deixa MIGRAÇÃO doar |
| Acoes correspondentes | `AJUSTE_CD_*` | `AJUSTE_FB_*` |
| Doador residual da FB (positivo) | n/a | LF via INDUSTRIALIZACAO_FB_LF residual, ou ajuste positivo puro |

**O service `pre_etapa_estoque_service.py` ja sera parametrizado por
`company_id`** desde o inicio, para reuso direto no FB.

---

## Restricao temporal de doador (regra critica)

> "Antes de realizar na FB, podemos utilizar qualquer lote da FB.
> Apos realizar no CD, podemos utilizar apenas MIGRAÇÃO do CD."

Implicacao:

| Etapa | Doadores CD permitidos | Doadores FB permitidos |
|---|---|---|
| Antes de Onda 5 (CD pre-etapa) | n/a (CD nao doa fora) | qualquer lote FB |
| Apos Onda 5 CD | so MIGRAÇÃO do CD | qualquer lote FB |
| Apos Onda 6 FB (futuro) | so MIGRAÇÃO do CD | so MIGRAÇÃO da FB |

A pre-etapa CD nao depende dessa restricao (CD pre-etapa nao toca FB).
A Onda 2 residual (TRANSFERIR_FB_CD) **pode** usar qualquer lote da FB,
pois roda antes da Onda 6 FB. Quando Onda 6 FB rodar, qualquer
ajuste futuro que precise tirar do CD deve respeitar MIGRAÇÃO-only.

---

## Por que MIGRAÇÃO com cedilha (e nao MIGRACAO)

Decisao da outra sessao (script `padronizar_migracao.py`, 2026-05-18):
o lote historico no Odoo CIEL IT ja era `MIGRAÇÃO` (com cedilha + til);
o piloto criou inadvertidamente `MIGRACAO` (sem) e foi migrado de
volta. Todo codigo novo usa `MIGRAÇÃO`.

Encoding: Postgres UTF-8 + Odoo UTF-8. Sem problema. Mas precaucao no
Latin-1 (SPED ECD nao usa — irrelevante aqui).

---

## Servico novo

`app/odoo/services/pre_etapa_estoque_service.py` — planejador
parametrizado por company_id.

```python
class PreEtapaEstoqueService:
    def planejar(
        self, company_id: int,
        cod_produto: str,
        quants_odoo: list[dict],   # quants Odoo da company
        linhas_inv: list[dict],    # linhas inv desejadas
        quants_fb_disponivel: list[dict] | None = None,  # so para CD
    ) -> PlanoPreEtapa:
        ...
```

Retorna `PlanoPreEtapa`:

```python
@dataclass
class PlanoPreEtapa:
    transferencias_internas: list[TransferenciaPlanejada]  # CD interno
    residual_fb_cd: list[TransferenciaExternaPlanejada]    # NF FB→CD
    ajustes_positivos_puros: list[AjustePositivoPlanejado] # inventory adjust
    consolidacao_migracao: list[ConsolidacaoPlanejada]     # sobra → MIGRAÇÃO
```

---

## Tests TDD (cobertura)

`tests/odoo/services/test_pre_etapa_estoque_service.py`:

1. `test_sobra_pura_consolida_em_migracao_cd`
2. `test_falta_pura_pega_de_fb_se_disponivel`
3. `test_falta_pura_sem_fb_vira_ajuste_positivo_puro`
4. `test_sobra_e_falta_misto_balanceiam_internamente`
5. `test_lote_inv_sem_nome_usa_P_15_05_agregado_por_produto`
6. `test_multiplos_lotes_inv_do_mesmo_produto`
7. `test_quant_sem_lote_pode_doar_para_lote_alvo`
8. `test_fifo_quant_id_para_doacao_interna`
9. `test_lote_alvo_ja_existente_no_cd_mantido`
10. `test_quants_com_reserva_bloqueiam_doacao`
11. `test_company_id_parametrizado_funciona_para_fb` (regressao)
12. `test_custo_medio_ponderado_aplicado_em_ajuste_puro`

Total: ~12 tests novos + tests existentes (95 outros do baseline) = 107.
(5 testes failing pre-existentes da outra sessao em
`test_inventario_pipeline_service.py` nao bloqueiam — area diferente.)

---

## Scripts novos (paralelos, evitam conflito com outra sessao)

| Script | Propósito |
|---|---|
| `scripts/inventario_2026_05/03b_planejar_pre_etapa_cd.py` | Le quants Odoo + inv CD/FB, chama service, salva plano em /tmp + Excel |
| `scripts/inventario_2026_05/04b_propor_pre_etapa_cd.py` | DELETE PROPOSTO CD (com backup auto) + insert novos ajustes Onda 5 |
| `scripts/inventario_2026_05/09b_executar_pre_etapa.py` | `--company-id={4,1}` parametrizado; executa transferencias + ajustes positivos puros |

**NAO modificam** 03/04 existentes. Patches sugeridos para integrar
depois (quando outra sessao finalizar) listados em D007-PATCHES.

---

## Volume esperado pos-regeneracao

**Antes da regeneracao** (estado atual):
- CD PROPOSTO: 6.753 ajustes (5.470 + 791 + 356 + 107 + 29)
- TRANSFERIR_CD_FB: R$ 32,9 mi
- TRANSFERIR_FB_CD: R$ 0,5 mi

**Apos regeneracao** (esperado):
- CD PROPOSTO: ~600-1000 ajustes (1 ou poucos por produto x 591 produtos)
- AJUSTE_CD_TRANSF_INTERNA_POS: ~27 produtos x N lotes ~= 50-100
- AJUSTE_CD_TRANSF_INTERNA_NEG: ~549 produtos x 1 = ~549 (toda sobra → MIGRAÇÃO)
- AJUSTE_CD_POSITIVO_PURO: 0-N (so se FB nao cobrir)
- TRANSFERIR_FB_CD: drasticamente reduzido (so se FB tem o lote certo)
- TRANSFERIR_CD_FB: **0** (eliminado)
- INDISPONIBILIZAR_LOTE/LOCAL CD: **0** (eliminado — vira interno via MIGRAÇÃO)

Estimativa de reducao de NFs SEFAZ: -385 NFs (~100% das CD↔FB).

---

## Rollback

Se a regeneracao gerar resultado nao esperado:

```bash
# Restaurar backup
psql -d frete_sistema -c "DELETE FROM ajuste_estoque_inventario WHERE ciclo='INVENTARIO_2026_05' AND company_id=4;"
psql -d frete_sistema -f /tmp/backup_inventario_2026_05/ajustes_cd_pre_etapa_<TS>.sql
```

Backup full em `/tmp/backup_inventario_2026_05/`.

Se algo ja foi EXECUTADO no Odoo (transferencia ou ajuste positivo):
- Transferencia interna: reversivel via inventory adjustment inverso
- Ajuste positivo puro: reversivel via inventory adjustment negativo
- Ambas sem NF: rollback Odoo-only, sem impacto fiscal.

---

## Referencias

- Decisoes anteriores: `D004-rename-lote-diferenca-liquida.md` (rename + diferenca liquida), `D005-lote-migracao-consolidador-fantasmas.md` (lote MIGRAÇÃO consolida), `D006-transferir-quantidade-entre-lotes-nao-renomear.md` (TRANSFERIR via inventory adjustment)
- Service ja existente reutilizado: `app/odoo/services/stock_internal_transfer_service.py` (D006)
- Service ja existente: `app/odoo/services/stock_lot_service.py` (D006)
- Patches para docs existentes: `D007-PATCHES-PARA-DOCS-EXISTENTES.md`

## Contexto

ADR (decisao de arquitetura) — ciclo de inventario NACOM/LF/CD/FB 2026-05. Tema: Pre-etapa CD/FB para minimizar NFs inter-filial
