# Opcao 013 — Veiculo Sugerido por Setor

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Define os setores atendidos por um veiculo de coleta/entrega, permitindo que o sistema sugira automaticamente o veiculo correto ao comandar coletas ou entregas para aquele setor.

## Quando Usar
- Vincular veiculo a setores especificos
- Garantir que mesmo veiculo atenda mesma regiao
- Facilitar operacao de comando de coletas/entregas
- Obter relatorio de setores vinculados a veiculo

## Pre-requisitos
- Unidade cadastrada (Opcao 401)
- Veiculo cadastrado (Opcao 026)
- Setores definidos (Opcao 404)

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade | Sim | Unidade cujos setores serao vinculados |
| Veiculo | Sim | Placa do veiculo de coleta/entrega |
| Setores | Sim | Selecao de setores atendidos pelo veiculo |

## Fluxo de Uso
1. Acessar Opcao 013
2. Informar unidade
3. Informar placa do veiculo
4. Marcar setores atendidos
5. Gravar vinculacao

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 003 | Veiculo sugerido ao comandar coletas |
| 026 | Cadastro de veiculos |
| 035 | Veiculo sugerido ao emitir Romaneio de Entregas |
| 401 | Cadastro de unidades |
| 404 | Cadastro de setores |
| SSWMobile | Veiculo sugerido no mobile |

## Observacoes e Gotchas

### Objetivo
Proporcionar eficiencia operacional permitindo que **veiculo faca sempre a mesma regiao**, reduzindo tempo de deslocamento e aumentando conhecimento do motorista sobre a area.

### Relatorio
Link "Relatorio de Setores do veiculo" relaciona os setores vinculados ao veiculo.

### Uso Automatico
Veiculos vinculados sao sugeridos automaticamente:
- Ao comandar coletas (Opcao 003)
- Ao emitir Romaneio de Entregas (Opcao 035)
- No SSWMobile para motorista
