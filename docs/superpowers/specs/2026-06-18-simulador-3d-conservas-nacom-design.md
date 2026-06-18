<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# Simulador 3D — Expansão para Conservas Nacom (carga mista pallet + moto) — Design Spec

> **Papel:** Design spec da expansão do Simulador 3D de Carga (hoje só motos CarVia) para também acomodar produtos Nacom palletizados, no mesmo veículo, com pallets no piso e motos por cima.

## Indice

- [Contexto](#contexto)
- [Objetivo](#objetivo)
- [Decisoes de Design](#decisoes-de-design)
- [Arquitetura em 2 camadas](#arquitetura-em-2-camadas)
- [Camada 1 — Montagem de pallets (backend Python)](#camada-1--montagem-de-pallets-backend-python)
  - [Fonte de dados](#fonte-de-dados)
  - [Algoritmo de montagem](#algoritmo-de-montagem)
  - [Modos de agrupamento A–D](#modos-de-agrupamento-ad)
  - [Cálculo de altura do pallet (lastro + folga)](#cálculo-de-altura-do-pallet-lastro--folga)
- [Camada 2 — Arranjo 3D (extensão do bin-packer)](#camada-2--arranjo-3d-extensão-do-bin-packer)
  - [Perfil multi-slab e caminho crítico](#perfil-multi-slab-e-caminho-crítico)
  - [Regra "Nacom embaixo"](#regra-nacom-embaixo)
  - [Pallet sobre pallet](#pallet-sobre-pallet)
- [Flags da tela](#flags-da-tela)
- [Rotas / API](#rotas--api)
- [Render](#render)
- [Arquivos](#arquivos)
- [Plano de testes](#plano-de-testes)
- [Fora de escopo](#fora-de-escopo)
- [Pontos em aberto / riscos](#pontos-em-aberto--riscos)

**Data**: 2026-06-18
**Status**: Proposto (aguardando revisão do usuário)

---

## Contexto

O Simulador 3D de Carga (spec `2026-04-03-simulador-carga-3d-design.md`) acomoda **motos** CarVia num baú: bin-packing 3D client-side (`app/static/js/simulador-carga/bin-packer.js`), render Three.js (`carga-renderer.js`), rotas em `app/carvia/routes/simulador_routes.py`. O motor é genérico — `bin-packer.js` opera sobre `{comprimento, largura, altura, peso_medio, qty}` e nunca toca em propriedade específica de moto.

A indústria Nacom expede **conservas palletizadas**. Já existe suporte estrutural para carga mista: um mesmo `Embarque` carrega `EmbarqueItem` Nacom (`separacao_lote_id = LOTE_*`) e CarVia (`CARVIA-*`) lado a lado, com rateio de frete conjunto (FONTE: `app/embarques/models.py:298-313` `_eh_carvia`/`_eh_nacom`; `app/fretes/routes.py:5338-5355`, decisão Rafael 2026-06-12). O veículo do embarque vem de `Embarque.modalidade` (nome textual) → `Veiculo` por nome (FONTE: `simulador_routes.py:317-327`).

Hoje o simulador, no modo embarque, lê só os itens CarVia daquele embarque. Falta acomodar os itens Nacom no mesmo baú, respeitando regras de palletização e a prioridade física **conservas embaixo, motos em cima**.

## Objetivo

Expandir o simulador para que, num único veículo, ele:

1. **Monte pallets PBR** (1,00×1,20×0,15 m) a partir das conservas de uma **Separação** Nacom, seguindo as regras de palletização do negócio.
2. **Arranje no baú** os pallets montados (no piso) + as motos (por cima), reusando o motor 3D, com **caminho crítico** (aproveitamento real da projeção da mercadoria sobre o pallet vizinho).
3. Permita ao operador configurar o comportamento por **flags na própria tela** (modo de agrupamento, overbooking, pallet sobre pallet, separação por pallet).
4. Renderize estrado PBR + coluna de mercadoria, colorindo por grupo (pedido/CNPJ/produto).

## Decisoes de Design

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Onde roda a montagem de pallets (Camada 1) | **Backend Python** (service novo), não JS | Regras de negócio críticas → testáveis com pytest, versionadas; JOIN `Separacao`→`CadastroPalletizacao` já é padrão backend |
| Onde roda o arranjo 3D (Camada 2) | **Frontend JS**, estendendo `bin-packer.js` + `carga-renderer.js` | Mantém o contrato atual (backend resolve itens, front arruma); reusa SA + render existentes |
| Dimensões da caixa de conserva | `CadastroPalletizacao.altura_cm/largura_cm/comprimento_cm` | Já existem (`app/producao/models.py:81-83`) |
| Limite de caixas por pallet | `CadastroPalletizacao.palletizacao` | Já existe (`app/producao/models.py:77`) |
| Peso | `CadastroPalletizacao.peso_bruto` (por unidade de venda) | Já existe (`app/producao/models.py:78`) |
| Pallet PBR | Constante nova `(100, 120, 15)` cm | Não existe modelo de pallet no sistema; não há schema a migrar |
| Fonte dos itens Nacom | Uma **Separação** (`separacao_lote_id`) | Itens já decididos no fluxo de expedição; granularidade pedido/CNPJ/produto disponível |
| Ponto de entrada da carga mista | O **Embarque** (já junta LOTE_* + CARVIA-*) | Suporte estrutural já existe; veículo derivado de `Embarque.modalidade` |
| "Nunca de pé" | Resolvido por convenção na montagem (caixa mantém `altura_cm` na vertical) | Não há flag de orientação no cadastro e não é preciso criar |
| Migration de schema | **Nenhuma** | Todos os campos necessários já existem |

## Arquitetura em 2 camadas

```
Separação (separacao_lote_id)
   │  JOIN cod_produto → CadastroPalletizacao (dims caixa, palletizacao, peso)
   ▼
┌─────────────────────────────────────────────┐
│ CAMADA 1 — Montagem de pallets (Python, NOVO)│
│  regras 1–4, overbooking, folga, modos A–D   │
│  saída: lista de PALLETS                      │
│  {base 100×120, altura, peso, merc_x, merc_y, │
│   conteúdo, grupo, cor}                        │
└─────────────────────────────────────────────┘
   │  JSON  +  motos do embarque (CarviaNfVeiculo)
   ▼
┌─────────────────────────────────────────────┐
│ CAMADA 2 — Arranjo 3D (bin-packer.js, EXT.)  │
│  pallets (piso, orient. única, multi-slab)    │
│  + motos (topo, 4 orient.)                    │
│  caminho crítico via colisão por altura       │
└─────────────────────────────────────────────┘
   ▼
   carga-renderer.js  (estrado cinza + coluna colorida + motos)
```

## Camada 1 — Montagem de pallets (backend Python)

Novo módulo: **`app/carteira/services/palletizacao_service.py`** (domínio de expedição Nacom; o JOIN `CarteiraPrincipal/Separacao`→`CadastroPalletizacao` já é feito em `app/carteira/services/mapa_service.py:74-79`). Função pura e testável, sem dependência de Flask request.

Constantes do módulo:

```python
PALLET_PBR_CM = (100.0, 120.0, 15.0)   # base_x, base_y, altura_estrado
FOLGA_LASTRO_CM = 5.0                   # mercadoria pode exceder a base em até +5 por dimensão
OVERBOOKING_MAX = 0.50                  # teto de 50% sobre o limite de caixas
```

### Fonte de dados

Entrada: `separacao_lote_id`. Carrega itens via:

```python
db.session.query(
    Separacao.num_pedido, Separacao.cnpj_cpf, Separacao.cod_produto,
    Separacao.qtd_saldo,
    CadastroPalletizacao.altura_cm, CadastroPalletizacao.largura_cm,
    CadastroPalletizacao.comprimento_cm, CadastroPalletizacao.palletizacao,
    CadastroPalletizacao.peso_bruto,
).outerjoin(
    CadastroPalletizacao,
    and_(Separacao.cod_produto == CadastroPalletizacao.cod_produto,
         CadastroPalletizacao.ativo == True),
).filter(Separacao.separacao_lote_id == lote_id)
```

Campos (FONTE: `app/separacao/models.py` — `separacao_lote_id:12`, `num_pedido:13`, `cnpj_cpf:15`, `cod_produto:19`, `qtd_saldo:22`). Item sem dimensão cadastrada (`altura_cm=0` ou `palletizacao` nulo) entra numa lista de **pendências** retornada à UI (não trava a simulação; sinaliza cadastro faltante).

### Algoritmo de montagem

Para cada **escopo de mistura** definido pelo modo de agrupamento (ver A–D):

1. **Pallets fechados (regra 1):** para cada `cod_produto` no escopo, `n_fechados = floor(qtd_no_escopo / limite)`, onde `limite = palletizacao × (1 + overbooking_pct)`. Cada fechado vira um pallet mono-produto cheio. A regra 1 ("pallets fechados sempre com o mesmo produto") é absoluta — pallets fechados nunca recebem outro produto.
2. **Frações (regras 2 e 3):** o resto de cada produto (`qtd % limite`) entra numa fila de frações. Agrupa as frações por **dimensão de caixa** (chave = `(largura_cm, comprimento_cm)`, com `altura_cm` como desempate preferencial para camadas uniformes), preenchendo pallets até `limite` caixas (contagem). Produtos de mesma dimensão ficam juntos no mesmo pallet quando couberem (ex.: 56 cx de 4320147 + 56 cx de 4360147). Havendo >1 dimensão, prioriza manter mesma dimensão junta, respeitando o `limite`.
3. **Separação por pallet (flag, modos B/C):** se ligada, as frações não cruzam a fronteira de pedido (modo B/C separado) — cada pedido fecha seus próprios pallets fracionados. Separação **lógica**: não se cria pallet vazio (pallet só existe para apoiar conserva no chão; vazio roubaria espaço das motos).
4. **Altura:** calcula a altura física de cada pallet (ver fórmula abaixo).

Saída — lista de pallets:

```json
{
  "tipo": "pallet",
  "base_x": 100, "base_y": 120, "altura_estrado": 15,
  "merc_x": 104, "merc_y": 104, "altura_merc": 122,
  "altura_total": 137,
  "peso": 412.5,
  "grupo": "PED-VCD123",          // chave do escopo, para cor/legenda
  "conteudo": [{"cod_produto": "4830103", "caixas": 64}],
  "color": "#c0844a"
}
```

### Modos de agrupamento A–D

O **escopo de mistura** é o conjunto dentro do qual frações de produtos podem dividir um pallet:

| Modo | Escopo de mistura | Rastreabilidade | Observação |
|------|-------------------|-----------------|------------|
| **A — Pedido** (default) | `num_pedido` | por pedido | pallets nunca misturam pedidos |
| **B — CNPJ** | `cnpj_cpf` | por cliente | flag separado-por-pallet: on = pedidos do CNPJ não dividem pallet; off = dividem |
| **C — Remontagem** | global (todos os clientes) | por pallet | mistura clientes para otimizar; flag separado-por-pallet idem B |
| **D — Lote** | `cod_produto` global | nenhuma (só produto) | maximiza pallets fechados; separação de cliente/pedido é do last-mile |

> Confirmar: o CNPJ do modo B é `cnpj_cpf` (cliente comprador) e não `cnpj_endereco_ent` (endereço de entrega, `app/carteira/models.py:71`). Default assumido: `cnpj_cpf`.

### Cálculo de altura do pallet (lastro + folga)

A **folga de 5cm** significa que a mercadoria pode **ultrapassar** a borda do estrado em até +5cm por dimensão (não reduz a base). Lastro (caixas por camada):

```
lastro = max sobre as 2 orientações da base da caixa (dimA,dimB):
         floor((100 + 5) / dimA) × floor((120 + 5) / dimB)
camadas        = ceil(caixas_no_pallet / lastro)
altura_total   = 15 + camadas × altura_cm     (cm)
merc_x, merc_y = footprint da mercadoria = (n_caixas_dirX × dimA, n_caixas_dirY × dimB)
```

Validação com o exemplo do usuário — item `4830103`, caixa 26×26×30,5:
- `floor(105/26)=4`, `floor(125/26)=4` → **lastro 4×4 = 16 cx/camada** ✓ (bate com "Lastro 4x4").
- `merc_x = merc_y = 4×26 = 104` (excede 4cm sobre o estrado de 100).

As caixas ficam **centralizadas** no estrado; o excesso (até 5cm) distribui-se nas bordas.

## Camada 2 — Arranjo 3D (extensão do bin-packer)

Extensão de `app/static/js/simulador-carga/bin-packer.js`. Hoje cada item é uma caixa uniforme com 4 orientações (`getOrientations`, l.225) e colisão por bounding box uniforme (`subtractBox`, l.443; `findBestFit`, l.245). Duas adições:

### Perfil multi-slab e caminho crítico

Cada item ganha um **perfil de slabs** (fatias por faixa de altura), cada slab com `{y0, y1, fw, fd, fox, foy}` (faixa vertical + footprint + offset relativo ao canto do item):

- **Moto** → 1 slab uniforme (mantém as 4 orientações atuais; comportamento inalterado).
- **Pallet** → 2 slabs, **orientação única** (estrado sempre com base no chão, não rotaciona):
  - slab 0 (estrado): `y0=0, y1=15`, footprint `100×120`, offset `(0,0)`.
  - slab 1 (coluna): `y0=15, y1=altura_total`, footprint `merc_x×merc_y`, **centralizado** → offset `((100-merc_x)/2, (120-merc_y)/2)` (negativo quando excede, ex. −2 para 104).

Mudanças no motor:
- `findBestFit` valida que **todos os slabs** cabem no baú e não colidem com itens já posicionados em `placed`, checando colisão **por faixa de altura** (dois volumes só colidem se sobrepõem em X, em Z **e** em Y). Isso permite a coluna de um pallet invadir o **ar sobre o estrado** do vizinho (Y≥15) sem colidir, desde que **não atravesse** a coluna vizinha.
- `subtractBox` passa a subtrair **cada slab** do espaço livre (reusa a lógica atual por volume).

Disso o **caminho crítico emerge**: a distância mínima entre dois pallets vizinhos é `max(borda_estrado, (merc_A + merc_B)/2)`. Validação com o exemplo (P1 merc 104, P2 merc 90, estrados encostados na grade de 100): sobre o estrado de P2 → `2 (coluna P1) + 3 livre + 90 (P2) + 5 livre = 100` ✓ — "sobrepondo mas nunca atravessando". Dois pallets de 104 (média 104 > 100) afastam os estrados em 4cm; não cabem encostados.

`MAX_ITEMS` (hoje 200, `bin-packer.js:31`) cobre pallets+motos de um veículo; o modo D pode gerar muitos pallets — `palletizacao_service` retorna a contagem e a UI avisa se exceder.

### Regra "Nacom embaixo"

Garantida pela **ordem de empacotamento em duas fases**:
1. Empacota **todos os pallets primeiro** (orientação única; por padrão só Y=0). Ocupam o fundo-baixo do baú.
2. Empacota as **motos** no espaço livre restante (4 orientações, regras de apoio atuais).

Como os pallets já estão posicionados quando as motos entram, **nenhuma moto fica sob um pallet** (o volume já está ocupado). Motos podem ficar no chão **ao lado** de pallets (chão livre) — permitido; a restrição é só "moto nunca sob pallet". O `packOptimized` (SA, l.72) roda sobre a ordem **dentro de cada fase**, preservando a invariante de fases.

### Pallet sobre pallet

Flag opcional. Quando ligada, a fase 1 permite empilhar pallet sobre pallet (Y>0) usando as regras de apoio existentes (`getSupportPercentage`, l.300); o nível de cima soma **+15cm** (estrado PBR) acima do topo da mercadoria do nível de baixo. Quando desligada (default), pallets ficam em camada única de piso (Y=0).

## Flags da tela

Só o modo **A** nasce ligado; o resto é toggle que o operador ativa por carga. Partial novo `app/templates/carvia/simulador/_pallet_controls.html` (espelhando `_pack_controls.html` existente):

| Flag | Default | Efeito |
|------|---------|--------|
| Modo de agrupamento | **A — pedido** | A pedido / B CNPJ / C remontagem / D lote |
| Separado por pallet (B/C) | off | on = grupos não dividem pallet (separação lógica) |
| Overbooking do limite | off | on = até +50% sobre `palletizacao` (slider 0–50%) |
| Pallet sobre pallet | off | on = empilha pallet, +15cm/nível |
| Folga de lastro | 5cm | margem de excesso da mercadoria sobre o estrado |

## Rotas / API

Estender `app/carvia/routes/simulador_routes.py`:

- **`GET /carvia/api/simulador-carga/pallets-por-separacao?lote=<id>&modo=A&overbooking=0&...`** → roda `palletizacao_service` e devolve `{pallets:[...], pendencias:[...], resumo:{n_pallets, peso_total}}`. Recalculado quando o operador muda flags (a montagem é barata; fica no backend para manter a regra testável).
- **Modo embarque (misto):** estender `_resolver_dados_embarque` (l.189) para, além das motos CarVia, coletar os `EmbarqueItem` Nacom (`separacao_lote_id` começando com `LOTE_`, FONTE: `app/embarques/models.py:387`), resolver as Separações correspondentes e montar pallets. O JSON de init passa a conter `{veiculo, motos:[...], pallets:[...]}`.

O veículo continua vindo de `Embarque.modalidade` → `Veiculo` (`_veiculo_data_por_nome`, l.317) ou do seletor no modo livre.

## Render

Estender `carga-renderer.js`:
- Pallet renderizado como **dois box**: estrado `100×120×15` (cinza PBR) + coluna `merc_x×merc_y×altura_merc` (cor do grupo), com a coluna centralizada e podendo exceder o estrado.
- Legenda por **grupo** (pedido/CNPJ/produto conforme modo), reusando o esquema de cores atual.
- Motos inalteradas. Filtro/realce por grupo no `simulador-ui.js`.

## Arquivos

**Criar:**
1. `app/carteira/services/palletizacao_service.py` — montagem de pallets (Camada 1), função pura + constantes.
2. `app/templates/carvia/simulador/_pallet_controls.html` — partial das flags.
3. `tests/carteira/test_palletizacao_service.py` — testes pytest da Camada 1.

**Modificar:**
4. `app/carvia/routes/simulador_routes.py` — endpoint `pallets-por-separacao` + Nacom no modo embarque (`_resolver_dados_embarque`).
5. `app/static/js/simulador-carga/bin-packer.js` — perfil multi-slab, colisão por altura, orientação única de pallet, empacotamento em 2 fases.
6. `app/static/js/simulador-carga/carga-renderer.js` — render estrado + coluna.
7. `app/static/js/simulador-carga/simulador-ui.js` — flags, merge pallets+motos, legenda por grupo.
8. `app/static/js/simulador-carga/bin-packer.test.js` — casos do caminho crítico.
9. `app/templates/carvia/simulador/simulador_livre.html` e `simulador_embarque.html` — seletor de separação + inclusão do partial.
10. `app/static/css/modules/_simulador_carga.css` — estilo do estrado/coluna e dos novos controles.

## Plano de testes

**Camada 1 (pytest, `test_palletizacao_service.py`):**
- Pallet fechado: `palletizacao=64`, `qtd=128` → 2 pallets fechados, 0 fração.
- Fração com overbooking off vs on (50%).
- Agrupamento de 2 produtos de mesma dimensão numa fração (ex.: 56+56).
- Lastro/altura do item `4830103` → lastro 16, `merc 104×104`, altura conforme camadas.
- Modos A/B/C/D: partição correta dos escopos; separado-por-pallet on/off.
- Produto sem dimensão → entra em `pendencias`, não quebra.

**Camada 2 (node, `bin-packer.test.js`):**
- Caminho crítico: P1 merc 104 + P2 merc 90 cabem encostados (grade 100); dois de 104 não.
- "Nacom embaixo": com pallets + motos, nenhuma moto tem pallet acima dela.
- Pallet sobre pallet on: +15cm por nível, apoio respeitado; off: só Y=0.
- Regressão: carga só de motos produz layout idêntico ao atual (perfil 1-slab).

## Fora de escopo

- Pallet-divisor físico (vazio) — explicitamente descartado (rouba espaço de moto).
- Persistir o resultado da simulação (continua efêmero, como hoje).
- Editar dimensões de caixa/`palletizacao` pela tela — usa o cadastro existente.
- Empilhamento de moto sobre conserva (proibido pela regra de prioridade).
- Op. Assai no mesmo embarque (invariante de não-mistura, `app/fretes/routes.py:4433`).

## Pontos em aberto / riscos

1. **CNPJ do modo B:** `cnpj_cpf` (assumido) vs `cnpj_endereco_ent`. Confirmar com o usuário.
2. **Complexidade do multi-slab:** generalizar `findBestFit`/`subtractBox` para colisão por altura é a parte mais arriscada; mitigada por testes do caminho crítico e pela regressão moto-only (perfil 1-slab deve reproduzir o layout atual).
3. **Volume de itens no modo D:** muitos pallets podem aproximar `MAX_ITEMS=200`; a UI avisa e o `palletizacao_service` reporta a contagem.
4. **Performance do SA com 2 fases:** o orçamento atual (160 iters / 1500ms, l.75-76) é por fase; avaliar se o total no browser segue aceitável com cargas grandes.
