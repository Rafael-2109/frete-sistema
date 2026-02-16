# Opcao 335 — Acoes de Vendas

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (fonte: opcao 333)
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra tabela de acoes de vendas (com codigos numericos de 2 digitos) a serem utilizadas pela agenda (opcao 335) e relatorio de visita (opcao 119) para organizacao e rastreamento de atividades comerciais.

## Quando Usar
- Padronizar acoes comerciais para uso na agenda e relatorios
- Organizar atividades de vendas com codigos unificados
- Preparar tabela de acoes antes de usar agenda de vendas (opcao 335)
- Configurar acoes para rastreamento em relatorio de visitas (opcao 119)

## Pre-requisitos
- Definicao das acoes comerciais a serem rastreadas
- Planejamento de codigos numericos (2 digitos, 00-99)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Codigo | Sim | Codigo numerico de 2 digitos (00-99) |
| Descricao | Sim | Descricao da acao (ex: Telefonar ao cliente, Visitar cliente, Realizar cotacao, Black-Friday, Natal, Dia das Maes) |
| Excluir | Nao | Exclui acao ainda NAO utilizada pela opcao 335 |

## Fluxo de Uso
1. Definir codigo numerico de 2 digitos para acao
2. Descrever acao de forma clara e objetiva
3. Salvar cadastro
4. Acao fica disponivel para uso na:
   - Agenda de vendas (opcao 335)
   - Relatorio de visita (opcao 119)
5. Se acao ainda nao foi utilizada, pode ser excluida

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 335 | Agenda — utiliza acoes de vendas cadastradas nesta opcao |
| 119 | Relatorio de visita — utiliza acoes de vendas cadastradas nesta opcao |

## Observacoes e Gotchas
- **Codigo de 2 digitos**: limite de 00 a 99 (maximo 100 acoes diferentes)
- **Exclusao condicional**: acao so pode ser excluida se ainda NAO foi utilizada pela opcao 335 (agenda)
- **Exemplos de acoes**:
  - Operacionais: Telefonar ao cliente, Visitar cliente, Realizar cotacao
  - Campanhas sazonais: Black-Friday, Natal, Dia das Maes
  - Eventos comerciais: Feira, Visita tecnica, Apresentacao de proposta
- **Padronizacao**: uso de codigos unificados facilita analise de produtividade comercial e geracao de relatorios consolidados
- **Nota sobre numeracao**: opcao 333 e 335 parecem ser relacionadas (333=cadastro de acoes, 335=agenda que usa as acoes)
