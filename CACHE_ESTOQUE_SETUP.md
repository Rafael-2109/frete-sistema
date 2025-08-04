# 📦 Sistema de Cache de Estoque - Guia de Configuração

## 🎯 Visão Geral

O sistema de cache de estoque otimiza consultas de saldo para performance < 1 segundo, considerando:
- ✅ **Códigos Unificados**: Agrupa produtos com códigos relacionados
- ✅ **Performance Otimizada**: Consultas pré-calculadas
- ✅ **Atualização Incremental**: Mantém cache atualizado automaticamente

## 🚀 Configuração Inicial

### 1. Local (Desenvolvimento)

```bash
# Inicializar cache pela primeira vez
flask inicializar-cache-estoque

# Ou usando Python diretamente
python inicializar_cache_estoque.py
```

### 2. Render (Produção)

#### Opção A: Comando Flask via Shell

```bash
# No console do Render
flask inicializar-cache-estoque
```

#### Opção B: Script Python

```bash
# No console do Render
python inicializar_cache_render.py
```

#### Opção C: Via API (se configurado)

```bash
# Fazer POST para endpoint protegido
curl -X POST https://seu-app.onrender.com/estoque/saldo-estoque-v2/atualizar-cache \
  -H "Content-Type: application/json" \
  -d '{"tipo": "completo"}' \
  --cookie "session=..."
```

## 📊 Funcionalidades do Cache

### Dados Armazenados

1. **Saldo Atual**: Soma de todas as movimentações
2. **Quantidades em Carteira**: Itens pendentes
3. **Quantidades em Pré-Separação**: Itens selecionados
4. **Quantidades em Separação**: Itens em processo
5. **Status de Ruptura**: CRÍTICO, ATENÇÃO ou OK
6. **Projeção 29 dias**: Previsão de estoque futuro

### Códigos Unificados

O sistema **automaticamente agrupa** produtos relacionados:

```python
# Exemplo: Produtos 1001, 1002, 1003 são unificados
# O cache mostra saldo total considerando todos os códigos
Código Principal: 1001
Saldo Total: 500 (soma de 1001 + 1002 + 1003)
```

## 🔄 Manutenção do Cache

### Atualização Automática

O cache é atualizado automaticamente quando:
- Nova movimentação de estoque
- Alteração em carteira
- Mudança em separações

### Atualização Manual

```bash
# Atualizar produto específico
flask atualizar-cache-estoque --produto 1001

# Atualizar todos os produtos
flask atualizar-cache-estoque
```

## 🛠️ Comandos Disponíveis

### CLI (Flask)

| Comando | Descrição |
|---------|-----------|
| `flask inicializar-cache-estoque` | Recria todo o cache (com confirmação) |
| `flask atualizar-cache-estoque` | Atualiza cache existente |
| `flask atualizar-cache-estoque --produto CODE` | Atualiza produto específico |

### API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/estoque/saldo-estoque-v2` | GET | Consulta cache otimizado |
| `/estoque/saldo-estoque-v2/api/produto/<codigo>` | GET | Detalhes de produto |
| `/estoque/saldo-estoque-v2/atualizar-cache` | POST | Atualiza cache (admin) |
| `/estoque/saldo-estoque-v2/status-cache` | GET | Status do cache |

## 📈 Performance

### Antes do Cache
- Consulta de saldo: 5-10 segundos
- 100+ queries ao banco
- Alto uso de CPU

### Com Cache
- Consulta de saldo: < 1 segundo
- 1-3 queries ao banco
- Baixo uso de CPU

## 🚨 Troubleshooting

### Erro: Chave Duplicada

**Problema**: `duplicate key value violates unique constraint`

**Solução**: O sistema já trata automaticamente, mas se persistir:
```bash
# Limpar e recriar cache
flask inicializar-cache-estoque
```

### Cache Desatualizado

**Problema**: Valores não refletem realidade

**Solução**:
```bash
# Forçar atualização completa
flask atualizar-cache-estoque
```

### Performance Degradada

**Problema**: Consultas lentas mesmo com cache

**Solução**:
```bash
# Verificar status do cache
curl https://seu-app.onrender.com/estoque/saldo-estoque-v2/status-cache
```

## 🔐 Segurança

- Apenas **admins** podem recriar cache completo
- Atualização incremental é automática
- Logs de todas as operações

## 📋 Checklist de Deploy

- [ ] Criar tabelas de cache com migração
- [ ] Executar `flask inicializar-cache-estoque`
- [ ] Verificar em `/estoque/saldo-estoque-v2`
- [ ] Monitorar performance inicial
- [ ] Configurar job periódico (opcional)

## 💡 Dicas

1. **Primeira Execução**: Pode demorar 2-5 minutos dependendo do volume
2. **Projeções**: Calcule apenas para produtos críticos
3. **Monitoramento**: Verifique `/estoque/saldo-estoque-v2/status-cache` regularmente
4. **Códigos Unificados**: Sistema agrupa automaticamente produtos relacionados

## 🔗 Referências

- Modelo: `app/estoque/models_cache.py`
- Rotas: `app/estoque/routes_cache.py`
- CLI: `app/cli.py`
- Triggers: `app/estoque/cache_triggers.py`