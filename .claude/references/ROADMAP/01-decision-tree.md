# 01 - Decision Tree

**Status**: ✅ CONCLUIDO (12/12/2025)
**Prioridade**: CRITICO
**Responsavel**: Claude + Rafael
**Arquivo alvo**: `.claude/skills/gerindo-expedicao/SKILL.md`

---

## Problema

A skill tem 7 scripts e 55+ parametros, mas **nenhum guia de decisao** sobre qual usar.

**Exemplo real da falha:**
```
Pergunta Stephanie: "quantas caixas de ketchup tem pendentes pro atacadao 183"

Scripts possiveis:
1. consultando_situacao_pedidos.py --grupo atacadao --produto ketchup
2. analisando_disponibilidade_estoque.py --grupo atacadao --loja 183
3. consultando_produtos_estoque.py --produto ketchup --pendente

Resultado: Agente escolheu script errado (mostrou catalogo em vez de carteira)
```

---

## Solucao

Adicionar secao "Decision Tree" no SKILL.md (apos linha 26, antes de "Scripts Disponiveis").

---

## Conteudo Proposto

```markdown
---

## DECISAO: Qual Script Usar?

**SEMPRE consulte esta tabela ANTES de executar qualquer script.**

### Mapeamento Rapido

| Tipo de Pergunta | Palavras-chave | Script | Parametros |
|------------------|----------------|--------|------------|
| Quantidade pendente de produto para cliente | "quantas", "pendente", produto + cliente/grupo | `consultando_situacao_pedidos.py` | `--grupo X --produto Y` |
| Pedidos de um cliente/grupo | "tem pedido", "pedidos do" | `consultando_situacao_pedidos.py` | `--grupo X` |
| Quando pedido fica disponivel | "quando", "disponivel", pedido | `analisando_disponibilidade_estoque.py` | `--pedido X` |
| Disponibilidade para grupo | "disponivel", "completude", grupo | `analisando_disponibilidade_estoque.py` | `--grupo X --completude` |
| Estoque de produto | "quanto tem", "estoque", produto | `consultando_produtos_estoque.py` | `--produto X --completo` |
| Entradas recentes | "chegou", "entrou", produto | `consultando_produtos_estoque.py` | `--produto X --entradas` |
| Previsao de falta | "vai faltar", "ruptura" | `consultando_produtos_estoque.py` | `--ruptura --dias 7` |
| Prazo de entrega | "quando chega", "lead time" | `calculando_leadtime_entrega.py` | `--pedido X --data-embarque Y` |
| Criar separacao | "crie separacao", "separe" | `criando_separacao_pedidos.py` | `--pedido X --expedicao Y` |
| Programacao producao | "programacao", "producao" | `consultando_programacao_producao.py` | `--listar` |

### Regras de Decisao

1. **Se pergunta tem PRODUTO + CLIENTE/GRUPO**: Use `consultando_situacao_pedidos.py`
2. **Se pergunta e so sobre PRODUTO (estoque)**: Use `consultando_produtos_estoque.py`
3. **Se pergunta e sobre DISPONIBILIDADE de pedido**: Use `analisando_disponibilidade_estoque.py`
4. **Se pergunta e sobre PRAZO**: Use `calculando_leadtime_entrega.py`
5. **Se for ACAO (criar/separar)**: Use `criando_separacao_pedidos.py`

---
```

---

## Tarefas

- [ ] Rafael confirmar mapeamentos da tabela
- [ ] Claude inserir conteudo no SKILL.md
- [ ] Testar com perguntas reais

---

## GAPS IDENTIFICADOS - Funcionalidades Faltantes

### Respostas do Rafael (12/12/2025):

| Gap | Descricao | Status |
|-----|-----------|--------|
| GAP-01 | Nao existe `--cliente` (CNPJ ou razao social) nos scripts | ✅ **RESOLVIDO** (12/12/2025) |
| GAP-02 | Nao existe combinacao `--produto` + `--grupo` funcional | ✅ **RESOLVIDO** (12/12/2025) |
| GAP-03 | Nao existe combinacao `--produto` + `--cliente` | ✅ **RESOLVIDO** (12/12/2025) |

### Parametros Existentes vs Necessarios:

**consultando_situacao_pedidos.py:**
```
EXISTE:   --pedido, --grupo, --cliente, --produto, --atrasados, --status, --em-separacao, --ate-data
NOVOS:    --cliente (CNPJ ou razao social) ✅
          --grupo + --produto (combinacao funcional) ✅
          --cliente + --produto (combinacao funcional) ✅
```

**analisando_disponibilidade_estoque.py:**
```
EXISTE:   --pedido, --grupo, --loja, --uf, --completude, --ranking-impacto
FALTA:    --cliente, --produto (para filtrar disponibilidade por produto)
```

---

## RESPOSTAS DO RAFAEL - Mapeamentos Confirmados

| Pergunta | Status | Observacao |
|----------|--------|------------|
| "quantas X tem pendentes pro Y" | **GAP** | Precisa criar --cliente e combinacao produto+cliente/grupo |
| "tem pedido do X?" | **PARCIAL** | So funciona para GRUPO, nao para cliente especifico |
| "quando fica disponivel?" | **AMBIGUO** | Precisa perguntar: pedido ou produto? |
| "quanto tem de X?" | **OK** | `--produto X --completo` |
| "chegou X?" | **OK** | `--produto X --entradas` |
| "o que vai dar falta?" | **OK** | `--ruptura --dias 7` |

### Decisoes Confirmadas:

| Situacao | Decisao |
|----------|---------|
| "pedidos do Atacadao" (sem loja) | Mostrar TODAS as lojas |
| "produto + cliente" (sem especificar carteira/separacao) | Mostrar AMBOS |

---

## PERGUNTAS EXPANDIDAS - Casos Complexos

### Categoria: PEDIDOS (30 casos)

| # | Pergunta do Usuario | Script | Status |
|---|---------------------|--------|--------|
| P01 | "tem pedido do atacadao?" | `consultando_situacao_pedidos.py --grupo atacadao` | OK |
| P02 | "tem pedido do atacadao 183?" | `analisando_disponibilidade_estoque.py --grupo atacadao --loja 183` | OK |
| P03 | "tem pedido do Carrefour?" | **GAP** - Nao existe --cliente | CRIAR |
| P04 | "tem pedido do CNPJ 12345678000199?" | **GAP** - Nao existe --cnpj | CRIAR |
| P05 | "pedido VCD123 esta em separacao?" | `consultando_situacao_pedidos.py --pedido VCD123 --em-separacao` | OK |
| P06 | "qual o status do pedido VCD123?" | `consultando_situacao_pedidos.py --pedido VCD123 --status` | OK |
| P07 | "quantos pedidos do assai tem atrasados?" | `consultando_situacao_pedidos.py --grupo assai --atrasados` | OK |
| P08 | "pedidos atrasados" | `consultando_situacao_pedidos.py --atrasados` | OK |
| P09 | "pedidos que vao embarcar amanha" | `consultando_situacao_pedidos.py --ate-data amanha` | OK |
| P10 | "pedidos do Tenda pra embarcar essa semana" | `consultando_situacao_pedidos.py --grupo tenda --ate-data [sexta]` | OK |
| P11 | "pedidos com bonificacao faltando" | `consultando_situacao_pedidos.py --verificar-bonificacao` | OK |
| P12 | "pedidos pra consolidar com o assai 123" | `consultando_situacao_pedidos.py --consolidar-com "assai 123"` | OK |
| P13 | "pedidos com palmito" | `consultando_situacao_pedidos.py --produto palmito` | OK |
| P14 | "pedidos com azeitona verde pra amanha" | `consultando_situacao_pedidos.py --produto "az verde" --ate-data amanha` | OK |
| P15 | "pedidos do atacadao com ketchup" | **GAP** - --grupo + --produto nao filtra corretamente | VERIFICAR |
| P16 | "pedidos do [cliente nao-grupo] com palmito" | **GAP** - Nao existe --cliente | CRIAR |
| P17 | "VCD123" (so o numero) | `consultando_situacao_pedidos.py --pedido VCD123 --status` | OK |
| P18 | "2564291" (numero parcial) | `consultando_situacao_pedidos.py --pedido 2564291 --status` | OK |
| P19 | "pedidos em separacao do assai" | `consultando_situacao_pedidos.py --grupo assai --em-separacao` | OK? |
| P20 | "todos os pedidos" | `consultando_situacao_pedidos.py` (sem filtro) | OK |

### Categoria: PRODUTO + CLIENTE/GRUPO (15 casos - MAIORIA GAPS)

| # | Pergunta do Usuario | Status | Observacao |
|---|---------------------|--------|------------|
| PC01 | "quantas caixas de ketchup tem pro atacadao 183?" | **GAP** | Produto + grupo + loja |
| PC02 | "quanto de palmito tem pendente pro assai SP?" | **GAP** | Produto + grupo + UF |
| PC03 | "quanto de azeitona verde tem pro tenda?" | **GAP** | Produto + grupo |
| PC04 | "quais produtos o Carrefour comprou?" | **GAP** | Lista produtos de cliente |
| PC05 | "azeitona verde do atacadao - quanto falta separar?" | **GAP** | Produto + grupo + status separacao |
| PC06 | "cogumelo fatiado pro tenda - quando chega?" | **GAP** | Produto + grupo + disponibilidade |
| PC07 | "ketchup pendente por cliente" | **GAP** | Produto agrupado por cliente |
| PC08 | "palmito - quem comprou?" | **GAP** | Produto -> lista clientes |
| PC09 | "atacadao 183 - quais produtos tem pendente?" | **GAP** | Cliente -> lista produtos |
| PC10 | "assai SP - o que falta pra completar?" | `analisando_disponibilidade_estoque.py --grupo assai --uf SP --completude` | OK |
| PC11 | "quanto de pessego o tenda pegou esse mes?" | **GAP** | Produto + grupo + periodo |
| PC12 | "compare ketchup: atacadao vs assai" | **GAP** | Produto comparativo entre grupos |
| PC13 | "ranking de clientes por palmito" | **GAP** | Produto -> ranking clientes |
| PC14 | "top 5 produtos do atacadao" | **GAP** | Grupo -> ranking produtos |
| PC15 | "CNPJ 12345 - pedidos com azeitona" | **GAP** | CNPJ + produto |

### Categoria: ESTOQUE (15 casos)

| # | Pergunta do Usuario | Script | Status |
|---|---------------------|--------|--------|
| E01 | "quanto tem de palmito?" | `consultando_produtos_estoque.py --produto palmito --completo` | OK |
| E02 | "quanto tem de palmito inteiro 300g?" | `consultando_produtos_estoque.py --produto "palmito inteiro 300" --completo` | OK |
| E03 | "chegou cogumelo?" | `consultando_produtos_estoque.py --produto cogumelo --entradas` | OK |
| E04 | "chegou alguma coisa hoje?" | `consultando_produtos_estoque.py --entradas` (sem --produto) | OK? |
| E05 | "vai faltar azeitona?" | `consultando_produtos_estoque.py --produto azeitona --ruptura` | OK |
| E06 | "o que vai dar ruptura?" | `consultando_produtos_estoque.py --ruptura --dias 7` | OK |
| E07 | "quanto de pessego entrou essa semana?" | `consultando_produtos_estoque.py --produto pessego --entradas` | OK |
| E08 | "estoque de azeitona preta fatiada" | `consultando_produtos_estoque.py --produto "pf" --completo` | OK |
| E09 | "situacao do palmito" | `consultando_produtos_estoque.py --produto palmito --completo` | OK |
| E10 | "ruptura nos proximos 14 dias" | `consultando_produtos_estoque.py --ruptura --dias 14` | OK |
| E11 | "estoque de todos os ketchups" | `consultando_produtos_estoque.py --produto ketchup --completo` | OK |
| E12 | "sobra de azeitona" | `consultando_produtos_estoque.py --produto azeitona --sobra` | OK |
| E13 | "movimentacao de palmito" | `consultando_produtos_estoque.py --produto palmito --entradas --saidas` | OK? |
| E14 | "BD IND" | `consultando_produtos_estoque.py --produto "bd ind" --completo` | OK |
| E15 | "pouch 150g" | `consultando_produtos_estoque.py --produto "pouch 150" --completo` | OK |

### Categoria: DISPONIBILIDADE (12 casos)

| # | Pergunta do Usuario | Script | Status |
|---|---------------------|--------|--------|
| D01 | "quando o pedido VCD123 fica disponivel?" | `analisando_disponibilidade_estoque.py --pedido VCD123` | OK |
| D02 | "quando o atacadao 183 fica completo?" | `analisando_disponibilidade_estoque.py --grupo atacadao --loja 183 --completude` | OK |
| D03 | "quando fica disponivel?" | **AMBIGUO** - Perguntar: pedido ou produto? | PERGUNTAR |
| D04 | "disponibilidade do assai SP" | `analisando_disponibilidade_estoque.py --grupo assai --uf SP` | OK |
| D05 | "pedidos que dao pra embarcar amanha" | `analisando_disponibilidade_estoque.py --data amanha` | OK |
| D06 | "o que trava a carteira?" | `analisando_disponibilidade_estoque.py --ranking-impacto` | OK |
| D07 | "quais pedidos posso adiar?" | `analisando_disponibilidade_estoque.py --sugerir-adiamento` | OK |
| D08 | "diagnosticar falta do VCD123" | `analisando_disponibilidade_estoque.py --pedido VCD123 --diagnosticar-origem` | OK |
| D09 | "pedidos sem agendamento pra amanha" | `analisando_disponibilidade_estoque.py --data amanha --sem-agendamento` | OK |
| D10 | "pedidos atrasados - por que?" | `analisando_disponibilidade_estoque.py --atrasados --diagnosticar-causa` | OK |
| D11 | "completude do tenda" | `analisando_disponibilidade_estoque.py --grupo tenda --completude` | OK |
| D12 | "o que falta pro VCD123?" | `analisando_disponibilidade_estoque.py --pedido VCD123` | OK |

### Categoria: PRAZOS E ENTREGAS (10 casos)

| # | Pergunta do Usuario | Script | Status |
|---|---------------------|--------|--------|
| L01 | "se embarcar o VCD123 amanha, quando chega?" | `calculando_leadtime_entrega.py --pedido VCD123 --data-embarque amanha` | OK |
| L02 | "pra chegar dia 25/12, quando embarcar?" | `calculando_leadtime_entrega.py --pedido X --data-entrega 25/12` | OK |
| L03 | "lead time pra Sao Paulo" | `calculando_leadtime_entrega.py --cidade "Sao Paulo" --uf SP --data-embarque hoje` | OK |
| L04 | "quanto tempo demora pro atacadao 183?" | Via pedido ou resolver loja->cidade | OK |
| L05 | "previsao de entrega do VCD123" | `calculando_leadtime_entrega.py --pedido VCD123 --data-embarque [data_exp]` | OK |
| L06 | "quando chega em Curitiba?" | `calculando_leadtime_entrega.py --cidade Curitiba --uf PR --data-embarque hoje` | OK |
| L07 | "lead time SC" | `calculando_leadtime_entrega.py --uf SC --data-embarque hoje` | OK? |
| L08 | "D+3 onde chega?" | Inverter: calcular destinos por lead time | **GAP?** | desnecessario
| L09 | "embarque hoje - quando chega no assai 123?" | `calculando_leadtime_entrega.py --pedido [assai123] --data-embarque hoje` | OK |
| L10 | "data de entrega do pedido VCD123" | Se tem data_entrega_pedido, mostrar; senao calcular | OK |

### Categoria: SEPARACAO (12 casos)

| # | Pergunta do Usuario | Script | Status |
|---|---------------------|--------|--------|
| S01 | "crie separacao do VCD123 pra amanha" | `criando_separacao_pedidos.py --pedido VCD123 --expedicao amanha` (SIMULAR) | OK |
| S02 | "separe 28 pallets do VCD123" | `criando_separacao_pedidos.py --pedido VCD123 --expedicao [data] --pallets 28` | OK |
| S03 | "separe apenas o que tem estoque do VCD123" | `criando_separacao_pedidos.py --pedido VCD123 --expedicao [data] --apenas-estoque` | OK |
| S04 | "separe tudo do assai menos ketchup" | `criando_separacao_pedidos.py --pedido [assai] --excluir-produtos '["KETCHUP"]'` | OK |
| S05 | "ja tem separacao do VCD123?" | `consultando_situacao_pedidos.py --pedido VCD123 --em-separacao` | OK |
| S06 | "simule separacao do VCD123" | `criando_separacao_pedidos.py --pedido VCD123 --expedicao [data]` (sem --executar) | OK |
| S07 | "separe pallets inteiros do VCD123" | `criando_separacao_pedidos.py --pedido VCD123 --pallets-inteiros` | OK |
| S08 | "agende separacao do VCD123 pra 20/12" | `criando_separacao_pedidos.py --pedido VCD123 --expedicao [data] --agendamento 20/12` | OK |
| S09 | "confirme agendamento protocolo AG12345" | `criando_separacao_pedidos.py --pedido X --protocolo AG12345 --agendamento-confirmado` | OK |
| S10 | "separacoes do atacadao" | `consultando_situacao_pedidos.py --grupo atacadao --em-separacao` | OK |
| S11 | "o que tem em separacao pra amanha?" | `consultando_situacao_pedidos.py --em-separacao --ate-data amanha` | OK |
| S12 | "desfazer separacao do VCD123" | **NAO EXISTE** - Acao manual | MANUAL |

### Categoria: PRODUCAO (8 casos)

| # | Pergunta do Usuario | Script | Status |
|---|---------------------|--------|--------|
| PR01 | "programacao de producao" | `consultando_programacao_producao.py --listar` | OK |
| PR02 | "producao dos proximos 7 dias" | `consultando_programacao_producao.py --listar --dias 7` | OK |
| PR03 | "quando vai produzir palmito?" | `consultando_programacao_producao.py --produto palmito` | OK |
| PR04 | "producao por linha" | `consultando_programacao_producao.py --listar --por-linha` | OK |
| PR05 | "producao por dia" | `consultando_programacao_producao.py --listar --por-dia` | OK |
| PR06 | "producao da Linha A" | `consultando_programacao_producao.py --linha "Linha A"` | OK |
| PR07 | "antecipar producao de palmito" | `consultando_programacao_producao.py --produto palmito` (mostra opcoes) | OK |
| PR08 | "o que vai produzir amanha?" | `consultando_programacao_producao.py --listar --dias 1` | OK |

---

## PERGUNTAS AMBIGUAS - Quando PERGUNTAR

| Pergunta | Ambiguidade | O Que Perguntar |
|----------|-------------|-----------------|
| "quando fica disponivel?" | Pedido ou produto? | "Voce quer saber quando um PEDIDO fica disponivel ou quando um PRODUTO estara em estoque?" |
| "quanto tem pendente?" | De que? | "Pendente de que? Um produto especifico ou pedidos de um cliente/grupo?" |
| "programacao de entrega" | 4 significados | Ver [02-termos-ambiguos.md](02-termos-ambiguos.md) |
| "pedidos do cliente" | Qual cliente? | "Qual cliente? Informe o nome ou CNPJ" |
| "situacao" | De que? | "Situacao de qual pedido ou produto?" |
| "crie separacao" | Data? Tipo? | "Para quando? Separacao completa ou parcial?" |
| "separe" (sem pedido) | Qual pedido? | "Qual pedido deseja separar?" |
| "atrasados" | Pedidos ou entregas? | Assumir pedidos, mostrar ambos se relevante |
| "disponivel" | Estoque ou pedido? | "Disponibilidade de estoque do produto ou para embarque do pedido?" |

---

## PERGUNTAS PARA RAFAEL - Expandidas

### Sobre os GAPS (URGENTE):

1. Para criar `--cliente`, qual identificador usar?
   - [ ] CNPJ (busca exata)
   - [ ] Razao Social (busca parcial)
   - [ ] Ambos (tentar CNPJ primeiro, depois nome)
   - [x] Outro: CNPJ = 1 cliente / 1 cliente pode ser N CNPJ (caso de outros grupos) / Talvez o ideal seja aprimorar o "resolver_entidades" e utiliza-lo?

2. Para consulta produto + grupo, onde implementar?
   - [X] Adicionar em `consultando_situacao_pedidos.py` (ja tem --produto e --grupo separados)
   - [ ] Criar script novo `consultando_produto_cliente.py`
   - [ ] Modificar os scripts existentes para aceitar combinacao
   - [ ] Outro: ___________

3. Prioridade dos GAPS:
   - [ ] GAP-01 (--cliente) e mais urgente
   - [ ] GAP-02/03 (produto+grupo/cliente) e mais urgente
   - [X] Todos tem mesma prioridade
   - [ ] Outro: ___________

### Sobre casos complexos:

4. Se perguntarem "pedidos do [nome]" e existir tanto grupo quanto cliente com esse nome:
   - [X] Priorizar grupo
   - [ ] Perguntar qual
   - [ ] Mostrar ambos separados
   - [ ] Outro: ___________

5. Se perguntarem "quanto de X pro Y" e Y nao for encontrado:
   - [ ] Mostrar erro claro
   - [X] Sugerir correcao (fuzzy match)
   - [ ] Listar opcoes similares
   - [ ] Outro: ___________

6. Limite padrao de resultados:
   - [ ] 10 itens (resumido)
   - [X] 20 itens (moderado)
   - [ ] 50 itens (detalhado)
   - [ ] 100 itens (completo)
   - [X] Perguntar se quiser mais

7. Formato de resposta preferido:
   - [X] Tabela compacta
   - [ ] Lista detalhada
   - [ ] Resumo + "quer ver detalhes?"
   - [ ] Depende da quantidade de resultados

### Perguntas reais de usuarios (adicione):

8. Liste outras perguntas que usuarios ja fizeram e nao estao cobertas:
   - ___________
   - ___________
   - ___________

9. Quais erros os usuarios cometem com frequencia?
   - ___________
   - ___________

10. Ha algum termo/abreviacao que usuarios usam e nao esta documentado?
    - ___________
Abreviações dos produtos ou embalagem que consta abreviada utilizarem extensa, exemplo:
Verde Fatiada = VF 
Azeitona = AZ
Balde = BD
Cogumelo Inteiro = CI
Cogumelo Fatiado = CF
Barrica = BR
Caixa = CX

Para especificar melhor, os produtos de conserva em muito casos são compostos por:

Azeitona (MP) 
exemplo:[Azeitona,Cogumelo,Pepino,Cebolinha,Pimenta,Molho,Ol.misto,Azeite,Palmito,Pessego]

Verde Fatiada (tipo, variedade + estado) 
exemplo:[(Azeitona)Verde,Preta,Azapa]+[Fatiada,Recheada,Inteira,Sem Caroço], Formando[AZ VF,AZ PF, AZ VR, AZ VSC] 
[(Pimenta)Biquinho,Jalapeno] No caso da pimenta, há nomenclatura apenas para os estados != inteira [Picada,Condimentada...]

A MP é representada por tipo_materia_prima, com opções como "AZ VF".

BD 6x2 Todos os itens que houverem "x" significa que é 1 caixa com X embalagens (no caso 6) embalagem do tipo Y (No caso BD=Balde) com Z peso em cada uma (No caso sendo 2 é 2 kg)
Embalagens com X partem de 60 gramas até 3 kg ou seja, numeros acima de 50 indicam gramas, abaixo de 50 indicam KG no caxo de haver um "x" no meio.
exemplo: [(Azeitona Verde Fatiada)BD 6x2, Pouch 18x150, VD 12x420, Pouch 30x80, Sachet 36x60]

A Embalagem é representada por tipo_embalagem, com opções como BD 2 KG

Campo Belo normalmente no final indica a marca ou variação do mesmo produto
exemplo: [(Azeitona Verde Fatiada BD 6x2), Campo Belo(marca), Industria(destinado a industria), Benassi(marca), Imperial(marca)]

A Marca/variação é representada por categoria_produto, com opções como CAMPO BELO

Esses campos estão em categoria_produto

Os usuarios podem falar "balde" ou "bd"

Nome final AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO

---

## VERIFICAÇÃO TÉCNICA - Claude (12/12/2025)

### GAP-02 ✅ RESOLVIDO: `--grupo + --produto` FUNCIONA

**Correção implementada em 12/12/2025**

Nova função `consultar_situacao_pedidos_grupo_produto()` criada em [consultando_situacao_pedidos.py:188-334](../../skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py#L188-L334).

Teste executado:
```bash
python consultando_situacao_pedidos.py --grupo atacadao --produto 4320147
```

**Resultado**:
```json
{
  "sucesso": true,
  "tipo_analise": "PEDIDOS_GRUPO_PRODUTO",
  "grupo": "atacadao",
  "produto": {"cod_produto": "4320147", "nome_produto": "AZEITONA VERDE FATIADA - POUCH 18X150 GR - CAMPO BELO"},
  "resumo": {
    "total_pedidos": 28,
    "total_quantidade": 8430.0,
    "total_valor": 677682.35,
    "mensagem": "28 pedido(s) do Atacadao com AZEITONA VERDE FATIADA..."
  }
}
```

**Fluxo corrigido** ([consultando_situacao_pedidos.py:1160-1162](../../skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py#L1160-L1162)):
```python
# IMPORTANTE: Verificar combinacao grupo+produto ANTES dos filtros individuais
if args.grupo and args.produto:
    resultado = consultar_situacao_pedidos_grupo_produto(args)
```

---

### ABREVIAÇÕES - Análise Corrigida (12/12/2025)

#### EXISTEM NO BANCO (confirmado):

| Abreviação | Campo | Valor Exato | Qtd Produtos |
|------------|-------|-------------|--------------|
| **CI** | `tipo_materia_prima` | `'CI'` | 25 |
| **CF** | `tipo_materia_prima` | `'CF'` | 22 |
| **AZ VF** | `tipo_materia_prima` | `'AZ VF'` | - |
| **AZ PF** | `tipo_materia_prima` | `'AZ PF'` | 17 |
| **BR/BARRICA** | `tipo_embalagem` | `'BARRICA'` | 42 |
| **BD** | `tipo_embalagem` | `'BD 2 KG'` etc | - |

#### NÃO EXISTE COMO CAMPO:

| Termo | Como Identificar |
|-------|------------------|
| **CX (Caixa)** | Padrão `NxN` no nome: "6X2", "18X150", "12X180" |

#### PROBLEMA DO resolver_produto:

A busca atual usa `ILIKE '%termo%'` que encontra **falsos positivos**:
- "CI" → encontra "INTENSA", "ADOCICADA"
- "PF" → encontra "SPECK FOODS"
- "BR" → encontra "BRASLO"

**SOLUÇÃO NECESSÁRIA**: Criar mapeamento de abreviações conhecidas para busca EXATA:
```python
ABREVIACOES = {
    'CI': ('tipo_materia_prima', 'CI'),
    'CF': ('tipo_materia_prima', 'CF'),
    'AZ PF': ('tipo_materia_prima', 'AZ PF'),
    'AZ VF': ('tipo_materia_prima', 'AZ VF'),
    'BARRICA': ('tipo_embalagem', 'BARRICA'),
    'BR': ('tipo_embalagem', 'BARRICA'),  # alias
}
```

---

### RESPOSTAS DO RAFAEL - Abreviações (12/12/2025)

| Pergunta | Resposta |
|----------|----------|
| CI (Cogumelo Inteiro) existe? | ✅ Sim, `tipo_materia_prima = 'CI'` |
| CF (Cogumelo Fatiado) existe? | ✅ Sim, `tipo_materia_prima = 'CF'` |
| CX (Caixa) existe? | ❌ Não. Identificado pelo padrão `NxN` no nome |
| BR (Barrica) existe? | ✅ Sim, `tipo_embalagem = 'BARRICA'`. Buscar "BR " com espaço |
| 4x1,01 e 6x1,01 são o mesmo? | ❌ NÃO. São produtos diferentes (qtd/caixa diferente) |

#### Exemplos Verificados:

| Código | tipo_materia_prima | tipo_embalagem | Nome |
|--------|-------------------|----------------|------|
| 4230162 | AZ PF | BD 2 KG | AZEITONA PRETA FATIADA - BD 6X2 KG - CAMPO BELO |
| 4520173 | CI | VIDRO 200 G | COGUMELO INTEIRO - VD 12X180 G - CAMPO BELO |
| 4320138 | AZ VF | BARRICA | AZEITONA VERDE FATIADA - BR 30 KG - CAMPO BELO |

---

### GAP-01 e GAP-03 ✅ RESOLVIDOS: `--cliente` e `--cliente + --produto`

**Correção implementada em 12/12/2025**

1. Nova função `resolver_cliente()` em [resolver_entidades.py:409-584](../../skills/gerindo-expedicao/scripts/resolver_entidades.py#L409-L584)
2. Nova função `consultar_situacao_pedidos_cliente()` em [consultando_situacao_pedidos.py:338-391](../../skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py#L338-L391)
3. Nova função `consultar_situacao_pedidos_cliente_produto()` em [consultando_situacao_pedidos.py:394-547](../../skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py#L394-L547)

**Testes executados**:
```bash
# GAP-01: Busca por nome parcial
python consultando_situacao_pedidos.py --cliente "ATACADAO 183"
# Resultado: 8 pedidos encontrados

# GAP-01: Busca por CNPJ
python consultando_situacao_pedidos.py --cliente "75.315.333"
# Resultado: Encontrou todas as lojas do Atacadão

# GAP-03: Cliente + Produto
python consultando_situacao_pedidos.py --cliente "ATACADAO 183" --produto "4320147"
# Resultado: 8 pedidos com AZEITONA VERDE FATIADA
```

---

### ABREVIAÇÕES ✅ RESOLVIDO: Busca EXATA para CI, CF, BR, BD, etc.

**Correção implementada em 12/12/2025**

1. Novo dicionário `ABREVIACOES_PRODUTO` em [resolver_entidades.py:105-139](../../skills/gerindo-expedicao/scripts/resolver_entidades.py#L105-L139)
2. Nova função `detectar_abreviacoes()` em [resolver_entidades.py:154-193](../../skills/gerindo-expedicao/scripts/resolver_entidades.py#L154-L193)
3. Função `resolver_produto()` modificada para usar busca EXATA em abreviações

**Abreviações suportadas:**

| Abreviação | Campo | Tipo | Descrição |
|------------|-------|------|-----------|
| CI | tipo_materia_prima | EXATO | Cogumelo Inteiro |
| CF | tipo_materia_prima | EXATO | Cogumelo Fatiado |
| AZ VF | tipo_materia_prima | EXATO | Azeitona Verde Fatiada |
| AZ PF | tipo_materia_prima | EXATO | Azeitona Preta Fatiada |
| BR | tipo_embalagem | EXATO→BARRICA | Barrica |
| BD | tipo_embalagem | LIKE BD% | Balde |
| GL | tipo_embalagem | LIKE GALAO% | Galão |
| VD | tipo_embalagem | LIKE VIDRO% | Vidro |
| POUCH | tipo_embalagem | LIKE POUCH% | Pouch |
| MEZZANI | categoria_produto | EXATO | Marca Mezzani |
| IND | categoria_produto | EXATO→INDUSTRIA | Indústria |

**Testes executados:**

| Busca | Antes | Depois |
|-------|-------|--------|
| "CI" | ❌ Encontrava "MOSTARDA INTENSA" | ✅ Só COGUMELO INTEIRO (tipo_mp=CI) |
| "BR" | ❌ Encontrava "BRASLO" | ✅ Só BARRICA (tipo_emb=BARRICA) |
| "AZ VF BD" | ❌ Falsos positivos | ✅ Azeitona Verde Fatiada em Balde |

**Lógica implementada:**
```python
# Detecta abreviações em tokens (inclusive combinações como "AZ VF")
abreviacoes, tokens_restantes = detectar_abreviacoes(tokens)

# Para abreviações: busca EXATA no campo específico
if tipo == 'exato':
    filtros.append(func.upper(coluna) == valor.upper())
else:  # tipo == 'like'
    filtros.append(coluna.ilike(valor))

# Para tokens restantes: mantém busca parcial ILIKE
```

---

### PRÓXIMOS PASSOS - Prioridade

**Concluído**:
- [x] `--grupo + --produto` (combinar filtros) ✅ GAP-02
- [x] `--cliente` (busca por cliente não-grupo) ✅ GAP-01
- [x] `--cliente + --produto` (combinar filtros) ✅ GAP-03
- [x] Melhorar busca de abreviações (mapeamento exato) ✅ RESOLVIDO (12/12/2025)

**Pendente**:
- (nenhum GAP pendente neste documento)

---

## Dependencias

- Nenhuma para implementar o Decision Tree no SKILL.md
- GAPs dependem de desenvolvimento nos scripts
- Abreviações problemáticas precisam de decisão de Rafael

---

## Referencias

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Set appropriate degrees of freedom" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Avoid offering too many options" |
| Cookbook | [METAPROMPT.md](../cookbooks/METAPROMPT.md) | Gerar prompt otimizado |

**Citacao chave:**
> "Match the level of specificity to the task's fragility and variability."

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento | Claude |
| 12/12/2025 | Adicionadas referencias | Claude |
| 12/12/2025 | Respostas do Rafael (perguntas 1-7, 10) | Rafael |
| 12/12/2025 | Verificacao tecnica: GAP-02 confirmado, testes de abreviacoes | Claude |
| 12/12/2025 | Correcao abreviacoes: CI/CF/BR existem, CX nao existe | Claude+Rafael |
| 12/12/2025 | **GAP-02 RESOLVIDO**: Implementada funcao consultar_situacao_pedidos_grupo_produto() | Claude |
| 12/12/2025 | **GAP-01 RESOLVIDO**: Implementada funcao resolver_cliente() e consultar_situacao_pedidos_cliente() | Claude |
| 12/12/2025 | **GAP-03 RESOLVIDO**: Implementada funcao consultar_situacao_pedidos_cliente_produto() | Claude |
| 12/12/2025 | **ABREVIACOES RESOLVIDO**: Implementado ABREVIACOES_PRODUTO e detectar_abreviacoes() | Claude |
| 12/12/2025 | **DECISION TREE INSERIDO**: Aplicado METAPROMPT para gerar Decision Tree otimizado em SKILL.md | Claude |
| 12/12/2025 | **STATUS CONCLUIDO**: Documento 01-decision-tree.md finalizado | Claude |
