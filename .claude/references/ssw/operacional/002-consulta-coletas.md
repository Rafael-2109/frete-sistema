# Opcao 002 — Cotacao de Fretes

> **Modulo**: Operacional — Cotacao
> **Paginas de ajuda**: 5 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Realiza cotacoes de fretes com simulacao de valores, descontos e propostas. Cotacoes contratadas sao automaticamente utilizadas na emissao de CTRCs, aplicando o mesmo percentual de desconto negociado.

## Quando Usar
- Cliente solicita cotacao de frete
- Necessidade de simular valores antes de fechar negociacao
- Propor descontos ou acrescimos sobre tabela padrao
- Registrar proposta comercial com validade

## Pre-requisitos
- Cliente pagador cadastrado
- Cidades origem e destino atendidas
- Tabelas de frete cadastradas
- Limites de cotacao configurados (Opcao 469 ou Opcao 369)

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ pagador | Sim | Cliente que pagara o frete |
| Mercadoria | Nao | Tipo de mercadoria (se informado, CTRC deve usar o mesmo) |
| Frete | Sim | CIF ou FOB (permite terceiro pagador) |
| Coletar | Sim | S = frete inclui coleta |
| Entregar | Sim | N = mercadoria nao sera entregue (retira TDE/TDA/TRT/TAR) |
| CEP origem/destino | Sim | Origem e destino do frete |
| CNPJ remet/destin | Condicional | CNPJ remetente obrigatorio para FOB Dirigido |
| Peso (kg) | Sim | Peso da mercadoria |
| Valor mercadoria | Sim | Valor da mercadoria para calculo |
| Cubagem (m3) | Nao | Pode ser cadastrado no pagador (Opcao 423) |
| Frete subcontratante | Condicional | Necessario para cotar subcontratacao |
| Outros | Nao | Valor adicional (descarga, icamento, balsa, etc.) |

## Abas / Sub-telas

### Tela Inicial
- Incluir nova cotacao
- Listar cotacoes cadastradas (por unidade de inclusao, origem, usuario, CNPJ pagador ou periodo)

### Tela de Cotacao
- **Proposta Inicial**: Frete resultante das condicoes padrao (mesmo da emissao de CTRC)
- **Proposta Atual**: Frete obtido informando desconto/acrescimo sobre proposta atual
- **Limites**: Parametros da rota que cotacao deve obedecer
- **Parcelas**: Detalhamento das parcelas de frete

## Fluxo de Uso

### Cotacao Simples
1. Acessar Opcao 002
2. Informar CNPJ pagador
3. Preencher dados da operacao (origem, destino, peso, valor)
4. Clicar em "Simular" para obter Proposta Inicial
5. Informar desconto ou acrescimo desejado
6. Clicar em "Contratar" (valor variavel) ou "Contratar com valor fixo"

### Consulta de Cotacoes
1. Selecionar filtro (unidade, usuario, cliente, periodo)
2. Sistema lista cotacoes com opcao de duplicar

## Limites de Cotacao

| Limite | Configuracao | Descricao |
|--------|--------------|-----------|
| Valor Minimo (R$) | Opcao 469 | Frete Peso, Frete Valor e Frete minimos |
| Desconto max NTC (%) | Opcao 469 | Desconto maximo sobre Tabela NTC |
| Min RC (%) | Opcao 469 | Resultado Comercial Minimo |
| Max inicial (%) | Opcao 423 > Opcao 469 > Opcao 903 | Desconto maximo sobre proposta inicial |

**Nota**: Limites por grupos (Opcao 369) substituem Limites 1 se cadastrados.

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004 | Cotacao contratada usada automaticamente na emissao de CTRC |
| 055 | Lembretes do cliente mostrados na tela |
| 068 | Comissao de cotacao para cotadores |
| 110 | Clientes realizam cotacoes pelo SSW |
| 114 | Cotacoes solicitadas no site da transportadora |
| 131/132 | Relatorios de comissao de cotacao |
| 180 | Mensagens padroes em e-mails de cotacao |
| 369 | Limites de cotacao por grupos |
| 386 | Tipos de mercadoria vinculados ao cliente |
| 402 | Observacoes e lembretes da cidade |
| 423 | Desconto maximo sobre proposta inicial, cubagem e TDA |
| 469 | Limites de cotacao por rota |
| 485 | Tipo de operacao (Subcontratacao ou Redespacho) |
| 538 | Lembretes da unidade e cidade |
| 583 | Grupo de empresas |
| 903 | Prazo de validade de cotacoes, configuracoes gerais |
| 925 | Usuarios com desbloqueio de resultado |

## Observacoes e Gotchas

### Uso da Cotacao no CTRC
Cotacao contratada e usada automaticamente quando:
- Dentro do prazo de validade (Opcao 903/prazos)
- CNPJ pagador identico
- Tabela de frete identica
- Cidade origem/destino identicas
- Tipo de mercadoria (se houver)
- CNPJ remetente (se houver)
- CNPJ destinatario (se houver)
- Nota Fiscal (se houver)

**Importante**: CTRC tera o mesmo percentual de desconto da cotacao aplicado sobre tabelas vigentes no momento da emissao.

### Contratacao
- **Valor Variavel**: Mantem percentual de desconto, recalcula valor na emissao do CTRC
- **Valor Fixo**: CTRC emitido com mesmo valor em Reais da cotacao

### Cancelamento
- Possivel pelo usuario que cadastrou
- Possivel por usuarios com Desbloqueia Resultado = SIM (Opcao 925)
- CTRC cancelado libera cotacao para nova emissao

### Exclusao Automatica
Cotacoes fora da validade e nao utilizadas sao apagadas em 90 dias apos inclusao.

### Usuarios Sem Bloqueio
Nao sofrem bloqueio de limites:
- Whirpool (CNPJ raiz: 05117268, 59105999, 62058318, 63699839)
- Electrolux (CNPJ raiz: 13986197, 76487032, 02421684)
- Deere Hitachi (CNPJ: 03.982.513/0001-33)
- John Deere (CNPJ: 89.674.782/0012-00, 89.674.782/0001-58)

### Cotacoes da MTZ
Cotacoes efetuadas por API, cliente (Opcao 110) ou MTZ podem ser simuladas e contratadas por qualquer usuario/unidade.

### Substituicao Tributaria
Valor cotado e o valor a receber. Valor do ICMS e somado para obter base de calculo. Parametro "ICMS na Tabela" (Opcao 903 e 483) nao e considerado.

### Retencoes de Orgaos Publicos
Retencoes (IR, CSLL, PIS, COFINS) que ocorrem na emissao de CTRC (Opcao 004) NAO sao consideradas na cotacao (Opcao 002).

### Comissao de Cotacao
- Cadastrada em Opcao 068
- Calculo agendado em Opcao 903/processamento batch
- Comissionado = usuario que contrata (nao quem cadastra)
- Pagamento quando CT-e e autorizado ou liquidado (Opcao 903/Outros)
- Nao calculada para CTRCs com vendedores (Opcao 415)

### Restricao de Mercadorias
Clientes podem ter uso de tipos de mercadorias restrito aos cadastrados em Opcao 386.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A01](../pops/POP-A01-cadastrar-cliente.md) | Cadastrar cliente |
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
