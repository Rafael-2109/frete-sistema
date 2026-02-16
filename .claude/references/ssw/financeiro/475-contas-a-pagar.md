# Opção 475 — Contas a Pagar (Programação de Despesas)

> **Módulo**: Financeiro
> **Páginas de ajuda**: 25 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Programa e gerencia todas as despesas da transportadora para pagamento. Integra dados fiscais (NF-e/CT-e), financeiros (parcelas, vencimentos) e contábeis (lançamentos automáticos). Suporta importação automática de XMLs do SEFAZ e processamento de retenções de impostos.

## Quando Usar
- Lançamento de todas as despesas operacionais e administrativas
- Programação de pagamentos a fornecedores
- Apropriação de créditos fiscais (ICMS, PIS, COFINS)
- Registro de retenções (IRRF, INSS, ISS, PIS, COFINS)
- Controle de pagamentos a agregados, carreteiros e parceiros
- Acerto de Conta Corrente de Fornecedor (CCF)

## Pré-requisitos
- Fornecedor cadastrado (opção 478)
- Evento de despesa configurado (opção 503)
- NF-e/CT-e importada automaticamente do SEFAZ ou manualmente (opção 608)
- Plano de contas configurado para lançamentos automáticos (opção 526)
- Certificado digital ativo para busca automática de XMLs (opção 903/Certificados)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Unidade** | Sim | Unidade responsável pela despesa (pode ser sobrescrita por EVENTO) |
| **Chave NF-e/CT-e** | Condicional | Chave da DANFE/DACTE (44 dígitos) ou CNPJ/CPF do fornecedor |
| **CNPJ/CPF** | Condicional | Fornecedor se não usar chave NF-e |
| **Evento** | Sim | Classifica despesa (financeiro, fiscal, contábil) |

### Dados Fiscais
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Modelo de documento** | Sim | 55=NF-e, 57=CT-e, 95=Boleto, 99=NFS-e, etc. |
| **CFOP entrada** | Sim | Definido por CFOP saída (opção 432) ou EVENTO |
| **Data de entrada** | Sim | Apropriação crédito ICMS/PIS/COFINS e reconhecimento contábil |
| **Número NF/CT** | Sim | Número do documento fiscal |
| **Série** | Não | Série do documento |
| **Valor total** | Sim | Valor total da NF-e/CT-e |
| **Base ICMS** | Não | Base de cálculo do ICMS |
| **Valor ICMS** | Não | Valor do ICMS (para crédito real) |

### Retenções
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **IRRF** | Não | Imposto de Renda Retido na Fonte |
| **INSS** | Não | Retenção INSS (se habilitado no evento) |
| **ISS Retido** | Não | ISS retido em NFS-e modelo 99 |
| **PIS Retido** | Não | PIS retido na fonte |
| **COFINS Retido** | Não | COFINS retido na fonte |
| **CSLL Retido** | Não | CSLL retido na fonte |

### Dados do Pagamento
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Data de pagamento** | Sim | Data de saída do recurso financeiro (Caixa opção 458) |
| **Mês de competência** | Sim | Sugere mês de inclusão (para relatórios opção 477) |
| **Cód barras boleto** | Não | Para contas-a-pagar via arquivo (opção 522) |
| **QR Code do PIX** | Não | Para contas-a-pagar via arquivo PIX (opção 522) |
| **CNPJ beneficiário** | Não | Favorecido diferente (ex: factoring) |
| **Arquivo de remessa** | Não | Arquivo de remessa do Contas a Pagar (opção 522) |

## Abas / Sub-telas

**Disponíveis para programação:**
- Lista NF-es dos últimos 90 dias não programadas
- XMLs importados automaticamente do SEFAZ (certificado digital ativo)
- Filtros: Destinatário minha unidade, Mais de 90 dias
- Realizar desconhecimento de NF-es (manifesta ao SEFAZ)

**Geração por DANFSe:**
- Leitura de PDF de NFS-e de MEI (microempreendedor individual)
- Portal Nacional de Emissão de NFS-e

**Arquivo DDA:**
- Importa código de barras de boletos (Itaú e Bradesco)
- Insere automaticamente em despesas já cadastradas

**Dados dos produtos:**
- Relação de produtos com dados fiscais
- CST 61 (ICMS Monofásico) → crédito combustível (débito/crédito ICMS)
- IBS e CBS importados automaticamente do XML

**Adicionar novo documento:**
- Adiciona documento à mesma despesa (Número de Lançamento)

**Importar arquivo XML:**
- Adiciona XMLs da despesa (NF-e e CT-e) com mesma raiz do fornecedor
- Data de Entrada única para todos

**Adicionar parcelas:**
- Gera parcelas automaticamente (mensal, bimestral, trimestral)
- Mesmo valor e dia, variando mês

**Unificar parcelas:**
- Unifica várias parcelas em uma (se não aprovadas)

## Fluxo de Uso

### Inclusão Manual
1. Acessar opção 475
2. Informar CNPJ/CPF do fornecedor ou chave NF-e
3. Selecionar Evento (opção 503)
4. Preencher dados fiscais (modelo, CFOP, valores)
5. Informar retenções (se houver)
6. Definir data de pagamento e parcelas
7. Gravar lançamento (anota Número de Lançamento no documento físico)

### Importação de NF-e Disponível
1. Clicar em "Disponíveis para programação"
2. Localizar NF-e na lista (últimos 90 dias)
3. Clicar em "Incluir despesa"
4. Conferir dados importados automaticamente
5. Selecionar Evento
6. Ajustar data de pagamento e parcelas
7. Gravar lançamento

### Acerto de CCF (Conta Corrente Fornecedor)
1. Despesas de fornecedores com CCF ativa (opção 486)
2. Débito simultâneo na CCF ao programar despesa
3. Acertos de saldo via opção 486 geram lançamento automático nesta opção

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 072/075 | Emissão de CTRB gera lançamento contábil de impostos |
| 169 | Pedidos de compra (número gravado no XML) |
| 180 | Mensagens padrão em e-mails |
| 380 | Orçamento (tetos mensais por evento com bloqueio) |
| 401 | Configuração multiempresa, IE, regime PIS/COFINS |
| 432 | Tabela CFOP (define CFOP entrada e créditos) |
| 476 | Liquidação de despesas |
| 477 | Consultas e relatórios de despesas |
| 478 | Cadastro de fornecedores (CCF ativa, evento sugerido) |
| 486 | Conta Corrente do Fornecedor (débito automático) |
| 503 | Eventos de despesas (classificação e processamento) |
| 522 | Liquidação via arquivo (boleto/PIX) |
| 526 | Lançamentos automáticos contábeis de despesas |
| 540 | Plano de contas |
| 541 | Lançamentos automáticos gerais |
| 544 | Relatório de retenções |
| 554 | Provisão de despesas |
| 560 | Aprovação centralizada de despesas |
| 567 | Fechamento fiscal |
| 568 | Habilitação da contabilidade SSW |
| 569 | Conciliação bancária |
| 575 | Estoque da bomba |
| 576 | Informa consumo |
| 577 | Debita veículo |
| 578 | Debita comissão motorista |
| 579 | Debita CTRC |
| 584 | NCMs (define despesas creditáveis) |
| 608 | Importação manual de XMLs |
| 704 | Cadastro de ativo imobilizado (CFOPs 1406, 2406, 1551, 2551) |
| 903 | Aprovação centralizada (ativa/desativa) |
| 996 | Manifestação de desacordo/desconhecimento NF-e |

## Observações e Gotchas

- **Número de Lançamento**: Anotar no documento físico para facilitar controle
- **Confirmação SEFAZ**: Lançamento com NF-e confirma automaticamente recebimento ao SEFAZ
- **Aprovação centralizada**: Pode ser ativada (opção 903/Despesas) e executada (opção 560)
- **Salários**: Usar opção 580 (não esta opção)
- **CCF ativa**: Despesa debita automaticamente Conta Corrente Fornecedor (opção 486)
- **Provisão**: Opção 554 para despesas mensais sem lançamento financeiro/contábil/fiscal
- **Lançamento retroativo**: Permitido se posterior a conciliação bancária (opção 569) e fechamento fiscal (opção 567)
- **Duplicadas**: Sistema impede despesas duplicadas (mesmo CNPJ e NF) no período de 180 dias
- **Dados fiscais**: Podem ser alterados após liquidação (até fechamento fiscal opção 567)
- **Lançamentos complementares**: Sugeridos por EVENTO após confirmação:
  - Debita veículo (opção 577)
  - Informa consumo (opção 576)
  - Estoque bomba (opção 575)
  - Debita CCF (opção 486)
  - Debita CTRC (opção 579)
- **Arquivo morto**: Despesas liquidadas, conciliadas há 180+ dias e incluídas há 1+ ano (sem alterações)
- **Impostos sem CNPJ**: Usar fornecedor com CNPJ fictício ou da própria transportadora
- **Imobilizado**: CFOPs 1406, 2406, 1551, 2551 cadastram automaticamente na opção 704
- **XMLs**: Ficam disponíveis no SSW por 5 anos
- **ICMS Monofásico** (CST 61):
  - Preencher grupo ICMS monofásico para crédito (regime débito/crédito opção 401)
  - RS: Emitir NF de ajuste (opção 551) para tomada de crédito
  - Valores disponíveis opção 433 link ICMS Monofásico
- **IBS e CBS**: Importados automaticamente do XML NF-e/CT-e
- **Regime Não-Cumulativo PIS/COFINS**: Créditos apurados via XMLs importados (opção 401)
- **Retirar de remessa**: Usuário MTZ pode retirar despesa/parcela de arquivo não enviado ao banco
- **Imagens**: JPG, PDF podem ser anexadas à despesa (somente por quem incluiu)
- **NFS-e MEI**: Leitura de PDF via Portal Nacional de Emissão de NFS-e

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-B04](../pops/POP-B04-resultado-ctrc.md) | Resultado ctrc |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F02](../pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Ccf conta corrente fornecedor |
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
