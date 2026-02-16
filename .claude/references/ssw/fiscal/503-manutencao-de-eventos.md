# Opcao 503 — Manutencao de Eventos

> **Modulo**: Fiscal
> **Paginas de ajuda**: 2 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Efetua manutencao da tabela de Eventos, que classificam despesas e definem processos financeiros, fiscais, contabeis, de repasses, controle de frota e almoxarifado. Cada evento configura comportamentos automaticos para lancamentos de despesas.

## Quando Usar
- Cadastrar novos tipos de eventos (classificacoes de despesa)
- Configurar processos automaticos vinculados a eventos (repasses, creditos, retencoes)
- Agrupar eventos por natureza, centro de custos ou processo
- Definir sugestoes fiscais (CFOP, tipo de documento) para lancamento de despesas

## Pre-requisitos
- Entendimento dos processos financeiros e fiscais da transportadora
- Grupos de Eventos cadastrados (opcao 553) para organizacao
- Unidades cadastradas (se for definir unidade responsavel no evento)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Novo evento | - | Link para cadastrar novo evento |
| Grupo de Evento | Nao | Grupo do evento (opcao 553) para agrupamento em relatorios |
| Debita veiculo | Nao | X = repassa despesa a veiculos (opcao 577) |
| Informa consumo | Nao | X = informa consumo de veiculos (opcao 576) |
| Estoque bomba | Nao | X = entrada de combustivel na bomba interna (opcao 575) |
| Debita CCF | Nao | X = lancamento na Conta Corrente Fornecedor (opcao 486) |
| Debita CTRC | Nao | X = debita despesa a CTRCs (opcao 579) |
| Debita Comissao Motorista | Nao | X = debita base de calculo da comissao (opcao 691) |
| Ativo | Sim | Ativa/desativa uso do evento |
| Mais | - | Link para tela de configuracao complementar |

### Tela 2 (Complementar)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Evento** | | |
| Unidade | Nao | Define unidade responsavel (prioridade sobre opcao 475) |
| **Fiscal** | | |
| Tipo de documento fiscal | Nao | Tipo sugerido no lancamento (opcao 475) |
| CFOP de entrada | Nao | CFOP sugerido no lancamento (opcao 475) |
| **Credito** | | |
| Credita PIS/COFINS | Nao | S = gera credito PIS/COFINS se unidade for nao-cumulativa |
| Percentual diferenciado PIS/COFINS | Nao | N = aliquotas normais (1,65% e 7,60%), S = reduzidas (1,24% e 5,70%) |
| Conta Contabil PIS/COFINS | Nao | Obrigatorio se nao-cumulativa e usa SPED Contribuicoes |
| Natureza do credito | Nao | Define natureza no SPED Contribuicoes (opcao 515) |
| **Retencao** | | |
| Retencao | Nao | S = abre campos de retencao (IR, INSS, CSLL, PIS, COFINS, SEST/SENAT, PREV SOCIAL, ISS) na opcao 475 |
| Classificacao servico (REINF) | Nao | Para geracao SPED EFD REINF (opcao 587) |
| Natureza Rendimento (REINF) | Nao | Para geracao SPED EFD REINF (opcao 587) |
| **Outros** | | |
| Cadastrar imobilizado | Nao | S = apos inclusao da despesa, traz tela de imobilizado (opcao 704) |
| Entrada no Almoxarifado | Nao | S = apos inclusao, traz tela de almoxarifado (opcao 124) |
| Informacao restrita | Nao | S = despesa nao aparece na consulta controlada (opcao 488) |
| Concessionarias/tributos | Nao | S = identifica despesa como concessionaria/tributo (util para QR Code PIX na opcao 522) |

## Fluxo de Uso
1. Acessar opcao 503
2. Clicar em "Novo evento" ou editar evento existente
3. Configurar grupo, repasses e processos automaticos na tela inicial
4. Clicar em "Mais" para configurar aspectos fiscais, creditos e retencoes
5. Definir unidade responsavel se necessario (util para cadastro descentralizado de frota)
6. Salvar evento

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 475 | Lancamento de despesas (usa eventos para classificacao) |
| 553 | Cadastro de Grupos de Eventos (agrupamento) |
| 577 | Repasse de despesa a veiculos |
| 576 | Informacao de consumo de veiculos |
| 575 | Entrada combustivel bomba interna |
| 486 | Conta Corrente Fornecedor |
| 579 | Debito de despesa a CTRCs |
| 691 | Comissao motorista frota |
| 515 | SPED Contribuicoes PIS/COFINS |
| 587 | SPED EFD REINF |
| 704 | Cadastro de imobilizado |
| 124 | Almoxarifado |
| 488 | Consulta controlada de despesas |
| 522 | Arquivo Contas a Pagar (QR Code PIX) |
| 401 | Regime de Incidencia (Nao-Cumulativa) |
| 056 | Relatorios 001-SITUACAO GERAL e 100-SITUACAO DO CAIXA (agrupam por grupos) |

## Observacoes e Gotchas
- **Simplicidade**: tabela deve ter poucos codigos e ser de simples interpretacao (atribuicao manual na despesa)
- **NAO e sistema de custos**: nao criar eventos para centros de custos — SSW nao suporta rateio para atender simultaneamente fiscal e contabil
- **Grupos de eventos**: usar opcao 553 para agrupar eventos de mesma natureza/centro de custos/processo
- **Credito PIS/COFINS**: so gera credito se (1) evento configurado com S, (2) unidade responsavel for nao-cumulativa (opcao 401)
- **Aliquotas diferenciadas**: aliquotas reduzidas (1,24% PIS e 5,70% COFINS) aplicam-se a modelos 07, 08, 10, 67, 94, 97, 98, 99
- **Prioridade de unidade**: se evento tem unidade definida, prevalece sobre unidade informada no lancamento (opcao 475)
- **Retencoes**: campo "Retencao = S" abre multiplos campos na tela de lancamento (IR, INSS, CSLL, PIS, COFINS, SEST/SENAT, PREV SOCIAL, ISS)
- **Processos automaticos**: marcar X nas colunas da tela inicial faz lancamentos complementares automaticos apos inclusao da despesa
- **SPED**: campos REINF e Conta Contabil PIS/COFINS sao obrigatorios se transportadora gera arquivos SPED respectivos

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A05](../pops/POP-A05-cadastrar-fornecedor.md) | Cadastrar fornecedor |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F02](../pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Ccf conta corrente fornecedor |
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
