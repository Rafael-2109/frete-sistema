# Análise da Função aplicar_reducao_quantidade

## 1. Campos Utilizados - Análise de Correção

### ✅ Campos CORRETOS utilizados na função:

#### CarteiraPrincipal:
- `num_pedido` - ✅ Correto
- `cod_produto` - ✅ Correto
- `separacao_lote_id` - ✅ Correto (verifica se é None para saldo livre)
- `qtd_saldo_produto_pedido` - ✅ Correto (quantidade saldo do produto)

#### PreSeparacaoItem:
- `num_pedido` - ✅ Correto
- `cod_produto` - ✅ Correto
- `status` - ✅ Correto (filtra 'CRIADO', 'RECOMPOSTO')
- `data_criacao` - ✅ Correto (ordenação)
- `qtd_selecionada_usuario` - ✅ Correto (quantidade pré-separada)
- `id` - ✅ Correto (identificação)

#### Separacao:
- `num_pedido` - ✅ Correto
- `cod_produto` - ✅ Correto
- `qtd_saldo` - ✅ Correto (quantidade na separação)
- `separacao_lote_id` - ✅ Correto

#### Pedido:
- `separacao_lote_id` - ✅ Correto (join com Separacao)
- `status` - ✅ Correto (filtro 'ABERTO' ou 'COTADO')

### 🔍 Análise: TODOS OS CAMPOS ESTÃO CORRETOS!

## 2. Correção da Lógica da Função

### ✅ Hierarquia de Impacto (CORRETA):
1. **Saldo Livre** (CarteiraPrincipal sem separacao_lote_id)
2. **Pré-Separações** (mais recentes primeiro)
3. **Separações ABERTO**
4. **Separações COTADO** (com alerta crítico)

### ✅ Pontos Positivos da Implementação:
1. **Usa transação implícita** - Alterações só são commitadas se todo o processo funcionar
2. **Trata ImportError** - Caso módulos não estejam disponíveis
3. **Gera logs detalhados** - Rastreabilidade completa
4. **Remove pré-separações zeradas** - Limpeza automática
5. **Gera alertas críticos** - Quando afeta separações cotadas

### ⚠️ Possíveis Melhorias Identificadas:

1. **Falta commit explícito**: A função não faz `db.session.commit()`, delegando para o chamador
2. **Falta validação de entrada**: Não valida se qtd_reduzida > 0
3. **Retorno não padronizado**: A função não retorna um dicionário estruturado com resultado

## 3. Rastreamento de Chamadas na Sincronização

### 📍 Onde a função É chamada:

#### 1. `/app/api/odoo/routes.py` (linha 231)
```python
resultado_reducao = PreSeparacaoItem.aplicar_reducao_quantidade(
    item.num_pedido, item.cod_produto, qtd_reduzida, "SYNC_ODOO"
)
```
- Chamada durante atualização individual de item
- Ocorre quando qtd_nova < qtd_anterior

### 🚨 DESCOBERTA IMPORTANTE:

**A função NÃO é chamada durante `sincronizar_carteira_odoo()`!**

A sincronização da carteira com Odoo (`CarteiraService.sincronizar_carteira_odoo()`) faz uma **substituição completa** da tabela CarteiraPrincipal:
1. Deleta TODOS os registros: `db.session.query(CarteiraPrincipal).delete()`
2. Insere novos registros do Odoo
3. Não faz comparação item a item

### 🔄 Quando a função É executada:

1. **Atualização individual via API** (`/api/odoo/routes.py`)
   - Endpoint: `/api/v1/odoo/carteira/atualizar/<id>`
   - Compara qtd anterior x qtd nova
   - Aplica redução se necessário

2. **NÃO é executada na sincronização em massa**
   - `sincronizar_carteira_odoo()` substitui tudo
   - Não há lógica de comparação/redução

## 4. Conclusões e Recomendações

### ✅ A função está CORRETA em:
- Campos utilizados
- Hierarquia de impacto
- Lógica de consumo
- Tratamento de erros

### ⚠️ PROBLEMA IDENTIFICADO:

**A função `aplicar_reducao_quantidade` NÃO é chamada durante a sincronização principal com o Odoo!**

Isso significa que quando `sincronizar_carteira_odoo()` é executada:
1. TODOS os dados antigos são deletados
2. Novos dados são inseridos
3. **Nenhuma lógica de redução gradual é aplicada**
4. Pré-separações e separações podem ficar inconsistentes

### 🔧 RECOMENDAÇÃO CRÍTICA:

Implementar lógica de comparação na `sincronizar_carteira_odoo()`:

```python
# ANTES de deletar tudo, fazer:
1. Carregar dados atuais em memória
2. Comparar com novos dados do Odoo
3. Para cada redução detectada:
   - Chamar aplicar_reducao_quantidade()
4. Só então atualizar os registros
```

### 📊 Impacto Atual:

- **Atualizações individuais**: ✅ Funcionam corretamente
- **Sincronização em massa**: ❌ Ignora a lógica de redução
- **Risco**: Separações cotadas podem ser afetadas sem alertas

## 5. Código Sugerido para Correção

```python
def sincronizar_carteira_odoo_com_reducao(self, usar_filtro_pendente=True):
    """
    Sincronização que aplica reduções graduais ao invés de substituição total
    """
    # 1. Buscar dados atuais
    dados_atuais = {
        (item.num_pedido, item.cod_produto): item.qtd_saldo_produto_pedido
        for item in CarteiraPrincipal.query.all()
    }
    
    # 2. Buscar dados novos do Odoo
    resultado_odoo = self.obter_carteira_pendente()
    
    # 3. Comparar e aplicar reduções
    for item_novo in resultado_odoo['dados']:
        chave = (item_novo['num_pedido'], item_novo['cod_produto'])
        qtd_atual = dados_atuais.get(chave, 0)
        qtd_nova = item_novo['qtd_saldo_produto_pedido']
        
        if qtd_nova < qtd_atual:
            # Aplicar redução gradual
            PreSeparacaoItem.aplicar_reducao_quantidade(
                item_novo['num_pedido'],
                item_novo['cod_produto'],
                qtd_atual - qtd_nova,
                "SYNC_ODOO_MASSA"
            )
    
    # 4. Só então atualizar os registros
    # ... resto da lógica
```