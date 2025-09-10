-	-	Campos da planilha do Sendas	-	Valores pré preenchidos	- Ação no campo -	Explicação do campo
Coluna A	Linha 3	Demanda	Linha 4		- Preenchimento -	Deverá ser preenchido o ID da linha do CNPJ ou algum numero sequencial em que deverá ser o mesmo para filial, ao mudar de filial deverá acrescentar 1
Coluna B	Linha 3	Razão Social - Fornecedor	Linha 4	NACOM GOYA IND COM ALIMENTOS LTDA	-	
Coluna C	Linha 3	Nome Fantasia - Fornecedor	Linha 4	NACOM GOYA	-	
Coluna D	Linha 3	Unidade de destino	Linha 4	SENDAS 923 CD MANAUS	- Extração para pesquisa - 	Usar FilialDeParaSendas.filial para traduzir para o CNPJ em FilialDeParaSendas.cnpj através do método "filial_to_cnpj"
Coluna E	Linha 3	UF Destino	Linha 4	AM	-	
Coluna F	Linha 3	Fluxo de operação	Linha 4	Recebimento	-	
Coluna G	Linha 3	Código do pedido Cliente	Linha 4	19447861-923	- Extração para pesquisa -	A mascara desse campos é (pedido_cliente"-"numero da filial), nosso objetivo é extrair o pedido_cliente que vem antes de "-"
Coluna H	Linha 3	Código Produto Cliente	Linha 4	93734	- Extração para pesquisa - 	Usar ProdutoDeParaSendas.codigo_sendas para traduzir o Código do Sendas para o nosso ProdutoDeParaSendas.codigo_nosso através do método obter_nosso_codigo ou obter_codigo_sendas, avalie o melhor uso
Coluna I	Linha 3	Código Produto SKU Fornecedor	Linha 4	-	-	
Coluna J	Linha 3	EAN	Linha 4	-	-	
Coluna K	Linha 3	Setor	Linha 4	-	-	
Coluna L	Linha 3	Número do pedido Trizy	Linha 4	2998070	-	
Coluna M	Linha 3	Descrição do Item	Linha 4	AZEITONA PTA CAMPO BELO FAT 1,01KG	-	
Coluna N	Linha 3	Quantidade total	Linha 4	20	-	
Coluna O	Linha 3	Saldo disponível	Linha 4	20	-	
Coluna P	Linha 3	Unidade de medida	Linha 4	CX	-	
Coluna Q	Linha 3	Quantidade entrega	Linha 4	-	- Preenchimento -	Preencher a qtd respeitando o campos "Saldo Disponivel", no exemplo está "20" (Coluna O Linha 4)
Coluna R	Linha 3	Data sugerida de entrega	Linha 4	-	- Preenchimento -	Data de Agendamento que deveremos preencher no formato (DD/MM/YYYY)
Coluna S	Linha 3	ID de agendamento (opcional)	Linha 4	-	-	
Coluna T	Linha 3	Reserva de Slot (opcional)	Linha 4	-	-	
Coluna U	Linha 3	Característica da carga	Linha 4	Paletizada	- Preenchimento -	Campo select, utilizar SEMPRE "Paletizada"
Coluna V	Linha 3	Característica do veículo	Linha 4	-	- Preenchimento -	Campos select, utilizar conforme o peso total a ser agendado por CNPJ na área : peso / caminhão
Coluna W	Linha 3	Transportadora CNPJ (opcional)	Linha 4	-	-	
Coluna X	Linha 3	Observação/ Fornecedor (opcional)	Linha 4	-	- Preenchimento -	Gravar um identificador util e único por CNPJ neste agendamento para quando fomos verificar a agenda no portal (extrairemos 1 protocolo para N pedidos de 1 CNPJ posteriormente)
						
						
						
		Caminhão do campos "Select" da coluna "Característica do veículo"	Peso máximo em KG			
		Utilitário	800			
		Caminhão VUC 3/4	2000			
		Caminhão 3/4 (2 eixos) 16T	4000			
		Caminhão Truck (6x2) 23T	8000			
		Carreta Simples Toco (3 eixos) 25T	25000			
		Caminhão (4 eixos) 31T	acima de 25000			
