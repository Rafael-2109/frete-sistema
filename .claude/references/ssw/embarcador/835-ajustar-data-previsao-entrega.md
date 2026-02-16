# Opção 835 — Ajustar Data de Previsão de Entrega

> **Módulo**: Embarcador
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Altera a data de previsão de entrega do CTRC em situações excepcionais.

## Quando Usar
- Em situações excepcionais onde é necessário alterar a data de previsão de entrega
- Quando a data calculada automaticamente precisa ser ajustada
- Para correção de prazos por motivos operacionais específicos

## Pré-requisitos
- CTRC já emitido e autorizado

## Campos / Interface

### Tela 01
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Chave DACTE | Condicional | Capturar chave DACTE (ou informar número do CTRC) |
| Número do CTRC | Condicional | Informar número do CTRC (ou capturar chave DACTE) |

### Tela 02
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Nova data | Sim | Nova data de previsão de entrega |

## Fluxo de Uso
1. Acessar opção 835
2. Capturar chave DACTE ou informar número do CTRC
3. Informar nova data de previsão de entrega
4. Confirmar alteração

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 004 | Geração de CTRCs - define data de previsão inicial |
| 696 | Previsão de entrega por cliente (uma origem) |
| 697 | Previsão de entrega por cliente (origem-destino) |

## Observações e Gotchas

### Restrições
- **Data mínima**: Nova data não pode ser anterior à emissão do CTRC
- **Data máxima**: Nova data não pode ser posterior a 30 dias de hoje
- **Uso com parcimônia**: Deve ser utilizada com moderação para não perder credibilidade perante o cliente

### Características Importantes
- **Situações excepcionais**: Opção destinada a casos específicos onde cálculo automático não atende
- **Cálculo automático**: Data inicial é calculada automaticamente pelo sistema conforme tabelas (opções 696, 697, 402, 403)
- **Impacto na credibilidade**: Alterações frequentes podem prejudicar confiança do cliente nos prazos informados
- **Flexibilidade limitada**: Janela de 30 dias a partir de hoje limita ajustes muito distantes
