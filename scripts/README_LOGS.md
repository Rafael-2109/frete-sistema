# 🔍 Busca de Logs - Guia Rápido

## ⚡ Uso Rápido

O script já está configurado com suas credenciais do `.env`. Basta executar:

```bash
# Buscar webhooks das últimas 24h
python scripts/buscar_logs_webhooks.py --horas 24

# Buscar apenas webhooks de NFe
python scripts/buscar_logs_webhooks.py --tipo nfe

# Buscar webhooks rejeitados (erros de segurança)
python scripts/buscar_logs_webhooks.py --rejeitados

# Buscar logs de uma NFe específica
python scripts/buscar_logs_webhooks.py --nfe 12345

# Buscar com detalhes completos
python scripts/buscar_logs_webhooks.py --verbose --stats
```

## 📊 Exemplos Práticos

### 1. Investigar por que um webhook foi rejeitado
```bash
python scripts/buscar_logs_webhooks.py --rejeitados --verbose
```

Resultado mostrará:
- IP de origem
- Motivo da rejeição (X-Hub-Secret inválido, etc)
- Timestamp exato

### 2. Rastrear processamento de uma NFe
```bash
python scripts/buscar_logs_webhooks.py --nfe 12345
```

Você verá toda a jornada:
1. 🔔 Webhook recebido
2. ✅ Validação de segurança
3. 📦 Dados extraídos
4. 🔍 Busca na API TagPlus
5. ✅ NFe processada com X itens

### 3. Monitorar volume de webhooks
```bash
python scripts/buscar_logs_webhooks.py --horas 72 --stats
```

Estatísticas incluem:
- Total de webhooks recebidos
- Quantos validados vs rejeitados
- Webhooks por endpoint (/nfe, /cliente)
- IPs de origem
- NFes processadas

### 4. Exportar para análise
```bash
python scripts/buscar_logs_webhooks.py --horas 168 --exportar webhooks_semana.json
```

## 🎯 Casos de Uso Reais

### Webhook não chegou?
```bash
# Verificar últimas 2h
python scripts/buscar_logs_webhooks.py --horas 2 --verbose
```

### NFe não foi processada?
```bash
# Rastrear NFe específica
python scripts/buscar_logs_webhooks.py --nfe <numero>
```

Verificar:
- [ ] Webhook foi recebido?
- [ ] Passou na validação de segurança?
- [ ] API TagPlus retornou dados?
- [ ] Houve erro no processamento?

### Muitos webhooks rejeitados?
```bash
# Ver todos os rejeitados
python scripts/buscar_logs_webhooks.py --rejeitados --stats
```

Causas comuns:
- X-Hub-Secret incorreto no TagPlus
- IP bloqueado
- Payload malformado

## 🛠️ Teste Rápido

```bash
# Executar teste básico
./scripts/testar_logs.sh
```

## 📝 Ajuda Completa

```bash
python scripts/buscar_logs_webhooks.py --help
```

## 🔧 Configuração

As credenciais já estão no [.env](.env:57):
- `RENDER_API_KEY`: API Key do Render
- `RENDER_SERVICE_ID`: ID do serviço (srv-d13m38vfte5s738t6p60)

## 📚 Documentação Completa

Ver [GUIA_BUSCA_LOGS.md](GUIA_BUSCA_LOGS.md) para comandos avançados e troubleshooting.

## 🎓 Dicas

1. **Use `--stats`** para ter uma visão geral primeiro
2. **Use `--verbose`** para investigar problemas específicos
3. **Use `--exportar`** para análises offline
4. **Combine opções**: `--tipo nfe --horas 48 --stats`
