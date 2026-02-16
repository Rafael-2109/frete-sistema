# Opcao 228 — Motorista e Quarentena

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Cadastro de motoristas que estao impedidos de realizar operacoes de carregamento em determinados clientes durante um periodo especifico (quarentena).

## Quando Usar
- Cliente solicita restricao de operacao com determinado motorista (ex: incidente, problemas de conduta, questoes de seguranca)
- Necessario bloquear temporariamente motorista de carregar em cliente especifico
- Gestao de conformidade com exigencias de clientes

## Pre-requisitos
- Motorista cadastrado no sistema
- Cliente pagador cadastrado (CNPJ)
- Definicao do periodo de restricao

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ cliente | Sim | CNPJ do cliente pagador que restringe operacoes com determinados motoristas. **Restricao vale para TODOS os CNPJs da raiz do CNPJ cadastrado** |
| CPF motorista | Sim | CPF do motorista com restricoes no cliente |
| Periodo de quarentena | Sim | Periodo (DDMMAA) em que o motorista possui restricoes (data inicial e final) |
| Tabela (visualizacao) | Nao | Mostra relacao de motoristas em quarentena por cliente. Links permitem alteracao e exclusao |

## Fluxo de Uso
1. Informar CNPJ do cliente que solicita restricao
2. Informar CPF do motorista a ser restrito
3. Definir periodo de quarentena (data inicio e fim, formato DDMMAA)
4. Salvar cadastro
5. Motorista fica bloqueado automaticamente nas operacoes de carregamento durante o periodo
6. Tabela permite consultar, alterar ou excluir restricoes ativas

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 003 | Carregamento de coletas — bloqueado para motorista em quarentena |
| 020 | Transferencia — bloqueada para motorista em quarentena |
| 038 | Entrega — bloqueada para motorista em quarentena |

## Observacoes e Gotchas
- **Restricao por RAIZ de CNPJ**: a quarentena vale para TODOS os CNPJs da mesma raiz do CNPJ cadastrado (nao apenas para o CNPJ especifico)
- **Quarentena impede 3 operacoes**: carregamento de coletas (003), transferencia (020) e entrega (038)
- **Periodo temporario**: quarentena e definida por data inicio/fim. Apos o periodo, motorista volta a operar normalmente
- **Tabela gerencial**: interface mostra listagem de todas as quarentenas ativas com links para alteracao/exclusao rapida
- **Formato de data**: periodo usa formato DDMMAA (dia/mes/ano com 2 digitos)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A09](../pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista |
