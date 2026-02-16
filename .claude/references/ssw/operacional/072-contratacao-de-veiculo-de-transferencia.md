# Opção 072 — Contratação de Veículo de Transferência

> **Módulo**: Operacional — Contratação e Remuneração
> **Páginas de ajuda**: 16 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Contrata veículos (carreteiros, agregados ou frota) para realizar transferências de carga, emitindo CTRB/OS, gerando CIOT e Vale Pedágio conforme legislação ANTT.

## Quando Usar
- Antes da saída do veículo (opção 025) para vincular CTRB/OS aos Manifestos
- Contratar transporte avulso (carreteiro), periódico (agregado) ou interno (frota)
- Gerar CIOT e Vale Pedágio obrigatórios para terceiros
- Lançar créditos na Conta Corrente do Fornecedor (opção 486)

## Pré-requisitos
- Veículo cadastrado na opção 026 com tipo definido (Frota/Agregado/Carreteiro)
- Proprietário cadastrado na opção 027
- Fornecedor ativo na opção 478 com CCF ativada
- Manifestos já emitidos para o veículo (alguns domínios exigem)
- Vale Pedágio obrigatório para contratação de terceiros

## Campos / Interface — Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Veículo (placa) | Sim | Placa do veículo de tração (cavalo) cadastrado na opção 026 |

### Rodapé Tela Inicial
| Link | Descrição |
|------|-----------|
| Cadastro de veículo | Traz opção 026 para cadastrar veículo |
| Conta C Fornecedor | Traz CCF (opção 486) ativada no fornecedor (opção 478) |
| Consulta CIOT/ANTT | Abre site ANTT com situações de CIOTs |
| Liberar adiantamento PEF | Habilitado para PEFs específicos, liberação manual de saldo |

## Campos / Interface — Tela Principal
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CEP origem | Sim | CEP da cidade origem da contratação |
| Unidade destino | Sim | Unidade destino final (FEC exige cidade) |
| Passar por unidades (opc) | Não | Unidades intermediárias, ordenadas para tabelas e rota Vale Pedágio |
| Previsão de chegada | Sim | Sugerida por tabela (opção 403), usada como expiração do Vale Pedágio |
| Distância | Automático | Calculada entre unidades (opção 403), Google para FEC |
| Tipo carga | Sim | Conforme Resolução 5867/2020 para frete mínimo |
| Manifestos | Exibição | Já emitidos para o veículo, vinculados na saída (opção 025) |
| Valor a Pagar | Sim | Remuneração da viagem ao proprietário |
| Tabela ANTT | Exibição | Frete mínimo carreteiros (Res. 5867/2020, 6076/2026), apenas referência |
| Combustível | Não | Lançado na CCF se informado |
| Pedágio | Não | Lançado na CCF se informado |
| Outros | Não | Outras despesas lançadas na CCF |
| Taxa adm PEF | Não | Lançada na CCF se informado |
| CIOT | Automático | Gerado automaticamente (Carreteiro ou Agregado) |
| Vale Pedágio | Obrigatório | Obrigatório para terceiros, dados inseridos no MDF-e |

## Tipos de Contratação
| Tipo | CTRB/OS | CIOT | Acerto | Observações |
|------|---------|------|--------|-------------|
| Carreteiro | CTRB a cada viagem | CIOT Carreteiro por viagem | Não há | Pessoa física: CTRB + RPA com retenções INSS/IR |
| Agregado | OS na viagem | CIOT Agregado (30 dias) | CCF (opção 486) | OS sem retenções, acerto com retenções |
| Frota | CTRB para adiantamentos | Não gera | Não há | Controle consumo/manutenção/pneus |

## CIOT — Comunicação Obrigatória ANTT
| Tipo | Emissão | Vigência | Encerramento | Observações |
|------|---------|----------|--------------|-------------|
| CIOT Carreteiro | Automático por viagem (opção 072) | 1 viagem | Automático | Valor da contratação |
| CIOT Agregado | Automático (opção 072 ou 035) se não vigente | 30 dias | Próximo CIOT ou acerto CCF | Pagamento no acerto CCF, bloqueio ANTT se > 60 dias sem encerrar |

### CIOT Manual Gratuito
- **Target**: https://www.transportesbra.com.br/vectiofretepublico/
- **Repom**: https://www1.repom.com.br/geracao-de-ciot/
- **Plantões**: Ambipar (0800 117 2020), Apisul (51 98125-5026), E-Frete (0800 943-3800), Extratta (0800 600-0096), NDDCargo (49 3251-8070), Pamcard (0800 726-2279), REPOM (0800 701-6744), Sem Parar (4002 1552 / 0800 015-0252), Target (21 3500-5111), Truckpad (11 4118-2880)
- **Lista oficial ANTT**: https://www.gov.br/antt/pt-br/assuntos/cargas/pef

## Vale Pedágio — Obrigatório para Terceiros
- **Obrigatoriedade**: Resolução ANTT 2.885/2008, falta gera multa em radares ANTT
- **Inserção no MDF-e**: Dados informados na opção 072 são inseridos automaticamente na saída (opção 025)
- **Fornecedor habilitado ANTT**: Verificar lista oficial
- **Integração**: Geração eletrônica integrada à opção 072 (TARGET, SEM PARAR)

## Fluxo de Uso
1. Veículo é cadastrado (opção 026) com tipo Frota/Agregado/Carreteiro
2. Proprietário cadastrado (opção 027) com CCF ativada (opção 478)
3. Manifestos emitidos para o veículo (opção 020)
4. **Usuário acessa opção 072 ANTES da saída do veículo**
5. Informa placa, origem, destino, valor a pagar
6. Sistema gera CTRB/OS e CIOT automaticamente
7. Informar/gerar Vale Pedágio (obrigatório para terceiros)
8. Confirmar contratação
9. Lançamentos automáticos na CCF (opção 486) e Contas a Pagar (opção 475)
10. Saída do veículo (opção 025) vincula CTRB/OS aos Manifestos
11. Chegada (opção 030) encerra CTRB/OS automaticamente

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 025 | Saída do veículo — vincula CTRB/OS aos Manifestos |
| 026 | Cadastro de veículos (tipo Frota/Agregado/Carreteiro) |
| 027 | Cadastro de proprietários |
| 030 | Chegada do veículo — encerramento automático do CTRB |
| 020 | Emissão de Manifestos para o veículo |
| 035 | Emissão de Romaneio — pode gerar CIOT Agregado |
| 478 | Cadastro de fornecedores com CCF ativada |
| 486 | Conta Corrente Fornecedor — créditos/débitos/acerto |
| 475 | Contas a Pagar — lançamentos automáticos |
| 476 | Pagamento — liquidação da despesa do acerto CCF |
| 056 | Gestão — relatório 020 confronta CTRB/OS com Manifestos |
| 399 | Tabelas de remuneração por rota |
| 499 | Tabelas de remuneração por veículo (prioridade sobre rota) |
| 403 | Previsão de chegada e distâncias entre unidades |
| 903 | Configuração de eventos CTRB/Pedágio/Taxa PEF e obrigatoriedade de tabelas |
| 925 | Usuários que desbloqueiam limites de tabelas |

## Observações e Gotchas
- **Vale Pedágio obrigatório**: Falta gera multa eletrônica em radares ANTT
- **CTRB antes da saída**: Alguns domínios bloqueiam CTRB se veículo não manifestado
- **Encerramento automático CTRB**: Ocorre na chegada (opção 030) ou saída (opção 025) se não encerrou antes
- **CIOT bloqueio ANTT**: Sem encerramento há mais de 60 dias bloqueia emissão de novos CIOTs
- **Encerramento CIOT Agregado**: Acerto CCF (opção 486) ou excepcionalmente na opção 027
- **Agregado não pode CIOT em outra transportadora**: Bloqueio ANTT
- **Frete mínimo**: Calculado por Resolução 5867/2020 e 6076/2026, apenas referência (sem controle SSW)
- **Tabelas obrigatórias**: Opção 903/Operação, limites ignorados por usuários com permissão (opção 925)
- **Tabela veículo > tabela rota**: Opção 499 tem prioridade sobre opção 399
- **Pessoa física**: CTRB + RPA com retenções INSS/IR automáticas
- **Pessoa jurídica**: Deve apresentar documento fiscal
- **Integração PEF/CIOT**: Geração automática integrada (vide documentação específica)
- **Eventos configuráveis**: Opção 903/Operação define eventos Contas a Pagar, fornecedor (opção 478) tem prioridade
- **Resultado de viagens**: Relatório 020 (opção 056) disponível diariamente, confronta CTRB/OS com Manifestos
- **Emissão automática CTRB Frota**: Opção 903/Operação ativa, gerado na chegada (opção 030) se não houver CTRB e todos Manifestos finalizarem na unidade
- **TAG pedágio**: Se informada no veículo (opção 026), fornecedor TAG sugerido para Vale Pedágio
- **CPF motorista**: Se informado no veículo (opção 026), motorista sugerido no Manifesto (opção 020) e Romaneio (opção 035)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A09](../pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F02](../pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Ccf conta corrente fornecedor |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
