# Opcao 560 — Aprovacao de Despesas

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Efetua aprovacao centralizada de despesas para liberacao de liquidacao. Sistema controla aprovacao por parcela (nao por despesa), comparando com orcamento da unidade/evento/mes. Apenas despesas aprovadas podem ser liquidadas via opcao 476.

## Quando Usar
- Controle centralizado de aprovacao de despesas
- Verificar parcelas a pagar em relacao ao orcamento
- Aprovar/reprovar despesas programadas pelas unidades
- Evitar liquidacao de despesas sem aprovacao gerencial

## Pre-requisitos
- Aprovacao centralizada ativada (opcao 903/Outros)
- Grupo do usuario aprovador com opcao 560 liberada (opcao 918)
- Despesas programadas pelas unidades (opcao 475)
- Orcamentos cadastrados por unidade/evento/mes (opcao 380)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Pagamentos no periodo | Sim | Periodo para selecao de parcelas a aprovar (por data de pagamento) |
| Unidade | Nao | Filtro opcional (se omitido, considera todas as unidades) |
| Numero de Lancamento | Nao | Filtro para parcelas de uma despesa especifica |

### Tela de Aprovacao
| Coluna | Descricao |
|--------|-----------|
| Parcelas nao liquidadas | Lista de parcelas disponiveis para aprovacao |
| Total dos pagamentos marcados | Atualizado a cada parcela marcada |
| Orcamento | Valor estabelecido para unidade/evento/mes (opcao 380) |
| Comprometido | Parcelas ja liquidadas + aprovadas (opcao 560) no evento/mes/unidade |
| Saldo | Orcamento - Comprometido |
| Este pagamento | Valor a aprovar (COR VERMELHA se saldo insuficiente, mas NAO impede aprovacao) |
| Comentario | Comentarios do aprovador (aprovadas ou nao) |
| Marca de aprovacao | Marcar parcelas aprovadas (ultima coluna) |

## Fluxo de Uso

### Configuracao Inicial (Uma Vez)
1. Acessar opcao 903/Outros
2. Ativar aprovacao centralizada de despesas
3. Acessar opcao 918 (grupos de usuarios)
4. Liberar opcao 560 para grupo de usuarios aprovadores
5. Cadastrar orcamentos por unidade/evento/mes (opcao 380)

### Processo Recorrente
1. **Unidades programam despesas**: opcao 475
2. **Aprovacao**: opcao 560 (marca parcelas aprovadas)
3. **Liquidacao**: opcao 476 (apenas parcelas aprovadas)

### Aprovar Despesas
1. Acessar opcao 560
2. Informar periodo de pagamentos
3. Opcionalmente filtrar por unidade ou numero de lancamento
4. Analisar lista de parcelas:
   - Verificar orcamento vs comprometido vs saldo
   - Identificar parcelas com saldo insuficiente (vermelhas)
5. Marcar parcelas aprovadas (ultima coluna)
6. Adicionar comentarios se necessario
7. Confirmar aprovacao
8. Parcelas aprovadas ficam disponiveis para liquidacao (opcao 476)

### Desaprovar (Remover Marca)
- Possivel APENAS enquanto parcela nao foi liquidada
- Apos liquidacao (opcao 476), marca nao pode ser retirada

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 475 | Programacao de despesas (origem das parcelas) |
| 476 | Liquidacao de despesas (apenas parcelas aprovadas) |
| 380 | Cadastro de orcamentos (por unidade/evento/mes) |
| 903 | Ativacao de aprovacao centralizada (Outros) |
| 918 | Grupos de usuarios (liberar opcao 560 para aprovadores) |

## Observacoes e Gotchas

### Processo de Aprovacao Centralizada
1. **Ativacao**: configurar na opcao 903/Outros
2. **Permissoes**: grupo do usuario aprovador deve ter opcao 560 liberada (opcao 918)
3. **Programacao**: unidades programam despesas (opcao 475)
4. **Aprovacao**: parcelas aprovadas via opcao 560
5. **Liquidacao**: apenas parcelas aprovadas podem ser liquidadas (opcao 476)

### Selecao por Parcela
- **NAO por despesa**: selecao se da por PARCELA (data de pagamento), nao por despesa completa
- **Periodo**: informar periodo de pagamento das parcelas desejadas
- **Despesa especifica**: usar "Numero de Lancamento" para aprovar parcelas de uma despesa especifica

### Controle de Orcamento
- **Orcamento**: valor estabelecido para unidade/evento/mes (opcao 380)
- **Comprometido**: soma de parcelas ja liquidadas + aprovadas (opcao 560) no evento/mes/unidade
- **Saldo**: Orcamento - Comprometido
- **Alerta visual**: "Este pagamento" fica VERMELHO se saldo insuficiente

### Aprovacao Flexivel
- **Saldo insuficiente NAO impede aprovacao**: sistema alerta (vermelho) mas permite aprovar
- **Comentarios**: aprovador pode adicionar comentarios (parcelas aprovadas ou nao)
- **Reversao**: marca de aprovacao pode ser retirada ENQUANTO parcela nao foi liquidada

### Liquidacao Controlada
- **Somente aprovadas**: opcao 476 (liquidacao) so permite liquidar parcelas marcadas como aprovadas
- **Bloqueio permanente**: apos liquidacao, marca de aprovacao NAO pode ser retirada

### Filtros Uteis
- **Unidade**: filtrar despesas de unidade especifica (omitir = todas)
- **Numero de Lancamento**: aprovar parcelas de despesa especifica (util para despesas grandes ou urgentes)

### Total dos Pagamentos Marcados
- Atualizado dinamicamente a cada parcela marcada
- Facilita visualizacao do impacto total de aprovacoes no periodo

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
