#!/usr/bin/env python3
"""
Script para corrigir manualmente data_provider.py com padrão consistente
"""

# Padrão correto para propriedades com fallback
property_template = '''    @property
    def {name}(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("{name}")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock
'''

# Lista de modelos para criar propriedades
models = ["Pedido", "Embarque", "EmbarqueItem", "EntregaMonitorada", 
          "RelatorioFaturamentoImportado", "Transportadora", "Frete"]

# Ler arquivo original
with open("app/claude_ai_novo/providers/data_provider.py", 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar onde começam as propriedades
start_line = 0
for i, line in enumerate(lines):
    if "def db(self):" in line:
        # Encontrar o fim da propriedade db
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("@property"):
            j += 1
        start_line = j
        break

# Encontrar onde terminam as propriedades
end_line = 0
for i, line in enumerate(lines):
    if "def __init__(self, loader=None):" in line:
        end_line = i
        break

# Reconstruir arquivo
new_lines = lines[:start_line]

# Adicionar todas as propriedades com formato correto
for model in models:
    new_lines.append(property_template.format(name=model) + "\n")

# Adicionar o resto do arquivo
new_lines.extend(lines[end_line:])

# Salvar arquivo corrigido
with open("app/claude_ai_novo/providers/data_provider.py", 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ data_provider.py corrigido manualmente!")
print("✅ Todas as propriedades de modelo agora têm formato consistente.")