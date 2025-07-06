# 🧹 Instruções para Limpar Duplicação no Render

## 📊 Situação Atual
Você tem 2 serviços redundantes:
1. **`sistema-fretes`** - Serviço ORIGINAL (manter este!)
2. **`frete-sistema`** - Serviço duplicado (deletar este!)

## ✅ O que foi feito:
- `render.yaml` atualizado para usar apenas `sistema-fretes`
- Todas as referências corrigidas

## 🗑️ Passos para Limpar:

### 1. No Render Dashboard:
1. Acesse https://dashboard.render.com
2. Encontre o serviço `frete-sistema`
3. Clique nos 3 pontinhos → **Delete Service**
4. Confirme a exclusão

### 2. Verificar Banco de Dados:
- O `sistema-fretes` deve usar o banco `sistema-fretes-db`
- Se houver um banco `frete-sistema-db` órfão, delete também

### 3. Após Commit:
```bash
git add render.yaml INSTRUCOES_LIMPEZA_RENDER.md
git commit -m "Fix: Usar apenas sistema-fretes original - remover duplicação"
git push
```

## 📝 Resultado Esperado:
- Apenas 1 serviço: `sistema-fretes`
- URL: https://sistema-fretes.onrender.com
- Sem duplicação de recursos
- Sem confusão de deploys

## ⚠️ IMPORTANTE:
NÃO delete o `sistema-fretes`! Este é o serviço original que deve ser mantido. 