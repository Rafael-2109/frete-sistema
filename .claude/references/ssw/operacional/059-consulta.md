# Opcao 059 — Consulta (Observacao CTRC/Boleto por Cliente)

> **Modulo**: Cadastro — Clientes
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra observacoes a serem impressas nos CTRCs e boletos de cobranca por cliente. Permite combinar mensagens para remetente+destinatario especificos.

## Quando Usar
- Cadastrar observacoes padrao em CTRCs do cliente
- Configurar mensagens em boletos de cobranca
- Definir instrucoes impressas em DACTE

## Pre-requisitos
- Cliente cadastrado

## Campos / Interface

| Campo | Descricao |
|-------|-----------|
| CNPJ/CPF | Cliente a receber observacao |
| Raiz | S = aplica a todos CNPJs mesma raiz (8 primeiros digitos) |

### CTRC
| Campo | Descricao |
|-------|-----------|
| Mensagem | Texto da observacao do CTRC |
| Remetente | X = mensagem quando cliente e remetente |
| Remetente + destinatario | Link combina mensagem remetente+destinatario |
| Destinatario | X = mensagem quando cliente e destinatario |
| Pagador | X = mensagem quando cliente e pagador |

### Boleto
| Campo | Descricao |
|-------|-----------|
| Mensagem | Texto observacao boleto (quando cliente e pagador) |

## Fluxo de Uso
1. Acessar Opcao 059
2. Informar CNPJ/CPF cliente
3. Marcar "Raiz" se aplicar a todos CNPJs mesma raiz
4. Cadastrar mensagem CTRC e marcar situacoes (remetente/dest/pagador)
5. Cadastrar mensagem Boleto (se aplicavel)
6. Gravar

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004 | Sugerido em Instrucoes entrega |
| 005 | Sugerido em Instrucoes entrega |
| 006 | Sugerido em Instrucoes entrega |
| 055 | Lembretes do cliente |
| 059 | Esta opcao |
| 080 | Instrucoes entrega gravadas na NF |
| 101 | Instrucao resgate mercadoria |
| 381 | Deixar DACTE em destinatario FOB |
| 483 | Pegar canhoto NF assinado |
| SSWMobile | Mostra observacao |

## Observacoes e Gotchas

### Emissao do CTRC
Observacao gravada por Opcao 059 e sugerida na geracao CTRC (Opcao 004, 005, 006) no campo "Instrucoes entrega". E impressa na DACTE e Romaneio de Entregas e mostrada no SSWMobile.

### Relacao de Clientes
Link "Relacao de clientes" relaciona todos clientes e suas observacoes cadastradas.

### Tabela
Mensagens gravadas em tabela, permitindo alteracao e exclusao.

### Raiz CNPJ
Com "S" em Raiz, observacao aplicada a todos CNPJs que possuem mesma raiz (8 primeiros digitos).

### Combinacao Remetente + Destinatario
Link "Remetente + destinatario" permite combinar mensagens para pares especificos remetente-destinatario.

### Opcoes Relacionadas
- Opcao 101: Instrucao resgate mercadoria (codigo SSW 88)
- Opcao 055: Lembretes do cliente
- Opcao 059: Observacoes impressas em CTRCs/boletos
- Opcao 080: Instrucoes entrega gravadas na NF
- Opcao 381: Deixar DACTE em destinatario FOB
- Opcao 483: Pegar canhoto NF assinado
