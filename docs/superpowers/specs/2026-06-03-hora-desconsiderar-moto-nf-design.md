<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# HORA — Desconsiderar moto de NF de compra

> **Papel:** spec de design da funcionalidade de "desconsiderar" um item (moto) de uma NF de entrada no módulo HORA, removendo-o do estoque/recebimento sem apagar o registro fiscal da NF.

## Indice

- [Contexto](#contexto)
- [Escopo](#escopo)
- [Decisões aprovadas (Q&A)](#decisões-aprovadas-qa)
- [Máquina de estados do item da NF](#máquina-de-estados-do-item-da-nf)
- [Modelo de dados](#modelo-de-dados)
- [Serviços](#serviços)
- [Efeito nos demais locais](#efeito-nos-demais-locais)
- [UI e rotas](#ui-e-rotas)
- [Migration](#migration)
- [Não-objetivos](#não-objetivos)
- [Testes](#testes)
- [Riscos e pontos de atenção](#riscos-e-pontos-de-atenção)

## Contexto

No fluxo de entrada da HORA (Motochefe → HORA), uma NF de compra (`hora_nf_entrada`) é importada por DANFE PDF e gera um `HoraNfEntradaItem` por chassi. Cada item, no import, faz `get_or_create_moto` → cria a `HoraMoto` (identidade insert-once). O estoque é derivado de eventos (`hora_moto_evento`): uma moto só fica "em estoque" quando recebe o evento `RECEBIDA`/`CONFERIDA`, que nasce **no recebimento físico** — não no import.

**Problema de negócio**: algumas NFs são emitidas para **outra empresa**. Dentro dessas NFs há motos que **não são da HORA**. A HORA paga essas motos direto ao fornecedor e **evita pedir refaturamento** à outra empresa. Hoje não há como marcar essas motos: ao importar a NF, todas viram `HoraMoto` e ficam elegíveis a recebimento/estoque indevidamente.

**Solução**: permitir **desconsiderar** um item da NF — marcá-lo com um flag que o remove do estoque e do recebimento, removendo também o cadastro da moto, mas **mantendo** o item na NF (registro fiscal, reversível).

Fontes do estado atual:
- `app/hora/models/compra.py:117` (`HoraNfEntrada`), `:180` (`HoraNfEntradaItem`, FK `numero_chassi` NOT NULL → `hora_moto`).
- `app/hora/services/nf_entrada_service.py:71` (`importar_danfe_pdf`, cria moto por item).
- `app/hora/services/estoque_service.py:23` (`EVENTOS_EM_ESTOQUE`; estoque = último evento da moto).
- `app/hora/services/recebimento_service.py` (recebimento itera `rec.nf.itens`; ~15 pontos).
- `app/hora/services/chassi_protecao_service.py:14` (`chassi_protegido`).

## Escopo

**Dentro do escopo**: marcar/reverter a desconsideração de um item de NF de entrada; validações de pré-condição; remoção/recriação da `HoraMoto`; exclusão do item desconsiderado do recebimento e do confronto; UI no detalhe da NF.

**Fora do escopo (descartado pelo usuário)**: a relação Pedido↔NF e a loja de destino **permanecem no header** (`hora_nf_entrada.pedido_id` / `loja_destino_id`), como hoje. Não há vínculo de pedido/loja por item da NF (Tarefa originalmente proposta e descartada por ser desproporcional ao caso específico). Não há fluxo financeiro de "pagar direto ao fornecedor" (módulo ainda não tem títulos a pagar — Fase 2 futura).

## Decisões aprovadas (Q&A)

| ID | Decisão | Fonte |
|----|---------|-------|
| D1 | Moto desconsiderada **NÃO entra no estoque** físico da loja. | usuário |
| D2 | Desconsideração é **por item** (uma NF pode ter motos normais e desconsideradas misturadas). | usuário |
| D3 | "Estar com pedido" (bloqueia desconsiderar) = chassi presente em algum `HoraPedidoItem`. | usuário |
| D4 | Ao desconsiderar, **remover** a `HoraMoto` de `hora_moto` (evita "moto fantasma" no cadastro). | usuário |
| D5 | Desconsiderar = **flag reversível** no item (mantém o registro na NF; não apaga o item). | usuário |
| D6 | Regra de ordem: só desconsiderar se a moto **não estiver com pedido** e **não tiver sido recebida**. Item com pedido só pode ser desconsiderado se desvinculado antes (fluxo de pedido existente). | usuário |

## Máquina de estados do item da NF

Dois estados (mutuamente exclusivos) + trava por pré-condição:

```
CONSIDERADO (default, tem HoraMoto)
   │  desconsiderar  [valida: não em pedido, não recebido, sem refs bloqueantes] → deleta HoraMoto
   ▼
DESCONSIDERADO (desconsiderado=True, SEM HoraMoto)
   │  reverter → recria HoraMoto via get_or_create_moto
   ▲
   └────────────────────────────────────────────────────────────────
```

**Invariantes**:
- **INV-1**: item `desconsiderado=True` ⇒ não existe `HoraMoto` com aquele chassi (a menos que o mesmo chassi exista por outra NF/origem — ver INV-3).
- **INV-2**: não desconsiderar se o chassi consta em `HoraPedidoItem` (D3/D6).
- **INV-3**: não desconsiderar se o chassi já foi **recebido** (evento `RECEBIDA`/`CONFERIDA` ou conferência ativa em `hora_recebimento_conferencia`) ou está referenciado em qualquer fluxo de saída/movimentação (venda, avaria, transferência, empréstimo, devolução) ou em outro `HoraNfEntradaItem` **considerado**. Nestes casos a `HoraMoto` não pode ser removida com segurança → operação abortada com mensagem explicativa.

## Modelo de dados

Arquivo: `app/hora/models/compra.py` — `HoraNfEntradaItem`.

**Novo campo**:
```python
desconsiderado = db.Column(db.Boolean, nullable=False, default=False, server_default='false', index=True)
```

**Relaxar a FK** `numero_chassi → hora_moto` (ponto estrutural):
- Hoje: `numero_chassi = db.Column(db.String(30), db.ForeignKey('hora_moto.numero_chassi'), nullable=False, index=True)` (`compra.py:191`).
- Novo: manter a coluna `String(30)` NOT NULL (sempre o chassi declarado na NF), **sem** a `ForeignKey` constraint. Motivo: ao desconsiderar deletamos a `HoraMoto`, e o item precisa permanecer com o chassi.
- `relationship('moto')` passa a `viewonly=True` com `primaryjoin` explícito sobre `HoraMoto.numero_chassi == HoraNfEntradaItem.numero_chassi` (via `foreign()`), resolvendo a moto quando ela existe. O backref `HoraMoto.nfs_entrada_itens` segue o mesmo ajuste.

> A FK das demais tabelas para `hora_moto.numero_chassi` (14 no total — pedido, conferência, venda, avaria, transferência, empréstimo, devolução, peça faltando, evento) **não muda**; a remoção da moto é protegida pela validação INV-2/INV-3, que garante ausência dessas referências antes do delete.

### Validação aplicativa no lugar da FK (aprovado)

Como a constraint `numero_chassi → hora_moto` deixa de existir, a integridade que ela garantia passa a ser assegurada por **validação na aplicação** (decisão do usuário, 2026-06-03):

- **Integridade item↔moto** (invariante de aplicação, coberta por teste):
  - `desconsiderado = False` ⇒ existe `HoraMoto(numero_chassi)`.
  - `desconsiderado = True` ⇒ não existe `HoraMoto(numero_chassi)` (salvo chassi compartilhado por outra origem — caso barrado por INV-3, logo não ocorre).
  - Mantida pelos três únicos pontos de escrita: import (cria moto p/ item considerado), `desconsiderar_item_nf` (deleta moto), `reconsiderar_item_nf` (recria moto).
- **Proteção do delete** (substitui o `RESTRICT` referencial perdido): antes de remover a `HoraMoto`, `desconsiderar_item_nf` verifica **explicitamente** todas as referências ao chassi (INV-2/INV-3) e **aborta** (rollback) se houver qualquer uma — nunca delete em cascata.
- **Helper de verificação** `assert_item_moto_consistente(item)` (uso em testes/diagnóstico) valida a invariante para um item.

## Serviços

Arquivo: `app/hora/services/nf_entrada_service.py` (novos serviços) + helper de pré-condição.

### `desconsiderar_item_nf(nf_item_id, operador=None) -> dict`
1. Carrega `HoraNfEntradaItem`; se já `desconsiderado` → erro/no-op idempotente.
2. **INV-2** — chassi em `HoraPedidoItem`? Se sim → `ValueError("Moto {chassi} consta no pedido {n}; desvincule do pedido antes de desconsiderar.")`.
3. **INV-3** — chassi recebido (evento `RECEBIDA`/`CONFERIDA` ou conferência ativa) ou referenciado em venda/avaria/transferência/empréstimo/devolução/peça-faltando, ou presente em outro `HoraNfEntradaItem` considerado? Se sim → `ValueError` com o motivo específico.
4. `item.desconsiderado = True`.
5. Deleta a `HoraMoto` do chassi (e eventos órfãos, se houver — não deveria haver). Se o delete encontrar dependência inesperada, **aborta** (rollback) com erro claro.
6. `commit` + log (`current_app.logger.info`).
7. Retorna `{ok, nf_item_id, numero_chassi}`.

### `reconsiderar_item_nf(nf_item_id, operador=None) -> dict`
1. Carrega item `desconsiderado=True` (senão erro).
2. Recria a `HoraMoto` via `get_or_create_moto(numero_chassi, modelo_texto_original, cor_texto_original, numero_motor_texto_original, ...)` — mesmo fluxo do import (com `fallback_sentinela`/pendência de modelo).
3. `item.desconsiderado = False`.
4. `commit` + log. Retorna `{ok, nf_item_id, numero_chassi}`.

### Helper de pré-condição
`chassi_em_pedido(numero_chassi) -> bool` (em `chassi_protecao_service.py`): `EXISTS(HoraPedidoItem.numero_chassi == chassi)`. **Não** reusar `chassi_protegido` (que inclui `HoraNfEntradaItem` e daria sempre `True` aqui).

## Efeito nos demais locais

Helper único: `itens_considerados(nf) -> list[HoraNfEntradaItem]` = `[i for i in nf.itens if not i.desconsiderado]`.

**Recebimento** (`app/hora/services/recebimento_service.py`) — substituir `nf.itens` por `itens_considerados(nf)` nos pontos que tratam itens "a receber":
- `criar_recebimento` / `criar_recebimento_automatico_da_nf` — laço de conferências e `qtd_declarada`.
- `listar_nfs_para_recebimento_automatico` — `qtd_motos_nf`, lista de `chassis`.
- `definir_qtd_declarada`, cálculo de faltantes (`chassis_nf`), esperados, contagens.

**Confronto/matching** (`app/hora/services/matching_service.py`): `_chassis_nf` exclui desconsiderados (uma moto desconsiderada nunca está em pedido, mas a exclusão mantém a contagem coerente).

**Estoque** (`app/hora/services/estoque_service.py`): nenhuma mudança ativa — estoque deriva de evento da moto; item desconsiderado não tem moto nem evento. Verificar no plano que nenhum ponto do `estoque_service` conta "esperado" a partir de `HoraNfEntradaItem`.

**Detalhe da NF**: continua listando **todos** os itens (incluindo desconsiderados, marcados) — não usa `itens_considerados`.

## UI e rotas

**Template** `app/templates/hora/nf_detalhe.html`:
- Por item: badge "Desconsiderada" quando aplicável.
- Botão **Desconsiderar** (item considerado e elegível) / **Reverter** (item desconsiderado).
- Botão desabilitado com tooltip do motivo quando bloqueado (em pedido / recebido).
- Itens desconsiderados visualmente atenuados e fora das contagens de "a receber" exibidas.

**Rotas** `app/hora/routes/nfs.py` (perm `require_hora_perm('nfs', 'editar')`):
- `POST /hora/nfs/<nf_id>/itens/<item_id>/desconsiderar`
- `POST /hora/nfs/<nf_id>/itens/<item_id>/reverter`
- Padrão de resposta do módulo: `return jsonify(...), N` (ver memória `app_abort_4xx_gotcha`).

Acesso via UI já garantido (tela de detalhe da NF tem link no menu de NFs).

## Migration

Dual (`scripts/migrations/hora_NN_desconsiderar_item.{py,sql}`), idempotente:
- `ALTER TABLE hora_nf_entrada_item ADD COLUMN IF NOT EXISTS desconsiderado BOOLEAN NOT NULL DEFAULT false;`
- `DROP CONSTRAINT` da FK `numero_chassi → hora_moto` (descobrir o nome real via `information_schema`; `DROP CONSTRAINT IF EXISTS`).
- Índice em `desconsiderado` (opcional; filtros são por NF).
- **Sem backfill de dados** (default `False` cobre o legado).
- `.py` com `create_app()` + verificação before/after (regra de migrations duais do `~/.claude/CLAUDE.md`).

## Não-objetivos

- Vínculo de pedido/loja **por item** da NF (descartado).
- Fluxo financeiro / títulos a pagar (Fase 2 futura).
- Desconsiderar peças (`hora_nf_entrada_item_peca`) — escopo é só motos; reavaliar se surgir demanda.
- Desconsiderar em lote (v1 é item a item; lote pode vir depois se necessário).

## Testes

`tests/hora/test_desconsiderar_item_nf.py`:
- Desconsiderar item elegível → `desconsiderado=True` e `HoraMoto` removida.
- Reverter → `HoraMoto` recriada, `desconsiderado=False`.
- Bloqueio quando chassi em `HoraPedidoItem` (mensagem aponta o pedido).
- Bloqueio quando chassi recebido (evento/conferência).
- Bloqueio quando chassi em outro item de NF considerado / venda / avaria.
- Recebimento ignora itens desconsiderados: `qtd_declarada` e faltantes não os contam; recebimento automático não cria conferência para eles.
- Idempotência: desconsiderar 2x e reverter 2x não quebram.

## Riscos e pontos de atenção

- **Relaxar a FK** `numero_chassi` afeta todos os itens da NF (perde integridade referencial formal do item → moto). Mitigação: a integridade "item considerado tem moto" passa a ser garantida pela lógica de transição + testes. É o único ponto estrutural; revisar com atenção no plano.
- **Remoção da moto**: precisa varrer todas as 14 FKs para `hora_moto`. A validação INV-2/INV-3 cobre as relevantes; o delete deve **abortar** (não forçar) se encontrar dependência inesperada.
- **Mesmo chassi em duas NFs**: se o chassi existe em outro `HoraNfEntradaItem` considerado, a moto não pode ser removida → desconsideração abortada (INV-3).
- **Ordem dos fatores** (D6): a UI deve refletir claramente que vincular/desvincular pedido e receber são gates — botão de desconsiderar bloqueado com motivo.
