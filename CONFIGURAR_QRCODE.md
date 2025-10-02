# 🔲 CONFIGURAR QR CODE - LOCAL vs PRODUÇÃO

**Problema**: QR Code não abre no celular em ambiente local

**Causa**: `localhost` só funciona no próprio computador, não na rede

---

## 🎯 SOLUÇÃO RÁPIDA (Ambiente Local)

### **Passo 1: Descobrir seu IP na rede**

```bash
# Opção 1
hostname -I | awk '{print $1}'

# Opção 2
ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d'/' -f1

# Deve retornar algo como: 192.168.1.100
```

### **Passo 2: Configurar variável de ambiente**

Adicione ao arquivo `.env` (ou crie se não existir):

```bash
# .env
RASTREAMENTO_BASE_URL=http://192.168.1.100:5000
```

**IMPORTANTE**: Use o **SEU IP** que descobriu no Passo 1!

### **Passo 3: Rodar Flask com IP da rede**

```bash
# Parar Flask se estiver rodando
# Ctrl+C

# Rodar com acesso pela rede
flask run --host=0.0.0.0 --port=5000
```

**Saída esperada:**
```
 * Serving Flask app 'app'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.100:5000  ← ESTE É O IMPORTANTE!
```

### **Passo 4: Testar**

1. **No PC**: Acesse `http://192.168.1.100:5000`
2. **Crie embarque** e **imprima**
3. **Escaneie QR Code** com celular
4. **Deve abrir** a tela de aceite LGPD! ✅

---

## 🏭 CONFIGURAÇÃO PRODUÇÃO (Render/Heroku)

No arquivo `.env` de produção:

```bash
# .env (Produção)
RASTREAMENTO_BASE_URL=https://seudominio.com
```

Ou configure direto no Render:
1. Dashboard → Web Service → Environment
2. Adicionar variável:
   - **Key**: `RASTREAMENTO_BASE_URL`
   - **Value**: `https://seuapp.onrender.com`

---

## 🧪 VERIFICAR CONFIGURAÇÃO

Execute no Flask shell:

```bash
flask shell
```

```python
from app.rastreamento.models import RastreamentoEmbarque
import os

# Ver URL base configurada
print(f"URL Base: {os.getenv('RASTREAMENTO_BASE_URL')}")

# Buscar rastreamento
rastr = RastreamentoEmbarque.query.first()
if rastr:
    print(f"URL QR Code: {rastr.url_rastreamento}")
else:
    print("Nenhum rastreamento encontrado")
```

**Resultado esperado (Local):**
```
URL Base: http://192.168.1.100:5000
URL QR Code: http://192.168.1.100:5000/rastreamento/aceite/AbCdEf...
```

**Resultado esperado (Produção):**
```
URL Base: https://seudominio.com
URL QR Code: https://seudominio.com/rastreamento/aceite/AbCdEf...
```

---

## 🔧 TROUBLESHOOTING

### **QR Code ainda não abre**

**Verifique:**

1. **Celular e PC na mesma rede WiFi?**
   ```bash
   # No PC
   ip route | grep default

   # No celular: Configurações → WiFi → Nome da rede
   # Deve ser a MESMA rede!
   ```

2. **Firewall bloqueando porta 5000?**
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 5000/tcp

   # Ou desabilitar temporariamente
   sudo ufw disable
   ```

3. **Flask rodando com --host=0.0.0.0?**
   ```bash
   # Verificar se aparece "Running on http://0.0.0.0:5000"
   # Se não aparecer, não vai funcionar na rede!
   ```

4. **URL no .env está correta?**
   ```bash
   cat .env | grep RASTREAMENTO
   # Deve mostrar: RASTREAMENTO_BASE_URL=http://SEU_IP:5000
   ```

5. **Reiniciou Flask após configurar .env?**
   ```bash
   # Parar: Ctrl+C
   # Rodar novamente:
   flask run --host=0.0.0.0 --port=5000
   ```

---

### **Testar URL diretamente no celular**

1. Abra navegador do celular
2. Digite: `http://192.168.1.100:5000`
3. **Deve abrir** o sistema normalmente

Se NÃO abrir:
- ❌ Problema de rede/firewall
- ✅ Configure firewall e tente novamente

Se abrir:
- ✅ Rede OK!
- ❌ Problema no QR Code ou .env
- ✅ Verifique `.env` e reinicie Flask

---

### **QR Code gerado antes de configurar .env**

Se você criou embarques **ANTES** de configurar o `.env`:

**Opção 1**: Criar novos embarques (recomendado)

**Opção 2**: Atualizar QR Code manualmente:
```bash
flask shell
```

```python
from app.rastreamento.models import RastreamentoEmbarque
from app.embarques.models import Embarque

# Listar todos rastreamentos
rastreamentos = RastreamentoEmbarque.query.all()

for r in rastreamentos:
    print(f"Embarque #{r.embarque_id}: {r.url_rastreamento}")
```

O QR Code é gerado **em tempo real** ao imprimir, então:
1. **Reimprima** o embarque
2. QR Code agora terá a URL correta! ✅

---

## 📱 TESTAR SEM CELULAR (Opcional)

Use um emulador de QR Code:

1. Gere QR Code e salve imagem
2. Acesse: https://webqr.com
3. Upload da imagem do QR Code
4. Veja a URL que está codificada

---

## ✅ RESUMO

**LOCAL (Desenvolvimento):**
```bash
# 1. Descobrir IP
hostname -I | awk '{print $1}'

# 2. Configurar .env
echo "RASTREAMENTO_BASE_URL=http://192.168.1.100:5000" >> .env

# 3. Rodar Flask
flask run --host=0.0.0.0 --port=5000

# 4. Testar QR Code com celular
```

**PRODUÇÃO (Render/Heroku):**
```bash
# No painel de variáveis de ambiente:
RASTREAMENTO_BASE_URL=https://seuapp.onrender.com
```

---

**Depois de configurar, o QR Code vai funcionar perfeitamente! 📱✅**
