# 📘 GUIA COMPLETO - Refatoração Financeira MotoCHEFE

## 🎯 O QUE FOI IMPLEMENTADO

Sistema financeiro completamente refatorado com:
- ✅ **Títulos por moto** (4 tipos: Movimentação, Montagem, Frete, Venda)
- ✅ **Empresas como contas bancárias** (com saldo)
- ✅ **Baixa automática de motos** (FIFO)
- ✅ **Títulos a pagar** (Movimentação → MargemSogima, Montagem → Equipe)
- ✅ **Extrato financeiro detalhado** (origem e destino)
- ✅ **Comissão por moto** (não mais por pedido)

---

## 🚀 PASSO 1: EXECUTAR MIGRATIONS

### Local (SQLite/PostgreSQL):
```bash
python app/motochefe/scripts/migration_refatoracao_financeira_local.py
```

### Render (PostgreSQL):
1. Acesse o shell do PostgreSQL no Render
2. Copie e cole o conteúdo de: `app/motochefe/scripts/migration_refatoracao_financeira_render.sql`
3. Execute

### Verificar se funcionou:
```python
from app import create_app, db
from app.motochefe.models.financeiro import MovimentacaoFinanceira, TituloAPagar
from app.motochefe.services.empresa_service import garantir_margem_sogima

app = create_app()
with app.app_context():
    # Verificar tabelas
    print("MovimentacaoFinanceira:", MovimentacaoFinanceira.query.count())
    print("TituloAPagar:", TituloAPagar.query.count())

    # Verificar MargemSogima
    margem = garantir_margem_sogima()
    print("MargemSogima:", margem)
```

---

## 📋 PASSO 2: CONFIGURAR EMPRESAS

### 2.1. Criar/Configurar Empresas Recebedoras

**Exemplo: Fabricante Honda**
```python
empresa_honda = EmpresaVendaMoto(
    cnpj_empresa='12.345.678/0001-00',
    empresa='Fabricante Honda',
    tipo_conta='FABRICANTE',
    baixa_compra_auto=True,  # ✅ Baixa automática ATIVADA
    saldo=0,
    ativo=True
)
db.session.add(empresa_honda)
```

**Exemplo: Conta Operacional**
```python
empresa_operacional = EmpresaVendaMoto(
    cnpj_empresa='98.765.432/0001-00',
    empresa='Operacional MotoChefe',
    tipo_conta='OPERACIONAL',
    baixa_compra_auto=False,  # Apenas acumula saldo
    saldo=0,
    ativo=True
)
db.session.add(empresa_operacional)
```

### 2.2. MargemSogima (Criada Automaticamente)
```python
# Já criada pela migration
margem = EmpresaVendaMoto.query.filter_by(tipo_conta='MARGEM_SOGIMA').first()
print(margem.empresa)  # 'MargemSogima'
```

---

## 🛒 PASSO 3: EMITIR PEDIDO (NOVO FLUXO)

### 3.1. Imports Necessários
```python
from app.motochefe.services.titulo_service import gerar_titulos_por_moto, calcular_valores_titulos_moto
from app.motochefe.services.titulo_a_pagar_service import (
    criar_titulo_a_pagar_movimentacao,
    criar_titulo_a_pagar_montagem
)
```

### 3.2. Criar Pedido + Títulos
```python
# 1. Criar pedido (como antes)
pedido = PedidoVendaMoto(...)
db.session.add(pedido)
db.session.flush()

# 2. Para cada moto alocada
for item in itens_pedido:
    # Calcular valores
    equipe = pedido.vendedor.equipe
    valores = calcular_valores_titulos_moto(item, equipe)

    # Gerar 4 títulos (Movimentação, Montagem, Frete, Venda)
    titulos = gerar_titulos_por_moto(pedido, item, valores)

    # Criar títulos a pagar (PENDENTES)
    for titulo in titulos:
        if titulo.tipo_titulo == 'MOVIMENTACAO':
            criar_titulo_a_pagar_movimentacao(titulo)

        elif titulo.tipo_titulo == 'MONTAGEM' and item.montagem_contratada:
            criar_titulo_a_pagar_montagem(titulo, item)

db.session.commit()
```

---

## 💰 PASSO 4: RECEBER TÍTULOS (NOVO FLUXO)

### 4.1. Imports
```python
from app.motochefe.services.titulo_service import receber_titulo
```

### 4.2. Receber Título
```python
# Usuário escolhe empresa recebedora
empresa_recebedora = EmpresaVendaMoto.query.get(empresa_id)
titulo = TituloFinanceiro.query.get(titulo_id)
valor_recebido = Decimal('5000.00')

# Processar recebimento
resultado = receber_titulo(
    titulo,
    valor_recebido,
    empresa_recebedora,
    usuario=current_user.nome
)

db.session.commit()

# Resultado contém:
print(resultado['totalmente_pago'])           # True/False
print(resultado['titulo_a_pagar_liberado'])   # TituloAPagar ou None
print(resultado['baixa_automatica'])          # dict com motos pagas
print(resultado['comissao_gerada'])           # list de ComissaoVendedor
```

### 4.3. O que acontece automaticamente:

**Se empresa.baixa_compra_auto = True:**
1. ✅ Registra recebimento em `MovimentacaoFinanceira`
2. ✅ Atualiza saldo da empresa (+valor)
3. ✅ Se título totalmente pago:
   - Libera `TituloAPagar` (PENDENTE → ABERTO)
   - **Executa baixa automática de motos** (FIFO)
   - Gera comissão (se tipo VENDA)

---

## 📝 PASSO 5: PAGAR TÍTULOS A PAGAR

### 5.1. Listar Títulos Disponíveis
```python
from app.motochefe.services.titulo_a_pagar_service import listar_titulos_a_pagar

# Apenas liberados para pagamento
titulos_abertos = listar_titulos_a_pagar(status='ABERTO')

for titulo in titulos_abertos:
    print(f"{titulo.tipo} - {titulo.beneficiario} - R$ {titulo.valor_saldo}")
```

### 5.2. Pagar Título
```python
from app.motochefe.services.titulo_a_pagar_service import pagar_titulo_a_pagar

titulo_pagar = TituloAPagar.query.get(id)
empresa_pagadora = EmpresaVendaMoto.query.get(empresa_id)
valor = Decimal('1000.00')

resultado = pagar_titulo_a_pagar(
    titulo_pagar,
    valor,
    empresa_pagadora,
    usuario=current_user.nome
)

db.session.commit()

print(resultado['saldo_restante'])  # Quanto ainda falta pagar
```

---

## 📊 PASSO 6: EXTRATO FINANCEIRO

### 6.1. Obter Extrato
```python
from app.motochefe.services.movimentacao_service import obter_extrato, calcular_saldo_periodo
from datetime import date, timedelta

data_inicial = date.today() - timedelta(days=30)
data_final = date.today()

# Extrato geral
movimentacoes = obter_extrato(data_inicial, data_final)

# Extrato de empresa específica
movimentacoes_empresa = obter_extrato(
    data_inicial,
    data_final,
    empresa_id=empresa.id
)

# Calcular totais
totais = calcular_saldo_periodo(movimentacoes)
print(totais['recebimentos'])  # Total recebido
print(totais['pagamentos'])    # Total pago
print(totais['saldo'])          # Saldo do período
```

---

## 🔧 FUNÇÕES ÚTEIS

### Simular Baixa Automática
```python
from app.motochefe.services.baixa_automatica_service import simular_baixa_automatica

simulacao = simular_baixa_automatica(empresa, valor_disponivel=Decimal('50000'))

for moto in simulacao['motos_a_pagar']:
    print(f"Chassi: {moto['chassi']}")
    print(f"  Devedor: R$ {moto['devedor']}")
    print(f"  Vai pagar: R$ {moto['valor_a_pagar']}")
```

### Verificar Motos Pendentes
```python
from app.motochefe.services.baixa_automatica_service import verificar_motos_pendentes

stats = verificar_motos_pendentes()
print(f"Motos pendentes: {stats['motos_pendentes']}")
print(f"Motos parciais: {stats['motos_parciais']}")
print(f"Total devedor: R$ {stats['total_devedor']}")
```

### Validar Saldo
```python
from app.motochefe.services.empresa_service import validar_saldo

valido, mensagem = validar_saldo(empresa_id, valor_necessario=Decimal('10000'))
print(mensagem)  # "Saldo suficiente" ou "Atenção: Saldo ficará negativo..."
```

---

## ⚠️ REGRAS IMPORTANTES

### 1. Ordem de Pagamento de Títulos
Sempre paga nesta sequência:
1. Movimentação (ordem 1)
2. Montagem (ordem 2)
3. Frete (ordem 3)
4. Venda (ordem 4)

### 2. Status dos Títulos A Pagar
- **PENDENTE**: Aguardando cliente pagar título origem
- **ABERTO**: Liberado para pagamento
- **PARCIAL**: Pagamento parcial efetuado
- **PAGO**: Totalmente quitado

### 3. Comissão
- Gerada **por moto** quando título de VENDA totalmente pago
- Se equipe.tipo_comissao = 'PERCENTUAL': incide sobre SOMA dos 4 títulos da moto

### 4. Baixa Automática
- Só executa se `empresa.baixa_compra_auto = True`
- FIFO por `Moto.data_entrada`
- Processa 1 vez com valor total do recebimento

### 5. Saldo Negativo
- Sistema **PERMITE** saldo negativo
- Valida mas não bloqueia operações

---

## 🐛 TROUBLESHOOTING

### Problema: MargemSogima não foi criada
```python
from app.motochefe.services.empresa_service import garantir_margem_sogima
margem = garantir_margem_sogima()
```

### Problema: Título a pagar não liberou
```python
# Verificar status do título origem
titulo_origem = TituloFinanceiro.query.get(id)
print(titulo_origem.status)  # Deve ser 'PAGO'

# Forçar liberação manual
from app.motochefe.services.titulo_a_pagar_service import liberar_titulo_a_pagar
titulo_pagar = liberar_titulo_a_pagar(titulo_origem.id)
```

### Problema: Saldo desatualizado
```python
# Recalcular saldo (property)
empresa = EmpresaVendaMoto.query.get(id)
saldo_calculado = empresa.saldo_calculado  # Via MovimentacaoFinanceira
saldo_armazenado = empresa.saldo

if saldo_calculado != saldo_armazenado:
    empresa.saldo = saldo_calculado
    db.session.commit()
```

---

## 📁 ARQUIVOS CRIADOS

### Models:
- `app/motochefe/models/financeiro.py` (MODIFICADO)
- `app/motochefe/models/cadastro.py` (MODIFICADO)

### Services:
- `app/motochefe/services/empresa_service.py` (NOVO)
- `app/motochefe/services/movimentacao_service.py` (NOVO)
- `app/motochefe/services/titulo_a_pagar_service.py` (NOVO)
- `app/motochefe/services/baixa_automatica_service.py` (NOVO)
- `app/motochefe/services/titulo_service.py` (NOVO)
- `app/motochefe/services/comissao_service.py` (NOVO)

### Routes:
- `app/motochefe/routes/titulos_a_pagar.py` (NOVO)

### Migrations:
- `app/motochefe/scripts/migration_refatoracao_financeira_render.sql` (NOVO)
- `app/motochefe/scripts/migration_refatoracao_financeira_local.py` (NOVO)

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Executar migrations
2. ✅ Configurar empresas (fabricantes + operacional)
3. ✅ Testar emissão de pedido
4. ✅ Testar recebimento com baixa automática
5. ✅ Verificar títulos a pagar
6. ✅ Validar extrato financeiro

**BOA SORTE!** 🚀
