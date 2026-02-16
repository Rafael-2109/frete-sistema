# Opcao 028 — Relacao de Motoristas

> **Modulo**: Operacional — Frota
> **Paginas de ajuda**: 1 pagina consolidada (tambem referencia opcao 047)
> **Atualizado em**: 2026-02-14

## Funcao
Fornece relatorio com relacao de motoristas cadastrados, incluindo status de bloqueio, ultimo movimento e periodo de cadastramento.

## Quando Usar
- Consultar base de motoristas cadastrados
- Verificar motoristas bloqueados
- Auditar atividade de motoristas (ultimo movimento)
- Filtrar motoristas por periodo de cadastramento

## Pre-requisitos
- Motoristas cadastrados via opcao 028

## Campos / Interface

| Campo | Descricao |
|-------|-----------|
| **Relacao com a transportadora** | Status do vinculo conforme cadastrado (opcao 028) |
| **Bloqueado** | Indica se motorista esta bloqueado para operacao |
| **Ultimo movimento** | Data da ultima operacao executada pelo motorista no SSW (formato DDMMAA) |
| **Periodo de cadastramento** | Data do cadastramento do motorista (opcao 028) |

## Fluxo de Uso
1. Acessar opcao 047 (ou 028 para relatorio)
2. (Opcional) Aplicar filtros por periodo de cadastramento ou status
3. Visualizar relacao de motoristas
4. Verificar ultimo movimento para identificar motoristas inativos

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| **028** | Cadastro de motoristas (fonte dos dados) |
| **020** | Emissao de Manifesto — exige CPF motorista cadastrado |
| **025** | Saida de veiculos — registra movimento do motorista |
| **030** | Chegada de veiculos — registra movimento do motorista |
| **903** | Gerenciamento de Risco — configuracao de liberacao de motoristas |
| **228** | Motoristas em quarentena — bloqueio temporario |
| **163** | Cadastro de ajudantes |

## Observacoes e Gotchas
- **Formato de data** — DDMMAA (6 digitos, ex: 140226 = 14/02/2026)
- **Ultimo movimento** — util para identificar motoristas inativos ou terceiros eventuais
- **Bloqueio** — motorista bloqueado nao pode ser usado em emissao de manifestos (opcao 020)
- Opcao **047** (citada na ajuda) e o numero alternativo para acessar esta funcionalidade
- Video disponivel na documentacao original para demonstracao de uso

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A09](../pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
