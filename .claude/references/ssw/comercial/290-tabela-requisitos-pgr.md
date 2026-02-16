# Opcao 290 — Tabela de Requisitos PGR

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (duplicadas)
> **Atualizado em**: 2026-02-14

## Funcao
Define os requisitos utilizados pelo PGR (Programa de Gerenciamento de Riscos) acordado com a seguradora, que podem estar associados aos veiculos para controle de limites de carregamento de mercadorias.

## Quando Usar
- Cadastrar novos requisitos de seguranca exigidos pela seguradora
- Configurar requisitos de PGR para veiculos (bloqueador, localizador, estribo de cabine, etc.)
- Preparar tabela de requisitos para uso na opcao 390 (limites de carregamento)

## Pre-requisitos
- Acordo PGR firmado com seguradora definindo requisitos necessarios
- Conhecimento dos requisitos de seguranca exigidos

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Codigo | Sim | Identifica o requisito. Codigos 51-99 disponiveis para uso do cliente. Codigos 01-50 sao de uso do SSW |
| Requisito | Sim | Descricao do requisito (ex: estribo de cabine, bloqueador, localizador) |
| Tipo | Sim | V=especificos de veiculos (associados na opcao 026), O=Outros (de uso do SSW) |
| Ordem PGR | Sim | Ordem de apresentacao na tela da opcao 390, facilitando configuracao |
| Tabela (visualizacao) | Nao | Requisitos cadastrados com links para alteracao e exclusao |

## Fluxo de Uso
1. Definir codigo do requisito (51-99 para uso proprio, 01-50 reservados SSW)
2. Descrever requisito (nome/descricao clara)
3. Selecionar tipo (V=veiculo, O=outros)
4. Definir ordem de apresentacao na opcao 390
5. Salvar cadastro
6. Associar requisitos aos veiculos via opcao 026
7. Configurar limites de carregamento na opcao 390 com base nos requisitos

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 026 | Cadastro de veiculos — informa quais requisitos estao presentes no veiculo |
| 390 | Define limites de carregamento de mercadorias (valores) para condicoes operacionais e veiculos com seus requisitos |

## Observacoes e Gotchas
- **Codigos reservados**: 01-50 sao de uso exclusivo do SSW. Clientes devem usar 51-99
- **Tipo V (veiculo)**: requisitos marcados como V ficam disponiveis para associacao na opcao 026 (cadastro de veiculos)
- **Tipo O (outros)**: de uso interno do SSW
- **Ordem PGR**: define sequencia de exibicao na opcao 390, facilitando organizacao visual
- **Exclusao cascata**: ao excluir um requisito, TODOS os veiculos cadastrados (opcao 026) perdem este requisito
- **PGR (Programa de Gerenciamento de Riscos)**: sistema de controle exigido por seguradoras para limitar exposicao de risco conforme nivel de seguranca do veiculo
- **Exemplos de requisitos**: estribo de cabine, bloqueador de bau, rastreador/localizador GPS, camera de monitoramento, escolta armada, etc.
