# Opção 073 (077) — Reemissão de CTRBs

> **Módulo**: Operacional — Controle de Contratação
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Reimprime CTRBs (Contrato de Transporte Rodoviário de Bens) emitidos pelas opções 072, 075 e 118.

## Quando Usar
- Necessidade de reimprimir CTRB para entrega ao motorista/proprietário
- Perda ou extravio do documento físico
- Solicitação de segunda via

## Pré-requisitos
- CTRB já emitido pelas opções 072 (contratação transferência), 075 (contratação agregado) ou 118 (contratação frota)

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Número do CTRB | Sim | Número do CTRB a ser reimpresso |
| Último CTRB da unidade | Exibição | Mostra número do último CTRB gerado na unidade, clique abre para impressão |

## Opções de Impressão
| Link | Descrição |
|------|-----------|
| REIMPRIMIR CTRB/RPA | Imprime CTRB junto com RPA (Recibo de Pagamento de Autônomo) |
| REIMPRIMIR CTRB | Imprime apenas o CTRB |

## Fluxo de Uso
1. Usuário acessa opção 077 (ou 073)
2. Informa número do CTRB desejado OU clica no link "Último CTRB da unidade"
3. Seleciona opção de impressão (CTRB+RPA ou somente CTRB)
4. Sistema abre documento para impressão

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 072 | Emissão de CTRB para contratação de transferência |
| 075 | Emissão de CTRB para acerto de agregado |
| 118 | Emissão de CTRB para adiantamento frota |

## Observações e Gotchas
- **Opção 073 vs 077**: Mesmo conteúdo, opção 077 preferencialmente liberada para pessoal da expedição
- **RPA**: Recibo de Pagamento de Autônomo emitido para pessoa física com retenções INSS/IR
- **Último CTRB**: Atalho rápido para reimprimir documento mais recente da unidade
- **Somente reimpressão**: Opção não permite alterar dados, apenas reimprimir
