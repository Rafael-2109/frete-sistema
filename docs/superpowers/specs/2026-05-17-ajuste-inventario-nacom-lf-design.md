# Spec — Ajuste de Inventário NACOM/LF + Infraestrutura Reutilizável

**Data**: 17/05/2026
**Autor**: Rafael Nascimento (com Claude Code)
**Versão**: v2 (reescrita após audit dos services existentes)
**Status**: aguardando aprovação para gerar plano de implementação (`writing-plans`)
**Origem**: `app/agente/prompts/prompt_inventario.md` (v2)

---

## 1. Filosofia (orientação do dono do projeto)

> "Faça esse trabalho 1 shot com documentação e referências suficientes para que, após a implementação, você agrupe os conhecimentos adquiridos para criar features atômicas que poderão no futuro se tornar operações como um novo inventário."

Consequência direta para este spec:

- **Nada de service por CFOP.** A matriz CFOP × tipo produto × direção é **dado**, não código.
- **Reusar agressivamente o que já existe** em `lancamento_odoo_service.py`, `recebimento_lf_odoo_service.py`, `recebimento_fisico_odoo_service.py`, `emissao_nf_pallet.py`. Extrair, parametrizar, wrappear — não refazer.
- **Operações diárias primeiro, inventário depois.** Os serviços novos devem ser invocáveis fora do contexto "inventário 05/2026".
- **Features atômicas extraídas DEPOIS** — skills, telemetria, UI virão após a operação concluída.

## 2. Objetivo

Conduzir os ajustes de estoque do inventário físico de 16/05/2026 nas empresas:

- **NACOM GOYA**: FB (`company_id=1`, matriz/fábrica), CD (`company_id=4`, centro de distribuição). SC (`company_id=3`) **fora de escopo**.
- **LA FAMIGLIA** (`company_id=5`), prestadora de serviço de industrialização.

Os ajustes saem por **NF entre empresas** (4 CFOPs), **alteração de lote** e **indisponibilização** (lote ou local) — sempre seguindo as ordens 1→2→3 definidas no prompt original.

**Saídas esperadas:**

1. Estoque **disponível e visível para operação diária** ajustado conforme inventário em FB, CD e LF
2. Estoque a ajustar contabilmente **segregado deterministicamente e invisível ao faturamento** (ordem=3)
3. **3 services genéricos + 1 arquivo de constantes** em `app/odoo/`, consumíveis por operações diárias
4. **1 tabela de auditoria polimórfica** (`operacao_odoo_auditoria`) substituindo o padrão fretes-específico
5. **2 playbooks** em `.claude/references/odoo/` documentando o conhecimento extraído
6. **Documentação atômica** completa em `docs/inventario-2026-05/`

## 3. Escopo

### 3.1 Dentro

- 4 CFOPs (5152, 5901, 5903, 5949) executados via 1 service genérico parametrizado
- Alteração/criação de lote (P9 do prompt — caso qtd_igual + lote_diferente)
- Indisponibilização por lote OU por local (com canary técnico antes)
- Extração de constantes hoje espalhadas em 3 services
- Tabela de auditoria genérica + tabela enxuta de controle do ciclo de inventário
- Pipeline em ondas com canary fiscal por CFOP e canary técnico para ordem=3
- Hooks determinísticos
- Documentação atômica + 2 playbooks reutilizáveis

### 3.2 Fora

- **SC** (`company_id=3`) — usuário confirmou fora de escopo nesta fase
- **Período fiscal** das NFs — usuário confirmou fora de escopo
- **Skill invocável** pelo agente web — será extraída DEPOIS da operação concluída, conforme filosofia §1
- **Refator completo** de `lancamento_odoo_service.py` ou `recebimento_lf_odoo_service.py` — apenas extração mínima de funções genéricas; serviços existentes seguem operando
- Mudanças no Odoo ERP (módulos, views, fields)

## 4. Premissas confirmadas

| ID | Premissa | Origem |
|----|----------|--------|
| P1 | Produtos 1/2/3 em LF negativos: NF **perda** LF→FB CFOP 5903 | `prompt_inventario.md:46-48` |
| P2 | Produtos 1/2/3 em LF positivos: NF **industrializacao** FB→LF CFOP 5901 | `prompt_inventario.md:47` |
| P3 | Produtos 4 em LF (qualquer sinal): NF **dev-industrializacao** CFOP 5949, bidirecional | `prompt_inventario.md:50` |
| P4 | Produtos 4 em FB com ajuste: transferir CD→FB para FB ficar correto; diferença real permanece no CD (ordem=2) | `prompt_inventario.md:56` |
| P5 | Produtos 1/2/3 em CD com ajuste: transferir CD→FB para CD ficar correto; diferença real permanece em FB | `prompt_inventario.md:57` |
| P6 | Prioridade de lote: (1) inventariado, (2) MIGRAÇÃO, (3) mais antigo | resposta usuário 17/05 |
| P7 | Criação de lote respeita o nome do lote inventariado | resposta usuário 17/05 |
| P8 | Custo unitário das NFs = custo médio Odoo na data (`stock.quant.value/quantity`) | resposta usuário 17/05 |
| P9 | Divergência apenas de lote (qty igual, lote diferente): renomear lote do produto no Odoo se possível | `prompt_inventario.md:135` |
| P10 | Indisponibilização (ordem=3) é **independente** dos ajustes por NF — segrega estoque visível × estoque pendente de ajuste contábil | interpretação do `<estado_desejado>` item 4 |

## 5. Glossário operacional

### 5.1 Empresas (IDs Odoo)

| Codigo | CNPJ | `company_id` | `picking_type_id` | `location_id` estoque |
|--------|------|--------------|-------------------|----------------------|
| FB | 61724241000178 | 1 | 1 | 8 (a confirmar via audit run) |
| SC | 61724241000259 | 3 | 8 | (fora de escopo) |
| CD | 61724241000330 | 4 | 13 | 32 (a confirmar) |
| LF | 18467441000163 | 5 | 16 | (a descobrir no F0) |

Fontes: `.claude/references/odoo/IDS_FIXOS.md`; `app/recebimento/services/recebimento_lf_odoo_service.py:73-80`; `app/pallet/services/emissao_nf_pallet.py:35-82`.

### 5.2 Matriz operações fiscais inter-company (a consolidar em `constants/operacoes_fiscais.py`)

| CFOP | `l10n_br_tipo_pedido` | `move_type` | Direção | Tipo produto | NF referência | Service padrão usado |
|------|------------------------|-------------|---------|--------------|---------------|---------------------|
| 5152 | transf-filial | out_invoice | CD↔FB | 1/2/3/4 | NF 94410 | `account_move_intercompany_service` |
| 5901 | industrializacao | out_invoice | FB→LF | 1/2/3 | NF 94457 | idem |
| 5903 | perda | out_invoice | LF→FB | 1/2/3 | NF 13075 | idem |
| 5949 | dev-industrializacao | out_invoice | FB↔LF | 4 | NF 147772 | idem |

Cada combinação `(CFOP, direção)` mapeia para um `fiscal_position_id` específico. **Toda essa matriz vira dado em arquivo de constantes** — service genérico recebe `tipo_operacao` como string e lê a matriz.

## 6. Arquitetura — fundamentada no audit

### 6.1 Princípio

Após audit, ficou claro que **90% do que preciso já existe** no codebase, espalhado em 3 services. A estratégia é:

- **Extrair** funções genéricas para `app/odoo/services/` (novos serviços que envolvem helpers existentes)
- **Consolidar** constantes hoje distribuídas em `app/odoo/constants/operacoes_fiscais.py`
- **Generalizar** a tabela de auditoria (`operacao_odoo_auditoria` polimórfica)
- **NÃO refatorar** os services existentes — eles seguem operando como estão
- Wrappers novos chamam ou imitam padrões dos services existentes

### 6.2 Serviços novos (apenas 4)

```
app/odoo/services/

  stock_lot_service.py
      # Wrapper sobre helpers existentes em recebimento_fisico_odoo_service.py
      #   _resolver_lote()             (linha 324-378)
      #   _criar_stock_lot_com_fallback()  (linha 416-482)
      # API publica:
      #   criar(nome, product_id, company_id, expiration_date=None) -> lot_id
      #   renomear(lot_id, novo_nome) -> bool  (com guard: bloqueia se ha stock.move em picking nao-done)
      #   atualizar_validade(lot_id, expiration_date) -> bool
      #   inativar(lot_id) -> bool  (write active=False; usado por indisponibilizacao por lote)
      #   buscar_por_nome(nome, product_id, company_id) -> Optional[lot_id]  (usa operador 'in', NUNCA '=')

  stock_picking_service.py
      # Generalizacao do padrao em:
      #   emissao_nf_pallet.py:130-177           (picking expedicao simples)
      #   recebimento_lf_odoo_service.py:2122-2481  (step 20 picking saida FB)
      # API publica:
      #   criar_transferencia(company_origem_id, company_destino_id, linhas,
      #                       location_origem_id=None, location_destino_id=None,
      #                       incoterm='CIF', date=None) -> picking_id
      #   preencher_qty_done(picking_id, linhas)  (suporta lot_id ou lot_name por linha)
      #   validar(picking_id)  (fire_and_poll, trata 'cannot marshal None')
      #   cancelar(picking_id, motivo)
      # Reutiliza: timeout_override do connection.py, OdooConnection singleton

  account_move_intercompany_service.py
      # Service generico parametrizado por `tipo_operacao` (str) que mapeia para a
      # entrada correspondente em constants/operacoes_fiscais.py:MATRIZ_INTERCOMPANY.
      # NAO 1 service por CFOP — apenas 1 service que conhece a matriz.
      #
      # API publica:
      #   preview(payload) -> dict
      #       Le NF de referencia via XML-RPC, gera template, retorna diff campo-a-campo
      #       SEM CRIAR nada no Odoo. Resultado salvo em operacao_odoo_auditoria status=PREVIEW.
      #
      #   executar(payload, confirmar=True) -> external_id
      #       Cria account.move (move_type, l10n_br_tipo_pedido, partner_id, company_id,
      #       fiscal_position_id, invoice_line_ids), chama onchange_l10n_br_calcular_imposto,
      #       action_post via fire_and_poll. Idempotente via external_id.
      #       Pre-execucao chama hook pre_execute_nf. Pos-execucao chama pos_execute_nf.
      #
      #   cancelar(invoice_id, motivo) -> bool
      #       Cancela NF se dentro de janela SEFAZ.
      #
      # Internamente usa:
      #   stock_picking_service.criar_transferencia() quando a operacao exige picking
      #   stock_lot_service para lotes
      #   constants/operacoes_fiscais para mapeamento

  indisponibilizacao_estoque_service.py
      # API publica:
      #   canary_lote(lot_id) -> bool   (testa hipotese C1: stock.lot.active=False bloqueia faturamento)
      #   canary_local(location_id) -> bool  (C2: stock.location.active=False)
      #   canary_tag(lot_id, tag_id) -> bool  (C3 fallback)
      #   indisponibilizar_lote(lot_id) -> bool  (so executa se canary_lote ja passou)
      #   indisponibilizar_local(location_id) -> bool
      #   reverter_lote(lot_id) -> bool   (active=True)
      #   reverter_local(location_id) -> bool
```

### 6.3 Constantes consolidadas (1 arquivo novo)

```
app/odoo/constants/__init__.py
app/odoo/constants/operacoes_fiscais.py
    # Consolida o que hoje esta espalhado:
    #   CNPJ_PARA_COMPANY            (de lancamento_odoo_service.py:44-107)
    #   CONFIG_POR_EMPRESA           (idem)
    #   OPERACOES_TRANSPORTE         (idem)
    #   OPERACAO_DE_PARA             (idem, linha 112-123 — para fretes)
    #   EMPRESA_CONFIG_PALLET        (de emissao_nf_pallet.py:35-82)
    #   COMPANY_LOCATIONS            (NOVO — descoberto via audit run no F0)
    #   PICKING_TYPES_POR_COMPANY    (de IDS_FIXOS.md + recebimento_lf_odoo_service.py)
    #
    #   MATRIZ_INTERCOMPANY (NOVO):
    #       {
    #         'industrializacao': {
    #             'cfop': '5901',
    #             'l10n_br_tipo_pedido': 'industrializacao',
    #             'move_type': 'out_invoice',
    #             'direcao': ('FB', 'LF'),
    #             'tipo_produto': [1, 2, 3],
    #             'nf_referencia': 94457,
    #             'fiscal_position_id': {1: ..., 5: ...},  # por company
    #         },
    #         'perda': {...},
    #         'dev-industrializacao': {...},
    #         'transf-filial': {...},
    #       }
    #
    # Princípio: dado, não código. Adicionar nova operação = adicionar entrada no dict.

app/odoo/constants/locations.py
    # COMPANY_LOCATIONS — descoberto via audit run em F0. Hoje hardcoded em 3 locais.
```

**Estratégia de migração suave**: services existentes (`lancamento_odoo_service.py`, `emissao_nf_pallet.py`, `recebimento_lf_odoo_service.py`) **continuam tendo suas constantes locais**. O arquivo de constantes consolidado **espelha** o que existe, e os novos services consomem dali. Refator dos legados em outro spec, futuro.

### 6.4 Reuso explícito por categoria (do audit)

| Categoria | Reuso |
|---|---|
| **NF inter-company** | Padrão de `lancamento_odoo_service.py` (16 etapas DFe→PO→Invoice). **Para inventário não há DFe**, então o novo service cria `account.move` direto (sem PO) — mais simples. Reutiliza `fire_and_poll`, `_obter_operacao_correta`, `onchange_l10n_br_calcular_imposto`. |
| **Picking** | `emissao_nf_pallet.py:130-177` é o template mais limpo (sem DFe). Padrão `create → action_confirm → action_assign → preencher qty_done → button_validate (fire_and_poll)`. |
| **Lote** | `_resolver_lote` + `_criar_stock_lot_com_fallback` de `recebimento_fisico_odoo_service.py`. Já tem workaround do bug intermitente do operador `=` em `stock.lot.search`. |
| **Auditoria** | Modelo: `LancamentoFreteOdooAuditoria` (`app/fretes/models.py:1047-1134`). Generalizar com `tabela_origem` + `registro_id` polimórfico. |
| **Fire-and-poll** | `OdooConnection.execute_kw(timeout_override=180)` em `app/odoo/utils/connection.py`. Já implementado em 12+ lugares. |

## 7. Modelo de dados

### 7.1 Tabela `operacao_odoo_auditoria` (nova, **polimórfica e reutilizável**)

Substitui o padrão fretes-específico (`LancamentoFreteOdooAuditoria`). Pode ser usada por qualquer operação Odoo futura (inventário, transferência diária, devolução, etc.).

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | serial PK | |
| `external_id` | varchar(64) UNIQUE NOT NULL | idempotência |
| `tabela_origem` | varchar(40) NOT NULL | enum: `account_move`, `stock_picking`, `stock_lot`, `stock_location` |
| `registro_id` | int NOT NULL | FK lógico no banco local; pode apontar para `ajuste_estoque_inventario` ou outro |
| `acao` | varchar(20) NOT NULL | `create`, `write`, `post`, `cancel`, `validate`, `rename`, `inactivate` |
| `modelo_odoo` | varchar(60) NOT NULL | `account.move`, `stock.picking`, `stock.lot` |
| `metodo_odoo` | varchar(60) | `action_post`, `button_validate`, etc. |
| `odoo_id` | int | ID do registro afetado no Odoo |
| `etapa` | int | sequencial dentro de uma operação multi-etapa |
| `etapa_descricao` | varchar(80) | |
| `status` | varchar(20) NOT NULL | `SUCESSO`, `ERRO`, `AVISO`, `PREVIEW` |
| `payload_json` | jsonb | dict enviado (sanitize_for_json) |
| `resposta_json` | jsonb | retorno Odoo |
| `dados_antes_json` | jsonb | snapshot pre-write |
| `dados_depois_json` | jsonb | snapshot pos-write |
| `erro_msg` | text | |
| `tempo_execucao_ms` | int | |
| `contexto_origem` | varchar(40) | `INVENTARIO_2026_05`, `TRANSF_DIARIA`, `DEVOLUCAO`, etc. |
| `contexto_ref` | varchar(80) | external ref do contexto |
| `screenshot_s3_key` | varchar(255) | Playwright validacao SEFAZ |
| `executado_em` | timestamp NOT NULL | `agora_utc_naive()` |
| `executado_por` | varchar(80) NOT NULL | |

Índices: `external_id` UNIQUE, `(tabela_origem, odoo_id)`, `(contexto_origem, contexto_ref)`, `status`.

### 7.2 Tabela `ajuste_estoque_inventario` (nova, enxuta)

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | serial PK | |
| `ciclo` | varchar(40) NOT NULL | ex. `INVENTARIO_2026_05` |
| `cod_produto` | varchar(30) NOT NULL | |
| `tipo_produto` | smallint NOT NULL | 1/2/3/4 |
| `company_id` | int NOT NULL | |
| `lote_inventariado` | varchar(60) | |
| `lote_odoo` | varchar(60) | |
| `qtd_inventario` | numeric(15,4) NOT NULL | |
| `qtd_odoo` | numeric(15,4) NOT NULL | |
| `qtd_ajuste` | numeric(15,4) NOT NULL | |
| `custo_medio` | numeric(15,4) | |
| `acao_decidida` | varchar(30) NOT NULL | `TRANSFERIR_CD_FB` / `TRANSFERIR_FB_CD` / `INDUSTRIALIZACAO_FB_LF` / `PERDA_LF_FB` / `DEV_FB_LF` / `DEV_LF_FB` / `INDISPONIBILIZAR_LOTE` / `INDISPONIBILIZAR_LOCAL` / `RENOMEAR_LOTE` / `SEM_ACAO` |
| `external_id_operacao` | varchar(64) | FK lógico para `operacao_odoo_auditoria.external_id` |
| `canary_passou` | boolean DEFAULT FALSE | |
| `aprovado_em` | timestamp | |
| `aprovado_por` | varchar(80) | |
| `status` | varchar(20) DEFAULT 'PROPOSTO' | PROPOSTO/APROVADO/EXECUTADO/FALHA/CANCELADO |
| `erro_msg` | text | |
| `criado_em` | timestamp | |
| `criado_por` | varchar(80) | |

Índices: `(ciclo, company_id, cod_produto, lote_odoo)`, `status`, `acao_decidida`.

### 7.3 Migrations

```
scripts/migrations/2026_05_18_operacao_odoo_auditoria.py
scripts/migrations/2026_05_18_operacao_odoo_auditoria.sql
scripts/migrations/2026_05_18_ajuste_estoque_inventario.py
scripts/migrations/2026_05_18_ajuste_estoque_inventario.sql
```

Padrão DDL idempotente + Python conforme `~/.claude/CLAUDE.md`.

## 8. Pipeline operacional

### 8.1 Fases (mapeadas dos 10 passos do prompt)

| Fase | O que faz | Workflow item | Reusa |
|------|-----------|---------------|-------|
| **F0** — Audit run | Confirma `location_id` por company, lê estrutura completa das 4 NFs de referência (94457/13075/147772/94410), valida que `fiscal_position_id` mapeia para CFOPs corretos por company. Documenta em `00-decisoes/`. Sem mudanças no Odoo. | (preparação) | — |
| **F1** — Extração estoque | `stock.quant` paginado por company, gera 3 Excels (FB/CD/LF) + JSON dump | 2 | `connection.py` |
| **F2** — Confronto inv × Odoo | Diff por `(produto, company, lote)`, aplica P6/P7/P9 | 3 | — |
| **F3** — Proposta | Calcula `acao_decidida` (matriz tipo×company×sinal→ação), INSERT em `ajuste_estoque_inventario` status=PROPOSTO | 4-5 | `constants/operacoes_fiscais.py` |
| **F3.5** — Aprovação | Operador roda `04_propor_ajustes.py --aprovar-onda=N --hash=<sha>` | 6 | — |
| **F4a** — Canary técnico ordem=3 | C1/C2/C3 em **staging** ou company-cobaia. Decisão sobre via (lote/local/tag) registrada | (pre-requisito de O3) | `indisponibilizacao_estoque_service` |
| **F4b** — Canary fiscal por CFOP | Para cada CFOP: lê NF ref, gera template via `preview()`, executa 1 NF real menor, valida campos + SEFAZ | 7-9 | `account_move_intercompany_service.preview` |
| **F5** — Bulk supervisionado | Executa ondas O1/O2/O3/O4. Lock Redis por `(company, produto, lote)`. Hooks. | 10 | todos os 4 services novos |
| **F6** — Reconciliação | Re-extrai estoque Odoo, compara com inventário, gera relatório residual | (pós) | F1 |

### 8.2 Ondas

| Onda | Conteúdo | Service usado |
|------|----------|---------------|
| O0 | Canary técnico (C1/C2/C3) | `indisponibilizacao_estoque_service` |
| O1 | NFs CFOP 5901 / 5903 / 5949 (LF↔FB) | `account_move_intercompany_service` (3 `tipo_operacao` diferentes, mesmo service) |
| O2 | NFs CFOP 5152 (CD↔FB) | idem (`tipo_operacao='transf-filial'`) |
| O3 | Indisponibilizações | `indisponibilizacao_estoque_service` (`lote` ou `local` conforme O0) |
| O4 | Rename de lote (P9) | `stock_lot_service.renomear` |
| O5 | Reconciliação | F6 |

## 9. Hooks determinísticos

| Hook | Onde | Bloqueia se |
|------|------|-------------|
| `pre_execute_nf.py` | Service base | `ajuste_estoque_inventario.status ≠ APROVADO` OR `custo_medio diverge >20% do Odoo` OR `valor_onda > teto (default R$ 100k)` |
| `pos_execute_nf.py` | Service base | (não bloqueia, executa) Salva screenshot Playwright + `chave_nfe` + commit DB obrigatório |
| `pre_lote_rename.py` | `stock_lot_service.renomear` | Lote destino tem `stock.move` em picking não-done |
| `pre_execute_indisponibilizacao.py` | `indisponibilizacao_estoque_service` | Canary correspondente não passou (`canary_passou=False`) |
| `pre_commit_docs.sh` | Git pre-commit | Arquivo em `04-movimentacoes/` sem frontmatter mínimo (NF#, CFOP, hash payload) |

## 10. Estratégia de canary

### 10.1 Canary técnico (O0) — antes de qualquer NF

3 hipóteses testadas em ordem; primeira que passar define a via para ordem=3:

| Canary | Hipótese | Critério |
|--------|----------|----------|
| C1 | `stock.lot.active=False` esconde lote do faturamento | Cria SO rascunho do produto; verifica `move_line_ids`; lote desativado não aparece |
| C2 | `stock.location.active=False` esconde local | Idem; verifica reserva não aloca local desativado |
| C3 | Tag/campo custom (fallback) | Investigar `fiscal_position` ou campo `route_ids` que possa filtrar |

Resultado em `docs/inventario-2026-05/03-canary/canary-{c1,c2,c3}.md`. Decisão em `00-decisoes/D003-via-indisponibilizacao.md`.

### 10.2 Canary fiscal — antes de cada CFOP em bulk

Para cada `tipo_operacao` em `MATRIZ_INTERCOMPANY`:

1. `account_move_intercompany_service.preview(payload)` lê NF de referência via XML-RPC, gera template, retorna diff campo-a-campo
2. `_compare_to_reference()` bloqueia execução se campo crítico faltar
3. Executar 1 NF real com a menor qty disponível (`07_executar_onda1_lf_fb.py --canary --apenas=1`)
4. Validar `chave_nfe` SEFAZ + screenshot Playwright
5. Resultado em `docs/inventario-2026-05/03-canary/canary-nf-{5152,5901,5903,5949}.md`
6. Aprovação humana explícita antes de bulk daquele CFOP

## 11. Governança

- **Aprovação por onda**, hash da proposta calculado sobre `ajuste_estoque_inventario` da onda
- **Aprovação dupla automática** se `count(NFs) > 50` OR `sum(valor) > R$ 50k`
- Todo INSERT/UPDATE em `operacao_odoo_auditoria` e `ajuste_estoque_inventario` registrado com `executado_em`/`executado_por`/`aprovado_em`/`aprovado_por`
- Documento atômico em `04-movimentacoes/{onda}/{external_id}.md` gerado pelo `pos_execute_nf.py`

## 12. Rollback

| Operação | Janela |
|----------|--------|
| INSERT `ajuste_estoque_inventario` status=PROPOSTO | `DELETE WHERE status='PROPOSTO'` (livre) |
| NF draft (não postada) | `unlink` XML-RPC (livre) |
| Lote renomeado | `stock.lot.write` reverso |
| Indisponibilização | `active=True` |
| `action_post` em NF (postada) | SEFAZ: 24h transf-filial / 7d industrialização. Depois: nota devolução |

Hook `pre_execute_nf.py` exige flag `--operacao-irreversivel-confirmada` para qualquer NF > R$ 10k.

## 13. Estrutura de arquivos final

```
.claude/references/odoo/
  OPERACOES_FISCAIS_NACOM_LF.md              # NOVO — playbook 4 CFOPs com matriz, decision tree, gotchas
  OPERACOES_LOTE_E_INDISPONIBILIZACAO.md     # NOVO — rename + canary + ordem=3
  IDS_FIXOS.md GOTCHAS.md MODELOS_CAMPOS.md  # EXISTENTES
  PIPELINE_RECEBIMENTO.md PIPELINE_RECEBIMENTO_LF.md  # EXISTENTES
  PADROES_AVANCADOS.md ROUTING_ODOO.md CONVERSAO_UOM.md AGENT_BOILERPLATE.md  # EXISTENTES

app/odoo/services/                           # 4 services novos (não 6)
  stock_lot_service.py
  stock_picking_service.py
  account_move_intercompany_service.py
  indisponibilizacao_estoque_service.py

app/odoo/constants/                          # NOVO diretório
  __init__.py
  operacoes_fiscais.py                       # MATRIZ_INTERCOMPANY + constantes consolidadas
  locations.py                               # COMPANY_LOCATIONS (descoberto em F0)

app/odoo/models/                             # NOVO diretório
  __init__.py
  operacao_odoo_auditoria.py
  ajuste_estoque_inventario.py

scripts/migrations/
  2026_05_18_operacao_odoo_auditoria.{py,sql}
  2026_05_18_ajuste_estoque_inventario.{py,sql}

scripts/inventario_2026_05/
  README.md
  01_extrair_estoque_odoo.py
  02_carregar_inventario_xlsx.py
  03_confrontar_inv_vs_odoo.py
  04_propor_ajustes.py
  05_canary_estoque_staging.py
  06_canary_nfs_referencia.py
  07_executar_onda1_lf_fb.py
  08_executar_onda2_cd_fb.py
  09_executar_onda3_indisponibilizacao.py
  10_reconciliar_pos_ajuste.py
  hooks/
    pre_execute_nf.py
    pos_execute_nf.py
    pre_lote_rename.py
    pre_execute_indisponibilizacao.py
    pre_commit_docs.sh

docs/inventario-2026-05/
  README.md
  00-decisoes/
    D001-estudo-recebimento-lf.md
    D002-escopo-fases.md
    D003-via-indisponibilizacao.md
  01-premissas/
    P001-P010-{descricao}.md
  02-gotchas/
  03-canary/
    canary-c1-stock-lot-active.md
    canary-c2-stock-location-active.md
    canary-c3-tag-fallback.md
    canary-nf-5152-94410.md
    canary-nf-5901-94457.md
    canary-nf-5903-13075.md
    canary-nf-5949-147772.md
  04-movimentacoes/
    onda-1-lf-fb/
    onda-2-cd-fb/
    onda-3-indisponibilizacao/
    onda-4-lote-rename/
  05-rollback/
  06-aprovacoes/
  07-relatorios/
```

## 14. Referências obrigatórias (com linhas)

| Preciso de... | Documento |
|---|---|
| **IDs Odoo** (companies, journals, pickings) | `.claude/references/odoo/IDS_FIXOS.md` |
| **Gotchas críticos** (action_update_taxes, SEFAZ 225, button_validate, stock.lot.search) | `.claude/references/odoo/GOTCHAS.md` |
| **Campos** account.move, stock.picking, stock.lot, stock.move.line | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| **Padrões service Odoo** (anti-detach, fire-and-poll, checkpoint, commit antes) | `app/odoo/CLAUDE.md` P1-P7 |
| **OPERACAO_DE_PARA + helpers** | `app/fretes/services/lancamento_odoo_service.py:44-107,112-123,241-294,509-608` |
| **Padrão picking simples** | `app/pallet/services/emissao_nf_pallet.py:35-82,130-177,153-177` |
| **Padrão picking saída multi-company (step 20)** | `app/recebimento/services/recebimento_lf_odoo_service.py:73-80,2122-2200,2269-2481` |
| **Helpers stock.lot (workaround bug)** | `app/recebimento/services/recebimento_fisico_odoo_service.py:324-378,398-414,416-482` |
| **Modelo de auditoria a generalizar** | `app/fretes/models.py:1047-1134` (LancamentoFreteOdooAuditoria) |
| **OdooConnection, execute_kw, timeout_override** | `app/odoo/utils/connection.py:156-413` |
| **Timezone** | `.claude/references/REGRAS_TIMEZONE.md` + `app/utils/timezone.py:26-37` |
| **JSON sanitize** | `app/utils/json_helpers.py:79-231` |
| **UoM conversão** | `.claude/references/odoo/CONVERSAO_UOM.md` |
| **Roteamento Odoo** | `.claude/references/odoo/ROUTING_ODOO.md` |
| **Boilerplate de subagente Odoo** | `.claude/references/odoo/AGENT_BOILERPLATE.md` |

## 15. Itens em aberto (resolver durante F0)

| Item | Quando | Responsável |
|------|--------|-------------|
| Existe Odoo de staging? Senão, escolher company-cobaia + lote-cobaia em prod | Antes de O0 | Rafael |
| Confirmar `location_id` de FB, CD, LF para estoque (vai para `constants/locations.py`) | F0 | dev + Rafael |
| Threshold "valor onda > R$ 50k" para aprovação dupla — confirmar | Antes de O1 | Rafael |
| Teto absoluto por onda (default R$ 100k) — confirmar | Antes de O1 | Rafael |
| Formato exato da planilha de inventário (cabeçalho, sheets) | F1 | Rafael |
| `fiscal_position_id` por (CFOP × company × direção) | F0 (audit run via XML-RPC) | dev |
| Validação com contadora: emissão de NFs com data 17/05/2026 referindo 16/05 | Antes de O1 (não bloqueia spec) | Rafael + contadora |

## 16. Critérios de aceite

1. **4 services** existem em `app/odoo/services/` e são invocáveis isoladamente
2. **Arquivo de constantes** `app/odoo/constants/operacoes_fiscais.py` consolida o que hoje está em 3 services existentes; `MATRIZ_INTERCOMPANY` cobre os 4 CFOPs
3. **2 tabelas** existem em prod via migration: `operacao_odoo_auditoria` (polimórfica, reutilizável) e `ajuste_estoque_inventario`
4. **2 playbooks** em `.claude/references/odoo/` (`OPERACOES_FISCAIS_NACOM_LF.md`, `OPERACOES_LOTE_E_INDISPONIBILIZACAO.md`) existem e documentam decisões + gotchas
5. **Canary técnico (C1/C2/C3)** executado em staging/company-cobaia, decisão registrada
6. **Canary fiscal** executado para cada um dos 4 CFOPs, documento em `03-canary/`
7. **Ondas O1..O4** executadas com aprovação registrada
8. **Relatório residual** em `07-relatorios/residual-pos-ajuste.xlsx` documenta qualquer divergência persistente
9. **≥ 1 GOTCHA novo** registrado em `02-gotchas/` (premissa: descoberta durante execução é normal)
10. **Hooks determinísticos** instalados e funcionais (5 hooks)
11. **Os 4 services novos** invocáveis fora do contexto "inventário 05/2026" — para transferência diária, devolução ad-hoc, criação de lote pontual, etc.

## 17. Pós-implementação (próximo trabalho, fora deste spec)

Conforme filosofia §1, **após a operação concluída**, candidatos a serem extraídos como features atômicas/skills:

- Skill `transferindo-filial` (consome `account_move_intercompany_service` com `tipo_operacao='transf-filial'`)
- Skill `enviando-industrializacao-lf` (idem com 5901)
- Skill `recebendo-retorno-lf` (idem com 5903)
- Skill `devolvendo-industrializacao` (idem com 5949)
- Skill `gerenciando-lote` (rename/criar/inativar)
- Telemetria de uso dos services em dashboard admin
- Refator dos services legados (`lancamento_odoo_service.py`, `emissao_nf_pallet.py`) para consumir o novo arquivo de constantes

Isso será objeto de **outro brainstorming** com base no aprendizado real.

---

## Self-review

- **Placeholders**: zero TBD/TODO; itens incertos listados em §15 (resolver em F0, não bloqueiam spec)
- **Consistência interna**: matriz §5.2 ↔ `MATRIZ_INTERCOMPANY` §6.3 ↔ services §6.2 ↔ migrations §7.3 ↔ canaries §10 — todas alinhadas
- **Reuso justificado por evidência**: cada service novo §6.2 cita arquivo:linha do que reusa (resultado do audit)
- **Escopo enxuto**: 4 services + 1 arquivo de constantes + 2 tabelas + 2 playbooks. Sem skills, sem refator de legados.
- **Reversibilidade da decisão de design**: se `MATRIZ_INTERCOMPANY` se mostrar limitada, posso voltar a 1 service por tipo_operacao sem perder o trabalho (constantes ficam, services se especializam). Caminho contrário é mais caro.
- **Critérios de aceite**: 11 itens auditáveis após implementação
