<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-27
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
- [22. Notificação WhatsApp de NF emitida / pedido confirmado (TagPlus) — 2026-06-06](#22-notificação-whatsapp-de-nf-emitida--pedido-confirmado-tagplus--2026-06-06)
- [23. Pedido de Venda — edição em INCOMPLETO + preço a prazo na tela + AUT — 2026-06-25](#23-pedido-de-venda--edição-em-incompleto--preço-a-prazo-na-tela--aut--2026-06-25)
- [24. Inscrição Estadual + Consulta CNPJ (ReceitaWS) no Pedido de Venda — 2026-06-25](#24-inscrição-estadual--consulta-cnpj-receitaws-no-pedido-de-venda--2026-06-25)
- [25. Impressão de documentos do Pedido de Venda (PDV + termos) — 2026-06-26](#25-impressão-de-documentos-do-pedido-de-venda-pdv--termos--2026-06-26)
- [26. Reserva cancelada devolve a moto ao estoque (fix DEVOLVIDA) — 2026-06-26](#26-reserva-cancelada-devolve-a-moto-ao-estoque-fix-devolvida--2026-06-26)
- [27. Correções de campo do Pedido de Venda + aprovação gerencial (frete/brinde) — 2026-06-26](#27-correções-de-campo-do-pedido-de-venda--aprovação-gerencial-fretebrinde--2026-06-26)
- [28. Perfis de permissão das Lojas HORA (template de permissões) — 2026-06-27](#28-perfis-de-permissão-das-lojas-hora-template-de-permissões--2026-06-27)
- [29. Seção Gerencial — dashboards + relatórios — 2026-06-27](#29-seção-gerencial--dashboards--relatórios--2026-06-27)
- [30. Brinde — gerenciar em INCOMPLETO, exibir no preview e CORTESIA na NF — 2026-06-27](#30-brinde--gerenciar-em-incompleto-exibir-no-preview-e-cortesia-na-nf--2026-06-27)
- [31. Recebimento — dropdown de modelos canônicos + anti-duplicação de grafia de cor — 2026-06-27](#31-recebimento--dropdown-de-modelos-canônicos--anti-duplicação-de-grafia-de-cor--2026-06-27)
- [32. Recebimento — autocomplete de NF por permissão + guarda anti-duplicado — 2026-06-27](#32-recebimento--autocomplete-de-nf-por-permissão-de-recebimento--guarda-anti-duplicado--2026-06-27)
- [33. Loja real da venda vs matriz (emitente fiscal) — integridade — 2026-06-27](#33-loja-real-da-venda-vs-matriz-emitente-fiscal--integridade--2026-06-27)
- [34. Pedido de Venda — vendedor ao lado da loja + campo Telefone Lead — 2026-06-28](#34-pedido-de-venda--vendedor-ao-lado-da-loja--campo-telefone-lead--2026-06-28)
- [35. CORTESIA de revisão — texto institucional na NF — 2026-06-28](#35-cortesia-de-revisão--texto-institucional-na-nf--2026-06-28)
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

## Modelo de dados (48 tabelas — núcleo conceitual abaixo)

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
- `hora_perfil` + `hora_perfil_permissao` — **perfis de permissão HORA** (template que pré-preenche/redefine as permissões de um usuário). Migration: `scripts/migrations/hora_55_perfis.{py,sql}`. Ver seção 28.

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

**Módulos canônicos**: a lista COMPLETA e fonte de verdade é `MODULOS_HORA` em
`app/hora/models/permissao.py` (cresceu bem além do núcleo original
`usuarios, dashboard, lojas, modelos, pedidos, nfs, recebimentos, estoque, devolucoes, pecas` —
inclui hoje os módulos virtuais de visibilidade fina descritos abaixo). Sempre
consultar o código, não esta lista, ao contar/conferir módulos.

**5 ações** (`ACOES_HORA`): `ver, criar, editar, apagar, aprovar`.
A ação `aprovar` é semântica e só tem decorator real no módulo `usuarios` (aprovação de cadastros pendentes). Para os demais, a flag é armazenada mas ignorada — o template marca a célula com `—`.

**Flags de visibilidade fina (módulos virtuais em `MODULOS_SO_VER`)**: além dos
módulos-CRUD, existem slugs que só usam a ação `ver` para gatear pedaços de UI:
- `estoque_valores` — exibe os valores R$ no detalhe do chassi (`estoque_chassi_detalhe.html`:
  Preço esperado do pedido, Valor total + Preço desta moto da NF de entrada, Preço da venda).
  Sem a flag, o vendedor vê a moto/rastreio mas não os valores.
- `estoque_exportar` — botão + rota `estoque_exportar_xlsx` (export do estoque).
- `vendas_exportar` — botão + rota `vendas_exportar_xlsx` (export dos pedidos de venda).
- `vendas_nf` — **ação fiscal da NF de saída** (emitir/preview/cancelar/CC-e), SEPARADA
  do pedido de venda. Rotas `venda_nfe_{preview,emitir,cancelar,cce}` e os botões em
  `pedido_venda_novo.html` / `nfe_status.html` / `venda_preview_nfe.html`. Permite dar
  ao vendedor o poder de **criar pedido** (`vendas/criar`) SEM o poder de **emitir/cancelar
  a NFe fiscal**. O módulo `vendas` foi renomeado para "Vendas (Pedido de Venda)" — ele
  NÃO gateia mais a NF (só o pedido: COTACAO→CONFIRMADO + edição/itens).

São independentes de `estoque/ver` e `vendas/ver` (ver a tela ≠ ver valores / exportar / emitir NF).
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
- `get_matriz(user_id)` — dict `{modulo: {acao: bool}}` com todos os módulos de `MODULOS_HORA` × 5 ações.
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
   - **`loja_id` (COMERCIAL) ≠ emitente (FISCAL).** A loja física da venda vive em
     `hora_venda.loja_id` (verdade comercial: rankings, comissão, relatórios). O
     import/backfill **nunca** grava `loja_id`=matriz: resolve via `tagplus_departamento`
     → `hora_tagplus_departamento_map` ou, se só a matriz resolver, grava `NULL` +
     divergência `CNPJ_DESCONHECIDO` (loja a definir). A matriz é marcada
     `HoraLoja.is_matriz=True` (migration `hora_57`) e EXCLUÍDA das superfícies de venda.
     A UF do emitente para o CFOP vem da matriz, não de `venda.loja`. Detalhes: **seção 33**.

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

   **Edição de itens** (funções granulares DEPRECADAS — só em COTACAO; o caminho vigente `salvar_pedido_completo` edita itens também em INCOMPLETO desde 2026-06-25, ver §23):
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
   - `vendas/editar`: vendedor padrao — cria pedido, edita itens em INCOMPLETO/COTACAO (via `salvar_pedido_completo`, §23), confirma (`vendas_confirmar`).
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
- **FU-5 — um único "Salvar Pedido"**: novo `salvar_pedido_completo(venda_id, header, itens, pagamentos, usuario)` **reconcilia** numa transação compondo helpers **flush-only** `_aplicar_header` / `_aplicar_itens` (diff add/remove/update; `DEVOLVIDA`/`RESERVADA` + lock; guard "não remove o último") / `_aplicar_pagamentos`, com **1 commit**. Itens só em COTAÇÃO; pagamentos+`valor_total`+status só em INCOMPLETO/COTAÇÃO (não derruba CONFIRMADO+). **Corrige o gap itens↔pagamentos** (status reavaliado numa passada). Gotcha: `db.session.expire(venda, ['itens'])` após `_aplicar_itens` — a coleção em memória não reflete `delete()`/`add()` via session, sem isso o `sum()` somava estale. Rota `POST /vendas/<id>/salvar` (`vendas_salvar_pedido`); a tela de edição vira **um** form `#form-pedido-venda` → `vendas_salvar_pedido` (mesmo id da criação — branches exclusivas). **Atualizado 2026-06-25 (§23):** itens são reconciliados em **INCOMPLETO ou COTAÇÃO** (antes só COTAÇÃO).
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

Notifica o **grupo WhatsApp da loja** (regra **1 grupo por loja** desde 2026-06-27 — antes: grupo único global + DM do vendedor) quando uma NFe da loja é aprovada e quando um pedido de venda é confirmado. NF leva o **PDF da DANFE anexado**. **Sem DM do vendedor** (decisão do dono 2026-06-27: só o grupo). Spec: `docs/superpowers/specs/2026-06-06-hora-tagplus-notificacao-whatsapp-design.md`. Plano: `docs/superpowers/plans/2026-06-06-hora-tagplus-notificacao-whatsapp.md`.

> **Origem**: a 1ª tentativa foi feita por engano no TagPlus da Nacom (`app/integracoes/tagplus/`) e **revertida**; a implementação correta vive toda em `app/hora/` (fronteira do módulo).

**Gatilhos (best-effort — nunca quebram o fluxo principal)**:
- **NF aprovada**: `webhook_handler.WebhookHandler.processar` chama `_disparar_notificacao_nfe_safe(emissao.id)` **após o commit**, só para `nfe_aprovada`.
- **Pedido confirmado**: `venda_service.confirmar_venda` chama `enfileirar_notificacao('PEDIDO', venda.id)` **após o commit** do status `CONFIRMADO`.

**Processamento**: job `processar_notificacao(registro_id)` na fila RQ **`hora_nfe`** (já em PROD). Service `app/hora/services/tagplus/notificacao_whatsapp.py`: `enfileirar_notificacao(tipo, ref_id)` (dedupe por `UNIQUE(tipo, ref_id)` + enqueue), `processar_notificacao` (busca venda/NFe → formata → **resolve o grupo pela loja** `venda.loja.whatsapp_grupo_jid` → baixa DANFE via `ApiClient` → **envia só ao grupo**), `reenfileirar`, `_enviar_para_destinos` (idempotente via `enviado_grupo`; **loja sem grupo → status ERRO**, não envia). `_resolver_vendedor` mantida **reservada** (DM desativado 2026-06-27, reativável); coluna `enviado_vendedor` vestigial (sempre NULL).

**Envio (transport-aware desde 2026-06-27)**: passa pelo dispatcher
`app/utils/whatsapp_dispatch.send_whatsapp_unificado(target, text, anexo_b64=, anexo_filename=)`,
que roteia por **`HORA_WHATSAPP_TRANSPORT`** (`openclaw` default | `evolution`) — env **própria do
HORA**, independente do `WHATSAPP_TRANSPORT` do canal do agente (migra o envio do HORA sem tocar no
agente). Caminhos: `openclaw` → `whatsapp_notify.send_whatsapp` (gateway local loopback:18789, anexo
via `buffer` base64, **depende do PC do operador ligado**); `evolution` →
`whatsapp_evolution.send_whatsapp_evolution` (texto) + `send_media_evolution` (anexo via
`POST /message/sendMedia`, `mediatype=document`, base64), Evolution API 24/7 num Web Service Render
(`evoapicloud/evolution-api`), **não depende do PC**. O mesmo dispatcher serve o recibo ao cliente
(`recibo_service.enviar_recibo_whatsapp`).

**Model/migration**: `HoraTagPlusNotificacaoWhatsapp` (`app/hora/models/tagplus.py`) + `scripts/migrations/hora_45_tagplus_notificacao_whatsapp.{py,sql}`.

**Tela**: `/hora/tagplus/notificacoes` (`require_hora_perm('tagplus','ver')`; reenviar = `'editar'`) — `app/templates/hora/tagplus/notificacoes.html` (extends `hora/base.html`). Menu: grupo "Faturamento (TagPlus)" no `_sidebar.html`.

**Env**: `HORA_TAGPLUS_NOTIFY_GROUP_JID` (legado/fallback — hoje o grupo vem da loja) + `HORA_TAGPLUS_NOTIFY_ENABLED` (kill switch) + **`HORA_WHATSAPP_TRANSPORT`** (`openclaw`|`evolution`). OpenClaw: `OPENCLAW_GATEWAY_*`. Evolution: `EVOLUTION_API_URL`/`EVOLUTION_API_KEY`/`EVOLUTION_INSTANCE`. **Loja sem grupo configurado → status `ERRO` (não envia)** — relevante só para lojas que VENDEM; a matriz emitente (`MOTOCHEFE MATRIZ SP`, id=1) fica **sem grupo de propósito** (não faz venda física — vendas atribuídas a ela são erro de atribuição corrigido pela §32). Coluna `enviado_vendedor` vestigial (sempre NULL — DM desativado 2026-06-27). Grupo por loja em `hora_loja.whatsapp_grupo_jid` (migration `hora_56`), configurável na tela da loja (dropdown ao vivo via `fetch_grupos_evolution`). **Em PROD (2026-06-27):** Evolution ativa (`HORA_WHATSAPP_TRANSPORT=evolution`, instância `hora`), 4 filiais (Tatuapé/Bragança/PG/Santana) com grupo gravado.

**E-mail do HORA (NF + recibo ao cliente) — conta PRÓPRIA, isolada (2026-06-27)**: `nf_email_service` e `recibo_service.enviar_recibo_email` enviam de `financeiro@motochefesp.com.br` (Hostinger) via `app/hora/services/hora_email.py` (`HoraEmailConfig` + `hora_email_sender`), que lê envs **`HORA_EMAIL_*`** (`HOST`/`PORT`/`USERNAME`/`PASSWORD`/`USE_SSL`/`USE_TLS`; defaults `smtp.hostinger.com`/`465`/SSL no código — em PROD só `HORA_EMAIL_PASSWORD` precisa ser setada). **NÃO usar as `EMAIL_*` genéricas** (conta Gmail do sistema, usada por `app/notificacoes` + `app/manufatura`): o `EmailSender.__init__(config=)` aceita config injetada justamente para o HORA ter caixa própria. Remetente fixo: `HORA_NF_EMAIL_FROM`/`HORA_NF_EMAIL_FROM_NAME`. Lição (incidente 2026-06-27): NUNCA sobrescrever `EMAIL_*` para o HORA — são compartilhadas.

**Testes**: `tests/hora/test_notificacao_whatsapp_model.py` (2), `test_notificacao_whatsapp_service.py` (4), `test_notificacao_gatilhos.py` (4), `test_notificacao_tela.py` (4), `tests/test_whatsapp_notify_anexo.py` (2). Gotcha: a tabela acumula resíduo de teste local se o teardown abortar — `DELETE FROM hora_tagplus_notificacao_whatsapp` antes de re-rodar.

---

## 23. Pedido de Venda — edição em INCOMPLETO + preço a prazo na tela + AUT — 2026-06-25

Quatro correções no Pedido de Venda (`HoraVenda`), motivadas por um pedido real (1090)
criado com forma **a prazo** mas precificado como **à vista** na tela. Sem migration.

**F1 — Editar itens enquanto NÃO confirmado (INCOMPLETO além de COTAÇÃO).**
Antes, trocar/adicionar/remover moto só era possível em COTAÇÃO — um pedido salvo
como INCOMPLETO (ex.: falta AUT/valor) travava a edição da moto. Mudança em **dois
gates que andam juntos** (UI sozinha enganaria o usuário):
- `pedido_venda_novo.html` (bloco `set itens_editaveis`) → `(is_cotacao or is_incompleto) and pode_editar`.
- `venda_service.salvar_pedido_completo` → reconcilia itens (`_aplicar_itens`) em
  `INCOMPLETO` ou `COTAÇÃO` (antes só COTAÇÃO; em INCOMPLETO os itens submetidos
  eram **descartados em silêncio**). Trocar moto de item existente continua sendo
  **remover + readicionar** (chassi/modelo/cor de item existente são read-only por design).

**F2 — Tela reflete o preço A PRAZO (bug de JS, NÃO de cadastro).**
A forma `INFINITE_PAY_PARC` está classificada `A_PRAZO` no banco (não era config). Causa:
na criação multi-item o preço é resolvido **por linha-moto** (`atualizarPrecoTabelaLinha`),
disparado só ao mudar modelo/chassi; trocar a **forma de pagamento** chamava o
`atualizarPrecoTabela()` legado (no-op no multi-item) e **não re-precificava as motos**.
- Nova `reprecificarLinhasMoto()` (`_pedido_venda_scripts.html`) re-resolve o preço de
  TODAS as linhas-moto quando a forma muda (criação **e** editor de edição); item
  existente (sem `.js-modelo`) é ignorado (mantém o preço gravado).
- `formaRepresentativaParaPreco()` passou a varrer `#pagamentos-container .pag-forma`
  **e** `#pag-edit-container select[name=pagamento_forma]`; os options do editor de
  edição ganharam `data-tipo`/`data-aut`.
- **Backend (gotcha de ordem):** `_aplicar_itens` ganhou `forma_para_preco`; `salvar_pedido_completo`
  passa a forma representativa dos pagamentos **submetidos** (não o cache `venda.forma_pagamento`
  antigo, que p/ MISTO resolvia A_VISTA). `criar_venda_manual` já fazia certo via `_classificar_formas_para_preco`.

**F3 — Sem desconto-fantasma.** O desconto sempre foi `preco_tabela − valor_final`
(`_resolver_preco_tabela`); quando a tela mostrava à vista (11.990) e o backend gravava
a prazo (12.990), a diferença (1.100) virava "desconto" que ninguém digitou. Corrigido na
raiz por F2; além disso a linha-moto agora mostra o preço à vista como **referência**
(“a prazo — à vista seria R$ Y”). Salvaguarda de teto **já existia** em
`aprovacao_desconto_service` (bloqueia confirmação se `desconto_aplicado >
hora_modelo.desconto_maximo`) — depende do modelo ter `desconto_maximo` preenchido
(config; JET MAX estava NULL).

**F4 — AUT obrigatório para AVANÇAR (hard no avanço, soft no rascunho).** Já estava
fechado no backend e foi **blindado por teste**: forma com `exige_aut_id` sem `aut_id`
força `INCOMPLETO` (`_avaliar_status_pagamento`); `confirmar_venda` bloqueia INCOMPLETO;
`EmissorNfeHora.enfileirar` só emite CONFIRMADO/FATURADO. Salvar rascunho continua livre.

**Testes:** `tests/hora/test_pedido_venda_correcoes_2026_06_25.py` (6) — F1 troca/adiciona
em INCOMPLETO, F2 criar/salvar a prazo, F4 confirmar com/sem AUT. Validação: `node --check`
no JS renderizado + Jinja compila + suíte de venda (32) verde.

---

## 24. Inscrição Estadual + Consulta CNPJ (ReceitaWS) no Pedido de Venda — 2026-06-25

Dois acréscimos na tela de Pedido de Venda (criação **e** edição):

**Campo Inscrição Estadual** (`hora_venda.inscricao_estadual VARCHAR(20)`, migration
`hora_52`): registro/exibição do destinatário PJ. **NÃO entra no payload da NFe**
(decisão do dono) — é só cadastro. Editável em INCOMPLETO/COTAÇÃO (junto com nome/CPF, em
`_CAMPOS_COTACAO_FULL`). Lido por `criar_venda_manual`, `_aplicar_header` e as rotas
`tagplus_pedido_venda_criar` / `vendas_salvar_pedido` (campo `name="inscricao_estadual"`,
id `f-ie`).

**Botão "Consultar CNPJ"** ao lado do CPF/CNPJ: rota AJAX
`/hora/tagplus/pedido-venda/api/consultar-cnpj` (`require_hora_perm_any(('vendas','criar'),
('vendas','editar'))`), reusa `receitaws_service.consultar_cnpj` (mesma fonte do cadastro
de loja). O JS `consultarCnpj()` (em `_pedido_venda_scripts.html`, espelha `buscarCep`)
pré-preenche **apenas os campos vazios** (decisão do dono) — razão social, endereço,
telefone, email. `consultar_cnpj` tem **cache curto** in-memory por CNPJ
(`cachetools.TTLCache`, TTL 5 min, com lock) para não queimar a cota da ReceitaWS
(~3 req/min) em re-consultas; o HTTP 500 da rota não vaza a exceção (só loga).

**Limitação:** a ReceitaWS é base **federal** e **NÃO retorna Inscrição Estadual**
(estadual/SEFAZ). A IE permanece manual; o JS avisa isso após a consulta.

**Testes:** `test_ie_grava_na_criacao`, `test_ie_editavel_em_incompleto`
(`tests/hora/test_pedido_venda_correcoes_2026_06_25.py`). Migration aplicada em local + PROD.

---

## 25. Impressão de documentos do Pedido de Venda (PDV + termos) — 2026-06-26

Dropdown **Imprimir** na barra de topo do detalhe (`pedido_venda_novo.html`) gera 4
documentos pré-preenchidos via **WeasyPrint** (mesmo padrão de `recibo_service`), com
merge por **pypdf**. Sem migration, sem permissão nova (reusa `vendas/ver`).

**Service** `app/hora/services/documento_venda_service.py`:
- `gerar_pdv_pdf` — Pedido/Orçamento. Título dinâmico: `titulo_pdv()` → **"Cotação"**
  (INCOMPLETO/COTACAO) ou **"Pedido de Venda"** (CONFIRMADO/FATURADO). Emitente =
  **razão social, CNPJ e e-mail FIXOS da matriz** (`EMITENTE_MATRIZ`: "HORA COMÉRCIO
  DE MOTOCICLETAS LTDA", 62.634.044/0001-20) — **sem endereço, sem telefone, sem CNPJ
  de loja** (regra fiscal: NF-e sai sempre da matriz). A loja física da venda aparece
  só como **"Vendido por: <nome>"** (`loja.rotulo_display`, sem CNPJ). O CNPJ fixo também
  alimenta o cabeçalho "GRUPO SP" dos termos. Tabela de produtos = motos (1 un cada) +
  `itens_peca`; pagamentos de `venda.pagamentos` (fallback header `forma_pagamento`+`numero_parcelas`).
- `gerar_termo_garantia_pdf` / `gerar_termo_checagem_pdf` — **1 jogo por moto** (concatenado).
- `gerar_termo_ciclomotor_pdf` — 1 por moto ciclomotor; levanta `DocumentoVendaError`
  se nenhuma se aplica.
- `gerar_pacote_pdf` — PDF único: PDV + (garantia+checagem se CONFIRMADO/FATURADO) +
  (ciclomotor se houver). É o botão **"Imprimir tudo"**.

**Critério ciclomotor (canônico):** `tem_ciclomotor()` = algum item com
`moto.modelo.autopropelido is False` (mesmo campo que classifica a NF-e — NÃO
reimplementar por potência). A rota `vendas_detalhe` passa `tem_ciclomotor` ao template
para habilitar/desabilitar o item do dropdown.

**Rotas** (`vendas.py`, todas `@require_hora_perm('vendas','ver')` + escopo de loja):
`vendas_doc_pdv`, `vendas_doc_termo_garantia`, `vendas_doc_termo_checagem`,
`vendas_doc_termo_ciclomotor`, `vendas_doc_pacote` — servem PDF inline on-the-fly.

**Templates:** `app/templates/hora/documentos/{pdv,termo_garantia,termo_checagem,termo_ciclomotor}.html`.
Logo embutido como data-URI base64 (`app/static/hora/img/motochefe_logo.png`) — não
depende de `base_url`/servidor (funciona em worker/teste).

**Testes:** `tests/hora/test_documento_venda.py` (13) — título por status, classificação
ciclomotor, geração dos 4 PDFs, critério de status do pacote, emitente matriz fixa +
`vendido_por` (`test_emitente_matriz_fixa_e_vendido_por`).

---

## 27. Correções de campo do Pedido de Venda + aprovação gerencial (frete/brinde) — 2026-06-26

Lote de ajustes na tela de Pedido de Venda (`pedido_venda_novo.html` +
`_pedido_venda_scripts.html`) a partir de feedback das vendedoras, mais a extensão
do fluxo de aprovação.

**Correções (UX/bug):**
- **Criação não apaga mais ao faltar obrigatório**: a validação client-side
  (`_pedido_venda_scripts.html`, handler de submit) destaca o 1º campo `*` vazio
  (`is-invalid` + foco + scroll) e bloqueia o submit **sem zerar o form**. Mantém o
  `novalidate` de propósito (remover tornaria pagamento/AUT obrigatórios e quebraria
  o rascunho INCOMPLETO); o guard só roda na criação (gate por `action`) e **exclui
  `pagamento_*`**.
- **Badge INCOMPLETO mostra o motivo real** (soma divergente E/OU AUT faltando) via
  `venda_service.motivos_incompleto_venda()` (reusa `_avaliar_status_pagamento`),
  passado por `vendas_detalhe`. Antes a mensagem fixa citava só a soma.
- **Bug do autocomplete de peça** (`data-hora-autocomplete="peca"`): faltava
  `data-hora-target-key="id"` → o hidden recebia a **descrição** e o backend
  (`.isdigit()`) rejeitava com "Selecione uma peça". O mesmo bug existe em
  `pedido_detalhe.html`, `nf_detalhe.html` e nos 2 modais de estoque de peças
  (não corrigidos nesta passada).
- **Coluna Frete** em `vendas_lista.html`; **alertas mais marcantes** (ícone por
  categoria em `hora/base.html` + fundo `--bs-*-bg-subtle` em `_hora.css`, scoped a
  `.hora-module`).

**#4a — Brinde na criação**: `criar_venda_manual(brindes=[{peca_id, qtd}])` cria os
brindes na MESMA transação via `_criar_brinde_flush_only` (helper sem commit/guard,
reusado por `adicionar_brinde`). Vale mesmo se o pedido nascer INCOMPLETO. Seção
"Brindes (opcional)" no form de criação (linhas dinâmicas + autocomplete).

**#5b — Aprovação gerencial de frete e brinde** (estende #28 Fatia 2): a tabela
`hora_aprovacao_desconto` ganhou coluna **`tipo`** (`DESCONTO`/`FRETE`/`BRINDE`,
migration `hora_53`). `aprovacao_desconto_service.gatilhos_aprovacao()` detecta os 3
gatilhos (desconto acima do teto — regra mantida; **frete > 0** e **brinde** sempre
que houver) e `garantir_aprovacao_para_confirmar` cria **1 pendência por tipo**;
`confirmar_venda` bloqueia se houver qualquer pendência. A fila
`/hora/comissao/aprovacoes` ganhou coluna Tipo; o detalhe do pedido mostra aviso de
aprovação pendente. Decisão do dono (Haroldo/gestores, 2026-06-26): canal = tela web
com login (sem token WhatsApp). Testes em `test_aprovacao_desconto_service.py` (frete,
brinde, múltiplos gatilhos) e `test_criar_venda_multi_item.py` (brinde na criação).

**Permissão própria `aprovacoes`** (separada de `comissao` em 2026-06-26): aprovar/
rejeitar/ver a fila usa `aprovacoes/{aprovar,ver}` (não mais `comissao/aprovar`).
`comissao` ficou só com config + relatório. Quem concede: admin marca **Aprovar** na
linha "Aprovações de pedido" em `/hora/permissoes` (`aprovacoes` está em
`MODULOS_HORA` + `MODULOS_COM_APROVAR`). Migration `hora_54` faz o backfill idempotente
de quem já tinha `comissao/aprovar` → `aprovacoes`. O menu "Aprovações" passou a ser
gateado por `aprovacoes/ver` (config/relatório seguem em `comissao/ver`).

**Menu próprio + balão de pendências (2026-06-27):** "Aprovações" ganhou um **item de
topo** na barra do módulo (`hora/base.html`, logo após o Dashboard) com um **badge**
(`bg-danger` pílula) exibindo a contagem de aprovações pendentes — **mantendo também**
o item dentro do dropdown **Cadastros** (decisão do dono: acesso nos dois lugares; o
badge aparece em ambos). O número vem do context processor `_hora_aprovacoes_contador`
(`routes/comissao.py`, `@hora_bp.app_context_processor`, espelha
`_hora_pendencias_contador` de `modelos_unificacao.py`): injeta
`hora_aprovacoes_pendentes_qtd` = `COUNT(HoraAprovacaoDesconto status=PENDENTE)`, mas
**só para quem tem `aprovacoes/ver`** (demais recebem 0 e o item nem aparece). O gate
`show_cadastros` do dropdown segue incluindo `aprovacoes/ver` (inalterado).

---

## 26. Reserva cancelada devolve a moto ao estoque (fix DEVOLVIDA) — 2026-06-26

**Bug:** remover uma moto de um pedido (ou cancelar/descartar o pedido, ou NFe
cancelada via backfill) emitia o evento `DEVOLVIDA`. Como `DEVOLVIDA` está em
`EVENTOS_FORA_ESTOQUE` (estoque_service) e o estado da moto = último evento
(invariante 4), a moto sumia do estoque disponível e **não podia ser revendida**
— apesar de os comentários do código (e o teste `test_remover_item_devolve_chassi`)
afirmarem "volta/libera ao estoque". O teste validava só a emissão do evento, nunca
a disponibilidade — mascarando o bug.

**Causa-raiz:** `DEVOLVIDA` era sobrecarregado para dois sentidos opostos —
"voltou ao estoque" (cancelar reserva) e "saiu de vez" (devolução ao fornecedor/
cliente, descarte de recebimento). O segundo é legítimo fora do estoque; o primeiro
não. Não dava para só mover `DEVOLVIDA` para `EVENTOS_EM_ESTOQUE` (quebraria o
sentido B + a máquina de devolução de venda que depende de `ult == 'DEVOLVIDA'`).

**Correção (decisão do dono: "volta ao status anterior"):** novo helper
`moto_service.devolver_ao_estoque(chassi, ...)` re-emite o **último estado-em-estoque
anterior** à reserva (RECEBIDA/CONFERIDA/TRANSFERIDA/AVARIADA/...), via
`ultimo_evento_em_estoque` (ordenado por MAX(id), mesma derivação do estoque_service),
preservando a loja desse estado. Fallback `RECEBIDA` se não houver histórico (não
ocorre na prática — reservar exige estado em estoque via
`_lock_chassi_e_validar_disponivel`).

**Call-sites trocados** (`registrar_evento(tipo='DEVOLVIDA')` → `devolver_ao_estoque`)
— todos do **sentido A** (cancelamento de reserva de venda):
`venda_service`: `_aplicar_itens` (remover via `salvar_pedido_completo`),
`remover_item_pedido`, `editar_item_pedido` (troca de chassi devolve o antigo),
`cancelar_venda`, `descartar_venda_teste`; `tagplus/backfill_service` (NFe
cancelada/inutilizada). **Não alterados** (sentido B — fora do estoque é correto):
devolução ao fornecedor (`hora_devolucao_fornecedor_item`), devolução do cliente
(`hora_devolucao_venda_item`), descarte de recebimento
(`hora_recebimento_conferencia`), empréstimo (`hora_emprestimo_moto`).

**Passivo PROD:** `scripts/hora/fix_devolvida_reserva_presa.py` (dry-run default,
`--confirmar`, idempotente) restaura motos cujo último evento é `DEVOLVIDA` com
`origem_tabela IN ('hora_venda','hora_venda_item')` — discriminador à prova do
sentido A. Executado em 2026-06-26: **12 motos** restauradas a RECEBIDA (operador
`FIX_DEVOLVIDA_RESERVA_2026_06_26`); verificação pós zerou.

**Testes:** `tests/hora/test_pedido_workflow.py` — 2 novos
(`test_remover_item_volta_disponivel_no_status_anterior`,
`test_cancelar_venda_volta_disponivel_no_status_anterior`, que reproduziam o bug) +
3 atualizados (cancelar/remover/troca de chassi agora verificam `status_atual` ∈
`EVENTOS_EM_ESTOQUE`, não a emissão de DEVOLVIDA). Suíte HORA: 229 verdes.

---

## 28. Perfis de permissão das Lojas HORA (template de permissões) — 2026-06-27

Perfis **exclusivos das Lojas HORA**: um template de permissões reutilizável que
**pré-preenche** as permissões granulares de um usuário ao ser atribuído, mantendo-as
editáveis depois. Atende: criar perfis no módulo, não compartilhá-los nos outros links,
pré-fill, redefinir, accordion na tela de usuários e compatibilidade com os perfis do
restante do sistema.

**Decisão de arquitetura (campo único `Usuario.perfil`):** o perfil HORA NÃO é um campo
novo — reusa o `Usuario.perfil` global (`String(30)`). O slug carrega prefixo `hora_` e
**nunca colide** com os 6 slugs reservados (`administrador/vendedor/gerente_comercial/
financeiro/logistica/portaria`), então um usuário com perfil HORA fica HORA-only (todas as
checagens Nacom `perfil in [...]` / `== 'administrador'` retornam o esperado). O **nome** é
livre (pode haver perfil HORA "Financeiro"); só o **slug** é que não pode repetir — e é
**derivado automaticamente** do nome (o admin nunca digita slug). Mapa de impacto: dos ~40
read-sites de `perfil`, só as 3 `SelectField` auth quebrariam — resolvido com choices
dinâmicas (ver abaixo).

**Tabelas novas (2)** — migration `scripts/migrations/hora_55_perfis.{py,sql}`:
- `hora_perfil` — definição (`slug` UNIQUE, `nome`, `ativo`, `criado_em/por`).
- `hora_perfil_permissao` — o **esqueleto** (1 linha por `(perfil_id, modulo)` × 5 flags),
  espelha `hora_user_permissao`. É só TEMPLATE: a permissão efetiva continua em
  `hora_user_permissao` (o perfil NÃO é consultado em runtime).

**Service** (`app/hora/services/perfil_service.py`):
- `criar_perfil(nome)` — deriva slug `hora_<slugify(nome)>` único (dedup `_2`, `_N`),
  guarda nome duplicado/inválido, cria esqueleto vazio.
- `get_skeleton` / `salvar_skeleton` — matriz módulo×ação do perfil.
- `aplicar_perfil_em_usuario(user_id, slug)` — grava `Usuario.perfil = slug` E **copia** o
  esqueleto → `hora_user_permissao` (reusa `permissao_service.salvar_matriz_completa`).
- `redefinir_permissoes_pelo_perfil(user_id)` — re-aplica o esqueleto do perfil atual.
- `mapa_perfis_por_slug` — `{slug: HoraPerfil}` p/ exibir nome amigável (inclui inativos).

**Rotas** (`app/hora/routes/perfis.py` + extensões em `permissoes.py`):
- CRUD: `GET /hora/permissoes/perfis`, `POST .../novo`, `GET .../<id>`, `POST .../<id>/salvar`,
  `POST .../<id>/ativo` (soft-delete: desativar não mexe em quem já usa).
- Por usuário: `POST /hora/permissoes/<id>/perfil` (aplica + pré-fill) e
  `POST /hora/permissoes/<id>/redefinir`. A aprovação de pendente aceita perfil opcional.
- Gating: `usuarios/ver|criar|editar` (admin sempre passa) — quem tem permissão em
  "Usuários" gerencia perfis e atribui.

**UI**:
- Tela `/hora/permissoes` reescrita como **accordion** (1 painel por usuário, fechado por
  padrão, 1º aberto) — escala com nº de usuários. Matriz movida para o partial reusável
  `app/templates/hora/_matriz_permissoes.html` (mesma matriz na edição do perfil).
- Telas novas `perfis_lista.html` (lista + criar) e `perfil_form.html` (nome + esqueleto).
- Link "Perfis de acesso" no dropdown Cadastros (`hora/base.html`, `usuarios/ver`).

**Compatibilidade (auth)** — `app/auth/routes.py` (`aprovar_usuario`/`editar_usuario`):
`form.perfil.choices` é montado dinamicamente (`_choices_perfil_com_hora`): os 6 do sistema
+ (se o usuário tem perfil HORA) o próprio perfil HORA como opção extra. Assim a tela auth
**exibe** o perfil HORA atual e permite **voltar** a um perfil do sistema sem reset
silencioso — perfis HORA só são GERIDOS no módulo Lojas, nunca o catálogo nos links auth.
`listar_usuarios.html`/`editar_usuario.html` mostram o nome amigável via `perfis_por_slug`.

**Testes**: `tests/hora/test_perfil.py` (12 — slug/dedup/guardas/esqueleto/aplicar/redefinir)
+ `tests/hora/test_perfil_rotas.py` (6 — render accordion/partial/perfil_form/auth + fluxo).
Suíte HORA: 249 verdes.

---

## 29. Seção Gerencial — dashboards + relatórios — 2026-06-27

Nova seção **Gerencial** (dropdown próprio no menu do módulo) com 4 dashboards
inteligentes para gerência/diretoria + área de geração/construção de relatórios.
Fonte exclusiva `hora_*`. Spec: `docs/superpowers/specs/2026-06-27-hora-gerencial-design.md`.
Plano: `docs/superpowers/plans/2026-06-27-hora-gerencial.md`. **Sem migration.**

**Permissões (2 slugs novos em `MODULOS_HORA` + `MODULOS_SO_VER`, sem DDL):**
- `gerencial` — gateia os 4 dashboards (Executivo / Comercial / Estoque / Suprimento).
- `gerencial_relatorios` — gateia a área de relatórios (galeria + builder + export),
  **separada** (decisão do dono): pode-se dar dashboards a um gerente sem dar os relatórios.
- **Escopo por loja** aplicado no WHERE de cada query via `lojas_permitidas_ids()` →
  `gerencial/filtros.lojas_efetivas` (não só no menu). Bucket `loja_id IS NULL`
  (CNPJ desconhecido) só aparece para acesso irrestrito (admin / sem loja).
  **Atenção (admin):** conceder `gerencial`/`gerencial_relatorios` a um usuário
  **não-admin SEM `loja_hora_id`** o trata como IRRESTRITO (vê finanças de TODA a
  rede) — intencional para diretoria; ao conceder a um gerente de loja, garanta
  `loja_hora_id` preenchido para escopar.

**Arquitetura** (`app/hora/services/gerencial/` + `routes/gerencial.py` +
`templates/hora/gerencial/`):
- `filtros.py` — `parse_filtros` (período/loja/granularidade) + `lojas_efetivas`
  (interseção filtro×escopo, PURO/testável).
- `kpi_service.py` — Executivo: receita (FATURADO), **margem por chassi**
  (`hora_venda_item.preco_final − hora_nf_entrada_item.preco_real`, `desconsiderado=FALSE`,
  − brindes) com **transparência de cobertura** (% das motos com custo real), ticket,
  unidades, ranking de lojas, tendência (`date_trunc`), desconto.
- `comercial_kpi_service.py` — conversão de funil (só `origem_criacao='MANUAL'`),
  vendas/comissão por vendedor (reusa `comissao_service.calcular_comissao_venda` por
  `faturado_em`, com escopo), desconto médio, mix de pagamento, aprovações pendentes
  por tipo, peças, brindes.
- `estoque_kpi_service.py` — estado atual via **window function**
  `ROW_NUMBER() OVER (PARTITION BY chassi ORDER BY id DESC)` (MAX(id), consistente com
  `estoque_service`); estoque loja>modelo>cor, aging (faixas 0-30/31-60/61-90/90+),
  giro (RECEBIDA→venda), reservadas/em-trânsito.
- `suprimento_kpi_service.py` — lead time NF→recebimento, taxa de divergência
  (`substituida=FALSE`), custo médio de entrada (`desconsiderado=FALSE`), desvio real
  vs esperado (via pedido).
- `relatorio_catalogo.py` + `relatorio_service.py` — **builder curado**: whitelist de
  dimensões (loja/vendedor/modelo/período) × métricas (unidades/receita/desconto/margem);
  `validar_selecao` rejeita slug fora do catálogo (**nunca SQL livre**); galeria de
  relatórios pré-definidos + export xlsx (openpyxl)/csv. Rotas `gerencial_relatorios`
  + `gerencial_relatorios_export`.

**Guard-rails:** anti-N+1 (toda métrica = agregação SQL única); `status='FATURADO'`
para receita; `MAX(id)` (não `MAX(timestamp)`) para estado; filtros silenciosos
explicitados; isolamento de módulo (zero cross-join). **Comissão e margem refletem a
config/cobertura ATUAL** — rotulado nas telas.

**UI:** Bootstrap 5.3 + tokens `--bs-*` (light/dark automático) + Chart.js CDN; CSS
`app/static/css/modules/_hora_gerencial.css` (prefixo `ger-*`). Telas via skill
`frontend-design`.

**Testes:** `tests/hora/test_gerencial_{permissao,filtros,kpis,estoque,relatorios}.py`
(~50, incluindo gate de permissão separada e smokes autenticados via fixture
`client_admin`). Suíte HORA verde. **Não-objetivos v2:** PDF executivo, agendamento de
envio, builder multi-dimensão/SQL livre, frete de compra/custo de peça na margem,
comissão persistida.

---

## 30. Brinde — gerenciar em INCOMPLETO, exibir no preview e CORTESIA na NF — 2026-06-27

Três ajustes no brinde de venda (`HoraVendaBrinde`, #36) a partir de feedback real
("o brinde não aparece / não consigo adicionar"). Sem migration. A causa de cada
sintoma foi confirmada por reprodução (testes de render), não por inferência.

**#1 — Gerenciar brinde em INCOMPLETO além de COTAÇÃO.** O sintoma "não aparece" era
o **form de adicionar/remover** travado em COTAÇÃO: como pedido nasce INCOMPLETO
(falta pagamento/AUT), o vendedor não tinha onde adicionar. A *tabela* de brindes já
exibia em todos os status (sem regressão aí). Mudança alinhada à edição de itens
(§23 F1):
- `venda_service`: novo guard `_exigir_cotacao_ou_incompleto` em `adicionar_brinde` /
  `remover_brinde` (aceita INCOMPLETO+COTAÇÃO). **CONFIRMADO/FATURADO continuam
  bloqueados de propósito** — o brinde dispara aprovação gerencial avaliada na
  confirmação (§27 #5b); mexer depois furaria o gate.
- `pedido_venda_novo.html`: os 2 gates do brinde (remover/adicionar) passaram de
  `is_cotacao and pode_editar` para `(is_cotacao or is_incompleto) and pode_editar`
  (expressão completa, não `itens_editaveis` — esse `set` é condicional/aninhado e
  pode não estar no escopo da seção de brindes).

**#2 — Brinde no cálculo da margem do preview da NF.** `montar_preview` **já** subtraía
`custo_brindes_total` do líquido, mas `venda_preview_nfe.html` só mostrava
`Venda − Frete − Custo Moto = Líquido` — a conta não fechava e o custo do brinde
"sumia". Adicionada a coluna **"(-) Custo Brindes"** na seção de margem (layout
`col-6 col-md` p/ caber 5 colunas), a fórmula atualizada e um **detalhamento** dos
brindes (peça · qtd · custo) abaixo. Bug de exibição, não de cálculo.

**#3 — CORTESIA nas informações complementares.** `payload_builder._montar_inf_contribuinte`
ganhou, no fim do conteúdo fiscal (logo **antes** do rastreio gerencial interno
`Venda # | Loja | Vendedor`), a linha **`CORTESIA: <peça_1>, <peça_2>...`** (qtd ≠ 1
prefixa `Nx`, ex.: `2x RETROVISOR`). Só aparece quando há brinde. **Exceção (§35):**
a peça de **revisão** sai da linha de peças e ganha bloco institucional próprio.

**#4 — CAUSA-RAIZ do "brinde não aparece quando adiciono na criação"** (achada depois,
por reprodução). O backend grava o brinde na criação (teste de POST prova); o sumiço
era **permissão**: `GET /hora/autocomplete/peca` exigia **só** `pecas_estoque/ver`. O
vendedor que só tem `vendas/*` recebia **302** → o dropdown de peça não abria → ele não
selecionava a peça → o hidden `brinde_peca_id` ia **vazio** → a rota
`tagplus_pedido_venda_criar` **descartava a linha em silêncio** (`if not pid.isdigit()`).
Fix: `autocomplete_peca` passou para
`require_hora_perm_any(('pecas_estoque','ver'), ('vendas','criar'), ('vendas','editar'))`
— o catálogo de peças é read-only/global; quem cria/edita venda pode buscar peça (item
ou brinde). **Gotcha de teste:** admin enxerga tudo, então só reproduz com usuário
não-admin com matriz granular. (Risco latente NÃO corrigido: a rota ainda descarta linha
de brinde sem `peca_id` válido sem feedback — defesa em profundidade fica p/ depois.)

**Testes:** `tests/hora/test_brinde_service.py` (+2: add/remove em INCOMPLETO),
`test_brinde_inf_contribuinte.py` (3: CORTESIA, qtd>1, ausência sem brinde),
`test_brinde_preview_render.py` (2: render do preview), `test_brinde_detalhe_render.py`
(2: form aparece em INCOMPLETO, some em CONFIRMADO; tabela em ambos),
`test_brinde_criacao_post.py` (1: POST end-to-end grava brinde),
`test_brinde_autocomplete_perm.py` (2: vendedor acessa autocomplete de peça; sem perm
segue bloqueado). Suíte HORA: 326 verdes.

---

## 31. Recebimento — dropdown de modelos canônicos + anti-duplicação de grafia de cor — 2026-06-27

Dois ajustes de qualidade de dados no **wizard de recebimento**
(`/hora/recebimentos/<id>/wizard`). Sem migration.

**A — Dropdown de modelo só com canônicos/ativos.** `recebimentos_wizard`
(`routes/recebimentos.py`) carregava `HoraModelo.query.order_by(...).all()` — **sem**
filtrar `merged_em_id IS NULL` nem `ativo`, então o `<select id="select-modelo">` da
conferência listava também os modelos absorvidos por merge (§12) e os inativos. Trocado
por `cadastro_service.listar_modelos()` (a listagem canônica do módulo, mesma de
cadastro/vendas).

**B — Anti-duplicação de grafia de cor (prevenção leve, sem catálogo).** Cor segue
**texto livre** (decisão 2026-04-23 mantida — sem tabela própria). O passo C antes só
oferecia as cores **da NF/pedido daquele recebimento** e o modal "nova cor" criava
**texto 100% livre**, sem comparar com nada → nascem BRANCA/BRANCO/BRANCCA/BRANA, que
viram `HoraMoto.cor` definitiva (`recebimento_service.py:1756`) e ainda geram
divergência `COR_DIFERENTE` falsa.
- Novo `app/hora/services/cor_service.py` (lógica pura, sem dependência nova):
  `normalizar_cor` (upper + colapsa espaços, preserva acento), `listar_cores_existentes()`
  (DISTINCT global de `hora_moto.cor` + `hora_nf_entrada_item.cor_texto_original` +
  `hora_pedido_item.cor`, normalizado/dedup/ordenado) e `sugerir_similares(nome)`
  (`difflib.SequenceMatcher` ≥ 0.8 sobre chave sem acento/pontuação; exclui idênticos).
- Endpoint `GET /hora/autocomplete/cor` (`routes/autocomplete.py`,
  `require_hora_perm_any` recebimentos ver/criar/editar) → `{exato, similares, cores}`.
- `recebimentos_wizard` passa `cores_sugeridas` (desta NF/pedido, no topo) **+**
  `cores_existentes` (todas as grafias da base) — o `<select>` ganha 2 `<optgroup>`, então
  o conferente reaproveita em vez de redigitar.
- Modal "nova cor" (`recebimento_wizard.html`): ao salvar, consulta o endpoint; se houver
  similar e não for idêntica, mostra aviso **NÃO-bloqueante** ("Usar BRANCA" / "Criar
  'BRANCCA' mesmo assim") — preserva pares legítimos (PRETA/PRATA) deixando a decisão ao
  operador.

**Outro vetor NÃO coberto (reportado):** o **pedido de compra** (`pedido_detalhe.html`
inputs livres de cor → `pedidos.py:1250,1314`) é a outra porta de entrada manual de cor,
sem proteção. `cor_service` é reutilizável lá (mesma mecânica) — fica como follow-up.

**Testes:** `tests/hora/test_cor_service.py` (13 — normalização, similaridade incl.
erro de digitação/gênero/acento/idêntico/par-próximo, `listar_cores_existentes` com DB e
contrato do endpoint). Validação: 23 verdes (cor + recebimento), `node --check` no JS
renderizado, Jinja compila.

---

## 32. Recebimento — autocomplete de NF por permissão de recebimento + guarda anti-duplicado — 2026-06-27

Dois fixes no fluxo de recebimento (commits separados na main). Sem migration.

**A — Autocomplete de NF aceita operador de recebimento.** O endpoint
`GET /hora/autocomplete/nf-entrada` (`routes/autocomplete.py`) exigia **só** `nfs/ver`.
Um operador de recebimento (vendedor com `recebimentos/criar` mas **sem** `nfs/ver`,
ex.: Isabela) recebia **302** e o autocomplete da NF em `/hora/recebimentos/novo`
**falhava em silêncio** — não dava para selecionar a NF. Trocado para
`require_hora_perm_any(('nfs','ver'), ('recebimentos','criar'))` — **mesmo padrão/causa-raiz
do autocomplete de peça/brinde** (§30 #4). Provado em PROD (user 84).

**B — Guarda anti-recebimento-duplicado.** Causa-raiz: a moto `92WMCX113SM000988` foi
conferida em **dois** recebimentos (120 e 121) sem nenhum aviso — `registrar_conferencia_cega`
não checava se o chassi já fora recebido em outro recebimento (o wizard manual **não tinha
trava nenhuma**; a guarda `ESTADOS_JA_FORA` do automático trata o caso oposto, "já saiu").
- **Regra de "já recebido":** existe `HoraRecebimentoConferencia` ativa (`substituida=False`)
  para o chassi em **outro** `recebimento_id`. É à prova de falso-positivo porque **toda
  re-entrada legítima** (transferência `confirmar_item_destino`, devolução cancelada,
  cancelamento de reserva) passa por `registrar_evento` — **fora** da conferência — e a
  reconferência/re-scan do próprio recebimento cai no ramo `else` (`is_new=False`).
- **3 pontos** (`recebimento_service.py`): **bloqueio** no ramo `is_new` de
  `registrar_conferencia_cega` (`RecebimentoDuplicadoError(ValueError)` → a rota já devolve
  400); **aviso** em `validar_chassi_contra_recebimento` (`ja_recebido_outro` + mensagem);
  **pré-filtro** em `criar_recebimento_automatico_da_nf` (pula via `chassis_pulados_ja_recebido`,
  não aborta o lote). Cobre os 3 fluxos (manual / automático / sem-NF) pelo mesmo choke.
- **Avaria não passa por recebimento:** a mensagem da trava redireciona para o módulo
  **Avarias** (`avaria_service.registrar_avaria` — não tira do estoque, emite `AVARIADA`).
- **Testes:** `tests/hora/test_recebimento_anti_duplicata.py` (5 — bloqueia cross-rec, permite
  reconferência do mesmo rec, 1º recebimento, aviso, automático pula sem abortar).

---

## 33. Loja real da venda vs matriz (emitente fiscal) — integridade — 2026-06-27

**Problema (provado em produção):** toda NFe sai com o CNPJ da matriz (§7), e o resolver
`_resolver_loja_por_cnpj` resolvia a loja da venda pelo CNPJ do emitente → caía SEMPRE na
matriz (MORAH, `is_matriz`). 261 vendas FATURADAS (≈ R$ 2,84 mi) ficaram atribuídas à
matriz, inflando rankings/KPIs/comissão e subnotificando as lojas reais. A loja real vem
do `tagplus_departamento` (TagPlus) ou do SELECT do operador (fluxo manual, sempre correto).

**Flag `HoraLoja.is_matriz`** (migration `hora_57`): marca a matriz (CNPJ 62634044000120).
Permanece `ativa` (default de NF de ENTRADA + alvo do resolver de divergência), mas:
- NUNCA é gravada como `hora_venda.loja_id`;
- EXCLUÍDA das superfícies de VENDA: SELECT do pedido (`cadastro_service.listar_lojas_para_pedido_venda`),
  dropdowns gerenciais (`gerencial._lojas_disponiveis`), contagem "Lojas ativas" (`dashboard`),
  filtro/troca de loja na listagem (`vendas._lojas_ativas_permitidas` + listagem).

**Prevenção (origem)** — `venda_service._resolver_loja_real_venda(cnpj_emitente, tagplus_departamento)`:
departamento → CNPJ-se-não-matriz → `None`. Usado por `importar_nf_saida_pdf` (DANFE) e
`backfill_service.importar_nfe_da_api`. Quando resolve `None`: `loja_id=NULL` + divergência
`CNPJ_DESCONHECIDO` ("loja a definir"); o evento `VENDIDA` também sai sem a matriz.

**Auto-cura do passivo** — `pedido_backfill_service._aplicar_pedido_em_venda` aplica a loja
via `definir_loja_venda` assim que o departamento mapeia uma loja (corrige header + re-emite
`VENDIDA`). O botão `/hora/tagplus/departamento-map` → **Aplicar** segue para correção em massa
(só header; para header+evento use o script abaixo / `definir_loja_venda`).

**CFOP** — `PayloadBuilder._uf_emitente` deriva a UF do emitente da **matriz** (`is_matriz=True`),
não de `venda.loja` (que pode ser `NULL` pós-saneamento). Evita flip de CFOP e não quebra com
loja indefinida.

**Correção do passivo existente** — `scripts/hora/fix_loja_matriz_por_departamento.py`
(dry-run default; usa `definir_loja_venda`; guarda de UF). 109 vendas recuperáveis via
departamento; 151 sem departamento → recuperáveis via `backfill-pedidos-legados` (re-fetch
pela chave-44 grava `tagplus_departamento`) e então a auto-cura/Aplicar resolve a loja.

**Testes:** `test_loja_real_venda_resolver`, `test_import_nf_saida_loja_matriz`,
`test_pedido_backfill_aplica_loja`, `test_uf_emitente_matriz`, `test_frente_c_exclui_matriz`.

---

## 34. Pedido de Venda — vendedor ao lado da loja + campo Telefone Lead — 2026-06-28

Dois ajustes na tela de Pedido de Venda (`pedido_venda_novo.html`). **Migration: hora_58.**

**A — Vendedor ao lado da "Loja física da venda" (modo edição).** O bloco da loja
é um `<form>` próprio (`vendas_definir_loja`); o vendedor pertence ao
`form-pedido-venda` (`vendas_salvar_pedido`). Para exibi-los lado a lado **sem**
aninhar forms nem submeter o vendedor no "Trocar loja", o `<select name="vendedor">`
usa o atributo HTML **`form="form-pedido-venda"`** (associação por id, independente da
posição no DOM). O bloco virou um **card de 2 colunas** visível sempre que
`not is_cancelado` (antes só com `lojas_ativas and pode_editar`): col-8 = loja (form
de trocar quando editável, **OU** input read-only) + col-4 = vendedor (sempre visível,
`disabled` quando `not permite_editar_vendedor`). Isso **não regride** a visibilidade
do vendedor em telas read-only (faturado / sem permissão de editar). O vendedor saiu da
seção Cliente/Destinatário. **Sem mudança de backend** (o `vendedor` já era lido pelo
header em `vendas_salvar_pedido` → `_aplicar_header`).

**B — Campo "Telefone Lead"** (`hora_venda.telefone_lead VARCHAR(20)`, migration
`hora_58`): telefone do **lead/contato que originou a venda**, distinto do
`telefone_cliente` (destinatário fiscal). **Registro/exibição apenas — NÃO entra no
payload da NFe** (mesmo critério de `inscricao_estadual`, §24). Aparece **abaixo do
Telefone** do cliente nos 2 modos (criação e edição). Editável em INCOMPLETO/COTAÇÃO e
CONFIRMADO (mesmo gate `ro_oper` do `telefone_cliente`; está em `_CAMPOS_COTACAO_FULL`
**e** no conjunto CONFIRMADO de `_CAMPOS_EDITAVEIS_HEADER`). Lido/gravado por
`criar_venda_manual`, `_aplicar_header` e as rotas `tagplus_pedido_venda_criar`
(`name="telefone_lead"`) / `vendas_salvar_pedido` (header dict). Migration dual
`scripts/migrations/hora_58_venda_telefone_lead.{py,sql}` (idempotente, ADD COLUMN IF
NOT EXISTS) **aplicada em local + PROD**.

**Validação:** suíte de venda HORA (42) + render dos 2 modos (criação e edição)
verde; Jinja compila; coluna confirmada em PROD (`character varying(20)`, nullable).

---

## 35. CORTESIA de revisão — texto institucional na NF — 2026-06-28

Estende a §30 #3. Quando a venda tem a **peça de revisão** como brinde, a NF-e
exibe, em `inf_contribuinte`, um **bloco institucional próprio** em vez de listar a
peça na linha `CORTESIA: <peças>`. **Sem migration.**

**Texto fixo** (`TEXTO_CORTESIA_REVISAO` em `payload_builder.py` — fonte: dono do
módulo): "Cortesia: Revisão gratuita de 3 meses, mediante agendamento prévio
(telefônico ou WhatsApp da loja) e conforme disponibilidade da agenda técnica da loja
em que foi efetuada a compra/retirada. Será válida em apenas uma das lojas." Os
marcadores markdown do texto original (`*..*` / `_.._`) foram **removidos de
propósito**: `infCpl` da NFe é texto plano e os símbolos vazariam literais na DANFE.

**Detecção** (`_eh_peca_revisao`): `codigo_interno` normalizado (upper + sem acento)
`== 'REVISAO'` — **não** por id (211 em PROD difere de local/dev) nem por descrição
(é `SE - REVISÃO`). `codigo_interno` é UNIQUE e estável entre ambientes.

**Bloco 3 de `_montar_inf_contribuinte`:** separa os brindes em revisão vs demais. A
revisão **não entra** na linha `CORTESIA: <peças>` (ganha o bloco próprio, evitando
duplicar/poluir a leitura fiscal); as demais peças seguem na linha `CORTESIA:` como
antes. Venda com revisão + peça física exibe **as duas coisas**.

**Testes:** `tests/hora/test_brinde_inf_contribuinte.py` (+3: texto institucional,
detecção por código sem acento, revisão + peça física). Suíte de brinde/payload (37)
verde.

---

## Referências

- **Contrato de design**: `docs/hora/INVARIANTES.md`
- **Análise de primeiros princípios**: comando `/fp-lojas-motochefe` (`.claude/commands/fp-lojas-motochefe.md`)
- **Precedente de chassi como PK** (ver, não copiar): `app/motochefe/models/produto.py:45`
- **Parsers reusáveis**: `app/carvia/services/parsers/danfe_pdf_parser.py`, `app/carvia/services/pricing/moto_recognition_service.py`
- **Regra de migrations duais**: `/home/rafaelnascimento/.claude/CLAUDE.md` seção "MIGRATIONS"
- **JSON sanitization** (se usarmos JSONB para foto/metadados): `/home/rafaelnascimento/.claude/CLAUDE.md` seção "JSON SANITIZATION"
