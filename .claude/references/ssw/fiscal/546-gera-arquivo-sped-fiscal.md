# Opcao 546 — Gera Arquivo SPED FISCAL

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Gera arquivo SPED Fiscal (Escrituracao Fiscal Digital) com base em XMLs do SEFAZ ou Contas a Pagar. Disponibiliza 2 formas de geracao de entradas: XML (Competencia) ou Contas a Pagar (Caixa). Saidas sempre usam XMLs de CT-es autorizados pelo SEFAZ.

## Quando Usar
- Envio mensal obrigatorio do SPED Fiscal ao SEFAZ
- Apuracao de ICMS (debito/credito ou credito presumido)
- Conferencia de creditos e debitos de ICMS antes do envio definitivo
- Substituicao de arquivo SPED enviado anteriormente

## Pre-requisitos
- Regime de tributacao configurado (Debito/Credito ou Credito Presumido - opcao 401)
- XMLs de CT-es emitidos e autorizados pelo SEFAZ
- Se usar Contas a Pagar: despesas lancadas (opcao 475) e NF-es emitidas (opcao 551)
- Se usar XML: XMLs de entradas importados automaticamente (opcao 582)
- CFOPs creditaveis cadastrados (opcao 432)
- Dados do contador responsavel
- Inscricao Estadual configurada

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Finalidade do arquivo | Sim | 0 = original, 1 = substituto |
| Referencia | Sim | X = entradas via XML (Competencia), P = via Contas a Pagar (Caixa) |
| Registros | Sim | E = apenas entradas (rapido para conferencia), T = todos |
| Objetivo | Sim | S = simulacao (sem atualizacao), E = envio (arquivo definitivo) |
| Usa contab Credito a Recuperar | Nao | S = compensa creditos Ativo com impostos Passivo (se Debito/Credito + Contab SSW) |
| Periodo de referencia | Sim | Periodo de autorizacao dos documentos fiscais |
| Periodo extemporaneo | Nao | Periodo de docs anteriores nao considerados em arquivos anteriores |
| Inscricao Estadual | Sim | IE da transportadora |
| **Arquivo definitivo** | | |
| Vencimento | Sim* | Vencimento da obrigacao ICMS a recolher (registro E116) |
| Valor credito periodo anterior | Nao | Creditos nao aproveitados no periodo anterior (registro E110) |
| Valor de outros creditos | Nao | Outros creditos a considerar |
| Valor credito acao cultural (SP) | Nao | Credito SP para acao cultural (art 20, anexo III RICMS/SP) |
| Valor credito acao esportiva (SP) | Nao | Credito SP para acao esportiva (art 20, anexo III RICMS/SP) |
| Valor estorno outros debitos | Nao | Estorno de debitos indevidos (ex: ICMS antecipado, devolucoes) |
| Dados do contabilista | Sim* | Dados do contador responsavel |

*Obrigatorio para arquivo definitivo (Objetivo = E)

## Fluxo de Uso

### Geracao de Arquivo Original
1. Acessar opcao 512 (SPED FISCAL)
2. Configurar parametros:
   - Finalidade: 0 (original)
   - Referencia: X (XML/Competencia) ou P (Contas Pagar/Caixa)
   - Registros: T (todos) ou E (apenas entradas para conferencia)
   - Objetivo: S (simulacao para conferir) ou E (envio definitivo)
3. Informar periodo de referencia (mes/ano)
4. Opcionalmente informar periodo extemporaneo
5. Informar Inscricao Estadual
6. Se arquivo definitivo (Objetivo = E):
   - Informar vencimento ICMS
   - Informar creditos periodo anterior se houver
   - Informar outros creditos/estornos se houver
   - Informar dados do contabilista
7. Executar geracao
8. Validar arquivo gerado
9. Enviar ao SEFAZ

### Geracao de Arquivo Substituto
1. Seguir passos acima, mas definir Finalidade: 1 (substituto)
2. Arquivo substitui o enviado anteriormente

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 401 | Configuracao regime tributacao (Debito/Credito ou Credito Presumido) |
| 475 | Contas a Pagar (origem de dados se Referencia = P) |
| 551 | Emissao NF-e (origem de dados se Referencia = P) |
| 582 | XMLs importados do SEFAZ (origem de dados se Referencia = X) |
| 432 | CFOPs creditaveis |
| 546 | Livro CIAP (credito depreciacao ativo imobilizado, 48 meses) |
| 704 | Cadastro ativo imobilizado (bens creditaveis) |
| 433 | ICMS Monofasico (valores para NF ajuste - RS) |
| 567 | Fechamento fiscal (mesmo efeito de gerar SPED mes completo) |

## Observacoes e Gotchas

### Formas de Geracao (Entradas)
- **XML (Competencia)**: usa XMLs buscados automaticamente no SEFAZ (opcao 582), NAO usa Contas a Pagar
- **Contas a Pagar (Caixa)**: usa lancamentos do Contas a Pagar (opcao 475) e NF-es emitidas (opcao 551)
- **Saidas**: SEMPRE usam apenas XMLs de CT-es emitidos e autorizados pelo SEFAZ (independente da escolha)

### Debitos ICMS (Saidas)
- **CTRCs**: considera situacao tributacao normal
- **Subcontratos**: NAO tem debito ICMS (ICMS ja destacado integralmente no CT-e do subcontratante)
- **DIFAL** (CONVENIO ICMS 93/2015): partilha entre estados enviada no SPED
  - Origem: recolhido junto com ICMS normal
  - Destino: pode recolher via GNRE (por operacao) ou Inscricao Auxiliar (total do periodo)
- **DIFAL uso/consumo**: ao adquirir de outra UF, recolher diferenca de aliquota (cadastro opcao 704)

### Creditos ICMS (Entradas)
- **Regime**: creditos so considerados em apuracao Debito/Credito (opcao 401)
- **CT-es a pagar**: todos modelo 57 (transportadoras cobrando)
- **NF-es**: apenas modelo 55 com NCMs e CFOPs cadastrados
- **CFOPs creditaveis**: devem estar cadastrados (opcao 432)
- **Ativo imobilizado**: credito via livro CIAP (opcao 546), depreciacao 48 meses (XML ou Contas Pagar)
- **Credito Presumido**: normalmente 20% (varia por UF), documentos relacionados mas nao influenciam apuracao

### ICMS Monofasico Combustiveis
- **Reconhecimento**: CST = 61, incluido automaticamente na despesa (opcao 475) via XML (desde 07/11/2023)
- **Credito**: ocorre para optantes Debito/Credito (opcao 401)
- **RS**: emitir NF ajuste para tomada de credito (opcao 551), valores via opcao 433 link ICMS Monofasico
- **SC**: NAO escritura credito no documento, apropriacao via ajuste registro D197 (evita inconsistencia em cruzamento SEF/SC)

### Documentos Nao Enviados
- Modelos 07, 09, 10, 11, 26, 27 emitidos a partir de 01/01/2019 NAO sao enviados (Manual SPED pag 173)

### Fechamento Fiscal
- **Automatico**: geracao de SPED mes completo faz fechamento fiscal do mes (mesmo efeito opcao 567)

### Simulacao vs Envio
- **Simulacao (S)**: arquivo gerado SEM atualizacao fiscal, contabil e controles internos (util para conferencias)
- **Envio (E)**: arquivo DEFINITIVO para SEFAZ, com atualizacoes completas

### Registros Entrada vs Todos
- **Apenas Entradas (E)**: reduz tempo de processamento drasticamente, util para conferencias
- **Todos (T)**: geracao completa (entradas + saidas)

### Credito a Recuperar
- Campo "Usa contab Credito a Recuperar = S": compensa creditos Ativo com impostos Passivo
- Valido APENAS para: Debito/Credito (opcao 401) + Contabilidade SSW

### Periodo Extemporaneo
- Documentos fiscais anteriores ao periodo de referencia nao considerados em arquivos anteriores
- Creditos nao aproveitados anteriormente
- Complementar ao campo "Valor credito periodo anterior"

### Estornos e Creditos Especiais
- **Estorno outros debitos**: ICMS recolhido antecipadamente, ICMS em devolucoes (registro E110)
- **Creditos SP**: acoes culturais/esportivas (art 20, anexo III RICMS/SP)
