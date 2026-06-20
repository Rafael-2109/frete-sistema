<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Cotacao — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Cotacao — motor de cotacao de frete PRE-embarque (industria Nacom embarca). Fluxo: selecionar pedidos → calcular opcoes (DIRETA/FRACIONADA) → **Fechar Frete** cria Embarque + dispara frete automatico.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Blueprint e Rotas](#blueprint-e-rotas)
- [Regras Criticas](#regras-criticas)
  - [R1: Estado vive 100% na sessao Flask](#r1-estado-vive-100-na-sessao-flask)
  - [R2: "pedidos" sao separacao_lote_id (nome enganoso)](#r2-pedidos-sao-separacao_lote_id-nome-enganoso)
  - [R3: Pedido e VIEW — nunca gravar; escrita vai para Separacao](#r3-pedido-e-view-nunca-gravar-escrita-vai-para-separacao)
  - [R4: Status COTADO e derivado por event listener — nunca setar na rota](#r4-status-cotado-e-derivado-por-event-listener-nunca-setar-na-rota)
  - [R5: fechar_frete e o unico ponto de criacao de Embarque — afeta 5 modulos](#r5-fechar_frete-e-o-unico-ponto-de-criacao-de-embarque-afeta-5-modulos)
  - [R6: Campos de tabela de frete sao CONGELADOS no fechamento](#r6-campos-de-tabela-de-frete-sao-congelados-no-fechamento)
  - [R7: tabela_selecionada vem do payload; totais vem do banco](#r7-tabela_selecionada-vem-do-payload-totais-vem-do-banco)
  - [R8: fechar_frete tem 3 ramos (CarVia/Op.Assai/Nacom)](#r8-fechar_frete-tem-3-ramos-carviaopassainacom)
  - [R9: 3 modulos "cotacao" distintos — nao confundir](#r9-3-modulos-cotacao-distintos-nao-confundir)
- [Models](#models)
- [Fluxo Principal (iniciar → tela → fechar)](#fluxo-principal-iniciar-tela-fechar)
- [Otimizador e Redespacho](#otimizador-e-redespacho)
- [Gotchas](#gotchas)
- [Interdependencias](#interdependencias)
- [Acesso (sem item de menu)](#acesso-sem-item-de-menu)
- [Skills Relacionadas](#skills-relacionadas)
- [Referencias](#referencias)

## Contexto

4 arquivos Python (~4.5K LOC — `routes.py` 4.351), 7 templates. Motor de cotacao de frete **pre-embarque** da industria Nacom: o usuario seleciona pedidos da carteira, o modulo calcula as opcoes de frete por transportadora/tabela, e ao "Fechar Frete" cria o `Embarque` + `EmbarqueItem`, propaga `cotacao_id` para a `Separacao` (→ status COTADO) e ja tenta disparar o frete automatico.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{cotacoes,cotacao_itens,embarques,embarque_itens,separacao,pedidos}.json`
> Frete REAL (pos-embarque: CTe → Lancamento Odoo → pagamento): `app/fretes/CLAUDE.md`
> Motor de calculo: `app/utils/{frete_simulador,calculadora_frete,tabela_frete_manager}.py`
> Cotacao teorica via skill: `cotando-frete`

---

## Estrutura

```
app/cotacao/
  ├── __init__.py        # VAZIO
  ├── models.py          #  118 LOC — Cotacao, CotacaoItem
  ├── forms.py           #   10 LOC — CotarFreteForm (so para token CSRF)
  └── routes.py          # 4.351 LOC — cotacao_bp (13 rotas) + helpers de calculo
```

**Templates** (`app/templates/cotacao/`, 7): `cotacao.html` (tela principal), `otimizador.html`, `redespachar.html`, `redespachar_sao_paulo.html`, `redespachar_sao_bernardo.html`, `resumo_frete.html`, `visualizar.html` (**ORFAO** — ver G7).
**Sem JS/CSS dedicado** — Bootstrap + tokens do layout base. **Sem campos listados aqui** (campos sao SOT nos schemas JSON).

---

## Blueprint e Rotas

Blueprint `cotacao` (`url_prefix=/cotacao`, `routes.py:40`), registrado em `app/__init__.py:940` (import) + `:1005` (register). Todas as rotas sao `@login_required` (sem decorator de perfil).

| Rota | Funcao | Papel |
|------|--------|-------|
| `POST /iniciar` | `iniciar_cotacao` | ENTRADA — recebe `separacao_lote_ids`, grava na sessao, redireciona |
| `GET\|POST /tela` | `tela_cotacao` | Calcula opcoes DIRETA/FRACIONADA e renderiza a tela de selecao |
| `POST /fechar_frete` | `fechar_frete` | **HANDOFF** — cria Cotacao+Embarque+Itens, dispara frete (ver R5) |
| `POST /fechar_frete_grupo` | `fechar_frete_grupo` | Variante por GRUPO (multi-CNPJ, FRACIONADA) com advisory lock |
| `POST /incluir_em_embarque` | `incluir_em_embarque` | Anexa pedidos da sessao a um Embarque **existente** |
| `POST /incluir_pedido` / `/excluir_pedido` | — | Manipula a lista de lotes na sessao |
| `POST /verificar_nf_cd` | `verificar_nf_cd` | Pre-checagem AJAX bidirecional NF-no-CD (ver G8) |
| `GET /otimizar` | `otimizar` | Tela what-if conservadora (adicionar/remover pedidos) |
| `GET /resumo/<cotacao_id>` | `resumo_frete` | Resumo de cotacao JA fechada (destino do redirect pos-fechamento) |
| `GET /redespachar[_sao_paulo\|_sao_bernardo]` | `redespachar*` | Recota com destino forcado para hub SP (ver Otimizador e Redespacho) |

---

## Regras Criticas

### R1: Estado vive 100% na sessao Flask
Nao ha cache/Redis. Todo o fluxo entre telas passa por `session`: `cotacao_lotes`, `cotacao_pedidos`, `cotacao_pedidos_data`, `resultados`, `alterando_embarque`, `redespacho_ativo`. Quase toda rota le `session.get('cotacao_pedidos')`; se vazio → `redirect(pedidos.lista_pedidos)`. A limpeza dessas chaves e **manual e espalhada** (`iniciar_cotacao`, `tela_cotacao`, `incluir_em_embarque`). Cookie de sessao Flask tem limite ~4KB — listas grandes de lote/resultados podem estourar silenciosamente.

### R2: "pedidos" sao separacao_lote_id (nome enganoso)
`session['cotacao_lotes']` e `session['cotacao_pedidos']` guardam a **MESMA** lista de `separacao_lote_id` (strings) — `cotacao_pedidos` existe so por retrocompatibilidade. NAO sao IDs de pedido. `iniciar_cotacao` aceita `separacao_lote_ids` (novo) OU `pedido_ids` (fallback que resolve `num_pedido` → lote). No payload de `fechar_frete`, o campo `id` de cada item tambem carrega o `separacao_lote_id`.

### R3: Pedido e VIEW — nunca gravar; escrita vai para Separacao
`Pedido` e uma VIEW agregada sobre `Separacao` (somente leitura). Toda escrita de cotacao/status vai para `Separacao` chamando o classmethod `atualizar_cotacao(lote, cotacao_id, nf_cd=...)` (`app/separacao/models.py:194`). O identificador primario do fluxo e `separacao_lote_id`, NUNCA `pedido.id`/`num_pedido`. As NFs do `EmbarqueItem` Nacom tambem vem de `Separacao.numero_nf`, nao do Pedido.

### R4: Status COTADO e derivado por event listener — nunca setar na rota
`fechar_frete` so seta `cotacao_id` na `Separacao`. O `status='COTADO'` e derivado pelo event listener `before_insert/before_update` de `Separacao` (`atualizar_status_automatico`, `app/separacao/models.py:263`, REGRA 5) e pelo `Pedido.status_calculado`. NUNCA setar status manualmente no fechamento. **Atencao**: esse `atualizar_cotacao(...)` faz `commit()` interno e e chamado DUAS vezes no `fechar_frete` (antes e depois de criar os itens) → o request tem multiplos commits parciais, nao e uma transacao atomica unica.

### R5: fechar_frete e o unico ponto de criacao de Embarque — afeta 5 modulos
`fechar_frete` cria `Cotacao(status='Fechada')` + `Embarque(status='ativo', cotacao_id=...)` + `EmbarqueItem`(s), e em seguida dispara efeitos colaterais cross-modulo via **lazy import** (todos sob try/except que so logam):
- `embarques.routes.apagar_fretes_sem_cte_embarque` (ao alterar embarque)
- `fretes.routes.{verificar_requisitos_para_lancamento_frete, lancar_frete_automatico}` — tenta lancar o Frete por CNPJ
- `carvia...embarque_carvia_service` (espelhamento CarVia + auto-expandir provisorios)
- `motos_assai...separacao_mirror_service` (espelhamento Op.Assai)
- `rastreamento...EntregaRastreadaService` (so DIRETA)

Mexer no fechamento impacta esses 5 modulos. As variantes `fechar_frete_grupo` e `incluir_em_embarque` replicam parte dessa logica — ao alterar uma, revisar as TRES.

### R6: Campos de tabela de frete sao CONGELADOS no fechamento
Os ~30 campos da `TabelaFrete` (`valor_kg`, `percentual_gris`, `icms`, `pedagio_por_100kg`, `gris_minimo`, `adv_minimo`, `icms_proprio`, ...) sao COPIADOS para `Cotacao`/`CotacaoItem` e `Embarque`/`EmbarqueItem` via `TabelaFreteManager.atribuir_campos_objeto`. E um **snapshot**: alterar a `TabelaFrete` original depois NAO reflete na cotacao fechada. Recalcular o frete de uma cotacao antiga deve usar os campos do PROPRIO registro, nunca re-buscar a `TabelaFrete`. **DIRETA grava no `Embarque`; FRACIONADA grava em cada `EmbarqueItem`.** `icms_destino` vem de `localidades` (Cidade), nao da tabela de frete.

### R7: tabela_selecionada vem do payload; totais vem do banco
Os dados da tabela gravados no embarque/item vem do **payload do frontend** (`tabela_selecionada`) — `session['resultados']` so serve para detectar/logar divergencia. Sem `tabela_selecionada.nome_tabela` → erro 400. Ja `valor_mercadorias`/`peso_total`/`pallets` sao **recalculados do banco** (batch `Pedido.query.filter(separacao_lote_id.in_(...))`); o frontend e so fallback. DIRETA so e oferecida se todos os pedidos forem do **mesmo UF normalizado** (`LocalizacaoService.normalizar_uf_com_regras`, nao basta `cod_uf` cru).

### R8: fechar_frete tem 3 ramos (CarVia/Op.Assai/Nacom)
O loop de itens bifurca pelo prefixo do `id`/lote: `CARVIA-`/`CARVIA-PED-` (CarVia, entra como `provisorio=True`, expande pos-commit por NF), `ASSAI-SEP-` (Op.Assai, espelha Motos Assai), e o resto (Nacom). O disparo de frete Nacom EXCLUI itens CarVia (`carvia_cotacao_id is None` + skip lote `CARVIA-`). `fechar_frete` NAO e so Nacom — qualquer mudanca deve considerar os 3 dominios.

### R9: 3 modulos "cotacao" distintos — nao confundir
- **`app/cotacao`** (este) — `cotacao_bp` `/cotacao`, cotacao industrial Nacom automatica.
- **`app/pedidos/routes/cotacao_routes.py`** — `cotacao_manual`/`processar_cotacao_manual` (blueprint `pedidos`): caminho MANUAL/FOB que cria Embarque direto SEM passar por `cotacao_bp`.
- **`app/carvia/routes/cotacao_v2_routes.py`** — cotacao v2 do CarVia.

---

## Models

> Campos completos: `.claude/skills/consultando-sql/schemas/tables/{cotacoes,cotacao_itens}.json`

| Model | Tabela | Gotcha principal |
|-------|--------|------------------|
| `Cotacao` | `cotacoes` | Cabecalho de UMA transportadora. `status` default `'Em Aberto'`, mas o fechamento grava `'Fechada'` (NAO confundir com o `'COTADO'` da Separacao). `tipo_carga` `'DIRETA'`/`'FRACIONADA'`. ~24 colunas de tabela de frete inline = snapshot congelado (R6). `itens` com `cascade all,delete-orphan` |
| `CotacaoItem` | `cotacao_itens` | **`separacao_lote_id`** = campo principal (String, indexed, nullable). `pedido_id_old` = backup legado **SEM FK** (nao usar para join). SEM relationship ORM com Pedido (virou VIEW). As properties `.pedido` e `.separacoes` rodam query a cada acesso (lazy import; risco N+1; `.pedido` pode ser `None`, `.separacoes` pode ser `[]`) |

---

## Fluxo Principal (iniciar → tela → fechar)

1. **`iniciar_cotacao`** — POST recebe `separacao_lote_ids`; grava `session['cotacao_lotes']`/`['cotacao_pedidos']`; limpa `alterando_embarque` orfa; redireciona para `tela_cotacao`.
2. **`tela_cotacao`** — carrega `Pedido` (VIEW) pelos lotes; normaliza UF; calcula opcoes via `frete_simulador.calcular_frete_por_cnpj` (motor) e salva `session['resultados']`. DIRETA: ordena por `valor_liquido/peso`. FRACIONADA: por CNPJ escolhe a menor `R$/kg`, reagrupa por transportadora.
3. **`fechar_frete`** — re-busca totais do banco; cria `Cotacao('Fechada')` + `Embarque('ativo')` + `EmbarqueItem`(s) (3 ramos R8); grava tabela congelada (R6); chama `atualizar_cotacao()` da Separacao → COTADO (R4); dispara frete automatico (R5); redireciona para `resumo_frete`.

> **Modo `alterando_embarque`**: `?alterando_embarque=<id>` em `/tela` cria `session['alterando_embarque']`; `fechar_frete` entao ALTERA a cotacao do embarque existente (cria nova Cotacao, troca `embarque.cotacao_id`, DELETA a antiga, recria fretes). Bloqueia se o embarque ja tem `data_embarque`. Inconsistencia querystring×sessao → redirect para `embarques.visualizar_embarque`.

---

## Otimizador e Redespacho

- **Otimizador** (`/otimizar`): tela "what-if" que, para a opcao ja escolhida, calcula o impacto no `R$/kg` de **adicionar/remover** pedidos do mesmo `UF`+`sub_rota`. Deliberadamente **conservador**: usa a tabela de MAIOR valor (pior cenario) e so sugere mudanca se reduzir `> R$0,01/kg` mesmo nesse pior caso. Aborta se houver mais de 1 UF ou sub_rota. Exige `session['resultados']` + `indice_original`.
- **Redespacho** (`/redespachar`=Guarulhos, `/redespachar_sao_paulo`, `/redespachar_sao_bernardo`): recota os MESMOS pedidos fingindo entrega num hub de transbordo de SP. Cria **copias in-memory** do `Pedido` (`cod_uf='SP'`, cidade=hub, `rota='CIF'`) — o **DB nao e tocado** (objetos transientes). As 3 rotas sao ~250 linhas quase identicas (copy-paste); um fix precisa ir nas 3.

---

## Gotchas

### G1: Advisory lock so em fechar_frete_grupo
`fechar_frete_grupo` usa `pg_advisory_xact_lock(hashtext('fechar_frete_' + CNPJs ordenados))` para serializar o fechamento do mesmo conjunto de CNPJs (anti-duplicacao). O `fechar_frete` single **nao** tem esse lock.

### G2: Rotas aceitam JSON E form-data
`fechar_frete`/`fechar_frete_grupo` checam `request.is_json`; em form-data fazem `json.loads` manual dos campos (`pedidos`/`cnpjs`). Testes/scripts devem cobrir os dois caminhos.

### G3: ICMS de fechamento sempre de Guarulhos no redespacho
No `fechar_frete` com `redespacho_ativo`, o ICMS e buscado SEMPRE de `Cidade(nome='Guarulhos', uf='SP')`, ignorando se o redespacho foi para Sao Paulo ou Sao Bernardo. **Possivel bug de ICMS** para os hubs SP/SBC.

### G4: Frete pode nao nascer no fechamento
`verificar_requisitos_para_lancamento_frete` exige NFs faturadas (entre 5 requisitos) + gate de CD (2-CD). Como na cotacao as NFs normalmente AINDA nao foram faturadas, o frete fica pendente e e recriado depois pelo fluxo de embarque/faturamento. NAO assumir que `fechar_frete` sempre cria `Frete`.

### G5: Copia de Pedido por dir()+setattr e fragil
Redespacho/otimizador clonam `Pedido` iterando `dir()` + `setattr` com try/except silencioso. Atributos nao-mapeados ou que dao erro sao perdidos sem aviso; o objeto e transiente (fora da sessao SQLAlchemy).

### G6: Docstring da conservadora MENTE sobre conversao RED
O docstring de `calcular_frete_otimizacao_conservadora` diz tratar `rota='RED'` como Guarulhos. O codigo real NAO converte — le `cod_uf` cru. A conversao RED→hub so acontece nas rotas `/redespachar*` (que mutam copias antes do calculo). Nao confiar no docstring.

### G7: visualizar.html e template ORFAO
Nenhuma rota de `app/cotacao` renderiza `cotacao/visualizar.html` (os links "visualizar" apontam para `embarques.visualizar_embarque`). `session['redespacho_tipo']` tambem e morto (so escrito por `redespachar_sao_paulo`, nunca lido). Tratar como codigo morto ate prova de uso.

### G8: verificar_nf_cd e bidirecional
Agrupa lotes por CNPJ em GRUPO A (`sincronizado_nf=False AND nf_cd=False`) e GRUPO B (`nf_cd=True`) e busca pendentes do mesmo CNPJ na direcao OPOSTA nao selecionados — alerta o operador antes de cotar para evitar split de pedidos do mesmo cliente entre normal e NF-no-CD.

---

## Interdependencias

| Importa de | O que | Pattern |
|-----------|-------|---------|
| `app.utils.frete_simulador` | `calcular_frete_por_cnpj` (motor), `buscar_cidade_unificada`, `calcular_fretes_possiveis` | top-level |
| `app.utils.calculadora_frete` | `CalculadoraFrete` (`calcular_frete_unificado`, direta/fracionada) | top-level |
| `app.utils.tabela_frete_manager` | `TabelaFreteManager` (congela os ~30 campos — R6) | top-level |
| `app.utils.localizacao` / `app.utils.embarque_numero` | `LocalizacaoService`, `obter_proximo_numero_embarque` | top-level |
| `app.{pedidos,separacao,transportadoras,embarques,tabelas,localidades,veiculos,vinculos,rastreamento}.models` | Models do fluxo | top-level |
| `app.fretes.routes` | `lancar_frete_automatico`, `verificar_requisitos_para_lancamento_frete` | **lazy** (dentro de `fechar_frete`) — evita ciclo |
| `app.embarques.routes` | `apagar_fretes_sem_cte_embarque` | lazy |
| `app.carvia...embarque_carvia_service` / `app.motos_assai...separacao_mirror_service` | Espelhamento | lazy |
| `app.rastreamento...entrega_rastreada_service` | `EntregaRastreadaService` (so DIRETA) | lazy |

| Exporta para | O que |
|-------------|-------|
| `app/__init__.py` | `cotacao_bp` |
| `app/embarques/routes.py` | `from app.cotacao.models import Cotacao` (top-level) |
| `app/carteira/routes/mapa_routes.py` | redireciona para `cotacao.tela_cotacao` (`cotar_frete_mapa`) |

---

## Acesso (sem item de menu)

NAO ha entrada "Cotacao" na sidebar/`base.html`. A cotacao e sempre alcancada de UPSTREAM:
- **Lista de Pedidos** — `_sidebar.html` → `pedidos.lista_pedidos` → marcar pedidos → form POST para `cotacao.iniciar_cotacao` (`templates/pedidos/_partials/_tabela_pedidos.html:37`).
- **Mapa da Carteira** — `mapa_routes.py:478 cotar_frete_mapa` resolve `Separacao`→lote, grava na sessao e redireciona para `cotacao.tela_cotacao`.

Sem decorator de perfil (so `@login_required`) — nao confundir com o `@require_financeiro()` que protege o lancamento MANUAL de frete no modulo `fretes`.

---

## Skills Relacionadas

| Skill / Subagente | Como interage |
|---|---|
| `cotando-frete` (skill) | Cotacao teorica / frete real via SQL — sem import Python |
| `gerindo-expedicao` (skill) | Carteira/separacao PRE-faturamento — upstream da cotacao |
| `resolvendo-entidades` (skill) | Resolve cliente/cidade/transportadora antes de cotar |
| `analista-carteira` (subagente) | Decide quais pedidos seguem para cotacao (P1-P7) |

---

## Referencias

| Preciso de... | Documento |
|---------------|-----------|
| Frete REAL pos-embarque (CTe, Odoo, pagamento) | `app/fretes/CLAUDE.md` |
| Regras CarteiraPrincipal / Separacao (status, lote, listeners) | `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md` |
| Cadeia Pedido → Embarque → Frete → CTe → Pagamento | `.claude/references/modelos/CADEIA_PEDIDO_ENTREGA.md` |
| Frete real vs teorico / margem | `.claude/references/negocio/{FRETE_REAL_VS_TEORICO,MARGEM_CUSTEIO}.md` |
| Campos de qualquer tabela | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
| Espelhamento de embarque CarVia | `app/carvia/CLAUDE.md` |
