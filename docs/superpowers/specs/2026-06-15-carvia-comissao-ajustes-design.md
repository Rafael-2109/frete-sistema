<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->

# Design: Consistência de Comissões CarVia — Ajustes (débito/crédito) + filtro por data de corte

> **Papel:** especificar o mecanismo que garante consistência das comissões CarVia quando o
> `cte_valor` de um CTe já comissionado muda (ou o CTe é cancelado) DEPOIS do fechamento ter sido
> criado, gerando um **ajuste** (débito/crédito) que é abatido no próximo fechamento do mesmo
> vendedor — sem tocar no fechamento original. Também troca o filtro da tela de criação de
> `(data inicial + data final)` para **apenas data final** ("data de corte").

## Contexto

Levantamento de 2026-06-15 (sessão Claude Code). Operação com dados REAIS (comissões pagas a
vendedores). Estado atual verificado em código:

- O fechamento JÁ congela cada CTe via snapshot: `valor_cte_snapshot`, `percentual_snapshot`,
  `valor_comissao` — `app/carvia/models/comissao.py:142-147`.
- A busca de elegíveis JÁ "mata o passado": exclui CTes que já estão em fechamento não-cancelado
  via subquery — `app/carvia/services/financeiro/comissao_service.py:149-163`. Mas usa
  `cte_data_emissao BETWEEN data_inicio AND data_fim` — `comissao_service.py:143`.
- A comissão é `cte_valor × percentual` — `comissao_service.py:258-259`.
- **NÃO existe** propagação quando o `cte_valor` muda depois (`editar_cte_valor`,
  `operacao_routes.py:1320`, que comenta explicitamente em `:1322` que não recalcula nada) nem
  quando o CTe/operação é cancelado. O snapshot permanece com o valor antigo. Resultado: comissões
  divergem silenciosamente da realidade do CTe.

A feature fecha esse gap registrando a **diferença** como um lançamento próprio, abatido no
próximo fechamento.

---

## Decisões (confirmadas com o usuário)

1. **Gatilho** = na **criação** do fechamento. Uma vez que um CTe entra em um fechamento (mesmo
   `PENDENTE`), ele fica "no passado morto"; qualquer alteração de `cte_valor` ou cancelamento
   posterior vira **ajuste**, e o fechamento original **nunca** é alterado.
2. **Saldo nunca negativo (a pagar, jamais a receber)**: ao incorporar os ajustes pendentes (que
   podem ser débitos), se o `total_comissao` final ficaria `< 0`, o sistema **bloqueia** a criação
   do fechamento. Os débitos permanecem `PENDENTE` e acumulam até existir comissão bruta suficiente
   para absorvê-los. **Não existe despesa negativa.**
3. **Filtro de datas** na **tela de criação**: remove o campo data inicial; mantém só a **data
   final** ("Comissões até — data de corte"). Critério de elegibilidade passa a ser
   `cte_data_emissao <= data_final` (a exclusão de já-comissionados continua valendo).
4. **Chave do vendedor = FK `usuarios.id`** (vendedores SÃO usuários do sistema — ex.: "Jéssica" =
   usuária "Jéssica Tereza"). A criação passa a usar um **select de usuários** filtrado por
   `acesso_comissao_carvia = True AND status = 'ativo'`. `CarviaComissaoFechamento` e
   `CarviaComissaoAjuste` ganham `vendedor_usuario_id`; `vendedor_nome`/`vendedor_email` viram
   **snapshot de exibição** (copiados do usuário no momento). O matching de ajustes é por
   `vendedor_usuario_id`. **Backfill** dos fechamentos existentes: casar `lower(vendedor_email) =
   lower(usuarios.email)`; os que não casarem ficam com `vendedor_usuario_id` NULL e são resolvidos
   manualmente na tela (§4.4).

---

## Abordagem escolhida

**Tabela dedicada `carvia_comissao_ajustes`** (uma alternativa de "linhas de ajuste dentro da
junction" foi rejeitada por misturar snapshot congelado com delta mutável e poluir
`recalcular_totais()`). Segue o padrão do módulo (tabelas dedicadas + auditoria).

---

## 1. Modelo de dados

### 1.1 Novo: `CarviaComissaoAjuste` → tabela `carvia_comissao_ajustes`

| Campo | Tipo | Papel |
|---|---|---|
| `id` | Integer PK | |
| `operacao_id` | FK `carvia_operacoes.id`, NOT NULL, indexed | o CTe que mudou |
| `fechamento_origem_id` | FK `carvia_comissao_fechamentos.id`, NOT NULL, indexed | fechamento onde o CTe foi comissionado (fechamentos não sofrem hard-delete — R14 — logo sem ondelete SET NULL) |
| `vendedor_usuario_id` | FK `usuarios.id`, nullable, indexed | **chave de matching**; copiado da origem (NULL só se a origem não tiver vínculo) |
| `vendedor_nome` | String(100), NOT NULL | snapshot de exibição do beneficiário (do fechamento de origem) |
| `vendedor_email` | String(150), nullable | snapshot |
| `motivo` | String(20), NOT NULL | `ALTERACAO_VALOR` \| `CANCELAMENTO_CTE` |
| `cte_numero` | String(20), NOT NULL | snapshot |
| `valor_cte_anterior` | Numeric(15,2), NOT NULL | base corrente antes da mudança |
| `valor_cte_novo` | Numeric(15,2), NOT NULL | novo valor efetivo (0 em cancelamento) |
| `percentual_snapshot` | Numeric(10,8), NOT NULL | percentual do fechamento de origem |
| `delta_comissao` | Numeric(15,2), NOT NULL | `(novo − anterior) × pct` → **>0 crédito, <0 débito** |
| `status` | String(20), NOT NULL, default `PENDENTE`, indexed | `PENDENTE` \| `APLICADO` \| `CANCELADO` |
| `fechamento_aplicado_id` | FK `carvia_comissao_fechamentos.id` (ondelete SET NULL), nullable | fechamento que absorveu o ajuste |
| `criado_por` | String(100), NOT NULL | auditoria |
| `criado_em` | DateTime, NOT NULL, default `agora_utc_naive` | |
| `aplicado_em` | DateTime, nullable | quando virou `APLICADO` |
| `observacoes` | Text, nullable | |

Constraints:
- `CheckConstraint("status IN ('PENDENTE','APLICADO','CANCELADO')")`
- `CheckConstraint("motivo IN ('ALTERACAO_VALOR','CANCELAMENTO_CTE')")`
- Índices: `(vendedor_usuario_id, status)` (matching de pendentes), `operacao_id`, `status`.

> **Sem** `UniqueConstraint` por `(operacao_id, fechamento_origem_id)`: um CTe pode mudar N vezes,
> gerando N ajustes (cada um relativo à base corrente).

### 1.2 Alteração em `CarviaComissaoFechamento` (`carvia_comissao_fechamentos`)

- **ADD COLUMN `vendedor_usuario_id`** FK `usuarios.id`, nullable, indexed — chave canônica do
  vendedor. `vendedor_nome`/`vendedor_email` permanecem como snapshot de exibição (preenchidos a
  partir do usuário selecionado). Nullable para acomodar backfill incompleto (§4.4).
- **ADD COLUMN `total_ajustes`** Numeric(15,2), NOT NULL, default 0 — soma dos `delta_comissao`
  dos ajustes `APLICADO` a este fechamento (transparência na UI e na despesa).
- Semântica de `total_comissao` passa a ser **o total final** = comissão dos CTes ativos +
  `total_ajustes`. (É o valor que já alimenta a `CarviaDespesa` vinculada — `comissao_service.py:76`.)

---

## 2. Service — `ComissaoService`

### 2.1 Novo método: `sincronizar_ajustes_cte(operacao_id, novo_valor_efetivo, motivo, usuario)`

Núcleo da geração de ajustes. Para cada junction **ativa** (`excluido=False`) do `operacao_id`
em fechamentos com `status != 'CANCELADO'`:

1. **base corrente** = `valor_cte_novo` do último ajuste **não-cancelado** daquela junction
   (`fechamento_origem_id == junction.fechamento_id`, ordenado por `id DESC`), ou
   `junction.valor_cte_snapshot` se não houver ajuste.
2. `delta_comissao = ((Decimal(novo_valor_efetivo) - base) * junction.percentual_snapshot).quantize('0.01')`.
3. Se `delta_comissao == 0` → não cria (evita ruído / idempotência sobre re-disparos).
4. Senão cria `CarviaComissaoAjuste(status='PENDENTE', ...)` copiando `vendedor_usuario_id` e
   `vendedor_nome/email` do fechamento de origem, `cte_numero`, `valor_cte_anterior=base`,
   `valor_cte_novo`, `motivo`.

Cancelamento ⇒ chamar com `novo_valor_efetivo=0, motivo='CANCELAMENTO_CTE'`.
Alteração de valor ⇒ `novo_valor_efetivo=<novo cte_valor>, motivo='ALTERACAO_VALOR'`.

A função faz `flush`, **não** `commit` (o caller — rota/serviço — controla a transação).

### 2.2 `criar_fechamento(...)` (modificado)

Assinatura passa a receber **`vendedor_usuario_id`** (em vez de `vendedor_nome`/`vendedor_email`
livres). Resolve o `Usuario` (import lazy de `app.auth.models`), grava `vendedor_usuario_id` + copia
`vendedor_nome`/`vendedor_email` do usuário (snapshot). Após criar as junctions e
`recalcular_totais()`:

1. Buscar ajustes `PENDENTE` com `vendedor_usuario_id == fechamento.vendedor_usuario_id` (FK — sem
   ambiguidade de string). Ajustes de fechamentos sem vínculo (`vendedor_usuario_id IS NULL`) não
   entram automaticamente — exigem resolução de vínculo (§4.4).
2. `total_comissao_final = soma(valor_comissao CTes) + soma(delta_comissao ajustes pendentes)`.
3. **Guard**: se `total_comissao_final < 0` → `raise ValueError("Débitos pendentes (R$ X) excedem
   a comissão do período (R$ Y). Inclua mais CTes ou aguarde.")` ⇒ rollback, **nenhum** ajuste é
   marcado, fechamento não é criado.
4. Senão: marcar cada ajuste `APLICADO`, `fechamento_aplicado_id=fechamento.id`,
   `aplicado_em=agora`. Setar `fechamento.total_ajustes`. `recalcular_totais()` recomputa
   `total_comissao` incluindo ajustes. Criar despesa vinculada com o total final (fluxo atual).

### 2.3 `recalcular_totais()` em `CarviaComissaoFechamento` (modificado)

`comissao/models.py:93-111` passa a:
- `total_bruto` = soma `valor_cte_snapshot` dos CTes ativos (inalterado).
- `total_ajustes` = soma `delta_comissao` dos ajustes `APLICADO` a este fechamento (query — fonte
  de verdade, sem stale).
- `total_comissao` = soma `valor_comissao` dos CTes ativos **+ `total_ajustes`**.

### 2.4 `buscar_ctes_elegiveis(data_fim, data_inicio=None, excluir_ja_comissionados=True)` (modificado)

`comissao_service.py:119`: se `data_inicio is None`, filtro vira `cte_data_emissao <= data_fim`
(remove o `.between`). Demais filtros (status != CANCELADO, valor > 0, exclusão de comissionados)
inalterados.

### 2.5 Guards adicionais de não-negatividade (defense-in-depth)

- `excluir_cte(...)` (`comissao_service.py:374`): após `recalcular_totais()`, se
  `total_comissao < 0` → `raise ValueError(...)` ⇒ rollback (não permite excluir CTe a ponto de
  tornar o fechamento devedor).
- `marcar_pago(...)` (`comissao_service.py:616`): guard extra `if total_comissao < 0: raise`.

---

## 3. Hooks (pontos de disparo verificados)

| Local | Ação | Chamada |
|---|---|---|
| `operacao_routes.py:1318-1325` (`editar_cte_valor`) | após setar `operacao.cte_valor` e antes do commit | `ComissaoService.sincronizar_ajustes_cte(operacao_id, novo_valor, 'ALTERACAO_VALOR', current_user.email)` |
| `operacao_routes.py:880` (cancelamento direto da operação) | após `operacao.status='CANCELADO'` | `sincronizar_ajustes_cte(op.id, 0, 'CANCELAMENTO_CTE', user)` |
| `operacao_cancel_service.py:304` (cascade B3) | após `op.status='CANCELADO'` | idem |

> **A verificar no plano**: se a rota `:880` já delega ao `operacao_cancel_service` (cascade) para
> evitar disparo duplicado. Se delegar, hookar só no service. `sincronizar_ajustes_cte` é
> naturalmente idempotente sobre re-disparo (delta 0 não cria), mas evitar chamada dupla é mais limpo.

Todos os imports de `ComissaoService` nos routes/serviços devem ser **lazy** (regra R2 do CarVia).

---

## 4. UI

### 4.1 Criação (`comissao_routes.py:91` + `templates/carvia/comissoes/criar.html:30-56`)
- Campo **Vendedor**: input texto livre (`criar.html:31`) → **`<select>` de usuários**
  (`acesso_comissao_carvia=True AND status='ativo'`, ordenado por `nome`). Form envia
  `vendedor_usuario_id`; backend resolve `vendedor_nome`/`vendedor_email` a partir do usuário.
  Remove o input livre `vendedor_email` (`criar.html:35-36`). A route popula a lista de usuários no
  `render_template`.
- Remover o input **`data_inicio`**; manter só **`data_fim`** (rótulo "Comissões até (data de corte)").
- JS que chama `/carvia/api/comissoes/ctes-elegiveis` passa só `data_fim`.
- Ao selecionar vendedor: painel "Ajustes pendentes" listando os deltas (crédito/débito) que serão
  incorporados, com subtotal; e prévia do total final. Se total final `< 0`, desabilitar o submit
  com aviso ("débitos excedem a comissão do período").
- `data_inicio` do registro = **derivada** = `min(cte_data_emissao)` dos CTes selecionados (só para
  satisfazer `CheckConstraint data_inicio <= data_fim` em `models/comissao.py:16`).

### 4.2 API CTes elegíveis (`comissao_routes.py:310`)
- Aceita `data_fim` obrigatório, `data_inicio` opcional. Delega a `buscar_ctes_elegiveis`.

### 4.3 Detalhe (`templates/carvia/comissoes/detalhe.html`)
- Nova seção "Ajustes incorporados" (separada dos CTes): cada ajuste com CTe, motivo, delta e
  fechamento de origem. Mostrar `total_ajustes` e o `total_comissao` final.

### 4.4 Resolução manual de vínculo de vendedor
Fechamentos sem `vendedor_usuario_id` (backfill por e-mail não casou) precisam de vínculo para que
ajustes futuros casem. No detalhe (`detalhe.html`), quando `vendedor_usuario_id IS NULL`, exibir um
**select de usuário + botão "Vincular vendedor"** → novo endpoint
`POST /comissoes/<id>/vincular-vendedor` que seta `vendedor_usuario_id` e atualiza o snapshot
`vendedor_nome`/`vendedor_email`. Funciona em **qualquer status** (é correção de metadado, não altera
valores nem totais). Ao vincular, ajustes `PENDENTE` órfãos daquele fechamento herdam o
`vendedor_usuario_id`.

> **Fora de escopo (futuro)**: tela dedicada de gestão/listagem de ajustes pendentes. Por ora a
> visibilidade vem da criação (pendentes do vendedor) e do detalhe (incorporados).

---

## 5. Migration (dois artefatos — regra do projeto)

1. **DDL** + **migration Python (Flask-Migrate)**:
   - `CREATE TABLE carvia_comissao_ajustes` (§1.1) com FKs (incl. `vendedor_usuario_id` → `usuarios.id`), checks e índices.
   - `ALTER TABLE carvia_comissao_fechamentos ADD COLUMN vendedor_usuario_id INTEGER REFERENCES usuarios(id)` (nullable, indexed).
   - `ALTER TABLE carvia_comissao_fechamentos ADD COLUMN total_ajustes NUMERIC(15,2) NOT NULL DEFAULT 0`.
2. Backfill (na própria migration, idempotente):
   - `total_ajustes = 0` para fechamentos existentes (default cobre). Sem ajustes históricos (feature nova).
   - `UPDATE carvia_comissao_fechamentos f SET vendedor_usuario_id = u.id FROM usuarios u WHERE lower(f.vendedor_email) = lower(u.email) AND f.vendedor_email IS NOT NULL`. Os não-casados permanecem NULL → resolução manual (§4.4).

---

## 6. Edge cases / regras de consistência

- **CTe em fechamento `CANCELADO`** → ignorado por `sincronizar_ajustes_cte` (filtro
  `status != 'CANCELADO'`).
- **Múltiplas alterações do mesmo CTe** → cada ajuste usa a base corrente (último ajuste
  não-cancelado), encadeando corretamente; reversão ao valor original gera delta inverso que zera
  ("+ com −").
- **Excluir CTe de fechamento PENDENTE** → cancelar (`status='CANCELADO'`) os ajustes `PENDENTE`
  daquela junction (não faz sentido manter ajuste de CTe que saiu do fechamento). Reincluir reseta
  a base no snapshot atual (o `incluir_cte` já regrava snapshot — `comissao_service.py:344-346`).
- **Operação cancelada que não está em nenhum fechamento** → nenhuma junction ativa → nenhum
  ajuste (correto: nunca foi comissionada).
- **`editar_cte_valor` bloqueado por fatura PAGA** (`pode_editar_valor()`) → valor não muda → sem
  ajuste.
- **Transação atômica**: geração/incorporação de ajustes compartilha a transação do caller; se o
  guard de não-negatividade dispara, tudo sofre rollback.

---

## 7. Plano de arquivos (preliminar — detalhado no implementation plan)

| # | Arquivo | Mudança |
|---|---|---|
| 1 | `app/carvia/models/comissao.py` | novo model `CarviaComissaoAjuste` (com `vendedor_usuario_id`); colunas `vendedor_usuario_id` + `total_ajustes` no fechamento; `recalcular_totais()` soma ajustes aplicados |
| 2 | `app/carvia/models/__init__.py` | export do novo model |
| 3 | `app/carvia/services/financeiro/comissao_service.py` | `sincronizar_ajustes_cte`; `criar_fechamento` recebe `vendedor_usuario_id` (resolve nome/email) + incorporação (match por usuário) + guard; guards em `excluir_cte`/`marcar_pago`; `buscar_ctes_elegiveis` por data de corte; cancelar ajustes em `excluir_cte` |
| 4 | `app/carvia/routes/operacao_routes.py` | hook em `editar_cte_valor` (:1320) e cancelamento (:880) |
| 5 | `app/carvia/services/documentos/operacao_cancel_service.py` | hook no cascade (:304) |
| 6 | `app/carvia/routes/comissao_routes.py` | criação com `vendedor_usuario_id` (select) + só `data_fim`; popular lista de usuários elegíveis; API elegíveis `data_fim` + `data_inicio` opcional; expor ajustes pendentes do vendedor; `data_inicio` derivada; novo endpoint `vincular-vendedor` (§4.4) |
| 7 | `app/templates/carvia/comissoes/criar.html` | vendedor → `<select>` de usuários; remove input data inicial e email livre; painel de ajustes pendentes; prévia/guard total |
| 8 | `app/templates/carvia/comissoes/detalhe.html` | seção de ajustes incorporados; bloco de vínculo de vendedor quando `vendedor_usuario_id` NULL (§4.4) |
| 9 | `migrations/versions/<rev>_carvia_comissao_ajustes.py` | DDL tabela + colunas `vendedor_usuario_id`/`total_ajustes` + backfill por e-mail |
| 10 | `app/carvia/routes/exportacao_routes.py` (:1740) | **verificar/atualizar** export de comissões para refletir `total_ajustes`/total final |
| 11 | testes pytest | unit do service (geração de delta, base corrente, guard negativo, data de corte, match por usuário) + smoke do fluxo |

Checklist obrigatório (precision-engineer):
- [ ] Route/API atualizadas no blueprint CarVia
- [ ] Link no menu — N/A (telas já acessíveis via `/carvia/comissoes`)
- [ ] Template includes/extends corretos
- [ ] Imports lazy (R2)
- [ ] Migration: DDL + Python
- [ ] Validações frontend (prévia/guard total) E backend (guards no service)

---

## 8. Riscos / pontos a confirmar

- **Filtro `acesso_comissao_carvia`**: ✅ CONFIRMADO pelo usuário (2026-06-15) que **não há**
  beneficiário sem a flag — o select por `acesso_comissao_carvia=True AND status='ativo'` está correto.
- **Fechamentos antigos sem vínculo** (`vendedor_usuario_id` NULL após backfill por e-mail): ajustes
  de CTes nesses fechamentos não casam automaticamente até o vínculo ser resolvido (§4.4). Risco
  baixo (feature nova; backlog de fechamentos pequeno) — mas a UI deve sinalizar claramente.
- **Export de comissões** (`exportacao_routes.py:1740`): ✅ REQUISITO FIRME (confirmado 2026-06-15) —
  o export e todos os consumidores de `total_comissao` **devem** refletir o total final com ajustes.
  Mapear todos os leitores de `total_comissao`/`total_ajustes` no plano.
- **Re-importação de XML** alterando `cte_valor` de operação existente: o mapeamento indica que a
  importação grava em subcontrato (`importacao_service.py:2279`), não na operação; **confirmar no
  plano** que não há caminho de update de `CarviaOperacao.cte_valor` fora de `editar_cte_valor`.
