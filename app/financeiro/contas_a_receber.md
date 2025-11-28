# Pseudocampos da tabela

# Contas a Receber

## Empresa: Registrar o numero diante do nome importado do Odoo.
1 - NACOM GOYA - FB
2 - NACOM GOYA - SC
3 - NACOM GOYA - CD

## Titulo: NF-e

## Parcela
Exibir sempre: "Titulo"-"Parcela"

## CNPJ (Acrescentar campo na importação, verificar nome no serviço CarteiraService)

## Razão Social: Parceiro/Razão Social

## Razão Social Reduzida (Acrescentar campo na importação, verificar nome no serviço CarteiraService)

## Emissão: Data

## Vencimento: Data de Vencimento

## Liberação Prevista Antecipação: Data calculada através da tabela LiberaçãoAntecipação + EntregaMonitrada.data_hora_entrega_realizada

## Valor Original: Saldo Total

## Desconto %: Converter "Desconto Concedido (%)"/100

## Desconto: Desconto Concedido

## Valor Titulo: Saldo (Valor Original - Desconto - Abatimento.Valor)

## Tipo do Titulo: Forma de Pagamento

## Confirmação : Select da tabela de Tipos

## Forma de confirmação: Select da tabela de Tipos

## Observação: Campo preenchido no sistema

## Data de Confirmação: Log do preenchimento de Confirmação de entrega

## Confirmação de entrega: Campo preenchido no sistema

## Alerta = Boolean preenchido no sistema

## Ação Necessaria: Select da tabela de Tipos

## Obs da Ação Necessaria: Campo preenchido no sistema

## Data Lembrete: Data Preenchida no sistema


# Abatimento

## FK pra Contas a Receber pelo Titulo + Parcela

## Tipo: Select da tabela de Tipos

## Motivo: Campo preenchido no sistema

## Doc. do Motivo: Campo preenchido no sistema

## Valor: Campo preenchido no sistema

## Previsto: Boolean preenchido no sistema

## Data: Campo preenchido no sistema

## Data Vencimento: Campo preenchido no sistema


# Tipos

## Tipo

## Considera a Receber: Boolean para determinar se considera na projeção do contas a receber através de "Tipos.Tipo=Titulo Negociado" utilizado na tabela Contas a Receber

## Tabela

## Campo

## Explicação


# LiberaçãoAntecipação

## Critério de identificação: Select da tabela de Tipos (Prefixo do CNPJ / Nome Igual / Contem Nome)

## Identificador

## UF: Todos ou UFs especificos

## Dias Úteis Previsto


==========================================================

# Escopo:

## Objetivo: Montar o Contas a Receber importado do Odoo adicionando regras de negócio e enriquecimento de informações de EntregaMonitorada

# Enriquecimento: Através de dados de EntregaMonitorada

Acrescentar nesse enriquecimento:

## Acesso aos canhotos

## data_entrega_prevista

## Informações sobre AgendamentoEntrega (N/1 EntregaMonitorada)

## status_finalizacao

## nova_nf

## reagendar

## data_embarque

## transportadora

## vendedor

# Enriquecimento com FaturamentoProduto.ativo (Se false = CANCELADA)