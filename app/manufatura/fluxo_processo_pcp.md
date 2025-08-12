# 📋 FLUXO DO PROCESSO PCP - MÓDULO MANUFATURA

## 🎯 Visão Geral
Sistema otimizado para PCP trabalhar diariamente, com dupla alimentação:
- **Entrada Manual**: PCP opera no sistema (cria ordens, requisições)
- **Sincronização Odoo**: Importa operações confirmadas/realizadas

---

## 📊 FASE 1: PLANEJAMENTO MENSAL

### 1.1 Previsão de Demanda [Usuário: Comercial + PCP]
**Tela**: Gestão de Previsão de Demanda

**Ações do Usuário**:
1. Seleciona `data_mes` e `data_ano` para planejamento
2. Escolhe `nome_grupo` (GrupoEmpresarial)
3. Para cada `cod_produto`:
   - Informa `qtd_demanda_prevista` baseado em histórico
   - Define `disparo_producao` (MTS ou MTO)

**Sistema Automaticamente**:
- Calcula `qtd_demanda_realizada` usando HistoricoPedidos
- Busca `nome_produto` do CadastroPalletizacao
- Valida apenas produtos com `produto_vendido = True`

### 1.2 Plano Mestre de Produção [Usuário: PCP]
**Tela**: Plano Mestre de Produção

**Ações do Usuário**:
1. Revisa demandas importadas da PrevisaoDemanda
2. Define `qtd_estoque_seguranca` por produto
3. Aprova plano alterando `status_geracao` para 'aprovado'

**Sistema Automaticamente**:
- Importa `qtd_demanda_prevista` da PrevisaoDemanda
- Calcula `qtd_estoque` atual via MovimentacaoEstoque
- Calcula `qtd_reposicao_sugerida = demanda + segurança - estoque - programado`
- Busca `qtd_lote_ideal` e `qtd_lote_minimo` de RecursosProducao

---

## 🏭 FASE 2: PROGRAMAÇÃO DA PRODUÇÃO

### 2.1 Geração de Ordens MTO [Automático + Manual]
**Trigger**: Novo pedido em CarteiraPrincipal ou Separacao

**Sistema Automaticamente** (produtos MTO):
- Verifica `CadastroPalletizacao.disparo_producao = 'MTO'`
- Valida que pedido não está faturado: `Pedido.status != 'FATURADO'`
- Calcula data início: `expedicao - lead_time_mto` (dias úteis)
- Cria OrdemProducao com `origem_ordem = 'MTO'`
- Atualiza `CarteiraPrincipal.ordem_producao_id` ou vincula com Separacao

### 2.2 Geração de Ordens MTS [Usuário: PCP]
**Tela**: Criação de Ordens de Produção

**Ações do Usuário**:
1. Revisa produtos com `qtd_reposicao_sugerida > 0`
2. Define `qtd_planejada` respeitando lote mínimo
3. Seleciona `linha_producao` disponível
4. Define `data_inicio_prevista` e `data_fim_prevista`
5. Confirma criação com `origem_ordem = 'PMP'`

**Sistema Automaticamente**:
- Gera `numero_ordem` sequencial
- Calcula `materiais_necessarios` via ListaMateriais:
  ```json
  [{
    "cod_produto": "MP001",
    "qtd_necessaria": qtd_planejada * qtd_utilizada,
    "qtd_disponivel": estoque_atual,
    "qtd_comprar": max(0, necessaria - disponivel)
  }]
  ```
- Define `status = 'Planejada'`

### 2.3 Sequenciamento de Ordens [Usuário: PCP]
**Tela**: Quadro de Sequenciamento

**Ações do Usuário**:
1. Visualiza ordens por linha_producao (kanban/gantt)
2. Ajusta sequência considerando:
   - **Pedidos puxados pelo comercial**: Verifica `expedicao` em:
     - Separacao com `Pedido.status != 'FATURADO'` (JOIN via `separacao_lote_id`)
     - PreSeparacaoItem (apenas se `separacao_lote_id` não existe em Separacao)
     - **IMPORTANTE**: 
       - Quando mesmo `separacao_lote_id` existe em ambas tabelas, considerar APENAS Separacao
       - Ignorar Separacao onde `Pedido.status = 'FATURADO'` (já foi entregue)
   - Disponibilidade materiais (materiais_necessarios)
   - Capacidade linha (RecursosProducao.capacidade_unidade_minuto)
3. Resolve conflitos de horário entre ordens
4. Libera ordem alterando `status = 'Liberada'`

**Priorização Automática**:
- Sistema destaca ordens MTO com `expedicao` próxima
- Comercial define `expedicao` mesmo sem estoque disponível
- PCP prioriza produção para atender data comprometida
- **Exclui automaticamente** pedidos já faturados da análise de demanda

---

## 🛒 FASE 3: GESTÃO DE COMPRAS

### 3.1 Geração de Necessidades [Automático]
**Tela**: Lista de Necessidades de Compra (To-Do)

**Sistema Automaticamente**:
- Analisa `materiais_necessarios` das OrdemProducao
- Agrupa necessidades por `cod_produto`
- Calcula `data_necessidade` baseado em:
  - `data_inicio_prevista` da ordem
  - `lead_time_previsto` do LeadTimeFornecedor
- Cria registro de necessidade com status "Pendente"

**Visualização PCP**:
- Lista de materiais a requisitar (To-Do List)
- Quantidade total necessária por produto
- Data limite para disponibilidade
- Ordens impactadas se não comprar

### 3.2 Criação de Requisição no Odoo [Usuário: PCP/Compras]
**Ação Manual Externa**:
1. PCP visualiza lista de necessidades no sistema
2. Acessa Odoo e cria requisição de compra
3. Marca necessidade como "Requisitada" no sistema

### 3.3 Importação de Requisições [Automático via API]
**Job Schedulado**: A cada 30 minutos

**Sistema Automaticamente**:
- Busca requisições criadas no Odoo
- Cria/atualiza RequisicaoCompras com:
  - `num_requisicao` do Odoo
  - `data_requisicao_criacao`
  - `qtd_produto_requisicao`
- Vincula com necessidades pendentes
- Atualiza status para "Requisitada"

### 3.4 Importação de Pedidos de Compra [Automático via API]
**Job Schedulado**: A cada 30 minutos

**Sistema Automaticamente**:
- Busca pedidos criados no Odoo
- Cria/atualiza PedidoCompras com:
  - `num_pedido` do Odoo
  - `num_requisicao` vinculado
  - `cnpj_fornecedor`, `raz_social`
  - `data_pedido_previsao`
  - `confirmacao_pedido` quando confirmado

---

## 🔧 FASE 4: EXECUÇÃO DA PRODUÇÃO

### 4.1 Início da Produção [Usuário: PCP]
**Tela**: Ordens em Execução

**Ações do Usuário**:
1. Verifica materiais disponíveis
2. Confirma início alterando `status = 'Em Produção'`
3. Sistema registra `data_inicio_real`

### 4.2 Lançamento Ordem no Odoo [Usuário: PCP]
**Ação Manual Externa**:
1. Cria ordem de produção no Odoo
2. Informa número da ordem do sistema

### 4.3 Apontamento de Produção [Usuário: Produção]
**No Odoo**:
1. Operador aponta quantidade produzida

### 4.4 Importação Apontamentos [Automático via API]
**Job Schedulado**: A cada 1 hora

**Sistema Automaticamente**:
- Busca apontamentos do Odoo por numero_ordem
- Cria MovimentacaoEstoque:
  - `tipo_movimentacao = 'PRODUCAO'`
  - `qtd_movimentacao` = quantidade apontada
  - `ordem_producao_id` vinculado
- Atualiza OrdemProducao:
  - `qtd_produzida` = soma apontamentos
  - `status = 'Concluída'` quando qtd_produzida >= qtd_planejada

---

## 📥 FASE 5: RECEBIMENTO DE MATERIAIS

### 5.1 Entrada no Odoo [Externo]
**No Odoo**:
1. Almoxarifado registra entrada de materiais
2. Vincula ao pedido de compra

### 5.2 Importação Entradas [Automático via API]
**Job Schedulado**: A cada 30 minutos

**Sistema Automaticamente**:
- Busca entradas confirmadas no Odoo
- **Identifica produtos comprados**: Filtra movimentações onde:
  - Origem é pedido de compra
  - Tipo de operação é entrada
  - Produto tem `produto_comprado = True` no CadastroPalletizacao
- Cria MovimentacaoEstoque:
  - `tipo_movimentacao = 'ENTRADA_COMPRA'`
  - `num_pedido` do pedido de compra
  - `numero_nf` da nota fiscal
- Atualiza PedidoCompras:
  - `data_pedido_entrega` = data real
  - `confirmacao_pedido = True`
- Recalcula disponibilidade para ordens pendentes

**Nota**: Sistema valida no Odoo se movimento é de compra através do tipo de operação e documento origem

---

## 📊 FASE 6: MONITORAMENTO E AJUSTES

### 6.1 Dashboard PCP [Usuário: PCP/Gestão]
**Tela**: Dashboard Operacional

**Visualizações**:
- Ordens em atraso (data_fim_prevista < hoje e status != 'Concluída')
- Taxa ocupação linhas (ordens ativas / capacidade)
- Materiais críticos (estoque < necessidade próximos 7 dias)
- Aderência ao plano (produzido vs planejado)

### 6.2 Ajustes Dinâmicos [Usuário: PCP]
**Ações Possíveis**:
1. Repriorizar ordens em espera
2. Dividir ordens grandes (`qtd_planejada` em múltiplas)
3. Alterar `linha_producao` para balancear carga
4. Cancelar ordens (`status = 'Cancelada'`)

---

## 🔄 INTEGRAÇÕES ODOO - RESUMO

### Fluxo Sistema → Odoo (Manual):
1. **Necessidades de Compra**: Sistema gera To-Do, PCP cria requisição no Odoo
2. **Ordens de Produção**: PCP cria no sistema, lança no Odoo

### Fluxo Odoo → Sistema (Automático):
1. **Pedidos de Compra**: Importa confirmações e previsões
2. **Entradas de Material**: Importa recebimentos e NFs
3. **Apontamentos de Produção**: Importa quantidades produzidas
4. **Ordens de Produção**: Importa status e conclusões

### Campos-Chave para Integração:
- `numero_ordem`: Vincula OrdemProducao com Odoo
- `num_pedido`: Vincula PedidoCompras com Odoo
- `numero_nf`: Rastreia entradas fiscais
- `ordem_producao_id`: Liga CarteiraPrincipal → OrdemProducao (MTO)

---

## ⚠️ PONTOS DE ATENÇÃO

### Validações Críticas:
1. **Antes de criar ordem**: Verificar `produto_produzido = True`
2. **Antes de requisitar**: Verificar `produto_comprado = True`
3. **MTO automático**: Só se `lead_time_mto` preenchido
4. **Conflito de linha**: Não permitir sobreposição de horários
5. **Evitar duplicação de demanda**:
   - Query deve usar: `WHERE NOT EXISTS (SELECT 1 FROM Separacao s WHERE s.separacao_lote_id = PreSeparacaoItem.separacao_lote_id)`
   - Se `separacao_lote_id` existe em Separacao, ignorar PreSeparacaoItem
   - Separacao tem prioridade sobre PreSeparacaoItem
6. **Excluir pedidos faturados**:
   - Considerar apenas: `JOIN Pedido p ON s.separacao_lote_id = p.separacao_lote_id WHERE p.status != 'FATURADO'`
   - Pedidos faturados não geram demanda de produção

### Contingências:
1. **Falta material**: Sistema alerta mas permite override manual
2. **Atraso fornecedor**: Recalcula datas das ordens dependentes
3. **Quebra máquina**: PCP realoca ordens para outras linhas
4. **Divergência Odoo**: Log de inconsistências para análise

---

## 📈 MÉTRICAS OPERACIONAIS

### Indicadores Calculados:
- **Aderência Plano**: `qtd_produzida / qtd_planejada * 100`
- **Lead Time Real**: `data_fim_real - data_inicio_real`
- **Ocupação Linha**: `Σ(tempo_producao) / tempo_disponivel * 100`
- **Eficiência Produtiva**: `qtd_produzida / (capacidade_unidade_minuto * tempo_producao)`

### Alertas Automáticos:
- Ordem atrasada > 2 dias
- Material crítico < 3 dias estoque
- Linha parada > 4 horas
- Divergência Odoo > 10%

---

## 🚀 BENEFÍCIOS DO MODELO

1. **PCP Centralizado**: Opera principalmente no sistema, Odoo só confirmações
2. **Visibilidade Total**: Dashboard unificado de produção e materiais
3. **MTO Automático**: Reduz lead time de produtos sob encomenda
4. **Integração Suave**: Sincronização sem duplicação de trabalho
5. **Rastreabilidade**: Todo movimento tem origem identificada