<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Inventário Cíclico — Contagem parcial por quant + Plano de ajustes — Design

> **Papel:** Inventário Cíclico — Contagem parcial por quant + Plano de ajustes — Design.

## Indice

- [1. Visão e objetivos](#1-visão-e-objetivos)
- [2. Não-objetivos (out of scope)](#2-não-objetivos-out-of-scope)
- [3. Granularidades (decisão central)](#3-granularidades-decisão-central)
- [4. Arquitetura (Abordagem 1 — sub-fluxo isolado)](#4-arquitetura-abordagem-1-sub-fluxo-isolado)
- [5. Modelo de dados](#5-modelo-de-dados)
  - [5.1 `ContagemInventario` (cabeçalho) — tabela `inventario_contagem`](#51-contageminventario-cabeçalho-tabela-inventario_contagem)
  - [5.2 `ContagemInventarioItem` (1 linha = 1 quant) — tabela `inventario_contagem_item`](#52-contageminventarioitem-1-linha-1-quant-tabela-inventario_contagem_item)
- [6. Regras de negócio](#6-regras-de-negócio)
  - [6.1 Casamento e escopo — **por QUANT, nunca por item**](#61-casamento-e-escopo-por-quant-nunca-por-item)
  - [6.2 Linha nova (lote criado no físico)](#62-linha-nova-lote-criado-no-físico)
  - [6.3 Classificação → átomo (o que dá determinismo na aplicação)](#63-classificação-átomo-o-que-dá-determinismo-na-aplicação)
  - [6.4 Integração com o Confronto (inventário vigente)](#64-integração-com-o-confronto-inventário-vigente)
- [7. Fluxo (2 tempos)](#7-fluxo-2-tempos)
- [8. Salvaguardas](#8-salvaguardas)
- [9. Telas](#9-telas)
- [10. Migrations](#10-migrations)
- [11. Testes (~20)](#11-testes-20)
- [12. Tratamento de erros e bordas](#12-tratamento-de-erros-e-bordas)
- [13. Riscos e decisões](#13-riscos-e-decisões)
- [14. Próximos passos](#14-próximos-passos)
- [Contexto](#contexto)

**Data**: 2026-05-31
**Autor**: Rafael Nascimento + Claude (Opus 4.8)
**Status**: Aprovado — implementado
**Módulo**: `app/inventario/` (sub-fluxo novo, ao lado do Confronto existente)
**Spec irmão (não alterado)**: `docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md`

---

> **Revisão 2026-05-31 (pós-implementação) — coluna AJUSTE autoritativa.**
> Decisão do usuário: o ajuste que vai para a coluna **INV/MOV do Confronto** passa a
> vir da **coluna AJUSTE da planilha** (campo novo `ajuste_inventario`, autoritativo;
> vazio = 0), e **não** de `contagem − qtd_esperada`. Motivo: quando o Odoo está
> "semi-ajustado" (divergente do `InventarioBase`), derivar o ajuste contra o Odoo
> (`qtd_esperada`) levava a coluna MOV a um valor errado. Os **dois** ajustes ficam
> separados (não confundir): `ajuste` (= contagem − qtd_esperada) segue alimentando o
> plano de aplicação no **Odoo** (skills) e a `classe`; `ajuste_inventario` alimenta
> **só** o Confronto. Ver §5.2, §6.1, §6.4.

## 1. Visão e objetivos

Hoje o módulo `app/inventario/` só faz o **Confronto** (inventário geral por **produto + empresa**, sem detalhe de local — `confronto_service.py:169`). A necessidade nova é **contagem cíclica sob demanda**: contar fisicamente um recorte do estoque a qualquer momento e materializar os ajustes resultantes.

**Dois objetivos (e só estes):**

1. **Corrigir o estoque com os ajustes** — gerar, a partir da contagem, um plano determinístico de ajustes que **eu/agente aplico no Odoo via skills `gestor-estoque-odoo`** (não o módulo).
2. **Gerar o relatório de estoque por quant com as colunas certas + armazenar os ajustes** — extrair o estoque atual do Odoo na granularidade de quant, casar com a contagem, calcular/classificar os ajustes e **persistir o histórico**.
3. **Refletir os ajustes cíclicos no Confronto** — as colunas `INV FB/CD/LF` do Confronto passam a exibir a baseline do inventário completo **mais a soma dos ajustes cíclicos** do período vigente, agregados por produto+empresa (§6.4).

## 2. Não-objetivos (out of scope)

- **Escrever no Odoo a partir do módulo.** A escrita continua nas skills (`ajustando-quant-odoo`, `operando-reservas-odoo`, `operando-picking-odoo`) com dry-run + confirmação. Reafirma o não-objetivo do spec irmão (§1).
- **Ajustar `MovimentacaoEstoque` / sistema_fretes.** Fica **manual**, fora do módulo.
- **Cycle counting com agenda/curva ABC / frequência-alvo / acuracidade no tempo.** Não é o pedido.
- **Rastrear "aplicado no Odoo" por item/onda.** Cortado para não inventar moda.
- **Reescrever o Confronto.** O Confronto recebe **uma única alteração cirúrgica** (somar ajustes cíclicos nas 3 colunas INV — §6.4); todo o resto (ODOO/MOV/SIST, drill-down, snapshot) é preservado.

## 3. Granularidades (decisão central)

| Fluxo | Granularidade | Status |
|---|---|---|
| **Confronto** (existente) | produto + empresa + local válido (sem detalhar local) | 1 alteração: INV soma cíclicos (§6.4) |
| **Contagem Cíclica** (novo) | `location_name` + `cod` + `lote` (= 1 `stock.quant`: produto + local + lote + empresa) | a construir |

A ligação entre os dois (cíclico → INV do Confronto) é agregada por **produto+empresa** e cortada por data — detalhe em §6.4.

A granularidade fina é o que dá **determinismo**: cada linha do plano aponta para **um quant**, então o átomo `ajustar_quant` sabe exatamente qual saldo mexer.

## 4. Arquitetura (Abordagem 1 — sub-fluxo isolado)

Novo sub-fluxo dentro de `app/inventario/`, reusando o Blueprint `inventario_bp` (`app/__init__.py:1208-1209`). O Confronto recebe **1 alteração cirúrgica** (§6.4).

```
app/inventario/
├── models.py                              + ContagemInventario, ContagemInventarioItem
├── routes/
│   └── contagem_routes.py                 NOVO — CRUD contagem, gerar base, upload, preview, relatório, export
├── services/
│   ├── confronto_service.py               ALTERADO — INV FB/CD/LF soma ajustes cíclicos do período (§6.4)
│   ├── extracao_quant_service.py          NOVO — extrai stock.quant por (location,cod,lote); núcleo reaproveitado
│   ├── contagem_service.py                NOVO — casa reupload por quant, calcula ajuste, classifica, persiste
│   └── contagem_export_service.py         NOVO — gera Excel da base e do relatório/plano
app/templates/inventario/
│   ├── contagens.html                     NOVO — lista
│   └── contagem_detalhe.html              NOVO — gerar base/download → upload → preview → relatório/export
scripts/migrations/
│   ├── inventario_contagem_create.py      NOVO — DDL Python + verificação
│   └── inventario_contagem_create.sql     NOVO — DDL SQL idempotente (IF NOT EXISTS)
tests/inventario/
│   ├── test_extracao_quant_service.py     NOVO (mock Odoo)
│   ├── test_contagem_service.py           NOVO (regras de semântica + classificação)
│   └── test_contagem_routes.py            NOVO (gerar base, preview, export, permissões)
```

**Reuso (não duplicar):** a lógica de extração de `scripts/inventario_2026_05/extrair_estoque_locais_emp.py` (busca `stock.quant`, classifica `local_tipo`/`is_migracao`, agrega por `(filial, location_name, cod, lote)`, deriva `reservado`/`disponivel` — linhas `178-239`) é **extraída para `extracao_quant_service.py`**; o script CLI passa a chamar o service, mantendo retrocompatibilidade (regra `[[feedback_parametrizar_scripts_existentes]]`).

**Integração com sistema:** `app/templates/base.html` — link ao lado do Confronto de Inventário existente. Sem novas filas RQ (extração é síncrona e leve; ver §13).

## 5. Modelo de dados

### 5.1 `ContagemInventario` (cabeçalho) — tabela `inventario_contagem`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `codigo` | String(50) unique | auto, ex. `CONT-2026-05-31-FB-01` |
| `empresa` | String(10) | FB / CD / LF (companies 1/4/5, igual ao resto do módulo) |
| `filtro_locais` | JSON | lista de `location_name` selecionados (vazio = todos) |
| `filtro_codigos` | JSON | lista de `cod_produto` selecionados (vazio = todos) |
| `incluir_indisponivel` | Boolean | default False (espelha modo default do script — exclui `{emp}/Indisponivel`) |
| `data_base` | DateTime | T0 da extração (saldo-esperado ancorado aqui). **Também é a data de corte** do somatório no Confronto (§6.4); comparação por dia (`func.date`) |
| `status` | String(20) | `BASE_GERADA` → `CONTABILIZADA` (2 estados) |
| `descricao` | String(200) | livre |
| `criado_em` / `criado_por` | DateTime / String(100) | `agora_utc_naive` |

Resumo (preenchido na contabilização, derivável): `tot_itens`, `tot_com_ajuste`, `tot_ajuste_pos`, `tot_ajuste_neg`, `qt_lotes_novos`.

### 5.2 `ContagemInventarioItem` (1 linha = 1 quant) — tabela `inventario_contagem_item`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `contagem_id` | Integer FK → `inventario_contagem.id` | index |
| `location_name` | String(120) | ex. `FB/Estoque`, `FB/Pré-Produção/Linha Balde` |
| `location_id` | Integer | ID Odoo do location (determinismo na aplicação) |
| `local_tipo` | String(20) | `Estoque` / `Indisponivel` (do script) |
| `is_migracao` | Boolean | lote MIGRAÇÃO = fantasma (do script) |
| `cod_produto` | String(50) | index |
| `nome_produto` | String(200) | |
| `lote` | String(60) | **`''` (vazio) = sem lote** (sentinela, p/ a unique funcionar) |
| `company_id` | Integer | 1/4/5 |
| `qtd_esperada` | Numeric(15,3) | saldo Odoo no T0 (`quantity`) |
| `reservado_esperado` | Numeric(15,3) | `reserved_quantity` no T0 |
| `contagem` | Numeric(15,3) nullable | físico contado (coluna CONTAGEM); preenchido pelo usuário |
| `ajuste` | Numeric(15,3) | `= contagem − qtd_esperada` → delta a aplicar no **Odoo** (skills); define a `classe` |
| `ajuste_inventario` | Numeric(15,3) NOT NULL default 0 | **valor literal da coluna AJUSTE** (autoritativo; vazio = 0) → delta somado ao último inventário na coluna INV/MOV do **Confronto**. Independe do Odoo |
| `classe` | String(20) | NORMAL / RESERVA_FANTASMA / NEGATIVO / LOTE_NOVO / SEM_AJUSTE (baseada em `ajuste`) |
| `obs` | String(300) | |

`UniqueConstraint(contagem_id, location_name, cod_produto, lote)` — `lote=''` para sem-lote evita o NULL-distinct do Postgres.

**Volume:** ~800 itens por contagem (a FB inteira ≈ 776 quants); dezenas de contagens/ano → < 50K linhas em anos. Sem particionamento.

## 6. Regras de negócio

### 6.1 Casamento e escopo — **por QUANT, nunca por item**

A unidade de presença/escopo é a **linha = 1 quant** `(location_name, cod_produto, lote)`, **nunca** o código agregado.

- **Quant presente** na planilha reenviada ⇒ inventariado:
  - `CONTAGEM` preenchida (inclusive `0`) ⇒ `ajuste = contagem − qtd_esperada` (→ Odoo).
  - `CONTAGEM` em branco ⇒ tratada como **0** (zera o fantasma no Odoo).
  - `AJUSTE` (coluna autoritativa, opcional) ⇒ `ajuste_inventario = valor literal` (→ Confronto);
    em branco ⇒ **0** (sem ajuste no Confronto). Aceita negativo. **Não** é derivado da contagem.
- **Quant ausente** da planilha ⇒ **intocado**, mesmo que o mesmo `cod_produto` apareça em outras linhas.

> **AJUSTE × CONTAGEM são independentes.** CONTAGEM governa o plano para o Odoo (incl.
> vazia = zera); AJUSTE governa a coluna INV/MOV do Confronto. Preencher um não afeta o outro.

> Exemplo validado com o usuário: código com 5 quants no Odoo; reenvia 3 linhas (2 zeradas + 1 com qtd) ⇒ ajusta só as 3; os 2 quants ausentes ficam intocados.

### 6.2 Linha nova (lote criado no físico)

Linha da planilha que **não casa** com nenhum quant da base (par `(location_name, cod, lote)` inexistente no Odoo) ⇒ `qtd_esperada = 0`, `classe = LOTE_NOVO`, `ajuste = contagem`.

### 6.3 Classificação → átomo (o que dá determinismo na aplicação)

Calculada na contabilização, gravada em `classe`, exibida no relatório. **Orienta qual átomo eu uso** — não é workflow.

| `classe` | Condição (no T0) | Átomo / skill na aplicação |
|---|---|---|
| `NORMAL` | `qtd_esperada ≥ 0`, `reservado_esperado = 0`, `ajuste ≠ 0` | `ajustar_quant --delta` com `delta_esperado=ajuste` (`quant.py:94-170`) |
| `RESERVA_FANTASMA` | `ajuste < 0` **e** `reservado_esperado > 0` | `ajustar_quant --resetar-reserva` + `reserva.zerar_reserved_residual`, ordem `unlink → zerar` — `[[gotcha_resetar_reserva_orfao_negativo]]`, `[[sequencia_unlink_zerar_residual]]` |
| `NEGATIVO` | `qtd_esperada < 0` (ajuste +) | `picking.py` (stock.picking p/ destino negativo) — **nunca** inventory adjustment (infla `2V−Q`) — `[[gotcha_inventory_adjustment_quant_negativo]]` |
| `LOTE_NOVO` | linha não existe no Odoo (§6.2) | `ajustar_quant --criar-se-faltar` — resolve/cria lote **por produto + `company_id`** (G031, `[[gotcha_lote_multiempresa_company_filter]]`) |
| `SEM_AJUSTE` | `ajuste = 0` | nenhuma ação (só histórico) |

> `lote=''` (sem lote) é **atributo** da linha, não uma classe — qualquer átomo trata passando lote vazio.

### 6.4 Integração com o Confronto (inventário vigente)

O Confronto continua sendo renderizado **por inventário completo** (`CicloInventario`, granularidade produto+empresa). A novidade: as colunas **`INV FB/CD/LF`** passam a ser

```
INV_<empresa>(produto) = baseline(InventarioBase)                      -- contagem do inventário completo
                       + Σ ajuste_inventario das ContagemInventarioItem -- coluna AJUSTE (autoritativa)
                         do período vigente, da <empresa>,
                         agrupados por (cod_produto, empresa)
```

> **Usa `ajuste_inventario` (coluna AJUSTE), NÃO `ajuste`.** O delta somado ao último
> inventário é o que o usuário digitou em AJUSTE — independe de `qtd_esperada` (saldo
> Odoo do T0). Isso evita carregar para a coluna MOV a divergência Odoo↔inventário
> quando o Odoo está "semi-ajustado".

**Exemplo (validado com o usuário) — Produto A, empresa FB:**
- Baseline do inventário completo: `INV FB = 1000`.
- Cíclico (por quant): Lote 1/Local X contou 500 (bate, AJUSTE 0); Lote 2/Local Y o físico
  exigia somar `−100` ao inventário ⇒ coluna **AJUSTE = −100**.
- `ajuste_inventario` agregado por produto+empresa = `−100` ⇒ Confronto exibe **`Produto A · FB = 900`**.

**Caso "semi-ajustado" (o que motivou a revisão 2026-05-31):** se o Odoo já tinha sido
parcialmente ajustado antes da contagem (ex. `qtd_esperada = 90` onde o físico é 80, e o
inventário completo era 100), então `ajuste = 80 − 90 = −10` (aplicado no Odoo, leva ODOO a 80),
mas o delta correto sobre o inventário é `−20` (100 → 80) ⇒ o usuário digita **AJUSTE = −20**.
A coluna INV vai a `1000 − 20 = 980` em vez de `1000 − 10 = 990`. Os dois ajustes divergem
de propósito; cada um corrige a sua dimensão.

**Vigência / reset — corte por data (`>=`):** sejam os inventários completos ordenados por `data_snapshot`. Para o Confronto do inventário completo `I`, somam os ajustes das contagens cíclicas cuja `data_base` cai no intervalo

```
data_snapshot(I)  <=  data_base(contagem)  <  data_snapshot(próximo completo, se houver)
```

- Para o inventário **vigente** (o mais recente, sem completo posterior) o intervalo é aberto em cima ⇒ degenera no critério pedido: **`data_base >= data_snapshot(I)`**.
- Um **novo inventário completo** vira nova baseline e **mata os cíclicos anteriores** (eles caem fora do novo intervalo). O limite superior só importa ao reabrir o Confronto de um inventário antigo — impede vazamento de cíclicos de períodos futuros.
- Empate de data não ocorre: o usuário garante que não há "cíclico + inventário + cíclico no mesmo dia".

**Por que não há double-count:** o `INV` do Confronto é calculado **independente** do snapshot Odoo (vem de `InventarioBase` + cíclicos). Somar o ajuste cíclico no `INV` é justamente o que faz os dois lados (INV e ODOO já corrigido) convergirem; não há dupla contagem porque são fontes distintas.

**Acoplamento mínimo:** não há FK entre `ContagemInventario` e `CicloInventario`. A ligação é só a query temporal acima, dentro do `ConfrontoService` — os modelos permanecem desacoplados.

## 7. Fluxo (2 tempos)

1. **Criar contagem + gerar base (passo único)** — você define empresa (obrigatória) + `filtro_locais` e/ou `filtro_codigos` (opcionais) + `incluir_indisponivel`; ao confirmar, o `extracao_quant_service` lê os `stock.quant` do Odoo e **só então** o registro é persistido (cabeçalho + itens) — nasce já em `BASE_GERADA`. Se a extração falhar, rollback (nada gravado). Isso garante os 2 estados sem um `RASCUNHO` órfão.
2. **Base gerada** — itens com `qtd_esperada`, `reservado_esperado`, `contagem` nula, `data_base = now`. **Download Excel** no formato da planilha 31-05 (`location_name, local_tipo, cod, nome_produto, lote, qtd, reservado, disponivel, AJUSTE, CONTAGEM`).
3. **Contagem física** — você preenche `CONTAGEM`, adiciona linhas de lote novo se houver.
4. **Reupload + preview** — o módulo casa por quant (§6.1), calcula `ajuste`, classifica (§6.3), e **mostra preview de impacto SEM gravar**: "N zeram, M positivos, K lotes novos, total a remover = X un, total a adicionar = Y un". Você confirma ⇒ persiste itens + resumo, status `CONTABILIZADA`.
5. **Relatório / plano** — tela por quant com `qtd_esperada / contagem / ajuste / classe` + **export Excel**. Esse relatório **é o plano** que eu consumo para aplicar no Odoo (objetivo 1). sistema_fretes: manual (fora do módulo).

## 8. Salvaguardas

- **Preview antes de gravar** (§7.4) — porque "presente+vazio=0" pode zerar em massa se a base inteira for reenviada por engano.
- **Saldo-esperado ancorado no T0** (`qtd_esperada`/`reservado_esperado`) ⇒ vira `delta_esperado` no plano ⇒ o **guard do átomo** detecta divergência se o saldo mudou entre contagem e aplicação (`quant.py:248-278`). O relatório sinaliza `data_base` antiga.
- `require_admin` em todas as rotas (igual ao Confronto, `ciclo_routes.py:9,22`).
- `sanitize_for_json()` em todo retorno JSON com `Numeric`/`Decimal` (regra `~/.claude/CLAUDE.md`).
- Timestamps via `agora_utc_naive()` (regra REGRAS_TIMEZONE).

## 9. Telas

- **`contagens.html`** — lista (código, empresa, data_base, status, tot_itens, tot_com_ajuste); botão "Nova contagem".
- **`contagem_detalhe.html`** — criar/ver contagem; botão **Gerar base** + **Download Excel**; **Upload** da planilha preenchida; bloco de **preview**; **relatório por quant** (tabela com filtros simples por classe) + **Exportar Excel**.
- **Menu** (`base.html`) — link ao lado do "Confronto de Inventário".

## 10. Migrations

Dois artefatos (regra `~/.claude/CLAUDE.md`):
- `scripts/migrations/inventario_contagem_create.py` — `create_app()` + verificação before/after + `db.create_all()` filtrado pelos 2 modelos.
- `scripts/migrations/inventario_contagem_create.sql` — `CREATE TABLE IF NOT EXISTS` + índices `IF NOT EXISTS` para as 2 tabelas.

## 11. Testes (~20)

- `test_extracao_quant_service.py` (mock Odoo): agrega por `(location_name, cod, lote)`; exclui Indisponivel no default e inclui quando `incluir_indisponivel`; deriva `reservado`/`disponivel`.
- `test_contagem_service.py`: **presente+vazio ⇒ 0**; **ausente ⇒ ignora**; **linha nova ⇒ LOTE_NOVO**; classificação NORMAL/RESERVA_FANTASMA/NEGATIVO/SEM_AJUSTE; `ajuste = contagem − qtd_esperada`; resumo correto.
- `test_contagem_routes.py`: gerar base (mock Odoo), preview não grava, confirmar grava, export Excel `Content-Type` correto, `require_admin` ⇒ 403 sem permissão.
- `test_confronto_ciclico_integracao.py`: INV do Confronto = baseline + ajuste cíclico agregado por produto+empresa (**exemplo Produto A ⇒ 900**); cíclico com `data_base` fora do intervalo do ciclo **não** soma; corte `>=` na `data_snapshot`; **regressão**: sem nenhuma contagem cíclica, o Confronto produz exatamente o resultado atual.

## 12. Tratamento de erros e bordas

1. Upload sem colunas `location_name`/`cod`/`lote`/`CONTAGEM` ⇒ erro estruturado com detalhe.
2. `CONTAGEM` não-numérica ⇒ linha reportada, não trava o lote inteiro.
3. Contagem negativa digitada ⇒ aceita só se houver justificativa? **Decisão:** rejeita `contagem < 0` (físico não é negativo); negativo só existe como `qtd_esperada` (classe NEGATIVO).
4. Reupload duplicado da mesma tripla `(location, cod, lote)` ⇒ última linha vence + aviso.
5. Odoo indisponível ao gerar base ⇒ erro claro + **rollback** (nada gravado); a contagem só existe quando a extração conclui (§7.1). Você tenta gerar de novo.

## 13. Riscos e decisões

| Item | Decisão / mitigação |
|---|---|
| Extração Odoo lenta (~800 quants) | Síncrona (poucos segundos por filtro). Sem fila RQ. Se um filtro amplo (empresa inteira) passar de ~10s, migrar para job (não no V1). |
| `data_base` envelhece antes da aplicação | `delta_esperado` + guard do átomo cobre; relatório sinaliza idade. |
| Sem lote (`lote=''`) vs NULL | sentinela `''` no parse e na unique. |
| Double-count no Confronto | impossível: `INV` vem de `InventarioBase` + cíclicos (independe do snapshot Odoo) — §6.4. Coberto por teste de regressão. |
| Granularidade da soma | cíclico é por quant; soma no Confronto **agrega por (cod_produto, empresa)** antes de somar à coluna INV da empresa. |
| Corte de data (date × datetime) | comparar por dia (`func.date(data_base) >= data_snapshot`); usuário garante não haver cíclico/inventário no mesmo dia. |
| SC (company 3) | fora do escopo (FB/CD/LF como o resto do módulo); estrutura permite incluir depois. |

## 14. Próximos passos

1. **Usuário revisa este spec** (você lê e dá go/changes).
2. Invocar `superpowers:writing-plans` → plano detalhado em `docs/superpowers/plans/2026-05-31-inventario-ciclico-contagem-ajustes-plan.md` com tasks numeradas e checkpoints.
3. Executar via `superpowers:subagent-driven-development` / `executing-plans` com seus checkpoints.

---

**Referências consultadas:**
- `app/inventario/{models.py, services/confronto_service.py, services/snapshot_odoo_service.py, services/inventario_loader.py, routes/ciclo_routes.py}`
- `scripts/inventario_2026_05/extrair_estoque_locais_emp.py` (extração por quant — origem da planilha 31-05)
- `app/odoo/estoque/scripts/{quant.py, reserva.py, picking.py, transfer.py}` (átomos da aplicação)
- `/mnt/c/Users/rafael.nascimento/Downloads/AJUSTES INVENTARIO 31-05.xlsx` (planilha-referência: 776 quants FB, colunas validadas)
- `docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md` (spec irmão — Confronto)
- Memórias: `[[gotcha_inventory_adjustment_quant_negativo]]`, `[[gotcha_resetar_reserva_orfao_negativo]]`, `[[sequencia_unlink_zerar_residual]]`, `[[gotcha_lote_multiempresa_company_filter]]`, `[[skill2_transfer_interno_pattern]]` (G031)
- Regras: `~/.claude/CLAUDE.md` (migrations, JSON sanitization, menu), `CLAUDE.md` (companies FB=1/CD=4/LF=5)

## Contexto

_A completar (PAD-A Onda 4)._
