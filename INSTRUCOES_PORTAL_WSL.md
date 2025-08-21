# 🚀 INSTRUÇÕES - PORTAL DE AGENDAMENTO NO WSL

## ✅ SOLUÇÃO FUNCIONANDO - Chrome Windows + WSL

Este documento explica como usar o sistema de agendamento automático de portais no WSL conectando ao Chrome do Windows.

---

## 📋 PRÉ-REQUISITOS

### No Windows:
- ✅ Google Chrome instalado
- ✅ Arquivo `iniciar_chrome_windows.bat` (já criado)

### No WSL:
- ✅ Python com Selenium instalado
- ✅ Sistema de frete rodando

---

## 🔧 CONFIGURAÇÃO INICIAL (FAZER UMA VEZ)

### 1️⃣ No Windows - Iniciar Chrome com Debug Port

**Opção A - Usar o arquivo .bat (RECOMENDADO):**
```cmd
# Dê duplo clique no arquivo:
iniciar_chrome_windows.bat
```

**Opção B - Executar manualmente:**
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"
```

> ⚠️ **IMPORTANTE**: O Chrome abrirá uma nova janela. NÃO FECHE ESTA JANELA!

### 2️⃣ No WSL - Testar Conexão

```bash
# Teste rápido se está funcionando:
curl http://localhost:9222/json/version

# Se retornar JSON com informações do Chrome, está OK!
```

### 3️⃣ Executar Teste Completo

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python testar_chrome_wsl.py
```

Você deve ver:
```
✅ Porta 9222
✅ Selenium
✅ BrowserManager
✅ Portal Atacadão

🎉 TODOS OS TESTES PASSARAM!
```

---

## 📱 USO DO PORTAL DE AGENDAMENTO

### 1️⃣ Acessar Sistema de Carteira

1. Abra o sistema: http://localhost:5000
2. Vá para **Carteira de Pedidos**
3. Selecione um pedido

### 2️⃣ Usar Botões do Portal

Os botões aparecem em 2 lugares:

#### A) No Modal de Separações:
- Clique em "Ver Separações" de um pedido
- No modal, você verá o card "Portal do Cliente"
- Clique em **"Agendar no Portal"**

#### B) No Card de Separação (Workspace):
- Na área de trabalho de separações
- Cada card tem botões do portal na parte inferior
- Clique em **"Portal"** (ícone de calendário)

### 3️⃣ Processo de Agendamento

1. **Sistema detecta automaticamente o portal** (Atacadão, etc)
2. **Chrome abre a página do portal**
3. **Sistema preenche os dados automaticamente**
4. **Protocolo é gerado e salvo**
5. **Modal mostra o protocolo gerado**

---

## 🔍 VERIFICAÇÃO DE STATUS

### Ver Protocolos Gerados

```sql
-- No banco de dados:
SELECT 
    separacao_lote_id,
    protocolo,
    agendamento,
    agendamento_confirmado
FROM separacao
WHERE protocolo IS NOT NULL
ORDER BY criado_em DESC;
```

### Ver Integrações no Portal

1. Acesse: http://localhost:5000/portal
2. Veja lista de integrações
3. Status possíveis:
   - `aguardando` - Criado mas não processado
   - `processando` - Em execução
   - `aguardando_confirmacao` - Protocolo gerado
   - `confirmado` - Agendamento confirmado
   - `erro` - Falha no processo

---

## 🐛 TROUBLESHOOTING

### ❌ Erro: "Não conseguiu conectar na porta 9222"

**Solução:**
1. Verifique se o Chrome está rodando no Windows
2. Execute `iniciar_chrome_windows.bat` novamente
3. No WSL, teste: `curl http://localhost:9222/json/version`

### ❌ Erro: "ChromeDriver não encontrado"

**Solução no WSL:**
```bash
# Instalar ChromeDriver
sudo apt update
sudo apt install chromium-chromedriver

# Verificar instalação
which chromedriver
```

### ❌ Erro: "selenium.common.exceptions.WebDriverException"

**Possíveis causas:**
1. Chrome não está rodando no Windows
2. Firewall bloqueando porta 9222
3. WSL não consegue acessar localhost

**Soluções:**
```bash
# Verificar conectividade
ping localhost
telnet localhost 9222

# Se não funcionar, tentar IP do Windows
cat /etc/resolv.conf  # Ver IP do Windows
curl http://[IP_WINDOWS]:9222/json/version
```

### ❌ Botões do Portal não Aparecem

**Verificar:**
1. Campo `protocolo` existe na tabela `separacao`
2. JavaScript está carregado: F12 > Console
3. Não há erros de JavaScript

**Debug no Console do Browser:**
```javascript
// Verificar se dados estão chegando
console.log(window.separacoes_data);

// Forçar renderização dos botões
location.reload();
```

---

## 🔐 SEGURANÇA

### Sessão do Chrome

- O Chrome com debug port mantém a sessão
- Você pode fazer login manual uma vez
- A sessão persiste entre execuções
- Dados ficam em `C:\temp\chrome-debug`

### Proteção de Dados

- Senhas não são armazenadas em texto claro
- Logs são salvos para auditoria
- Screenshots apenas em caso de erro

---

## 📊 MONITORAMENTO

### Logs do Sistema

```bash
# Ver logs em tempo real
tail -f logs/portal.log

# Ver apenas erros
grep ERROR logs/portal.log

# Ver agendamentos bem-sucedidos
grep "Protocolo:" logs/portal.log
```

### Métricas

```python
# No shell Python
from app.portal.models import PortalIntegracao
from app import db

# Total de agendamentos
total = PortalIntegracao.query.count()

# Taxa de sucesso
confirmados = PortalIntegracao.query.filter_by(status='confirmado').count()
taxa_sucesso = (confirmados / total * 100) if total > 0 else 0

print(f"Total: {total}")
print(f"Confirmados: {confirmados}")
print(f"Taxa de Sucesso: {taxa_sucesso:.1f}%")
```

---

## 🚀 COMANDOS RÁPIDOS

```bash
# Iniciar sistema
cd /home/rafaelnascimento/projetos/frete_sistema
python app.py

# Testar portal
python testar_chrome_wsl.py

# Ver logs
tail -f logs/portal.log

# Limpar sessão Chrome (Windows)
rmdir /s /q C:\temp\chrome-debug
```

---

## 📝 NOTAS IMPORTANTES

1. **Chrome deve estar aberto no Windows** antes de usar o portal
2. **Não feche a janela do Chrome** durante o uso
3. **Uma janela Chrome = Uma sessão** de automação
4. **Login manual** pode ser necessário na primeira vez
5. **Protocolo é salvo automaticamente** no banco

---

## ✅ CHECKLIST DE FUNCIONAMENTO

- [ ] Chrome rodando no Windows com porta 9222
- [ ] WSL consegue acessar localhost:9222
- [ ] Sistema de frete rodando
- [ ] Botões do portal aparecem na interface
- [ ] Click no botão abre o Chrome
- [ ] Protocolo é gerado e salvo

---

## 📞 SUPORTE

Em caso de problemas:
1. Execute o teste: `python testar_chrome_wsl.py`
2. Verifique os logs: `tail -100 logs/portal.log`
3. Capture o erro completo
4. Documente os passos para reproduzir

---

**Última atualização:** Novembro 2024
**Versão:** 1.0 - WSL com Chrome Windows