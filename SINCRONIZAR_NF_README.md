# 📋 Scripts de Sincronização NF - Separação

## 📌 Objetivo
Sincronizar o campo `sincronizado_nf` na tabela `Separacao` baseado nos dados da tabela `RelatorioFaturamentoImportado`.

## 🔍 O que faz
1. Busca todas as separações com `numero_nf` preenchido e `sincronizado_nf=False`
2. Para cada separação, verifica se a NF existe em `RelatorioFaturamentoImportado`
3. Se existe, compara o CNPJ do cliente
4. Se o CNPJ corresponde, marca `sincronizado_nf=True` e registra a data de sincronização

## 📂 Scripts Disponíveis

### 1. `sincronizar_nf_separacao.py` (Completo)
Script completo com opções e relatório detalhado.

**Uso local:**
```bash
# Modo simulação (não salva alterações)
python sincronizar_nf_separacao.py --dry-run

# Modo silencioso (apenas resumo)
python sincronizar_nf_separacao.py --quiet

# Executar sincronização completa
python sincronizar_nf_separacao.py
```

### 2. `sincronizar_nf_render.py` (Simplificado)
Script simplificado para rodar no Render Shell.

**Uso no Render Shell:**
```python
exec(open('sincronizar_nf_render.py').read())
```

### 3. `test_sync_nf.py` (Teste)
Script para verificar o status atual antes de sincronizar.

**Uso:**
```bash
python test_sync_nf.py
```

## 🚀 Como executar no Render

### Opção 1: Via Render Shell
1. Acesse o Render Dashboard
2. Vá para o serviço do sistema
3. Clique em "Shell"
4. Execute:
```python
from app import create_app, db
app = create_app()
with app.app_context():
    exec(open('sincronizar_nf_render.py').read())
```

### Opção 2: Via Job/Cron
Adicione ao seu `render.yaml` ou configure um Job:
```yaml
- type: cron
  name: sync-nf-separacao
  env: python
  schedule: "0 2 * * *"  # Diariamente às 2h
  buildCommand: pip install -r requirements.txt
  startCommand: python sincronizar_nf_separacao.py --quiet
```

## 📊 Campos Utilizados

### Tabela: `separacao`
- `numero_nf` - Número da nota fiscal
- `cnpj_cpf` - CNPJ/CPF do cliente
- `sincronizado_nf` - Flag de sincronização (Boolean)
- `data_sincronizacao` - Data/hora da sincronização

### Tabela: `relatorio_faturamento_importado`
- `numero_nf` - Número da nota fiscal
- `cnpj_cliente` - CNPJ do cliente
- `ativo` - Flag se o registro está ativo

## ⚠️ Importante
- O script compara CNPJs removendo formatação (pontos, traços, barras)
- Apenas registros com `ativo=True` em RelatorioFaturamentoImportado são considerados
- O campo `sincronizado_nf` é usado para projeção de estoque - marcar com cuidado!

## 📈 Monitoramento
Após executar, verifique:
```sql
-- Total de separações sincronizadas
SELECT COUNT(*) FROM separacao 
WHERE numero_nf IS NOT NULL 
AND sincronizado_nf = true;

-- Separações pendentes de sincronização
SELECT COUNT(*) FROM separacao 
WHERE numero_nf IS NOT NULL 
AND sincronizado_nf = false;

-- Taxa de sincronização
SELECT 
    COUNT(*) FILTER (WHERE sincronizado_nf = true) AS sincronizadas,
    COUNT(*) AS total,
    ROUND(COUNT(*) FILTER (WHERE sincronizado_nf = true) * 100.0 / COUNT(*), 2) AS percentual
FROM separacao 
WHERE numero_nf IS NOT NULL;
```

## 🐛 Troubleshooting

### Erro: "No module named 'app'"
Certifique-se de estar no diretório correto do projeto.

### Erro: "Database connection failed"
Verifique as variáveis de ambiente DATABASE_URL.

### CNPJs não correspondem
Execute o teste para ver exemplos:
```bash
python test_sync_nf.py
```

## 📝 Logs
O script principal gera logs detalhados mostrando:
- Total de separações processadas
- NFs encontradas/não encontradas
- CNPJs correspondentes/divergentes
- Taxa de sucesso da sincronização

---
**Última atualização:** 03/09/2025