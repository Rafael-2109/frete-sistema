# 🗺️ MAPA COMPLETO DO FLUXO BACKEND - SINCRONIZAÇÃO ODOO

## 📊 VISÃO GERAL DO FLUXO

```
ODOO → API Gateway → Autenticação → Rotas → Validação → Processamento → Alertas → BD
```

## 🔑 1. AUTENTICAÇÃO (app/api/odoo/auth.py)

### 1.1 Middleware de Autenticação
```python
@odoo_bp.before_request
def verify_authentication():
    # 1. require_api_key() - Verifica X-API-Key header
    # 2. require_jwt_token() - Verifica Bearer token
```

### 1.2 Funções de Autenticação
- `require_api_key()` - Valida API key no header
- `require_jwt_token()` - Valida JWT token
- `generate_jwt_token()` - Gera tokens para teste
- `validate_permissions()` - Verifica permissões
- `check_rate_limit()` - Controle de rate limiting

## 🛣️ 2. ROTAS PRINCIPAIS (app/api/odoo/routes.py)

### 2.1 Rota de Sincronização da Carteira
```
POST /api/v1/odoo/carteira/bulk-update
```

**Fluxo Principal:**
1. `bulk_update_carteira()` - Função principal
2. Validação de entrada (items obrigatório)
3. Pre-sincronização check via `MonitoramentoSincronizacao.pre_sincronizacao_check()`
4. Validação individual via `validate_carteira_data()`
5. Processamento em lote via `process_bulk_operation()`
6. Pós-sincronização check via `MonitoramentoSincronizacao.pos_sincronizacao_check()`
7. Registro de métricas via `MetricasCarteira.registrar_sincronizacao_odoo()`

### 2.2 Funções de Processamento da Carteira
- `_process_carteira_item()` - Processa item individual
- `_update_carteira_item()` - Atualiza item existente
- `_create_carteira_item()` - Cria novo item
- `_sync_carteira_copia()` - Sincroniza com tabela cópia

### 2.3 Rota de Sincronização do Faturamento
```
POST /api/v1/odoo/faturamento/bulk-update
```

**Fluxo Principal:**
1. `bulk_update_faturamento()` - Função principal
2. Validação de tipo (consolidado/produto)
3. Validação via `validate_faturamento_data()`
4. Processamento via `_process_faturamento_consolidado_item()` ou `_process_faturamento_produto_item()`

## ✅ 3. VALIDADORES (app/api/odoo/validators.py)

### 3.1 validate_carteira_data()
**Campos Obrigatórios:**
- num_pedido, cod_produto, nome_produto
- qtd_produto_pedido, qtd_saldo_produto_pedido
- cnpj_cpf, preco_produto_pedido

**Validações:**
- CNPJ/CPF formato (11 ou 14 dígitos)
- Quantidades positivas
- Saldo não pode exceder quantidade total

### 3.2 validate_faturamento_data()
**Campos Obrigatórios (Consolidado):**
- numero_nf, data_fatura, cnpj_cliente, nome_cliente
- valor_total, origem

**Campos Obrigatórios (Produto):**
- Todos acima + cod_produto, nome_produto
- qtd_produto_faturado, preco_produto_faturado, valor_produto_faturado

## 🛠️ 4. UTILITÁRIOS (app/api/odoo/utils.py)

### 4.1 Funções Principais
- `create_response()` - Resposta padronizada da API
- `process_bulk_operation()` - Processamento em lote com controle de transações
- `validate_date_format()` - Normaliza datas
- `sanitize_string()` - Sanitiza strings
- `validate_numeric()` - Valida números
- `batch_commit()` - Commit em lotes
- `validate_cnpj()` - Valida CNPJ brasileiro
- `measure_execution_time()` - Decorator para medir tempo

## 🚨 5. SISTEMA DE ALERTAS (app/carteira/alert_system.py)

### 5.1 Classe AlertaSistemaCarteira
**Métodos Principais:**
- `verificar_separacoes_cotadas_antes_sincronizacao()` - Verifica separações COTADAS
- `detectar_alteracoes_separacao_cotada_pos_sincronizacao()` - Detecta alterações críticas
- `gerar_alerta_critico()` - Gera alertas padronizados
- `gerar_alerta_pre_separacao_conflito()` - Alertas de constraint
- `gerar_alerta_quantidade_insuficiente()` - Alertas de quantidade

### 5.2 Classe MonitoramentoSincronizacao
- `pre_sincronizacao_check()` - Verificações pré-sync
- `pos_sincronizacao_check()` - Verificações pós-sync

## 📊 6. MONITORAMENTO (app/carteira/monitoring.py)

### 6.1 Classe MetricasCarteira
- `registrar_operacao_pre_separacao()` - Métricas de pré-separação
- `registrar_sincronizacao_odoo()` - Métricas de sincronização
- `registrar_calculo_estoque()` - Métricas de estoque

### 6.2 Classe AuditoriaCarteira
- `registrar_alteracao_pre_separacao()` - Auditoria de alterações
- `registrar_violacao_constraint()` - Registro de violações
- `registrar_alerta_critico()` - Registro de alertas

### 6.3 Decorators
- `@monitorar_performance()` - Monitora performance
- `@auditar_alteracao()` - Audita alterações

## 💾 7. MODELOS DE DADOS

### 7.1 CarteiraPrincipal (app/carteira/models.py)
**Campos Chave:**
- num_pedido, cod_produto (chave única composta)
- qtd_saldo_produto_pedido (quantidade disponível)
- separacao_lote_id (vínculo com separação)
- Campos de projeção D0-D28

### 7.2 PreSeparacaoItem (app/carteira/models.py)
**Funcionalidade Crítica:**
- Sobrevive à reimportação do Odoo
- Métodos de redução/aumento de quantidade
- Sistema de recomposição

**Métodos Importantes:**
- `aplicar_reducao_quantidade()` - Hierarquia: Saldo livre → Pré-separação → Separação ABERTO → COTADO
- `aplicar_aumento_quantidade()` - Lógica total/parcial
- `detectar_tipo_envio_automatico()` - Detecta tipo de envio

### 7.3 Separacao (app/separacao/models.py)
- separacao_lote_id (identificador único)
- tipo_envio (total/parcial)
- Sem campo status (usa Pedido.status via JOIN)

### 7.4 Pedido (app/pedidos/models.py)
- separacao_lote_id (vínculo com separação)
- status (ABERTO, COTADO, EMBARCADO, FATURADO, NF no CD)
- Propriedade status_calculado

### 7.5 FaturamentoProduto (app/faturamento/models.py)
- numero_nf, cod_produto (identificadores)
- Dados do produto faturado

## 📝 8. LOGGING (app/utils/logging_config.py)

### 8.1 Funções de Logging
- `setup_logging()` - Configura sistema
- `@log_performance()` - Decorator de performance
- `log_system_status()` - Status do sistema
- `log_database_query()` - Queries do BD
- `log_error()` - Erros detalhados

## 🔄 9. FLUXO DE SINCRONIZAÇÃO DETALHADO

### 9.1 Recebimento da Requisição
1. API Gateway recebe POST
2. Middleware valida autenticação (API Key + JWT)
3. Rate limiting verificado

### 9.2 Processamento da Carteira
1. **PRÉ-SINCRONIZAÇÃO:**
   - Verifica separações COTADAS
   - Emite alertas se necessário

2. **VALIDAÇÃO:**
   - Cada item validado individualmente
   - Erros coletados e retornados

3. **PROCESSAMENTO:**
   - Busca item existente por num_pedido + cod_produto
   - Se existe: atualiza com lógica de redução/aumento
   - Se não existe: cria novo

4. **LÓGICA DE QUANTIDADE (CRÍTICA):**
   - REDUÇÃO: Aplica hierarquia (saldo livre → pré-sep → sep ABERTO → COTADO)
   - AUMENTO: Verifica tipo (total/parcial) e atualiza apropriadamente

5. **PÓS-SINCRONIZAÇÃO:**
   - Detecta alterações em separações COTADAS
   - Gera alertas críticos se necessário
   - Registra métricas

### 9.3 Processamento do Faturamento
1. Validação de tipo (consolidado/produto)
2. Busca por chave única (numero_nf ou numero_nf + cod_produto)
3. Atualiza ou cria registro
4. Commit no banco

## ⚠️ 10. PONTOS CRÍTICOS E ALERTAS

### 10.1 Separações COTADAS
- Máxima prioridade de preservação
- Alertas críticos se afetadas
- Log especial para rastreabilidade

### 10.2 Hierarquia de Consumo
1. Saldo livre (sem separação)
2. Pré-separações (mais recentes primeiro)
3. Separações ABERTO
4. Separações COTADO (com alerta crítico)

### 10.3 Constraint Única de Pré-Separação
- num_pedido + cod_produto + data_expedicao + data_agendamento + protocolo
- Permite múltiplas pré-separações com contextos diferentes

## 🔐 11. SEGURANÇA

### 11.1 Autenticação Dupla
- API Key para identificação
- JWT Token para autorização

### 11.2 Rate Limiting
- Controle por API Key
- Armazenamento em memória (produção: Redis)

### 11.3 Validação de Dados
- Sanitização de strings
- Validação de tipos
- Limites de tamanho

## 📈 12. PERFORMANCE

### 12.1 Processamento em Lote
- Transações agrupadas
- Log a cada 100 itens
- Rollback em caso de erro

### 12.2 Índices de Banco
- Chaves compostas para consultas rápidas
- Índices em campos de filtro frequente

### 12.3 Monitoramento
- Tempo de execução medido
- Alertas para operações lentas
- Métricas de memória

## 🔧 13. MANUTENÇÃO E TROUBLESHOOTING

### 13.1 Logs Detalhados
- Cada operação registrada
- Contexto completo em erros
- Rastreabilidade total

### 13.2 Sistema de Alertas
- Notificações para situações críticas
- Integração futura com webhooks/email

### 13.3 Auditoria
- Todas alterações registradas
- Usuário e timestamp
- Estado anterior e novo