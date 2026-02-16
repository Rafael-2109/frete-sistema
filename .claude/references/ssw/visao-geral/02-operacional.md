# 02 — Operacional

> **Fonte**: `visao_geral_operacional.htm` (08/03/2020)
> **Links internos**: 107 | **Imagens**: 0

## Sumario

Fluxo operacional completo: Coleta → Expedicao → Transferencia → Chegada → Entrega → Pendencias.

---

## 1. Coleta

### Configuracoes
| Opcao | Funcao |
|-------|--------|
| [404](../cadastros/404-setores-coleta-entrega.md) | Setores de coleta/entrega (subdivisao por CEP) |
| [013](../operacional/013-veiculo-sugerido-setor.md) | Veiculo sugerido por setor |
| [491](../comercial/491-emails-telefones-unidade.md) | Dados da unidade (fone, email) para info ao cliente |
| [402](../cadastros/402-cidades-atendidas.md) | Cidades com servico de coleta |
| 519 | Codigos de ocorrencia de coleta |
| [390](../comercial/390-cadastro-especies-mercadorias.md) | Gerenciamento de risco da coleta |
| [903](../cadastros/903-parametros-gerais.md)/SMS | Disparo de SMS ao cliente/motorista |
| [055](../operacional/055-lembretes.md) | Lembretes para coletas (especialmente devolucao) |

### Cadastramento
- SAC ([opção 001](../operacional/001-cadastro-coletas.md))
- EDI ([opção 600](../edi/600-edi-integracao-eletronica.md) + [opção 006](../operacional/006-emissao-cte-os.md))
- Cliente acessa direto (opção 103) ou via `ssw.inf.br/2/coleta`
- Agendamento automatico (opção 042)
- Ordem de Coleta ([opção 003](../operacional/003-ordem-coleta-gerenciamento.md))

### Execucao
- Gerenciamento de veiculos em coleta: [opção 003](../operacional/003-ordem-coleta-gerenciamento.md)
- Ao final do dia: TODAS as coletas devem estar coletadas, reagendadas ou canceladas
- Acompanhamento: `ssw.inf.br`, opção 050, opção 103

### SSWMobile na Coleta
- Motorista recebe coletas online no seu setor
- Veiculos rastreados ([opção 003](../operacional/003-ordem-coleta-gerenciamento.md))
- Captura chave DANFE ([opção 206](../comercial/206-chaves-danfes-capturadas-coleta.md)) para antecipacao

### Coleta no Cliente
- Volumes vinculados a DANFE via **Etiquetas Sequenciais**
- Se cliente tem identificacao propria → EDI

### Descarga da Coleta
- CT-es gerados ([opção 004](../operacional/004-emissao-ctrcs.md)/[006](../operacional/006-emissao-cte-os.md)) com veiculo que coletou
- SSWBar para identificacao e conferencia
- Acompanhamento online (opção 022)
- Volumes alocados por destino (unidades/setores)

---

## 2. Expedicao

### Emissao de Pre-CTRCs
| Opcao | Tipo |
|-------|------|
| [004](../operacional/004-emissao-ctrcs.md) | Individual — a partir de XML de NF-e (automatico, sem digitacao) |
| [006](../operacional/006-emissao-cte-os.md) | Em lotes — a partir de EDI, Portal NF-e, ou Manifesto SSW |

**Fontes de XML**: email `recebe.nfe@ssw.inf.br`, upload (opção 608), Portal NF-e, aquisicao SSW

### Autorizacao fiscal
- **CT-e (SEFAZ)**: [opção 007](../operacional/007-emissao-cte-complementar.md)
- **RPS (Prefeitura)**: [opção 009](../operacional/009-impressao-rps-nfse.md) (impressao) → opção 014 (envio)
- **Envio automatico ao SEFAZ**: configuravel em [opção 903](../cadastros/903-parametros-gerais.md)
- **Averbacoes e rastreamento**: processados automaticamente

### Verificacoes pre-envio (opção 483/Operacao)
- Pesagem, cubagem, romaneio, recepcao SSWBar

### CTRCs Complementares
| Opcao | Tipo |
|-------|------|
| [222](../comercial/222-emissao-ctrc-servico-complementar.md) | CTRC Complementar |
| 016 | Reentrega e devolucao |
| 089 | Paletizacao |
| [015](../operacional/015-agendamento-entregas.md) | Agendamento |
| [099](../operacional/099-consulta.md) | Estadia |
| 199 | Armazenagem |
| [520](../fiscal/520-substituicao-cte-complementacao-icms.md) | Anulacao/complemento de ICMS |

---

## 3. Transferencia

### Carregamento
- SSWBar para leitura de codigos de barras dos volumes
- Acompanhamento em tempo real ([opção 020](../operacional/020-manifesto-carga.md))
- Conclusao do carregamento → emissao do **Manifesto Operacional**
- Planejamento ([opção 019](../operacional/019-manifesto-operacional.md))
- Cada unidade destino = 1 Manifesto Operacional
- Gerenciamento de risco ([opção 390](../comercial/390-cadastro-especies-mercadorias.md))

### Contratacao do Veiculo (opção 072)
- Tabelas (opção 399/[499](../comercial/499-replicar-config-ctrb-transferencia-veiculo.md)), uso obrigatorio ([opção 903](../cadastros/903-parametros-gerais.md)/Operacao)
- PEF/CIOT integrados com administradoras
- CCF ([opção 486](../financeiro/486-conta-corrente-fornecedor.md)): viagens creditam automaticamente

### Saida do Veiculo (opção 025)
- Apos contratacao + Manifestos emitidos
- MDF-e emitido por UF destino (enviado ao SEFAZ)
- Rastreamento automatico (`ssw.inf.br`)
- SSWMobile: localizacao a cada 5 min

---

## 4. Chegada da Transferencia (opção 030)

- SSWMobile pode dar chegada automatica ([opção 903](../cadastros/903-parametros-gerais.md)/Operacao)
- Ocorrencias ([opção 033](../operacional/033-ocorrencias-de-transferencia.md)), resolucao (opção 108)
- Rastreamento e emails atualizados automaticamente
- Descarga com SSWBar (opção 264)

---

## 5. Entrega

### Carregamento para Entrega
- SSWBar para leitura dos volumes ([opção 035](../operacional/035-romaneio-entregas.md))
- Conclusao → emissao do **Romaneio de Entregas**
- Planejamento ([opção 081](../operacional/081-romaneio.md))
- Rastreamento e SMS de entrega iminente ([opção 903](../cadastros/903-parametros-gerais.md)/SMS)

### Baixa de Entregas (opção 038)
- Manual pela [opção 038](../operacional/038-baixa-entregas-ocorrencias.md)
- SSWScan ([opção 398](../comercial/398-escanear-comprovantes-entregas.md)): scan do comprovante baixa o CTRC
- SSWMobile: foto/assinatura em tempo real

### Retaguarda
- Frete FOB a vista ([opção 048](../operacional/048-liquidacao-vista.md))
- Capear comprovantes (opção 040) → enviar a matriz
- Contratacao de agregados: [opção 409](../comercial/409-remuneracao-veiculos.md) → 076 → 075 → [486](../financeiro/486-conta-corrente-fornecedor.md)

---

## 6. Resolvendo Pendencias

- Ocorrencias interrompem fluxo normal → registradas com codigos ([opção 039](../operacional/039-acompanhamento.md))
- Transferencia: [opção 033](../operacional/033-ocorrencias-de-transferencia.md)
- Entrega: [opção 038](../operacional/038-baixa-entregas-ocorrencias.md)
- SSWBar detecta faltas/sobras automaticamente (opção 022, [020](../operacional/020-manifesto-carga.md), 264, [035](../operacional/035-romaneio-entregas.md))
- Toda unidade deve instruir solucao (opção 108)
- **Nenhuma ocorrencia deve permanecer pendente ao final do dia**

---

## Fluxo Completo

```
COLETA                  EXPEDIÇÃO                TRANSFERÊNCIA
001 Cadastro     →  004/006 Pre-CTRC      →  020 Manifesto
003 Ordem Coleta →  007 Envio SEFAZ       →  072 Contratação
SSWMobile        →  009/014 RPS/Prefeitura →  025 Saída veículo
                                                 ↓
                    ENTREGA               ←  030 Chegada
                    035 Romaneio          ←  264 Descarga SSWBar
                    038 Baixa entrega     ←  033 Ocorrências
                    048 Liquidação vista  ←  108 Resolver pendências
```

---

## Contexto CarVia

### Opcoes que CarVia usa

| Opcao | POP | Status | Quem Faz |
|-------|-----|--------|----------|
| [004](../operacional/004-emissao-ctrcs.md) | C01, C02 | ATIVO | Rafael/Jaqueline |
| [007](../operacional/007-emissao-cte-complementar.md) | C01, C02, C05 | ATIVO | Rafael |
| [035](../operacional/035-romaneio-entregas.md) | D02 | PARCIAL | Rafael |

> **C03** (CTe complementar), **C06** (cancelar CTe), **C07** (carta de correcao) usam a mesma opcao 007 mas NAO IMPLANTADOS — Rafael nunca executou esses processos.

### Opcoes que CarVia NAO usa (mas deveria)

| Opcao | POP | Funcao | Impacto |
|-------|-----|--------|---------|
| [020](../operacional/020-manifesto-carga.md) | D03 | Manifesto de carga | **RISCO LEGAL** — obrigatorio para transporte interestadual |
| [025](../operacional/025-saida-veiculos.md) | D03 | Saida de veiculos / MDF-e | **RISCO LEGAL** — multa fiscal + seguro pode nao cobrir sinistro |
| [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) | D01 | Contratacao de veiculo | Sem CIOT formal = multa ANTT + bloqueio cadastral |
| [038](../operacional/038-baixa-entregas-ocorrencias.md) | D05, D06 | Baixa de entrega + ocorrencias | Fundamental para fechar ciclo operacional |
| [030](../operacional/030-chegada-de-veiculo.md) | D04 | Chegada de veiculo | Relevante quando usar transferencias |
| [033](../operacional/033-ocorrencias-de-transferencia.md) | D06 | Ocorrencias de transferencia | Sem registro no SSW |
| [108](../operacional/108-ocorrencias-entrega.md) | D06 | Resolver ocorrencias de entrega | Sem registro no SSW |
| 040 | D07 | Capas de comprovantes de entrega | Nao controla comprovantes no SSW |
| [049](../operacional/049-controle-comprovantes.md) | D07 | Controle de comprovantes | Nao controla comprovantes no SSW |
| 428 | D07 | Comprovantes de entrega | Nao controla comprovantes no SSW |
| [459](../financeiro/459-cadastro-tde.md) | C04 | Cadastro de TDE/diaria | Rafael nao sabe onde cadastrar custos extras |

### Responsaveis

- **Atual**: Rafael (emissao CTe, romaneio esporadico), Jaqueline (apoio CTe fracionado)
- **Futuro**: Rafael (expedicao), Stephanie (entrega/baixa/ocorrencias — pendente treinamento PEND-08)
