# Simulador 3D de Carga de Motos — Design Spec

**Data**: 2026-04-03
**Status**: Aprovado

---

## Contexto

A CarVia transporta motos em diversos tipos de veiculos (Fiorino a Carreta). Hoje nao existe ferramenta visual para planejar a alocacao de motos no bau. O usuario precisa visualizar interativamente quantas motos cabem em cada veiculo, considerando dimensoes reais dos modelos cadastrados em `CarviaModeloMoto`.

## Objetivo

Criar um simulador 3D interativo que:
1. Permite ao usuario selecionar veiculo + N modelos de moto com quantidades
2. Calcula automaticamente o melhor arranjo (bin-packing 3D)
3. Renderiza o resultado em Three.js com camera orbital
4. Mostra metricas: motos posicionadas, rejeitadas, % ocupacao, peso total
5. Funciona em dois contextos: simulacao livre (CarVia) e embarque real

---

## Decisoes de Design

| Decisao | Escolha | Motivo |
|---------|---------|--------|
| Modelo de motos | `CarviaModeloMoto` | Ja possui comprimento/largura/altura em cm |
| Dimensoes veiculo | Adicionar ao modelo `Veiculo` | 3 campos Float (comprimento_bau, largura_bau, altura_bau) |
| Tecnologia 3D | Three.js via CDN | Leve (~170KB), camera orbital, raycasting, ecossistema maduro |
| Algoritmo | 3D Guillotine / Maximal Rectangles | Suporta empilhamento e 4 orientacoes, performante para <200 itens |
| Orientacoes | 4 por moto | Comprimento sempre horizontal; largura/altura intercambiaveis (deitada) |
| Empilhamento | Permitido | Se a altura residual comportar |
| Layout | Sidebar esquerda + Canvas 3D | Espaco para controles detalhados |
| Computacao | Client-side (JS) | Recalculo em tempo real sem roundtrip ao servidor |

---

## Arquitetura

### Backend (Flask — dados apenas)

**Rotas** (`app/carvia/routes/simulador_routes.py`):

| Metodo | URL | Retorno |
|--------|-----|---------|
| GET | `/carvia/simulador-carga` | Pagina HTML (simulador livre) |
| GET | `/carvia/embarques/<id>/simulador-carga` | Pagina HTML (embarque real) |
| GET | `/carvia/api/simulador-carga/catalogo` | JSON: veiculos com dims + modelos moto ativos |
| GET | `/carvia/api/simulador-carga/embarque/<id>` | JSON: veiculo + motos reais do embarque |

**API Catalogo** — resposta:
```json
{
  "veiculos": [
    {"id": 1, "nome": "CARRETA", "peso_maximo": 27000,
     "comprimento_bau": 1400, "largura_bau": 260, "altura_bau": 280}
  ],
  "modelos_moto": [
    {"id": 3, "nome": "CG 160", "comprimento": 200, "largura": 74, "altura": 108,
     "peso_medio": 127.5}
  ]
}
```

**API Embarque** — resposta:
```json
{
  "embarque_id": 42,
  "veiculo": {"nome": "CARRETA", "comprimento_bau": 1400, "largura_bau": 260, "altura_bau": 280, "peso_maximo": 27000},
  "motos": [
    {"modelo_id": 3, "modelo_nome": "CG 160", "quantidade": 4,
     "comprimento": 200, "largura": 74, "altura": 108, "peso_medio": 127.5}
  ],
  "peso_total": 510.0,
  "items_sem_modelo": 2
}
```

**Resolucao de motos no embarque**: Usa `MotoRecognitionService` (regex_pattern) sobre descricoes de itens das NFs do embarque. Itens nao reconhecidos contados em `items_sem_modelo`.

**Resolucao de veiculo no embarque**: `embarque.modalidade` → `Veiculo.query.filter(nome=modalidade)`. Se veiculo nao encontrado ou sem dimensoes do bau, retorna erro com mensagem orientando configurar dimensoes.

### Migration

Adicionar ao modelo `Veiculo`:
- `comprimento_bau` Float nullable — comprimento interno do bau em cm
- `largura_bau` Float nullable — largura interna do bau em cm
- `altura_bau` Float nullable — altura interna do bau em cm
- Metodo `tem_dimensoes_bau()` → bool

Dois artefatos: `scripts/migrations/adicionar_dimensoes_bau_veiculo.py` + `.sql`

### Frontend (JavaScript — IIFE, sem bundler)

**`bin-packer.js`** — `window.BinPacker`

Algoritmo 3D Guillotine com Maximal Rectangles:
1. Inicia com 1 cuboid livre = bau inteiro
2. Para cada moto (ordenadas por volume decrescente — FFD):
   a. Gera 4 orientacoes validas (comprimento nunca vertical)
   b. Para cada cuboid livre, testa cada orientacao
   c. Prioriza: menor Y (chao primeiro), depois menor Z, depois menor X
   d. Ao posicionar, subdivide cuboid residual em ate 3 sub-cuboids
   e. Merge cuboids adjacentes para evitar fragmentacao
3. Retorna: `{ placed: [{moto, x, y, z, w, d, h, orientacao}], rejected: [moto] }`

As 4 orientacoes validas:
```
O1: (comprimento→X, largura→Z, altura→Y) — em pe, alinhada
O2: (comprimento→X, altura→Z, largura→Y) — deitada, alinhada
O3: (largura→X, comprimento→Z, altura→Y) — em pe, rotacionada 90
O4: (largura→X, altura→Z, comprimento→Y) — deitada e rotacionada (*excluida se comprimento > bau.altura*)
```
*Nota: O4 coloca comprimento na vertical — INVALIDA pela regra. Na pratica, temos 3 orientacoes validas + 1 condicional.*

Correcao: O4 correta seria `(altura→X, comprimento→Z, largura→Y)` — comprimento ao longo da profundidade, deitada lateralmente. Todas 4 mantem comprimento horizontal.

**`carga-renderer.js`** — `window.CargaRenderer`

Three.js scene:
- `WebGLRenderer` com antialias
- `PerspectiveCamera` + `OrbitControls` (CDN)
- Bau: wireframe (`EdgesGeometry` + `LineSegments`), chao semi-transparente
- Motos: `BoxGeometry` com `MeshPhongMaterial`, cor por modelo (paleta de 8 cores), opacidade 0.85
- Iluminacao: `AmbientLight(0.6)` + `DirectionalLight(0.8)`
- Vistas preset: Frontal, Lateral, Topo, 3D (com animacao de transicao)
- Dark/light: escuta `themechange`, ajusta clearColor e cores de wireframe
- `dispose()` para cleanup de memoria

**`simulador-ui.js`** — controlador (sem export)

- `init()` no DOMContentLoaded
- Fetch catalogo → popula selects
- Event listeners em vehicle select e campos de quantidade
- Debounce 200ms no recalculo
- Fluxo: coletar form → `BinPacker.pack()` → `CargaRenderer.render()` → atualizar stats DOM

### CSS

`app/static/css/modules/_simulador_carga.css` dentro de `@layer modules`:
- `.simulador-container` — flex layout sidebar + canvas
- `.simulador-sidebar` — overflow-y auto, padding, border
- `.simulador-canvas-wrap` — flex:1, position:relative, min-height:500px
- `.simulador-moto-row` — card com cor de borda por modelo
- `.simulador-stats` — grid 2x2 com cards de metrica
- `.simulador-views` — botoes de vista preset
- `.simulador-legend` — legenda flutuante sobre o canvas
- Todos os valores usando design tokens (`var(--bg)`, `var(--text)`, etc.)

### Templates

**`simulador_livre.html`**:
- Extends `base.html`
- Quick nav com `carvia_active = 'simulador'`
- Sidebar: select veiculo, linhas de moto (dinamicas), stats
- Canvas: container para Three.js
- Scripts: Three.js CDN + OrbitControls CDN + 3 JS locais

**`simulador_embarque.html`**:
- Extends `base.html`
- Header com dados do embarque (read-only)
- Warning se itens sem modelo reconhecido
- Mesmo canvas/JS, mas dados injetados via `<script id="simulador-init-data" type="application/json">`

---

## Navegacao

- Link no quick nav CarVia (entre "Gerencial" e "Config")
- Link no menu base.html sob CarVia (seção dropdown)
- Na tela de detalhe do embarque, botao "Simulador de Carga 3D" (se veiculo tem dimensoes)

---

## Arquivos

### Criar (9 arquivos)

1. `app/carvia/routes/simulador_routes.py` — rotas + APIs
2. `app/static/js/simulador-carga/bin-packer.js` — algoritmo packing
3. `app/static/js/simulador-carga/carga-renderer.js` — Three.js renderer
4. `app/static/js/simulador-carga/simulador-ui.js` — controlador UI
5. `app/static/css/modules/_simulador_carga.css` — estilos do modulo
6. `app/templates/carvia/simulador/simulador_livre.html` — pagina simulador livre
7. `app/templates/carvia/simulador/simulador_embarque.html` — pagina embarque
8. `scripts/migrations/adicionar_dimensoes_bau_veiculo.py` — migration Python
9. `scripts/migrations/adicionar_dimensoes_bau_veiculo.sql` — migration SQL

### Modificar (6 arquivos)

1. `app/veiculos/models.py` — 3 campos Float + `tem_dimensoes_bau()`
2. `app/veiculos/routes.py` — aceitar/salvar/retornar campos de dimensao
3. `app/templates/veiculos/admin_veiculos.html` — campos de dimensao nos modais
4. `app/carvia/routes/__init__.py` — registrar simulador_routes
5. `app/static/css/main.css` — import `_simulador_carga.css`
6. `app/templates/carvia/_quick_nav.html` — link do simulador

---

## Verificacao

1. **Cadastrar dimensoes**: Editar veiculo CARRETA com dims (1400x260x280cm), confirmar que persiste
2. **Simulador livre**: Abrir `/carvia/simulador-carga`, selecionar CARRETA, adicionar 10 Pop 110i + 5 CG 160
   - Verificar: cena 3D renderiza, motos coloridas por modelo, stats corretos
   - Rotacionar camera, testar vistas preset
   - Alterar quantidade e verificar recalculo em tempo real
3. **Empilhamento**: Adicionar motos suficientes para forcar empilhamento vertical
4. **Motos rejeitadas**: Adicionar mais motos do que cabe, verificar contagem de "nao couberam"
5. **Dark/light mode**: Alternar tema, verificar cores do canvas se adaptam
6. **Embarque**: Criar/usar embarque com motos, verificar auto-deteccao via regex
7. **Responsividade**: Redimensionar janela, canvas deve se ajustar
