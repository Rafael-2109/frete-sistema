# 🎯 ROTEIRO DE TESTES CFOP - INÍCIO

## OBJETIVO
Descobrir como preencher o campo CFOP ao criar pedidos via API no Odoo

## ⚠️ PREMISSAS DE SEGURANÇA
- ✅ Testes apenas em pedido isolado criado para este fim
- ✅ Um método por vez
- ✅ Documentação completa de cada resultado
- ✅ Pedido teste será deletado após conclusão

## 📋 CHECKLIST DE EXECUÇÃO

### [ ] FASE 1: Criar Pedido Teste
1. Abra o arquivo: `roteiro_testes_cfop_seguro.py`
2. Copie o código da **FASE 1**
3. Ajuste as configurações (URL, DB, usuário, senha)
4. Execute o script
5. **ANOTE OS IDs:**
   - Pedido ID: _________
   - Linha ID: _________

### [ ] FASE 2: Descobrir Métodos
1. No Odoo, vá em **Settings → Technical → Server Actions**
2. Crie nova Server Action:
   - Name: "Descoberta CFOP - Segura"
   - Model: `sale.order.line`
   - Action Type: Execute Python Code
3. Cole o código da **FASE 2** do arquivo `roteiro_testes_cfop_seguro.py`
4. Execute na linha do pedido teste
5. **COPIE O RESULTADO** (lista de métodos)

### [ ] FASE 3: Testar Métodos
**ATENÇÃO**: Teste apenas métodos que parecem seguros!

Métodos prioritários para testar:
- `_compute_tax_id` (se existir)
- `_onchange_product_id` (se existir)
- Métodos com "fiscal" ou "cfop" no nome

Para cada método:
1. Documente estado ANTES (CFOP vazio?)
2. Execute o método via Server Action
3. Documente estado DEPOIS (CFOP preenchido?)
4. Registre resultado

### [ ] FASE 4: Limpar Ambiente
1. Execute script de limpeza
2. Confirme exclusão do pedido teste

## 📊 TABELA DE RESULTADOS

| Método Testado | CFOP Antes | CFOP Depois | Funcionou? | Observações |
|----------------|------------|-------------|------------|-------------|
| _____________  | VAZIO      | _________   | SIM/NÃO    | ___________ |
| _____________  | VAZIO      | _________   | SIM/NÃO    | ___________ |
| _____________  | VAZIO      | _________   | SIM/NÃO    | ___________ |

## ✅ CRITÉRIO DE SUCESSO
- Encontrar método que preenche CFOP
- Sem efeitos colaterais
- Reproduzível
- Performance < 5 segundos

## 🚨 MÉTODOS PERIGOSOS (NUNCA EXECUTAR)
- ❌ unlink
- ❌ delete
- ❌ cancel
- ❌ purge
- ❌ cleanup
- ❌ reset
- ❌ clear
- ❌ remove

## 📝 PRÓXIMO PASSO
Após identificar o método que funciona, criaremos a solução final automatizada.