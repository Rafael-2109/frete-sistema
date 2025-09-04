# Sistema de Análise de Ruptura Assíncrono

## Arquitetura Implementada

Sistema de análise de ruptura de estoque que processa pedidos em lotes de 20, sem cache, garantindo dados sempre atualizados.

## Componentes

### 1. Backend - API Assíncrona
**Arquivo:** `app/carteira/routes/ruptura_api_async.py`
- Endpoint `/api/ruptura/analisar-lote-async` processa lotes de pedidos
- Processamento paralelo com ThreadPoolExecutor (5 workers por padrão)
- Sem cache - dados sempre frescos
- Retorna todos os resultados de uma vez

### 2. Frontend - JavaScript
**Arquivo:** `app/static/carteira/js/ruptura-estoque-async.js`
- Coleta todos os pedidos da tela
- Envia para análise em lote único
- Renderiza resultados assim que chegam
- Visual diferenciado por criticidade (cores)
- Modal para detalhes de ruptura

### 3. Workers (Opcional)
**Arquivo:** `app/portal/workers/ruptura_jobs.py`
- Processamento com Redis Queue se necessário
- Pode ser usado para jobs muito grandes

## Como Usar

### 1. No Template HTML
```html
<!-- Incluir o script assíncrono -->
<script src="{{ url_for('static', filename='carteira/js/ruptura-estoque-async.js') }}"></script>
```

### 2. Iniciar Workers (Opcional)
```bash
# Se quiser usar Redis Queue
python start_workers.py

# Ou com variáveis de ambiente
NUM_WORKERS=4 python start_workers.py
```

## Fluxo de Funcionamento

1. **Carregamento da Página**
   - JavaScript identifica todos os pedidos na tabela
   - Adiciona indicadores de "Aguardando análise..."

2. **Processamento em Lote**
   - Envia todos os pedidos de uma vez para a API
   - API processa em paralelo (5 threads)
   - Sem cache - sempre dados atualizados

3. **Renderização dos Resultados**
   - Assim que a API retorna, renderiza todos os resultados
   - Cores indicam criticidade:
     - Verde: Estoque OK
     - Vermelho: Ruptura CRÍTICA
     - Amarelo: Ruptura ALTA
     - Azul: Ruptura MÉDIA
     - Cinza: Ruptura BAIXA

4. **Visualização de Detalhes**
   - Clique em "Ver detalhes" abre modal
   - Mostra itens em ruptura
   - Indica datas de produção futuras

## Performance

- **Lotes de 20 pedidos**: Balanceamento entre performance e memória
- **5 workers paralelos**: Processamento rápido sem sobrecarregar
- **Sem cache**: Dados sempre atualizados
- **Tempo médio**: ~50-100ms por pedido

## Vantagens

1. **Dados sempre atualizados** - Sem cache desatualizado
2. **Performance otimizada** - Processamento paralelo
3. **Interface responsiva** - Não trava durante análise
4. **Visual intuitivo** - Cores indicam urgência
5. **Detalhamento completo** - Modal com todas informações

## Configuração

### Variáveis de Ambiente (Opcionais)
```bash
# Número de workers paralelos (padrão: 5)
MAX_WORKERS=10

# Tamanho do lote (padrão: 20)
BATCH_SIZE=50
```

## Manutenção

### Para adicionar novos campos na análise:
1. Editar `analisar_pedido_individual()` em `ruptura_api_async.py`
2. Adicionar campos no retorno do resultado
3. Atualizar renderização em `ruptura-estoque-async.js`

### Para ajustar performance:
1. Modificar `tamanhoLote` no JavaScript (padrão: 20)
2. Modificar `max_workers` na API (padrão: 5)

## Troubleshooting

**Problema:** Análise muito lenta
**Solução:** Aumentar `max_workers` ou reduzir `tamanhoLote`

**Problema:** Memória alta
**Solução:** Reduzir `tamanhoLote` ou `max_workers`

**Problema:** Dados desatualizados
**Solução:** Já resolvido - sem cache!