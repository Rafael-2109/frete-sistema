# Reforma Modulo Pessoal — Controle Financeiro

**Data**: 2026-04-05
**Status**: Aprovado

## Contexto

O modulo `pessoal` foi criado como um conciliador de extratos Bradesco com auto-categorizacao via regex (5 camadas). Funciona bem para categorizar transacoes, mas falta controle financeiro: nao tem orcamento, nao tem dashboard de gastos, e tem campos inuteis como `ordem_exibicao`.

**Objetivo**: Transformar de "conciliador" em "controle financeiro pessoal" com:
1. Dashboard visual de gastos
2. Orcamento mensal (global + por categoria)
3. Conciliacao simplificada (manter motor backend, simplificar UI)

**Principio**: Sem over-engineering. Tudo wired e funcional.

---

## Decisoes de Design

| Decisao | Escolha | Motivo |
|---------|---------|--------|
| Tela principal | Dashboard visual | Usuario quer ver gastos vs orcamento ao abrir |
| Orcamento | Mensal global + categorias opcionais | Macro + detalhe |
| Conciliacao | Manter motor 5 camadas, simplificar UI | Motor funciona bem |
| Remover | Apenas `ordem_exibicao` | Resto esta ok |
| Visao membros | Consolidado familiar | Sem breakdown por pessoa no dashboard |
| Computacao | On-the-fly (SUM/GROUP BY) | ~200-500 transacoes/mes, indices existem |
| Filtro despesas | `excluir_relatorio=False` + excluir grupo "Receitas" | Flags existentes ja cobrem pagto cartao, transferencias, empresa |

---

## Schema

### Nova tabela: `pessoal_orcamentos`

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | Serial PK | — |
| `ano_mes` | Date | Primeiro dia do mes (ex: 2026-04-01) |
| `categoria_id` | FK nullable → pessoal_categorias | NULL = limite global |
| `valor_limite` | Numeric(15,2) | Valor do limite |
| `criado_em` | DateTime | agora_utc_naive() |
| `atualizado_em` | DateTime | agora_utc_naive() |

**Constraints**: `UNIQUE(ano_mes, categoria_id)` — nulls distintos (usar UNIQUE com COALESCE ou partial index)

### Remocao: `ordem_exibicao` de `pessoal_categorias`

Ordenacao passa a ser `grupo, nome` (alfabetica dentro do grupo).

---

## Arquivos Novos

| Arquivo | Proposito |
|---------|-----------|
| `app/pessoal/routes/dashboard.py` | Blueprint `pessoal_dashboard`. Rota GET + 3 endpoints API |
| `app/pessoal/routes/orcamento.py` | Blueprint `pessoal_orcamento`. Rota GET + 3 endpoints API |
| `app/pessoal/services/dashboard_service.py` | 3 funcoes de query: resumo, categorias, tendencia |
| `app/templates/pessoal/dashboard.html` | Chart.js + KPI cards + tabela resumo |
| `app/templates/pessoal/orcamento.html` | Formulario de limites mensais |
| `scripts/migrations/pessoal_orcamento.py` | Migration Python (add tabela + drop coluna) |
| `scripts/migrations/pessoal_orcamento.sql` | Migration SQL idempotente |

## Arquivos Modificados

| Arquivo | Mudanca |
|---------|---------|
| `app/pessoal/__init__.py` | Registrar `pessoal_dashboard` e `pessoal_orcamento` |
| `app/pessoal/models.py` | Adicionar `PessoalOrcamento`; remover `ordem_exibicao` de `PessoalCategoria` |
| `app/pessoal/routes/configuracao.py` | Remover handling de `ordem_exibicao` no CRUD |
| `app/pessoal/routes/transacoes.py` | Remover `ordem_exibicao` do order_by de categorias |
| `app/templates/pessoal/configuracao.html` | Remover coluna Ordem da tab Categorias + campo do modal |
| `app/templates/base.html` | Reestruturar menu Pessoal (5 itens + divider) |

---

## Dashboard (`GET /pessoal/dashboard`)

### Layout (top → bottom)

1. **Seletor de mes** — dropdown (mes/ano), default = mes atual

2. **KPI Cards** (4 cards em linha):
   - Total Despesas
   - Orcamento Global (limite - gasto = saldo)
   - Total Receitas
   - % Orcamento Usado (barra: verde < 80%, amarelo 80-100%, vermelho > 100%)

3. **Grafico de Barras Horizontal** — Gastos por Categoria
   - Cada barra = categoria com valor gasto
   - Linha de referencia do limite (se definido)
   - Ordenado por valor (maior primeiro)

4. **Grafico de Linha** — Tendencia Mensal (ultimos 6 meses)
   - Linha despesas vs linha orcamento global
   - Eixo X = meses, Eixo Y = R$

5. **Tabela Resumo** — Gastos por categoria
   - Colunas: Categoria | Grupo | Gasto | Limite | Saldo | % Usado
   - Sem limite → "—"
   - Badge: dentro/alerta/estourado

### Endpoints API

```
GET /pessoal/api/dashboard/resumo?mes=2026-04
    → {total_despesas, total_receitas, limite_global, saldo, percentual, delta_mes_anterior}

GET /pessoal/api/dashboard/categorias?mes=2026-04
    → [{categoria, grupo, icone, gasto, limite, percentual}, ...]

GET /pessoal/api/dashboard/tendencia?meses=6
    → [{mes, despesas, receitas, limite}, ...]
```

### Filtros de Query

- Despesas: `tipo='debito' AND excluir_relatorio=False`
- Receitas: `tipo='credito' AND excluir_relatorio=False`
- Agregacao: `SUM(valor) GROUP BY categoria_id` (indices existentes: `idx_pessoal_transacoes_data`, `idx_pessoal_transacoes_categoria`)

---

## Pagina de Orcamento (`GET /pessoal/orcamento`)

### Layout

1. **Seletor de mes**

2. **Limite Global** — input numerico
   - Ao lado: "Gasto atual: R$ X.XXX (Y%)"

3. **Tabela de Categorias** (apenas categorias de despesa, excluindo grupo "Receitas"):
   - Colunas: Grupo | Categoria | Gasto Mes Anterior | Gasto Mes Atual | Limite (input)
   - Inputs vazios = sem limite individual

4. **Acoes**:
   - Salvar (POST batch com todos os limites)
   - Copiar do mes anterior

### Endpoints API

```
GET /pessoal/api/orcamento?mes=2026-04
    → {limite_global, categorias: [{id, nome, grupo, gasto_anterior, gasto_atual, limite}]}

POST /pessoal/api/orcamento
    body: {ano_mes, limite_global, limites: [{categoria_id, valor_limite}]}
    → batch upsert

POST /pessoal/api/orcamento/copiar
    body: {mes_origem, mes_destino}
    → copia limites
```

---

## Navegacao (base.html)

```
Pessoal (fa-wallet)
  Dashboard          → pessoal.pessoal_dashboard.index
  Transacoes         → pessoal.pessoal_transacoes.listar
  ─────────
  Importar CSV       → pessoal.pessoal_importacao.importar
  Orcamento          → pessoal.pessoal_orcamento.index
  Configuracao       → pessoal.pessoal_configuracao.index
```

---

## Service Layer: `dashboard_service.py`

```python
def calcular_resumo_mensal(ano: int, mes: int) -> dict:
    """KPIs: total despesas/receitas, limite global, saldo, %, delta mes anterior."""

def gastos_por_categoria(ano: int, mes: int) -> list[dict]:
    """Gasto por categoria + limite do orcamento (se definido)."""

def tendencia_mensal(meses: int = 6) -> list[dict]:
    """Totais mensais dos ultimos N meses + limite global de cada mes."""
```

Todas as queries filtram `excluir_relatorio=False`. Reutilizam indices existentes em `data` e `categoria_id`.

---

## Fases de Implementacao

### Fase 1 — Schema + Migration
- Criar tabela `pessoal_orcamentos`
- Dropar coluna `ordem_exibicao` de `pessoal_categorias`
- 2 artefatos: `pessoal_orcamento.py` + `pessoal_orcamento.sql`

### Fase 2 — Modelo + Cleanup
- Adicionar `PessoalOrcamento` em `models.py`
- Remover `ordem_exibicao` de `PessoalCategoria`
- Limpar referencias em `configuracao.py`, `transacoes.py`, `configuracao.html`

### Fase 3 — Pagina de Orcamento
- `routes/orcamento.py` com GET + 3 endpoints
- `templates/pessoal/orcamento.html`
- Registrar blueprint em `__init__.py`

### Fase 4 — Dashboard
- `services/dashboard_service.py` (3 funcoes)
- `routes/dashboard.py` com GET + 3 endpoints API
- `templates/pessoal/dashboard.html` com Chart.js
- CSS em `css/modules/_pessoal.css` (se necessario)

### Fase 5 — Navegacao
- Reestruturar menu em `base.html`
- Dashboard como primeiro item

---

## Verificacao

1. **Migration**: rodar localmente, verificar tabela criada e coluna removida
2. **Orcamento**: definir limite global + 2-3 categorias, salvar, recarregar — dados persistem
3. **Dashboard**: importar CSV, categorizar transacoes, abrir dashboard — KPIs e graficos refletem dados reais
4. **Copiar mes**: definir orcamento em abril, copiar para maio — limites copiados corretamente
5. **Cleanup**: abrir Configuracao → tab Categorias → coluna Ordem nao existe mais
6. **Menu**: verificar 5 itens no dropdown Pessoal com divider entre visualizacao e setup
