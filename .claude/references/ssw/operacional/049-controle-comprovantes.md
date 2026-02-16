# Opcao 049 — Controle (Saiu para Entrega / Emissao Manual CTRCs)

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Grava ocorrencia "SAIU PARA ENTREGA" em CTRCs capturando codigo de barras. Alternativa para parceiros que nao conseguem emitir Romaneio SSW (Opcao 035). Tambem permite emissao manual de CTRCs em unidades sem sistema.

## Quando Usar
- Parceiro nao emite Romaneio SSW (mistura cargas de transportadoras)
- Registrar "Saiu para Entrega" via captura codigo barras (importante para e-commerce)
- Emitir manualmente CTRCs de blocos/formularios em unidades sem sistema

## Pre-requisitos
- CTRCs autorizados
- Codigo de barras CTRC/DACTE (para Saiu para Entrega)

## Funcao 1: Saiu para Entrega

### Campos / Interface
| Campo | Descricao |
|-------|-----------|
| Codigo de barras | Codigo do documento transportadora subcontratante |

### Fluxo
1. Capturar codigo barras CTRC/DACTE
2. Sistema grava ocorrencia "SAIU PARA ENTREGA"
3. Mesmas funcoes Opcao 035: disparo SMS, EDI, e-mail

### Cidade da Ocorrencia
Cidade da unidade entregadora da subcontratante.

## Funcao 2: Emissao Manual CTRCs

### Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade emissora | Sim | Sigla da unidade (qualquer pode digitar) |
| N/C/F | Sim | Normal/Cortesia/Fechada ou Completa |
| Data | Sim | Data emissao manual (pode ser passada) |
| Nro Controle | Sim | Numero formulario gráfica |
| Placa | Sim | Placa coleta (ou ARMAZEM se cliente trouxe) |
| Tipo do frete | Sim | 1-CIF, 2-FOB |
| Reembolso | Sim | S = cobrar valor mercadoria de destinatario |
| Remetente | Sim | CNPJ remetente |
| Destinatario | Sim | CNPJ destinatario |
| Pagador | Nao | Definido pelo tipo frete se nao informado |
| Tipo mercadoria | Sim | Tabela tipo mercadoria |
| Especie | Sim | Tabela especie |
| Quantidade volumes | Sim | Volumes |
| Peso real | Sim | Peso em quilos |
| Volume (m3) | Sim | Cubagem |
| Nota Fiscal | Sim | Serie + numero |
| Valor mercadoria | Sim | Valor em Reais |
| Despacho | Sim | Valor final frete (unica parcela habilitada) |
| Observacao | Nao | Informacoes adicionais |

### Fluxo
1. Informar unidade emissora
2. Preencher todos dados CTRC
3. Sistema numera automaticamente por IE da unidade
4. CTRC entra no sistema como se digitado pela Opcao 004
5. NAO e impresso (CTRC Manual e o documento fiscal)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004 | CTRC manual tratado como se digitado por esta opcao |
| 012 | Cadastro redespacho |
| 035 | Romaneio SSW (mesmas funcoes de disparo) |
| 483 | Parametros de cliente |
| 485 | Cadastro transportadora redespachadora |
| 903 | Parametros transportadora |

## Observacoes e Gotchas

### Saiu para Entrega
- Importante para embarcadores e-commerce
- Link http://www.ssw.inf.br/2/lastmile possui mesma funcionalidade
- Mesmas funcoes Opcao 035: SMS, EDI, e-mail

### Emissao Manual CTRC
- Todos dados informados manualmente
- Apenas ICMS calculado automaticamente (sem considerar CTRC manual)
- Todas validacoes padroes Opcao 004: cliente, cidades atendidas
- Valor frete no campo DESPACHO (inclui ICMS se cobrado de cliente)
- Sem impressao (CTRC Manual e documento fiscal)
- Apos inclusao, tratado como CTRC normal (Opcao 004)
- Pode ser alterado ate ser manifestado, romanceado ou faturado
- Remuneracao agregado pela placa informada
- Se cliente trouxe carga: placa = ARMAZEM

### Agrupamento NF
Link "AGRUPAMENTO DE NF" permite informar dados de multiplas NFs agrupadas.

### Redespacho/Local Entrega
Diferente de destinatario. Cadastrar transportadora (Opcao 012 e 485) ou informar endereco + CEP calculo.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D07](../pops/POP-D07-comprovantes-entrega.md) | Comprovantes entrega |
