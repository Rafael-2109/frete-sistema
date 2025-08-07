# 📋 INSTRUÇÕES DE DEPLOYMENT - SISTEMA HÍBRIDO DE ESTOQUE

## 🚀 DEPLOYMENT NO RENDER

### Opção 1: Via Render Shell (Recomendado)

1. **Acesse o Render Dashboard**
   - Entre em: https://dashboard.render.com
   - Selecione seu serviço

2. **Abra o Shell**
   - Clique na aba "Shell"
   - Aguarde o terminal carregar

3. **Execute o comando de deployment**
   ```bash
   # Opção A: Se o arquivo deploy_render.sh existir
   bash deploy_render.sh
   
   # Opção B: Executar diretamente o Python
   python deploy_sistema_hibrido.py
   ```

4. **Reinicie o serviço**
   - Após o script terminar com sucesso
   - Clique em "Manual Deploy" → "Deploy latest commit"
   - Ou use: "Settings" → "Restart Service"

### Opção 2: Via Deploy Hook

1. **Configure um Deploy Hook** (se ainda não tiver)
   - Em Settings → Deploy Hooks
   - Adicione ao seu build command:
   ```bash
   pip install -r requirements.txt && python deploy_sistema_hibrido.py
   ```

2. **Faça o deploy**
   ```bash
   git add -A
   git commit -m "feat: deploy sistema híbrido de estoque"
   git push origin main
   ```

## 💻 DEPLOYMENT LOCAL

### Pré-requisitos
- Python 3.8+
- PostgreSQL rodando
- Ambiente virtual ativado

### Passos

1. **Ative o ambiente virtual**
   ```bash
   cd /home/rafaelnascimento/projetos/frete_sistema
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate     # Windows
   ```

2. **Execute o script de deployment**
   ```bash
   python deploy_sistema_hibrido.py
   ```

3. **Reinicie a aplicação**
   ```bash
   # Parar aplicação (Ctrl+C se estiver rodando)
   # Reiniciar
   python run.py
   # ou
   flask run
   ```

## 🔍 VERIFICAÇÃO PÓS-DEPLOYMENT

### 1. Verificar Saúde do Sistema
```bash
# Local
curl http://localhost:5000/estoque/api/hibrido/saude

# Render
curl https://seu-app.onrender.com/estoque/api/hibrido/saude
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "cache_memory": {
    "produtos": 100,
    "hit_rate": "95%"
  },
  "cache_db": {
    "produtos": 5000,
    "ultima_atualizacao": "2025-08-05T10:30:00"
  },
  "performance": {
    "memoria_ms": 5,
    "db_ms": 45,
    "calculo_ms": 500
  }
}
```

### 2. Testar uma Projeção
```bash
# Substitua 4840103 por um código de produto válido
curl http://localhost:5000/estoque/api/hibrido/produto/4840103
```

### 3. Ver Estatísticas do Cache
```bash
curl http://localhost:5000/estoque/api/hibrido/cache/stats
```

## 🔧 TROUBLESHOOTING

### Erro: "Execute este script na raiz do projeto!"
**Solução:**
```bash
cd /caminho/para/frete_sistema
python deploy_sistema_hibrido.py
```

### Erro: "No module named 'app'"
**Solução:**
```bash
# Certifique-se de estar no diretório correto
pwd  # Deve mostrar .../frete_sistema

# Ative o ambiente virtual
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
```

### Erro: "relation does not exist"
**Solução:**
O script criará as tabelas automaticamente. Se persistir:
```sql
-- Execute no PostgreSQL
CREATE TABLE IF NOT EXISTS estoque_atual (
    cod_produto VARCHAR(50) PRIMARY KEY,
    estoque NUMERIC(15,3) NOT NULL DEFAULT 0,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versao INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS estoque_projecao_cache (
    cod_produto VARCHAR(50) PRIMARY KEY,
    projecao_json JSON,
    menor_estoque_7d NUMERIC(15,3),
    status_ruptura VARCHAR(20),
    data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tempo_calculo_ms INTEGER,
    versao INTEGER DEFAULT 1
);
```

### Erro: PG 1082 ainda aparece
**Solução:**
1. Execute o script de deployment
2. Reinicie completamente a aplicação
3. Verifique se as novas tabelas foram criadas:
   ```sql
   SELECT * FROM estoque_atual LIMIT 1;
   SELECT * FROM estoque_projecao_cache LIMIT 1;
   ```

## 📊 O QUE O SCRIPT FAZ

1. **Cria Tabelas**
   - `estoque_atual`: Estoque em tempo real
   - `estoque_projecao_cache`: Projeções materializadas

2. **Cria Índices Otimizados**
   - Por produto
   - Por data de atualização
   - Por status de ruptura

3. **Migra Dados Existentes**
   - Calcula estoque atual de MovimentacaoEstoque
   - Gera projeções iniciais

4. **Configura Triggers**
   - Atualização automática ao modificar dados
   - Jobs agendados para recálculo

5. **Limpa Cache Antigo**
   - Remove dados da tabela antiga saldo_estoque_cache

6. **Verifica Instalação**
   - Testa tabelas
   - Testa cálculo de projeção
   - Reporta performance

## ✅ CHECKLIST PÓS-DEPLOYMENT

- [ ] Script executado sem erros
- [ ] Aplicação reiniciada
- [ ] Endpoint /estoque/api/hibrido/saude retorna "healthy"
- [ ] Projeções sendo calculadas (<50ms com cache)
- [ ] Logs sem erros PG 1082
- [ ] Página /estoque/saldo-estoque/ carregando rapidamente

## 📈 MÉTRICAS DE SUCESSO

Após o deployment bem-sucedido, você deve observar:

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Tempo de resposta (com cache) | 500-1000ms | <10ms | 100x |
| Tempo de resposta (sem cache) | 1000-2000ms | <50ms | 20x |
| Erro PG 1082 | Frequente | Nunca | 100% |
| Uso de memória | Variável | Estável | - |

## 🆘 SUPORTE

Se encontrar problemas:

1. **Verifique os logs do deployment**
   - O script mostra logs detalhados de cada etapa

2. **Execute verificação manual**
   ```bash
   python -c "from app import create_app; app = create_app(); print('✅ App OK')"
   ```

3. **Teste conexão com banco**
   ```bash
   python -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.engine.execute('SELECT 1'); print('✅ DB OK')"
   ```

---

**Última atualização:** 05/08/2025
**Versão:** 1.0.0
**Status:** PRONTO PARA PRODUÇÃO