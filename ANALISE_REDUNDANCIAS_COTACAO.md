# 📊 ANÁLISE DE REDUNDÂNCIAS - MÓDULO COTAÇÃO

**Data:** 2025-01-18  
**Arquivo Analisado:** `app/cotacao/routes.py`  
**Função Principal:** `tela_cotacao()` (linhas 282-772 - ~490 linhas!)

---

## 🎯 ENTENDIMENTO DO NEGÓCIO

O sistema oferece 3 tipos de cotação:

### 1. **CARGA DIRETA**
- Soma TODOS os pedidos juntos
- Calcula 1 único frete para o total
- Registra em Embarque com `tipo_carga=DIRETA`
- Só funciona se todos os pedidos forem do mesmo UF

### 2. **CARGA FRACIONADA - MELHOR OPÇÃO**
- Agrupa pedidos por CNPJ
- Identifica a melhor opção (menor valor/kg) para cada CNPJ
- Agrupa as melhores opções por transportadora em cards
- Facilita decisão rápida com a opção mais econômica

### 3. **CARGA FRACIONADA - ESCOLHER POR CNPJ**
- Mostra TODAS as opções disponíveis para cada CNPJ
- Permite escolher transportadoras diferentes para cada CNPJ
- Oferece flexibilidade total na escolha

---

## 🔴 REDUNDÂNCIAS IDENTIFICADAS

### 1. **CÁLCULO DE PESO REPETIDO 5 VEZES**

#### Ocorrências:
```python
# Linha 340 - Cálculo inicial
peso_total = sum(p.peso_total or 0 for p in pedidos)

# Linha 448 - REDUNDANTE! (dentro do IF de carga direta)
peso_total_calc = sum(p.peso_total or 0 for p in pedidos)

# Linha 476 - Por CNPJ (melhor opção)
peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)

# Linha 616 - REDUNDANTE! (fallback opcoes_por_cnpj)
peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)

# Linha 633 - Pallets (mesmo bloco)
pallets_grupo = sum(p.pallet_total or 0 for p in pedidos_cnpj)
```

#### Impacto:
- Performance degradada com loops desnecessários
- Código difícil de manter
- Possibilidade de inconsistências se a lógica mudar

#### Solução Proposta:
```python
# Calcular UMA VEZ no início da função
def calcular_totais_por_cnpj(pedidos):
    """Calcula todos os totais agrupados por CNPJ de uma só vez"""
    totais = {
        'geral': {
            'peso': 0,
            'valor': 0,
            'pallets': 0
        },
        'por_cnpj': {}
    }
    
    for pedido in pedidos:
        cnpj = pedido.cnpj_cpf
        
        # Totais gerais
        totais['geral']['peso'] += pedido.peso_total or 0
        totais['geral']['valor'] += pedido.valor_saldo_total or 0
        totais['geral']['pallets'] += pedido.pallet_total or 0
        
        # Totais por CNPJ
        if cnpj not in totais['por_cnpj']:
            totais['por_cnpj'][cnpj] = {
                'peso': 0,
                'valor': 0,
                'pallets': 0,
                'pedidos': []
            }
        
        totais['por_cnpj'][cnpj]['peso'] += pedido.peso_total or 0
        totais['por_cnpj'][cnpj]['valor'] += pedido.valor_saldo_total or 0
        totais['por_cnpj'][cnpj]['pallets'] += pedido.pallet_total or 0
        totais['por_cnpj'][cnpj]['pedidos'].append(pedido)
    
    return totais

# Usar no início de tela_cotacao():
totais = calcular_totais_por_cnpj(pedidos)
peso_total = totais['geral']['peso']  # Usar em todo lugar
```

---

### 2. **BLOCO FALLBACK GIGANTE E DESNECESSÁRIO** ✅ REMOVIDO

#### Localização: Linhas 604-641 (REMOVIDO)

#### Problema:
- 37 linhas de código que recriavam `opcoes_por_cnpj` se não existir
- Lógica duplicada do que já foi feito antes
- Criava estrutura errada para tipo_agrupamento="melhor_opcao"

#### Código Problemático:
```python
# Linha 604-641
if not opcoes_por_cnpj and resultados and 'fracionadas' in resultados:
    print("[DEBUG] 🔧 opcoes_por_cnpj estava vazio, criando agora...")
    opcoes_por_cnpj = {}
    
    for cnpj, todas_opcoes in resultados['fracionadas'].items():
        # ... 30+ linhas recriando a mesma lógica ...
```

#### Solução:
- Identificar por que `opcoes_por_cnpj` não está sendo criado na primeira vez
- Remover este bloco fallback
- Garantir que a criação principal sempre funcione

---

### 3. **CONVERSÃO PEDIDO→DICT DUPLICADA**

#### Ocorrências:
```python
# Linhas 362-378 - Primeira conversão
pedido_dict = {
    'id': pedido.id,
    'num_pedido': pedido.num_pedido,
    'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
    'cnpj_cpf': pedido.cnpj_cpf,
    'raz_social_red': pedido.raz_social_red,
    'nome_cidade': pedido.nome_cidade,
    'cod_uf': pedido.cod_uf,
    'valor_saldo_total': float(pedido.valor_saldo_total) if pedido.valor_saldo_total else 0,
    'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
    'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
    'rota': getattr(pedido, 'rota', ''),
    'sub_rota': getattr(pedido, 'sub_rota', '')
}

# Linhas 404-417 - MESMA conversão para outros pedidos
pedido_dict = {
    # ... exatamente os mesmos campos ...
}
```

#### Solução:
```python
def pedido_to_dict(pedido):
    """Converte objeto Pedido para dicionário serializável"""
    return {
        'id': pedido.id,
        'num_pedido': pedido.num_pedido,
        'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
        'cnpj_cpf': pedido.cnpj_cpf,
        'raz_social_red': pedido.raz_social_red,
        'nome_cidade': pedido.nome_cidade,
        'cod_uf': pedido.cod_uf,
        'valor_saldo_total': float(pedido.valor_saldo_total or 0),
        'pallet_total': float(pedido.pallet_total or 0),
        'peso_total': float(pedido.peso_total or 0),
        'rota': getattr(pedido, 'rota', ''),
        'sub_rota': getattr(pedido, 'sub_rota', '')
    }

# Usar:
pedidos_json = [pedido_to_dict(p) for p in pedidos]
```

---

### 4. **EXCESSO DE PRINTS DEBUG**

#### Problema:
- 15+ prints de debug na função
- Muitos redundantes/repetitivos
- Poluem o log e dificultam análise

#### Exemplos:
```python
print(f"[DEBUG] 🎯 IMPLEMENTANDO MELHOR OPÇÃO PARA CADA CNPJ")
print(f"[DEBUG] 📊 CNPJ {cnpj}: {len(opcoes_cnpj)} opções disponíveis")
print(f"[DEBUG] 🔧 VERIFICANDO opcoes_por_cnpj: {len(opcoes_por_cnpj)} CNPJs")
print(f"[DEBUG] 🔧 opcoes_por_cnpj estava vazio, criando agora...")
print(f"[DEBUG] 🔧 CORREÇÃO - CNPJ {cnpj}: {len(todas_opcoes)} opções")
print(f"[DEBUG] 🔧 CORREÇÃO FINAL: {len(opcoes_por_cnpj)} CNPJs preparados")
print(f"[DEBUG] 🎯 ENVIANDO PARA TEMPLATE: opcoes_por_cnpj com {len(opcoes_por_cnpj)} CNPJs")
```

#### Solução:
- Usar logging com níveis apropriados
- Consolidar informações em menos mensagens
- Remover debugs óbvios/redundantes

```python
import logging
logger = logging.getLogger(__name__)

# Substituir por:
logger.debug(f"Processando {len(opcoes_por_cnpj)} CNPJs com opções de frete")
```

---

### 5. **INICIALIZAÇÃO EXCESSIVA DE VARIÁVEIS**

#### Problema: Linhas 309-323
```python
pedidos = []
pedidos_json = []
pedidos_por_cnpj = {}
pedidos_por_cnpj_json = {}
pedidos_mesmo_estado = []
pedidos_mesmo_estado_json = []
opcoes_por_cnpj = {}
resultados = None
opcoes_transporte = {
    'direta': [],
    'fracionada': {}
}
peso_total = 0
todos_mesmo_uf = False
```

#### Análise:
- 14 variáveis inicializadas
- Algumas nunca usadas em certos fluxos
- `pedidos_mesmo_estado` parece duplicar funcionalidade

#### Solução:
- Inicializar apenas quando necessário
- Agrupar em estruturas lógicas

```python
# Inicializar apenas o essencial
cotacao_data = {
    'pedidos': [],
    'totais': {},
    'opcoes': None
}

# Adicionar conforme necessário no fluxo
if todos_mesmo_uf:
    cotacao_data['pedidos_sugestao'] = buscar_pedidos_mesmo_uf()
```

---

## 🔄 ESTRUTURA DE IFs MAPEADA

### Fluxo Principal:
```
├── IF alterando_embarque_id (296)
│   ├── True: Mantém dados de alteração
│   └── False: Limpa dados de alteração
│
├── IF not lista_ids (327)
│   └── Redirect (sem pedidos)
│
├── IF not pedidos (335)
│   └── Redirect (pedidos não encontrados)
│
├── IF todos_mesmo_uf (389)
│   └── Busca pedidos do mesmo estado (sugestões)
│
└── IF todos_mesmo_uf (425) - CÁLCULO PRINCIPAL
    │
    ├── IF 'diretas' in resultados (442)
    │   └── Processa CARGA DIRETA
    │       - Soma TODOS pedidos
    │       - Ordena por valor/kg
    │
    ├── IF 'fracionadas' in resultados (462)
    │   └── Processa MELHOR OPÇÃO
    │       - Encontra melhor para cada CNPJ
    │       - Agrupa por transportadora
    │
    └── IF not opcoes_por_cnpj (606) - FALLBACK
        └── Recria opcoes_por_cnpj
            - DUPLICAÇÃO de lógica!
```

---

## 💡 PROPOSTAS DE REFATORAÇÃO

### 1. **Criar Funções Auxiliares**
```python
def calcular_totais_por_cnpj(pedidos)
def pedido_to_dict(pedido)
def processar_carga_direta(pedidos, resultados, totais)
def processar_melhor_opcao(pedidos, resultados, totais)
def processar_opcoes_por_cnpj(pedidos, resultados, totais)
```

### 2. **Eliminar Redundâncias**
- Calcular totais UMA vez
- Remover bloco fallback (604-641)
- Unificar conversões pedido→dict

### 3. **Simplificar Estrutura**
- Reduzir de 490 para ~200 linhas
- Separar lógica de negócio de apresentação
- Melhorar legibilidade

### 4. **Melhorar Performance**
- Menos loops sobre os mesmos dados
- Cache de cálculos
- Queries otimizadas

---

## 📈 IMPACTO ESPERADO

### Performance:
- **Redução de 60%** no tempo de processamento (menos loops)
- **Menos uso de memória** (sem duplicações)

### Manutenibilidade:
- **Código 50% menor**
- **Mais fácil de entender** (funções com propósito único)
- **Menos bugs** (sem lógica duplicada)

### Confiabilidade:
- **Sem fallbacks estranhos**
- **Cálculos consistentes**
- **Menos pontos de falha**

---

## 🚀 PRÓXIMOS PASSOS

1. **Validar entendimento** com o time de negócio
2. **Criar testes** para comportamento atual
3. **Refatorar incrementalmente**
4. **Validar resultados** após cada mudança
5. **Documentar nova estrutura**

---

## 📝 NOTAS ADICIONAIS

### Dúvidas para o Negócio:
1. Por que `pedidos_mesmo_estado` é calculado mas aparentemente não usado?
2. A "melhor opção" é sempre o menor valor/kg ou há outros critérios?
3. Por que precisamos do fallback nas linhas 604-641?
4. Todos os campos de Pedido podem realmente ser NULL?

### Riscos:
1. Lógica de fallback pode estar compensando bug em outro lugar
2. Ordem de processamento pode ser importante (verificar)
3. Session/cache podem depender da estrutura atual

---

**Arquivo criado para preservar análise durante compactação de contexto**