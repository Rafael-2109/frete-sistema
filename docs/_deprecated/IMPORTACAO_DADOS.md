# Guia de Importação de Dados

Este documento descreve como usar os scripts de importação de dados para o sistema de frete.

## 1. Importação de Clientes (XML)

### Descrição
Importa clientes de um arquivo XML para a tabela `CadastroCliente`.

### Uso
```bash
# No ambiente local
python scripts/importar_clientes_xml.py

# No Render
python scripts/importar_clientes_xml.py
```

### Formato do XML esperado
```xml
<clientes>
  <cliente>
    <razao_social>EMPRESA LTDA</razao_social>
    <nome_fantasia>EMPRESA</nome_fantasia>
    <cnpj>00.000.000/0001-00</cnpj>
    <enderecos>
      <endereco>
        <principal>1</principal>
        <logradouro>RUA EXEMPLO</logradouro>
        <numero>123</numero>
        <complemento>SALA 1</complemento>
        <bairro>CENTRO</bairro>
        <cidade>SAO PAULO</cidade>
        <sigla_estado>SP</sigla_estado>
        <cep>00000-000</cep>
      </endereco>
    </enderecos>
  </cliente>
</clientes>
```

### Campos mapeados
- `cnpj` → `cnpj_cpf` (limpo, apenas números)
- `razao_social` → `raz_social`
- `nome_fantasia` → `raz_social_red`
- `sigla_estado` → `estado`
- `cidade` → `municipio`
- Endereço principal → Campos de endereço de entrega

## 2. Importação de Faturamento TagPlus (Excel)

### Descrição
Importa faturamento de um arquivo Excel exportado do TagPlus, processando:
- Criação de registros em `FaturamentoProduto` e `RelatorioFaturamentoImportado`
- Atualização de embarques
- Criação de movimentações de estoque
- Baixa na `CarteiraCopia` e atualização da `CarteiraPrincipal`

### Uso
```bash
# No ambiente local
python scripts/importar_faturamento_tagplus.py caminho/para/arquivo.xlsx

# No Render
python scripts/importar_faturamento_tagplus.py /tmp/faturamento_tagplus.xlsx
```

### Formato do Excel TagPlus

O arquivo Excel deve conter linhas no seguinte formato:

1. **Linha de cabeçalho da NF:**
   ```
   NF-e - 3548 - PAO PAO E ARROZ LTDA EPP
   ```
   - Caracteres 8-11: Número da NF (3548)
   - A partir do caractere 15: Razão social do cliente

2. **Linhas de itens da NF:**
   - Coluna A: Código do produto entre aspas simples ('4320162')
   - Coluna D: Data do faturamento (01/07/2025 às 16:32:39)
   - Coluna E: Quantidade faturada (5,000)
   - Coluna F: Valor total do item (1.001,40)

3. **Linha de finalização:**
   ```
   Total de Custo Utilizado: 0,35
   ```

### Processamento realizado

O script usa o **ProcessadorFaturamentoTagPlus** que implementa TODAS as funcionalidades do sistema:

1. **Criação dos registros básicos:**
   - Busca o CNPJ pela razão social em `CadastroCliente`
   - Cria registros em `FaturamentoProduto` para cada item
   - Marca com `created_by='ImportTagPlus'` para identificação

2. **Processamento completo via ProcessadorFaturamentoTagPlus:**
   - **Score de vinculação**: Encontra separações usando CNPJ + Produto + Qtd
   - **Movimentações de estoque**: Cria registros de saída automática
   - **Atualização de embarques**: Vincula NF aos EmbarqueItems correspondentes
   - **Baixa na carteira**: Atualiza `CarteiraCopia` e `CarteiraPrincipal`
   - **Consolidação**: Cria registro em `RelatorioFaturamentoImportado`

3. **Sincronizações integradas (igual ao Odoo):**
   - **Entregas monitoradas**: Sincroniza com módulo de monitoramento
   - **Re-validação de embarques**: Processa embarques pendentes
   - **NFs de embarques**: Sincroniza NFs pendentes
   - **Lançamento de fretes**: Processa fretes automaticamente

### Vantagens do ProcessadorFaturamentoTagPlus

- **Consistência**: Usa exatamente a mesma lógica do sistema principal
- **Score inteligente**: Vincula NFs mesmo sem número de pedido
- **Processamento completo**: Todas as sincronizações em uma única chamada
- **Compatibilidade**: Funciona com todas as funcionalidades existentes

## 3. Filtro Dinâmico de Clientes

A tela de cadastro de clientes (`/carteira/cadastro-cliente`) já possui um filtro dinâmico implementado:

### Funcionalidades
- Campo de busca que filtra em tempo real
- Busca por CNPJ, razão social ou cidade
- Atualização automática da lista conforme digita
- Delay de 300ms para otimizar performance

### Como usar
1. Digite no campo "Buscar por CNPJ, nome ou cidade..."
2. A lista será filtrada automaticamente
3. Clique em um cliente para editá-lo

## Observações Importantes

### Segurança
- Os scripts validam todos os dados antes de inserir no banco
- CNPJ/CPF são limpos (apenas números) antes de salvar
- Transações são revertidas em caso de erro

### Performance
- Importação em lote com commits otimizados
- Mensagens de progresso durante o processamento
- Relatório completo ao final da importação

### Tratamento de Erros
- Clientes/NFs duplicados são identificados e pulados
- Produtos não encontrados geram avisos mas não impedem importação
- Erros são logados com detalhes para debug

### Manutenção
- Scripts podem ser executados múltiplas vezes com segurança
- Registros existentes são atualizados, não duplicados
- Logs detalhados facilitam auditoria

## Exemplos de Uso

### Importar clientes e depois faturamento
```bash
# 1. Importar base de clientes
python scripts/importar_clientes_xml.py

# 2. Importar faturamento do mês
python scripts/importar_faturamento_tagplus.py ~/Downloads/faturamento_julho_2025.xlsx
```

### Verificar importação
```sql
-- Verificar clientes importados
SELECT COUNT(*) FROM cadastro_cliente;

-- Verificar faturamento importado
SELECT COUNT(*) FROM faturamento_produto WHERE origem = 'IMPORTACAO_TAGPLUS';

-- Verificar baixas na carteira
SELECT num_pedido, cod_produto, baixa_produto_pedido 
FROM carteira_copia 
WHERE baixa_produto_pedido > 0;
```