# 🚚 RASTREAMENTO NACOM - GUIA COMPLETO DE BUILD

## 📋 ÍNDICE

1. [Pré-requisitos](#1-pré-requisitos)
2. [Setup Inicial](#2-setup-inicial)
3. [Build Desenvolvimento](#3-build-desenvolvimento)
4. [Build Produção](#4-build-produção)
5. [Instalação no Celular](#5-instalação-no-celular)
6. [Troubleshooting](#6-troubleshooting)
7. [Deploy Produção](#7-deploy-produção)

---

## 1. PRÉ-REQUISITOS

### ✅ O que você precisa ter instalado:

1. **Node.js e npm** (para Capacitor)
   ```bash
   # Verificar instalação
   node --version  # v18+
   npm --version   # v9+
   ```

2. **Java JDK 17+** (para Gradle/Android)
   ```bash
   # Verificar instalação
   java -version

   # Se não tiver, instalar:
   sudo apt install openjdk-17-jdk
   ```

3. **Android Studio** (para compilar APK)
   ```bash
   # Instalação via snap (já rodando)
   sudo snap install android-studio --classic

   # Aguardar instalação completa (pode levar 5-10 minutos)
   ```

---

## 2. SETUP INICIAL

### **PASSO 1: Aguardar Android Studio Instalar**

```bash
# Verificar se instalação terminou
snap list | grep android-studio

# Quando aparecer "android-studio" na lista, prosseguir
```

### **PASSO 2: Configurar Android SDK**

```bash
# Abrir Android Studio pela primeira vez
android-studio
```

**No wizard inicial:**
1. Escolha **"Standard Installation"**
2. Aceite licenças
3. Aguarde download do Android SDK (~2GB)
4. SDK será instalado em: `~/Android/Sdk`

### **PASSO 3: Executar Script de Setup**

```bash
# Após SDK instalado, rodar:
./setup-android-sdk.sh

# O script irá:
# - Detectar Android SDK automaticamente
# - Configurar variáveis de ambiente (ANDROID_HOME)
# - Criar android/local.properties
# - Verificar Java e Gradle
```

### **PASSO 4: Recarregar Terminal**

```bash
# Recarregar variáveis de ambiente
source ~/.bashrc

# Verificar se funcionou
echo $ANDROID_HOME
# Deve mostrar: /home/rafaelnascimento/Android/Sdk
```

---

## 3. BUILD DESENVOLVIMENTO

### **Quando usar:**
- Testar app localmente
- Depuração
- App aponta para: `http://192.168.1.100:5000`

### **Como fazer:**

```bash
# Build completo automatizado
./build-dev.sh
```

**O script faz:**
1. Copia `capacitor.config.dev.json` → `capacitor.config.json`
2. Instala dependências npm
3. Sincroniza código web → Android
4. Compila APK debug
5. Gera: `rastreamento-nacom-dev.apk`

**Tempo estimado:** 2-5 minutos (primeiro build demora mais)

---

## 4. BUILD PRODUÇÃO

### **Quando usar:**
- Distribuir para motoristas
- Ambiente real
- App aponta para: `https://sistema-fretes.onrender.com`

### **Como fazer:**

```bash
# Build produção
./build-prod.sh
```

**O script:**
1. Pede confirmação (segurança)
2. Copia `capacitor.config.prod.json` → `capacitor.config.json`
3. Build APK apontando para produção
4. Gera: `rastreamento-nacom-prod.apk`
5. Restaura config dev automaticamente

---

## 5. INSTALAÇÃO NO CELULAR

### **Opção A: Via USB (ADB)**

```bash
# 1. Conectar celular via USB
# 2. Habilitar "Depuração USB" no celular:
#    Configurações > Sobre > Toque 7x em "Número da versão"
#    Configurações > Opções do desenvolvedor > Depuração USB

# 3. Verificar se celular está conectado
adb devices

# 4. Instalar APK
adb install rastreamento-nacom-dev.apk
# ou
adb install rastreamento-nacom-prod.apk
```

### **Opção B: Via Arquivo (WhatsApp/Email)**

```bash
# 1. Enviar APK para celular
# Você pode enviar o arquivo rastreamento-nacom-*.apk via:
# - WhatsApp
# - Email
# - Google Drive
# - Pendrive

# 2. No celular:
# - Abrir arquivo APK
# - Permitir "Instalar apps desconhecidos" (se pedido)
# - Instalar normalmente
```

---

## 6. TROUBLESHOOTING

### ❌ **Erro: "SDK location not found"**

**Causa:** Android SDK não configurado

**Solução:**
```bash
./setup-android-sdk.sh
source ~/.bashrc
```

---

### ❌ **Erro: "JAVA_HOME não definido"**

**Solução:**
```bash
# Instalar Java JDK
sudo apt install openjdk-17-jdk

# Adicionar ao ~/.bashrc
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
source ~/.bashrc
```

---

### ❌ **Erro: "Gradle build failed"**

**Solução:**
```bash
# Limpar cache do Gradle
cd android
./gradlew clean
cd ..

# Sincronizar novamente
npx cap sync android

# Tentar build novamente
./build-dev.sh
```

---

### ❌ **Erro: "permission denied: ./gradlew"**

**Solução:**
```bash
chmod +x android/gradlew
./build-dev.sh
```

---

### ⚠️ **GPS não funciona no app**

**Verificar permissões:**
1. Abrir app no celular
2. Configurações > Permissões
3. **Localização** → Permitir o tempo todo (background)
4. **Notificações** → Permitir (para notificação persistente)

---

### ⚠️ **App não conecta ao servidor**

**DEV:**
- Verificar se Flask está rodando: `http://192.168.1.100:5000`
- Celular e PC na mesma rede WiFi

**PROD:**
- Verificar se servidor Render está online
- Testar no navegador: `https://sistema-fretes.onrender.com`

---

## 7. DEPLOY PRODUÇÃO

### **Checklist antes de distribuir:**

- [ ] Build PROD rodado com sucesso
- [ ] APK testado em pelo menos 1 celular
- [ ] Servidor de produção funcionando
- [ ] GPS funciona em background
- [ ] Notificação persistente aparece
- [ ] Ping chegando no dashboard

### **Distribuição:**

**Opção 1: Link direto**
```bash
# Upload APK para algum servidor
# Enviar link para motoristas
# Ex: https://sistema-fretes.onrender.com/download/app.apk
```

**Opção 2: Google Play (Interno)**
- Criar conta Google Play Console
- Upload APK como "Internal Testing"
- Adicionar emails dos motoristas
- Enviar link de teste

**Opção 3: WhatsApp/Email**
- Enviar APK diretamente
- Instruir instalação manual

---

## 📊 DIFERENÇAS: DEV vs PROD

| Item | DEV | PROD |
|------|-----|------|
| **Servidor** | http://192.168.1.100:5000 | https://sistema-fretes.onrender.com |
| **Rede** | Mesma WiFi obrigatório | Internet 4G/WiFi |
| **APK** | rastreamento-nacom-dev.apk | rastreamento-nacom-prod.apk |
| **Nome App** | "Rastreamento Nacom DEV" | "Rastreamento Nacom" |
| **Notificação** | "🚚 ... (DEV)" | "🚚 Rastreamento Ativo" |
| **Uso** | Testes internos | Motoristas reais |

---

## 🔧 COMANDOS ÚTEIS

```bash
# Ver logs do app em tempo real
adb logcat | grep Capacitor

# Desinstalar app do celular
adb uninstall com.nacom.rastreamento

# Listar dispositivos conectados
adb devices

# Verificar versão do APK
aapt dump badging rastreamento-nacom-dev.apk | grep version

# Build release (assinado) - futuro
cd android && ./gradlew assembleRelease
```

---

## 📁 ARQUIVOS PRINCIPAIS

```
projeto/
├── capacitor.config.json          # Config ativa (dev ou prod)
├── capacitor.config.dev.json      # Config desenvolvimento
├── capacitor.config.prod.json     # Config produção
│
├── build-dev.sh                   # Build DEV
├── build-prod.sh                  # Build PROD
├── setup-android-sdk.sh           # Setup inicial do SDK
│
├── app/static/capacitor/          # webDir
│   ├── index.html                 # Placeholder (redirecionamento)
│   └── capacitor.js               # Capacitor runtime
│
├── app/static/js/capacitor/       # Código fonte
│   ├── gps-service-hibrido.js     # Serviço GPS
│   ├── rastreamento-integration.js # Integração UI
│   └── capacitor.js               # Runtime (cópia)
│
├── android/                       # Projeto Android nativo
│   ├── app/build/outputs/apk/     # APKs gerados aqui
│   └── local.properties           # SDK path (gerado por setup)
│
├── rastreamento-nacom-dev.apk     # APK desenvolvimento
└── rastreamento-nacom-prod.apk    # APK produção
```

---

## ✅ STATUS IMPLEMENTAÇÃO

- [x] GPS Service Híbrido (native + web)
- [x] Background Geolocation plugin configurado
- [x] Permissões Android completas
- [x] Templates adaptados (backward compatible)
- [x] Build scripts (dev + prod)
- [x] Setup automatizado do SDK
- [x] Documentação completa
- [x] Index.html no webDir
- [x] Configs separados por ambiente
- [ ] ⏳ Android Studio instalando...
- [ ] ⏳ Primeiro build

---

## 📱 PRÓXIMOS PASSOS

**AGORA:**
1. Aguardar Android Studio terminar instalação
2. Rodar: `./setup-android-sdk.sh`
3. Rodar: `./build-dev.sh`
4. Testar APK em celular

**DEPOIS:**
1. Build produção: `./build-prod.sh`
2. Distribuir para motoristas
3. Monitorar no dashboard

---

## 🆘 SUPORTE

**Problemas?**
1. Consultar seção [Troubleshooting](#6-troubleshooting)
2. Ver logs: `adb logcat | grep Capacitor`
3. Verificar documentação oficial:
   - [Capacitor Docs](https://capacitorjs.com/docs)
   - [Background Geolocation](https://github.com/capacitor-community/background-geolocation)

**Desenvolvido por:** Rafael Nascimento
**Data:** Outubro 2025
**Versão:** 1.0.0
