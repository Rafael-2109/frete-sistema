Acabei de implementar um processo de:
1- Importação dos comprovantes de pagamento de boleto em PDF.
2- Importação do extrato OFX vinculando esse comprovante com o Odoo.
3- Agora preciso criar um Match completo desse comprovante com os pagamentos do Odoo.
Use o agente de desenvolvimento para fazer isso:

1- Utilizar o CNPJ do cliente para pesquisar pela empresa no Odoo (Se for da Nacom, pesquise pelas 3 empresas do Odoo, se for LF pesquise apenas LF).
2- CNPJ do Beneficiario deve ser o CNPJ do Fornecedor do Odoo, antes de utilizar esse parametro, verifique no Odoo se há alguma fatura com esse CNPJ (Há fornecedores que descontam o titulo com financeiras e com isso o CNPJ do Beneficiario poderá ser o da financeira, porem as financeiras não emitem faturas para nós, logo a forma assertiva de saber se é financeira é ver se existe fatura com esse CNPJ)
3- Valor do documento deverá ser o valor da parcela do Odoo (nessa questão há uma particularidade que vou expor abaixo.)
4- Numero do documento deverá ser a NF + parcela (Tambem explico abaixo pelas variações aparentes).

<valor>
As parcelas do Odoo são divididas considerando uma qtd limitada de casas decimais, portanto eu precisaria que o sistema avaliasse a condição de pagamento, enxergasse quantas parcelas há na condição de pagamento, pegasse o valor da fatura, dividisse pela qtd de parcelas da condição de pagamento e ajustasse o valor das parcelas caso a fatura não tenha nenhum pagamento vinculado, ANTES de fazer o match).
</valor>

<numero_documento>
O numero do documento poderá vir através de diversas combinações de NF + parcela e incluindo N "0" na frente (000000123456..), segue exemplos abaixo:
<exemplos>
12345-01
12345-001
12345-1
12345/1
12345/01
12345/001
12345 1
12345 01
12345 001
12345A (parcela 1)
123451
1234501
12345001
</exemplos>
</numero_documento>
Para trazer os matchs / encontrar o match e conhecendo o negócio, pensei nessas etapas:
1- Precisamos 1º encontrar o Fornecedor (até pra verificar se usamos ou não o CNPJ)
2- Precisamos encontrar o valor da parcela (após revalidar as parcelas através da correção dos valores)
3- Precisamos encontrar o numero da NF (Pra isso, precisamos verificar se a condição de pagamento é parcela unica ou N parcelas, caso seja N parcelas, devemos descobrir qual parcela estamos tratando, para isso extraia o numero da parcela através dos exemplos, sempre iniciando com o ultimo caracter e removendo os simbolos/espaço, caso seja um caso de "1234501", devemos retirar apenas o 1 e tentar, depois remover os N "0" antes do 1, 1 por vez até chegar em um numero (teste 1 - NF123450 parcela 1 | teste 2 NF12345, remove "0", parcela 1, teste 3 "invalidar" pois tiraria "50" e "5" é != de 0)

Com isso, preciso que crie uma tabela para "Lançamento de comprovantes" registrando o comprovante e os dados da fatura que será realizado o match com % de confiança.