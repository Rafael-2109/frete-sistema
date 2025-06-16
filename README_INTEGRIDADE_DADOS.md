# 🔧 Scripts de Integridade de Dados

Este documento explica como usar os scripts criados para garantir a integridade dos dados no sistema de fretes.

## 📋 Visão Geral das Correções Implementadas

### 1. **Alterações no config.py**
- Adicionada configuração para filtrar apenas NFs FOB do monitoramento
- `FILTRAR_FOB_MONITORAMENTO`: Remove NFs com incoterm FOB (ativo por padrão)
- ✅ **REGRA CORRETA**: NFs em embarques não-FOB DEVEM estar no monitoramento
- 🚫 **REMOVIDO**: `FILTRAR_EMBARQUES_MONITORAMENTO` (era problemático)

### 2. **Correção do Filtro "Sem Agendamento"**
- Corrigida lógica no template `listar_entregas.html`
- Não mostra mais alerta "Sem Agendamento" quando a forma de agendamento for "SEM AGENDAMENTO"

### 3. **Filtros na Importação do Faturamento**
- Filtros aplicados durante a sincronização:
  - ✅ **NFs FOB**: Não são incluídas no monitoramento
  - ✅ **NFs em embarques FOB**: Não são incluídas no monitoramento  
  - ✅ **NFs em embarques não-FOB**: São incluídas normalmente no monitoramento

## 🚀 Scripts Disponíveis

### 1. **inativar_nfs_fob.py** - Inativar NFs FOB
```bash
# Simular inativação (recomendado primeiro)
python inativar_nfs_fob.py --dry-run

# Executar inativação
python inativar_nfs_fob.py --confirmar
```

**O que faz:**
- Identifica NFs com incoterm FOB no faturamento
- Marca como inativas no faturamento
- Remove do monitoramento de entregas
- Mostra estatísticas detalhadas

### 2. **analisar_nfs_cif_nao_vinculadas.py** - Analisar NFs CIF
```bash
# Análise básica dos últimos 30 dias
python analisar_nfs_cif_nao_vinculadas.py

# Análise detalhada dos últimos 60 dias
python analisar_nfs_cif_nao_vinculadas.py --detalhado --recentes=60

# Análise de todas as NFs
python analisar_nfs_cif_nao_vinculadas.py --recentes=0
```

**O que faz:**
- Identifica NFs CIF que não estão no monitoramento
- Categoriza os motivos (embarque FOB, embarque normal, sem embarque, dados incompletos)
- Sugere ações corretivas
- Calcula taxa de vinculação

### 3. **preparar_atualizacao_entrega_monitorada.py** - Atualizar via Planilha
```bash
# Simular atualizações
python preparar_atualizacao_entrega_monitorada.py planilha.xlsx --dry-run

# Executar atualizações
python preparar_atualizacao_entrega_monitorada.py planilha.xlsx --confirmar

# Usar aba específica
python preparar_atualizacao_entrega_monitorada.py planilha.xlsx --sheet="Dados" --confirmar
```

**Estrutura da Planilha:**
| Coluna | Obrigatório | Descrição |
|--------|-------------|-----------|
| numero_nf | ✅ | Número da NF |
| data_embarque | ❌ | Data de embarque |
| data_entrega_prevista | ❌ | Data de entrega prevista |
| data_agenda | ❌ | Data da agenda |
| status_finalizacao | ❌ | Status: 'Cancelada', 'Devolvida', etc. |
| protocolo_agendamento | ❌ | Protocolo do agendamento |
| data_agendamento | ❌ | Data do agendamento |
| acompanhamento_descricao | ❌ | Descrição do acompanhamento |

**O que faz:**
- Atualiza datas (embarque, entrega prevista, agenda)
- Define status de finalização (Cancelada/Devolvida)
- Cria agendamentos com protocolo
- Adiciona acompanhamentos informativos

### 4. **testar_correcoes_integridade.py** - Testar Correções
```bash
# Teste básico
python testar_correcoes_integridade.py

# Teste detalhado
python testar_correcoes_integridade.py --verbose
```

**O que testa:**
- ✅ Filtro FOB funcionando
- ✅ Filtro "Sem Agendamento" funcionando
- ✅ Vinculação de NFs CIF adequada
- ✅ Sincronização respeitando filtros

### 5. **diagnosticar_nfs_embarque_nao_monitoradas.py** - Diagnóstico Específico
```bash
# Diagnóstico geral
python diagnosticar_nfs_embarque_nao_monitoradas.py

# Análise de embarque específico
python diagnosticar_nfs_embarque_nao_monitoradas.py --embarque=123

# Tentar corrigir automaticamente
python diagnosticar_nfs_embarque_nao_monitoradas.py --corrigir
```

**O que faz:**
- Identifica NFs que estão em `EmbarqueItem` mas não em `EntregaMonitorada`
- Categoriza os problemas (sem faturamento, FOB em embarque não-FOB, sincronização)
- Pode tentar corrigir automaticamente problemas de sincronização
- Calcula taxa de sincronização por embarque

### 6. **Scripts Auxiliares Existentes**
```bash
# Testar filtros de monitoramento
python testar_filtros_monitoramento.py

# Configurar filtros
python configurar_filtros_monitoramento.py
```

## 📊 Fluxo Recomendado de Uso

### **1. Diagnóstico Inicial**
```bash
# 🎯 PROBLEMA ESPECÍFICO: NFs em embarques não monitoradas
python diagnosticar_nfs_embarque_nao_monitoradas.py

# Testar estado geral
python testar_correcoes_integridade.py --verbose

# Analisar NFs CIF não vinculadas
python analisar_nfs_cif_nao_vinculadas.py --detalhado
```

### **2. Limpeza de NFs FOB**
```bash
# Simular primeiro
python inativar_nfs_fob.py --dry-run

# Executar se estiver OK
python inativar_nfs_fob.py --confirmar
```

### **3. Atualizações via Planilha (se necessário)**
```bash
# Preparar planilha com dados
# Simular atualizações
python preparar_atualizacao_entrega_monitorada.py dados.xlsx --dry-run

# Executar se estiver OK
python preparar_atualizacao_entrega_monitorada.py dados.xlsx --confirmar
```

### **4. Verificação Final**
```bash
# Testar todas as correções
python testar_correcoes_integridade.py --verbose
```

## ⚠️ Cuidados Importantes

### **Sempre Simular Primeiro**
- Use `--dry-run` antes de executar alterações
- Revise os resultados antes de confirmar
- Faça backup dos dados importantes

### **Monitoramento Contínuo**
- Execute `testar_correcoes_integridade.py` regularmente
- Monitore a taxa de vinculação de NFs CIF
- Verifique se novos problemas surgem

### **Configurações de Ambiente**
```bash
# Verificar configurações atuais
python -c "from app import create_app; app = create_app(); print(f'FOB: {app.config.get(\"FILTRAR_FOB_MONITORAMENTO\")}'); print(f'Embarques: {app.config.get(\"FILTRAR_EMBARQUES_MONITORAMENTO\")}')"
```

## 🔍 Solução de Problemas

### **NFs FOB ainda aparecem no monitoramento**
1. Execute `python inativar_nfs_fob.py --confirmar`
2. Verifique configuração `FILTRAR_FOB_MONITORAMENTO=True`
3. Execute sincronização manual se necessário

### **Taxa de vinculação CIF baixa**
1. Execute `python analisar_nfs_cif_nao_vinculadas.py --detalhado`
2. Verifique motivos específicos
3. Execute sincronização manual das NFs sem embarque

### **NFs em embarques não aparecem no monitoramento**
1. Execute `python diagnosticar_nfs_embarque_nao_monitoradas.py`
2. Identifique a categoria do problema:
   - **Sem faturamento**: Importar faturamento dessas NFs
   - **FOB em embarque não-FOB**: Revisar classificação do embarque
   - **Problemas de sincronização**: Use `--corrigir` para tentar resolver
3. Para casos específicos: `python diagnosticar_nfs_embarque_nao_monitoradas.py --embarque=123 --corrigir`

### **Alertas "Sem Agendamento" incorretos**
1. Verifique se as correções no template foram aplicadas
2. Confirme que contatos com forma "SEM AGENDAMENTO" estão corretos
3. Execute `python testar_correcoes_integridade.py`

## 📞 Suporte

Para problemas específicos, execute primeiro:
```bash
python testar_correcoes_integridade.py --verbose
```

E inclua o resultado completo ao reportar o problema. 