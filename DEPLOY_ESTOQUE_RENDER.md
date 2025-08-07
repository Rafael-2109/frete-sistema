# 🚀 Guia de Deploy - Sistema de Estoque em Tempo Real no Render

## 📋 Visão Geral

Este documento descreve o processo de deploy do sistema de estoque em tempo real no Render, incluindo:
- Criação automática de tabelas
- População de dados iniciais
- Configuração de triggers
- Verificação de integridade

## 🔧 Arquivos Principais

### 1. **`init_render_estoque.py`**
- Script principal de inicialização
- Cria tabelas usando SQL direto (sem depender de Flask-Migrate)
- Popula dados iniciais a partir de MovimentacaoEstoque
- Configura movimentações previstas
- Calcula rupturas D+7

### 2. **`pre_start.py`**
- Executado ANTES da aplicação principal
- Registra tipos PostgreSQL
- Corrige DATABASE_URL se necessário
- Chama init_render_estoque.py automaticamente

### 3. **`start_render.sh`**
- Script de inicialização do Render
- Executa pre_start.py
- Inicia o Gunicorn

## 📦 Tabelas Criadas

### `estoque_tempo_real`
```sql
- cod_produto (PK)      # Código do produto
- nome_produto          # Nome do produto
- saldo_atual           # Saldo em tempo real
- atualizado_em         # Timestamp última atualização
- menor_estoque_d7      # Menor estoque nos próximos 7 dias
- dia_ruptura           # Data prevista de ruptura
```

### `movimentacao_prevista`
```sql
- id (PK)               # ID único
- cod_produto           # Código do produto
- data_prevista         # Data da movimentação
- entrada_prevista      # Quantidade de entrada
- saida_prevista        # Quantidade de saída
```

### `programacao_producao` (se não existir)
```sql
- id (PK)               # ID único
- data_programacao      # Data da produção
- cod_produto           # Código do produto
- nome_produto          # Nome do produto
- qtd_programada        # Quantidade programada
```

## 🚀 Processo de Deploy

### 1. **Teste Local** (Recomendado)
```bash
# Testar localmente antes do deploy
python test_init_estoque_local.py
```

### 2. **Configurar Variáveis de Ambiente no Render**

No painel do Render, adicione:
```bash
# Obrigatórias
DATABASE_URL=postgresql://...    # URL do PostgreSQL

# Opcionais
INIT_ESTOQUE_TEMPO_REAL=true    # Habilitar inicialização (padrão: true)
NO_EMOJI_LOGS=true               # Desabilitar emojis nos logs
```

### 3. **Deploy Automático**

O sistema será inicializado automaticamente quando você fizer push para o GitHub:

```bash
git add .
git commit -m "Deploy sistema de estoque em tempo real"
git push origin main
```

### 4. **Verificar Logs no Render**

Procure por estas mensagens nos logs:
```
✅ PRE-START: Sistema de estoque inicializado com sucesso!
✅ Tabela estoque_tempo_real criada
✅ Tabela movimentacao_prevista criada
✅ Saldos migrados: X produtos
✅ X movimentações previstas migradas
```

## 🔍 Verificação Pós-Deploy

### Via Render Shell
```bash
# Conectar ao shell do Render
python -c "
from app import create_app, db
from app.estoque.models_tempo_real import EstoqueTempoReal

app = create_app()
with app.app_context():
    count = EstoqueTempoReal.query.count()
    print(f'Total de produtos: {count}')
    
    # Amostra
    produtos = EstoqueTempoReal.query.limit(5).all()
    for p in produtos:
        print(f'{p.cod_produto}: {p.saldo_atual}')
"
```

### Via API
```bash
# Testar endpoint de estoque
curl https://seu-app.onrender.com/api/estoque/saldo/SEU_CODIGO_PRODUTO
```

## 🛠️ Solução de Problemas

### Erro: "Tabelas não foram criadas"
- Verifique se DATABASE_URL está configurada
- Verifique permissões do usuário PostgreSQL
- Olhe os logs detalhados no Render

### Erro: "PG 1082" ou problemas com tipos PostgreSQL
- O pre_start.py já registra os tipos automaticamente
- Se persistir, reinicie a aplicação no Render

### Dados não foram populados
- Verifique se existem dados em MovimentacaoEstoque
- O sistema só migra produtos com ativo=True
- Limite inicial de 1000 registros por tabela

### Performance lenta
- O processo inicial pode demorar alguns minutos
- Processamento é feito em lotes de 50 produtos
- Após inicialização, sistema opera em tempo real

## 📊 Monitoramento

### Verificar Estatísticas
```python
# No shell do Render
python -c "
from app import create_app, db
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from sqlalchemy import func

app = create_app()
with app.app_context():
    # Estatísticas
    total_produtos = EstoqueTempoReal.query.count()
    total_movs = MovimentacaoPrevista.query.count()
    negativos = EstoqueTempoReal.query.filter(EstoqueTempoReal.saldo_atual < 0).count()
    rupturas = EstoqueTempoReal.query.filter(EstoqueTempoReal.dia_ruptura.isnot(None)).count()
    
    print(f'''
    ESTATÍSTICAS DO SISTEMA:
    ========================
    Produtos: {total_produtos}
    Movimentações: {total_movs}
    Estoque Negativo: {negativos}
    Rupturas Previstas: {rupturas}
    ''')
"
```

## ⚡ Performance

### Otimizações Implementadas
- Índices em todas as colunas de busca
- Processamento em lotes
- Commits parciais a cada 50 registros
- Constraint UNIQUE para evitar duplicatas
- SQL direto para operações críticas

### Tempos Esperados
- Criação de tabelas: < 5 segundos
- População inicial (1000 produtos): 1-3 minutos
- Cálculo de rupturas: 10-30 segundos
- Consultas de API: < 100ms

## 🔄 Atualizações Futuras

Para atualizar o sistema após deploy:
1. Modifique os arquivos necessários
2. Faça commit e push
3. O Render executará automaticamente o processo

Para DESABILITAR a inicialização automática:
```bash
# No Render, defina:
INIT_ESTOQUE_TEMPO_REAL=false
```

## 📞 Suporte

Em caso de problemas:
1. Verifique os logs completos no Render
2. Execute o teste local: `python test_init_estoque_local.py`
3. Verifique a documentação dos modelos em `/app/estoque/models_tempo_real.py`

## ✅ Checklist de Deploy

- [ ] Teste local executado com sucesso
- [ ] DATABASE_URL configurada no Render
- [ ] Backup do banco realizado (se aplicável)
- [ ] Commit e push realizados
- [ ] Logs verificados no Render
- [ ] API testada após deploy
- [ ] Estatísticas verificadas

---

**Última atualização:** 08/08/2025  
**Versão:** 1.0