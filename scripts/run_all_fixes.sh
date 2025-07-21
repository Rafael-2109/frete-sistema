#!/bin/bash

echo "🚀 Executando todas as correções..."

echo "1. Removendo migration problemática..."
python scripts/remove_problematic_migration.py

echo "2. Corrigindo campos equipe_vendas..."
python scripts/fix_equipe_vendas.py

echo "3. Verificando sistema de permissões..."
python scripts/verify_permissions.py

echo "✅ Todas as correções executadas!"