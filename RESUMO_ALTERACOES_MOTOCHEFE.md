# 📋 RESUMO DAS ALTERAÇÕES - MÓDULO MOTOCHEFE

**Data:** 10/01/2025
**Objetivo:** Reestruturar completamente o sistema de pagamentos e recebimentos para seguir padrão unificado

---

## 🎯 OBJETIVO GERAL

Garantir que TODOS os tipos de movimentação financeira (recebimentos e pagamentos) sigam o mesmo padrão:

1. **Linha única no extrato** para lotes de pagamento/recebimento
2. **Botão "Detalhes"** que abre tela com breakdown individual
3. **Empresa pagadora/recebedora** registrada em TODOS os tipos
4. **Abatimento automático de saldo** de EmpresaVendaMoto
5. **Rastreabilidade completa** via MovimentacaoFinanceira

---

## 📦 ARQUIVOS CRIADOS

### Migrations
1. **migrations/scripts/20250110_adicionar_campos_pagamento_lote.py**
   - Script Python para rodar localmente
   - Adiciona campos: `empresa_pagadora_id`, `lote_pagamento_id`
   - Tabelas: `moto`, `comissao_vendedor`, `pedido_venda_moto_item`

2. **migrations/sql/20250110_adicionar_campos_pagamento_lote.sql**
   - Script SQL para rodar no Shell do Render
   - Cria os mesmos campos + índices + foreign keys

### Services
3. **app/motochefe/services/lote_pagamento_service.py**
   - **Funções principais:**
     - `processar_pagamento_lote_motos()` - Paga lote de motos
     - `processar_pagamento_lote_comissoes()` - Paga lote de comissões
     - `processar_pagamento_lote_montagens()` - Paga lote de montagens
     - `processar_pagamento_lote_despesas()` - Paga lote de despesas
     - `obter_detalhes_lote_pagamento()` - Busca detalhes para tela
   - **Padrão:** Cria 1 MovimentacaoFinanceira PAI + N FILHOS

### Templates
4. **app/templates/motochefe/financeiro/detalhes_pagamento.html**
   - Tela de detalhes de pagamento em lote
   - Mostra resumo do lote + tabela de itens

5. **app/templates/motochefe/financeiro/detalhes_recebimento.html**
   - Tela de detalhes de recebimento por moto
   - Mostra os 4 títulos (MOVIMENTACAO, MONTAGEM, FRETE, VENDA)
   - Mostra histórico de recebimentos

---

## 🔧 ARQUIVOS MODIFICADOS

### Models

#### app/motochefe/models/produto.py (Moto)
**Campos adicionados:**
```python
empresa_pagadora_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
lote_pagamento_id = db.Column(db.Integer, nullable=True, index=True)
empresa_pagadora = db.relationship('EmpresaVendaMoto', foreign_keys=[empresa_pagadora_id], backref='motos_pagas')
```

#### app/motochefe/models/financeiro.py (ComissaoVendedor)
**Campos adicionados:**
```python
empresa_pagadora_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
lote_pagamento_id = db.Column(db.Integer, nullable=True, index=True)
empresa_pagadora = db.relationship('EmpresaVendaMoto', foreign_keys=[empresa_pagadora_id], backref='comissoes_pagas')
```

#### app/motochefe/models/vendas.py (PedidoVendaMotoItem)
**Campos adicionados:**
```python
empresa_pagadora_montagem_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
lote_pagamento_montagem_id = db.Column(db.Integer, nullable=True, index=True)
empresa_pagadora_montagem = db.relationship('EmpresaVendaMoto', foreign_keys=[empresa_pagadora_montagem_id], backref='montagens_pagas')
```

---

### Routes

#### app/motochefe/routes/financeiro.py

**1. Função `pagar_lote()` - REFATORADA COMPLETAMENTE**
- **Antes:** Atualizava campos diretamente, não criava MovimentacaoFinanceira
- **Agora:**
  - Agrupa itens por tipo (moto, comissão, montagem, despesa)
  - Cria 1 lote para cada tipo usando services
  - Cada lote = 1 MovimentacaoFinanceira PAI + N FILHOS
  - Atualiza saldo automaticamente
  - Fretes ainda processados individualmente (futuro: também em lote)

**2. Função `listar_contas_a_pagar()` - ATUALIZADA**
- Adicionado: Busca empresas ativas para select de empresa pagadora
- Passa `empresas` para o template

**3. Rotas NOVAS adicionadas:**
```python
@motochefe_bp.route('/pagamentos/<int:movimentacao_id>/detalhes')
def detalhes_pagamento(movimentacao_id)

@motochefe_bp.route('/recebimentos/<int:titulo_id>/detalhes')
def detalhes_recebimento(titulo_id)
```

---

### Services

#### app/motochefe/services/extrato_financeiro_service.py

**Modificações principais:**

1. **SQL de RECEBIMENTOS (linha 51-78):**
   - Adicionado filtro: `AND mf.movimentacao_origem_id IS NULL`
   - **Efeito:** Mostra apenas PAI (lotes) e recebimentos individuais
   - **Rota detalhes:** `/motochefe/recebimentos/{titulo_id}/detalhes`

2. **SQL de PAGAMENTOS - REMOVIDOS:**
   - ❌ sql_moto (Custo de Motos)
   - ❌ sql_montagem (Montagem)
   - ❌ sql_comissao (Comissões)
   - ❌ sql_despesa (Despesas)

3. **SQL de PAGAMENTOS - ADICIONADO:**
   - ✅ `sql_pagamentos_lote` (linha 101-126)
   - Busca apenas MovimentacaoFinanceira com:
     - `tipo = 'PAGAMENTO'`
     - `movimentacao_origem_id IS NULL` (apenas PAI)
     - `categoria IN ('Lote Custo Moto', 'Lote Comissão', 'Lote Montagem', 'Lote Despesa')`
   - **Rota detalhes:** `/motochefe/pagamentos/{movimentacao_id}/detalhes`

4. **SQL de FRETES - MANTIDO:**
   - ✅ Ainda busca diretamente de `embarque_moto`
   - Futuro: migrar para lote também

---

### Templates

#### app/templates/motochefe/financeiro/extrato.html
**Modificação:**
- Botão "Detalhes" agora mostra texto "Detalhes" além do ícone
- Verifica se `mov.rota_detalhes` existe antes de mostrar

####app/templates/motochefe/financeiro/contas_a_pagar.html
**Adicionado:**
- Card com select de **Empresa Pagadora** (OBRIGATÓRIO)
- Mostra saldo de cada empresa no select
- Tooltip explicativo

---

## 🔄 FLUXO COMPLETO

### PAGAMENTO EM LOTE (Exemplo: 3 motos)

**1. Usuário seleciona itens na tela de Contas a Pagar:**
- Seleciona empresa pagadora no select
- Marca 3 motos da NF 12345
- Clica em "Pagar Selecionados"

**2. Backend processa (`pagar_lote()`):**
```python
# Agrupa por tipo
chassi_list = ['ABC123', 'DEF456', 'GHI789']

# Chama service
processar_pagamento_lote_motos(
    chassi_list=chassi_list,
    empresa_pagadora=Honda Brasil,
    data_pagamento=2025-01-10,
    usuario='João'
)
```

**3. Service cria estrutura PAI + FILHOS:**
```
MovimentacaoFinanceira #100 (PAI)
├─ tipo: PAGAMENTO
├─ categoria: Lote Custo Moto
├─ valor: R$ 45.000,00
├─ empresa_origem_id: 1 (Honda Brasil)
├─ descricao: "Pagamento Lote 3 moto(s) - NF 12345"
└─ observacoes: "Lote com 3 moto(s): ABC123, DEF456, GHI789"

MovimentacaoFinanceira #101 (FILHO)
├─ tipo: PAGAMENTO
├─ categoria: Custo Moto
├─ valor: R$ 15.000,00
├─ numero_chassi: ABC123
├─ movimentacao_origem_id: 100 (referência ao PAI)

MovimentacaoFinanceira #102 (FILHO)
├─ tipo: PAGAMENTO
├─ valor: R$ 15.000,00
├─ numero_chassi: DEF456
├─ movimentacao_origem_id: 100

MovimentacaoFinanceira #103 (FILHO)
├─ tipo: PAGAMENTO
├─ valor: R$ 15.000,00
├─ numero_chassi: GHI789
├─ movimentacao_origem_id: 100
```

**4. Atualiza registros individuais:**
```python
# Para cada moto:
moto.custo_pago = moto.custo_aquisicao
moto.status_pagamento_custo = 'PAGO'
moto.data_pagamento_custo = 2025-01-10
moto.empresa_pagadora_id = 1  # 🆕
moto.lote_pagamento_id = 100  # 🆕
```

**5. Atualiza saldo da empresa:**
```python
atualizar_saldo(empresa_id=1, valor=45000, operacao='SUBTRAIR')
# Honda Brasil: saldo anterior - R$ 45.000
```

**6. No extrato, aparece UMA ÚNICA LINHA:**
```
Data       | Tipo      | Categoria        | Descrição                  | Valor     | Ação
10/01/2025 | PAGAMENTO | Lote Custo Moto  | Pagamento Lote 3 moto(s).. | -45.000   | [Detalhes]
```

**7. Ao clicar em "Detalhes":**
- Abre `/motochefe/pagamentos/100/detalhes`
- Mostra resumo do lote + tabela com 3 linhas (uma para cada moto)

---

### RECEBIMENTO (Exemplo: 1 moto com 4 títulos)

**1. Estrutura de Títulos (criada no faturamento):**
```
Moto ABC123 - Pedido 001
├─ TituloFinanceiro #1 (MOVIMENTACAO, ordem=1)  - R$ 1.000
├─ TituloFinanceiro #2 (MONTAGEM, ordem=2)      - R$ 500
├─ TituloFinanceiro #3 (FRETE, ordem=3)         - R$ 300
└─ TituloFinanceiro #4 (VENDA, ordem=4)         - R$ 15.000
```

**2. Cliente paga título de VENDA:**
```python
receber_titulo(
    titulo=titulo_venda,
    valor_recebido=15000,
    empresa_recebedora=Honda Brasil,
    usuario='João'
)
```

**3. Service cria MovimentacaoFinanceira:**
```
MovimentacaoFinanceira #200
├─ tipo: RECEBIMENTO
├─ categoria: Título VENDA
├─ valor: R$ 15.000,00
├─ empresa_destino_id: 1 (Honda Brasil)
├─ titulo_financeiro_id: 4
├─ numero_chassi: ABC123
```

**4. No extrato, aparece:**
```
Data       | Tipo        | Categoria     | Descrição              | Valor    | Ação
10/01/2025 | RECEBIMENTO | Título VENDA  | Recebimento Título #4  | +15.000  | [Detalhes]
```

**5. Ao clicar em "Detalhes":**
- Abre `/motochefe/recebimentos/4/detalhes`
- Mostra os 4 títulos da moto ABC123
- Mostra histórico de recebimentos

---

## ✅ VALIDAÇÕES IMPLEMENTADAS

### 1. Saldo sempre atualizado
- **Recebimentos:** `atualizar_saldo(empresa, valor, 'SOMAR')`
- **Pagamentos:** `atualizar_saldo(empresa, valor, 'SUBTRAIR')`

### 2. Empresa pagadora/recebedora SEMPRE registrada
- ✅ Motos: `moto.empresa_pagadora_id`
- ✅ Comissões: `comissao.empresa_pagadora_id`
- ✅ Montagens: `item.empresa_pagadora_montagem_id`
- ✅ Despesas: `despesa.empresa_pagadora_id` (já existia)
- ✅ Fretes: `embarque.empresa_pagadora_id` (já existia)
- ✅ Títulos: `titulo.empresa_recebedora_id` (já existia)

### 3. Rastreabilidade PAI → FILHOS
- Campo `movimentacao_origem_id` em MovimentacaoFinanceira
- Permite buscar todos os filhos de um lote: `WHERE movimentacao_origem_id = {pai_id}`

---

## 🚀 PRÓXIMOS PASSOS

### ANTES DE RODAR EM PRODUÇÃO:

1. **Rodar migrations localmente:**
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python migrations/scripts/20250110_adicionar_campos_pagamento_lote.py
```

2. **Validar no ambiente local:**
   - Fazer pagamento em lote de motos
   - Verificar se aparece no extrato
   - Clicar em "Detalhes" e validar breakdown
   - Verificar se saldo da empresa foi atualizado

3. **Rodar migration no Render:**
   - Acessar Shell do Render
   - Copiar conteúdo de `migrations/sql/20250110_adicionar_campos_pagamento_lote.sql`
   - Executar no psql

4. **Testar em produção:**
   - Fazer pagamento teste
   - Validar extrato
   - Validar saldos

---

## 📊 ESTATÍSTICAS DAS ALTERAÇÕES

- **Arquivos criados:** 5
- **Arquivos modificados:** 7
- **Linhas de código adicionadas:** ~800
- **Campos de banco adicionados:** 6
- **Novas rotas:** 2
- **Novos services:** 5 funções

---

## 🎓 CONCEITOS IMPLEMENTADOS

### Padrão PAI-FILHO
- **PAI:** Movimentação principal (lote)
- **FILHOS:** Movimentações individuais (itens do lote)
- **Vantagem:** Extrato limpo + rastreabilidade total

### Single Source of Truth
- `MovimentacaoFinanceira` é a ÚNICA fonte de verdade
- Campos nas tabelas específicas são REDUNDANTES (para queries rápidas)
- Em caso de divergência, MovimentacaoFinanceira prevalece

### Separação de Responsabilidades
- **Routes:** Orquestração e validação
- **Services:** Lógica de negócio
- **Models:** Estrutura de dados

---

**FIM DO RESUMO**
