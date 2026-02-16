# Opcao 308 — CTRCs com Fale Conosco Preenchido

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Localiza CTRCs cujos clientes preencheram o formulario "Fale Conosco" no site de rastreamento www.ssw.inf.br, permitindo a transportadora responder as solicitacoes diretamente no sistema, com respostas disponibilizadas automaticamente no site para visualizacao do cliente.

## Quando Usar
- Atender solicitacoes de clientes enviadas via site de rastreamento
- Centralizar respostas a clientes em um unico local
- Monitorar CTRCs com pendencias de comunicacao com cliente
- Gerar relatorios de demandas de clientes via Fale Conosco

## Pre-requisitos
- Site de rastreamento www.ssw.inf.br ativo
- Cliente preencheu formulario Fale Conosco para um CTRC especifico

## Campos / Interface

### Tela Inicial (Filtros)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cadastrado pelo cliente no periodo | Sim | Data de preenchimento do Fale Conosco no site de rastreamento |
| Selecionar | Sim | N=CTRCs nao entregues, T=todos |
| Mostrar em | Sim | V=video (tela), R=relatorio, E=Excel com ocorrencias e instrucoes, X=Excel apenas com ocorrencias |

### Tela CTRC (Resposta)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Instrucao | Sim | Resposta ao cliente. Campo DETALHAR pode ser usado para informacoes adicionais |

## Fluxo de Uso
1. Cliente rastreia compra no site www.ssw.inf.br e preenche formulario Fale Conosco
2. Transportadora acessa opcao 308 e filtra por periodo/status de entrega
3. Tabela exibe CTRCs com Fale Conosco pendente de resposta
4. Clicar na linha do CTRC desejado para abrir Tela CTRC
5. Informar resposta no campo "Instrucao" (com detalhes se necessario)
6. Confirmar resposta
7. Resposta e disponibilizada automaticamente no site de rastreamento para visualizacao do cliente
8. CTRC sai da tabela de pendentes (ja respondido)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 101 | Tela de CTRC — exibe dados completos do Fale Conosco e instrucoes/respostas (sem sigilo) |

## Observacoes e Gotchas
- **Sigilo de dados**: no site de rastreamento, numeros sao ocultados para preservar sigilo. Na opcao 101, TODOS os dados sao mostrados sem restricao
- **Respostas via opcao 101**: instrucoes/respostas dadas no CTRC (opcao 101) sao automaticamente disponibilizadas no site de rastreamento
- **CTRCs respondidos saem da tabela**: apos confirmar resposta, CTRC nao aparece mais na lista de pendentes
- **Campo DETALHAR**: permite adicionar informacoes complementares a resposta (alem do campo Instrucao)
- **Filtro N vs. T**: "N" (nao entregues) e util para focar em CTRCs ainda em transito; "T" (todos) inclui tambem CTRCs ja entregues
- **Formatos de saida**: 4 opcoes de visualizacao (video, relatorio, Excel completo, Excel resumido)
- **Site publico**: www.ssw.inf.br e site de rastreamento publico onde clientes acompanham status de entregas
- **Comunicacao bidirecional**: cliente envia mensagem via site → transportadora responde via opcao 308 → cliente visualiza resposta no site
