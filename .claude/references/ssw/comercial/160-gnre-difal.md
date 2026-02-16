# Opcao 160 — GNRE DIFAL

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (referencia na opcao 471)
> **Atualizado em**: 2026-02-14

## Funcao
Gera e processa GNRE (Guia Nacional de Recolhimento de Tributos Estaduais) para recolhimento do ICMS Diferencial de Aliquota (DIFAL) em operacoes interestaduais destinadas a consumidor final, conforme Emenda Constitucional 87/2015. O DIFAL e recolhido via GNRE em cada operacao e pode ser apurado mensalmente atraves do Livro Fiscal de ICMS Diferencial de Aliquota (opcao 471).

## Quando Usar
- Recolher ICMS DIFAL em operacao interestadual para consumidor final
- Gerar GNRE de operacao com diferencial de aliquota entre UF origem e UF destino
- Operacoes onde pagador nao e contribuinte da UF destino
- Operacoes realizadas por transportadora fora do Simples Nacional

## Pre-requisitos
- CTRCs emitidos em operacao interestadual para consumidor final
- Pagador do frete NAO ser contribuinte da UF destino (caso contrario, DIFAL nao se aplica)
- Transportadora NAO estar no Simples Nacional (conforme liminar STF de 26/02/2016)
- Inscricao Estadual da unidade emissora dos CTRCs

## Campos / Interface

### Geracao de GNRE (Opcao 160)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC / Operacao | Sim | Identificacao da operacao que exige recolhimento de DIFAL |
| UF Destino | Sim | Estado destino da operacao (determina aliquota DIFAL) |
| Valor base de calculo | Sim | Base de calculo para o DIFAL |
| Aliquota DIFAL | Sim | Diferenca entre aliquota total da operacao e aliquota interestadual |

### Livro Fiscal ICMS DIFAL (Opcao 471)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Periodo de emissao | Sim | Periodo de emissao dos CTRCs |
| Inscricao Estadual | Sim | IE da unidade emissora dos CTRCs |
| Pagina inicial do Livro de Saidas | Sim | Pagina inicial (>= 2, pagina 1 e reservada para abertura do Livro) |

### Colunas do Relatorio (Opcao 471)
| Coluna | Descricao |
|--------|-----------|
| ALIQ OPER (%) | Aliquota total da operacao |
| ALIQ. INTER (%) | Aliquota interestadual |
| ALIQ. DIFAL (%) | Diferenca de aliquota (ALIQ OPER - ALIQ INTER) |

## Fluxo de Uso

### Recolhimento Individual por Operacao
1. Emitir CTRC de operacao interestadual para consumidor final
2. Verificar se pagador NAO e contribuinte da UF destino
3. Acessar opcao 160
4. Gerar GNRE para recolhimento do DIFAL
5. Efetuar pagamento da GNRE

### Apuracao Mensal (Livro Fiscal)
1. Acessar opcao 471 (Livro Fiscal ICMS DIFAL)
2. Informar periodo de emissao dos CTRCs
3. Selecionar IE da unidade emissora
4. Definir pagina inicial do Livro de Saidas (>= 2)
5. Gerar relatorio subtotalizado por UF destino
6. Conferir DIFAL devidos/recolhidos no periodo

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 471 | Livro Fiscal ICMS Diferencial de Aliquota (apuracao mensal dos DIFAL gerados pela opcao 160) |
| CTRCs | Operacoes que geram obrigacao de recolhimento de DIFAL |

## Observacoes e Gotchas
- **DIFAL nao se aplica quando pagador e contribuinte da UF destino**: Se o pagador do frete (destinatario ou terceiro) for contribuinte da UF destino, o DIFAL nao e devido
- **Empresas do Simples Nacional estao isentas**: Conforme liminar do STF de 26/02/2016, empresas optantes do Simples Nacional nao recolhem DIFAL
- **GNRE por operacao**: Cada operacao sujeita a DIFAL gera uma GNRE individual na opcao 160
- **Livro por IE emissor**: O Livro Fiscal (opcao 471) e emitido por IE da unidade emissora e subtotalizado por UF destino
- **Pagina inicial >= 2**: No Livro Fiscal, a pagina inicial deve ser maior ou igual a 2 (pagina 1 e reservada para termo de abertura)
- **Emenda Constitucional 87/2015**: Base legal para o recolhimento do DIFAL em operacoes interestaduais para consumidor final
- **Aliquota DIFAL e a diferenca**: DIFAL = Aliquota total da operacao (UF destino) - Aliquota interestadual
- **Consumidor final**: DIFAL aplica-se apenas a operacoes destinadas a consumidor final (nao contribuinte ou contribuinte de outra UF)
