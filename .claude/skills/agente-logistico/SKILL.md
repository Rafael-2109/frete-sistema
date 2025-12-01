---
name: agente-logistico
description: Analisa e consulta dados do sistema de fretes. Responde perguntas sobre disponibilidade de pedidos, estoque, rupturas, atrasos, prazos de entrega e programacao de producao. Use quando o usuario perguntar sobre carteira de pedidos, separacoes, projecoes de estoque ou prazos de entrega.
---

# Agente Logístico - Sistema de Fretes

## Quando Usar Este Skill

- Perguntas sobre disponibilidade de pedidos ou estoque
- Consultas sobre pedidos pendentes, atrasados ou em separacao
- Analise de rupturas, gargalos e impactos
- Projecoes de entrega e prazos
- Verificacao de bonificacoes e consolidacao de cargas
- Reprogramacao de producao para resolver rupturas

## Fluxo de Trabalho

1. **Identificar a intencao** do usuario (consulta, analise, simulacao)
2. **Selecionar script apropriado** com base no dominio
3. **Executar via bash** com parametros adequados
4. **Interpretar resultado** e formatar resposta clara
5. **Verificar se responde** completamente a pergunta

## Scripts Disponiveis (5 scripts consolidados)

### analisando_disponibilidade.py (9 queries)
Analisa disponibilidade de estoque para pedidos ou grupos de clientes.

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido | `--pedido VCD123` |
| `--grupo` | Grupo empresarial | `--grupo atacadao` |
| `--loja` | Identificador da loja (em raz_social_red) | `--loja 183` |
| `--uf` | Filtrar por UF | `--uf SP` |
| `--data` | Data alvo (padrao: hoje) | `--data amanha` |
| `--sem-agendamento` | Apenas pedidos sem exigencia de agendamento | flag |
| `--sugerir-adiamento` | Identificar pedidos competidores para adiar | flag |
| `--diagnosticar-origem` | Distinguir falta absoluta vs relativa | flag |
| `--completude` | Mostrar % faturado vs pendente | flag |
| `--atrasados` | Analisar apenas pedidos com expedicao vencida | flag |
| `--diagnosticar-causa` | Detalhar causa do atraso (falta ou outro) | flag |
| `--ranking-impacto` | Rankear pedidos que mais travam carteira | flag |

**Queries cobertas:** Q1, Q2, Q3, Q4, Q5, Q6, Q9, Q11, Q12

### consultando_pedidos.py (5 queries)
Consulta pedidos por diversos filtros e perspectivas.

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido | `--pedido VCD123` |
| `--grupo` | Grupo empresarial | `--grupo assai` |
| `--atrasados` | Apenas pedidos com expedicao < hoje | flag |
| `--verificar-bonificacao` | Verificar se venda+bonif estao juntos | flag |
| `--consolidar-com` | Buscar pedidos proximos para consolidar | `--consolidar-com "assai 123"` |
| `--status` | Detalhar status (separado, parcial, pendente) | flag |
| `--limit` | Limite de resultados | `--limit 20` |

**Queries cobertas:** Q8, Q10, Q14, Q16, Q19

### consultando_estoque.py (4 queries)
Consulta estoque atual, movimentacoes, pendencias e projecoes.

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou termo do produto | `--produto palmito` |
| `--entradas` | Mostrar entradas recentes (qtd > 0) | flag |
| `--saidas` | Mostrar saidas recentes (qtd < 0) | flag |
| `--pendente` | Quantidade pendente + lista de pedidos | flag |
| `--sobra` | Calcular sobra apos atender demanda | flag |
| `--ruptura` | Previsao de rupturas | flag |
| `--dias` | Horizonte de projecao (padrao: 7) | `--dias 14` |

**Queries cobertas:** Q13, Q17, Q18, Q20

### calculando_prazo.py (1 query)
Calcula data de entrega baseada em lead time de transportadoras.

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido | `--pedido VCD123` |
| `--data-embarque` | Data de embarque | `--data-embarque amanha` |
| `--limit` | Limite de opcoes de transportadora | `--limit 5` |

**Queries cobertas:** Q7

### analisando_programacao.py (1 query)
Simula reprogramacao de producao para resolver rupturas.

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou termo do produto | `--produto "VF pouch 150"` |
| `--linha` | Linha de producao especifica | `--linha 3` |

**Queries cobertas:** Q15

## Como Executar

```bash
source /home/rafaelnascimento/projetos/frete_sistema/venv/bin/activate && \
python /home/rafaelnascimento/projetos/frete_sistema/.claude/skills/agente-logistico/scripts/NOME_SCRIPT.py [parametros]
```

## Regras de Interpretacao

### Grupos Empresariais
| Nome | Prefixos CNPJ |
|------|---------------|
| Atacadao | 93209765, 75315333, 00063960 |
| Assai | 06057223 |
| Tenda | 01157555 |

### Termos do Dominio
- **Matar pedido** = Completar 100% do pedido
- **Ruptura** = Falta de estoque para atender demanda
- **Separacao** = Pedido reservado para envio (sincronizado_nf=False)
- **Pendente** = Na carteira mas nao separado
- **Bonificacao** = forma_pgto_pedido LIKE 'Sem Pagamento%'
- **Falta absoluta** = Estoque < demanda (mesmo sem outros pedidos)
- **Falta relativa** = Estoque comprometido com outros pedidos

### Calculos Chave
- **Estoque disponivel** = MovimentacaoEstoque - Separacao(sincronizado_nf=False)
- **Valor pendente** = qtd_saldo * preco (do pedido)
- **Completude** = 1 - (valor_pendente / valor_original)

### Resolucao de Produtos
Usuarios podem usar termos abreviados:
- AZ = Azeitona | PF = Preta Fatiada | VF = Verde Fatiada
- BD = Balde | IND = Industrial | POUCH = Pouch
- Exemplo: "pf mezzani" = Azeitona Preta Fatiada Mezzani

## Nivel de Detalhes (Progressive Disclosure)

Os scripts retornam dados completos. Claude decide o que mostrar:

1. **Resposta inicial**: Resumo com 3-5 itens principais
2. **Se usuario pedir mais**: Mostrar mais itens do mesmo JSON (sem re-executar)
3. **Se usuario pedir "todos"**: Mostrar lista completa

Exemplos de pedidos para expandir:
- "me mostre todos os pedidos"
- "quero ver a lista completa"
- "detalhe mais"
- "tem mais?"

## Formato de Resposta

Sempre incluir:
1. **Resposta direta** a pergunta (sim/nao, data, quantidade)
2. **Dados quantitativos** relevantes (valores, %, quantidades)
3. **Lista de itens** quando aplicavel (pedidos, produtos) - iniciar com 3-5, expandir se pedido
4. **Sugestao de acao** quando pertinente

## Referencias

- [QUERIES.md](reference/QUERIES.md) - Mapeamento detalhado das 20 queries
- [TABELAS.md](TABELAS.md) - Esquema das tabelas do banco
- [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) - Regras de negocio especificas
