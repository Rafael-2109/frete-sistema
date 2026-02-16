# Opcao 250 — Controle de Acareacao - Matriz

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (opcoes 250 e 251)
> **Atualizado em**: 2026-02-14

## Funcao
Efetua cadastramento e acompanhamento de requisicoes do embarcador (cliente) para cumprimento pelas unidades entregadoras, quando o cliente contesta a entrega da mercadoria e solicita: Comprovante de Entregas, Acareacao de Entregas ou devolucao da mercadoria.

## Quando Usar
- Cliente contesta entrega de mercadoria e solicita comprovante/acareacao/devolucao
- Necessario registrar requisicao formal do cliente com prazo estabelecido
- Preciso debitar valor de mercadoria nao entregue ao parceiro (unidade terceirizada)
- Acompanhamento gerencial de acareacoes em andamento

## Pre-requisitos
- CTRC emitido e autorizado
- Solicitacao formal do cliente (comprovante/acareacao/devolucao)
- Para debito: parceiro cadastrado (opcao 486)

## Campos / Interface

### Incluir Requisicao
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Requisicao | Sim | 10=Comprovante de Entregas, 20=Acareacoes, 30=Devolucao da mercadoria |
| Prazo | Sim | Prazo em dias corridos estabelecido pelo cliente |
| Complemento | Nao | Informacao adicional da requisicao |
| Tipo de dado | Condicional | Tipo de dado enviado pelo cliente para localizacao do CTRC |
| Arquivo | Condicional | Arquivo enviado pelo cliente (processo de importacao ajustado pela equipe SSW) |

### Debito de Mercadorias
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC (com DV) | Sim | CTRC cuja mercadoria sera debitada da unidade responsavel pela entrega (via opcao 486) |

### Relatorio de Situacao
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Filtros diversos | Nao | Permitem gerar relatorio da situacao das acareacoes |

## Fluxo de Uso

### Processo Completo (Matriz + Filial)
1. **Cliente**: contesta entrega e solicita comprovante/acareacao/devolucao
2. **Matriz (opcao 250)**: cadastra requisicao do cliente, informando tipo (10/20/30) e prazo
3. **Sistema**: CTRCs com acareacao recebem ocorrencia SSW 21 - "Acareacao solicitada"
4. **Filial (opcao 251)**: atende solicitacao cadastrada
   - Para acareacao: imprime formulario, coleta assinatura do recebedor, escaneia e anexa
   - Sistema registra ocorrencia SSW 22 - "Acareacao confirma entrega"
5. **Sistema**: Comprovante/Acareacao sao devolvidos automaticamente por e-mail ao cliente
6. **Matriz**: acompanha processo via relatorio diario (opcao 056) ou link Acareacao (opcao 101)
7. **Se necessario**: debita mercadoria ao parceiro via opcao 486

### Cadastro de Requisicao (Matriz)
1. Selecionar tipo de requisicao (10/20/30)
2. Informar prazo em dias corridos
3. Adicionar complemento (opcional)
4. Informar tipo de dado e arquivo (se cliente enviou planilha/arquivo)
5. Sistema registra e envia para unidade entregadora

### Debito de Mercadoria (Matriz)
1. Informar CTRC com DV
2. Sistema debita mercadoria da unidade responsavel via opcao 486
3. Util para unidades terceirizadas que nao entregaram

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 251 | Controle de Acareacao - Filial (atende requisicoes cadastradas pela opcao 250) |
| 486 | Debito de mercadorias ao parceiro (unidade terceirizada) |
| 056 | Relatorio diario "250-Controle de Acareacao" para acompanhamento |
| 101 | Consulta situacao via link "Acareacao" |

## Observacoes e Gotchas
- **Ocorrencias automaticas**:
  - SSW 21 = "Acareacao solicitada" (ao cadastrar requisicao tipo 20)
  - SSW 22 = "Acareacao confirma entrega" (ao anexar formulario escaneado)
- **E-mail automatico**: Comprovantes e Acareacoes sao devolvidos automaticamente por e-mail ao cliente
- **Subcontrato**: quando operacao e realizada por subcontratado, este deve usar Subcontrato/Redespacho de RECEPCAO (o de Expedicao e usado apenas para cobranca da coleta)
- **Formulario de acareacao**: disponibilizado pela opcao 251 (filial) para assinatura do recebedor e posterior escaneamento
- **Rastreamento**: ocorrencia e imagem escaneada ficam disponiveis no site ssw.inf.br
- **Relatorio gerencial**: opcao 056 disponibiliza diariamente relatorio "250-Controle de Acareacao"
- **Importacao de arquivo**: processo de importacao de arquivo enviado pelo cliente deve ser ajustado pela equipe SSW (nao e automatico)
- **Devolucao alternativa**: se mercadoria for encontrada, pode-se fazer devolucao em vez de acareacao (opcao 251)
