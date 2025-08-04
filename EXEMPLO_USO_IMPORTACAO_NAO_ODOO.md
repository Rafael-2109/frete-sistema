# Sistema de Importação de Pedidos Não-Odoo

## Visão Geral

Este sistema permite importar pedidos que não vêm do Odoo para a CarteiraCopia, utilizando um cadastro de clientes próprio para complementar as informações.

## Componentes Criados

### 1. Modelo CadastroCliente (`app/carteira/models.py`)
- Tabela para cadastrar clientes não-Odoo
- Campos principais: CNPJ, razão social, município, vendedor, equipe
- Campos de endereço de entrega
- Métodos para limpar e formatar CNPJ

### 2. API de Cadastro de Clientes (`app/carteira/routes/cadastro_cliente_api.py`)

**Endpoints disponíveis:**

- `GET /api/cadastro-cliente` - Lista clientes cadastrados
- `GET /api/cadastro-cliente/<id>` - Obtém cliente por ID
- `GET /api/cadastro-cliente/cnpj/<cnpj>` - Busca cliente por CNPJ
- `POST /api/cadastro-cliente` - Cria novo cliente
- `PUT /api/cadastro-cliente/<id>` - Atualiza cliente
- `DELETE /api/cadastro-cliente/<id>` - Inativa cliente
- `GET /api/cadastro-cliente/opcoes` - Lista opções para campos select
- `GET /api/cadastro-cliente/cidades/<uf>` - Lista cidades por UF

### 3. Serviço de Importação (`app/carteira/services/importacao_nao_odoo.py`)
- Lê arquivos Excel com pedidos
- Suporta múltiplas versões de nomes de campos
- Busca dados do cliente cadastrado
- Cria registros na CarteiraCopia

### 4. API de Importação (`app/carteira/routes/importacao_nao_odoo_api.py`)

**Endpoints disponíveis:**

- `POST /api/importacao-nao-odoo/upload` - Upload e importação de arquivo
- `POST /api/importacao-nao-odoo/validar` - Validação prévia do arquivo
- `GET /api/importacao-nao-odoo/template` - Informações sobre o template

## Formato do Arquivo Excel

### Campos do Cabeçalho (formato chave-valor)
```
| A                                  | B              |
|------------------------------------|----------------|
| NUMERO DO PEDIDO DO REPRESENTANTE  | PED-001        |
| CNPJ*                              | 12345678901234 |
| NUMERO DO PEDIDO DO CLIENTE        | CLI-123        |
| Data Entrega                       | 15/08/2024     |
```

### Tabela de Produtos
```
| CÓDIGO | Qtde Solicitada | Valor Negociado |
|--------|-----------------|-----------------|
| P001   | 100            | 25.50           |
| P002   | 50             | 30.00           |
```

## Fluxo de Uso

### 1. Cadastrar Cliente (se ainda não existir)

```javascript
// Exemplo de requisição para criar cliente
POST /api/cadastro-cliente
{
    "cnpj_cpf": "12345678901234",
    "raz_social": "Empresa Exemplo LTDA",
    "raz_social_red": "Empresa Exemplo",
    "municipio": "São Paulo",
    "estado": "SP",
    "vendedor": "João Silva",
    "equipe_vendas": "Equipe A",
    "aplicar_endereco_cliente": true
}
```

### 2. Importar Pedido

```javascript
// Upload de arquivo Excel
POST /api/importacao-nao-odoo/upload
Content-Type: multipart/form-data
file: arquivo.xlsx
```

### 3. Resposta da Importação

```json
{
    "success": true,
    "mensagem": "Importação concluída com sucesso!",
    "pedidos_importados": 2,
    "detalhes": [
        {
            "num_pedido": "PED-001",
            "cod_produto": "P001",
            "quantidade": 100,
            "valor": 25.50
        },
        {
            "num_pedido": "PED-001",
            "cod_produto": "P002",
            "quantidade": 50,
            "valor": 30.00
        }
    ],
    "avisos": []
}
```

## Validações Implementadas

1. **CNPJ**: Limpa e formata automaticamente
2. **Cliente**: Deve estar cadastrado antes da importação
3. **Campos obrigatórios**: Número do pedido e CNPJ
4. **Produtos**: Código e quantidade devem ser válidos
5. **Duplicatas**: Não permite importar pedido/produto já existente

## Próximos Passos

Para completar o sistema, ainda faltam:

1. **Interface Web de Cadastro de Clientes**
   - Formulário HTML para cadastrar/editar clientes
   - Lista de clientes cadastrados
   - Integração com API

2. **Interface Web de Importação**
   - Upload de arquivo Excel
   - Preview antes de importar
   - Feedback de erros e sucessos

## Exemplo de Interface HTML (sugestão)

```html
<!-- Cadastro de Cliente -->
<form id="formCadastroCliente">
    <h3>Cadastro de Cliente Não-Odoo</h3>
    
    <div class="form-group">
        <label>CNPJ/CPF*</label>
        <input type="text" name="cnpj_cpf" required>
    </div>
    
    <div class="form-group">
        <label>Razão Social*</label>
        <input type="text" name="raz_social" required>
    </div>
    
    <div class="form-group">
        <label>Nome Fantasia</label>
        <input type="text" name="raz_social_red">
    </div>
    
    <div class="form-group">
        <label>Estado*</label>
        <select name="estado" required>
            <!-- Carregar de /api/cadastro-cliente/opcoes -->
        </select>
    </div>
    
    <div class="form-group">
        <label>Município*</label>
        <select name="municipio" required>
            <!-- Carregar de /api/cadastro-cliente/cidades/{uf} -->
        </select>
    </div>
    
    <button type="submit">Salvar Cliente</button>
</form>

<!-- Importação de Pedidos -->
<form id="formImportacao">
    <h3>Importar Pedidos Não-Odoo</h3>
    
    <div class="form-group">
        <label>Arquivo Excel</label>
        <input type="file" name="file" accept=".xlsx,.xls" required>
    </div>
    
    <button type="button" onclick="validarArquivo()">Validar</button>
    <button type="submit">Importar</button>
</form>
```

## Observações Importantes

1. O CNPJ é a chave principal para vincular pedido ao cliente
2. O cliente deve ser cadastrado ANTES de importar pedidos
3. O sistema padroniza automaticamente o CNPJ (remove formatação para busca, aplica máscara para exibição)
4. Todos os campos de endereço de entrega são opcionais
5. O sistema busca vendedores e equipes existentes no RelatorioFaturamentoImportado

## Tabela Criada no Banco

```sql
CREATE TABLE cadastro_cliente (
    id SERIAL PRIMARY KEY,
    cnpj_cpf VARCHAR(20) NOT NULL UNIQUE,
    raz_social VARCHAR(255) NOT NULL,
    raz_social_red VARCHAR(100),
    municipio VARCHAR(100) NOT NULL,
    estado VARCHAR(2) NOT NULL,
    vendedor VARCHAR(100),
    equipe_vendas VARCHAR(100),
    -- campos de endereço de entrega...
    cliente_ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW()
);
```