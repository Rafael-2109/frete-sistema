# Opcao 533 — Liquidacao de Subcontratos via Mapa de Comissao

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Permite que subcontratada (que usa SSW) confira Mapa de Comissionamento emitido pela subcontratante e liquide os Subcontratos correspondentes que emitiu. Sistema credita valores na Conta Corrente Bancaria indicada.

## Quando Usar
- Subcontratada (usa SSW) recebeu Mapa de Comissao da subcontratante
- Necessidade de conferir valores de comissao calculada vs comissao paga
- Liquidacao de subcontratos emitidos pela subcontratada

**IMPORTANTE**: Cobranca via faturamento (opcao 436) e melhor alternativa que esta opcao 533 que usa Mapa.

## Pre-requisitos
- Subcontratada usa SSW e emitiu subcontratos
- Subcontratante enviou Mapa de Comissionamento
- Subcontratante cadastrada (opcao 485)
- Conta Corrente Bancaria configurada (opcao 456)

## Campos / Interface
| Campo | Descricao |
|-------|-----------|
| Sigla subcontratante | Sigla da subcontratante (opcao 485) |
| Mapa | Numero/dados do Mapa de Comissionamento |

### Listagem de CTRCs
| Coluna | Descricao |
|--------|-----------|
| CTRC | CTRC incluido no Mapa |
| Destino | Sigla da unidade destino |
| Pacote | Pacote de arquivamento do CTRC da subcontratante |
| Comissao de calculo | Valor calculado (importado do CTRC ou calculado por tabelas) |
| Subcontrato | Subcontrato correspondente ao CTRC do Mapa |
| Comissao paga | Valor sendo pago no Mapa (elaborado pela subcontratante) |
| Diferenca | Diferenca entre comissao calculada e comissao paga |

### Rodape
| Funcao | Descricao |
|--------|-----------|
| Ver Mapa | Visualiza Mapa |
| Imprimir Mapa | Imprime Mapa em formato padrao |
| Imprimir Mapa Excel | Imprime Mapa em formato Excel |
| Liquidar Mapa | Credita valor na Conta Corrente Bancaria e liquida subcontratos |
| Desistir da verificacao | Abandona verificacao do Mapa |

## Fluxo de Uso
1. Receber Mapa de Comissionamento da subcontratante
2. Acessar opcao 533
3. Informar sigla da subcontratante (opcao 485)
4. Informar dados do Mapa
5. Se subcontratante NAO usa SSW: digitar CTRCs e valores de comissao manualmente
6. Conferir listagem de CTRCs:
   - Verificar comissao calculada vs comissao paga
   - Analisar diferencas
7. Visualizar totais no final da tela
8. Decidir aceitar ou nao o Mapa
9. Se aceitar: clicar em "Liquidar Mapa"
   - Sistema credita valor na Conta Corrente Bancaria (opcao 456)
   - Subcontratos sao liquidados
10. Se nao aceitar: clicar em "Desistir da verificacao"

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 485 | Cadastro de subcontratante |
| 456 | Conta Corrente Bancaria (credito do Mapa) |
| 436 | Cobranca via fatura (alternativa RECOMENDADA) |
| 607 | Conferencia pela subcontratante (se usa SSW) |

## Observacoes e Gotchas

### Recomendacao Importante
- **Cobranca via faturamento e melhor**: opcao 436 (cobranca via fatura como qualquer cliente) e alternativa MELHOR que opcao 533 (Mapa)
- Se subcontratante usa SSW, ela efetua conferencia pela opcao 607

### Subcontratante Nao Usa SSW
- Mapa (valor da comissao e CTRCs) precisa ser digitado manualmente
- Redigitacao de CTRC retira o CTRC da lista

### Comissao de Calculo
- **Subcontratante usa SSW**: valor importado do CTRC da subcontratante
- **Subcontratante NAO usa SSW**: valor calculado pelas tabelas de fretes

### Conferencia e Diferencas
- Sistema mostra diferenca entre comissao calculada e comissao paga
- Totais no final da tela permitem aceitar ou nao o Mapa
- Analise de diferencas e importante antes de liquidar

### Liquidacao
- Clicar em "Liquidar Mapa" realiza:
  1. Credito na Conta Corrente Bancaria (opcao 456)
  2. Liquidacao dos subcontratos correspondentes
- **Estornos**: eventuais estornos devem ser lancados diretamente na conta (opcao 456)

### Impressao
- 3 formatos disponiveis: visualizacao, impressao padrao, impressao Excel
- Util para documentacao e conferencia antes de liquidar
