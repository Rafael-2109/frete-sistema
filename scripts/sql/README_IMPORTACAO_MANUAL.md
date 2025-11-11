# Importação Manual de Pedido ou NF do Odoo

## 📋 Visão Geral

Este documento explica como importar manualmente um pedido ou nota fiscal específica do Odoo para o sistema de fretes.

## 🚀 Script Python (Ambiente Local)

### Instalação
```bash
cd /caminho/para/frete_sistema
```

### Uso - Importar Pedido

```bash
# Importar um pedido específico
python scripts/importar_pedido_nf_especifico.py --pedido VSC01234

# Importar múltiplos pedidos
python scripts/importar_pedido_nf_especifico.py --pedido VSC01234 VSC01235 VSC01236

# Modo verboso (mais detalhes)
python scripts/importar_pedido_nf_especifico.py --pedido VSC01234 --verbose
```

### Uso - Importar NF

```bash
# Importar uma NF específica
python scripts/importar_pedido_nf_especifico.py --nf 12345

# Importar múltiplas NFs
python scripts/importar_pedido_nf_especifico.py --nf 12345 12346 12347

# Modo verboso
python scripts/importar_pedido_nf_especifico.py --nf 12345 --verbose
```

## 🔧 Como Funciona

### Para Pedidos:
1. Verifica se pedido já existe na carteira
2. Busca pedido no Odoo usando `CarteiraService.obter_carteira_pendente(pedidos_especificos=[numero])`
3. Sincroniza usando `sincronizar_carteira_odoo_com_gestao_quantidades()`
4. Atualiza saldos e cria/atualiza registros na `carteira_principal`

### Para NF:
1. Verifica se NF já existe no sistema
2. Busca NF no Odoo usando `FaturamentoService.sincronizar_faturamento_incremental()`
3. Processa NF usando `ProcessadorFaturamento.processar_nfs_importadas(nfs_especificas=[numero])`
4. Cria movimentações de estoque
5. Atualiza EmbarqueItems se houver
6. Marca separações como faturadas

## ⚙️ Funções Utilizadas

### CarteiraSer vice (app/odoo/services/carteira_service.py)
- `obter_carteira_pendente(pedidos_especificos=[...])` - Busca pedidos específicos no Odoo
- `sincronizar_carteira_odoo_com_gestao_quantidades()` - Sincroniza dados com gestão de quantidades

### FaturamentoService (app/odoo/services/faturamento_service.py)
- `sincronizar_faturamento_incremental()` - Busca NFs do Odoo

### ProcessadorFaturamento (app/faturamento/services/processar_faturamento.py)
- `processar_nfs_importadas(nfs_especificas=[...])` - Processa NFs específicas

## 📊 Saída do Script

### Pedido:
```
================================================================================
✅ PEDIDO IMPORTADO COM SUCESSO!
================================================================================
📋 Pedido: VSC01234
📊 Total de linhas: 5
🆕 Novos: 0
🔄 Atualizados: 5
❌ Cancelados: 0

Pedido VSC01234 importado com sucesso!
================================================================================
```

### NF:
```
================================================================================
✅ NF IMPORTADA COM SUCESSO!
================================================================================
📄 NF: 12345
✅ Processadas: 1
📦 Movimentações criadas: 3
🚚 EmbarqueItems atualizados: 1

NF 12345 importada e processada com sucesso!
================================================================================
```

## 🔍 Troubleshooting

### "Pedido não encontrado no Odoo"
- Verifique se o número do pedido está correto (ex: VSC01234, não 01234)
- Confirme se o pedido está ativo no Odoo
- Verifique se é um pedido de Venda ou Bonificação

### "NF não encontrada no Odoo"
- Verifique se o número da NF está correto
- Confirme se a NF está no status 'Lançado' no Odoo
- Verifique se a NF foi criada nos últimos 30 dias (ajuste `minutos_status` se necessário)

### Erro de conexão Odoo
- Verifique as variáveis de ambiente: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD
- Teste a conexão com o Odoo

### Erro de banco de dados
- Verifique se o banco PostgreSQL está acessível
- Confirme as variáveis: DATABASE_URL ou DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

## ⚠️ Avisos Importantes

1. **Pedidos Existentes**: Se o pedido já existir, o script irá ATUALIZAR os dados
2. **NFs Existentes**: Se a NF já existir, o script irá REPROCESSAR
3. **Commits Automáticos**: O script faz commits automáticos após cada importação
4. **Rollback em Erro**: Em caso de erro, faz rollback automático

## 🔐 Permissões Necessárias

- Acesso ao Odoo (credenciais configuradas)
- Acesso ao banco de dados (leitura e escrita)
- Permissões para executar scripts Python no ambiente

## 📝 Logs

O script gera logs detalhados:
- **INFO**: Informações gerais do processo
- **WARNING**: Avisos (pedido já existe, etc)
- **ERROR**: Erros durante a execução
- **DEBUG**: Detalhes técnicos (apenas com --verbose)

Use `--verbose` para ver todos os detalhes das queries e processamento.
