# 📋 INSTRUÇÕES DE CONFIGURAÇÃO DO PORTAL

## 1️⃣ CONFIGURAR CHROME COM DEBUG

### Opção A: Usar o script automático
```bash
# Executar o script de configuração
./configurar_chrome_debug.sh
```

### Opção B: Configurar manualmente
```bash
# 1. Fechar todas as instâncias do Chrome
pkill chrome

# 2. Iniciar Chrome com porta de debug
google-chrome \
    --remote-debugging-port=9222 \
    --user-data-dir="/tmp/chrome-debug" \
    --no-first-run \
    --start-maximized \
    "https://b2b.atacadao.com.br/"

# 3. Fazer login manual no portal do Atacadão
# 4. Manter a janela aberta durante o uso
```

### Verificar se está funcionando:
```bash
# Deve retornar informações do Chrome
curl http://localhost:9222/json/version
```

---

## 2️⃣ CRIAR TABELAS NO BANCO DE DADOS (RENDER)

### Opção A: Via interface do Render
1. Acesse o dashboard do Render
2. Vá em "PostgreSQL" > "Connect" > "PSQL Command"
3. Cole e execute o script SQL:

```sql
-- Copie todo o conteúdo do arquivo:
-- app/portal/sql/001_criar_tabelas_portal.sql
```

### Opção B: Via linha de comando local
```bash
# Configurar variável de ambiente com a URL do banco
export DATABASE_URL="postgresql://user:pass@host/database"

# Executar o script
psql $DATABASE_URL < app/portal/sql/001_criar_tabelas_portal.sql
```

### Verificar se as tabelas foram criadas:
```sql
-- Listar as tabelas do portal
SELECT table_name FROM information_schema.tables 
WHERE table_name LIKE 'portal_%'
ORDER BY table_name;

-- Deve retornar:
-- portal_atacadao_produto_depara
-- portal_configuracoes
-- portal_integracoes
-- portal_logs
-- portal_sessoes
```

---

## 3️⃣ USAR O PORTAL NO SISTEMA

### 📍 Onde estão os botões:

1. **Na Carteira Agrupada**:
   - Clique no botão de "Separações" de um pedido
   - No modal que abre, cada card de separação terá:
     - ✅ **Botão "Agendar no Portal"** (verde)
     - 🔍 **Botão "Verificar Portal"** (azul)

### 🎯 Como usar:

#### Para Agendar:
1. Clique em **"Agendar no Portal"**
2. Se não há data de agendamento, será solicitada
3. O sistema fará o agendamento automaticamente
4. O protocolo será exibido ao final

#### Para Verificar/Comparar:
1. Clique em **"Verificar Portal"**
2. Abrirá um modal comparando:
   - **Esquerda**: Produtos da separação (sistema)
   - **Direita**: Produtos do portal
3. Use **"Extrair Confirmações"** para atualizar status

---

## 4️⃣ REQUISITOS

### ✅ Chrome Debug
- Chrome rodando com `--remote-debugging-port=9222`
- Login manual feito no portal

### ✅ Banco de Dados
- Tabelas `portal_*` criadas
- Índices e triggers configurados

### ✅ Campo pedido_cliente
- Deve existir na CarteiraPrincipal
- Contém o número do pedido no cliente

### ✅ Dependências Python
```bash
pip install selenium webdriver-manager
```

---

## 5️⃣ FLUXO COMPLETO

```mermaid
graph LR
    A[Carteira Agrupada] --> B[Modal Separações]
    B --> C{Escolher Ação}
    C --> D[Agendar no Portal]
    C --> E[Verificar Portal]
    D --> F[Agendamento Automático]
    F --> G[Protocolo Gravado]
    E --> H[Modal Comparação]
    H --> I[Extrair Confirmações]
```

---

## 6️⃣ SOLUÇÃO DE PROBLEMAS

### ❌ Botões não aparecem
- Verificar se as tabelas `portal_*` foram criadas
- Reiniciar o servidor Flask
- Limpar cache do navegador (Ctrl+F5)

### ❌ Chrome não conecta
- Verificar se porta 9222 está aberta: `netstat -an | grep 9222`
- Reiniciar Chrome com debug
- Verificar firewall/antivírus

### ❌ Erro ao agendar
- Verificar campo `pedido_cliente` na CarteiraPrincipal
- Confirmar login no portal
- Ver logs em `portal_logs`

### ❌ Comparação vazia
- Verificar se há integração para o lote
- Confirmar que o agendamento foi feito primeiro

---

## 7️⃣ LOGS E DEBUG

### Ver logs do portal:
```sql
-- Últimas operações
SELECT * FROM portal_logs 
ORDER BY criado_em DESC 
LIMIT 20;

-- Integrações recentes
SELECT * FROM portal_integracoes 
ORDER BY criado_em DESC 
LIMIT 10;
```

### Debug no console JavaScript:
```javascript
// Ver se os botões foram carregados
console.log(window.modalSeparacoes);

// Testar agendamento manual
window.modalSeparacoes.agendarNoPortal('SEP001', '2025-01-10');

// Testar verificação
window.modalSeparacoes.verificarPortal('SEP001');
```

---

## 📞 SUPORTE

Em caso de problemas:
1. Verificar esta documentação
2. Consultar logs em `portal_logs`
3. Screenshots em caso de erro: `screenshots/`