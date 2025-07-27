# Instruções de Migração - Sistema de Permissões

## 📋 Processo Correto de Migração

### 1. Gerar a Migration com Flask-Migrate
```bash
# Primeiro, gere a migration automática
flask db migrate -m "Add hierarchical permission system"
```

### 2. Revisar e Ajustar a Migration
```bash
# Verifique o arquivo gerado em migrations/versions/
# Ele terá um nome como: xxxx_add_hierarchical_permission_system.py
```

### 3. Aplicar a Migration
```bash
# Aplique as alterações no banco
flask db upgrade
```

### 4. Executar o Script de Dados
```bash
# SOMENTE DEPOIS de aplicar a migration, execute o script de dados
python migrations/upgrade_permissions_system.py
```

## 🔄 Ordem de Execução

1. **flask db migrate** - Gera as alterações de estrutura do banco
2. **flask db upgrade** - Aplica as alterações de estrutura
3. **python migrations/upgrade_permissions_system.py** - Popula dados e faz ajustes

## ⚠️ Importante

- O script `upgrade_permissions_system.py` é um **complemento** à migration do Flask
- Ele **NÃO substitui** o processo padrão do Flask-Migrate
- Use o script apenas para:
  - Popular dados iniciais
  - Migrar dados existentes
  - Criar categorias e templates padrão

## 🚨 Se der erro no migrate

Se o `flask db migrate` não detectar mudanças:

```bash
# Force a detecção de novas tabelas
flask db stamp head
flask db migrate -m "Add hierarchical permission system" --rev-id permission_v1

# Ou edite manualmente a migration gerada
```

## 📝 Checklist

- [ ] Executar `flask db migrate -m "Add hierarchical permission system"`
- [ ] Revisar arquivo de migration gerado
- [ ] Executar `flask db upgrade`
- [ ] Executar `python migrations/upgrade_permissions_system.py`
- [ ] Testar novo sistema em `/permissions/hierarchical`