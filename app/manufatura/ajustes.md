Preciso acrescentar um campo de ordem de produção nas produções realizadas.
<producoes_realizadas>

<tela_movimentacao_estoque>
1- Nas produções que são importadas através da tela de movimentacoes de estoque, tabela MovimentacaoEstoque, preciso acrescentar esse campo de ordem de produção.
2- Esse campo deverá ser exibido em uma coluna na tela de movimentações após "Observações".
3- Todos os produtos consumidos através dessa importação de "Produção" deverão ter esse campo propagado.
4- Para importação tipo_movimentacao=PRODUCAO sem ordem de produção preenchida, o sistema deverá aceitar a importação mas exibir um modal com "Produções sem ordem de produção", forçando o usuario a preenche-la.
5- Para movimentacoes do tipo_movimentacao=PRODUCAO sem ordem de produção preenchida, deverá ser exibido a contagem em um botão na tela de movimentacoes de produções (qtd de linhas com produto Tipo Origem RAIZ)
Esse botão deverá renderizar um MODAL com todas as linhas do tipo_movimentacao=PRODUCAO (ou PRODUÇÃO, não sei como está registrado, por precaução busque sempre sem "Ç" e "~") sem ordem de produção preenchida do Tipo Origem RAIZ com o campo de ordem de produção para ser preenchido.
Ao salvar, deverá ser propagado para todos os componentes recursivamente para manter o vinculo correto.
</tela_movimentacao_estoque>

<tela_manufatura_analise_producao>
1- Nessa tela, deverá ser agrupado por ordem de produção + produto.
2- Esse campo de Ordem de produção, tambem deverá ser exibido na tela em coluna no lugar de OPERAÇÂO.
3- A tela de analise-producao, tambem deverá conter filtro para ordem de produção, linha de produção (ou LOCAL) e nome do produto incorporado por "ILIKE" (Fitlrar N produtos).
4- O modal tambem deverá somar as qtds da ordem de produção + produto.
5- Os ajustes quando realizados, deverão ser registrados com a ordem de produção e se necessario pode usar a última "OPERAÇÂO" encontrada.
</tela_manufatura_analise_producao>

</producoes_realizadas>
