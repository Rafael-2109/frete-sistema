# 🚀 GUIA DE DEPLOYMENT - SISTEMA DE ESTOQUE EM TEMPO REAL

## 📋 PRÉ-REQUISITOS

### Dependências do Sistema
- Python 3.8+
- PostgreSQL 12+ (produção) ou SQLite (desenvolvimento)
- Redis (opcional, para cache adicional)

### Pacotes Python Necessários
```bash
pip install -r requirements.txt
```

Se não existir requirements.txt, instalar:
```bash
pip install flask flask-sqlalchemy flask-login flask-wtf flask-migrate
pip install psycopg2-binary python-dotenv pandas
pip install apscheduler  # Para job de fallback
```

## 🏠 CONFIGURAÇÃO LOCAL (DESENVOLVIMENTO)

### 1. Configurar Variáveis de Ambiente
Criar arquivo `.env` na raiz do projeto:
```bash
# Desenvolvimento Local
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-mudar-em-producao

# Banco de Dados Local (SQLite)
DATABASE_URL=sqlite:///frete_sistema.db

# Ou PostgreSQL Local
# DATABASE_URL=postgresql://usuario:senha@localhost/frete_sistema_dev
```

### 2. Criar/Migrar Banco de Dados
```bash
# Criar tabelas do novo sistema
flask db init  # Se ainda não foi inicializado
flask db migrate -m "Add EstoqueTempoReal and MovimentacaoPrevista"
flask db upgrade

# Migrar dados existentes para novo sistema
python scripts/migrar_para_tempo_real.py
```

### 3. Testar Sistema
```bash
# Testar performance
python test_performance_tempo_real.py

# Rodar aplicação localmente
flask run
# ou
python run.py
```

### 4. Verificar Funcionamento
- Acessar: http://localhost:5000
- Testar telas:
  - `/estoque/saldo-estoque` - Dashboard de estoque
  - `/carteira/workspace` - Workspace de montagem
  - API: `/api/estoque/tempo-real/estatisticas`

## 🌐 CONFIGURAÇÃO PRODUÇÃO

### 1. Variáveis de Ambiente (Render/Heroku)
Configurar no painel do serviço:
```bash
# Produção
FLASK_ENV=production
SECRET_KEY=chave-secreta-forte-gerada-aleatoriamente
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Configurações Adicionais
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_POOL_TIMEOUT=30
SQLALCHEMY_POOL_RECYCLE=1800
SQLALCHEMY_MAX_OVERFLOW=20

# Desabilitar logs verbosos
SQLALCHEMY_ECHO=false
```

### 2. Script de Deploy Automático
Criar arquivo `deploy.sh`:
```bash
#!/bin/bash
echo "🚀 Iniciando deploy..."

# 1. Migrar banco de dados
echo "📊 Migrando banco de dados..."
flask db upgrade

# 2. Migrar dados para novo sistema (primeira vez)
if [ "$RUN_MIGRATION" = "true" ]; then
    echo "🔄 Migrando dados para sistema de tempo real..."
    python scripts/migrar_para_tempo_real.py
fi

# 3. Coletar arquivos estáticos (se houver)
# flask collect-static

echo "✅ Deploy concluído!"
```

### 3. Configuração Render.yaml
```yaml
services:
  - type: web
    name: frete-sistema
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn run:app"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DATABASE_URL
        fromDatabase:
          name: frete-db
          property: connectionString
    autoDeploy: true

databases:
  - name: frete-db
    databaseName: frete_sistema
    user: frete_user
    plan: starter
```

### 4. Procfile (Heroku)
```
web: gunicorn run:app --workers 4 --threads 2
release: bash deploy.sh
```

## 🔧 CONFIGURAÇÕES IMPORTANTES

### 1. Job de Fallback
O job de fallback é configurado automaticamente em `app/__init__.py`:
```python
# Roda a cada 60 segundos
# Recalcula 10 produtos mais antigos
# Garante consistência dos dados
```

### 2. Triggers Automáticos
Os triggers são registrados automaticamente ao iniciar:
- MovimentacaoEstoque → EstoqueTempoReal
- PreSeparacaoItem → MovimentacaoPrevista
- Separacao → MovimentacaoPrevista
- ProgramacaoProducao → MovimentacaoPrevista

### 3. Performance
Garantias do sistema:
- Consultas < 100ms
- Atualização em tempo real
- Zero tolerância para dados defasados

## 📝 CHECKLIST DE DEPLOY

### Primeira Vez (Sistema Novo)
- [ ] Configurar variáveis de ambiente
- [ ] Criar banco de dados
- [ ] Rodar migrations: `flask db upgrade`
- [ ] Migrar dados: `python scripts/migrar_para_tempo_real.py`
- [ ] Testar APIs de estoque
- [ ] Verificar job de fallback rodando
- [ ] Testar performance < 100ms

### Atualizações
- [ ] Fazer backup do banco
- [ ] Atualizar código via git
- [ ] Rodar migrations se houver
- [ ] Reiniciar aplicação
- [ ] Verificar logs por erros
- [ ] Testar funcionalidades críticas

## 🐛 TROUBLESHOOTING

### Problema: "ImportError: cannot import name 'models_hibrido'"
**Solução**: Sistema híbrido foi removido. Atualizar código e remover referências.

### Problema: "Tabela estoque_tempo_real não existe"
**Solução**: 
```bash
flask db upgrade
# ou criar manualmente:
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Problema: "Performance > 100ms"
**Solução**:
1. Verificar índices no banco
2. Aumentar pool de conexões
3. Verificar job de fallback rodando
4. Executar: `python test_performance_tempo_real.py`

### Problema: "Dados inconsistentes"
**Solução**:
```bash
# Recalcular produto específico via API
curl -X POST http://localhost:5000/api/estoque/tempo-real/recalcular/PRODUTO_ID

# Ou rodar migração completa novamente
python scripts/migrar_para_tempo_real.py
```

## 📊 MONITORAMENTO

### Endpoints de Health Check
```javascript
GET /api/estoque/tempo-real/estatisticas
// Retorna estatísticas gerais do sistema

GET /health
// Retorna status da aplicação (implementar se necessário)
```

### Logs Importantes
Monitorar no console/logs:
- "✅ Triggers de Estoque Tempo Real registrados"
- "✅ Job de Fallback de Estoque configurado"
- "✅ API de Estoque Tempo Real registrada"

### Métricas Chave
- Total de produtos: `EstoqueTempoReal.query.count()`
- Produtos com ruptura: verificar `dia_ruptura != null`
- Performance média das consultas
- Taxa de execução do job de fallback

## 🔐 SEGURANÇA

### Recomendações
1. **Nunca** commitar `.env` no git
2. Usar secrets manager em produção
3. Rotacionar SECRET_KEY periodicamente
4. Configurar CORS apropriadamente
5. Usar HTTPS sempre em produção
6. Limitar rate de APIs públicas

## 📞 SUPORTE

### Documentação
- `SISTEMA_ESTOQUE_TEMPO_REAL.md` - Arquitetura técnica
- `MIGRACAO_ESTOQUE_TEMPO_REAL.md` - Guia de migração
- `test_performance_tempo_real.py` - Testes de performance

### Comandos Úteis
```bash
# Verificar status do banco
flask db current

# Criar backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restaurar backup
psql $DATABASE_URL < backup_20250806.sql

# Limpar dados de teste
python -c "from app import create_app, db; from app.estoque.models_tempo_real import EstoqueTempoReal; app = create_app(); app.app_context().push(); EstoqueTempoReal.query.filter(EstoqueTempoReal.cod_produto.like('TEST_%')).delete(); db.session.commit()"
```

## ✅ PRONTO PARA PRODUÇÃO!

Sistema completamente configurado e otimizado para deploy.