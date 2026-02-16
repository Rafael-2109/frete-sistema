# Opcao 381 — Cadastro de Clientes - Operacao

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Define regras operacionais especificas por cliente para envio de pre-CTRCs ao SEFAZ, impressao de DACTEs para comprovacao de entrega, e bloqueio operacional. Regras sao validas quando o cliente e o PAGADOR do frete.

## Quando Usar
- Configurar regras especificas de envio ao SEFAZ por cliente (pesagem, cubagem, romaneio, etc.)
- Definir se cliente exige DACTE em papel ou aceita comprovacao digital (operacao sem papel)
- Bloquear cliente operacionalmente (remetente, expedidor, destinatario, recebedor)
- Configurar geracao automatica de pre-CTRC a partir da coleta
- Exigir autorizacao previa para CTRC Complementar de Reembolso

## Pre-requisitos
- Transportadora deve ativar funcionalidade correspondente na opcao 903/Envio de pre-CTRC ao SEFAZ (para que cliente possa informar "N")
- Para geracao automatica de pre-CTRC: transportadora configurada na opcao 903/Operacao

## Campos / Interface

### Emissao do Pre-CTRC
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Automaticamente gerar pre-CTRC a partir da coleta | Sim | S=coleta com situacao "coletada" gera pre-CTRC automaticamente. Transportadora deve estar configurada na opcao 903/Operacao |
| Agrupamento manual (Pre-CTRC em lote opc 006) | Sim | S=agrupamento de NFs manual na opcao 006, N=agrupamento automatico |

### Envia Pre-CTRC ao SEFAZ
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Sem pesagem | Sim | N=pre-CTRC sem nova pesagem NAO e enviado ao SEFAZ. Pesagem via: opcao 084 (pre-CTRCs), 184 (volumes), SSWBalanca ou cubadoras (Toledo, Compudech) |
| Sem cubagem | Sim | N=pre-CTRC sem cubagem (m3) NAO e enviado ao SEFAZ. Cubagem via: opcao 004, 006, 084, 184 ou cubadora |
| Sem recubagem | Sim | N=pre-CTRC sem segunda cubagem (opcao 084 e cubadora) NAO e enviado ao SEFAZ |
| Sem Romaneio/Packing List | Sim | N=apenas pre-CTRCs com volumes em Romaneio/Packing List (opcao 006/R) sao enviados ao SEFAZ |
| Sem captura pelo SSWBAR | Sim | N=pre-CTRC sem pelo menos 1 volume capturado pelo SSWBAR (descarga coleta ou carregamento manifesto) NAO e enviado. Util para clientes que enviam NF-e via EDI mas esquecem mercadoria |
| Sem conferencia pelo conferente | Sim | N=pre-CTRC so enviado ao SEFAZ se mercadoria conferida (opcao 284). Cliente deve estar configurado |
| Complementar de Reembolso sem autorizacao | Sim | N=pre-CTRC Complementar de Reembolso (opcao 222) NAO enviado ao SEFAZ sem autorizacao previa por e-mail ou opcao 201 |

### DACTE/Comprovante de Entregas
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Imprime DACTE | Sim | S=cliente exige comprovacao de entrega (DACTE) em papel. Tem efeito se transportadora ativou na opcao 903/Operacao |
| Operacao FOB imprime 2 vias | Sim | S=caso impressao DACTE=S, operacao FOB tera via adicional de DACTE |
| Observacao (campo) | Nao | Sugerida na geracao do CTRC (opcoes 004, 005, 006) no campo "Instrucoes entrega". Impressa na DACTE, Romaneio de Entregas e mostrada no SSWMobile |

### Bloqueio Operacional
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Bloqueio operacional | Sim | S=cliente bloqueado como remetente, expedidor, destinatario e/ou recebedor. Impede participacao em cotacoes (002), coletas (001) e geracao de pre-CTRCs (004, 005, 006) |

## Fluxo de Uso

### Configuracao de Cliente (Operacao sem Papel)
1. Ativar funcionalidade geral na opcao 903 (transportadora)
2. Cadastrar cliente com "Imprime DACTE = N" (operacao sem papel)
3. Cliente recebera comprovacao digital de entrega
4. Configurar campo Observacao se necessario (instrucoes especificas de entrega)

### Configuracao de Cliente (Pesagem/Cubagem Obrigatoria)
1. Ativar funcionalidade geral na opcao 903 (transportadora)
2. Configurar cliente com "Sem pesagem = N" e/ou "Sem cubagem = N"
3. Pre-CTRCs sem pesagem/cubagem ficam retidos na fila de "CTRCs nao enviados" (opcao 007)
4. Realizar pesagem/cubagem via opcoes 084, 184, SSWBalanca ou cubadoras
5. Pre-CTRC e enviado automaticamente ao SEFAZ apos pesagem/cubagem

### Configuracao de Cliente (Reembolso com Autorizacao)
1. Configurar cliente com "Complementar de Reembolso sem autorizacao = N"
2. Ao gerar CTRC Complementar de Reembolso (opcao 222), sistema envia e-mail automatico para cliente
3. Cliente autoriza via link no e-mail OU via opcao 201 (autorizacao manual)
4. Apos autorizacao, pre-CTRC e enviado ao SEFAZ

### Bloqueio Operacional
1. Configurar cliente com "Bloqueio operacional = S"
2. Cliente fica impedido de participar de:
   - Cotacoes (opcao 002)
   - Coletas (opcao 001)
   - Geracao de pre-CTRCs (opcoes 004, 005, 006)
3. Para desbloquear: alterar campo para "N"

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 903/Envio de pre-CTRC ao SEFAZ | Ativacao geral das funcionalidades (pre-requisito para usar "N" no cliente) |
| 903/Operacao | Ativacao geral para geracao automatica de pre-CTRC a partir da coleta |
| 007 | Fila de "CTRCs nao enviados" — pre-CTRCs aguardando condicoes para envio ao SEFAZ |
| 006 | Geracao de pre-CTRCs em lote — agrupamento manual/automatico conforme configuracao |
| 084 | Pesagem de pre-CTRCs |
| 184 | Pesagem de volumes |
| 284 | Conferencia de mercadoria pelo conferente |
| 222 | CTRC Complementar de Reembolso — requer autorizacao previa se configurado |
| 201 | Autorizacao manual de CTRC Complementar de Reembolso |
| 004 | Geracao manual de CTRC — usa campo Observacao |
| 005 | Geracao manual de CTRC — usa campo Observacao |
| 001 | Coleta — bloqueada se cliente bloqueado operacionalmente |
| 002 | Cotacao — bloqueada se cliente bloqueado operacionalmente |
| 427 | Tabela Generica (controle configurado na opcao 903, nao na 381) |

## Observacoes e Gotchas
- **Regras validas quando cliente = PAGADOR**: regras definidas nesta opcao sao validas apenas quando o cliente e o pagador do frete
- **Configuracao geral obrigatoria**: para ativar funcionalidade no cliente (informar "N"), transportadora deve ativar previamente na opcao 903
- **Pre-CTRC nao tem valor fiscal**: pode ser alterado/excluido sem controle. Formato: XXX 999999-8 (XXX=sigla unidade/tipo documento, 999999=sequencial, 8=DV)
- **Pesagens/cubagens parciais**: volumes faltantes sao calculados usando media dos ja pesados/cubados
- **CTRCs nao enviados**: alteracoes nesta opcao 381 sao consideradas por pre-CTRCs na fila de "CTRCs nao enviados" (opcao 007)
- **Operacao sem papel**: deve iniciar todos os clientes com "Imprime DACTE = S" e gradativamente mudar para "N" (transicao controlada)
- **Tabela Generica**: controle configurado APENAS na transportadora (opcao 903), NAO no cliente
- **SSWBAR**: programa de captura de volumes com leitor de codigo de barras (descarga de coleta ou carregamento de manifesto)
- **SSWMobile**: aplicativo mobile que exibe observacoes de entrega para motorista/entregador
- **Observacao vs. Instrucoes entrega**: campo Observacao e sugerido como "Instrucoes entrega" na geracao do CTRC
