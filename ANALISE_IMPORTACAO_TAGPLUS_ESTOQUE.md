# Análise da Importação do Faturamento TagPlus - Movimentações de Estoque

## Visão Geral do Processo

A importação do faturamento TagPlus via Excel segue um fluxo específico com múltiplas etapas de processamento. A questão das movimentações de estoque está diretamente ligada ao parâmetro `processar_completo`.

## Fluxo de Importação

### 1. Upload do Arquivo Excel
- **Rota**: `/integracoes/tagplus/api/importar-excel`
- **Arquivo**: `app/integracoes/tagplus/routes.py:547-608`
- O arquivo é recebido, validado e salvo temporariamente

### 2. Processamento do Excel
- **Função**: `processar_arquivo_tagplus_web()`
- **Arquivo**: `app/integracoes/tagplus/servico_importacao_excel.py:64-308`
- Lê o arquivo Excel linha por linha
- Extrai informações de NFs e produtos
- Cria registros em `FaturamentoProduto` com `created_by='ImportTagPlus'`

### 3. Processamento Completo (Opcional)
- **Controlado por**: parâmetro `processar_completo` (linha 590 em routes.py)
- **Default**: Depende do checkbox na interface web
- Se `processar_completo=True`, executa `ProcessadorFaturamentoTagPlus`

## Critérios para Movimentação de Estoque

### Condição Principal
```python
# servico_importacao_excel.py:262-266
if processar_completo and todos_faturamento_produtos:
    processador = ProcessadorFaturamentoTagPlus()
    resultado_processamento = processador.processar_lote_completo(todos_faturamento_produtos)
```

**A movimentação de estoque SÓ ocorre quando `processar_completo=True`**

### Processo de Criação da Movimentação

1. **Busca de Separação por Score**
   - Função: `_encontrar_separacao_por_score()`
   - Critérios de busca:
     - CNPJ do cliente coincide
     - EmbarqueItem sem NF (`numero_nf IS NULL`)
     - Embarque e Item ativos
     - Item com `erro_validacao` preenchido
   - Sistema de pontuação:
     - Produto igual: +50 pontos
     - Quantidade exata: +40 pontos
     - Quantidade com tolerância 10%: +30 pontos
     - Quantidade com tolerância 20%: +20 pontos
     - Embarque recente (≤7 dias): +10 pontos

2. **Criação da Movimentação**
   - Função: `_criar_movimentacao_estoque()`
   - Verifica se já existe movimentação para evitar duplicação
   - Cria registro em `MovimentacaoEstoque`:
     ```python
     tipo_movimentacao = 'FATURAMENTO TAGPLUS'
     local_movimentacao = 'VENDA'
     qtd_movimentacao = -abs(qtd_faturada)  # Negativo para saída
     observacao = "Baixa automática NF X - Lote Y" ou "Sem Separação"
     criado_por = 'Sistema'
     ```

### Outros Processamentos do Modo Completo

1. **Atualização de EmbarqueItem**
   - Preenche campo `numero_nf` quando encontra match

2. **Baixa na Carteira**
   - Atualiza `baixa_produto_pedido` em `CarteiraCopia`
   - Recalcula saldo
   - Sincroniza com `CarteiraPrincipal`

3. **Consolidação em RelatorioFaturamentoImportado**
   - Cria registro consolidado da NF

4. **Sincronizações Adicionais** (processar_nf_completo):
   - Sincronizar entrega monitorada
   - Re-validar embarques pendentes
   - Sincronizar NFs pendentes em embarques
   - Lançamento automático de fretes

## Diagnóstico do Problema

### Possíveis Causas para Não Processar Movimentações

1. **`processar_completo=False`**
   - Verificar se o checkbox está marcado na interface
   - O parâmetro vem do formulário: `request.form.get('processar_completo') == 'true'`

2. **Lista `todos_faturamento_produtos` vazia**
   - Erro na criação dos registros FaturamentoProduto
   - Verificar logs de erro durante o processamento

3. **Erro no ProcessadorFaturamentoTagPlus**
   - Exceção capturada mas processamento continua
   - Verificar logs para mensagens de erro

4. **Critérios não atendidos para score**
   - Nenhum EmbarqueItem candidato encontrado
   - Score insuficiente (precisa ser > 0)

### Como Verificar

1. **Logs do Sistema**
   ```bash
   # Buscar por mensagens específicas
   grep "Processando NF TagPlus" app.log
   grep "Movimentação criada:" app.log
   grep "Nenhum EmbarqueItem ativo" app.log
   ```

2. **Verificar no Banco de Dados**
   ```sql
   -- NFs importadas do TagPlus
   SELECT * FROM faturamento_produto 
   WHERE created_by = 'ImportTagPlus'
   ORDER BY created_at DESC;

   -- Movimentações criadas
   SELECT * FROM movimentacao_estoque 
   WHERE tipo_movimentacao = 'FATURAMENTO TAGPLUS'
   ORDER BY created_at DESC;

   -- EmbarqueItems candidatos
   SELECT ei.*, cc.cnpj_cpf 
   FROM embarque_item ei
   JOIN embarque e ON ei.embarque_id = e.id
   JOIN carteira_copia cc ON ei.num_pedido = cc.num_pedido 
     AND ei.cod_produto = cc.cod_produto
   WHERE ei.numero_nf IS NULL
     AND e.status = 'ativo'
     AND ei.status = 'ativo'
     AND ei.erro_validacao IS NOT NULL;
   ```

## Solução Recomendada

1. **Garantir `processar_completo=True`**
   - Marcar checkbox na interface
   - Ou chamar diretamente o processador após importação

2. **Reprocessar NFs já importadas**
   ```python
   # Script para reprocessar
   from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus
   
   processador = ProcessadorFaturamentoTagPlus()
   resultado = processador.processar_lote_nfs()
   ```

3. **Monitorar logs durante importação**
   - Ativar nível DEBUG para o módulo
   - Verificar cada etapa do processamento

4. **Validar critérios de match**
   - Verificar se existem EmbarqueItems candidatos
   - Confirmar CNPJ e produtos coincidem
   - Verificar campo `erro_validacao` preenchido