# 08 — Logistica (Armazenagem)

> **Fonte**: `visao_geral_logistica.htm` (01/09/2024)
> **Links internos**: 24 | **Imagens**: 1

## Sumario

Modulo de armazenagem integrado ao transporte. 2 modalidades: Armazem Geral (fiscal) e Operador Logistico (sem fiscal).

---

## Modalidades

| Tipo | Fiscal | Descricao |
|------|--------|-----------|
| **Armazem Geral** | Sim (SEFAZ) | Entrada e saida de mercadorias no estoque. NF de transferencia obrigatoria |
| **Operador Logistico** | Nao | Prestador de servico. NF de saida = mesma da entrada |

---

## O Estoque

### Movimentacao
| Opcao | Funcao |
|-------|--------|
| [701](../logistica/701-entrada-estoque.md) | Entrada no estoque (com DANFE do cliente). Itens devem estar em [opção 741](../logistica/741-cadastro-mercadorias.md) |
| [702](../logistica/702-saida-estoque-nft.md) | Saida do estoque |
| 703/707 | NF de transferencia (Armazem Geral → emissao obrigatoria) |

### Situacao do Estoque
| Opcao | Funcao |
|-------|--------|
| 724 | Volumes disponiveis (saldo atual de todas as mercadorias) |
| 721 | Entradas, saidas e saldos no periodo |
| 722 | Saldos diarios em: Kg, litro, m3, m2, m2 empilhado → Excel para calculo de armazenagem |
| 725 | Romaneio de carregamento (itens a carregar) |
| 734 | Situacao da NF (entrada, saida ou transferencia) |

---

## Retaguarda

| Opcao | Funcao |
|-------|--------|
| 723 | Lancamentos manuais no estoque (ajustes) |
| [733](../logistica/733-emissao-rps.md)/[009](../operacional/009-impressao-rps-nfse.md) | Emissao de RPS (cobrar servico de armazenagem) |
| 101 | Situacao da NFS |
| [731](../logistica/731-impressao-ordem-servico.md)/732 | Ordem de Servico (controle, sem valor fiscal/financeiro) |
| 735 | Situacao da OS |

---

## Conceito: M2 Empilhado

- Area ocupada considerando empilhamento maximo
- Formula: `area_sem_empilhamento / qtd_maxima_empilhavel`
- Exemplo: 1,2 m2 com empilhamento max 50 → 0,024 m2/caixa
- Para 230 caixas: 0,024 x 230 = 5,52 m2 = 4,6 pallets de 1,2 m2

---

## Cadastros

| Opcao | Funcao |
|-------|--------|
| [741](../logistica/741-cadastro-mercadorias.md) | Mercadorias (embalagem, peso, litros, m3, m2, m2 empilhado por volume) |
| [483](../cadastros/483-cadastro-clientes.md) | Cliente — define servico: ARMAZEM GERAL ou OPERADOR LOGISTICO |
| [401](../cadastros/401-cadastro-unidades.md) | Unidade — define tipo de servico prestado |

---

## Contexto CarVia

### Opcoes que CarVia usa
*Nenhuma — CarVia nao opera logistica avancada (armazenagem, cross-docking, logistica reversa).*

### Opcoes que CarVia NAO usa (mas deveria)
*Nenhuma no momento — modulo inteiro NAO IMPLANTADO, baixa prioridade.*

CarVia e uma transportadora simples (2 caminhoes, foco em entregas). Opcoes 700+ (logistica/armazenagem) nao se aplicam ao modelo operacional atual. Se CarVia crescer para operacao logistica (armazem geral ou operador logistico), este modulo se torna relevante.

### Status de Implantacao
- Modulo inteiro NAO IMPLANTADO — baixa prioridade

### Responsaveis
- **Atual**: Ninguem (modulo nao aplicavel)
- **Futuro**: A definir (somente se CarVia expandir para operacao logistica)
