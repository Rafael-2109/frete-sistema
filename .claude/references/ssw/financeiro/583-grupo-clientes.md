# Opção 583 — Grupo de Clientes

> **Módulo**: Financeiro
> **Páginas de ajuda**: 7 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Agrupa múltiplos CNPJs de clientes sob um único grupo para tratamento unificado em diversas operações do sistema. Permite consolidar análises, faturas, relatórios e operações para empresas com múltiplas filiais ou marcas.

## Quando Usar

- Empresas com múltiplas filiais/CNPJs que precisam de visão consolidada
- Clientes que desejam fatura única agrupando múltiplos CNPJs
- Análise de performance/produção considerando todos os CNPJs de um cliente
- Geração de relatórios gerenciais agregados por grupo econômico
- Processamento em lote de ocorrências para todos os CNPJs do grupo

## Pré-requisitos

- CNPJs dos clientes já cadastrados no sistema (opção 483)
- Definição de qual CNPJ será o principal/representante do grupo
- Identificar quais CNPJs fazem parte do mesmo grupo econômico

## Campos / Interface

### Cadastro do Grupo

- **CNPJ do grupo**: CNPJ principal que representa o grupo
- **CNPJs membros**: Lista de CNPJs que fazem parte do grupo
- **Unidade responsável**: Pode variar por CNPJ ou ser unificada (opção 483)

## Fluxo de Uso

### Configuração Inicial

```
1. Opção 583 → Cadastro do grupo de clientes
2. Informar CNPJ principal do grupo
3. Adicionar CNPJs membros ao grupo
4. Validar agrupamento nas opções que utilizam grupos
```

### Uso em Operações

As opções que aceitam "CNPJ ou Grupo" processam automaticamente todos os CNPJs membros quando o CNPJ do grupo é informado.

## Integração com Outras Opções

### Faturamento e Cobrança

- **Opção 457**: Manutenção de faturas
  - Localiza faturas de todos os CNPJs do grupo
  - Permite faturamento consolidado
- **Opção 459**: Créditos e débitos agendados
  - Aplica lançamentos a todos os CNPJs do grupo
- **Opção 438**: Transferência de faturas para agência
  - Processa faturas de todo o grupo
- **Opção 466**: Relação de transferidos
  - Lista transferências do grupo completo

### Relatórios Gerenciais (opção 056)

- **Relatório 073**: Monitoração de clientes (todas unidades)
  - Clientes agrupados em ordem decrescente de valor de frete
  - Grupos formados pela opção 583
  - Compara valor do frete com 2 meses anteriores
  - Mostra crescimento percentual (CRES)
  - Separado por vendedor (opção 415) e supervisor (opção 067)

- **Relatório 075**: Monitoração de clientes da unidade
  - Mesma estrutura do 073, apenas com clientes da unidade responsável

- **Relatório 157**: Faturas não enviadas ao cliente
  - Acompanhamento de faturas do grupo por e-mail

- **Relatório 154**: Faturas não impressas pelo cliente
  - Controle de impressão de faturas enviadas ao grupo

### Performance e Análise

- **Opção 106**: Performance de entregas
  - Aceita CNPJ ou CNPJ do grupo
  - Gera performance única para todos os CNPJs do grupo
  - 4 relatórios simultâneos:
    1. Performance de Entregas (principal)
    2. CTRCs Atrasados - Culpa Cliente
    3. CTRCs Atrasados - Culpa Transportadora
    4. CTRCs no Prazo
  - Fórmula: `PERFORMANCE = (NOPRAZO / (ENTREGUE - ATRASO CLIENTE)) x 100`

- **Opção 511**: Produção mensal do cliente
  - Com "Processar o Grupo = S", considera todos os CNPJs do grupo
  - Mostra produção mensal do ano anterior e vigente
  - Comparativos entre os 2 anos
  - Crescimento/decrescimento percentual

- **Opção 102**: Classificação ABC e resultado comercial
  - Classifica grupos de clientes
  - Análise de resultado por grupo

### Operações em Lote

- **Opção 930**: Gera BD de ocorrências
  - Extrai ocorrências em CSV para todo o grupo
  - Período de até 31 dias quando informado CNPJ do grupo
  - Filtra por situação (pendente/entregue)

- **Opção 116**: Pesquisa de ocorrências em lote
  - Complementa arquivo CSV do cliente com dados do SSW
  - Processa todos os CNPJs do grupo
  - Busca por: NF, Pedido, CT-e, Volume, etc.
  - **Usar com parcimônia** (sobrecarrega servidores)

- **Opção 153**: Recebimento de notificações do cliente
  - Importa planilha com Pedidos/Notas Fiscais
  - Aplica ocorrências a CTRCs de todo o grupo
  - Tipo "G" considera CTRCs cujo pagador pertence ao grupo

### Cadastros Relacionados

- **Opção 483**: Cadastro de clientes
  - Define unidade responsável por CNPJ
  - CNPJs do grupo podem ter unidades diferentes
- **Opção 415**: Vendedores
  - Relatórios de grupo podem separar por vendedor
- **Opção 067**: Supervisores
  - Relatórios de grupo podem separar por supervisor
- **Opção 406**: Código de mercadoria
  - Filtro adicional em relatórios de performance
- **Opção 180**: Mensagens padrão
  - Configuração de e-mails para faturas do grupo

### Análise de Inadimplência

- **Opção 334**: Arquivo Serasa
  - Marca faturas do grupo para inclusão/baixa
- **Opção 336**: Arquivo Equifax
  - Idem Serasa
- **Opção 337**: Arquivo SPC
  - Inclusão/baixa de faturas do grupo
- **Opção 357**: Marcar faturas como perdidas
  - Processo em lote para faturas do grupo
- **Opção 389**: Bloqueio de clientes
  - Pode bloquear todos os CNPJs do grupo

### Outras Opções

- **Opção 448**: Desconto de faturas
  - Localiza faturas descontadas do grupo
- **Opção 443**: Remessa bancária
  - Envia cobrança de faturas do grupo
- **Opção 444**: Retorno bancário (confirmação de entrada)
- **Opção 458**: Crédito no caixa
- **Opção 456**: Conta bancária (lançamentos)
- **Opção 486**: Conta Corrente do Fornecedor
  - Se agência for membro do grupo
- **Opção 475**: Contas a Pagar
  - Idem CCF

## Observações e Gotchas

### CTRCs Considerados nos Relatórios

**Incluídos:**
- CTRCs normais
- CTRCs de substituição (opção 520)
- Subcontratos não fiscais
- RPSs provisórios (série 999 em algumas opções)

**Excluídos:**
- CTRCs emitidos pela MTZ (opção 531)
- CTRCs anulados (opção 520)
- CTRCs de anulação (opção 520)
- CTRCs complementares (não contam peso/qtd/valor mercadoria para evitar duplicação)
- CTRCs cancelados
- RPSs gerados pela opção 172 (em alguns relatórios)
- RPSs unitizados (opção 172) em pesquisas de ocorrência

### Períodos e Datas

- **Data de emissão/autorização**: Base para seleção em relatórios de monitoração (073/075)
- **Data de autorização SEFAZ**: Base para produção mensal (opção 511)
- **Emissão para RPS**: Base quando não há autorização SEFAZ
- **Dias úteis**: Considerados em comparativos de crescimento
- **Mês em curso**: Comparado com mesmo período usando distribuição percentual (opção 903)

### Performance de Entregas (Opção 106)

- **Pré-entregas**: Podem ser consideradas como entregas (opção 039) com flag "S"
- **Complementares**: Flag "N" exclui CTRCs complementares
- **Subcontratos e Redespacho**: Sempre excluídos
- **Responsabilidade**: Ocorrências classificam atraso como culpa do cliente ou transportadora
- **Período**: Pode ser por autorização do CTRC OU por previsão de entrega
- **Tipo de cliente**: R-remetente, D-destinatário, P-pagador, E-terceiro, T-transportadora, O-todos
- **Tipo de destinatário**: C-totaliza por cidade, D-totaliza por cliente

### Produção Mensal (Opção 511)

- **3 quadros**: Valores mensais deste ano, ano anterior e crescimento
- **Crescimento negativo**: Indica decrescimento
- **Com ICMS**: Flag "S" inclui ICMS no frete
- **Tipo de cliente**: Filtra por tipo de participação no CTRC

### Pesquisa de Ocorrências (Opção 116)

- **Sobrecarga**: Usar com parcimônia, impacta performance
- **Base de dados**: P-últimos 12 meses, M-antes dos 12 meses
- **Tipo de dado**: N-NF, P-Pedido, C-Pré-CTRC, E-CT-e, O-CT-e origem, V-Volume/Shipment
- **Primeira visita**: Primeira ocorrência após SSW 85 (SAÍDA PARA ENTREGA)
- **Mercado Envios**: Primeira visita é qualquer dos códigos 05, 10, 11, 31, 32, 33, 38, 39
- **Nome arquivo EDI**: Arquivo usado para gerar o CT-e
- **Ocorrências informativas**: Não consideradas

### Notificações do Cliente (Opção 153)

- **Formato**: Arquivo CSV (separado por vírgulas)
- **Identificador**: P-Pedido ou N-Nota Fiscal
- **Série NF**: Coluna opcional, útil para clientes com múltiplas séries
- **Tipo**: C-CNPJs específicos, G-todos do grupo
- **Ocorrências proibidas**: Inativas, que informam cliente, tipos ENTREGA ou PRÉ-ENTREGA
- **Indicar sucesso**: Coluna opcional mostra ocorrência lançada

### Faturamento Consolidado

- **Fatura sintética**: Faturas com mais de 5.000 CTRCs são impressas sem relacionar CTRCs
  - CTRCs enviados via EDI separadamente
  - Alguns clientes (ex: Mercado Livre) sempre usam modelo sintético
- **Link Excel desabilitado**: Para faturas com mais de 5.000 CTRCs
- **Pagamento parcial**: Faturas não são incluídas em remessas bancárias (opção 443)
- **ACNI reconhecida**: Liquidação via opção 571

### Crescimento do Frete

- **Indicador no Menu Principal**: Mostra crescimento geral
- **Base**: Data de emissão/autorização dos CTRCs
- **Comparação**: Mesmo período do mês anterior, apenas dias úteis
- **Cálculo**: Percentual sobre valor do frete

### Observações Financeiras

- **Data crédito caixa**: Opção 458, inclusive para faturas descontadas
- **Transferido agência**: Flag "S" indica débito na CCF da agência (opção 486)
- **Envio por e-mail**: Automático na madrugada após geração do boleto (opção 443)
- **Envio manual**: Via opção 457, não envia automaticamente depois (evita duplicidade)
- **Condições para envio**: Não liquidada, não vencida, gerada há menos de 10 dias, com Nosso Número (se bancária), cliente configurado para receber
- **Protocolo de entrega**: Opção 482, pouco usado

### Instruções Gerais vs Bancárias

**Instruções Gerais (opção 457):**
- Para faturas ainda não enviadas ao banco
- Não geram instruções bancárias
- 25+ funções (incluir/excluir CTRCs, alterar datas, crédito/débito, liquidar, cancelar, etc.)

**Instruções Bancárias:**
- Para faturas com CONFIRMAÇÃO DE ENTRADA
- Enviadas ao banco via opção 443
- Funções: Prorrogar, Abater, Protestar, Baixar, Sustar protesto, Serasa (bancos 341 e 748)

### Pontos de Atenção

- **Unidades do mesmo armazém** (opção 431): CTRCs reconhecidos entre unidades
- **Opção 324**: Avaliação individual de veículos (não usa grupo)
- **Opção 531**: MTZ - CTRCs desconsiderados em relatórios
- **Opção 903**: Configurações diversas (automação, distribuição percentual, etc.)
- **Arquivo morto**: Faturas no arquivo morto não permitem impressão/envio
- **Fatura perdida**: Apenas vencidas há mais de 90 dias (prazo anti-fraude)
- **Protesto**: Banco Itaú não exige ocorrência de entrada confirmada
- **Desconto em banco**: Mantém fatura PENDENTE, crédito na conta (opção 456)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
