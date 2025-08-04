# 📋 Resumo da Integração TagPlus

## 🔗 URLs de Acesso

### Interface Web
- **Importação Manual**: `/integracoes/tagplus/importacao`

### Webhooks (Recebimento Automático)
- **Clientes**: `/webhook/tagplus/cliente`
- **Notas Fiscais**: `/webhook/tagplus/nfe`
- **Teste**: `/webhook/tagplus/teste`

### APIs de Importação
- **Testar Conexão**: `POST /api/tagplus/testar-conexao`
- **Importar Clientes**: `POST /api/tagplus/importar-clientes`
- **Importar NFs**: `POST /api/tagplus/importar-nfs`

---

## 👥 IMPORTAÇÃO DE CLIENTES

### Campos Mapeados (TagPlus → CadastroCliente)

| TagPlus | Sistema | Observação |
|---------|---------|------------|
| `cnpj` ou `cpf` | `cnpj_cpf` | Remove formatação |
| `razao_social` ou `nome` | `raz_social` | Nome da empresa |
| `nome_fantasia` | `raz_social_red` | Máx 50 caracteres |
| `cep` | `cep_endereco_ent` | CEP |
| `logradouro` | `rua_endereco_ent` | Rua |
| `logradouro + numero` | `endereco_ent` | Endereço completo |
| `bairro` | `bairro_endereco_ent` | Bairro |
| `cidade` | `nome_cidade`, `municipio` | Cidade |
| `uf` | `estado`, `cod_uf` | Estado |
| `telefone` | `telefone_endereco_ent` | Telefone |
| `email` | `email` | Email |

### Campos Preenchidos Automaticamente
- `vendedor`: "A DEFINIR"
- `equipe_vendas`: "GERAL"
- `cliente_ativo`: True
- `created_by`: "ImportTagPlus" ou "WebhookTagPlus"

### Comportamento
- **Cliente Novo**: Cria registro completo
- **Cliente Existente**: Atualiza apenas campos vazios
- **Identificação**: Por CNPJ/CPF (sem formatação)

---

## 📄 IMPORTAÇÃO DE NOTAS FISCAIS

### Limite e Ordenação
- **Máximo**: 500 NFs por importação
- **Ordem**: Mais recentes primeiro (DESC)
- **Status**: Apenas NFs autorizadas

### Campos Mapeados (TagPlus → FaturamentoProduto)

| TagPlus | Sistema | Observação |
|---------|---------|------------|
| `numero` | `numero_nf` | Número da NF |
| `data_emissao` | `data_fatura` | Data de emissão |
| `cliente.cnpj` | `cnpj_cliente` | CNPJ do cliente |
| - | `nome_cliente` | Busca do CadastroCliente |
| - | `municipio` | Busca do CadastroCliente |
| - | `estado` | Busca do CadastroCliente |
| - | `vendedor` | Busca do CadastroCliente |
| - | `equipe_vendas` | Busca do CadastroCliente |

### Campos por Item da NF

| TagPlus | Sistema | Observação |
|---------|---------|------------|
| `codigo` | `cod_produto` | Código do produto |
| `descricao` | `nome_produto` | Descrição |
| `quantidade` | `qtd_produto_faturado` | Quantidade |
| `valor_unitario` | `preco_produto_faturado` | Preço unitário |
| `valor_total` | `valor_produto_faturado` | Valor total |
| `peso_unitario` | `peso_unitario_produto` | Peso unitário |
| - | `peso_total` | Calculado: qtd × peso_unit |
| - | `origem` | Vazio (não tem pedido) |
| - | `status_nf` | "Lançado" |

---

## 🔄 PROCESSAMENTO APÓS IMPORTAÇÃO

### Processamento Automático via Webhook
Quando uma NF é recebida via webhook, o sistema automaticamente:
1. Cria os registros em `FaturamentoProduto`
2. **Executa o processamento completo** (score, movimentação, vinculação)
3. Registra logs de sucesso ou inconsistências

### 1. Busca de Separação (Score)

**Critérios de Busca (EmbarqueItem):**
- `Embarque.status = 'ativo'`
- `EmbarqueItem.status = 'ativo'`
- `EmbarqueItem.erro_validacao != NULL`
- `EmbarqueItem.numero_nf = NULL`
- CNPJ do cliente coincide

**Cálculo de Score:**
- Produto igual: +50 pontos
- Quantidade exata: +40 pontos
- Quantidade próxima (±10%): +30 pontos
- Quantidade próxima (±20%): +20 pontos
- Data recente (≤7 dias): +10 pontos
- **Score mínimo**: >0 pontos (qualquer score positivo)

### 2. Movimentação de Estoque

**Tabela**: `MovimentacaoEstoque` + `ItemMovimentacaoEstoque`

**Campos Preenchidos:**
- `tipo_movimento`: "SAIDA"
- `origem`: "FATURAMENTO TAGPLUS"
- `referencia`: "NF {numero} - Lote {id}" ou "NF {numero} - Sem Separação"
- `observacoes`: "Faturamento TagPlus - NF {numero}"
- `usuario_responsavel`: "Sistema"

### 3. Atualização EmbarqueItem

**Se encontrou separação com score > 0:**
- `EmbarqueItem.numero_nf` = Número da NF

### 4. Baixa na Carteira

**Se EmbarqueItem tem num_pedido:**
- `CarteiraCopia.baixa_produto_pedido` += quantidade faturada
- `CarteiraCopia.qtd_saldo_produto_calculado` = recalculado
- `CarteiraPrincipal.qtd_saldo_produto_pedido` = sincronizado com CarteiraCopia

### 5. Consolidação

**Tabela**: `RelatorioFaturamentoImportado`

**Campos Consolidados por NF:**
- `numero_nf`: Número da NF
- `data_fatura`: Data de emissão
- `cnpj_cliente`, `nome_cliente`: Dados do cliente
- `valor_total`: Soma dos valores dos itens
- `peso_bruto`: Soma dos pesos dos itens
- `municipio`, `estado`: Do cliente
- `origem`: número do pedido (se encontrado) ou "TagPlus"
- `vendedor`, `equipe_vendas`: Do cliente

---

## 🔄 SUBSTITUIÇÃO DE PEDIDOS (Importação Não-Odoo)

### Quando Pode Substituir
- Mesmo número de pedido sendo reimportado
- **NÃO** tem `SeparacaoLote` com `pedido = 'COTADO'`

### O que Acontece
1. Remove todos os itens do pedido de `CarteiraCopia`
2. Remove todos os itens do pedido de `CarteiraPrincipal`
3. Importa novos itens do arquivo

---

## 🧪 TESTE LOCAL

### Configuração
```bash
# Variáveis de ambiente
export TAGPLUS_TEST_MODE=local
export TAGPLUS_TEST_URL=http://localhost:8080/api/v1

# Executar teste
python teste_tagplus_local.py --importar  # Testa importação
python teste_tagplus_local.py --webhook   # Testa webhooks
```

### Credenciais Padrão
- **Usuário**: rayssa
- **Senha**: A12345

---

## 📊 FLUXO RESUMIDO

1. **Cliente TagPlus** → **CadastroCliente** (cria/atualiza)
2. **NF TagPlus** → **FaturamentoProduto** (cada item)
3. **Score CNPJ+Produto+Qtd** → Encontra **EmbarqueItem**
4. **Cria MovimentacaoEstoque** (com ou sem lote)
5. **Atualiza EmbarqueItem** com NF (se encontrou)
6. **Atualiza baixa_produto_pedido** (se tem pedido)
7. **Consolida em RelatorioFaturamentoImportado** (por NF)

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

- TagPlus não envia número do pedido nas NFs
- Sistema usa score para vincular NF com separações
- Apenas EmbarqueItems ativos com erro_validacao são considerados
- Clientes são criados automaticamente se não existirem
- Importação limitada a 500 NFs por vez (mais recentes primeiro)
- **Webhooks executam processamento completo automaticamente**
- Para NFs sem vinculação automática, usar interface manual em `/tagplus/vincular-nfs`