Preciso desenhar uma nova solução para:
# 1- Controlar as coletas da Carvia através de uma planilha rascunho onde poderá vincular à informações reais conforme forem "nascendo" no sistema, isto é: poderá registrar uma NF na mão, cliente da forma que a pessoa achar q é o nome, mas possibilitando vincular essa "nf na mão" à NF real, consolidando por exemplo nome do cliente com nome real. Ou seja, um rascunho para o pessoal poder trabalhar como "papel de pão" porem com lógica suficiente para se transformar em informação real, validada. Um exemplo desse "rascunho" é esse:[Image #1] Se puder ver as informações do sistema relativos a essas NF entenderá o q estou dizendo quanto a transição desse anexo para informações do sistema com PDF, CTE, Fatura. Essa coleta deverá conter valor da coleta, Contratado, placa, destino (CD Victorio Marchezine / CD Tenente Marques), data prevista, data coletada bool + data/hora e essa coleta deverá criar uma despesa a ser conciliada.
# 2- Controle de recebimento dos produtos da Carvia por coleta conferindo por chassi:
## A. Motos deverão ser conferidos o recebimento pelo chassi através do QR Code + auto-complete caso preenchido a mão + permitindo anexar Foto.
### Não precisa validar cor, apenas modelo e chassi.
## B. Cada linha do recebimento (NF se houver já) será validada moto a moto diante do recebimento por chassi, ou seja, quando todos os chassi da NF forem recebido, o sistema da a NF como recebida, mas lembrando que o recebimento é por Moto e não por NF.
# 3- Criar um "Portal do Cliente" para os clientes da Carvia:
## A. Enxergarem o status das suas NF (Coletado -> Recebido Matriz SP -> Embarcado -> Recebido Filial Entrega -> Entregue)
## B. Cotarem um frete
# 4- Essa Flag de CD Victorio Marchezine / CD Tenente Marques deverá haver uma lógica + Coletado -> Recebido Matriz SP -> Embarcado -> Recebido Filial Entrega -> Entregue)propagação dessa informação + cores padronizadas em todos os locais onde a flag for exibida (Amarelo com letra preta pra Victorio Marchezine / Badge Roxo com letra branca pra Tenente Marques) para diversos locais da seguinte forma:
## A. NF carregar Flag (Sem ação)
## B. Pedido exibido na VIEW url /pedidos/lista_pedidos carregar flag (Sem ação)
## C. Controle de Portaria atual será bifurcado em 2 através do acesso de Controle da Portaria -> 2 Cards [Victorio Marchezine, Tenente Marques] controlado pelo campo default (local_cd=Victorio Marchezine).
## D. Preencher todos os registros históricos com esse default.
## E. Cadastro de motoristas pode ser compartilhado
## F. Histórico, embarques pendentes, motoristas na portaria, etc deverá ser controlado respeitando a flag de local_cd pois haverão 2 portarias e cada porteiro deve controlar a sua portaria.
## G. Todos os pedidos Nacom serão default Victorio Marchezine.
## H. Os pedidos da Carvia poderão haver as 2 flags.
## I. Vinculo da portaria ao Embarque deverá processar respeitando a flag (preenchimento de data_embarque, registro no monitoramento, etc).
## J. Monitoramento deverá haver essa flag apenas nos pedidos != Nacom.
# 5. Roteirização, cotação nada muda.
# 6. Monitoramento deverá conter 1 campo de "chegada filial" para os pedidos carvia registrando "bool" + data e hora.
# 7. Nos primeiros tópicos eu citei "Coletado -> Recebido Matriz SP -> Embarcado -> Recebido Filial Entrega -> Entregue" para ser exibido aos clientes, diante do contexto veja cada campo que alimentará esse portal.
# 8. Acesso ao portal será granularizado da seguinte forma:
## A. Cientes deverão ser agrupados login -> N CNPJ destino
## B. Vendedores Motochefe deverão ser agrupados por "Cliente Comercial" (entidade que já possui cnpj vinculado)