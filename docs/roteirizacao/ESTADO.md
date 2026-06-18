<!-- doc:meta
tipo: state
camada: L1
sot_de: estado vivo do projeto de ampliacao da roteirizacao "Ver no Mapa" (fonte unica de progresso das 3 fases)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# Roteirizacao "Ver no Mapa" — ESTADO

> **Papel:** fonte UNICA de progresso da ampliacao da roteirizacao. Atualizar AQUI a cada avanco (nao replicar estado em outros docs). Design = spec; passo-a-passo = plano (links abaixo).

## Artefatos

- **Spec (design):** [docs/superpowers/specs/2026-06-16-roteirizacao-ver-no-mapa-design.md](docs/superpowers/specs/2026-06-16-roteirizacao-ver-no-mapa-design.md)
- **Plano Fase 1:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase1.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase1.md)
- **Plano Fase 2:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase2.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase2.md)
- **Plano Fase 3:** [docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase3.md](docs/superpowers/plans/2026-06-16-roteirizacao-ver-no-mapa-fase3.md)

## Decisoes fechadas (Rafael, 16/06/2026)

- Escopo: **mono-veiculo** (1 rota refinavel). VRP multi-veiculo fica para depois.
- Motor de otimizacao: **Google Route Optimization API (Single Vehicle)** — alvo; entra plugavel quando a service account existir (ver R1).
- Custo: **teorico parametrico** (sem comparativo com real/cotacao nesta entrega).
- Fonte de custo: **por tipo** de veiculo (tabela `veiculos`).
- Composicao do custo: combustivel + motorista/dia + **fixo/dia** + **depreciacao** (/30) + pedagio.
- Empacotador 3D de motos: **fora de escopo** (outra sessao).

## Estado atual

**PROJETO CONCLUIDO (17/06/2026).** As 3 FASES + Route Optimization API REAL **em PROD e VALIDADAS**. **38 testes verdes** (PostgreSQL local); migrations aplicadas no banco local **e em PROD** (`veiculos`+8 campos, `geocode_cache`, `rota_salva`); render dos templates = 200. R1 resolvido (Route Optimization validado contra a API real). Credenciais GCP em PROD (`ROUTE_OPTIMIZATION_PROJECT` + `GOOGLE_CREDENTIALS_JSON`). **Smoke real em PROD (17/06):** `POST /carteira/mapa/api/rota/otimizar` = 200 (1.2-1.8s), sem warning de fallback → Route Optimization ativo de fato. Conformidade proposto×implementado verificada item a item (ver "Validacao final" abaixo).

| Fase | Escopo | Status |
|------|--------|--------|
| **1 — Fundacao de custo + motor** | migration `veiculos` (8 campos) + CRUD; service custo/selecao/motor (chunking 25); API `/api/rota/otimizar`; UI parametros + card de custo | ✅ CONCLUIDA — em PROD, smoke real OK |
| **2 — Interatividade + persistencia** | incluir/remover on-demand; tabela `rota_salva` (salvar/nomear/listar); `geocode_cache` persistente | ✅ CONCLUIDA — em PROD |
| **3 — Cotacao por rota + extras** | cotar a partir de rota salva (reusa wizard); reordenar drag-and-drop; origem configuravel | ✅ CONCLUIDA — em PROD |

Tasks da Fase 1:

- [x] T1 — Migration `veiculos` (8 colunas) + model + schema JSON
- [x] T2 — `calcular_custo_operacional` (funcao pura, TDD)
- [x] T3 — `selecionar_veiculo` multidimensional (TDD)
- [x] T4 — Motor `otimizar_rota` + `_chunk_waypoints` (TDD)
- [x] T5 — Backend Directions+chunking + plug Route Optimization (TDD)
- [x] T6 — API `POST /api/rota/otimizar` (TDD)
- [x] T7 — Frontend: CRUD custos + painel de parametros + card de custo (render OK; smoke browser pendente)

Tasks da Fase 2:

- [x] T1 — `GeocodeCache` (L2 persistente) no `geocodificar_endereco`
- [x] T2 — model `RotaSalva` + migration
- [x] T3 — APIs salvar/listar/carregar/excluir rota
- [x] T4 — API adicionar pedido on-demand
- [x] T5 — UI incluir/remover on-demand + salvar/carregar rotas (render OK; smoke browser pendente)

Tasks da Fase 3:

- [x] T1 — API cotar frete a partir de rota salva (reusa wizard)
- [x] T2 — UI cotar rota + origem configuravel + drag-and-drop (render OK; smoke browser pendente)

Ajustes vs plano (durante a execucao TDD): (a) fixture `_isola_veiculos` desativa os 10 veiculos pre-existentes do banco em `test_roteirizacao_selecao` (savepoint reverte); (b) `otimizar_rota` checa lista vazia ANTES de importar o backend (bug pego pelo teste); (c) backend adiciona o ponto que vira destino na ordem quando nao ha volta (espelha `mapa_service` original); (d) `api/lista` converte `Numeric`->float (jsonify nao serializa Decimal).

## Validacao final (proposto × implementado) — 17/06/2026

Cruzamento item a item da spec/planos contra o codigo em PROD. **Foco em UI** (validado lendo `mapa_pedidos.html` + `admin_veiculos.html`); backend coberto por 38 testes + smoke real.

### UI — painel de parametros (Fase 1 T7)
| Proposto | Implementado | Evidencia |
|----------|--------------|-----------|
| `<select id="rotaVeiculo">` + opcao "Automatico" | ✅ | `mapa_pedidos.html:75-77` (`onchange=atualizarCustoRota`) |
| input dias de viagem | ✅ | `:80-81` (`#rotaDias`, min 0, default 0) |
| checkbox "considerar volta" | ✅ | `:82-84` (`#rotaVolta`) |
| origem configuravel (vazio = CD) | ✅ | `:78-79` (`#rotaOrigem`) — Fase 3 |

### UI — card de custo (Fase 1 T7)
| Proposto | Implementado | Evidencia |
|----------|--------------|-----------|
| combustivel / motorista / fixo / depreciacao / total | ✅ | `:140-145` (`#custoCombustivel..#custoTotal`) |
| dias + pedagio | ✅ | `:144` (`#custoDias`), `:132` (`#pedagioEstimado`) |
| recalcula ao mudar parametro | ✅ | `atualizarCustoRota()` `:1059-1106`; onchange em veiculo/dias/volta |

### UI — interatividade e persistencia (Fase 2 T5 / Fase 3 T2)
| Proposto | Implementado | Evidencia |
|----------|--------------|-----------|
| incluir pedido on-demand (input + botao) | ✅ | `:86-88` (`#addPedidoInput`), `adicionarPedidoMapa()` `:1112` |
| remover recalcula custo | ✅ | checkbox cliente `onchange="recalcularTotais(); atualizarCustoRota()"` `:896-899` |
| salvar/nomear rota | ✅ | botao `:89`, `salvarRota()` `:1158` |
| listar rotas salvas (modal) | ✅ | botao `:90`, `abrirRotasSalvas()` `:1195` |
| carregar / excluir rota | ✅ | `carregarRota()` `:1214`, `excluirRota()` `:1223` |
| cotar frete da rota | ✅ | botao "Cotar" `:1205`, `cotarRotaSalva()` `:1236` → redirect wizard |
| drag-and-drop reordenar | ✅ | `draggable` `:894`, `dndStart/dndOver/dndDrop` `:1249-1262` |

### UI — CRUD de custos no admin de veiculos (Fase 1 T7)
| Proposto | Implementado | Evidencia |
|----------|--------------|-----------|
| inputs dos 7 campos custo/capacidade (criar) | ✅ | `admin_veiculos.html:267-280` |
| idem (editar) + populados | ✅ | `:377-390` + `:458-464` (data-attrs) |
| checkbox `ativo` | ✅ editar (`:393`) / ⚠️ ausente no CRIAR (nasce `ativo=true` por default da migration) |

### Divergencias vs plano (todas aceitaveis)
- **`/api/rota/recalcular`** (proposto na spec, Fase 2) NAO virou endpoint separado: `atualizarCustoRota()` reusa `POST /api/rota/otimizar`. Equivalente funcional, menos superficie de API.
- **Pedagio** e exibido no card de estatisticas (`#pedagioEstimado`), nao numa celula do card de custo dedicado; atualizado no mesmo fluxo e salvo na rota. Cosmetico.
- **Checkbox `ativo`** presente no form EDITAR, ausente no CRIAR (default `TRUE` no banco cobre). Menor.

**Conclusao:** 100% dos itens de UI propostos estao implementados e validados; nenhuma lacuna funcional. Divergencias sao simplificacoes/cosmeticas.

## Melhorias operacionais (Onda 17/06/2026) — branch `feat/roteirizacao-mapa-melhorias`

14 ajustes pedidos pela operacao + 1 recurso novo, sobre a base ja entregue.
**Raiz arquitetural corrigida:** desenho e custo passaram a vir do MESMO motor
(`/api/rota/otimizar` enriquecido com `legs`/`bounds`/`ordem_clientes`); o backend
ganhou `respeitar_ordem` (medir ordem manual sem reotimizar) e os backends expoem
`legs` (segundos/metros reais) + `bounds`.

| # | Item | Como |
|---|------|------|
| 1 | Volta ao CD ignorada no desenho | `inclui_volta` agora chega ao motor unico; checkbox redesenha o tracado |
| 2 | Erro ao analisar densidade | densidade calculada no front (clientesData) + `NULLIF(palletizacao,0)` no backend |
| 3 | Matriz nao abria | `pedidosData` (inexistente) -> `clientesData`; novo `/api/matriz-clientes` (coords, fluxo lotes/CarVia) |
| 4 | Drag-and-drop mede ordem manual | `recalcularRota({otimizar:false})` respeita a sequencia arrastada e redesenha km/tempo/pedagio/custo |
| 5 | Parada extra por endereco/CNPJ | `/api/parada-extra` (ReceitaWS/geocode); placeholder afeta rota/custo mas nao e cotavel |
| 6 | Acumular rota de lista_pedidos | `/api/rota/acumular` (nova/existente) + resgate `?rota_id=`; botao na lista_pedidos |
| 7 | Modal de busca no mapa | `/api/rota/buscar-pendentes` (sem data_embarque OU nf_cd) + filtros + select sub-rota |
| 8 | Remover entrega da lista | botao de remover por cliente |
| 9 | Checkbox nao reseta ao otimizar | `Set clientesDesmarcados` preserva selecao entre re-renders |
| 10 | X do InfoWindow invisivel | `.gm-ui-hover-effect>span` em `utilities/_legacy.css` (link no template) |
| 11 | Exp/agend sempre visiveis | helper DRY `renderPedidoSubItem` (formato unico) |
| 12 | "Tempo ate aqui" correto | usa `legs[].duracao_s` (fim do parse regex que pegava so o 1o numero) |
| 13 | Lista compacta | densidade visual + respiro entre cards |
| 14 | Peso sem casas decimais | `formatarPeso` unico (kg sem decimais / t com 1 casa) |
| + | **Romaneio LIFO imprimivel** | botao "Romaneio": ordem de carga (inversa) + ordem de entrega, com agendamento/protocolo |

Limpeza: removida a funcao legada `exibirRotaOtimizada` (199 linhas mortas, usava
`pedidosData`). **+20 testes** novos (motor unificado, matriz-clientes, acumular,
parada-extra, busca-pendentes); **58 testes carteira verdes**; `node --check` no JS
do template + render 200.

**Pendente desta onda:**
- **Vinculo Romaneio <-> Embarque:** quando a rota do mapa vira embarque (via Cotar
  Frete -> wizard), persistir a ordem/`rota_id` no Embarque e expor o romaneio a
  partir dele. Atravessa `cotacao`/`embarques` (model + fluxo de criacao) — sessao
  propria. Hoje o romaneio e client-side da rota atual no mapa.
- Smoke browser em PROD (todas as interacoes).
- Migration: nenhuma coluna nova (RotaSalva ja existe; `status='rascunho'` usa coluna existente).

## Melhorias operacionais (Onda 18/06/2026)

2 ajustes pedidos pela operacao, sobre a base entregue.

| # | Item | Como |
|---|------|------|
| 1 | Botao "Adicionar a rota" da lista preso `disabled` | Causa-raiz: cache do navegador servindo `lista-checkboxes.js` antigo (que setava `disabled`). HTML/JS ja nao desabilitavam (commit `dd33e64f9`), mas os `<script>` de `lista_pedidos.html` carregavam por `url_for('static',...)` sem cache-busting. Migrados para o filtro `asset_url` (`?v=<hash md5>`) — o cache invalida sozinho. |
| 2 | Agrupar rota em avaliacao + rota salva -> NOVA rota | `POST /api/rota/agrupar` (`rota_agrupar`) une os lotes de uma `RotaSalva` existente + os lotes em avaliacao (`_lotesSelecionados()`), deduplicando e preservando ordem, e grava uma rota NOVA (`status='salva'`); a de origem fica intacta — difere de `/api/rota/acumular` (#6), que ANEXA a uma existente. UI: botao "Agrupar c/ rota" + modal `agruparComRotaSalva()`. Ex.: Rota 1 (5) + avaliacao (5) -> Rota 1 intacta + Rota 2 (10). |

Doc SOT do modulo: `app/carteira/CLAUDE.md` R11 atualizada. **Sem migration** (RotaSalva ja existe).
Validacao: `py_compile` (mapa_routes) + parse Jinja dos 2 templates + `node --check` da funcao nova.

## Pendencias

- **R1 — Route Optimization API:** RESOLVIDO (17/06/2026). `route_optimization_backend` implementado (optimizeTours via service account / google-auth) e **validado contra a API real** (ordem otimizada + distancia/tempo/polyline; ex.: 3 paradas SP = 72,34 km / 107,6 min). `default_backend` usa Route Optimization quando `ROUTE_OPTIMIZATION_PROJECT` esta setado; senao cai para Directions+chunking (fallback automatico em erro). Projeto = `dynamic-heading-434921-q5`; SA = `sistema-fretes-routes-api@...` (role Route Optimization Editor). Janela global = 7 dias; metrica = `travelDuration`. Credencial: `_ro_token()` prioriza `GOOGLE_CREDENTIALS_JSON` (conteudo do JSON da SA na env var) e cai para ADC padrao (`GOOGLE_APPLICATION_CREDENTIALS`) se ausente — ambos os caminhos cobertos por teste.
- **PROD (Render) — Route Optimization ATIVADO:** env vars gravadas em PROD (`sistema-fretes` / `srv-d13m38vfte5s738t6p60`) via Render API em 17/06/2026: `ROUTE_OPTIMIZATION_PROJECT=dynamic-heading-434921-q5` + `GOOGLE_CREDENTIALS_JSON` (JSON da SA, 2373 bytes). Optou-se por env var JSON em vez de Secret File pois o MCP/automacao so grava env vars; o token OAuth2 foi validado localmente lendo a credencial pela env var. A chave NAO esta no git (vive em `.secrets/route-optimization-sa.json` no dev, gitignorada). Fica efetivo no proximo deploy (o do push desta entrega — gravar env var nao disparou redeploy).
- **R4 — Geocoding sem persistencia:** RESOLVIDO na Fase 2 (`geocode_cache` L2 no banco; L1 memoria -> L2 banco -> Google).
- **Smoke (browser/PROD):** CONCLUIDO (17/06/2026) — Rafael fez o smoke real; `/carteira/mapa/api/rota/otimizar` = 200 sem fallback. Validacao UI item a item registrada acima.
- **Push/PR:** CONCLUIDO (17/06/2026) — merge fast-forward na `main` + push; worktree removida.
- **Backlog (nao bloqueia):**
  - Card chama `/api/rota/otimizar` ALEM do desenho via `/api/rota-clientes` — 2 roteirizacoes por calculo. Unificar (aceitavel; dentro do free tier).
  - Adicionar checkbox `ativo` ao form de CRIAR veiculo (hoje so no editar; novo veiculo nasce `ativo=true`).
  - Empacotador 3D de motos / multi-veiculo (VRP) / comparativo custo real — fora de escopo desta entrega (outra sessao).

## Atualizado

- **2026-06-16 (1):** criado o ESTADO; spec e plano da Fase 1 escritos e registrados nos indices.
- **2026-06-16 (2):** Fase 1 IMPLEMENTADA no branch worktree (8 commits, T1-T7); 20 testes verdes; migration aplicada no banco local; render 200 nos 2 templates. Pendente: smoke browser + push/PR + R1.
- **2026-06-16 (3):** Fase 2 IMPLEMENTADA (T1-T5): `geocode_cache` (L2) + `RotaSalva` + APIs salvar/listar/carregar/excluir + adicionar pedido on-demand + UI. 28 testes verdes no total; tabelas criadas no banco local; render 200. Pendente: smoke browser + push/PR.
- **2026-06-16 (4):** Fase 3 IMPLEMENTADA (T1-T2): API cotar frete por rota salva (reusa wizard) + origem configuravel + drag-and-drop. **31 testes verdes**; render 200. As 3 fases concluidas. Pendente: smoke browser + push/PR.
- **2026-06-17 (5):** R1 RESOLVIDO — Route Optimization API real (optimizeTours via service account) implementada e VALIDADA contra a API ao vivo; fallback Directions automatico; google-auth==2.55.0; credencial em `.secrets/` (gitignore). **36 testes verdes**. Pendente: smoke browser + push/PR + credenciais no Render.
- **2026-06-17 (6):** ENTREGA — `_ro_token()` passa a aceitar `GOOGLE_CREDENTIALS_JSON` (credencial via env var, p/ Render) alem de ADC, com 2 testes novos (**38 testes verdes**). Env vars gravadas em PROD via Render API (`ROUTE_OPTIMIZATION_PROJECT` + `GOOGLE_CREDENTIALS_JSON`, ambos HTTP 200). Merge fast-forward na `main` + push. Route Optimization ativo no proximo deploy. Pendente: validar em PROD pos-deploy + smoke browser.
- **2026-06-17 (7):** INCIDENTE PROD + FIX — apos o deploy, `/pedidos/lista_pedidos` deu 500 (`UndefinedColumn: veiculos.custo_km`): a migration `2026_06_16_veiculo_parametros_custo.sql` (8 colunas em `veiculos`) nao havia sido aplicada em PROD. O boot (`create_all`) cria TABELAS novas (`geocode_cache`/`rota_salva` ja existiam) mas NAO adiciona colunas a tabela existente — colunas novas exigem rodar o `.sql` em PROD. Apliquei as 3 migrations idempotentes via `DATABASE_URL_PROD`; `lista_pedidos` voltou a 200. LICAO: aplicar migration de coluna em PROD ANTES/junto do push (o deploy do Render nao roda `scripts/migrations/*.sql`).
- **2026-06-17 (8):** PROJETO CONCLUIDO — smoke real em PROD pelo Rafael (`/carteira/mapa/api/rota/otimizar` = 200, Route Optimization ativo sem fallback). Resgate proposto×implementado + validacao UI item a item (painel, card de custo, incluir/remover, salvar/listar/carregar/excluir/cotar, drag-and-drop, CRUD admin veiculos): 100% coberto, 0 lacuna funcional; 3 divergencias menores documentadas (recalcular reusa otimizar; pedagio no card de stats; `ativo` so no editar). Encerrado.
- **2026-06-18 (9):** Onda operacao (2 itens) — (1) botao "Adicionar a rota" da lista corrigido na RAIZ: scripts de pedidos migrados para `asset_url` (cache-busting); o `disabled` ja fora removido em `dd33e64f9`, mas o JS cacheado o reativava. (2) Novo `POST /api/rota/agrupar` + botao "Agrupar c/ rota" no mapa: une avaliacao + rota salva criando uma rota NOVA, preservando a de origem (Rota 1 (5)+aval(5) -> Rota 1 + Rota 2 (10)). R11 do `app/carteira/CLAUDE.md` atualizada. Sem migration.
