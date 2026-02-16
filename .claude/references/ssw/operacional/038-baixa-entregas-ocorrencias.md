# Opcao 038 — Baixa de Entregas / Ocorrencias

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 5 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Efetua baixa manual de entregas e registra ocorrencias (pendencias) em CTRCs. A baixa so pode ser efetuada na unidade destinataria. SSWMobile realiza baixa em tempo real (forma recomendada).

## Quando Usar
- Baixar entregas realizadas manualmente
- Informar pendencias de entrega
- Informar retorno de veiculo (Romaneios itinerantes ou SSWMobile)
- Visualizar comprovantes de entrega
- Controlar estadias

## Pre-requisitos
- Romaneio de Entregas emitido (Opcao 035)
- Tabela de ocorrencias (Opcao 405)
- Usuario na unidade destinataria do CTRC

## Campos / Interface

### Formas de Baixa

| Forma | Descricao |
|-------|-----------|
| Romaneio | Relaciona Romaneios com CTRCs pendentes de ocorrencias |
| Todos | Relaciona todos Romaneios da data (avalia qualidade comprovantes) |
| Codigo de barras | Baixa individual capturando codigo CTRC |
| Digitacao de CTRC | Baixa individual digitando numero CTRC |
| Romaneio sem controle | Baixa Romaneios de setores sem controle (Opcao 404) |
| Romaneio devolucao | Usa Romaneio assinado/escaneado (JPEG <20Mb) como comprovante |
| CTRCs pendentes | Relaciona em tela e Excel |
| CTRCs em Romaneios | Relaciona em relatorio (Opcao 129) |

### Tela CTRC

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Ocorrencia | Sim | Codigo de ocorrencia (Opcao 405) |
| Data/hora ocorrencia | Sim | Quando ocorreu |
| Odometro | Condicional | Se modulo Frota ativo |
| Receber frete | Nao | Frete FOB A VISTA (liquidar em Opcao 048) |
| Chegada/Saida | Condicional | Se controle estadias ativo (Opcao 903) |
| Dados recebedor | Condicional | Se configurado (Opcao 388 e 903) |

## Fluxo de Uso

### Baixar Entregas
1. Acessar Opcao 038
2. Escolher forma de baixa (Romaneio recomendado)
3. Selecionar Romaneio
4. Informar data/hora entrega
5. Marcar CTRCs entregues
6. Confirmar
7. Sistema muda para situacao "Entregue"

### Informar Pendencias
1. Acessar Opcao 038
2. Selecionar Romaneio ou CTRC
3. Escolher codigo ocorrencia pendencia (Opcao 405)
4. Informar data/hora e complemento
5. Confirmar
6. Sistema registra pendencia

### Retorno Veiculo (Romaneios Itinerantes)
1. Acessar Opcao 038
2. Informar codigo barras Romaneio ou "Retornar todos"
3. Sistema libera CTRCs para Capa (Opcao 040)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 028 | Motoristas sem SSWMobile |
| 035 | Romaneio de Entregas |
| 038 | Esta opcao |
| 040 | Capa de Comprovantes (Romaneios itinerantes) |
| 048 | Liquidacao de frete FOB A VISTA |
| 056 | Relatorio estadias nao cobradas (130) |
| 081 | CTRCs disponiveis para entrega |
| 088 | Situacao veiculos tempo real |
| 099 | CTRC Complementar de Estadia |
| 101 | Instrucoes de resgate |
| 129 | CTRCs em Romaneios |
| 138 | Estorno de ocorrencia |
| 236 | Encerramento MDF-e Romaneio |
| 381 | Deixar DACTE em destinatario FOB |
| 383 | Disparo e-mails rastreamento |
| 388 | Dados recebedor obrigatorios |
| 398 | Instalacao SSWScan |
| 405 | Tabela de ocorrencias |
| 409 | Remuneracao de entregas |
| 423 | CTRC Reentrega automatica, tabela estadia |
| 428 | Arquivamento Comprovantes |
| 523 | Relatorio estadias |
| 903 | Configuracoes gerais |
| SSWMobile | Baixa tempo real (recomendado) |
| SSWScan | Escaneamento comprovante |

## Observacoes e Gotchas

### Baixa Obrigatoria Dia Anterior
- Todos CTRCs Romaneio dia anterior devem receber ocorrencia
- Necessario para emitir novo Romaneio no dia seguinte
- Exceto setores sem controle (Opcao 404)

### Romaneios Itinerantes
- Requerem "Retorno do Veiculo" para entrar em Capa (Opcao 040)
- SSWMobile requer Opcao 903/Operacao ativado

### Controle de Estadias
Quando ativo (Opcao 903/Operacao):
- Tela solicita hora chegada e hora saida
- CTRC Complementar Estadia emitido automaticamente se:
  - Ocorrencia marcada (Opcao 405)
  - Cliente possui tabela (Opcao 423)
- SSWMobile: chegada = ocorrencia SSW 29, saida = proxima ocorrencia Entrega
- Relatorios: Opcao 056/130 (nao cobradas), Opcao 523 (por cliente)

### CTRC Reentrega Automatica
- Opcao 423: Cliente com S
- Ocorrencias marcadas REENTREGA (Opcao 405)
- CTRCs Reentrega emitidos automaticamente (Opcao 038 ou SSWMobile)

### Dados do Recebedor
- Nome, documento e parentesco
- Configuracao por cliente (Opcao 388) ou transportadora (Opcao 903/Operacao)

### Remuneracao Veiculos
- Tabela Opcao 409
- Codigos de ocorrencias atribuidos

### Integracao Parceiros
- Ocorrencias atualizam todas transportadoras integrantes da operacao CTRC
- Baixa pode ser dada por qualquer unidade tipo filial (FEC ou parceiras)

### Estorno de Ocorrencia
- Ultima ocorrencia tipo BAIXA/ENTREGA ou resgate (codigo SSW 88)
- Estorno via Opcao 138

### Modulo FROTA
- Solicita quilometragem atual odometro
- Para gerenciamento manutencao veiculo

### Comprovantes
Link "Comprovantes" relaciona todos CTRCs e respectivos Comprovantes de Entrega (capturados ou nao pelo SSWMobile), permitindo avaliar existencia de comprovacao.

### Encerramento MDF-e
MDF-e vinculado ao Romaneio (Opcao 236) encerra automaticamente com:
- Emissao proximo MDF-e vinculado ao Romaneio (mesma UF destino)
- Baixa integral do Romaneio

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-C05](../pops/POP-C05-imprimir-cte.md) | Imprimir cte |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D05](../pops/POP-D05-baixa-entrega.md) | Baixa entrega |
| [POP-D06](../pops/POP-D06-registrar-ocorrencias.md) | Registrar ocorrencias |
| [POP-D07](../pops/POP-D07-comprovantes-entrega.md) | Comprovantes entrega |
