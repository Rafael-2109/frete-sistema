# ✅ CHECKLIST - BOTÕES DO PORTAL

## 1️⃣ REINICIAR O SERVIDOR
```bash
# Parar o servidor atual (Ctrl+C)
# Reiniciar:
python run.py
```

## 2️⃣ LIMPAR CACHE DO NAVEGADOR
- Pressione **Ctrl + F5** na página da Carteira Agrupada
- Ou abra em janela anônima/privada

## 3️⃣ TESTAR OS BOTÕES

### Como testar:
1. Acesse a **Carteira Agrupada**
2. Clique no botão **"Separações"** de qualquer pedido
3. No modal que abrir, você deve ver:
   - ✅ Botão verde **"Agendar no Portal"**
   - 🔍 Botão azul **"Verificar Portal"**

### Debug no navegador (F12):
Abra o console (F12) e procure por:
- `🎨 Renderizando X separações`
- `📦 Dados das separações:`
- `🔍 Separação 1:` (deve mostrar protocolo_portal)

## 4️⃣ SE OS BOTÕES NÃO APARECEREM

### Verificar no console do navegador:
```javascript
// Cole isso no console (F12):
console.log(window.modalSeparacoes);

// Deve retornar o objeto ModalSeparacoes
// Se retornar undefined, o JavaScript não carregou
```

### Verificar se as tabelas existem:
```python
# Execute:
python criar_tabelas_portal.py
```

### Verificar logs do servidor:
Procure por estas mensagens no terminal do servidor:
- `✅ Portal: Protocolo encontrado para lote`
- `ℹ️ Portal: Nenhuma integração para lote`
- `❌ Portal: Erro ao buscar protocolo`

## 5️⃣ TESTE MANUAL DOS BOTÕES

### Teste direto no console:
```javascript
// No console do navegador (F12), com o modal aberto:
window.modalSeparacoes.agendarNoPortal('SEP001', '2025-01-15');
window.modalSeparacoes.verificarPortal('SEP001');
```

## 📝 RESUMO DO QUE FOI IMPLEMENTADO

### Backend:
- ✅ Módulo portal completo (`app/portal/`)
- ✅ Modelos de banco de dados
- ✅ Rotas da API (`/portal/api/`)
- ✅ Campo `protocolo_portal` na API de separações

### Frontend:
- ✅ Botões no modal de separações
- ✅ Funções JavaScript para portal
- ✅ Modal de comparação
- ✅ Integração com SweetAlert2

### Banco de Dados:
- ✅ 5 tabelas do portal criadas
- ✅ Triggers e índices configurados
- ✅ 3 registros de teste já existem

## 🆘 SUPORTE

Se ainda não funcionar:
1. **Screenshots**: Tire print do console (F12)
2. **Logs do servidor**: Copie os últimos logs
3. **Teste da API**: Execute `python teste_api_separacoes.py`

## ✨ FUNCIONALIDADES DISPONÍVEIS

Quando os botões aparecerem, você poderá:
- 📅 **Agendar no Portal**: Solicita agendamento automático
- 🔍 **Verificar Portal**: Compara dados do sistema com o portal
- 📊 **Ver Protocolo**: Badge verde mostra protocolo quando existe
- 🔄 **Extrair Confirmações**: Atualiza status do portal

---

**Status Atual**: Sistema 100% implementado
**Próximo Passo**: Reiniciar servidor e testar