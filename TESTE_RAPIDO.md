# ⚡ TESTE RÁPIDO - RASTREAMENTO GPS

**Execute este passo a passo para testar o sistema completo**

---

## ✅ PRÉ-REQUISITOS

- [x] Bibliotecas instaladas (qrcode, pillow, geopy, haversine)
- [x] Tabelas criadas no banco de dados
- [x] Aplicação reiniciada

---

## 🧪 TESTE 1: Verificar Tabelas Criadas

```bash
# Conectar ao PostgreSQL
psql -d frete_sistema

# Verificar tabelas
\dt rastreamento*

# Ver configuração
SELECT * FROM configuracao_rastreamento;
```

**Resultado esperado:**
```
 intervalo_ping_segundos | distancia_chegada_metros | dias_retencao_dados
-------------------------+--------------------------+---------------------
                     120 |                    200.0 |                  90
```

---

## 🧪 TESTE 2: Criar Embarque e Rastreamento

### **Opção A: Via Interface Web**

1. Acesse o sistema
2. Crie um novo embarque
3. Verifique no banco se rastreamento foi criado:

```sql
SELECT
    r.id,
    r.embarque_id,
    e.numero as embarque_numero,
    r.status,
    r.aceite_lgpd,
    LEFT(r.token_acesso, 20) as token_parcial
FROM rastreamento_embarques r
JOIN embarques e ON e.id = r.embarque_id
ORDER BY r.criado_em DESC
LIMIT 5;
```

### **Opção B: Via Script Python**

```bash
python criar_tabelas_rastreamento.py
# Digite 'S' quando perguntar sobre criar rastreamento de teste
```

---

## 🧪 TESTE 3: Imprimir Embarque e Ver QR Code

1. **Acesse:** Embarques → Visualizar Embarque
2. **Clique:** "Imprimir Embarque"
3. **Verifique:** QR Code deve aparecer na **última página**

**QR Code deve ter:**
- ✅ Tamanho: 300x300px
- ✅ Borda verde
- ✅ Instruções abaixo
- ✅ Número do embarque

---

## 🧪 TESTE 4: Escanear QR Code (Celular)

1. **Abra câmera** do celular
2. **Escaneie QR Code** da impressão
3. **Deve abrir:** Tela de aceite LGPD

**Tela deve mostrar:**
- ✅ Informações do embarque
- ✅ Termo LGPD completo
- ✅ Checkbox "Li e aceito"
- ✅ Botão "Aceitar e Iniciar"

---

## 🧪 TESTE 5: Aceitar Termo LGPD

1. **Marque:** Checkbox "Li e aceito"
2. **Clique:** "Aceitar e Iniciar Rastreamento"
3. **Permita:** Acesso à localização quando solicitado

**Deve redirecionar para:** Tela de rastreamento ativo

---

## 🧪 TESTE 6: Rastreamento Ativo

**Tela deve mostrar:**
- ✅ "RASTREAMENTO ATIVO" (pulsando)
- ✅ Destino do embarque
- ✅ Distância até destino (calculando...)
- ✅ Indicador "Última atualização"
- ✅ Botão "ENTREGUEI O PEDIDO"

**No console do navegador (F12):**
```
🚀 Iniciando rastreamento GPS...
📍 Intervalo de ping: 120 segundos
✅ Rastreamento iniciado com sucesso
📍 Localização atualizada: [lat, lon]
✅ Ping enviado com sucesso
```

---

## 🧪 TESTE 7: Verificar Pings no Banco

Após 2-5 minutos de rastreamento ativo:

```sql
SELECT
    p.id,
    p.rastreamento_id,
    ROUND(p.latitude::numeric, 4) as lat,
    ROUND(p.longitude::numeric, 4) as lon,
    ROUND(p.distancia_destino::numeric, 0) as distancia_m,
    p.bateria_nivel,
    p.criado_em
FROM pings_gps p
ORDER BY p.criado_em DESC
LIMIT 10;
```

**Resultado esperado:**
- ✅ Novos pings a cada 2 minutos
- ✅ Coordenadas GPS válidas
- ✅ Distância até destino calculada
- ✅ Nível de bateria capturado

---

## 🧪 TESTE 8: Simular Chegada ao Destino

Se a distância não chegar a 200m naturalmente, **simule**:

```sql
-- Forçar status de chegada ao destino
UPDATE rastreamento_embarques
SET
    status = 'CHEGOU_DESTINO',
    chegou_destino_em = NOW(),
    distancia_minima_atingida = 150.0
WHERE embarque_id = [ID_DO_EMBARQUE];
```

**Recarregue a página do rastreamento:**
- ✅ Badge deve mudar: "🎯 PRÓXIMO AO DESTINO!"
- ✅ Cor muda para amarelo piscando
- ✅ Alerta: "Você está próximo ao destino!"

---

## 🧪 TESTE 9: Upload de Canhoto

1. **Clique:** "ENTREGUEI O PEDIDO"
2. **Deve abrir:** Tela de upload de canhoto
3. **Clique:** "Abrir Câmera" ou arraste arquivo
4. **Tire foto** ou selecione imagem
5. **Verifique:** Preview aparece
6. **Verifique:** "Localização capturada" com coordenadas
7. **Clique:** "Confirmar Entrega"

**Resultado:**
- ✅ "Canhoto enviado com sucesso!"
- ✅ Redireciona para tela de confirmação

---

## 🧪 TESTE 10: Verificar Dados Salvos

```sql
-- Ver rastreamento completo
SELECT
    r.id,
    r.embarque_id,
    r.status,
    r.aceite_lgpd,
    r.aceite_lgpd_em,
    r.aceite_lgpd_ip,
    r.rastreamento_iniciado_em,
    r.chegou_destino_em,
    r.distancia_minima_atingida,
    r.canhoto_arquivo,
    r.canhoto_enviado_em,
    (SELECT COUNT(*) FROM pings_gps WHERE rastreamento_id = r.id) as total_pings
FROM rastreamento_embarques r
WHERE r.embarque_id = [ID_DO_EMBARQUE];

-- Ver logs de auditoria
SELECT * FROM logs_rastreamento
WHERE rastreamento_id = [ID_RASTREAMENTO]
ORDER BY criado_em;
```

**Resultado esperado:**
- ✅ `status` = 'ENTREGUE'
- ✅ `aceite_lgpd` = true
- ✅ `aceite_lgpd_ip` preenchido
- ✅ `canhoto_arquivo` com caminho
- ✅ `total_pings` > 0
- ✅ Logs: ACEITE_LGPD, CHEGADA_DESTINO, UPLOAD_CANHOTO

---

## 🧪 TESTE 11: Dashboard de Monitoramento

1. **Acesse:** `/rastreamento/dashboard`
2. **Deve mostrar:**
   - ✅ Estatísticas (rastreamentos ativos, próximos ao destino)
   - ✅ Mapa com marcadores
   - ✅ Tabela de rastreamentos ativos
   - ✅ Botão "Detalhes" em cada rastreamento

---

## 🧪 TESTE 12: Detalhes do Rastreamento

1. **Clique:** "Detalhes" em um rastreamento
2. **Deve mostrar:**
   - ✅ Timeline de eventos
   - ✅ Mapa com histórico de rota
   - ✅ Tabela de pings GPS
   - ✅ Logs de auditoria
   - ✅ Imagem do canhoto (se enviado)

---

## 🧪 TESTE 13: Verificar LGPD (90 dias)

```sql
-- Ver datas de expurgo
SELECT
    id,
    embarque_id,
    criado_em,
    data_expurgo_lgpd,
    DATE_PART('day', data_expurgo_lgpd - NOW()) as dias_restantes
FROM rastreamento_embarques
ORDER BY criado_em DESC;
```

**Resultado esperado:**
- ✅ `data_expurgo_lgpd` = criado_em + 90 dias
- ✅ `dias_restantes` ≈ 90

---

## 🧪 TESTE 14: Worker de Limpeza LGPD (Opcional)

**Testar manualmente:**

```bash
flask shell
```

```python
from app.rastreamento.tasks import limpar_dados_expirados_lgpd
from app import db

# Simular rastreamento expirado
from app.rastreamento.models import RastreamentoEmbarque
from datetime import datetime, timedelta

rastr = RastreamentoEmbarque.query.first()
rastr.data_expurgo_lgpd = datetime.utcnow() - timedelta(days=1)
db.session.commit()

# Executar limpeza
total, erros = limpar_dados_expirados_lgpd()
print(f"Expurgados: {total}, Erros: {erros}")
```

**Resultado:**
- ✅ Rastreamento deletado
- ✅ Pings deletados (cascade)
- ✅ Logs deletados (cascade)

---

## ✅ CHECKLIST FINAL

| Teste | Status | Observação |
|-------|--------|------------|
| Tabelas criadas | ⬜ | 4 tabelas + índices |
| Rastreamento auto-criado | ⬜ | Ao criar embarque |
| QR Code na impressão | ⬜ | Última página |
| Aceite LGPD funciona | ⬜ | Mobile-friendly |
| GPS captura coordenadas | ⬜ | A cada 2 minutos |
| Pings salvos no banco | ⬜ | Tabela pings_gps |
| Detecção de chegada | ⬜ | ≤ 200 metros |
| Upload de canhoto | ⬜ | Com GPS |
| Dashboard visível | ⬜ | Mapa + estatísticas |
| Logs de auditoria | ⬜ | Tabela logs_rastreamento |
| Data expurgo LGPD | ⬜ | Criado_em + 90 dias |

---

## 🎯 RESULTADO ESPERADO

**Se TODOS os testes passaram:**
- ✅ Sistema 100% funcional
- ✅ Conformidade LGPD
- ✅ Pronto para produção

**Se ALGUM teste falhou:**
- Consulte: [`INSTALACAO_RASTREAMENTO_GPS.md`](INSTALACAO_RASTREAMENTO_GPS.md) → Troubleshooting
- Verifique logs: `tail -f /var/log/gunicorn/error.log`
- Execute novamente: `python criar_tabelas_rastreamento.py`

---

**Desenvolvido com precisão! 🎯**
