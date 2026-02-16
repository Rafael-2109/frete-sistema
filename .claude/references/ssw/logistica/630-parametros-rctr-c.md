# Opção 630 — Parâmetros de Cálculo do Seguro RCTR-C

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Cadastra parâmetros para cálculo do seguro RCTR-C (Responsabilidade Civil do Transportador Rodoviário de Cargas).

## Quando Usar
- Para configurar percentuais de cálculo do seguro RCTR-C por origem-destino
- Antes de iniciar operações que requerem seguro RCTR-C
- Para conferência da fatura da seguradora

## Pré-requisitos
- Contrato de seguro RCTR-C com seguradora

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Cidade origem | Não | Cidade de origem (tem prioridade sobre UF) |
| UF origem | Não | UF de origem (alternativa à cidade) |
| Cidade destino | Não | Cidade de destino (tem prioridade sobre UF) |
| UF destino | Não | UF de destino (alternativa à cidade) |
| % valor de mercadoria | Sim | Percentual a ser aplicado sobre valor de mercadorias averbáveis |

## Fluxo de Uso
1. Acessar opção 630
2. Cadastrar percentuais de cálculo por origem-destino
3. Informar cidade origem/destino OU UF origem/destino
4. Informar percentual do valor de mercadoria
5. Confirmar cadastro

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 056 | Relatório 165 - apresenta resumo com valores apurados do seguro RCTR-C |

## Observações e Gotchas
- **Prioridade**: Cidade origem/destino tem prioridade sobre UF origem/destino
- **Conferência diária**: Relatório da opção 056 apresenta resumo ao final com valores apurados (coluna VAL AVERBÁVEL)
- **Conferência mensal**: Relatório do dia 1 do mês seguinte (que acumula todos os dias do mês anterior) deve ser utilizado para conferir valor cobrado pela seguradora
- **Parametrização obrigatória**: Esta opção 630 deve ser configurada com os percentuais de cálculo do seguro RCTR-C
- **Valor averbável**: Utiliza coluna "VAL AVERBÁVEL" do relatório 165 (opção 056)
