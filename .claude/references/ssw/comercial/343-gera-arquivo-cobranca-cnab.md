# Opcao 343 — Gera Arquivo de Cobranca CNAB

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (fonte: opcao 443)
> **Atualizado em**: 2026-02-14

## Funcao
Gera arquivo de cobranca bancaria no formato CNAB para faturas emitidas com cobranca bancaria, enviando ao banco para registro de boletos. Cobrancas on-line via API estao sendo disponibilizadas gradativamente (remessa e retorno automaticos sem intervencao humana).

## Quando Usar
- Enviar faturas com cobranca bancaria ao banco para registro de boletos
- Reenviar instrucoes bancarias de alteracao de cobranca
- Retransmitir arquivo previamente gerado
- Cancelar arquivo de remessa nao enviado ao banco
- Listar faturas de cobranca bancaria ainda nao enviadas ao banco

## Pre-requisitos
- Faturas geradas com cobranca bancaria (via opcao 436 ou 437)
- Conta bancaria cadastrada e homologada pelo banco (opcao 904)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Gerar arquivo para BANCO/AG/CCOR (DV opc) | Sim | Conta devidamente cadastrada e homologada pelo banco (opcao 904) |
| Faturas geradas ate | Sim | Data limite de faturas geradas pela opcao 436 e 437 a incluir no arquivo |
| Filiais dos clientes faturados | Nao | Sigla da unidade de cobranca do cliente (opcao 384). Opcional |
| Faixa de faturas | Nao | Numeros da primeira e ultima fatura a incluir (nao filtra instrucoes) |
| Gerar arquivo com | Sim | R=faturas e instrucoes nao enviadas, I=apenas instrucoes bancarias de alteracao |
| Listar faturas nao enviadas banco | Nao | Botao que relaciona faturas de cobranca bancaria ainda sem arquivo de remessa |
| Arquivo para retransmitir ao micro | Nao | Regeracao de arquivo previamente gerado (numero do arquivo via opcao 457) |
| Ultima remessa | Nao | Link habilitado apos escolher banco/ag/ccor no topo da tela |
| Cancela arquivo de remessa | Nao | Cancela arquivo e libera faturas (evita envio de boletos ao cliente) |

## Fluxo de Uso

### Remessa Normal (Primeira Vez)
1. Selecionar conta bancaria (banco/ag/ccor)
2. Informar data limite de faturas geradas
3. Opcionalmente filtrar por unidade de cobranca ou faixa de faturas
4. Selecionar tipo de arquivo: R=remessa completa (faturas+instrucoes)
5. Gerar arquivo CNAB
6. Enviar arquivo ao banco UMA UNICA VEZ no final do dia (alguns bancos rejeitam arquivos fora de sequencia)
7. Faturas sao enviadas ao cliente a partir da madrugada do dia seguinte

### Remessa de Instrucoes (Alteracoes)
1. Selecionar conta bancaria
2. Selecionar tipo de arquivo: I=apenas instrucoes bancarias
3. Gerar arquivo CNAB com instrucoes de alteracao
4. Enviar arquivo ao banco

### Retransmitir Arquivo
1. Descobrir numero do arquivo nas ocorrencias da fatura (opcao 457)
2. Informar numero no campo "Arquivo para retransmitir ao micro"
3. Arquivo e regerado
4. Renomear arquivo conforme exigencia do banco (vide secao Observacoes)
5. Enviar ao banco

### Cancelar Arquivo
1. Informar numero do arquivo de remessa
2. Executar cancelamento
3. Faturas sao liberadas e boletos NAO sao enviados ao cliente

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 436 | Faturamento automatico — gera faturas com cobranca em carteira e bancaria |
| 437 | Faturamento manual — gera faturas com cobranca em carteira e bancaria |
| 444 | Importacao de arquivo de retorno bancario (faturas liquidadas) |
| 904 | Cadastro e homologacao de conta bancaria |
| 384 | Unidade de cobranca do cliente (filtro opcional) |
| 457 | Ocorrencias da fatura (consultar numero do arquivo de remessa) |
| 343 | Cobranca on-line via API (remessa/retorno automaticos) |

## Observacoes e Gotchas
- **IMPORTANTE: Arquivo tipo R deve ser enviado UMA UNICA VEZ no final do dia** — alguns bancos rejeitam arquivos enviados com numeracao fora da sequencia
- **Instrucoes sempre enviadas**: ao gerar arquivo com faixa de faturas, novas instrucoes disponiveis sao SEMPRE enviadas (nao sao filtradas pela faixa)
- **Cobranca on-line via API**: gradativamente sendo disponibilizada (remessa e retorno automaticos sem intervencao humana via opcao 343)
- **Envio ao cliente**: faturas sao enviadas ao cliente a partir das primeiras horas do dia seguinte (madrugada)
- **Arquivo de retorno**: faturas liquidadas pelo banco sao informadas via arquivo que deve ser importado pela opcao 444

### Renomeacao de Arquivos Retransmitidos (Por Banco)
- **Sicredi**: verificar documentacao especifica
- **Bradesco**: formato CBDDMMXX.REM
  - DD=dia, MM=mes, XX=variavel alfanumerica de diferenciacao (01, AB, A1)
  - REM=fixo (para producao), TST (para teste)
- **Itau**: arquivo gerado com 10 digitos (3 do banco + 7 do numero sequencial)
  - Necessario reduzir para 8 digitos: retirar 2 zeros a esquerda do numero

### Cancelamento de Arquivo
- **Quando cancelar**: arquivos que se desistiu de enviar ao banco devem ser cancelados para que boletos NAO sejam enviados ao cliente
- **Efeito**: libera faturas do arquivo de remessa, permitindo inclusao em nova remessa
