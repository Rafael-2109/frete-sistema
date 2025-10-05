# 🏍️ SISTEMA MOTOCHEFE

**Versão**: 1.0.0
**Descrição**: Gestão completa de motos elétricas - Estoque, Vendas, Financeiro e Logística

---

## 🎯 OBJETIVOS DO SISTEMA

Controlar **TODAS** as operações de uma empresa de motos elétricas:

✅ **Estoque** - FIFO automático por chassi
✅ **Vendas** - Pedido → Faturamento → Envio
✅ **Financeiro** - Títulos a receber, Comissões
✅ **Logística** - Embarques com rateio de frete
✅ **Custos** - Montagem, Movimentação, Despesas mensais

---

## 📂 ESTRUTURA DO PROJETO

```
app/motochefe/
├── README.md (este arquivo)
├── ESTRUTURA_BD.md (documentação técnica completa)
├── escopo.md (especificação original)
│
├── models/ (14 tabelas organizadas)
│   ├── __init__.py
│   ├── cadastro.py (4 tabelas)
│   ├── produto.py (2 tabelas - CENTRAL: Moto)
│   ├── vendas.py (2 tabelas)
│   ├── financeiro.py (2 tabelas)
│   ├── logistica.py (2 tabelas)
│   └── operacional.py (2 tabelas)
│
├── services/ (futuro - regras de negócio)
├── routes/ (futuro - APIs REST)
│
└── scripts/
    ├── create_tables.py (gerador de SQL)
    └── create_tables.sql (SQL para Render)
```

---

## 🚀 INÍCIO RÁPIDO

### **1. Criar tabelas no banco de dados**

```bash
# Método 1: Via Shell do Render (RECOMENDADO)
1. Acesse o PostgreSQL Shell no Render
2. Copie o conteúdo de: app/motochefe/scripts/create_tables.sql
3. Cole e execute no Shell

# Método 2: Via Python (local)
python app/motochefe/scripts/create_tables.py
```

### **2. Importar models no código**

```python
# Importação completa
from app.motochefe.models import *

# Ou importação específica
from app.motochefe.models import (
    ModeloMoto, Moto,
    PedidoVendaMoto, PedidoVendaMotoItem,
    TituloFinanceiro, ComissaoVendedor
)
```

### **3. Exemplo de uso - Entrada de Moto**

```python
from app.motochefe.models import ModeloMoto, Moto
from app import db

# 1. Criar modelo (se não existir)
modelo = ModeloMoto(
    nome_modelo='XYZ Cargo',
    potencia_motor='2000W',
    autopropelido=True,
    preco_tabela=10000.00
)
db.session.add(modelo)
db.session.commit()

# 2. Cadastrar moto (entrada)
moto = Moto(
    numero_chassi='9BWZZZ377VT004251',
    numero_motor='MT2024001',
    modelo_id=modelo.id,
    cor='Vermelha',
    ano_fabricacao=2024,
    nf_entrada='000123',
    data_nf_entrada=date.today(),
    fornecedor='Fornecedor ABC',
    custo_aquisicao=8500.00,
    pallet='A-15'
)
db.session.add(moto)
db.session.commit()
```

### **4. Exemplo - Criar Pedido com FIFO**

```python
from app.motochefe.models import PedidoVendaMoto, PedidoVendaMotoItem, Moto

# Buscar motos disponíveis (FIFO)
motos_disponiveis = Moto.query.filter_by(
    modelo_id=1,
    cor='Vermelha',
    status='DISPONIVEL',
    reservado=False
).order_by(Moto.data_entrada.asc()).limit(2).all()

# Criar pedido
pedido = PedidoVendaMoto(
    numero_pedido='PED-2024-001',
    cliente_id=1,
    vendedor_id=1,
    data_pedido=date.today(),
    valor_total_pedido=21000.00
)
db.session.add(pedido)
db.session.flush()  # Para pegar pedido.id

# Adicionar itens e reservar chassi
for moto in motos_disponiveis:
    item = PedidoVendaMotoItem(
        pedido_id=pedido.id,
        numero_chassi=moto.numero_chassi,
        preco_venda=10500.00
    )
    moto.reservado = True
    moto.status = 'RESERVADA'
    db.session.add(item)

db.session.commit()
```

---

## 📊 ESTRUTURA DE DADOS

### **14 Tabelas** divididas em 6 grupos:

| Grupo | Tabelas | Descrição |
|-------|---------|-----------|
| **Cadastro** | 4 | Vendedores, Equipes, Transportadoras, Clientes |
| **Produto** | 2 | ModeloMoto (catálogo), **Moto** (central) |
| **Vendas** | 2 | PedidoVendaMoto, Items |
| **Financeiro** | 2 | Títulos, Comissões |
| **Logística** | 2 | EmbarqueMoto, EmbarquePedido (N:N) |
| **Operacional** | 2 | Custos fixos, Despesas mensais |

📖 **Documentação completa**: [ESTRUTURA_BD.md](./ESTRUTURA_BD.md)

---

## 💡 REGRAS DE NEGÓCIO

### **RN1: FIFO Automático**
```python
# Chassi mais antigo sai primeiro
ORDER BY moto.data_entrada ASC
```

### **RN2: Comissão**
```
Comissão Total = Valor Fixo + Excedente
Excedente = (Preço Venda - Preço Tabela)
Rateio = Comissão Total / Qtd Vendedores Equipe
```

### **RN3: Rateio de Frete**
```
Frete por Moto = Valor Frete Embarque / Total Motos
Frete Pedido = Frete por Moto × Qtd Motos Pedido
```

### **RN4: Margem Bruta (por moto)**
```
Margem = (Venda + Frete Cliente + Montagem)
         - (Custo Moto + Comissão + Frete Pago + Montagem + Movimentação)
```

### **RN5: Margem Mensal**
```
Margem Mensal = Σ(Margem Bruta) - Despesas Operacionais
```

---

## 🔄 FLUXO OPERACIONAL

```
1. ENTRADA
   NF Fornecedor → Cadastrar Motos → Status: DISPONIVEL

2. VENDA
   Pedido → FIFO aloca Chassi → Moto: RESERVADA
   Faturamento → Gera NF → Moto: VENDIDA

3. LOGÍSTICA
   Embarque → Agrupa N Pedidos → Rateio Frete

4. FINANCEIRO
   Títulos a Receber (se parcelado)
   Comissões (calculadas automaticamente)

5. RELATÓRIOS
   Margem por Moto
   Margem Mensal (Bruta - Despesas)
```

---

## 📁 ARQUIVOS IMPORTANTES

| Arquivo | Descrição |
|---------|-----------|
| `README.md` | Este arquivo (visão geral) |
| `ESTRUTURA_BD.md` | Documentação técnica completa |
| `escopo.md` | Especificação original do sistema |
| `scripts/create_tables.sql` | SQL para criar todas as tabelas |
| `models/*.py` | Definições das 14 tabelas |

---

## ⚠️ ATENÇÃO

### **Modelos OBSOLETOS (NÃO USAR)**:
```
app/motochefe/_old_cadastro/
app/motochefe/_old_entrada/
app/motochefe/_old_estoque/
app/motochefe/_old_saida/
app/motochefe/_old_financeiro/
```

**Use apenas**: `app/motochefe/models/*.py`

---

## 📈 PRÓXIMOS PASSOS

- [ ] Implementar services (regras de negócio encapsuladas)
- [ ] Criar rotas/APIs REST
- [ ] Desenvolver dashboards
- [ ] Testes automatizados
- [ ] Documentação de APIs

---

## 🛠️ TECNOLOGIAS

- **Python 3.x**
- **Flask**
- **SQLAlchemy**
- **PostgreSQL**

---

## 📞 SUPORTE

**Documentação**:
- [ESTRUTURA_BD.md](./ESTRUTURA_BD.md) - Detalhamento técnico
- [escopo.md](./escopo.md) - Especificação original

**Arquivos**:
- Models: `app/motochefe/models/`
- SQL: `app/motochefe/scripts/create_tables.sql`

---

**Sistema desenvolvido com planejamento arquitetural rigoroso**
**Versão**: 1.0.0 | **Data**: Outubro 2025
