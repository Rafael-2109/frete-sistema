<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-25
-->
# Módulo HORA — Lojas Motochefe

> **Papel:** guia de desenvolvimento do modulo HORA — controle de estoque unitario de motos eletricas nas lojas fisicas da HORA (B2C varejo), com fronteira estrita contra outros modulos.

## Indice

- [Contexto](#contexto)
- [Fronteira do módulo (o que NÃO fazer)](#fronteira-do-módulo-o-que-não-fazer)
- [Convenções obrigatórias](#convenções-obrigatórias)
  - [1. Prefixo de tabela `hora_`](#1-prefixo-de-tabela-hora_)
  - [2. Blueprint Flask isolado](#2-blueprint-flask-isolado)
  - [3. Menu](#3-menu)
- [Invariante central (resumo)](#invariante-central-resumo)
- [Modelo de dados (46 tabelas — núcleo conceitual abaixo)](#modelo-de-dados-46-tabelas-núcleo-conceitual-abaixo)
  - [Tabelas complementares (32)](#tabelas-complementares-32)
- [Autorização granular (decorator + service)](#autorização-granular-decorator-service)
- [Parsers reusados (via adapter)](#parsers-reusados-via-adapter)
- [O que NÃO fazer (lista explícita)](#o-que-não-fazer-lista-explícita)
- [Ordem de implementação planejada](#ordem-de-implementação-planejada)
- [11. Peças (cadastro, estoque, faturamento) — 2026-05-05](#11-peças-cadastro-estoque-faturamento-2026-05-05)
- [13. Listagem de Pedidos de Venda com itens inline + filtro chassi — 2026-05-06](#13-listagem-de-pedidos-de-venda-com-itens-inline-filtro-chassi-2026-05-06)
- [14. Backfill `tagplus_pedido_id` para vendas legadas — 2026-05-06](#14-backfill-tagplus_pedido_id-para-vendas-legadas-2026-05-06)
- [12. Unificação de modelos (N nomes → 1 canônico) — 2026-05-06](#12-unificação-de-modelos-n-nomes-1-canônico-2026-05-06)
- [15. Preço A vista / A prazo + desconto % por moto — 2026-05-06](#15-preço-a-vista-a-prazo-desconto-por-moto-2026-05-06)
- [16. Campo `consumidor_final` no faturamento TagPlus — 2026-05-07 (revisado)](#16-campo-consumidor_final-no-faturamento-tagplus-2026-05-07-revisado)
- [17. Desconsiderar moto de NF de compra — 2026-06-03](#17-desconsiderar-moto-de-nf-de-compra--2026-06-03)
- [18. Unificação da tela de Pedido de Venda + filtro loja/vendedor + fix desconto — 2026-06-03](#18-unificação-da-tela-de-pedido-de-venda--filtro-lojavendedor--fix-desconto--2026-06-03)
- [19. Guarda do recebimento automático (anti-ressurreição) — 2026-06-03](#19-guarda-do-recebimento-automático-anti-ressurreição--2026-06-03)
- [20. Editar item (moto travada) + Enter=Próximo + chassi autocomplete + restauração de regressões — 2026-06-03](#20-editar-item-moto-travada--enterpróximo--chassi-autocomplete--restauração-de-regressões--2026-06-03)
- [21. Unificação multi-item do Pedido de Venda + "Salvar Pedido" único (FU-1/2/3/5) — 2026-06-04](#21-unificação-multi-item-do-pedido-de-venda--salvar-pedido-único-fu-1235--2026-06-04)
- [Onboarding Tours (2026-05-08)](#onboarding-tours-2026-05-08)
- [Referências](#referências)

## Contexto

PJ distinta da Motochefe-distribuidora e da CarVia. Nao compartilha dados com modulos vizinhos — joins, FKs cross-modulo e imports de modelos de outros modulos sao proibidos (reuso so via adapter). Fluxos pedido -> NF -> recebimento em producao, com permissoes granulares ativas. A fronteira e reforcada em camada-tool pelo Agente Lojas HORA (`app/agente_lojas/`).

**Data**: 2026-05-20 (atualizado)
**Status**: em produção — modelos, migrations e fluxos pedido→NF→recebimento implementados; permissões granulares ativas.
**Propósito**: controle de estoque unitário de motos elétricas nas lojas físicas da HORA (PJ distinta da Motochefe-distribuidora e CarVia).

---

## Fronteira do módulo (o que NÃO fazer)

O módulo HORA **não compartilha dados** com os módulos abaixo. Joins, FKs cross-módulo e imports de modelos de outros módulos para código HORA são proibidos.

| Módulo vizinho | Motivo da fronteira | O que NÃO misturar |
|---|---|---|
| `app/motochefe/` (distribuidora) | PJ diferente (Motochefe ≠ HORA). Motochefe é B2B atacadista; HORA é B2C varejo. | Não importar `Moto`, `PedidoVendaMoto`, `ClienteMoto`. Não reusar status enum. |
| `app/carvia/` (transportadora) | PJ diferente. CarVia só transporta; não tem estoque. | Não importar `FaturaCarVia`, modelos de CTe. |
| `app/cadastros_*`, `app/faturamento`, etc. | Clientes e produtos da Nacom Goya são indústria alimentícia; nada a ver com motos varejo. | Zero relação. |

**Reuso permitido (via adapter, não import direto)**:
- `app/carvia/services/parsers/danfe_pdf_parser.py` — extrai chassi/modelo/cor de DANFE via LLM. **Usar via `app/hora/services/parsers/danfe_adapter.py`** que encapsula a chamada e traduz para entidades HORA.
- `app/carvia/services/pricing/moto_recognition_service.py` — regex de padronização de nomes de modelo. Mesmo padrão de adapter.

**Barreira SDK adicional (Agente Lojas HORA)**: o `app/agente_lojas/` reforça este contrato em camada-tool via `skills=sorted(SKILLS_PERMITIDAS)` em `ClaudeAgentOptions` (SDK 0.1.77+). Skills do domínio Nacom Goya (`cotando-frete`, `rastreando-odoo`, `gerindo-expedicao`, `acessando-ssw`, `gerindo-carvia`, `executando-odoo-financeiro`, etc.) ficam **rejeitadas pelo Skill tool** — o operador HORA não consegue invocá-las mesmo via prompt. Detalhe técnico em `app/agente_lojas/CLAUDE.md` (seção "Barreira SDK adicional"). Esta barreira **complementa** o code review humano, não substitui.

---

## Convenções obrigatórias

### 1. Prefixo de tabela `hora_`

Todas as tabelas do módulo vivem no schema `public` e começam com `hora_`. Exemplos: `hora_loja`, `hora_moto`, `hora_pedido`, `hora_pedido_item`, `hora_nf_entrada`, `hora_nf_entrada_item`, `hora_recebimento`, `hora_recebimento_conferencia`, `hora_venda`, `hora_venda_item`, `hora_moto_evento`, `hora_modelo`, `hora_tabela_preco`.

**Não usar** schema PostgreSQL separado nem bind SQLAlchemy dedicado. Decisão tomada em 2026-04-18 pelo usuário: isolamento via prefixo + code review + este CLAUDE.md é suficiente.

### 2. Blueprint Flask isolado

Rotas em `app/hora/routes/`, services em `app/hora/services/`, models em `app/hora/models/`. Blueprint registrado em `app/__init__.py` com `url_prefix='/hora'`. Templates em `app/templates/hora/`.

### 3. Menu

Toda tela do módulo DEVE ter link em `app/templates/base.html` (submenu dedicado "Lojas HORA") ou em tela-mãe do próprio módulo. Regra global: nunca criar tela sem acesso via UI.

---

## Invariante central (resumo)

**`hora_moto.chassi` é a chave universal do módulo.** Detalhes completos: `docs/hora/INVARIANTES.md`.

Em 1 linha por invariante:
1. Chassi é a chave de rastreamento universal.
2. Toda tabela transacional tem `chassi` FK indexada.
3. `hora_moto` é insert-once com atributos imutáveis (chassi, modelo_id, cor, motor, ano).
4. Estado atual = consulta à tabela de eventos, não UPDATE na linha da moto.

**Consequências práticas**:
- Nunca escreva `UPDATE hora_moto SET status = ...`. Em vez disso, `INSERT INTO hora_moto_evento (chassi, tipo, ...)`.
- Ao criar uma nova tabela transacional, pergunte: "tem `chassi`?" Se não, revise o desenho.
- Ao adicionar coluna em `hora_moto`, pergunte: "esse dado pode mudar durante a vida da moto?" Se sim, o lugar certo é satélite.

**Exceções autorizadas (UPDATE em `hora_moto.cor` e `modelo_id` apenas)**:
1. Retroatividade de modelo sentinela (`modelo_retroatividade_service.propagar_resolucao`).
2. Recebimento como SOT: `recebimento_service._aplicar_correcao_moto_se_divergir` UPDATE-eia cor/modelo quando conferência diverge da NF (regra confirmada pelo dono do módulo em 2026-05-06). Categoria nova de evento `MOTO_FALTANDO` (em `EVENTOS_FALTANDO_FISICAMENTE`) emitida por `finalizar_recebimento` para chassis declarados na NF mas que não chegaram fisicamente — não conta como disponível em estoque.
   Detalhes em `docs/hora/INVARIANTES.md` seção "Exceções controladas".

---

## Modelo de dados (46 tabelas — núcleo conceitual abaixo)

> O módulo tem **46 tabelas** `hora_*` em produção (lista completa: `grep -rhoE "__tablename__\s*=\s*['\"]hora_[a-z0-9_]+" app/hora/`). A lista abaixo cobre o núcleo conceitual; as auxiliares (empréstimo, devolução fornecedor/venda, conferência/auditoria, parser DANFE, pagamentos) seguem o mesmo padrão.

Documentação detalhada na análise de primeiros princípios do módulo (comando `/fp-lojas-motochefe` — `.claude/commands/fp-lojas-motochefe.md`). Resumo:

**Cadastros**:
- `hora_loja` — lojas físicas (identidade, CNPJ, nome).
- `hora_modelo` — catálogo de modelos (modelo + variantes).
- `hora_tabela_preco` — preço de tabela por modelo com vigência.

**Identidade**:
- `hora_moto` — uma linha por moto física, insert-once.

**Fluxo de entrada** (Motochefe → HORA):
- `hora_pedido` + `hora_pedido_item` — pedido da HORA à Motochefe.
- `hora_nf_entrada` + `hora_nf_entrada_item` — NF recebida da Motochefe.
- `hora_recebimento` + `hora_recebimento_conferencia` — ato de receber na loja + QR code + foto + divergências.

**Fluxo de saída** (HORA → consumidor):
- `hora_venda` + `hora_venda_item` — venda ao consumidor final, multi-item possível, com `preco_tabela_ref` + `desconto_aplicado` + `preco_final` auditáveis.

**Histórico**:
- `hora_moto_evento` — log de todas as transições de estado por chassi.

**Autorização (adicionada 2026-04-22)**:
- `hora_user_permissao` — permissões granulares por (`user_id`, `modulo`) com flags `pode_ver/criar/editar/apagar/aprovar`. Sem FK para `usuarios` (mantém `app/hora` independente de `app/auth`). Migration: `scripts/migrations/hora_13_user_permissao.{py,sql}`.

### Tabelas complementares (32)

> Núcleo acima (14) + estas 32 = 46. Padrões recorrentes: header + itens; auditoria append-only (nunca UPDATE/DELETE); fotos/anexos em S3.

**Avaria**:
- `hora_avaria` — avaria física em moto (`numero_chassi`, `loja_id`, `status`); NÃO bloqueia venda, emite evento `AVARIADA`.
- `hora_avaria_foto` — fotos S3 de uma avaria (header + N fotos).

**Devolução fornecedor (HORA → Motochefe)**:
- `hora_devolucao_fornecedor` — header de devolução de motos ao fornecedor (`motivo`, `status`, `nf_saida_chave_44`).
- `hora_devolucao_fornecedor_item` — 1 chassi por linha (UNIQUE por devolução).

**Devolução venda (cliente → HORA)**:
- `hora_devolucao_venda` — header de devolução pelo consumidor (`venda_id`, `motivo`, `status`). NÃO confundir com devolução fornecedor.
- `hora_devolucao_venda_item` — chassi devolvido, resolução individual (`resolucao_acao`: DISPONIVEL/AVARIA/PECA_FALTANDO).

**Empréstimo**:
- `hora_emprestimo_moto` — empréstimo entre loja HORA e externa (`tipo` SAIDA/ENTRADA); ressarcimento com outra moto do mesmo modelo.

**Modelo / Alias**:
- `hora_modelo_alias` — N nomes → 1 modelo canônico (`tipo`: TAGPLUS_*/NOME_NF/NOME_PEDIDO). UNIQUE `(tipo, nome_alias)`.
- `hora_modelo_pendente` — fila de nomes não reconhecidos aguardando decisão do operador (`origem`, `status`, `qtd_ocorrencias`).

**Peças (fungíveis, sem chassi)**:
- `hora_peca` — catálogo de peças (`codigo_interno` UNIQUE, `ncm`, `cfop_default`). NÃO confundir com `hora_peca_faltando`.
- `hora_tagplus_peca_map` — mapeamento opcional peça → TagPlus (UNIQUE `peca_id`).
- `hora_peca_movimento` — log signed de entradas/saídas por loja; saldo via `SUM(qtd)` (sem materialização).
- `hora_nf_entrada_item_peca` — linha de peça em NF de entrada com conferência 1:1 (`qtd_nf` vs `qtd_conferida`).
- `hora_venda_item_peca` — linha de peça em venda (`preco_unitario_referencia` snapshot, `desconto_aplicado`).

**Peças faltando em moto**:
- `hora_peca_faltando` — peça ausente em moto (N por moto); canibalização via `chassi_doador` (emite `FALTANDO_PECA` na doadora).
- `hora_peca_faltando_foto` — fotos S3 da pendência.

**Conferência / Auditoria de recebimento**:
- `hora_conferencia_divergencia` — divergências 1-N por conferência (`tipo`: MODELO/COR_DIFERENTE, MOTO_FALTANDO, CHASSI_EXTRA, AVARIA). UNIQUE `(conferencia_id, tipo)`.
- `hora_conferencia_auditoria` — log append-only de ações no recebimento (imutável).

**Transferência entre filiais**:
- `hora_transferencia` — header (`loja_origem/destino`, `status`); emissão→EM_TRANSITO, confirmação→TRANSFERIDA.
- `hora_transferencia_item` — chassi na transferência (`qr_code_lido`, `foto_s3_key`). UNIQUE `(transferencia_id, numero_chassi)`.
- `hora_transferencia_auditoria` — log append-only de ações.

**TagPlus (integração NFe)**:
- `hora_tagplus_conta` — conta singleton (todas as lojas faturam pelo CNPJ matriz); secrets Fernet.
- `hora_tagplus_token` — tokens OAuth2 (1 por conta, encriptados).
- `hora_tagplus_produto_map` — de-para `HoraModelo` → produto TagPlus (UNIQUE `modelo_id`).
- `hora_tagplus_forma_pagamento_map` — de-para forma de pagamento → ID TagPlus.
- `hora_tagplus_nfe_emissao` — fila + fonte de verdade do status de emissão NFe (UNIQUE `venda_id`).
- `hora_tagplus_backfill_job` — job de backfill em RQ (fila `hora_backfill`) com progresso/relatório.
- `hora_tagplus_departamento_map` — de-para departamento TagPlus → `HoraLoja` (emitente é sempre a matriz).

**Parser DANFE (aprendizado por feedback)**:
- `hora_danfe_parser_append` — append-prompt versionado do extrator de chassi/motor; apenas 1 `ativo` (permite rollback).

**Venda — auxiliares**:
- `hora_venda_divergencia` — divergências do import de NF de saída (fluxo permissivo, não bloqueia).
- `hora_venda_auditoria` — log append-only de transições/edições de `HoraVenda`.
- `hora_venda_pagamento` — pagamento parcial 1:N; soma deve igualar `valor_total` para sair de INCOMPLETO.

---

## Autorização granular (decorator + service)

> Substitui o antigo `require_lojas` (mantido apenas para retrocompat). Use sempre `require_hora_perm` em rotas novas.

**10 módulos canônicos** (em `app/hora/models/permissao.py:MODULOS_HORA`):
`usuarios, dashboard, lojas, modelos, pedidos, nfs, recebimentos, estoque, devolucoes, pecas`.

**5 ações** (`ACOES_HORA`): `ver, criar, editar, apagar, aprovar`.
A ação `aprovar` é semântica e só tem decorator real no módulo `usuarios` (aprovação de cadastros pendentes). Para os demais, a flag é armazenada mas ignorada — o template marca a célula com `—`.

**Flags de visibilidade fina (módulos virtuais em `MODULOS_SO_VER`)**: além dos
módulos-CRUD, existem slugs que só usam a ação `ver` para gatear pedaços de UI:
- `estoque_valores` — exibe os valores R$ no detalhe do chassi (`estoque_chassi_detalhe.html`:
  Preço esperado do pedido, Valor total + Preço desta moto da NF de entrada, Preço da venda).
  Sem a flag, o vendedor vê a moto/rastreio mas não os valores.
- `estoque_exportar` — botão + rota `estoque_exportar_xlsx` (export do estoque).
- `vendas_exportar` — botão + rota `vendas_exportar_xlsx` (export dos pedidos de venda).

São independentes de `estoque/ver` e `vendas/ver` (ver a tela ≠ ver valores / exportar).
Default `False`: usuário não-admin só ganha cada uma quando o admin marca o checkbox
correspondente em `/hora/permissoes`. Sem DDL — `hora_user_permissao.modulo` é VARCHAR(40)
e as linhas são criadas sob demanda por `salvar_matriz_completa`.

**Como usar em rotas novas**:
```python
from app.hora.decorators import require_hora_perm

@hora_bp.route('/pedidos')
@require_hora_perm('pedidos', 'ver')   # admin sempre passa; usuario inativo bloqueado; resto via tabela
def pedidos_lista(): ...
```

**Tela acessivel por mais de um perfil** — use `require_hora_perm_any` (passa se
QUALQUER par for concedido). Ex.: a fila de **NFs de Saida** (`tagplus_emissoes_lista`)
e vista tanto pelo vendedor quanto pelo operador de faturamento:
```python
from app.hora.decorators import require_hora_perm_any

@hora_bp.route('/tagplus/emissoes')
@require_hora_perm_any(('vendas', 'ver'), ('tagplus', 'ver'))
def tagplus_emissoes_lista(): ...
```
A rota escopa por loja/vendedor (mesma regra de `vendas_lista` via
`criterio_pedidos_hora` + `lojas_permitidas_ids`) para o vendedor nao ver NFs de
outras lojas. O link do menu (`base.html`) deve usar o MESMO OR de permissoes que
o decorator — caso contrario o usuario ve o link mas leva "acesso negado".

**Como usar em templates**:
```jinja
{% if current_user.tem_perm_hora('lojas', 'criar') %}
  <a href="{{ url_for('hora.lojas_novo') }}">Nova loja</a>
{% endif %}
```
`Usuario.tem_perm_hora` (em `app/auth/models.py`) tem cache `_hora_perm_cache` por instância — uma única query por request resolve N chamadas no menu.

**Service** (`app/hora/services/permissao_service.py`):
- `tem_perm(user, modulo, acao)` — fonte de verdade (admin sempre True; status≠ativo False; sem entry False).
- `get_matriz(user_id)` — dict `{modulo: {acao: bool}}` com 10 módulos × 5 ações.
- `get_matrizes_batch(user_ids)` — versão N-usuarios em 1 query (usado na tela de gestão).
- `salvar_matriz_completa(user_id, matriz, atualizado_por_id)` — upsert em batch + commit.

**Tela de gestão**: `/hora/permissoes` (rota `hora.permissoes_lista`). Decorator `usuarios/ver` para abrir; `usuarios/editar` para toggle/loja/granular; `usuarios/aprovar` para o card de pendentes (aprovar/rejeitar com escolha de loja). Self-edit e edição de admin por não-admin são bloqueados.

---

## Parsers reusados (via adapter)

**Não duplicar**, **não mover**, **não reimplementar**. Os parsers de DANFE da CarVia já lidam com:
- Laiouns (DANFEs compactas sem CFOP, código com dash) — `danfe_pdf_parser.py:623,1076`.
- Q.P.A (repeat detection de código) — `danfe_pdf_parser.py:1191,1221`.
- B2B (comportamento default).
- **Bling / Mainô** (seção "Itens da nota fiscal"): itens ancorados na **linha-NCM** (não no código numérico), suportando NF com **itens mistos** — moto NCM 8711 + acessório/brinde de outro NCM (capacete 6506, brinquedo 9503), com ou sem código `NNN -` — `danfe_pdf_parser.py:_parsear_itens_bling`.
- Extração de chassi/motor/cor/modelo via LLM (Haiku primário, Sonnet fallback) — `danfe_pdf_parser.py:1418`. O gate de chassi (`_secao_tem_indicio_chassi`) aceita **chassi nacional não-VIN** (série alfanumérica, ex: `XL2025107152`), não só VIN-17 — DANFE de moto elétrica nacional não volta mais "sem veículo".
- Regex de modelos eletric motos — `moto_recognition_service.py:48`.

**Padrão de uso no HORA**:
```python
# app/hora/services/parsers/danfe_adapter.py
from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
from app.hora.models import HoraMoto, HoraNfEntrada

def processar_danfe_motochefe(pdf_bytes, loja_id, ...):
    parser = DanfePDFParser()
    resultado = parser.parse(pdf_bytes)
    # traduzir resultado para entidades hora_*
    ...
```

Se um comportamento específico da HORA for necessário (ex.: validação adicional de chassi), coloque na camada adapter, **nunca edite o parser CarVia**.

---

## O que NÃO fazer (lista explícita)

1. **Não copiar** o padrão `PedidoVendaMoto + PedidoVendaMotoItem` do Motochefe-distribuidora como template. Aquele desenho é B2B com fungibilidade por modelo; HORA é B2C com chassi declarado. Ver `docs/hora/INVARIANTES.md` seção "Anti-padrões rejeitados".
2. **Não adicionar status/loja/preço em `hora_moto`**. Viola invariante 3.
3. **Não fazer UPDATE em `hora_moto`** após insert. Viola invariante 4.
4. **Não criar FK cross-módulo** para tabelas de `app/motochefe/`, `app/carvia/`, ou qualquer outra tabela não-`hora_`.
5. **Não duplicar** os parsers de DANFE/regex de modelo. Reusar via adapter.
6. **Não criar schema PostgreSQL separado** nem bind dedicado. Decisão tomada em 2026-04-18.
7. **Não modelar Venda como atômica** (1 moto por venda hardcoded). Sempre header + item, mesmo quando quase todas as vendas são 1-moto.

---

## Ordem de implementação planejada

Segue o plano aprovado em 2026-04-18:

1. **P1**: documentos contratuais — `docs/hora/INVARIANTES.md` e este `app/hora/CLAUDE.md`. **Concluído**.
2. **P2**: migrations + modelos SQLAlchemy das 13 tabelas iniciais. **Concluído** (+ `hora_user_permissao` em 2026-04-22; o módulo cresceu para 46 tabelas nas fases seguintes).
3. **P3**: fluxo pedido → NF → recebimento → conferência (ingestão e confronto). **Concluído**.
4. **P4**: fluxo venda com tabela de preço + desconto auditável. **Parcial — fluxo (a) concluído 2026-04-24**.
   - **Fluxo (a) — import NF saída (DANFE PDF)**: operador sobe PDF emitido pelo ERP externo em `/hora/vendas/upload`; service `venda_service.importar_nf_saida_pdf` parseia via `danfe_adapter` (reuso CarVia + extensão CPF/nome destinatário), cria `HoraVenda` + `HoraVendaItem` + emite evento `VENDIDA` nos chassis, persiste PDF em `hora/vendas/` S3, preenche `cnpj_emitente`, `parser_usado`, `parseada_em`.
   - **Fluxo permissivo**: problemas geram `HoraVendaDivergencia` (5 tipos: `CHASSI_NAO_CADASTRADO`, `CHASSI_INDISPONIVEL`, `LOJA_DIVERGENTE`, `CNPJ_DESCONHECIDO`, `TABELA_PRECO_AUSENTE`) sem bloquear o import.
   - **Campos pós-import editáveis** na tela de detalhe: `vendedor` (NULL inicialmente, preenchido manualmente), `forma_pagamento` (default `'NAO_INFORMADO'`, operador troca para PIX/CARTAO_CREDITO/DINHEIRO/MISTO), telefone, email, observações.
   - **Cancelamento**: `cancelar_venda` muda status=CANCELADA e emite evento `DEVOLVIDA` nos chassis (simetria com devolução).
   - **Wiring no estoque**: `listar_estoque` enriquece com `venda_id`, `nf_saida_numero`, `venda_status`; template mostra link clicável para a venda na coluna NF (ambas entrada e saída) e em `estoque_chassi_detalhe.html` seção Venda.
   - **Migration**: `scripts/migrations/hora_17_nf_saida.{py,sql}` — ALTER `hora_venda` (4 colunas novas + loja_id nullable + forma_pagamento default) + CREATE `hora_venda_divergencia`.
   - **Permissão**: módulo `vendas` adicionado a `MODULOS_HORA` (`app/hora/models/permissao.py:35`).
   - **Fluxo (c) — TagPlus**: ainda pendente (será em sessão futura quando houver integração de faturamento pelo sistema).
5. **P5** (2026-04-22): autorização granular por usuário × módulo × ação. **Concluído** — todas as 64 rotas usam `require_hora_perm`.
6. **P6** (2026-04-22): **Transferência entre filiais + Registro de avaria em estoque**. **Concluído**.
   - 5 tabelas novas: `hora_transferencia`, `hora_transferencia_item`, `hora_transferencia_auditoria`, `hora_avaria`, `hora_avaria_foto` (migration `hora_15`).
   - 2 tipos de evento novos em `hora_moto_evento.tipo`: `EM_TRANSITO`, `CANCELADA`.
   - Fluxo transferência: Loja A emite → `EM_TRANSITO` (loja_id=destino). Loja B confirma → `TRANSFERIDA`. A pode cancelar enquanto em trânsito → `CANCELADA` (loja_id=origem). Itens já confirmados no destino permanecem.
   - Avaria: **não bloqueia venda**. Registra + emite evento `AVARIADA`. Foto obrigatória + descrição ≥ 3 chars + múltiplas avarias por chassi permitidas. Listagem de estoque mostra badge "⚠ N" quando há avarias abertas.
   - `EVENTOS_EM_ESTOQUE` agora inclui `CANCELADA`. `EM_TRANSITO` fica em limbo (helper `listar_em_transito` em `estoque_service`).
   - Services: `transferencia_service`, `transferencia_audit`, `avaria_service` + helper `loja_origem_permitida_para_transferencia` em `auth_helper`.
   - 36 testes em `tests/hora/` cobrindo regras de negócio.
   - Spec: `docs/superpowers/specs/2026-04-22-hora-transferencia-e-avaria-design.md`.
   - Plano: `docs/superpowers/plans/2026-04-22-hora-transferencia-e-avaria.md`.
7. **Invariante de Faturamento (REGRA FISCAL)** (2026-04-27):

   **Toda NFe da Lojas HORA sai com o CNPJ da MATRIZ.** Mesmo que a venda física
   ocorra em filial, o emitente fiscal é sempre a matriz HORA cadastrada na conta
   TagPlus (singleton `HoraTagPlusConta`).

   - **Implementação**: `PayloadBuilder.build()` **não inclui** o campo `emitente`
     no JSON do POST /nfes. TagPlus aplica automaticamente o emitente padrão da
     conta OAuth — que é a matriz.
   - **Multi-emitente NÃO é suportado por design.** Não adicionar campo
     `tagplus_emitente_id` em `HoraLoja`, não criar lookup, não passar `emitente:`
     ou `endereco_emitente:` no payload.
   - A loja física é apenas **rastreada gerencialmente** em `inf_contribuinte`
     ("Loja: <nome>") — sem efeito fiscal.
   - Mudança nesta regra exige aprovação explícita do dono fiscal HORA.

8. **Emissão NFe via TagPlus** (2026-04-26). **Concluído** — fluxo (c) do desenho:
   - 5 tabelas em `app/hora/models/tagplus.py` (migration `hora_18_tagplus.{py,sql}`):
     `hora_tagplus_conta` (singleton), `hora_tagplus_token`, `hora_tagplus_produto_map`,
     `hora_tagplus_forma_pagamento_map`, `hora_tagplus_nfe_emissao`.
   - Services em `app/hora/services/tagplus/`: `crypto` (Fernet), `oauth_client` (DB-persistente
     com lock pessimista), `api_client` (HTTP wrapper, refresh em 401), `payload_builder`
     (HoraVenda → JSON TagPlus), `emissor_nfe` (enfileirar + processar com retry),
     `webhook_handler` (nfe_aprovada/rejeitada/cancelada + race retry +10s),
     `cancelador_nfe` (PATCH /nfes/cancelar com justificativa ≥15), `cce_service`
     (POST /nfes/gerar_cce).
   - Workers em `app/hora/workers/`: `emissao_nfe_worker` (RQ jobs `processar_emissao` e
     `processar_webhook`), `reconciliacao_worker` (job 30min para webhooks perdidos).
     Worker dedicado: `worker_hora_nfe.py` na raiz, queue `hora_nfe`.
   - 18 rotas em `app/hora/routes/tagplus_routes.py`: configuração (conta + OAuth +
     callback + refresh + checklist), mapeamentos (produtos, formas de pagamento),
     webhook público, fila de emissões e operações por venda
     (`/vendas/<id>/nfe/{emitir,cancelar,cce,danfe.pdf,xml}`).
   - Templates em `app/templates/hora/tagplus/`: `conta_form`, `oauth_result`, `checklist`,
     `produto_map`, `forma_pag_map`, `emissoes_lista`, `nfe_status`.
   - Permissão: módulo `tagplus` adicionado em `MODULOS_HORA`.
   - 2 novos tipos de evento `HoraMotoEvento.tipo`: `NF_EMITIDA`, `NF_CANCELADA`.
   - Env var: `HORA_TAGPLUS_ENC_KEY` (Fernet), `REDIS_URL` (RQ).
   - Spec: `app/hora/EMISSAO_NFE_ENGENHARIA.md`.
   - Pendências v2 (não bloqueantes): NFC-e, contingência, séries por loja,
     endereço de retirada por loja, MISTO como forma de pagamento.

9. **Workflow de Pedido de Venda** (2026-04-28). **Concluído** — máquina de estado completa com auditoria estruturada:

   **Status (`HoraVenda.status`)**: `COTACAO` → `CONFIRMADO` → `FATURADO` → `CANCELADO`.
   Constantes em `app/hora/models/venda.py`: `VENDA_STATUS_*` + `VENDA_STATUS_VALIDOS` + `VENDA_STATUS_RESERVA_CHASSI`.

   **Transições**:
   - **(novo) → COTACAO**: `criar_venda_manual` (pedido manual via TagPlus) — emite evento `RESERVADA` com lock `SELECT FOR UPDATE` no `hora_moto`.
   - **COTACAO → CONFIRMADO**: `confirmar_venda` (rota `POST /vendas/<id>/confirmar`, perm `vendas/editar` desde 2026-05-13 — antes era `vendas/aprovar`; mudou para vendedor padrao poder confirmar).
   - **CONFIRMADO → COTACAO** (reabrir): `voltar_para_cotacao` (rota `POST /vendas/<id>/voltar-cotacao`, perm `vendas/aprovar` desde 2026-05-13 — antes era `vendas/editar`; agora exclusivo de gerente).
   - **CONFIRMADO → FATURADO**: webhook `nfe_aprovada` do TagPlus (em `webhook_handler._handle_aprovada`).
   - **FATURADO → CONFIRMADO**: webhook `nfe_cancelada` (NFe cancelada SEFAZ; pedido volta a confirmado, decisão de re-emitir ou cancelar fica com operador).
   - **\* → CANCELADO**: `cancelar_venda` — bloqueia se NFe em-voo; FATURADO exige NFe já cancelada SEFAZ. Emite `DEVOLVIDA` em todos os chassis.
   - **DANFE legado → FATURADO direto**: `importar_nf_saida_pdf` (NF emitida em ERP externo, sem passar por COTACAO/CONFIRMADO).

   **Estoque** (`EVENTOS_FORA_ESTOQUE` em `estoque_service`):
   - `RESERVADA`, `VENDIDA`, `NF_EMITIDA`, `NF_CANCELADA`, `DEVOLVIDA` — saem do estoque disponível.
   - Pedido em qualquer status ativo (COTACAO/CONFIRMADO/FATURADO) reserva o chassi; CANCELADO devolve via `DEVOLVIDA`.

   **Lock pessimista** (`venda_service._lock_chassi_e_validar_disponivel`):
   - `SELECT FOR UPDATE` no `hora_moto` em `criar_venda_manual`, `adicionar_item_pedido` e `editar_item_pedido` (troca de chassi).
   - Impede 2 operadores reservarem o mesmo chassi simultaneamente.
   - `hora_venda_item` NÃO tem mais UNIQUE em `numero_chassi` — pedido cancelado libera chassi para nova venda.

   **Edição** (matriz por status em `_CAMPOS_EDITAVEIS_HEADER`):
   - `COTACAO`: tudo (cliente, endereço, operacional, observações, itens).
   - `CONFIRMADO`: contato, endereço, operacional, observações (sem mexer em CPF/nome — payload TagPlus).
   - `FATURADO`: só observações.
   - `CANCELADO`: nada (raise `TransicaoInvalidaError`).
   - Defesa adicional: NFe em estado em-voo (`EM_ENVIO`/`ENVIADA_SEFAZ`/`CANCELAMENTO_SOLICITADO`) bloqueia tudo exceto observações.

   **Edição de itens** (só em COTACAO):
   - `adicionar_item_pedido` (novo chassi → evento `RESERVADA`).
   - `remover_item_pedido` (chassi antigo → evento `DEVOLVIDA`; impede remover último item).
   - `editar_item_pedido` (troca de chassi e/ou novo valor; troca emite `DEVOLVIDA`+`RESERVADA`).

   **Janela de cancelamento NFe**: 24h em `cancelador_nfe._validar_janela` (defesa em profundidade — TagPlus também valida na SEFAZ). Constante `JANELA_CANCELAMENTO_HORAS=24`. Tela `nfe_status.html` mostra countdown e desabilita botão após janela.

   **Auditoria**: nova tabela `hora_venda_auditoria` (espelho de `hora_transferencia_auditoria`). Service `app/hora/services/venda_audit.py` com 14 ações:
   `CRIOU`, `EDITOU_HEADER`, `EDITOU_ITEM`, `ADICIONOU_ITEM`, `REMOVEU_ITEM`, `CONFIRMOU`, `EMITIU_NFE`, `FATURADO`, `CANCELOU_NFE`, `NFE_CANCELADA_SEFAZ`, `EMITIU_CCE`, `CANCELOU`, `RESOLVEU_DIVERGENCIA`, `DEFINIU_LOJA`.
   FK `item_id` com `ON DELETE SET NULL` (preserva auditoria de itens deletados).

   **Migration**: `scripts/migrations/hora_20_pedido_workflow.{py,sql}` — converte legados (`CONCLUIDA`+chave→`FATURADO`, `CONCLUIDA` sem chave→`CONFIRMADO`, `DEVOLVIDA`→`CANCELADO`) + DROP UNIQUE chassi + CREATE auditoria.

   **UI**:
   - Menu: "Vendas (NF saída)" → "Pedidos de Venda".
   - `venda_detalhe.html` reescrito: timeline de status, botões de transição (Confirmar / Emitir NFe / Cancelar pedido), edição de header com matriz por status, edição/adição/remoção de itens em COTACAO, histórico de auditoria.
   - `vendas_lista.html`: badges coloridos por status (4 cores).
   - `nfe_status.html`: countdown 24h e bloqueio do botão de cancelamento após janela.
   - `estoque_lista.html` + `estoque_chassi_detalhe.html`: badge "Reservado em Pedido #X (status)".

   **Permissões `vendas/editar` vs `vendas/aprovar`** (atualizado 2026-05-13):
   - `vendas/editar`: vendedor padrao — cria pedido, edita itens em COTACAO, confirma (`vendas_confirmar`).
   - `vendas/aprovar`: gerente — reabre pedido CONFIRMADO via `vendas_voltar_cotacao` (vendedor comum nao pode).
   - Whitelist `MODULOS_COM_APROVAR` em `app/hora/models/permissao.py` controla quais modulos exibem o checkbox "Aprovar" no gerenciador `/hora/permissoes`. Atualmente: `{'usuarios', 'modelos', 'vendas'}`. Adicionar slug ao adicionar `require_hora_perm(<X>, 'aprovar')` em rota nova.

   **Testes**: `tests/hora/test_pedido_workflow.py` — 15 testes cobrindo criação, confirmação, cancelamento, edição (matriz por status), adicionar/remover/editar itens, lock pessimista (chassi indisponível bloqueia 2ª reserva), auditoria.

10. **Fase 2 futura**: financeiro (títulos a pagar/receber, conciliação, comissões). Todas as tabelas novas com `chassi` FK conforme invariante 2.

---

## 11. Peças (cadastro, estoque, faturamento) — 2026-05-05

Peças (capacete, retrovisor, bateria, acessórios) são produtos **fungíveis sem chassi**, paralelos a motos no ciclo HORA.

**Tabelas novas (5)** — migrations `hora_26..28`:
- `hora_peca` — cadastro (codigo_interno, descricao, ncm, cfop_default, unidade, preco_venda_padrao, foto, ativo)
- `hora_tagplus_peca_map` — mapeamento opcional p/ emissão TagPlus (peça pode existir sem TagPlus)
- `hora_peca_movimento` — log de entradas/saídas signed; saldo derivado por SUM (mesmo padrão moto-evento)
- `hora_nf_entrada_item_peca` — peça em NF entrada com **conferência embutida 1:1** (qtd_conferida, divergencia, foto)
- `hora_venda_item_peca` — peça em pedido de venda

**ALTER `hora_pedido_item`**: adicionado `peca_id`, `qtd_pedida` com **CHECK XOR** (item é OU moto OU peça).

**Permissões**: `pecas_cadastro` e `pecas_estoque` em `MODULOS_HORA` (separados de `pecas` que continua significando "peças faltando em motos").

**Ciclo de vida**:
1. **Pedido compra** (`HoraPedido`) — itens podem ser moto OU peça (`peca_id` + `qtd_pedida`). UI: seção "Peças do pedido" em `pedido_detalhe.html`.
2. **NF entrada** — operador adiciona peças manualmente em `nf_detalhe.html`. Confronto 1:1 (`qtd_nf` vs `qtd_conferida`) com modal por linha. Conferir emite movimento `ENTRADA_NF` no estoque da loja destino.
3. **Estoque de peças** — saldo materializado **NÃO existe**. Saldo = `SELECT SUM(qtd) FROM hora_peca_movimento WHERE peca_id, loja_id`. Tipos de movimento: `ENTRADA_NF`, `SAIDA_VENDA`, `TRANSFERENCIA_OUT/IN`, `AJUSTE_POS/NEG`, `DEVOLUCAO_VENDA`, `DEVOLUCAO_FORNECEDOR`. Saldo só é positivo (transferência valida).
4. **Pedido venda** (`HoraVenda`) — `criar_venda_manual` continua aceitando moto. `adicionar_item_peca(venda_id, peca_id, qtd, valor_unitario_final)` em COTACAO emite `SAIDA_VENDA`. Cancelar venda emite `DEVOLUCAO_VENDA` para todas as peças.
5. **NFe TagPlus** — payload misto: `_montar_itens()` concatena `venda.itens` (motos: qtd=1, detalhes=Chassi/Motor) + `venda.itens_peca` (peças: qtd N, sem detalhes chassi). CFOP por item (peca_map.cfop_default override peca.cfop_default).
6. **Backfill TagPlus** (em `tagplus/backfill_service.py`):
   - `executar_backfill_produtos_pecas()` — itera `GET /produtos`, popula `hora_peca` + `hora_tagplus_peca_map`. Heurística NCM 8711* = moto (pula).
   - `executar_backfill_pecas_faltantes(limite)` — busca `HoraVenda` FATURADO com `valor_total - sum(itens) > 0`, repuxa NFe e classifica peças cujo código bate em `hora_tagplus_peca_map`.

**Proteção de chassi (CRÍTICA — fonte: usuário 2026-05-05)**:

Helper `chassi_protecao_service.chassi_protegido(numero_chassi)` retorna True se chassi tem registro em `HoraPedidoItem` OU `HoraNfEntradaItem`. Esses registros são fonte de verdade.

Aplicação em `tagplus/backfill_service._atualizar_moto_complementar()`:
- Se chassi protegido + parser sugeriu cor/motor diferente: **NÃO atualiza**, apenas registra warning.
- Preserva identidade da moto vinda de pedido/NF de compra.

Não-objetivos v1: versionamento de preço de peça (preço fixo em `hora_peca.preco_venda_padrao`), custo médio, devolução parcial, inventário cíclico, multi-emitente.

**UI / Menu**:
- Cadastros → Peças (`/hora/pecas/cadastro`)
- Movimentação → Estoque de Peças (`/hora/pecas/estoque`) com modais ajuste manual e transferência
- Faturamento → Mapeamento de peças, Backfill catálogo de peças, Backfill peças faltantes (delta)

**Spec/Plano**:
- `docs/superpowers/specs/2026-05-05-hora-pecas-design.md`
- `docs/superpowers/plans/2026-05-05-hora-pecas.md`

---

## 13. Listagem de Pedidos de Venda com itens inline + filtro chassi — 2026-05-06

A listagem `/hora/vendas` agora exibe os chassis e modelos dos itens
diretamente em cada linha (sem precisar abrir o detalhe), com filtro por
chassi.

**Service** (`app/hora/services/venda_service.py`):
- `_query_vendas` aceita parametro `chassi` (substring case-insensitive).
  Aplicado via `EXISTS(SELECT 1 FROM hora_venda_item ...)` para nao duplicar
  linhas quando o chassi casa multiplos itens.
- Eager loading: `selectinload(HoraVenda.itens).selectinload(HoraVendaItem.moto).selectinload(HoraMoto.modelo)`
  evita N+1 na renderizacao.
- `paginar_vendas(... chassi=...)` repassa para `_query_vendas`.

**Rota** (`app/hora/routes/vendas.py:vendas_lista`):
- Le `request.args.get('chassi')` (uppercased + trimmed).
- Repassa para o service e ao template como `filtro_chassi`.

**Template** (`app/templates/hora/vendas_lista.html`):
- Coluna nova "Itens (chassi · modelo · cor)" com `<ul>` de cada item.
- Chassi que casa o filtro recebe highlight `bg-warning-subtle`.
- Coluna nova "Pedido TP" mostra `tagplus_pedido_id` quando preenchido.
- Filtro novo `<input name="chassi">` no formulario de busca.

---

## 14. Backfill `tagplus_pedido_id` para vendas legadas — 2026-05-06

Cobre vendas FATURADO sem pedido TagPlus vinculado — incluindo legacy
DANFE PDF (origem='DANFE') e vendas MANUAL sem entrada em
`HoraTagPlusNfeEmissao`.

**Service** (`app/hora/services/tagplus/pedido_backfill_service.py`):
- `_aplicar_pedido_em_venda(api, venda, pedido_id_tp, operador, emissao=None)` —
  extracao reusavel da logica de aplicar GET /pedidos/{id} em uma venda
  (compartilhada entre os 2 universos).
- `_buscar_tagplus_nfe_id_para_venda(api, venda)` — descobre o id da NFe
  no TagPlus paginando `GET /nfes` em janela `[data_venda - 7d, data_venda + 7d]`
  com header `X-Data-Filter: data_emissao`. Match por `chave_acesso`
  (preferencial), fallback `numero`. Constante `JANELA_BUSCA_NFE_DIAS = 7`.
- `_enriquecer_venda_legada(api, venda, operador)` — orquestra
  busca NFe → GET /nfes/{id} → extrai `pedido_os_vinculada.id` → aplica.
- `executar_backfill_pedidos_vendas_legadas(operador, limite, progress_callback)`
  itera `HoraVenda FATURADO + tagplus_pedido_id IS NULL + nf_saida_chave_44 NOT NULL`.
- `enfileirar_backfill_pedidos_vendas_legadas_job` — RQ enqueue, queue `hora_backfill`.

**Worker** (`app/hora/workers/pedido_backfill_worker.py`):
- `processar_backfill_pedidos_vendas_legadas_job(job_id)` — espelho do
  `processar_backfill_pedidos_job` mas chama `executar_backfill_pedidos_vendas_legadas`
  e usa `_gravar_progresso_legado` (que mapeia `sem_nfe` para
  `n_pulada_invalida`).

**Modelo** (`app/hora/models/tagplus.py`):
- Constante nova: `BACKFILL_JOB_TIPO_PEDIDO_VENDAS_LEGADAS = 'PEDIDO_VENDAS_LEGADAS'`.
- Adicionada em `BACKFILL_JOB_TIPOS_VALIDOS`. **Sem migration necessaria** —
  campo `tipo` em `hora_tagplus_backfill_job` e VARCHAR(30) sem CHECK constraint.

**Rota** (`app/hora/routes/tagplus_routes.py`):
- `POST/GET /hora/tagplus/backfill-pedidos-legados` — perm `tagplus/editar`.
  Mostra universo + jobs anteriores; POST enfileira o job RQ.

**Template** (`app/templates/hora/tagplus/backfill_pedidos_legados.html`)
e link no menu Faturamento (`base.html`).

**Idempotencia**: 2x executa sem problemas. Vendas com `tagplus_pedido_id`
ja preenchido caem fora do universo (`WHERE tagplus_pedido_id IS NULL`).

**Pre-requisito**: scope OAuth deve incluir `read:pedidos`. Sem scope, o
service levanta `ScopeInsuficienteError` na primeira venda e aborta o
job inteiro.

---

## 12. Unificação de modelos (N nomes → 1 canônico) — 2026-05-06

Resolve duplicação histórica: TagPlus, NFs e pedidos podem se referir ao mesmo modelo físico com descrições divergentes (ex: `BOB`, `BOB AM`, `SCOOTER ELETRICA BOB` todas são `MT-BOB / tagplus_id=10`). Antes da migration `hora_29`, o sistema criava `HoraModelo` distintos via `buscar_ou_criar_modelo`. Resultado em produção: 8 grupos de duplicação, 20 modelos absorvíveis em 8 canônicos.

**3 tabelas envolvidas (migration `hora_29`)**:
- `hora_modelo_alias` — N nomes → 1 modelo canônico. Tipos: `TAGPLUS_PRODUTO_ID`, `TAGPLUS_CODIGO`, `NOME_NF`, `NOME_PEDIDO`, `NOME_LIVRE`. UNIQUE `(tipo, nome_alias)`.
- `hora_modelo_pendente` — fila de nomes desconhecidos aguardando decisão. UNIQUE `(nome_observado, origem)`.
- `hora_modelo` ALTER — `merged_em_id` (self FK), `merged_em`, `merged_por` para auditoria de merge físico.

**Fluxo de ingestão** (TagPlus, NF DANFE, pedido manual, recebimento):
1. Chama `modelo_resolver_service.resolver_ou_pendenciar(nome, origem=...)`.
2. Resolver consulta `hora_modelo_alias` (case-insensitive) e fallback `hora_modelo.nome_modelo`.
3. Se acha → retorna `(modelo, None)`. Se não → cria/incrementa pendência e retorna `(None, pendente)`.
4. `get_or_create_moto` levanta `ModeloPendenteError` (com `pendencia` no atributo) quando modelo não resolve. Caller decide:
   - **TagPlus backfill / DANFE saída**: captura, registra divergência `MODELO_PENDENTE`, **skipa o item**, segue.
   - **NF entrada DANFE**: aborta o import inteiro **antes** de gravar a NF. Pendências persistem (commit isolado em `resolver_ou_pendenciar(commit=True)`).
   - **Import de pedido (XLSX/imagem, `criar_pedido`)**: NÃO propaga — usa `get_or_create_moto(fallback_sentinela=True)`, cria a moto no sentinela DESCONHECIDO + grava `modelo_texto_original` no item, e segue (o pedido nasce completo). A retroatividade corrige depois. Mudou em 2026-06-19: antes propagava `ModeloPendenteError` e, sem rollback por-pedido na rota de confirmação, o header flushado vazava no commit do pedido seguinte do batch → pedido com 0 itens (incidente 119/124/125/126).
   - **Adição manual de item (`adicionar_item_pedido`, 1 item interativo)**: propaga, rota retorna 4xx com link para resolver (feedback imediato — não usa sentinela).

**Resolução em UI**: `/hora/modelos/pendencias`.
- **Vincular**: cria `HoraModeloAlias` apontando o nome para um modelo existente.
- **Criar novo**: cria `HoraModelo` + alias do nome observado.
- **Ignorar**: marca como ignorada (não gera modelo nem alias).

**Retroatividade automática** (`modelo_retroatividade_service.propagar_resolucao`): ao resolver pendência:
- Cria `HoraMoto` para chassis em `hora_nf_entrada_item` cujo `modelo_texto_original` bate no nome observado.
- Marca divergências `MODELO_PENDENTE` como resolvidas para esses chassis.
- Corrige `hora_pedido_item` cujo `modelo_texto_original` bate o nome observado (migration `hora_51`): seta `modelo_id`=canônico nos itens pendentes (sentinela DESCONHECIDO ou NULL) e UPDATE-eia a `HoraMoto` sentinela vinda só de pedido (única exceção ao invariante 3, igual ao caminho NF). Antes (até 2026-06-19) isto não era feito e o operador editava o item manualmente. Idempotente.

**Merge físico** (`/hora/modelos/unificar`, perm `modelos/aprovar`):
- Operador escolhe canônico + N aliases.
- Service `modelo_merge_service.merge_modelos` em UMA transação:
  - `UPDATE` em todas as 6 FKs apontando para alias → canônico (`hora_moto`, `hora_pedido_item`, `hora_recebimento_conferencia`, `hora_emprestimo_moto`, `hora_modelo_alias`, `hora_modelo_pendente.resolvido_modelo_id`).
  - `hora_tabela_preco`: descarta do alias (preserva só do canônico).
  - `hora_tagplus_produto_map` (UNIQUE em `modelo_id`): se canônico já tem map, transfere `tagplus_codigo`+`tagplus_produto_id` como `HoraModeloAlias` e deleta map duplicado; se não tem, faz `UPDATE`.
  - Cria alias `NOME_LIVRE` para o nome do alias (preserva nome histórico).
  - Marca alias `ativo=False, merged_em_id=canonico, merged_em=now, merged_por=operador`.
- Tela `unificar.html` tem **preview AJAX** (dry-run via `preview_merge`) antes de executar.

**Pontos importantes**:
- `HoraMoto.modelo_id` permanece `NOT NULL` (invariante 3) — moto só é criada após pendência resolvida.
- Listagens (`cadastro_service.listar_modelos`, `autocomplete_service.modelos`) filtram `merged_em_id IS NULL` por padrão.
- Autocomplete agora busca também em aliases (operador digita "BOB AM" e acha modelo BOB).
- Modelo sentinela `DESCONHECIDO` (id criado em `hora_30`) absorve nomes técnicos `CHASSI_EXTRA_DESCONHECIDO`, `MODELO_DESCONHECIDO`, `NAO_INFORMADO` para evitar pendências em loop no recebimento.

**Migrations relacionadas**:
- `hora_29_modelo_alias.{py,sql}` — DDL das 2 tabelas + ALTER `hora_modelo`.
- `hora_30_seed_aliases_atuais.py` — popula aliases iniciais (`NOME_LIVRE` para cada modelo, sentinela DESCONHECIDO).
- `hora_32_sugestoes_merge.py` — relatório read-only dos grupos duplicados (guia para `/hora/modelos/unificar`).

**Permissões**: módulo `modelos` × ações `ver` (listar), `editar` (vincular pendência, gerir aliases), `criar` (criar modelo de pendência), `aprovar` (executar merge — operação de alta consequência).

**Constantes em `app/hora/models/modelo_alias.py`**: `ALIAS_TIPO_*`, `PENDENTE_ORIGEM_*`, `PENDENTE_STATUS_*`.

**Spec/Plano**: implementado em sessão única 2026-05-06. Sem spec separado (escopo coeso).

---

## 15. Preço A vista / A prazo + desconto % por moto — 2026-05-06

Cadastro de modelo passou a guardar 2 preços (`preco_a_vista`, `preco_a_prazo`)
diretos em `hora_modelo`. Forma de pagamento (`hora_tagplus_forma_pagamento_map`)
ganhou `tipo_pagamento` ('A_VISTA' | 'A_PRAZO' | NULL). Item de venda
(`hora_venda_item`) ganhou `desconto_percentual` (Numeric(5,2)).

**Fluxo no Pedido de Venda manual (`/hora/tagplus/pedido-venda/novo`)**:
- Operador escolhe modelo + forma de pagamento → JS chama
  `GET /hora/tagplus/pedido-venda/api/preco-modelo?modelo_id=&forma_pagamento=`
  → backend resolve via `venda_service.buscar_preco_para_pedido` (prioriza
  preço do modelo conforme `tipo_pagamento`; fallback A_VISTA; ultimo recurso
  `HoraTabelaPreco` legada).
- 2 campos novos sincronizam: `desconto_percentual` ↔ `desconto (R$)` ↔ `valor final`.
  Fonte de verdade no submit é `valor` (preço final). Backend em
  `_resolver_preco_tabela` recalcula `desconto_aplicado` e `desconto_percentual`
  a partir de `preco_tabela_referencia - valor_final`.

**Mudancas de assinatura**:
- `_resolver_preco_tabela(modelo_id, na_data, valor_final, forma_pagamento_hora=None)`
  → retorna agora 5-tupla: `(preco_ref, desconto_rs, desconto_pct, tabela_id, divergencia)`.
  **Regressao 2026-06-03**: o backfill TagPlus (`tagplus/backfill_service._criar_itens_da_api`)
  ficou esquecido desempacotando 4 valores → `ValueError: too many values to unpack (expected 4)`
  no backfill de NFs. Fix: desempacota 5 + grava `desconto_percentual=desconto_pct` no
  `HoraVendaItem` (invariante `venda.py:258`). Guard de aridade:
  `tests/hora/test_resolver_preco_tabela_arity.py` (AST, sem DB). Ao mudar a aridade
  desta funcao, atualize TODOS os call sites de uma vez.
- `cadastro_service.criar_modelo` / `atualizar_modelo` aceitam `preco_a_vista` e
  `preco_a_prazo` (str/Decimal/None — `_normalizar_preco` aceita formato BR).

**API publica** (consumida pelo JS, mas reutilizavel):
- `venda_service.buscar_preco_para_pedido(modelo_id, forma_pagamento_hora)` → dict
  `{preco, fonte, tipo_pagamento, preco_a_vista, preco_a_prazo}`.

**HoraTabelaPreco mantida** como fallback legado (vigência continua valendo
para vendas legacy DANFE). Se modelo tem `preco_a_vista`/`preco_a_prazo`
preenchido, esses valores ganham prioridade — `HoraTabelaPreco` so e usada
quando os dois sao NULL.

**Permissão `tagplus/editar`** (mantida): cadastrar/editar `tipo_pagamento` em
formas; cadastros nao-tagplus (preco no modelo) usam permissão `modelos/criar`
/ `modelos/editar`.

**Migration**: `scripts/migrations/hora_33_preco_avp_desconto.{py,sql}` —
ALTER 3 tabelas. Idempotente.

---

## 16. Campo `consumidor_final` no faturamento TagPlus — 2026-05-07 (revisado)

**Decisão final do dono fiscal HORA (2026-05-07)**: 100% das NFe da Lojas
HORA saem com `consumidor_final=True`, independentemente de PF/PJ no
destinatário. Campo removido da UI; payload_builder hardcoded.

**Histórico**: Inicialmente (mesmo dia, mais cedo) o operador podia
escolher Sim/Não no pedido. Após validação fiscal, decidiu-se que toda
venda da HORA é tratada como consumidor final, sem exceção.

**Estado atual**:
- `payload_builder.py` — `'consumidor_final': True` hardcoded.
- `pedido_venda_novo.html` — sem switch (apenas detector CPF/CNPJ no
  info text, que continua útil para validação visual do documento).
- `venda_detalhe.html` — sem switch.
- `tagplus_routes.tagplus_pedido_venda_criar` — não lê mais `consumidor_final`
  do form; não passa para `criar_venda_manual`.
- `vendas.vendas_editar` — não lê mais `consumidor_final_flag`/`consumidor_final`
  do form; não passa para `editar_venda`.
- Coluna `hora_venda.consumidor_final` (migration `hora_36`) **continua
  existindo no banco como vestigial** — não foi feita migration de drop
  para preservar histórico de vendas que já foram emitidas com escolha
  explícita do operador. Service aceita o kwarg mas o valor é ignorado
  pelo payload TagPlus.

**Limite CPF/CNPJ**: 18 caracteres no form/route (acomoda máscara
"00.000.000/0000-00"); banco continua String(14), service normaliza para
dígitos.

**Não confundir com a invariante fiscal do item 7** (NFe sai sempre pela
MATRIZ HORA): independentes. consumidor_final=True informa à SEFAZ que o
destinatário é PF/B2C; emitente continua sendo a matriz HORA via OAuth
TagPlus.

**Para reverter** (se um dia o requisito fiscal mudar):
1. Tirar hardcode no `payload_builder.py:157`.
2. Reativar leitura do campo nas rotas (commit `c667c28d` tem o histórico).
3. Reativar switch nos templates.
4. Coluna no banco já existe — não precisa de migration.

---

## 18. Unificação da tela de Pedido de Venda + filtro loja/vendedor + fix desconto — 2026-06-03

Três mudanças no Pedido de Venda (`HoraVenda`). Spec: `docs/superpowers/specs/2026-06-03-hora-unificar-pedido-venda-design.md`. Plano: `docs/superpowers/plans/2026-06-03-hora-unificar-pedido-venda.md`.

**Tela única (criação + edição)** — `venda_detalhe.html` foi **REMOVIDO**. A tela `pedido_venda_novo.html` opera em 2 modos no mesmo template:
- **Criação** (`tagplus_pedido_venda_novo`, sem `venda`): `{% else %}` — form único → `tagplus_pedido_venda_criar` (inalterado). Guarda pré-existente: sem modelos OU sem `formas_pagamento` mapeadas, o form é escondido e mostra alerta de configuração.
- **Edição/Ver** (`vendas_detalhe`, com `venda`): `{% if venda %}` — timeline + todas as ações de workflow + edição por seção (respeitando `_CAMPOS_EDITAVEIS_HEADER`) + "adicionar moto" via componente de cascata. **Reusa as rotas granulares existentes** (`vendas_editar`, `vendas_pagamentos_editar`, `vendas_item_adicionar`, etc.) — zero lógica de salvar nova.
- Componente extraído: `app/templates/hora/tagplus/_componente_moto_desconto.html` (markup modelo→cor→chassi + desconto, ids `f-modelo`/`f-cor`/`f-chassi`/`f-preco-tabela`/`f-desconto-pct`/`f-desconto-rs`/`f-valor`) + `_pedido_venda_scripts.html` (todo o JS, **defensivo** — cada grupo só inicializa se seus elementos existem). Reusados nos 2 modos.
- `vendas_detalhe` e `tagplus_pedido_venda_novo` compartilham `_contexto_lookup_pedido_venda()` (em `routes/vendas.py`) para as listas de lookup (`modelos`, `formas_pagamento`, `vendedores_disponiveis`, `lojas_disponiveis`, `lojas_ativas`) — DRY.
- Adicionar moto na edição: form `#form-add-moto-edicao` posta `numero_chassi`/`valor_final` (hidden inputs sincronizados por JS no submit a partir de `f-chassi`/`f-valor` do componente — a rota `vendas_item_adicionar` deriva o desconto do `valor_final` via `_resolver_preco_tabela`). Editar item existente mantém o form simples. Cascata só no "adicionar moto" (1 instância → sem colisão de ids).
- Tour `vendas_aprovar.js`: ids `#timeline-status`, `#btn-confirmar`, `#btn-emitir-nfe`, `#secao-historico`, `#btn-cancelar-pedido` preservados na tela unificada (tour intacto).

**Fix do desconto (drift de centavos)** — `atualizarPrecoTabela()` (em `_pedido_venda_scripts.html`) passou a ancorar o recálculo no **VALOR FINAL** (`recalcular('valor')`) em vez do `%` arredondado — elimina o drift (500,00 → 500,05) ao trocar forma de pagamento. 1ª carga (valor vazio/0) usa `'pct'` (preço cheio, desconto 0).

**Filtro loja/vendedor** (por usuário, configurado em `/hora/permissoes`):
- Nova coluna `usuarios.criterio_pedidos_hora` VARCHAR(10) DEFAULT `'loja'` (valores `'loja'` | `'vendedor'`).
- Nova coluna `hora_venda.criado_por_id` INTEGER (sem FK; gravado por `criar_venda_manual`; backfill best-effort via `hora_venda_auditoria` acao=`CRIOU`).
- `vendas_lista` lê o critério: `'loja'` = escopo por `loja_hora_id` (padrão atual); `'vendedor'` = `OR(HoraVenda.vendedor IN [nome, vendedor_vinculado], criado_por_id == user.id)` **ignorando** loja. Aplicado em `venda_service._query_vendas(filtro_vendedor=...)` / `paginar_vendas`.
- Endpoint `POST /hora/permissoes/<id>/criterio-pedidos` (`permissoes_set_criterio_pedidos`, perm `usuarios/editar`, bloqueio self/admin) + `<select>` no card do usuário.
- Migration dual: `scripts/migrations/hora_44_criterio_pedidos_e_criador.{py,sql}` (idempotente, IF NOT EXISTS + índice + backfill).

**Bug latente corrigido**: `venda_adicionar_item_peca`/`venda_remover_item_peca` redirecionavam para `hora.venda_detalhe` (rota inexistente → BuildError) → corrigido para `hora.vendas_detalhe`.

**Testes**: `tests/hora/test_pedido_filtro_vendedor.py` (filtro vendedor/loja + `criado_por_id`). Validação visual via Playwright: tela unificada (edição + criação) renderiza, cascata modelo→cor funciona, zero erros de console JS.

---

## 20. Editar item (moto travada) + Enter=Próximo + chassi autocomplete + restauração de regressões — 2026-06-03

Quatro frentes na tela unificada de Pedido de Venda (`pedido_venda_novo.html`). Spec: `docs/superpowers/specs/2026-06-03-hora-pedido-venda-edicao-autocomplete-design.md`. Plano: `docs/superpowers/plans/2026-06-03-hora-pedido-venda-edicao-autocomplete.md`.

**A — Editar item = só desconto/valor (moto travada)**: o collapse `#item-edit-<id>` mostra modelo/cor/chassi **read-only** e edita desconto %/R$ + valor final, sincronizados por `wireDescontoSync` (função por-escopo via classes `.js-desconto-pct/.js-desconto-rs/.js-valor` + `data-preco-tabela` no root — N instâncias sem colisão de ids). Só `valor_final` é submetido (backend deriva o desconto via `_resolver_preco_tabela`). **Trocar a moto = remover + readicionar.** A rota `vendas_item_editar` (`routes/vendas.py`) **deixou de ler `novo_chassi`** (defesa em profundidade); o service `editar_item_pedido` mantém a capacidade de troca só para os testes de workflow. Guard AST: `tests/hora/test_pedido_venda_editar_item.py`.

**B — Enter = "Próximo"**: `_pedido_venda_scripts.html` intercepta Enter em `input`/`select` dos forms de pedido → foca o próximo campo (não submete). `textarea` mantém Enter; submit por clique. Escopo: páginas de pedido (o script só carrega nelas).

**C — Chassi autocomplete**: o `<select id="f-chassi">` virou `<input data-hora-autocomplete="chassi" data-hora-extra-params="disponivel=1">`. Modelo/cor são **filtros opcionais** (sem `required`, label "(filtro)") que ajustam `data-hora-extra-params` (`modelo_id`/`cor`); ao escolher um chassi, o JS preenche modelo + preço de tabela. `autocomplete_service.chassis` ganhou `disponivel`/`modelo_id`/`cor` (disponível = último evento em `EVENTOS_EM_ESTOQUE`, critério canônico do `estoque_service`) + `modelo_id` no JSON; a rota `/autocomplete/chassi` repassa os filtros. **`app/static/js/hora/autocomplete.js` passou a ler `data-hora-extra-params` DINAMICAMENTE no fetch** (retrocompatível) — telas podem mudar os filtros em runtime sem reinit (evita dropdown duplicado). Testes: `tests/hora/test_autocomplete_chassi_disponivel.py`.

**D — Restauração de regressões** (perdidas na unificação `9a50b5af8`/`e6cc96586`; auditoria de 33 itens na spec):
- **Críticas**: seção "Peças do pedido" (tabela `itens_peca` + add via `data-hora-autocomplete="peca"` + remover c/ confirm; rotas `venda_adicionar_item_peca`/`venda_remover_item_peca`); botão "Reimportar do TagPlus" (`tagplus_backfill_nfe_unica`); `valor_frete`/`tipo_frete_calc` usam `disabled` (não `readonly`) quando travado — preserva frete FOB legado (input disabled não é submetido); confirm do descarte com aviso "A NFe NÃO será cancelada na SEFAZ"; aviso contextual de campos editáveis por status.
- **Altas**: KPIs (loja/chave 44d/data/valor/itens); parcelamento (`numero_parcelas`/`intervalo_parcelas_dias`, editáveis COTAÇÃO/CONFIRMADO via `ro_oper`) + aviso intervalo<7d; auditoria com colunas Campo/De/Para; histórico de divergências (resolvidas); preview de frete CIF multi-item (`tr[data-item-chassi/final/tabela]` → `#d-alerta-frete`); vendedor fallback "(não habilitado)" (não zera legado); pagamentos (badge INCOMPLETO no header + linha "total vs pedido" + coluna Tipo via `formas_pagamento|selectattr` + soma ao vivo no editor `pag-edit-*`); guard de modalidade de frete legada (2/3/4/9).
- **NÃO restaurado** (P-14 reclassificado como correção): endereço travado em FATURADO está **correto** — alinhado à matriz `_CAMPOS_EDITAVEIS_HEADER` (`venda_service.py`), onde FATURADO só aceita `observacoes`. O template antigo contrariava o backend. Backlog (médio/baixo): textos de confirm truncados, tooltips, placeholders, NF no `<h2>`, `origem_criacao`.

**Sem migration** (nenhuma mudança de schema). Validação: pytest `tests/hora/` verde · `node --check` no JS renderizado · Jinja compila.

**Follow-ups v2 (próxima sessão — NÃO feitos; reportados 2026-06-03 pós-deploy)** — detalhes na spec, seção "Follow-ups v2". Brainstorming antes de codar (FU-2+FU-3 são refactor grande):
- **FU-4 (BUG, prioridade)**: autocomplete de chassi **não filtra modelo+cor** (o `data-hora-extra-params` é setado por `atualizarFiltroChassi`, mas o filtro não chega no fetch — investigar front/ordem de eventos ou deploy não concluído; backend tem teste verde).
- **FU-1 (UX)**: autocomplete deve **listar/preencher ao clicar** (hoje só com ≥2 chars digitados) — opt-in em `autocomplete.js` para não afetar as ~20 telas.
- **FU-2 (refactor)**: área de "Moto vendida" **igual nas 2 telas** (criação vs edição).
- **FU-3 (feature)**: pedido permite **N motos na CRIAÇÃO** (hoje cria 1; edição já permite N). Unifica com FU-2.
- **FU-5 (UX)**: **um único "Salvar Pedido" no final** (hoje a edição tem vários "Salvar X" por seção/form granular). Ligado a FU-2+FU-3.
- **Obs. (investigar)**: motos **aparecem OK em COTAÇÃO** (entrega validada); dúvida se em **INCOMPLETO** não aparecem — o "bug pré-existente" (motos sumidas na edição) está parcialmente esclarecido, verificar por status.

---

## 21. Unificação multi-item do Pedido de Venda + "Salvar Pedido" único (FU-1/2/3/5) — 2026-06-04

Resolve os follow-ups v2 da §20. Spec: `docs/superpowers/specs/2026-06-04-hora-pedido-venda-unificacao-multi-item-design.md`. Plano: `docs/superpowers/plans/2026-06-04-hora-pedido-venda-unificacao-multi-item.md`. **Sem migration.**

- **FU-4 (não era código)**: o filtro modelo+cor do autocomplete já funcionava em PROD; o sintoma era **cache de browser** do `autocomplete.js` antigo (`Caddyfile` serve `/static/*` com `Cache-Control: immutable, max-age=604800` e a URL não tem `?v=`). Hard-refresh resolve. Risco sistêmico latente (qualquer mudança futura em JS/CSS fica invisível por 7d a quem já visitou) — cache-busting global fica como conserto opcional fora deste escopo.
- **FU-1 — autocomplete lista ao clicar**: `autocomplete_service.chassis(permitir_vazio=)` + rota `/autocomplete/chassi` lê `vazio_ok=1`; `app/static/js/hora/autocomplete.js` ganhou `data-hora-open-on-focus` (focar/clicar com campo vazio lista o top-N). Opt-in (não afeta as ~20 telas). O chassi do componente de moto usa a flag.
- **FU-3 — N motos na criação**: `criar_venda_manual(itens=[{numero_chassi, valor_final}, ...])` (retrocompatível: sem `itens`, usa `numero_chassi`/`valor_final` singulares). A rota `tagplus_pedido_venda_criar` lê `chassi[]`/`valor[]` via `_parse_itens_form`. Loop cria N `HoraVendaItem` + `RESERVADA` por item, `valor_total` = soma, status avaliado depois; 1 commit.
- **FU-2 — área de motos idêntica nas 2 telas**: componente de **lista repetível** `_lista_motos.html` + `_linha_moto.html` (substituem `_componente_moto_desconto.html`, removido). Linha = só classes `.js-*` (sem ids `f-*` globais → sem colisão entre N linhas); item existente (edição) = chassi/modelo/cor read-only + hidden `item_id`, só valor/desconto editam; linha nova = cascata completa; `somente_leitura`/`ro_oper` trava tudo. JS por-linha (`wireLinhaMoto`, cascata + `wireDescontoSync` por escopo + add/remove); `atualizarSomaPagamentos` soma os `.js-valor` das linhas (não mais o `f-valor` global).
- **FU-5 — um único "Salvar Pedido"**: novo `salvar_pedido_completo(venda_id, header, itens, pagamentos, usuario)` **reconcilia** numa transação compondo helpers **flush-only** `_aplicar_header` / `_aplicar_itens` (diff add/remove/update; `DEVOLVIDA`/`RESERVADA` + lock; guard "não remove o último") / `_aplicar_pagamentos`, com **1 commit**. Itens só em COTAÇÃO; pagamentos+`valor_total`+status só em INCOMPLETO/COTAÇÃO (não derruba CONFIRMADO+). **Corrige o gap itens↔pagamentos** (status reavaliado numa passada). Gotcha: `db.session.expire(venda, ['itens'])` após `_aplicar_itens` — a coleção em memória não reflete `delete()`/`add()` via session, sem isso o `sum()` somava estale. Rota `POST /vendas/<id>/salvar` (`vendas_salvar_pedido`); a tela de edição vira **um** form `#form-pedido-venda` → `vendas_salvar_pedido` (mesmo id da criação — branches exclusivas).
- **Rotas granulares deprecadas** (decisão do dono): `vendas_editar`, `vendas_pagamentos_editar`, `vendas_item_adicionar/remover/editar` permanecem registradas (sem link na UI) — só os forms saíram do template; cleanup futuro. As funções de service `editar_venda`/`editar_pagamentos`/`adicionar_item_pedido`/etc. seguem (wrappers `helper + commit`; usadas por testes).
- **Peças**: ficam inline (fora do v1; `venda_adicionar_item_peca`/`remover` AJAX).

**Testes**: `test_criar_venda_multi_item`, `test_parse_itens_form`, `test_helpers_flush_only`, `test_salvar_pedido_completo`, `test_parse_form_edicao` (+ regressão `test_pedido_workflow`/`test_pedido_venda_editar_item`/`test_autocomplete_chassi_disponivel`) — 38 verdes. Validação comportamental no browser **não** executada nesta entrega (a pedido); Jinja compila + `node --check` no JS.

---

## Onboarding Tours (2026-05-08)

Tours guiados in-app via Driver.js para usuarios novos.

**Spec:** `docs/superpowers/specs/2026-05-08-onboarding-tours-hora-assai-design.md`
**Plano:** `docs/superpowers/plans/2026-05-08-onboarding-tours-hora-assai.md`

**Estrutura:**
- 1 macro adaptativo (`hora.macro`) com 9 passos filtrados por `requirePerm: { modulo, acao }`
- 13 mini-tours por tela critica em `app/static/onboarding/tours/hora/`
- Filtragem: usuario so ve tours com permissao no `permissao_service.get_matriz`
- Auto-start no 1o acesso a cada tela (localStorage por user_id)

**Adicionar tour novo:**
1. Criar `app/static/onboarding/tours/hora/<nome>.js` com `requirePerm: { modulo, acao }`
2. Adicionar IDs nos elementos do template alvo (em wrappers se necessario para nao colidir)
3. Incluir no `{% block onboarding_tours %}` do template
4. **OBRIGATORIO**: incluir `<script>` em `app/templates/admin/onboarding_health.html` E `onboarding_preview.html`. Sem isso o tour nao aparece nas paginas admin
5. Validar em `/admin/onboarding/health` apos commit
6. Preview em `/admin/onboarding/preview?tour=hora.<nome>`

**Engine:** `window.OnboardingEngine` (register/start/isVisible/listAllVisible)
**Tracker:** `window.OnboardingTracker` (wasSeen/markSeen/resetModule)

---

## 17. Desconsiderar moto de NF de compra — 2026-06-03

Permite marcar um item de NF de entrada (`HoraNfEntradaItem`) como **desconsiderado**: moto que veio em NF emitida para outra empresa e **não é da HORA**. O item sai do estoque/recebimento e o cadastro `HoraMoto` é removido, mas o item permanece na NF (reversível).

**Modelo** (`app/hora/models/compra.py`):
- `HoraNfEntradaItem.desconsiderado` (Boolean, default false).
- FK `numero_chassi → hora_moto` **removida** (migration `hora_43`): item desconsiderado mantém o chassi declarado sem `HoraMoto`. `relationship('moto')` é `viewonly` com `primaryjoin`. Integridade item↔moto garantida por validação aplicativa (`nf_entrada_service.assert_item_moto_consistente`), não por FK.
- `HoraNfEntrada.itens_considerados` — property que filtra `desconsiderado=False`; base do recebimento e do matching.

**Serviços** (`app/hora/services/nf_entrada_service.py`):
- `desconsiderar_item_nf(nf_item_id, operador)` — valida pré-condições e remove a `HoraMoto`. Faz `flush()` (NÃO commit) — o `commit()` é da rota.
- `reconsiderar_item_nf(nf_item_id, operador)` — reverte: recria a `HoraMoto` via `get_or_create_moto` + zera o flag.
- Gates (`_motivo_bloqueio_desconsiderar`): bloqueia se o chassi está em pedido (`chassi_protecao_service.chassi_em_pedido`), se a NF já entrou em recebimento, se o chassi foi conferido, se a moto tem qualquer evento, ou se o chassi consta em outro item de NF considerado.

**Efeito no recebimento/matching**: `recebimento_service` usa `nf.itens_considerados` nos pontos "a receber" (qtd declarada, conferência automática, faltantes, esperados, listagem); `matching_service._chassis_nf` exclui desconsiderados. Estoque deriva de evento — item desconsiderado nunca recebe `RECEBIDA`.

**UI**: `app/templates/hora/nf_detalhe.html` (badge "desconsiderada" + botões Desconsiderar/Reverter por item; cadeado quando em pedido ou NF já em recebimento) + rotas `nfs_desconsiderar_item`/`nfs_reverter_item` em `app/hora/routes/nfs.py` (perm `nfs/editar`).

**Migration**: `scripts/migrations/hora_43_nf_item_desconsiderar.{py,sql}`.

**Spec/Plano**: `docs/superpowers/specs/2026-06-03-hora-desconsiderar-moto-nf-design.md` · `docs/superpowers/plans/2026-06-03-hora-desconsiderar-moto-nf.md`.

---

## 19. Guarda do recebimento automático (anti-ressurreição) — 2026-06-03

**Incidente**: o backfill `scripts/hora/backfill_recebimentos.py` (operador `BACKFILL_2026_05_16`) re-processou TODAS as NFs de entrada sem olhar o estado atual do chassi e emitiu um evento `RECEBIDA` (id/timestamp = momento do backfill) por cima de motos já `VENDIDA`. Como **estado da moto = último evento** (invariante 4), essas motos voltaram a contar como "em estoque". Medido em PROD: **505 chassis** cujo último estado real era `VENDIDA` passaram a aparecer como `RECEBIDA`.

**Causa estrutural**: a máquina de estado é "último evento vence", sem validação de transição — `registrar_evento` (`moto_service.py`) aceita qualquer tipo da allow-list, e `criar_recebimento_automatico_da_nf` não checava o estado atual antes de conferir cada item. Nota: a derivação de "último evento" diverge entre `estoque_service` (`MAX(id)`) e `moto_service`/`rastreamento_completo` (`MAX(timestamp)`); hoje concordam, mas inserção retroativa pode fazê-las divergir (risco latente conhecido — **não** corrigido nesta entrega).

**Guarda** (`recebimento_service.py`):
- `criar_recebimento_automatico_da_nf` **pula** itens cujo `status_atual(chassi)` está em `EVENTOS_FORA_ESTOQUE | EVENTOS_EM_TRANSITO` (vendida/reservada/devolvida/NF emitida/NF cancelada/em trânsito). Não cria conferência nem emite `RECEBIDA`; coleta em `chassis_pulados_ja_fora` (no retorno e na auditoria `RECEBIMENTO_AUTOMATICO`).
- `finalizar_recebimento` ganhou o parâmetro `ignorar_chassis: Optional[Set[str]] = None` (default = comportamento histórico). Os pulados são passados aí para **não** virarem `MOTO_FALTANDO` (eles não estão faltando — já foram vendidos).
- Motos `RECEBIDA`/`CONFERIDA`/em estoque ou sem evento seguem o fluxo normal (o backfill deleta os recebimentos antes, então re-receber estoque legítimo continua válido).

**Correção do passivo** (505 motos já gravadas): `scripts/hora/fix_backfill_vendidas_revertidas.py` re-emite `VENDIDA` (método aditivo A1) herdando `loja_id`/origem do último `VENDIDA` real. Dry-run por default, `--confirmar` para executar, idempotente (seleção zera após a correção). Não apaga o `RECEBIDA` do backfill (preserva histórico).

**Testes**: `tests/hora/test_recebimento_automatico_blindagem.py` (4 casos: pula vendido; pula reservado/em-trânsito; `ignorar_chassis` não marca faltante; default marca faltante).

---

## 22. Notificação WhatsApp de NF emitida / pedido confirmado (TagPlus) — 2026-06-06

Réplica do fluxo N8N: notifica um **grupo único de vendas** no WhatsApp **e a DM do vendedor** quando uma NFe da loja é aprovada e quando um pedido de venda é confirmado. NF leva o **PDF da DANFE anexado**. Spec: `docs/superpowers/specs/2026-06-06-hora-tagplus-notificacao-whatsapp-design.md`. Plano: `docs/superpowers/plans/2026-06-06-hora-tagplus-notificacao-whatsapp.md`.

> **Origem**: a 1ª tentativa foi feita por engano no TagPlus da Nacom (`app/integracoes/tagplus/`) e **revertida**; a implementação correta vive toda em `app/hora/` (fronteira do módulo).

**Gatilhos (best-effort — nunca quebram o fluxo principal)**:
- **NF aprovada**: `webhook_handler.WebhookHandler.processar` chama `_disparar_notificacao_nfe_safe(emissao.id)` **após o commit**, só para `nfe_aprovada`.
- **Pedido confirmado**: `venda_service.confirmar_venda` chama `enfileirar_notificacao('PEDIDO', venda.id)` **após o commit** do status `CONFIRMADO`.

**Processamento**: job `processar_notificacao(registro_id)` na fila RQ **`hora_nfe`** (já em PROD). Service `app/hora/services/tagplus/notificacao_whatsapp.py`: `enfileirar_notificacao(tipo, ref_id)` (dedupe por `UNIQUE(tipo, ref_id)` + enqueue), `processar_notificacao` (busca venda/NFe → formata → resolve vendedor → baixa DANFE via `ApiClient` → envia grupo + DM), `reenfileirar`, `_resolver_vendedor` (casa `HoraVenda.vendedor` com `usuarios.vendedor_vinculado`/`nome` + `whatsapp_autorizado` + `telefone`), `_enviar_para_destinos` (idempotente por destino: `enviado_grupo`/`enviado_vendedor`).

**Envio**: reusa `app/utils/whatsapp_notify.send_whatsapp(target, text, anexo_b64=, anexo_filename=)` (gateway OpenClaw, anexo via `buffer` base64).

**Model/migration**: `HoraTagPlusNotificacaoWhatsapp` (`app/hora/models/tagplus.py`) + `scripts/migrations/hora_45_tagplus_notificacao_whatsapp.{py,sql}`.

**Tela**: `/hora/tagplus/notificacoes` (`require_hora_perm('tagplus','ver')`; reenviar = `'editar'`) — `app/templates/hora/tagplus/notificacoes.html` (extends `hora/base.html`). Menu: grupo "Faturamento (TagPlus)" no `_sidebar.html`.

**Env**: `HORA_TAGPLUS_NOTIFY_GROUP_JID` (JID `...@g.us`, obrigatório) + `HORA_TAGPLUS_NOTIFY_ENABLED` (kill switch) + reuso `OPENCLAW_GATEWAY_*`. Vendedor sem cadastro/autorização → fallback só-grupo (status `ENVIADO`, `enviado_vendedor=NULL`).

**Testes**: `tests/hora/test_notificacao_whatsapp_model.py` (2), `test_notificacao_whatsapp_service.py` (4), `test_notificacao_gatilhos.py` (4), `test_notificacao_tela.py` (4), `tests/test_whatsapp_notify_anexo.py` (2). Gotcha: a tabela acumula resíduo de teste local se o teardown abortar — `DELETE FROM hora_tagplus_notificacao_whatsapp` antes de re-rodar.

---

## Referências

- **Contrato de design**: `docs/hora/INVARIANTES.md`
- **Análise de primeiros princípios**: comando `/fp-lojas-motochefe` (`.claude/commands/fp-lojas-motochefe.md`)
- **Precedente de chassi como PK** (ver, não copiar): `app/motochefe/models/produto.py:45`
- **Parsers reusáveis**: `app/carvia/services/parsers/danfe_pdf_parser.py`, `app/carvia/services/pricing/moto_recognition_service.py`
- **Regra de migrations duais**: `/home/rafaelnascimento/.claude/CLAUDE.md` seção "MIGRATIONS"
- **JSON sanitization** (se usarmos JSONB para foto/metadados): `/home/rafaelnascimento/.claude/CLAUDE.md` seção "JSON SANITIZATION"
