# MÓDULO MANUFATURA - ESTADO ATUAL (25/10/2025)

## ✅ FUNCIONALIDADES ATIVAS

### 1. PREVISÃO DE DEMANDA (Implementado e Funcional)
Define previsão de vendas em PrevisaoDemanda junto ao comercial e histórico das demandas realizadas por grupo

### 2. ANÁLISE DE NECESSIDADE DE PRODUÇÃO (Implementado e Funcional) ✅ NOVO!
**Implementado em:** 25/10/2025
Cálculo da necessidade de produção baseado em:
```
Previsao de vendas(todos os grupos)
If Previsão de vendas > Pedidos inseridos:
    Saldo vendas = Previsão de vendas - Pedidos inseridos + Carteira de pedidos
Else
    Saldo vendas = Carteira de pedidos

Necessidade produção = Saldo vendas - Estoque - Programação de produção

If not Necessidade produção > 0:
    Necessidade produção = 0
```

Solicitado:
**Tabela UI planejada com:**
- Cod
- Produto
- Politica de estoque (MTO/MTS)
- Estoque
- Necessidade Produção
- Botão "Programar" (Será detalhado posteriormente)
- Projeção Estoque D0-D60

Realizado:
**Tabela UI implementada com:**
- ✅ Código do Produto
- ✅ Nome do Produto
- ✅ Previsão de Vendas
- ✅ Pedidos Inseridos (do mês)
- ✅ Carteira de Pedidos (saldo total)
- ✅ Saldo de Vendas (calculado)
- ✅ Estoque Atual
- ✅ Programação de Produção
- ✅ Necessidade de Produção (resultado final)
- ✅ Criticidade (Alta/Média/Baixa)
- ✅ Botão "Ver Projeção" → Modal com Projeção D0-D60
- ✅ **Unificação de Códigos**: Produtos com códigos unificados aparecem uma única vez, somando quantidades

**Features implementadas:**
- ✅ Filtro por Mês/Ano
- ✅ Filtro por Produto (opcional)
- ✅ Cálculo automático seguindo fórmula exata do escopo
- ✅ Modal de Projeção de Estoque D0-D60
- ✅ Tratamento de UnificacaoCodigos (produtos relacionados aparecem uma vez só)

---

## 🔄 FUNCIONALIDADES FUTURAS (Aguardando Implementação)

### 3. PLANO MESTRE DE PRODUÇÃO (Planejado)
Define/avalia estoque de segurança, avalia qtd_reposicao_sugerida e gera as ordens em PlanoMestreProducao.
Essa tela deverá mostrar:
- qtd_demanda_prevista.
- qtd_estoque_seguranca.
- qtd_estoque
- qtd_producao_programada (esse campo acredito que deva ser uma querie sum(OrdemProducao.qtd_planejada) através do join com data_mes, data_ano com data_inicio_prevista e cod_produto)
- qtd_reposicao_sugerida = qtd_demanda_prevista + qtd_estoque_seguranca - qtd_estoque - qtd_producao_programada


### 4. SEQUENCIAMENTO DE ORDENS DE PRODUÇÃO (Planejado)
Sequencia Ordens de produção através de:
A- Carteira de Pedidos
Deverá considerar as datas de expedicao das Separacao onde Pedido.status!=FATURADO (join através de separacao_lote_id), PreSeparacaoItem quando não houver Separacao (comparação se há duplicidade pelo separacao_lote_id) e considerar o saldo da CarteiraPrincipal que não contem Separacao/PreSeparacaoItem

B- Disponibilidade dos componentes
B.1 As ordens de produção deverá avaliar a ListaMateriais verificando separadamente os produtos_produzidos e produtos_comprados
B.2- Os produtos_produzidos, deverão ser avaliados através do estoque previsto do produto filho na data da ordem do produto pai e gerar uma ordem de produção de maneira automatica e vinculada à ordem pai, dessa forma qualquer alteração na ordem pai, deverá ser reavaliado o estoque previsto do produto filho na data da ordem do produto pai e atualizar a ordem filho. 
B.3- PedidoCompras / RequisicaoCompras
Considerar as data_pedido_previsao dos componentes do produto pai e dos componentes do produto_produzido da ListaMateriais do produto pai através da ListaMateriais do produto filho
B.4- Lead time dos componentes
Considerar o LeadTime dos produtos_comprados através dos componentes da ListaMateriais incluindo o componente dos produtos_produzidos constantes no produto pai


C- Disponibilidade de maquinas
Mostrar na tela de uma forma que seja extremamente visual e interativo para o usuario verificar se é possivel incluir aquela ordem de produção naquele dia ou se ele prefere quebrar a ordem de produção para coloca-la naquele momento

### 5. REQUISIÇÃO DE COMPRAS (Planejado)
Cria uma requisição de compras respeitando lead time dos componentes de maneira automatica na criação da ordem de produção ou opta por não criar a requisição de compras na ordem de produção e cria posteriormente avaliando o estoque dos componentes.

### 6. AVALIAÇÃO DE ESTOQUES DE PRODUTOS COMPRADOS (Planejado)
Avaliação dos estoques de produtos onde CadastroPalletizacao.produto_comprado = True junto com as RequisicaoCompras, PedidoCompras (Não sei como vincular a requisição criada no Odoo com a requisição criada no sistema, onde a requisição do sistema deverá ser um "rascunho" da requisição do sistema)

---

## 📂 ESTRUTURA DE ARQUIVOS ATUAL

```
app/manufatura/
├── __init__.py
├── models.py
├── escopo.md
├── routes/
│   ├── __init__.py
│   ├── dashboard_routes.py  ✅ NOVO - Hub inicial
│   ├── previsao_demanda_routes.py  ✅ ATIVO
│   └── necessidade_producao_routes.py  ✅ NOVO
├── services/
│   ├── __init__.py
│   ├── demanda_service.py  ✅ ATIVO
│   └── necessidade_producao_service.py  ✅ NOVO
└── templates/manufatura/
    ├── index.html  ✅ NOVO - Tela inicial do módulo
    ├── previsao_demanda_nova.html  ✅ ATIVO
    └── necessidade_producao.html  ✅ NOVO
```

## 🔗 ROTAS DISPONÍVEIS

**Hub Principal:**
- `/manufatura/` → Tela inicial com cards de acesso

**Previsão de Demanda:**
- `/manufatura/previsao-demanda` → Tela de Previsão de Demanda
- `/manufatura/api/previsao-demanda/*` → APIs da Previsão de Demanda

**Necessidade de Produção:** ✅ NOVO
- `/manufatura/necessidade-producao` → Tela de Análise de Necessidade
- `/manufatura/api/necessidade-producao/calcular` → Calcula necessidade por produto
- `/manufatura/api/necessidade-producao/projecao-estoque` → Projeção D0-D60
- `/manufatura/api/necessidade-producao/programar` → Programa produção

---

## 📝 HISTÓRICO DE ALTERAÇÕES

**25/10/2025 - Parte 2** - Implementação Necessidade de Produção:
- ✅ Criada tela inicial (hub) do módulo com cards de acesso
- ✅ Implementada funcionalidade completa de Necessidade de Produção
- ✅ Service com tratamento de UnificacaoCodigos
- ✅ Rotas API completas (calcular, projeção, programar)
- ✅ Template HTML responsivo com tabela, filtros e modal de projeção
- ✅ Fórmula implementada conforme especificação exata do escopo

**25/10/2025 - Parte 1** - Refatoração inicial:
- ❌ Removidas funcionalidades: Dashboard obsoleto, Master, Plano Mestre, Ordens de Produção, Integração Odoo, Requisições de Compras
- ✅ Mantida: Previsão de Demanda (funcional)
- 🎯 Objetivo: Reconstruir módulo gradualmente com processos bem definidos



Deu certo.
Agora vamos pensar o seguinte:
Quando uma pessoa for programar a produção, ela deverá visualizar os itens que há necessidade de programar e visualizar as diversas premissas que resultaram na conclusão de que "precisa programar", premissas essas que enxergo estar faltando apenas a qtd da carteira "s/data" onde seria "CarteiraPrincipal.qtd_saldo_produto_pedido - Separacao.qtd_saldo" para informações "macro".
Após a definilção de que "precisa produzir" é necessario avaliar "qto produzir" e "qdo produzir", onde para se definir isso, enxergo como premissas:
1- Capacidade de produção das maquinas - (definida em RecursosProducao, porem necessario remover "UniqueConstraint" pois há mais de uma maquina possivel produzir).
Com isso, é possivel ver qual/quais maquinas (maquinas = linhas de producao, trate como sinonimos) possuem espaço na linha tornando possivel programar, ver a qtd possivel a ser programada assim como ver quais produtos já estão programados naquela linha de produção.
2- Disponibilidade de componentes onde deverá ser avaliado através da ListaMateriais do produto avaliado e deverá ser renderizado por produto acabado:
- Todos os componentes nas linhas.
- Na frente de cada linha, a qtd em estoque, qtd consumida pela "qtd a ser programada", e uma projeção de estoque dos componentes para os próximos 60 dias.
Adicione um toggle para que a avaliação de estoque dos componentes possa ser avaliado através do estoque dos componentes ou da qtd possivel de produção (nada mais é do que a qtd dos componentes / pela qtd da estrutura)

lista de materiais -> Agora nesse momento, preciso avaliar o que é necessario para garantir que cada produto tenha a lista de materiais considerando que há componentes que podem ser comprados ou produzidos, onde esses componentes produzidos são produtos "intermediarios", podendo haver até 2 niveis de componentes produzidos (produto acabado -> componente intermediario 1 -> componente intermediario 2 -> componente comprado 3).

recursos de produção -> preciso garantir que não possua "unique constraint" em "RecursosProducao" para que com isso possa haver mais de 1 linha de producao por produto.

Me ajude a planejar em como fazer o que eu preciso de maneira que a lógica necessaria seja aplicavel.
CONFIRMAÇÃO DO ENTENDIMENTO: Entendi que você precisa implementar um sistema completo de programação de produção que permita ao usuário:
Visualizar necessidades de produção com todas as premissas (incluindo carteira s/data)
Avaliar capacidade produtiva por linha/máquina (múltiplas linhas por produto)
Verificar disponibilidade de componentes com estrutura multinível (até 2 níveis de intermediários)
Projetar estoque de componentes para 60 dias
Toggle entre visualização por estoque ou por capacidade produtiva


Após essa etapa, preciso criar estoque dos componentes e retirar inserir pedidos e faturamento apenas do que tiver "ORIGEM".
Segregar os estoques para considerar estoque dos componentes apenas do que houver compra