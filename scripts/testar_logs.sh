#!/bin/bash
# Script rápido para testar busca de logs

echo "🔍 Testando busca de logs de webhooks TagPlus..."
echo ""

# Teste 1: Buscar webhooks das últimas 24h
echo "📊 Buscando webhooks das últimas 24 horas..."
python scripts/buscar_logs_webhooks.py --horas 24 --stats

echo ""
echo "✅ Teste concluído!"
echo ""
echo "💡 Outros comandos úteis:"
echo "  python scripts/buscar_logs_webhooks.py --tipo nfe --horas 48"
echo "  python scripts/buscar_logs_webhooks.py --rejeitados"
echo "  python scripts/buscar_logs_webhooks.py --nfe 12345"
echo "  python scripts/buscar_logs_webhooks.py --verbose"
