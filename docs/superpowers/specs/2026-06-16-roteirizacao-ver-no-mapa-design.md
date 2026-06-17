<!-- doc:meta
tipo: explanation
camada: L3
sot_de: design da ampliacao da roteirizacao (Ver no Mapa) — proposta aprovada no desenho, aguardando plano de implementacao
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-16
-->
# Roteirizacao "Ver no Mapa" — Ampliacao (design)

> **Papel:** spec de design da ampliacao do recurso "Ver no Mapa" (roteirizacao de pedidos a partir de `lista_pedidos.html`). Desenho aprovado pelo Rafael (16/06/2026); este doc precede o plano de implementacao (writing-plans). NADA implementado ainda.

## Indice

- [Contexto](#contexto)
- [Estado atual (resumo do estudo)](#estado-atual-resumo-do-estudo)
- [Decisoes fechadas](#decisoes-fechadas)
- [Modelo de dados](#modelo-de-dados)
- [Backend](#backend)
- [Frontend](#frontend)
- [Faseamento](#faseamento)
- [Custo Google Maps](#custo-google-maps)
- [Riscos e gotchas](#riscos-e-gotchas)
- [Fora de escopo](#fora-de-escopo)

## Contexto

O botao **"Ver no Mapa"** (`_tabela_pedidos.html:63` → `lista-crud.js:6 abrirMapaPedidos()`) abre `/carteira/mapa/visualizar?lotes[]=...` numa aba nova: pagina standalone `mapa_pedidos.html` (jQuery + Google Maps JS API), servida por `mapa_routes.py` + `mapa_service.py` (1346 linhas). Hoje plota clientes agrupados, calcula 1 rota otimizada via Directions API e estima custo/pedagio de forma **hardcoded**. O objetivo e transformar isso num roteirizador de planejamento de expedicao com custo real parametrico, sem limite pratico de paradas, com rotas salvas e cotacao a partir delas.

Demanda do Rafael: ampliar parametros de custo (tabela de veiculos como fonte), custo de motorista por dia, flag de volta, inclusao/remocao de pedidos on-demand, superar o limite de waypoints do Google, armazenar+nomear rotas e cotar frete por rota armazenada.

## Estado atual (resumo do estudo)

| Recurso | Estado hoje | Evidencia |
|---------|-------------|-----------|
| Custo por km | `custo = km × 2,5` **hardcoded** | `mapa_service.py:843,978` |
| Selecao de veiculo | so por `peso_maximo` (menor que comporta) | `mapa_service.py:1007-1035` |
| Volta ao CD | nao existe (rota termina na ultima parada) | `mapa_service.py:775,898` |
| Custo motorista / dias | inexistente | — |
| Limite de waypoints | nao tratado (quebra acima de ~25) | `mapa_service.py:759-789` |
| Matriz de distancias | teto de 10 pedidos | `mapa_service.py:1261` |
| Geocoding | cache so em memoria (`TTLCache` 1h), re-geocodifica a cada abertura | `mapa_service.py:28,692` |
| Persistencia de rota | tudo em `session`; nenhuma tabela | `mapa_routes.py:116` |
| Cotacao do mapa | ponte joga lotes na `session` → wizard `/cotacao` | `mapa_routes.py:442` |
| Painel lateral | checkbox por cliente recalcula **totais**, NAO a rota | `mapa_pedidos.html:785` |

**Modelos de veiculo:** `Veiculo` (`veiculos` = tipo/categoria: FIORINO→CARRETA; so `peso_maximo`/eixos/`multiplicador_pedagio`/dims do bau) e `FrotaVeiculo` (fisico: placa, km, `depreciacao_mensal`) com `FrotaDespesa` (custo real). A fonte de custo desta feature e o **tipo** (`Veiculo`).

**Dados de geo/peso/pallet:** nao ha lat/lng persistido em `carteira_principal`/`separacao` (geocoding on-the-fly). Endereco de entrega vem de `CarteiraPrincipal` (`rua/bairro/cep/nome_cidade/cod_uf_endereco_ent`); peso/pallet pre-calculados em `Separacao.peso`/`Separacao.pallet`; m3 derivavel de `cadastro_palletizacao.altura_cm/largura_cm/comprimento_cm`.

## Decisoes fechadas

1. **Escopo:** mono-veiculo — uma rota (TSP) refinavel interativamente. Multi-veiculo (VRP) fica para depois.
2. **Motor de otimizacao:** **Google Route Optimization API (SKU Single Vehicle Routing)**. Resolve o limite de 25 paradas nativamente (suporta centenas), cobra linear por shipment (US$0,01/parada), otimizacao global real.
3. **Custo:** teorico parametrico (sem comparativo com real/cotacao nesta entrega).
4. **Fonte de custo:** por **tipo** de veiculo (tabela `veiculos` ampliada).
5. **Composicao do custo:** combustivel + motorista/dia + **fixo/dia** + **depreciacao** + pedagio.

## Modelo de dados

> Toda alteracao de schema = par migration `.sql` + `.py` idempotente em `app/.../scripts/migrations/` (regra do projeto; `create_all` no boot cria tabelas novas, coluna nova exige par).

### `Veiculo` (ampliar — `app/veiculos/models.py`)
Adicionar colunas (todas nullable, default sensato; nao quebram registros existentes):

| Coluna | Tipo | Uso |
|--------|------|-----|
| `custo_km` | `Numeric(10,2)` | combustivel+pneus+manutencao por km rodado |
| `custo_motorista_dia` | `Numeric(10,2)` | diaria do motorista |
| `custo_fixo_dia` | `Numeric(10,2)` | seguro, rastreador, licenciamento rateados/dia |
| `depreciacao_mensal` | `Numeric(15,2)` | depreciacao do tipo/mes (÷30 no calculo) |
| `capacidade_pallets` | `Integer` | selecao multidimensional |
| `capacidade_m3` | `Float` | selecao multidimensional |
| `velocidade_media_kmh` | `Float` | estimar `dias_viagem` quando nao informado |
| `ativo` | `Boolean` default `true` | listar so veiculos ativos |

CRUD ampliado em `app/veiculos/routes.py` (form + `api_lista_veiculos`).

### `rota_salva` (nova tabela — Fase 2)
`id`, `nome` (varchar nullable), `criado_por`, `criado_em`, `atualizado_em`, `veiculo_id` (FK `veiculos`), `origem_endereco`/`origem_lat`/`origem_lng` (default CD), `inclui_volta` (bool), `dias_viagem` (int), `lotes` (JSON — lista de `separacao_lote_id`), `ordem_otimizada` (JSON), `distancia_km`, `tempo_min`, `peso_total`, `pallet_total`, `valor_total`, `custo_combustivel`, `custo_motorista`, `custo_fixo`, `custo_depreciacao`, `custo_pedagio`, `custo_total` (snapshot), `polyline` (text), `status` (rascunho/salva).

### `geocode_cache` (nova tabela — Fase 2)
`id`, `endereco_hash` (unique), `endereco` (text), `lat` (float), `lng` (float), `geocodificado_em` (timestamp), `fonte` (varchar). Reusavel por todos os modulos; substitui o `TTLCache` volatil.

## Backend

Novo `app/carteira/services/roteirizacao_service.py` (separa responsabilidade do `mapa_service.py`, ja grande; `mapa_service` mantem geocoding + agrupamento de clientes):

- `otimizar_rota(paradas, veiculo, inclui_volta, dias_viagem, origem)` → chama Route Optimization API; se `inclui_volta`, fim = origem; retorna `{ordem, polyline, distancia_km, tempo_min}`. Sem teto de paradas.
- `calcular_custo(rota, veiculo, dias)`:
  - `dias = dias_viagem` informado, ou `ceil(tempo_total / jornada_diaria)` se 0 (usa `velocidade_media_kmh`).
  - `custo_combustivel = distancia_km × veiculo.custo_km`
  - `custo_motorista  = dias × veiculo.custo_motorista_dia`
  - `custo_fixo       = dias × veiculo.custo_fixo_dia`
  - `custo_depreciacao= dias × (veiculo.depreciacao_mensal / 30)`
  - `custo_pedagio    = estimativa atual (heuristica por multiplicador_pedagio; a distancia ja inclui volta)`
  - `custo_total = soma`
- `selecionar_veiculo(peso, pallets, m3)` → menor `Veiculo.ativo` que atende as 3 dimensoes; fallback maior.

Novas APIs em `mapa_routes.py` (blueprint `/carteira/mapa`):

| Metodo | Rota | Funcao |
|--------|------|--------|
| POST | `/api/rota/otimizar` | otimiza + custa (sem salvar) |
| POST | `/api/rota/recalcular` | re-otimiza apos add/remove (Fase 2) |
| POST | `/api/rota/salvar` | persiste `rota_salva` (Fase 2) |
| GET | `/api/rotas` | lista rotas do usuario (Fase 2) |
| GET | `/api/rota/<id>` | carrega rota salva (Fase 2) |
| DELETE | `/api/rota/<id>` | exclui (Fase 2) |
| POST | `/api/rota/<id>/cotar` | popula `session['cotacao_lotes']` + redirect wizard (Fase 3, reusa `cotar_frete_mapa`) |

## Frontend

`mapa_pedidos.html`:
- **Painel de parametros** (Fase 1): seletor de veiculo (ou "automatico por capacidade"), input `dias`, checkbox `considerar volta`, origem (default CD).
- **Card de custo detalhado** (Fase 1): combustivel / motorista / fixo / depreciacao / pedagio / **total**, recalculando ao mudar parametros.
- **Incluir/remover on-demand** (Fase 2): carrega candidatos roteirizaveis + busca por num_pedido; toggle recalcula a rota.
- **Salvar/nomear rota + lista de rotas salvas + "Cotar frete desta rota"** (Fase 2/3).
- **Reordenar manual (drag-and-drop)** (Fase 3, opcional).

## Faseamento

**Fase 1 — Fundacao de custo + motor de otimizacao (maior ROI).**
Migration `Veiculo` (8 campos) + CRUD; `roteirizacao_service` com Route Optimization API (acaba o limite de 25) + formula de custo parametrica; flag volta; dias de viagem; selecao multidimensional; UI de parametros + card de custo. Substitui o `2,5` hardcoded e a selecao so-por-peso.

**Fase 2 — Interatividade + persistencia.**
Incluir/remover pedidos on-demand recalculando a rota; tabela `rota_salva` + salvar/nomear/listar/carregar/excluir; `geocode_cache` persistente.

**Fase 3 — Cotacao por rota salva + extras.**
Cotar a partir de rota salva (reusa wizard); reordenar drag-and-drop; origem configuravel.

## Custo Google Maps

Pricing oficial (jun/2026), apos free tier:

| SKU | Gratis/mes | Preco | Cobranca |
|-----|-----------|-------|----------|
| Route Optimization — Single Vehicle | 5.000 | US$10/1k shipments | linear: 1/parada (US$0,01/parada) |
| Directions Advanced (optimize) | 5.000 | US$10/1k requests | 1/rota (teto 25 paradas) |
| Distance Matrix Advanced | 5.000 | US$10/1k elementos | N² (descartado: caro) |

Rota de 40 paradas ≈ US$0,40; free tier ≈ 5.000 paradas/mes. Uso de planejamento cabe no gratis ou poucos US$/mes.

## Riscos e gotchas

- **R1 — Autenticacao do Route Optimization API:** pode exigir **service account / OAuth2** (Google Cloud), nao a `GOOGLE_MAPS_API_KEY` atual (que serve Geocoding/Directions). **Validar logo no inicio da Fase 1.** Fallback se inviavel: Directions `optimize:true` para ≤25 paradas + chunking de 25 com overlap acima disso (otimizacao por bloco).
- **R2 — Timezone/datas:** qualquer campo de data segue `app/utils/timezone.py` (Brasil naive) — ja usado em `mapa_routes.py`.
- **R3 — CarVia:** pedidos CarVia chegam com `peso=0/pallet=0` na roteirizacao (`mapa_service.py:602`); selecao de veiculo por capacidade ignora-os — manter comportamento, sinalizar na UI.
- **R4 — Custo de geocoding:** sem `geocode_cache` (Fase 2), cada otimizacao re-geocodifica enderecos novos — aceitavel na Fase 1, prioridade na Fase 2.
- **R5 — `mapa_service.py` grande (1346 linhas):** nao inchar; logica nova vai em `roteirizacao_service.py`.

## Fora de escopo

- **Empacotador 3D de motos** (`app/static/js/simulador-carga/bin-packer.js`): explicitamente adiado pelo Rafael para outra sessao.
- **Multi-veiculo (VRP):** mono-veiculo nesta entrega.
- **Comparativo de custo** (real `FrotaDespesa`/`BI` ou cotacao de transportadora): nao nesta entrega.
