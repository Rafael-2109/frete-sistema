# Opcao 001 — Cadastro de Coletas

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 9 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Registra solicitacoes de coletas recebidas do cliente via telefone, internet, API ou EDI. A tela unica permite cadastrar dados completos da coleta incluindo remetente, destinatario, endereco, mercadoria e previsao de entrega.

## Quando Usar
- Cliente solicita coleta via telefone, site ou API
- Necessidade de programar coleta em embarcador
- Registro de coleta reversa (devolucao)
- Cadastro de coleta para parceiro subcontratado

## Pre-requisitos
- Cidade de coleta cadastrada com dias de atendimento (Opcao 402)
- Unidade de coleta definida (Opcao 388 para cliente ou Opcao 402 para cidade)
- Cliente remetente cadastrado
- Tabela de ocorrencias de coleta (Opcao 519) para coletas com parceiros SSW

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Situacao | Sim | Pre-cadastrada, Cadastrada, Comandada, Coletada ou Cancelada |
| CNPJ/CPF Remetente | Sim | Cliente que solicita a coleta |
| CNPJ/CPF Destinatario | Condicional | Obrigatorio para coleta reversa |
| End (logr, num, compl) | Sim | Endereco da coleta (nao necessariamente do remetente) |
| Cidade/UF | Sim | Cidade e estado da coleta |
| Data hora limite | Sim | Data e hora limite para coletar (primeira = Data hora limite inicial) |
| Coletar dia | Sim | Dia da coleta (sugerido conforme Opcao 402) |
| Unidade da coleta | Auto | Definida por Opcao 388 > Opcao 402 > unidade do usuario > unidade alternativa (Opcao 395) |
| Especie | Condicional | Obrigatorio se GR ativa (Opcao 903) e PGR possui regras (Opcao 390) |
| Previsao de entrega | Auto | Calculado com base no dia de atendimento do municipio (Opcao 402) |

## Situacoes da Coleta

| Situacao | Descricao |
|----------|-----------|
| Pre-cadastrada | Solicitado via internet, pendente de confirmacao (Opcao 042) |
| Cadastrada | Confirmada pelo cliente |
| Comandada | Passada para veiculo (Opcao 003 ou SSWMobile) |
| Coletada | Realizada (Opcao 003 ou SSWMobile) |
| Cancelada | Cancelada |

## Fluxo de Uso

### Cadastro Manual
1. Acessar Opcao 001
2. Informar dados do remetente
3. Definir endereco de coleta
4. Informar data/hora limite
5. Sistema sugere unidade de coleta
6. Gravar coleta com situacao "Cadastrada"

### Cadastro Automatico
- **Via API**: Cliente usa API sswCotacaoColeta
- **Via Site**: Cliente solicita via site da transportadora
- **Via EDI**: ssw2287 permite inclusao com numero do Pedido
- **Agendamento**: Opcao 042 programa coletas recorrentes

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 003 | Comandar coletas para veiculos |
| 042 | Programacao automatica de coletas |
| 004 | Gera CTRC a partir da coleta |
| 006 | Gera pre-CTRC a partir de volumes coletados (Opcao 166 ou SSWMobile) |
| 055 | Lembretes do cliente mostrados na tela |
| 080 | Instrucoes para entrega gravadas na NF |
| 103 | Consulta situacao das coletas |
| 137 | Documentos PDF anexados a coletas |
| 166 | Captura volumes coletados on-line |
| 304 | Alertas de areas de risco |
| 383 | Disparo de e-mails de rastreamento |
| 388 | Unidade e endereco de coleta por cliente |
| 395 | Unidade alternativa de coleta |
| 402 | Unidade e dias de atendimento da cidade |
| 404 | Hora limite de coleta por setor |
| 408 | Identificacao de parceiro para coleta subcontratada |
| 519 | Tabela de ocorrencias de coleta |
| 538 | Lembretes da unidade e cidade |
| SSWMobile | Atualizacao on-line de coletas pelo motorista |
| SSWCol | Gravacao off-line de mercadorias coletadas |

## Observacoes e Gotchas

### Unidade de Coleta
Ordem de prioridade para definir unidade:
1. Opcao 388 - Cadastrada no cliente
2. Opcao 402 - Cadastrada na cidade
3. Unidade do usuario que registra
4. Unidade alternativa (Opcao 395)

### Coleta Comandada Automaticamente
CTRC emitido em qualquer unidade muda coleta para "Coletada" quando:
- Mesma placa
- Mesmo remetente (raiz CNPJ)
- Mesma data de comandada
- Dia/hora limite anterior ao da emissao do CTRC
- Emissao NAO foi via EDI

### Coletas em Parceiros SSW
- Subcontratante cadastra coleta (Opcao 001)
- Sistema identifica parceiro (Opcao 408)
- Localiza unidade coletadora (Opcao 402 do parceiro)
- Grava coleta no dominio do parceiro
- Parceiro comanda via Opcao 003
- Ocorrencias gravadas em ambos dominios (tabela Opcao 519)

### Gerenciamento de Risco
- Se GR ativa (Opcao 903) e PGR possui regras para coleta (Opcao 390)
- Campo "Especie" torna-se obrigatorio

### Hora Limite
- Cadastrada por Setor (Opcao 404)
- Apos este horario, cadastro so e possivel para dia seguinte

### Gerar CTRC a Partir da Coleta
Botao habilitado quando:
- Mesma raiz CNPJ remetente
- Sem CTRC emitido
- Situacao: Comandada ou Coletada
- Data limite = hoje ou anterior

### Rastreamento
- Coletas rastreavveis em www.ssw.inf.br
- Cliente pode receber SMS informando realizacao (Opcao 903/SMS)
- Informacoes disponiveis ate 4 meses apos registro

### Mensagens e Alertas
- Lembretes por cliente (Opcao 055) mostrados na tela e impressos na Ordem de Coleta
- Alertas de areas de risco (Opcao 304) na coleta e entrega
- Lembretes de unidade/cidade (Opcao 538)
- Instrucoes para entrega (Opcao 080) para CNPJ+NF ainda nao emitido
- Mensagens padroes em e-mails (Opcao 180)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
