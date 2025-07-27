# Deploy no Render - Sistema de Permissões

## Configuração Inicial

### 1. Variáveis de Ambiente Necessárias

```bash
DATABASE_URL=postgresql://...
SECRET_KEY=sua-chave-secreta
FLASK_ENV=production

# Opcional: para setup automático do admin
SETUP_ADMIN=true
ADMIN_EMAIL=rafael6250@gmail.com
```

### 2. Build Command no Render

```bash
pip install -r requirements.txt && flask db upgrade
```

### 3. Start Command

```bash
gunicorn app:app
```

## Configuração do Admin

### Opção 1: Manual (Recomendado)

Após o deploy, execute no Shell do Render:

```bash
python scripts/setup_admin_production.py rafael6250@gmail.com
```

### Opção 2: Automático no Deploy

1. Adicione as variáveis de ambiente:
   - `SETUP_ADMIN=true`
   - `ADMIN_EMAIL=rafael6250@gmail.com`

2. Use este Build Command:
```bash
pip install -r requirements.txt && flask db upgrade && bash scripts/render_post_deploy.sh
```

## Processo de Migração

O sistema executará automaticamente:

1. **Migrações do Flask-Migrate**: Cria/atualiza estrutura das tabelas
2. **Script de Migração de Dados**: Popula categorias e permissões iniciais
3. **Setup do Admin**: Configura usuário como administrador

## Verificação

Após o deploy, acesse:

1. `/auth/login` - Faça login com sua conta
2. `/permissions/admin` - Interface de administração
3. `/permissions/hierarchical` - Nova UI hierárquica

## Troubleshooting

### Erro: "Usuário não encontrado"
- Certifique-se de criar a conta primeiro em `/auth/register`
- Depois execute o script de admin

### Erro: "Coluna perfil_id não existe"
- O script criará automaticamente as colunas necessárias
- Se falhar, execute manualmente no Shell:

```python
from app import create_app, db
app = create_app()
with app.app_context():
    db.session.execute("ALTER TABLE usuarios ADD COLUMN perfil_id INTEGER")
    db.session.execute("ALTER TABLE usuarios ADD COLUMN perfil_nome VARCHAR(50)")
    db.session.commit()
```

### Verificar se é Admin

No Shell do Render:

```python
from app import create_app
from app.auth.models import Usuario

app = create_app()
with app.app_context():
    user = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
    print(f"Admin: {user.perfil_nome == 'admin'}")
```

## Manutenção

### Adicionar Novos Admins

```bash
python scripts/setup_admin_production.py novo_admin@email.com
```

### Remover Admin

```python
from app import create_app, db
from app.auth.models import Usuario

app = create_app()
with app.app_context():
    user = Usuario.query.filter_by(email='email@example.com').first()
    user.perfil_id = None
    user.perfil_nome = None
    db.session.commit()
```