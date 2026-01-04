# Regras de Negocio - Gerindo Expedicao

Constantes, calculos e regras de negocio utilizadas pelos scripts desta skill.

> **Quando usar:** Consulte este arquivo quando precisar de valores de constantes, formulas de calculo, ou regras de negocio para expedicao.

---

## Indice

1. [Grupos Empresariais](#grupos-empresariais)
2. [Constantes de Negocio](#constantes-de-negocio)
3. [Limites de Veiculos](#limites-de-veiculos)
4. [UFs para Regras de Expedicao](#ufs-para-regras-de-expedicao)
5. [Leadtimes de Planejamento](#leadtimes-de-planejamento)
6. [Calculos de Estoque](#calculos-de-estoque)
7. [Calculos de Separacao](#calculos-de-separacao)
8. [Identificacao de Gestores](#identificacao-de-gestores)
9. [Normalizacao de Texto](#normalizacao-de-texto)

---

## Grupos Empresariais

> **VER CLAUDE.md** - Grupos empresariais estao documentados no arquivo CLAUDE.md na raiz do projeto (secao "Regras de Negocio").
> Scripts usam `resolver_entidades.GRUPOS_EMPRESARIAIS` que ja contem os prefixos CNPJ corretos.

---

## Constantes de Negocio

```python
# Limites para carga direta (exige agendamento)
LIMITE_PALLETS_CARGA_DIRETA = 26
LIMITE_PESO_CARGA_DIRETA = 20000  # kg

# Limites para envio parcial obrigatorio
LIMITE_PALLETS_ENVIO_PARCIAL = 30
LIMITE_PESO_ENVIO_PARCIAL = 25000  # kg

# Regras de parcial
LIMITE_FALTA_PARCIAL_AUTO = 0.10        # 10%
LIMITE_FALTA_CONSULTAR = 0.20           # 20%
DIAS_DEMORA_PARA_PARCIAL = 3
VALOR_MINIMO_CONSULTAR_COMERCIAL = 10000
VALOR_PEDIDO_PEQUENO = 15000
```

---

## Limites de Veiculos

| Veiculo | Limite Peso | Limite Pallets | Uso |
|---------|-------------|----------------|-----|
| Toco | Pelo peso | - | Cargas menores |
| Truck | - | 16 pallets | Cargas medias |
| Carreta | 24-32 ton | 26-30 pallets | Cargas diretas |

**Regras de carga:**
- Carga direta: >= 26 pallets OU >= 20.000 kg
- Parcial obrigatorio: >= 30 pallets OU >= 25.000 kg (limite carreta)

---

## UFs para Regras de Expedicao

```python
# SC/PR com carga direta > 2.000kg = D-2
UFS_CARGA_DIRETA_D2 = ['SC', 'PR']
LIMITE_PESO_CARGA_DIRETA_SC_PR = 2000  # kg
```

---

## Leadtimes de Planejamento

### Com data_entrega_pedido definida

| Destino | Expedicao |
|---------|-----------|
| SC/PR (>2.000kg) | data_entrega_pedido - 2 dias uteis |
| SP | data_entrega_pedido - 1 dia util |

### Necessita de agendamento

| Campo | Calculo |
|-------|---------|
| Expedicao | D+3 |
| Agendamento sugerido | D+3 + leadtime |

### Outros casos

| Expedicao |
|-----------|
| D+1 |

---

## Calculos de Estoque

### Estoque Atual
```python
estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
```

### Projecao de Estoque
```python
projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=28)
# Retorna: {
#   'dia_ruptura': 'YYYY-MM-DD' ou None,
#   'projecao': [{'data': '...', 'saldo_final': N}, ...]
# }
```

---

## Calculos de Separacao

### Peso e Pallets
```python
peso = qtd_saldo * peso_bruto  # Do CadastroPalletizacao
pallet = qtd_saldo / palletizacao  # Do CadastroPalletizacao
```

### Rota e Sub-rota
```python
from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade

rota = buscar_rota_por_uf(cod_uf)
sub_rota = buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade)
```

---

## Identificacao de Gestores

> **VER communication.md** - Mapeamento de gestores e canais esta em `references/communication.md`.
