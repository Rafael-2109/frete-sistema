Webhook
Seja bem vindo ao nosso Webhook!

O que é?
O Webhook TagPlus é um serviço que permite o ERP de um cliente notificar sistemas de terceiros sobre eventos, esses eventos podem ser criação ou alteração de produtos ou pedidos, dentre outros.

Como funciona?
Sempre que algum dado mudar no ERP, nossos servidores irão notificar seus servidores sobre qual mudança aconteceu no ERP, por exemplo um pedido ou produto criado.

Para que o webhook funcione basta que você cadastre sua URL de callback no menu Webhook do ERP (em breve o cadastro será possível via API).

O cadastro de um Webhook é constituido por quatro informações:

Nome da integração: O nome da integração fica a critério de quem a cadastrar, ex: Meu sistema de pedidos interno.
URL de Callback: A URL de callback é um ponto muito importante, informe nesse campo a URL a qual nossos servidores devem mandar as requisições de que vão informar as mudanças. Ex: http://lojadepneuspneubom.com.br/webhook, nessa URL será realizada uma requisição POST, abaixo vamos detalhar o corpo da chamada.
X-Hub-Secret: O Hub Secret é uma chave (ou token) a qual você receberá no header X-Hub-Secret da requisição, essa chave é definida por você, o importante é que a chave que você espera receber seja a mesma que for salva nesse campo, o preenchimento dessa informação é opcional, porém, recomendamos usá-la para garantir que apenas nossos servidores consigam disparar eventos em sua URL.
Eventos de Disparo: Os eventos de disparo são os acontecimentos de mudanças de dados no ERP que vão determinar que devemos chamar sua URL de callback informando o que aconteceu, ou seja, caso o evento de disparo pedido_criado esteja, marcado em algum webhook cadastrado, quando um usuário criar um pedido, o ERP irá notificar os webhooks cadastrados enviando informações desse novo pedido criado.
Corpo da requisição
Os dados enviados na chamada webhook são Content-Type: application/json

Exemplo de requisição que nossos servidores fará para notificar os eventos.
curl -X POST \
http://lojadepneuspneubom.com.br/webhook \
-H 'content-type: application/json' \
-H 'x-hub-secret: ABC123XPTO' \
-d '{
  "id": 999,
  "sistema": "pneubom",
  "uid": "5cd74b6782d706dc9134f863b65bea8e1a32e8a2",
  "event_type": "pedido_criado",
  "data": [
  {"id":"1"}
  ]
}'
Exempo de corpo enviado na requisição.

{
    "id": 999,
    "sistema": "pneubom",
    "uid": "5cd74b6782d706dc9134f863b65bea8e1a32e8a2",
    "event_type": "pedido_criado",
    "data": [
        {
            "id": "1"
        }
    ]
}
Agora vejamos o que é cada informação

CAMPO	DESCRIÇÃO
id	Código identificador do webhook cadastrado
sistema	Nome do sistema TagPlus
uid	Identificador único do sistema
event_type	Tipo de evento de disparo
data	Dados do registro criado, alterado ou apagado que disparou o evento webhook, nesse campo será retornado no mínimo o id do regitro, ex: id de um produto, id de um pedido. (usando essa informação você poderá recuperar os dados pela API.)
Utilizando Webhook em conjunto com a API TagPlus
A maior vantagem em utilizar nosso webhook é a possibilidade de usá-lo em conjunto com nossa API.

Se você possui um aplicativo que consome nossa API, para manter seu serviço atualizado em relação aos dados do ERP, ou seja, produtos, pedidos e outros recursos da API, seria necessário fazer requisições a cada minuto, hora, dia ou seja, requisições periódicas.

Utilizando o webhook, você poderá programar essas requisições de atualização de dados conforme os eventos de mudança que receber.

Consulte nosso guia da API aqui