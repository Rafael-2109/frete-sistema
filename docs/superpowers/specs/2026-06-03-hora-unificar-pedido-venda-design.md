<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# HORA — Unificar tela de Pedido de Venda + filtro loja/vendedor + fix desconto

> **Papel:** spec de design de três mudanças no Pedido de Venda (`HoraVenda`) do módulo Lojas HORA: (1) unificar a tela "Ver" do pedido na tela "Novo pedido de venda"; (2) corrigir o bug de drift de centavos no desconto ao trocar/adicionar forma de pagamento; (3) adicionar critério opcional de filtragem dos pedidos por loja **ou** por vendedor, configurável por usuário na tela de permissões.

## Indice

- [Contexto](#contexto)
- [Escopo](#escopo)
- [Decisões aprovadas (Q&A)](#decisões-aprovadas-qa)
- [Parte 2 — Fix do desconto em centavos](#parte-2--fix-do-desconto-em-centavos)
- [Parte 3 — Filtro loja/vendedor](#parte-3--filtro-lojavendedor)
- [Parte 1 — Unificação das telas](#parte-1--unificação-das-telas)
- [Modelo de dados e migrations](#modelo-de-dados-e-migrations)
- [UI e rotas](#ui-e-rotas)
- [Não-objetivos](#não-objetivos)
- [Testes](#testes)
- [Riscos e pontos de atenção](#riscos-e-pontos-de-atenção)

## Contexto

O Pedido de Venda da HORA (`HoraVenda`, `app/hora/models/venda.py`) tem hoje **duas telas distintas**:

- **"Novo pedido de venda"** (`app/templates/hora/tagplus/pedido_venda_novo.html`), rota `hora.tagplus_pedido_venda_novo` (GET `/hora/tagplus/pedido-venda/novo`, `app/hora/routes/tagplus_routes.py:1008`). Rica em UX: seleção de moto em **cascata** modelo→cor→chassi (`pedido_venda_novo.html:152-175`), sincronização desconto% ↔ desconto R$ ↔ valor final (`pedido_venda_novo.html:199-218,743-796`), preço de tabela automático por forma de pagamento, múltiplas formas de pagamento, busca ViaCEP. **Cria 1 moto** (campos singulares; `criar_venda_manual` recebe `numero_chassi` singular — `tagplus_routes.py:1196`). **Não tem modo edição.**
- **"Ver" pedido** (`app/templates/hora/venda_detalhe.html`), rota `hora.vendas_detalhe` (GET `/hora/vendas/<id>`, `app/hora/routes/vendas.py:222`). Tem timeline de status, ~17 ações de workflow e edição por seção, mas a adição de item usa **input manual de chassi** (sem cascata) e não tem o componente de desconto sincronizado.

Os operadores preferem a tela "Novo pedido". O objetivo é que ela passe a ser a **tela única** (criar **e** ver/editar), eliminando `venda_detalhe.html`.

Dois problemas adicionais reportados pelo dono do módulo motivam o mesmo spec:

- **Bug**: ao adicionar/trocar uma forma de pagamento, o desconto sofre drift de centavos (ex.: R$ 500,00 → R$ 500,05).
- **Falta de feature**: a listagem de pedidos só pode ser escopada por loja. Faltam usuários cujo recorte natural é "meus pedidos" (vendedor/criador).

Fontes do estado atual (mapeamento completo em [Parte 1](#parte-1--unificação-das-telas)):
- `app/hora/routes/vendas.py` — 18 rotas de venda (lista, detalhe, editar, item add/remove/edit, confirmar, cancelar, etc.).
- `app/hora/routes/tagplus_routes.py:1008-1310` — rotas de criação manual + APIs AJAX (cores, chassis, preço-modelo).
- `app/hora/services/venda_service.py` — `criar_venda_manual:604`, `_query_vendas:2140`, `adicionar_item_pedido:1260`, `editar_item_pedido:1369`, matriz `_CAMPOS_EDITAVEIS_HEADER:1051`.
- `app/hora/models/permissao.py:78` (`hora_user_permissao`) e `app/auth/models.py` (`Usuario.loja_hora_id:40`, `sistema_lojas:36`, `lojas_hora_ids_permitidas:308`, `tem_perm_hora:321`).

## Escopo

Três partes em um único spec, implementadas na ordem de risco crescente: **(2) fix desconto → (3) filtro → (1) unificação**. Tudo dentro de `app/hora/` (+ 1 coluna em `usuarios`, sem FK — padrão do módulo). Sem alterações em Odoo, TagPlus, ou outros módulos.

## Decisões aprovadas (Q&A)

| # | Decisão | Escolha |
|---|---|---|
| 1 | Bug do desconto: o que preservar ao trocar forma de pagamento | **Preservar o valor/desconto em R$** (recalcular pela âncora `valor`, nunca pelo `%` arredondado). |
| 2 | Como identificar o criador do pedido para o filtro "vendedor" | **Adicionar `hora_venda.criado_por_id`** (FK robusta, sem constraint — padrão do módulo). Backfill best-effort via auditoria. |
| 3 | Onde guardar a preferência [loja/vendedor] por usuário | **Nova coluna `usuarios.criterio_pedidos_hora`** (VARCHAR, default `'loja'`). |
| 4 | Escopo da unificação de telas | **Tudo num spec só**: tela única cria+edita, todas as ~17 ações migradas, `venda_detalhe.html` removida. |
| 5 | Rota de entrada da edição | **Manter `hora.vendas_detalhe`** renderizando a tela unificada em modo edição (não quebra ~20 redirects internos + 9 templates externos). |
| 6 | Abrangência do filtro | Afeta **somente** a listagem `/hora/vendas`; demais telas inalteradas. |
| 7 | Backfill do criador | **Best-effort** por nome via `hora_venda_auditoria` (`acao='CRIOU'`); sem match → NULL. |

## Parte 2 — Fix do desconto em centavos

**Causa-raiz** (`app/templates/hora/tagplus/pedido_venda_novo.html`):
- O `<select>` de forma de pagamento dispara `atualizarPrecoTabela()` no `change` (`pedido_venda_novo.html:627-633`), assim como troca de modelo (`:798-802`) e remoção de forma de pagamento.
- `atualizarPrecoTabela()` re-busca o preço de tabela (que difere entre À VISTA e A PRAZO) e **sempre** encerra com `recalcular('pct')` (`:737-738`).
- O ramo `'pct'` (`:765-772`) reconstrói o R$ a partir do `%` **já arredondado a 2 casas**: `rs = arred2(preco * pct / 100)`. Como o `%` perdeu precisão quando foi calculado a partir do R$ original (`:776`, `pct = arred2(rs / preco * 100)`), a ida-e-volta introduz o drift (500,00 → 500,05).

**Correção** (decisão #1 — preservar valor R$):
- `atualizarPrecoTabela()` passa a usar a âncora **`valor`** em vez de `pct`: recalcular o desconto a partir do **valor final** que o operador digitou. O ramo `'valor'` já existe e é correto (`:781-789`): `rs = arred2(preco - valor)`, `pct = arred2(rs/preco*100)`. Isso preserva exatamente o valor/desconto R$; o `%` é apenas um derivado exibido.
- **Caso de borda — primeira carga / valor vazio**: quando `valor_final` ainda está vazio ou `0` (operador acabou de escolher o modelo, sem ter digitado valor), manter a inicialização pelo preço cheio. A correção condiciona a âncora: se `valor_final` vazio/0 → `recalcular('pct')` (inicializa com desconto 0 = preço cheio); senão → `recalcular('valor')` (preserva o digitado).
- A correção é **só JS**, isolada no template (e no partial extraído na Parte 1). **Sem backend, sem migration.** O backend já está correto: `_resolver_preco_tabela` (`venda_service.py:447`) deriva desconto de `valor_final`; a API de preço (`buscar_preco_para_pedido:374`) só devolve preço de tabela e não recalcula desconto.

## Parte 3 — Filtro loja/vendedor

**Preferência por usuário** (decisão #3): nova coluna `usuarios.criterio_pedidos_hora` VARCHAR(10) `DEFAULT 'loja'`, domínio `{'loja','vendedor'}`.

**Rastreabilidade do criador** (decisão #2): nova coluna `hora_venda.criado_por_id` INTEGER nullable, **sem FK** (mesmo padrão de `hora_user_permissao.user_id` e `Usuario.loja_hora_id`, que evitam FK para manter `app/hora` desacoplado de `app/auth`).
- Gravação: `criar_venda_manual` (`venda_service.py:604`) passa a receber e gravar `criado_por_id`; a rota `tagplus_pedido_venda_criar` já resolve o operador (`tagplus_routes.py:1206`, `_operador()`) e passa também `current_user.id`.
- Backfill (decisão #7): `UPDATE hora_venda SET criado_por_id = u.id FROM hora_venda_auditoria a JOIN usuarios u ON u.nome = a.usuario WHERE a.acao = 'CRIOU' AND a.venda_id = hora_venda.id`. Sem match → permanece NULL.

**Aplicação do filtro** (`venda_service._query_vendas:2140`, hoje aplica só loja em `:2182-2186`):
- O caller `vendas_lista` (`vendas.py:51-124`) lê `current_user.criterio_pedidos_hora`:
  - `'loja'` (default): comportamento atual inalterado — `lojas_permitidas_ids()` → `HoraVenda.loja_id.in_(...)`.
  - `'vendedor'`: **ignora** escopo de loja e filtra `OR(HoraVenda.vendedor == current_user.nome, HoraVenda.criado_por_id == current_user.id)`.
- `_query_vendas`/`paginar_vendas` ganham um parâmetro novo (ex.: `filtro_vendedor: tuple[str|None, int|None] | None`) para receber `(nome, user_id)` quando o critério é vendedor; mantém `lojas_permitidas_ids` para o critério loja. A rota decide qual passar — o service não acessa `current_user` (mantém testabilidade).
- **Admins**: o critério também se aplica, mas o default `'loja'` + `loja_hora_id=NULL` mantém "vê tudo". Só muda se um admin for explicitamente marcado como `'vendedor'`.
- **Fragilidade conhecida e mitigada**: `HoraVenda.vendedor` é texto livre (nome, `venda.py:152`). O `OR` com `criado_por_id` (id robusto) cobre os pedidos novos com precisão; o match por nome cobre os legados. Pedidos legados sem criador e com vendedor de nome divergente podem escapar — aceitável (decisão #7).

**UI permissões** (`app/templates/hora/permissoes_lista.html`, bloco "Loja segregada" ~`:109-122`): novo `<select name="criterio_pedidos_hora">` com opções "Por loja (padrão)" / "Por vendedor", + novo endpoint `POST /hora/permissoes/<id>/criterio-pedidos` em `app/hora/routes/permissoes.py` (espelho de `permissoes_set_loja`, perm `usuarios/editar`, bloqueio de self-edit e edição-de-admin-por-não-admin como nos demais).

## Parte 1 — Unificação das telas

**Estratégia** (decisões #4, #5): a tela "Novo pedido" (`pedido_venda_novo.html`) torna-se a **tela única**, em 2 modos. `venda_detalhe.html` é **deletada**. A rota `hora.vendas_detalhe` é **mantida** mas passa a renderizar a tela unificada em modo edição — preservando todas as referências existentes:

| Referência a `hora.vendas_detalhe` | Onde |
|---|---|
| ~20 redirects pós-ação | `vendas.py:278..730` |
| 9 templates externos | `vendas_lista.html:153`, `venda_preview_nfe.html`, `nfe_status.html`, `emissoes_lista.html`, `estoque_lista.html`, `estoque_chassi_detalhe.html`, `devolucao_venda_lista.html`, `devolucao_venda_detalhe.html`, `venda_upload.html` |

**Dois modos:**
- **Criação** (`hora.tagplus_pedido_venda_novo`, sem `venda_id`): form único atual (1 moto + cliente + endereço + pagamento) → POST `hora.tagplus_pedido_venda_criar` (lógica inalterada).
- **Edição/Ver** (`hora.vendas_detalhe`, com `venda_id`): renderiza a mesma tela pré-preenchida com a `HoraVenda`, somando tudo que hoje só existe no detalhe:
  - Timeline de status + barra de ações por status: **Confirmar** (`hora.vendas_confirmar`), **Emitir NFe** (`hora.venda_nfe_preview`), **Voltar p/ cotação** (`hora.vendas_voltar_cotacao`), **Gerenciar NFe** (`hora.venda_nfe_status`), **Cancelar** (`hora.vendas_cancelar`), **Descartar teste** (`hora.vendas_descartar_teste`), **Reimportar TagPlus** (`hora.tagplus_backfill_nfe_unica`), **Resolver divergências** (`hora.vendas_resolver_divergencia`), **Definir/Trocar loja** (`hora.vendas_definir_loja`), **DANFE original** (`hora.vendas_download_pdf`), histórico de **auditoria**/divergências.
  - Seções cliente/endereço/frete/obs e pagamentos respeitando a **matriz por status** já existente no backend (`_CAMPOS_EDITAVEIS_HEADER:1051` + defesa NFe em-voo `:1089-1094`). Cada seção posta para os **endpoints granulares já existentes** (`hora.vendas_editar`, `hora.vendas_pagamentos_editar`, etc.). **Reuso total do backend maduro; nenhuma lógica de salvamento nova.**
  - Itens (motos/peças): em COTACAO, "adicionar/editar item" passa a usar o **componente de cascata** (modelo→cor→chassi + desconto sincronizado) em vez do input manual de chassi atual.

**Refator-chave — componente reutilizável:** extrair "seletor de moto em cascata + sincronização de desconto" (hoje inline em `pedido_venda_novo.html:152-218` + JS `:326-939`) para:
- um **partial Jinja** (ex.: `app/templates/hora/tagplus/_componente_moto_desconto.html`) reutilizado na criação e no add/edit de item da edição;
- um **arquivo JS de módulo** (ex.: `app/static/js/hora/pedido_venda.js`), removendo ~600 linhas de JS inline do template (alinhado à regra do projeto: nada de `<script>` grande inline). O fix da Parte 2 vive neste arquivo, beneficiando os dois modos.

**Backend de item — NÃO muda de assinatura:** `adicionar_item_pedido` (`venda_service.py:1260`) e `editar_item_pedido` (`:1369`) já recebem `valor_final` e **derivam** `desconto_aplicado`/`desconto_percentual` via `_resolver_preco_tabela` (`:1284`). O componente de cascata no frontend só precisa produzir `numero_chassi` + `valor_final` no submit das rotas `hora.vendas_item_adicionar`/`hora.vendas_item_editar` — o desconto é recalculado no servidor. Logo, a unificação do item é trabalho de **frontend** (reusar o componente), sem mudança de contrato no backend.

**Bug latente corrigido de brinde:** `vendas.py:1009` e `:1029` (`venda_adicionar_item_peca`/`venda_remover_item_peca`) redirecionam para `hora.venda_detalhe` (rota inexistente → `BuildError` em runtime). Corrigir para `hora.vendas_detalhe`.

## Modelo de dados e migrations

Duas migrations duais (`.py` Python com `create_app()` + verificação, e `.sql` idempotente para Render Shell), conforme regra do projeto. Sufixo sequencial conforme o próximo número livre de `scripts/migrations/hora_*` (verificar no plano).

1. **`hora_NN_criterio_pedidos_e_criador`** (ou duas migrations separadas):
   - `ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja';`
   - `ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS criado_por_id INTEGER;` (+ índice em `criado_por_id` para o filtro).
   - Backfill `criado_por_id` via `hora_venda_auditoria` (decisão #7) — parte Python (data fix), idempotente (só preenche onde `criado_por_id IS NULL`).

Modelos SQLAlchemy a atualizar: `Usuario` (`app/auth/models.py`) — campo + (opcional) helper de leitura; `HoraVenda` (`app/hora/models/venda.py`) — campo `criado_por_id`.

## UI e rotas

- **Menu** (`app/templates/hora/base.html`): "Novo Pedido de Venda" (`:216`, Faturamento) e "Pedidos de Venda" (`:123`, Movimentação) permanecem. Nada novo no menu — a edição entra pelo botão "Ver" da lista (`vendas_lista.html:153`), que já aponta para `hora.vendas_detalhe` (agora tela unificada).
- **Permissões** (`permissoes_lista.html` + `permissoes.py`): novo `<select>` de critério + novo endpoint `POST /hora/permissoes/<id>/criterio-pedidos`.
- **Templates removidos**: `app/templates/hora/venda_detalhe.html` (após migrar 100% das ações para a tela unificada).
- **Onboarding**: o tour `vendas_aprovar.js` aponta para elementos de `venda_detalhe.html`; reapontar IDs para a tela unificada (ou consolidar com `venda_manual_nova.js`) — validar em `/admin/onboarding/health`.

## Não-objetivos

- Não alterar o fluxo de import DANFE PDF (`vendas_upload`), TagPlus, nem a invariante fiscal (emitente = matriz).
- Não permitir múltiplas motos no modo **criação** (continua 1 moto por criação; múltiplos itens só na edição COTACAO, como hoje).
- Não adicionar FK física para `usuarios`/`hora_loja` (mantém desacoplamento do módulo).
- Não tornar o critério "vendedor" retroativamente perfeito para legados sem `criado_por_id` e com nome divergente.
- Não mexer no escopo de loja de outras telas (estoque, recebimento, etc.).

## Testes

`tests/hora/` (pytest determinístico — evals LLM vetados por custo):
- **Filtro**: `_query_vendas` com `criterio='loja'` (regressão do comportamento atual) e `criterio='vendedor'` (retorna pedidos por `vendedor==nome` OU `criado_por_id==id`; ignora loja).
- **Criador**: `criar_venda_manual` grava `criado_por_id`; backfill preenche a partir da auditoria e é idempotente.
- **Matriz por status preservada**: editar campos/itens conforme status na tela unificada continua respeitando `_CAMPOS_EDITAVEIS_HEADER` (testes existentes de `test_pedido_workflow.py` devem continuar verdes).
- **Bug latente**: smoke test de `url_for('hora.vendas_detalhe', ...)` nas rotas de peça (garante que o `BuildError` foi corrigido).
- **Fix desconto** (JS): cobertura por teste manual documentado no plano (não há harness JS); validar 500,00 estável ao trocar forma de pagamento, e inicialização correta com valor vazio.

## Riscos e pontos de atenção

- **Regressão na tela unificada**: a tela passa a servir 2 modos × 4 status. Risco de uma ação sumir/duplicar. Mitigação: checklist explícito no plano comparando cada ação/seção de `venda_detalhe.html` migrada, + rodar a suíte `tests/hora/`.
- **JS extraído para arquivo de módulo**: precisa de cache-bust e inclusão correta no template (e no partial). Validar que a cascata e o fix de desconto funcionam idênticos em criação e edição.
- **Coluna `criterio_pedidos_hora` em `usuarios`**: tabela compartilhada por todo o sistema; usar `DEFAULT 'loja'` + `NOT NULL` para não exigir mudança em nenhuma outra rota.
- **Backfill por nome**: `hora_venda_auditoria.usuario` pode ter nomes que não casam exatamente com `usuarios.nome`; aceitável (best-effort). Logar quantos preencheu vs. ficaram NULL.
- **Onboarding tours**: esquecer de reapontar os tours quebra a experiência guiada (não o app). Item no checklist do plano.
