# Spec — Transferência de saldo entre códigos (Odoo) mantendo lote

**Data**: 22/05/2026
**Autor**: Rafael Nascimento (com Claude Code)
**Status**: aguardando revisão do spec → `writing-plans`
**Prova de conceito**: transferência real executada em 22/05 (4729198→4759198, 5 cx, lote 135/26, CD/Estoque): origem 290→285, destino 2→7. Mecânica validada em produção.

---

## 1. Objetivo

Tela + endpoint no módulo `app/estoque` para transferir saldo de estoque de um **código de produto** para outro, **mantendo o mesmo nome de lote**, em **CD/Estoque** (Odoo `company_id=4`, `location_id=32`), usando os pares cadastrados em `UnificacaoCodigos`.

Fluxo do usuário: digita um código → vê os lotes desse código em CD/Estoque (saldo Odoo) → em cada lote, informa uma quantidade e clica **Transferir** → o saldo vai para o código par, no mesmo lote (criado se não existir).

## 2. Decisões (confirmadas com o dono)

| # | Decisão | Detalhe |
|---|---------|---------|
| D1 | **Direção bidirecional** | A partir do código X, "o outro código" é o par relacionado em `UnificacaoCodigos` (X como origem **ou** destino). Se X tiver mais de um par ativo, o usuário escolhe o destino numa lista. |
| D2 | **Odoo + local** | Ajusta os quants no Odoo **e** cria `MovimentacaoEstoque` local espelhando a troca (saída do código origem + entrada no destino). |
| D3 | **Efetiva direto** | Sem dry-run no servidor e **sem etapa de confirmação**: clicar Transferir executa. (Opcional, a seu critério: um `confirm()` JS instantâneo como proteção mínima — fica desligado por padrão para respeitar a decisão.) |
| D4 | **Acesso via menu** | Item no menu **"Carteira e estoque"** (`base.html`/`_sidebar.html`). |
| D5 | **1 lote por clique (síncrono)** | Botão por linha = 2 chamadas Odoo (~5–15s) com loading. Sem batch/worker na V1. |
| D6 | **Service desacoplado da UI** | Toda a lógica vive no `TransferenciaSaldoCodigoService` (sem `flask`/`request`/`current_user` dentro dele — `usuario` entra por parâmetro). Razão: a função vira **skill** do subagente `gestor-estoque-odoo` (planejado, ainda não existe em 22/05/2026). Tela e skill consomem o mesmo service. |

## 3. Arquitetura

```
Tela transferir_saldo_odoo.html (menu "Carteira e estoque")
  1. digita código X            → GET  /estoque/transferencia-saldo/api/lotes?codigo=X
  2. tabela de lotes + destino(s)
  3. qty + [Transferir] (confirm)→ POST /estoque/transferencia-saldo/api/executar
        ▼
estoque_bp (app/estoque/routes.py)
        ▼
TransferenciaSaldoCodigoService (app/odoo/services/)           [átomo de escrita Odoo; imports lazy de estoque]
  ├─ resolver_produto(cod) .......... product.product.default_code → product_id (+uom, tracking, use_expiration_date)
  ├─ listar_lotes_cd_estoque(cod) ... stock.quant (company 4, loc 32) → lote/qtd/reservado/disponível/validade
  ├─ descobrir_destinos(cod) ........ UnificacaoCodigos.get_todos_codigos_relacionados (bidirecional)
  └─ transferir(...) ................ StockQuantAdjustmentService ×2  (reduzir origem / aumentar destino)   [Odoo]
                                      + StockLotService.criar_se_nao_existe (lote destino, com validade)     [Odoo]
                                      + MovimentacaoEstoque ×2 (SAIDA origem + ENTRADA destino)              [DB local]
```

**Primitivas reusadas (já testadas):**
- `StockQuantAdjustmentService.ajustar_quant()` — `app/odoo/services/stock_quant_adjustment_service.py:94` (delta, `criar_se_faltar`, `validar_nao_negativar`, `validar_nao_abaixo_reserva`).
- `StockLotService.criar_se_nao_existe()` — `app/odoo/services/stock_lot_service.py:100` (filtra `(nome, product_id, company_id)`; aceita `expiration_date`).
- `COMPANY_LOCATIONS` — `app/odoo/constants/locations.py` (CD = company 4 / loc 32).
- `UnificacaoCodigos.get_todos_codigos_relacionados()` — `app/estoque/models.py:307`.

## 4. Contrato do service (`TransferenciaSaldoCodigoService`)

| Método | Entrada | Saída / comportamento |
|--------|---------|-----------------------|
| `resolver_produto(cod)` | `cod: str` | `{product_id, name, tracking, uom, use_expiration_date}`. Erro se 0 ou >1 produto ativo com esse `default_code`. |
| `listar_lotes_cd_estoque(cod)` | `cod: str` | `[{lote_nome, lot_id, quantidade, reservado, disponivel, is_migracao, expiration_date}]` (company 4, loc 32). `disponivel = quantidade − reservado`. |
| `descobrir_destinos(cod)` | `cod: str` | `[{codigo, nome}]` — pares ativos relacionados, excluindo o próprio. Lista vazia ⇒ sem par cadastrado. |
| `transferir(cod_origem, cod_destino, lote_nome, qty, usuario)` | strings + float | Executa os 2 ajustes Odoo + espelho local + auditoria. Retorna `{status, origem_antes/apos, destino_antes/apos, lote_criado, erro?}`. |

## 5. Criação de lote no destino + GOTCHAS (atenção especial)

Ao transferir para um lote que **não existe** no produto destino, criar via `StockLotService.criar_se_nao_existe(lote_nome, product_id_destino, company_id=4, expiration_date=<validade do lote ORIGEM>)`. Gotchas confirmados no Odoo (22/05):

| Gotcha | Evidência | Tratamento |
|--------|-----------|------------|
| **Validade não propaga** | `GOTCHAS.md:447` (`lot_name` não propaga `expiration_date`). Ambos os produtos do teste têm `use_expiration_date=True`. | Ler `expiration_date` do **lote origem** e passá-la ao criar o lote destino. Se origem sem validade e produto exige, registrar aviso. |
| **Mesmo nome em N companies/produtos** | nome `135/26` existe em **56 lotes** (FB 28, CD 22, LF 6). | SEMPRE filtrar por `product_id` **e** `company_id=4`. `StockLotService` já faz; o orquestrador deve passar os 3 corretos. Não filtrar ⇒ "Empresas incompatíveis" no Odoo. |
| **Bug operador `=`** | `stock.lot.search` com `=` retorna vazio intermitente. | `StockLotService.buscar_por_nome` já usa `in` + fallback `=like`. |
| **Unique constraint** `(name, product_id, company_id)` | criação concorrente | `criar_se_nao_existe` captura duplicate e retorna o existente. |
| **Validade divergente por produto** | mesmo nome com validades diferentes (origem CD 2028-05-15, destino CD 2028-05-18) | Replicar a do **lote origem** (decisão); se o lote destino já existe, **não** sobrescrever a validade existente. |
| **Quant sem lote** (`lot_id=False`) | quants podem não ter lote | Transferir "sem lote" → "sem lote" no destino (não inventar nome). |

## 6. Tratamento de erros / atomicidade

A operação são 2 ajustes. Ordem: **reduzir origem → aumentar destino**. Se o aumento falhar após a redução real, **compensar** (re-aumentar a origem) e retornar erro — nunca deixar estoque "sumido". Auditar via `OperacaoOdooAuditoria`.

Bloqueios herdados das primitivas (retornam erro claro, sem gravar):
- `qty > disponível` (reserva) → `FALHA_RESERVADO`.
- `qty_apos < 0` → `FALHA_QUANT_NEGATIVO` (não inflar negativos — `gotcha_inventory_adjustment_quant_negativo`).
- produto inexistente / par não cadastrado / `tracking ≠ lot` → erro de validação antes de qualquer write.

## 7. Validações

- **Frontend**: código preenchido; `qty` numérica `> 0` e `≤ disponível` (input limitado); destino selecionado quando houver >1 par. (`confirm()` antes do POST = opcional, ver D3.)
- **Backend**: produto origem/destino existem (1 ativo cada); par válido e ativo em `UnificacaoCodigos`; `qty>0`; `qty ≤ disponível` do lote; `tracking='lot'`. Decorator de permissão das rotas vizinhas de `estoque_bp`.

## 8. Espelho local (`MovimentacaoEstoque`)

2 registros: `SAIDA` (cod_origem) + `ENTRADA` (cod_destino), ambos `local_movimentacao='AJUSTE'`, `tipo_origem='MANUAL'`, `lote_nome=<lote>`, `qtd_movimentacao=qty`, `observacao` referenciando a transferência. **Não duplica com o sync**: `entrada_material_service.py:359` importa apenas `picking_type_code='incoming'`; inventory adjustment não gera picking de entrada. (O estoque local não tem dimensão de empresa — o reflexo é no saldo global do código; coerente com a unificação, que soma os pares.)

## 9. Fora de escopo (YAGNI)

- Transferência em batch / múltiplos lotes num clique (worker RQ + polling) — só se houver demanda.
- Dry-run/preview no servidor (D3 = efetiva direto).
- Outras companies/locations além de CD/Estoque (FB, Indisponível, Pré-Produção).
- Sentido fixo origem→destino (D1 = bidirecional).

## 10. Arquivos a criar/modificar

| Ação | Arquivo | Conteúdo |
|------|---------|----------|
| CRIAR | `app/odoo/services/transferencia_saldo_codigo_service.py` | `TransferenciaSaldoCodigoService` (4 métodos da §4). Junto dos átomos-irmãos (`stock_quant_adjustment_service`, `stock_internal_transfer_service`, `stock_lot_service`); imports lazy de `UnificacaoCodigos`/`MovimentacaoEstoque`. Alinha com a futura skill do `gestor-estoque-odoo`. |
| MODIFICAR | `app/estoque/routes.py` (`estoque_bp`) | 3 rotas: tela (GET), `api/lotes` (GET), `api/executar` (POST). |
| CRIAR | `app/templates/estoque/transferir_saldo_odoo.html` | Input código → tabela lotes + seletor destino + AJAX/loading. |
| MODIFICAR | `app/templates/base.html` (e/ou `_sidebar.html`) | Item no menu "Carteira e estoque". |
| — | (sem migration) | Usa `UnificacaoCodigos` e `MovimentacaoEstoque` existentes; sem DDL. |

## 11. Checklist de verificação (pré-entrega)

- [ ] Rota registrada no `estoque_bp`; métodos HTTP corretos.
- [ ] Link no menu "Carteira e estoque" (`base.html`) → tela acessível.
- [ ] `resolver_produto` trata 0/>1 produto.
- [ ] Lote criado com `expiration_date` do lote origem quando `use_expiration_date=True`.
- [ ] Lote resolvido/criado SEMPRE com `product_id` + `company_id=4`.
- [ ] Compensação testada (aumento falha após redução).
- [ ] Bloqueio de `qty > disponível` (reserva) no front e no back.
- [ ] Espelho local: 2 `MovimentacaoEstoque` (SAIDA+ENTRADA), sem duplicar sync.
- [ ] Validações front + back.
