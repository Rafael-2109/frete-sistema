# TODO: Perguntas de Usuarios NAO Cobertas pelas Skills

**Criado em**: 05/02/2026
**Status**: Brainstorm aprovado, aguardando priorizacao para implementacao

---

## GAP ESTRUTURAL #1: Nenhuma skill cruza a fronteira pre/pos-faturamento

A linha divisoria e `Separacao.sincronizado_nf`. `gerindo-expedicao` opera ANTES, `monitorando-entregas` opera DEPOIS. Perguntas que cruzam essa fronteira ficam sem resposta.

---

## DOMINIO 1: CADEIA COMPLETA DO PEDIDO (Pedido -> Embarque -> Entrega)

### 1.1 "Qual o status completo do pedido VCD123?" (RAIO-X)
- **Frequencia**: DIARIA | **Complexidade**: 5+ tabelas
- **Path**: `CarteiraPrincipal(num_pedido)` -> `Separacao(num_pedido)` -> `EmbarqueItem(separacao_lote_id)` -> `Embarque(id)` -> `FaturamentoProduto(numero_nf)` -> `EntregaMonitorada(numero_nf)`
- **Gap**: Nenhuma skill conecta pedido->separacao->embarque->faturamento->entrega em resposta unica

### 1.2 "Quando entrega o pedido VCD123?"
- **Frequencia**: DIARIA | **Complexidade**: 4-5 tabelas + logica condicional
- **Path CASO 1** (nao faturado): `Separacao(sincronizado_nf=False)` -> `expedicao + lead_time teorico`
- **Path CASO 2** (faturado): `Separacao(numero_nf)` -> `EntregaMonitorada(numero_nf)` -> `data_entrega_prevista` ou `AgendamentoEntrega(data_agendada)`
- **Gap**: Nenhuma skill responde "quando entrega o pedido X" cruzando a barreira pre/pos-faturamento

### 1.3 "Quanto custou o frete do pedido VCD123?"
- **Frequencia**: SEMANAL | **Complexidade**: 5+ tabelas
- **Path**: `Separacao(num_pedido)` -> `EmbarqueItem(separacao_lote_id)` -> `Embarque(id)` -> `Frete(embarque_id)` -> `valor_cotado, valor_cte, valor_pago` + `DespesaExtra(frete_id)`
- **Gap**: `cotando-frete` calcula preco TEORICO. Nenhuma skill mostra custo EFETIVO (cotado vs CTe vs pago + despesas extras)

### 1.4 "O que embarcou junto com o pedido VCD123?" (co-passageiros)
- **Frequencia**: SEMANAL | **Complexidade**: 3 tabelas
- **Path**: `Separacao(num_pedido)` -> `EmbarqueItem(separacao_lote_id)` -> `embarque_id` -> `EmbarqueItem(WHERE embarque_id=X)` -> clientes, pedidos, NFs, destinos, pesos
- **Gap**: Conceito de "co-passageiros de embarque" nao existe em nenhuma skill

### 1.5 "Historico completo de entregas do pedido VCD123"
- **Frequencia**: SEMANAL | **Complexidade**: 4+ tabelas
- **Path**: `FaturamentoProduto(origem='VCD123')` -> `numero_nf` -> `EntregaMonitorada(numero_nf)` -> `AgendamentoEntrega` + `EventoEntrega` + `ComentarioNF`
- **Gap**: `monitorando-entregas` parte da NF, nao do pedido. O campo `FaturamentoProduto.origem` (= num_pedido) e a chave, mas nenhuma skill usa esse caminho

### 1.6 "O que falta entregar do pedido VCD123?"
- **Frequencia**: DIARIA | **Complexidade**: 3-4 tabelas
- **Path**: `CarteiraPrincipal(num_pedido)` -> qtd total -> `FaturamentoProduto(origem='VCD123')` -> qtd faturada -> `EntregaMonitorada(entregue=True)` -> qtd entregue -> diferenca
- **Gap**: Nenhuma skill calcula "saldo a entregar" cruzando carteira + faturamento + entrega


### 1.7 "Quais pedidos do cliente X estao em transito?"
- **Frequencia**: DIARIA | **Complexidade**: 3 tabelas
- **Path**: `EntregaMonitorada(status_finalizacao IS NULL, data_embarque IS NOT NULL, nf_cd=False)` JOIN `FaturamentoProduto(numero_nf)` -> `origem` (= num_pedido)
- **Estados complementares**:
  - **Ainda nao saiu**: `EntregaMonitorada(data_embarque IS NULL, nf_cd=False)`
  - **NF no CD (voltou)**: `EntregaMonitorada(nf_cd=True)`
- **Gap**: `gerindo-expedicao` mostra pedidos em carteira. `monitorando-entregas` mostra NFs. Nenhuma skill mostra "pedidos em transito" por cliente

---

## DOMINIO 2: FRETE REAL (Historico Pago vs Teorico)

### 2.1 "Quanto gastei de frete com o cliente Atacadao este mes?"
- **Frequencia**: SEMANAL | **Complexidade**: 2-3 tabelas + grupo empresarial
- **Path**: `resolvendo-entidades(Atacadao)` -> prefixo_cnpj -> `Frete(cnpj_cliente LIKE prefixo%)` -> `SUM(valor_pago)` + `DespesaExtra(frete_id)` -> `SUM(valor_despesa)`
- **Gap**: `cotando-frete` = preco teorico. Nenhuma skill consulta Frete.valor_pago (historico real)

### 2.2 "Qual a transportadora mais cara/barata para Manaus nos ultimos 3 meses?"
- **Frequencia**: MENSAL | **Complexidade**: 2 tabelas + agregacao
- **Path**: `Frete(cidade_destino='MANAUS')` -> `JOIN Transportadora` -> `AVG(valor_pago/peso_total) as custo_por_kg` -> `GROUP BY transportadora` -> `ORDER BY custo_por_kg`
- **Gap**: Nenhuma skill compara custo REAL entre transportadoras (so tabela teorica)

### 2.3 "Quantas despesas extras tivemos com a transportadora Braspress?"
- **Frequencia**: MENSAL | **Complexidade**: 2-3 tabelas
- **Path**: `Frete(transportadora_id)` -> `DespesaExtra(frete_id)` -> `GROUP BY tipo_despesa` -> `SUM(valor_despesa), COUNT(*)`
- **Gap**: Tabelas `despesas_extras` e `bi_despesa_detalhada` existem mas nenhuma skill agrega

### 2.4 "Percentual de frete sobre faturamento por UF"
- **Frequencia**: MENSAL | **Complexidade**: 1-2 tabelas
- **Path**: `Frete(uf_destino)` -> `SUM(valor_pago) / SUM(valor_total_nfs) * 100` -> `GROUP BY uf_destino`
- **Gap**: Calculo "% frete/faturamento" nao e operacao nativa de nenhuma skill

### 2.5 "Divergencia entre CTe cobrado e cotacao?"
- **Frequencia**: DIARIA | **Complexidade**: 1-2 tabelas
- **Path**: `Frete` -> `WHERE ABS(valor_cte - valor_cotado) > tolerancia` -> `JOIN Transportadora`
- **Gap**: Metodos `diferenca_cotado_cte()` e `requer_aprovacao_por_valor()` existem no modelo Frete mas nenhuma skill expoe divergencias

### 2.6 "Saldo de conta corrente com a transportadora Braspress"
- **Frequencia**: SEMANAL | **Complexidade**: 2 tabelas
- **Path**: `ContaCorrenteTransportadora(transportadora_id)` -> `SUM(credito) - SUM(debito)`
- **Gap**: Tabela existe mas nenhuma skill consulta

### 2.7 "Fretes pendentes de lancamento no Odoo"
- **Frequencia**: DIARIA | **Complexidade**: 1 tabela
- **Path**: `Frete(status='APROVADO', lancado_odoo_em IS NULL)`
- **Gap**: Status de integracao Odoo dos fretes nao e consultado por nenhuma skill

### 2.8 "Quanto gastei de frete por tipo de carga (direta vs fracionada) este mes?"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela + agregacao
- **Path**: `Frete(tipo_carga)` -> `GROUP BY tipo_carga` -> `SUM(valor_pago)`
- **Gap**: Nenhuma skill segmenta custo por tipo de carga

### 2.9 "Qual o frete medio por kg para cada UF?"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela + agregacao
- **Path**: `Frete(uf_destino)` -> `AVG(valor_pago / peso)` -> `GROUP BY uf_destino` -> `ORDER BY custo_kg`
- **Gap**: Benchmark de custo/kg por destino nao existe em nenhuma skill

---

## DOMINIO 3: ENTREGA E MONITORAMENTO (Analises Agregadas)

### 3.1 "Lead time medio de entrega para MG"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela + agregacao
- **Path**: `EntregaMonitorada(entregue=True, lead_time IS NOT NULL)` -> `AVG(lead_time)` -> `GROUP BY uf` ou `transportadora`
- **Gap**: `monitorando-entregas` consulta entregas individuais. Nao faz analise estatistica

### 3.2 "Quantas entregas estao atrasadas?"
- **Frequencia**: DIARIA | **Complexidade**: 1 tabela + calculo
- **Path**: `EntregaMonitorada(entregue=False, data_entrega_prevista < HOJE)` -> `COUNT(*)` -> `GROUP BY transportadora, uf`
- **Gap**: `--pendentes` lista entregas nao entregues mas NAO calcula atraso em dias nem agrega

### 3.3 "Ranking de transportadoras por velocidade de entrega para SP"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela + agregacao
- **Path**: `EntregaMonitorada(uf='SP', entregue=True)` -> `AVG(lead_time)` -> `GROUP BY transportadora` -> `ORDER BY ASC`
- **Gap**: Nenhuma skill compara performance de transportadoras. `bi_performance_transportadora` tem dados mas sem skill

### 3.4 "Historico de devolucoes do cliente Sendas"
- **Frequencia**: SEMANAL | **Complexidade**: 3-4 tabelas
- **Path**: `NFDevolucao(cnpj LIKE prefixo_sendas%)` -> `NFDevolucaoLinha(nfd_id)` -> produtos/quantidades + `OcorrenciaDevolucao(nfd_id)` -> tratativas
- **Gap**: `monitorando-entregas` foca em devolucoes abertas. Nao tem historico por cliente com detalhamento de produtos

### 3.5 "Custo total de devolucoes este mes"
- **Frequencia**: MENSAL | **Complexidade**: 2 tabelas
- **Path**: `DespesaExtra(tipo_despesa='DEVOLUÇÃO')` -> `SUM(valor_despesa)`. Link via `DespesaExtra.nfd_id` -> `NFDevolucao` para detalhes da devolucao original
- **Gap**: Nenhuma skill agrega impacto financeiro total de devolucoes via DespesaExtra

### 3.6 "Entregas com custo extra (TDE, reentrega, diaria)"
- **Frequencia**: SEMANAL | **Complexidade**: 2 tabelas
- **Path**: `CustoExtraEntrega(entrega_id)` -> `tipo_custo, valor` -> `JOIN EntregaMonitorada` -> `GROUP BY tipo_custo`
- **Gap**: `CustoExtraEntrega` existe no modelo monitoramento mas nenhuma skill agrega custos extras de entrega

### 3.7 "Taxa de sucesso de entrega por transportadora"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela + agregacao
- **Path**: `EntregaMonitorada` -> `COUNT(entregue=True) / COUNT(*) * 100` -> `GROUP BY transportadora`
- **Gap**: Nenhuma skill calcula taxa de sucesso/insucesso

### 3.8 "Entregas reagendadas mais de 2 vezes"
- **Frequencia**: SEMANAL | **Complexidade**: 2 tabelas
- **Path**: `AgendamentoEntrega` -> `GROUP BY entrega_id HAVING COUNT(*) > 2` -> `JOIN EntregaMonitorada`
- **Gap**: `monitorando-entregas` mostra agendamentos mas nao filtra por quantidade de reagendamentos

---

## DOMINIO 4: ESTOQUE (Analises nao cobertas)

### 4.1 "Quais produtos vao faltar nos proximos 7 dias?"
- **Frequencia**: DIARIA | **Complexidade**: 3-4 tabelas
- **Path**: `MovimentacaoEstoque(saldo atual)` - `Separacao(sincronizado_nf=False, expedicao <= 7 dias)`.qtd_saldo + `ProgramacaoProducao(data <= 7 dias)`.qtd_programada -> `WHERE resultado < 0`
- **Gap**: `gerindo-expedicao` consulta estoque por produto individual. Nao faz ALERTA proativo de ruptura futura

### 4.2 "Historico de movimentacao do produto X (entrada/saida/producao)"
- **Frequencia**: SEMANAL | **Complexidade**: 1 tabela
- **Path**: `MovimentacaoEstoque(cod_produto)` -> `ORDER BY data_movimentacao DESC` -> tipo, qtd, origem
- **Gap**: `gerindo-expedicao` mostra saldo atual. Nao mostra historico de movimentacoes

### 4.3 "De onde veio o estoque do produto X? (compra vs producao)"
- **Frequencia**: SEMANAL | **Complexidade**: 1-2 tabelas
- **Path**: `MovimentacaoEstoque(cod_produto, tipo_movimentacao='ENTRADA')` -> `GROUP BY local_movimentacao` (COMPRA, PRODUCAO, AJUSTE, DEVOLUCAO)
- **Gap**: Nenhuma skill discrimina origem do estoque

### 4.4 "Giro de estoque por produto"
- **Frequencia**: MENSAL | **Complexidade**: 2-3 tabelas
- **Path**: `FaturamentoProduto(cod_produto, ultimos 30 dias)` -> `SUM(qtd_faturada)` / `saldo_medio_estoque` -> giro
- **Gap**: Nenhuma skill calcula giro de estoque

### 4.5 "Estoque parado ha mais de 30 dias (sem saida)"
- **Frequencia**: MENSAL | **Complexidade**: 2 tabelas
- **Path**: `MovimentacaoEstoque(cod_produto)` -> `MAX(data_movimentacao WHERE tipo='SAIDA')` -> `WHERE ultima_saida < 30 dias atras` + saldo > 0
- **Gap**: Nenhuma skill identifica estoque obsoleto/parado

### 4.6 "Quanto de estoque esta comprometido com separacoes?"
- **Frequencia**: DIARIA | **Complexidade**: 2 tabelas
- **Path**: `Separacao(sincronizado_nf=False)` -> `GROUP BY cod_produto` -> `SUM(qtd_saldo)` = estoque comprometido
- **Gap**: `gerindo-expedicao` mostra projecao mas nao isola "comprometido por separacoes" como metrica explicita

---

## DOMINIO 5: EMBARQUE, PORTARIA E PALLET

### 5.1 "Qual o caminhao do embarque 1234?"
- **Frequencia**: DIARIA | **Complexidade**: 3 tabelas
- **Path**: `Embarque(numero=1234)` -> `ControlePortaria(embarque_id)` -> `Motorista(motorista_id)` -> nome, placa, telefone
- **Gap**: Modulo portaria sem skill

### 5.2 "Quantos veiculos estao na fabrica agora?"
- **Frequencia**: VARIAS/DIA | **Complexidade**: 1-2 tabelas
- **Path**: `ControlePortaria(data_saida IS NULL, status='DENTRO')` -> `COUNT(*)` + detalhes
- **Gap**: Metodo `veiculos_do_dia()` existe mas sem skill

### 5.3 "Tempo medio de carregamento por tipo de veiculo"
- **Frequencia**: MENSAL | **Complexidade**: 2 tabelas + calculo
- **Path**: `ControlePortaria(hora_saida - hora_entrada)` -> `GROUP BY tipo_veiculo_id`
- **Gap**: Nenhuma skill analisa permanencia na fabrica

### 5.4 "Saldo de pallets com a transportadora Braspress"
- **Frequencia**: SEMANAL | **Complexidade**: 1-2 tabelas
- **Path**: `PalletCredito(tipo_responsavel='TRANSPORTADORA', cnpj_responsavel)` -> `SUM(qtd_saldo)` OU `Embarque.saldo_pallets_pendentes`
- **Gap**: Modulo pallet sem skill

### 5.5 "Embarques com pallets pendentes de NF"
- **Frequencia**: SEMANAL | **Complexidade**: 1-2 tabelas
- **Path**: `Embarque` -> property `saldo_pallets_pendentes > 0` -> lista
- **Gap**: Nenhuma skill consulta saldo de pallets

---

## DOMINIO 6: CUSTEIO, MARGEM E PRODUTO

### 6.1 "Margem bruta do pedido VCD123"
- **Frequencia**: SEMANAL | **Complexidade**: 4+ tabelas
- **Path**: `CarteiraPrincipal(margem_bruta)` + detalhamento: `CustoConsiderado(cod_produto)` + `CustoFrete(incoterm, uf)` + `RegraComissao(cnpj, produto)`
- **Gap**: Campo existe mas composicao detalhada nao exposta

### 6.2 "Custo medio do produto X nos ultimos 3 meses"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela
- **Path**: `CustoMensal(cod_produto, ano, mes)` -> `custo_liquido_medio` -> ultimos 3 meses
- **Gap**: Modulo custeio sem skill

### 6.3 "Resumo completo do produto palmito" (360 graus)
- **Frequencia**: SEMANAL | **Complexidade**: 7+ tabelas
- **Path**: `CadastroPalletizacao` + `ProgramacaoProducao(programados)` + `MovimentacaoEstoque(saldo)` + `CarteiraPrincipal(pendentes)` + `Separacao(separados)` + `FaturamentoProduto(faturados)` + `CustoConsiderado(custo)`
- **Gap**: Nenhuma visao consolidada de produto cruzando todos os dominios

### 6.4 "Produtos mais devolvidos nos ultimos 30 dias"
- **Frequencia**: MENSAL | **Complexidade**: 2-3 tabelas
- **Path**: `NFDevolucaoLinha` -> `GROUP BY cod_produto_local` -> `COUNT(*), SUM(qtd_devolvida)` -> ranking
- **Gap**: Nenhuma skill agrega devolucoes por produto

---

## DOMINIO 7: PERGUNTAS TEMPORAIS E COMPARATIVAS

### 7.1 "Faturamento deste mes vs mes passado"
- **Frequencia**: SEMANAL | **Complexidade**: 1 tabela, 2 queries
- **Path**: `FaturamentoProduto` -> `SUM(valor)` por periodo -> diferenca percentual
- **Gap**: Sem template de comparativo periodo-a-periodo

### 7.2 "Evolucao do custo de frete nos ultimos 6 meses"
- **Frequencia**: MENSAL | **Complexidade**: 1-2 tabelas + serie temporal
- **Path**: `BiIndicadorMensal(ano, mes)` -> `custo_total_frete, custo_medio_por_kg` OU `Frete` -> `GROUP BY month`
- **Gap**: Tabelas BI existem mas nenhuma skill as consulta

### 7.3 "Clientes novos na carteira este mes"
- **Frequencia**: MENSAL | **Complexidade**: 1-2 tabelas + subquery
- **Path**: `CarteiraPrincipal(data_pedido >= inicio_mes)` -> `CNPJ NOT IN (SELECT DISTINCT cnpj WHERE data_pedido < inicio_mes)`
- **Gap**: Nenhuma skill identifica clientes novos vs recorrentes

### 7.4 "Performance de entregas semana a semana"
- **Frequencia**: SEMANAL | **Complexidade**: 1 tabela + agregacao
- **Path**: `EntregaMonitorada` -> `GROUP BY DATE_TRUNC('week')` -> `COUNT(entregue=True), COUNT(atrasadas), AVG(lead_time)`
- **Gap**: Nenhuma skill gera series temporais de performance

### 7.5 "Embarques por dia da semana (concentracao)"
- **Frequencia**: MENSAL | **Complexidade**: 1 tabela
- **Path**: `Embarque` -> `GROUP BY EXTRACT(DOW FROM data_embarque)` -> distribuicao semanal
- **Gap**: Nenhuma skill analisa concentracao operacional por dia

---

## DOMINIO 8: PRODUCAO (Cross-domain com estoque)

### 8.1 "Insumo X esta atrasado? Quando chega?"
- **Frequencia**: SEMANAL | **Complexidade**: 2-3 tabelas
- **Path**: `PedidoCompras(cod_produto)` -> `data_pedido_previsao vs HOJE` -> `qtd_recebida vs qtd_pedida`
- **Gap**: Modulo compras/manufatura sem skill no agente web

### 8.2 "Producao realizada vs programada da semana"
- **Frequencia**: SEMANAL | **Complexidade**: 2 tabelas
- **Path**: `ProgramacaoProducao(data_semana)` -> `PlanoMestreProducao` -> `qtd_realizada / qtd_programada * 100`
- **Gap**: `gerindo-expedicao` consulta programacao futura mas nao compara realizado vs programado

---

## RESUMO: TOP 10 PERGUNTAS MAIS CRITICAS (por frequencia x impacto)

| # | Pergunta | Freq | Tabelas | Gap Principal |
|---|----------|------|---------|---------------|
| 1 | Status completo do pedido X | DIARIA | 5+ | Nenhuma skill cruza pre/pos-faturamento |
| 2 | Quando entrega o pedido X? | DIARIA | 4-5 | Logica condicional pre/pos-faturamento |
| 3 | Entregas atrasadas (agregado) | DIARIA | 1 | monitorando-entregas nao calcula atraso em dias |
| 4 | Produtos que vao faltar em 7 dias | DIARIA | 3-4 | Sem alerta proativo de ruptura |
| 5 | Divergencia CTe vs cotacao | DIARIA | 1-2 | Modelo tem metodos, skill nao expoe |
| 6 | Pedidos em transito por cliente | DIARIA | 3 | Nenhuma skill mostra "em transito" |
| 7 | Custo REAL de frete do pedido X | SEMANAL | 5+ | cotando-frete = teorico, sem historico pago |
| 8 | Co-passageiros do embarque | SEMANAL | 3 | Conceito inexistente em skills |
| 9 | Gasto de frete com cliente X (real) | SEMANAL | 2-3 | Sem agregacao de Frete.valor_pago por grupo |
| 10 | O que falta entregar do pedido X | DIARIA | 3-4 | Sem cruzamento carteira+faturamento+entrega |

---

## 4 GAPS ESTRUTURAIS IDENTIFICADOS

### Gap A: Travessia pre/pos-faturamento
Skills operam em silos separados por `sincronizado_nf`. Nenhuma faz a ponte.
**Impacto**: Perguntas 1.1, 1.2, 1.3, 1.5, 1.6, 1.7

### Gap B: Frete REAL vs TEORICO
`cotando-frete` = tabelas de preco. Frete(valor_pago, valor_cte) + DespesaExtra = custos reais nao consultados.
**Impacto**: Perguntas 1.3, 2.1-2.9

### Gap C: Modulos operacionais sem skill
Pallet, Portaria, Custeio, Devolucoes (detalhado) - UI web existe, agente nao acessa.
**Impacto**: Perguntas 5.1-5.5, 6.1-6.4, 3.4-3.6

### Gap D: Tabelas BI nao exploradas
`bi_frete_agregado`, `bi_performance_transportadora`, `bi_indicador_mensal` - ETL pronto, nenhuma skill usa.
**Impacto**: Perguntas 2.2, 3.3, 7.2, 7.4

---

## RELACOES INDIRETAS CHAVE

```
PEDIDO -> ENTREGA:
  FaturamentoProduto.origem = num_pedido (DIRETO!)
  Separacao.num_pedido -> Separacao.numero_nf -> EntregaMonitorada.numero_nf

PEDIDO -> EMBARQUE:
  Separacao.separacao_lote_id -> EmbarqueItem.separacao_lote_id -> Embarque.id

PEDIDO -> FRETE:
  (via embarque acima) -> Frete.embarque_id
  FaturamentoProduto.numero_nf -> Frete.numeros_nfs (CSV)

EMBARQUE -> CO-PASSAGEIROS:
  EmbarqueItem(embarque_id=X) -> todos os lotes/clientes no mesmo caminhao

ENTREGA -> DEVOLUCAO:
  EntregaMonitorada.id -> NFDevolucao.entrega_monitorada_id
  EntregaMonitorada.numero_nf -> NFDevolucao (pela NF original)
```

### PRODUTO -> CICLO COMPLETO (fluxos paralelos que convergem)

```
FLUXO COMPRAS:    PedidoCompras ──────────────────┐
FLUXO PRODUCAO:   ProgramacaoProducao ─(produz)───┤
                                                   ▼
                                       MovimentacaoEstoque (saldo real)
                                                   │
PROJECAO ESTOQUE = saldo real                      │
                 + PedidoCompras pendentes          │
                 + ProgramacaoProducao pendente     │
                 - ProgramacaoProducao (componentes deduzidos)
                                                   │
                                                   ▼
FLUXO VENDA:      CarteiraPrincipal (enxerga projecao + saldo real)
                       │ programa expedicao, deduz da projecao
                       ▼
                  Separacao (compromete estoque)
                       │
                  EmbarqueItem -> Embarque
                       │
                  ┌────┴────┐
                  ▼         ▼
         FaturamentoProduto  Frete
                  │
                  ▼
         EntregaMonitorada
```

---

## FORMULAS DE CALCULO POR PEDIDO

### Total do pedido (valor original)
```
CarteiraPrincipal: SUM(qtd_produto_pedido * preco_produto_pedido)
  WHERE num_pedido = 'VCD123'
  GROUP BY cod_produto (por produto) ou total
```

### Total pendente de faturamento
```
CarteiraPrincipal: SUM(qtd_saldo_produto_pedido * preco_produto_pedido)
  WHERE num_pedido = 'VCD123'
  (qtd_saldo_produto_pedido = qtd restante nao faturada)
```

### Total programado para expedicao
```
Separacao: qtd_saldo (QTD), valor_saldo (VALOR)
  WHERE sincronizado_nf = False AND num_pedido = 'VCD123'
  Detalhar por cod_produto para ver produto a produto
```

### Data programada de expedicao
```
Separacao.expedicao POR Separacao.separacao_lote_id
  (1 separacao_lote_id -> 1 FaturamentoProduto.numero_nf apos faturamento)

ENRIQUECIMENTO com portaria:
  Separacao.separacao_lote_id -> EmbarqueItem.separacao_lote_id
  -> EmbarqueItem.embarque_id -> Embarque.id
  -> ControlePortaria(embarque_id=Embarque.id)
  -> ControlePortaria.status (property: SAIU/DENTRO/AGUARDANDO/PENDENTE)
  -> hora_chegada, hora_entrada, hora_saida
```

### Numero do embarque
```
Embarque.id (ou .numero) WHERE:
  EmbarqueItem.separacao_lote_id = Separacao.separacao_lote_id
```

### Frete do embarque (calculo)
```
Se Embarque.tipo_carga = 'DIRETA':
  Tabela de frete em Embarque.tabela_* (tabela_valor_kg, tabela_percentual_valor, etc.)
  Calcular frete por somatoria do Embarque e ratear pelo peso de cada CNPJ

Se Embarque.tipo_carga = 'FRACIONADA':
  Tabela de frete em EmbarqueItem.tabela_* (cada item pode ter tabela diferente)
  Calcular frete pela somatoria de valor e peso por CNPJ do Embarque

USAR: app/utils/calculadora_frete.py (CalculadoraFrete)
  .calcular_frete_carga_direta() ou .calcular_frete_carga_fracionada()
  .extrair_dados_tabela_embarque() / .extrair_dados_tabela_item()
```

### Valor faturado do pedido
```
FaturamentoProduto: SUM(valor_produto_faturado)
  WHERE origem = 'VCD123' (campo origem = num_pedido!)
  GROUP BY numero_nf (total por NF desse pedido)
  ou total geral
```

---

## ESTADOS DE ENTREGA (EntregaMonitorada)

### Pedidos em transito
```
EntregaMonitorada WHERE:
  status_finalizacao IS NULL
  AND data_embarque IS NOT NULL  (ja saiu)
  AND nf_cd = False              (nao voltou pro CD)

JOIN FaturamentoProduto.origem para obter num_pedido:
  EntregaMonitorada.numero_nf = FaturamentoProduto.numero_nf
```

### NF ainda nao saiu (aguardando embarque)
```
EntregaMonitorada WHERE:
  data_embarque IS NULL
  AND nf_cd = False
```

### NF esta no CD (voltou)
```
EntregaMonitorada WHERE:
  nf_cd = True
```

---

## CUSTO DE DEVOLUCAO (path correto)

```
DespesaExtra WHERE tipo_despesa = 'DEVOLUÇÃO'
  -> SUM(valor_despesa)
  -> Link: DespesaExtra.nfd_id -> NFDevolucao
  -> Link: DespesaExtra.frete_id -> Frete (embarque original)
  -> Link: DespesaExtra.despesa_cte_id -> ConhecimentoTransporte (CTe complementar)
  -> Link: DespesaExtra.transportadora_id -> override de transportadora se diferente
```

---

## RELATIONSHIPS DO MODULO DE FRETES

```
Frete
├── .embarque -> Embarque (embarque_id)
├── .transportadora -> Transportadora (transportadora_id)
├── .fatura_frete -> FaturaFrete (fatura_frete_id)
├── .cte -> ConhecimentoTransporte (frete_cte_id)
├── .despesas_extras -> [DespesaExtra] (cascade, backref: .frete)
├── .conhecimentos_transporte -> [ConhecimentoTransporte] (backref via frete_id)
├── .movimentacoes_conta_corrente -> [ContaCorrenteTransportadora] (backref)
├── .aprovacao -> [AprovacaoFrete] (backref)
└── .auditorias_odoo -> [LancamentoFreteOdooAuditoria] (backref)

DespesaExtra
├── .frete -> Frete (frete_id)
├── .fatura_frete -> FaturaFrete (fatura_frete_id)
├── .transportadora -> Transportadora (nullable, override)
├── .cte -> ConhecimentoTransporte (despesa_cte_id)
├── .nfd -> NFDevolucao (nfd_id) -- LINK DEVOLUCAO!
└── .auditorias_odoo -> [LancamentoFreteOdooAuditoria] (backref)

FaturaFrete
├── .transportadora -> Transportadora
├── .fretes -> [Frete] (backref)
└── .despesas_extras -> [DespesaExtra] (backref)

ContaCorrenteTransportadora
├── .transportadora -> Transportadora
├── .frete -> Frete (frete_id)
└── .frete_compensacao -> Frete (compensacao_frete_id)

ConhecimentoTransporte
├── .frete -> Frete (frete_id)
├── .cte_original -> ConhecimentoTransporte (self-ref para CTe complementar)
├── .ctes_complementares -> [ConhecimentoTransporte] (backref)
├── .frete_vinculado -> Frete (via frete_cte_id, backref)
└── .despesas_extras_vinculadas -> [DespesaExtra] (backref)

AprovacaoFrete
└── .frete -> Frete

LancamentoFreteOdooAuditoria
├── .frete -> Frete
├── .despesa_extra -> DespesaExtra
└── .cte -> ConhecimentoTransporte
```

### TIPOS_DESPESA (DespesaExtra.tipo_despesa)
```
REENTREGA | TDE | PERNOITE | DEVOLUÇÃO | DIARIA
COMPLEMENTO DE FRETE | COMPRA/AVARIA | TRANSFERENCIA
DESCARGA | ESTACIONAMENTO | CARRO DEDICADO | ARMAZENAGEM
```
