Agora preciso implementar uma camada no sistema de enorme importância, a gestão da carteira de pedidos e os estoques.
Hoje o processo começa apartir da importação da separação, porem ela é muito sensível quando falamos de cancelamento de pedidos, alteração de itens no pedido etc.
Portanto preciso implementar a:
1- Carteira de pedidos
2- Saldo de estoque
3- Programação de produção
4- Faturamento por produto (precisamos analisar se alteramos o RelatorioFaturamentoImportado ou se criamos um modulo com o faturamento em que o RelatorioFaturamentoImportado seria gerado apartir de um resumo desse novo faturamento)

Hoje trabalho essas informações em uma planilha, nela contem as seguintes abas:

1-	Carteira de pedidos, onde contem todos os pedidos aberto por produto, com qtd de pallets, peso, estoque projetado para os próximos dias por produto, data prevista de expedição, data prevista de entrega, data de agendamento, protocolo de agendamento, qtd prevista nesse embarque, além de todos os outros campos da carteira.
2-	Copia dessa carteira de pedidos utilizada para vincular o faturamento nos pedidos e com isso deduzir do estoque apenas os itens contidos nos pedidos (para evitar que uma troca de NF baixe os pedidos 2 vezes)
3-	Faturamento (Utilizado para adicionar o faturamento por produto e com isso vincular a cópia da carteira de pedidos
4-	Saldo de estoque, onde aparece apenas o saldo dos estoques, fruto do estoque inicial - faturamento baixado na copia da carteira + movimentação de estoque gerando um novo estoque inicial
5-	Programação de produção, onde há uma programação de produção com código dos produtos, qtd a ser produzida e data programada
6-	Movimentação de estoque, aonde se coloca tudo o que foi produzido, comprado, retrabalhado e avariado, hoje eu não coloco o faturamento nessa aba para prevenir baixas de NFs canceladas, porem podemos avaliar
7-	Conversão de códigos, pois há alguns produtos que são iguais porem estão com códigos diferentes, dessa forma unificamos o estoque desses itens no mesmo código
8-	Base de dados com palletização de cada item e peso de cada item
9-	Base de dados com rota
10-	Base de dados com sub rota

Hoje como funciona a baixa de estoque:

1-	Eu importo a carteira pendente do sistema e coloco ela em um excel em 2 abas, na carteira que eu mexo eu substituo a anterior pela nova, na “copia” eu analiso para ver se é um pedido novo ou alteração de um pedido existente ou alteração em decorrência do faturamento.
2-	Quando há faturamento, na copia mostra o saldo que ficou daquele pedido, dessa forma eu consigo ter uma relação de (pedido original – faturamento = carteira pendente). 
3-	Ou seja, na cópia ficará sempre a qtd por item por pedido que foi faturado, nunca ultrapassando a carteira para evitar considerar uma nf cancelada, porem é necessário uma analise para também evitar desconsiderar um pedido que foi faturado entre as atualizações da carteira
