<!-- doc:meta
tipo: how-to
camada: L3
sot_de: Visao geral e quick start do app nativo de rastreamento GPS (Capacitor) — instalacao, build e troubleshooting.
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 📱 RASTREAMENTO GPS - APP NATIVO (CAPACITOR)

> **Papel:** porta de entrada do app nativo de rastreamento GPS (Capacitor) — explica o que e, como instalar/buildar e como resolver problemas comuns.

## Indice

- [O que e](#-o-que-e)
- [Quick Start](#-quick-start)
- [Comparacao](#-comparacao)
- [Arquivos principais](#-arquivos-principais)
- [Comandos uteis](#-comandos-uteis)
- [Troubleshooting](#-troubleshooting)
- [Documentacao completa](#-documentacao-completa)
- [Status](#-status)

---

## 🎯 O QUE É

Sistema de rastreamento GPS que funciona como:
- **App Android/iOS**: GPS funciona em background (minimizado, tela desligada, app fechado)
- **Web Browser**: GPS tradicional (fallback automático)

**Detecção automática de plataforma** - Usa a melhor tecnologia disponível sem configuração manual.

---

## ⚡ QUICK START

### **1. Instalar Dependências**
```bash
npm install
```

### **2. Build APK**
```bash
# Build genérico (debug)
./build-app.sh

# Build apontando para o servidor local de desenvolvimento (http://192.168.1.100:5000)
./build-dev.sh

# Build apontando para produção (https://sistema-fretes.onrender.com)
./build-prod.sh
```

### **3. Instalar no Celular**
```bash
# Via USB (escolha o APK gerado pelo script usado acima)
adb install rastreamento-nacom-debug.apk   # build-app.sh
adb install rastreamento-nacom-dev.apk     # build-dev.sh
adb install rastreamento-nacom-prod.apk    # build-prod.sh

# Ou envie o APK por WhatsApp e instale manualmente
```

### **4. Usar**
1. Abra o app
2. Escaneie QR Code do embarque
3. Aceite permissões
4. GPS funciona automaticamente! 🚀

---

## 📊 COMPARAÇÃO

| Feature | Web | App Nativo |
|---------|-----|------------|
| GPS com app aberto | ✅ | ✅ |
| GPS minimizado | ❌ | ✅ |
| GPS tela desligada | ❌ | ✅ |
| GPS app fechado | ❌ | ✅ |
| Precisão | 20-100m | 10-30m |
| Taxa sucesso | ~60% | ~95% |

---

## 📁 ARQUIVOS PRINCIPAIS

```
├── app/static/js/capacitor/
│   ├── gps-service-hibrido.js         # 🎯 Serviço GPS híbrido
│   ├── rastreamento-integration.js    # 🔗 Integração com UI
│   └── capacitor.js                   # ⚙️  Capacitor Core
│
├── android/                            # 📱 Projeto Android
│   └── app/build/outputs/apk/         # 📦 APKs gerados
│
├── capacitor.config.json               # ⚙️  Config Capacitor
├── package.json                        # 📦 Dependencies
├── build-app.sh                        # 🚀 Build genérico → rastreamento-nacom-debug.apk
├── build-dev.sh                        # 🧪 Build DEV → rastreamento-nacom-dev.apk (servidor local)
├── build-prod.sh                       # 🌐 Build PROD → rastreamento-nacom-prod.apk (produção)
├── CAPACITOR_SETUP.md                  # 📖 Doc completa
└── CAPACITOR_README.md                 # 📄 Este arquivo
```

---

## 🔧 COMANDOS ÚTEIS

```bash
# Build APK genérico (debug)
./build-app.sh

# Build DEV (aponta para o servidor local http://192.168.1.100:5000)
./build-dev.sh

# Build PROD (aponta para https://sistema-fretes.onrender.com)
./build-prod.sh

# Sincronizar código web → Android
npm run sync:android

# Abrir Android Studio
npm run open:android

# Build manual
cd android && ./gradlew assembleDebug

# Instalar via ADB
adb install rastreamento-nacom-debug.apk

# Ver logs do app
adb logcat | grep Capacitor
```

---

## 🚨 TROUBLESHOOTING

### GPS não funciona no app
- Verificar permissões no `android/app/src/main/AndroidManifest.xml`
- Deve ter: `ACCESS_BACKGROUND_LOCATION`, `FOREGROUND_SERVICE_LOCATION`

### Notificação não aparece
- Android 13+: Aceitar permissão de notificações
- Verificar `notificationTitle` e `notificationText` do plugin `BackgroundGeolocation` em `capacitor.config.json`

### Build falha
```bash
npm run sync:android
cd android && ./gradlew clean && ./gradlew assembleDebug
```

---

## 📖 DOCUMENTAÇÃO COMPLETA

Ver [`capacitor-setup.md`](./capacitor-setup.md) para:
- Arquitetura detalhada
- Fluxo de dados
- Deploy produção
- Troubleshooting avançado

---

## ✅ STATUS

- [x] Serviço GPS híbrido implementado
- [x] Plugin background geolocation configurado
- [x] Permissões Android configuradas
- [x] Template adaptado (backward compatible)
- [x] Script de build automatizado
- [x] Documentação completa
- [x] Pronto para produção

---

**Desenvolvido**: Outubro 2025
**Versão**: 1.0.0
**Licença**: MIT
