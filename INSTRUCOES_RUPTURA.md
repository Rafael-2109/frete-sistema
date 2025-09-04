# 📊 Sistema de Ruptura de Estoque - INSTRUÇÕES DE USO

## ⚡ IMPORTANTE: ZERO CACHE - Dados sempre atualizados!

## 🔧 Como funciona agora:

### 1️⃣ **Análise Automática ao Carregar Página**
- Ao abrir `/carteira/workspace` (agrupados_balanceado.html)
- Sistema analisa TODOS os pedidos automaticamente
- Processa em lotes de 20 pedidos
- Mostra badges coloridos com resultado

### 2️⃣ **Botão Manual "Atualizar Estoque"**
- Botão azul adicional (não mexe no antigo)
- Faz nova análise SEM CACHE
- Atualiza resultado instantaneamente

## 🎨 Cores dos Badges:
- 🟢 **Verde**: Estoque OK
- 🔴 **Vermelho**: Ruptura CRÍTICA (>3 itens e >10% valor)
- 🟡 **Amarelo**: Ruptura ALTA (≤3 itens e ≤10% valor)
- 🔵 **Azul**: Ruptura MÉDIA (≤2 itens e ≤5% valor)
- ⚪ **Cinza**: Ruptura BAIXA (outros casos)

## 🐛 Solução de Problemas:

### Se não estiver funcionando:
1. **Verificar console do navegador** (F12)
2. **Recarregar a página** (Ctrl+F5)
3. **Verificar se o servidor está rodando**

### Identificar qual sistema está rodando:
- **Sistema ANTIGO**: Botão "Verificar Estoque" (ícone caixa)
- **Sistema NOVO**: Botão "Atualizar Estoque" (ícone sync)

## 📁 Arquivos do Sistema:

### Backend (APIs sem cache):
- `/app/carteira/routes/ruptura_api_async.py` - Nova API sem cache
- Endpoint: `/carteira/api/ruptura/analisar-lote-async`

### Frontend:
- `/app/static/carteira/js/ruptura-estoque-integrado.js` - Script novo
- IDs únicos: `ruptura-novo-*` (para não conflitar)

### Template:
- `/app/templates/carteira/agrupados_balanceado.html`
- Linha 588: `<script src="ruptura-estoque-integrado.js">`

## ✅ Checklist de Funcionamento:

- [ ] Página carrega sem erros no console
- [ ] Badges aparecem automaticamente ao carregar
- [ ] Botão "Atualizar Estoque" aparece (azul)
- [ ] Clicar no botão atualiza o resultado
- [ ] Cores mudam conforme criticidade

## 🚀 Para Ativar/Desativar:

### Desativar temporariamente:
```html
<!-- Comentar linha 588 em agrupados_balanceado.html -->
<!-- <script src="{{ url_for('static', filename='carteira/js/ruptura-estoque-integrado.js') }}"></script> -->
```

### Reativar:
```html
<!-- Descomentar linha 588 -->
<script src="{{ url_for('static', filename='carteira/js/ruptura-estoque-integrado.js') }}"></script>
```

## 📝 Notas:
- Sistema NOVO não interfere com o ANTIGO
- Ambos podem coexistir até o novo estar 100%
- ZERO CACHE = dados sempre frescos do banco