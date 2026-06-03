<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Margem e Custeio

> **Papel:** Margem e Custeio.

## Indice

- [Formula da Margem Bruta](#formula-da-margem-bruta)
- [Formula da Margem Liquida](#formula-da-margem-liquida)
  - [Caso especial: BONIFICACAO](#caso-especial-bonificacao)
  - [Campo pre-calculado](#campo-pre-calculado)
- [Tabelas de Custeio](#tabelas-de-custeio)
  - [CustoConsiderado (tabela `custo_considerado`)](#custoconsiderado-tabela-custo_considerado)
  - [CustoFrete (tabela `custo_frete`)](#custofrete-tabela-custo_frete)
  - [CustoMensal (tabela `custo_mensal`)](#customensal-tabela-custo_mensal)
  - [ParametroCusteio (tabela `parametro_custeio`)](#parametrocusteio-tabela-parametro_custeio)
  - [RegraComissao (tabela `regra_comissao`)](#regracomissao-tabela-regra_comissao)
- [Consultas Uteis](#consultas-uteis)
  - [Margem de um pedido](#margem-de-um-pedido)
  - [Custo atual de um produto](#custo-atual-de-um-produto)
  - [Percentual de frete por UF](#percentual-de-frete-por-uf)
  - [Produtos sem custo cadastrado (potenciais margens NULL)](#produtos-sem-custo-cadastrado-potenciais-margens-null)
  - [Saude do custeio (dormencia)](#saude-do-custeio-dormencia)
- [Pontos de atencao para mantenedores](#pontos-de-atencao-para-mantenedores)

Documentacao da composicao de margem bruta/liquida e tabelas de custeio.

> **Atualizado em 2026-05-10** apos auditoria — esclarecimentos sobre ICMS-ST,
> BONIFICACAO, tipos de custo `MANUAL` e `PRODUCAO`, e estado atual do pipeline.
> **Revisao 2026-06-01**: corrigidas refs de linha/caminho de `custeio_service.py`
> (vive em `app/custeio/services/`, nao `app/carteira/services/`) e bloco BONIFICACAO.

---

## Formula da Margem Bruta

Calculo POR UNIDADE (impostos divididos por `qtd_produto_pedido`):

```
Margem Bruta = preco_produto_pedido
             - icms_valor / qtd
             - pis_valor / qtd
             - cofins_valor / qtd
             - CustoConsiderado * (1 + PERCENTUAL_PERDA / 100)
             - (desconto_percentual / 100) * preco
             - (frete_percentual_vigente / 100) * preco         # CustoFrete por incoterm/UF
             - (CUSTO_FINANCEIRO_PERCENTUAL / 100) * preco
             - (comissao_percentual / 100) * preco              # RegraComissao ou COMISSAO_PADRAO
```

> **ICMS-ST NAO entra**. No Odoo `l10n_br`, `price_unit` (mapeado para
> `preco_produto_pedido`) e o preco da mercadoria com **ICMS proprio "por dentro"**
> mas **SEM ICMS-ST**. O `icmsst_valor` e cobrado adicional do cliente e repassado
> a SEFAZ — nao sai do caixa Nacom. Subtrair seria duplicar a deducao.
> FONTE: `app/odoo/services/carteira_service.py:949` (mapeamento price_unit).

## Formula da Margem Liquida

```
Margem Liquida = Margem Bruta
              - (CUSTO_OPERACAO_PERCENTUAL / 100) * preco
              - custo_producao * (1 + PERCENTUAL_PERDA / 100)
```

### Caso especial: BONIFICACAO

Quando `forma_pgto_pedido = 'SEM PAGAMENTO'`:

```
Margem Bruta (bonificacao) = - CustoConsiderado * (1 + PERCENTUAL_PERDA / 100)
                             - icms_valor / qtd
                             - (CUSTO_FINANCEIRO_PERCENTUAL / 100) * preco
                             - (frete_percentual / 100) * preco
```

Notas:
- Sem PIS/COFINS, sem desconto, sem comissao (zerada).
- Margem Liquida usa a mesma formula geral (subtrai operacao + producao).
- FONTE: `carteira_service.py:1376` (bloco `# VERIFICAR SE E BONIFICACAO`, flag `eh_bonificacao` em :1379).

### Campo pre-calculado

`CarteiraPrincipal.margem_bruta` contem a margem ja calculada para cada linha de pedido.

**A margem e calculada**:
- Em **INSERT** (sync inicial de pedido novo).
- Em **UPDATE** quando algum dos campos relevantes muda (preco, qtd, UF, incoterm, ICMS, PIS, COFINS, desconto, forma_pgto, vendedor, cnpj). FONTE: `carteira_service.py:2625-2700`.

Para forcar recalculo manual: `POST /custeio/api/margem/recalcular`.

---

## Tabelas de Custeio

### CustoConsiderado (tabela `custo_considerado`)

Custo unitario do produto usado para calculo de margem.

- `cod_produto` — codigo do produto
- `tipo_produto` — `COMPRADO`, `INTERMEDIARIO`, `ACABADO` (CHECK constraint, Sprint 2)
- `custo_atual = TRUE` — versao vigente (partial UNIQUE garante 1 registro por produto, Sprint 2)
- `tipo_custo_selecionado` — fonte do `custo_considerado`:
  - `MEDIO_MES` — custo medio do ultimo mes fechado
  - `ULTIMO_CUSTO` — ultima compra do mes
  - `MEDIO_ESTOQUE` — custo medio do estoque
  - `BOM` — calculado via lista de materiais
  - `MANUAL` — cadastrado manualmente via UI/importacao Excel
  - `PRODUCAO` — focado em `custo_producao` (preserva `custo_considerado` anterior)
- `custo_considerado` — valor efetivamente usado na margem
- `custo_producao` — custo de mao de obra direta (entra apenas na margem liquida)
- Versionamento: `versao` + `vigencia_inicio` + `vigencia_fim` + `motivo_alteracao`

> **PROTECAO MANUAL/PRODUCAO**: ao mudar de MANUAL/PRODUCAO para outro tipo, o
> sistema valida que o tipo destino tem valor preenchido. Se nao tem, o servico
> retorna erro impedindo perda silenciosa do custo cadastrado.
> FONTE: `app/custeio/services/custeio_service.py:827-841` (Sprint 1 - C2).

### CustoFrete (tabela `custo_frete`)

Percentual de frete sobre valor de venda.

- `incoterm` — CIF, FOB, RED
- `cod_uf` — UF de destino
- `percentual_frete` — % aplicado sobre valor venda (CHECK 0-100, Sprint 2)
- Vigencia: `vigencia_inicio` + `vigencia_fim` (CHECK fim > inicio, Sprint 2)
- Sobreposicao bloqueada no backend (Sprint 2 - C11)

### CustoMensal (tabela `custo_mensal`)

Historico mensal de custos por produto (populado pelo cron de fechamento).

- `ano`, `mes`, `cod_produto` — UNIQUE
- `custo_liquido_medio`, `custo_medio_estoque`, `ultimo_custo`, `custo_bom`
- `status` — `ABERTO` ou `FECHADO` (CHECK constraint, Sprint 2)

> **Fechamento mensal e AUTOMATICO** via cron WSL2 (dia 5 as 04:00).
> Endpoint manual `POST /custeio/api/mensal/fechar` exige header
> `X-Cron-Source: fechar_mes_automatico` (Sprint 1 - C6).
> Tela `/custeio/mensal` permite apenas SIMULACAO.

### ParametroCusteio (tabela `parametro_custeio`)

Parametros globais.

- `chave` (UNIQUE) — `CUSTO_OPERACAO_PERCENTUAL`, `CUSTO_FINANCEIRO_PERCENTUAL`, `PERCENTUAL_PERDA`, `COMISSAO_PADRAO`.
- `valor` — numerico, validado por range no backend (Sprint 2 - C11):
  - Percentuais (PERCENTUAL_*, CUSTO_*): 0-100
  - COMISSAO_PADRAO: 0-30
- `descricao` — explicacao

### RegraComissao (tabela `regra_comissao`)

Regras de comissao com hierarquia de especificidade.

- `tipo_regra` — 7 tipos validos via CHECK (CLIENTE_PRODUTO, GRUPO_PRODUTO, VENDEDOR_PRODUTO, CLIENTE, GRUPO, VENDEDOR, PRODUTO)
- `comissao_percentual` — CHECK 0-30 (Sprint 2)
- Hierarquia (mais especifico ganha): CLIENTE_PRODUTO > GRUPO_PRODUTO > VENDEDOR_PRODUTO > CLIENTE > GRUPO > VENDEDOR > PRODUTO
- Fallback: `ParametroCusteio.obter_valor('COMISSAO_PADRAO', 3.0)` se nenhuma regra aplica

---

## Consultas Uteis

### Margem de um pedido
```sql
SELECT num_pedido, cod_produto, nome_produto,
       preco_produto_pedido, margem_bruta, margem_liquida,
       margem_bruta_percentual, margem_liquida_percentual
FROM carteira_principal
WHERE num_pedido = 'VCD123';
```

### Custo atual de um produto
```sql
SELECT cod_produto, nome_produto, tipo_custo_selecionado,
       custo_considerado, custo_medio_mes, ultimo_custo,
       custo_medio_estoque, custo_bom, custo_producao,
       atualizado_em, vigencia_inicio
FROM custo_considerado
WHERE cod_produto = 'PA001' AND custo_atual = TRUE;
```

### Percentual de frete por UF
```sql
SELECT cod_uf, incoterm, percentual_frete
FROM custo_frete
WHERE vigencia_fim IS NULL OR vigencia_fim >= CURRENT_DATE
ORDER BY cod_uf, incoterm;
```

### Produtos sem custo cadastrado (potenciais margens NULL)
```sql
SELECT cp.cod_produto, cp.nome_produto,
       cp.produto_comprado, cp.produto_produzido, cp.produto_vendido
FROM cadastro_palletizacao cp
WHERE cp.ativo = TRUE
  AND NOT EXISTS (
    SELECT 1 FROM custo_considerado cc
    WHERE cc.cod_produto = cp.cod_produto AND cc.custo_atual = TRUE
  );
```

### Saude do custeio (dormencia)
```sql
SELECT
  MAX(atualizado_em) AS ultima_atualizacao,
  EXTRACT(DAY FROM NOW() - MAX(atualizado_em)) AS dias_dormente,
  COUNT(*) AS produtos_custeados
FROM custo_considerado
WHERE custo_atual = TRUE;
```

---

## Pontos de atencao para mantenedores

1. **Custo manual/PRODUCAO preserva valor**: ao implementar nova rota que cria
   versao de CustoConsiderado, NUNCA chamar `recalcular_custo_considerado()` em
   produto MANUAL/PRODUCAO sem antes verificar que o tipo destino tem valor.
2. **N+1 em ParametroCusteio**: usar parametros_cache em batch quando processar
   alto volume de itens. Ver `_substituir_carteira_principal` (Sprint 2 - C13).
3. **Lock pessimista** ao criar nova versao: `with_for_update()` em
   `alterar_tipo_custo`, `cadastrar_custo_manual`, `_salvar_custo_propagado`.
4. **Soma parcial em propagar_custos_bom**: BOM com componente sem custo gera
   custo subestimado SEM warning. TODO: marcar BOM como "incompleto" quando
   detectado (`app/custeio/services/custeio_service.py:1140,1160` — "soma parcial").
5. **status_odoo='done' nao existe na tabela**: filtro `in_(['done','purchase'])`
   so captura `'purchase'`. Filtro vestigial mas funcional.
