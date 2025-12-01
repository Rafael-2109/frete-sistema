---
name: agente-logistico
description: Analisa, consulta e CRIA separacoes no sistema de fretes. Responde perguntas sobre disponibilidade, estoque, rupturas, atrasos e prazos. CRIA separacoes via linguagem natural (completas, parciais, por pallets). Use quando o usuario perguntar sobre carteira, separacoes, estoque OU quando pedir para criar/gerar separacao de pedido.
---

# Agente Logístico - Sistema de Fretes

## Quando Usar Este Skill

### Consultas (somente leitura)
- Perguntas sobre disponibilidade de pedidos ou estoque
- Consultas sobre pedidos pendentes, atrasados ou em separacao
- Analise de rupturas, gargalos e impactos
- Projecoes de entrega e prazos
- Verificacao de bonificacoes e consolidacao de cargas
- Reprogramacao de producao para resolver rupturas

### Acoes (criacao/modificacao)
- **Criar separacao de pedido** (completa ou parcial)
- Gerar separacao com quantidade especifica de pallets
- Separar pedido excluindo determinados produtos
- Separar apenas o que tem em estoque

## Fluxo de Trabalho

### Para Consultas
1. **Identificar a intencao** do usuario (consulta, analise, simulacao)
2. **Selecionar script apropriado** com base no dominio
3. **Executar via bash** com parametros adequados
4. **Interpretar resultado** e formatar resposta clara
5. **Verificar se responde** completamente a pergunta

### Para Criacao de Separacao
1. **Identificar pedido** e validar existencia na carteira
2. **Coletar informacoes obrigatorias** (ver checklist abaixo)
3. **Validar estoque** antes de confirmar
4. **Executar criacao** via script com --executar
5. **Confirmar resultado** ao usuario

## Scripts Disponiveis (6 scripts consolidados)

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

### criando_separacao.py (ACAO)
Cria separacoes de pedidos via linguagem natural. **SEMPRE executar primeiro SEM --executar para validar.**

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido (OBRIGATORIO) | `--pedido VCD123` |
| `--expedicao` | Data de expedicao (OBRIGATORIO) | `--expedicao 2025-12-20` |
| `--tipo` | Tipo de separacao | `--tipo completa` ou `--tipo parcial` |
| `--pallets` | Quantidade de pallets desejada | `--pallets 28` |
| `--pallets-inteiros` | Forcar pallets inteiros por item | flag |
| `--excluir-produtos` | Produtos a excluir (JSON) | `--excluir-produtos '["KETCHUP","MOSTARDA"]'` |
| `--apenas-estoque` | Separar apenas o que tem em estoque | flag |
| `--agendamento` | Data de agendamento | `--agendamento 2025-12-22` |
| `--protocolo` | Protocolo de agendamento | `--protocolo AG12345` |
| `--agendamento-confirmado` | Marcar agendamento como confirmado | flag |
| `--executar` | Efetivamente criar a separacao | flag |

**Modos de operacao:**
- **Sem --executar**: Apenas SIMULA e mostra o que seria criado (SEMPRE usar primeiro!)
- **Com --executar**: Cria efetivamente a separacao no banco

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

## Fluxo Conversacional: Criacao de Separacao

### Checklist Obrigatorio (SEMPRE coletar antes de criar)

| Campo | Obrigatorio | Como Obter |
|-------|-------------|------------|
| Pedido | SIM | Usuario informa |
| Data expedicao | SIM | Usuario informa |
| Tipo (completa/parcial) | SIM | Perguntar se nao especificado |
| Agendamento | CONDICIONAL | Verificar `contatos_agendamento` pelo CNPJ |
| Protocolo | CONDICIONAL | Se exige agendamento |
| Agendamento confirmado | CONDICIONAL | Se exige agendamento |

### Verificacao de Agendamento

**ANTES de criar separacao, SEMPRE verificar:**
```
Se CNPJ existe em contatos_agendamento E forma != 'SEM AGENDAMENTO':
    -> Cliente EXIGE agendamento
    -> Solicitar: data agendamento, protocolo, confirmacao
    -> Se usuario nao informar algum, AVISAR mas permitir continuar

Se CNPJ NAO existe em contatos_agendamento OU forma = 'SEM AGENDAMENTO':
    -> Informar: "Pelo cadastro, este cliente nao precisa de agendamento"
    -> Se usuario informar mesmo assim, registrar
```

### Tipos de Separacao

| Tipo | Descricao | Parametros |
|------|-----------|------------|
| **Completa** | Todos os itens com qtd total | `--tipo completa` |
| **Parcial - itens completos** | N itens com qtd total cada | `--tipo parcial` |
| **Parcial - qtds parciais** | N itens com qtds especificas | `--tipo parcial` + JSON |
| **Por pallets** | Somar X pallets total | `--pallets N` |
| **Por pallets inteiros** | Cada item = pallets inteiros | `--pallets N --pallets-inteiros` |
| **Apenas estoque** | So o que tem disponivel | `--apenas-estoque` |
| **Excluindo produtos** | Tudo exceto lista | `--excluir-produtos '[...]'` |

### Validacao de Estoque (CRITICA)

**SEMPRE validar estoque ANTES de confirmar criacao:**

1. Executar script SEM --executar (simulacao)
2. Verificar campo `alertas_estoque` na resposta
3. Se houver alertas:
   - Mostrar ao usuario quais produtos tem falta
   - Perguntar se deseja continuar
   - Sugerir alternativas (--apenas-estoque, excluir produtos)

### Exemplos de Conversacao

**Exemplo 1: Separacao completa simples**
```
Usuario: Crie uma separacao do pedido VCD123
Agente: Para criar a separacao do pedido VCD123, preciso de algumas informacoes:
        - Data de expedicao (embarque)?
        [Verifica agendamento...] Pelo cadastro, este cliente nao precisa de agendamento.
        - Separacao completa ou parcial?

Usuario: Dia 20/12, completa
Agente: [Executa simulacao, valida estoque]
        Simulacao da separacao VCD123:
        - 5 itens, R$ 45.000
        - Estoque: OK para todos os itens
        Confirma criacao?

Usuario: Sim
Agente: [Executa com --executar]
        Separacao criada com sucesso! Lote: SEP-20251201-XXXX
```

**Exemplo 2: Separacao por pallets**
```
Usuario: Crie separacao do VCD456 com 28 pallets para dia 20/12
Agente: [Verifica agendamento...] Este cliente EXIGE agendamento (Portal).
        Preciso de:
        - Data de agendamento?
        - Protocolo?
        - Agendamento ja confirmado?

Usuario: Agendamento 22/12, protocolo AG999, confirmado
Agente: [Executa simulacao com --pallets 28]
        Simulacao VCD456 (28 pallets):
        - Produto A: 15 pallets (1.500 un)
        - Produto B: 10 pallets (800 un)
        - Produto C: 3 pallets (240 un)
        ALERTA: Produto B tem apenas 600 un em estoque (faltam 200)
        Deseja continuar com quantidade reduzida ou excluir produto?
```

**Exemplo 3: Separacao com exclusao**
```
Usuario: Pode enviar o VCD789 sem o ketchup e a mostarda dia 15/12
Agente: [Executa simulacao com --excluir-produtos]
        Separacao VCD789 (excluindo Ketchup e Mostarda):
        - 8 itens restantes, R$ 32.000
        Confirma?
```

### Mensagens Padrao

| Situacao | Mensagem |
|----------|----------|
| Cliente sem agendamento | "Pelo cadastro, este cliente nao precisa de agendamento" |
| Cliente com agendamento | "Este cliente EXIGE agendamento via [forma]. Preciso de: data, protocolo, confirmacao" |
| Falta de estoque | "ALERTA: [produto] tem apenas [qtd] em estoque (precisa [qtd]). Deseja continuar?" |
| Simulacao OK | "Simulacao concluida. [N] itens, R$ [valor]. Confirma criacao?" |
| Criacao OK | "Separacao criada com sucesso! Lote: [lote_id]" |

## Referencias

- [QUERIES.md](reference/QUERIES.md) - Mapeamento detalhado das 20 queries
- [MODELOS_CAMPOS.md](../../references/MODELOS_CAMPOS.md) - Esquema completo das tabelas do banco
- [REGRAS_NEGOCIO.md](../../references/REGRAS_NEGOCIO.md) - Regras de negocio detalhadas

> **NOTA**: Os arquivos TABELAS.md e REGRAS_NEGOCIO.md foram consolidados em `.claude/references/`
> para evitar duplicacao com o CLAUDE.md principal.
