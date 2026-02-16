# Opcao 478 — Cadastro de Fornecedores

> **Modulo**: Financeiro
> **Paginas de ajuda**: 4 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Cadastro central de fornecedores com ativacao de CCF (Conta Corrente de Fornecedor), definicao de eventos padrao para acerto automatico, configuracao de PEF/CIOT, parametrizacao de pagamento agendado e controle de especialidades.

## Quando Usar
- Cadastrar novo fornecedor (agregados, carreteiros, frota, agencias, parceiros, prestadores de servico)
- Ativar CCF (Conta Corrente de Fornecedor) para controle de creditos/debitos
- Configurar evento padrao para acerto automatico de saldo CCF
- Definir unidade pagamento para processamento agendado
- Cadastrar fornecedor de PEF/CIOT para integracao eletronica
- Cadastrar fornecedor de pneus (opcao 313)
- Consultar fornecedores ativos/inativos com CCF (opcao 535)

## Pre-requisitos
- CNPJ/CPF do fornecedor
- Dados cadastrais completos (razao social, endereco, telefone, email)
- Evento cadastrado (opcao 503) para classificacao de despesa
- Conta bancaria do fornecedor (se adiantamentos/pagamentos)

## Campos / Interface

### Identificacao
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ/CPF | Sim | Identificacao do fornecedor |
| Razao Social | Sim | Nome do fornecedor |
| Nome Fantasia | Nao | Nome comercial |
| Inscricao Estadual | Condicional | Obrigatorio se Pessoa Juridica contribuinte |

### CCF - Conta Corrente de Fornecedor
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CCF ativada | Nao | S = ativa CCF, N = desativa |
| Evento padrao | Condicional | Evento para acerto automatico de saldo (opcao 503) |
| Unidade pagamento | Nao | Unidade para processamento agendado |

### Dados Bancarios
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Banco | Condicional | Banco do fornecedor (se adiantamentos/pagamentos) |
| Agencia | Condicional | Agencia do fornecedor |
| Conta Corrente | Condicional | Numero da conta |
| Tipo de conta | Condicional | Conta corrente, poupanca, etc |

### Outros
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Especialidade | Nao | Tipo de servico prestado (busca parcial permitida) |
| Ativo | Sim | S = ativo, N = inativo |
| UF | Sim | Estado do fornecedor |

## Fluxo de Uso

### Cadastrar Novo Fornecedor
1. Acessar opcao 478
2. Informar CNPJ/CPF
3. Preencher dados cadastrais (razao social, endereco, telefone, email)
4. Informar dados bancarios (se adiantamentos/pagamentos)
5. Definir especialidade (opcional)
6. Marcar como ativo
7. Gravar cadastro

### Ativar CCF (Conta Corrente de Fornecedor)
1. Acessar opcao 478
2. Localizar fornecedor por CNPJ/CPF
3. Marcar "CCF ativada" = S
4. Definir "Evento padrao" para acerto automatico (opcao 503)
5. Definir "Unidade pagamento" para processamento agendado (opcional)
6. Gravar alteracoes
7. CCF passa a ser reconhecida por processos e relatorios (opcao 486)

### Configurar Acerto Automatico de Saldo CCF
1. Parametrizar processamento agendado (opcao 903 - Agendar processamento)
2. No cadastro do fornecedor (opcao 478), definir:
   - CCF ativada = S
   - Evento padrao (para classificacao da despesa)
   - Unidade pagamento (para lancamento no Contas a Pagar)
3. Sistema ira automaticamente:
   - Acertar saldo CCF no periodo configurado
   - Gerar CTRB (se fornecedor for proprietario de veiculo)
   - Lancar despesa no Contas a Pagar (opcao 475) com 2 parcelas:
     - Parcela 1: adiantamento liquidado
     - Parcela 2: saldo a pagar
   - Enviar e-mail com extrato e CTRBs ao fornecedor
   - Disponibilizar resultado no Relatorio 182 (opcao 056)

### Cadastrar Fornecedor de PEF/CIOT
1. Cadastrar fornecedor normalmente (opcao 478)
2. Acessar opcao 903 - Pagamento Eletronico de Frete
3. Parametrizar integracao (login, senha, certificado digital)
4. Definir administradora padrao

### Consultar Fornecedores com CCF
1. Acessar opcao 535
2. Marcar "Com Conta Corrente" = S
3. Selecionar filtros adicionais (ativo, UF, unidade pagamento, especialidade)
4. Gerar relatorio (PDF ou CSV)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 026 | Cadastro de veiculos - proprietario deve ser fornecedor |
| 027 | Proprietario de veiculo - encerra CIOT Agregado excepcionalmente |
| 035 | Romaneio de Entregas - emite CIOT Agregado |
| 056 | Relatorios Gerenciais - Relatorio 182 (resultado acerto automatico CCF) |
| 072 | Emissao de CTRB - credita CCF de carreteiros e agregados |
| 075 | Ordem de Servico - credita CCF de agregados |
| 118 | Ordem de Servico - credita CCF de agregados |
| 313 | Cadastro de pneus - fornecedor deve estar cadastrado |
| 401 | Multiempresa - define unidade responsavel |
| 408 | Tabela de comissao - define comissao de agenciador |
| 428 | Capa de Remessa - processa credito CCF de agencias/parceiros |
| 456 | Conta Corrente - recebe debitos/creditos de adiantamentos a motoristas da frota |
| 475 | Contas a Pagar - recebe acerto de saldo CCF |
| 476 | Liquidacao Contas a Pagar - libera saldos da viagem |
| 486 | Conta Corrente de Fornecedor - usa ativacao e evento padrao |
| 503 | Grupos de eventos - define evento padrao para acerto CCF |
| 522 | Arquivo bancario C Pagar - efetua adiantamento via arquivo |
| 535 | Consulta a Fornecedores - filtra por CCF ativada |
| 607 | Fatura de agencia - processa credito CCF de agencias/parceiros |
| 611 | Conta Corrente de Fornecedor (consulta) - mostra saldo CCF |
| 903 | Configuracoes - parametriza PEF/CIOT, eventos, acerto automatico CCF |
| 904 | Cadastro de bancos - define conta de origem de adiantamentos |

## Observacoes e Gotchas

### CCF - Conta Corrente de Fornecedor
- **Ativacao obrigatoria**: CCF sem ativacao NAO e reconhecida por processos e relatorios, mesmo possuindo lancamentos passados
- **Controle de informalidade**: define valor formal (saldo) a ser utilizado no Contas a Pagar (financeiro, contabil e fiscal) e comunicacao a ANTT
- **Creditos automaticos**: carreteiros/frota (CTRB opcao 072), agregados (OS opcoes 072, 075, 118), agencias/parceiros (mapa opcao 056, fatura opcao 607, capa opcao 428)

### Tipos de Fornecedor
- **Carreteiros**: contratacao avulsa de TAC (Transportador Autonomo de Cargas)
- **Agregados**: contratacao por periodo de TAC
- **Frota**: motoristas proprios da transportadora
- **Agencias/Parceiros**: outras transportadoras ou agenciadores
- **Prestadores de servico**: manutencao, abastecimento, pneus, etc

### Acerto de Saldo CCF
- **Manual**: pela opcao 486 a qualquer momento
- **Automatico**: configurado na opcao 903, executa no periodo agendado
- **Composicao do valor**: saldo CCF + adiantamento
- **Lancamento Contas a Pagar**: 2 parcelas (adiantamento liquidado + saldo a pagar)
- **CTRB**: gerado automaticamente se fornecedor for proprietario de veiculo (opcao 027)
- **RPA**: emitido automaticamente se fornecedor for Pessoa Fisica
- **NF**: Pessoa Juridica deve apresentar documento fiscal

### Evento Padrao
- Classificacao da despesa (opcao 503)
- Define processamento financeiro, fiscal, contabil, frota
- Sugerido automaticamente no acerto de saldo CCF

### Unidade Pagamento
- Define unidade responsavel pelo processamento agendado
- Usado em acerto automatico de saldo CCF
- Lancamento no Contas a Pagar (opcao 475) vinculado a esta unidade

### PEF / CIOT
- **PEF**: Pagamento Eletronico de Frete
- **CIOT**: Codigo Identificador da Operacao de Transporte (ANTT)
- **Obrigatorio para TAC**: carreteiros e agregados
- **Integracao eletronica**: configurada na opcao 903
- **Administradora**: pode ter diversas configuradas (e-FRETE gratuito, outras pagas)
- **CNPJ raiz**: considera todos CNPJs da mesma raiz
- **Certificado digital**: instalado na opcao 903

### CIOT Agregado
- **Emissao**: na contratacao de viagem de transferencia (opcao 072) ou romaneio (opcao 035)
- **Vigencia maxima**: 30 dias
- **Encerramento na ANTT**: na emissao do proximo CIOT apos acerto CCF (opcao 486)
- **Encerramento excepcional**: pela opcao 027 (proprietario de veiculo)

### Multiempresa
- Acerto de saldo CCF ocorre por empresa (opcao 401)
- Saldo CCF so zerada quando todas as empresas fizerem acerto
- Lancamentos (opcao 486) e emissao CTRBs (opcao 072) ocorrem por empresa

### INSS e IR Retidos no CTRB
- Retidos automaticamente para fornecedor Pessoa Fisica
- Opcao 903 parametriza regras de retencao

### Adiantamentos
- **Formas**: DOC, TED, transferencia, dinheiro, arquivo bancario (opcao 522), cheque
- **Conta bancaria**: deve estar cadastrada no fornecedor
- **Composicao do acerto**: valor adiantado compoem parcela 1 do Contas a Pagar (liquidado)
- **Motorista da frota**: devolucao ou reembolso lancado na opcao 486 (link "Lancar")

### Consulta de Fornecedores (Opcao 535)
- Filtros: ativo/inativo, com CCF, UF, unidade pagamento, especialidade
- Busca parcial de especialidade permitida
- Exportacao para CSV disponivel
- Todos os dados buscados no cadastro da opcao 478

### Especialidade
- Tipo de servico prestado (ex: manutencao, abastecimento, pneus, agregado, carreteiro)
- Busca parcial permitida (ex: "manu" encontra "manutencao")
- Usado em filtros de relatorios

### Conta Bancaria
- Obrigatoria se fornecedor recebe adiantamentos ou pagamentos
- Usada em:
  - Adiantamentos (opcao 486)
  - Arquivo bancario C Pagar (opcao 522)
  - Pagamento via DOC/TED/transferencia

### Fornecedor Inativo
- Nao aparece em selecoes de emissao de CTRB, OS, etc
- Pode ser reativado a qualquer momento
- Lancamentos passados permanecem visiveis

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A02](../pops/POP-A02-cadastrar-unidade-parceira.md) | Cadastrar unidade parceira |
| [POP-A05](../pops/POP-A05-cadastrar-fornecedor.md) | Cadastrar fornecedor |
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F02](../pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Ccf conta corrente fornecedor |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
