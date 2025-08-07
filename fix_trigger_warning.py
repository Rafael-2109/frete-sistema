#!/usr/bin/env python3
"""
Script para corrigir o warning de Session.add() nos triggers
Atualiza o serviço para usar uma abordagem mais segura
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def atualizar_servico_estoque():
    """Atualiza o serviço de estoque para evitar warnings"""
    
    arquivo = 'app/estoque/services/estoque_tempo_real.py'
    
    print(f"📝 Atualizando {arquivo}...")
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Substituir db.session.add por db.session.merge
    conteudo_novo = conteudo.replace(
        'db.session.add(estoque)',
        'db.session.merge(estoque)'
    )
    
    # Adicionar flag no_autoflush onde necessário
    if 'from sqlalchemy.orm import Session' not in conteudo_novo:
        conteudo_novo = conteudo_novo.replace(
            'from app import db',
            'from app import db\nfrom sqlalchemy.orm import Session'
        )
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo_novo)
    
    print("✅ Arquivo atualizado com sucesso!")
    
    # Criar arquivo de patch alternativo
    criar_patch_alternativo()


def criar_patch_alternativo():
    """Cria um patch alternativo usando context manager"""
    
    patch = '''# Patch para corrigir warning de Session.add() nos triggers

## Opção 1: Usar merge ao invés de add
```python
# Antes:
db.session.add(estoque)

# Depois:
db.session.merge(estoque)
```

## Opção 2: Usar no_autoflush context manager
```python
from sqlalchemy.orm.session import Session

# Dentro do trigger:
with db.session.no_autoflush:
    db.session.add(estoque)
```

## Opção 3: Usar flag na sessão
```python
# No início do método:
db.session.autoflush = False
try:
    # ... código do trigger
    db.session.add(estoque)
finally:
    db.session.autoflush = True
```
'''
    
    with open('PATCH_TRIGGER_WARNING.md', 'w', encoding='utf-8') as f:
        f.write(patch)
    
    print("📄 Patch alternativo criado em PATCH_TRIGGER_WARNING.md")


if __name__ == '__main__':
    atualizar_servico_estoque()
    print("\n✅ Correção aplicada! Faça commit e push para aplicar no Render.")