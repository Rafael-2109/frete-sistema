# Opcao 423 — Parametros Comerciais do Cliente

> **Modulo**: Comercial
> **Paginas de ajuda**: 8 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra parametros comerciais especificos por cliente para cobrancas de servicos adicionais, reentrega, devolucao, recoleta, armazenagem e servicos complementares (paletizacao, agendamento, separacao, capatazia, veiculo dedicado). Define percentuais e minimos para cada tipo de servico baseado no CTRC referencia.

## Quando Usar
- Definir parametros de reentrega/devolucao/recoleta para cliente
- Cadastrar tabela de armazenagem por cliente
- Configurar cobranca de servicos complementares (paletizacao, agendamento, etc.)
- Estabelecer franquia de armazenagem
- Definir cubagem padrao do cliente
- Configurar devolucao de canhoto NF

## Pre-requisitos
- Cliente cadastrado (opcao 483)
- CTRC referencia para aplicar parametros
- Para armazenagem: ocorrencias configuradas (opcao 405)

## Campos / Interface

### Reentrega, Devolucao e Recoleta
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Percentual Reentrega | Condicional | % sobre frete CTRC referencia + minimo R$ |
| Percentual Devolucao | Condicional | % sobre frete CTRC referencia + minimo R$ |
| Percentual Recoleta | Condicional | % sobre frete CTRC referencia (2a tentativa coleta) |

### Armazenagem
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Tabela armazenagem | Condicional | Valores por periodo (dias) |
| Franquia | Condicional | Dias sem cobranca (desconta previsao entrega) |
| Periodo | Condicional | Contado a partir ocorrencia "Paga armazenagem" |

### Servicos Complementares
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Paletizacao | Nao | R$ fixo ou % sobre frete |
| Agendamento | Nao | R$ fixo ou % sobre frete |
| Separacao | Nao | R$ fixo ou % sobre frete |
| Capatazia | Nao | R$ fixo ou % sobre frete |
| Veiculo Dedicado | Nao | R$ fixo ou % sobre frete |
| Devolucao Canhoto NF | Nao | R$ fixo |

### Outros Parametros
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cubagem padrao | Nao | Kg/m3 para calculo peso cubado |
| Tabela Generica | Nao | Parametros para clientes sem tabela especifica |

## Fluxo de Uso

### Cadastro Parametros Cliente:
1. Acessar opcao 423
2. Informar CNPJ cliente
3. Configurar percentuais reentrega/devolucao/recoleta
4. Definir tabela armazenagem (se aplicavel)
5. Cadastrar servicos complementares
6. Informar cubagem padrao
7. Gravar configuracao

### Emissao Reentrega/Devolucao (opcao 016):
1. Sistema usa parametros opcao 423 como base
2. Calcula frete sobre CTRC referencia
3. Aplica % e minimo configurado
4. Emite novo CTRC com valores calculados

### Armazenagem (opcao 136 + 199):
1. Opcao 136: identifica CTRCs com potencial cobranca
2. Sistema conta periodo (ocorrencia "Paga armazenagem" - previsao entrega - franquia)
3. Opcao 199: emite CTRC complementar armazenagem

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004 | Emissao CTRC - aplica servicos adicionais |
| 016 | Reentrega/Devolucao/Recoleta - usa parametros 423 |
| 136 | Identificacao CTRCs para armazenagem |
| 199 | Emissao CTRC armazenagem |
| 222 | CTRC complementar |
| 388 | Local entrega devolucao |
| 405 | Ocorrencias - "Paga armazenagem" |
| 417/418/420 | Tabelas frete - aplicam servicos adicionais |
| 483 | Cadastro clientes |
| 609 | Volumes unitizados - devolucao em conjunto |
| 622 | CTRC Complementar com tabelas |
| 903 | Parametros gerais (fallback se cliente sem tabela) |

## Observacoes e Gotchas

### Reentrega vs Devolucao
- **Reentrega**: mesmo remetente/destinatario, so para efeito frete, operacao continua no CTRC referencia
- **Devolucao**: inverte remetente/destinatario, baixa CTRC referencia (codigo SSW 36), operacao continua no CTRC Devolucao
- **Recoleta**: 2a tentativa coleta, so para efeito frete

### Base de Calculo
- Percentuais aplicados sobre frete CTRC referencia
- **Impostos Repassados** (a partir 01/01/22): calculados conforme cadastro cliente (opcao 483)
- Base calculo: frete CTRC referencia SEM parcela "Imposto Repassado"
- Dominios especificos (EML, BLU, DIR, raiz 20121850): base = frete total CTRC referencia

### Armazenagem
- **Periodo**: contado a partir ocorrencia "Paga armazenagem" (pendencia cliente)
- **Franquia**: dias sem cobranca (descontados automaticamente)
- **Desconta previsao entrega**: nao cobra dias normais de transporte
- **Requisitos CTRC**:
  - Ultima ocorrencia: ENTREGA, BAIXA ou SOLUCIONADA
  - Ocorrencia anterior: marcada "Paga armazenagem" + tipo PENDENCIA CLIENTE
  - Emitido nos ultimos 3 meses

### Servicos Complementares (CTRC Complementar)
- Motivos: **D**-descarga, **V**-veiculo dedicado, **S**-separacao, **Z**-capatazia
- Local prestacao: **O**-cidade origem, **D**-cidade destino
- Opcao 622: emite CTRC Complementar usando tabelas 423
- Tabela Generica: usada para clientes sem tabela especifica

### Restricoes
- **Subcontratos**: reentrega/devolucao so se subcontratante NAO usa SSW
  - Se usa SSW: 1 CTRC = 1 Subcontrato unico. Solicitar subcontratante emitir CTRC reentrega/devolucao
- **Volumes Unitizados** (opcao 609): CTRCs componentes devolvidos em conjunto automaticamente
- **CTRC Simplificado** (opcao 004): NAO pode ter CTRC Complementar gerado
- **Ocorrencia Devolucao autorizada** (codigo SSW 27): transportadoras que usam este codigo so emitem devolucao apos CTRC referencia receber SSW 27

### Devolucao - Particularidades
- **Unidade destino**: usa unidade emissora do CTRC referencia
- **Local entrega**: sugere local expedidor CTRC referencia, considera opcao 388 se existe
- **Taxa Agendamento**: NAO cobrada em CTRC Devolucao
- **Redespacho**: informar quando local entrega destinatario em outra UF

### Cubagem
- Configurada por cliente ou usa padrao transportadora (opcao 903)
- Peso cubado = volume (m3) x cubagem (Kg/m3)
- Frete calculado sobre maior: peso real ou peso cubado

### Fallback
- Se cliente NAO possui parametros opcao 423: usa parametros transportadora (opcao 903)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-D05](../pops/POP-D05-baixa-entrega.md) | Baixa entrega |
