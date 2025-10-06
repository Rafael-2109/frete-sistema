# 📋 Scripts de Migration

## 🎯 Migration: agendamento_confirmado em EmbarqueItem

**Arquivo:** `20250106_adicionar_agendamento_confirmado.py`

**O que faz:**
1. Adiciona coluna `agendamento_confirmado` (BOOLEAN) em `embarque_itens`
2. Popula valores baseado em `Separacao` (via `separacao_lote_id`)
3. Verifica e exibe estatísticas

---

## 🚀 COMO EXECUTAR

### Opção 1: Executar Python diretamente
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python migrations/scripts/20250106_adicionar_agendamento_confirmado.py
```

### Opção 2: Via Flask Shell
```bash
flask shell
```

Dentro do shell:
```python
from migrations.scripts.20250106_adicionar_agendamento_confirmado import run_migration
resultado = run_migration()
print(resultado)
```

### Opção 3: No Render (Shell)
```bash
# No dashboard do Render, abrir Shell:
python migrations/scripts/20250106_adicionar_agendamento_confirmado.py
```

---

## 📊 OUTPUT ESPERADO

```
============================================================
🚀 INICIANDO MIGRATION: agendamento_confirmado
============================================================
📝 PASSO 1: Adicionando coluna agendamento_confirmado...
✅ Coluna adicionada com sucesso!
📝 PASSO 2: Populando valores baseado em Separacao...
✅ 45 registros atualizados!
📝 PASSO 3: Verificando resultado...
============================================================
📊 RESULTADO DA MIGRATION:
   Total de registros: 45
   Confirmados: 12
   Não confirmados: 33
============================================================
✅ MIGRATION CONCLUÍDA COM SUCESSO!
============================================================

🎉 SUCESSO!
   Migration concluída com sucesso
   Registros atualizados: 45
```

---

## ⚠️ CASO DE ERRO: "Coluna já existe"

Se a coluna já existir, o script irá:
1. **Pular a criação da coluna**
2. **Apenas atualizar os valores**
3. **Exibir estatísticas**

Isso garante que você pode executar o script múltiplas vezes sem problemas.

---

## 🔄 ROLLBACK (Reverter Migration)

**⚠️ CUIDADO:** Isso apaga a coluna e TODOS os dados dela!

```bash
python migrations/scripts/20250106_adicionar_agendamento_confirmado.py rollback
```

Será solicitada confirmação:
```
Digite 'SIM' para confirmar rollback: SIM
```

---

## ✅ VERIFICAR SE DEU CERTO

### Via SQL direto:
```sql
-- Verificar se coluna existe
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name='embarque_itens'
AND column_name='agendamento_confirmado';

-- Ver dados
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN agendamento_confirmado THEN 1 ELSE 0 END) as confirmados,
    SUM(CASE WHEN agendamento_confirmado = false THEN 1 ELSE 0 END) as nao_confirmados
FROM embarque_itens;
```

### Via Python:
```python
from app.embarques.models import EmbarqueItem
from app import db

# Ver estatísticas
result = db.session.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN agendamento_confirmado THEN 1 ELSE 0 END) as confirmados
    FROM embarque_itens
""").fetchone()

print(f"Total: {result[0]}, Confirmados: {result[1]}")
```

---

## 🐛 TROUBLESHOOTING

### Erro: "relation embarque_itens does not exist"
**Solução:** Verificar se o nome da tabela está correto. Pode ser `embarques_itens` ao invés de `embarque_itens`.

### Erro: "column agendamento_confirmado already exists"
**Solução:** Normal! O script detecta isso e apenas atualiza os valores.

### Erro: "permission denied"
**Solução:** Verificar se o usuário do banco tem permissão para ALTER TABLE.

---

## 📝 LOGS

O script gera logs detalhados:
- ✅ Sucesso (verde)
- ⚠️  Avisos (amarelo)
- ❌ Erros (vermelho)

Todos os logs incluem timestamp para auditoria.

---

## 🔒 SEGURANÇA

- ✅ Rollback automático em caso de erro
- ✅ Verificação de coluna existente antes de criar
- ✅ Confirmação obrigatória para rollback
- ✅ Logs detalhados para auditoria
- ✅ Sem perda de dados (apenas adiciona coluna)

---

## 📞 SUPORTE

Em caso de problemas:
1. Verificar logs do script
2. Verificar permissões do banco
3. Executar SQL manualmente (arquivo `.sql` disponível)
4. Contatar suporte técnico

**Arquivo SQL alternativo:**
`migrations/sql/20250106_adicionar_agendamento_confirmado_embarque_item.sql`
