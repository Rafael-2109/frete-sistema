# Carteira — Guia de Desenvolvimento

**LOC**: ~17.6K | **Arquivos**: 64 | **Atualizado**: 16/03/2026

Workspace principal do sistema de fretes. Exibe pedidos agrupados, gera separacoes,
analisa ruptura de estoque, programa lotes (Atacadao/Sendas) e gerencia standby.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Regras CarteiraPrincipal vs Separacao: `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`

---

## Estrutura

```
app/carteira/
  ├── routes/                    # 26 APIs + agrupados.py
  │   └── programacao_em_lote/   # 4 arquivos (Atacadao/Sendas)
  ├── services/                  # 4 services (agrupamento, mapa, importacao, atualizacao)
  ├── utils/                     # 3 helpers (separacao, workspace, formatters)
  ├── models.py                  # 7 models (703 linhas)
  ├── models_alertas.py          # AlertaSeparacaoCotada
  ├── models_adapter_presep.py   # Adapter PreSeparacaoItem -> Separacao
  └── main_routes.py             # Apenas dashboard index() — NAO adicionar novas rotas
```

**Templates**: 13 HTML em `app/templates/carteira/`
**JavaScript**: 21 arquivos em `app/templates/carteira/js/`
**CSS**: `app/static/css/modules/_carteira.css` + `carteira/carteira-simples.css`

---

## Regras Criticas

### R1: CarteiraPrincipal NAO tem campos de separacao
`expedicao`, `agendamento`, `protocolo`, `agendamento_confirmado`, `rota`, `sub_rota` e
`separacao_lote_id` foram REMOVIDOS de CarteiraPrincipal. Dados vem APENAS de `Separacao`.
Usar `agrupamento_service.py` que enriquece via batch queries.

### R2: main_routes.py contem apenas dashboard index()
189 linhas (limpo na Fase 3). NUNCA adicionar novas rotas em `main_routes.py`.
Novas rotas: criar arquivo em `routes/` e registrar em `routes/__init__.py`.

### R3: PreSeparacaoItem e um Adapter
`models_adapter_presep.py` redireciona para Separacao com `status='PREVISAO'`.
NUNCA importar de `pre_separacao_item` diretamente — usar adapter.

### R4: 11 Blueprints registrados em routes/__init__.py
Blueprint principal `carteira_bp` (`/carteira`) com sub-blueprints:
`carteira_simples_bp`, `standby_bp`, `importante_bp`, `views_nao_odoo_bp`,
`programacao_em_lote_bp`, `alertas_visualizacao_bp`, etc.
Verificar `routes/__init__.py` ANTES de criar novo blueprint.

### R5: agrupamento_service.py usa batch queries (3 queries vs N+1)
`obter_pedidos_agrupados()` carrega rotas, subrotas e separacoes em batch.
NUNCA adicionar queries individuais por pedido no loop de enriquecimento.
Novo dado necessario: adicionar ao batch loading (`_carregar_*_batch`).

### R6: carteira_simples_api.py e monolito (2.3K LOC)
NUNCA adicionar mais endpoints neste arquivo. Novas APIs: criar arquivo separado em `routes/`.

### R7: 2 variantes de ruptura — escolher a correta

| Variante | Arquivo | Quando usar |
|----------|---------|-------------|
| Com cache | `ruptura_api.py` (667L) | Consulta rapida, dados podem ter delay |
| Sem cache | `ruptura_api_sem_cache.py` (575L) | Dados criticos em tempo real |

### R8: Template usa `data-pedido` (NAO `data-num-pedido`)
`agrupados_balanceado.html` usa `data-pedido="{{ pedido.num_pedido }}"`.
No JS, SEMPRE usar `row.dataset.pedido || row.dataset.numPedido` como fallback.
NUNCA usar apenas `dataset.numPedido` — sera `undefined`.

### R9: POSTs AJAX precisam de X-CSRFToken
Todas requisicoes POST/PUT/DELETE devem incluir:
```javascript
headers: { 'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || '' }
```

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarteiraPrincipal | `carteira_principal` | `qtd_saldo_produto_pedido` (NAO `qtd_saldo`). SEM campos de separacao (R1) |
| CarteiraCopia | `carteira_copia` | Espelho para nao-Odoo. Property `baixa_produto_pedido` via FaturamentoProduto |
| SaldoStandby | `saldo_standby` | Filtra pedido INTEIRO da agrupada quando status IN ('ATIVO','BLOQ. COML.','SALDO') |
| PreSeparacaoItem | _(adapter)_ | NAO e tabela real — usa Separacao com status='PREVISAO' (R3) |
| FaturamentoParcialJustificativa | `faturamento_parcial_justificativa` | Model existe em models.py mas API/tela removidos (Fase 3) |
| ControleCruzadoSeparacao | `controle_cruzado_separacao` | Detecta diferencas separacao <-> faturamento |

---

## Padroes do Modulo

### Enriquecimento de pedidos (agrupamento_service.py)
```
_query_agrupamento_base() -> batch load (rotas, subrotas, separacoes)
  -> _enriquecer_pedido_batch() para cada pedido -> sort por rota/subrota/cnpj
```
Adicionar novo campo: incluir na query base, no batch loading se necessario, e no dict de retorno.

### Resposta JSON padrao das APIs
```python
{"success": bool, "data": {}, "error": "mensagem"}
```

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/separacao/` | `Separacao` | Modelo principal de separacoes (R1) |
| `app/producao/` | `CadastroPalletizacao` | Peso, pallets — JOIN na query base |
| `app/estoque/` | `ServicoEstoqueSimples` | Projecao de estoque (29 dias) |
| `app/localidades/` | `CadastroRota`, `CadastroSubRota` | Batch-loaded em agrupamento_service |
| `app/portal/` | `GrupoEmpresarial` | Identifica Atacadao/Sendas por CNPJ |
| `app/models/` | `Embarque`, `FaturamentoProduto` | FK de embarques e faturamento |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/templates/carteira/` | Templates Jinja2 | 13 telas + 21 JS files |
| `app/odoo/jobs/` | CarteiraPrincipal model | Sincronizacao incremental importa model |

---

## Skills Relacionadas

| Skill | Opera neste modulo? | Referencia |
|-------|---------------------|-----------|
| `gerindo-expedicao` | Sim | `.claude/skills/gerindo-expedicao/SKILL.md` |
| `cotando-frete` | Parcial (usa rotas) | `.claude/skills/cotando-frete/SKILL.md` |
| `visao-produto` | Parcial (estoque) | `.claude/skills/visao-produto/SKILL.md` |
| `operando-portal-atacadao` | Sim (agendamento) | `.claude/skills/operando-portal-atacadao/SKILL.md` |
| `analise-carteira` | Sim | Subagente `analista-carteira` |
