# CarVia — Cotacao e Pricing

**Referenciado por**: `app/carvia/CLAUDE.md`

Fluxo de cotacao de frete CarVia: calculo via CidadeAtendida, categorias de moto, cotacoes comerciais e de rotas.

---

## Fluxo via CidadeAtendida

`CotacaoService` usa o MESMO fluxo do sistema principal:
```
Cidade nome + UF → buscar_cidade_unificada() → Cidade.codigo_ibge
→ CidadeAtendida → grupo_empresarial → TabelaFrete → TabelaFreteManager → CalculadoraFrete
```

**Reutiliza** (NAO cria novas utils):
- `buscar_cidade_unificada(cidade, uf)` de `app/utils/frete_simulador.py`
- `CidadeAtendida.query.filter(codigo_ibge)` de `app/vinculos/models.py`
- `GrupoEmpresarialService.obter_transportadoras_grupo()` de `app/utils/grupo_empresarial.py`
- `TabelaFreteManager.preparar_dados_tabela()` de `app/utils/tabela_frete_manager.py`
- `CalculadoraFrete.calcular_frete_unificado()` de `app/utils/calculadora_frete.py`

**Retorno enriquecido**: `lead_time` (do vinculo CidadeAtendida), `icms_destino` (da Cidade)
**Fallback**: Se cidade nao encontrada ou sem vinculos, busca por UF (comportamento anterior)

---

## Cotacao por Categoria de Moto (Preco por Unidade)

Empresas de moto podem ter preco fixo por unidade em vez de calculo por peso.
Deteccao automatica: se `categorias_moto` fornecido E tabela tem `CarviaPrecoCategoriaMoto`, usa preco por categoria.

```
CarviaTabelaService.cotar_carvia(categorias_moto=[{categoria_id, quantidade}]):
  1. Resolver grupo (existente)
  2. Buscar tabelas (existente)
  3. Para cada tabela:
     → TEM precos por categoria? → _calcular_por_categoria_moto()
     → NAO TEM → calcular_com_tabela_carvia() (peso, existente)
  4. Retorno inclui tipo_calculo: 'CATEGORIA_MOTO' | 'PESO'
```

**ICMS**: Aplicado sobre o total por categoria (mesma logica de `icms_incluso`/`icms_proprio`).
**Backward compat**: Tabelas sem `CarviaPrecoCategoriaMoto` continuam usando calculo por peso.

---

## Dois Tipos de Cotacao — Coexistem

| Feature | Modelo | Prefixo | Label UI | Uso |
|---------|--------|---------|----------|-----|
| Cotacao Comercial | `CarviaCotacao` | `COT-###` | "Cotacao Comercial" | Fluxo formal: cliente → pricing → desconto → aprovacao → pedido |
| Cotacao de Rotas | `CarviaSessaoCotacao` | `COTACAO-###` | "Cotacao de Rotas" | Ferramenta pontual: cotar rota para cliente sob demanda |

Ambos coexistem sem colisao de prefixo. NAO deprecar nenhum.

---

## Cotacao de Rotas (Ferramenta Comercial)

**Prefixo**: `COTACAO-###` (anteriormente SC-###, backfill aplicado)
**Campos contato cliente**: `cliente_nome`, `cliente_email`, `cliente_telefone`, `cliente_responsavel` (opcionais)
**Autocomplete cidade**: Via `GET /localidades/ajax/cidades_por_uf/<uf>` + cache client-side + filtro debounce 200ms

**Fluxo de status**:
```
RASCUNHO ── enviar ──> ENVIADO ── resposta ──> APROVADO
                                           └─> CONTRA_PROPOSTA (com valor)
CANCELADO <── cancelar (de qualquer estado exceto APROVADO)
```

**Rotas** (`sessao_cotacao_routes.py`):
- HTML: `GET /sessoes-cotacao` (listar), `GET|POST /sessoes-cotacao/nova`, `GET /sessoes-cotacao/<id>` (detalhe)
- HTML: `POST .../adicionar-demanda`, `POST .../remover-demanda/<did>`, `POST .../enviar`, `POST .../resposta`, `POST .../cancelar`
- API: `POST /api/sessao-cotacao/<id>/cotar-demanda/<did>` (retorna todas opcoes + lead_time + breakdown), `POST .../selecionar-opcao/<did>` (grava escolha)

**Validacoes**:
- Enviar: TODAS demandas devem ter frete selecionado
- Cancelar: bloqueado se APROVADO
- Contra proposta: `valor_contra_proposta` obrigatorio
- Remover demanda: bloqueado se for a unica
