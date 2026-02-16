# Opção 558 — Lançamentos Manuais

> **Módulo**: Contabilidade
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Realiza lançamentos manuais na Contabilidade, complementando os lançamentos automáticos. Os lançamentos são organizados em lotes cujo total de créditos deve ser igual ao total de débitos.

## Quando Usar
- Lançamentos que não são gerados automaticamente pelo sistema
- Ajustes contábeis manuais
- Reclassificações de contas
- Provisões, depreciações e outros lançamentos gerenciais

## Pré-requisitos
- Plano de Contas configurado (opção 540)
- Históricos padrões cadastrados (opção 557) — opcional, mas recomendado
- Período contábil aberto (opção 559)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Data do Lançamento | Sim | Data contábil para os lançamentos do lote (formato dd/mm/aaaa) |
| Lote | Auto | Numerado automaticamente pelo SSW (em caso de continuação) |

### Tela de Lançamento
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Documento | Sim | Número do documento que justifica o lançamento |
| Conta | Sim | Conta do Plano de Contas (opção 540) |
| Complemento | Condicional | Conforme definido no Plano de Contas (banco, unidade, CNPJ, etc.) |
| Valor | Sim | Valor do lançamento |
| D/C | Sim | Débito ou Crédito |
| Histórico Padrão | Não | Código de histórico padrão (opção 557) |
| Histórico | Sim | Descrição do lançamento (pode ser preenchido pelo Histórico Padrão) |
| Contrapartida - Conta | Não | Conta de contrapartida (opcional) |
| Contrapartida - Complemento | Condicional | Complemento da conta de contrapartida |

## Fluxo de Uso

### Lançamento Manual via Interface
1. Acessar opção 558
2. Clicar em "LANÇAR COM DATA" e informar data contábil
3. Preencher documento, conta, complemento, valor, D/C e histórico
4. Opcionalmente preencher contrapartida
5. Clicar em "INCLUIR LANÇAMENTO"
6. Repetir para todos os lançamentos do lote
7. Verificar que total de débitos = total de créditos
8. Clicar em "CONCLUIR LOTE" para efetivar na Contabilidade

### Importação via Arquivo CSV
1. Preparar arquivo CSV conforme layout especificado
2. Acessar opção 558
3. Clicar em "ARQUIVO" e selecionar CSV
4. Sistema importa e cria lote automaticamente
5. Verificar lançamentos importados
6. Concluir lote

### Continuação de Lote Interrompido
1. Acessar opção 558
2. Clicar em "CONTINUAR LOTE"
3. Selecionar lote na parte inferior da tela
4. Adicionar lançamentos faltantes
5. Concluir lote

### Reabertura de Lote
1. Acessar opção 558
2. Clicar em "ABRIR LOTE"
3. Informar número do lote finalizado
4. Realizar ajustes necessários
5. Concluir lote novamente

## Layout CSV para Importação

| Coluna | Campo | Formato | Descrição |
|--------|-------|---------|-----------|
| A | Data | dd/mm/aaaa | Data do lançamento (período aberto na opção 559) |
| B | Documento | Texto | Número do documento |
| C | Conta | Sem espaços/pontos | Código da conta no Plano de Contas |
| D | Complemento | Sem espaços/pontos | CNPJ, banco, unidade, etc. |
| E | Valor | Numérico | Valor do lançamento |
| F | D/C | D ou C | Débito ou Crédito |
| G | Histórico | Texto | Descrição do lançamento |

### Exemplo CSV
```
15/01/2026,1001,1110101,,5000.00,D,Abertura de caixa
15/01/2026,1001,3110101,,5000.00,C,Abertura de caixa
```

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 540 | Plano de Contas — estrutura de contas utilizada nos lançamentos |
| 557 | Histórico Padrão — históricos reutilizáveis para lançamentos |
| 559 | Saldo das Contas / Fechamento — período deve estar aberto para lançar |
| 541 | Lançamentos Automáticos — complementa os lançamentos manuais |
| 543 | Consulta de Lançamentos — visualização dos lançamentos efetuados |
| 548 | Livro Razão — relatório contábil com lançamentos manuais e automáticos |

## Observações e Gotchas
- **Lote completo obrigatório**: Apenas lotes com total de débitos = total de créditos são efetivados
- **Lançamentos incompletos não contabilizam**: Lote aberto ou com diferença entre débitos/créditos não gera saldo nas contas
- **Data do lançamento**: Todas as linhas do lote devem ter a mesma data contábil
- **Contrapartida com mesma data**: Lançamento e contrapartida devem possuir a mesma data
- **Período fechado**: Não é possível lançar em período fechado na opção 559
- **Complemento banco**: Deve ter 18 dígitos (3 banco + 5 agência + 10 conta corrente)
- **CSV sem espaços/pontos**: Conta e complemento devem ser informados sem formatação
- **Alteração de data do lote**: Link "ALTERAR DATA DO LOTE" muda todas as datas dos lançamentos do lote
- **Exclusão de lote vazio**: Link "EXCLUIR LOTE VAZIO" remove lote sem lançamentos
- **Usuário responsável**: Lançamentos manuais registram usuário que criou; lançamentos automáticos aparecem como "SISTEMA"

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
