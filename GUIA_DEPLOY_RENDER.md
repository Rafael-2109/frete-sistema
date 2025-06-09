# 🚀 Guia de Deploy - Sistema de Fretes no Render

## 📋 Pré-requisitos

- [x] ✅ Sistema limpo (apenas usuário Rafael)
- [x] ✅ Arquivos de teste removidos
- [x] ✅ Backup de segurança criado
- [x] ✅ Procfile criado
- [x] ✅ render.yaml configurado
- [x] ✅ requirements.txt atualizado

## 🔧 Passos para Deploy

### 1. 📚 Repositório GitHub

1. **Criar repositório no GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Sistema de Fretes - versão produção"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/sistema-fretes.git
   git push -u origin main
   ```

2. **Adicionar .gitignore:**
   ```
   __pycache__/
   *.py[cod]
   *$py.class
   instance/
   .env
   venv/
   env/
   .venv/
   flask_session/
   *.db
   *.log
   .DS_Store
   Thumbs.db
   uploads/
   ```

### 2. 🌐 Configuração no Render

1. **Acessar render.com** e fazer login
2. **Conectar repositório GitHub**
3. **Escolher "Blueprint"** e selecionar o arquivo `render.yaml`
4. **Configurar variáveis de ambiente:**

#### Variáveis Obrigatórias:
| Variável | Valor |
|----------|-------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | Gerar chave forte |
| `PYTHON_VERSION` | `3.11.0` |

#### Variáveis Automáticas:
- `DATABASE_URL` - Será gerada automaticamente pelo PostgreSQL

### 3. 🗄️ Banco de Dados PostgreSQL

O Render criará automaticamente um banco PostgreSQL gratuito com:
- **Nome:** sistema-fretes-db
- **Usuário:** sistema_user
- **Plano:** Free (100MB)

### 4. 🔄 Migração de Dados

#### Após primeiro deploy bem-sucedido:

1. **Acessar o Shell do Render:**
   ```bash
   flask shell
   ```

2. **Criar usuário administrador:**
   ```python
   from app.auth.models import Usuario
   from app import db
   from werkzeug.security import generate_password_hash
   from datetime import datetime
   
   admin = Usuario(
       nome='Rafael de Carvalho Nascimento',
       email='rafael@nacomgoya.com.br',
       senha_hash=generate_password_hash('Rafa2109'),
       perfil='administrador',
       status='ativo',
       empresa='NACOM GOYA',
       cargo='Administrador',
       telefone='(64) 99999-9999',
       criado_em=datetime.now(),
       aprovado_em=datetime.now(),
       aprovado_por='Sistema'
   )
   
   db.session.add(admin)
   db.session.commit()
   print("Usuário administrador criado!")
   ```

### 5. 📊 Importação de Dados Reais

Após sistema no ar, criar rotinas para importar:

1. **Transportadoras**
2. **Faturamento histórico**
3. **Pedidos em andamento**
4. **Dados de fretes**
5. **Configurações específicas**

### 6. 🔐 Configurações de Segurança

1. **Configurar domínio personalizado** (se disponível)
2. **Certificado SSL** (automático no Render)
3. **Backup automático** do PostgreSQL
4. **Monitoramento de logs**

## 📁 Estrutura de Arquivos para Deploy

```
sistema-fretes/
├── app/                    # Aplicação Flask
├── migrations/             # Migrações do banco
├── instance/              # (ignorado no git)
├── Procfile               # Comando para iniciar app
├── render.yaml            # Configuração do Render
├── requirements.txt       # Dependências Python
├── config.py             # Configurações
├── run.py                # Ponto de entrada
└── README.md             # Documentação
```

## 🔍 Comandos Úteis

### Logs do Render:
```bash
# Ver logs em tempo real
render logs --service sistema-fretes

# Acessar shell
render shell --service sistema-fretes
```

### Comandos Flask no Render:
```bash
# Migração do banco
flask db upgrade

# Shell interativo
flask shell

# Criar usuário
flask create-admin
```

## 🚨 Troubleshooting

### Problemas Comuns:

1. **Erro de dependências:**
   - Verificar requirements.txt
   - Atualizar versões se necessário

2. **Erro de banco:**
   - Verificar se DATABASE_URL está configurada
   - Rodar migrações manualmente

3. **Erro de importação:**
   - Verificar estrutura de pastas
   - Verificar __init__.py em todas as pastas

4. **Erro de SECRET_KEY:**
   - Gerar nova chave secreta forte
   - Configurar nas variáveis de ambiente

## 🎯 Pós-Deploy

### Lista de Verificação:

- [ ] ✅ Sistema acessível via URL
- [ ] ✅ Login funcionando
- [ ] ✅ PostgreSQL conectado
- [ ] ✅ Usuário admin criado
- [ ] ✅ Templates carregando
- [ ] ✅ Upload de arquivos funcionando
- [ ] ✅ Todas as rotas acessíveis
- [ ] ✅ Logs sem erros críticos

### Próximos Passos:

1. **Configurar domínio personalizado**
2. **Importar dados históricos**
3. **Treinar usuários**
4. **Monitorar performance**
5. **Configurar backups**

## 📞 Suporte

Em caso de problemas:
1. Verificar logs do Render
2. Testar localmente primeiro
3. Verificar documentação do Render
4. Contatar suporte se necessário

---

**🎉 Sistema pronto para produção!** 