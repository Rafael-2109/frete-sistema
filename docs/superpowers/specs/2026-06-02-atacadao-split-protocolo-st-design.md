<!-- doc:meta
tipo: explanation
camada: L3
sot_de: desenho do split de NF por protocolo ST no fluxo Atacadao RJ (leitura PDF -> Odoo)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# Spec — Split de NF por Protocolo ST (Atacadão RJ)

> **Papel deste doc:** desenho aprovado (spec) da quebra de 1 Pedido Atacadão em 2 pedidos Odoo
> conforme protocolo ST, no RJ. Define regra, modelo de dados, pontos de inserção no código,
> UI e testes. **Não** é a implementação — é o blueprint que vira plano.
> **Abra quando:** for revisar/ajustar a regra de split antes/depois da implementação.

**Data**: 2026-06-02 · **Branch**: `worktree-feat-atacadao-split-protocolo-st` · **Status**: Aprovado — em implementação

---

## Indice

- [Contexto](#contexto)
- [Regra de negocio (condicao de split)](#regra-de-negocio-condicao-de-split)
- [Modelo de dados](#modelo-de-dados-2-campos-novos)
- [Componente central — ProtocoloStService](#componente-central--protocolostservice-novo)
- [Fluxo de dados](#fluxo-de-dados-onde-cada-peca-encaixa)
- [UI](#ui)
- [Testes](#testes-pytest-deterministico--sem-llm)
- [Arquivos tocados](#arquivos-tocados-checklist)
- [Riscos / decisoes](#riscos--decisoes)

---

## Contexto

No RJ, o faturamento do Atacadão precisa ser separado em **2 NFs** conforme o tipo de
produto (sujeito a Substituição Tributária — "protocolo ST" — vs demais). Hoje, ao importar
o PDF do Atacadão e lançar no Odoo, **1 filial = 1 `sale.order`** com todos os itens juntos.

Objetivo: quando aplicável, **quebrar 1 Pedido Atacadão em 2 pedidos Odoo** (1 com os produtos
ST, 1 com os demais), mantendo todo o resto do fluxo intacto.

> **Não é** cadastro fiscal de ST por estado. É **apenas separação no pedido**. A ST de fato
> varia por estado, mas o propósito aqui é segregar o lançamento — modelagem simples (bool).

## Regra de negocio (condicao de split)

Para cada filial (CNPJ) de um upload, quebrar em 2 pedidos **se e somente se**:

1. `RegiaoTabelaRede(rede, uf=<uf da filial>, ativo=True).separar_protocolo_st == True`, **E**
2. a filial tem **ambos**: ≥1 item com `protocolo_st=True` **e** ≥1 item com `protocolo_st=False`.

Divisão:
- **Grupo ST** = itens `protocolo_st=True` → 1 `sale.order`
- **Grupo Demais** = itens `protocolo_st=False` → 1 `sale.order`
- Ambos com o **mesmo** `l10n_br_pedido_compra` (decisão do usuário: mesmo nº de pedido de compra).

Caso a condição falhe (UF sem flag, ou só 1 tipo presente) → **comportamento atual** (1 `sale.order`).

Esclarecimentos travados com o usuário:
- ID Odoo: **mesmo `l10n_br_pedido_compra`** nos 2 (Odoo gera 2 VCDs distintos).
- `protocolo_st`: **bool fixo do produto** no De-Para; UF só liga/desliga via `separar_protocolo_st`.
- Abrangência: flag por `(rede, uf)` na `regiao_tabela_rede`; hoje só ATACADAO/RJ.
- Colunas Excel: **incluídas** (import/export) em ambas as telas.
- Item sem De-Para: **não lança, força cadastro** (= bloqueio atual, mantido).
- Sem borda fiscal adicional.

## Modelo de dados (2 campos novos)

| Tabela | Campo | Tipo | Onde |
|---|---|---|---|
| `regiao_tabela_rede` | `separar_protocolo_st` | `BOOLEAN NOT NULL DEFAULT FALSE` | `app/pedidos/validacao/models.py:97` (`RegiaoTabelaRede`) |
| `portal_atacadao_produto_depara` | `protocolo_st` | `BOOLEAN NOT NULL DEFAULT FALSE` | `app/portal/atacadao/models.py:10` (`ProdutoDeParaAtacadao`) — **não** entra na UniqueConstraint |

Migrations (padrão do projeto: `.py` + `.sql` idempotente, sem Alembic):
- `scripts/migrations/2026_06_02_atacadao_protocolo_st.sql` → `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ... BOOLEAN NOT NULL DEFAULT FALSE` (BEGIN/COMMIT) para as 2 tabelas.
- `scripts/migrations/2026_06_02_atacadao_protocolo_st.py` → `create_app()` + before/after via `information_schema.columns`.
- Atualizar os 2 schemas JSON em `.claude/skills/consultando-sql/schemas/tables/`.

## Componente central — ProtocoloStService (novo)

Arquivo: `app/pedidos/services/protocolo_st_service.py` (cria `app/pedidos/services/__init__.py` se faltar).

Três responsabilidades, separando I/O (enriquecimento) de lógica pura (split):

- `enriquecer_itens_raw(itens, rede) -> None` — **I/O** (1 query De-Para).
  Garante `item['protocolo_st']` (default `False`). Para `rede == 'ATACADAO'`: índice
  `codigo_nosso -> any(protocolo_st)` (agregação `any` — robusto, alinhado a "atributo fixo do
  produto"; evita fragilidade de match por CNPJ). Mutação in-place.
- `enriquecer_separar_flag(dados_filiais, rede) -> None` — **I/O** (1 query
  `RegiaoTabelaRede`). Garante `filial['separar_protocolo_st']` (default `False`) por UF.
- `gerar_grupos_lancamento(filial) -> list[dict]` — **PURA** (sem DB). Lê os flags já
  enriquecidos. Retorna 1 ou 2 grupos:
  `{'rotulo_st': 'ST'|'NORMAL'|None, 'itens_odoo': [...], 'tem_divergencia': bool, 'divergencias': [...] | None}`.
  Centraliza a montagem de `itens_odoo` + `divergencias` hoje **duplicada** em sync/async
  (cleanup DRY). Split só quando `separar AND com_st AND sem_st`.

## Fluxo de dados (onde cada peca encaixa)

**Upload (`app/pedidos/leitura/routes.py:upload` ~82):**
1. Após `data_serializable = serialize_data(result['data'])` e resolver `rede`:
   `enriquecer_itens_raw(data_serializable, rede)` → cada item raw ganha `protocolo_st`.
2. `protocolo_st` flui para `dados_brutos` → `dados_filiais.itens` via **1 linha** em
   `PedidoImportacaoTemp.criar_do_upload` (`integracao_odoo/models.py:412-423`):
   `'protocolo_st': bool(produto.get('protocolo_st', False))`.
3. Após `registro_temp = criar_do_upload(...)`:
   `enriquecer_separar_flag(registro_temp.dados_filiais, rede)` e **reatribuir**
   `registro_temp.dados_filiais = <enriquecido>` antes do `add/commit`
   (coluna JSON exige reassign p/ detectar mutação).
4. Response já envia `registro_temp.dados_filiais` → front recebe ambos os flags.

**Lançamento síncrono (`routes.py:inserir_odoo` ~524):**
- Substituir o bloco "monta `itens_odoo` + `criar_pedido_e_registrar` 1x" por:
  `grupos = gerar_grupos_lancamento(filial)`; para cada grupo →
  `criar_pedido_e_registrar(itens=grupo['itens_odoo'], divergente=grupo['tem_divergencia'],
  divergencias=grupo['divergencias'], excluir_order_ids=order_ids_criados, ...)`;
  após sucesso, `order_ids_criados.append(resultado.order_id)`.
- Preservar checagens de `itens_sem_depara` e justificativa por filial.

**Lançamento assíncrono (`routes.py:inserir_lote` ~719 + worker):**
- Ao montar `filiais_dados`: para cada filial, `grupos = gerar_grupos_lancamento(filial)` e
  dar `append` de **1 entrada por grupo** (cada uma com seu `itens_odoo`, `divergencias`,
  `tem_divergencia`, `numero_pedido_cliente` igual, e `rotulo_st`).
- Worker `inserir_pedidos_job.py`: mantém lista `order_ids_criados` e passa
  `excluir_order_ids=order_ids_criados` a cada `criar_pedido`; `append` após sucesso.

**Robustez do poll (`integracao_odoo/service.py`):**
- `criar_pedido(..., excluir_order_ids=None)`: no `poll_fn`, se fornecido,
  `filtros.append(('id', 'not in', excluir_order_ids))`. Default `None` = comportamento atual
  (zero regressão). Necessário porque os 2 pedidos compartilham `l10n_br_pedido_compra` e o
  poll busca por `(partner_id, company_id, l10n_br_pedido_compra) order id desc limit 1`.
- `criar_pedido_e_registrar(..., excluir_order_ids=None)`: pass-through.

## UI

**Telas CRUD (campo editável + Excel):**

- `/pedidos/leitura/regioes`:
  - `regioes.html`: nova coluna "Separar ST" (badge `bg-success` Sim / muted Não); colspan 6→7.
  - `regioes_form.html`: checkbox "Separar Protocolo ST" (sempre visível; `form-check`).
  - `routes.py`: `regioes_criar`/`regioes_editar` aceitam `separar_protocolo_st == 'on'`;
    `regioes_importar` lê coluna opcional `separar_protocolo_st` (create+update);
    `regioes_exportar` adiciona a coluna.
- `/portal/atacadao/depara/listar`:
  - `listar.html`: nova coluna "Protocolo ST" (badge `bg-info` Sim / muted Não); colspan 8→9.
  - `form.html`: switch "Protocolo ST" (espelha o switch "Status").
  - `routes_depara.py`: `novo`/`editar` aceitam `protocolo_st == 'on'`; `importar` lê coluna
    `protocolo st` (create+update); `exportar` + `baixar_modelo` adicionam a coluna.

**Tela `/pedidos/leitura/` (visual — `index.html`, JS `createFilialCard` ~640):**
- Refatorar a montagem da tabela de itens num helper `renderTabelaItens(itens, filial)`.
- Quando `filial.separar_protocolo_st && comSt.length>0 && semSt.length>0`:
  - Badge no header: **"Separação Produtos c/ Protocolo ST"**.
  - 2 seções rotuladas dentro do card ("Com Protocolo ST" / "Demais Produtos"), cada uma com
    sua tabela (helper). Caso contrário, 1 tabela única (comportamento atual).
- Badges seguem `GUIA_COMPONENTES_UI.md` (sem `text-white/text-dark` redundante).

## Testes (pytest deterministico — sem LLM)

`tests/pedidos/test_protocolo_st_service.py`:
- `gerar_grupos_lancamento` (PURO), 4+ cenários:
  - flag OFF → 1 grupo (mesmo com 2 tipos).
  - flag ON + só ST → 1 grupo.
  - flag ON + só Demais → 1 grupo.
  - flag ON + 2 tipos → 2 grupos (ST primeiro), itens corretos por grupo, divergências por grupo.
  - itens sem `nosso_codigo` não entram em `itens_odoo` (grupo pode ficar vazio → omitido).
- Enrichers com DB (fixture `db`): `protocolo_st` por item (any-agg), `separar_protocolo_st` por UF.

## Arquivos tocados (checklist)

**Models/migrations/schemas (6):**
1. `app/pedidos/validacao/models.py` — `+separar_protocolo_st`
2. `app/portal/atacadao/models.py` — `+protocolo_st`
3. `scripts/migrations/2026_06_02_atacadao_protocolo_st.sql`
4. `scripts/migrations/2026_06_02_atacadao_protocolo_st.py`
5. `.claude/skills/consultando-sql/schemas/tables/regiao_tabela_rede.json`
6. `.claude/skills/consultando-sql/schemas/tables/portal_atacadao_produto_depara.json`

**Backend (5):**
7. `app/pedidos/services/protocolo_st_service.py` (+`__init__.py`)
8. `app/pedidos/integracao_odoo/models.py` — 1 linha (`protocolo_st` no item)
9. `app/pedidos/leitura/routes.py` — upload (2 enrich) + inserir_odoo (split) + regioes CRUD/Excel
10. `app/pedidos/workers/inserir_pedidos_job.py` — `excluir_order_ids` tracking
11. `app/pedidos/integracao_odoo/service.py` — `excluir_order_ids` em `criar_pedido`/`_e_registrar`

**Backend De-Para (1):**
12. `app/portal/atacadao/routes_depara.py` — novo/editar/importar/exportar/modelo

**Templates (5):**
13. `app/templates/pedidos/leitura/regioes.html`
14. `app/templates/pedidos/leitura/regioes_form.html`
15. `app/templates/portal/atacadao/depara/listar.html`
16. `app/templates/portal/atacadao/depara/form.html`
17. `app/templates/pedidos/leitura/index.html` (JS)

**Testes (1):**
18. `tests/pedidos/test_protocolo_st_service.py` (+`tests/pedidos/__init__.py` se faltar)

## Riscos / decisoes

- **Poll ambíguo** (2 pedidos mesmo `l10n_br_pedido_compra`): mitigado por `excluir_order_ids`.
- **`protocolo_st` por `any(codigo_nosso)`**: assume consistência do produto (decisão do usuário).
- **Sem split para Assai/Tenda**: só ATACADAO tem De-Para com `protocolo_st`; estrutura
  `(rede, uf)` deixa extensível sem retrabalho.
- **Idempotência/dedup**: o lançamento não bloqueia o 2º pedido da mesma filial (não há trava
  por `numero_documento`; cada `criar_pedido` é independente). Confirmado no código atual.
