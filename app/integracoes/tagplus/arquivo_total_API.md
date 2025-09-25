API ERP (2.0.0)
Download OpenAPI specification:Download

pre vendas
Reúne Pedidos, Pedidos de Compras e Ordens de Serviços.

Listar Pré-Vendas
Recupera Pedidos, Pedidos de Compras e Ordens de Serviços salvos no sistema.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/pre_vendas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"tipo": "OS",
"numero": 0,
"status": "A",
"data_criacao": "string",
"hora_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_alteracao": "string",
"data_abertura": "string",
"data_confirmacao": "string",
"departamento": {},
"funcionario": {},
"vendedor": {},
"cliente": {},
"fornecedor": {},
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_total": 0,
"observacoes": "string"
}
]
pedidos
No ERP os pedidos tem o nome de Pedidos/Orçamentos.

Listar pedidos
Recupera pedidos salvos no sistema.

AUTHORIZATIONS:
Authorization_Code_FlowImplicit_Flow
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

X-Totalizadores	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

Responses
200 Sucesso!

GET
/pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24",
"hora_criacao": "11:00:00",
"data_entrega": "2017-01-25",
"hora_entrega": "15:00:00",
"data_confirmacao": "2017-01-25",
"departamento": {},
"cliente": {}
}
]
Criar pedido
Você pode enviar um corpo vazio para criar um pedido sem produtos.

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

hora_criacao	
string
Hora de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

hora_confirmacao	
string
Hora de confirmação do pedido.

departamento	
integer
Campo identificador do departamento ao qual o pedido está vinculado, saiba como recuperar departamentos clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pelo pedido, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual o pedido foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens do pedido.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

valor_acrescimo	
number
Valor de acrescimo do pedido.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

integracao	
string
Caso o pedido veio de alguma integração, informa o nome do parceiro.

possui_vinculo	
boolean
Identifica se o Pedido possui algum vínculo no sistema.

Responses
201 Pedido criado!

POST
/pedidos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"hora_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"departamento": 0,
"vendedor": 0,
"cliente": 0,
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"observacoes": "string",
"integracao": "string",
"possui_vinculo": true
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24",
"hora_criacao": "11:00:00",
"data_entrega": "2017-01-25",
"hora_entrega": "15:00:00",
"data_confirmacao": "2017-01-25",
"departamento": {
"$ref": "departamento.yaml#/example"
},
"cliente": {
"$ref": "cliente.yaml#/example"
}
}
Recuperar pedido
Recupera um pedido detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/pedidos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24",
"hora_criacao": "11:00:00",
"data_entrega": "2017-01-25",
"hora_entrega": "15:00:00",
"data_confirmacao": "2017-01-25",
"departamento": {
"$ref": "departamento.yaml#/example"
},
"cliente": {
"$ref": "cliente.yaml#/example"
}
}
Editar pedido
Atualiza as informações do pedido.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

hora_criacao	
string
Hora de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

hora_confirmacao	
string
Hora de confirmação do pedido.

departamento	
integer
Campo identificador do departamento ao qual o pedido está vinculado, saiba como recuperar departamentos clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pelo pedido, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual o pedido foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens do pedido.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

valor_acrescimo	
number
Valor de acrescimo do pedido.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

integracao	
string
Caso o pedido veio de alguma integração, informa o nome do parceiro.

possui_vinculo	
boolean
Identifica se o Pedido possui algum vínculo no sistema.

Responses
200 Pedido alterado!

PATCH
/pedidos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"hora_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"departamento": 0,
"vendedor": 0,
"cliente": 0,
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"observacoes": "string",
"integracao": "string",
"possui_vinculo": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24",
"hora_criacao": "11:00:00",
"data_entrega": "2017-01-25",
"hora_entrega": "15:00:00",
"data_confirmacao": "2017-01-25",
"departamento": {
"$ref": "departamento.yaml#/example"
},
"cliente": {
"$ref": "cliente.yaml#/example"
}
}
Apagar pedido
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Pedido apagado!

DELETE
/pedidos/{id}
Gera uma NF-e através de Pedido/Orçamento
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos/to_nfe/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Gera uma NFC-e através de Pedido/Orçamento
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos/to_nfce/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"transportadora": {
"transportador": {}
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
Gera uma NFS-e através de Pedido/Orçamento
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos/to_nfse/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Gera uma Venda Simples através de Pedido/Orçamento
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos/to_venda_simples/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [
"string"
],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
Gera uma Ajuste de Estoque através de Pedido/Orçamento
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Tipo-Ajuste
required
string
Example: E
Indica qual o tipo de ajuste de estoque será criado (entrada/saida).

X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos/to_ajuste_estoque/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/pedidos/pdf/recibo_a4/{id}
Recibo A4 PDF Resumido
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 resumido no formato PDF

GET
/pedidos/pdf/recibo_a4_resumido/{id}
Recibo Mini PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo Mini no formato PDF

GET
/pedidos/pdf/recibo_mini/{id}
Imprimir Listagem de Pedidos/Orçamentos
'Imprimir Listagem de Pedidos/Orçamentos'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Pedidos/Orçamentos no formato PDF

POST
/pedidos/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Mesclar Pedidos/Orçamentos
'Mesclar Pedidos/Orçamentos'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
mesclar_observacoes
required
boolean
Indica se irá mesclar as observações

agrupar
required
boolean
Indica se irá agrupar os produtos iguais.

opcoes
required
integer
Default: 0
Enum: 0 1 2
Opções:

0=Além de mesclar, manter os Pedidos/Orçamentos indicados como estão

1=Após mesclar, cancelar os Pedidos/Orçamentos indicados

2=Após mesclar, confirmar os Pedidos/Orçamentos indicados

ids
required
Array of integers
Id's dos pedidos que serão mesclados

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

Responses
200 Sucesso!

POST
/pedidos/mesclar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"cliente": 0,
"vendedor": 0,
"opcoes": 0,
"agrupar": true,
"mesclar_observacoes": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24",
"hora_criacao": "11:00:00",
"data_entrega": "2017-01-25",
"hora_entrega": "15:00:00",
"data_confirmacao": "2017-01-25",
"departamento": {},
"cliente": {}
}
]
Enviar e-mail Pedidos/Orçamento
'Enviar pedido por e-mail'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids
required
Array of integers
Ids das movimentações enviadas por email

emails	
Array of strings
Array com os e-mails para onde serão enviadas as movimentações.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

anexar_arquivos	
boolean
Default: false
Indica se os arquivos vinculados à movimentação serão anexados ao e-mail.

anexar_fotos_produtos	
boolean
Default: false
Indica se as fotos vinculadas aos produtos serão anexados ao e-mail.

Responses
200 Sucesso!

POST
/pedidos/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"enviar_para_todos": false,
"anexar_arquivos": false,
"anexar_fotos_produtos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Informa produtos inativos em um pedido
'Informa produtos inativos em um pedido'

Responses
200 Sucesso!

GET
/pedidos/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
Pedidos | Evolução de Criação
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/pedidos/evolucao_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"qtd": 0,
"qtd_medio": 0,
"valor": 0,
"valor_f": "string",
"vr_medio": 0,
"vr_medio_f": "string"
}
]
Pedidos | Pedidos Entrega
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/pedidos_entrega
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"origem": "string",
"data": "string",
"id_pedido": 0,
"numero_controle": "string",
"os": 0,
"tipo": "string"
}
]
Pedidos | Origem Pedidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/pedidos/origem_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"total": 0,
"valor": 0,
"origem": "string",
"os": 0,
"valor_f": "string"
}
]
Pedidos | Status
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/status_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"status": "string",
"total": 0,
"valor": 0,
"valor_f": "string"
}
]
Pedidos | Loja Virtual
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/loja_virtual
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"total": 0,
"status": "string",
"valor": 0,
"valor_f": "string"
}
]
Resumo | Pedidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/numeros
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"resumo_numero_dias": 0,
"total_pedidos": 0,
"total_pedidos_ecommerce": 0,
"total_pedidos_aberto": 0,
"total_pedidos_concluido": 0
}
Pedidos de Compra
No ERP os pedidos_compra tem o nome de Pedidos de Compra.

Listar pedidos de compra
Recupera pedidos de compra salvos no sistema.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/pedidos_compra
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": {},
"fornecedor": {},
"link": "string",
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"valor_total": 0,
"observacoes": "string",
"anexos": [],
"tem_fatura": true
}
]
Criar pedido de compra
Criar pedido de compra

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
itens
required
Array of objects (Item de Pedido)
Itens do pedido.

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

funcionario	
integer
Campo identificador do funcionario relacionado ao pedido.

fornecedor	
integer
Campo identificador do fornecedor para o qual o pedido foi aberto, saiba como recuperar fornecedors clicando aqui

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

Responses
201 Pedido de compra criado!

POST
/pedidos_compra
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": 0,
"fornecedor": 0,
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"observacoes": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"fornecedor": {
"razao_social": "OAS Swagger"
},
"link": "string",
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_total": 0,
"observacoes": "string",
"anexos": [
"string"
],
"tem_fatura": true
}
Recuperar pedido de compra
Recupera um pedido detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/pedidos_compra/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"fornecedor": {
"razao_social": "OAS Swagger"
},
"link": "string",
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_total": 0,
"observacoes": "string",
"anexos": [
"string"
],
"tem_fatura": true
}
Editar pedido de compra
Atualiza as informações do pedido de compra.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

funcionario	
integer
Campo identificador do funcionario relacionado ao pedido.

fornecedor	
integer
Campo identificador do fornecedor para o qual o pedido foi aberto, saiba como recuperar fornecedors clicando aqui

itens	
Array of objects (Item de Pedido)
Itens do pedido.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

Responses
200 Pedido de compra alterado!

PATCH
/pedidos_compra/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": 0,
"fornecedor": 0,
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"observacoes": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"fornecedor": {
"razao_social": "OAS Swagger"
},
"link": "string",
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_total": 0,
"observacoes": "string",
"anexos": [
"string"
],
"tem_fatura": true
}
Apagar pedido de compra
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Pedido de compra apagado!

DELETE
/pedidos_compra/{id}
Enviar e-mail Pedidos de Compra
'Enviar pedido de comrpa por e-mail'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids
required
Array of integers
Ids das movimentações enviadas por email

emails	
Array of strings
Array com os e-mails para onde serão enviadas as movimentações.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

anexar_arquivos	
boolean
Default: false
Indica se os arquivos vinculados à movimentação serão anexados ao e-mail.

anexar_fotos_produtos	
boolean
Default: false
Indica se as fotos vinculadas aos produtos serão anexados ao e-mail.

Responses
200 Sucesso!

POST
/pedidos_compra/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"enviar_para_todos": false,
"anexar_arquivos": false,
"anexar_fotos_produtos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o A4 no formato PDF

GET
/pedidos_compra/pdf/a4/{id}
Imprimir Listagem de Pedidos de Compra
'Imprimir Listagem de Pedidos de Compra'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Pedidos de Compra no formato PDF

POST
/pedidos_compra/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Gera uma NF-e através de Pedido de Compra
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos_compra/to_nfe/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Gera um ajuste de estoque de compra através de Pedido de Compra
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos_compra/to_ajuste_estoque/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
Gera uma nota fiscal de entrada através de Pedido de Compra
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/pedidos_compra/to_nota_fiscal_entrada/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"funcionario_responsavel": 0,
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": {
"id": 0,
"id_entidade": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"natureza_operacao": "string",
"pedido_vinculado": {
"id": 0,
"numero": 0
},
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "",
"sub_serie": "str",
"modelo": "",
"tributacao": "",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"ICMSTot": {
"vBC": "string",
"vICMS": "string",
"vICMSDeson": "string",
"vFCPUFDest": "string",
"vFCP": "string",
"vBCST": "string",
"vST": "string",
"vFCPST": "string",
"vFCPSTRet": "string",
"vProd": "string",
"vFrete": "string",
"vSeg": "string",
"vDesc": "string",
"vII": "string",
"vIPI": "string",
"vIPIDevol": "string",
"vPIS": "string",
"vCOFINS": "string",
"vOutro": "string",
"vNF": "string"
},
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_servicos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_bc_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"valor_original_fatura": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string",
"tem_fatura": true
}
Informa produtos inativos em um pedido de compra
'Informa produtos inativos em um pedido de compra'

Responses
200 Sucesso!

GET
/pedidos_compra/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
Pedidos Compra | Evolução de Criação
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/pedidos_compra/evolucao_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"qtd": 0,
"qtd_medio": 0,
"valor": 0,
"valor_f": "string",
"vr_medio": 0,
"vr_medio_f": "string"
}
]
Ordens de Serviço
No ERP as ordens de serviço tem o nome de Emitir Ordens de Serviço.

Listar ordens de serviço
Recupera ordens de serviço salvas no sistema.

AUTHORIZATIONS:
Authorization_Code_FlowImplicit_Flow
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

X-Totalizadores	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

Responses
200 Sucesso!

GET
/os
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24 00:00:00",
"data_entrega": "2017-01-25 00:00:00",
"data_confirmacao": "2017-01-25 00:00:00",
"departamento": {},
"cliente": {}
}
]
Criar ordem de serviço
Você pode enviar um corpo vazio para criar uma ordem de serviço sem produtos.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
status_os
required
integer
Campo identificador da atividade. É possível recuperar atividades pelo recurso /status_atividades_os, saiba como recuperar status e atividades da OS do ERP clicando aqui

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código da ordem de serviço. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Enum: "A" "B" "C"
Campo identificador do status. É possível criar a os com 3 tipos de campos [A : Em aberto|B Confirmado|C: Cancelado

data_criacao	
string
Data de criação da ordem de serviço.

data_entrega	
string
Data de entrega da ordem de serviço.

hora_entrega	
string
Hora de entrega da ordem de serviço.

data_confirmacao	
string
Data fechamento da ordem de serviço.

hora_confirmacao	
string
Hora de fechamento da ordem de serviço.

data_alteracao	
string
Data da última alteração

departamento	
integer
Campo identificador do departamento ao qual a ordem de serviço está vinculado, saiba como recuperar departamentos clicando aqui

funcionario	
integer
Campo identificador do funcionário responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual a ordem de serviço foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens da ordem de serviço.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da ordem de serviço. São as formas de pagamento usadas para pagar pela ordem de serviço.

objeto_conserto	
Array of objects (Objeto do Conserto)
Detalhes dos objetos e das condições do conserto.

atividades_os	
Array of objects (Objeto do Conserto)
Registro de atividades da ordem de serviço.

valor_desconto	
number
Valor do desconto da ordem de serviço.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre a ordem de serviço. Campo de texto livre.

Responses
201 Ordem de serviço criada!

POST
/os
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"data_alteracao": "string",
"status_os": 0,
"departamento": 0,
"funcionario": 0,
"vendedor": 0,
"cliente": 0,
"itens": [
{}
],
"faturas": [
{}
],
"objeto_conserto": [
{}
],
"atividades_os": [
{}
],
"valor_desconto": 0,
"valor_troco": 0,
"observacoes": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24 00:00:00",
"data_entrega": "2017-01-25 00:00:00",
"data_confirmacao": "2017-01-25 00:00:00",
"departamento": {
"$ref": "departamento.yaml#/example"
},
"cliente": {
"$ref": "cliente.yaml#/example"
}
}
Recuperar ordem de serviço
Recupera uma ordem de serviço detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/os/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24 00:00:00",
"data_entrega": "2017-01-25 00:00:00",
"data_confirmacao": "2017-01-25 00:00:00",
"departamento": {
"$ref": "departamento.yaml#/example"
},
"cliente": {
"$ref": "cliente.yaml#/example"
}
}
Editar ordem de serviço
Atualiza as informações da ordem de serviço.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código da ordem de serviço. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Enum: "A" "B" "C"
Campo identificador do status. É possível criar a os com 3 tipos de campos [A : Em aberto|B Confirmado|C: Cancelado

data_criacao	
string
Data de criação da ordem de serviço.

data_entrega	
string
Data de entrega da ordem de serviço.

hora_entrega	
string
Hora de entrega da ordem de serviço.

data_confirmacao	
string
Data fechamento da ordem de serviço.

hora_confirmacao	
string
Hora de fechamento da ordem de serviço.

data_alteracao	
string
Data da última alteração

status_os	
integer
Campo identificador da atividade. É possível recuperar atividades pelo recurso /status_atividades_os, saiba como recuperar status e atividades da OS do ERP clicando aqui

departamento	
integer
Campo identificador do departamento ao qual a ordem de serviço está vinculado, saiba como recuperar departamentos clicando aqui

funcionario	
integer
Campo identificador do funcionário responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual a ordem de serviço foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens da ordem de serviço.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da ordem de serviço. São as formas de pagamento usadas para pagar pela ordem de serviço.

objeto_conserto	
Array of objects (Objeto do Conserto)
Detalhes dos objetos e das condições do conserto.

atividades_os	
Array of objects (Objeto do Conserto)
Registro de atividades da ordem de serviço.

valor_desconto	
number
Valor do desconto da ordem de serviço.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre a ordem de serviço. Campo de texto livre.

Responses
200 Ordem de Serviço alterado!

PATCH
/os/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"data_alteracao": "string",
"status_os": 0,
"departamento": 0,
"funcionario": 0,
"vendedor": 0,
"cliente": 0,
"itens": [
{}
],
"faturas": [
{}
],
"objeto_conserto": [
{}
],
"atividades_os": [
{}
],
"valor_desconto": 0,
"valor_troco": 0,
"observacoes": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24 00:00:00",
"data_entrega": "2017-01-25 00:00:00",
"data_confirmacao": "2017-01-25 00:00:00",
"departamento": {
"$ref": "departamento.yaml#/example"
},
"cliente": {
"$ref": "cliente.yaml#/example"
}
}
Apagar os
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Ordem de Serviço apagado!

DELETE
/os/{id}
Gera uma venda simples através de OS
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/os/to_venda_simples/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [
"string"
],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
Gera um ajuste de estoque através de OS
PATH PARAMETERS
id
required
integer
Example: 1
QUERY PARAMETERS
tipo_ajuste	
string
Default: "C"
Enum: "C" "E" "S"
C=Compra E=Entrada S=Saída

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/os/to_ajuste_estoque/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
Gera uma NF-e através de Ordem de serviço
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/os/to_nfe/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Gera uma NFC-e através de Ordem de serviço
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/os/to_nfce/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"transportadora": {
"transportador": {}
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
Gera uma NFS-e através de Ordem de serviço
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/os/to_nfse/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/os/pdf/recibo_a4/{id}
Recibo Mini PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo Mini no formato PDF

GET
/os/pdf/recibo_mini/{id}
Atividades PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna as atividades de uma O.S no formato PDF

GET
/os/pdf/atividades/{id}
Imprimir Listagem de Ordens de serviço
'Imprimir Listagem de Ordens de serviço'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Ordens de serviços no formato PDF

POST
/os/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Imprimir etiquetas de Ordens de serviço
'Imprimir etiquetas de Ordens de serviço'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Id's das O.S que terão suas etiquetas impressas

Responses
200 Retorna arquivo de etiquetas de Ordens de serviços no formato PDF

POST
/os/pdf/etiquetas
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Mesclar Ordens de serviço
'Mesclar Ordens de serviço'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
mesclar_observacoes
required
boolean
Indica se irá mesclar as observações

agrupar
required
boolean
Indica se irá agrupar os itens iguais.

opcoes
required
integer
Default: 0
Enum: 0 1 2
Opções:

0=Além de mesclar, manter as Ordens de serviço indicadas como estão

1=Após mesclar, cancelar Ordens de serviço indicadas

2=Após mesclar, confirmar Ordens de serviço indicadas

ids
required
any
Id's das O.S que serão mescladas

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

Responses
200 Sucesso!

POST
/os/mesclar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"ids": null,
"cliente": 0,
"vendedor": 0,
"opcoes": 0,
"agrupar": true,
"mesclar_observacoes": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24 00:00:00",
"data_entrega": "2017-01-25 00:00:00",
"data_confirmacao": "2017-01-25 00:00:00",
"departamento": {},
"cliente": {}
}
]
Enviar e-mail O.S
'Enviar ordem de serviço por e-mail'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids
required
Array of integers
Ids das movimentações enviadas por email

emails	
Array of strings
Array com os e-mails para onde serão enviadas as movimentações.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

anexar_arquivos	
boolean
Default: false
Indica se os arquivos vinculados à movimentação serão anexados ao e-mail.

anexar_fotos_produtos	
boolean
Default: false
Indica se as fotos vinculadas aos produtos serão anexados ao e-mail.

Responses
200 Sucesso!

POST
/os/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"enviar_para_todos": false,
"anexar_arquivos": false,
"anexar_fotos_produtos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
OS | Status OS
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/os/status_os
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"status": "string",
"total": 0,
"valor": 0,
"valor_f": "string"
}
]
OS | Atividades OS
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/os/atividades_os
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"descricao_os": "string",
"data_os": "string",
"id_os": 0,
"numero_controle": "string"
}
]
vendas
Vendas engloba os seguintes tipos de movimentações: Venda Simples, NF-e e NFC-e.

Listar vendas
Vendas engloba os seguintes tipos de movimentações: Venda Simples, NF-e e NFC-e.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/vendas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_nfe": 0,
"id_nfce": 0,
"id_nfse": 0,
"modelo": "01",
"numero": "string",
"serie": "string",
"tipo": "E",
"cfop": "string",
"status": "0",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"cliente": {},
"funcionario": {},
"vendedor": {},
"venda_vinculada": {},
"pedido_vinculado": {},
"valor_total_nota": 0.01,
"valor_total_itens_bruto": 0.01,
"valor_total_produtos": 0.01,
"valor_total_servicos": 0,
"valor_fatura_bruto": 0.01,
"itens": [],
"faturas": []
}
]
Recuperar venda
Vendas engloba os seguintes tipos de movimentações: Venda Simples (SD), NF-e (55), NFC-e (65), NFS-e (NS), MDF-e (58), SAT (59), Nota Fiscal de Entrada (01), Ajustes de estoque (AE), NF Movimentação Manual (MM), entre outras. Para filtrar passe o parâmetro modelo com os valores separados por vírgula, ex: GET /vendas?modelo=SD,55 Trará Vendas Simples e NF-e

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/vendas/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nfe": 0,
"id_nfce": 0,
"id_nfse": 0,
"modelo": "01",
"numero": "string",
"serie": "string",
"tipo": "E",
"cfop": "string",
"status": "0",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_vinculado": {
"id": 1,
"numero": 111,
"status": "A",
"data_criacao": "2017-01-24",
"hora_criacao": "11:00:00",
"data_entrega": "2017-01-25",
"hora_entrega": "15:00:00",
"data_confirmacao": "2017-01-25",
"departamento": {},
"cliente": {}
},
"valor_total_nota": 0.01,
"valor_total_itens_bruto": 0.01,
"valor_total_produtos": 0.01,
"valor_total_servicos": 0,
"valor_fatura_bruto": 0.01,
"itens": [
{}
],
"faturas": [
{}
]
}
nfes
Listar NF-e
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

X-Totalizadores	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

Responses
200 Sucesso!

GET
/nfes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {},
"cliente": {},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {},
"consumidor_final": true,
"uso_livre_contribuinte": [],
"econf": [],
"transportadora": {},
"funcionario": {},
"itens": [],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {},
"id_nota": 0,
"venda_vinculada": {},
"pedido_os_vinculada": {},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {},
"endereco_emitente": {},
"endereco_destinatario": {},
"endereco_retirada": {},
"historico": [],
"link": "string"
}
]
Criar nfe
Ao criar uma NFE-e, se for enviado o Header X-Enviar-Nota:true, sua nota será enviada para SEFAZ. Para acompanhar a aprovação da sua nota você pode utilizar nosso webhook, e então quando a nota for aprovada, você receberá uma notificação dos nossos servidores atráves do webhook.

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Enviar-Nota	
boolean
Example: true
Indica se a nota criada ou atualizada deve ser enviada para SEFAZ.

X-Calculo-Trib-Automatico	
boolean
Example: true
Indica se a nota criada ou atualizada deve ter o calculo de tributação automatico.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
destinatario
required
integer
Campo identificador do cliente para o qual a venda foi aberta, saiba como recuperar clientes clicando aqui

itens
required
Array of objects (Item de Venda)
Itens da venda.

cfop
required
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

tipo	
string
Enum: "E" "S"
E=Entrada | S=Saida

status	
string
Enum: "0" "N" "A" "S" "2" "4"
Status das Notas Fiscais 0=Indiferente | N=Em digitação | A=Aprovada | S=Cancelada | 2=Denegada | 4=Inutilizada

serie	
integer
Serie da númeração da NF-e.

numero	
integer <= 9 characters <= 999999999
Númeração da NF-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

emitente	
object
Dados do emitente da NF-e.

cpf_cnpj_responsavel_retirada	
string
Campo para complementação das informações de identificação do estabelecimento e do endereco do local de retirada.

ie_retirada	
string
Inscrição Estadual do estabelecimento de retirada.

data_contingencia	
string <date>
Data da contingência.

hora_contingencia	
string <time>
Hora da contingência.

justificativa_contingencia	
string >= 15 characters
Justificativa da contingência.

cpf_cnpj_responsavel_entrega	
string
Campo para complementação das informações de identificação do estabelecimento e do endereco do local de entrega.

ie_entrega	
string
Inscrição Estadual do estabelecimento de entrega.

dados_entrega_nome	
string
Razão Social ou Nome do Recebedor

dados_entrega_telefone	
string
Telefone do Recebedor

data_criacao	
string <date-time>
Data de criação.

data_emissao	
string <date-time>
Data de emissão.

data_entrada_saida	
string <date>
Data Entrada/Saida.

hora_entrada_saida	
string <time>
Hora Entrada/Saida.

modalidade_frete	
string
Default: 0
Enum: "0" "1" "2" "3" "4" "9"
0 - Contratação do Frete por conta do Remetente (CIF)

1 - Contratação do Frete por conta do Destinatário (FOB)

2 - Contratação do Frete por conta de Terceiros

3 - Transporte Próprio por conta do Remetente

4 - Transporte Próprio por conta do Destinatário

9 - Sem Ocorrência de Transporte

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

notas_referenciadas	
Array of objects
finalidade_emissao	
integer
Enum: 1 2 3 4 9
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 4=Devolução de mercadoria | 9=Normal Consumidor Final

indicador_presenca	
integer
Enum: 0 1 2 3 5 9
0=Não se aplica | 1=Operação presencial; | 2=Operação não presencial, pela Internet; | 3=Operação não presencial, Teleatendimento; | 5=Operação presencial, fora do estabelecimento; | 9=Operação não presencial |

indicador_intermediador	
integer
Default: 0
Enum: 0 1
0=Operação sem intermediador | 1=Operação em site ou Plataformas de Terceiros; |

intermediador	
integer
Intermediador da transação

tipo_emissao	
integer
Enum: 1 2 3 4 5 6 7 8
Forma pela qual a NF-e está sendo emitida. 1=Normal (padrão) | 2=Contingencia FS 3=Contingencia SCAN | 4=Contingencia EPEC | 5=Contingencia FS-DA | 6=Contingencia SVC-AN | 7=Contingencia SVC-RS | 8=Contingencia SVC-SP

vendedor	
integer
Campo identificador do vendedor responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

consumidor_final	
boolean
Indica se o destinatário da NF-e é o consumidor final ou não.

uso_livre_contribuinte	
Array of objects
econf	
Array of objects
transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

valor_frete	
number
Valor do frete.

valor_seguro	
number
Valor do seguro.

valor_outras_despesas	
number
Valor de outras despesas.

valor_desconto	
number
Valor do desconto.

valor_icms	
number
Valor do ICMS.

valor_cofins_st	
number
Valor da substituicão tributária do cofins.

valor_pis_st	
number
Valor da substituicão tributária do pis.

valor_bc_icms_mono_retencao	
number
Valor do somatório do BC do ICMS Monofásico Sujeito a Retenção dos itens

valor_icms_mono_retido	
number
Valor do somatório do Valor do ICMS Monofásico Retido Anteriormente dos itens

valor_fcp	
number
Valor do Somatório do FCP dos itens

valor_fcp_st	
number
Valor do Somatório do FCP de substituição tributária dos itens

valor_fcp_st_ret	
number
Valor do Somatório do FCP de substituição tributária dos itens retidos

valor_pis_retido	
number
Valor Total do PIS retido da Nota

valor_cofins_retido	
number
Valor Total do COFINS retido da Nota

valor_csll_retido	
number
Valor Total do CSLL retido da Nota

base_calculo_irrf	
number
Base de cálculo do IRRF

valor_irrf_retido	
number
Valor Total do IRRF retido da Nota

base_calculo_previdencia_social	
number
Base de cálculo da Previdência Social

valor_previdencia_social	
number
Valor Total do Previdência Social retido da Nota

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

inf_fisco	
string
Informações Adicionais de Interesse do Fisco.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinteç.

observacoes	
string
Observações Fiscais.

numero_pedido	
string
Número do Pedido vinculado a nota

justificativa	
string >= 15 characters
Justificativa para cancelamento da nota.

pedido_os_vinculada	
integer
ID do Pedido vinculado a nota.

abater_icms_desonerado	
boolean
Flag par não abater valor de ICMS desonerado do Total da Nota

endereco_destinatario	
integer
Endereço do Destinatário. Referente ao endpoint /enderecos_entidades

endereco_entrega	
integer
Endereço de Entrega. Deixe vazio para usar o endereço padrão do destinatário. Referente ao endpoint /enderecos_entidades

endereco_emitente	
integer
Endereço do Emitente. Referente ao endpoint /enderecos_entidades

endereco_retirada	
integer
Endereço de retirada. Deixe vazio para usar o endereço padrão do emitente. Referente ao endpoint /enderecos_entidades

Responses
201 NFE-e criada!
202 NFE-e criada e enviada para SEFAZ!

POST
/nfes
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": 0,
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": 0,
"tipo_emissao": 1,
"vendedor": 0,
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": 0,
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"gera_credito": true,
"valor_servico": 0,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_icms": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"justificativa": "stringstringstr",
"pedido_os_vinculada": 0,
"abater_icms_desonerado": true,
"endereco_destinatario": 0,
"endereco_entrega": 0,
"endereco_emitente": 0,
"endereco_retirada": 0
}
Response samples
201202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Recuperar NF-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/nfes/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Editar nfe
Atualiza as informações da nfe.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Enviar-Nota	
boolean
Example: true
Indica se a nota criada ou atualizada deve ser enviada para SEFAZ.

X-Calculo-Trib-Automatico	
boolean
Example: true
Indica se a nota criada ou atualizada deve ter o calculo de tributação automatico.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
tipo	
string
Enum: "E" "S"
E=Entrada | S=Saida

status	
string
Enum: "0" "N" "A" "S" "2" "4"
Status das Notas Fiscais 0=Indiferente | N=Em digitação | A=Aprovada | S=Cancelada | 2=Denegada | 4=Inutilizada

serie	
integer
Serie da númeração da NF-e.

numero	
integer <= 9 characters <= 999999999
Númeração da NF-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

emitente	
object
Dados do emitente da NF-e.

cpf_cnpj_responsavel_retirada	
string
Campo para complementação das informações de identificação do estabelecimento e do endereco do local de retirada.

ie_retirada	
string
Inscrição Estadual do estabelecimento de retirada.

data_contingencia	
string <date>
Data da contingência.

hora_contingencia	
string <time>
Hora da contingência.

justificativa_contingencia	
string >= 15 characters
Justificativa da contingência.

destinatario	
integer
Campo identificador do cliente para o qual a venda foi aberta, saiba como recuperar clientes clicando aqui

cpf_cnpj_responsavel_entrega	
string
Campo para complementação das informações de identificação do estabelecimento e do endereco do local de entrega.

ie_entrega	
string
Inscrição Estadual do estabelecimento de entrega.

dados_entrega_nome	
string
Razão Social ou Nome do Recebedor

dados_entrega_telefone	
string
Telefone do Recebedor

data_criacao	
string <date-time>
Data de criação.

data_emissao	
string <date-time>
Data de emissão.

data_entrada_saida	
string <date>
Data Entrada/Saida.

hora_entrada_saida	
string <time>
Hora Entrada/Saida.

modalidade_frete	
string
Default: 0
Enum: "0" "1" "2" "3" "4" "9"
0 - Contratação do Frete por conta do Remetente (CIF)

1 - Contratação do Frete por conta do Destinatário (FOB)

2 - Contratação do Frete por conta de Terceiros

3 - Transporte Próprio por conta do Remetente

4 - Transporte Próprio por conta do Destinatário

9 - Sem Ocorrência de Transporte

cfop	
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

notas_referenciadas	
Array of objects
finalidade_emissao	
integer
Enum: 1 2 3 4 9
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 4=Devolução de mercadoria | 9=Normal Consumidor Final

indicador_presenca	
integer
Enum: 0 1 2 3 5 9
0=Não se aplica | 1=Operação presencial; | 2=Operação não presencial, pela Internet; | 3=Operação não presencial, Teleatendimento; | 5=Operação presencial, fora do estabelecimento; | 9=Operação não presencial |

indicador_intermediador	
integer
Default: 0
Enum: 0 1
0=Operação sem intermediador | 1=Operação em site ou Plataformas de Terceiros; |

intermediador	
integer
Intermediador da transação

tipo_emissao	
integer
Enum: 1 2 3 4 5 6 7 8
Forma pela qual a NF-e está sendo emitida. 1=Normal (padrão) | 2=Contingencia FS 3=Contingencia SCAN | 4=Contingencia EPEC | 5=Contingencia FS-DA | 6=Contingencia SVC-AN | 7=Contingencia SVC-RS | 8=Contingencia SVC-SP

vendedor	
integer
Campo identificador do vendedor responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

consumidor_final	
boolean
Indica se o destinatário da NF-e é o consumidor final ou não.

uso_livre_contribuinte	
Array of objects
econf	
Array of objects
transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

itens	
Array of objects (Item de Venda)
Itens da venda.

valor_frete	
number
Valor do frete.

valor_seguro	
number
Valor do seguro.

valor_outras_despesas	
number
Valor de outras despesas.

valor_desconto	
number
Valor do desconto.

valor_icms	
number
Valor do ICMS.

valor_cofins_st	
number
Valor da substituicão tributária do cofins.

valor_pis_st	
number
Valor da substituicão tributária do pis.

valor_bc_icms_mono_retencao	
number
Valor do somatório do BC do ICMS Monofásico Sujeito a Retenção dos itens

valor_icms_mono_retido	
number
Valor do somatório do Valor do ICMS Monofásico Retido Anteriormente dos itens

valor_fcp	
number
Valor do Somatório do FCP dos itens

valor_fcp_st	
number
Valor do Somatório do FCP de substituição tributária dos itens

valor_fcp_st_ret	
number
Valor do Somatório do FCP de substituição tributária dos itens retidos

valor_pis_retido	
number
Valor Total do PIS retido da Nota

valor_cofins_retido	
number
Valor Total do COFINS retido da Nota

valor_csll_retido	
number
Valor Total do CSLL retido da Nota

base_calculo_irrf	
number
Base de cálculo do IRRF

valor_irrf_retido	
number
Valor Total do IRRF retido da Nota

base_calculo_previdencia_social	
number
Base de cálculo da Previdência Social

valor_previdencia_social	
number
Valor Total do Previdência Social retido da Nota

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

inf_fisco	
string
Informações Adicionais de Interesse do Fisco.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinteç.

observacoes	
string
Observações Fiscais.

numero_pedido	
string
Número do Pedido vinculado a nota

justificativa	
string >= 15 characters
Justificativa para cancelamento da nota.

pedido_os_vinculada	
integer
ID do Pedido vinculado a nota.

abater_icms_desonerado	
boolean
Flag par não abater valor de ICMS desonerado do Total da Nota

endereco_destinatario	
integer
Endereço do Destinatário. Referente ao endpoint /enderecos_entidades

endereco_entrega	
integer
Endereço de Entrega. Deixe vazio para usar o endereço padrão do destinatário. Referente ao endpoint /enderecos_entidades

endereco_emitente	
integer
Endereço do Emitente. Referente ao endpoint /enderecos_entidades

endereco_retirada	
integer
Endereço de retirada. Deixe vazio para usar o endereço padrão do emitente. Referente ao endpoint /enderecos_entidades

Responses
200 NFE-e atualizada!
202 NFE-e atualizada e enviada para SEFAZ!

PATCH
/nfes/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": 0,
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": 0,
"tipo_emissao": 1,
"vendedor": 0,
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": 0,
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"gera_credito": true,
"valor_servico": 0,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_icms": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"justificativa": "stringstringstr",
"pedido_os_vinculada": 0,
"abater_icms_desonerado": true,
"endereco_destinatario": 0,
"endereco_entrega": 0,
"endereco_emitente": 0,
"endereco_retirada": 0
}
Response samples
200202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Apagar nfe
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Nfe apagada!

DELETE
/nfes/{id}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/nfes/pdf/recibo_a4/{id}
Imprimir Listagem de Nfes
'Imprimir Listagem de Nfes'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de NFE no formato PDF

POST
/nfes/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Imprimir Listagem de Nfes usando o modelo simplificado
'Imprimir Danfe Simplificada'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de NFE no formato PDF simplificado

POST
/nfes/danfe_simplificada/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Xml da NF-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a Nf-e em formato XML

GET
/nfes/gerar_link_xml/{id}
Envia NF-e por Email
'Envia NF-e por Email'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Ids das notas enviadas por email

emails	
Array of strings
Emails para os quais a nota será enviada

protocolo_aprovacao	
string
Protocolo de aprovação da NF-e

contador	
boolean
Indicador se o email deve ser enviado ao contador

envia_email_forcado	
boolean
Clientes têm a opção de não receber e-mails automáticos. Essa flag indica se o email é manual ou não. Se for indicada e o cliente não receber e-mail automático, ele vai receber esse e-mail. Se não for indicado, ele não vai receber.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

Responses
200 Sucesso!

POST
/nfes/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"protocolo_aprovacao": "string",
"contador": true,
"envia_email_forcado": true,
"enviar_para_todos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Inutilizar uma NF-e
'Inutilizar uma NF-e'

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
justificativa
required
string >= 15 characters
Justificativa para inutilização da nota.

Responses
200 NF-e foi enviada para inutilização com sucesso!

PATCH
/nfes/inutilizar/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"justificativa": "stringstringstr"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"item": {
"justificativa": "string"
},
"message": "string"
}
Cancelar NF-e
'Manda a NF-e para o SEFAZ para cancelamento'

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
justificativa
required
string >= 15 characters
Justificativa para cancelamento da nota.

Responses
200 A NFE Foi enviada para cancelamento.

PATCH
/nfes/cancelar/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"justificativa": "stringstringstr"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"item": {
"justificativa": "string"
},
"message": "string"
}
Inutiliza Nfes em massa
'Inutiliza Nfes em massa'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
num_inicio	
integer
Número da primeira nota a ser inutilizada.

num_fim	
integer
Número da última nota a ser inutilizada.

serie	
integer
Serie das NF-es que serão inutilizadas.

justificativa	
string >= 15 characters
Justificativa para inutilização das NF-es.

Responses
200 NF-es inutilizadas com sucesso!

PATCH
/nfes/inutilizar_varias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"num_inicio": 0,
"num_fim": 0,
"serie": 0,
"justificativa": "stringstringstr"
}
Gera CC-e
'Gera pedido de CCe'

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao_correcao	
string >= 15 characters
Texto de correção para CC-e (Carta de Correção Eletrônica)

Responses
201 CC-e criada com sucesso!

POST
/nfes/gerar_cce/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao_correcao": "stringstringstr"
}
PDF da CC-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a CC-e (Carta de Correção Eletrônica) em A4 no formato PDF

GET
/nfes/pdf/cce/{id}
Xml da CC-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a CC-e em formato XML

GET
/nfes/gerar_xml_cce/{id}
Envia solicitação a Sefaz para download do XML.
PATH PARAMETERS
id
required
integer
Example: 1
Responses
201 Pedido de xml enviado com sucesso a SEFAZ.

POST
/nfes/gerar_xml_sefaz/{id}
Gerar Xml de NF-e sem assinatura
PATH PARAMETERS
id
required
integer
Example: 1
QUERY PARAMETERS
cancelada	
boolean
aprovada	
boolean
inutilizada	
boolean
Responses
200 Retorna a NF-e em formato XML sem assinatura

GET
/nfes/gerar_xml_sem_assinatura/{id}
Usado para vincular um transporte a uma nota já aprovada.
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
modalidade_frete
required
string
Enum: "0" "1" "2" "9"
0=Emitente | 1=Destinátario | 2=Terceiros | 9=Sem Frete

transportador
required
string
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

numero_nota
required
string
data_emissao
required
string
data_prestacao
required
string
total_nota
required
string
cfop
required
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

valor_servico
required
string
base_calculo_icms_ret
required
string
aliquota_icms_ret
required
string
valor_icms_ret
required
string
municipio_gerador
required
string
Código do município

serie	
integer
Serie da númeração da NF-e.

modelo	
string
Enum: "57" "07" "08" "09" "10" "11"
cst_b	
string
chave_cte	
string
desconto	
number
sub_serie	
string
observacoes	
string
Responses
200 Sucesso!

PATCH
/nfes/transporte_vinculado/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"modalidade_frete": "0",
"transportador": "string",
"numero_nota": "string",
"serie": 0,
"modelo": "57",
"cst_b": "string",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": "string",
"sub_serie": "string",
"cfop": "string",
"valor_servico": "string",
"base_calculo_icms_ret": "string",
"aliquota_icms_ret": "string",
"valor_icms_ret": "string",
"municipio_gerador": "string",
"observacoes": "string"
}
Retorna o transporte vinculado a uma NF-e.
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/nfes/transporte_vinculado/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"modalidade_frete": "0",
"transportador": "string",
"numero_nota": "string",
"serie": 0,
"modelo": "57",
"cst_b": "string",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": "string",
"sub_serie": "string",
"cfop": "string",
"valor_servico": "string",
"base_calculo_icms_ret": "string",
"aliquota_icms_ret": "string",
"valor_icms_ret": "string",
"municipio_gerador": "string",
"observacoes": "string"
}
Carrega Tributação de uma NFE
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects
id_destinatario
required
integer
Campo identificador do cliente/fornecedor para o qual a nota foi vinculada.

cfop_nota
required
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

somar_ipi_icms_st	
boolean
somar_ipi_icms	
boolean
Responses
200 Sucesso!

POST
/nfes/carregar_tributacao
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_destinatario": 0,
"cfop_nota": "string",
"somar_ipi_icms_st": true,
"somar_ipi_icms": true,
"itens": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados_item": {},
"icms_simples_nacional": {},
"icms": {},
"icms_efetivo": {},
"fcp": {},
"ipi": {},
"ii": {},
"pis": {},
"pis_st": {},
"cofins": {},
"cofins_st": {},
"combustivel": {},
"outros": {},
"icms_op_interestaduais": {}
}
]
Informa produtos inativos em uma nota fiscal eletrônica
'Informa produtos inativos em uma nota fiscal eletrônica'

Responses
200 Sucesso!

GET
/nfes/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
Gera ECONF (Evento de Conciliação Financeira)
'Gera ECONF'

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Enviar-Econf	
boolean
Example: true
Indica se o arquivo Econf criado ou atualizado deve ser enviada para SEFAZ.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
faturas	
Array of objects
Responses
201 ECONF criado com sucesso!

POST
/nfes/econf/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"faturas": [
{}
]
}
Atualiza ECONF (Evento de Conciliação Financeira)
'Atualiza ECONF'

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Enviar-Econf	
boolean
Example: true
Indica se o arquivo Econf criado ou atualizado deve ser enviada para SEFAZ.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
faturas	
Array of objects
Responses
200 ECONF atualizado com sucesso!
202 ECONF atualizado e enviado com sucesso!

PATCH
/nfes/econf/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"faturas": [
{}
]
}
Xml do ECONF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o xml do ECONF

GET
/nfes/gerar_xml_econf/{id}
Gera pedido de cancelamento do ECONF (Evento de Conciliação Financeira)
'Cancela ECONF'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id_econf
required
string
Responses
200 ECONF foi enviada para cancelamento.!

PATCH
/nfes/cancelar_econf/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id_econf": "string"
}
Informa produtos inativos em uma nota fiscal eletrônica
'Informa produtos inativos em uma nota fiscal eletrônica'

Responses
200 Sucesso!

GET
/ajustes_estoque/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
nfces
Listar NFC-e
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

X-Totalizadores	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

Responses
200 Sucesso!

GET
/nfces
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {},
"funcionario": {},
"vendedor": {},
"transportadora": {},
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
]
Criar nfce
Ao criar uma NFC-e, se for enviado o Header X-Enviar-Nota:true, sua nota será enviada para SEFAZ. Para acompanhar a aprovação da sua nota você pode utilizar nosso webhook, e então quando a nota for aprovada, você receberá uma notificação dos nossos servidores atráves do webhook.

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Enviar-Nota	
boolean
Example: true
Indica se a nota criada ou atualizada deve ser enviada para SEFAZ.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects (Item de Venda)
Itens da venda.

cfop
required
string
Código Fiscal de Operações e Prestações da NFC-e. Máscara 9.999

status	
string
Enum: "0" "N" "A" "S" "2" "4"
Status das Notas Fiscais 0=Indiferente | N=Em digitação | A=Aprovada | S=Cancelada | 2=Denegada | 4=Inutilizada

rejeitada	
integer
Enum: 0 1
Campo para indicar se a nota já foi rejeitada. 0=Não foi rejeitada| 1=Foi rejeitada

serie	
integer
Serie da númeração da NFC-e.

numero	
integer
Númeração da NFC-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

data_criacao	
string <date-time>
Data de criação.

data_emissao	
string <date-time>
Data de emissão.

pedido_os_vinculada	
integer
ID do Pedido vinculado a nota.

indicador_presenca	
integer
Default: 1
Enum: 0 1 2 4 9
0=Não se aplica | 1=Operação presencial; | 2=Operação não presencial, pela Internet; | 3=Operação não presencial, Teleatendimento; | 4=NFC-e em operação com entrega em domicílio; | 9=Operação não presencial |

indicador_intermediador	
integer
Default: 0
Enum: 0 1
0=Operação sem intermediador | 1=Operação em site ou Plataformas de Terceiros; |

intermediador	
integer
Intermediador da transação

modalidade_frete	
string
Default: 0
Enum: "0" "1" "2" "3" "4" "9"
0 - Contratação do Frete por conta do Remetente (CIF)

1 - Contratação do Frete por conta do Destinatário (FOB)

2 - Contratação do Frete por conta de Terceiros

3 - Transporte Próprio por conta do Remetente

4 - Transporte Próprio por conta do Destinatário

9 - Sem Ocorrência de Transporte

indicador_forma_pagamento	
integer
Default: 0
Enum: 0 1 2
0=À vista | 1=A prazo | 2=Outros

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

cliente	
integer
Campo identificador do cliente para o qual a venda foi aberta, saiba como recuperar clientes clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

valor_frete	
number
Valor do frete.

valor_desconto	
number
Valor do desconto.

valor_produtos	
number
Valor dos produtos.

valor_bc_icms	
number
Valor da Base de Cálculo do ICMS.

valor_icms	
number
Valor do ICMS.

valor_pis	
number
Valor Total do PIS da Nota.

valor_cofins	
number
Valor Total do COFINS da Nota

valor_pago	
number
Valor pago

valor_troco	
number
Valor do troco da Nota

observacoes	
string
Observações Fiscais.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinteç.

data_contingencia	
string
Data da contingência.

hora_contingencia	
string
Hora da contingência.

justificativa_contingencia	
string
Justificativa da contingência.

abater_icms_desonerado	
boolean
possui_xml_banco	
boolean
possui_xml_s3	
boolean
Responses
201 NFC-e criada!
202 NFC-e criada e enviada para SEFAZ!

POST
/nfces
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "0",
"rejeitada": 0,
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": 0,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": 0,
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"cliente": 0,
"vendedor": 0,
"transportadora": {
"transportador": 0
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"possui_xml_banco": true,
"possui_xml_s3": true
}
Response samples
201202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"transportadora": {
"transportador": {}
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
Recuperar NFC-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/nfces/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"transportadora": {
"transportador": {}
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
Editar nfce
Atualiza as informações da nfce.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Enviar-Nota	
boolean
Example: true
Indica se a nota criada ou atualizada deve ser enviada para SEFAZ.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
status	
string
Enum: "0" "N" "A" "S" "2" "4"
Status das Notas Fiscais 0=Indiferente | N=Em digitação | A=Aprovada | S=Cancelada | 2=Denegada | 4=Inutilizada

rejeitada	
integer
Enum: 0 1
Campo para indicar se a nota já foi rejeitada. 0=Não foi rejeitada| 1=Foi rejeitada

serie	
integer
Serie da númeração da NFC-e.

numero	
integer
Númeração da NFC-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

data_criacao	
string <date-time>
Data de criação.

data_emissao	
string <date-time>
Data de emissão.

pedido_os_vinculada	
integer
ID do Pedido vinculado a nota.

indicador_presenca	
integer
Default: 1
Enum: 0 1 2 4 9
0=Não se aplica | 1=Operação presencial; | 2=Operação não presencial, pela Internet; | 3=Operação não presencial, Teleatendimento; | 4=NFC-e em operação com entrega em domicílio; | 9=Operação não presencial |

indicador_intermediador	
integer
Default: 0
Enum: 0 1
0=Operação sem intermediador | 1=Operação em site ou Plataformas de Terceiros; |

intermediador	
integer
Intermediador da transação

cfop	
string
Código Fiscal de Operações e Prestações da NFC-e. Máscara 9.999

modalidade_frete	
string
Default: 0
Enum: "0" "1" "2" "3" "4" "9"
0 - Contratação do Frete por conta do Remetente (CIF)

1 - Contratação do Frete por conta do Destinatário (FOB)

2 - Contratação do Frete por conta de Terceiros

3 - Transporte Próprio por conta do Remetente

4 - Transporte Próprio por conta do Destinatário

9 - Sem Ocorrência de Transporte

indicador_forma_pagamento	
integer
Default: 0
Enum: 0 1 2
0=À vista | 1=A prazo | 2=Outros

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

cliente	
integer
Campo identificador do cliente para o qual a venda foi aberta, saiba como recuperar clientes clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

itens	
Array of objects (Item de Venda)
Itens da venda.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

valor_frete	
number
Valor do frete.

valor_desconto	
number
Valor do desconto.

valor_produtos	
number
Valor dos produtos.

valor_bc_icms	
number
Valor da Base de Cálculo do ICMS.

valor_icms	
number
Valor do ICMS.

valor_pis	
number
Valor Total do PIS da Nota.

valor_cofins	
number
Valor Total do COFINS da Nota

valor_pago	
number
Valor pago

valor_troco	
number
Valor do troco da Nota

observacoes	
string
Observações Fiscais.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinteç.

data_contingencia	
string
Data da contingência.

hora_contingencia	
string
Hora da contingência.

justificativa_contingencia	
string
Justificativa da contingência.

abater_icms_desonerado	
boolean
possui_xml_banco	
boolean
possui_xml_s3	
boolean
Responses
200 NFC-e atualizada!
202 NFC-e atualizada e enviada para SEFAZ!

PATCH
/nfces/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "0",
"rejeitada": 0,
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": 0,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": 0,
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"cliente": 0,
"vendedor": 0,
"transportadora": {
"transportador": 0
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"possui_xml_banco": true,
"possui_xml_s3": true
}
Response samples
200202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"transportadora": {
"transportador": {}
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
Apagar nfce
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Nfce apagada!

DELETE
/nfces/{id}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/nfces/pdf/recibo_a4/{id}
Recibo Mini PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo Mini no formato PDF

GET
/nfces/pdf/recibo_mini/{id}
Recibo Cupom Troca PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Cupom de Troca no formato PDF

GET
/nfces/pdf/cupom_troca/{id}
Imprimir Listagem de Nfces
'Imprimir Listagem de Nfces'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de NFCE no formato PDF

POST
/nfces/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Envia NFC-e por Email
'Envia NFC-e por Email'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Ids das notas enviadas por email

emails	
Array of strings
Emails para os quais a nota será enviada

protocolo_aprovacao	
string
Protocolo de aprovação da NFC-e

envia_email_forcado	
boolean
Clientes têm a opção de não receber e-mails automáticos. Essa flag indica se o email é manual ou não. Se for indicada e o cliente não receber e-mail automático, ele vai receber esse e-mail. Se não for indicado, ele não vai receber.

contador	
boolean
Indicador se o email deve ser enviado ao contador

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

Responses
200 Sucesso!

POST
/nfces/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"protocolo_aprovacao": "string",
"envia_email_forcado": true,
"contador": true,
"enviar_para_todos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
inutilizar Nfce
'inutilizar Nfce'

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
justificativa	
string >= 15 characters
Justificativa para inutilização da NFC-e.

Responses
200 NFC-e inutilizada com sucesso!

PATCH
/nfces/inutilizar/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"justificativa": "stringstringstr"
}
inutilizar varias Nfces
'inutilizar varias Nfces'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
num_inicio
required
integer
Número da primeira nota a ser inutilizada.

num_fim
required
integer
Número da última nota a ser inutilizada.

serie
required
integer
Serie das NFC-es que serão inutilizadas.

justificativa
required
string >= 15 characters
Justificativa para inutilização das NFC-es.

Responses
200 NFC-es inutilizadas com sucesso!

PATCH
/nfces/inutilizar_varias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"num_inicio": 0,
"num_fim": 0,
"serie": 0,
"justificativa": "stringstringstr"
}
Cancelar NFC-e
'Envia pedido de cancelamento da NFC-e para a SEFAZ'

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
cancelamento_substituicao
required
boolean
Informar se será um cancelamento por substituição.

justificativa
required
string >= 15 characters
Justificativa para cancelamento da nota.

id_nfce_vinculada	
integer
Id da NFC-e vinculada (Campo obrigatório quando é feito cancelamento por substituição)

chave_nfce_vinculada	
string
Chave da NFC-e vinculada (Campo obrigatório quando é feito cancelamento por substituição)

Responses
200 A NFC-e foi enviada para cancelamento.

PATCH
/nfces/cancelar/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"cancelamento_substituicao": true,
"justificativa": "stringstringstr",
"id_nfce_vinculada": 0,
"chave_nfce_vinculada": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"item": {
"cancelamento_substituicao": true,
"id_nfce_vinculada": 0,
"chave_nfce_vinculada": "string",
"justificativa": "string"
},
"message": "string"
}
Envia solicitação a Sefaz para download do XML.
PATH PARAMETERS
id
required
integer
Example: 1
Responses
201 Pedido de xml enviado com sucesso a SEFAZ.

POST
/nfces/gerar_xml_sefaz/{id}
Gerar Xml de NFC-e sem assinatura
PATH PARAMETERS
id
required
integer
Example: 1
QUERY PARAMETERS
cancelada	
boolean
Retorna o XML de cancelamento.

aprovada	
boolean
Retorna o XML de aprovação.

inutilizada	
boolean
Retorna o XML de inutilização.

restante	
boolean
Retorna todos os xmls disponiveis para a NFC-e.

Responses
200 Retorna a NFC-e em formato XML sem assinatura

GET
/nfces/gerar_xml_sem_assinatura/{id}
Xml da NFC-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a NFC-e em formato XML

GET
/nfces/gerar_link_xml/{id}
Listagem Nfces em Estado Crítico
Responses
200 Sucesso!

GET
/nfces/estado_critico
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"numero_nota": 0,
"serie_nota": 0,
"data": "2019-08-24",
"hora": "14:15:22Z",
"acao_necessaria": "string",
"aprovada": true,
"cancelada": true,
"inutilizada": true
}
]
Listagem Nfces em Estado Crítico
Responses
200 Sucesso!

POST
/nfces/estado_critico/resolver
Exportar NFC-es
Exportar NFC-es

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
data_inicial
required
string
Data Inicial

data_final
required
string
Data Final

tipo_exportacao
required
string
Enum: "D" "E"
D=Realizar Download. | E=Enviar por e-mail

id_nfce	
integer
Gera exportação de NFCe especifico

configuracao	
string
Enum: "" "1" "2"
1=Agrupar DANFE e XML por pasta. | 2=Gerar todas as DANFEs em um único arquivo

gerar_xml	
boolean
Gerar Xml das NFCe- a exportar

gerar_danfe	
boolean
Gerar Danfe das NFCe- a exportar

data_considerada	
string
Enum: "1" "2" "3"
Indica a data a ser considerada para geração do(s) Xml(s)/Danfe(s): 1 - Criação | 2 - Aprovação | 3 - Emissão |

data_periodo	
string
Default: ""
Enum: "" "1" "2" "3" "4"
O periodo considerado. É obrigatorio caso não passe a data inicial e final. 1 - Periodo do Mês Atual

2 - Periodo do Mês Passado

3 - Periodo da semana atual

4 - Periodo da semana passada

5 - Periodo dos ultimos sete dias

6 - Periodo dos ultimos trinta dias

email	
string
Email para onde a nota exportada será enviada (**Campo Obrigatório caso o tipo_exportação seja E)

status_nota	
string
Enum: "" "A" "S" "4" "2"
Indica a situação da nota **** - Qualquer | A - Confirmado | S - Cancelado | 4 - Inutilizadas | 2 - Denegadas

Responses
200 Sucesso!

POST
/nfces/exportar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id_nfce": 0,
"configuracao": "",
"gerar_xml": true,
"gerar_danfe": true,
"data_considerada": "1",
"data_inicial": "string",
"data_final": "string",
"data_periodo": "",
"tipo_exportacao": "D",
"email": "string",
"status_nota": ""
}
Informa produtos inativos em uma nota fiscal de consumidor eletrônica
'Informa produtos inativos em uma nota fiscal de consumidor eletrônica'

Responses
200 Sucesso!

GET
/nfces/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
Carrega Tributação de uma NFCE
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects
cfop_nota
required
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

id_cliente	
integer
Campo identificador do cliente para o qual a nota foi vinculada.

somar_ipi_icms_st	
boolean
somar_ipi_icms	
boolean
Responses
200 Sucesso!

POST
/nfces/carregar_tributacao
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_cliente": 0,
"cfop_nota": "string",
"somar_ipi_icms_st": true,
"somar_ipi_icms": true,
"itens": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados_item": {},
"icms_simples_nacional": {},
"icms": {},
"desoneracao": {},
"fcp": {},
"pis": {},
"cofins": {},
"combustivel": {}
}
]
nfses
Listar NFS-e
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/nfses
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": []
}
]
Criar nfse
Ao criar uma NFS-e, se for enviado o Header X-Enviar-Nota:true, sua nota será enviada para a SEFAZ. Para acompanhar a aprovação da sua nota você pode utilizar nosso webhook, e então quando a nota for aprovada, você receberá uma notificação dos nossos servidores atráves do webhook.

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Enviar-Nota	
boolean
Example: true
Indica se a nota criada ou atualizada deve ser enviada para SEFAZ.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects (Item de Venda)
Itens da venda.

id_tecnospeed	
string
status	
string
Enum: "0" "N" "A" "S" "2" "4"
Status das Notas Fiscais 0=Indiferente | N=Em digitação | A=Aprovada | S=Cancelada | 2=Denegada | 4=Inutilizada

rejeitada	
integer
Enum: 0 1
Campo para indicar se a nota já foi rejeitada. 0=Não foi rejeitada| 1=Foi rejeitada

serie_rps	
integer
Serie da RPS da NFS-e.

numero_rps	
integer
Númeração da RPS da NFS-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

pedido_orcamento	
integer
Id do pedido, orçamento ou ordem de serviço vinculado a NFS-e. (DEPRECATED: 2024, usar pedido_os_vinculada)

pedido_os_vinculada	
integer
ID do Pedido vinculado a nota.

serie_nfse	
string
Serie da NFS-e.

numero_nfse	
integer
Númeração da NFS-e.

data_aprovacao	
string <date-time>
Data de aprovação.

data_emissao	
string <date-time>
Data de emissão.

cliente	
integer
Campo identificador do cliente para o qual a venda foi aberta, saiba como recuperar clientes clicando aqui

funcionario	
integer
Campo identificador do funcionário responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

data_criacao	
string <date-time>
Data de criação.

observacoes	
string
Observações Fiscais.

municipio_tributacao	
integer
Código IBGE do município onde o serviço foi tributado.

municipio_prestacao	
integer
Código IBGE do município onde o serviço foi prestado.

natureza_operacao	
integer
Enum: 1 2 3 4 5 6
1=Tributação no município 2=Tributação fora do município 3=Isenção 4=Imunidade 5=Exigibilidade suspensa por decisão judicial 6=Exigibilidade suspensa por procedimento administrativo

natureza_tributacao	
integer
Enum: 1 2 3 4 5 6
1=Simples Nacional | 2=Fixo | 3=Depósito em Juizo | 4=Exigibilidade suspensa por decisão judicial | 5=Exigibilidade suspensa por procedimento administrativo | 6=Isenção Parcial

tipo_tributacao	
integer
Default: 6
Enum: 1 2 3 4 5 6 7 8
1=Isenta de ISS | 2=Imune | 3=Não Incidência no Município | 4=Não Tributável | 5=Retida | 6=Tributação no Município | 7=Tributação fora do Município | 8=Tributável dentro do Município pelo Tomador

intermediario_razao_social	
string
Razão social do intermediário.

intermediario_im	
string
Inscrição Municipal do intermediário.

intermediario_cnpj	
string
CNPJ do intermediário.

numero_art	
string
Número da ART.

codigo_obra	
string
Código da obra relativo a construção civil.

descricao_servico	
string
Descrição dos serviços prestados.

codigo_tabela_servico	
string
Código do serviço na tabela de serviços do ERP. No ERP acesse: Menu > Tabela de Serviços.

id_tabela_servico	
integer
Id da tabela de serviço

cst_pis	
string
CST PIS utilizado para operações.

cst_cofins	
string
CST COFINS utilizado para operações.

valor_servico	
number
Valor total dos serviços prestados.

aliquota_iss	
number
Percentual de ISS.

valor_deducoes	
number
Valor das deduções.

valor_iss	
number
Valor do ISS.

valor_liquido	
number
Valor liquido da nota.

valor_iss_retido	
number
Valor do ISS Retido.

valor_pis_retido	
number
Valor do PIS Retido.

valor_cofins_retido	
number
Valor do COFINS Retido.

valor_inss_retido	
number
Valor do INSS Retido.

valor_ir_retido	
number
Valor do IR Retido.

valor_csll_retido	
number
Valor do CSLL Retido.

valor_outras_retencoes	
number
responsavel_retencao	
integer
Enum: 0 1 2
0=Não informado 1=Tomador 2=Intermediario

valor_bc_pis	
number
Base de cálculo do PIS.

aliquota_pis	
number
Percentual de PIS.

valor_pis	
number
Valor do PIS.

valor_bc_cofins	
number
Base de cálculo do COFINS.

aliquota_cofins	
number
Percentual de COFINS.

valor_cofins	
number
Valor do COFINS.

xml	
string
XML da nota.

valor_total_servicos	
number
Valor do serviço da nota.

valor_original_fatura	
number
Valor bruto da Fatura vinculada a Nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

Responses
201 NFS-e criada!
202 NFS-e criada e enviada para SEFAZ!

POST
/nfses
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Response samples
201202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Recuperar NFS-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/nfses/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Apagar nfse
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Nfse apagada!

DELETE
/nfses/{id}
Editar nfse
Atualiza as informações da nfse.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Enviar-Nota	
boolean
Example: true
Indica se a nota criada ou atualizada deve ser enviada para SEFAZ.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id_tecnospeed	
string
status	
string
Enum: "0" "N" "A" "S" "2" "4"
Status das Notas Fiscais 0=Indiferente | N=Em digitação | A=Aprovada | S=Cancelada | 2=Denegada | 4=Inutilizada

rejeitada	
integer
Enum: 0 1
Campo para indicar se a nota já foi rejeitada. 0=Não foi rejeitada| 1=Foi rejeitada

serie_rps	
integer
Serie da RPS da NFS-e.

numero_rps	
integer
Númeração da RPS da NFS-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

pedido_orcamento	
integer
Id do pedido, orçamento ou ordem de serviço vinculado a NFS-e. (DEPRECATED: 2024, usar pedido_os_vinculada)

pedido_os_vinculada	
integer
ID do Pedido vinculado a nota.

serie_nfse	
string
Serie da NFS-e.

numero_nfse	
integer
Númeração da NFS-e.

data_aprovacao	
string <date-time>
Data de aprovação.

data_emissao	
string <date-time>
Data de emissão.

cliente	
integer
Campo identificador do cliente para o qual a venda foi aberta, saiba como recuperar clientes clicando aqui

funcionario	
integer
Campo identificador do funcionário responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

data_criacao	
string <date-time>
Data de criação.

observacoes	
string
Observações Fiscais.

municipio_tributacao	
integer
Código IBGE do município onde o serviço foi tributado.

municipio_prestacao	
integer
Código IBGE do município onde o serviço foi prestado.

natureza_operacao	
integer
Enum: 1 2 3 4 5 6
1=Tributação no município 2=Tributação fora do município 3=Isenção 4=Imunidade 5=Exigibilidade suspensa por decisão judicial 6=Exigibilidade suspensa por procedimento administrativo

natureza_tributacao	
integer
Enum: 1 2 3 4 5 6
1=Simples Nacional | 2=Fixo | 3=Depósito em Juizo | 4=Exigibilidade suspensa por decisão judicial | 5=Exigibilidade suspensa por procedimento administrativo | 6=Isenção Parcial

tipo_tributacao	
integer
Default: 6
Enum: 1 2 3 4 5 6 7 8
1=Isenta de ISS | 2=Imune | 3=Não Incidência no Município | 4=Não Tributável | 5=Retida | 6=Tributação no Município | 7=Tributação fora do Município | 8=Tributável dentro do Município pelo Tomador

intermediario_razao_social	
string
Razão social do intermediário.

intermediario_im	
string
Inscrição Municipal do intermediário.

intermediario_cnpj	
string
CNPJ do intermediário.

numero_art	
string
Número da ART.

codigo_obra	
string
Código da obra relativo a construção civil.

descricao_servico	
string
Descrição dos serviços prestados.

codigo_tabela_servico	
string
Código do serviço na tabela de serviços do ERP. No ERP acesse: Menu > Tabela de Serviços.

id_tabela_servico	
integer
Id da tabela de serviço

cst_pis	
string
CST PIS utilizado para operações.

cst_cofins	
string
CST COFINS utilizado para operações.

itens	
Array of objects (Item de Venda)
Itens da venda.

valor_servico	
number
Valor total dos serviços prestados.

aliquota_iss	
number
Percentual de ISS.

valor_deducoes	
number
Valor das deduções.

valor_iss	
number
Valor do ISS.

valor_liquido	
number
Valor liquido da nota.

valor_iss_retido	
number
Valor do ISS Retido.

valor_pis_retido	
number
Valor do PIS Retido.

valor_cofins_retido	
number
Valor do COFINS Retido.

valor_inss_retido	
number
Valor do INSS Retido.

valor_ir_retido	
number
Valor do IR Retido.

valor_csll_retido	
number
Valor do CSLL Retido.

valor_outras_retencoes	
number
responsavel_retencao	
integer
Enum: 0 1 2
0=Não informado 1=Tomador 2=Intermediario

valor_bc_pis	
number
Base de cálculo do PIS.

aliquota_pis	
number
Percentual de PIS.

valor_pis	
number
Valor do PIS.

valor_bc_cofins	
number
Base de cálculo do COFINS.

aliquota_cofins	
number
Percentual de COFINS.

valor_cofins	
number
Valor do COFINS.

xml	
string
XML da nota.

valor_total_servicos	
number
Valor do serviço da nota.

valor_original_fatura	
number
Valor bruto da Fatura vinculada a Nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

Responses
200 NFS-e atualizada!
202 NFS-e atualizada e enviada para SEFAZ!

PATCH
/nfses/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Response samples
200202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Cancelar NFS-e
'Manda a NFS-e para cancelamento'

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 A NFSE Foi enviada para cancelamento.

PATCH
/nfses/cancelar/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id_nfse": 0,
"message": "string"
}
Envia NFS-e por Email
'Envia NFS-e por Email'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Ids das notas enviadas por email

emails	
Array of strings
Emails para os quais a nota será enviada

contador	
boolean
Indicador se o email deve ser enviado ao contador

envia_email_forcado	
boolean
Clientes têm a opção de não receber e-mails automáticos. Essa flag indica se o email é manual ou não. Se for indicada e o cliente não receber e-mail automático, ele vai receber esse e-mail. Se não for indicado, ele não vai receber.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

Responses
200 Sucesso!

POST
/nfses/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"contador": true,
"envia_email_forcado": true,
"enviar_para_todos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Imprimir Listagem de Nfses
'Imprimir Listagem de Nfses'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de NFSE no formato PDF

POST
/nfses/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Resolver uma NFS-e
'Resolver uma NFS-e'

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 NFS-e foi sincronizada com sucesso!

PATCH
/nfses/resolver/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"message": "string"
}
Exportar Nfses
Exportar Nfses

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
data_inicial
required
string
Data Inicial

data_final
required
string
Data Final

tipo_exportacao
required
string
Enum: "D" "E"
D=Realizar Download. | E=Enviar por e-mail

id_nfse	
integer
Gera exportação de NFs-e especifica

configuracao	
string
Enum: "" "1" "2"
1=Agrupar Espelho e XML por pasta. | 2=Gerar todas os espelhos em um único arquivo

gerar_xml	
boolean
Gerar Xml das nfses a exportar

gerar_espelho	
boolean
Gerar Espelho das nfses a exportar

data_considerada	
string
Enum: "1" "2" "3"
Indica a data a ser considerada para geração do(s) Xml(s)/Espelho(s): 1 - Criação | 2 - Confirmação | 3 - Emissão

email	
string
Email para onde a nota exportada será enviada

situacao	
string
Enum: "" "A" "S" "I"
Indica a situação da nota A - Confirmada | S - Cancelada | I - Qualquer

id_clientes	
Array of integers
ids dos clientes vinculados a nfse

id_servicos	
Array of integers
ids dos servicos vinculados a nfse

Responses
200 Sucesso!

POST
/nfses/exportar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_nfse": 0,
"configuracao": "",
"gerar_xml": true,
"gerar_espelho": true,
"data_considerada": "1",
"data_inicial": "string",
"data_final": "string",
"tipo_exportacao": "D",
"email": "string",
"situacao": "",
"id_clientes": [
0
],
"id_servicos": [
0
]
}
Gerar Xml de NFS-e
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a NFS-e em formato XML

GET
/nfses/gerar_xml/{id}
Envia certificado para cadastro
Envia certificado para cadastro na Tecnospeed.

Responses
200 Sucesso!

POST
/nfses/certificado
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"message": "string",
"data": {
"id": "string"
}
}
Cadastra a empresa do emitente no Plugnotas/Tecnospeed
Cadastra a empresa do emitente no Plugnotas/Tecnospeed

Responses
200 Sucesso!

POST
/nfses/empresa
Consultar empresa cadastrada no Plugnotas/Tecnospeed
Responses
200 Sucesso!

GET
/nfses/empresa
Consultar cidades homologadas na tecnospeed
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/nfses/cidade/{id}
sats
Listar SATs
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/sats
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_nota": 0,
"status": "N",
"numero_extrato_aprovacao": "string",
"numero_extrato_cancelamento": "string",
"chave_aprovacao": "string",
"chave_cancelamento": "string",
"data_aprovacao": "2019-08-24T14:15:22Z",
"data_cancelamento": "2019-08-24T14:15:22Z",
"serie_equipamento": "string",
"numero_pdv": 0,
"cliente": {},
"data_criacao": "string",
"data_emissao": "2019-08-24T14:15:22Z",
"qrcode_aprovacao": "string",
"qrcode_cancelamento": "string",
"funcionario": {},
"vendedor": {},
"valor_acrescimo": 0,
"valor_desconto": 0,
"valor_total": 0,
"itens": [],
"faturas": [],
"tem_fatura": true,
"cupons": [],
"xml_aprovacao": "string",
"xml_cancelamento": "string"
}
]
Recuperar SAT
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/sats/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "N",
"numero_extrato_aprovacao": "string",
"numero_extrato_cancelamento": "string",
"chave_aprovacao": "string",
"chave_cancelamento": "string",
"data_aprovacao": "2019-08-24T14:15:22Z",
"data_cancelamento": "2019-08-24T14:15:22Z",
"serie_equipamento": "string",
"numero_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"data_criacao": "string",
"data_emissao": "2019-08-24T14:15:22Z",
"qrcode_aprovacao": "string",
"qrcode_cancelamento": "string",
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"valor_acrescimo": 0,
"valor_desconto": 0,
"valor_total": 0,
"itens": [
{}
],
"faturas": [
{}
],
"tem_fatura": true,
"cupons": [
{}
],
"xml_aprovacao": "string",
"xml_cancelamento": "string"
}
Imprimir Listagem de Sats em PDF
'Imprimir Listagem de Sats em PDF'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Sats no formato PDF

POST
/sats/pdf/listagem_recibo_mini
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Envia SAT por Email
'Envia SAT por Email'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Ids das notas enviadas por email

emails	
Array of strings
Emails para os quais a nota será enviada

contador	
boolean
Indicador se o email deve ser enviado ao contador

envia_email_forcado	
boolean
Clientes têm a opção de não receber e-mails automáticos. Essa flag indica se o email é manual ou não. Se for indicada e o cliente não receber e-mail automático, ele vai receber esse e-mail. Se não for indicado, ele não vai receber.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

Responses
200 Sucesso!

POST
/sats/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"contador": true,
"envia_email_forcado": true,
"enviar_para_todos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Exportar SATs
Exportar SATs

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
data_inicial
required
string
Data Inicial

data_final
required
string
Data Final

tipo_exportacao
required
string
Enum: "D" "E"
D=Realizar Download. | E=Enviar por e-mail

id_sat	
integer
Gera exportação de SAT especifico

configuracao	
string
Enum: "1" "2"
1=Agrupar DANFE e XML por pasta. | 2=Gerar todas as DANFEs em um único arquivo

gerar_xml	
boolean
Gerar Xml das nfes a exportar

gerar_danfe	
boolean
Gerar Danfe das nfes a exportar

data_considerada	
string
Enum: "1" "2" "3"
Indica a data a ser considerada para geração do(s) Xml(s)/Danfe(s): 1 - Criação | 2 - Aprovação | 3 - Emissão |

email	
string
Email para onde a nota exportada será enviada (**Campo Obrigatório caso o tipo_exportação seja E)

situacao	
string
Enum: "" "A" "S"
Indica a situação da nota **** - Qualquer | A - Confirmado | S - Cancelado |

id_clientes	
Array of integers
ids dos clientes vinculados ao SAT

Responses
200 Sucesso!

POST
/sats/exportar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_sat": 0,
"configuracao": "1",
"gerar_xml": true,
"gerar_danfe": true,
"data_considerada": "1",
"data_inicial": "string",
"data_final": "string",
"tipo_exportacao": "D",
"email": "string",
"situacao": "",
"id_clientes": [
0
]
}
Gera uma NF-e através de um sat
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/sats/to_nfe/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Notas Fiscais de Entrada
Criar Nota Fiscal de Entrada
Cria uma Nota Fiscal de Entrada.

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects (Item de Venda)
Itens da venda.

cfop
required
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

numero
required
integer <= 9 characters <= 999999999
Númeração da NF-e.

serie
required
integer
Serie da númeração da NF-e.

data_entrada
required
string <date>
Data Entrada.

situacao	
string
Default: "N"
Enum: "N" "A" "S" "E" "2" "4" "F" "X"
N=Em aberto | A=Confirmado | S=Cancelado | 2=Denegada | 4=Inutilizada | E=Normal Extemporânea | F=Aprovada Extemporânea | X=Cancelada Extemporânea

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

modelo	
string
Enum: "55" "01"
Modelo da nota Fiscal

01=Nota Fiscal

55=Nota Fiscal Eletrônica

chave_acesso	
string = 44 characters
Chave de acesso da NF-e.

lancar_estoque	
string
Enum: "" "P" "R"
Qual estoque deve ser movimentado ao confirmar a nota? Válido apenas para produtos com CFOP de 'X.912' ou '1.126'

P=Estoque Próprio

R=Estoque de Revenda (O padrão)

emitente	
integer
ID do fornecedor da nota fiscal.

data_emissao	
string <date-time>
Data de emissão.

hora_entrada	
string <time>
Hora Entrada.

data_criacao	
string <date-time>
Data de criação.

finalidade_emissao	
integer
Enum: 1 2 3 8
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 8=Regime Especial

pedido_vinculado	
integer
Id Pedido de compra vinculado a nota.

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

modalidade_frete	
string
Enum: "0" "1" "2" "3" "4" "9"
0=Contratação do Frete por conta do Remetente (CIF)

1=Contratação do Frete por conta do Destinatário (FOB)

2=Contratação do Frete por conta de Terceiros

3=Transporte Próprio por conta do Remetente

4=Transporte Próprio por conta do Destinatário

9=Sem Ocorrência de Transporte

forma_pagamento	
string
Enum: "0" "1" "2"
0=À Vista

1=À Prazo

2=Outros

transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

ICMSTot	
object
Dados Referente aos Totais do XML

valor_servicos	
number
Valor dos servicos.

valor_icms	
number
Valor do ICMS.

valor_icms_complemento	
number
Complemento de ICMS (SINTEGRA).

valor_cofins_st	
number
Valor da substituicão tributária do cofins.

valor_pis_st	
number
Valor da substituicão tributária do pis.

valor_pis_retido	
number
Valor Total do PIS retido da Nota

valor_cofins_retido	
number
Valor Total do COFINS retido da Nota

valor_csll_retido	
number
Valor Total do CSLL retido da Nota

base_calculo_irrf	
number
Base de cálculo do IRRF

valor_irrf_retido	
number
Valor Total do IRRF retido da Nota

base_calculo_previdencia_social	
number
Base de cálculo da Previdência Social

valor_previdencia_social	
number
Valor Total do Previdência Social retido da Nota

valor_original_fatura	
number
Valor bruto da Fatura vinculada a Nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

inf_fisco	
string
Informações Adicionais de Interesse do Fisco.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinte.

opcoes	
string
JSON com as opções da nota fiscal.

Responses
201 Nota Fiscal de Entrada criada!
202 Nota Fiscal de Entrada criada.

POST
/notas_fiscais_entrada
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": 0,
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"pedido_vinculado": 0,
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {
"transportador": 0,
"numero_nota": "string",
"serie": "",
"sub_serie": "string",
"modelo": "",
"tributacao": "",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"ICMSTot": {
"vBC": "string",
"vICMS": "string",
"vICMSDeson": "string",
"vFCPUFDest": "string",
"vFCP": "string",
"vBCST": "string",
"vST": "string",
"vFCPST": "string",
"vFCPSTRet": "string",
"vProd": "string",
"vFrete": "string",
"vSeg": "string",
"vDesc": "string",
"vII": "string",
"vIPI": "string",
"vIPIDevol": "string",
"vPIS": "string",
"vCOFINS": "string",
"vOutro": "string",
"vNF": "string"
},
"valor_servicos": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_original_fatura": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string"
}
Response samples
201202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"funcionario_responsavel": 0,
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": {
"id": 0,
"id_entidade": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"natureza_operacao": "string",
"pedido_vinculado": {
"id": 0,
"numero": 0
},
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "",
"sub_serie": "str",
"modelo": "",
"tributacao": "",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"ICMSTot": {
"vBC": "string",
"vICMS": "string",
"vICMSDeson": "string",
"vFCPUFDest": "string",
"vFCP": "string",
"vBCST": "string",
"vST": "string",
"vFCPST": "string",
"vFCPSTRet": "string",
"vProd": "string",
"vFrete": "string",
"vSeg": "string",
"vDesc": "string",
"vII": "string",
"vIPI": "string",
"vIPIDevol": "string",
"vPIS": "string",
"vCOFINS": "string",
"vOutro": "string",
"vNF": "string"
},
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_servicos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_bc_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"valor_original_fatura": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string",
"tem_fatura": true
}
Recuperar Nota Fiscal de Entrada
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/notas_fiscais_entrada/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"funcionario_responsavel": 0,
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": {
"id": 0,
"id_entidade": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"natureza_operacao": "string",
"pedido_vinculado": {
"id": 0,
"numero": 0
},
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "",
"sub_serie": "str",
"modelo": "",
"tributacao": "",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"ICMSTot": {
"vBC": "string",
"vICMS": "string",
"vICMSDeson": "string",
"vFCPUFDest": "string",
"vFCP": "string",
"vBCST": "string",
"vST": "string",
"vFCPST": "string",
"vFCPSTRet": "string",
"vProd": "string",
"vFrete": "string",
"vSeg": "string",
"vDesc": "string",
"vII": "string",
"vIPI": "string",
"vIPIDevol": "string",
"vPIS": "string",
"vCOFINS": "string",
"vOutro": "string",
"vNF": "string"
},
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_servicos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_bc_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"valor_original_fatura": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string",
"tem_fatura": true
}
Editar Nota Fiscal de Entrada
Atualiza as informações da nota_fiscal_entrada.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
situacao	
string
Default: "N"
Enum: "N" "A" "S" "E" "2" "4" "F" "X"
N=Em aberto | A=Confirmado | S=Cancelado | 2=Denegada | 4=Inutilizada | E=Normal Extemporânea | F=Aprovada Extemporânea | X=Cancelada Extemporânea

numero	
integer <= 9 characters <= 999999999
Númeração da NF-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

serie	
integer
Serie da númeração da NF-e.

modelo	
string
Enum: "55" "01"
Modelo da nota Fiscal

01=Nota Fiscal

55=Nota Fiscal Eletrônica

chave_acesso	
string = 44 characters
Chave de acesso da NF-e.

lancar_estoque	
string
Enum: "" "P" "R"
Qual estoque deve ser movimentado ao confirmar a nota? Válido apenas para produtos com CFOP de 'X.912' ou '1.126'

P=Estoque Próprio

R=Estoque de Revenda (O padrão)

emitente	
integer
ID do fornecedor da nota fiscal.

data_emissao	
string <date-time>
Data de emissão.

data_entrada	
string <date>
Data Entrada.

hora_entrada	
string <time>
Hora Entrada.

data_criacao	
string <date-time>
Data de criação.

finalidade_emissao	
integer
Enum: 1 2 3 8
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 8=Regime Especial

cfop	
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

pedido_vinculado	
integer
Id Pedido de compra vinculado a nota.

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

modalidade_frete	
string
Enum: "0" "1" "2" "3" "4" "9"
0=Contratação do Frete por conta do Remetente (CIF)

1=Contratação do Frete por conta do Destinatário (FOB)

2=Contratação do Frete por conta de Terceiros

3=Transporte Próprio por conta do Remetente

4=Transporte Próprio por conta do Destinatário

9=Sem Ocorrência de Transporte

forma_pagamento	
string
Enum: "0" "1" "2"
0=À Vista

1=À Prazo

2=Outros

transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

itens	
Array of objects (Item de Venda)
Itens da venda.

ICMSTot	
object
Dados Referente aos Totais do XML

valor_servicos	
number
Valor dos servicos.

valor_icms	
number
Valor do ICMS.

valor_icms_complemento	
number
Complemento de ICMS (SINTEGRA).

valor_cofins_st	
number
Valor da substituicão tributária do cofins.

valor_pis_st	
number
Valor da substituicão tributária do pis.

valor_pis_retido	
number
Valor Total do PIS retido da Nota

valor_cofins_retido	
number
Valor Total do COFINS retido da Nota

valor_csll_retido	
number
Valor Total do CSLL retido da Nota

base_calculo_irrf	
number
Base de cálculo do IRRF

valor_irrf_retido	
number
Valor Total do IRRF retido da Nota

base_calculo_previdencia_social	
number
Base de cálculo da Previdência Social

valor_previdencia_social	
number
Valor Total do Previdência Social retido da Nota

valor_original_fatura	
number
Valor bruto da Fatura vinculada a Nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

inf_fisco	
string
Informações Adicionais de Interesse do Fisco.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinte.

opcoes	
string
JSON com as opções da nota fiscal.

Responses
200 Nota Fiscal de Entrada atualizada!
202 Nota Fiscal de Entrada atualizada.

PATCH
/notas_fiscais_entrada/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": 0,
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"pedido_vinculado": 0,
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {
"transportador": 0,
"numero_nota": "string",
"serie": "",
"sub_serie": "string",
"modelo": "",
"tributacao": "",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"ICMSTot": {
"vBC": "string",
"vICMS": "string",
"vICMSDeson": "string",
"vFCPUFDest": "string",
"vFCP": "string",
"vBCST": "string",
"vST": "string",
"vFCPST": "string",
"vFCPSTRet": "string",
"vProd": "string",
"vFrete": "string",
"vSeg": "string",
"vDesc": "string",
"vII": "string",
"vIPI": "string",
"vIPIDevol": "string",
"vPIS": "string",
"vCOFINS": "string",
"vOutro": "string",
"vNF": "string"
},
"valor_servicos": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_original_fatura": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string"
}
Response samples
200202
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"funcionario_responsavel": 0,
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": {
"id": 0,
"id_entidade": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"natureza_operacao": "string",
"pedido_vinculado": {
"id": 0,
"numero": 0
},
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "",
"sub_serie": "str",
"modelo": "",
"tributacao": "",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"itens": [
{}
],
"ICMSTot": {
"vBC": "string",
"vICMS": "string",
"vICMSDeson": "string",
"vFCPUFDest": "string",
"vFCP": "string",
"vBCST": "string",
"vST": "string",
"vFCPST": "string",
"vFCPSTRet": "string",
"vProd": "string",
"vFrete": "string",
"vSeg": "string",
"vDesc": "string",
"vII": "string",
"vIPI": "string",
"vIPIDevol": "string",
"vPIS": "string",
"vCOFINS": "string",
"vOutro": "string",
"vNF": "string"
},
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_servicos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_bc_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"valor_original_fatura": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string",
"tem_fatura": true
}
Apagar Nota Fiscal de Entrada
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Nota Fiscal de Entrada apagada!

DELETE
/notas_fiscais_entrada/{id}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/notas_fiscais_entrada/pdf/recibo_a4/{id}
Importar Nota Fiscal de Entrada
HEADER PARAMETERS
X-Criar-Produto
required
integer
Example: 1
1 - Cadastrar produto automaticamente (serão inseridos dados padrões) 2 - Não cadastrar produto automaticamente e validar o reconhecimento dos Produtos somente pelo código 3 - Não cadastrar produto automaticamente e validar o reconhecimento dos Produtos pelo código e descrição

REQUEST BODY SCHEMA: multipart/form-data
file	
string <binary>
O xml a ser enviado.

Responses
200 Sucesso ao importar xml!

POST
/notas_fiscais_entrada/importar_xml
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": { },
"errors": []
}
]
Informa produtos inativos em uma nota fiscal de entrada
'Informa produtos inativos em uma nota fiscal de entrada'

Responses
200 Sucesso!

GET
/notas_fiscais_entrada/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
Vendas Simples
Listar vendas simples
Lista também as vendas simples feitas pelo PDV.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

X-Totalizadores	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

Responses
200 Sucesso!

GET
/vendas_simples
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {},
"pedido_os_vinculada": {},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {},
"itens": [],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {},
"faturas": [],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
]
Criar vendas simples
'Criar vendas simples'

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects (Item de Venda)
Itens da venda simples.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
string <= 7 characters
Número da venda. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

pedido_os_vinculada	
integer
ID do Pedido ou OS vinculado à Venda Simples.

data_criacao	
string <date-time>
Data de criação da venda. Gerado automaticamente.

data_confirmacao	
string <date-time>
Data de confirmação da venda

status	
string
Enum: "N" "A" "S"
Situação das Vendas N=Em digitação | A=Aprovada | S=Cancelada |

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

observacoes	
string
Observações gerais. Texto livre.

valor_desconto	
number
Valor do desconto.

valor_frete	
number
Valor do frete.

valor_acrescimo	
number
Valor do acréscimo.

valor_troco	
number
Valor do troco.

valor_total	
number
Valor total da nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da venda. São as formas de pagamento usadas para pagar pela venda.

departamento	
integer
Campo identificador do departamento ao qual a venda está vinculada. se não informado, o departamento padrão será indicado. Saiba como recuperar departamentos clicando aqui

Responses
201 Vendas simples criada!

POST
/vendas_simples
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": 0,
"pedido_os_vinculada": 0,
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": 0,
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"faturas": [
{}
],
"departamento": 0
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [
"string"
],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
Recuperar venda simples
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/vendas_simples/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [
"string"
],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
Editar venda simples
Atualiza as informações da venda simples.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
string <= 7 characters
Número da venda. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

pedido_os_vinculada	
integer
ID do Pedido ou OS vinculado à Venda Simples.

data_criacao	
string <date-time>
Data de criação da venda. Gerado automaticamente.

data_confirmacao	
string <date-time>
Data de confirmação da venda

status	
string
Enum: "N" "A" "S"
Situação das Vendas N=Em digitação | A=Aprovada | S=Cancelada |

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

itens	
Array of objects (Item de Venda)
Itens da venda simples.

observacoes	
string
Observações gerais. Texto livre.

valor_desconto	
number
Valor do desconto.

valor_frete	
number
Valor do frete.

valor_acrescimo	
number
Valor do acréscimo.

valor_troco	
number
Valor do troco.

valor_total	
number
Valor total da nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da venda. São as formas de pagamento usadas para pagar pela venda.

departamento	
integer
Campo identificador do departamento ao qual a venda está vinculada. se não informado, o departamento padrão será indicado. Saiba como recuperar departamentos clicando aqui

Responses
200 Venda simples alterada!

PATCH
/vendas_simples/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": 0,
"pedido_os_vinculada": 0,
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": 0,
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"faturas": [
{}
],
"departamento": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [
"string"
],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
Apagar venda simples
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Venda simples apagada!

DELETE
/vendas_simples/{id}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/vendas_simples/pdf/recibo_a4/{id}
Recibo Mini PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo Mini no formato PDF

GET
/vendas_simples/pdf/recibo_mini/{id}
Cupom Troca PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Cupom de Troca no formato PDF

GET
/vendas_simples/pdf/cupom_troca/{id}
Imprimir Listagem Venda Simples
'Imprimir Listagem Venda Simples'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem Venda Simples no formato PDF

POST
/vendas_simples/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Mesclar vendas simples
'Mesclar vendas simples'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
mesclar_observacoes
required
boolean
Indica se irá mesclar as observações

mesclar_frete
required
boolean
Default: true
Indica se irá mesclar os valores de frete

agrupar
required
boolean
Indica se irá agrupar os produtos iguais.

opcoes
required
integer
Default: 0
Enum: 0 1 2
Opções:

0=Além de mesclar, manter as Vendas Simples selecionadas como estão

1=Após mesclar, cancelar as Vendas Simples selecionadas

2=Após mesclar, confirmar as Vendas Simples selecionadas

ids
required
Array of integers
Id's das vendas que serão mescladas

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

Responses
200 Sucesso!

POST
/vendas_simples/mesclar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"cliente": 0,
"vendedor": 0,
"opcoes": 0,
"agrupar": true,
"mesclar_frete": true,
"mesclar_observacoes": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": {},
"pedido_os_vinculada": {},
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": {},
"itens": [],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"funcionario": {},
"faturas": [],
"venda_no_pdv": true,
"terminal_caixa": "string",
"anexos": [],
"data_alteracao": "2019-08-24T14:15:22Z",
"link": "string",
"item": 0,
"message": "string",
"tem_fatura": true
}
]
Enviar e-mail Vendas simples
'Enviar vendas por e-mail'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids
required
Array of integers
Ids das movimentações enviadas por email

emails	
Array of strings
Array com os e-mails para onde serão enviadas as movimentações.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

anexar_arquivos	
boolean
Default: false
Indica se os arquivos vinculados à movimentação serão anexados ao e-mail.

anexar_fotos_produtos	
boolean
Default: false
Indica se as fotos vinculadas aos produtos serão anexados ao e-mail.

Responses
200 Sucesso!

POST
/vendas_simples/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"enviar_para_todos": false,
"anexar_arquivos": false,
"anexar_fotos_produtos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Gera uma NF-e através de venda simples
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/vendas_simples/to_nfe/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "E",
"status": "0",
"serie": 0,
"numero": 999999999,
"numero_fatura": "string",
"chave_acesso": "string",
"emitente": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cpf_cnpj_responsavel_retirada": "string",
"ie_retirada": "string",
"data_contingencia": "2019-08-24",
"hora_contingencia": "14:15:22Z",
"justificativa_contingencia": "stringstringstr",
"destinatario": {
"id": 0,
"tipo": "F",
"razao_social": "string",
"cpf": "string",
"cnpj": "string",
"enderecos": []
},
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"cpf_cnpj_responsavel_entrega": "string",
"ie_entrega": "string",
"dados_entrega_nome": "string",
"dados_entrega_telefone": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"data_alteracao": "2019-08-24T14:15:22Z",
"data_entrada_saida": "2019-08-24",
"hora_entrada_saida": "14:15:22Z",
"modalidade_frete": "0",
"cfop": "string",
"movimentacao_mercadoria": true,
"notas_referenciadas": [
{}
],
"finalidade_emissao": 1,
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"tipo_emissao": 1,
"ambiente": 1,
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"consumidor_final": true,
"uso_livre_contribuinte": [
{}
],
"econf": [
{}
],
"transportadora": {
"transportador": {},
"numero_nota": "string",
"serie": "B",
"sub_serie": "string",
"modelo": "57",
"tributacao": "00",
"chave_cte": "string",
"data_emissao": "string",
"data_prestacao": "string",
"desconto": 0,
"total_nota": 0,
"cfop": "string",
"valor_servico": 0,
"gera_credito": true,
"base_calculo_icms_ret": 0,
"aliquota_icms_ret": 0,
"valor_icms_ret": 0,
"municipio_gerador": "string",
"observacoes": "string",
"identificacao_balsa": "string",
"identificacao_vagao": "string",
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string",
"reboque": [],
"volume": []
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"itens": [
{}
],
"valor_frete": 0,
"valor_seguro": 0,
"valor_outras_despesas": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_bc_icms_st": 0,
"valor_icms_st": 0,
"valor_icms_desonerado": 0,
"valor_icms_st_desonerado": 0,
"valor_ipi_devolvido": 0,
"valor_ii": 0,
"valor_ipi": 0,
"valor_pis": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_cofins": 0,
"valor_icms_mono": 0,
"valor_bc_icms_mono": 0,
"valor_icms_mono_retencao": 0,
"valor_bc_icms_mono_retencao": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_fcp": 0,
"valor_fcp_st": 0,
"valor_fcp_st_ret": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_nota": 0,
"faturas": [
{}
],
"inf_fisco": "string",
"inf_contribuinte": "string",
"observacoes": "string",
"numero_pedido": "string",
"xml_aprovacao": "string",
"xml_cancelamento": "string",
"xml_inutilizacao": "string",
"justificativa": "stringstringstr",
"anexos": [
"string"
],
"tem_fatura": true,
"tem_cce": true,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"id_nota": 0,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"enviada": 0,
"rejeitada": 0,
"possui_xml_banco": true,
"possui_xml_s3": true,
"endereco_entrega": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_emitente": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_destinatario": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"endereco_retirada": {
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"informacoes_adicionais": "string",
"tipo_cadastro": {},
"id_entidade": 0,
"id_endereco_entidade": 0
},
"historico": [
{}
],
"link": "string"
}
Gera uma NFC-e através de venda simples
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/vendas_simples/to_nfce/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_nota": 0,
"status": "0",
"rejeitada": 0,
"processando": true,
"opcoes": {
"utilizar_vr_nota": true,
"lancar_financeiro": true,
"lancar_estoque": true,
"abater_icms_desonerado": true
},
"serie": 0,
"numero": 0,
"numero_fatura": "string",
"chave_acesso": "string",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"data_emissao": "2019-08-24T14:15:22Z",
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": {
"id": 0,
"cnpj": "string",
"razao_social": "string",
"identificador": "string"
},
"cfop": "string",
"modalidade_frete": "0",
"indicador_forma_pagamento": 0,
"movimentacao_mercadoria": true,
"venda_vinculada": {
"id": 0,
"numero": 0
},
"tipo_emissao": 1,
"ambiente": 1,
"codigo_numerico": 0,
"situacao_pdv": 0,
"cliente": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"vendedor": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"transportadora": {
"transportador": {}
},
"itens": [
{}
],
"faturas": [
{}
],
"valor_frete": 0,
"valor_desconto": 0,
"valor_produtos": 0,
"valor_bc_icms": 0,
"valor_icms": 0,
"valor_icms_mono_retido": 0,
"valor_bc_icms_mono_retido": 0,
"valor_pis": 0,
"valor_cofins": 0,
"valor_pago": 0,
"valor_troco": 0,
"valor_nota": 0,
"valor_total": 0,
"observacoes": "string",
"inf_contribuinte": "string",
"data_contingencia": "string",
"hora_contingencia": "string",
"justificativa_contingencia": "string",
"abater_icms_desonerado": true,
"xml": "string",
"tem_fatura": true,
"possui_xml_banco": true,
"possui_xml_s3": true,
"link": "string"
}
Gera uma NFS-e através de venda simples
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

Responses
200 Sucesso!

GET
/vendas_simples/to_nfse/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"status": "A",
"serie_rps": 12345,
"numero_rps": "56405046574",
"numero_nfse": 1,
"data_aprovacao": "2019-02-07 17:00:00",
"cliente": 2,
"funcionario": 1,
"vendedor": 1,
"observacoes": "",
"municipio_prestacao": 4205407,
"natureza_tributacao": 1,
"tipo_tributacao": 6,
"intermediario_razao_social": "padaria pao de cada dia",
"intermediario_im": "13456168042",
"intermediario_cnpj": "94.015.121/0001-50",
"numero_art": "0",
"codigo_obra": "0",
"descricao_servico": "Desenvolvimento de Software",
"codigo_tabela_servico": "1234",
"cnae": "6202300",
"codigo_tributacao_municipio": "",
"cst_pis": "01",
"cst_cofins": "01",
"itens": [
{}
],
"valor_servico": 10000,
"aliquota_iss": 6,
"valor_deducoes": 300,
"valor_iss": 582,
"valor_liquido": 7900,
"valor_iss_retido": 300,
"valor_pis_retido": 300,
"valor_cofins_retido": 300,
"valor_inss_retido": 300,
"valor_ir_retido": 300,
"valor_csll_retido": 300,
"valor_outras_retencoes": 300,
"valor_bc_pis": 9700,
"aliquota_pis": 6,
"valor_pis": 582,
"valor_bc_cofins": 9700,
"aliquota_cofins": 6,
"valor_cofins": 582,
"xml": "aaaaaaa",
"faturas": [
{}
]
}
Informa produtos inativos na venda simples
'Informa produtos inativos na venda simples'

Responses
200 Sucesso!

GET
/vendas_simples/produtos_inativos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao_produto": "string",
"descricao": "string",
"ativo": true,
"cod_secundario": "string"
}
]
Ajustes de Estoque
Listar ajustes de estoque
Listar ajustes de estoque.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/ajustes_estoque
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {},
"pedido_os_vinculada": {},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {},
"faturas": [],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
]
Criar ajustes de estoque
'Criar ajustes de estoque'

HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
itens
required
Array of objects (Item de Venda)
Itens do ajuste de estoque simples.

tipo
required
string
Enum: "C" "D" "E" "S"
C=Compra D=Devolução E=Entrada S=Saída

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
string
Número do ajuste de estoque. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

entidade	
integer
Campo identificador da entidade

pedido_os_vinculada	
integer
ID do Pedido ou OS vinculado ao Ajuste de Estoque.

status	
string
Enum: "N" "A" "S"
Situação das Vendas N=Em digitação | A=Aprovada | S=Cancelada |

data_criacao	
string <date-time>
Data de criação do ajuste de estoque. Gerado automaticamente.

data_confirmacao	
string <date-time>
Data de confirmação do ajuste de estoque

observacoes	
string
Observações gerais. Texto livre.

valor_frete	
number
Valor do frete.

valor_total	
number
Valor total da nota.

valor_outros	
number
Valor de outros da nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do ajuste de estoque. São as formas de pagamento usadas para pagar pela venda.

Responses
201 Ajuste de estoque criado!

POST
/ajustes_estoque
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": 0,
"pedido_os_vinculada": 0,
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"faturas": [
{}
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
Recuperar ajuste de estoque
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/ajustes_estoque/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
Editar ajuste de estoque
Atualiza as informações do ajuste de estoque.

PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
tipo	
string
Enum: "C" "D" "E" "S"
C=Compra D=Devolução E=Entrada S=Saída

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
string
Número do ajuste de estoque. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

entidade	
integer
Campo identificador da entidade

pedido_os_vinculada	
integer
ID do Pedido ou OS vinculado ao Ajuste de Estoque.

status	
string
Enum: "N" "A" "S"
Situação das Vendas N=Em digitação | A=Aprovada | S=Cancelada |

data_criacao	
string <date-time>
Data de criação do ajuste de estoque. Gerado automaticamente.

data_confirmacao	
string <date-time>
Data de confirmação do ajuste de estoque

itens	
Array of objects (Item de Venda)
Itens do ajuste de estoque simples.

observacoes	
string
Observações gerais. Texto livre.

valor_frete	
number
Valor do frete.

valor_total	
number
Valor total da nota.

valor_outros	
number
Valor de outros da nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do ajuste de estoque. São as formas de pagamento usadas para pagar pela venda.

Responses
200 Ajuste de estoque alterado!

PATCH
/ajustes_estoque/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": 0,
"pedido_os_vinculada": 0,
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"faturas": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "C",
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"entidade": {
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
},
"pedido_os_vinculada": {
"id": 0,
"numero": 0,
"tipo": "string"
},
"status": "N",
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"itens": [
{}
],
"observacoes": "string",
"valor_frete": 0,
"valor_total": 0,
"valor_outros": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"faturas": [
{}
],
"data_alteracao": "2019-08-24T14:15:22Z",
"tem_fatura": true
}
Apagar ajuste de estoque
PATH PARAMETERS
id
required
integer
Example: 1
HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Ajuste de estoque apagado!

DELETE
/ajustes_estoque/{id}
Imprimir Listagem de Ajustes de Estoque
'Imprimir Listagem de Ajustes de Estoque'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Ajustes de Estoque no formato PDF

POST
/ajustes_estoque/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
servicos
Listar servicos
Lista todos os servicos cadastrados.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/servicos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"categoria": {},
"tabela_servico": {},
"codigo": "string",
"comissao": 0,
"pontos": 0,
"valor_unitario": 0,
"descricao": "string",
"imagem_principal": {},
"observacoes": "string",
"aliquota_deducoes": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_inss": 0,
"aliquota_ir_retido": 0,
"aliquota_csll_retido": 0,
"aliquota_outros": 0,
"aliquota_iss_retido": 0,
"natureza_operacao": "1",
"indicador_incentivo_fiscal": "1",
"exigibilidade": "",
"data_alteracao": "string",
"movimentado": true,
"imagens": []
}
]
Criar servico
Criar um serviço

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo
required
string
Código do servico.

descricao
required
string
Descricão/Nome do servico.

valor_unitario
required
number
Valor por Unidade do Serviço. Ex.: Valor por Hora, Impressão, etc.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o serviço está ativo, onde ativo=true indica serviço ativo.

categoria	
string
Campo identificador da categoria do produto, é possível recuperar categorias pelo recurso /categorias, saiba como recuperar categorias do ERP clicando aqui

tabela_servico	
integer
ID Tabela serviço.

comissao	
number
Alíquota de comissão do serviço.

pontos	
integer
Pontos do serviço.

imagem_principal	
integer
ID da imagem principal.

observacoes	
string
Descricão/Nome do servico.

aliquota_deducoes	
number
Alíquota de deduções.

aliquota_pis	
number
Alíquota de PIS.

aliquota_cofins	
number
Alíquota de COFINS.

aliquota_inss	
number
Alíquota de INSS.

aliquota_ir_retido	
number
Alíquota de IR Retido.

aliquota_csll_retido	
number
Alíquota de CSLL Retido.

aliquota_outros	
number
Alíquota de Outras Retenções.

aliquota_iss_retido	
number
Alíquota de ISS Retido.

natureza_operacao	
string
Enum: "1" "2" "3" "4" "5" "6"
"Data da última alteração no servico."

1=Tributação no município

2=Tributação fora do município

3=Isenção

4=Imune

5=Exigibilidade suspensa por decisão judicial

6=Exigibilidade suspensa por procedimento administrativo

indicador_incentivo_fiscal	
string
Default: "S"
Enum: "1" "2"
"Indicador de incentivo fiscal"

1=Sim

2=Não

exigibilidade	
string
Default: "1"
Enum: "" "1" "2" "3" "4" "5" "6" "7"
"Exigibilidade do ISS"

1=Exigível

2=Não Incidência

3=Isenção

4=Exportação

5=Imunidade

6=Supenso por Ação Judicial

7=Suspenso por Ação Administrativa

imagens	
Array of objects (Dados da imagem)
Array de Base64 de imagens para serem salvas no serviço.

property name*
additional property
any
Responses
201 Servico criado!

POST
/servicos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"ativo": true,
"categoria": "string",
"tabela_servico": 0,
"codigo": "string",
"comissao": 0,
"pontos": 0,
"valor_unitario": 0,
"descricao": "string",
"imagem_principal": 0,
"observacoes": "string",
"aliquota_deducoes": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_inss": 0,
"aliquota_ir_retido": 0,
"aliquota_csll_retido": 0,
"aliquota_outros": 0,
"aliquota_iss_retido": 0,
"natureza_operacao": "1",
"indicador_incentivo_fiscal": "1",
"exigibilidade": "",
"imagens": [
{}
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"categoria": {
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {}
},
"tabela_servico": {
"id": 0,
"cnae": {},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
},
"codigo": "string",
"comissao": 0,
"pontos": 0,
"valor_unitario": 0,
"descricao": "string",
"imagem_principal": {
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
},
"observacoes": "string",
"aliquota_deducoes": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_inss": 0,
"aliquota_ir_retido": 0,
"aliquota_csll_retido": 0,
"aliquota_outros": 0,
"aliquota_iss_retido": 0,
"natureza_operacao": "1",
"indicador_incentivo_fiscal": "1",
"exigibilidade": "",
"data_alteracao": "string",
"movimentado": true,
"imagens": [
"string"
]
}
Recuperar servico
Recupera o servico detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/servicos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"categoria": {
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {}
},
"tabela_servico": {
"id": 0,
"cnae": {},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
},
"codigo": "string",
"comissao": 0,
"pontos": 0,
"valor_unitario": 0,
"descricao": "string",
"imagem_principal": {
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
},
"observacoes": "string",
"aliquota_deducoes": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_inss": 0,
"aliquota_ir_retido": 0,
"aliquota_csll_retido": 0,
"aliquota_outros": 0,
"aliquota_iss_retido": 0,
"natureza_operacao": "1",
"indicador_incentivo_fiscal": "1",
"exigibilidade": "",
"data_alteracao": "string",
"movimentado": true,
"imagens": [
"string"
]
}
Atualizar servico
Atualizar um serviço

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o serviço está ativo, onde ativo=true indica serviço ativo.

categoria	
string
Campo identificador da categoria do produto, é possível recuperar categorias pelo recurso /categorias, saiba como recuperar categorias do ERP clicando aqui

tabela_servico	
integer
ID Tabela serviço.

codigo	
string
Código do servico.

comissao	
number
Alíquota de comissão do serviço.

pontos	
integer
Pontos do serviço.

valor_unitario	
number
Valor por Unidade do Serviço. Ex.: Valor por Hora, Impressão, etc.

descricao	
string
Descricão/Nome do servico.

imagem_principal	
integer
ID da imagem principal.

observacoes	
string
Descricão/Nome do servico.

aliquota_deducoes	
number
Alíquota de deduções.

aliquota_pis	
number
Alíquota de PIS.

aliquota_cofins	
number
Alíquota de COFINS.

aliquota_inss	
number
Alíquota de INSS.

aliquota_ir_retido	
number
Alíquota de IR Retido.

aliquota_csll_retido	
number
Alíquota de CSLL Retido.

aliquota_outros	
number
Alíquota de Outras Retenções.

aliquota_iss_retido	
number
Alíquota de ISS Retido.

natureza_operacao	
string
Enum: "1" "2" "3" "4" "5" "6"
"Data da última alteração no servico."

1=Tributação no município

2=Tributação fora do município

3=Isenção

4=Imune

5=Exigibilidade suspensa por decisão judicial

6=Exigibilidade suspensa por procedimento administrativo

indicador_incentivo_fiscal	
string
Default: "S"
Enum: "1" "2"
"Indicador de incentivo fiscal"

1=Sim

2=Não

exigibilidade	
string
Default: "1"
Enum: "" "1" "2" "3" "4" "5" "6" "7"
"Exigibilidade do ISS"

1=Exigível

2=Não Incidência

3=Isenção

4=Exportação

5=Imunidade

6=Supenso por Ação Judicial

7=Suspenso por Ação Administrativa

imagens	
Array of objects (Dados da imagem)
Array de Base64 de imagens para serem salvas no serviço.

property name*
additional property
any
Responses
200 Servico Atualizado!

PATCH
/servicos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"ativo": true,
"categoria": "string",
"tabela_servico": 0,
"codigo": "string",
"comissao": 0,
"pontos": 0,
"valor_unitario": 0,
"descricao": "string",
"imagem_principal": 0,
"observacoes": "string",
"aliquota_deducoes": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_inss": 0,
"aliquota_ir_retido": 0,
"aliquota_csll_retido": 0,
"aliquota_outros": 0,
"aliquota_iss_retido": 0,
"natureza_operacao": "1",
"indicador_incentivo_fiscal": "1",
"exigibilidade": "",
"imagens": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"categoria": {
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {}
},
"tabela_servico": {
"id": 0,
"cnae": {},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
},
"codigo": "string",
"comissao": 0,
"pontos": 0,
"valor_unitario": 0,
"descricao": "string",
"imagem_principal": {
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
},
"observacoes": "string",
"aliquota_deducoes": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_inss": 0,
"aliquota_ir_retido": 0,
"aliquota_csll_retido": 0,
"aliquota_outros": 0,
"aliquota_iss_retido": 0,
"natureza_operacao": "1",
"indicador_incentivo_fiscal": "1",
"exigibilidade": "",
"data_alteracao": "string",
"movimentado": true,
"imagens": [
"string"
]
}
Apagar servico
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Servicos apagado!

DELETE
/servicos/{id}
Imprimir Listagem de Serviços
'Imprimir Listagem de Serviços'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Serviços no formato PDF

POST
/servicos/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Recupera descrição do serviço do service auxiliar.
Responses
200 Sucesso!

GET
/servicos/cod_servico
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"descricao": "string"
}
]
Tabela de Serviço
Listar tabela de servicos
Lista todas as tabelas de servicos cadastradas.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/tabela_servicos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"cnae": {},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
}
]
Criar tabela de servico
Criar uma tabela de serviço

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo
required
string <= 6 characters
Código da Tabela Serviço

descricao
required
string
Descrição

aliquota_iss
required
number
Alíquota de ISS

cnae	
integer
ID do CNAE

cst_pis	
string
Enum: "01" "02" "04" "06" "07" "08" "09" "49" "99"
CST PIS

01 - Operação Tributável com Alíquota Básica

02 - Operação Tributável com Alíquota Diferenciada

04 - Operação Tributável Monofásica - Revenda a Alíquota Zero

06 - Operação Tributável a Alíquota Zero

07 - Operação Isenta da Contribuição

08 - Operação Sem Incidência da Contribuição

09 - Operação com Suspensão da Contribuição

49 - Outras Operações de Saída

99 - Outras Operações

aliquota_pis	
number
Alíquota de PIS

cst_cofins	
string
Enum: "01" "02" "04" "06" "07" "08" "09" "49" "99"
CST COFINS

01 - Operação Tributável com Alíquota Básica

02 - Operação Tributável com Alíquota Diferenciada

04 - Operação Tributável Monofásica - Revenda a Alíquota Zero

06 - Operação Tributável a Alíquota Zero

07 - Operação Isenta da Contribuição

08 - Operação Sem Incidência da Contribuição

09 - Operação com Suspensão da Contribuição

49 - Outras Operações de Saída

99 - Outras Operações

aliquota_cofins	
number
Alíquota de COFINS

codigo_tributacao_municipio	
string
Código de tributação do municipio.

property name*
additional property
any
Responses
201 Tabela de Servico criado!

POST
/tabela_servicos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"cnae": 0,
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"cnae": {
"id": 0,
"codigo": "string",
"descricao": "string",
"principal": true,
"cnae_vinculado": true
},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
}
Recuperar tabela de servico
Recupera a tabela de servico detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/tabela_servicos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"cnae": {
"id": 0,
"codigo": "string",
"descricao": "string",
"principal": true,
"cnae_vinculado": true
},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
}
Atualizar tabela de servico
Atualizar uma tabela de serviço

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
cnae	
integer
ID do CNAE

codigo	
string <= 6 characters
Código da Tabela Serviço

descricao	
string
Descrição

cst_pis	
string
Enum: "01" "02" "04" "06" "07" "08" "09" "49" "99"
CST PIS

01 - Operação Tributável com Alíquota Básica

02 - Operação Tributável com Alíquota Diferenciada

04 - Operação Tributável Monofásica - Revenda a Alíquota Zero

06 - Operação Tributável a Alíquota Zero

07 - Operação Isenta da Contribuição

08 - Operação Sem Incidência da Contribuição

09 - Operação com Suspensão da Contribuição

49 - Outras Operações de Saída

99 - Outras Operações

aliquota_pis	
number
Alíquota de PIS

cst_cofins	
string
Enum: "01" "02" "04" "06" "07" "08" "09" "49" "99"
CST COFINS

01 - Operação Tributável com Alíquota Básica

02 - Operação Tributável com Alíquota Diferenciada

04 - Operação Tributável Monofásica - Revenda a Alíquota Zero

06 - Operação Tributável a Alíquota Zero

07 - Operação Isenta da Contribuição

08 - Operação Sem Incidência da Contribuição

09 - Operação com Suspensão da Contribuição

49 - Outras Operações de Saída

99 - Outras Operações

aliquota_cofins	
number
Alíquota de COFINS

aliquota_iss	
number
Alíquota de ISS

codigo_tributacao_municipio	
string
Código de tributação do municipio.

property name*
additional property
any
Responses
200 Tabela de Servico Atualizado!

PATCH
/tabela_servicos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"cnae": 0,
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"cnae": {
"id": 0,
"codigo": "string",
"descricao": "string",
"principal": true,
"cnae_vinculado": true
},
"codigo": "string",
"descricao": "string",
"cst_pis": "01",
"aliquota_pis": 0,
"cst_cofins": "01",
"aliquota_cofins": 0,
"aliquota_iss": 0,
"codigo_tributacao_municipio": "string",
"possui_vinculo": true
}
Apagar tabela de servico
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Tabela de Servicos apagado!

DELETE
/tabela_servicos/{id}
produtos
Listar produtos
Lista todos os produtos cadastrados.

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/produtos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo": 123456789,
"descricao": "Aparador 350V"
}
]
Criar produto
Cadastra um novo produto.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descricão/Nome do produto.

id	
integer
Campo identificador do registro do produto.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o produto está ativo, onde ativo=true indica produto ativo.

codigo	
string
Caso não seja fornecido um código interno, o sistema gera um automáticamente

codigo_barras	
string
Código de barras do fabricante do produto. Padrão EAN13

codigo_barras_tributavel	
string [ 8 .. 14 ] characters
Código de barras da unidade do produto (cEAN Trib.). Caso seja preenchido, este campo deve ser um EAN válido e possuir 8, 12,13 ou 14 caracteres. Padrão EAN13

imagem_principal	
integer
ID da imagem principal.

categoria	
integer
Campo identificador da categoria do produto, é possível recuperar categorias pelo recurso /categorias, saiba como recuperar categorias do ERP clicando aqui

departamento	
integer
Campo identificador do departamento do produto, é possível recuperar departamentos pelo recurso /departamento, saiba como recuperar departamentos do ERP clicando aqui

estoque	
object (Estoque de Produto)
qtd_revenda	
number
data_validade	
string
Data de validade do produto.

unidade_entrada	
integer
unidade_saida	
integer
unidade_entrada_tributacao	
integer
unidade_entrada_inventario	
integer
taxa_conversao_saida	
number
Taxa de conversão do produto.

taxa_conversao_inventario	
number
Taxa de conversão de entrada do inventário.

taxa_conversao_tributacao	
number
Taxa de conversão de entrada de tributação.

tipo	
string
Default: "N"
Enum: "N" "K" "G"
Indica o tipo de produto: Normal, Kit, Grade.

finalidade	
string
Indica a finalidade principal do produto. 00=Mercadoria para Revenda | 01=Matéria-Prima | 02=Embalagem | 03=Produto em Processo | 04=Produto Acabado | 05=Subproduto | 06=Produto Intermediário | 07=Material de Uso e Consumo | 08=Ativo Imobilizado | 10=Outros Insumos | 99=Outras

cfop	
string
Retorna o CFOP cadastrado no produto no formato X.NNN Ex. X.102

cest	
string = 7 characters
Cest do produto

cst_a	
string
Enum: "0" "1" "2" "3" "4" "5" "6" "7" "8"
Código CST A.

0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 1 - Estrangeira - Importação direta, exceto a indicada no código 6 2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70% 4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam as legislações citadas nos Ajustes 5 - Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% 6 - Estrangeira - Importação direta, sem similar nacional, constante em lista da CAMEX e gás natural 7 - Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista da CAMEX e gás natural 8 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70%

indicador_escala	
string
Enum: "" "S" "N"
Indicador de Escala Relevante

"" - Não informado S - Produzido em Escala Relevante N - Produzido em Escala não Relevante

localizacao_estoque	
string <= 82 characters
Localização do produto no estoque, ao imprimir uma Ordem de Serviço ou Pedido/Orçamento em formato A4, este campo será impresso como observações.

codigo_fornecedor_xml	
boolean
Indica que o produto poderá usar o codígo do fonecedor no XML da Nfe de devolução caso ele tenha sido importado com o codígo maior que 15 digitos.

cnpj_fabricante	
string
CNPJ do fabricante.

cnpj_produtor	
string
CNPJ do produtor.

embalagem	
object
valor_venda_varejo	
number
Valor de venda do tipo Varejo.

custo_utilizado	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

custo_outras_despesas	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

serie	
boolean
Default: false
Indica se a Série ou Selo de garantia do produto deve ser requisitado ao realizar a venda do produto no PDV.

vendido_separado	
boolean
Default: true
false: pode compor um produto tipo kit ou composição, mas não pode ser indicado diretamente em uma movimentação de saída. true: pode compor um produto kit ou composição e também pode ser vendido separadamente.

comercializavel	
boolean
Default: true
Indica se o produto pode ser vendido no PDV.

peso	
number
Peso do produto.

largura	
number
Largura do produto.

altura	
number
Altura do produto.

comprimento	
number
Comprimento do produto.

tipo_producao	
string
Default: ""
Enum: "" "P" "T"
Própria, Terceiros.

observacoes	
string
Informações sobre o produto, entrada de texto livre.

atributos	
Array of objects (Produto Atributo)
Lista de atributos do produto. ex: Marca = Nike

mapa_integracao	
Array of objects (Mapa Integracao)
Lista de sincronização do produto com outras integracoes

produto_integracao	
Array of objects
Lista de ids de integrações vinculadas ao produto

nota_fiscal_entrada	
Array of objects (Produto Nota Compra Vinculada)
Notas fiscais de compra vinculadas ao produto

ajuste_estoque	
Array of objects (Produto Ajuste Estoque Vinculado)
Ajustes de estoque vinculados ao produto

valores_venda	
Array of objects (Valor de Venda)
Lista de valores de venda de um produto.

aliquota_ipi	
number
aliquota_icms	
number
aliquota_pis	
number
aliquota_cofins	
number
aliquota_irpj	
number
aliquota_cpp	
number
aliquota_csll	
number
comissao	
number
comissao_produto	
number
id_pai	
integer
Campo usado para produtos do tipo Grade, quando possuir algum inteiro e tipo do produto igual G, indica que o produto em questão é filho do produto de id igual id_pai.

itens_vinculados	
Array of objects (Item de Kit/Composição)
Detalha os itens de um produto Kit ou Composição. Confira o tipo do produto para determinar se é kit ou composição.

filhos	
Array of objects (Produto)
Filhos do produto, quando este é do tipo grade e principal.

modalidades	
Array of integers
Lista de ids das modalidades vinculadas ao produto.

fornecedores	
Array of integers
Lista de ids de fornecedores do produto.

imagens	
Array of objects (Dados da imagem)
Array de Base64 de imagens para serem salvas no produto.

tributo_ncm	
string <= 8 characters
Código do tributo NCM vinculado ao produto, todos os NCM's podem ser recuperados através do endpoint /tributos_ncm

sincroniza	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

ignorar_estoque	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

valor_oferta	
number
Loja Virtual. Valor Oferta

vender_de	
string
Loja Virtual. Vender a partir da data

vender_ate	
string
Loja Virtual. Vender ate a data

descricao_curta	
string
Loja Virtual. Descrição Curta

descricao_longa	
string
Loja Virtual. Descrição Longa

filtro_grade	
string
Enum: "" "F" "P" "T" "S"
Filtro Opcional valido apenas para listagem. Ele indica quais elementos o sistema deve trazer.

"" - (Padrão) Apenas os pais de grade e outros tipos de produtos. F - Apenas os filhos de grade P - Apenas os pais de grade T - Pais e filhos de grade. S - Pais, filhos de grade e outros tipos de produtos.

criar_composicao	
boolean
Indica se uma composição será criada

desfazer_composicao	
boolean
Indica se uma composição será desfeita

quantidade_composicao	
number
Quantidade de composição que será desfeita ou criada de acordo com o que foi informado nos campos criar_composicao ou desfazer_composicao

Responses
201 Produto criado!

POST
/produtos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"descricao": "string",
"imagem_principal": 0,
"categoria": 0,
"departamento": 0,
"estoque": {
"qtd_revenda": 20,
"qtd_min": 10,
"qtd_max": 10,
"qtd_consumo": 1,
"qtd_imobilizado": 0
},
"qtd_revenda": 0,
"data_validade": "string",
"unidade_entrada": 0,
"unidade_saida": 0,
"unidade_entrada_tributacao": 0,
"unidade_entrada_inventario": 0,
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {
"altura": 0,
"largura": 0,
"comprimento": 0,
"peso": 0
},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [
{}
],
"mapa_integracao": [
{}
],
"produto_integracao": [
{}
],
"nota_fiscal_entrada": [
{}
],
"ajuste_estoque": [
{}
],
"valores_venda": [
{}
],
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [
{}
],
"filhos": [
{}
],
"modalidades": [
0
],
"fornecedores": [
0
],
"imagens": [
{}
],
"tributo_ncm": "string",
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"filtro_grade": "",
"criar_composicao": true,
"desfazer_composicao": true,
"quantidade_composicao": 0
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"codigo": 123456789,
"descricao": "Aparador 350V"
}
Recuperar produto
Recupera o produto detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/produtos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"codigo": 123456789,
"descricao": "Aparador 350V"
}
Editar produto
Altera um produto. Os campos que não forem enviados no corpo serão mantidos.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o produto está ativo, onde ativo=true indica produto ativo.

codigo	
string
Caso não seja fornecido um código interno, o sistema gera um automáticamente

codigo_barras	
string
Código de barras do fabricante do produto. Padrão EAN13

codigo_barras_tributavel	
string [ 8 .. 14 ] characters
Código de barras da unidade do produto (cEAN Trib.). Caso seja preenchido, este campo deve ser um EAN válido e possuir 8, 12,13 ou 14 caracteres. Padrão EAN13

descricao	
string
Descricão/Nome do produto.

imagem_principal	
integer
ID da imagem principal.

categoria	
integer
Campo identificador da categoria do produto, é possível recuperar categorias pelo recurso /categorias, saiba como recuperar categorias do ERP clicando aqui

departamento	
integer
Campo identificador do departamento do produto, é possível recuperar departamentos pelo recurso /departamento, saiba como recuperar departamentos do ERP clicando aqui

estoque	
object (Estoque de Produto)
qtd_revenda	
number
data_validade	
string
Data de validade do produto.

unidade_entrada	
integer
unidade_saida	
integer
unidade_entrada_tributacao	
integer
unidade_entrada_inventario	
integer
taxa_conversao_saida	
number
Taxa de conversão do produto.

taxa_conversao_inventario	
number
Taxa de conversão de entrada do inventário.

taxa_conversao_tributacao	
number
Taxa de conversão de entrada de tributação.

finalidade	
string
Indica a finalidade principal do produto. 00=Mercadoria para Revenda | 01=Matéria-Prima | 02=Embalagem | 03=Produto em Processo | 04=Produto Acabado | 05=Subproduto | 06=Produto Intermediário | 07=Material de Uso e Consumo | 08=Ativo Imobilizado | 10=Outros Insumos | 99=Outras

cfop	
string
Retorna o CFOP cadastrado no produto no formato X.NNN Ex. X.102

cest	
string = 7 characters
Cest do produto

cst_a	
string
Enum: "0" "1" "2" "3" "4" "5" "6" "7" "8"
Código CST A.

0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 1 - Estrangeira - Importação direta, exceto a indicada no código 6 2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70% 4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam as legislações citadas nos Ajustes 5 - Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% 6 - Estrangeira - Importação direta, sem similar nacional, constante em lista da CAMEX e gás natural 7 - Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista da CAMEX e gás natural 8 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70%

indicador_escala	
string
Enum: "" "S" "N"
Indicador de Escala Relevante

"" - Não informado S - Produzido em Escala Relevante N - Produzido em Escala não Relevante

localizacao_estoque	
string <= 82 characters
Localização do produto no estoque, ao imprimir uma Ordem de Serviço ou Pedido/Orçamento em formato A4, este campo será impresso como observações.

codigo_fornecedor_xml	
boolean
Indica que o produto poderá usar o codígo do fonecedor no XML da Nfe de devolução caso ele tenha sido importado com o codígo maior que 15 digitos.

cnpj_fabricante	
string
CNPJ do fabricante.

cnpj_produtor	
string
CNPJ do produtor.

embalagem	
object
valor_venda_varejo	
number
Valor de venda do tipo Varejo.

custo_utilizado	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

custo_outras_despesas	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

serie	
boolean
Default: false
Indica se a Série ou Selo de garantia do produto deve ser requisitado ao realizar a venda do produto no PDV.

vendido_separado	
boolean
Default: true
false: pode compor um produto tipo kit ou composição, mas não pode ser indicado diretamente em uma movimentação de saída. true: pode compor um produto kit ou composição e também pode ser vendido separadamente.

comercializavel	
boolean
Default: true
Indica se o produto pode ser vendido no PDV.

peso	
number
Peso do produto.

largura	
number
Largura do produto.

altura	
number
Altura do produto.

comprimento	
number
Comprimento do produto.

tipo_producao	
string
Default: ""
Enum: "" "P" "T"
Própria, Terceiros.

observacoes	
string
Informações sobre o produto, entrada de texto livre.

atributos	
Array of objects (Produto Atributo)
Lista de atributos do produto. ex: Marca = Nike

mapa_integracao	
Array of objects (Mapa Integracao)
Lista de sincronização do produto com outras integracoes

produto_integracao	
Array of objects
Lista de ids de integrações vinculadas ao produto

nota_fiscal_entrada	
Array of objects (Produto Nota Compra Vinculada)
Notas fiscais de compra vinculadas ao produto

ajuste_estoque	
Array of objects (Produto Ajuste Estoque Vinculado)
Ajustes de estoque vinculados ao produto

valores_venda	
Array of objects (Valor de Venda)
Lista de valores de venda de um produto.

aliquota_ipi	
number
aliquota_icms	
number
aliquota_pis	
number
aliquota_cofins	
number
aliquota_irpj	
number
aliquota_cpp	
number
aliquota_csll	
number
comissao	
number
comissao_produto	
number
id_pai	
integer
Campo usado para produtos do tipo Grade, quando possuir algum inteiro e tipo do produto igual G, indica que o produto em questão é filho do produto de id igual id_pai.

itens_vinculados	
Array of objects (Item de Kit/Composição)
Detalha os itens de um produto Kit ou Composição. Confira o tipo do produto para determinar se é kit ou composição.

filhos	
Array of objects (Produto)
Filhos do produto, quando este é do tipo grade e principal.

modalidades	
Array of integers
Lista de ids das modalidades vinculadas ao produto.

fornecedores	
Array of integers
Lista de ids de fornecedores do produto.

imagens	
Array of objects (Dados da imagem)
Array de Base64 de imagens para serem salvas no produto.

tributo_ncm	
string <= 8 characters
Código do tributo NCM vinculado ao produto, todos os NCM's podem ser recuperados através do endpoint /tributos_ncm

sincroniza	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

ignorar_estoque	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

valor_oferta	
number
Loja Virtual. Valor Oferta

vender_de	
string
Loja Virtual. Vender a partir da data

vender_ate	
string
Loja Virtual. Vender ate a data

descricao_curta	
string
Loja Virtual. Descrição Curta

descricao_longa	
string
Loja Virtual. Descrição Longa

filtro_grade	
string
Enum: "" "F" "P" "T" "S"
Filtro Opcional valido apenas para listagem. Ele indica quais elementos o sistema deve trazer.

"" - (Padrão) Apenas os pais de grade e outros tipos de produtos. F - Apenas os filhos de grade P - Apenas os pais de grade T - Pais e filhos de grade. S - Pais, filhos de grade e outros tipos de produtos.

criar_composicao	
boolean
Indica se uma composição será criada

desfazer_composicao	
boolean
Indica se uma composição será desfeita

quantidade_composicao	
number
Quantidade de composição que será desfeita ou criada de acordo com o que foi informado nos campos criar_composicao ou desfazer_composicao

Responses
200 Produto alterado!

PATCH
/produtos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"descricao": "string",
"imagem_principal": 0,
"categoria": 0,
"departamento": 0,
"estoque": {
"qtd_revenda": 20,
"qtd_min": 10,
"qtd_max": 10,
"qtd_consumo": 1,
"qtd_imobilizado": 0
},
"qtd_revenda": 0,
"data_validade": "string",
"unidade_entrada": 0,
"unidade_saida": 0,
"unidade_entrada_tributacao": 0,
"unidade_entrada_inventario": 0,
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {
"altura": 0,
"largura": 0,
"comprimento": 0,
"peso": 0
},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [
{}
],
"mapa_integracao": [
{}
],
"produto_integracao": [
{}
],
"nota_fiscal_entrada": [
{}
],
"ajuste_estoque": [
{}
],
"valores_venda": [
{}
],
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [
{}
],
"filhos": [
{}
],
"modalidades": [
0
],
"fornecedores": [
0
],
"imagens": [
{}
],
"tributo_ncm": "string",
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"filtro_grade": "",
"criar_composicao": true,
"desfazer_composicao": true,
"quantidade_composicao": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"codigo": 123456789,
"descricao": "Aparador 350V"
}
Apagar produto
Apaga o produto especificado.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Produto apagado!

DELETE
/produtos/{id}
Recuperar imagens do produto
Recupera imagens de um produto

Responses
200 Sucesso!

GET
/produtos/imagens/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
]
Salvar uma imagem do produto
Permite salvar uma imagem, indicando se ela é principal ou não.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
extensao
required
string
base64
required
string
id	
string
principal	
boolean
Responses
201 Imagem salva!

POST
/produtos/imagens/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"base64": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
Altera imagem principal do produto
Permite alterar a imagem principal do produto.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id
required
string
extensao
required
string
principal	
boolean
base64	
string
Responses
201 Imagem alterada com sucesso!

PATCH
/produtos/imagens/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"base64": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
Apagar uma imagem do produto
Apaga uma imagem de um produto.

QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo

Responses
200 Imagem Apagada apagado!

DELETE
/produtos/imagens/{id}
Imprimir log de produtos
'Imprimir log de Produtos'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna o log dos produtos no formato PDF

POST
/produtos/pdf/log
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Tabela de preços dos produtos
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna a tabela de preços de produtos no formato PDF

POST
/produtos/pdf/tabela_precos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Tabela de produtos Kit e Composição
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna a tabela de produtos Kit e Composição no formato PDF

POST
/produtos/pdf/kit_composicao
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Tabela de Movimentação Manual
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna a tabela de Movimentação Manual de produtos no formato PDF

POST
/produtos/pdf/movimentacao_manual
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Tabela de Inventário Atual
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Invetário Atual de produtos no formato PDF

POST
/produtos/pdf/inventario_atual
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Recupera o valor de despesas acessórias do produto
Responses
200 Valor de despesas acessórias buscado com sucesso!

GET
/produtos/valor_despesas_acessorias/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"valor_despesas_acessorias": 0
}
Planilha de produtos
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
trazer_grades	
boolean
Se deve trazer as grades na planilha.

toda_listagem	
boolean
Se deve trazer toda a planilha de itens, sem limite de itens.

Responses
200 Retorna a tabela de produtos no formato de Excel

POST
/produtos/planilha_produtos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"trazer_grades": true,
"toda_listagem": true
}
Recupera informações e código de barras(EAN) do produto
QUERY PARAMETERS
codigo	
string
Código de barras do produto

Responses
200 Recupera código de barras

GET
/produtos/codigo_barras
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"descricao_produto": "string",
"cod_ncm": "string",
"codigo_barra": 0,
"tipo_mercadoria": "string",
"mercadoria": "string"
}
]
Atualiza valor de custo de todos os produtos
Responses
200 Sucesso!

PATCH
/produtos/atualiza_custo
Produtos | Resumo Estoque Mínimo e Negativo
Responses
200 Sucesso!

GET
/dashboard/produtos/estoque
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"estoque_minimo": 0,
"estoque_negativo": 0
}
]
Produtos | Mais vendidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/produtos/produtos_mais_vendidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"valor": 0,
"valor_produto_vendido": 0,
"quantidade": 0
}
]
Produtos | Menos vendidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/produtos/produtos_menos_vendidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"valor": 0,
"valor_produto_vendido": 0,
"quantidade": 0
}
]
clientes
Listar clientes
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/clientes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
}
]
Criar cliente
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
razao_social
required
string >= 3 characters
Nome do cliente quando pessoa física e razão social quando pessoa jurídica.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o cliente está ativo.

codigo	
string
Código que identifica unicamente o cliente. Não deve repetir em outro cliente.

categoria	
integer
tipo	
string
Default: "F"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

exterior	
boolean
Default: false
Indica a origem do cliente: false para nacional e true para estrangeira.

cpf	
string
Número de CPF. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

identidade_estrangeiro	
string
Número do passaporte ou outro documento legal de identificação.Informe somente se origem do cliente for estrangeira.

nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

ie	
string
Número de Inscrição Estadual.

im	
string
Número de Inscrição Municipal. Informe somente se pessoa jurídica.

indicador_ie	
boolean
Indica se a IE (Inscrição Estadual) é classificada como 'Não Contribuinte'

responsavel	
string
Nome do responsável da empresa. Informe somente se pessoa jurídica.

suframa	
string
Número SUFRAMA. Informe somente se pessoa jurídica.

rg	
string
Registro Geral. Informe somente se pessoa física.

data_nascimento	
string
Data de nascimento do cliente. Informe somente se pessoa física.

sexo	
string
Enum: "" "M" "F"
profissao	
string
Profissão exercida pelo cliente. Informe somente se pessoa física.

filiacao_mae	
string
Nome da mãe. Informe somente se pessoa física.

filiacao_pai	
string
Nome do pai. Informe somente se pessoa física.

conjuge_nome	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

conjuge_cpf	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

conjuge_data_nascimento	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

conjuge_profissao	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

estado_civil	
string
Enum: "" "S" "C" "D" "V"
Estado civil do cliente. Informe somente se pessoa física.

renda_mensal	
number
Renda aproximada por mês. Informe somente se pessoa física.

recebe_email	
boolean
Default: true
Informa se o cliente deve receber e-mails automáticos quando decorrente de algum evento no ERP. Um exemplo é o envio da NF-e para o destinatário quando ela é aprovada.

limite_credito	
number
Valor que o cliente terá de limite de crédito. Também altera o valor do saldo do cliente de acordo com os lançamentos financeiros do cliente (saldo = limite_credito caso não tenha lançamentos)

informacao_adicional	
string
Coloque aqui as informações importantes que não tem um campo específico.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

vendedores	
Array of integers
Lista de ids de vendedores que serão vinculados ao cliente.

tributo_ncm	
Array of objects
Lista de tributos NCM vinculado ao cliente

saldo_devedor	
object
Retorna o saldo devedor do cliente

extras	
object
Campo de uso interno. É possível vincular uma forma de pagamento ao cliente passando um objeto: { "id_forma_pagamento": 8 }

Responses
201 Cliente criado!

POST
/clientes
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"ativo": true,
"codigo": "string",
"categoria": 0,
"tipo": "F",
"exterior": false,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"razao_social": "string",
"nome_fantasia": "string",
"ie": "string",
"im": "string",
"indicador_ie": true,
"responsavel": "string",
"suframa": "string",
"rg": "string",
"data_nascimento": "string",
"sexo": "",
"profissao": "string",
"filiacao_mae": "string",
"filiacao_pai": "string",
"conjuge_nome": "string",
"conjuge_cpf": "string",
"conjuge_data_nascimento": "string",
"conjuge_profissao": "string",
"estado_civil": "",
"renda_mensal": 0,
"recebe_email": true,
"limite_credito": 0,
"informacao_adicional": "string",
"contatos": [
{}
],
"enderecos": [
{}
],
"vendedores": [
0
],
"tributo_ncm": [
{}
],
"saldo_devedor": {
"nao_confirmado_vencido": {},
"nao_confirmado_nao_vencido": {},
"confirmado": {}
},
"extras": { }
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
}
Recuperar cliente
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/clientes/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
}
Editar cliente
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o cliente está ativo.

codigo	
string
Código que identifica unicamente o cliente. Não deve repetir em outro cliente.

categoria	
integer
tipo	
string
Default: "F"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

exterior	
boolean
Default: false
Indica a origem do cliente: false para nacional e true para estrangeira.

cpf	
string
Número de CPF. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

identidade_estrangeiro	
string
Número do passaporte ou outro documento legal de identificação.Informe somente se origem do cliente for estrangeira.

razao_social	
string >= 3 characters
Nome do cliente quando pessoa física e razão social quando pessoa jurídica.

nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

ie	
string
Número de Inscrição Estadual.

im	
string
Número de Inscrição Municipal. Informe somente se pessoa jurídica.

indicador_ie	
boolean
Indica se a IE (Inscrição Estadual) é classificada como 'Não Contribuinte'

responsavel	
string
Nome do responsável da empresa. Informe somente se pessoa jurídica.

suframa	
string
Número SUFRAMA. Informe somente se pessoa jurídica.

rg	
string
Registro Geral. Informe somente se pessoa física.

data_nascimento	
string
Data de nascimento do cliente. Informe somente se pessoa física.

sexo	
string
Enum: "" "M" "F"
profissao	
string
Profissão exercida pelo cliente. Informe somente se pessoa física.

filiacao_mae	
string
Nome da mãe. Informe somente se pessoa física.

filiacao_pai	
string
Nome do pai. Informe somente se pessoa física.

conjuge_nome	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

conjuge_cpf	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

conjuge_data_nascimento	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

conjuge_profissao	
string
Nome do Conjuge. Informe somente se pessoa física, e estado civil 'Casado'

estado_civil	
string
Enum: "" "S" "C" "D" "V"
Estado civil do cliente. Informe somente se pessoa física.

renda_mensal	
number
Renda aproximada por mês. Informe somente se pessoa física.

recebe_email	
boolean
Default: true
Informa se o cliente deve receber e-mails automáticos quando decorrente de algum evento no ERP. Um exemplo é o envio da NF-e para o destinatário quando ela é aprovada.

limite_credito	
number
Valor que o cliente terá de limite de crédito. Também altera o valor do saldo do cliente de acordo com os lançamentos financeiros do cliente (saldo = limite_credito caso não tenha lançamentos)

informacao_adicional	
string
Coloque aqui as informações importantes que não tem um campo específico.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

vendedores	
Array of integers
Lista de ids de vendedores que serão vinculados ao cliente.

tributo_ncm	
Array of objects
Lista de tributos NCM vinculado ao cliente

saldo_devedor	
object
Retorna o saldo devedor do cliente

extras	
object
Campo de uso interno. É possível vincular uma forma de pagamento ao cliente passando um objeto: { "id_forma_pagamento": 8 }

Responses
200 Cliente alterado!

PATCH
/clientes/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"ativo": true,
"codigo": "string",
"categoria": 0,
"tipo": "F",
"exterior": false,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"razao_social": "string",
"nome_fantasia": "string",
"ie": "string",
"im": "string",
"indicador_ie": true,
"responsavel": "string",
"suframa": "string",
"rg": "string",
"data_nascimento": "string",
"sexo": "",
"profissao": "string",
"filiacao_mae": "string",
"filiacao_pai": "string",
"conjuge_nome": "string",
"conjuge_cpf": "string",
"conjuge_data_nascimento": "string",
"conjuge_profissao": "string",
"estado_civil": "",
"renda_mensal": 0,
"recebe_email": true,
"limite_credito": 0,
"informacao_adicional": "string",
"contatos": [
{}
],
"enderecos": [
{}
],
"vendedores": [
0
],
"tributo_ncm": [
{}
],
"saldo_devedor": {
"nao_confirmado_vencido": {},
"nao_confirmado_nao_vencido": {},
"confirmado": {}
},
"extras": { }
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
}
Apagar cliente
Apaga um cliente específico pelo id. Se o cliente possuir movimentações não será deletado, será necessário um PATCH enviando campo 'ativo' como 'false'.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/clientes/{id}
Listar categoria de clientes
Responses
200 Sucesso!

GET
/clientes/categorias
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"categoria_mae": {},
"descricao": "string"
}
]
Criar categoria de cliente
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
categoria_mae	
integer
Responses
201 Categoria de cliente criado!

POST
/clientes/categorias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Recuperar categoria de cliente
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/clientes/categorias/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Editar categoria de cliente
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
categoria_mae	
integer
descricao	
string
Responses
200 Categoria de cliente alterado!

PATCH
/clientes/categorias/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Apagar uma categoria de cliente
Apaga uma categoria de cliente específica pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/clientes/categorias/{id}
Listar vales do cliente
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/clientes/vales/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"vales": [
{}
],
"saldo_total": 0
}
Imprimir Fichas de cadastro de Clientes
'Imprimir Fichas de cadastro de Clientes'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
pdf_unico	
boolean
Se true, indica que será gerado um único arquivo PDF. Se false cada arquivo será gerado separadamente e retornado em um arquivo .zip.

Responses
200 Retorna Listagem de Ficha de cadastros de clientes no formato PDF

POST
/clientes/pdf/ficha_cadastro
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"pdf_unico": true
}
Imprimir Listagem de Clientes
'Imprimir Listagem de Clientes'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de clientes no formato PDF

POST
/clientes/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Gera listagem de clientes em excel
'Gerar Listagem de Clientes em Excel'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Clientes no Formato XLS

POST
/clientes/excel/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Listar email principal e razao social de clientes
Responses
200 Sucesso!

GET
/clientes/listar_emails
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"razao_social": "string",
"email": "string"
}
]
Gerar Historico de compras
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id	
number
Id do cliente.

tipo_exportacao	
string
Default: "D"
Enum: "D" "E"
Tipo de exportação D realiza download ou E envia por email.

emails	
Array of strings
Responses
200 Historico de compras gerado com sucesso.

POST
/clientes/historico_compras
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo_exportacao": "D",
"emails": [
"string"
]
}
Listar notas e outros
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/clientes/notas_e_outros/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"notas": [
{}
],
"contratos": [
{ }
],
"pre_vendas": [
{}
]
}
Imprime ou envia por email saldo devedor do cliente
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id	
number
Id do cliente.

tipo_exportacao	
string
Default: "D"
Enum: "D" "E"
Tipo de exportação D realiza download ou E envia por email.

emails	
Array of strings
cred_nao_confirmado_vencido	
boolean
Créditos não Confirmados e Vencidos

cred_nao_confirmado_nao_vencido	
boolean
Créditos não Confirmados e não Vencidos

cred_confirmado	
boolean
Créditos já Confirmados

somar_multa_atraso	
boolean
Responses
200 Sucesso!

POST
/clientes/saldo_devedor
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo_exportacao": "D",
"emails": [
"string"
],
"cred_nao_confirmado_vencido": true,
"cred_nao_confirmado_nao_vencido": true,
"cred_confirmado": true,
"somar_multa_atraso": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"ativo": true,
"codigo": "C3PO",
"tipo": "J",
"razao_social": "João da Silva",
"exterior": false,
"cpf": "999.999.999"
}
]
Recuperar tributacao de cliente
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/clientes/tributacoes/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"ncm": "string",
"descricao": "string",
"tributo_detalhe": {}
}
]
Clientes | Melhores Compradores por Quantidade
QUERY PARAMETERS
data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/clientes/melhores_compradores_qtd
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"total": 0,
"razao_social": "string"
}
]
Clientes | Evolução de Clientes
QUERY PARAMETERS
data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Agrupar-Semana	
boolean
Gera agrupamento do objeto de resposta com relação a semana.

X-Agrupar-Mes	
boolean
Gera agrupamento do objeto de resposta com relação a mes.

X-Agrupar-Ano	
boolean
Gera agrupamento do objeto de resposta com relação a ano.

Responses
200 Sucesso!

GET
/dashboard/clientes/evolucao_clientes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"quantidade": 0,
"quantidade_media": 0
}
]
empresas
Recupera empresa pelo ID.
Esse recurso recupera dados da sua empresa, para usa-lo, indique o id. Por padrão, os dados encontrados no menu do ERP Dados da sua empresa são recuperados no id 1 ou use a string "me" ex: GET /empresas/1 ou GET /empresas/me

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/empresas/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "F",
"ie": "string",
"ie_adicionais": [
{}
],
"im": "string",
"data_alteracao": "string",
"cpf": "string",
"cnpj": "string",
"plano": {
"id": 0,
"nome": "string",
"blacklist": []
},
"suframa": "string",
"razao_social": "string",
"nome_fantasia": "string",
"responsavel": "string",
"rg": "string",
"contatos": [
{}
],
"enderecos": [
{}
],
"data_abertura": "2019-08-24",
"tipo_atividade": "I",
"regime_tributario": 1,
"regime_especial_servicos": 0,
"incentivador_cultural": true,
"certificado_a1": true,
"cnaes": [
{}
],
"uid": "string",
"ws_user": "string",
"ws_pass": "string",
"versao_pdv": "string",
"versao_nfe": "string",
"versao_nfse": "string",
"layout_padrao": true,
"aliquota_padrao": 0,
"imagem_principal": {
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
}
Editar empresa
Atualiza as informações da empresa.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
tipo	
string
Default: "F"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

ie	
string
Número de Inscrição Estadual.

ie_adicionais	
Array of objects (IE's adicionais)
Inscrições estaduais adicionais.

im	
string
Número de Inscrição Municipal. Informe somente se pessoa jurídica.

cpf	
string
Número de CPF. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

suframa	
string
razao_social	
string
Nome do cliente quando pessoa física e razão social quando pessoa jurídica.

nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

responsavel	
string
Nome do responsável da empresa. Informe somente se pessoa jurídica.

rg	
string
Registro Geral. Informe somente se pessoa física.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

data_abertura	
string <date>
Data de abertura da empresa.

tipo_atividade	
string
Enum: "I" "O"
Tipo de Atividade da empresa. Indica se a empresa é contribuinte do IPI ou não I=Indústria/Importador O=Outros - Não Industrial

regime_tributario	
integer
Enum: 1 2 3 4
Código de Regime Tributário da empresa. 1=Simples Nacional 2=Simples Nacional – excesso de sublimite de receita bruta 3=Regime Normal 4=Simples Nacional – Microempreendedor Individual - MEI"

regime_especial_servicos	
integer
Enum: 0 1 2 3 4 5 6
Regime Especial de Tributação da empresa. Necessário para a NFS-e. 0=Não possuo 1=Microempresa Municipal 2=Estimativa 3=Sociedade de Profissionais 4=Cooperativa 5=MEI – Simples Nacional 6=ME EPP – Simples Nacional

incentivador_cultural	
boolean
Incentivador Cultural

certificado_a1	
boolean
Identifica se certificado é A1

cnaes	
Array of objects (Contato)
Cadastro dos CNAE's.

uid	
string
Identificador único do ERP.

layout_padrao	
boolean
Ao habilitar esta opção, o campo para informação de interesse do contribuinte será preenchido com o layout padrão do sistema, substituindo o texto indicado na aba Nota Fiscal das Configurações do Sistema

aliquota_padrao	
number
Valor que será preenchido no texto padrão para informação de interesse do contribuinte

Responses
200 Empresa alterada!

PATCH
/empresas/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"tipo": "F",
"ie": "string",
"ie_adicionais": [
{}
],
"im": "string",
"cpf": "string",
"cnpj": "string",
"suframa": "string",
"razao_social": "string",
"nome_fantasia": "string",
"responsavel": "string",
"rg": "string",
"contatos": [
{}
],
"enderecos": [
{}
],
"data_abertura": "2019-08-24",
"tipo_atividade": "I",
"regime_tributario": 1,
"regime_especial_servicos": 0,
"incentivador_cultural": true,
"certificado_a1": true,
"cnaes": [
{}
],
"uid": "string",
"layout_padrao": true,
"aliquota_padrao": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"tipo": "F",
"ie": "string",
"ie_adicionais": [
{}
],
"im": "string",
"data_alteracao": "string",
"cpf": "string",
"cnpj": "string",
"plano": {
"id": 0,
"nome": "string",
"blacklist": []
},
"suframa": "string",
"razao_social": "string",
"nome_fantasia": "string",
"responsavel": "string",
"rg": "string",
"contatos": [
{}
],
"enderecos": [
{}
],
"data_abertura": "2019-08-24",
"tipo_atividade": "I",
"regime_tributario": 1,
"regime_especial_servicos": 0,
"incentivador_cultural": true,
"certificado_a1": true,
"cnaes": [
{}
],
"uid": "string",
"ws_user": "string",
"ws_pass": "string",
"versao_pdv": "string",
"versao_nfe": "string",
"versao_nfse": "string",
"layout_padrao": true,
"aliquota_padrao": 0,
"imagem_principal": {
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
}
Salvar um CNAE para a empresa
Permite salvar um CNAE.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
cod
required
string >= 2 characters
Código do CNAE.

descricao
required
string >= 2 characters
Descrição do CNAE.

cod_trib_municipio	
string
Código tributário do municipio.

Responses
201 CNAE salvo!

POST
/empresas/cnae
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"cod": "string",
"cod_trib_municipio": "string",
"descricao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"cod": "string",
"cod_trib_municipio": "string",
"descricao": "string",
"id": "string",
"principal": "string",
"id_empresa": "string"
}
Recuperar imagens da empresa
Recupera imagens de um empresa

Responses
200 Sucesso!

GET
/empresas/imagens/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
]
Salvar uma imagem da empresa
Permite salvar uma imagem, indicando se ela é principal ou não.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
extensao
required
string
base64
required
string
id	
string
principal	
boolean
Responses
201 Imagem salva!

POST
/empresas/imagens/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"base64": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
Altera imagem principal da empresa
Permite alterar a imagem principal da empresa.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id
required
string
extensao
required
string
principal	
boolean
base64	
string
Responses
200 Imagem alterada com sucesso!

PATCH
/empresas/imagens/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"base64": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": "string",
"principal": true,
"extensao": "string",
"url": "string",
"base64": "string"
}
Apagar uma imagem da empresa
Apaga uma imagem de um empresa.

Responses
200 Imagem Apagada apagada!

DELETE
/empresas/imagens/{id}
fornecedores
Listar fornecedores
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/fornecedores
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"razao_social": "OAS Swagger"
}
]
Criar fornecedor
Cria um novo fornecedor no sistema.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
razao_social
required
string
Nome do cliente quando pessoa física e razão social quando pessoa jurídica.

id_entidade	
integer
ID para utilização interna.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

categoria	
integer
nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

fabricante	
boolean
Default: false
Indica se o fornecedor é fabricante do produto fornecido.

im	
string
Número de Inscrição Municipal. Informe somente se pessoa jurídica.

informacao_adicional	
string
Coloque aqui as informações importantes que não tem um campo específico.

crt	
integer
Código de Regime Tributário.

recebe_email	
boolean
Default: true
Informa se o fornecedor deve receber e-mails automáticos quando decorrente de algum evento no ERP. Um exemplo é o envio da NF-e para o destinatário quando ela é aprovada.

ramo_atividade	
string
Descrição do ramo de atividade.

responsavel	
string
Nome do responsável.

cpf	
string
Número de CPF. Informe somente se pessoa física.

rg	
string
Número do RG. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

identidade_estrangeiro	
string
Número de identidade de pessoa estrangeira. Informe somente se for estrangeiro.

ie	
string
Número de Inscrição Estadual.

ativo	
boolean
Default: true
Indica se o fornecedor está ativo.

exterior	
boolean
Default: false
Indica a origem do fornecedor: false para nacional e true para estrangeira.

tipo	
string
Default: "J"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

Responses
201 Fornecedor criado!

POST
/fornecedores
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_entidade": 0,
"codigo_externo": "string",
"categoria": 0,
"nome_fantasia": "string",
"razao_social": "string",
"fabricante": false,
"im": "string",
"informacao_adicional": "string",
"crt": 0,
"recebe_email": true,
"ramo_atividade": "string",
"responsavel": "string",
"cpf": "string",
"rg": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"razao_social": "OAS Swagger"
}
Recuperar fornecedor
Recupera o fornecedor específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/fornecedores/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"razao_social": "OAS Swagger"
}
Editar fornecedor
Altera parcialmente os dados de um fornecedor.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id_entidade	
integer
ID para utilização interna.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

categoria	
integer
nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

razao_social	
string
Nome do cliente quando pessoa física e razão social quando pessoa jurídica.

fabricante	
boolean
Default: false
Indica se o fornecedor é fabricante do produto fornecido.

im	
string
Número de Inscrição Municipal. Informe somente se pessoa jurídica.

informacao_adicional	
string
Coloque aqui as informações importantes que não tem um campo específico.

crt	
integer
Código de Regime Tributário.

recebe_email	
boolean
Default: true
Informa se o fornecedor deve receber e-mails automáticos quando decorrente de algum evento no ERP. Um exemplo é o envio da NF-e para o destinatário quando ela é aprovada.

ramo_atividade	
string
Descrição do ramo de atividade.

responsavel	
string
Nome do responsável.

cpf	
string
Número de CPF. Informe somente se pessoa física.

rg	
string
Número do RG. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

identidade_estrangeiro	
string
Número de identidade de pessoa estrangeira. Informe somente se for estrangeiro.

ie	
string
Número de Inscrição Estadual.

ativo	
boolean
Default: true
Indica se o fornecedor está ativo.

exterior	
boolean
Default: false
Indica a origem do fornecedor: false para nacional e true para estrangeira.

tipo	
string
Default: "J"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

Responses
200 Fornecedor alterado!

PATCH
/fornecedores/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_entidade": 0,
"codigo_externo": "string",
"categoria": 0,
"nome_fantasia": "string",
"razao_social": "string",
"fabricante": false,
"im": "string",
"informacao_adicional": "string",
"crt": 0,
"recebe_email": true,
"ramo_atividade": "string",
"responsavel": "string",
"cpf": "string",
"rg": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"razao_social": "OAS Swagger"
}
Apagar fornecedor
Apaga um fornecedor específico pelo id. Se o fornecedor possui movimentações não será apagado, será necessário um PATCH enviando campo 'ativo' como 'false'.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Fornecedor apagado!

DELETE
/fornecedores/{id}
Listar categoria de fornecedores
Responses
200 Sucesso!

GET
/fornecedores/categorias
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"categoria_mae": {},
"descricao": "string"
}
]
Criar categoria de fornecedor
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
categoria_mae	
integer
Responses
201 Categoria de fornecedor criado!

POST
/fornecedores/categorias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Listar email principal e razao social de fornecedores
Responses
200 Sucesso!

GET
/fornecedores/listar_emails
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"razao_social": "string",
"email": "string"
}
]
Gera listagem de fornecedores em excel
'Gerar Listagem de Fornecedores em Excel'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Fornecedores no Formato XLS

POST
/fornecedores/excel/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Gera listagem de fornecedores em PDF
'Gerar Listagem de Fornecedores em PDF'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Fornecedores no Formato PDF

POST
/fornecedores/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Recuperar categoria de fornecedor
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/fornecedores/categorias/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Editar categoria de fornecedor
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
categoria_mae	
integer
descricao	
string
Responses
200 Categoria de fornecedor alterado!

PATCH
/fornecedores/categorias/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Apagar uma categoria de fornecedor
Apaga uma categoria de fornecedor específica pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/fornecedores/categorias/{id}
Vincular produto ao fornecedor
Vincula produtos à fornecedores

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id_fornecedor	
integer
id_produto	
Array of integers
Responses
201 Vínculo criado!

POST
/fornecedores/vincular_produto
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_fornecedor": 0,
"id_produto": [
0
]
}
Desvincular produtos do fornecedor
Desvincula produtos do fornecedor

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id_fornecedor	
integer
id_produto	
Array of integers
Responses
201 Desvinculado com sucesso!

POST
/fornecedores/desvincular_produto
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id_fornecedor": 0,
"id_produto": [
0
]
}
Listar produtos do fornecedor
Recupera todos produtos vinculados ao fornecedor.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/fornecedores/produtos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo": 123456789,
"descricao": "Aparador 350V"
}
]
transportadoras
Listar transportadoras
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/transportadoras
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"categoria": {},
"nome_fantasia": "string",
"razao_social": "string",
"email": "string",
"telefone": "string",
"data_criacao": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [],
"enderecos": [],
"anexos": [],
"possui_vinculo": true
}
]
Criar transportadora
Cria uma transportadora

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
razao_social
required
string
Nome da transportadora quando pessoa física e razão social quando pessoa jurídica.

tipo
required
string
Default: "J"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

categoria	
integer
nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

informacao_adicional	
string
Coloque aqui as informações importantes que não tem um campo específico.

recebe_email	
boolean
Default: true
Informa se o fornecedor deve receber e-mails automáticos quando decorrente de algum evento no ERP. Um exemplo é o envio da NF-e para o destinatário quando ela é aprovada.

cpf	
string
Número de CPF. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

identidade_estrangeiro	
string
Número de identidade de pessoa estrangeira. Informe somente se for estrangeiro.

ie	
string
Número de Inscrição Estadual.

ativo	
boolean
Default: true
Indica se o fornecedor está ativo.

exterior	
boolean
Default: false
Indica a origem do fornecedor: false para nacional e true para estrangeira.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

Responses
201 Transportadora criada!

POST
/transportadoras
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"categoria": 0,
"nome_fantasia": "string",
"razao_social": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"nome_fantasia": "string",
"razao_social": "string",
"email": "string",
"telefone": "string",
"data_criacao": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
],
"anexos": [
"string"
],
"possui_vinculo": true
}
Recuperar transportadora
Recupera a transportadora específica pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/transportadoras/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"nome_fantasia": "string",
"razao_social": "string",
"email": "string",
"telefone": "string",
"data_criacao": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
],
"anexos": [
"string"
],
"possui_vinculo": true
}
Apagar transportadora
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Transportadora apagada!

DELETE
/transportadoras/{id}
Editar transportadora
Atualiza as informações da transportadora.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
categoria	
integer
nome_fantasia	
string
Nome informal. Informe somente se pessoa jurídica.

razao_social	
string
Nome da transportadora quando pessoa física e razão social quando pessoa jurídica.

informacao_adicional	
string
Coloque aqui as informações importantes que não tem um campo específico.

recebe_email	
boolean
Default: true
Informa se o fornecedor deve receber e-mails automáticos quando decorrente de algum evento no ERP. Um exemplo é o envio da NF-e para o destinatário quando ela é aprovada.

cpf	
string
Número de CPF. Informe somente se pessoa física.

cnpj	
string
Número de CNPJ. Informe somente se pessoa jurídica.

identidade_estrangeiro	
string
Número de identidade de pessoa estrangeira. Informe somente se for estrangeiro.

ie	
string
Número de Inscrição Estadual.

ativo	
boolean
Default: true
Indica se o fornecedor está ativo.

exterior	
boolean
Default: false
Indica a origem do fornecedor: false para nacional e true para estrangeira.

tipo	
string
Default: "J"
Enum: "F" "J"
Indicação de pessoa Física ou Jurídica.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

Responses
200 Transportadora alterada!

PATCH
/transportadoras/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"categoria": 0,
"nome_fantasia": "string",
"razao_social": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"nome_fantasia": "string",
"razao_social": "string",
"email": "string",
"telefone": "string",
"data_criacao": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"identidade_estrangeiro": "string",
"ie": "string",
"ativo": true,
"exterior": false,
"tipo": "F",
"contatos": [
{}
],
"enderecos": [
{}
],
"anexos": [
"string"
],
"possui_vinculo": true
}
Listar categoria de transportadoras
Responses
200 Sucesso!

GET
/transportadoras/categorias
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"categoria_mae": {},
"descricao": "string"
}
]
Criar categoria de transportadora
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
categoria_mae	
integer
Responses
201 Categoria de transportadora criado!

POST
/transportadoras/categorias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Recuperar categoria de transportadora
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/transportadoras/categorias/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Editar categoria de transportadora
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
categoria_mae	
integer
descricao	
string
Responses
200 Categoria de transportadora alterado!

PATCH
/transportadoras/categorias/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Apagar uma categoria de transportadora
Apaga uma categoria de transportadora específica pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/transportadoras/categorias/{id}
usuarios
Listar usuários
HEADER PARAMETERS
X-Usuario-Suporte	
boolean
Example: true
Se verdadeiro, retorna usuário suporte no get collection

Responses
200 Sucesso!

GET
/usuarios
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
}
]
Criar usuário
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome
required
string
Nome do usuário do sistema, podendo esse ser por exemplo: um vendedor ou funcionario responsável, gerente, etc..."

ativo
required
boolean
Indica se o usuário é um usuário ativo quando true.

perfil_acesso
required
integer
login
required
string
senha
required
string [ 6 .. 100 ] characters
departamento
required
integer
ID do departamento

data_alteracao	
string
Data em que os dados do usuário foram alterados pela última vez.

sexo	
string
Enum: "M" "F"
cpf	
string
CPF do usuário

cnpj	
string
Campo específico para sistemas de parceiros

categoria	
integer
outros	
object
opcoes	
object
observacoes	
string
rg	
string
data_nascimento	
string <date>
escolaridade	
integer
Enum: 0 1 2 3 4 5
0 - Ensino Fundamental Incompleto

1 - Ensino Fundamental Completo

2 - Ensino Médio Incompleto

3 - Ensino Médio Completo

4 - Ensino Superior Incompleto

5 - Ensino Superior Completo

data_admissao	
string <date>
data_demissao	
string <date>
descanso_semanal	
string
ctps	
string
salario	
number
Cadastro do salário do funcionario.

tipo_conta	
integer
Enum: 0 1 2
0 - Conta Corrente

1 - Conta Poupança

2 - Conta Salário

banco_agencia	
string
banco_conta	
string
banco_numero	
string
comissao	
number
desconto_maximo_permitido	
number
hora_entrada	
string
hora_saida	
string
hora_almoco_entrada	
string
hora_almoco_saida	
string
enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

clientes	
Array of integers
Array de id's de clientes aos quais o usuário tem permissão para efetuar vendas.

dependentes	
Array of objects (Dependente)
parceria	
boolean
Responses
201 Usuário criado!

POST
/usuarios
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": 0,
"departamento": 0,
"categoria": 0,
"login": "string",
"senha": "string",
"outros": {
"tempo_maximo_inatividade": "string",
"dia_acesso": "string",
"vendas_restritas": "string",
"aba_principal": 0
},
"opcoes": {
"visualizar_informacoes_inicial": true,
"visualizar_painel_informacoes": true,
"visualizar_dashboard": true,
"visualizar_todos_funcionarios": true
},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [
{}
],
"contatos": [
{}
],
"clientes": [
0
],
"dependentes": [
{}
],
"parceria": true
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {
"id": 0,
"perfil": "string",
"opcoes_erp": "string"
},
"departamento": {
"id": 0,
"descricao": "string"
},
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"login": "string",
"senha": "string",
"outros": {
"tempo_maximo_inatividade": "string",
"dia_acesso": "string",
"vendas_restritas": "string",
"aba_principal": 0
},
"opcoes": {
"visualizar_informacoes_inicial": true,
"visualizar_painel_informacoes": true,
"visualizar_dashboard": true,
"visualizar_todos_funcionarios": true,
"grafico_vol_vendas": true,
"grafico_faturamento": true,
"grafico_saldo_financeiro": true,
"atividades_recentes": true,
"resumos": true,
"grafico_financ_mes": true
},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [
{}
],
"contatos": [
{}
],
"clientes": [
{}
],
"permissoes": [
"string"
],
"dependentes": [
{}
],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [
"string"
],
"parceria": true
}
Recuperar usuário
Recupera um usuário.

PATH PARAMETERS
id
required
integer
Responses
200 Sucesso!

GET
/usuarios/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {
"id": 0,
"perfil": "string",
"opcoes_erp": "string"
},
"departamento": {
"id": 0,
"descricao": "string"
},
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"login": "string",
"senha": "string",
"outros": {
"tempo_maximo_inatividade": "string",
"dia_acesso": "string",
"vendas_restritas": "string",
"aba_principal": 0
},
"opcoes": {
"visualizar_informacoes_inicial": true,
"visualizar_painel_informacoes": true,
"visualizar_dashboard": true,
"visualizar_todos_funcionarios": true,
"grafico_vol_vendas": true,
"grafico_faturamento": true,
"grafico_saldo_financeiro": true,
"atividades_recentes": true,
"resumos": true,
"grafico_financ_mes": true
},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [
{}
],
"contatos": [
{}
],
"clientes": [
{}
],
"permissoes": [
"string"
],
"dependentes": [
{}
],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [
"string"
],
"parceria": true
}
Editar usuário
Atualiza as informações do usuário.

PATH PARAMETERS
id
required
integer
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
data_alteracao	
string
Data em que os dados do usuário foram alterados pela última vez.

ativo	
boolean
Indica se o usuário é um usuário ativo quando true.

sexo	
string
Enum: "M" "F"
nome	
string
Nome do usuário do sistema, podendo esse ser por exemplo: um vendedor ou funcionario responsável, gerente, etc..."

cpf	
string
CPF do usuário

cnpj	
string
Campo específico para sistemas de parceiros

perfil_acesso	
integer
departamento	
integer
ID do departamento

categoria	
integer
login	
string
senha	
string [ 6 .. 100 ] characters
outros	
object
opcoes	
object
observacoes	
string
rg	
string
data_nascimento	
string <date>
escolaridade	
integer
Enum: 0 1 2 3 4 5
0 - Ensino Fundamental Incompleto

1 - Ensino Fundamental Completo

2 - Ensino Médio Incompleto

3 - Ensino Médio Completo

4 - Ensino Superior Incompleto

5 - Ensino Superior Completo

data_admissao	
string <date>
data_demissao	
string <date>
descanso_semanal	
string
ctps	
string
salario	
number
Cadastro do salário do funcionario.

tipo_conta	
integer
Enum: 0 1 2
0 - Conta Corrente

1 - Conta Poupança

2 - Conta Salário

banco_agencia	
string
banco_conta	
string
banco_numero	
string
comissao	
number
desconto_maximo_permitido	
number
hora_entrada	
string
hora_saida	
string
hora_almoco_entrada	
string
hora_almoco_saida	
string
enderecos	
Array of objects (Endereço)
Cadastro dos endereços do cliente.

contatos	
Array of objects (Contato)
Informações de telefone, e-mail, Twitter, etc...

clientes	
Array of integers
Array de id's de clientes aos quais o usuário tem permissão para efetuar vendas.

dependentes	
Array of objects (Dependente)
parceria	
boolean
Responses
200 Usuário alterado!

PATCH
/usuarios/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": 0,
"departamento": 0,
"categoria": 0,
"login": "string",
"senha": "string",
"outros": {
"tempo_maximo_inatividade": "string",
"dia_acesso": "string",
"vendas_restritas": "string",
"aba_principal": 0
},
"opcoes": {
"visualizar_informacoes_inicial": true,
"visualizar_painel_informacoes": true,
"visualizar_dashboard": true,
"visualizar_todos_funcionarios": true
},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [
{}
],
"contatos": [
{}
],
"clientes": [
0
],
"dependentes": [
{}
],
"parceria": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {
"id": 0,
"perfil": "string",
"opcoes_erp": "string"
},
"departamento": {
"id": 0,
"descricao": "string"
},
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"login": "string",
"senha": "string",
"outros": {
"tempo_maximo_inatividade": "string",
"dia_acesso": "string",
"vendas_restritas": "string",
"aba_principal": 0
},
"opcoes": {
"visualizar_informacoes_inicial": true,
"visualizar_painel_informacoes": true,
"visualizar_dashboard": true,
"visualizar_todos_funcionarios": true,
"grafico_vol_vendas": true,
"grafico_faturamento": true,
"grafico_saldo_financeiro": true,
"atividades_recentes": true,
"resumos": true,
"grafico_financ_mes": true
},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [
{}
],
"contatos": [
{}
],
"clientes": [
{}
],
"permissoes": [
"string"
],
"dependentes": [
{}
],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [
"string"
],
"parceria": true
}
Apagar usuário
PATH PARAMETERS
id
required
integer
Responses
200 Usuário apagada!

DELETE
/usuarios/{id}
Recuperar comissão
Recuperar a comissão de um funcionário

PATH PARAMETERS
id
required
integer
QUERY PARAMETERS
tipo_opcoes_comissao
required
integer
Enum: 1 2 3 4
1 - Itens e Serviços Vendidos 2 - Vendas e Notas Fiscais Confirmadas 3 - Pedidos e Orçamentos Confirmados 4 - Financeiro Confirmado

data_considerada
required
integer
Enum: 1 2
1 - Criação 2 - Confirmação

data_inicial
required
string
Data inicial

data_final
required
string
Data final

Responses
200 Sucesso!

GET
/usuarios/comissao/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"valor": 0
}
Listar categoria de usuários
Responses
200 Sucesso!

GET
/usuarios/categorias
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"categoria_mae": {},
"descricao": "string"
}
]
Criar categoria de usuário
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
categoria_mae	
integer
Responses
201 Categoria de usuário criado!

POST
/usuarios/categorias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Recuperar categoria de usuário
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/usuarios/categorias/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Editar categoria de usuário
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
categoria_mae	
integer
descricao	
string
Responses
200 Categoria de usuário alterado!

PATCH
/usuarios/categorias/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"categoria_mae": 0,
"descricao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"categoria_mae": {
"id": 0,
"descricao": "string"
},
"descricao": "string"
}
Apagar uma categoria de usuário
Apaga uma categoria de usuário específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/usuarios/categorias/{id}
Recuperar foto do usuário
Recupera o link da foto do usuário.

PATH PARAMETERS
id
required
integer
Responses
200 Sucesso!

GET
/usuarios/foto/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"url": "string"
}
Fazer upload da foto do usuário
PATH PARAMETERS
id
required
integer
REQUEST BODY SCHEMA: multipart/form-data
file	
string <binary>
O arquivo a ser enviado.

Responses
201 Upload feito com sucesso!

POST
/usuarios/foto/{id}
Criar usuário master
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
usuario_master
required
integer
Id do Usuário/Funcionário

email_cobranca
required
string
Email principal de Cobrança

nome_responsavel	
string
Nome do responsavel pela empresa

telefone	
string
Telefone principal

Responses
201 Usuário master criado!

POST
/usuarios/usuario_master
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"nome_responsavel": "string",
"usuario_master": 0,
"email_cobranca": "string",
"telefone": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"nome_responsavel": "string",
"usuario_master": "string",
"email_cobranca": "string",
"telefone": "string"
}
Recupera se o cliente pode cadastrar novo usuário
Recupera se o cliente pode cadastrar novo usuário

Responses
200 Sucesso!

GET
/usuarios/checar_limite_plano
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"checar_limite_plano": true
}
Recupera informações do usuário que autorizou o token.
Responses
200 Sucesso!

GET
/me
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {
"id": 0,
"perfil": "string",
"opcoes_erp": "string"
},
"departamento": {
"id": 0,
"descricao": "string"
},
"categoria": {
"id": 0,
"id_categoria_mae": 0,
"descricao": "string"
},
"login": "string",
"senha": "string",
"outros": {
"tempo_maximo_inatividade": "string",
"dia_acesso": "string",
"vendas_restritas": "string",
"aba_principal": 0
},
"opcoes": {
"visualizar_informacoes_inicial": true,
"visualizar_painel_informacoes": true,
"visualizar_dashboard": true,
"visualizar_todos_funcionarios": true,
"grafico_vol_vendas": true,
"grafico_faturamento": true,
"grafico_saldo_financeiro": true,
"atividades_recentes": true,
"resumos": true,
"grafico_financ_mes": true
},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [
{}
],
"contatos": [
{}
],
"clientes": [
{}
],
"permissoes": [
"string"
],
"dependentes": [
{}
],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [
"string"
],
"parceria": true,
"erp_uid": "string",
"gestao_id": "string"
}
Recupera as permissões de menus do usuário que autorizou o token.
Responses
200 Sucesso!

GET
/me/menus
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"opcoes_erp": [
"string"
]
}
Recupera as permissões do usuário que autorizou o token.
Responses
200 Sucesso!

GET
/me/permissoes
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"alterar_numero_controle_ajuste_estoque": true,
"alterar_numero_controle_os": true,
"alterar_numero_controle_contrato": true,
"alterar_numero_controle_pedido_venda": true,
"alterar_numero_controle_venda_simples": true,
"alterar_numero_controle_gestao_saldo": true,
"alterar_numero_controle_pedido_compra": true,
"alterar_numero_controle_consignacao": true,
"alterar_data_criacao_movimentacoes": true,
"alterar_data_confirmacao_movimentacoes": true,
"alterar_atividade_os": true,
"alterar_atividade_contrato": true,
"alterar_vendedor_contrato_normal": true,
"alterar_vendedor_vinculado_cliente": true,
"alterar_data_hora_atividade_os": true,
"alterar_estoque_produto": true,
"funcionario_visualizar_valores_custos": true,
"funcionario_permissao_modificar_valor_unitario": true,
"funcionario_selecionar_valores_venda": true,
"funcionario_permissao_data_conf": true,
"funcionario_permissao_data_lanc": true,
"funcionario_permissao_fechamento_mes": true,
"funcionario_permissao_estorno": true,
"funcionario_permissao_movimentacoes": 0,
"funcionario_permissao_clientes": 0,
"indicar_convidados_agenda": true,
"funcionario_permissao_acrescimo_contrato": true,
"funcionario_permissao_estorno_contrato": true,
"funcionario_permissao_meus_cartoes": true,
"funcionario_permissao_bloquear_juros": true,
"funcionario_bloquear_envio_em_massa_pedidos": true,
"funcionario_bloquear_envio_em_massa_venda_simples": true,
"funcionario_bloquear_envio_em_massa_nfe": true,
"funcionario_bloquear_envio_em_massa_nfce": true,
"funcionario_bloquear_envio_em_massa_nfse": true,
"funcionario_bloquear_cancelar_confirmacao": true,
"funcionario_permissao_visualizar_tagbank": true,
"funcionario_acesso_certificado": true,
"bloquear_limite_credito": true,
"bloquear_avisos_tagpix": true,
"acesso_pvc": true,
"acesso_financeiro": true,
"alteracoes": true,
"alteracoes_data": true,
"alteracoes_numero": true,
"bloqueios": true,
"edicoes": true,
"envio_massa": true,
"alterar_numero_nfe": true,
"alterar_numero_nfce": true,
"alterar_numero_mdfe": true,
"funcionario_permissao_loja_app": true,
"funcionario_permissao_spc_serasa": true,
"desbloquer_cliente_gestao": true,
"funcionario_permissao_ocultar_saldo_listagem": true,
"funcionario_bloquear_relatorios_app": true,
"funcionario_permissao_visualizar_agenda": true,
"valor_venda_custo_utilizado": true
}
financeiros
Listar financeiros
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

X-Totalizadores	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

X-Saldo-Anterior	
boolean
Example: true
Indica que se a consulta irá retornar os totalizadores da consulta realizada considerando o saldo anterior.

Responses
200 Sucesso!

GET
/financeiros
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {},
"conta_bancaria": {},
"departamento": {},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {},
"funcionario_responsavel": {},
"tipo_entidade": "C",
"entidade": {},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [],
"boleto": [],
"fatura_parcela_vinculada": {},
"anexos": []
}
]
Criar financeiro
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
tipo
required
string
Default: "S"
Enum: "E" "S"
Indica se o lançamento financeiro é do tipo Entrada ou Saida. Entradas são todos valores creditados, ex: Vendas. Saidas são todos valores debitados, ex: Conta de energia elétrica, aluguel, pagamento de funcionários.

plano_orcamentario
required
integer
forma_pagamento
required
integer
descricao
required
string
Descrição a que se refere o lançamento.

valor_bruto
required
number
Valor Bruto.

conta_bancaria
required
integer
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero_documento	
string
Número do documento que identifica o lançamento financeiro pra funcionalides como por exemplo conciliação bancária.

confirmado	
boolean
Default: false
Indica se o lançamento financeiro já foi pago seja ele entrada ou saida. Quando já está pago, é considerado como true confirmado.

numero_sigla_movimentacao_vinculada	
string
Número e sigla identificando movimentação vinculada.

data_vencimento	
string <date-time>
Data de vencimento. Caso não informado, será preenchida com a data atual da criação.

valor_original	
number
Valor Original.

valor_pago	
number
Valor Pago.

departamento	
integer
ID do departamento do financeiro. Caso não informado, será preenchido com departamento do usuário que está criando o registro.

item_fatura	
integer
transferencia	
boolean
Default: false
Indica de há tranferência entre contas.

data_lancamento	
string <date-time>
Data de lançamento. Caso não informado, será preenchida com a data atual da criação.

data_confirmacao	
string
Data de confirmação.

valor_desconto	
number
Valor desconto.

valor_acrescimo	
number
Valor acréscimo.

valor_juros_atraso	
number
Valor dos juros cobrados por atraso.

aliquota_juros_ao_dia	
number
Percentual dos jutos cobrados ao dia.

tipo_entidade	
string
Enum: "C" "F" "T" "U" "O"
Tipo de entidade a qual está vinculada ao lançamento. C=Cliente | F=Fornecedor | T=Transportadora | U=Funcionário | O=Outros |

entidade	
integer
ID da entidade referente ao cliente, ou fornecedor, ou funcionário, ou transportador a qual o financeiro estará vinculado. Caso não informado, não haverá entidade vinculada, mas tipo da entidade será salvo.

data_competencia	
string
Data em que será diluido o lançamento caso exista diluição.

diluicao_lancamento	
integer
Quantidade de meses em que se deve diluir o lançamento a partir da data de competencia ou data do lançamento.

primeira_parcela	
integer
ID da parcela que será vinculada a essa.

id_caixa	
integer
ID do Caixa, no caso de lançamentos financeiros originados pelo PDV.

informacao_1	
string
Informações adicionais da parcela.

informacao_2	
string
Informações adicionais da parcela.

informacao_3	
string
Informações adicionais da parcela.

historico	
string
Informações adicionais da parcela.

observacoes	
string
Informações adicionais da parcela.

financeiro_parcelas	
Array of objects (Financeiro)
Responses
201 Financeiro criado!

POST
/financeiros
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "2019-08-24T14:15:22Z",
"forma_pagamento": 0,
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"plano_orcamentario": 0,
"conta_bancaria": 0,
"departamento": 0,
"item_fatura": 0,
"transferencia": false,
"data_lancamento": "2019-08-24T14:15:22Z",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"tipo_entidade": "C",
"entidade": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": 0,
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [
{}
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {},
"classificacao_dre": {},
"data_alteracao": "string"
},
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"departamento": {
"id": 1,
"descricao": "VENDAS"
},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"funcionario_responsavel": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"tipo_entidade": "C",
"entidade": {
"id": 0,
"tipo_entidade": "C",
"nome_fantasia": "string",
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"data_vencimento": "string",
"descricao": "string",
"valor_total": 0,
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"parcela": 0,
"total_parcelas": 0,
"forma_pagamento": {}
},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [
{}
],
"boleto": [
{}
],
"fatura_parcela_vinculada": {
"id": 0,
"parcela": 0,
"valor_parcela": 0,
"data_vencimento": "string",
"documento": "string"
},
"anexos": [
"string"
]
}
Recuperar financeiro
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/financeiros/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {},
"classificacao_dre": {},
"data_alteracao": "string"
},
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"departamento": {
"id": 1,
"descricao": "VENDAS"
},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"funcionario_responsavel": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"tipo_entidade": "C",
"entidade": {
"id": 0,
"tipo_entidade": "C",
"nome_fantasia": "string",
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"data_vencimento": "string",
"descricao": "string",
"valor_total": 0,
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"parcela": 0,
"total_parcelas": 0,
"forma_pagamento": {}
},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [
{}
],
"boleto": [
{}
],
"fatura_parcela_vinculada": {
"id": 0,
"parcela": 0,
"valor_parcela": 0,
"data_vencimento": "string",
"documento": "string"
},
"anexos": [
"string"
]
}
Editar financeiro
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero_documento	
string
Número do documento que identifica o lançamento financeiro pra funcionalides como por exemplo conciliação bancária.

tipo	
string
Default: "S"
Enum: "E" "S"
Indica se o lançamento financeiro é do tipo Entrada ou Saida. Entradas são todos valores creditados, ex: Vendas. Saidas são todos valores debitados, ex: Conta de energia elétrica, aluguel, pagamento de funcionários.

confirmado	
boolean
Default: false
Indica se o lançamento financeiro já foi pago seja ele entrada ou saida. Quando já está pago, é considerado como true confirmado.

numero_sigla_movimentacao_vinculada	
string
Número e sigla identificando movimentação vinculada.

data_vencimento	
string <date-time>
Data de vencimento. Caso não informado, será preenchida com a data atual da criação.

forma_pagamento	
integer
descricao	
string
Descrição a que se refere o lançamento.

valor_bruto	
number
Valor Bruto.

valor_original	
number
Valor Original.

valor_pago	
number
Valor Pago.

plano_orcamentario	
integer
conta_bancaria	
integer
departamento	
integer
ID do departamento do financeiro. Caso não informado, será preenchido com departamento do usuário que está criando o registro.

item_fatura	
integer
transferencia	
boolean
Default: false
Indica de há tranferência entre contas.

data_lancamento	
string <date-time>
Data de lançamento. Caso não informado, será preenchida com a data atual da criação.

data_confirmacao	
string
Data de confirmação.

valor_desconto	
number
Valor desconto.

valor_acrescimo	
number
Valor acréscimo.

valor_juros_atraso	
number
Valor dos juros cobrados por atraso.

aliquota_juros_ao_dia	
number
Percentual dos jutos cobrados ao dia.

tipo_entidade	
string
Enum: "C" "F" "T" "U" "O"
Tipo de entidade a qual está vinculada ao lançamento. C=Cliente | F=Fornecedor | T=Transportadora | U=Funcionário | O=Outros |

entidade	
integer
ID da entidade referente ao cliente, ou fornecedor, ou funcionário, ou transportador a qual o financeiro estará vinculado. Caso não informado, não haverá entidade vinculada, mas tipo da entidade será salvo.

data_competencia	
string
Data em que será diluido o lançamento caso exista diluição.

diluicao_lancamento	
integer
Quantidade de meses em que se deve diluir o lançamento a partir da data de competencia ou data do lançamento.

primeira_parcela	
integer
ID da parcela que será vinculada a essa.

id_caixa	
integer
ID do Caixa, no caso de lançamentos financeiros originados pelo PDV.

informacao_1	
string
Informações adicionais da parcela.

informacao_2	
string
Informações adicionais da parcela.

informacao_3	
string
Informações adicionais da parcela.

historico	
string
Informações adicionais da parcela.

observacoes	
string
Informações adicionais da parcela.

financeiro_parcelas	
Array of objects (Financeiro)
Responses
200 Financeito alterado!

PATCH
/financeiros/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "2019-08-24T14:15:22Z",
"forma_pagamento": 0,
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"plano_orcamentario": 0,
"conta_bancaria": 0,
"departamento": 0,
"item_fatura": 0,
"transferencia": false,
"data_lancamento": "2019-08-24T14:15:22Z",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"tipo_entidade": "C",
"entidade": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": 0,
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {},
"classificacao_dre": {},
"data_alteracao": "string"
},
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"departamento": {
"id": 1,
"descricao": "VENDAS"
},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"funcionario_responsavel": {
"id": 0,
"id_entidade": 0,
"data_alteracao": "string",
"ativo": true,
"sexo": "M",
"nome": "string",
"email_principal": "string",
"cpf": "string",
"cnpj": "string",
"perfil_acesso": {},
"departamento": {},
"categoria": {},
"login": "string",
"senha": "string",
"outros": {},
"opcoes": {},
"observacoes": "string",
"rg": "string",
"data_nascimento": "2019-08-24",
"escolaridade": 0,
"data_admissao": "2019-08-24",
"data_demissao": "2019-08-24",
"descanso_semanal": "string",
"ctps": "string",
"salario": 0,
"tipo_conta": 0,
"banco_agencia": "string",
"banco_conta": "string",
"banco_numero": "string",
"comissao": 0,
"desconto_maximo_permitido": 0,
"hora_entrada": "string",
"hora_saida": "string",
"hora_almoco_entrada": "string",
"hora_almoco_saida": "string",
"enderecos": [],
"contatos": [],
"clientes": [],
"permissoes": [],
"dependentes": [],
"possui_log": true,
"possui_vinculo": true,
"usuario_master": true,
"anexos": [],
"parceria": true
},
"tipo_entidade": "C",
"entidade": {
"id": 0,
"tipo_entidade": "C",
"nome_fantasia": "string",
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"data_vencimento": "string",
"descricao": "string",
"valor_total": 0,
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"parcela": 0,
"total_parcelas": 0,
"forma_pagamento": {}
},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [
{}
],
"boleto": [
{}
],
"fatura_parcela_vinculada": {
"id": 0,
"parcela": 0,
"valor_parcela": 0,
"data_vencimento": "string",
"documento": "string"
},
"anexos": [
"string"
]
}
Apagar financeiro
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Financeito apagado!

DELETE
/financeiros/{id}
Realizar transferencia entre contas
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
conta_origem
required
integer
ID da conta de origem

plano_orcamentario_origem
required
integer
ID do plano orçamentário de origem

conta_destino
required
integer
ID da conta de destino

plano_orcamentario_destino
required
integer
ID do plano orçamentário de destino

valor_total
required
number
Valor da Transferência

descricao
required
string
Descrição

forma_pagamento
required
integer
ID da forma de pagamento

departamento
required
integer
ID do departamento

data_vencimento
required
string
Data de Vencimento

data_confirmacao	
string
Data de Confirmação

confirmar_lancamentos	
boolean
Default: true
Confirmar lançamentos

observacoes	
string
Observações

Responses
201 Transferência realizada!

POST
/financeiros/transferencia
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"conta_origem": 0,
"plano_orcamentario_origem": 0,
"conta_destino": 0,
"plano_orcamentario_destino": 0,
"valor_total": 0,
"descricao": "string",
"forma_pagamento": 0,
"departamento": 0,
"data_vencimento": "string",
"data_confirmacao": "string",
"confirmar_lancamentos": true,
"observacoes": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {},
"conta_bancaria": {},
"departamento": {},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {},
"funcionario_responsavel": {},
"tipo_entidade": "C",
"entidade": {},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [],
"boleto": [],
"fatura_parcela_vinculada": {},
"anexos": []
}
]
Conciliação bancária
REQUEST BODY SCHEMA: multipart/form-data
required
conta
required
integer
ID da conta bancária

considera_data_vencimento	
boolean
Default: false
Ao tentar buscar um lançamento a data de vencimento será considerada. Será levada em consideração 10 dias antes e 10 dias depois, com base na data que está no arquivo

conciliacao_apurada	
boolean
Default: false
Ao marcar esta opção a pesquisa do lançamento será feita somente pelo Número do Documento, Valor e Data de Vencimento. Caso não esteja marcada será feito as validações normalmente.

conciliacao_proximidade	
boolean
Default: false
Ao marcar esta opção a pesquisa do lançamento será por proximidade de valor de 0,5% de variação para cima ou para baixo e data de vencimento de 2 dias obedecendo o mesmo preceito. Caso não esteja marcada, o comportamento será o padrão.

arquivo	
string <binary>
Arquivo '.ofx' exportado do extrato da conta bancária.

Responses
201 Conciliação realizada!

POST
/financeiros/conciliacao
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {},
"conta_bancaria": {},
"departamento": {},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {},
"funcionario_responsavel": {},
"tipo_entidade": "C",
"entidade": {},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [],
"boleto": [],
"fatura_parcela_vinculada": {},
"anexos": []
}
]
Importação do arquivo de boleto
REQUEST BODY SCHEMA: multipart/form-data
conta	
integer
Id da conta bancária

considera_data_vencimento	
boolean
Default: false
Ao tentar buscar um lançamento a data de vencimento será considerada. Será levada em consideração 10 dias antes e 10 dias depois, com base na data que está no arquivo

arquivo	
string <binary>
Arquivo '.RET' exportado do extrato da conta bancária.

Responses
201 Boletos importados com sucesso!

POST
/financeiros/boleto
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"numero_documento": "string",
"data_confirmacao": "string",
"data_vencimento": "string",
"descricao": "string",
"tipo": "E",
"valor_total": 0,
"valor_original": 0,
"codigo_ocorrencia": "string"
}
]
Retornar o fechamento diario em formato A4
Retorna o fechamento diario em formato A4

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
detalhado
required
string
Enum: "1" "2"
1 - Detalhado

2 - Resumido

data
required
string
Data de Fechamento

Responses
200 Sucesso!

POST
/financeiros/fechamento_diario_a4
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"detalhado": "1",
"data": "06-09-2022"
}
Retornar o fechamento diario em formato Cupom
Retorna o fechamento diario em formato Cupom

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
detalhado
required
string
Enum: "1" "2"
1 - Detalhado

2 - Resumido

data
required
string
Data de Fechamento

Responses
200 Sucesso!

POST
/financeiros/fechamento_diario_mini
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"detalhado": "1",
"data": "06-09-2022"
}
Retorna data definida para fechamento do mês
Responses
200 Sucesso!

GET
/financeiros/fechamento_mes
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"mes": "string",
"ano": "string"
}
Definir data para fechamento do mês.
Essa opção impossibilitará o lançamento financeiro somente manual, levando em consideração as datas de criação, vencimento, confirmação e competência

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
mes	
string
Enum: "" "01" "02" "03" "04" "05" "06" "07" "08" "09" "10" "11" "12"
Mês limite dos lancamentos

01 - Janeiro

02 - Fevereiro

03 - Março

04 - Abril

05 - Maio

06 - Junho

07 - Julho

08 - Agosto

09 - Setembro

10 - Outubro

11 - Novembro

12 - Dezembro

ano	
string <= 4 characters
Ano limite dos lançamentos no formato (AAAA). O ano deve estar entre os 5 últimos anos e os próximos 5 anos.

Responses
201 Data limite dos lançamentos definida com sucesso!

POST
/financeiros/fechamento_mes
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"mes": "",
"ano": "2019"
}
Fluxo de Caixa PDF
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
data_inicial	
string
Data Inicial

data_final	
string
Data Final

tipo_lancamento	
string
Default: ""
Enum: "" "E" "S"
"" - Créditos e Débitos

E - Créditos

S - Débitos

situacao_lancamentos	
integer
Default: ""
Enum: "" 0 1
"" - Confirmados e Não Confirmados

1 - Confirmados

0 - Não Confirmados

data_considerada	
string
Default: "V"
Enum: "" "V" "O" "C" "M" "A"
A - Data Alteração

V - Data de Vencimento

O - Data de Confirmação

C - Data de Criação

M - Data de Competência

vinculacao	
string
Default: "I"
Enum: "" "I" "C" "U" "F" "T" "O" "V"
I - Indiferente

C - Cliente

U - Funcionário

F - Fornecedor

T - Transportadora

O - Outros

V - Vendedor

transferencia	
boolean
Default: true
Considerar transferências

saldo_anterior	
boolean
Default: false
Considerar saldo anterior

funcionario_responsavel	
Array of integers
O funcionario responsavel pela movimentação

funcionario	
Array of integers
O funcionario da movimentação

conta_bancaria	
Array of integers
A conta relacionada a movimentação

entidade	
Array of integers
A entidade relacionada a movimentação

departamento	
Array of integers
O departamento relacionado a movimentação

plano_orcamentario	
Array of integers
O plano orçamentario relacionado a movimentação

Responses
200 Retorna o Fluxo de Caixa no formato PDF

POST
/financeiros/pdf/fluxo_caixa
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"data_inicial": "string",
"data_final": "string",
"tipo_lancamento": "",
"situacao_lancamentos": "",
"data_considerada": "",
"vinculacao": "",
"transferencia": true,
"saldo_anterior": false,
"funcionario_responsavel": [
0
],
"funcionario": [
0
],
"conta_bancaria": [
0
],
"entidade": [
0
],
"departamento": [
0
],
"plano_orcamentario": [
0
]
}
Plano de Contas PDF
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
data_inicial	
string
Data Inicial

data_final	
string
Data Final

tipo_lancamento	
string
Default: ""
Enum: "" "E" "S"
"" - Créditos e Débitos

E - Créditos

S - Débitos

situacao_lancamentos	
integer
Default: ""
Enum: "" 0 1
"" - Confirmados e Não Confirmados

1 - Confirmados

0 - Não Confirmados

data_considerada	
string
Default: "V"
Enum: "" "V" "O" "C" "M" "A"
A - Data Alteração

V - Data de Vencimento

O - Data de Confirmação

C - Data de Criação

M - Data de Competência

vinculacao	
string
Default: "I"
Enum: "" "I" "C" "U" "F" "T" "O" "V"
I - Indiferente

C - Cliente

U - Funcionário

F - Fornecedor

T - Transportadora

O - Outros

V - Vendedor

transferencia	
boolean
Default: true
Considerar transferências

saldo_anterior	
boolean
Default: false
Considerar saldo anterior

funcionario_responsavel	
Array of integers
O funcionario responsavel pela movimentação

funcionario	
Array of integers
O funcionario da movimentação

conta_bancaria	
Array of integers
A conta relacionada a movimentação

entidade	
Array of integers
A entidade relacionada a movimentação

departamento	
Array of integers
O departamento relacionado a movimentação

plano_orcamentario	
Array of integers
O plano orçamentario relacionado a movimentação

Responses
200 Retorna o Plano de Contas no formato PDF

POST
/financeiros/pdf/plano_contas
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"data_inicial": "string",
"data_final": "string",
"tipo_lancamento": "",
"situacao_lancamentos": "",
"data_considerada": "",
"vinculacao": "",
"transferencia": true,
"saldo_anterior": false,
"funcionario_responsavel": [
0
],
"funcionario": [
0
],
"conta_bancaria": [
0
],
"entidade": [
0
],
"departamento": [
0
],
"plano_orcamentario": [
0
]
}
Financeiro PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Financeiro no formato PDF

GET
/financeiros/pdf/financeiro/{id}
Recibo A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo A4 no formato PDF

GET
/financeiros/pdf/recibo_a4/{id}
Recibo Mini PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Recibo Mini no formato PDF

GET
/financeiros/pdf/recibo_mini/{id}
Carnê A4 PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna o Carnê A4 no formato PDF

GET
/financeiros/pdf/carne_a4/{id}
Carnê Mini PDF
PATH PARAMETERS
id
required
integer
Example: 1
QUERY PARAMETERS
parcela	
boolean
Se true irá gerar o carnê apenas da parcela, se false gera todos os carnês.

Responses
200 Retorna o Carnê Mini no formato PDF

GET
/financeiros/pdf/carne_mini/{id}
Imprimir boleto
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
numero_documento	
string
Número do documento (Nosso número)

demonstrativo_1	
string
Demonstrativo 1

demonstrativo_2	
string
Demonstrativo 2

demonstrativo_3	
string
Demonstrativo 3

instrucoes_1	
string
Instruções 1

instrucoes_2	
string
Instruções 2

instrucoes_3	
string
Instruções 3

instrucoes_4	
string
Instruções 4

Responses
200 Retorna a linha digitavel e a url para a visualização do boleto

POST
/financeiros/pdf/boleto/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"numero_documento": "string",
"demonstrativo_1": "string",
"demonstrativo_2": "string",
"demonstrativo_3": "string",
"instrucoes_1": "string",
"instrucoes_2": "string",
"instrucoes_3": "string",
"instrucoes_4": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"linha_digitavel": "string",
"url": "string"
}
Gera boleto parcelas
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a url para acesso dos boletos de todas as parcelas de um lançamento financeiro

GET
/financeiros/pdf/boleto_lote/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"url": "string"
}
Enviar e-mail Financeiros
'Enviar lançamento financeiro por e-mail'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids
required
Array of integers
Ids dos lançamentos financeiros

emails	
Array of strings
Array com os e-mails para onde serão enviadas os lançamentos financeiros.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

anexar_arquivos	
boolean
Default: false
Indica se os arquivos vinculados ao lançamento financeiro serão anexados ao e-mail.

Responses
200 Sucesso!

POST
/financeiros/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"enviar_para_todos": false,
"anexar_arquivos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Gerar nosso número
QUERY PARAMETERS
forma_pagamento
required
string
ID da forma de pagamento

num_parcelas	
string
Default: 1
Numero de parcelas

Responses
200 Sucesso!

GET
/financeiros/nosso_numero
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"nosso_numero": "string"
}
]
Exportar Arquivos Financeiros
'Exportar Arquivos Financeiros '

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
data_considerada
required
string
Default: "V"
Enum: "" "V" "O" "C" "M"
V - Data de Vencimento

O - Data de Confirmação

C - Data de Criação

M - Data de Competência

data_periodo	
string
Default: ""
Enum: "" "1" "2" "3" "4"
O periodo considerado. É obrigatorio caso não passe a data inicial e final. 1 - Periodo do Mês Atual

2 - Periodo do Mês Passado

3 - Periodo da semana atual

4 - Periodo da semana passada

5 - Periodo dos ultimos sete dias

6 - Periodo dos ultimos trinta dias

filtro_download	
string
Enum: "" "1" "2"
1 - Agrupar conta bancária por pasta

2 - Gerar todos os arquivos na mesma pasta

data_inicial_export	
string
Data Inicial

data_final_export	
string
Data Final

Responses
200 Sucesso!

POST
/financeiros/exportar_arquivos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"data_considerada": "",
"data_periodo": "",
"filtro_download": "",
"data_inicial_export": "string",
"data_final_export": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"mensagem": "string",
"link": "string"
}
Exportar Arquivos Financeiros Assincronamente
Exportar Arquivos Financeiros Assincronamente

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
ids	
Array of integers
Gera exportação de financeiros selecionados

data_considerada	
string
Enum: "data_lancamento" "data_confirmacao" "data_vencimento" "data_competencia"
Indica a data a ser considerada nos campos data_inicial e data_final:

data_inicial	
string
Data Inicial

data_final	
string
Data Final

emails	
Array of strings
Emails para onde os arquivos serão enviados. Mesmo que nenhum email seja preenchido, a exportação ficará disponível na aba Últimas exportações do modal

situacao	
string
Enum: "" "0" "1"
Indica a situação da nota 0 - Não Confirmados | 1 - Confirmados | **** - Qualquer

tipo	
string
Enum: "A" "E" "S"
Tipo do Financeiro: A - Entrada e Saída | E - Entrada | S - Saída

ids_entidades	
Array of integers
IDs das entidades vinculados

ids_contas	
Array of integers
IDs das entidades vinculados

nome_solicitacao	
string
Nome para identificar a solicitação

Responses
201 Sucesso!

POST
/financeiros/export_async
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"data_considerada": "data_lancamento",
"data_inicial": "string",
"data_final": "string",
"emails": [
"string"
],
"situacao": "",
"tipo": "A",
"ids_entidades": [
0
],
"ids_contas": [
0
],
"nome_solicitacao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
[
null
]
Confirmar Lançamentos em Massa
'Confirmar Lançamentos em Massa'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
any
Responses
200 Sucesso!

POST
/financeiros/confirmar_massa
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
[
null
]
Financeiros | Evolução de receitas e despesas
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/evolucao_receitas_despesas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"receita": 0,
"despesa": 0,
"saldo": 0,
"valor_credito": 0,
"valor_debito": 0,
"valor_saldo": 0
}
]
Financeiros | Evolução do faturamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/evolucao_faturamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"valor": 0,
"valor_medio": 0
}
]
Financeiros | Evolução do faturamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

since	
string
Data inicial para geração do relatório

until	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/grafico_faturamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"valor": 0,
"valor_medio": 0
}
]
Financeiros | Funcionários rentáveis
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/funcionarios_rentaveis
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"razao_social": "string"
}
]
Financeiros | Clientes rentáveis
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/clientes_rentaveis
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"razao_social": "string"
}
]
Financeiros | Receitas por plano orçamentário
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/receitas_plano_orcamentario
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"plano_orcamentario": "string"
}
]
Financeiros | Despesas por plano orçamentário
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/despesas_plano_orcamentario
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"plano_orcamentario": "string"
}
]
Financeiros | Receitas por forma de pagamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/receitas_forma_pagamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"descricao_forma_pagamento": "string"
}
]
Financeiros | Despesas por forma de pagamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/despesas_forma_pagamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"descricao_forma_pagamento": "string"
}
]
Financeiros | Clientes inadimplentes
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/clientes_inadimplentes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id_cliente": 0,
"razao_social": "string",
"valor": 0
}
]
Financeiros | Fornecedores credores
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/fornecedores_credores
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id_fornecedor": 0,
"razao_social": "string",
"valor": 0
}
]
Financeiros | Saldo por conta bancária
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/saldo_conta_bancaria
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"conta": "string",
"valor": 0
}
]
Financeiros | Saldo por departamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/saldo_departamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"departamento": "string",
"valor": 0
}
]
Resumo | Financeiros
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/numeros
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"resumo_numero_dias": 0,
"valor_total_creditos": 0,
"valor_total_debitos": 0,
"saldo_atual": 0
}
movimentacoes
Recupera uma lista de movimentações de uma entidade ou produto.
Recupera uma lista de movimentações de uma entidade ou produto.

PATH PARAMETERS
id
required
integer
Example: 1
QUERY PARAMETERS
tipo
required
string
Enum: "E" "P"
Define se a busca será feita pela entidade ou por produto:

E = Entidade

P = Produto/Serviço

Responses
200 Sucesso!

GET
/movimentacoes/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"financeiros": [
{}
],
"notas_e_outros": [
{}
],
"nfes": [
{}
],
"nfses": [
{}
],
"nfces": [
{}
],
"pedido_os": [
{}
]
}
contas
Listar contas
Responses
200 Sucesso!

GET
/contas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
}
]
Criar conta
Cria uma conta bancária

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome
required
string
ativo	
integer
Default: 1
Enum: 0 1 2
0=Inativa 1=Ativa 2=Visivel somente em relatórios

banco	
integer
Campo identificador do banco, saiba como recuperar bancos clicando aqui

agencia	
string
agencia_digito	
string
carteira	
string
conta	
string
conta_digito	
string
conta_cobranca	
string
contato	
string
contrato	
string
convenio	
string
observacoes	
string
ua	
string
num_transmissao	
string <= 20 characters
num_seq_boleto	
string
modalidade_carteira	
integer
Enum: 1 2 3
1=Simples

2=Vinculada / Caucionada

3=Descontada

tipo_carteira	
string
impressao_logo	
boolean
dados_adicionais	
object <= 1 characters
Para alguns bancos devem ser informadas alguns dados adicionais. Abaixo estão listados todos os bancos e seus respectivos campos adicionais.

data_alteracao	
string
Responses
201 Conta criada!

POST
/contas
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ativo": 0,
"nome": "string",
"banco": 0,
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {
"ailos": {},
"banco_da_amazonia": { },
"banco_do_brasil": {},
"banco_do_nordeste": { },
"banco_inter": {},
"banco_real": { },
"banestes": { },
"banrisul": {},
"bradesco": {},
"caixa_economica_federal": {},
"citibank": { },
"hsbc": {},
"itau": {},
"santander": {},
"sicoob": {},
"sicredi": {},
"unicred": { },
"boleto_informacoes_personalizadas": true,
"boleto_demonstrativo_1": "string",
"boleto_demonstrativo_2": "string",
"boleto_demonstrativo_3": "string",
"boleto_informacoes_1": "string",
"boleto_informacoes_2": "string",
"boleto_informacoes_3": "string",
"boleto_informacoes_4": "string"
},
"data_alteracao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {
"id": 0,
"numero": 0,
"nome": "string"
},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {
"saldo_inicial": "string",
"nosso_numero": 0,
"ailos": {},
"boleto_informacoes_personalizadas": "string",
"boleto_demonstrativo_1": "string",
"boleto_demonstrativo_2": "string",
"boleto_demonstrativo_3": "string",
"boleto_informacoes_1": "string",
"boleto_informacoes_2": "string",
"boleto_informacoes_3": "string",
"boleto_informacoes_4": "string",
"banco_da_amazonia": { },
"banco_do_brasil": {},
"banco_do_nordeste": { },
"banco_inter": {},
"banco_real": { },
"banestes": { },
"banrisul": {},
"bradesco": {},
"caixa_economica_federal": {},
"citibank": { },
"hsbc": {},
"itau": {},
"santander": {},
"sicoob": {},
"sicredi": {},
"unicred": {},
"banco_safra": {}
},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
}
Recuperar conta
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/contas/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {
"id": 0,
"numero": 0,
"nome": "string"
},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {
"saldo_inicial": "string",
"nosso_numero": 0,
"ailos": {},
"boleto_informacoes_personalizadas": "string",
"boleto_demonstrativo_1": "string",
"boleto_demonstrativo_2": "string",
"boleto_demonstrativo_3": "string",
"boleto_informacoes_1": "string",
"boleto_informacoes_2": "string",
"boleto_informacoes_3": "string",
"boleto_informacoes_4": "string",
"banco_da_amazonia": { },
"banco_do_brasil": {},
"banco_do_nordeste": { },
"banco_inter": {},
"banco_real": { },
"banestes": { },
"banrisul": {},
"bradesco": {},
"caixa_economica_federal": {},
"citibank": { },
"hsbc": {},
"itau": {},
"santander": {},
"sicoob": {},
"sicredi": {},
"unicred": {},
"banco_safra": {}
},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
}
Editar conta
Atualiza as informações da conta.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ativo	
integer
Default: 1
Enum: 0 1 2
0=Inativa 1=Ativa 2=Visivel somente em relatórios

nome	
string
banco	
integer
Campo identificador do banco, saiba como recuperar bancos clicando aqui

agencia	
string
agencia_digito	
string
carteira	
string
conta	
string
conta_digito	
string
conta_cobranca	
string
contato	
string
contrato	
string
convenio	
string
observacoes	
string
ua	
string
num_transmissao	
string <= 20 characters
num_seq_boleto	
string
modalidade_carteira	
integer
Enum: 1 2 3
1=Simples

2=Vinculada / Caucionada

3=Descontada

tipo_carteira	
string
impressao_logo	
boolean
dados_adicionais	
object <= 1 characters
Para alguns bancos devem ser informadas alguns dados adicionais. Abaixo estão listados todos os bancos e seus respectivos campos adicionais.

data_alteracao	
string
Responses
200 Conta alterada!

PATCH
/contas/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ativo": 0,
"nome": "string",
"banco": 0,
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {
"ailos": {},
"banco_da_amazonia": { },
"banco_do_brasil": {},
"banco_do_nordeste": { },
"banco_inter": {},
"banco_real": { },
"banestes": { },
"banrisul": {},
"bradesco": {},
"caixa_economica_federal": {},
"citibank": { },
"hsbc": {},
"itau": {},
"santander": {},
"sicoob": {},
"sicredi": {},
"unicred": { },
"boleto_informacoes_personalizadas": true,
"boleto_demonstrativo_1": "string",
"boleto_demonstrativo_2": "string",
"boleto_demonstrativo_3": "string",
"boleto_informacoes_1": "string",
"boleto_informacoes_2": "string",
"boleto_informacoes_3": "string",
"boleto_informacoes_4": "string"
},
"data_alteracao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {
"id": 0,
"numero": 0,
"nome": "string"
},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {
"saldo_inicial": "string",
"nosso_numero": 0,
"ailos": {},
"boleto_informacoes_personalizadas": "string",
"boleto_demonstrativo_1": "string",
"boleto_demonstrativo_2": "string",
"boleto_demonstrativo_3": "string",
"boleto_informacoes_1": "string",
"boleto_informacoes_2": "string",
"boleto_informacoes_3": "string",
"boleto_informacoes_4": "string",
"banco_da_amazonia": { },
"banco_do_brasil": {},
"banco_do_nordeste": { },
"banco_inter": {},
"banco_real": { },
"banestes": { },
"banrisul": {},
"bradesco": {},
"caixa_economica_federal": {},
"citibank": { },
"hsbc": {},
"itau": {},
"santander": {},
"sicoob": {},
"sicredi": {},
"unicred": {},
"banco_safra": {}
},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
}
Apagar conta
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Conta apagada!

DELETE
/contas/{id}
Gerar certificado banco inter
Gerar certificado banco inter

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id	
integer
aplicacao	
string
senha_certificado_inter	
string
Responses
201 Conta criada!

POST
/contas/gerar_certificado
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id": 0,
"aplicacao": "string",
"senha_certificado_inter": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"aplicacao": "string",
"senha_certificado_inter": "string"
}
Planos Orçamentarios
Listar planos orçamentários
Responses
200 Sucesso!

GET
/planos_orcamentarios
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {},
"classificacao_dre": {},
"data_alteracao": "string"
}
]
Criar planos orçamentários
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome
required
string
plano_orcamentario_pai
required
integer
Plano Orçamentário Pai Ex: Vendas Brinquedos pertence ao plano Vendas que por sua vez pertence ao Plano Crédito.

tipo
required
string
Enum: "E" "S"
posicao	
string
protegido	
boolean
Default: false
classificacao_dre	
integer
ID da Classificação DRE

data_alteracao	
string
Responses
201 Plano Orçamentário criado!

POST
/planos_orcamentarios
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": 0,
"classificacao_dre": 0,
"data_alteracao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {
"id": 0,
"nome": "string"
},
"classificacao_dre": {
"id": 0,
"descricao": "string"
},
"data_alteracao": "string"
}
Recuperar plano orçamentário
Recupera um planos_orcamentario.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/planos_orcamentarios/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {
"id": 0,
"nome": "string"
},
"classificacao_dre": {
"id": 0,
"descricao": "string"
},
"data_alteracao": "string"
}
Editar plano orçamentário
Atualiza as informações do planos_orcamentario.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
posicao	
string
tipo	
string
Enum: "E" "S"
protegido	
boolean
Default: false
plano_orcamentario_pai	
integer
Plano Orçamentário Pai Ex: Vendas Brinquedos pertence ao plano Vendas que por sua vez pertence ao Plano Crédito.

classificacao_dre	
integer
ID da Classificação DRE

data_alteracao	
string
Responses
200 Planos Orçamentário alterado!

PATCH
/planos_orcamentarios/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": 0,
"classificacao_dre": 0,
"data_alteracao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {
"id": 0,
"nome": "string"
},
"classificacao_dre": {
"id": 0,
"descricao": "string"
},
"data_alteracao": "string"
}
Apagar plano orçamentário
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Plano Orçamentário apagado!

DELETE
/planos_orcamentarios/{id}
Alterar arranjo de plano orçamentario
Alterar a configuração de posições do plano orçamentário por completo

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id	
integer
Id do Plano Orçamentário.

plano_orcamentario_pai	
integer
Plano Orçamentário Pai Ex: Vendas Brinquedos pertence ao plano Vendas que por sua vez pertence ao Plano Crédito.

posicao	
string
Posição dentro do arranjo de planos orçamentários

tipo	
string
Enum: "E" "S"
E=Entrada S=Saída

Responses
200 Sucesso!

POST
/planos_orcamentarios/lista
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"plano_orcamentario_pai": 0,
"posicao": "string",
"tipo": "E"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"nome": "string",
"posicao": "string",
"tipo": "E",
"protegido": false,
"plano_orcamentario_pai": {},
"classificacao_dre": {},
"data_alteracao": "string"
}
]
Recuperar Classificações de DRE
Recupera um lista de classificações DRE.

Responses
200 Sucesso!

GET
/planos_orcamentarios/classificacao_dre
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string"
}
]
Editar Associação de DRE
Alterar em massa a classificação de DRE dos planos orçamentários

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
plano_orcamentario	
integer
ID do Plano Orçamentário

classificacao_dre	
integer
ID da Classificacao DRE

Responses
200 Sucesso!

POST
/planos_orcamentarios/associar_dre
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"plano_orcamentario": 0,
"classificacao_dre": 0
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Impressão dos Planos Orçamentarios
Impressão dos Planos Orçamentarios em A4 PDF

Responses
200 Retorna impressão dos Planos Orçamentarios no formato PDF

GET
/planos_orcamentarios/pdf/impressao
Impressão Associação DRE
Impressão dos Planos Orçamentarios associados ao DRE em A4 PDF

Responses
200 Retorna os Planos Orçamentarios associados ao DRE no formato PDF

GET
/planos_orcamentarios/pdf/impressao_associacao_dre
bancos
Listar bancos
Responses
200 Sucesso!

GET
/bancos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"numero": 0,
"nome": "string"
}
]
Recuperar banco
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/bancos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"numero": 0,
"nome": "string"
}
Listar todos os bancos em operação no Brasil
Responses
200 Sucesso!

GET
/bancos/todos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"ISPB": 0,
"nome_reduzido": "string",
"numero_codigo": "string",
"participa_da_compe": "string",
"acesso_principal": "string",
"nome_extenso": "string",
"inicio_da_operacao": "string"
}
]
boletos
Criar boleto
Cria um boleto. Caso já exista um boleto com data de vencimento, cliente, valor cobrado, carteira da conta e forma de pagamento, iguais ao boleto a ser criado, retornará 200 com o registro de boleto com essas mesmas informações. Caso contrário, cria um novo registro e retorna 201.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
conta_bancaria
required
integer
ID da conta bancária.

forma_pagamento
required
integer
ID da forma de pagamento.

data_vencimento
required
string <date>
Data de vencimento.

numero
required
string
Número do boleto, o qual será usado para confirmações de pagamento no sistema.

valor_cobrado
required
number
Valor cobrado.

exportado	
boolean
Indica se boleto foi exportado para o banco.

mesclado	
boolean
Indica se boleto é mesclado

vinculado	
boolean
Indica se boleto esta vinculado a um lançamento financeiro

dados_adicionais	
object
Dados adicionais referentes ao Boleto

cliente	
integer
ID do cliente (sacado), saiba como recuperar clientes clicando aqui

entidade	
integer
ID da entidade

valor_desconto	
number
Valor de desconto.

cod_servico	
string
Código do serviço.

demonstrativo_1	
string
Informações sobre o boleto.

demonstrativo_2	
string
Informações sobre o boleto.

demonstrativo_3	
string
Informações sobre o boleto.

instrucoes_1	
string
Informações sobre o boleto.

instrucoes_2	
string
Informações sobre o boleto.

instrucoes_3	
string
Informações sobre o boleto.

instrucoes_4	
string
Informações sobre o boleto.

lancamento_financeiro_vinculado	
integer
ID do lançamento financeiro a vincular.

fatura_parcela_vinculada	
integer
ID da parcela vinculada.

contrato	
integer
ID do contrato a vincular.

Responses
200 Boleto já existente recuperado!
201 Boleto criado!

POST
/boletos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"data_vencimento": "2019-08-24",
"exportado": true,
"mesclado": true,
"vinculado": true,
"dados_adicionais": { },
"cliente": 0,
"entidade": 0,
"numero": "string",
"valor_cobrado": 0,
"valor_desconto": 0,
"cod_servico": "string",
"demonstrativo_1": "string",
"demonstrativo_2": "string",
"demonstrativo_3": "string",
"instrucoes_1": "string",
"instrucoes_2": "string",
"instrucoes_3": "string",
"instrucoes_4": "string",
"lancamento_financeiro_vinculado": 0,
"conta_bancaria": 0,
"fatura_parcela_vinculada": 0,
"forma_pagamento": 0,
"contrato": 0
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"data_vencimento": "2019-08-24",
"exportado": true,
"mesclado": true,
"vinculado": true,
"dados_adicionais": { },
"cliente": {
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"entidade": {
"id": 0,
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"numero": "string",
"valor_cobrado": 0,
"valor_desconto": 0,
"valor_pago": 0,
"data_criacao": "2019-08-24",
"registrado": true,
"numero_banco": 0,
"conta": 0,
"conta_dv": 0,
"agencia": 0,
"agencia_dv": 0,
"carteira": "string",
"convenio": "string",
"cod_servico": "string",
"demonstrativo_1": "string",
"demonstrativo_2": "string",
"demonstrativo_3": "string",
"instrucoes_1": "string",
"instrucoes_2": "string",
"instrucoes_3": "string",
"instrucoes_4": "string",
"link": "string",
"pagamento_confirmado": true,
"linha_digitavel": "string",
"lancamento_financeiro_vinculado": {
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {},
"conta_bancaria": {},
"departamento": {},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {},
"funcionario_responsavel": {},
"tipo_entidade": "C",
"entidade": {},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [],
"boleto": [],
"fatura_parcela_vinculada": {},
"anexos": []
},
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"fatura_parcela_vinculada": {
"id": 0,
"parcela": 0,
"valor_parcela": 0,
"data_vencimento": "string",
"documento": "string",
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"lancamento_financeiro_vinculado": {},
"cAut": "string"
},
"forma_pagamento": {
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
},
"contrato": {
"id": 0,
"numero": 0,
"situacao": "",
"cancelado": true,
"data_criacao": "string",
"hora_criacao": "string",
"hora_fechamento": "string",
"data_inicio": "string",
"data_termino": "string",
"data_termino_teste": "string",
"data_fechamento": "string",
"valor_desconto": 0,
"valor_total": 0,
"cliente": {},
"funcionario": {},
"vendedor": {},
"recorrencia_automatica": 0,
"recorrencia": "M",
"recorrencia_dia": 0,
"recorrencia_mes": 0,
"recorrencia_intervalo": 0,
"observacoes": "string",
"exibir_meu_plano": true,
"esconder_chat": true,
"itens": [],
"atividades": [],
"historico": []
}
}
Listar boletos
HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros 'since' e 'until' da query string, Ex: Se a data considerada do filtro since é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/boletos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"data_vencimento": "2019-08-24",
"exportado": true,
"mesclado": true,
"vinculado": true,
"dados_adicionais": { },
"cliente": {},
"entidade": {},
"numero": "string",
"valor_cobrado": 0,
"valor_desconto": 0,
"valor_pago": 0,
"data_criacao": "2019-08-24",
"registrado": true,
"numero_banco": 0,
"conta": 0,
"conta_dv": 0,
"agencia": 0,
"agencia_dv": 0,
"carteira": "string",
"convenio": "string",
"cod_servico": "string",
"demonstrativo_1": "string",
"demonstrativo_2": "string",
"demonstrativo_3": "string",
"instrucoes_1": "string",
"instrucoes_2": "string",
"instrucoes_3": "string",
"instrucoes_4": "string",
"link": "string",
"pagamento_confirmado": true,
"linha_digitavel": "string",
"lancamento_financeiro_vinculado": {},
"conta_bancaria": {},
"fatura_parcela_vinculada": {},
"forma_pagamento": {},
"contrato": {}
}
]
Recuperar boleto
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/boletos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"data_vencimento": "2019-08-24",
"exportado": true,
"mesclado": true,
"vinculado": true,
"dados_adicionais": { },
"cliente": {
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"entidade": {
"id": 0,
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"numero": "string",
"valor_cobrado": 0,
"valor_desconto": 0,
"valor_pago": 0,
"data_criacao": "2019-08-24",
"registrado": true,
"numero_banco": 0,
"conta": 0,
"conta_dv": 0,
"agencia": 0,
"agencia_dv": 0,
"carteira": "string",
"convenio": "string",
"cod_servico": "string",
"demonstrativo_1": "string",
"demonstrativo_2": "string",
"demonstrativo_3": "string",
"instrucoes_1": "string",
"instrucoes_2": "string",
"instrucoes_3": "string",
"instrucoes_4": "string",
"link": "string",
"pagamento_confirmado": true,
"linha_digitavel": "string",
"lancamento_financeiro_vinculado": {
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {},
"conta_bancaria": {},
"departamento": {},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {},
"funcionario_responsavel": {},
"tipo_entidade": "C",
"entidade": {},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [],
"boleto": [],
"fatura_parcela_vinculada": {},
"anexos": []
},
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"fatura_parcela_vinculada": {
"id": 0,
"parcela": 0,
"valor_parcela": 0,
"data_vencimento": "string",
"documento": "string",
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"lancamento_financeiro_vinculado": {},
"cAut": "string"
},
"forma_pagamento": {
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
},
"contrato": {
"id": 0,
"numero": 0,
"situacao": "",
"cancelado": true,
"data_criacao": "string",
"hora_criacao": "string",
"hora_fechamento": "string",
"data_inicio": "string",
"data_termino": "string",
"data_termino_teste": "string",
"data_fechamento": "string",
"valor_desconto": 0,
"valor_total": 0,
"cliente": {},
"funcionario": {},
"vendedor": {},
"recorrencia_automatica": 0,
"recorrencia": "M",
"recorrencia_dia": 0,
"recorrencia_mes": 0,
"recorrencia_intervalo": 0,
"observacoes": "string",
"exibir_meu_plano": true,
"esconder_chat": true,
"itens": [],
"atividades": [],
"historico": []
}
}
Apagar boleto
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Boleto apagado!

DELETE
/boletos/{id}
Boleto PDF
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Retorna a boleto na base64, a linha digitavel ou a url pra visualização do boleto

GET
/boletos/pdf/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"base64": "string",
"linha_digitavel": "string",
"url": "string"
}
Vincular financeiro
Vincula lançamento financeiro a boleto.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id_financeiro	
integer
Id do lançamento financeiro ao qual o boleto será vinculado.

Responses
200 Lançamento financeiro vinculado!

PATCH
/boletos/vincular_financeiro/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id_financeiro": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"data_vencimento": "2019-08-24",
"exportado": true,
"mesclado": true,
"vinculado": true,
"dados_adicionais": { },
"cliente": {
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"entidade": {
"id": 0,
"razao_social": "string",
"cpf": "string",
"cnpj": "string"
},
"numero": "string",
"valor_cobrado": 0,
"valor_desconto": 0,
"valor_pago": 0,
"data_criacao": "2019-08-24",
"registrado": true,
"numero_banco": 0,
"conta": 0,
"conta_dv": 0,
"agencia": 0,
"agencia_dv": 0,
"carteira": "string",
"convenio": "string",
"cod_servico": "string",
"demonstrativo_1": "string",
"demonstrativo_2": "string",
"demonstrativo_3": "string",
"instrucoes_1": "string",
"instrucoes_2": "string",
"instrucoes_3": "string",
"instrucoes_4": "string",
"link": "string",
"pagamento_confirmado": true,
"linha_digitavel": "string",
"lancamento_financeiro_vinculado": {
"id": 0,
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "string",
"forma_pagamento": {},
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"valor_total": 0,
"plano_orcamentario": {},
"conta_bancaria": {},
"departamento": {},
"item_fatura": 0,
"transferencia": false,
"data_alteracao": "2019-08-24T14:15:22Z",
"data_lancamento": "string",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"funcionario": {},
"funcionario_responsavel": {},
"tipo_entidade": "C",
"entidade": {},
"parcela": 0,
"total_parcelas": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": {},
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": [],
"boleto": [],
"fatura_parcela_vinculada": {},
"anexos": []
},
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"fatura_parcela_vinculada": {
"id": 0,
"parcela": 0,
"valor_parcela": 0,
"data_vencimento": "string",
"documento": "string",
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"lancamento_financeiro_vinculado": {},
"cAut": "string"
},
"forma_pagamento": {
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
},
"contrato": {
"id": 0,
"numero": 0,
"situacao": "",
"cancelado": true,
"data_criacao": "string",
"hora_criacao": "string",
"hora_fechamento": "string",
"data_inicio": "string",
"data_termino": "string",
"data_termino_teste": "string",
"data_fechamento": "string",
"valor_desconto": 0,
"valor_total": 0,
"cliente": {},
"funcionario": {},
"vendedor": {},
"recorrencia_automatica": 0,
"recorrencia": "M",
"recorrencia_dia": 0,
"recorrencia_mes": 0,
"recorrencia_intervalo": 0,
"observacoes": "string",
"exibir_meu_plano": true,
"esconder_chat": true,
"itens": [],
"atividades": [],
"historico": []
}
}
Imprimir Listagem de Boletos
'Imprimir Listagem de Pedidos/Orçamentos'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de Boletos no formato PDF

POST
/boletos/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Mesclar Boletos
'Mesclagem de Boletos'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
cliente	
integer
Id do cliente ao qual o boleto será vinculado.

forma_pagamento	
integer
Id da forma de pagamento que será vinculada ao boleto.

data_vencimento	
string
Data de vencimento que será vinculada ao boleto.

data_inicial	
string
Data inicial que serão buscados boletos para mesclagem.

data_final	
string
Data final que serão buscados boletos para mesclagem.

Responses
200 Retorna o numero do boleto, a linha digitavel ou a url pra visualização do boleto

POST
/boletos/mesclar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"cliente": 0,
"forma_pagamento": 0,
"data_vencimento": "string",
"data_inicial": "string",
"data_final": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"base64": "string",
"linha_digitavel": "string",
"url": "string"
}
Enviar e-mail Boletos
'Enviar boleto por e-mail'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids
required
Array of integers
Ids dos boletos

emails	
Array of strings
Array com os e-mails para onde serão enviados os boletos.

enviar_para_todos	
boolean
Default: false
Se verdadeiro, irá enviar e-mail para o e-mail principal do cliente com cópia oculta para todos os e-mails descritos no campo 'e-mails'. Se for falso o campo emails é obrigatório

Responses
200 Sucesso!

POST
/boletos/enviar_email
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
],
"emails": [
"string"
],
"enviar_para_todos": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"success": [
{}
],
"errors": [
{}
]
}
Exportar Boletos
'Exporta boletos para registro'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
conta_bancaria
required
integer
ID da conta bancária vinculada aos boletos

cliente	
Array of integers
ID's dos clientes vinculados aos boletos

boletos	
Array of integers
ID's dos boletos a serem exportados (todos devem ter a mesma conta bancária vinculada)

data_considerada	
any
Enum: "C" "V"
Indica a data considera ao filtrar os boletos: Criação, Vencimento.

data_inicial	
string
Data inicial que serão buscados boletos para registro.

data_final	
string
Data final que serão buscados boletos para registro.

layout	
any
Enum: "" "CNAB240" "CNAB400"
Indica o formato do arquivo de remessa que será gerado. Caso não seja informado, o layout considerado será o CNAB240.

busca_nao_exportados	
boolean
Se marcado como true, traz apenas os boletos que não foram exportados.

Responses
200 Retorna o arquivo de registro de boletos

POST
/boletos/exportar
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"conta_bancaria": 0,
"cliente": [
0
],
"boletos": [
0
],
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"layout": "",
"busca_nao_exportados": true
}
Tipos de Contatos
Listar tipos de contatos
Responses
200 Sucesso!

GET
/tipos_contatos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"descricao": "Telefone"
}
]
Criar tipo de contato
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição do tipo contato. Ex: E-mail, Telefone, Fax, etc...

tipo	
string
Enum: "T" "E" "O"
T=Telefone | E=E-mail | O=Outros

vinculado	
boolean
Responses
201 Tipo de contato criado!

POST
/tipos_contatos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"tipo": "T",
"descricao": "string",
"vinculado": true
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Telefone"
}
Recuperar tipo de contato
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/tipos_contatos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Telefone"
}
Apagar um tipo de contato
Apaga um tipo de contato específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/tipos_contatos/{id}
Editar tipo de contato
Atualiza as informações do tipo de contato.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
tipo	
string
Enum: "T" "E" "O"
T=Telefone | E=E-mail | O=Outros

descricao	
string
Descrição do tipo contato. Ex: E-mail, Telefone, Fax, etc...

vinculado	
boolean
Responses
200 Tipo de contato alterado!

PATCH
/tipos_contatos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"tipo": "T",
"descricao": "string",
"vinculado": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Telefone"
}
Tipos de cadastros
Os tipos de cadastros são utilizados para diferenciar contatos e endereços de um cliente ou fornecedor. Ex: comercial, residencial e entrega.

Listar tipos de cadastros
Responses
200 Sucesso!

GET
/tipos_cadastros
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"descricao": "Comercial"
}
]
Criar tipo cadastro
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição do tipo cadastro. Ex: Comercial, Entrega, Residencial, etc...

Responses
201 Tipo cadastro criado!

POST
/tipos_cadastros
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao": "string"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Comercial"
}
Recuperar tipo de cadastro
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/tipos_cadastros/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Comercial"
}
Editar tipo cadastro
Atualiza as informações do tipo cadastro.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao	
string
Descrição do tipo cadastro. Ex: Comercial, Entrega, Residencial, etc...

Responses
200 Tipo cadastro alterada!

PATCH
/tipos_cadastros/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao": "string"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Comercial"
}
Apagar tipo cadastro
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Tipo cadastro apagada!

DELETE
/tipos_cadastros/{id}
departamentos
Listar departamentos
Responses
200 Sucesso!

GET
/departamentos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"descricao": "VENDAS"
}
]
Criar departamento
Cria um departamento

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição/Nome do departamento. Ex: Administrativo.

Responses
201 Departamento criado!

POST
/departamentos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao": "VENDAS"
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "VENDAS"
}
Recupera um departamento
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200

GET
/departamentos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "VENDAS"
}
Editar departamento
Atualiza as informações de um departamento

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao	
string
Descrição/Nome do departamento. Ex: Administrativo.

Responses
200 Departamento alterado!

PATCH
/departamentos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao": "VENDAS"
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "VENDAS"
}
Apagar departamento
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Departamento apagado!

DELETE
/departamentos/{id}
unidades
Listar unidades
Responses
200 Sucesso!

GET
/unidades
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"descricao": "Unidade",
"padrao": true,
"fracionado": true,
"vinculado": true
}
]
Criar unidade
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Nome da unidade.

sigla
required
string [ 1 .. 6 ] characters
Sigla da unidade. Ex: Unidade Quilograma, sigla KG.

fracionado
required
boolean
Indica se a unidade é fracionada, unidades fracionadas permitem a saida ou entrada fracionada de produtos. Ex: A unidade do produto Farinha é KG fracionada, será possível indicar 0,500 KG de Farinha.

padrao	
boolean
Indica a unidade padrão do sistema, apenas uma unidade pode ser padrão, essa unidade será carregada automaticamente nos formulários em sua abertura. true quando é padrão | false" quando não é padrão.

vinculado	
boolean
Indica se a unidade possui vinculos no sistema. true quando tem vinculos | false" quando não tem vinculos.

Responses
201 Unidade criada!

POST
/unidades
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"sigla": "string",
"descricao": "string",
"fracionado": true,
"padrao": true,
"vinculado": true
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Unidade",
"padrao": true,
"fracionado": true,
"vinculado": true
}
Recuperar unidade
Recupera um unidade.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/unidades/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Unidade",
"padrao": true,
"fracionado": true,
"vinculado": true
}
Editar unidade
Atualiza as informações do unidade.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
sigla	
string [ 1 .. 6 ] characters
Sigla da unidade. Ex: Unidade Quilograma, sigla KG.

descricao	
string
Nome da unidade.

fracionado	
boolean
Indica se a unidade é fracionada, unidades fracionadas permitem a saida ou entrada fracionada de produtos. Ex: A unidade do produto Farinha é KG fracionada, será possível indicar 0,500 KG de Farinha.

padrao	
boolean
Indica a unidade padrão do sistema, apenas uma unidade pode ser padrão, essa unidade será carregada automaticamente nos formulários em sua abertura. true quando é padrão | false" quando não é padrão.

vinculado	
boolean
Indica se a unidade possui vinculos no sistema. true quando tem vinculos | false" quando não tem vinculos.

Responses
200 Unidade alterada!

PATCH
/unidades/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"sigla": "string",
"descricao": "string",
"fracionado": true,
"padrao": true,
"vinculado": true
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 1,
"descricao": "Unidade",
"padrao": true,
"fracionado": true,
"vinculado": true
}
Apagar unidade
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Unidade apagada!

DELETE
/unidades/{id}
categorias
Listar categorias
Responses
200 Sucesso!

GET
/categorias
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {}
}
]
Criar categoria
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição da categoria. Ex: Doces, Alimentos, Carros, Veiculos...

tipo
required
string
Enum: "P" "S"
Define se a categoria será de produto ou de serviço P=Produto | S=Serviço |

localizacao	
string
Localização dessa categoria. Ex: Doces estão na plateleira do corredor D2.

categoria_mae	
integer
ID da categoria mãe.

Responses
201 Categoria criado!

POST
/categorias
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": 0
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {
"id": 0,
"descricao": "string",
"localizacao": "string"
}
}
Recuperar categoria
Recupera um categoria.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/categorias/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {
"id": 0,
"descricao": "string",
"localizacao": "string"
}
}
Editar categoria
Atualiza as informações do categoria.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao	
string
Descrição da categoria. Ex: Doces, Alimentos, Carros, Veiculos...

localizacao	
string
Localização dessa categoria. Ex: Doces estão na plateleira do corredor D2.

tipo	
string
Enum: "P" "S"
Define se a categoria será de produto ou de serviço P=Produto | S=Serviço |

categoria_mae	
integer
ID da categoria mãe.

Responses
200 Categoria alterada!

PATCH
/categorias/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"localizacao": "string",
"tipo": "P",
"categoria_mae": {
"id": 0,
"descricao": "string",
"localizacao": "string"
}
}
Apagar categoria
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Categoria apagada!

DELETE
/categorias/{id}
enderecos
Listar enderecos
Responses
200 Sucesso!

GET
/enderecos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"exterior": true,
"cep": "string",
"logradouro": "string",
"bairro": "string",
"cidade": {},
"pais": {},
"ativo": true
}
]
Criar Endereco
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
cep
required
string
CEP do endereço, valor retornado possui mascará: 99999-999

logradouro
required
string
Nome do logradouro. Ex: Avenida Amazonas.

bairro
required
string
Nome do bairro do endereço.

id_cidade
required
integer
id_pais
required
integer
alterar_entidades	
boolean
Deve atualizar as entidades que possuem esse endereço? O padrão é não.

Responses
201 Endereco criado!

POST
/enderecos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"cep": "string",
"logradouro": "string",
"bairro": "string",
"id_cidade": 0,
"id_pais": 0,
"alterar_entidades": true
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {
"id": 0,
"codigo": 0,
"nome": "string",
"estado": {}
},
"pais": {
"id": 0,
"codigo": 0,
"nome": "string"
},
"informacoes_adicionais": "string",
"tipo_cadastro": {
"id": 1,
"descricao": "Comercial"
},
"id_entidade": 0
}
Retorna endereco
Responses
200 Sucesso!

GET
/enderecos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"exterior": true,
"cep": "string",
"logradouro": "string",
"bairro": "string",
"cidade": {
"id": 0,
"codigo": 0,
"nome": "string",
"estado": {}
},
"pais": {
"id": 0,
"codigo": 0,
"nome": "string"
},
"ativo": true
}
Editar Endereco
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
cep
required
string
CEP do endereço, valor retornado possui mascará: 99999-999

logradouro
required
string
Nome do logradouro. Ex: Avenida Amazonas.

bairro
required
string
Nome do bairro do endereço.

id_cidade
required
integer
id_pais
required
integer
alterar_entidades	
boolean
Deve atualizar as entidades que possuem esse endereço? O padrão é não.

Responses
201 Endereco alterado!

POST
/enderecos/nova_alteracao/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"cep": "string",
"logradouro": "string",
"bairro": "string",
"id_cidade": 0,
"id_pais": 0,
"alterar_entidades": true
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"principal": true,
"exterior": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"cidade": {
"id": 0,
"codigo": 0,
"nome": "string",
"estado": {}
},
"pais": {
"id": 0,
"codigo": 0,
"nome": "string"
},
"informacoes_adicionais": "string",
"tipo_cadastro": {
"id": 1,
"descricao": "Comercial"
},
"id_entidade": 0
}
Tributos Referência
Listar tributos referência
Responses
200 Sucesso!

GET
/tributos_referencia
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_empresa": 0,
"pis": 0,
"cofins": 0,
"irpj": 0,
"ipi": 0,
"icms": 0,
"csll": 0,
"cpp": 0,
"deducoes": 0,
"pis_retido": 0,
"cofins_retido": 0,
"inss_retido": 0,
"ir_retido": 0,
"csll_retido": 0,
"iss_retido": 0,
"outras_retencoes": 0
}
]
Atualizar tributos referência
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
id
required
integer
id_empresa
required
integer
pis
required
number
cofins
required
number
irpj
required
number
ipi
required
number
icms
required
number
csll
required
number
cpp
required
number
deducoes
required
number
pis_retido
required
number
cofins_retido
required
number
inss_retido
required
number
ir_retido
required
number
csll_retido
required
number
iss_retido
required
number
outras_retencoes
required
number
Responses
200 Tributo referência atualizado!

PUT
/tributos_referencia
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"id": 0,
"id_empresa": 0,
"pis": 0,
"cofins": 0,
"irpj": 0,
"ipi": 0,
"icms": 0,
"csll": 0,
"cpp": 0,
"deducoes": 0,
"pis_retido": 0,
"cofins_retido": 0,
"inss_retido": 0,
"ir_retido": 0,
"csll_retido": 0,
"iss_retido": 0,
"outras_retencoes": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_empresa": 0,
"pis": 0,
"cofins": 0,
"irpj": 0,
"ipi": 0,
"icms": 0,
"csll": 0,
"cpp": 0,
"deducoes": 0,
"pis_retido": 0,
"cofins_retido": 0,
"inss_retido": 0,
"ir_retido": 0,
"csll_retido": 0,
"iss_retido": 0,
"outras_retencoes": 0
}
]
Operações Interestaduais
Recupera Operações Interestaduais
Responses
200 Sucesso!

GET
/operacoes_interestaduais
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_localidade_estado": 0,
"estado": "string",
"uf": "string",
"icms_interestadual": 0,
"realiza_operacoes": true
}
]
Atualiza Operações Interestaduais
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
Array 
id
required
integer
id_localidade_estado
required
integer
ID do Estado.

estado
required
string
Estado.

uf
required
string
icms_interestadual
required
number
realiza_operacoes
required
boolean
Responses
200 Operações Interestaduais atualizadas!

PUT
/operacoes_interestaduais
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_localidade_estado": 0,
"estado": "string",
"uf": "string",
"icms_interestadual": 0,
"realiza_operacoes": true
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_localidade_estado": 0,
"estado": "string",
"uf": "string",
"icms_interestadual": 0,
"realiza_operacoes": true
}
]
tipos valor venda
Listar tipos valor venda
Responses
200 Sucesso!

GET
/tipos_valor_venda
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"padrao": true,
"nome": "Varejo",
"lucro": 100
}
]
Criar tipo valor venda
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome
required
string
Nome do valor de venda. Ex: Varejo

lucro
required
number
Indica a margem de lucro esperada ao realizar calculos de preços de revenda.

padrao	
boolean
Indica o valor de venda que é carregado por padrão quando usado no sistema.

Responses
201 Tipo valor venda criado!

POST
/tipos_valor_venda
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"padrao": true,
"nome": "Varejo",
"lucro": 100
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"padrao": true,
"nome": "Varejo",
"lucro": 100
}
Recuperar tipo valor venda
Recupera um tipo valor venda.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/tipos_valor_venda/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"padrao": true,
"nome": "Varejo",
"lucro": 100
}
Editar tipo valor venda
Atualiza as informações do tipo valor venda.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
padrao	
boolean
Indica o valor de venda que é carregado por padrão quando usado no sistema.

nome	
string
Nome do valor de venda. Ex: Varejo

lucro	
number
Indica a margem de lucro esperada ao realizar calculos de preços de revenda.

Responses
200 Tipo valor venda alterado!

PATCH
/tipos_valor_venda/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"padrao": true,
"nome": "Varejo",
"lucro": 100
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"padrao": true,
"nome": "Varejo",
"lucro": 100
}
Apagar tipo valor venda
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Tipo valor venda apagado!

DELETE
/tipos_valor_venda/{id}
Adicionar produtos ao ajuste de valor de venda
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ativo	
string or null
Enum: "0" "1" "3" ""
0=Não 1=Sim 3=Independe

sincroniza	
string or null
Enum: "0" "1" "3" ""
0=Não 1=Sim 3=Independe

comercializavel	
string or null
Enum: "0" "1" "3" ""
0=Não 1=Sim 3=Independe

vendido_separado	
string or null
Enum: "0" "1" "3" ""
0=Não 1=Sim 3=Independe

vinculacao	
Array of strings or null
Items Enum: "N" "C" "G" "K"
tipo_mercadoria	
Array of strings or null
Items Enum: "00" "01" "02" "03" "04" "05" "06" "07" "08" "10" "99"
data_considerada	
string or null
Default: "1"
Enum: "1" "2" ""
1=Data de Criação 2=Data de Alteração

data_inicial	
string
data_final	
string
data_periodo	
string or null
Enum: "1" "2" "3" "4" "5" "6" ""
1=Mês Atual 2=Mẽs Passado 3=Semana Atual 4=Semana Passada 5=Últimos 7 dias 6=Últimos 30 dias

fornecedor	
Array of integers or null
ncm	
Array of strings or null
categoria	
Array of integers or null
atributo	
Array of integers or null
nota	
Array of strings or null
ajuste_estoque	
Array of strings or null
Responses
200 Produtos valor de venda!

POST
/tipos_valor_venda/ajuste/adicionar_produtos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ativo": "0",
"sincroniza": "0",
"comercializavel": "0",
"vendido_separado": "0",
"vinculacao": [
"N"
],
"tipo_mercadoria": [
"00"
],
"data_considerada": "1",
"data_inicial": "string",
"data_final": "string",
"data_periodo": "1",
"fornecedor": [
0
],
"ncm": [
"string"
],
"categoria": [
0
],
"atributo": [
0
],
"nota": [
"string"
],
"ajuste_estoque": [
"string"
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"item": 0,
"produto": 0,
"valor_custo": 0,
"vinculacao": "N",
"valores_venda": []
}
]
Realizar ajuste de valor de venda
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
item
required
integer
produto
required
integer
valor_custo
required
number
vinculacao
required
string
Enum: "N" "C" "G" "K"
N=Normal C=Composição G=Grade K=Kit

valores_venda
required
Array of objects or null
Responses
200 Ajuste valor de venda!

POST
/tipos_valor_venda/ajuste
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"item": 0,
"produto": 0,
"valor_custo": 0,
"vinculacao": "N",
"valores_venda": []
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"item": 0,
"produto": 0,
"valor_custo": 0,
"vinculacao": "N",
"valores_venda": []
}
]
Modalidades de grade
Listar modalidades de grade
Responses
200 Sucesso!

GET
/modalidades_grade
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"id_modalidade": "string",
"tipo": "M",
"has_vinculo": true,
"grades": []
}
]
Criar modalidade de grade
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição da modalidade do produto grade. Ex: Cor, Tamanho...

tipo
required
string
Enum: "M" "G"
Tipo da modalidade de grade. M=Modalidade G=Grade

modalidade	
integer
ID da modalidade vinculada à grade.

descricao_grades	
Array of strings
Variações da modalidade do produto grade. Ex: Vermelho, G...

Responses
201 Modalidade de Grade criado!

POST
/modalidades_grade
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"modalidade": 0,
"descricao": "string",
"tipo": "M",
"descricao_grades": [
"string"
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"id_modalidade": "string",
"tipo": "M",
"has_vinculo": true,
"grades": [
null
]
}
Recuperar modalidade de grade
Recupera um modalidade de grade.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/modalidades_grade/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"id_modalidade": "string",
"tipo": "M",
"has_vinculo": true,
"grades": [
null
]
}
Editar modalidade de grade
Atualiza as informações do modalidade de grade.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição da modalidade do produto grade. Ex: Cor, Tamanho...

tipo
required
string
Enum: "M" "G"
Tipo da modalidade de grade. M=Modalidade G=Grade

id	
integer
id_modalidade	
string
Id da modalidade pai

has_vinculo	
boolean
Indica se grade está vinculada a algum produto

grades	
Array of any
Variações da modalidade do produto grade. Ex: Vermelho, G...

modalidade	
integer
ID da modalidade vinculada à grade.

Responses
200 Modalidade de Grade alterada!

PATCH
/modalidades_grade/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"id_modalidade": "string",
"tipo": "M",
"has_vinculo": true,
"grades": [
null
],
"modalidade": 0
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"descricao": "string",
"id_modalidade": "string",
"tipo": "M",
"has_vinculo": true,
"grades": [
null
]
}
Apagar modalidade de grade
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Modalidade de Grade apagada!

DELETE
/modalidades_grade/{id}
tributos ncm
Listar Tributos NCM
Responses
200 Sucesso!

GET
/tributos_ncm
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"ncm": "string",
"descricao": "string",
"nfce": {},
"tributo_detalhe": []
}
]
Criar Tributo NCM
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ncm
required
string = 8 characters
descricao
required
string
nfce	
object
Tributação utilizada para vendas em Cupom Fiscal (ECF), Nota Fiscal Série D (Modelo 02) e Nota Fiscal de Consumidor Eletrônica (NFC-e).

tributo_detalhe	
Array of objects
Indique aqui a tributação utilizada para emissão de NF-e's destinadas à Qualquer UF, separando-as por CFOP. Caso a mesma tributação seja para todos os CFOP's, digite 0.000 no campo CFOP.

Responses
201 Tributo NCM criado!

POST
/tributos_ncm
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ncm": "stringst",
"descricao": "string",
"nfce": {
"cest": "string",
"cfop": "",
"codigo_beneficio_fiscal": null,
"cst_b": "",
"modalidade_base_calculo_icms": "",
"aliquota_icms": 0,
"reducao_base_calculo_icms": 0,
"reducao_base_calculo_efetivo": 0,
"aliquota_icms_efetivo": 0,
"aliquota_icms_mono_retido": 0,
"csosn": "",
"aliquota_calculo_credito": 0,
"cst_pis": "",
"aliquota_pis": 0,
"cst_cofins": "",
"aliquota_cofins": 0,
"aliquota_ipi": 0,
"aliquota_fcp": 0,
"aliquota_icms_desonerado": 0,
"aliquota_icms_desonerado_st": 0,
"motivo_desonerado": "string",
"motivo_desonerado_st": "string",
"codigo_produto_anp": "string",
"descricao_produto_anp": "string",
"uf_consumo": "",
"percentual_glp_petroleo": 0,
"percentual_gas_natural_nacional": 0,
"percentual_gas_natural_importado": 0,
"valor_partida": 0,
"codigo_autorizacao": "string",
"quantidade_combustivel": 0,
"percent_indice_biodisel": 0,
"base_calculo_cide": 0,
"aliquota_cide": 0,
"valor_cide": 0,
"indicador_importacao": "0",
"uf_orig": "AC",
"percentual_uf_orig": 0,
"numero_bico": 0,
"numero_bomba": 0,
"numero_tanque": 0,
"valor_encerrante_inicial": 0,
"valor_encerrante_final": 0
},
"tributo_detalhe": [
{}
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ncm": "string",
"descricao": "string",
"nfce": {
"cest": "string",
"cfop": "0.000",
"codigo_beneficio_fiscal": "string",
"cst_b": "",
"modalidade_base_calculo_icms": "",
"aliquota_icms": 0,
"aliquota_icms_mono_retido": 0,
"reducao_base_calculo_icms": 0,
"reducao_base_calculo_efetivo": 0,
"aliquota_icms_efetivo": 0,
"csosn": "",
"aliquota_calculo_credito": 0,
"cst_pis": "",
"aliquota_pis": 0,
"cst_cofins": "",
"aliquota_cofins": 0,
"aliquota_ipi": 0,
"aliquota_fcp": 0,
"aliquota_icms_desonerado": 0,
"aliquota_icms_desonerado_st": 0,
"motivo_desonerado": "string",
"motivo_desonerado_st": "string",
"codigo_produto_anp": "string",
"descricao_produto_anp": "string",
"uf_consumo": "",
"percentual_glp_petroleo": 0,
"percentual_gas_natural_nacional": 0,
"percentual_gas_natural_importado": 0,
"valor_partida": 0,
"codigo_autorizacao": "string",
"quantidade_combustivel": 0,
"percent_indice_biodisel": 0,
"base_calculo_cide": 0,
"aliquota_cide": 0,
"valor_cide": 0,
"indicador_importacao": "0",
"uf_orig": "AC",
"percentual_uf_orig": 0,
"numero_bico": 0,
"numero_bomba": 0,
"numero_tanque": 0,
"valor_encerrante_inicial": 0,
"valor_encerrante_final": 0
},
"tributo_detalhe": [
{}
]
}
Recuperar Tributo NCM
Recupera um Tributo NCM.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/tributos_ncm/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ncm": "string",
"descricao": "string",
"nfce": {
"cest": "string",
"cfop": "0.000",
"codigo_beneficio_fiscal": "string",
"cst_b": "",
"modalidade_base_calculo_icms": "",
"aliquota_icms": 0,
"aliquota_icms_mono_retido": 0,
"reducao_base_calculo_icms": 0,
"reducao_base_calculo_efetivo": 0,
"aliquota_icms_efetivo": 0,
"csosn": "",
"aliquota_calculo_credito": 0,
"cst_pis": "",
"aliquota_pis": 0,
"cst_cofins": "",
"aliquota_cofins": 0,
"aliquota_ipi": 0,
"aliquota_fcp": 0,
"aliquota_icms_desonerado": 0,
"aliquota_icms_desonerado_st": 0,
"motivo_desonerado": "string",
"motivo_desonerado_st": "string",
"codigo_produto_anp": "string",
"descricao_produto_anp": "string",
"uf_consumo": "",
"percentual_glp_petroleo": 0,
"percentual_gas_natural_nacional": 0,
"percentual_gas_natural_importado": 0,
"valor_partida": 0,
"codigo_autorizacao": "string",
"quantidade_combustivel": 0,
"percent_indice_biodisel": 0,
"base_calculo_cide": 0,
"aliquota_cide": 0,
"valor_cide": 0,
"indicador_importacao": "0",
"uf_orig": "AC",
"percentual_uf_orig": 0,
"numero_bico": 0,
"numero_bomba": 0,
"numero_tanque": 0,
"valor_encerrante_inicial": 0,
"valor_encerrante_final": 0
},
"tributo_detalhe": [
{}
]
}
Editar Tributo NCM
Atualiza as informações do tributos NCM.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ncm	
string [ 2 .. 8 ] characters
descricao	
string
nfce	
object
Tributação utilizada para vendas em Cupom Fiscal (ECF), Nota Fiscal Série D (Modelo 02) e Nota Fiscal de Consumidor Eletrônica (NFC-e).

tributo_detalhe	
Array of objects
Indique aqui a tributação utilizada para emissão de NF-e's destinadas à Qualquer UF, separando-as por CFOP. Caso a mesma tributação seja para todos os CFOP's, digite 0.000 no campo CFOP.

Responses
200 Tributo NCM alterada!

PATCH
/tributos_ncm/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ncm": "string",
"descricao": "string",
"nfce": {
"cest": "string",
"cfop": "",
"codigo_beneficio_fiscal": "string",
"cst_b": "",
"modalidade_base_calculo_icms": "",
"aliquota_icms": 0,
"reducao_base_calculo_icms": 0,
"reducao_base_calculo_efetivo": 0,
"aliquota_icms_efetivo": 0,
"aliquota_icms_mono_retido": 0,
"csosn": "",
"aliquota_calculo_credito": 0,
"cst_pis": "",
"aliquota_pis": 0,
"cst_cofins": "",
"aliquota_cofins": 0,
"aliquota_ipi": 0,
"aliquota_fcp": 0,
"aliquota_icms_desonerado": 0,
"aliquota_icms_desonerado_st": 0,
"motivo_desonerado": "string",
"motivo_desonerado_st": "string",
"codigo_produto_anp": "string",
"descricao_produto_anp": "string",
"uf_consumo": "",
"percentual_glp_petroleo": 0,
"percentual_gas_natural_nacional": 0,
"percentual_gas_natural_importado": 0,
"valor_partida": 0,
"codigo_autorizacao": "string",
"quantidade_combustivel": 0,
"percent_indice_biodisel": 0,
"base_calculo_cide": 0,
"aliquota_cide": 0,
"valor_cide": 0,
"indicador_importacao": "0",
"uf_orig": "AC",
"percentual_uf_orig": 0,
"numero_bico": 0,
"numero_bomba": 0,
"numero_tanque": 0,
"valor_encerrante_inicial": 0,
"valor_encerrante_final": 0
},
"tributo_detalhe": [
{}
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ncm": "string",
"descricao": "string",
"nfce": {
"cest": "string",
"cfop": "0.000",
"codigo_beneficio_fiscal": "string",
"cst_b": "",
"modalidade_base_calculo_icms": "",
"aliquota_icms": 0,
"aliquota_icms_mono_retido": 0,
"reducao_base_calculo_icms": 0,
"reducao_base_calculo_efetivo": 0,
"aliquota_icms_efetivo": 0,
"csosn": "",
"aliquota_calculo_credito": 0,
"cst_pis": "",
"aliquota_pis": 0,
"cst_cofins": "",
"aliquota_cofins": 0,
"aliquota_ipi": 0,
"aliquota_fcp": 0,
"aliquota_icms_desonerado": 0,
"aliquota_icms_desonerado_st": 0,
"motivo_desonerado": "string",
"motivo_desonerado_st": "string",
"codigo_produto_anp": "string",
"descricao_produto_anp": "string",
"uf_consumo": "",
"percentual_glp_petroleo": 0,
"percentual_gas_natural_nacional": 0,
"percentual_gas_natural_importado": 0,
"valor_partida": 0,
"codigo_autorizacao": "string",
"quantidade_combustivel": 0,
"percent_indice_biodisel": 0,
"base_calculo_cide": 0,
"aliquota_cide": 0,
"valor_cide": 0,
"indicador_importacao": "0",
"uf_orig": "AC",
"percentual_uf_orig": 0,
"numero_bico": 0,
"numero_bomba": 0,
"numero_tanque": 0,
"valor_encerrante_inicial": 0,
"valor_encerrante_final": 0
},
"tributo_detalhe": [
{}
]
}
Apagar Tributo NCM
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Tributo NCM apagada!

DELETE
/tributos_ncm/{id}
Imprimir Listagem de NCMs
'Imprimir Listagem de NCMs'

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Retorna Listagem de NCM no formato PDF

POST
/tributos_ncm/pdf/listagem
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Recupera dados de código ANP do service auxiliar.
Responses
200 Sucesso!

GET
/tributos_ncm/codigo_anp_service
formas pagamento
Listar formas de pagamento
Responses
200 Sucesso!

GET
/formas_pagamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {}
}
]
Criar forma pagamento
Criar uma forma pagamento.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Nome para identificar a forma de pagamento

conta_bancaria
required
integer
ID da conta bancária vinculada a forma de pagamento.

forma_pagamento_base
required
integer
Enum: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22
Forma de Pagamento PDV. Forma de Pagamento que será utilizada no PDV. 1=Dinheiro 2=Cartao Debito 3=Cartao Credito 4=Cheque a Vista 5=Cheque a Prazo 6=Venda a Prazo 7=Venda a Vista 8=Boleto Bancário 9=Crédito Loja 10=Vale Alimentação 11=Vale Refeição 12=Vale Presente 13=Vale Combustível 14=Débito Bancário 15=Pagamento Instantâneo (PIX) - Dinâmico 16=Transferencia Bancária, Carteira Digital 17=Programa de fidelidade, Cashback, Crédito Virtual 18=Sem Pagamento 19=Outros 20=Pagamento Instantâneo (PIX) – Estático 21=Crédito em Loja 22=Pagamento Eletrônico não Informado - falha de hardware do sistema emissor

ativo	
integer
Default: 1
Enum: 0 1 2
Indica se a forma de pagamento está ativa. 0=Inativa 1=Ativa 2=Visível Somente em relatórios

indicador_forma_pagamento	
string
Enum: "0" "1"
Indicador da Forma de Pagamento. 0=Á Vista 1=À Prazo

tipo	
integer
Default: 0
Enum: 0 1 2 3
Tipo da Forma de Pagamento. 0=Pagamento e Recebimento 1=Somente Pagamento 2=Somente Recebimento 3=Somente Utilizada no Financeiro

confirmacao_financeiro	
integer
Default: 0
Enum: 0 1 2 3 4
Indica se o lançamento deve ser confirmado automaticamente no financeiro quando lançado através de compra, venda, devolução, etc.

0 - Nunca Confirmar

1 - Sempre Confirmar

2 - Confirmar Somente no Recebimento

3 - Confirmar Somente no Pagamento

4 - Não gerar financeiro

indicador_pergunta_faturamento	
boolean
Indica se o sistema deve exibir a pergunta sobre lançamento financeiro quando uma movimentação é confirmada

is_tagpix	
boolean
Indica se forma de pagamento é tagpix instantâneo

is_boleto_cobranca_pix	
boolean
Indica se forma de pagamento é tagpix boleto

tipo_boleto	
string
Value: "SB"
Tipo de Boleto CEF. Indica qual tipo de boleto da Caixa Econômica Federal deve ser gerado, SIGCB. SB=SIGCB

especie_boleto	
string
Default: "DM"
Enum: "DM" "DS"
Espécie do boleto. DM=Duplicata Mercantil DS=Duplicata de Serviço

carne	
boolean
Default: false
É um Carnê. Indica se a Forma de Pagamento deve permitir o controle e impressão de Carnê (Crediário). Caso a Forma de Pagamento seja movimentada, esta opção não poderá ser alterada.

duplicata	
boolean
Default: true
Exibir na NF-e (Duplicata). Indica que a forma de pagamento é uma Duplicata, e portanto deve ser impressa na DANFE e informada no XML da NF-e.

vencimento_dia_util	
boolean
Default: false
No vencimento, desconsiderar finais de semana.

gera_numero_boleto	
boolean
Default: false
Gerar Número Documento Automaticamente. Indica que o Número do Documento será gerado automaticamente tanto na Fatura quanto nos Lançamentos Financeiros.

email_automatico	
boolean
Default: false
Se deve enviar o boleto automaticamente por e-mail quando a nota for aprovada. (NFe/NFSe/NFCe)

operadora_cartao	
integer
Enum: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28
Operadora do cartão. 1=Visa 2=Mastercard 3=American Express 4=Sorocred 5=Diners Club 6=Elo 7=Hipercard 8=Aura 9=Cabal 10=Alelo 11=Banes Card 12=CalCard 13=Credz 14=Discover 15=GoodCard 16=GreenCard 17=Hiper 18=JcB 19=Mais 20=MaxVan 21=Policard 22=RedeCompras 23=Sodexo 24=ValeCard 25=Verocheque 26=VR 27=Ticket 28=Outros

operadora_taxa_operacao	
number
Taxa de Operação (%). Porcentagem cobrada da loja normalmente pela operadora de Cartão de Crédito/Débito.

credenciadora	
integer
Id da credenciadora vinculada a forma de pagamento.

qtd_max_parcelas	
integer
Default: 1
Nº Máximo de Parcelas.

intervalo_entre_parcelas	
integer
Intervalo Entre Parcelas. Intervalo de dias entre as parcelas lançadas nesta forma de pagamento.Não utilizado para TEF.

confirmar_primeira_parcela	
boolean
Considerar 1º Parcela. Indica se o Intervalo deve ser aplicado na primeira parcela.

juros_loja	
number
Juros da Loja (% ao mês). Juros que a loja cobra do cliente pelo parcelamento.

taxa_parcela	
number
Taxa por Parcela (R$). Taxa por parcela (valor único) que a loja cobra do cliente.

multa_atraso	
number
Multa Atraso (R$). Multa de valor único cobrado; deve ser aplicada sobre o valor da parcela, uma única vez.

mora_atraso	
number
Mora Atraso (% ao Dia). Multa em juros ao Dia cobrado pela loja do cliente, pelo atraso no pagamento da parcela. Para transformar sua taxa de juros ao mês para juros ao dia, utilize a fórmula: ((1 + % ao mês) elevado a 0,0333) -1.

taxa_banco	
number
Taxa Banco. Taxa cobrada da empresa pelo banco(ex: taxa por boleto emitido).

nome_inf1	
string
Nome da Informação 1.

nome_inf2	
string
Nome da Informação 2.

nome_inf3	
string
Nome da Informação 3.

data_alteracao	
string
Data de alteração

tipo_tef	
boolean
dias_compensacao	
integer
Dias para Compensação. Prazo para lançamento dos valores pagos à loja pela operadora em transações TEF. Ex: Se informado 30 , cada parcela do Cartão no TEF será lançada com 30 dias de prazo entre sí.

picpay_token	
string
Token de integração do PicPay. É necessário que a descrição dessa forma de pagamento seja exatamente 'PicPay'.

valores_taxa_parcelas	
Array of objects
possui_gerencianet	
boolean
Indica se a forma de pagamento possui GerenciaNet

client_id_gerencianet	
string
Client ID do GerenciaNet

client_secret_gerencianet	
string
Client Secret do GerenciaNet

pix_nome_recebedor	
string
Nome do recebedor do PIX

pix_expiracao	
string
tempo de expiração

pix_lancar_taxa	
integer
Enum: 0 1
Lança ou cria um novo lançamento da taxa do pix no financeiro 0=Desconta a taxa no lançamento financeiro 1=Cria um novo lançamento financeiro com a taxa

dias_apos_vencimento	
string
Quantidade de dias que o pix ficará ativo após o vencimento

modalidade_desconto	
integer
Enum: 1 2
Deve aplicar o desconto como valor fixo ou percentagem? (É aplicado em pix cobrança) 1=Valor Fixo 2=Porcentagem

valor_desconto	
number
Valor do desconto para aplicar (É aplicado em pix cobrança)

validade_desconto	
integer
Quantidade de dias antes da data de vencimento que o desconto vai ser aplicado (É aplicado em pix cobrança)

gerar_boleto	
boolean
Flag que indica se pode ser gerado boleto bancário para esta forma de pagamento.

instrumento_pagamento	
object
Responses
201 Forma pagamento criada!

POST
/formas_pagamento
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ativo": 0,
"descricao": "string",
"conta_bancaria": 0,
"forma_pagamento_base": 1,
"indicador_forma_pagamento": "0",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": 0,
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [
{},
{}
],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {
"id": 0,
"tipo": "string",
"razao_social": "string",
"cnpj": "string",
"cpf": "string",
"ie": "string",
"endereco": {}
}
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {
"id": 0,
"nome_empresa": "string",
"cnpj_empresa": "string"
},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [
{},
{}
],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {
"id": 0,
"ativo": true,
"tipo": "F",
"exterior": false,
"ie": "string",
"im": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"razao_social": "string",
"nome_fantasia": "string",
"responsavel": "string",
"rg": "string",
"extras": "string",
"endereco": "string",
"id_endereco": "string",
"id_endereco_entidade": "string",
"id_cliente": "string",
"id_empresa": "string",
"id_transportadora": "string",
"id_fornecedor": "string",
"id_funcionario": "string",
"cod_uf": "string",
"crt": "string",
"tipo_entidade": "string",
"suframa": "string",
"contatos": [],
"enderecos": []
}
}
Listar formas de pagamento base
Responses
200 Sucesso!

GET
/formas_pagamento_base
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"tpag": "string"
}
]
Recuperar formas de pagamento
Recupera uma forma de pagamento

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/formas_pagamento/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {
"id": 0,
"nome_empresa": "string",
"cnpj_empresa": "string"
},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [
{},
{}
],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {
"id": 0,
"ativo": true,
"tipo": "F",
"exterior": false,
"ie": "string",
"im": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"razao_social": "string",
"nome_fantasia": "string",
"responsavel": "string",
"rg": "string",
"extras": "string",
"endereco": "string",
"id_endereco": "string",
"id_endereco_entidade": "string",
"id_cliente": "string",
"id_empresa": "string",
"id_transportadora": "string",
"id_fornecedor": "string",
"id_funcionario": "string",
"cod_uf": "string",
"crt": "string",
"tipo_entidade": "string",
"suframa": "string",
"contatos": [],
"enderecos": []
}
}
Editar forma pagamento
Atualiza as informações do forma pagamento.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ativo	
integer
Default: 1
Enum: 0 1 2
Indica se a forma de pagamento está ativa. 0=Inativa 1=Ativa 2=Visível Somente em relatórios

descricao	
string
Nome para identificar a forma de pagamento

conta_bancaria	
integer
ID da conta bancária vinculada a forma de pagamento.

forma_pagamento_base	
integer
Enum: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22
Forma de Pagamento PDV. Forma de Pagamento que será utilizada no PDV. 1=Dinheiro 2=Cartao Debito 3=Cartao Credito 4=Cheque a Vista 5=Cheque a Prazo 6=Venda a Prazo 7=Venda a Vista 8=Boleto Bancário 9=Crédito Loja 10=Vale Alimentação 11=Vale Refeição 12=Vale Presente 13=Vale Combustível 14=Débito Bancário 15=Pagamento Instantâneo (PIX) - Dinâmico 16=Transferencia Bancária, Carteira Digital 17=Programa de fidelidade, Cashback, Crédito Virtual 18=Sem Pagamento 19=Outros 20=Pagamento Instantâneo (PIX) – Estático 21=Crédito em Loja 22=Pagamento Eletrônico não Informado - falha de hardware do sistema emissor

indicador_forma_pagamento	
string
Enum: "0" "1"
Indicador da Forma de Pagamento. 0=Á Vista 1=À Prazo

tipo	
integer
Default: 0
Enum: 0 1 2 3
Tipo da Forma de Pagamento. 0=Pagamento e Recebimento 1=Somente Pagamento 2=Somente Recebimento 3=Somente Utilizada no Financeiro

confirmacao_financeiro	
integer
Default: 0
Enum: 0 1 2 3 4
Indica se o lançamento deve ser confirmado automaticamente no financeiro quando lançado através de compra, venda, devolução, etc.

0 - Nunca Confirmar

1 - Sempre Confirmar

2 - Confirmar Somente no Recebimento

3 - Confirmar Somente no Pagamento

4 - Não gerar financeiro

indicador_pergunta_faturamento	
boolean
Indica se o sistema deve exibir a pergunta sobre lançamento financeiro quando uma movimentação é confirmada

is_tagpix	
boolean
Indica se forma de pagamento é tagpix instantâneo

is_boleto_cobranca_pix	
boolean
Indica se forma de pagamento é tagpix boleto

tipo_boleto	
string
Value: "SB"
Tipo de Boleto CEF. Indica qual tipo de boleto da Caixa Econômica Federal deve ser gerado, SIGCB. SB=SIGCB

especie_boleto	
string
Default: "DM"
Enum: "DM" "DS"
Espécie do boleto. DM=Duplicata Mercantil DS=Duplicata de Serviço

duplicata	
boolean
Default: true
Exibir na NF-e (Duplicata). Indica que a forma de pagamento é uma Duplicata, e portanto deve ser impressa na DANFE e informada no XML da NF-e.

vencimento_dia_util	
boolean
Default: false
No vencimento, desconsiderar finais de semana.

gera_numero_boleto	
boolean
Default: false
Gerar Número Documento Automaticamente. Indica que o Número do Documento será gerado automaticamente tanto na Fatura quanto nos Lançamentos Financeiros.

email_automatico	
boolean
Default: false
Se deve enviar o boleto automaticamente por e-mail quando a nota for aprovada. (NFe/NFSe/NFCe)

operadora_cartao	
integer
Enum: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28
Operadora do cartão. 1=Visa 2=Mastercard 3=American Express 4=Sorocred 5=Diners Club 6=Elo 7=Hipercard 8=Aura 9=Cabal 10=Alelo 11=Banes Card 12=CalCard 13=Credz 14=Discover 15=GoodCard 16=GreenCard 17=Hiper 18=JcB 19=Mais 20=MaxVan 21=Policard 22=RedeCompras 23=Sodexo 24=ValeCard 25=Verocheque 26=VR 27=Ticket 28=Outros

operadora_taxa_operacao	
number
Taxa de Operação (%). Porcentagem cobrada da loja normalmente pela operadora de Cartão de Crédito/Débito.

credenciadora	
integer
Id da credenciadora vinculada a forma de pagamento.

qtd_max_parcelas	
integer
Default: 1
Nº Máximo de Parcelas.

intervalo_entre_parcelas	
integer
Intervalo Entre Parcelas. Intervalo de dias entre as parcelas lançadas nesta forma de pagamento.Não utilizado para TEF.

confirmar_primeira_parcela	
boolean
Considerar 1º Parcela. Indica se o Intervalo deve ser aplicado na primeira parcela.

juros_loja	
number
Juros da Loja (% ao mês). Juros que a loja cobra do cliente pelo parcelamento.

taxa_parcela	
number
Taxa por Parcela (R$). Taxa por parcela (valor único) que a loja cobra do cliente.

multa_atraso	
number
Multa Atraso (R$). Multa de valor único cobrado; deve ser aplicada sobre o valor da parcela, uma única vez.

mora_atraso	
number
Mora Atraso (% ao Dia). Multa em juros ao Dia cobrado pela loja do cliente, pelo atraso no pagamento da parcela. Para transformar sua taxa de juros ao mês para juros ao dia, utilize a fórmula: ((1 + % ao mês) elevado a 0,0333) -1.

taxa_banco	
number
Taxa Banco. Taxa cobrada da empresa pelo banco(ex: taxa por boleto emitido).

nome_inf1	
string
Nome da Informação 1.

nome_inf2	
string
Nome da Informação 2.

nome_inf3	
string
Nome da Informação 3.

data_alteracao	
string
Data de alteração

tipo_tef	
boolean
dias_compensacao	
integer
Dias para Compensação. Prazo para lançamento dos valores pagos à loja pela operadora em transações TEF. Ex: Se informado 30 , cada parcela do Cartão no TEF será lançada com 30 dias de prazo entre sí.

picpay_token	
string
Token de integração do PicPay. É necessário que a descrição dessa forma de pagamento seja exatamente 'PicPay'.

valores_taxa_parcelas	
Array of objects
possui_gerencianet	
boolean
Indica se a forma de pagamento possui GerenciaNet

client_id_gerencianet	
string
Client ID do GerenciaNet

client_secret_gerencianet	
string
Client Secret do GerenciaNet

pix_nome_recebedor	
string
Nome do recebedor do PIX

pix_expiracao	
string
tempo de expiração

pix_lancar_taxa	
integer
Enum: 0 1
Lança ou cria um novo lançamento da taxa do pix no financeiro 0=Desconta a taxa no lançamento financeiro 1=Cria um novo lançamento financeiro com a taxa

dias_apos_vencimento	
string
Quantidade de dias que o pix ficará ativo após o vencimento

modalidade_desconto	
integer
Enum: 1 2
Deve aplicar o desconto como valor fixo ou percentagem? (É aplicado em pix cobrança) 1=Valor Fixo 2=Porcentagem

valor_desconto	
number
Valor do desconto para aplicar (É aplicado em pix cobrança)

validade_desconto	
integer
Quantidade de dias antes da data de vencimento que o desconto vai ser aplicado (É aplicado em pix cobrança)

gerar_boleto	
boolean
Flag que indica se pode ser gerado boleto bancário para esta forma de pagamento.

instrumento_pagamento	
object
Responses
200 Forma pagamento alterada!

PATCH
/formas_pagamento/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ativo": 0,
"descricao": "string",
"conta_bancaria": 0,
"forma_pagamento_base": 1,
"indicador_forma_pagamento": "0",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": 0,
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [
{},
{}
],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {
"id": 0,
"tipo": "string",
"razao_social": "string",
"cnpj": "string",
"cpf": "string",
"ie": "string",
"endereco": {}
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 0,
"ativo": 0,
"descricao": "string",
"conta_bancaria": {
"id": 0,
"ativo": 0,
"nome": "string",
"banco": {},
"agencia": "string",
"agencia_digito": "string",
"carteira": "string",
"conta": "string",
"conta_digito": "string",
"conta_cobranca": "string",
"contato": "string",
"contrato": "string",
"convenio": "string",
"observacoes": "string",
"ua": "string",
"num_transmissao": "string",
"num_seq_boleto": "string",
"modalidade_carteira": 1,
"tipo_carteira": "string",
"impressao_logo": true,
"dados_adicionais": {},
"data_alteracao": "string",
"saldo": 0,
"editavel": true
},
"forma_pagamento_base": 1,
"forma_pagamento_base_tpag": "string",
"indicador_forma_pagamento": "0",
"indicador": "string",
"tipo": 0,
"confirmacao_financeiro": 0,
"indicador_pergunta_faturamento": true,
"is_tagpix": true,
"is_boleto_cobranca_pix": true,
"tipo_boleto": "SB",
"especie_boleto": "DM",
"carne": false,
"duplicata": true,
"vencimento_dia_util": false,
"gera_numero_boleto": false,
"vinculo": false,
"email_automatico": false,
"operadora_cartao": 0,
"operadora_taxa_operacao": 0,
"credenciadora": {
"id": 0,
"nome_empresa": "string",
"cnpj_empresa": "string"
},
"qtd_max_parcelas": 1,
"intervalo_entre_parcelas": 0,
"confirmar_primeira_parcela": true,
"juros_loja": 0,
"taxa_parcela": 0,
"multa_atraso": 0,
"mora_atraso": 0,
"taxa_banco": 0,
"nome_inf1": "string",
"nome_inf2": "string",
"nome_inf3": "string",
"data_alteracao": "string",
"tipo_tef": true,
"dias_compensacao": 0,
"picpay_token": "string",
"valores_taxa_parcelas": [
{},
{}
],
"possui_gerencianet": true,
"client_id_gerencianet": "string",
"client_secret_gerencianet": "string",
"pix_nome_recebedor": "string",
"pix_chave": "string",
"pix_expiracao": "string",
"pix_lancar_taxa": 0,
"dias_apos_vencimento": "string",
"modalidade_desconto": 1,
"valor_desconto": 0,
"validade_desconto": 0,
"gerar_boleto": true,
"instrumento_pagamento": {
"id": 0,
"ativo": true,
"tipo": "F",
"exterior": false,
"ie": "string",
"im": "string",
"data_alteracao": "string",
"informacao_adicional": "string",
"recebe_email": true,
"cpf": "string",
"cnpj": "string",
"razao_social": "string",
"nome_fantasia": "string",
"responsavel": "string",
"rg": "string",
"extras": "string",
"endereco": "string",
"id_endereco": "string",
"id_endereco_entidade": "string",
"id_cliente": "string",
"id_empresa": "string",
"id_transportadora": "string",
"id_fornecedor": "string",
"id_funcionario": "string",
"cod_uf": "string",
"crt": "string",
"tipo_entidade": "string",
"suframa": "string",
"contatos": [],
"enderecos": []
}
}
Apagar forma pagamento
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Forma pagamento apagado!

DELETE
/formas_pagamento/{id}
Listar formas de pagamento
Responses
200 Sucesso!

GET
/formas_pagamento_bandeira
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_bandeira": "string",
"operadora": "string"
}
]
paises
Listar paises
Responses
200 Sucesso!

GET
/paises
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo": 0,
"nome": "string"
}
]
Recuperar pais
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/paises/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"codigo": 0,
"nome": "string"
}
Status e Atividades OS
Listar status e atividades da ordem de serviço
Responses
200 Sucesso!

GET
/status_atividades_os
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"tipo": "O",
"descricao": "string",
"padrao": false
}
]
Criar status ou atividade da ordem de serviço
Cria um status ou atividade da ordem de serviço

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
descricao
required
string
Descrição da atividade ou status.

tipo	
string
Default: "O"
Enum: "O" "I"
Utilize os seguintes códigos O=Status | I=Atividade

padrao	
boolean
Default: false
Definir como status ou atividade padrão

Responses
201 Status/Atividade criada!

POST
/status_atividades_os
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"status": "O",
"descricao": "Aguardando Reparo de Terceiros",
"padrao": false
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"tipo": "O",
"descricao": "string",
"padrao": false
}
Recuperar status ou atividade da ordem de serviço
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/status_atividades_os/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"tipo": "O",
"descricao": "string",
"padrao": false
}
Editar status ou atividade da ordem de serviço
Atualiza as informações do status ou atividade de ordem de serviço.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
tipo	
string
Default: "O"
Enum: "O" "I"
Utilize os seguintes códigos O=Status | I=Atividade

descricao	
string
Descrição da atividade ou status.

padrao	
boolean
Default: false
Definir como status ou atividade padrão

Responses
200 Status ou atividade de ordem de serviço alterada!

PATCH
/status_atividades_os/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
{
"status": "O",
"descricao": "Aguardando Reparo de Terceiros",
"padrao": false
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"tipo": "O",
"descricao": "string",
"padrao": false
}
Apagar status ou atividade de ordem de serviço
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Status ou atividade de ordem de serviço apagada!

DELETE
/status_atividades_os/{id}
CFOP's
Listar CFOP's
Responses
200 Sucesso!

GET
/cfops
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"cfop": "string",
"nome": "string",
"descricao": "string"
}
]
Recuperar todos CFOP's
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/cfops/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
{
"id": 0,
"cfop": "string",
"nome": "string",
"descricao": "string"
}
Dashboard
Dados dos relatórios da Dashboard

Financeiros | Evolução de receitas e despesas
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/evolucao_receitas_despesas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"receita": 0,
"despesa": 0,
"saldo": 0,
"valor_credito": 0,
"valor_debito": 0,
"valor_saldo": 0
}
]
Financeiros | Evolução do faturamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/evolucao_faturamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"valor": 0,
"valor_medio": 0
}
]
Financeiros | Evolução do faturamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

since	
string
Data inicial para geração do relatório

until	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/grafico_faturamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"valor": 0,
"valor_medio": 0
}
]
Financeiros | Funcionários rentáveis
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/funcionarios_rentaveis
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"razao_social": "string"
}
]
Financeiros | Clientes rentáveis
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/clientes_rentaveis
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"razao_social": "string"
}
]
Financeiros | Receitas por plano orçamentário
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/receitas_plano_orcamentario
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"plano_orcamentario": "string"
}
]
Financeiros | Despesas por plano orçamentário
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/despesas_plano_orcamentario
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"plano_orcamentario": "string"
}
]
Financeiros | Receitas por forma de pagamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/receitas_forma_pagamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"descricao_forma_pagamento": "string"
}
]
Financeiros | Despesas por forma de pagamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/financeiros/despesas_forma_pagamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"valor": 0,
"descricao_forma_pagamento": "string"
}
]
Financeiros | Clientes inadimplentes
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/clientes_inadimplentes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id_cliente": 0,
"razao_social": "string",
"valor": 0
}
]
Financeiros | Fornecedores credores
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/fornecedores_credores
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id_fornecedor": 0,
"razao_social": "string",
"valor": 0
}
]
Financeiros | Saldo por conta bancária
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/saldo_conta_bancaria
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"conta": "string",
"valor": 0
}
]
Financeiros | Saldo por departamento
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/financeiros/saldo_departamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"departamento": "string",
"valor": 0
}
]
OS | Status OS
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/os/status_os
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"status": "string",
"total": 0,
"valor": 0,
"valor_f": "string"
}
]
OS | Atividades OS
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/os/atividades_os
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"descricao_os": "string",
"data_os": "string",
"id_os": 0,
"numero_controle": "string"
}
]
Pedidos | Evolução de Criação
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/pedidos/evolucao_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"qtd": 0,
"qtd_medio": 0,
"valor": 0,
"valor_f": "string",
"vr_medio": 0,
"vr_medio_f": "string"
}
]
Pedidos Compra | Evolução de Criação
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/pedidos_compra/evolucao_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"qtd": 0,
"qtd_medio": 0,
"valor": 0,
"valor_f": "string",
"vr_medio": 0,
"vr_medio_f": "string"
}
]
Pedidos | Pedidos Entrega
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/pedidos_entrega
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"origem": "string",
"data": "string",
"id_pedido": 0,
"numero_controle": "string",
"os": 0,
"tipo": "string"
}
]
Notas | Evolução Notas
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

since	
string
Data inicial para geração do relatório

until	
string
Data final para geração do relatório

tipo	
string
Enum: "C" "E" "S"
C=Compra E=Entrada S=Saída

modelo	
string
Enum: "55" "65" "NS" "SD" "01"
55=Nota Fiscal Eletrônica 65=Nota Fiscal do Consumidor Eletronica (NFC-e) NS=Nota Fiscal de Serviço SD=Venda Simples 01=Nota Fiscal

HEADER PARAMETERS
X-Grafico	
boolean
Quando 'true' irá agrupar o resultado do gráfico em dias, semanas ou meses de acordo com o período filtrado para melhor visualização em gráficos

X-Totalizadores	
boolean
Indica que se a consulta irá retornar os totalizadores da consulta realizada.

X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/nota/evolucao_notas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"qtd": 0,
"valor_reprovado": 0,
"valor_aprovado": 0,
"valor_digitacao": 0
}
]
Pedidos | Origem Pedidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/pedidos/origem_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"total": 0,
"valor": 0,
"origem": "string",
"os": 0,
"valor_f": "string"
}
]
Pedidos | Status
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/status_pedidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"status": "string",
"total": 0,
"valor": 0,
"valor_f": "string"
}
]
Pedidos | Loja Virtual
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/pedidos/loja_virtual
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"total": 0,
"status": "string",
"valor": 0,
"valor_f": "string"
}
]
Produtos | Resumo Estoque Mínimo e Negativo
Responses
200 Sucesso!

GET
/dashboard/produtos/estoque
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"estoque_minimo": 0,
"estoque_negativo": 0
}
]
Produtos | Mais vendidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/produtos/produtos_mais_vendidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"valor": 0,
"valor_produto_vendido": 0,
"quantidade": 0
}
]
Produtos | Menos vendidos
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/produtos/produtos_menos_vendidos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"valor": 0,
"valor_produto_vendido": 0,
"quantidade": 0
}
]
Vendas | Evolução de Vendas
Informações de quantidade e valores médios das vendas (vendas simples, nfes, nfces, nfses), de um período, agrupadas pelos headers X-Data-Filter e X-Agrupar

QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

modelo	
string
Modelo da nota para gerar o relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Agrupar-Semana	
boolean
Gera agrupamento do objeto de resposta com relação a semana.

X-Agrupar-Mes	
boolean
Gera agrupamento do objeto de resposta com relação ao mes.

X-Agrupar-Ano	
boolean
Gera agrupamento do objeto de resposta com relação ao ano.

X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso! - Obs: a resposta com X-Graficos=true é diferente

GET
/dashboard/vendas/evolucao_vendas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"quantidade": 0,
"quantidade_medio": 0,
"valor": 0,
"valor_formatado": "string",
"valor_medio": 0,
"valor_medio_formatado": "string"
}
]
Vendas | Por dia da semana
Informações de quantidade e valores médios das vendas (vendas simples, nfes, nfces, nfses), de um período, agrupadas por dia da semana. Por padrão considera a semana atual

QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

modelo	
string
Modelo da nota para gerar o relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/vendas/vendas_dia
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"semana": "string",
"qtd": 0,
"faturamento": 0,
"qtd_media": 0,
"valor_media": 0
}
]
Vendas | Por hora do dia
Informações de quantidade e valores médios das vendas (vendas simples, nfes, nfces, nfses), de um período, agrupadas por hora do dia. Por padrão considera o dia atual

QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

modelo	
string
Modelo da nota para gerar o relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/vendas/vendas_hora
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"hora": "string",
"qtd": 0,
"valor": "string",
"qtd_media": 0
}
]
Venda Simples | Quantidade Agrupada Por Mês/Ano
QUERY PARAMETERS
funcionario	
integer
Id do funcionário

data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

Responses
200 Sucesso!

GET
/dashboard/vendas_simples/quantidade_vendas
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
[
null
]
]
Clientes | Melhores Compradores por Quantidade
QUERY PARAMETERS
data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Data-Filter	
string
Example: data_alteracao
Sobrescreve a data considerada para os filtros de data da query string, Ex: Se a data considerada do filtro é 'data_criacao', é possível informar outro campo atráves do header 'X-Data-Filter' como exemplo 'data_alteracao'.

Responses
200 Sucesso!

GET
/dashboard/clientes/melhores_compradores_qtd
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"total": 0,
"razao_social": "string"
}
]
Clientes | Evolução de Clientes
QUERY PARAMETERS
data_inicial	
string
Data inicial para geração do relatório

data_final	
string
Data final para geração do relatório

HEADER PARAMETERS
X-Agrupar-Semana	
boolean
Gera agrupamento do objeto de resposta com relação a semana.

X-Agrupar-Mes	
boolean
Gera agrupamento do objeto de resposta com relação a mes.

X-Agrupar-Ano	
boolean
Gera agrupamento do objeto de resposta com relação a ano.

Responses
200 Sucesso!

GET
/dashboard/clientes/evolucao_clientes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"data": "string",
"quantidade": 0,
"quantidade_media": 0
}
]
Autosuggest
Dados otimizados para utilização em autosuggest's.

Recupera dados de produtos otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/produtos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string"
}
]
Recupera dados de produtos otimizados para autosuggest de Pedido/OS - Venda Simples.
Responses
200 Sucesso!

GET
/autosuggests/produtos_completos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"movimentado": true,
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"codigo_grade": "string",
"descricao": "string",
"imagem_principal": {},
"categoria": {},
"departamento": {},
"estoque": {},
"qtd_revenda": 0,
"data_alteracao": "string",
"data_criacao": "string",
"data_validade": "string",
"unidade_entrada": {},
"unidade_saida": {},
"unidade_entrada_tributacao": {},
"unidade_entrada_inventario": {},
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [],
"mapa_integracao": [],
"produto_integracao": [],
"nota_fiscal_entrada": [],
"ajuste_estoque": [],
"valores_venda": [],
"custo_medio": 0,
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [],
"filhos": [],
"modalidades": [],
"fornecedores": [],
"imagens": [],
"tributo_ncm": {},
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"mercadoria": true
}
]
Recupera dados de produtos otimizados para autosuggest com dados de pai e filhos da grade.
Responses
200 Sucesso!

GET
/autosuggests/produtos_completos_grades
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"movimentado": true,
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"codigo_grade": "string",
"descricao": "string",
"imagem_principal": {},
"categoria": {},
"departamento": {},
"estoque": {},
"qtd_revenda": 0,
"data_alteracao": "string",
"data_criacao": "string",
"data_validade": "string",
"unidade_entrada": {},
"unidade_saida": {},
"unidade_entrada_tributacao": {},
"unidade_entrada_inventario": {},
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [],
"mapa_integracao": [],
"produto_integracao": [],
"nota_fiscal_entrada": [],
"ajuste_estoque": [],
"valores_venda": [],
"custo_medio": 0,
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [],
"filhos": [],
"modalidades": [],
"fornecedores": [],
"imagens": [],
"tributo_ncm": {},
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"mercadoria": true
}
]
Recupera dados de produtos sem kit otimizados para autosuggest NF-e de Entrada.
Responses
200 Sucesso!

GET
/autosuggests/produtos_semkit
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"movimentado": true,
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"codigo_grade": "string",
"descricao": "string",
"imagem_principal": {},
"categoria": {},
"departamento": {},
"estoque": {},
"qtd_revenda": 0,
"data_alteracao": "string",
"data_criacao": "string",
"data_validade": "string",
"unidade_entrada": {},
"unidade_saida": {},
"unidade_entrada_tributacao": {},
"unidade_entrada_inventario": {},
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [],
"mapa_integracao": [],
"produto_integracao": [],
"nota_fiscal_entrada": [],
"ajuste_estoque": [],
"valores_venda": [],
"custo_medio": 0,
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [],
"filhos": [],
"modalidades": [],
"fornecedores": [],
"imagens": [],
"tributo_ncm": {},
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"mercadoria": true
}
]
Recupera dados de produtos com grade vendidas separadamente otimizados para autosuggest NF-e/NFC-e.
Responses
200 Sucesso!

GET
/autosuggests/produtos_nseparado
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"movimentado": true,
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"codigo_grade": "string",
"descricao": "string",
"imagem_principal": {},
"categoria": {},
"departamento": {},
"estoque": {},
"qtd_revenda": 0,
"data_alteracao": "string",
"data_criacao": "string",
"data_validade": "string",
"unidade_entrada": {},
"unidade_saida": {},
"unidade_entrada_tributacao": {},
"unidade_entrada_inventario": {},
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [],
"mapa_integracao": [],
"produto_integracao": [],
"nota_fiscal_entrada": [],
"ajuste_estoque": [],
"valores_venda": [],
"custo_medio": 0,
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [],
"filhos": [],
"modalidades": [],
"fornecedores": [],
"imagens": [],
"tributo_ncm": {},
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"mercadoria": true
}
]
Recupera dados de atributos de produtos otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/produtos_atributos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"nome_atributo": "string",
"valor_atributo": "string"
}
]
Recupera dados de formas de pagamento otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/formas_pagamento
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string"
}
]
Recupera dados de clientes otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/clientes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"nome_fantasia": "string",
"cnpj": "string",
"cpf": "string"
}
]
Recupera dados de fornecedores otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/fornecedores
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"nome_fantasia": "string",
"cnpj": "string",
"cpf": "string"
}
]
Recupera dados de nome fantasia de fornecedores otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/fornecedores/nome_fantasia
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"nome_fantasia": "string",
"cnpj": "string",
"cpf": "string"
}
]
Recupera dados de transportadoras otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/transportadoras
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"nome_fantasia": "string",
"cnpj": "string",
"cpf": "string"
}
]
Recupera dados de intermediadores otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/intermediadores
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"razao_social": "string",
"identificacao_intermediador": "string",
"cnpj": "string"
}
]
Recupera os bairros de endereços ja cadastrados no sistema.
Responses
200 Sucesso!

GET
/autosuggests/bairros
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"bairro": "string"
}
]
Recupera os CNAE's cadastrados no sistema.
Responses
200 Sucesso!

GET
/autosuggests/cnaes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo": "string",
"codigo_tributario_municipio": "string",
"descricao": "string"
}
]
Recupera os terminais cadastrados no sistema.
Responses
200 Sucesso!

GET
/autosuggests/terminais
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"terminal": "string"
}
]
Recupera os objetos de conserto cadastrados no sistema.
Responses
200 Sucesso!

GET
/autosuggests/objetos_conserto
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"descricao": "string",
"info": "string",
"equipamento": "string",
"marca": "string",
"modelo": "string"
}
]
Recupera dados básicos de notas fiscais de entrada e ajustes de estoque.
Responses
200 Sucesso!

GET
/autosuggests/notas_ajustes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"id_entidade": 0,
"numero": "string",
"modelo": "string",
"serie": "string",
"razao_social": "string",
"relevancia": "string",
"tipo_entidade": "C"
}
]
Recupera dados de valores de venda otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/valores_venda
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"nome": "string",
"lucro": 0
}
]
Recupera dados de NCM do service auxiliar.
Responses
200 Sucesso!

GET
/autosuggests/ncm_service
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"value": "string",
"info": "string",
"relevancia": "string"
}
]
Recupera dados de CEST do service auxiliar.
Responses
200 Sucesso!

GET
/autosuggests/cest_service
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"text": "string",
"value": "string"
}
]
Recupera dados de cnae do service auxiliar.
Responses
200 Sucesso!

GET
/autosuggests/cnae_service
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"cnae": "string",
"descricao": "string"
}
]
Recupera dados das credenciadoras otimizados para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/credenciadoras
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"nome_empresa": "string",
"cnpj": "string"
}
]
Recupera dados otimizados das integrações para autosuggest.
Responses
200 Sucesso!

GET
/autosuggests/integracoes
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"nome": "string",
"codigo_servico": "string",
"ultima_sincronizacao": "string"
}
]
Upload de arquivos
Alguns cadastros aceitam upload de arquivos. Na API é possível realizar arquivos através desse endpoint.

Enviar arquivos Financeiro. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/financeiro/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos Financeiro
Responses
200 Sucesso!

GET
/arquivos/financeiro/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo financeiro
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/financeiro/{id}
Enviar arquivos para Pedido/Orçamento. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/pedido/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos de Pedido/Orçamento
Responses
200 Sucesso!

GET
/arquivos/pedido/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo de Pedido/Orçamento
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/pedido/{id}
Enviar arquivos para Pedidos de Compra. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/pedido_compra/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos de Pedidos de Compra
Responses
200 Sucesso!

GET
/arquivos/pedido_compra/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo de Pedidos de Compra
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/pedido_compra/{id}
Enviar arquivos Vendas simples. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/venda_simples/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos venda simples
Responses
200 Sucesso!

GET
/arquivos/venda_simples/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo venda simples
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/venda_simples/{id}
Enviar arquivo certificado A1.
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/certificado
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivo certificado digital
Responses
200 Sucesso!

GET
/arquivos/certificado
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo certificado digital
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/certificado
Listar arquivos gerados pelas consultas SPC/SERASA
Responses
200 Sucesso!

GET
/arquivos/consulta_spc
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Enviar arquivos para Cliente. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/cliente/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos de Cliente
Responses
200 Sucesso!

GET
/arquivos/cliente/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo de Cliente
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/cliente/{id}
Enviar arquivos para Ordem serviço. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/os/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos de Ordem de serviço
Responses
200 Sucesso!

GET
/arquivos/os/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo de Ordem de serviço
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/os/{id}
Enviar arquivos para Conta Bancaria Inter. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo .CRT a ser enviado.

file2	
string <binary>
O arquivo .KEY a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/conta_inter/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos da Conta Bancaria Inter
Responses
200 Sucesso!

GET
/arquivos/conta_inter/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo da Conta Bancaria Inter
QUERY PARAMETERS
nome_arquivo_crt	
string
Nome do arquivo .CRT a ser apagado

nome_arquivo_key	
string
Nome do arquivo .KEY a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/conta_inter/{id}
Enviar arquivos para Fornecedores. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/fornecedores/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos de Fornecedores
Responses
200 Sucesso!

GET
/arquivos/fornecedores/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo de Fornecedores
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/fornecedores/{id}
Enviar arquivos para Funcionarios. É possível enviar até 05 arquivos de uma vez
REQUEST BODY SCHEMA: multipart/form-data
file1	
string <binary>
O arquivo a ser enviado.

file2	
string <binary>
O arquivo a ser enviado.

file3	
string <binary>
O arquivo a ser enviado.

file4	
string <binary>
O arquivo a ser enviado.

file5	
string <binary>
O arquivo a ser enviado.

Responses
201 Sucesso!

POST
/arquivos/funcionarios/{id}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Listar arquivos de Funcionarios
Responses
200 Sucesso!

GET
/arquivos/funcionarios/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"recurso": "string",
"data_upload": "string",
"extensao": "string",
"nome_arquivo": "string",
"pasta": "string",
"url": "string",
"size": 0
}
]
Apagar arquivo de Funcionarios
QUERY PARAMETERS
nome_arquivo	
string
Nome do arquivo a ser apagado

Responses
200 Arquivo apagado!

DELETE
/arquivos/funcionarios/{id}
Gerar links de download
Gera links de download para os arquivos de suporte.

QUERY PARAMETERS
tipo	
string (Tipo de arquivo a ser baixado)
Enum: "chrome" "contrato" "firefox" "pdv" "tabela_clientes" "tabela_fornecedores" "tabela_produtos" "terminal_consulta" "uninfe"
Responses
200 Sucesso!

GET
/arquivos/link_download
bulk
Sobre operações BULK: O objeto de retorno de operações bulk contém as posições success e errors, tais posições delvolvem o sucesso e os erros ocorridos na requisição, a posição success do retorno contém os itens criados/atualizados, e na posição errors contém os erros acontecidos para cada objeto que foi enviado no array bulk.

Criar vários produtos em uma só requisição.
Cadastra novos produtos.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
descricao
required
string
Descricão/Nome do produto.

id	
integer
Campo identificador do registro do produto.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o produto está ativo, onde ativo=true indica produto ativo.

codigo	
string
Caso não seja fornecido um código interno, o sistema gera um automáticamente

codigo_barras	
string
Código de barras do fabricante do produto. Padrão EAN13

codigo_barras_tributavel	
string [ 8 .. 14 ] characters
Código de barras da unidade do produto (cEAN Trib.). Caso seja preenchido, este campo deve ser um EAN válido e possuir 8, 12,13 ou 14 caracteres. Padrão EAN13

imagem_principal	
integer
ID da imagem principal.

categoria	
integer
Campo identificador da categoria do produto, é possível recuperar categorias pelo recurso /categorias, saiba como recuperar categorias do ERP clicando aqui

departamento	
integer
Campo identificador do departamento do produto, é possível recuperar departamentos pelo recurso /departamento, saiba como recuperar departamentos do ERP clicando aqui

estoque	
object (Estoque de Produto)
qtd_revenda	
number
data_validade	
string
Data de validade do produto.

unidade_entrada	
integer
unidade_saida	
integer
unidade_entrada_tributacao	
integer
unidade_entrada_inventario	
integer
taxa_conversao_saida	
number
Taxa de conversão do produto.

taxa_conversao_inventario	
number
Taxa de conversão de entrada do inventário.

taxa_conversao_tributacao	
number
Taxa de conversão de entrada de tributação.

tipo	
string
Default: "N"
Enum: "N" "K" "G"
Indica o tipo de produto: Normal, Kit, Grade.

finalidade	
string
Indica a finalidade principal do produto. 00=Mercadoria para Revenda | 01=Matéria-Prima | 02=Embalagem | 03=Produto em Processo | 04=Produto Acabado | 05=Subproduto | 06=Produto Intermediário | 07=Material de Uso e Consumo | 08=Ativo Imobilizado | 10=Outros Insumos | 99=Outras

cfop	
string
Retorna o CFOP cadastrado no produto no formato X.NNN Ex. X.102

cest	
string = 7 characters
Cest do produto

cst_a	
string
Enum: "0" "1" "2" "3" "4" "5" "6" "7" "8"
Código CST A.

0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 1 - Estrangeira - Importação direta, exceto a indicada no código 6 2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70% 4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam as legislações citadas nos Ajustes 5 - Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% 6 - Estrangeira - Importação direta, sem similar nacional, constante em lista da CAMEX e gás natural 7 - Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista da CAMEX e gás natural 8 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70%

indicador_escala	
string
Enum: "" "S" "N"
Indicador de Escala Relevante

"" - Não informado S - Produzido em Escala Relevante N - Produzido em Escala não Relevante

localizacao_estoque	
string <= 82 characters
Localização do produto no estoque, ao imprimir uma Ordem de Serviço ou Pedido/Orçamento em formato A4, este campo será impresso como observações.

codigo_fornecedor_xml	
boolean
Indica que o produto poderá usar o codígo do fonecedor no XML da Nfe de devolução caso ele tenha sido importado com o codígo maior que 15 digitos.

cnpj_fabricante	
string
CNPJ do fabricante.

cnpj_produtor	
string
CNPJ do produtor.

embalagem	
object
valor_venda_varejo	
number
Valor de venda do tipo Varejo.

custo_utilizado	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

custo_outras_despesas	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

serie	
boolean
Default: false
Indica se a Série ou Selo de garantia do produto deve ser requisitado ao realizar a venda do produto no PDV.

vendido_separado	
boolean
Default: true
false: pode compor um produto tipo kit ou composição, mas não pode ser indicado diretamente em uma movimentação de saída. true: pode compor um produto kit ou composição e também pode ser vendido separadamente.

comercializavel	
boolean
Default: true
Indica se o produto pode ser vendido no PDV.

peso	
number
Peso do produto.

largura	
number
Largura do produto.

altura	
number
Altura do produto.

comprimento	
number
Comprimento do produto.

tipo_producao	
string
Default: ""
Enum: "" "P" "T"
Própria, Terceiros.

observacoes	
string
Informações sobre o produto, entrada de texto livre.

atributos	
Array of objects (Produto Atributo)
Lista de atributos do produto. ex: Marca = Nike

mapa_integracao	
Array of objects (Mapa Integracao)
Lista de sincronização do produto com outras integracoes

produto_integracao	
Array of objects
Lista de ids de integrações vinculadas ao produto

nota_fiscal_entrada	
Array of objects (Produto Nota Compra Vinculada)
Notas fiscais de compra vinculadas ao produto

ajuste_estoque	
Array of objects (Produto Ajuste Estoque Vinculado)
Ajustes de estoque vinculados ao produto

valores_venda	
Array of objects (Valor de Venda)
Lista de valores de venda de um produto.

aliquota_ipi	
number
aliquota_icms	
number
aliquota_pis	
number
aliquota_cofins	
number
aliquota_irpj	
number
aliquota_cpp	
number
aliquota_csll	
number
comissao	
number
comissao_produto	
number
id_pai	
integer
Campo usado para produtos do tipo Grade, quando possuir algum inteiro e tipo do produto igual G, indica que o produto em questão é filho do produto de id igual id_pai.

itens_vinculados	
Array of objects (Item de Kit/Composição)
Detalha os itens de um produto Kit ou Composição. Confira o tipo do produto para determinar se é kit ou composição.

filhos	
Array of objects (Produto)
Filhos do produto, quando este é do tipo grade e principal.

modalidades	
Array of integers
Lista de ids das modalidades vinculadas ao produto.

fornecedores	
Array of integers
Lista de ids de fornecedores do produto.

imagens	
Array of objects (Dados da imagem)
Array de Base64 de imagens para serem salvas no produto.

tributo_ncm	
string <= 8 characters
Código do tributo NCM vinculado ao produto, todos os NCM's podem ser recuperados através do endpoint /tributos_ncm

sincroniza	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

ignorar_estoque	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

valor_oferta	
number
Loja Virtual. Valor Oferta

vender_de	
string
Loja Virtual. Vender a partir da data

vender_ate	
string
Loja Virtual. Vender ate a data

descricao_curta	
string
Loja Virtual. Descrição Curta

descricao_longa	
string
Loja Virtual. Descrição Longa

filtro_grade	
string
Enum: "" "F" "P" "T" "S"
Filtro Opcional valido apenas para listagem. Ele indica quais elementos o sistema deve trazer.

"" - (Padrão) Apenas os pais de grade e outros tipos de produtos. F - Apenas os filhos de grade P - Apenas os pais de grade T - Pais e filhos de grade. S - Pais, filhos de grade e outros tipos de produtos.

criar_composicao	
boolean
Indica se uma composição será criada

desfazer_composicao	
boolean
Indica se uma composição será desfeita

quantidade_composicao	
number
Quantidade de composição que será desfeita ou criada de acordo com o que foi informado nos campos criar_composicao ou desfazer_composicao

Responses
200 Produtos criados com sucesso e produtos com erros.

POST
/bulk/produtos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"descricao": "string",
"imagem_principal": 0,
"categoria": 0,
"departamento": 0,
"estoque": {},
"qtd_revenda": 0,
"data_validade": "string",
"unidade_entrada": 0,
"unidade_saida": 0,
"unidade_entrada_tributacao": 0,
"unidade_entrada_inventario": 0,
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [],
"mapa_integracao": [],
"produto_integracao": [],
"nota_fiscal_entrada": [],
"ajuste_estoque": [],
"valores_venda": [],
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [],
"filhos": [],
"modalidades": [],
"fornecedores": [],
"imagens": [],
"tributo_ncm": "string",
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"filtro_grade": "",
"criar_composicao": true,
"desfazer_composicao": true,
"quantidade_composicao": 0
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza vários produtos em uma só requisição.
Atualiza produtos.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id
required
integer
Campo identificador do registro do produto.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

ativo	
boolean
Default: true
Indica se o produto está ativo, onde ativo=true indica produto ativo.

codigo	
string
Caso não seja fornecido um código interno, o sistema gera um automáticamente

codigo_barras	
string
Código de barras do fabricante do produto. Padrão EAN13

codigo_barras_tributavel	
string [ 8 .. 14 ] characters
Código de barras da unidade do produto (cEAN Trib.). Caso seja preenchido, este campo deve ser um EAN válido e possuir 8, 12,13 ou 14 caracteres. Padrão EAN13

descricao	
string
Descricão/Nome do produto.

imagem_principal	
integer
ID da imagem principal.

categoria	
integer
Campo identificador da categoria do produto, é possível recuperar categorias pelo recurso /categorias, saiba como recuperar categorias do ERP clicando aqui

departamento	
integer
Campo identificador do departamento do produto, é possível recuperar departamentos pelo recurso /departamento, saiba como recuperar departamentos do ERP clicando aqui

estoque	
object (Estoque de Produto)
qtd_revenda	
number
data_validade	
string
Data de validade do produto.

unidade_entrada	
integer
unidade_saida	
integer
unidade_entrada_tributacao	
integer
unidade_entrada_inventario	
integer
taxa_conversao_saida	
number
Taxa de conversão do produto.

taxa_conversao_inventario	
number
Taxa de conversão de entrada do inventário.

taxa_conversao_tributacao	
number
Taxa de conversão de entrada de tributação.

tipo	
string
Default: "N"
Enum: "N" "K" "G"
Indica o tipo de produto: Normal, Kit, Grade.

finalidade	
string
Indica a finalidade principal do produto. 00=Mercadoria para Revenda | 01=Matéria-Prima | 02=Embalagem | 03=Produto em Processo | 04=Produto Acabado | 05=Subproduto | 06=Produto Intermediário | 07=Material de Uso e Consumo | 08=Ativo Imobilizado | 10=Outros Insumos | 99=Outras

cfop	
string
Retorna o CFOP cadastrado no produto no formato X.NNN Ex. X.102

cest	
string = 7 characters
Cest do produto

cst_a	
string
Enum: "0" "1" "2" "3" "4" "5" "6" "7" "8"
Código CST A.

0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 1 - Estrangeira - Importação direta, exceto a indicada no código 6 2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70% 4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam as legislações citadas nos Ajustes 5 - Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% 6 - Estrangeira - Importação direta, sem similar nacional, constante em lista da CAMEX e gás natural 7 - Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista da CAMEX e gás natural 8 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70%

indicador_escala	
string
Enum: "" "S" "N"
Indicador de Escala Relevante

"" - Não informado S - Produzido em Escala Relevante N - Produzido em Escala não Relevante

localizacao_estoque	
string <= 82 characters
Localização do produto no estoque, ao imprimir uma Ordem de Serviço ou Pedido/Orçamento em formato A4, este campo será impresso como observações.

codigo_fornecedor_xml	
boolean
Indica que o produto poderá usar o codígo do fonecedor no XML da Nfe de devolução caso ele tenha sido importado com o codígo maior que 15 digitos.

cnpj_fabricante	
string
CNPJ do fabricante.

cnpj_produtor	
string
CNPJ do produtor.

embalagem	
object
valor_venda_varejo	
number
Valor de venda do tipo Varejo.

custo_utilizado	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

custo_outras_despesas	
number
Somatório do Custo Médio, Despesas Acessórias e Outras Despesas

serie	
boolean
Default: false
Indica se a Série ou Selo de garantia do produto deve ser requisitado ao realizar a venda do produto no PDV.

vendido_separado	
boolean
Default: true
false: pode compor um produto tipo kit ou composição, mas não pode ser indicado diretamente em uma movimentação de saída. true: pode compor um produto kit ou composição e também pode ser vendido separadamente.

comercializavel	
boolean
Default: true
Indica se o produto pode ser vendido no PDV.

peso	
number
Peso do produto.

largura	
number
Largura do produto.

altura	
number
Altura do produto.

comprimento	
number
Comprimento do produto.

tipo_producao	
string
Default: ""
Enum: "" "P" "T"
Própria, Terceiros.

observacoes	
string
Informações sobre o produto, entrada de texto livre.

atributos	
Array of objects (Produto Atributo)
Lista de atributos do produto. ex: Marca = Nike

mapa_integracao	
Array of objects (Mapa Integracao)
Lista de sincronização do produto com outras integracoes

produto_integracao	
Array of objects
Lista de ids de integrações vinculadas ao produto

nota_fiscal_entrada	
Array of objects (Produto Nota Compra Vinculada)
Notas fiscais de compra vinculadas ao produto

ajuste_estoque	
Array of objects (Produto Ajuste Estoque Vinculado)
Ajustes de estoque vinculados ao produto

valores_venda	
Array of objects (Valor de Venda)
Lista de valores de venda de um produto.

aliquota_ipi	
number
aliquota_icms	
number
aliquota_pis	
number
aliquota_cofins	
number
aliquota_irpj	
number
aliquota_cpp	
number
aliquota_csll	
number
comissao	
number
comissao_produto	
number
id_pai	
integer
Campo usado para produtos do tipo Grade, quando possuir algum inteiro e tipo do produto igual G, indica que o produto em questão é filho do produto de id igual id_pai.

itens_vinculados	
Array of objects (Item de Kit/Composição)
Detalha os itens de um produto Kit ou Composição. Confira o tipo do produto para determinar se é kit ou composição.

filhos	
Array of objects (Produto)
Filhos do produto, quando este é do tipo grade e principal.

modalidades	
Array of integers
Lista de ids das modalidades vinculadas ao produto.

fornecedores	
Array of integers
Lista de ids de fornecedores do produto.

imagens	
Array of objects (Dados da imagem)
Array de Base64 de imagens para serem salvas no produto.

tributo_ncm	
string <= 8 characters
Código do tributo NCM vinculado ao produto, todos os NCM's podem ser recuperados através do endpoint /tributos_ncm

sincroniza	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

ignorar_estoque	
boolean
Loja Virtual. Sincronizar este produto com a Loja Virtual ou Integrações Utilizadas

valor_oferta	
number
Loja Virtual. Valor Oferta

vender_de	
string
Loja Virtual. Vender a partir da data

vender_ate	
string
Loja Virtual. Vender ate a data

descricao_curta	
string
Loja Virtual. Descrição Curta

descricao_longa	
string
Loja Virtual. Descrição Longa

filtro_grade	
string
Enum: "" "F" "P" "T" "S"
Filtro Opcional valido apenas para listagem. Ele indica quais elementos o sistema deve trazer.

"" - (Padrão) Apenas os pais de grade e outros tipos de produtos. F - Apenas os filhos de grade P - Apenas os pais de grade T - Pais e filhos de grade. S - Pais, filhos de grade e outros tipos de produtos.

criar_composicao	
boolean
Indica se uma composição será criada

desfazer_composicao	
boolean
Indica se uma composição será desfeita

quantidade_composicao	
number
Quantidade de composição que será desfeita ou criada de acordo com o que foi informado nos campos criar_composicao ou desfazer_composicao

Responses
200 Produtos atualizados com sucesso e produtos com erros.

PATCH
/bulk/produtos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"ativo": true,
"codigo": "string",
"codigo_barras": "string",
"codigo_barras_tributavel": "stringst",
"descricao": "string",
"imagem_principal": 0,
"categoria": 0,
"departamento": 0,
"estoque": {},
"qtd_revenda": 0,
"data_validade": "string",
"unidade_entrada": 0,
"unidade_saida": 0,
"unidade_entrada_tributacao": 0,
"unidade_entrada_inventario": 0,
"taxa_conversao_saida": 0,
"taxa_conversao_inventario": 0,
"taxa_conversao_tributacao": 0,
"tipo": "N",
"finalidade": "string",
"cfop": "string",
"cest": "strings",
"cst_a": "0",
"indicador_escala": "",
"localizacao_estoque": "string",
"codigo_fornecedor_xml": true,
"cnpj_fabricante": "string",
"cnpj_produtor": "string",
"embalagem": {},
"valor_venda_varejo": 0,
"custo_utilizado": 0,
"custo_outras_despesas": 0,
"serie": false,
"vendido_separado": true,
"comercializavel": true,
"peso": 0,
"largura": 0,
"altura": 0,
"comprimento": 0,
"tipo_producao": "",
"observacoes": "string",
"atributos": [],
"mapa_integracao": [],
"produto_integracao": [],
"nota_fiscal_entrada": [],
"ajuste_estoque": [],
"valores_venda": [],
"aliquota_ipi": 0,
"aliquota_icms": 0,
"aliquota_pis": 0,
"aliquota_cofins": 0,
"aliquota_irpj": 0,
"aliquota_cpp": 0,
"aliquota_csll": 0,
"comissao": 0,
"comissao_produto": 0,
"id_pai": 0,
"itens_vinculados": [],
"filhos": [],
"modalidades": [],
"fornecedores": [],
"imagens": [],
"tributo_ncm": "string",
"sincroniza": true,
"ignorar_estoque": true,
"valor_oferta": 0,
"vender_de": "string",
"vender_ate": "string",
"descricao_curta": "string",
"descricao_longa": "string",
"filtro_grade": "",
"criar_composicao": true,
"desfazer_composicao": true,
"quantidade_composicao": 0
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias vendas simples
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
itens
required
Array of objects (Item de Venda)
Itens da venda simples.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
string <= 7 characters
Número da venda. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

pedido_os_vinculada	
integer
ID do Pedido ou OS vinculado à Venda Simples.

data_criacao	
string <date-time>
Data de criação da venda. Gerado automaticamente.

data_confirmacao	
string <date-time>
Data de confirmação da venda

status	
string
Enum: "N" "A" "S"
Situação das Vendas N=Em digitação | A=Aprovada | S=Cancelada |

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

observacoes	
string
Observações gerais. Texto livre.

valor_desconto	
number
Valor do desconto.

valor_frete	
number
Valor do frete.

valor_acrescimo	
number
Valor do acréscimo.

valor_troco	
number
Valor do troco.

valor_total	
number
Valor total da nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da venda. São as formas de pagamento usadas para pagar pela venda.

departamento	
integer
Campo identificador do departamento ao qual a venda está vinculada. se não informado, o departamento padrão será indicado. Saiba como recuperar departamentos clicando aqui

Responses
200 Vendas simples criadas!

POST
/bulk/vendas_simples
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": 0,
"pedido_os_vinculada": 0,
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": 0,
"itens": [],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"faturas": [],
"departamento": 0
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza várias vendas simples em uma só requisição.
Atualiza vendas simples.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id
required
integer
Campo identificador do registro da venda simples.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
string <= 7 characters
Número da venda. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

cliente	
integer
Campo identificador do cliente, saiba como recuperar clientes clicando aqui

pedido_os_vinculada	
integer
ID do Pedido ou OS vinculado à Venda Simples.

data_criacao	
string <date-time>
Data de criação da venda. Gerado automaticamente.

data_confirmacao	
string <date-time>
Data de confirmação da venda

status	
string
Enum: "N" "A" "S"
Situação das Vendas N=Em digitação | A=Aprovada | S=Cancelada |

vendedor	
integer
Campo identificador do vendedor responsável pela venda, se não informado, o funcionário vinculado ao token será indicado. É possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

itens	
Array of objects (Item de Venda)
Itens da venda simples.

observacoes	
string
Observações gerais. Texto livre.

valor_desconto	
number
Valor do desconto.

valor_frete	
number
Valor do frete.

valor_acrescimo	
number
Valor do acréscimo.

valor_troco	
number
Valor do troco.

valor_total	
number
Valor total da nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da venda. São as formas de pagamento usadas para pagar pela venda.

departamento	
integer
Campo identificador do departamento ao qual a venda está vinculada. se não informado, o departamento padrão será indicado. Saiba como recuperar departamentos clicando aqui

Responses
200 Vendas simples atualizadas com sucesso e vendas simples com erros.

PATCH
/bulk/vendas_simples
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero": "string",
"numero_fatura": "string",
"cliente": 0,
"pedido_os_vinculada": 0,
"data_criacao": "2019-08-24T14:15:22Z",
"data_confirmacao": "2019-08-24T14:15:22Z",
"status": "N",
"vendedor": 0,
"itens": [],
"observacoes": "string",
"valor_desconto": 0,
"valor_frete": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"valor_total": 0,
"faturas": [],
"departamento": 0
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Deleta várias vendas simples em uma só requisição.
QUERY PARAMETERS
ids	
string
ID's das vendas a serem apagadas.

HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Vendas simples deletadas com sucesso e vendas simples com erros.

DELETE
/bulk/vendas_simples
Editar Associação de Posições e Planos pai
Alterar em massa a associação dos planos orçamentários

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id	
integer
Id do Plano Orçamentário.

plano_orcamentario_pai	
integer
Plano Orçamentário Pai Ex: Vendas Brinquedos pertence ao plano Vendas que por sua vez pertence ao Plano Crédito.

Responses
200 Sucesso!

PATCH
/bulk/planos_orcamentarios
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"plano_orcamentario_pai": 0
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar vários lançamentos financeiros
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
tipo
required
string
Default: "S"
Enum: "E" "S"
Indica se o lançamento financeiro é do tipo Entrada ou Saida. Entradas são todos valores creditados, ex: Vendas. Saidas são todos valores debitados, ex: Conta de energia elétrica, aluguel, pagamento de funcionários.

plano_orcamentario
required
integer
forma_pagamento
required
integer
descricao
required
string
Descrição a que se refere o lançamento.

valor_bruto
required
number
Valor Bruto.

conta_bancaria
required
integer
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero_documento	
string
Número do documento que identifica o lançamento financeiro pra funcionalides como por exemplo conciliação bancária.

confirmado	
boolean
Default: false
Indica se o lançamento financeiro já foi pago seja ele entrada ou saida. Quando já está pago, é considerado como true confirmado.

numero_sigla_movimentacao_vinculada	
string
Número e sigla identificando movimentação vinculada.

data_vencimento	
string <date-time>
Data de vencimento. Caso não informado, será preenchida com a data atual da criação.

valor_original	
number
Valor Original.

valor_pago	
number
Valor Pago.

departamento	
integer
ID do departamento do financeiro. Caso não informado, será preenchido com departamento do usuário que está criando o registro.

item_fatura	
integer
transferencia	
boolean
Default: false
Indica de há tranferência entre contas.

data_lancamento	
string <date-time>
Data de lançamento. Caso não informado, será preenchida com a data atual da criação.

data_confirmacao	
string
Data de confirmação.

valor_desconto	
number
Valor desconto.

valor_acrescimo	
number
Valor acréscimo.

valor_juros_atraso	
number
Valor dos juros cobrados por atraso.

aliquota_juros_ao_dia	
number
Percentual dos jutos cobrados ao dia.

tipo_entidade	
string
Enum: "C" "F" "T" "U" "O"
Tipo de entidade a qual está vinculada ao lançamento. C=Cliente | F=Fornecedor | T=Transportadora | U=Funcionário | O=Outros |

entidade	
integer
ID da entidade referente ao cliente, ou fornecedor, ou funcionário, ou transportador a qual o financeiro estará vinculado. Caso não informado, não haverá entidade vinculada, mas tipo da entidade será salvo.

data_competencia	
string
Data em que será diluido o lançamento caso exista diluição.

diluicao_lancamento	
integer
Quantidade de meses em que se deve diluir o lançamento a partir da data de competencia ou data do lançamento.

primeira_parcela	
integer
ID da parcela que será vinculada a essa.

id_caixa	
integer
ID do Caixa, no caso de lançamentos financeiros originados pelo PDV.

informacao_1	
string
Informações adicionais da parcela.

informacao_2	
string
Informações adicionais da parcela.

informacao_3	
string
Informações adicionais da parcela.

historico	
string
Informações adicionais da parcela.

observacoes	
string
Informações adicionais da parcela.

financeiro_parcelas	
Array of objects (Financeiro)
Responses
200 Financeiros criados!

POST
/bulk/financeiros
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "2019-08-24T14:15:22Z",
"forma_pagamento": 0,
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"plano_orcamentario": 0,
"conta_bancaria": 0,
"departamento": 0,
"item_fatura": 0,
"transferencia": false,
"data_lancamento": "2019-08-24T14:15:22Z",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"tipo_entidade": "C",
"entidade": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": 0,
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": []
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza vários lançamentos financeiros em uma só requisição.
Atualiza financeiros.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero_documento	
string
Número do documento que identifica o lançamento financeiro pra funcionalides como por exemplo conciliação bancária.

tipo	
string
Default: "S"
Enum: "E" "S"
Indica se o lançamento financeiro é do tipo Entrada ou Saida. Entradas são todos valores creditados, ex: Vendas. Saidas são todos valores debitados, ex: Conta de energia elétrica, aluguel, pagamento de funcionários.

confirmado	
boolean
Default: false
Indica se o lançamento financeiro já foi pago seja ele entrada ou saida. Quando já está pago, é considerado como true confirmado.

numero_sigla_movimentacao_vinculada	
string
Número e sigla identificando movimentação vinculada.

data_vencimento	
string <date-time>
Data de vencimento. Caso não informado, será preenchida com a data atual da criação.

forma_pagamento	
integer
descricao	
string
Descrição a que se refere o lançamento.

valor_bruto	
number
Valor Bruto.

valor_original	
number
Valor Original.

valor_pago	
number
Valor Pago.

plano_orcamentario	
integer
conta_bancaria	
integer
departamento	
integer
ID do departamento do financeiro. Caso não informado, será preenchido com departamento do usuário que está criando o registro.

item_fatura	
integer
transferencia	
boolean
Default: false
Indica de há tranferência entre contas.

data_lancamento	
string <date-time>
Data de lançamento. Caso não informado, será preenchida com a data atual da criação.

data_confirmacao	
string
Data de confirmação.

valor_desconto	
number
Valor desconto.

valor_acrescimo	
number
Valor acréscimo.

valor_juros_atraso	
number
Valor dos juros cobrados por atraso.

aliquota_juros_ao_dia	
number
Percentual dos jutos cobrados ao dia.

tipo_entidade	
string
Enum: "C" "F" "T" "U" "O"
Tipo de entidade a qual está vinculada ao lançamento. C=Cliente | F=Fornecedor | T=Transportadora | U=Funcionário | O=Outros |

entidade	
integer
ID da entidade referente ao cliente, ou fornecedor, ou funcionário, ou transportador a qual o financeiro estará vinculado. Caso não informado, não haverá entidade vinculada, mas tipo da entidade será salvo.

data_competencia	
string
Data em que será diluido o lançamento caso exista diluição.

diluicao_lancamento	
integer
Quantidade de meses em que se deve diluir o lançamento a partir da data de competencia ou data do lançamento.

primeira_parcela	
integer
ID da parcela que será vinculada a essa.

id_caixa	
integer
ID do Caixa, no caso de lançamentos financeiros originados pelo PDV.

informacao_1	
string
Informações adicionais da parcela.

informacao_2	
string
Informações adicionais da parcela.

informacao_3	
string
Informações adicionais da parcela.

historico	
string
Informações adicionais da parcela.

observacoes	
string
Informações adicionais da parcela.

financeiro_parcelas	
Array of objects (Financeiro)
Responses
200 Lançamentos financeiros atualizados com sucesso e com erros.

PATCH
/bulk/financeiros
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo_externo": "string",
"numero_documento": "string",
"tipo": "E",
"confirmado": false,
"numero_sigla_movimentacao_vinculada": "string",
"data_vencimento": "2019-08-24T14:15:22Z",
"forma_pagamento": 0,
"descricao": "string",
"valor_bruto": 0,
"valor_original": 0,
"valor_pago": 0,
"plano_orcamentario": 0,
"conta_bancaria": 0,
"departamento": 0,
"item_fatura": 0,
"transferencia": false,
"data_lancamento": "2019-08-24T14:15:22Z",
"data_confirmacao": "string",
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_juros_atraso": 0,
"aliquota_juros_ao_dia": 0,
"tipo_entidade": "C",
"entidade": 0,
"data_competencia": "string",
"diluicao_lancamento": 0,
"primeira_parcela": 0,
"id_caixa": 5612,
"informacao_1": "string",
"informacao_2": "string",
"informacao_3": "string",
"historico": "string",
"observacoes": "string",
"financeiro_parcelas": []
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar vários pedidos
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

hora_criacao	
string
Hora de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

hora_confirmacao	
string
Hora de confirmação do pedido.

departamento	
integer
Campo identificador do departamento ao qual o pedido está vinculado, saiba como recuperar departamentos clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pelo pedido, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual o pedido foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens do pedido.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

valor_acrescimo	
number
Valor de acrescimo do pedido.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

integracao	
string
Caso o pedido veio de alguma integração, informa o nome do parceiro.

possui_vinculo	
boolean
Identifica se o Pedido possui algum vínculo no sistema.

Responses
200 Pedidos criados!

POST
/bulk/pedidos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"hora_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"departamento": 0,
"vendedor": 0,
"cliente": 0,
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"observacoes": "string",
"integracao": "string",
"possui_vinculo": true
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza vários pedidos em uma só requisição.
Atualiza pedidos.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id
required
integer
Campo identificador do registro do Pedido.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

hora_criacao	
string
Hora de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

hora_confirmacao	
string
Hora de confirmação do pedido.

departamento	
integer
Campo identificador do departamento ao qual o pedido está vinculado, saiba como recuperar departamentos clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pelo pedido, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual o pedido foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens do pedido.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

valor_acrescimo	
number
Valor de acrescimo do pedido.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

integracao	
string
Caso o pedido veio de alguma integração, informa o nome do parceiro.

possui_vinculo	
boolean
Identifica se o Pedido possui algum vínculo no sistema.

Responses
200 Pedidos atualizados com sucesso e pedidos com erros.

PATCH
/bulk/pedidos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"hora_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"departamento": 0,
"vendedor": 0,
"cliente": 0,
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"valor_acrescimo": 0,
"valor_troco": 0,
"observacoes": "string",
"integracao": "string",
"possui_vinculo": true
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Deleta vários pedidos em uma só requisição.
QUERY PARAMETERS
ids	
string
ID's dos pedidos a serem apagados.

HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Pedidos deletados com sucesso e pedidos com erros.

DELETE
/bulk/pedidos
Criar vários pedidos de compra
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
itens
required
Array of objects (Item de Pedido)
Itens do pedido.

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

funcionario	
integer
Campo identificador do funcionario relacionado ao pedido.

fornecedor	
integer
Campo identificador do fornecedor para o qual o pedido foi aberto, saiba como recuperar fornecedors clicando aqui

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

Responses
200 Pedidos de Compra criados!

POST
/bulk/pedidos_compra
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"funcionario": 0,
"fornecedor": 0,
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"observacoes": "string"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza vários pedidos de compra em uma só requisição.
Atualiza pedidos de compra.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id
required
integer
Campo identificador do registro do Pedido.

numero	
integer
Número/código do pedido. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Default: "A"
Enum: "A" "B" "C"
A=Em aberto | B=Confirmado | C=Cancelado

data_criacao	
string
Data de criação do pedido.

data_entrega	
string
Data de entrega do pedido.

hora_entrega	
string
Hora de entrega do pedido.

data_confirmacao	
string
Data de confirmação do pedido.

fornecedor	
object (Fornecedor)
Dados de um fornecedor, saiba mais detalhes do recurso /fornecedores clicando aqui

itens	
Array of objects (Item de Pedido)
Itens do pedido.

faturas	
Array of objects (Fatura Pagamento)
Faturamento do pedido. São as formas de pagamento usadas para pagar pelo pedido.

valor_frete	
number
Valor do frete do pedido.

valor_desconto	
number
Valor do desconto do pedido.

observacoes	
string
Observações gerais sobre o pedido. Campo de texto livre.

Responses
200 Pedidos de compra atualizados com sucesso e pedidos de compra com erros.

PATCH
/bulk/pedidos_compra
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"fornecedor": {},
"itens": [],
"faturas": [],
"valor_frete": 0,
"valor_desconto": 0,
"observacoes": "string"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Deleta vários pedidos de compra em uma só requisição.
QUERY PARAMETERS
ids	
string
ID's dos pedidos de compra a serem apagados.

HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Pedidos de compra deletados com sucesso e pedidos de compra com erros.

DELETE
/bulk/pedidos_compra
Criar várias ordens de serviço
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
status_os
required
integer
Campo identificador da atividade. É possível recuperar atividades pelo recurso /status_atividades_os, saiba como recuperar status e atividades da OS do ERP clicando aqui

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código da ordem de serviço. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Enum: "A" "B" "C"
Campo identificador do status. É possível criar a os com 3 tipos de campos [A : Em aberto|B Confirmado|C: Cancelado

data_criacao	
string
Data de criação da ordem de serviço.

data_entrega	
string
Data de entrega da ordem de serviço.

hora_entrega	
string
Hora de entrega da ordem de serviço.

data_confirmacao	
string
Data fechamento da ordem de serviço.

hora_confirmacao	
string
Hora de fechamento da ordem de serviço.

data_alteracao	
string
Data da última alteração

departamento	
integer
Campo identificador do departamento ao qual a ordem de serviço está vinculado, saiba como recuperar departamentos clicando aqui

funcionario	
integer
Campo identificador do funcionário responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual a ordem de serviço foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens da ordem de serviço.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da ordem de serviço. São as formas de pagamento usadas para pagar pela ordem de serviço.

objeto_conserto	
Array of objects (Objeto do Conserto)
Detalhes dos objetos e das condições do conserto.

atividades_os	
Array of objects (Objeto do Conserto)
Registro de atividades da ordem de serviço.

valor_desconto	
number
Valor do desconto da ordem de serviço.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre a ordem de serviço. Campo de texto livre.

Responses
200 Ordens de serviço criadas!

POST
/bulk/os
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"data_alteracao": "string",
"status_os": 0,
"departamento": 0,
"funcionario": 0,
"vendedor": 0,
"cliente": 0,
"itens": [],
"faturas": [],
"objeto_conserto": [],
"atividades_os": [],
"valor_desconto": 0,
"valor_troco": 0,
"observacoes": "string"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza várias ordens de serviço em uma só requisição.
Atualiza ordens de serviço.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id
required
integer
Campo identificador do registro da Ordem de serviço.

codigo_externo	
string (codigo_externo) <= 50 characters
Código identificador em aplicações externas

numero	
integer
Número/código da ordem de serviço. Gerado automaticamente.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

status	
string
Enum: "A" "B" "C"
Campo identificador do status. É possível criar a os com 3 tipos de campos [A : Em aberto|B Confirmado|C: Cancelado

data_criacao	
string
Data de criação da ordem de serviço.

data_entrega	
string
Data de entrega da ordem de serviço.

hora_entrega	
string
Hora de entrega da ordem de serviço.

data_confirmacao	
string
Data fechamento da ordem de serviço.

hora_confirmacao	
string
Hora de fechamento da ordem de serviço.

data_alteracao	
string
Data da última alteração

status_os	
integer
Campo identificador da atividade. É possível recuperar atividades pelo recurso /status_atividades_os, saiba como recuperar status e atividades da OS do ERP clicando aqui

departamento	
integer
Campo identificador do departamento ao qual a ordem de serviço está vinculado, saiba como recuperar departamentos clicando aqui

funcionario	
integer
Campo identificador do funcionário responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

vendedor	
integer
Campo identificador do vendedor responsável pela ordem de serviço, é possível recuperar vendedores pelo recurso /usuarios, saiba como recuperar usuarios do ERP clicando aqui

cliente	
integer
Campo identificador do cliente para o qual a ordem de serviço foi aberto, saiba como recuperar clientes clicando aqui

itens	
Array of objects (Item de Pedido)
Itens da ordem de serviço.

faturas	
Array of objects (Fatura Pagamento)
Faturamento da ordem de serviço. São as formas de pagamento usadas para pagar pela ordem de serviço.

objeto_conserto	
Array of objects (Objeto do Conserto)
Detalhes dos objetos e das condições do conserto.

atividades_os	
Array of objects (Objeto do Conserto)
Registro de atividades da ordem de serviço.

valor_desconto	
number
Valor do desconto da ordem de serviço.

valor_troco	
number
Valor do troco.

observacoes	
string
Observações gerais sobre a ordem de serviço. Campo de texto livre.

Responses
200 Ordens de serviço atualizadas com sucesso e com erros.

PATCH
/bulk/os
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"codigo_externo": "string",
"numero": 0,
"numero_fatura": "string",
"status": "A",
"data_criacao": "string",
"data_entrega": "string",
"hora_entrega": "string",
"data_confirmacao": "string",
"hora_confirmacao": "string",
"data_alteracao": "string",
"status_os": 0,
"departamento": 0,
"funcionario": 0,
"vendedor": 0,
"cliente": 0,
"itens": [],
"faturas": [],
"objeto_conserto": [],
"atividades_os": [],
"valor_desconto": 0,
"valor_troco": 0,
"observacoes": "string"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Deleta várias ordens de serviço em uma só requisição.
QUERY PARAMETERS
ids	
string
ID's das ordens de serviço a serem apagadas.

HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Ordens de serviço deletadas com sucesso e com erros.

DELETE
/bulk/os
Criar várias Notas fiscais de entrada
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
itens
required
Array of objects (Item de Venda)
Itens da venda.

cfop
required
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

numero
required
integer <= 9 characters <= 999999999
Númeração da NF-e.

serie
required
integer
Serie da númeração da NF-e.

data_entrada
required
string <date>
Data Entrada.

situacao	
string
Default: "N"
Enum: "N" "A" "S" "E" "2" "4" "F" "X"
N=Em aberto | A=Confirmado | S=Cancelado | 2=Denegada | 4=Inutilizada | E=Normal Extemporânea | F=Aprovada Extemporânea | X=Cancelada Extemporânea

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

modelo	
string
Enum: "55" "01"
Modelo da nota Fiscal

01=Nota Fiscal

55=Nota Fiscal Eletrônica

chave_acesso	
string = 44 characters
Chave de acesso da NF-e.

lancar_estoque	
string
Enum: "" "P" "R"
Qual estoque deve ser movimentado ao confirmar a nota? Válido apenas para produtos com CFOP de 'X.912' ou '1.126'

P=Estoque Próprio

R=Estoque de Revenda (O padrão)

emitente	
integer
ID do fornecedor da nota fiscal.

data_emissao	
string <date-time>
Data de emissão.

hora_entrada	
string <time>
Hora Entrada.

data_criacao	
string <date-time>
Data de criação.

finalidade_emissao	
integer
Enum: 1 2 3 8
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 8=Regime Especial

pedido_vinculado	
integer
Id Pedido de compra vinculado a nota.

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

modalidade_frete	
string
Enum: "0" "1" "2" "3" "4" "9"
0=Contratação do Frete por conta do Remetente (CIF)

1=Contratação do Frete por conta do Destinatário (FOB)

2=Contratação do Frete por conta de Terceiros

3=Transporte Próprio por conta do Remetente

4=Transporte Próprio por conta do Destinatário

9=Sem Ocorrência de Transporte

forma_pagamento	
string
Enum: "0" "1" "2"
0=À Vista

1=À Prazo

2=Outros

transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

ICMSTot	
object
Dados Referente aos Totais do XML

valor_servicos	
number
Valor dos servicos.

valor_icms	
number
Valor do ICMS.

valor_icms_complemento	
number
Complemento de ICMS (SINTEGRA).

valor_cofins_st	
number
Valor da substituicão tributária do cofins.

valor_pis_st	
number
Valor da substituicão tributária do pis.

valor_pis_retido	
number
Valor Total do PIS retido da Nota

valor_cofins_retido	
number
Valor Total do COFINS retido da Nota

valor_csll_retido	
number
Valor Total do CSLL retido da Nota

base_calculo_irrf	
number
Base de cálculo do IRRF

valor_irrf_retido	
number
Valor Total do IRRF retido da Nota

base_calculo_previdencia_social	
number
Base de cálculo da Previdência Social

valor_previdencia_social	
number
Valor Total do Previdência Social retido da Nota

valor_original_fatura	
number
Valor bruto da Fatura vinculada a Nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

inf_fisco	
string
Informações Adicionais de Interesse do Fisco.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinte.

opcoes	
string
JSON com as opções da nota fiscal.

Responses
200 Notas fiscais de entrada criadas!

POST
/bulk/notas_fiscais_entrada
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": 0,
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"pedido_vinculado": 0,
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {},
"itens": [],
"ICMSTot": {},
"valor_servicos": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_original_fatura": 0,
"faturas": [],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Atualiza várias Notas fiscais de entrada em uma só requisição.
Atualiza Notas fiscais de entrada.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
Array 
id
required
integer
Campo identificador do registro da Ordem de serviço.

situacao	
string
Default: "N"
Enum: "N" "A" "S" "E" "2" "4" "F" "X"
N=Em aberto | A=Confirmado | S=Cancelado | 2=Denegada | 4=Inutilizada | E=Normal Extemporânea | F=Aprovada Extemporânea | X=Cancelada Extemporânea

numero	
integer <= 9 characters <= 999999999
Númeração da NF-e.

numero_fatura	
string <= 10 characters
Número da Fatura. Este campo só deve ser informado caso exista um documento de Fatura vinculado a esta nota.

serie	
integer
Serie da númeração da NF-e.

modelo	
string
Enum: "55" "01"
Modelo da nota Fiscal

01=Nota Fiscal

55=Nota Fiscal Eletrônica

chave_acesso	
string = 44 characters
Chave de acesso da NF-e.

lancar_estoque	
string
Enum: "" "P" "R"
Qual estoque deve ser movimentado ao confirmar a nota? Válido apenas para produtos com CFOP de 'X.912' ou '1.126'

P=Estoque Próprio

R=Estoque de Revenda (O padrão)

emitente	
integer
ID do fornecedor da nota fiscal.

data_emissao	
string <date-time>
Data de emissão.

data_entrada	
string <date>
Data Entrada.

hora_entrada	
string <time>
Hora Entrada.

data_criacao	
string <date-time>
Data de criação.

finalidade_emissao	
integer
Enum: 1 2 3 8
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 8=Regime Especial

cfop	
string
Código Fiscal de Operações e Prestações da NF-e. Máscara 9.999

pedido_vinculado	
integer
Id Pedido de compra vinculado a nota.

movimentacao_mercadoria	
boolean
Default: true
Indica se houve movimentacao fisica da mercadoria.

modalidade_frete	
string
Enum: "0" "1" "2" "3" "4" "9"
0=Contratação do Frete por conta do Remetente (CIF)

1=Contratação do Frete por conta do Destinatário (FOB)

2=Contratação do Frete por conta de Terceiros

3=Transporte Próprio por conta do Remetente

4=Transporte Próprio por conta do Destinatário

9=Sem Ocorrência de Transporte

forma_pagamento	
string
Enum: "0" "1" "2"
0=À Vista

1=À Prazo

2=Outros

transportadora	
object
Campo identificador da transportadora, é possível recuperar transportadoras pelo recurso /transportadoras, saiba como recuperar transportadoras do ERP clicando aqui

itens	
Array of objects (Item de Venda)
Itens da venda.

ICMSTot	
object
Dados Referente aos Totais do XML

valor_servicos	
number
Valor dos servicos.

valor_icms	
number
Valor do ICMS.

valor_icms_complemento	
number
Complemento de ICMS (SINTEGRA).

valor_cofins_st	
number
Valor da substituicão tributária do cofins.

valor_pis_st	
number
Valor da substituicão tributária do pis.

valor_pis_retido	
number
Valor Total do PIS retido da Nota

valor_cofins_retido	
number
Valor Total do COFINS retido da Nota

valor_csll_retido	
number
Valor Total do CSLL retido da Nota

base_calculo_irrf	
number
Base de cálculo do IRRF

valor_irrf_retido	
number
Valor Total do IRRF retido da Nota

base_calculo_previdencia_social	
number
Base de cálculo da Previdência Social

valor_previdencia_social	
number
Valor Total do Previdência Social retido da Nota

valor_original_fatura	
number
Valor bruto da Fatura vinculada a Nota.

faturas	
Array of objects (Fatura Pagamento)
Faturamento. São as formas de pagamento usadas no pagamento.

inf_fisco	
string
Informações Adicionais de Interesse do Fisco.

inf_contribuinte	
string
Informações Complementares de interesse do Contribuinte.

opcoes	
string
JSON com as opções da nota fiscal.

Responses
200 Notas fiscais de entrada atualizadas com sucesso e com erros.

PATCH
/bulk/notas_fiscais_entrada
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"situacao": "N",
"numero": 999999999,
"numero_fatura": "string",
"serie": 0,
"modelo": "55",
"chave_acesso": "stringstringstringstringstringstringstringst",
"lancar_estoque": "",
"emitente": 0,
"data_emissao": "2019-08-24T14:15:22Z",
"data_entrada": "2019-08-24",
"hora_entrada": "14:15:22Z",
"data_criacao": "2019-08-24T14:15:22Z",
"finalidade_emissao": 1,
"cfop": "string",
"pedido_vinculado": 0,
"movimentacao_mercadoria": true,
"modalidade_frete": "0",
"forma_pagamento": "0",
"transportadora": {},
"itens": [],
"ICMSTot": {},
"valor_servicos": 0,
"valor_icms": 0,
"valor_icms_complemento": 0,
"valor_cofins_st": 0,
"valor_pis_st": 0,
"valor_pis_retido": 0,
"valor_cofins_retido": 0,
"valor_csll_retido": 0,
"base_calculo_irrf": 0,
"valor_irrf_retido": 0,
"base_calculo_previdencia_social": 0,
"valor_previdencia_social": 0,
"valor_original_fatura": 0,
"faturas": [],
"inf_fisco": "string",
"inf_contribuinte": "string",
"opcoes": "string"
}
]
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Deleta várias Notas fiscais de entrada em uma só requisição.
QUERY PARAMETERS
ids	
string
ID's das vendas a serem apagadas.

HEADER PARAMETERS
X-Apagar-Financeiro	
boolean
Example: true
Indica que ao estornar a venda/pre-venda deverá ser apagado também o lançamento financeiro vinculado.

Responses
200 Notas fiscais de entrada deletadas com sucesso e com erros.

DELETE
/bulk/notas_fiscais_entrada
Criar várias vendas simples a partir de pedidos
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 vendas simples criadas!

POST
/bulk/pedidos/to_venda_simples
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar vários ajustes de estoque a partir de pedidos
HEADER PARAMETERS
X-Tipo-Ajuste
required
string
Example: E
Indica qual o tipo de ajuste de estoque será criado (entrada/saida).

X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Ajustes de estoque criados!

POST
/bulk/pedidos/to_ajuste_estoque
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFEs a partir de pedidos
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFEs criadas!

POST
/bulk/pedidos/to_nfe
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFSEs a partir de pedidos
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFSEs criadas!

POST
/bulk/pedidos/to_nfse
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFCEs a partir de pedidos
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFCEs criadas!

POST
/bulk/pedidos/to_nfce
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias vendas simples a partir de ordens de serviço
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Vendas simples criadas!

POST
/bulk/os/to_venda_simples
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar vários ajustes de estoque a partir de ordens de serviço
HEADER PARAMETERS
X-Tipo-Ajuste
required
string
Example: E
Indica qual o tipo de ajuste de estoque será criado (entrada/saida).

X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Ajustes de estoque criados!

POST
/bulk/os/to_ajuste_estoque
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFEs a partir de ordens de serviço
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFEs criadas!

POST
/bulk/os/to_nfe
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFSEs a partir de ordens de serviço
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFSEs criadas!

POST
/bulk/os/to_nfse
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFCEs a partir de ordens de serviço
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFCEs criadas!

POST
/bulk/os/to_nfce
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar vários ajustes de estoque de compra a partir de pedidos de compra
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Ajustes de estoque criados!

POST
/bulk/pedidos_compra/to_ajuste_estoque
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFEs a partir de pedidos de compra
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFEs criadas!

POST
/bulk/pedidos_compra/to_nfe
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias notas fiscais de entrada a partir de pedidos de compra
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 Notas fiscais de entrada criadas!

POST
/bulk/pedidos_compra/to_nota_fiscal_entrada
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFEs a partir de Sats
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFEs criadas!

POST
/bulk/sats/to_nfe
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFEs a partir de vendas simples
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFEs criadas!

POST
/bulk/vendas_simples/to_nfe
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFCEs a partir de vendas simples
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFCEs criadas!

POST
/bulk/vendas_simples/to_nfce
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Criar várias NFSEs a partir de vendas simples
HEADER PARAMETERS
X-Criar-Financeiro	
boolean
Example: true
Indica que ao confirmar uma venda/pre-venda deverá ser criado também um lançamento financeiro.

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
ids	
Array of integers
Responses
200 NFSEs criadas!

POST
/bulk/vendas_simples/to_nfse
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"ids": [
0
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"success": [],
"errors": []
}
]
Webhook
Integrações via webhook. Para saber mais sobre webhooks clique aqui

Listar webhooks
Recupera webhooks salvos no sistema.

Responses
200 Sucesso!

GET
/webhooks
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"nome_integracao": "Meu sistema de restaurante",
"url": "http://meu-sistema.com.br/integracao-webhook",
"hub_secret": "ABCD12345678",
"eventos": []
}
]
Criar webhook
Criar um webhook

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome_integracao
required
string
Nome da integração.

url
required
string
URL de Callback.

eventos
required
Array of strings
Eventos de disparo.

hub_secret	
string
X-Hub-Secret.

Responses
201 Webhook criado!

POST
/webhooks
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome_integracao": "string",
"url": "string",
"hub_secret": "string",
"eventos": [
"string"
]
}
Response samples
201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"nome_integracao": "Meu sistema de restaurante",
"url": "http://meu-sistema.com.br/integracao-webhook",
"hub_secret": "ABCD12345678",
"eventos": [
"pedido_criado",
"produto_criado",
"estoque_revenda_alterado"
]
}
Recuperar webhook
Recupera um webhook detalhadamente.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/webhooks/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"nome_integracao": "Meu sistema de restaurante",
"url": "http://meu-sistema.com.br/integracao-webhook",
"hub_secret": "ABCD12345678",
"eventos": [
"pedido_criado",
"produto_criado",
"estoque_revenda_alterado"
]
}
Editar webhook
Atualiza as informações do webhook.

PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome_integracao	
string
Nome da integração.

url	
string
URL de Callback.

hub_secret	
string
X-Hub-Secret.

eventos	
Array of strings
Eventos de disparo.

Responses
200 Webhook alterado!

PATCH
/webhooks/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome_integracao": "string",
"url": "string",
"hub_secret": "string",
"eventos": [
"string"
]
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"nome_integracao": "Meu sistema de restaurante",
"url": "http://meu-sistema.com.br/integracao-webhook",
"hub_secret": "ABCD12345678",
"eventos": [
"pedido_criado",
"produto_criado",
"estoque_revenda_alterado"
]
}
Apagar webhook
PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Webhook apagado!

DELETE
/webhooks/{id}
Registro Atividades
Listar registro de atividades
Recupera informações de registros que foram criados, alterados ou apagados no sistema

Valores permitidos para busca de entidade:
  boleto, categoria, cliente, compra, consignacao, empresa,
  endereco, financeiro_conta, financeiro_lancamento, financeiro_plano_conta,
  financeiro_setor, forma_pagamento, fornecedor, funcionario,
  funcionario_api_token, funcionario_perfil_acesso, vendas_simples, nota_fiscal, 
  os, pedido, pre_venda_os_status (status de os), produto, produto_categoria,
  produto_estoque, produto_tabela_tipo_valor, produto_unidade
  produto_valor_venda, produto_vinculado, servico, servico_tabela
  transportadora, tributo_ncm, tipo_contato, financeiro_setor (departamento) 
AUTHORIZATIONS:
Authorization_Code_FlowImplicit_Flow
Responses
200 Sucesso!

GET
/registro_atividades
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 1,
"funcionario": {},
"data_criacao": "2017-01-24 00:00:00",
"evento": "Criou um novo registro de fornecedor",
"tipo_evento": "C",
"entidade": "fornecedor",
"id_entidade": "5",
"nome_app": "",
"id_app": 0
}
]
Recuperar registro de atividades
Recupera um item do Registro Atividades.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/registro_atividades/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"id": 1,
"funcionario": {
"id": 1,
"nome": "Administrador"
},
"data_criacao": "2017-01-24 00:00:00",
"evento": "Criou um novo registro de fornecedor",
"tipo_evento": "C",
"entidade": "fornecedor",
"id_entidade": "5",
"nome_app": "",
"id_app": 0
}
relatorio-entidade
Lista Relatórios Entidades
Lista todos os relatórios de entidade salvos.

Responses
200 Sucesso!

GET
/relatorio_entidade
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Relatório de Entidades
HEADER PARAMETERS
X-Gerar-Relatorio	
integer
Example: 1
Se presente, gera o relatório ao invés de salvar.

1 - Retorna os dados do relatório em formato JSON

2 - Retorna os dados do relatório em formato PDF

3 - Retorna os dados do relatório em formato XML

5 - Retorna os dados do relatório em formato EXCEL

X-Envia-Email	
boolean
Example: true
Indica se o relatório deve ser enviado por email

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!
201 Sucesso!

POST
/relatorio_entidade
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"tipo_entidade": "",
"cliente": [],
"funcionario": [],
"vendedor": [],
"fornecedor": [],
"transportadora": [],
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"melhores_clientes": "",
"incluir_aniversariante": true,
"categoria": [],
"categoria_filhos": "",
"uf": [],
"cidade": [],
"bairro": [],
"agrupa_entidade": true,
"recebe_email": "",
"ativo": "",
"colunas": "string"
}
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"filtro": [],
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
Recupera Relatório de Entidades
Lista todos os relatórios de entidade salvos.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/relatorio_entidade/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Altera Relatório de Entidades
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!

PATCH
/relatorio_entidade/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"tipo_entidade": "",
"cliente": [],
"funcionario": [],
"vendedor": [],
"fornecedor": [],
"transportadora": [],
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"melhores_clientes": "",
"incluir_aniversariante": true,
"categoria": [],
"categoria_filhos": "",
"uf": [],
"cidade": [],
"bairro": [],
"agrupa_entidade": true,
"recebe_email": "",
"ativo": "",
"colunas": "string"
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Apagar Relatório de Entidades
Apaga um relatório específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/relatorio_entidade/{id}
relatorio-funcionario
Lista os Relatórios de Atividades de Funcionários
Lista todos os relatórios de log de funcionarios salvos.

Responses
200 Sucesso!

GET
/relatorio_funcionario_log
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Relatório de Atividade de Funcionários
HEADER PARAMETERS
X-Gerar-Relatorio	
integer
Example: 1
Se presente, gera o relatório ao invés de salvar.

1 - Retorna os dados do relatório em formato JSON

2 - Retorna os dados do relatório em formato PDF

3 - Retorna os dados do relatório em formato XML

5 - Retorna os dados do relatório em formato EXCEL

X-Envia-Email	
boolean
Example: true
Indica se o relatório deve ser enviado por email

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!
201 Sucesso!

POST
/relatorio_funcionario_log
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"data_inicial": "string",
"data_final": "string",
"funcionario": [],
"departamento": [],
"periodo": "",
"outros": "",
"colunas": "string"
}
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
Recupera Relatório de Atividades de Funcionários
Lista todos os relatórios de log de funcionarios salvos.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/relatorio_funcionario_log/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Altera Relatório de Atividades de Funcionários
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!

PATCH
/relatorio_funcionario_log/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"data_inicial": "string",
"data_final": "string",
"funcionario": [],
"departamento": [],
"periodo": "",
"outros": "",
"colunas": "string"
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Apagar Relatório de Atividades de Funcionários
Apaga um relatório específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/relatorio_funcionario_log/{id}
relatorio-financeiro
Lista os Relatórios Financeiro
Lista todos os relatórios financeiros salvos.

Responses
200 Sucesso!

GET
/relatorio_financeiro
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Gera Relatório Financeiro
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!
201 Sucesso!

POST
/relatorio_financeiro
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"situacao_lancamentos": "1",
"tipo_lancamento": "1",
"tipo_relatorio": "1",
"sintetizacao": "",
"acumula_saldo_anterior": true,
"comparar_diferenca_dre": true,
"considerar_transferencia": true,
"carnes_recebidos": true,
"desconsiderar_devolucoes": true,
"tipo_saida_nfe": true,
"tipo_saida_nfce": true,
"tipo_saida_cupom": true,
"tipo_saida_nota_consumidor": true,
"tipo_saida_nfse": true,
"tipo_modelo_01": true,
"tipo_sat": true,
"tipo_saida_pedido_venda": true,
"pedido_compra": true,
"tipo_saida_os": true,
"modelo_vd": true,
"modelo_ae": true,
"consignacao": true,
"agrupamento_periodo": "",
"agrupamento_outros": "",
"tipo_comissao": "",
"data_considerada": "V",
"data_inicial": "string",
"data_final": "string",
"vinculacao": "",
"entidade": [],
"departamento": [],
"plano_orcamentario": [],
"incluir_planos_orcamentarios_filhos": true,
"forma_pagamento": [],
"funcionario_responsavel": [],
"conta": [],
"colunas": "string"
}
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
Retorna Relatório Financeiro
Lista todos os relatórios financeiros salvos.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/relatorio_financeiro/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Altera Relatório Financeiro
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!

PATCH
/relatorio_financeiro/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"situacao_lancamentos": "1",
"tipo_lancamento": "1",
"tipo_relatorio": "1",
"sintetizacao": "",
"acumula_saldo_anterior": true,
"comparar_diferenca_dre": true,
"considerar_transferencia": true,
"carnes_recebidos": true,
"desconsiderar_devolucoes": true,
"tipo_saida_nfe": true,
"tipo_saida_nfce": true,
"tipo_saida_cupom": true,
"tipo_saida_nota_consumidor": true,
"tipo_saida_nfse": true,
"tipo_modelo_01": true,
"tipo_sat": true,
"tipo_saida_pedido_venda": true,
"pedido_compra": true,
"tipo_saida_os": true,
"modelo_vd": true,
"modelo_ae": true,
"consignacao": true,
"agrupamento_periodo": "",
"agrupamento_outros": "",
"tipo_comissao": "",
"data_considerada": "V",
"data_inicial": "string",
"data_final": "string",
"vinculacao": "",
"entidade": [],
"departamento": [],
"plano_orcamentario": [],
"incluir_planos_orcamentarios_filhos": true,
"forma_pagamento": [],
"funcionario_responsavel": [],
"conta": [],
"colunas": "string"
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Apagar Relatório Financeiro
Apaga um relatório específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/relatorio_financeiro/{id}
relatorio-estoque
Lista os Relatórios de Estoque
Lista todos os relatórios de estoque salvos.

Responses
200 Sucesso!

GET
/relatorio_estoque
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Relatório de Estoque
HEADER PARAMETERS
X-Gerar-Relatorio	
integer
Example: 1
Se presente, gera o relatório ao invés de salvar.

1 - Retorna os dados do relatório em formato JSON

2 - Retorna os dados do relatório em formato PDF

3 - Retorna os dados do relatório em formato XML

5 - Retorna os dados do relatório em formato EXCEL

X-Envia-Email	
boolean
Example: true
Indica se o relatório deve ser enviado por email

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

tipo_pdf	
string
Default: "P"
Enum: "L" "P"
Define a orientação da página para gerar o PDF. Somente válido quando for gerar relatório do tipo PDF.

L - Paisagem

P - Retrato

filtros	
object
Responses
200 Sucesso!
201 Sucesso!

POST
/relatorio_estoque
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"tipo_pdf": "L",
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"filtro_produtos": [],
"filtro_categoria": [],
"filtro_atributo": [],
"filtro_finalidade": [],
"filtro_ncm": [],
"fornecedor": [],
"departamento": [],
"categoria_filhos": true,
"status_mercadoria": "-1",
"r_estoque_unidade_considerada": "0",
"r_tipo_estoque": "",
"situacao_estoque": "",
"r_estoque_minimo_maximo": "",
"r_estoque_agrupar": "",
"r_estoque_produto_grade": "0",
"mostrar_produtos_nunca_vendidos": true,
"r_estoque_produto_inclui_custo_medio": true,
"colunas": "string"
}
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
Retorna Relatório de Estoque
Lista todos os relatórios de estoque salvos.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/relatorio_estoque/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Altera Relatório de Estoque
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

tipo_pdf	
string
Default: "P"
Enum: "L" "P"
Define a orientação da página para gerar o PDF. Somente válido quando for gerar relatório do tipo PDF.

L - Paisagem

P - Retrato

filtros	
object
Responses
200 Sucesso!

PATCH
/relatorio_estoque/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"tipo_pdf": "L",
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"filtro_produtos": [],
"filtro_categoria": [],
"filtro_atributo": [],
"filtro_finalidade": [],
"filtro_ncm": [],
"fornecedor": [],
"departamento": [],
"categoria_filhos": true,
"status_mercadoria": "-1",
"r_estoque_unidade_considerada": "0",
"r_tipo_estoque": "",
"situacao_estoque": "",
"r_estoque_minimo_maximo": "",
"r_estoque_agrupar": "",
"r_estoque_produto_grade": "0",
"mostrar_produtos_nunca_vendidos": true,
"r_estoque_produto_inclui_custo_medio": true,
"colunas": "string"
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Apagar Relatório de Estoque
Apaga um relatório específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/relatorio_estoque/{id}
relatorio-inventario
Retorna Relatório de Inventário
Lista todos os relatórios de inventário salvos.

Responses
200 Sucesso!

GET
/relatorio_inventario
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": "string",
"data_referencia": "string",
"data_criacao": "string",
"size": 0
}
]
Gera o Relatório de Inventário
Lista todos os relatórios de inventário salvos.

PATH PARAMETERS
id
required
string
Example: 01_03_2022
HEADER PARAMETERS
X-Gerar-Relatorio	
integer
Example: 1
Se presente, gera o relatório ao invés de salvar.

1 - Retorna os dados do relatório em formato JSON

2 - Retorna os dados do relatório em formato PDF

3 - Retorna os dados do relatório em formato XML

5 - Retorna os dados do relatório em formato EXCEL

X-Envia-Email	
boolean
Example: true
Indica se o relatório deve ser enviado por email

Responses
200 Sucesso!

GET
/relatorio_inventario/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
relatorio-comercial
Lista os Relatórios Comerciais
Lista todos os relatórios de comercial salvos.

Responses
200 Sucesso!

GET
/relatorio_comercial
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Relatório Comercial
HEADER PARAMETERS
X-Gerar-Relatorio	
integer
Example: 1
Se presente, gera o relatório ao invés de salvar.

1 - Retorna os dados do relatório em formato JSON

2 - Retorna os dados do relatório em formato PDF

3 - Retorna os dados do relatório em formato XML

5 - Retorna os dados do relatório em formato EXCEL

X-Envia-Email	
boolean
Example: true
Indica se o relatório deve ser enviado por email

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!
201 Sucesso!

POST
/relatorio_comercial
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"tipo_relatorio": "1",
"status": "",
"cliente": [],
"vendedor": [],
"funcionario": [],
"fornecedor": [],
"categoria_entidades": [],
"categoria_descricao": "string",
"uf": [],
"cidade": [],
"terminal": [],
"departamento": [],
"departamento_vendedor_vinculado": [],
"status_os": [],
"forma_pagamento": [],
"incluir_forma_pgto": true,
"incluir_vale": true,
"tipo_comissao": "",
"periodo": "",
"outros": "",
"tipo_saida_nfe": true,
"tipo_saida_nfse": true,
"tipo_saida_nfce": true,
"tipo_sat": true,
"tipo_saida_cupom": true,
"tipo_saida_nota_consumidor": true,
"tipo_modelo_01": true,
"tipo_modelo_01_devolucao": true,
"tipo_saida_pre_venda": true,
"tipo_saida_os": true,
"tipo_saida_dav": true,
"tipo_saida_pedido_venda": true,
"pedido_compra": true,
"pedido_ecommerce": true,
"tipo_saida_ordem_servico": true,
"tipo_saida_conta_cliente": true,
"modelo_vd": true,
"modelo_ae": true,
"consignacao": true,
"colunas": "string"
}
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
Busca Relatório Comercial
Busca um relatório comercial salvo.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/relatorio_comercial/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Altera Relatório Comercial
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!

PATCH
/relatorio_comercial/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"data_considerada": "C",
"data_inicial": "string",
"data_final": "string",
"tipo_relatorio": "1",
"status": "",
"cliente": [],
"vendedor": [],
"funcionario": [],
"fornecedor": [],
"categoria_entidades": [],
"categoria_descricao": "string",
"uf": [],
"cidade": [],
"terminal": [],
"departamento": [],
"departamento_vendedor_vinculado": [],
"status_os": [],
"forma_pagamento": [],
"incluir_forma_pgto": true,
"incluir_vale": true,
"tipo_comissao": "",
"periodo": "",
"outros": "",
"tipo_saida_nfe": true,
"tipo_saida_nfse": true,
"tipo_saida_nfce": true,
"tipo_sat": true,
"tipo_saida_cupom": true,
"tipo_saida_nota_consumidor": true,
"tipo_modelo_01": true,
"tipo_modelo_01_devolucao": true,
"tipo_saida_pre_venda": true,
"tipo_saida_os": true,
"tipo_saida_dav": true,
"tipo_saida_pedido_venda": true,
"pedido_compra": true,
"pedido_ecommerce": true,
"tipo_saida_ordem_servico": true,
"tipo_saida_conta_cliente": true,
"modelo_vd": true,
"modelo_ae": true,
"consignacao": true,
"colunas": "string"
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Apagar Relatório Comercial
Apaga um relatório específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/relatorio_comercial/{id}
relatorio-produtos servicos
Lista os Relatórios de Itens e Serviços
Lista todos os relatórios de itens e serviços salvos.

Responses
200 Sucesso!

GET
/relatorio_produtos_servicos
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Relatorio de Itens e Serviços
HEADER PARAMETERS
X-Gerar-Relatorio	
integer
Example: 1
Se presente, gera o relatório ao invés de salvar.

1 - Retorna os dados do relatório em formato JSON

2 - Retorna os dados do relatório em formato PDF

3 - Retorna os dados do relatório em formato XML

5 - Retorna os dados do relatório em formato EXCEL

X-Envia-Email	
boolean
Example: true
Indica se o relatório deve ser enviado por email

REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!
201 Sucesso!

POST
/relatorio_produtos_servicos
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"tipo_relatorio": "1",
"tipo_itens": "1",
"nfe": true,
"nfse": true,
"nfce": true,
"tipo_sat": true,
"cupom_fiscal": true,
"nota_consumidor": true,
"modelo_01": true,
"modelo_01_devolucao": true,
"movimentacao_manual": true,
"pre_venda": true,
"dav_os": true,
"dav": true,
"pedido_venda": true,
"pedido_compra": true,
"pedido_ecommerce": true,
"ordem_servico": true,
"conta_cliente": true,
"modelo_vd": true,
"modelo_ae": true,
"consignacao": true,
"nf_serie_d": true,
"produtos_servicos": [],
"categoria": [],
"ncm": [],
"filtro_atributo": [],
"data_inicial": "string",
"data_final": "string",
"cliente": [],
"vendedor": [],
"funcionario": [],
"outros_filtros_objeto": [],
"fornecedor": [],
"fornecedor_vinculado": [],
"uf": [],
"cidade": [],
"status": "",
"agrupamento_periodo": "",
"agrupamento_outros": "",
"data_considerada": "",
"sinal": "",
"tipo_comissao": "",
"separar_produtos": true,
"departamento_produto": [],
"departamento_pedido": [],
"categoria_filhos": "",
"forma_pagamento": [],
"financeiro_confirmado": true,
"filtrar_produtos_filhos": "string",
"incluir_kit_composicao": true,
"colunas": "string"
}
}
Response samples
200201
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"dados": [],
"totais": {},
"agrupado_por": "string"
}
]
Busca Relatório de Itens e Serviços
Lista todos os relatórios de comercial salvos.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

GET
/relatorio_produtos_servicos/{id}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Altera Relatório de Itens e Serviços
PATH PARAMETERS
id
required
integer
Example: 1
REQUEST BODY SCHEMA: 
application/json; charset=utf-8
application/json; charset=utf-8
required
nome	
string
Nome do relatório

compartilhado	
boolean
Indica se o relatório é compartilhado

emails	
Array of strings
Emails para os quais o relatório deve ser enviado

filtros	
object
Responses
200 Sucesso!

PATCH
/relatorio_produtos_servicos/{id}
Request samples
Payload
Content type

application/json; charset=utf-8
application/json; charset=utf-8

Copy
Expand allCollapse all
{
"nome": "string",
"compartilhado": true,
"emails": [
"string"
],
"filtros": {
"ordenar_por": "string",
"ordenacao": "0",
"tipo_pdf": "L",
"periodo_intervalo": "",
"tipo_relatorio": "1",
"tipo_itens": "1",
"nfe": true,
"nfse": true,
"nfce": true,
"tipo_sat": true,
"cupom_fiscal": true,
"nota_consumidor": true,
"modelo_01": true,
"modelo_01_devolucao": true,
"movimentacao_manual": true,
"pre_venda": true,
"dav_os": true,
"dav": true,
"pedido_venda": true,
"pedido_compra": true,
"pedido_ecommerce": true,
"ordem_servico": true,
"conta_cliente": true,
"modelo_vd": true,
"modelo_ae": true,
"consignacao": true,
"nf_serie_d": true,
"produtos_servicos": [],
"categoria": [],
"ncm": [],
"filtro_atributo": [],
"data_inicial": "string",
"data_final": "string",
"cliente": [],
"vendedor": [],
"funcionario": [],
"outros_filtros_objeto": [],
"fornecedor": [],
"fornecedor_vinculado": [],
"uf": [],
"cidade": [],
"status": "",
"agrupamento_periodo": "",
"agrupamento_outros": "",
"data_considerada": "",
"sinal": "",
"tipo_comissao": "",
"separar_produtos": true,
"departamento_produto": [],
"departamento_pedido": [],
"categoria_filhos": "",
"forma_pagamento": [],
"financeiro_confirmado": true,
"filtrar_produtos_filhos": "string",
"incluir_kit_composicao": true,
"colunas": "string"
}
}
Response samples
200
Content type
application/json; charset=utf-8

Copy
Expand allCollapse all
[
{
"id": 0,
"funcionario": {},
"nome": "string",
"compartilhado": true,
"data_criacao": "string",
"filtros": {}
}
]
Apagar Relatório de Itens e Serviços
Apaga um relatório específico pelo id.

PATH PARAMETERS
id
required
integer
Example: 1
Responses
200 Sucesso!

DELETE
/relatorio_produtos_servicos/{i