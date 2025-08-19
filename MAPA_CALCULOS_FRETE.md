# 📊 MAPA COMPLETO DOS CÁLCULOS DE FRETE NO SISTEMA

**Data de Criação**: 19/08/2025  
**Última Atualização**: 19/08/2025  
**Versão**: 1.0

---

## 📋 SUMÁRIO EXECUTIVO

O sistema possui **2 arquivos principais** de cálculo de frete e **5 módulos consumidores**:

1. **`app/utils/calculadora_frete.py`** - Motor central de cálculo (classe CalculadoraFrete)
2. **`app/utils/frete_simulador.py`** - Simulação e busca de opções (calcular_fretes_possiveis)
3. **`app/cotacao/routes.py`** - Cotação automática e manual
4. **`app/fretes/routes.py`** - Lançamento de fretes
5. **`app/embarques/routes.py`** - Gestão de embarques
6. **`app/pedidos/routes.py`** - Cotação manual de pedidos
7. **`app/tabelas/routes.py`** - Gestão de tabelas de frete

---

## 🔧 1. NÚCLEO DO CÁLCULO

### 📁 **app/utils/calculadora_frete.py**
**Responsabilidade**: Motor matemático central de cálculo de frete

#### **Classe CalculadoraFrete**

##### `calcular_frete_unificado()` (Linha 19-124)
```python
def calcular_frete_unificado(peso, valor_mercadoria, tabela_dados, 
                            cidade=None, codigo_ibge=None, 
                            transportadora_optante=False)
```
- **Propósito**: Função principal de cálculo unificado
- **Fluxo de Cálculo**:
  1. Determina peso para cálculo (real vs mínimo)
  2. Calcula frete base (peso + valor)
  3. Adiciona adicionais (GRIS, ADV, RCA)
  4. Calcula pedágio
  5. Soma valores fixos (TAS, Despacho, CTE)
  6. Aplica frete mínimo valor
  7. Aplica ICMS se não incluso
  8. Calcula valor líquido (desconta ICMS se não optante)
- **Retorno**: Dict com valor_bruto, valor_com_icms, valor_liquido, detalhes

##### `calcular_frete_carga_direta()` (Linha 272-324)
```python
def calcular_frete_carga_direta(peso_total_embarque, valor_total_embarque,
                                peso_cnpj, valor_cnpj, tabela_dados, ...)
```
- **Propósito**: Calcula frete para carga DIRETA com rateio por peso
- **Especificidade**: Rateia proporcionalmente pelo peso do CNPJ

##### `calcular_frete_carga_fracionada()` (Linha 326-353)
```python
def calcular_frete_carga_fracionada(peso_cnpj, valor_cnpj, tabela_dados, ...)
```
- **Propósito**: Calcula frete para carga FRACIONADA
- **Especificidade**: Cálculo direto por CNPJ

#### **Métodos Auxiliares**
- `_obter_icms_cidade()` - Obtém ICMS da cidade
- `_determinar_peso_calculo()` - Aplica peso mínimo
- `_calcular_frete_base()` - Calcula frete peso + valor
- `_calcular_adicionais_valor()` - GRIS, ADV, RCA
- `_calcular_pedagio()` - Pedágio por frações de 100kg
- `_calcular_valores_fixos()` - TAS, Despacho, CTE
- `_aplicar_frete_minimo_valor()` - Aplica mínimo no líquido
- `_aplicar_icms_final()` - Embute ICMS se necessário
- `_calcular_valor_liquido()` - Desconta ICMS se não optante

---

### 📁 **app/utils/frete_simulador.py**
**Responsabilidade**: Busca e simulação de múltiplas opções de frete

#### `calcular_fretes_possiveis()` (Linha 15-260)
```python
def calcular_fretes_possiveis(cidade_destino_id=None, peso_utilizado=None, 
                              valor_carga=None, veiculo_forcado=None, 
                              tipo_carga=None, ...)
```
- **Propósito**: Busca TODAS as opções de frete disponíveis
- **Fluxo**:
  1. Busca cidade destino
  2. Busca atendimentos (CidadeAtendida)
  3. **NOVO**: Filtra transportadoras ativas (linha 129-131)
  4. Busca tabelas do grupo empresarial
  5. Calcula frete para cada tabela
  6. Para DIRETA: Aplica "tabela mais cara" por transportadora/UF/modalidade
- **Especificidades**:
  - Considera grupo empresarial
  - Aplica lógica "tabela mais cara" para carga DIRETA
  - Retorna lista com TODOS os campos da tabela
- **Cálculo Inline** (não usa CalculadoraFrete):
  ```python
  # Linha 159-192: Cálculo direto
  peso_para_calculo = max(peso_final, tf.frete_minimo_peso or 0)
  frete_peso = (tf.valor_kg or 0) * peso_para_calculo
  frete_valor = (tf.percentual_valor or 0) * valor_final / 100
  # ... etc
  ```

#### `calcular_frete_por_cnpj()` (Linha 353-508)
```python
def calcular_frete_por_cnpj(pedidos, veiculo_forcado=None)
```
- **Propósito**: Calcula fretes agrupando por CNPJ
- **Fluxo**:
  1. Agrupa pedidos por CNPJ
  2. Para mesmo UF: Busca opções DIRETAS e FRACIONADAS
  3. Para DIRETA: Busca tabelas de todas as cidades, aplica mais cara
  4. Para FRACIONADA: Calcula por CNPJ individual
- **Retorno**: Dict com 'diretas' e 'fracionadas'

#### Funções Auxiliares
- `agrupar_por_cnpj()` - Agrupa pedidos por CNPJ
- `deve_calcular_frete()` - Verifica se deve calcular (não FOB)
- `pedidos_mesmo_uf()` - Verifica se todos são do mesmo UF
- `normalizar_dados_pedido()` - Normaliza cidade/UF
- `buscar_cidade_unificada()` - Busca cidade com regras especiais

---

## 🎯 2. MÓDULOS CONSUMIDORES

### 📁 **app/cotacao/routes.py**
**Responsabilidade**: Cotação automática e otimização

#### Funções de Cálculo:

##### `calcular_otimizacoes_pedido_adicional()` (Linha 132)
- **Usa**: `calcular_fretes_possiveis()` internamente
- **Propósito**: Otimiza adição de pedido em embarque existente

##### `calcular_otimizacoes_pedido()` (Linha 191)
- **Usa**: Lógica própria de otimização
- **Propósito**: Calcula otimizações gerais

##### `calcular_frete_otimizacao_conservadora()` (Linha 1952)
- **Usa**: `calcular_frete_por_cnpj()` de frete_simulador
- **Propósito**: Cotação conservadora para múltiplos pedidos

#### Rotas Principais:
- `/cotacao/multiplos` - Cotação de múltiplos pedidos
- `/cotacao/resumo` - Resumo com cálculo detalhado
- `/cotacao/lancar` - Lançamento após cotação

---

### 📁 **app/fretes/routes.py**
**Responsabilidade**: Lançamento e gestão de fretes

#### Funções de Lançamento:

##### `lancar_fretes_embarque()` (Linha 1703)
- **Usa**: `CalculadoraFrete.calcular_frete_carga_direta()` ou `calcular_frete_carga_fracionada()`
- **Propósito**: Lança fretes de um embarque completo
- **Fluxo**:
  1. Busca embarque e itens
  2. Para DIRETA: Calcula e rateia
  3. Para FRACIONADA: Calcula por CNPJ
  4. Cria registros de Frete

##### `lancar_frete()` (Linha 1752)
- **Usa**: `CalculadoraFrete` indiretamente
- **Propósito**: Lançamento manual de frete individual

##### `lancar_frete_automatico()` (Linha 1862)
- **Usa**: `CalculadoraFrete` através de lancar_fretes_embarque
- **Propósito**: Lançamento automático por CNPJ

---

### 📁 **app/embarques/routes.py**
**Responsabilidade**: Gestão de embarques

#### Integração com Cálculo:
- **Não calcula diretamente**, mas:
  - Armazena dados da tabela no embarque
  - Fornece dados para `fretes/routes.py` calcular
  - Campos: `tabela_*` (valor_kg, percentual_valor, etc.)

---

### 📁 **app/pedidos/routes.py**
**Responsabilidade**: Cotação manual de pedidos

#### Rota `/pedidos/cotacao_manual`:
- **Usa**: Interface manual, não calcula automaticamente
- **Permite**: Seleção manual de transportadora/tabela

---

### 📁 **app/tabelas/routes.py**
**Responsabilidade**: CRUD de tabelas de frete

#### Funcionalidades:
- Cadastro de tabelas com todos os campos de cálculo
- Histórico de alterações
- Importação em massa
- **Não calcula frete**, apenas gerencia dados

---

## 🔄 3. FLUXO DE DADOS

### **Fluxo Principal de Cotação**:
```
1. Pedidos selecionados
   ↓
2. cotacao/routes → calcular_frete_por_cnpj()
   ↓
3. frete_simulador → calcular_fretes_possiveis()
   ↓
4. Busca tabelas (com filtro ativo=true)
   ↓
5. Calcula inline (não usa CalculadoraFrete)
   ↓
6. Retorna opções
   ↓
7. Usuario seleciona
   ↓
8. Cria Embarque
```

### **Fluxo de Lançamento**:
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

## ⚠️ 4. PONTOS DE ATENÇÃO

### **Duplicação de Lógica**:
- `calcular_fretes_possiveis()` calcula inline
- `CalculadoraFrete` tem mesma lógica modularizada
- **Risco**: Divergência se alterar só um lugar

### **Filtro de Transportadoras Ativas**:
- ✅ Implementado em `calcular_fretes_possiveis()` (linha 129-131)
- ⚠️ NÃO implementado em `CalculadoraFrete` (não busca tabelas)

### **Campos de Cálculo**:
```python
# Campos essenciais para cálculo:
- valor_kg              # Valor por kg
- percentual_valor      # % sobre valor mercadoria
- frete_minimo_peso     # Peso mínimo para cálculo
- frete_minimo_valor    # Valor mínimo do frete
- percentual_gris       # % GRIS
- percentual_adv        # % Ad Valorem
- percentual_rca        # % RCA
- pedagio_por_100kg     # Pedágio por fração
- valor_tas             # Taxa TAS
- valor_despacho        # Taxa despacho
- valor_cte             # Taxa CTE
- icms_incluso          # ICMS já está no valor?
```

### **Regras de Negócio Importantes**:
1. **Peso mínimo**: Sempre usa o maior entre peso real e mínimo
2. **Frete base**: SOMA peso + valor (não pega o maior)
3. **Frete mínimo**: Aplicado ANTES do ICMS
4. **ICMS**: Embutido apenas se não estiver incluso
5. **Optante**: Não desconta ICMS do valor líquido
6. **Carga DIRETA**: Aplica "tabela mais cara" por transportadora/UF
7. **Pedágio**: Calculado por frações de 100kg (arredonda pra cima)

---

## 🎯 5. RECOMENDAÇÕES

### **Unificação Futura**:
1. Extrair lógica comum em função auxiliar
2. Manter separação de responsabilidades:
   - `frete_simulador`: Busca e seleção
   - `CalculadoraFrete`: Cálculo preciso
3. Criar testes unitários para garantir consistência

### **Campos Pendentes de Implementação**:
Como discutido, implementar em Transportadora:
- `config_frete_minimo` - JSON com regras de participação
- `tipo_calculo_pedagio` - POR_100KG vs POR_FRACAO
- ✅ `ativo` - Já implementado

### **Melhorias Sugeridas**:
1. Cache de cálculos repetidos
2. Log de auditoria de cálculos
3. Validação de consistência entre métodos
4. Dashboard de análise de fretes

---

## 📚 6. REFERÊNCIAS CRUZADAS

- `CLAUDE.md` - Nomes corretos dos campos
- `MAPA_FLUXOS_COTACAO.md` - Fluxo detalhado de cotação
- `migrations/` - Histórico de mudanças no banco
- `tests/` - Testes de cálculo (se existirem)

---

**Nota**: Este documento deve ser atualizado sempre que houver mudanças nas funções de cálculo de frete.