# REGRAS DE NEGOCIO DOS MODELOS - REFERENCIA

**Ultima Atualizacao**: 07/02/2026
**Uso**: Regras de negocio, gotchas e comportamentos especiais dos modelos secundarios
**Fonte de verdade para campos**: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

> **NOTA**: Para regras de **CarteiraPrincipal** e **Separacao** (mais usados),
> consulte `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`

---

## Pedido (app/pedidos/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/pedidos.json`

### E UMA VIEW (nao tabela)
```python
__table_args__ = {'info': {'is_view': True}}
```

### REGRA DA VIEW:
- **IGNORA**: Separacao com status='PREVISAO'
- **AGREGA**: Por separacao_lote_id e num_pedido
- **INCLUI**: Apenas status != 'PREVISAO'

---

## PreSeparacaoItem (app/carteira/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/pre_separacao_items.json`

### DEPRECATED - NAO USAR!
SEMPRE substituir por Separacao com status='PREVISAO' para fazer tudo que PreSeparacaoItem fazia.

---

## Embarque (app/embarques/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/embarques.json`

### Regras de Status
- `draft`: Rascunho, pode ser editado
- `ativo`: Embarque ativo, em operacao
- `cancelado`: Embarque cancelado (requer motivo)

### Tipos de Carga
- `FRACIONADA`: Cotacao por EmbarqueItem (cada item tem cotacao_id)
- `DIRETA`: Cotacao unica no Embarque (embarque.cotacao_id)

### EmbarqueItem

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/embarque_items.json`

---

## FaturamentoProduto (app/faturamento/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/faturamento_produto.json`

### GOTCHAS CRITICOS (naming traps):
- Usa `cnpj_cliente` (NAO `cnpj_cpf`)
- Usa `nome_cliente` (NAO `razao_social` nem `raz_social_red`)
- Campo `origem` = numero do pedido de venda (NAO indica sistema de origem)

### Regras de Status NF:
- `Lancado`: NF ativa
- `Cancelado`: NF cancelada
- `Provisorio`: NF provisoria (aguardando confirmacao)

### Reversao de NF (Nota de Credito):
- `revertida=True`: Esta NF foi anulada por nota de credito
- `nota_credito_id`: Aponta para a NF de credito que reverteu
- `data_reversao`: Timestamp da reversao

---

## RelatorioFaturamentoImportado (app/faturamento/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/relatorio_faturamento_importado.json`

### Regra: `numero_nf` eh UNIQUE — um registro por NF (resumo da NF inteira, nao por produto)

---

## DespesaExtra (app/fretes/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/despesas_extras.json`

### GOTCHAS CRITICOS (naming traps):
- Usa `valor_despesa` (NAO `valor`)
- Usa `criado_em` (NAO `data_lancamento`)
- `numero_nfd` eh cache do numero para exibicao (fonte real eh NFDevolucao.numero_nfd)

### REGRAS DE STATUS (5 estados):
1. **PENDENTE**: Despesa criada, aguardando processamento
2. **VINCULADO_CTE**: CTe Complementar vinculado, pronto para Odoo
3. **LANCADO_ODOO**: Lancado com sucesso no Odoo (16 etapas)
4. **LANCADO**: Finalizado sem Odoo (NFS/Recibo)
5. **CANCELADO**: Despesa cancelada

### Transportadora Override:
- Se `transportadora_id` NULL → usar transportadora do frete
- Se preenchido → usar esta (ex: devolucao coletada por outro)

### Logica de Sugestao de CTe (3 prioridades):
1. CTe Complementar que referencia CTe vinculado ao Frete da Despesa
2. CTe Complementar que referencia CTe com NFs em comum com Frete
3. CTe Complementar com mesmo CNPJ cliente + prefixo transportadora

---

## CadastroPalletizacao (app/producao/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/cadastro_palletizacao.json`

### Formulas de Calculo:
- **Pallets**: `quantidade / palletizacao`
- **Peso total**: `quantidade * peso_bruto`

### Classificacao do Produto:
- `produto_comprado`: Produto comprado (nao produzido)
- `produto_produzido`: Produzido internamente
- `produto_vendido`: Vendido ao cliente (vs. intermediario)

---

## ContasAReceber (app/financeiro/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/contas_a_receber.json`

### CHAVE UNICA: empresa + titulo_nf + parcela

### Regras de Reconciliacao:
- `valor_titulo` = `valor_original` - `desconto` - SUM(abatimentos)
- `liberacao_prevista_antecipacao`: Calculada via LiberacaoAntecipacao + EntregaMonitorada

### Campos que NAO sao colunas (obtidos via relacionamento):
- `data_entrega_prevista`, `data_hora_entrega_realizada`, `status_finalizacao`
- `nova_nf`, `reagendar`, `data_embarque`, `transportadora`, `vendedor`
- `canhoto_arquivo`, `nf_cd`, `ultimo_agendamento_*`
- Todos via `entrega_monitorada` (FK `entrega_monitorada_id`)

### Property calculada (NAO coluna):
- `nf_cancelada`: @property que busca FaturamentoProduto.status_nf == 'Cancelado'

---

## LiberacaoAntecipacao (app/financeiro/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/liberacao_antecipacao.json`

### PRIORIDADE DE MATCH (3 niveis):
1. `prefixo_cnpj` (8 primeiros digitos do CNPJ)
2. `nome_exato` (razao social exata)
3. `contem_nome` (contem substring)

### Metodos Uteis:
- `buscar_configuracao(cnpj, razao_social, uf)` — Busca por prioridade
- `calcular_data_liberacao(data_entrega, dias_uteis)` — Calcula data
- `extrair_prefixo_cnpj(cnpj)` — Extrai 8 primeiros digitos

---

## ContasAReceberAbatimento (app/financeiro/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/contas_a_receber_abatimento.json`

### Regra: Abatimentos 1:N vinculados a ContasAReceber
- `previsto=True`: Abatimento previsto (projecao)
- `previsto=False`: Abatimento ja realizado

---

## ContasAReceberTipo (app/financeiro/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/contas_a_receber_tipos.json`

### Regra: Tabela de dominio para 2 tabelas e 4 campos
- `tabela`: `contas_a_receber` ou `contas_a_receber_abatimento`
- `campo`: `confirmacao`, `forma_confirmacao`, `acao_necessaria`, `tipo`
- `considera_a_receber`: Se considera na projecao de recebiveis

---

## ContasAReceberSnapshot (app/financeiro/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/contas_a_receber_snapshots.json`

### Regra: Historico de alteracoes em campos vindos do Odoo
- `valor_anterior` e `valor_novo`: Armazenados como JSON string
- Metodo: `registrar_alteracao(conta, campo, valor_anterior, valor_novo, usuario, odoo_write_date)`

---

## Tabelas Auxiliares

### MovimentacaoEstoque (app/estoque/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/movimentacao_estoque.json`

**Calculo de estoque atual**: `SELECT SUM(qtd_movimentacao) FROM movimentacao_estoque WHERE cod_produto = ? AND ativo = True`

Tipos: ENTRADA, SAIDA, AJUSTE, COMPRA

### ProgramacaoProducao (app/producao/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/programacao_producao.json`

### ContatoAgendamento (app/cadastros/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/contato_agendamento.json`

**Valores de `forma`**: `SEM AGENDAMENTO`, `Portal`, `Telefone`, `E-mail`, `WhatsApp` (NULL = sem agendamento)

### CidadeAtendida / CadastroSubRota (app/cotacao/models.py)

> Campos completos: ver schemas em `.claude/skills/consultando-sql/schemas/tables/`

---

## Devolucoes (app/devolucao/models.py)

> **Documentacao completa**: `app/devolucao/README.md`

### NFDevolucao

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/nf_devolucao.json`

**Status**: REGISTRADA -> VINCULADA_DFE -> EM_TRATATIVA -> FINALIZADA

### OcorrenciaDevolucao

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/ocorrencia_devolucao.json`

**Status**: ABERTA -> EM_ANALISE -> RESOLVIDA
**Destino**: RETORNO, DESCARTE
**Localizacao**: CLIENTE, EM_TRANSITO, CD
**Responsavel**: NACOM, TRANSPORTADORA, CLIENTE

### DeParaProdutoCliente

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/depara_produto_cliente.json`

**Constraint unica**: prefixo_cnpj + codigo_cliente
**Uso**: Mapeamento codigo do cliente → nosso codigo interno (com fator de conversao)
