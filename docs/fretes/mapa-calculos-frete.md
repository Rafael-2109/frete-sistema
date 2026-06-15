<!-- doc:meta
tipo: explanation
camada: L2
sot_de: Mapa completo de onde e como o frete e calculado no sistema (motor central, simulador, modulos consumidores e fluxo de dados).
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Mapa completo dos calculos de frete no sistema

> **Papel:** explicar onde mora cada calculo de frete (motor central `CalculadoraFrete`, simulador, modulos consumidores), como os dados fluem da cotacao ao lancamento e quais regras de negocio governam o calculo.

## Contexto

Este documento mapeia os 2 arquivos principais de calculo de frete e os modulos que os consomem, servindo de referencia para entender o fluxo Cotacao -> Embarque -> Lancamento. Reflete o estado do codigo apos a unificacao do calculo: o simulador hoje delega ao motor central `CalculadoraFrete`, eliminando a duplicacao de logica que existia na versao anterior deste mapa.

## Indice

- [1. Nucleo do calculo](#1-nucleo-do-calculo)
- [2. Modulos consumidores](#2-modulos-consumidores)
- [3. Fluxo de dados](#3-fluxo-de-dados)
- [4. Pontos de atencao](#4-pontos-de-atencao)
- [5. Recomendacoes](#5-recomendacoes)
- [6. Referencias cruzadas](#6-referencias-cruzadas)

---

## Sumario executivo

O sistema possui **2 arquivos principais** de calculo de frete e **5 modulos consumidores**:

1. **`app/utils/calculadora_frete.py`** - Motor central de calculo (classe CalculadoraFrete)
2. **`app/utils/frete_simulador.py`** - Simulacao e busca de opcoes (calcular_fretes_possiveis)
3. **`app/cotacao/routes.py`** - Cotacao automatica e manual
4. **`app/fretes/routes.py`** - Lancamento de fretes
5. **`app/embarques/routes.py`** - Gestao de embarques
6. **`app/pedidos/routes.py`** - Cotacao manual de pedidos
7. **`app/tabelas/routes.py`** - Gestao de tabelas de frete

---

## 1. Nucleo do calculo

### app/utils/calculadora_frete.py

**Responsabilidade**: Motor matematico central de calculo de frete

#### Classe CalculadoraFrete (Linha 17)

##### `calcular_frete_unificado()` (Linha 46)
```python
def calcular_frete_unificado(peso, valor_mercadoria, tabela_dados, 
                            cidade=None, codigo_ibge=None, 
                            transportadora_optante=False)
```
- **Proposito**: Funcao principal de calculo unificado
- **Fluxo de Calculo**:
  1. Determina peso para calculo (real vs minimo)
  2. Calcula frete base (peso + valor)
  3. Adiciona adicionais (GRIS, ADV, RCA)
  4. Calcula pedagio
  5. Soma valores fixos (TAS, Despacho, CTE)
  6. Aplica frete minimo valor
  7. Aplica ICMS se nao incluso
  8. Calcula valor liquido (desconta ICMS se nao optante)
- **Retorno**: Dict com valor_bruto, valor_com_icms, valor_liquido, detalhes

##### `calcular_frete_carga_direta()` (Linha 502)
```python
def calcular_frete_carga_direta(peso_total_embarque, valor_total_embarque,
                                peso_cnpj, valor_cnpj, tabela_dados, ...)
```
- **Proposito**: Calcula frete para carga DIRETA com rateio por peso
- **Especificidade**: Rateia proporcionalmente pelo peso do CNPJ

##### `calcular_frete_carga_fracionada()` (Linha 563)
```python
def calcular_frete_carga_fracionada(peso_cnpj, valor_cnpj, tabela_dados, ...)
```
- **Proposito**: Calcula frete para carga FRACIONADA
- **Especificidade**: Calculo direto por CNPJ

#### Metodos Auxiliares
- `_obter_icms_cidade()` - Obtem ICMS da cidade
- `_determinar_peso_calculo()` - Aplica peso minimo
- `_calcular_frete_base()` - Calcula frete peso + valor
- `_calcular_adicionais_valor()` - GRIS, ADV, RCA
- `_calcular_pedagio()` - Pedagio por fracoes de 100kg
- `_calcular_valores_fixos()` - TAS, Despacho, CTE
- `_aplicar_frete_minimo_valor()` - Aplica minimo no liquido
- `_aplicar_icms_final()` - Embute ICMS se necessario
- `_calcular_valor_liquido()` - Desconta ICMS se nao optante

---

### app/utils/frete_simulador.py

**Responsabilidade**: Busca e simulacao de multiplas opcoes de frete

#### `calcular_fretes_possiveis()` (Linha 17)
```python
def calcular_fretes_possiveis(cidade_destino_id=None, peso_utilizado=None, 
                              valor_carga=None, veiculo_forcado=None, 
                              tipo_carga=None, ...)
```
- **Proposito**: Busca TODAS as opcoes de frete disponiveis
- **Fluxo**:
  1. Busca cidade destino
  2. Busca atendimentos (CidadeAtendida)
  3. **NOVO**: Filtra transportadoras ativas
  4. Busca tabelas do grupo empresarial
  5. Calcula frete para cada tabela
  6. Para DIRETA: Aplica "tabela mais cara" por transportadora/UF/modalidade
- **Especificidades**:
  - Considera grupo empresarial
  - Aplica logica "tabela mais cara" para carga DIRETA
  - Retorna lista com TODOS os campos da tabela
- **Integracao com o motor central**: a logica de calculo NAO e mais inline. A funcao
  prepara os dados da tabela via `TabelaFreteManager.preparar_dados_tabela()` e delega o
  calculo a `CalculadoraFrete.calcular_frete_unificado()`. A duplicacao de logica que
  existia em versoes anteriores foi resolvida — ha uma unica fonte de verdade para o
  calculo.

#### `calcular_frete_por_cnpj()` (Linha 382)
```python
def calcular_frete_por_cnpj(pedidos, veiculo_forcado=None)
```
- **Proposito**: Calcula fretes agrupando por CNPJ
- **Fluxo**:
  1. Agrupa pedidos por CNPJ
  2. Para mesmo UF: Busca opcoes DIRETAS e FRACIONADAS
  3. Para DIRETA: Busca tabelas de todas as cidades, aplica mais cara
  4. Para FRACIONADA: Calcula por CNPJ individual
- **Retorno**: Dict com 'diretas' e 'fracionadas'

#### Funcoes Auxiliares
- `agrupar_por_cnpj()` - Agrupa pedidos por CNPJ
- `deve_calcular_frete()` - Verifica se deve calcular (nao FOB)
- `pedidos_mesmo_uf()` - Verifica se todos sao do mesmo UF
- `normalizar_dados_pedido()` - Normaliza cidade/UF
- `buscar_cidade_unificada()` - Busca cidade com regras especiais

---

## 2. Modulos consumidores

### app/cotacao/routes.py

**Responsabilidade**: Cotacao automatica e otimizacao

#### Funcoes de Calculo:

##### `calcular_otimizacoes_pedido_adicional()` (Linha 132)
- **Usa**: `calcular_fretes_possiveis()` internamente
- **Proposito**: Otimiza adicao de pedido em embarque existente

##### `calcular_otimizacoes_pedido()` (Linha 188)
- **Usa**: Logica propria de otimizacao
- **Proposito**: Calcula otimizacoes gerais

##### `calcular_frete_otimizacao_conservadora()` (Linha 2900)
- **Usa**: `calcular_frete_por_cnpj()` de frete_simulador
- **Proposito**: Cotacao conservadora para multiplos pedidos

#### Rotas Principais:
- `/cotacao/multiplos` - Cotacao de multiplos pedidos
- `/cotacao/resumo` - Resumo com calculo detalhado
- `/cotacao/lancar` - Lancamento apos cotacao

---

### app/fretes/routes.py

**Responsabilidade**: Lancamento e gestao de fretes

#### Funcoes de Lancamento:

##### `lancar_fretes_embarque()` (Linha 3457)
- **Usa**: `CalculadoraFrete.calcular_frete_carga_direta()` ou `calcular_frete_carga_fracionada()`
- **Proposito**: Lanca fretes de um embarque completo
- **Fluxo**:
  1. Busca embarque e itens
  2. Para DIRETA: Calcula e rateia
  3. Para FRACIONADA: Calcula por CNPJ
  4. Cria registros de Frete

##### `lancar_frete()` (Linha 3507)
- **Usa**: `CalculadoraFrete` indiretamente
- **Proposito**: Lancamento manual de frete individual

##### `lancar_frete_automatico()` (Linha 3685)
- **Usa**: `CalculadoraFrete` atraves de lancar_fretes_embarque
- **Proposito**: Lancamento automatico por CNPJ

---

### app/embarques/routes.py

**Responsabilidade**: Gestao de embarques

#### Integracao com Calculo:
- **Nao calcula diretamente**, mas:
  - Armazena dados da tabela no embarque
  - Fornece dados para `fretes/routes.py` calcular
  - Campos: `tabela_*` (valor_kg, percentual_valor, etc.)

---

### app/pedidos/routes.py

**Responsabilidade**: Cotacao manual de pedidos

#### Rota `/pedidos/cotacao_manual`:
- **Usa**: Interface manual, nao calcula automaticamente
- **Permite**: Selecao manual de transportadora/tabela

---

### app/tabelas/routes.py

**Responsabilidade**: CRUD de tabelas de frete

#### Funcionalidades:
- Cadastro de tabelas com todos os campos de calculo
- Historico de alteracoes
- Importacao em massa
- **Nao calcula frete**, apenas gerencia dados

---

## 3. Fluxo de dados

### **Fluxo Principal de Cotacao**:
```
1. Pedidos selecionados
   ↓
2. cotacao/routes → calcular_frete_por_cnpj()
   ↓
3. frete_simulador → calcular_fretes_possiveis()
   ↓
4. Busca tabelas (com filtro ativo=true)
   ↓
5. Calcula via CalculadoraFrete.calcular_frete_unificado()
   (dados preparados por TabelaFreteManager)
   ↓
6. Retorna opcoes
   ↓
7. Usuario seleciona
   ↓
8. Cria Embarque
```

### **Fluxo de Lancamento**:
```
1. Embarque criado
   ↓
2. fretes/routes → lancar_fretes_embarque()
   ↓
3. CalculadoraFrete → calcular_frete_*()
   ↓
4. Cria registros Frete
   ↓
5. Atualiza status
```

---

## 4. Pontos de atencao

### **Logica de calculo unificada (refactor concluido)**:
- `calcular_fretes_possiveis()` NAO calcula mais inline: delega a
  `CalculadoraFrete.calcular_frete_unificado()`, com os dados da tabela preparados por
  `TabelaFreteManager.preparar_dados_tabela()`.
- Existe uma unica fonte de verdade para o calculo (a classe `CalculadoraFrete`), entao
  nao ha mais o risco de divergencia entre simulador e motor central que existia antes.

### **Filtro de Transportadoras Ativas**:
- Implementado em `calcular_fretes_possiveis()` (etapa de filtro de atendimentos).
- O filtro vive na camada de busca/simulacao; `CalculadoraFrete` nao busca tabelas, apenas
  calcula sobre os dados ja selecionados.

### **Campos de Calculo**:
```python
# Campos essenciais para calculo:
- valor_kg              # Valor por kg
- percentual_valor      # % sobre valor mercadoria
- frete_minimo_peso     # Peso minimo para calculo
- frete_minimo_valor    # Valor minimo do frete
- percentual_gris       # % GRIS
- percentual_adv        # % Ad Valorem
- percentual_rca        # % RCA
- pedagio_por_100kg     # Pedagio por fracao
- valor_tas             # Taxa TAS
- valor_despacho        # Taxa despacho
- valor_cte             # Taxa CTE
- icms_incluso          # ICMS ja esta no valor?
```

### **Regras de Negocio Importantes**:
1. **Peso minimo**: Sempre usa o maior entre peso real e minimo
2. **Frete base**: SOMA peso + valor (nao pega o maior)
3. **Frete minimo**: Aplicado ANTES do ICMS
4. **ICMS**: Embutido apenas se nao estiver incluso
5. **Optante**: Nao desconta ICMS do valor liquido
6. **Carga DIRETA**: Aplica "tabela mais cara" por transportadora/UF
7. **Pedagio**: Calculado por fracoes de 100kg (arredonda pra cima)

---

## 5. Recomendacoes

### **Manutencao da arquitetura unificada**:
1. Manter o calculo concentrado em `CalculadoraFrete` (fonte de verdade unica).
2. Preservar a separacao de responsabilidades:
   - `frete_simulador`: Busca e selecao
   - `CalculadoraFrete`: Calculo preciso
3. Manter/ampliar testes unitarios para garantir consistencia do calculo.

### **Campos Pendentes de Implementacao**:
Implementar em Transportadora:
- `config_frete_minimo` - JSON com regras de participacao
- `tipo_calculo_pedagio` - POR_100KG vs POR_FRACAO
- `ativo` - Ja implementado

### **Melhorias Sugeridas**:
1. Cache de calculos repetidos
2. Log de auditoria de calculos
3. Validacao de consistencia entre metodos
4. Dashboard de analise de fretes

---

## 6. Referencias cruzadas

- `CLAUDE.md` - Nomes corretos dos campos
- `MAPA_FLUXOS_COTACAO.md` - Fluxo detalhado de cotacao (documento historico; nao versionado neste hub)

---

**Nota**: Este documento deve ser atualizado sempre que houver mudancas nas funcoes de calculo de frete.
