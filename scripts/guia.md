Api v2.0
Este guia vai esclarecer algumas questões da API como autenticação, formatos e parâmetros aceitos. Caso você queira consultar a lista dos métodos da API consulte a referência.

Qualquer dúvida, envie email para integracoes@tagplus.com.br

Formato
O formato (Content-Type) utilizado no corpo (body) das requisições e respostas deve ser JSON ou XML.

Versão
Para manter o mínimo de compatibilidade, é necessário informar a versão da API em toda requisição feita.

Informe no cabeçalho X-Api-Version a versão desejada. A versão atual é a 2.0.

Verbos e recursos
Existem duas partes importantes da requisição: URL e Verbo HTTP.

A URL indica o recurso. Recurso pode ser um cadastro (cliente, produto), uma movimentação (pedido, nfe, venda) ou até mesmo uma configuração do ERP.

Já o verbo HTTP indica a ação a ser feita. De forma geral, os verbos aceitos são: GET, POST, PUT, PATCH, DELETE.

Antes de explicar cada um dos verbos precisamos entender o conceito de coleção e item.

Dizemos coleção quando a requisição tem como alvo um conjunto de recursos. Se uma requisição retorna uma lista de produtos ou clientes, ela está atuando sobre uma coleção. Um exemplo seria /produtos que retorna todos os produtos cadastrados. Por padrão a coleção inclui apenas os principais campos de cada recurso na resposta.

O item se aplica quando estamos lidando com apenas um recurso. Tomando como exemplo produtos, para recuperar apenas um e não vários teríamos a seguinte URL: /produtos/234, onde 234 é o ID do produto. Por padrão todos os campos são retornados quando um item é acessado.

Na medida do possível utilizamos os verbos HTTP de acordo com a especificação:

CRUD	Verbo HTTP	Coleção (/produtos)	Item (/produtos/1)
CREATE	POST	Cria um cadastro	Não permitido
READ	GET	Retorna uma lista	Retorna um item específico
UPDATE	PUT/PATCH	Não permitido	Atualiza um item
DELETE	DELETE	Não permitido	Apaga um item
Nota: os recursos sempre estarão no plural.

Parâmetros
Alguns métodos da API aceitam parâmetros que indicam como a requisição deve ser interpretada.

Esses parâmetros podem estar nos seguintes componentes da requisição:

Caminho (path):
Em produtos/1, o 1 é o parâmetro id em /produtos/{id}.

Nota: também chamado de segmement.

Cabeçalho (header):
Um exemplo é a versão da API citada acima: X-Api-Version: 2.0.

Exemplo prático em curl:

$ curl -H 'X-Api-Version: 2.0' "https://api.tagplus.com.br/clientes"
Query string
Um exemplo pra recuperar somente os fornecedores ativos e que não recebem e-mail:
https://api.tagplus.com.br/fornecedores?ativo=1&recebe_email=0

Observe que o & é utilizado para concatenar os vários parâmetros da query string.

Corpo (body)
Mais comum em operações de criação (POST) e atualização (PUT/PATCH) de recursos.

Exemplo em curl para criar um produto:

$ curl -d '{"codigo": "8947328947198", "descricao": "Televisor"}' "https://api.tagplus.com.br/produtos"
Body no GET
Normalmente, uma requisição de verbo GET apenas aceita parâmetros na própria URL, mas algumas vezes esses parâmetros possuem valores inválidos ou são muito grandes.

Nesses casos é possível enviar um header na requisição para aceitar parâmetros no body, como se fosse um POST ou PATCH:

"X-Accepts-Body": 1
Assim, os filtros que normalmente seriam usados na URL podem ser usados no body também:

curl --request GET 'https://api.tagplus.com.br/clientes?fields=ativo' \
--header 'x-accepts-body: 1' \
--header 'Content-Type: application/json' \
--data '{
    "ativo": true
}'
Paginação
É possível paginar qualquer resultado de chamadas feitas para uma coleção. Os parâmetros são passados na requisição no componente query string.

Lista dos parâmetros aceitos:

page: indica a página desejada
per_page: indica a quantidade de registros por página
"https://api.tagplus.com.br/produtos?page=2&per_page=100"
Ordenação
Para ordenar os resultados utilize o parâmetro sort. Por padrão a ordem é ascendente, caso queira inverter basta colocar o sinal de menos ("-") antes do campo. Exemplo de ordenação descendente por data de alteração: sort=-data_alteracao

Também é possível informar vários campos, basta separá-los por vírgula.

"https://api.tagplus.com.br/produtos?sort=-data_alteracao,preco"
Filtros
Limitar os itens retornados, coloque o campo na query string no formato campo=valor.

Exemplo para recuperar somente os clientes ativos:

$ curl "https://api.tagplus.com.br/clientes?ativo=1"
A comparação feita é de igualdade, todo o conteúdo deve ser idêntico.

Quando o valor é verdadeiro ou falso você pode indicar 1 ou true para verdadeiro e 0 ou false para falso.

Filtro de Data
É possível buscar na api utilizando os campos since (início) e until (fim) nos params da request. São suportadas datas no formato YYYY-mm-dd H:i:s ou Unix timestamp.

Por padrão a data considerada no filtro é rederente ao campo data de alteração. Para considerar outra data é possível passar no header x-data-filter ou X-Data-Filter com algum dos seguintes valores data_alteracao, data_criacao, data_vencimento, data_competencia.

Para o x-data-filter ser válido o campo de data tem que existir naquele endpoint.

$ curl --request GET 'https://api.tagplus.com.br/vendas_simples?since=1611083180' \
--header 'X-Data-Filter: data_confirmacao' \
Esta retorna todas vendas simples desde a data referenciada como Unix Timestamp, podendo ser utilizada tambem com o parâmetro 2021-01-19 19:06:20 vide exemplo abaixo

$ curl --request GET 'https://api.tagplus.com.br/vendas_simples?since=1611083180&until=2021-01-19 19:06:20' \
--header 'X-Data-Filter: data_confirmacao' \
Busca
Ao contrário dos filtros, a busca não faz uma comparação de igualdade.

O valor passado para a busca é comparado com principais campos do recurso, bastando um pedaço ser igual.

Poderíamos dizer que seria algo como um LIKE '%busca%' no MySQL.

Buscar todos os clientes que tenham Silva em algum campo, seja nome, razão social e outros:

$ curl "https://api.tagplus.com.br/clientes?q=Silva"
A sintaxe é q=termo na query string.

Campos
Lembrando que, diferente de acessar um item, por padrão o retorno de uma coleção não inclui todos os campos, apenas os principais.

Você também pode especificar exatamente quais campos deseja na resposta, basta incluir o parâmetro fields na query string.

Digamos que queira apenas o nome e a descrição dos produtos cadastrados:

"https://api.tagplus.com.br/produtos?fields=nome,descricao"
Existe uma opção curinga para trazer todos os campos: fields=*.

Escopos de Permissão
O que são?
O escopo de permissão define quais operações são autorizadas por aplicativo autenticado, ou seja, você só pode salvar produtos via API se o usuário permitir.

Como usar?
O escopo é definido no momento da autorização do usuário no seu app, o escopo é armazenado em nossa base junto ao token que você recebe para acessar os dados do usuário, verifique no Guia como funciona a solicitação de escopo ao solicitar um token.

Como eles são?
Na sessão OAuth2 Scopes dos esquemas de autenticação que está logo abaixo é possível ver exemplos de escopos. Os métodos HTTP (GET, POST..., etc) e recursos (/produtos, /pedidos..., etc) definem o formato dos escopos de permissão. Basicamente, temos um prefixo e sufixo separados por : (dois pontos), onde o prefixo é a operação podendo ser de escrita ou leitura e o sufixo o recurso o qual é permitido a operação.

Exemplo:
Se você deseja enviar uma requisição GET para acessar dados no recurso /produtos você deve possuir um token que contemple o escopo read:produtos, onde read representa leitura. Já para fazer um POST em /produtos você precisará da permissão write:produtos, onde write representa escrita. Para solicitar mais de um escopo, basta enviar o parâmetro scope com todos escopos necessários separados por espaço, 'write:produtos read:pedidos' ou seja,
?scope=write:produtos+read:pedidos.

É importante saber que escopos de escrita por padrão permitem a leitura, ou seja, se seu token permite write:produtos, executar um GET em /produtos será permitido.

Autenticação oAuth2
Todas as requisições precisam estar devidamente autenticadas, do contrário serão recusadas.

Caso ainda não conheça a framework OAuth2 veja este guia que explica de forma simplificada como funciona.

Cadastro
O primeiro passo pra você, desenvolvedor, é se registrar. Para isso basta clicar no link Cadastrar no canto superior direito.

Depois de cadastrado você poderá adicionar os aplicativos que você possui e deseja integrar com o nosso ERP.

O cadastro é bem simples, você informará um nome e uma URL de retorno para receber as respostas. Ao cadastrar um aplicativo será gerado um Client ID e um Client Secret. Nunca compartilhe o Client Secret!

Nossa API suporta dois fluxos de autenticação OAuth2: Authorization Code Grant e Implicit Grant.

Aplicativos WEB
Esse fluxo deve ser escolhido quando seu aplicativo é WEB e o código fonte não é acessível pelo cliente. A lógica e processamento são feitos no servidor e nenhum dados sensível é visível para o cliente (navegador).

Esse fluxo é a implementação do Authorization Code Grant e abaixo segue a explicação.

1. Redirecionar o usuário para o ERP
Você deve redirecionar o usuário para a tela de autorização no ERP:

GET https://developers.tagplus.com.br/authorize
Você também deve inserir os seguintes parâmetros na query string:

Nome	Descrição
response_type	Obrigatório. Informe code.
client_id	Obrigatório. O Client ID recebido ao registrar a aplicação.
redirect_uri	Não suportado. URL de retorno do seu aplicativo que processa o code. (A versão atual da API não aceita esse parâmetro, mas está documentado porque é comum nas autorizações OAuth2. Dessa forma a URL de retorno utilizada será a informada no momento do cadastro do aplicativo)
scope	Obrigatório. O Scope define os recursos e operações que o aplicativo poderá utilizar. Exemplo: O escopo de acesso para recuperar produtos da API seria permitido por ?scope=read:produtos e para recuperar pedidos é ?scope=read:pedidos, para solicitar os dois escopos desse exemplo você deve envia-los separados por espaço como exemplo read:produtos read:pedidos
state	Opcional O State É um parâmetro definido livremente por você, enviado na url de callback. Ex: minha_flag
Depois de inserir os parâmetros na querystring, a requisição final ficaria assim:

GET https://developers.tagplus.com.br/authorize?response_type=code&client_id=XXX&scope=write:produtos+read:pedidos&state=minha_flag
2. ERP redireciona o navegador para seu sistema
Depois que o cliente aceitar, ou recusar, dar permissão ao seu aplicativo, o ERP vai redireciná-lo para sua URL de retorno (redirect_uri). O endereço da sua URL de retorno (redirect_uri) deve receber code e a partir dele pegar um access token.

Fique atento, pois esse code é temporário e poderá ser utilizado apenas uma vez.

Exemplo: se a sua URL de retorno é https://meuapp.com.br/oauth2, o ERP vai redirecionar o usuário para:

GET https://meusite.com.br/oauth2?code=XXX&state=minha_flag
Depois que o código for recebido deve ser feita uma chamada para recuperar um access token:

POST https://api.tagplus.com.br/oauth2/token
Parâmetros

Nome	Descrição
grant_type	Obrigatório. Informe authorization_code
code	Obrigatório. O code recebido como resposta no passo 1.
client_id	Obrigatório. O Client ID recebido ao registrar a aplicação.
client_secret	Obrigatório. O Client Secret recebido ao registrar a aplicação
redirect_uri	Não suportado. URL de retorno do seu aplicativo que processa o code. (A versão atual da API não aceita esse parâmetro, mas está documentado porque é comum nas autorizações OAuth2. Dessa forma a URL de retorno utilizada será a informada no momento de cadastrar o aplicativo)
Os parâmetros acima devem ser passados no corpo da requisição no formato application/x-www-form-urlencoded.

Você receberá uma resposta em JSON nesse formato:

{
    "refresh_token": "XXX",
    "token_type": "bearer",
    "access_token": "XXX",
    "expires_in": 86400
}
Você deverá guardar todas essas informações!

3. Acessar API usando o access token
Agora você pode fazer sua requisição utilizando o access token.

Exemplo de uma requisição para recuperar produtos:

GET https://api.tagplus.com.br/produtos?access_token=XXX
Você pode passar o access token na query string como mostrado acima, mas uma forma mais limpa é colocá-lo no header de autorização:

Authorization: Bearer XXX
4. Atualizar token
Observe que a resposta do passo 2 tem o atributo expires_in. Ele indica o tempo que o token é válido em segundos. O tempo do exemplo é o padrão utilizado pela nossa API.

Quando esse tempo expirar você receberá uma resposta com o código 401 Unauthorized indicando que o token é inválido ou expirou.

Nesse caso você deve fazer uma requisição para recuperar um novo access token e para isso vai precisar do refresh_token recebido no passo 2.

URL para atualizar o token:

POST https://api.tagplus.com.br/oauth2/token
Parâmetros

Nome	Descrição
grant_type	Obrigatório. Informe refresh_token
refresh_token	Obrigatório. O refresh_token recebido como resposta no passo 2.
client_id	Obrigatório. O Client ID recebido ao registrar a aplicação.
client_secret	Obrigatório. O Client Secret recebido ao registrar a aplicação
Os parâmetros acima devem ser passados no corpo da requisição com o formato application/x-www-form-urlencoded.

A resposta é semelhante à do passo 2. Novamente os dados recebidos devem ser guardados para uma próxima atualização do token.

Aplicativos públicos
São considerados aplicativos públicos aqueles que não conseguem manter dados sensíveis como senhas seguros.
Quando isso acontece deve ser usado um fluxo de autenticação que não precise das credenciais do aplicativo (Client Secret).

Este fluxo é a implementação do Implicit Grant.

Na definição do OAuth2 existem dois tipos de aplicativos públicos:

Aplicativo Nativo: são aqueles instalados no dispositivo do usuário, normalmente um celular ou computador;
Aplicativo de Navegador: são executados inteiramente no cliente, o código fonte é baixado de um servidor mas toda a execução é feita no navegador do cliente.
Os aplicativos de navegador são comumente chamados de in-browser app ou browser-based app.

1. Redirecionar usuário para o ERP
Leve o usuário ao ERP para que ele possa autorizar sua aplicação:

GET https://developers.tagplus.com.br/authorize
Coloque também os seguintes parâmetos na query string:

Nome	Descrição
response_type	Obrigatório. Informe token.
client_id	Obrigatório. O Client ID recebido ao registrar a aplicação.
redirect_uri	Não suportado. URL de retorno do seu aplicativo que processa o code. (A versão atual da API não aceita esse parâmetro, mas está documentado porque é comum nas autorizações OAuth2. Dessa forma a URL de retorno utilizada será a informada no momento do cadastro do aplicativo)
scope	Obrigatório. O Scope define os recursos e operações que o aplicativo poderá utilizar. Exemplo: O escopo de acesso para recuperar produtos da API seria permitido por ?scope=read:produtos e para recuperar pedidos é ?scope=read:pedidos, para solicitar os dois escopos desse exemplo você deve envia-los separados por espaço como exemplo read:produtos read:pedidos
Depois de colocar os parâmetros a URL ficará assim:

https://developers.tagplus.com.br/authorize?response_type=token&client_id=XXX&scope=write:produtos+read:pedidos
No caso dos aplicativos nativos, aconselhamos chamar o navegador padrão do sistema operacional onde o programa está sendo executado.

Já nos aplicativos de navegador não deve haver problema, pois ele já está sendo executado no próprio navegador.

2. ERP redireciona usuário de volta para seu aplicativo
O ERP vai redirecionar o usuário para sua URL de retorno (redirect_uri) no seguinte formato:

https://meuapp.com.br/oauth2#token_type=bearer&access_token=XXX
Nos aplicativos nativos você terá um trabalho a mais, pois o usuário vai autenticar fora do seu aplicativo. Então de alguam forma seu aplicativo deve acionado a partir da URL de redirecionamento do ERP. Normalmente é preciso fazel algum tipo de registro no sistema operacional para fazer isso.

Alguns links que podem ajudar:

OAuth2 Simplified - Mobile Apps
Registering an Application to a URI Scheme
Handling App Links
Já os aplicativos de navegador precisam de menos esforço, conforme pode ser visto nesta explicação.
3. Acessar API usando o access token
Agora que você já tem a autorização, basta fazer a requisição pra API colocando o access token.

GET https://api.tagplus.com.br/clientes?access_token=XXX
Apesar de ser possível passar via query string a forma preferível é passar no cabeçalho, exemplo em curl:

$ curl -H 'Authorization: Bearer XXX' "https://api.tagplus.com.br/clientes"
Respostas HTTP
Sucesso
2xx
Esta classe de códigos de status indica a ação solicitada pelo cliente foi recebida, compreendida, aceita e processada com êxito.

200 Requisição Válida
A requisição foi realizada com sucesso.

201 Criado
Indica que a requisição foi bem sucedida e que um novo recurso foi criado.

Erro de cliente
4xx
A classe 4xx de código de status é destinado para os casos em que o cliente parece ter cometido um erro.

400 Requisição inválida
O pedido não pôde ser entregue devido à sintaxe incorreta.

401 Não autorizado
Foram fornecidas credenciais inválidas de acesso.

402 Pagamento necessário
Este código é retornado quando um cliente está em débito por mais de 7 dias, o acesso será liberado no dia seguinte à identificação do pagamento.

403 Proibido
O pedido é reconhecido pelo servidor mas este recusa-se a executá-lo.

404 Não encontrado
O recurso requisitado não foi encontrado, verifique se a url de chamada está correta.

Outros Erros
5xx
A classe 5xx de código de status é destinado para os casos em que ocorrem erros em nossos servidores. Caso você encontre um desses erros favor entrar em contato com o suporte.

500 Erro interno do servidor
O pedido não pôde ser entregue devido à um erro interno no servidor.

501 Não implementado
O servidor ainda não suporta a funcionalidade ativada.

502 Bad Gateway
Este problema esta relacionado a execução dos nossos servidores e antes de analisar este problema, é necessário limpar o cache do navegador completamente.

503 Serviço indisponível
O pedido é reconhecido pelo servidor mas este recusa-se a executá-lo. Causas comuns são um servidor que está em manutenção ou sobrecarregado.

Exceptions
Deu erro?
Durante as requisições na API podem ocorrer algumas exceções nas faixas de HTTP CODE 400 e 500. Sempre que uma exceção ocorrer será retornado um objeto contendo informações da exceção. É possível que não exista erro algum, mas sim parâmetros incorretos na requisição feita.

Veja abaixo um exemplo de exceção gerada pela requisição DELETE /clientes/{id}

Requisição
  curl -X DELETE \
  http://api.tagplus.com.br/clientes/8 \
  -H 'Authorization: Bearer {TOKEN}' \
  -H 'Cache-Control: no-cache' \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Version: 2.0'
Resposta
  {
    "error_code": "apagar_cliente_vinculado",
    "message": "O cliente possui vinculos, portanto não pode ser apagado, se preferir ele pode ser desativado.",
    "dev_message": "O cliente possui vinculos, portanto não pode ser apagado, é possível desativar o cliente enviando uma requisição PATCH com o corpo {\"ativo\":false}. Para saber mais verifique a documentação da API  e tente novamente.",
    "data": [
        {
            "id": "8",
            "field": null
        }
    ]
  }
Corpo de Exceção
Note que o corpo da exceção acima possui quatro propriedades, são elas:

error_code: Constante de erro, a qual pode ser usada para mapear os erros da API. Aqui serão apresentadas todas contantes existentes.
message: Mensagem de erro. O ponto importante da diferenciação entre 'message' e 'dev_message' está em quem é o alvo dessa mensagem. As mensagems nessse campo são para os usuários das aplicações que consomem a API.
dev_message: Já as mensagems nessse campo são os desenvolvedores das aplicações que consomem a API.
data: Essa propriedade é do tipo array e conterá dados sobre a exceção retornada, conforme exemplo de requisição acima.

Constantes de Códigos de Erros error_code
nao_encontrado é retornado quando não encontrado algum dado, seja produto, pedido, cliente, dentre outros. Ex: GET /produtos/{id} se o produto não existe, será retornado HTTP CODE 404 e {"error_code":"nao_encontrado"}
operacao_nao_permitida é retornado quando uma operação não pode ser realizada.
apagar_cliente_vinculado é retornado quando executado DELETE em um cliente possui vínculos que podem ser com: vendas, pedidos, notas. Ex: DELETE /clientes/{id} se o cliente possui vinculo, a API rejeitará a operação devolvendo um HTTP CODE 403 e {"error_code":"apagar_cliente_vinculado"}
escopo_nao_autorizado é retornado quando uma aplicação tenta usar um recurso em que o escopo do token não permite, a API rejeitará a operação devolvendo um HTTP CODE 401 e {"error_code":"escopo_nao_autorizado"}
apagar_conta_vinculada é retornado quando executado DELETE em uma conta bancária que possui vínculos. Ex: DELETE /contas/{id}
apagar_financeiro_confirmado é retornado quando executado DELETE em um financeiro que está confirmado. Ex: DELETE /financeiros/{id}
nota_sem_faturamento é retornado quando uma nota é criada ou atualizada e enviada para aprovação da SEFAZ, porém sem faturamento. Ex: POST /nfces
produtos_sem_tributacao é retornado quando uma nota é criada ou atualizada e enviada para aprovação da SEFAZ, porém os produtos informados não possuem tributação definida.
error_serie_nfce_nao_configurada é retornado quando tenta-se salvar uma nota porém o ERP ainda não foi configurado para emissão de NFC-e. Acesse as configurações do ERP na aba Nota Fiscal e informe a sério da NFC-e.
base64_formato_invalido é retornado quando a string de base64 enviada enviada via API é inválida. Exemplo salvar imagens para produtos.
campo_obrigatorio é retornado quando um campo pode ser obrigatório conforme a regra de negócio, exemplo se uma nota possui frete, o campo transportadora é de preenchimento obrigatório. Verifique a posição 'field' na resposta, ela conterá o campo que é obrigatório.
alterar_nota_nao_autorizado é retornado quando tenta-se alterar dados em uma nota já aprovada, cancelada ou inutilizada, só é possivel alterar notas em estado de digitação.
permissao_editar_data_lancamento_financeiro é retornado quando tenta-se enviar a data de um lançamento financeiro sem possuir permissão para alterar essa data com o perfil de aceso atual.
permissao_editar_data_confirmacao_financeiro é retornado quando tenta-se enviar a data de confirmação de um lançamento financeiro sem possuir permissão para alterar essa data com o perfil de aceso atual.
permissao_editar_valor_juros_financeiro é retornado quando tenta-se enviar o valor de juros de um lançamento financeiro sem possuir permissão para alterar esse valor com o perfil de aceso atual.
permissao_estornar_pedido é retornado quando tenta-se estornar um pedido sem possuir permissão.
permissao_estornar_venda_simples é retornado quando tenta-se estornar uma venda simples sem possuir permissão.
permissao_alterar_data_confirmacao_movimentacoes é retornado quando tenta-se alterar uma data de confirmação de uma movimentação. Ex: Venda Simples;
permissao_alterar_vendedor_vinculado_cliente é retornado quando tenta-se alterar a lista de vendedores vinculados ao cliente. Ex: Venda Simples;
permissao_alterar_estoque_produto é retornado quando tenta-se alterar a quantidade de estoque de um produto diretamente em seu registro.
item_sem_valor_venda é retornado quando tenta-se registrar uma venda ou pedido indicando um item sem indicar seu valor de venda, podendo ser os campos valor_venda ou valor_unitario.
pagamento_pendente é retornado quando o sistema em que está usando a API possui débitos em aberto e precisa se regularizar com o setor Comercial da Tagplus.
permissao_alterar_valor_unitario é retornado quando criar ou alterar uma venda, nota ou pedido e nos itens informar o 'valor_unitario' sem que o usuário tenha permissão para alterar o valor unitário de produtos, verifique essa permissão no menu Perfil de Acesso do ERP ou para informar o valor do item deve-se informar a posição 'valor_venda' com ID do valor de venda do produto no item da venda ou pedido.
Aviso
Estamos trabalhando para gerar novas constantes de erros para que você possa tratar suas chamadas em nossa API com mais robustez.

SDK
Agora que você já sabe de tudo sobre a API! Vamos programar!!!