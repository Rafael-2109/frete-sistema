# Opção 100 — Geração de E-mails para Clientes

> **Módulo**: Comercial
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Gera e envia e-mails automaticamente para clientes pessoa jurídica em três modalidades: mensagens de cobrança para devedores, cartões de aniversário para contatos cadastrados e mensagens diversas customizadas.

## Quando Usar
- Enviar avisos de atraso de liquidação de faturas automaticamente
- Parabenizar contatos de clientes em seus aniversários
- Disparar campanhas ou mensagens informativas para base de clientes segmentada

## Pré-requisitos
- **Opção 483**: Cadastro de clientes com classificação (especiais/comuns)
- **Opção 387**: Cadastro de relacionamentos (contatos) com data de aniversário e e-mails
- **Opção 491, 903 ou 401**: Configuração de remetente/assinatura dos e-mails
- **Opção 384**: E-mails de cobrança (para mensagens diversas)
- **Opção 383**: E-mails de ocorrências (para mensagens diversas)
- **Opção 415**: Cadastro de vendedores (filtro opcional em mensagens diversas)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Tipo de e-mail | Sim | Devedores, Aniversariantes ou Mensagens Diversas |

### Tela Devedores
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Envio automático | Sim | **A** (ativado, disparo automático nas primeiras segundas-feiras) ou **D** (desativado) |
| Faturas vencidas há mais de | Sim | Período de verificação em dias (padrão 120 dias) |
| Clientes com classificação | Sim | **E** (especiais), **C** (comuns) ou **A** (ambos) |
| Mensagem | Sim | Texto de cobrança (aceita HTML). Faturas atrasadas são listadas automaticamente abaixo |

### Tela Aniversariantes
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Envio automático | Sim | **A** (ativado, disparo diário na madrugada) ou **D** (desativado) |
| Clientes cadastrados a partir de | Não | Formato DDMMAA |
| Com movimento nos últimos | Não | Período em dias |
| Mensagem | Sim | Texto do cartão. Use **#** para posicionar imagem ou **#_** para redimensioná-la a 700px |
| Imagem JPG | Não | Imagem local (deve lembrar a transportadora) |

### Tela Mensagens Diversas
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Assunto | Sim | Linha de assunto do e-mail |
| Selecionar endereços de e-mails de | Sim | **R** (relacionamento/opção 387), **O** (ocorrências/opção 383), **C** (cobrança/opção 384), **T** (todos) |
| Clientes com classificação | Sim | **E** (especiais), **C** (comuns) ou **A** (ambos) |
| Clientes com movimento no período | Não | Filtro por data de movimento |
| Clientes sem movimento no período | Não | Filtro por ausência de movimento |
| Clientes cadastrados a partir de | Não | Filtro por data de cadastro |
| Selecionar unidades | Não | Unidades responsáveis pelos clientes (opção 483) |
| Manifesto (com DV) | Não | Enviar apenas para remetente, destinatários e pagadores de CTRCs do Manifesto |
| Vendedor | Não | Filtro por vendedor do cliente (opção 415) |
| Enviado | Sim | **N** (agendado para próxima madrugada) ou **S** (já enviado). Trocar S→N para reenviar |
| Mensagem | Sim | Texto customizado (aceita HTML) |
| Imagem JPG | Não | Posicionar com **#**. Máximo 700px (redimensionamento automático) |

## Fluxo de Uso

### Devedores
1. Acessar opção 100 → selecionar "Para devedores"
2. Configurar período de vencimento (ex: 120 dias) e classificação de clientes
3. Escrever mensagem de cobrança (HTML permitido)
4. Ativar envio automático (A)
5. Salvar → disparo ocorrerá automaticamente nas primeiras segundas-feiras de cada mês após meia-noite

### Aniversariantes
1. Acessar opção 100 → selecionar "Para aniversariantes"
2. Definir filtros (cadastro a partir de, movimento recente)
3. Escrever mensagem e fazer upload de imagem JPG
4. Marcar posição da imagem com **#** ou **#_**
5. Ativar envio automático (A)
6. Salvar → disparo ocorrerá diariamente para aniversariantes do dia após meia-noite

### Mensagens Diversas
1. Acessar opção 100 → selecionar "Para envio de mensagens diversas"
2. Definir assunto e selecionar fonte de e-mails (relacionamento/ocorrências/cobrança/todos)
3. Aplicar filtros (classificação, movimento, unidades, vendedor, manifesto)
4. Escrever mensagem e opcionalmente incluir imagem JPG com **#**
5. Confirmar campo "Enviado" como **N**
6. Salvar → disparo ocorrerá **uma única vez** na próxima madrugada

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 155 | Relatório de e-mails enviados automaticamente (rastreamento) |
| 387 | Fonte de contatos para aniversários e e-mails de relacionamento |
| 383 | Fonte de e-mails de ocorrências |
| 384 | Fonte de e-mails de cobrança |
| 483 | Cadastro de clientes (classificação, unidades, vendedor) |
| 491 | Configuração de remetente/assinatura |
| 903 | Configuração alternativa de remetente (Site, e-mail e telefones) |
| 401 | Configuração alternativa de remetente |
| 415 | Cadastro de vendedores (filtro) |

## Observações e Gotchas
- **CUIDADO**: Parametrização incorreta pode disparar milhares de e-mails indesejados
- **Apenas pessoa jurídica**: Disparo só ocorre para clientes PJ
- **Mensagens diversas**: Apenas uma mensagem é disparada por dia (consumo alto de processamento)
- **Agendamento**: Todas as modalidades disparam após meia-noite
- **HTML**: Tags e scripts HTML são permitidos nas mensagens
- **Imagens**: Usar **#** para posicionar imagem ou **#_** para redimensionar a 700px de largura
- **Redimensionamento automático**: SSW ajusta imagens maiores que 700px automaticamente
- **Reenvio**: Para reenviar mensagem diversa, trocar campo "Enviado" de **S** para **N**
- **Visualização**: Botão "Visualizar e-mail" permite pré-visualizar antes do disparo
- **Múltiplas mensagens**: É possível configurar várias mensagens diversas de uma vez, mas apenas uma por dia será disparada

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
