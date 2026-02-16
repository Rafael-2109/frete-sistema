# 06 — Informacoes Gerenciais (Opcao 056)

> **Fonte**: `ssw0082.htm` (10/03/2025)
> **Links internos**: 98 | **Imagens**: 4

## Sumario

[Opcao 056](../relatorios/056-informacoes-gerenciais.md) — "Dirigindo a transportadora (para dar LUCRO)". Dezenas de relatorios diarios agrupados em 6 objetivos. E o painel central de gestao do SSW.

---

## Conceitos

- **6 Objetivos** medidos diariamente, todos direcionados ao principio "TEM QUE DAR LUCRO"
- **Mobilizacao para corrigir**: diretores e gerentes devem avaliar e implementar acoes corretivas
- **Sem perfumaria**: nao precisa BI, grafico ou planilha — tudo pronto na [opção 056](../relatorios/056-informacoes-gerenciais.md)
- **Processamento**: diario (alguns de hora em hora), disponiveis por ate 1 ano
- **Visibilidade**: cada usuario ve sua unidade; MTZ ve todas com resumos
- **Liberacao**: por grupo de usuario (opção 902, opção 300)

---

## Navegacao da Tela

| Elemento | Descricao |
|----------|-----------|
| Gerados hoje (1) | Relatorios do dia (vermelho = vitais) |
| Ultimos 7 dias (2) | Historico recente |
| Filtros (3) | Por codigo ou por data |
| Abrir relatorio (4) | Clique na linha |
| Periodo (5) | Mensais acumulam ate ontem, disponivel ano vigente + anterior |
| Excel (1) | Converte em Excel |
| Localizar (2) | Busca texto no relatorio |
| Ajuda (3) | Dicas de uso nos vitais (vermelho) |

---

## A. Os 6 Objetivos

### Objetivo 1 — Transportadora tem que dar LUCRO

| Relatorio | Descricao | Frequencia |
|-----------|-----------|------------|
| **001** | SITUACAO GERAL — entradas vs saidas, 3 meses + vigente + 3 dias | Diario |
| 075 | Monitoracao de clientes por unidade (volume mes vs anterior) | Diario |
| 050/052 | Volumes expedidos (diario/mensal) por cliente | Diario/Mensal |
| 054/056 | Volumes recebidos (diario/mensal) por cliente | Diario/Mensal |
| 058/059 | Volumes expedidos e recebidos por cidade/setor | Diario/Mensal |
| 060/061 | Volumes de cargas transbordadas | Diario/Mensal |
| 069 | Maiores clientes — Excel | Dias 01 e 10 |
| **070** | Maiores clientes — classificacao ABC, indicador REAJNE | Dias 01 e 10 |
| 100 | Situacao do caixa — fluxo 15 dias futuros | Diario |
| 150/152 | Volumes pagadores vs nao-pagadores | Diario/Mensal |
| 151/153 | Volumes dos pagadores analitico | Diario/Mensal |

### Objetivo 2 — Entregas no Prazo

| Relatorio | Descricao | Frequencia |
|-----------|-----------|------------|
| **010/011/013** | CTRCs ATRASADOS DE ENTREGA (mais importante para cliente) | Diario |
| 088 | Performance coletas/entregas (7 dias e 30 dias) | Diario |
| 080 | Saidas/chegadas de veiculos vs horarios limites ([opção 403](../cadastros/403-rotas.md)) | Diario |
| 164 | Tempo de transbordo por unidade | Diario |
| 012 | Performance CTRCs entregues (dias antes/apos previsao) | Diario |
| 087 | Ocorrencias dadas fora do cliente (SSWMobile vs nao) | Diario |
| 084 | Performance entregas por cidade destino | Dias 01 e 10 |
| 083 | Performance entregas por cliente emitente | Dias 01 e 10 |
| 081 | Performance entrega unidade destinataria (sem transferencia) | Diario |

### Objetivo 3 — CTRC/Cliente tem que dar LUCRO

| Relatorio | Descricao | Frequencia |
|-----------|-----------|------------|
| **030/031** | CTRCs COM PREJUIZO — Resultado Comercial Minimo e Desconto NTC | Diario |
| — | Situacao do cliente ([opção 102](../comercial/102-consulta-ctrc.md)/Geral e Producao Mensal 24 meses) | Sob demanda |
| — | Resultado por cliente (opção 449) — por rota e peso | Sob demanda |
| 032 | Verificacao frete calculado pelo cliente (EDI) | Diario |
| 130 | Taxas adicionais nao cobradas | Diario |

### Objetivo 4 — Caminhao tem que dar LUCRO

| Relatorio | Descricao | Frequencia |
|-----------|-----------|------------|
| **020/023** | Resultado de viagens (frete manifestos vs custo CTRB) | Diario |
| 021 | Resultado transferencias realizadas (mensal por veiculo/motorista/rota) | Dia 01 |
| 023 | Resultado coletas/entregas por unidade | Diario |
| 022 | Resultado coletas/entregas realizadas (mensal) | Dia 01 |

### Objetivo 5 — Unidade tem que dar LUCRO

| Relatorio | Descricao | Frequencia |
|-----------|-----------|------------|
| **168** | Resultado da unidade (receita servicos [opção 408](../comercial/408-comissao-unidades.md) vs despesas [opção 475](../financeiro/475-contas-a-pagar.md)) | Diario |
| 166 | Resultado comercial por cliente na unidade (CTRCs emitidos ontem) | Diario |
| 167 | Resultado comercial por unidade (CTRCs ontem + acumulado mes) | Diario |

### Objetivo 6 — Inadimplencia nao e LUCRO

| Relatorio | Descricao | Frequencia |
|-----------|-----------|------------|
| **040** | Faturas vencidas — processado as 09:30h | Diario |
| 157 | Emails enviados — envio de faturas | Diario |
| 154 | Fatura por email nao impressa (< 4 dias do vencimento) | Diario |
| 156 | Emails enviados — atraso de liquidacao | Diario |
| 041 | Frete a vista nao liquidado (CIF/FOB) | Diario |
| 155 | Emails enviados automaticamente ([opção 100](../comercial/100-geracao-emails-clientes.md)) | Diario |

---

## B. Relatorios Comerciais

### Monitoracao de Clientes
| Relatorio | Descricao |
|-----------|-----------|
| 075 | Por unidade — volume mes vs mesmo periodo anterior + por vendedor |
| 073 | Ref mes anterior — toda transportadora + por vendedor (uso da matriz) |

### Producao de Vendedores
| Relatorio | Descricao |
|-----------|-----------|
| 125 | Producao por vendedor (mensal, por cliente, com ALVO e METAS) — unidades |
| 126 | Producao por vendedor — resumo para matriz |

### Comissionamento de Vendedores
| Relatorio | Escopo | Descricao |
|-----------|--------|-----------|
| 120 | Unidades | Mapa analitico (por CTRC) |
| 121 | Unidades | Mapa em Excel |
| 127 | Unidades | Previsao (PROX COM + PREV COM) |
| 123 | Unidades | Clientes sem movimentacao por vendedor |
| 124 | Matriz | Mapa resumo por cliente — usado para pagamento |
| 128 | Matriz | Previsao sintetico por vendedor |

### Comissionamento de Cotacao
| Relatorio | Descricao |
|-----------|-----------|
| 131 | Mapa analitico — unidades |
| 132 | Resumo — matriz |

---

## C. Outros Relatorios

| Relatorio | Descricao |
|-----------|-----------|
| 110 | Comissao de agenciamento ([opção 408](../comercial/408-comissao-unidades.md)) — unidades |
| 111 | Comissao de agenciamento — previsao |
| 112 | Comissao de agenciamento — resumo |
| 165 | Conferencia de averbacao |
| 090 | Divergencias unidades cadastro de clientes |
| 074 | Clientes PJ nao contribuintes (IE ISENTO → aliquota interna) |

---

## Relatorios VITAIS (linha vermelha)

1. **001** — Situacao Geral
2. **010/011/013** — CTRCs Atrasados de Entrega
3. **030/031** — CTRCs com Prejuizo
4. **020** — Resultado de Viagens
5. **168** — Resultado da Unidade
6. **040** — Faturas Vencidas

---

## Contexto CarVia

### Opcoes que CarVia usa
*Nenhuma — CarVia nao utiliza relatorios gerenciais do SSW.*

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| [056](../relatorios/056-informacoes-gerenciais.md) | Central de relatorios gerenciais (6 objetivos, dezenas de relatorios diarios) | Falta de visibilidade sobre performance operacional — sem acompanhamento diario de lucratividade, entregas, inadimplencia |

### Status de Implantacao
- **B05**: NAO IMPLANTADO — nunca acessou opcao 056

### Responsaveis
- **Atual**: Ninguem (modulo nao implantado)
- **Futuro**: Rafael/Jessica (plano de implantacao de relatorios gerenciais)
