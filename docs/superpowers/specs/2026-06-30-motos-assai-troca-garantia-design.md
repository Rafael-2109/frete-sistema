<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Motos Assaí — Troca em Garantia (swap-in-place) — Design

> **Papel:** design do processo de **troca em garantia** de motos Q.P.A. (cliente final do Assaí troca a moto comprada por outra do mesmo modelo, sem documento fiscal de devolução nem de saída), centralizado na seção **Pós-venda**.

## Indice

- [Contexto](#contexto)
  - [1.1 O processo de negócio](#11-o-processo-de-negócio)
  - [1.2 O descasamento físico-fiscal](#12-o-descasamento-físico-fiscal)
  - [1.3 Por que nenhum fluxo atual cobre](#13-por-que-nenhum-fluxo-atual-cobre)
- [2. Decisões aprovadas (Q&A com o dono do produto)](#2-decisões-aprovadas-qa-com-o-dono-do-produto)
- [3. Modelo da solução: swap-in-place](#3-modelo-da-solução-swap-in-place)
- [4. Modelo de dados](#4-modelo-de-dados)
  - [4.1 Extensão de `assai_pos_venda_ocorrencia`](#41-extensão-de-assai_pos_venda_ocorrencia)
  - [4.2 Motivo de vínculo `TROCA_GARANTIA`](#42-motivo-de-vínculo-troca_garantia)
  - [4.3 Eventos de moto: zero evento novo](#43-eventos-de-moto-zero-evento-novo)
- [5. Serviço `troca_garantia_service` — sequência exata](#5-serviço-troca_garantia_service-sequência-exata)
  - [5.1 O bloqueio crítico (B livre) e como resolvemos](#51-o-bloqueio-crítico-b-livre-e-como-resolvemos)
  - [5.2 Sequência de `registrar_troca`](#52-sequência-de-registrar_troca)
  - [5.3 Pré-condições e guards](#53-pré-condições-e-guards)
  - [5.4 O gap do espelho Nacom](#54-o-gap-do-espelho-nacom)
- [6. UI e link Faturamento ↔ Pós-venda](#6-ui-e-link-faturamento--pós-venda)
  - [6.1 Entrada no Pós-venda + seleção de motos](#61-entrada-no-pós-venda--seleção-de-motos)
  - [6.2 Picker da moto B (DISPONIVEL + ver outros estados)](#62-picker-da-moto-b-disponivel--ver-outros-estados)
  - [6.3 Reflexo no Faturamento](#63-reflexo-no-faturamento)
- [7. Migrations](#7-migrations)
- [8. Fronteiras de escopo](#8-fronteiras-de-escopo)
- [9. Plano de testes (TDD)](#9-plano-de-testes-tdd)
- [10. Riscos e tratativas](#10-riscos-e-tratativas)
- [11. Referências de código](#11-referências-de-código)

---

## Contexto

### 1.1 O processo de negócio

1. Vendemos motos elétricas ao **Assaí** (atacadista) com **NF de venda** (Q.P.A. → Sendas/Assaí).
2. O Assaí revende ao **cliente final**.
3. A moto apresenta defeito; o cliente final nos procura.
4. Para resolver, fazemos uma **troca em garantia**: pegamos de volta a moto defeituosa e entregamos **outra do mesmo modelo** (a cor pode variar).
5. O evento é controlado **manualmente** pela seção **Pós-venda**. Não há NF de devolução (NFd) na volta nem NF de saída na entrega da nova moto — é uma **troca sem documento fiscal**.

Convenção de nomes neste design:
- **Moto A** = a defeituosa, hoje `FATURADA` numa NF de venda ao Assaí; **volta** fisicamente ao CD.
- **Moto B** = a nova/substituta, hoje **livre** no estoque (`DISPONIVEL`); **sai** para o cliente final.

### 1.2 O descasamento físico-fiscal

Sem tratamento, a troca cria dois descasamentos:
- **Chassi A**: fisicamente no nosso CD, mas no sistema continua `FATURADA`, `AssaiNfQpaItem.devolvido=False`, NF `BATEU`, `qtd_faturada` inflada no pedido → *o sistema não enxerga o retorno.*
- **Chassi B**: fisicamente no cliente, mas no sistema continua `DISPONIVEL`/`MONTADA` → **estoque fantasma** (conta como vendável e nunca recebe NF real).

### 1.3 Por que nenhum fluxo atual cobre

| Estrutura existente | Por que não serve |
|---|---|
| `assai_pos_venda_ocorrencia` (`pos_venda_service`) | Relato textual; **não emite evento**, não mexe em estoque, 1 chassi só (sem par A↔B) |
| `assai_devolucao_nfd` (`devolucao_service`) | Exige `numero_nfd` obrigatório (`UNIQUE`) + último evento `==FATURADA`. A troca é **sem NFd** → bloqueado |
| `assai_divergencia` (9 tipos) | Nenhum tipo cobre "retorno sem NFd" nem "saída sem NF" |
| CCe `aplicar_correcao_cce` | Troca chassi na NF, mas reverte o antigo para `CARREGADA`/`SEPARADA` (não `PENDENTE`) e **só fecha o match se o novo chassi já estiver numa separação** |

Confirmação por `grep`: toda menção a "troca/substituir" no módulo refere-se a troca de chassi em separação/CCe — **não existe** infraestrutura de troca em garantia.

---

## 2. Decisões aprovadas (Q&A com o dono do produto)

| # | Decisão | Justificativa do dono |
|---|---|---|
| D1 | **Escopo fiscal = só controle interno.** O descasamento (A consta vendida / B consta em estoque no SEFAZ) é estado conhecido e aceito. Sem painel de exposição, sem geração de documento. | Troca é deliberadamente sem NF |
| D2 | **Moto A volta como `PENDENTE`.** Não existem estados "conserto/sucata/revenda" — o estado correto é `PENDENTE` (o mesmo que `devolucao_service` já emite). | "o estado correto nesse caso é pendência" |
| D3 | **Moto B vira `FATURADA` assumindo o slot de A na NF.** Faturamento fica com a moto que está de fato com o cliente = consistência fiscal real. | "mantém consistência" |
| D4 | **Registro centralizado no Pós-venda**, não em tabela própria nem no Faturamento. Faturamento identifica a troca *via* o registro de pós-venda (link `nf_qpa_id`), sem colunas de troca próprias. | "Faturamento fica com moto B, pós-venda fica registrado A→B" |
| D5 | **Frete: não gerar leg nova.** O swap só sincroniza o espelho Nacom existente (B herda a linha já faturada de A). O envio físico de B ao cliente é controlado no pós-venda. | "a questão física da moto deverá ser tratada no pós-venda" |
| D6 | **Seleção de B = picker `DISPONIVEL` do mesmo modelo** + toggle "Ver em outros estados" (`SEPARADA`/`MONTADA`/`ESTOQUE` bloqueadas, com aviso de tratativa). Só `DISPONIVEL` é selecionável. | Alertar que há mais opções, mas precisam de tratativa |

Decisão de engenharia derivada (D4): em vez de uma tabela `assai_troca_garantia` separada, **estendemos `assai_pos_venda_ocorrencia`** (a troca é uma ocorrência de pós-venda especializada).

---

## 3. Modelo da solução: swap-in-place

A moto A é **substituída por B na própria NF** (mecânica análoga à da CCe), com dois deltas em relação à CCe: A vai para `PENDENTE` (não `CARREGADA`/`SEPARADA`), e B (que está **livre**, fora de qualquer separação) precisa **assumir o slot de separação** que A deixou para que o match a reconheça.

Resultado final desejado:

```
ANTES                                  DEPOIS
NF (item)      : chassi = A            NF (item)      : chassi = B
sep_item       : chassi = A            sep_item       : chassi = B   (mesma linha, mutada)
status_efetivo : A = FATURADA          status_efetivo : A = PENDENTE  (volta ao estoque)
                 B = DISPONIVEL                         B = FATURADA  (consistência fiscal)
espelho Nacom  : chassi_assai = A      espelho Nacom  : chassi_assai = B  (frete vê B)
pós-venda      : —                     pós-venda      : ocorrência TROCA_GARANTIA A→B (link nf_qpa_id)
```

---

## 4. Modelo de dados

### 4.1 Extensão de `assai_pos_venda_ocorrencia`

A ocorrência já tem `chassi` (= A, sujeito natural do pós-venda), `categoria` (`CLIENTE`), `descricao` (`NOT NULL` = motivo do defeito) e anexos S3 (fotos). Adicionamos:

| Coluna | Tipo | Função |
|---|---|---|
| `tipo` | varchar(20), `NOT NULL`, default `'RELATO'` | `RELATO` (comportamento atual) \| `TROCA_GARANTIA` |
| `chassi_substituto` | varchar(50), nullable | a moto **B** que saiu |
| `nf_qpa_id` | FK → `assai_nf_qpa.id`, nullable | o **link** que o Faturamento consulta |

**Guards de imutabilidade** (porque a ocorrência é mutável por padrão e a troca produz efeito fiscal):
- Em ocorrências `tipo='TROCA_GARANTIA'`, os campos `chassi`, `chassi_substituto`, `nf_qpa_id`, `tipo` ficam **congelados** após a criação (`atualizar_ocorrencia` rejeita alteração desses campos).
- `excluir_ocorrencia` é **bloqueado** para `tipo='TROCA_GARANTIA'`.
- `descricao` e anexos (fotos) seguem editáveis (documentação).

### 4.2 Motivo de vínculo `TROCA_GARANTIA`

`AssaiNfQpaItemVinculoHistorico.motivo` tem CHECK `ck_assai_nf_qpa_item_vinculo_motivo` (hoje: `NF_CANCELADA`, `CCE_ALTEROU_CHASSI`, `SUBSTITUICAO_CROSS_LOJA` — `migrations/motos_assai_26`). Adicionar `TROCA_GARANTIA`:
- Constante `VINCULO_MOTIVO_TROCA_GARANTIA = 'TROCA_GARANTIA'` em `models/nf_qpa_vinculo.py` + incluir em `VINCULO_MOTIVOS_VALIDOS`.
- `ALTER` do CHECK (padrão idempotente da Migration 33).

Esse histórico é a **trilha append-only** do swap de chassi na NF (preserva `separacao_item_id` e o chassi no momento).

### 4.3 Eventos de moto: zero evento novo

`PENDENTE` e `FATURADA` já constam no CHECK `ck_assai_moto_evento_tipo`. A transição `FATURADA → PENDENTE` já é usada por `devolucao_service.py:199`. `emitir_evento` não tem guard de sequência (valida só `tipo ∈ EVENTOS_VALIDOS`). **Nenhuma migration de evento é necessária.**

---

## 5. Serviço `troca_garantia_service` — sequência exata

A mecânica do swap vive num serviço **dedicado** (responsabilidade única — orquestra NF + separação + espelho + pós-venda), **invocado pela** rota de pós-venda. Os dados ficam no pós-venda (D4); a lógica fica isolada.

### 5.1 O bloqueio crítico (B livre) e por que o swap é cirúrgico

Reusar a mecânica da CCe (`aplicar_correcao_cce` → `_calcular_match`) **não funciona** aqui, por dois motivos descobertos no traçado do código:

1. **`_calcular_match` ignora seps `FATURADA`** (`nf_qpa_adapter.py:599-609`: `WHERE AssaiSeparacao.status NOT IN (FATURADA, CANCELADA)`). A sep que A ocupa **já é `FATURADA`** (a NF bateu). Logo o match nunca encontraria o slot para religar B — `CHASSI_SEM_SEPARACAO` → `DIVERGENTE`.
2. **`sincronizar_espelho_com_separacao` reconcilia por delta** (cria/deleta). Ele criaria uma linha nova para B e tentaria **deletar** a de A — mas a deleção é **bloqueada** porque a linha de A tem `numero_nf` preenchido (`separacao_mirror_service.py:563-574`) → A e B ficariam **duplicados** no espelho.

**Solução — swap cirúrgico:** como conhecemos o vínculo 1:1 exato (A está numa `AssaiSeparacaoItem` apontada por `AssaiNfQpaItem.separacao_item_id`), fazemos a troca diretamente, **sem** `_calcular_match` e **sem** o delta de sincronização: mutamos `AssaiSeparacaoItem.chassi` A→B in-place (preserva `valor_unitario_qpa`/modelo/sep), religamos o `AssaiNfQpaItem` a B, emitimos os eventos diretamente (como `cancelamento`/`devolucao` já fazem) e trocamos `chassi_assai` no espelho in-place. A sep permanece `FATURADA` o tempo todo — ela representa "1 moto vendida nesta NF", e essa moto passa a ser B.

### 5.2 Sequência de `registrar_troca`

`registrar_troca(*, nf_id, chassi_a, chassi_b, operador_id, motivo, dry_run=True)` — `dry_run=True` é o **default** (padrão das skills WRITE do módulo): valida tudo e devolve o plano, sem efetivar.

1. **Valida** todas as pré-condições (§5.3). Em `dry_run`, retorna o plano e para aqui.
2. Lock pessimista: `with_for_update` em `AssaiMoto(A)` e `AssaiMoto(B)`.
3. `nf_item = AssaiNfQpaItem(nf_id, chassi=A)`; `sep_item = AssaiSeparacaoItem.get(nf_item.separacao_item_id)`; `sep_id = sep_item.separacao_id`.
4. Grava `AssaiNfQpaItemVinculoHistorico(nf_qpa_item_id, separacao_item_id=sep_item.id, motivo=TROCA_GARANTIA, chassi_no_momento=A, registrado_por_id, detalhes={chassi_novo:B, nf_id})`. *(reusa o model do `cancelamento_nf_service.py:230-238)*
5. **Muta o slot in-place**: `sep_item.chassi = B` (preserva valor/modelo/sep). `nf_item.chassi = B`; `nf_item.tipo_divergencia = None`; mantém `nf_item.separacao_item_id` (já aponta para o slot, agora B).
6. `emitir_evento(B, SEPARADA)` depois `emitir_evento(B, FATURADA)` — B passa a ser a moto vendida (ordem por `id` garante FATURADA como último). `dados_extras={origem:'troca_garantia', nf_id, chassi_substituido:A}`. A `sep.status` já é `FATURADA` — inalterada.
7. `emitir_evento(A, PENDENTE, observacao="Troca garantia NF {n}: substituída por {B}")` — A volta ao estoque (D2).
8. **Espelho in-place**: `separacao_mirror_service.trocar_chassi_no_espelho(sep_id, A, B)` → `UPDATE separacao SET chassi_assai=B WHERE separacao_lote_id=lote AND chassi_assai=A` (preserva `numero_nf`/status; sem leg nova — D5; §5.4).
9. Cria `AssaiPosVendaOcorrencia(chassi=A, categoria=CLIENTE, tipo=TROCA_GARANTIA, chassi_substituto=B, nf_qpa_id=nf_id, descricao=motivo, criado_por_id=operador_id)`; opcionalmente anexa fotos.
10. `db.session.commit()`.

### 5.3 Pré-condições e guards (validados antes de qualquer escrita)

- A existe na NF (`AssaiNfQpaItem(nf_id, chassi=A)`) **com `separacao_item_id` preenchido**; `status_efetivo(A) == FATURADA`; NF não `CANCELADA`.
- B existe em `assai_moto`; `status_efetivo(B) == DISPONIVEL`. *(DISPONIVEL já implica recebida+montada+livre — chegou a esse estado pelo pipeline; não há guard de recibo separado porque o swap não roda `_calcular_match`.)*
- B é do **mesmo modelo** de A (cor pode variar).
- Idempotência: não existe ocorrência `TROCA_GARANTIA` para o par (`nf_qpa_id`, `chassi=A`).

### 5.4 Espelho Nacom: swap in-place (novo helper)

O espelho `separacao` Nacom (1 linha por chassi via `chassi_assai`, criada quando a sep fechou) precisa apontar para B, senão o frete enxergaria a moto defeituosa A. **Não** se pode usar `sincronizar_espelho_com_separacao` (delta create/delete — a deleção da linha de A é bloqueada pelo `numero_nf`, §5.1).

Novo helper **`trocar_chassi_no_espelho(assai_sep_id, chassi_de, chassi_para)`** em `separacao_mirror_service.py`: `UPDATE` direto de `chassi_assai` A→B na(s) linha(s) do lote `ASSAI-SEP-{id}`, preservando `numero_nf`/status. Como A e B são do **mesmo modelo**, os demais campos da linha (`cod_produto`, `nome_produto`, `peso`, `valor_saldo`) são idênticos — só `chassi_assai` muda. `numero_nf` preservado ⇒ **nenhuma cotação/leg nova** (D5): B herda a linha já faturada de A.

---

## 6. UI e link Faturamento ↔ Pós-venda

### 6.1 Entrada no Pós-venda + seleção de motos

Nova ação na seção Pós-venda: **"Registrar troca em garantia"**.
- **Moto A (defeituosa)**: escolhida na **lista de motos vendidas** do pós-venda (chassis presentes em `assai_nf_qpa_item`). Reusa `listar_motos_vendidas` + `chassi_foi_vendido`. Resolve a NF de A via `rastrear_chassi`/`_buscar_nfs` (a NF `BATEU` com `devolvido=False`).
- **Moto B (substituta)**: picker descrito em §6.2.
- **Motivo** (= `descricao`, obrigatório) + **fotos** (anexos, opcionais).

### 6.2 Picker da moto B (DISPONIVEL + ver outros estados)

- **Padrão**: motos `DISPONIVEL` do **mesmo modelo de A** (chassi + cor). Apenas estas são **selecionáveis**.
- **Toggle "Ver em outros estados"**: revela motos do mesmo modelo em `SEPARADA` / `MONTADA` / `ESTOQUE` como **bloqueadas**, com o aviso *"existem mais opções, mas precisam de tratativa para virar DISPONIVEL"*:
  - `MONTADA` → precisa **Disponibilizar**.
  - `ESTOQUE` → precisa **Montar** + **Disponibilizar**.
  - `SEPARADA` → precisa **liberar** da separação ativa.
- Reuso: `chassi_autocomplete_service.buscar_chassis` (novo contexto `troca_substituto`, filtrando `DISPONIVEL` por modelo) + `resumo_service` para as contagens por estado.

### 6.3 Reflexo no Faturamento

Faturamento **não ganha colunas de troca**; consulta o pós-venda por `nf_qpa_id`:
- **Detalhe da NF** (`routes/faturamento.py:440` → `faturamento_nf_detalhe`, template `nf_detalhe.html`): seção "Troca em Garantia" (A → B, data, motivo) + badge, espelhando o bloco `devolucoes_da_nf` existente (`nf_detalhe.html:95-133`). Link para a ocorrência de pós-venda.
- **Lista de NFs** (`faturamento_lista`, no batch-load junto de `cces_por_nf:136-152`): badge "Troca" + pesquisável por NF.

Query base: `AssaiPosVendaOcorrencia.query.filter_by(nf_qpa_id=nf.id, tipo='TROCA_GARANTIA')`.

---

## 7. Migrations

> Toda migration = par DDL `.sql` + `.py` (regra do projeto). Schema JSON regenerado via `generate_schemas.py`. Próximo número livre: `motos_assai_34_troca_garantia`.

1. **`assai_pos_venda_ocorrencia`**: `ADD COLUMN tipo varchar(20) NOT NULL DEFAULT 'RELATO'`, `ADD COLUMN chassi_substituto varchar(50)`, `ADD COLUMN nf_qpa_id integer REFERENCES assai_nf_qpa(id)`. Index em `nf_qpa_id`. Backfill: linhas existentes recebem `tipo='RELATO'` (default cobre).
2. **`ck_assai_nf_qpa_item_vinculo_motivo`**: `DROP CONSTRAINT IF EXISTS` + `ADD CONSTRAINT ... CHECK (motivo IN ('NF_CANCELADA','CCE_ALTEROU_CHASSI','SUBSTITUICAO_CROSS_LOJA','TROCA_GARANTIA'))` (idempotente, padrão Migration 33).
3. **Sem migration** para `ck_assai_moto_evento_tipo` (PENDENTE/FATURADA já constam).

---

## 8. Fronteiras de escopo

- **Fiscal = só controle interno** (D1). `AssaiNfQpaItem.devolvido` **não** é tocado (exclusivo do fluxo NFd). `qtd_faturada` do pedido **não muda** — B substitui A na mesma NF, o saldo de venda é o mesmo; `recalcular_status_pedido` **não** é chamado.
- **Frete** (D5): só sincroniza o espelho existente; sem cotação/leg nova. O transporte físico de B ao cliente e o retorno de A são tratados/ registrados no pós-venda.
- **Reversão de troca**: fora do MVP. A trilha append-only (`vinculo_historico` + `assai_moto_evento`) permite auditar; desfazer = troca inversa registrada depois.
- **Multi-troca**: 1 ocorrência `TROCA_GARANTIA` = 1 par A→B. Se B falhar depois, B→C é uma nova troca (chassi=B).

---

## 9. Plano de testes (TDD)

| Caso | Esperado |
|---|---|
| Swap feliz | B → `FATURADA`; A → `PENDENTE`; NF item.chassi=B; sep_item.chassi=B; espelho `chassi_assai`=B; ocorrência `TROCA_GARANTIA` criada com `nf_qpa_id` |
| `dry_run` (default) | Plano retornado, **zero** escrita |
| Guard: A não-`FATURADA` | Rejeita, sem mutação |
| Guard: B não-`DISPONIVEL` / em uso | Rejeita |
| Guard: modelo divergente | Rejeita |
| Idempotência | 2ª chamada do mesmo par rejeita (guard) |
| Imutabilidade | `atualizar`/`excluir` em ocorrência `TROCA_GARANTIA` bloqueado nos campos estruturais |
| Link Faturamento | Detalhe e lista da NF exibem a troca; busca por NF funciona |
| Espelho Nacom | `separacao.chassi_assai` reflete B; `numero_nf` preservado (sem frete novo) |

## 10. Riscos e tratativas

| Risco | Tratativa |
|---|---|
| Espelho desatualizado (B não aparece no frete) | Passo 8 obrigatório (`trocar_chassi_no_espelho`) — coberto por teste |
| `_calcular_match` ignora sep `FATURADA`; delta de espelho bloqueado por `numero_nf` | Swap cirúrgico direto (§5.1): **sem** `_calcular_match`, **sem** `sincronizar_espelho_com_separacao` |
| Corrida em A/B | `with_for_update` em `AssaiMoto(A)` e `AssaiMoto(B)` |
| A ausente / não-faturada na NF | Validação explícita (§5.3) — rejeita antes de qualquer escrita |

## 11. Referências de código

- Swap de chassi (reuso parcial): `app/motos_assai/services/cancelamento_nf_service.py:183` (`aplicar_correcao_cce`), linhas 224-275.
- Match e `FATURADA` (referência p/ entender por que **não** usamos): `app/motos_assai/services/parsers/nf_qpa_adapter.py:567` (`_calcular_match`), 599-609 (busca sep_item exclui `FATURADA`), 691-712 (guard recibo).
- Transição `FATURADA → PENDENTE` (emissão direta): `app/motos_assai/services/devolucao_service.py:199`.
- Emissão direta de evento por serviço (padrão): `app/motos_assai/services/cancelamento_nf_service.py:263` (CARREGADA/SEPARADA).
- Eventos: `app/motos_assai/services/moto_evento_service.py` (`emitir_evento(chassi, tipo, operador_id, observacao, dados_extras, ocorrido_em)` — NÃO commita, faz `flush`; `status_efetivo`); `app/motos_assai/models/moto.py` (`EVENTO_*`, `EVENTOS_VALIDOS`, CHECK `ck_assai_moto_evento_tipo`).
- Espelho Nacom: `app/motos_assai/services/separacao_mirror_service.py` — `mirror_assai_to_separacao:130` (cria linhas, campo `chassi_assai`), `sincronizar_espelho_com_separacao:493` (delta — **não** usado), `lote_id_de` (helper de lote). **Novo**: `trocar_chassi_no_espelho`.
- Vínculo histórico + CHECK: `app/motos_assai/models/nf_qpa_vinculo.py`; `scripts/migrations/motos_assai_26_vinculo_historico.sql`.
- Pós-venda: `app/motos_assai/models/pos_venda.py`, `app/motos_assai/services/pos_venda_service.py`, `app/motos_assai/routes/pos_venda.py`.
- Faturamento UI: `app/motos_assai/routes/faturamento.py:39` (lista), `:440` (detalhe); `app/templates/motos_assai/faturamento/{lista_separacoes,nf_detalhe}.html`.
- Picker/autocomplete: `app/motos_assai/services/chassi_autocomplete_service.py`; contagens: `app/motos_assai/services/resumo_service.py`.
- Padrão arquitetural de referência: `app/motos_assai/CLAUDE.md`.
