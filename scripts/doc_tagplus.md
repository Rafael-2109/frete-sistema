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
"tipo_nota_debito": "",
"tipo_nota_credito": "",
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
Enum: 1 2 3 4 5 6 9
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 4=Devolução de mercadoria | 5=Nota de Crédito | 6=Nota de Débito 9=Normal Consumidor Final

tipo_nota_debito	
string
Enum: "" "1" "2" "3" "4" "5" "6" "7" "8"
Tipo de Nota de Débito. 1=Transferência de créditos para Cooperativas | 2=Anulação de Crédito por Saídas Imunes/Isentas | 3=Débitos de notas fiscais não processadas na apuração | 4=Multa e juros | 5=Transferência de crédito na sucessão | 6=Pagamento antecipado | 7=Perda em estoque | 8=Desenquadramento do SN

tipo_nota_credito	
string
Enum: "" "1" "2" "3" "4" "5"
Tipo de Nota de Crédito. 1=Multa e juros | 2=Apropriação de crédito presumido de IBS sobre o saldo devedor na ZFM | 3=Retorno por recusa total na entrega ou por não localização dodestinatário na tentativa de entrega | 4=Redução de valores | 5=Transferência de crédito na sucessão

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

valor_ibs_estadual	
number
Valor Total do IBS Federal da Nota

base_calculo_ibs_estadual	
number
Base de Cálculo do IBS Federal da Nota

valor_ibs_municipal	
number
Valor Total do IBS Municipal da Nota

base_calculo_ibs_municipal	
number
Base de Cálculo do IBS Municipal da Nota

valor_cbs	
number
Valor Total do CBS da Nota

base_calculo_cbs	
number
Base de Cálculo do CBS da Nota

valor_nota	
number
Valor total da nota.

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
"enderecos": [
{
"principal": true,
"cep": "string",
"logradouro": "string",
"numero": "string",
"complemento": "string",
"bairro": "string",
"informacoes_adicionais": "string",
"tipo_cadastro": {
"id": 1,
"descricao": "Comercial"
}
}
]
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
{
"chave_cte": "stringstringstringstringstringstringstringst",
"chave_nfe": "stringstringstringstringstringstringstringst",
"coo": 0,
"data_emissao": "2019-08-24",
"modelo": "55",
"numero_nota": 0,
"numero_ordem_sequencial": 0,
"serie": "string",
"uf_emissor": "string",
"cnpj_emissor": "string",
"cpf_emissor": "string",
"ie_emissor": "string"
}
],
"finalidade_emissao": 1,
"tipo_nota_debito": "",
"tipo_nota_credito": "",
"indicador_presenca": 0,
"indicador_intermediador": 0,
"intermediador": 0,
"tipo_emissao": 1,
"vendedor": 0,
"consumidor_final": true,
"uso_livre_contribuinte": [
{
"identificacao": "string",
"conteudo": "string"
}
],
"econf": [
{
"id": 0,
"id_forma_pagamento": 0,
"data_pagamento": "2019-08-24",
"valor_pagamento": 0,
"status": "A",
"caut": "string"
}
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
"reboque": [
{
"id": 0,
"registro_antt": "string",
"placa_veiculo": "string",
"uf_placa": "string"
}
],
"volume": [
{
"id": 0,
"quantidade": "string",
"especie": "string",
"marca": "string",
"numeracao": "string",
"peso_bruto": 0,
"peso_liquido": 0,
"lacre": [
{
"id": 0,
"lacre": "string"
}
]
}
]
},
"itens": [
{
"produto": 1,
"qtd": 2,
"valor_unitario": 50,
"valor_acrescimo": 0,
"valor_desconto": 0,
"detalhes": ""
}
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
"valor_nota": 0,
"faturas": [
{
"forma_pagamento": 1,
"parcelas": [
{
"documento": "123",
"valor_parcela": 50,
"data_vencimento": "2017-10-10"
},
{
"documento": "456",
"valor_parcela": 50,
"data_vencimento": "2017-10-10"
}
]
}
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
"tipo_nota_debito": "",
"tipo_nota_credito": "",
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"tipo_nota_debito": "",
"tipo_nota_credito": "",
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
Enum: 1 2 3 4 5 6 9
Finalidade pela qual a Nota está sendo emitida. 1=Normal | 2=Complementar | 3=Ajuste | 4=Devolução de mercadoria | 5=Nota de Crédito | 6=Nota de Débito 9=Normal Consumidor Final

tipo_nota_debito	
string
Enum: "" "1" "2" "3" "4" "5" "6" "7" "8"
Tipo de Nota de Débito. 1=Transferência de créditos para Cooperativas | 2=Anulação de Crédito por Saídas Imunes/Isentas | 3=Débitos de notas fiscais não processadas na apuração | 4=Multa e juros | 5=Transferência de crédito na sucessão | 6=Pagamento antecipado | 7=Perda em estoque | 8=Desenquadramento do SN

tipo_nota_credito	
string
Enum: "" "1" "2" "3" "4" "5"
Tipo de Nota de Crédito. 1=Multa e juros | 2=Apropriação de crédito presumido de IBS sobre o saldo devedor na ZFM | 3=Retorno por recusa total na entrega ou por não localização dodestinatário na tentativa de entrega | 4=Redução de valores | 5=Transferência de crédito na sucessão

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

valor_ibs_estadual	
number
Valor Total do IBS Federal da Nota

base_calculo_ibs_estadual	
number
Base de Cálculo do IBS Federal da Nota

valor_ibs_municipal	
number
Valor Total do IBS Municipal da Nota

base_calculo_ibs_municipal	
number
Base de Cálculo do IBS Municipal da Nota

valor_cbs	
number
Valor Total do CBS da Nota

base_calculo_cbs	
number
Base de Cálculo do CBS da Nota

valor_nota	
number
Valor total da nota.

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
"tipo_nota_debito": "",
"tipo_nota_credito": "",
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
"valor_nota": 0,
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
"tipo_nota_debito": "",
"tipo_nota_credito": "",
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"id_cidade": 0,
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
"icms_op_interestaduais": {},
"reforma_tributaria": {}
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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

valor_ibs_estadual	
number
Valor Total do IBS Federal da Nota

base_calculo_ibs_estadual	
number
Base de Cálculo do IBS Federal da Nota

valor_ibs_municipal	
number
Valor Total do IBS Municipal da Nota

base_calculo_ibs_municipal	
number
Base de Cálculo do IBS Municipal da Nota

valor_cbs	
number
Valor Total do CBS da Nota

base_calculo_cbs	
number
Base de Cálculo do CBS da Nota

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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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

valor_ibs_estadual	
number
Valor Total do IBS Federal da Nota

base_calculo_ibs_estadual	
number
Base de Cálculo do IBS Federal da Nota

valor_ibs_municipal	
number
Valor Total do IBS Municipal da Nota

base_calculo_ibs_municipal	
number
Base de Cálculo do IBS Municipal da Nota

valor_cbs	
number
Valor Total do CBS da Nota

base_calculo_cbs	
number
Base de Cálculo do CBS da Nota

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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"valor_ibs_estadual": 0,
"base_calculo_ibs_estadual": 0,
"valor_ibs_municipal": 0,
"base_calculo_ibs_municipal": 0,
"valor_cbs": 0,
"base_calculo_cbs": 0,
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
"combustivel": {},
"reforma_tributaria": {}
}
]

