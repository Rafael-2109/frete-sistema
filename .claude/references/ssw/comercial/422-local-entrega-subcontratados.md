# Opcao 422 — Local de Entrega para Subcontratados

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Define endereco de entrega diferente para subcontratados quando eles se responsabilizam pela transferencia ate sua unidade de distribuicao. Permite configurar local especifico onde mercadorias serao entregues ao parceiro, diferente do endereco cadastrado na unidade.

## Quando Usar
- Subcontratado tem ponto de recebimento diferente da unidade de distribuicao
- Parceiro assume transferencia ate sua base
- Operacao requer entrega em armazem/cross-dock especifico do subcontratado

## Pre-requisitos
- Unidade atual cadastrada (opcao 401)
- Unidade parceiro (subcontratado) cadastrada (opcao 401)
- Parceria ativa

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| ATUAL | Automatico | Sigla da unidade que fara entregas aos subcontratados |
| PARCEIRO | Sim | Sigla da unidade que identifica subcontratado |
| ENDERECO | Sim | Rua, numero e complemento onde mercadorias serao entregues |
| CEP | Sim | CEP do endereco do subcontratado |

## Fluxo de Uso

1. Acessar opcao 422
2. Sistema mostra unidade atual
3. Informar sigla unidade PARCEIRO
4. Cadastrar endereco especifico de entrega
5. Informar CEP
6. Gravar configuracao
7. Processos reconhecem novo endereco automaticamente (Romaneio, remuneracao)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 035 | Romaneio de entrega - reconhece endereco diferente |
| 075 | Emissao OS coleta/entrega - reconhece novo endereco |
| 076 | Demonstrativo remuneracao - reconhece novo endereco |
| 401 | Cadastro unidades (atual e parceiro) |
| 408 | Comissao de unidades (parcerias) |

## Observacoes e Gotchas

- **CTRC mantém dados originais**: endereco diferente nao afeta dados do CTRC emitido
- **Automatico para processos**: Romaneio e remuneracao reconhecem sem intervencao manual
- **Por unidade**: configuracao e especifica desta unidade para cada parceiro
- **Transferencia por parceiro**: util quando subcontratado assume custo transferencia ate sua base
