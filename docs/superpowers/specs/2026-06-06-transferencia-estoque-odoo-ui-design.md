<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->
# Spec — Transferência de Estoque (Odoo): tela admin unificada (3 modos)

> **Papel:** Spec — tela admin-only para transferir estoque no Odoo em 3 modos (local→local, lote→lote, código→código), com dados ao vivo do código origem e autocomplete.

## Indice

- [1. Objetivo](#1-objetivo)
- [2. Decisões (confirmadas com o dono)](#2-decisões-confirmadas-com-o-dono)
- [3. Arquitetura](#3-arquitetura)
- [4. Backend — services](#4-backend-services)
- [5. Endpoints](#5-endpoints)
- [6. Frontend (tela)](#6-frontend-tela)
- [7. Dados ao vivo do código origem (A/B/C/D)](#7-dados-ao-vivo-do-código-origem-abcd)
- [8. Admin-only + menu](#8-admin-only-menu)
- [9. Tratamento de erros / edge cases / GOTCHAS](#9-tratamento-de-erros-edge-cases-gotchas)
- [10. Espelho local (`MovimentacaoEstoque`)](#10-espelho-local-movimentacaoestoque)
- [11. Lixo a remover](#11-lixo-a-remover)
- [12. Fora de escopo (YAGNI)](#12-fora-de-escopo-yagni)
- [13. Arquivos a criar/modificar](#13-arquivos-a-criarmodificar)
- [14. Testes](#14-testes)
- [15. Checklist de verificação (pré-entrega)](#15-checklist-de-verificação-pré-entrega)
- [Contexto](#contexto)

**Data**: 06/06/2026
**Autor**: Rafael Nascimento (com Claude Code)
**Status**: aguardando revisão do spec → `writing-plans`
**Base**: worktree `feat/transferencia-estoque-odoo-ui` (de `origin/main` @ `4258ca3fb`)

---

## 1. Objetivo

Evoluir a tela existente `/estoque/transferencia-saldo` (`app/estoque/routes.py:2155`, template `transferir_saldo_odoo.html`, hoje **CD-only** e `@login_required`) para uma **tela admin-only unificada** de transferência de estoque no Odoo, com **3 modos** numa mesma página e um painel **ao vivo** do código origem.

Fluxo do usuário: seleciona **empresa** + **modo** → digita o **código origem** (autocomplete) → vê **A** qtd por local, **B** qtd reservada, **C** qtd por lote → preenche os campos do modo → clica **Simular** (dry-run, mostra antes→depois) → clica **Confirmar** (executa).

Os 3 modos:

| Modo | Descrição | O que muda |
|------|-----------|------------|
| **1 — Local → Local** | transferir estoque de um local para outro, mesma empresa | `location` (mesmo código, mesmo lote) |
| **2 — Lote → Lote** | reclassificar saldo entre lotes, mesma empresa | `lote` (mesmo código, mesmo local) |
| **3 — Código → Código** | transferir saldo de um código para outro | `produto` + (opcional) `lote` + (opcional) `local` |

No **Modo 3**, conforme o pedido: seleciona `código origem` + `código destino`; `lote origem` + `lote destino` (**prefill** com o mesmo lote, editável); `local origem` + `local destino` (**prefill** com o mesmo local, editável).

## 2. Decisões (confirmadas com o dono)

| # | Decisão | Detalhe |
|---|---------|---------|
| **D1** | **Simular → Confirmar (2 passos)** | Botão "Simular" roda **dry-run real** (átomos com `dry_run=True`) e mostra preview (qty antes→depois de cada quant, lote a criar, validações). Só então "Confirmar" executa. Espelha o padrão dry-run dos átomos do estoque. |
| **D2** | **Modo 3: código destino livre, com aviso** | Autocomplete livre de qualquer código destino. Se o par **não** estiver em `UnificacaoCodigos`, exibe **aviso amarelo** mas **permite** prosseguir. (A trava dura do service atual em `transferencia_saldo_codigo_service.py:126-129` vira aviso.) |
| **D3** | **Reserva: transferir só o disponível** | Qtd máxima = `quantity − reserved_quantity` por quant escolhido. Bloqueia se a qtd solicitada ultrapassar o disponível — respeita o guard **G027** (`validar_nao_abaixo_reserva=True`). A reserva fica intacta; **sem** opção de override/reset na V1. |
| **D4** | **Admin-only** | Todas as rotas: `@login_required` + `@require_admin` (`app/utils/auth_decorators.py:64`). Link do menu movido para dentro de `{% if current_user.perfil == 'administrador' %}`. |
| **D5** | **Reuso de átomos maduros** | Modo 1 → `StockInternalTransferService.transferir_entre_locations()` (`app/odoo/estoque/scripts/transfer.py:705`); Modo 2 → `transferir_entre_lotes_v2()` (`transfer.py:569`). Sem reimplementar. |
| **D6** | **Síncrono (sem RQ)** | Cada operação são ~2–6 chamadas XML-RPC (~3–10s), dentro do timeout HTTP. Botões com loading. Sem worker/fila na V1 (decisão reversível se aparecer timeout). |
| **D7** | **Intra-empresa apenas** | Os 3 modos operam **dentro de uma empresa**. Transferência entre empresas emite NF (faturamento) e está fora de escopo. Empresas: **FB / CD / LF** (`CODIGO_PARA_COMPANY_ID` em `app/odoo/constants/operacoes_fiscais.py:53`); SC fora do escopo operacional. |
| **D8** | **Espelho local só no Modo 3** | Modo 3 (troca de código) altera o saldo por **código** → grava `MovimentacaoEstoque` (SAÍDA −qty / ENTRADA +qty), como hoje. Modos 1/2 são **net-zero por código** → **não** registram espelho local. |
| **D9** | **Service desacoplado da UI** | Lógica nos services (`transferencia_saldo_codigo_service.py` e `transfer.py`), sem `flask`/`request`/`current_user`; `usuario` entra por parâmetro. Tela e (futura) skill consomem o mesmo service. |

## 3. Arquitetura

Fluxo: **Request → Route (`app/estoque/routes.py`) → Service (Odoo) → Odoo XML-RPC → resposta JSON → Template/JS**.

```
Tela (Jinja + vanilla JS)
  ├─ Empresa (select FB/CD/LF)  +  Modo (1/2/3)
  ├─ Código origem (autocomplete) ── GET /api/dados-codigo ─┐
  │                                                          ▼
  │   Painel ao vivo (A por local · B reservada · C por lote)
  │        StockQuantQueryService.listar_quants()  (consulta_quant.py:66)
  │
  ├─ Form do modo (campos variáveis + autocomplete de local)
  ├─ [Simular] ── POST /api/simular ── service(dry_run=True) ── preview
  └─ [Confirmar] ── POST /api/executar ── service(dry_run=False) ── resultado

Modo 1 → StockInternalTransferService.transferir_entre_locations()  transfer.py:705
Modo 2 → StockInternalTransferService.transferir_entre_lotes_v2()   transfer.py:569
Modo 3 → TransferenciaSaldoCodigoService.transferir_v2()  (NOVO, generalizado)
```

Conexão Odoo: `get_odoo_connection()` (`app/odoo/utils/connection.py:437`), import **lazy** dentro das funções (gotcha de import circular do módulo Odoo).

## 4. Backend — services

### 4.1 Modo 3 — generalizar `TransferenciaSaldoCodigoService`

Novo método (mantém o `transferir()` legado como wrapper fino → retrocompat dos 12 testes atuais + 2 callers em `app/estoque/routes.py:2174,2209`):

```python
def transferir_v2(self, *, company_id, cod_origem, location_id_origem, lote_nome_origem,
                  cod_destino, location_id_destino, lote_nome_destino,
                  qty, usuario, dry_run=False) -> Dict[str, Any]
```

Lógica (reaproveita a sequência madura de `transferir()` em `transferencia_saldo_codigo_service.py:110-198`):

1. Resolver `cod_origem`/`cod_destino` → `product_id` (`resolver_produto`, `:47`).
2. Resolver `lote_nome_origem` no produto origem com filtro `company_id` (`StockLotService.buscar_por_nome`, operador `in` — G036). Herdar `expiration_date`.
3. **Reduzir origem**: `ajustar_quant(product_id=pid_o, company_id, location_id=location_id_origem, lot_id=lot_o, delta=-qty, validar_nao_abaixo_reserva=True, delta_esperado=-qty, dry_run=dry_run)`.
4. Garantir/criar `lote_nome_destino` no produto destino (`criar_se_nao_existe`, validade herdada se `use_expiration_date`).
5. **Aumentar destino**: `ajustar_quant(product_id=pid_d, company_id, location_id=location_id_destino, lot_id=lot_d, delta=+qty, criar_se_faltar=True, delta_esperado=+qty, dry_run=dry_run)`.
6. **Compensação automática** se o aumento falhar (já existe em `:179-190`).
7. **Aviso de par** (D2): retornar `aviso_par=True` se `cod_destino` não estiver em `descobrir_destinos(cod_origem)` (`:93`) — **não** bloqueia.
8. **Espelho local** (D8): `_registrar_movimentacao_local(...)` **somente quando `dry_run=False`**.

Retorno: dict com `status`, `reducao`, `aumento`, `*_antes/_apos`, `lote_criado`, `aviso_par`, `dry_run`.

### 4.2 Modos 1 e 2 — reuso direto (sem alteração)

Ambos já aceitam `dry_run` e retornam dict estruturado:
- Modo 1: `transferir_entre_locations(product_id, company_id, lot_id, qty, location_id_origem, location_id_destino, dry_run=...)`.
- Modo 2: `transferir_entre_lotes_v2(product_id, company_id, location_id, qty, lot_id_origem, lot_id_destino, dry_run=...)`.

`product_id` é resolvido por `cod` via `resolver_produto` (`app/odoo/estoque/_utils.py:43`). `lot_id` resolvido por nome + `company_id` (G021/G036).

## 5. Endpoints

Todos em `app/estoque/`, blueprint `estoque_bp` (`/estoque`, `app/estoque/__init__.py:4`), com `@login_required` + `@require_admin`. Sugerido arquivo dedicado `app/estoque/transferencia_estoque_routes.py` importado pelo `estoque_bp` (mantém `routes.py` enxuto); decisão final na fase de plano.

| Rota | Método | Função |
|------|--------|--------|
| `/estoque/transferencia-estoque` | GET | renderiza a tela |
| `/estoque/transferencia-estoque/api/autocomplete/produto?q=` | GET | `product.product` por `default_code`/`name` ilike → `[{label, cod, product_id, tracking}]` |
| `/estoque/transferencia-estoque/api/autocomplete/local?q=&empresa=` | GET | `stock.location` internas da empresa, ilike `complete_name` → `[{label, location_id, complete_name}]` |
| `/estoque/transferencia-estoque/api/dados-codigo?codigo=&empresa=` | GET | A/B/C agrupados (ver §7) |
| `/estoque/transferencia-estoque/api/simular` | POST | dry-run do modo → preview |
| `/estoque/transferencia-estoque/api/executar` | POST | execução real |

Payload `simular`/`executar`: `{modo, empresa, cod_origem, qty, ...campos do modo}`. `simular` chama o service com `dry_run=True`; `executar` com `dry_run=False`.

## 6. Frontend (tela)

Template novo `app/templates/estoque/transferir_estoque_odoo.html` (substitui o antigo). Layout:

```
┌─ Transferência de Estoque (Odoo) ───────────── [admin] ─┐
│ Empresa: [ FB ▼ ]   Modo: ( )1·Local ( )2·Lote (•)3·Código│
│ Código origem: [ 4729098  ▼autocomplete ]                │
├─ Situação do código origem (ao vivo) ───────────────────┤
│  A·Por Local        | Qtd    | Reservada | Disponível    │
│   CD/Estoque        | 1.200  |   200     |  1.000        │
│  C·Por Lote         | Qtd    | Reservada | Disponível    │
│   139/26            |   800  |   200     |   600         │
├─ Transferência (Modo 3) ────────────────────────────────┤
│  Código destino: [ 4759098 ▼ ]  ⚠ não é par cadastrado   │
│  Lote origem: [139/26 ▼]  Lote destino: [139/26](prefill)│
│  Local origem:[CD/Estoque▼] Local dest:[CD/Estoque](prefill)│
│  Qtd: [ 100 ]   (máx disponível: 600)                    │
│                          [ Simular ]                     │
├─ Preview (após Simular) ────────────────────────────────┤
│  Origem 4729098/139/26: 800 → 700                        │
│  Destino 4759098/139/26: 0 → 100 (lote será criado)      │
│                  [ Confirmar ]  [ Cancelar ]             │
└─────────────────────────────────────────────────────────┘
```

- **Autocomplete**: engine vanilla JS no padrão do projeto (sem libs externas), consumindo os endpoints `/api/autocomplete/*`.
- **Campos por modo** (origem sempre o código do painel):
  - **Modo 1**: lote (select dos lotes com saldo, ou "sem lote") · local origem (select dos locais com saldo) · local destino (autocomplete) · qtd.
  - **Modo 2**: local (select dos locais com saldo) · lote origem (select) · lote destino (texto + autocomplete, **prefill = lote origem**) · qtd.
  - **Modo 3**: código destino (autocomplete) · lote origem (select) · lote destino (texto, **prefill = lote origem**) · local origem (select, **prefill**) · local destino (autocomplete, **prefill = local origem**) · qtd.
- **Limite de qtd**: trava no front em `disponível` (= qtd − reservada) do quant escolhido → respeita D3/G027 antes do backend.
- **Empresas**: FB / CD / LF.

## 7. Dados ao vivo do código origem (A/B/C/D)

`GET /api/dados-codigo` → `StockQuantQueryService(odoo).listar_quants(cods=[codigo], empresas=[empresa])` (`consulta_quant.py:66`). Cada quant traz `location_name`, `lote`, `quantity`, `reserved_quantity`, `available` (`:210-225`). Agrupamento **em memória** (o projeto não usa `read_group`):

- **A · Por local**: `{location_name: {qty, reservada, disponivel}}`.
- **B · Reservada**: soma de `reserved_quantity` (total + por local/lote).
- **C · Por lote**: `{lote: {qty, reservada, disponivel}}`.
- **D · Empresa**: select alimentado por `CODIGO_PARA_COMPANY_ID` (FB/CD/LF). A empresa é escolhida **antes** do código.

Locais "fantasma" (`{emp}/Indisponivel` em `locations.py:45-50`; lotes `MIGRAÇÃO`) são exibidos mas **marcados visualmente** (não são saldo "real"); o admin decide.

## 8. Admin-only + menu

- Rotas: `@login_required` + `@require_admin`.
- `app/templates/_sidebar.html:152`: mover o `<li>` do link para **dentro** de `{% if current_user.perfil == 'administrador' %}` e renomear o label para "Transferir Estoque (Odoo)". Endpoint do `url_for` ajustado para a rota nova.

## 9. Tratamento de erros / edge cases / GOTCHAS

| Caso | Tratamento | Fonte |
|------|------------|-------|
| Produto `tracking='none'` (sem lote) | lote = `None` / quant sem lote | G040 |
| Lote multi-empresa + bug operador `=` | resolver com `company_id` + `['name','in',[...]]` | G021 / G036 (`stock_lot_service.py:26-52`) |
| `reserved_quantity` negativo (ML órfã) | exibir sem quebrar; disponível pode passar de qty | `consulta_quant.py` |
| Guard delta divergente (anti-CICLAMATO) | `delta_esperado` propagado nos `ajustar_quant` | `transfer.py` (G027/delta) |
| Falha no aumento do destino (Modo 3) | compensação automática (re-soma origem) | `:179-190` |
| Código não encontrado / ambíguo | `ValueError` → JSON `{success:false, message}` | `resolver_produto:56-60` |
| Odoo indisponível / timeout | try/except → JSON de erro amigável (sem 500) | padrão das rotas atuais |

Erros retornam `200` com `{success:false, message}` (padrão das rotas existentes em `routes.py:2182-2186`).

## 10. Espelho local (`MovimentacaoEstoque`)

Apenas **Modo 3** e apenas em `executar` (não em `simular`). Reaproveita `_registrar_movimentacao_local` (`:200-235`): SAÍDA `-qty` no código origem + ENTRADA `+qty` no destino, `local_movimentacao='AJUSTE'`, `tipo_origem='MANUAL'`, `criado_por=usuario`. Modos 1/2 não tocam o espelho (net-zero por código).

## 11. Lixo a remover

- Rotas antigas `transferencia-saldo/api/lotes` e `transferencia-saldo/api/executar` (`routes.py:2163-2226`) → substituídas pelos endpoints novos.
- Rota/tela `transferir_saldo_codigo` (`routes.py:2155-2160`) → substituída pela tela nova.
- Template `app/templates/estoque/transferir_saldo_odoo.html` (117 linhas) → removido (substituído por `transferir_estoque_odoo.html`).
- Link antigo no `_sidebar.html:152` → atualizado.

## 12. Fora de escopo (YAGNI)

- Transferência **entre empresas** (emite NF) — usar pipeline de faturamento.
- Operações **assíncronas** (RQ/worker), batch de múltiplos lotes num clique.
- Override/reset de reserva (D3 fixa "só disponível").
- Skill do `gestor-estoque-odoo` para Modos 1/2/3 (service já fica desacoplado para isso; criar sob demanda).

## 13. Arquivos a criar/modificar

| Arquivo | Ação |
|---------|------|
| `app/odoo/services/transferencia_saldo_codigo_service.py` | **modificar**: add `transferir_v2()` genérico; `transferir()` vira wrapper |
| `app/estoque/transferencia_estoque_routes.py` | **criar**: tela + 5 endpoints (importado pelo `estoque_bp`) |
| `app/estoque/routes.py` | **modificar**: remover rotas antigas de transferência-saldo |
| `app/templates/estoque/transferir_estoque_odoo.html` | **criar**: tela unificada 3 modos |
| `app/templates/estoque/transferir_saldo_odoo.html` | **remover** |
| `app/static/js/estoque/transferir_estoque.js` | **criar**: autocomplete + lógica de modo + simular/confirmar |
| `app/templates/_sidebar.html` | **modificar**: link admin-only + label + endpoint |
| `tests/odoo/services/test_transferencia_saldo_codigo_service.py` | **modificar**: add testes de `transferir_v2` |
| `tests/estoque/test_transferencia_estoque_routes.py` | **criar**: admin-only, dados-codigo, simular vs executar |
| `docs/superpowers/specs/INDEX.md` | **modificar**: registrar este spec (PAD-A) |

> **Migrations**: nenhuma (sem DDL — opera Odoo + reusa `MovimentacaoEstoque`).

## 14. Testes

Pytest determinístico (sem evals LLM). Odoo **mockado** (sem chamadas reais nos testes):

- `transferir_v2`: empresa FB/LF, local origem≠destino, lote origem≠destino, `dry_run=True` (não grava espelho), `aviso_par` quando não-par, compensação no aumento.
- Reuso Modos 1/2: smoke com mocks dos átomos (assinatura e propagação de `dry_run`/`delta_esperado`).
- Endpoints: `403` para não-admin; `dados-codigo` agrupa A/B/C; `simular` não persiste, `executar` persiste (Modo 3).
- Retrocompat: `transferir()` legado + os 12 testes atuais verdes.

## 15. Checklist de verificação (pré-entrega)

- [ ] Rotas registradas no `estoque_bp` (importadas em `routes.py`/`__init__.py`).
- [ ] Link no menu (`_sidebar.html`) — admin-only — apontando para a rota nova.
- [ ] `@login_required` + `@require_admin` em **todas** as rotas.
- [ ] Template `extends` correto + JS incluído.
- [ ] Imports lazy do Odoo (sem circular import).
- [ ] Validações front (qtd ≤ disponível) **e** back (G027 via átomos).
- [ ] Dry-run real no `simular`; espelho local só no `executar` (Modo 3).
- [ ] Lixo removido (rotas/template/link antigos).
- [ ] Testes verdes (novos + 12 legados).
- [ ] Spec registrado no `docs/superpowers/specs/INDEX.md`.

---

## Contexto

Spec da feature pedida em 06/06/2026 (tela admin de transferência de estoque Odoo em 3 modos). Sucede e generaliza o spec `2026-05-22-transferencia-saldo-codigos-odoo-design.md` (que cobria só o Modo 3 em CD/Estoque). Próximo passo após revisão: `writing-plans` → implementação na worktree `feat/transferencia-estoque-odoo-ui`.
