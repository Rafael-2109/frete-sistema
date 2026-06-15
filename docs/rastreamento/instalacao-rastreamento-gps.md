<!-- doc:meta
tipo: how-to
camada: L2
sot_de: Procedimento de instalacao, configuracao e troubleshooting do sistema de rastreamento GPS de embarques (LGPD, QR Code, pings GPS)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🚀 INSTALAÇÃO DO SISTEMA DE RASTREAMENTO GPS

> **Papel:** Guia how-to para instalar, configurar e operar o sistema de rastreamento GPS de embarques (modelos, QR Code, pings GPS e limpeza LGPD).

**Data**: 01/10/2025
**Status**: ✅ EM PRODUÇÃO
**Versão**: 1.0

---

## Indice

- [Checklist de Implementação](#-checklist-de-implementação)
- [Passo a Passo - Instalação](#-passo-a-passo---instalação)
- [Teste do Sistema](#-teste-do-sistema)
- [Monitoramento e Logs](#-monitoramento-e-logs)
- [Troubleshooting](#-troubleshooting)
- [Documentação Técnica](#-documentação-técnica)
- [Próximos Passos](#-próximos-passos)
- [Suporte](#-suporte)

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

- [x] Modelos de banco de dados criados (4 modelos)
- [x] Serviços de QR Code e GPS implementados
- [x] Blueprint com rotas/APIs criado
- [x] Templates HTML mobile-friendly
- [x] Integração com criação de embarques (automática)
- [x] QR Code adicionado na impressão de embarques
- [x] Worker de limpeza LGPD criado
- [x] Blueprint registrado em `app/__init__.py`
- [x] Migration do banco executada
- [x] Bibliotecas instaladas
- [x] Sistema testado

---

## 🔧 PASSO A PASSO - INSTALAÇÃO

### **1. Instalar Bibliotecas** (2 minutos)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema

# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências (versões atuais em requirements.txt:157-159)
pip install qrcode==8.2 pillow==12.1.1 haversine==2.9.0

# Verificar instalação
python -c "import qrcode, PIL, haversine; print('✅ Bibliotecas instaladas!')"
```

> O geocoding usa a Google Maps API (mesma de `mapa_service.py`); `geopy` não faz parte das dependências.

###  **2. Criar Migration do Banco de Dados** (1 minuto)

```bash
# Criar migration
flask db migrate -m "Adiciona sistema de rastreamento GPS com LGPD"

# IMPORTANTE: Revisar arquivo gerado em migrations/versions/
# Verificar se as tabelas estão corretas:
# - rastreamento_embarques
# - pings_gps
# - logs_rastreamento
# - configuracao_rastreamento

# Aplicar migration
flask db upgrade

# Verificar tabelas criadas
psql -d frete_sistema -c "\dt rastreamento*"
psql -d frete_sistema -c "\dt pings_gps"
```

### **3. Configurar Worker de Limpeza LGPD** (Opcional - 5 minutos)

**Opção A: APScheduler (em desenvolvimento)**

Adicione ao arquivo onde o scheduler é configurado:

```python
from app.rastreamento.tasks import limpar_dados_expirados_lgpd, verificar_rastreamentos_inativos, gerar_relatorio_rastreamento

# Job de limpeza LGPD (diário às 2h)
scheduler.add_job(
    id='limpar_dados_lgpd',
    func=limpar_dados_expirados_lgpd,
    trigger='cron',
    hour=2,
    minute=0,
    max_instances=1,
    coalesce=True
)

# Job de verificação de rastreamentos inativos (a cada 6h)
scheduler.add_job(
    id='verificar_rastreamentos_inativos',
    func=verificar_rastreamentos_inativos,
    trigger='interval',
    hours=6,
    max_instances=1
)

# Job de relatório diário (7h da manhã)
scheduler.add_job(
    id='relatorio_rastreamento',
    func=gerar_relatorio_rastreamento,
    trigger='cron',
    hour=7,
    minute=0
)
```

**Opção B: Cron do Sistema (em produção)**

```bash
# Editar crontab
crontab -e

# Adicionar linha (executa diariamente às 2h)
0 2 * * * cd /caminho/app && /caminho/venv/bin/python -c "from app import create_app; from app.rastreamento.tasks import limpar_dados_expirados_lgpd; app = create_app(); app.app_context().push(); limpar_dados_expirados_lgpd()"
```

### **4. Reiniciar Aplicação** (1 minuto)

```bash
# Desenvolvimento
flask run

# Produção (Gunicorn)
sudo systemctl restart gunicorn

# Verificar logs
tail -f /var/log/gunicorn/error.log
```

### **5. Configuração Inicial** (Opcional - 2 minutos)

O sistema já vem com configurações padrão, mas você pode ajustar:

```python
# Acessar shell do Flask
flask shell

# Importar modelo de configuração
from app.rastreamento.models import ConfiguracaoRastreamento

# Obter configuração (cria automaticamente se não existir)
config = ConfiguracaoRastreamento.get_config()

# Ajustar parâmetros (se necessário)
config.intervalo_ping_segundos = 120  # 2 minutos (padrão)
config.distancia_chegada_metros = 200.0  # 200 metros (padrão)
config.dias_retencao_dados = 90  # 90 dias (padrão)

# Salvar
from app import db
db.session.commit()
```

---

## 🧪 TESTE DO SISTEMA

### **Teste 1: Criar Embarque e Verificar Rastreamento**

```bash
# Acessar shell
flask shell

# Criar embarque de teste (ou use interface web)
from app.embarques.models import Embarque
from app.rastreamento.models import RastreamentoEmbarque

# Buscar um embarque existente
embarque = Embarque.query.first()

# Verificar se tem rastreamento
if hasattr(embarque, 'rastreamento') and embarque.rastreamento:
    print(f"✅ Rastreamento criado!")
    print(f"URL: {embarque.rastreamento.url_rastreamento}")
    print(f"Token: {embarque.rastreamento.token_acesso}")
else:
    print("❌ Rastreamento não criado automaticamente")
```

### **Teste 2: Gerar QR Code**

```python
from app.rastreamento.services.qrcode_service import QRCodeService

# Gerar QR Code de teste
url_teste = "https://exemplo.com/rastreamento/aceite/TOKEN123"
qr_base64 = QRCodeService.gerar_qrcode(url_teste)

if qr_base64:
    print("✅ QR Code gerado com sucesso!")
    print(f"Tamanho: {len(qr_base64)} caracteres")
else:
    print("❌ Erro ao gerar QR Code")
```

### **Teste 3: Cálculo de Distância GPS**

```python
from app.rastreamento.services.gps_service import GPSService

# Coordenadas de teste (São Paulo e Rio de Janeiro)
sp = (-23.5505, -46.6333)
rj = (-22.9068, -43.1729)

# Calcular distância
distancia = GPSService.calcular_distancia(sp, rj, 'km')
print(f"Distância SP-RJ: {distancia} km")  # ~360 km

# Verificar proximidade
proximo = GPSService.esta_proximo(sp, sp, raio_metros=200)
print(f"Está próximo: {proximo}")  # True
```

### **Teste 4: Fluxo Completo via Browser**

1. **Criar embarque** pela interface web
2. **Imprimir embarque** - Verificar se QR Code aparece
3. **Escanear QR Code** com celular
4. **Aceitar termo LGPD**
5. **Verificar rastreamento ativo**
6. **Simular chegada** (mudar coordenadas manualmente se necessário)
7. **Upload de canhoto**
8. **Verificar dashboard** de monitoramento

---

## 📊 MONITORAMENTO E LOGS

### **Verificar Rastreamentos Ativos**

```sql
-- No psql
SELECT
    r.id,
    r.embarque_id,
    e.numero as embarque_numero,
    r.status,
    r.aceite_lgpd,
    r.ultimo_ping_em,
    (SELECT COUNT(*) FROM pings_gps WHERE rastreamento_id = r.id) as total_pings
FROM rastreamento_embarques r
JOIN embarques e ON e.id = r.embarque_id
WHERE r.status IN ('ATIVO', 'CHEGOU_DESTINO')
ORDER BY r.ultimo_ping_em DESC;
```

### **Verificar Pings GPS Recentes**

```sql
SELECT
    p.id,
    p.rastreamento_id,
    p.latitude,
    p.longitude,
    p.distancia_destino,
    p.bateria_nivel,
    p.criado_em
FROM pings_gps p
WHERE p.criado_em > NOW() - INTERVAL '1 hour'
ORDER BY p.criado_em DESC
LIMIT 20;
```

### **Verificar Dados a Expirar (LGPD)**

```sql
SELECT
    id,
    embarque_id,
    status,
    criado_em,
    data_expurgo_lgpd,
    DATE_PART('day', data_expurgo_lgpd - NOW()) as dias_para_expurgo
FROM rastreamento_embarques
WHERE data_expurgo_lgpd > NOW()
ORDER BY data_expurgo_lgpd ASC
LIMIT 10;
```

---

## 🔧 TROUBLESHOOTING

### **Problema: QR Code não aparece na impressão**

**Causa**: Rastreamento não foi criado automaticamente

**Solução**:
```python
# Criar rastreamento manualmente
from app.rastreamento.models import RastreamentoEmbarque
from app import db

embarque_id = 123  # ID do embarque
rastreamento = RastreamentoEmbarque(
    embarque_id=embarque_id,
    criado_por='Sistema'
)
db.session.add(rastreamento)
db.session.commit()
```

### **Problema: Erro ao importar RastreamentoEmbarque**

**Causa**: Migration não foi aplicada

**Solução**:
```bash
flask db upgrade
```

### **Problema: GPS não funciona no celular**

**Causa**: Permissão de localização não concedida

**Solução**:
1. Navegador precisa de HTTPS (ou localhost)
2. Usuário precisa aceitar permissão de localização
3. GPS precisa estar ativo no dispositivo

### **Problema: Worker LGPD não executa**

**Causa**: Scheduler não configurado

**Solução**: Configurar APScheduler ou Cron (ver seção 3 acima)

---

## 📖 DOCUMENTAÇÃO TÉCNICA

### **Modelos Criados**

| Modelo | Arquivo | Tabela | Descrição |
|--------|---------|--------|-----------|
| RastreamentoEmbarque | app/rastreamento/models.py | rastreamento_embarques | Controle principal |
| PingGPS | app/rastreamento/models.py | pings_gps | Pings GPS (2 em 2 min) |
| LogRastreamento | app/rastreamento/models.py | logs_rastreamento | Auditoria LGPD |
| ConfiguracaoRastreamento | app/rastreamento/models.py | configuracao_rastreamento | Config global |

### **Rotas Disponíveis**

O módulo expõe 22 endpoints (`@rastreamento_bp.route` em `app/rastreamento/routes.py`). Principais rotas:

| Rota | Método | Público | Descrição |
|------|--------|---------|-----------|
| /rastreamento/aceite/<token> | GET/POST | ✅ | Aceite LGPD |
| /rastreamento/rastrear/<token> | GET | ✅ | Rastreamento ativo |
| /rastreamento/api/ping/<token> | POST | ✅ | Receber ping GPS |
| /rastreamento/upload_canhoto/<token> | GET/POST | ✅ | Upload canhoto |
| /rastreamento/confirmacao/<token> | GET | ✅ | Confirmação |
| /rastreamento/app | GET | ✅ | App de rastreamento |
| /rastreamento/scanner | GET | ✅ | Scanner de QR Code |
| /rastreamento/questionario | GET/POST | ✅ | Questionário de entrega |
| /rastreamento/api/verificar-proximidade | POST | ✅ | Verificar proximidade |
| /rastreamento/api/iniciar | POST | ✅ | Iniciar rastreamento |
| /rastreamento/api/encerrar | POST | ✅ | Encerrar rastreamento |
| /rastreamento/api/status | GET | ✅ | Status do rastreamento |
| /rastreamento/api/ativos | GET | ❌ | Rastreamentos ativos |
| /rastreamento/api/dificuldades | POST | ✅ | Registrar dificuldades |
| /rastreamento/api/finalizar-entrega | POST | ✅ | Finalizar entrega |
| /rastreamento/api/comentario | POST | ✅ | Registrar comentário |
| /rastreamento/dashboard | GET | ❌ | Dashboard interno |
| /rastreamento/detalhes/<id> | GET | ❌ | Detalhes interno |
| /rastreamento/monitoramento | GET | ❌ | Monitoramento interno |

### **Arquivos Criados/Modificados**

```
app/rastreamento/                              # NOVO
├── __init__.py                                # Blueprint
├── models.py                                  # 4 modelos
├── routes.py                                  # 22 endpoints
├── tasks.py                                   # Worker LGPD
├── services/
│   ├── qrcode_service.py                     # QR Code
│   └── gps_service.py                        # GPS

app/templates/rastreamento/                    # NOVO (11 templates)
├── aceite_lgpd.html                           # Aceite LGPD
├── app_inicio.html                            # App de rastreamento
├── confirmacao.html                           # Confirmação
├── dashboard.html                             # Dashboard
├── detalhes.html                              # Detalhes
├── erro.html                                  # Erro
├── monitoramento.html                         # Monitoramento
├── questionario_entrega.html                  # Questionário de entrega
├── rastreamento_ativo.html                    # Rastreamento
├── scanner_qrcode.html                        # Scanner QR Code
└── upload_canhoto.html                        # Upload

app/__init__.py                                # MODIFICADO
├── +import rastreamento_bp                    # Linha 930
└── +app.register_blueprint(rastreamento_bp)   # Linha 965

app/cotacao/routes.py                          # MODIFICADO
├── +import RastreamentoEmbarque               # Linha 22
├── +Criar rastreamento (linha 1584-1595)      # Após criar embarque
└── +Criar rastreamento (linha 2111-2119)      # Após criar embarque

app/embarques/routes.py                        # MODIFICADO
├── +import QRCodeService                      # imprimir_embarque
├── +Gerar QR Code                             # imprimir_embarque
└── +Passar qrcode_base64 para templates       # Ambas rotas

app/templates/embarques/imprimir_embarque.html # MODIFICADO
└── +Página de QR Code (linhas 309-321)        # Nova página

requirements.txt                               # MODIFICADO
└── +bibliotecas GPS/QR Code (linhas 157-159)  # qrcode, pillow, haversine
```

---

## ✅ PRÓXIMOS PASSOS

Após instalação:

1. ✅ Testar criação de embarque e verificar rastreamento
2. ✅ Testar impressão e verificar QR Code
3. ✅ Fazer teste completo com celular
4. ✅ Configurar worker de limpeza LGPD
5. ✅ Treinar equipe no uso do sistema
6. ✅ Monitorar logs nas primeiras semanas

---

## 📞 SUPORTE

Em caso de problemas:

1. Verificar logs: `tail -f /var/log/gunicorn/error.log`
2. Verificar migrations: `flask db current`
3. Consultar o código-fonte do módulo em `app/rastreamento/`
4. Abrir issue no repositório

---

**Sistema em produção. 🚀**
