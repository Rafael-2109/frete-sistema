1- Montar lista/dict com os produtos de CarteriaPrincipal
2- Query de todos os produtos da CarteiraPrincipal ou de todos geral em MovimentacaoEstoque
3- Query de todos os produtos da CarteiraPrincipal ou de todos geral em ProgramacaoProducao por data
4- Query de todas as Separações com sincronizado_nf=False
5- Montar uma matriz eixo X - produto
6- Eixo Y - D0= MovimentacaoEstoque, D1= "D"(1-1) + ProgramacaoProducao"D"(1-1) - Separacao.sincronizado=False"D"(1-1), D2= "D"(2-1) + ProgramacaoProducao"D"(2-1) - Separacao.sincronizado=False"D"(2-1)....
ruptura_7d=min(D0:D7)
7- Comparar qtd_saldo_produto_pedido com ruptura_7d:
If qtd_saldo_produto_pedido > ruptura_7d
then
Disponivel
Else
if qtd_saldo_produto_pedido > D7 then (linha debaixo) else (testa pra cima) if qtd_saldo_produto_pedido > D8 ....
if qtd_saldo_produto_pedido > D6 then (linha debaixo) else D7 (visto que D7 já testou na linha acima)
if qtd_saldo_produto_pedido > D5 then....

8- Depois disso, terá os itens "Disponivel" e a data possivel para cada item de cada pedido, ai se faz um "max.cod_produto.por pedido"
9- Com isso monta %valor.Disponivel | "max.cod_produto.por pedido"