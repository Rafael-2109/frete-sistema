# Scripts de Limpeza de Embarques Cancelados

Este conjunto de scripts foi criado para resolver problemas com embarques cancelados que ainda possuem NFs vinculadas, impedindo que os pedidos voltem ao status "Aberto".

## 📋 Problema Resolvido

Quando um embarque é cancelado, as NFs dos itens deveriam ser removidas automaticamente para que os pedidos voltem ao status "Aberto". Estes scripts corrigem essa situação.

## 🔧 Scripts Disponíveis

### 1. `verificar_embarques_cancelados.py` (SEGURO - Apenas consulta)

**Função:** Verifica e lista todos os embarques cancelados sem fazer alterações.

**Uso:**
```bash
python verificar_embarques_cancelados.py
```

**O que faz:**
- ✅ Lista todos os embarques com status "CANCELADO"
- ✅ Mostra quais NFs seriam removidas
- ✅ Mostra quais pedidos seriam resetados
- ✅ Exibe resumo completo das ações que seriam executadas
- ❌ **NÃO faz alterações no banco de dados**

**Recomendação:** Execute este script PRIMEIRO para verificar o que será alterado.

### 2. `limpar_embarques_cancelados.py` (CUIDADO - Faz alterações)

**Função:** Executa a limpeza efetiva dos embarques cancelados.

**Uso:**
```bash
python limpar_embarques_cancelados.py
```

**O que faz:**
- 🗑️ Remove NFs de todos os itens de embarques cancelados
- 🔄 Reseta pedidos para status "Aberto" (remove cotacao_id e transportadora)
- 💾 Salva alterações no banco de dados
- 📝 Gera log da operação em `log_limpeza_embarques.txt`

**Segurança:**
- ⚠️ Solicita confirmação dupla antes de executar
- ⚠️ Mostra resumo antes de salvar
- ⚠️ Permite cancelar a operação a qualquer momento
- 🔄 Faz rollback em caso de erro

## 🚀 Como Usar (Passo a Passo)

### Passo 1: Verificação (Recomendado)
```bash
# Execute primeiro para ver o que será alterado
python verificar_embarques_cancelados.py
```

### Passo 2: Limpeza (Se necessário)
```bash
# Execute apenas se a verificação mostrar problemas
python limpar_embarques_cancelados.py
```

### Passo 3: Confirmações
O script de limpeza pedirá duas confirmações:
1. **Primeira:** Digite `SIM` para iniciar o processo
2. **Segunda:** Digite `CONFIRMAR` para salvar as alterações

## 📊 Exemplo de Saída

### Verificação:
```
🔍 VERIFICAÇÃO DE EMBARQUES CANCELADOS
============================================================
Executado em: 15/01/2025 14:30:25
ℹ️  Este script apenas CONSULTA dados, não faz alterações.

📋 Encontrados 3 embarques cancelados:

🚛 1. Embarque #123
   📅 Criado em: 10/01/2025 09:15
   🚚 Transportadora: TRANSPORTADORA XYZ LTDA
   📍 Tipo: FRACIONADA
   🏷️  Status: CANCELADO
   📦 5 itens:
      • Item 456: CLIENTE ABC - ✅ COM NF
        📄 NF: 12345 (SERÁ REMOVIDA)
        📋 Lote: LOTE_789_20250110

📊 RESUMO GERAL:
   • Total de embarques cancelados: 3
   • Total de itens: 15
   • Total de NFs que seriam removidas: 8
   • Total de pedidos que seriam resetados: 12
```

### Limpeza:
```
🔧 SCRIPT DE LIMPEZA DE EMBARQUES CANCELADOS
============================================================
Iniciado em: 15/01/2025 14:35:10

⚠️  ATENÇÃO: Este script irá:
   - Remover NFs de todos os itens de embarques CANCELADOS
   - Voltar pedidos desses embarques para status 'Aberto'
   - Esta operação NÃO pode ser desfeita!

Deseja continuar? (digite 'SIM' para confirmar): SIM

🔍 Buscando embarques cancelados...
📋 Encontrados 3 embarques cancelados:

🚛 Processando Embarque #123 - TRANSPORTADORA XYZ LTDA
   📦 5 itens encontrados
   🗑️  Removendo NF 12345 do item 456
   ✅ 3 NFs removidas dos itens
   🔄 Resetando pedidos de 2 lotes de separação...
     📋 Pedido 789 resetado para 'Aberto'

📊 RESUMO DA OPERAÇÃO:
   • Embarques cancelados processados: 3
   • Itens processados: 15
   • NFs removidas: 8
   • Pedidos resetados para 'Aberto': 12

💾 Confirma a gravação das alterações no banco? (digite 'CONFIRMAR'): CONFIRMAR
✅ Alterações salvas com sucesso no banco de dados!
📝 Log da operação salvo em 'log_limpeza_embarques.txt'
```

## ⚠️ Avisos Importantes

1. **Backup:** Faça backup do banco antes de executar o script de limpeza
2. **Teste:** Execute primeiro o script de verificação
3. **Uso Único:** Estes scripts são para correção pontual, não para uso rotineiro
4. **Log:** Todas as operações são registradas em `log_limpeza_embarques.txt`

## 🔒 Segurança

- Scripts solicitam confirmação dupla
- Operações são transacionais (rollback em caso de erro)
- Log detalhado de todas as alterações
- Script de verificação não altera dados

## 📞 Suporte

Em caso de dúvidas ou problemas:
1. Execute primeiro o script de verificação
2. Verifique os logs gerados
3. Faça backup antes de executar a limpeza 