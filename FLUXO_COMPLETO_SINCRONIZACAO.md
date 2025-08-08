# 🔄 FLUXO COMPLETO DE SINCRONIZAÇÃO ODOO - ANÁLISE DETALHADA

## 📍 PONTO DE ENTRADA

### 1. **SincronizacaoIntegradaService.executar_sincronizacao_completa_segura()**
```python
# Arquivo: app/odoo/services/sincronizacao_integrada_service.py
# Executa na sequência:
1. FATURAMENTO primeiro (preserva NFs)
2. CARTEIRA depois → chama: carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades()
```

---

## 📊 FLUXO PRINCIPAL: sincronizar_carteira_odoo_com_gestao_quantidades()

### 📋 ETAPA 1: VERIFICAÇÃO PRÉ-SINCRONIZAÇÃO
```python
# Linha 1137
alertas_pre_sync = self._verificar_riscos_pre_sincronizacao()
```
- Verifica se existem separações COTADAS que seriam afetadas
- Gera alertas críticos mas NÃO impede a sincronização

### 💾 ETAPA 2: BACKUP DE PRÉ-SEPARAÇÕES (CRÍTICO!)
```python
# Linha 1146
backup_result = self._criar_backup_pre_separacoes()
```

**O que faz `_criar_backup_pre_separacoes()` (linha 818-856):**
```python
# PASSO CRUCIAL: Reseta TODAS as pré-separações!
for pre_sep in pre_separacoes_ativas:
    pre_sep.recomposto = False  # 🔴 RESETA PARA FALSE!
    pre_sep.observacoes = f"Aguardando recomposição pós-sync..."
```

### 📊 ETAPA 3: ANÁLISE DO ESTADO ATUAL
```python
# Linha 1153-1179
# Carrega CarteiraPrincipal em memória
# Separa pedidos Odoo (VSC, VCD, VFB) dos não-Odoo
```

### 🔄 ETAPA 4: BUSCAR DADOS DO ODOO
```python
# Linha 1181-1194
resultado_odoo = self.obter_carteira_pendente()
# Busca apenas itens com qty_saldo > 0 e status válidos
```

### 📈 ETAPA 5: CALCULAR DIFERENÇAS
```python
# Linha 1195-1263
# Compara carteira atual vs dados Odoo
# Identifica:
- reducoes = []     # Quantidade diminuiu
- aumentos = []     # Quantidade aumentou  
- novos_itens = []  # Itens novos
- itens_removidos = [] # Itens removidos
```

### 📉 ETAPA 6: APLICAR REDUÇÕES (Hierarquia!)
```python
# Linha 1267-1307
PreSeparacaoItem.aplicar_reducao_quantidade(num_pedido, cod_produto, qtd_reduzida)
```

**Hierarquia de redução (linha 932-1055):**
1. **Saldo livre** (CarteiraPrincipal sem separacao_lote_id)
2. **Pré-separações** (ajusta qtd_selecionada_usuario)
3. **Separações ABERTO**
4. **Separações COTADO** (gera alerta crítico!)

### 📈 ETAPA 7: APLICAR AUMENTOS
```python
# Linha 1311-1347
PreSeparacaoItem.aplicar_aumento_quantidade(num_pedido, cod_produto, qtd_aumentada)
```

**Lógica de aumento (linha 1057-1122):**
- Se existe pré-separação única → aumenta ela
- Se existem múltiplas → distribui proporcionalmente
- Adiciona ao saldo livre se não há pré-separações

### 🗑️ ETAPA 8: TRATAR ITENS REMOVIDOS
```python
# Linha 1352-1387
# Se item foi removido do Odoo com qtd > 0:
PreSeparacaoItem.aplicar_reducao_quantidade(num_pedido, cod_produto, qtd_atual)
```

### 🔄 ETAPA 9: SUBSTITUIR CARTEIRA
```python
# Linha 1388-1495
# DELETA todos os registros Odoo antigos
# INSERE novos dados do Odoo
# PRESERVA registros não-Odoo
```

### 💾 ETAPA 10: COMMIT
```python
# Linha 1501
db.session.commit()
```

### 🔄 ETAPA 11: RECOMPOSIÇÃO DE PRÉ-SEPARAÇÕES
```python
# Linha 1504
recomposicao_result = self._recompor_pre_separacoes_automaticamente()
```

**O que faz `_recompor_pre_separacoes_automaticamente()` (linha 858-887):**
```python
# Chama:
resultado = PreSeparacaoItem.recompor_todas_pendentes("SYNC_ODOO_AUTO")
```

**O que faz `recompor_todas_pendentes()` (linha 824-854):**
```python
# 1. Busca TODAS com recomposto = False (foram resetadas na ETAPA 2!)
pendentes = cls.buscar_nao_recompostas()

# 2. Para cada uma:
for pre_sep in pendentes:
    # Busca item na carteira
    carteira_item = CarteiraPrincipal.query.filter(...)
    
    # Chama recompor_na_carteira()
    pre_sep.recompor_na_carteira(carteira_item, usuario)
```

**O que faz `recompor_na_carteira()` (linha 744-774):**
```python
# 1. Gera novo hash
novo_hash = self.gerar_hash_item(carteira_item)

# 2. Compara com hash original
if self.hash_item_original != novo_hash:
    logger.warning("Item foi alterado no Odoo")  # Só loga!

# 3. Marca como recomposto
self.recomposto = True  # 🟢 VOLTA PARA TRUE!
self.status = 'RECOMPOSTO'
```

### 🔍 ETAPA 12: VERIFICAÇÃO PÓS-SINCRONIZAÇÃO
```python
# Linha 1510
alertas_pos_sync = self._verificar_alertas_pos_sincronizacao()
```

---

## 🔄 CICLO DO CAMPO `recomposto`

### 📊 Estado Inicial
- Pré-separações existentes: `recomposto = true`

### 🔄 Durante Sincronização
1. **INÍCIO** (ETAPA 2): Todas viram `recomposto = false`
2. **MEIO**: Ajustes de quantidade (ignora `recomposto`)
3. **FIM** (ETAPA 11): Todas voltam para `recomposto = true`

### 🔁 Próxima Sincronização
- Repete o ciclo: false → true → false → true...

---

## ❓ O QUE O CAMPO `recomposto` REALMENTE FAZ?

### ✅ O que FAZ:
1. **Força verificação de hash** em toda sincronização (pois sempre reseta)
2. **Marca status** 'CRIADO' → 'RECOMPOSTO'
3. **Gera logs** de warning se hash mudou

### ❌ O que NÃO FAZ:
1. **NÃO ajusta quantidades** (isso é feito por aplicar_reducao/aumento_quantidade)
2. **NÃO modifica carteira**
3. **NÃO reaplica divisões**
4. **NÃO age sobre mudanças detectadas**

---

## 🎯 CONCLUSÃO

### Para Movimentações Previstas:
- **IGNORAR `recomposto`** está correto ✅
- Ambos estados (true/false) representam pré-separações ativas

### Para Sincronização:
- `recomposto` é um **ciclo decorativo** de verificação passiva
- Os **ajustes reais** acontecem via `aplicar_reducao_quantidade()` e `aplicar_aumento_quantidade()`
- Estes métodos **ignoram** completamente o campo `recomposto`

### Problema Real:
- O sistema detecta mudanças via hash mas **não age** sobre elas
- É mais uma "verificação psicológica" do que funcional
- Os ajustes de quantidade funcionam **independentemente** deste campo

---

## 📝 NOTAS IMPORTANTES

1. **Pedidos não-Odoo** (que não começam com VSC/VCD/VFB) são **protegidos** e nunca alterados

2. **Hierarquia de impacto** é respeitada: Saldo livre → Pré-separação → Separação ABERTO → Separação COTADO

3. **Separações COTADAS** geram alertas críticos mas ainda podem ser alteradas

4. O campo `recomposto` poderia ser **removido** sem impacto funcional real