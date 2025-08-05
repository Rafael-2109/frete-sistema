# 🚨 INSTRUÇÕES PARA CORRIGIR ERRO PG 1082 NO RENDER

## Problema Identificado

O erro **"Unknown PG numeric type: 1082"** estava ocorrendo porque:
1. Os tipos PostgreSQL eram registrados DEPOIS da criação do SQLAlchemy
2. Isso fazia com que as primeiras conexões não tivessem os tipos registrados
3. O erro aparecia especificamente ao acessar campos DATE em `projecao_estoque_cache`

## Solução Aplicada

### 1. Ordem de Importação Corrigida

No arquivo `app/__init__.py`, agora registramos os tipos PostgreSQL ANTES de criar o SQLAlchemy:

```python
# ANTES (incorreto):
db = SQLAlchemy()  # Criava conexões sem tipos registrados
# ... depois registrava tipos

# AGORA (correto):
# Registra tipos PostgreSQL primeiro
extensions.register_type(extensions.new_type((1082,), "DATE", extensions.DATE))
# ... outros tipos
db = SQLAlchemy()  # Agora todas as conexões têm tipos corretos
```

## Passos para Aplicar no Render

### 1. No Shell do Render (Opcional - para testar)

```bash
# Testar se o problema foi resolvido
python3 test_render_pg1082.py

# Ou aplicar correção manual temporária
python3 fix_render_definitivo.py
```

### 2. Deploy da Correção

```bash
# Fazer push do código corrigido
git add app/__init__.py
git commit -m "fix: corrigir ordem de registro de tipos PostgreSQL para resolver PG 1082"
git push origin main
```

### 3. No Render

1. O deploy automático será iniciado
2. Aguarde a conclusão
3. O erro deve estar resolvido

## Verificação

Após o deploy, acesse:
- https://sistema-fretes.onrender.com/estoque/saldo-estoque

O erro "Unknown PG numeric type: 1082" não deve mais aparecer nos logs.

## Resumo da Correção

- **Problema**: Tipos PostgreSQL registrados DEPOIS do SQLAlchemy
- **Solução**: Registrar tipos ANTES do SQLAlchemy
- **Resultado**: Todas as conexões agora reconhecem o tipo DATE (1082)

## Arquivos Modificados

1. `app/__init__.py` - Ordem de importação corrigida
2. `app/utils/pg_types_config.py` - Mantido como backup
3. Removidas conversões desnecessárias (cast_date, etc.)

A solução agora é simples, limpa e definitiva! 🎯