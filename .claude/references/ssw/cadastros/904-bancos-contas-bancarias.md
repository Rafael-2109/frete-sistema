# Opção 904 — Parâmetros de Banco

> **Módulo**: Cadastros
> **Páginas de ajuda**: 4 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra contas bancárias para movimentação financeira e cobrança/pagamentos bancários. Todo o processo financeiro (contas a receber, contas a pagar e caixa) utiliza como base estas contas.

## Quando Usar
- Cadastrar novas contas bancárias para operação da transportadora
- Configurar contas para cobrança bancária (emissão de boletos)
- Configurar contas para PIX (QR Code em DACTEs à vista)
- Configurar contas para API de cobrança (cobrança online)
- Configurar contas para contas a pagar (pagamentos via arquivo FEBRABAN)
- Criar contas caixa internas (banco 999) para uso na Contabilidade SSW

## Pré-requisitos
- Opção 401: Cadastro de unidades (para multiempresa)
- Opção 483: CNPJ da agência bancária deve estar cadastrado como cliente
- Opção 903/Cobrança: Definir conta principal da empresa e parâmetros do faturamento
- Para cobrança bancária: Homologação junto ao banco (vide processo abaixo)

## Campos / Interface

### Tela Principal

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| EMPRESA | Condicional | Empresa que pertence a conta (quando multiempresa ativado na opção 401) |
| ATIVA | Sim | Indica se a conta está ativa ou não |
| HOMOLOGAÇÃO | Sim | S=conta em homologação (boletos sem efeito financeiro), N=operação normal |
| BANCO | Sim | Código do banco ou 999 para CAIXA interno |
| AGÊNCIA | Sim | Número da agência (dígito verificador opcional) |
| CNPJ AGÊNCIA | Não | CNPJ da agência bancária (deve estar cadastrado na opção 483) |
| CONTA | Sim | Número da conta com dígito verificador |
| CARTEIRA | Sim | Número da carteira de cobrança. Para nova carteira, cadastrar nova conta |
| DESCRIÇÃO DA CONTA | Sim | Descrição para identificar a conta (uso interno) |
| UNIDADE CONTÁBIL CAIXA (OPC) | Condicional | Obrigatório quando banco=999 para cadastrar conta caixa da Contabilidade SSW |
| IMPRIME BLOQUETO | Sim | S=imprime boletos ao gerar remessa (opção 443), N=não imprime |
| IMPRIME BLOQUETO NA EXPEDIÇÃO | Sim | S=boletos podem ser impressos na expedição (opção 007 e 017) |
| GERA ARQUIVO REMESSA | Sim | S=habilitada para arquivo de remessa, A=via API (on-line), N=apenas movimentação financeira |
| ÚLTIMA REMESSA | Não | Número do último arquivo de remessa enviado ao banco |
| CARTEIRA DESCONTO | Sim | S=carteira de desconto (transportadora recebe antes do cliente pagar) |
| CONTA REGISTRADA | Sim | Deve ser S (contas não registradas não existem desde 2017) |
| DIAS CREDITO D+ | Sim | Quantidade de dias para crédito no caixa (opção 458) após liquidação |
| PADRÃO CNAB | Sim | 240 ou 400 (deve ser único por banco no domínio) |
| 1ª/2ª INSTRUÇÃO REMESSA | Não | Instruções de remessa (protesto, baixa automática, juros, etc.) |
| TAXA DE MULTA % | Não | Percentual de multa para pagamento após vencimento |
| QTDE DIAS PARA MULTA | Não | Dias após vencimento para início da cobrança de multa |
| VALOR MÍNIMO PARA PROTESTO | Não | Valor mínimo do boleto para protesto |
| DIAS PARA PROTESTO | Não | Dias para protesto após vencimento (sugerido na opção 483/Faturamento) |
| VALOR MÍNIMO DA FATURA (R$) | Não | Valor mínimo para registro no banco (não usar a partir de 2017) |
| VALOR DA TARIFA (R$) | Não | Valor da tarifa bancária de cobrança |
| Nº DO CONTRATO | Sim | Número do contrato da conta junto ao banco |
| Nº DA AUTORIZAÇÃO | Não | Número de autorização fornecido pelo banco |
| FAIXA NOSSO Nº | Sim | Número inicial e final do NOSSO NÚMERO (ex: 000000000001 a 000099999999) |
| ÚLTIMO NÚMERO | Não | Último NOSSO NÚMERO utilizado |
| CNPJ TITULAR DA CONTA | Sim | CNPJ da transportadora (antigo CNPJ cedente) |
| UTILIZAR DADOS DA UNIDADE | Não | Faturas e boletos impressos com dados desta unidade |
| CNPJ BENEFICIÁRIO DA CONTA | Não | CNPJ cadastrado como fornecedor (opção 478) para antecipação de recursos |
| MENSAGEM BOLETO BANCO | Não | Mensagem/instrução impressa no boleto gerado pelo banco |
| OBSERVAÇÕES | Não | Observação sobre uso da conta |
| MENSAGEM NO BOLETO SSW | Não | Mensagem no boleto (alterável apenas pela Equipe SSW) |
| Local para pagamento | Não | Texto exemplo: "Pagável em qualquer agência até o vencimento" |

### Contas a Pagar

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| GERA ARQUIVO | Sim | S=conta usada para geração de arquivo do contas-a-pagar (opção 522) |
| Nº DO CONTRATO | Condicional | Número do contrato para troca de arquivos do contas-a-pagar |
| ÚLTIMA REMESSA | Não | Número do último arquivo de remessa enviado ao banco |

### Chave PIX

Deve ser informada a chave PIX da conta cadastrada no banco:
- **Celular**
- **CPF/CNPJ**
- **E-mail**
- **Aleatória**

### Credenciais PIX e API de Cobrança

Para ativação da cobrança via PIX e API de cobrança:

| Banco | Configuração |
|-------|--------------|
| **ITAÚ** | Gerar Certificado. Dados fornecidos: identificação da transportadora e token temporário. Validade: 1 ano. Link de atualização habilitado 30 dias antes da expiração |
| **BANCO DO BRASIL** | Campos: Id Cliente, Cliente secret e Chave de acesso do aplicativo |
| **BRADESCO** | Contratar serviço "API PIX com webhook". Fornecer certificado digital com senha. Banco fornece client_id e client_secret |
| **SANTANDER** | Fornecer certificado digital .pem |
| **SICOOB** | Contratar serviço "API PIX com webhook". Fornecer certificado digital com senha. Banco fornece client_id e client_secret |
| **SICREDI** | Configurar conforme documentação específica |

## Fluxo de Uso

### Cadastramento de Nova Conta Bancária
1. Acessar opção 904
2. Informar dados bancários (banco, agência, conta, carteira)
3. Configurar parâmetros de cobrança (se aplicável)
4. Definir conta principal da empresa na opção 903/Cobrança
5. Para cobrança bancária: seguir processo de homologação (vide abaixo)

### Homologação da Cobrança Bancária
1. Cadastrar conta bancária na opção 904
2. Configurar conta principal, juros e parâmetros na opção 903/Cobrança
3. Alterar "Homologação para S" na opção 904
4. Emitir faturas com boletos e arquivo de remessa como teste
5. Enviar boletos e arquivo ao setor de homologação do banco
6. Aguardar aprovação do banco
7. Atualizar numerações (Última remessa e faixa inicial nosso número) se já houve emissões em outro sistema
8. Alterar "Homologação para N" na opção 904

### Habilitação do PIX
1. Cadastrar credenciais PIX fornecidas pelo banco (link Credenciais PIX)
2. DACTEs à vista passarão a ter QR Codes impressos
3. Conta utilizada: da unidade (opção 401) ou da transportadora (opção 903/cobrança)
4. QR Code com expiração: 10 dias após previsão de entrega
5. Verificação de liquidações: on-line (opção 101) ou a cada hora (relatórios)

### Configurando o CAIXA INTERNO (banco 999)
1. BANCO = 999
2. AGÊNCIA = número fictício com DV (ex: 9999-9)
3. CONTA = número fictício com DV (ex: 8888-8)
4. TIPO = descrição (ex: "Caixa da filial XXX")
5. CARTEIRA = número fictício (ex: 111)
6. UNIDADE CONTÁBIL CAIXA (OPC) = sigla da unidade que utilizará esta conta caixa
7. Demais campos não precisam ser preenchidos

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 401 | Define empresas (multiempresa) e unidades que terão contas bancárias |
| 443 | Gera arquivo de remessa de cobrança bancária |
| 444 | Importa arquivo de retorno do banco (liquidações) |
| 456 | Efetua lançamentos manuais no caixa |
| 457 | Liquida faturas em carteira |
| 458 | Mostra caixa on-line da transportadora |
| 476 | Liquida despesas do contas-a-pagar |
| 478 | Cadastro de fornecedores (para CNPJ beneficiário e CNPJ agência) |
| 483 | Cadastro de clientes (define banco de cobrança por cliente) |
| 522 | Gera e recepciona arquivos de contas a pagar |
| 569 | Concilia conta bancária |
| 903 | Define conta principal da empresa e parâmetros de cobrança |

## Observações e Gotchas

### Geral
- Para cadastrar nova carteira, deve-se cadastrar uma **nova conta** (não é possível ter múltiplas carteiras na mesma conta)
- Padrão CNAB (240 ou 400) deve ser único por banco no domínio
- A partir de 2017, todas as cobranças devem ser registradas (não usar VALOR MÍNIMO DA FATURA)

### PIX
- Em domínios com multiempresa ativada, QRCode em operações FOB à vista será da conta da mesma empresa que emitiu o CT-e
- Substituição da chave PIX só pode ser realizada se quantidade de CTRCs com PIX em aberto não ultrapassar 4.999
- Troca de certificado digital deve ser enviada ao banco do PIX com mínimo de 1 semana de antecedência
- DACTEs à vista: conta utilizada é da unidade (opção 401) ou transportadora (opção 903/cobrança)
- QR Code tem data de expiração: 10 dias após data de previsão de entrega (OTC: 5 dias após emissão CIF ou 5 dias após dia de prev entrega CTRC)

### API de Cobrança
- Com API de cobrança configurada, remessas e retornos são processados automaticamente às 23:00h
- Boleto passa a ser híbrido (código de barras + QR Code)
- Fim do arquivo de retorno: informações gravadas on-line pelo banco via Webhook
- Opção 343 permite envio e retorno manual antes do processamento automático

### Remessa do Sicredi
- Ao cancelar remessa do Sicredi (748) pela opção 443, sistema retorna numeração do último arquivo gerado para evitar quebra de sequência

### Avisos por E-mail
- Usuários masters são comunicados por e-mail em caso de intervenções importantes no PIX (certificados, erros, etc.)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
