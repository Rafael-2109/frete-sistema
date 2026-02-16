# Opcao 520 — Substituicao de CT-e e Complementacao do ICMS

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Substitui CT-e emitido erroneamente (apos tomador registrar evento de prestacao em desacordo) e emite CT-e para complementar o ICMS ou ISS. Operacao realizada conforme Ajuste SINIEF 31 de 23/09/2022.

## Quando Usar
- Tomador (pagador do frete) registrou evento de prestacao em desacordo
- Necessidade de corrigir CT-e emitido com erro (substituicao)
- Complementar ICMS ou ISS recolhido anteriormente
- Recuperar ICMS, PIS e COFINS de CT-e errado

## Pre-requisitos
- CT-e original autorizado
- Evento de prestacao em desacordo registrado pelo tomador (para substituicao)
- CT-e substituto deve ser emitido ate 60 dias apos autorizacao do original
- CT-e original nao pode ter carta de correcao (opcao 736)
- CT-e original nao pode ter sido complementado anteriormente

## Campos / Interface

### Substituicao de Frete
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Incluir NF-e de anulacao | - | INATIVADO a partir de 03/04/2023 |
| Emitir CT-e de anulacao | - | INATIVADO a partir de 03/04/2023 |
| Emitir CT-e Substituto | Sim | Informar CT-e de referencia a ser substituido, depois digitar dados corretos (opcao 004) |
| Relacao de CTRCs substituidos | Info | Lista CTRCs substituidos e seus substitutos nao cancelados |

### Emitir CTRC/NF Complementar
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Emitir CTRC Complementar | Sim | Informar CTRC referencia para complementar ICMS |

## Fluxo de Uso

### Substituicao de CT-e
1. Tomador registra evento de prestacao em desacordo (site SEFAZ)
2. Acessar opcao 520
3. Clicar em "Emitir CT-e Substituto"
4. Informar numero do CT-e a ser substituido
5. Sistema abre tela de digitacao de CTRCs (opcao 004)
6. Informar dados corretos do novo CT-e
7. Emitir CT-e substituto
8. CT-e original passa a ter situacao "BLOQUEIO SUBSTITUICAO" (nao pode ser cobrado)
9. Sistema recupera automaticamente ICMS, PIS e COFINS do CT-e errado

### Complementacao de ICMS/ISS
1. Acessar opcao 520
2. Clicar em "Emitir CTRC Complementar"
3. Informar numero do CTRC referencia
4. Sistema emite novo CT-e (ou RPS) complementar de ICMS/ISS
5. Se referencia for Subcontrato, ICMS e excepcionalmente destacado no complementar

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 004 | Digitacao de CTRCs (usado para informar dados corretos do substituto) |
| 221 | Complementar frete do CTRC (NAO ICMS) |
| 222 | CT-e complementar (incompativel com substituicao) |
| 429 | Estorno da substituicao |
| 736 | Carta de Correcao (incompativel com substituicao) |
| 486 | Conta Corrente Fornecedor (debita comissao de agenciamento do substituido) |
| 512 | Arquivos/livros fiscais (ajustados automaticamente) |
| 515 | SPED Contribuicoes (ajustado automaticamente) |
| 496 | Livros fiscais (ajustados automaticamente) |
| 433 | Livros fiscais (ajustados automaticamente) |
| 996 | Evento de prestacao em desacordo (transportadora como tomadora) |

## Observacoes e Gotchas

### CT-e Substituto
- **Prazo**: so pode ser emitido ate 60 dias apos autorizacao do CT-e original
- **Cancelamento**: NAO pode ser cancelado
- **Recuperacao automatica**: recupera ICMS, PIS e COFINS do CT-e errado, ajusta arquivos/livros fiscais automaticamente

### CT-e Substituido
- **Bloqueio**: nao pode ser cobrado, passa a ter situacao "BLOQUEIO SUBSTITUICAO"
- **Sem complemento anterior**: nao pode ter sido complementado antes (mesmo que cancelado)
- **Sem carta de correcao**: nao pode ter carta de correcao (opcao 736)
- **Sem complementar**: nao pode ter CT-e complementar (opcao 222)

### CT-e Complementar
- **Subcontrato**: mesmo referencia sendo Subcontrato, ICMS e excepcionalmente destacado no complementar (Subcontrato normalmente nao tem ICMS)
- **Complementar frete**: para complementar valor do frete (NAO ICMS), usar opcao 221

### Processos Relacionados
- **Evento de prestacao em desacordo**: tomador deve registrar no site SEFAZ (https://dfe-portal.svrs.rs.gov.br/Cte/PrestacaoServicoDesacordo)
- **Estorno**: substituicao pode ser estornada via opcao 429
- **Comissao de agenciamento**: comissao de CTRC substituido incluido em Mapa sera debitado na Conta Corrente Fornecedor (opcao 486)
- **Transportadora tomadora**: se transportadora foi incluida erradamente como tomadora de CT-e Subcontrato/Redespacho, pode incluir evento via opcao 996

### Funcoes Inativadas
- "Incluir NF-e de anulacao" e "Emitir CT-e de anulacao" foram INATIVADAS a partir de 03/04/2023 (usar CT-e Substituto conforme SINIEF 31/2022)
