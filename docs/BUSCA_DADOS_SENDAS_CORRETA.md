# 📊 FLUXO CORRETO DE BUSCA DE DADOS PARA AGENDAMENTO SENDAS

**Data:** 2025-01-14
**Versão:** 2.0
**Objetivo:** Documentar o fluxo CORRETO de busca de dados, esclarecendo equívocos

---

## ⚠️ CORREÇÃO IMPORTANTE

### ENTENDIMENTO ERRADO (ANTERIOR):
- ❌ Buscar Separacao com sincronizado_nf=False separadamente
- ❌ Ignorar registros com status='PREVISAO'
- ❌ Buscar de 3 fontes diferentes

### ENTENDIMENTO CORRETO:
- ✅ CarteiraPrincipal JÁ INCLUI tudo com sincronizado_nf=False
- ✅ NUNCA ignorar status='PREVISAO' (são válidos para agendamento)
- ✅ Buscar de apenas 2 fontes

---

## 📋 FONTES DE DADOS CORRETAS

### 1️⃣ CarteiraPrincipal
**O que contém:**
- ✅ Saldo em carteira (pedidos originais)
- ✅ Separações com sincronizado_nf=False (não faturadas)
- ✅ Pré-separações (status='PREVISAO')
- ✅ TUDO que ainda não foi faturado e tem saldo

**Query:**
```sql
SELECT * FROM carteira_principal
WHERE cnpj_cpf = :cnpj
  AND ativo = true
  AND qtd_saldo_produto_pedido > 0
```

**Campos importantes:**
- `pedido_cliente`: Geralmente preenchido
- `qtd_saldo_produto_pedido`: Quantidade disponível
- `expedicao`, `agendamento`, `protocolo`: Datas e controle

### 2️⃣ Separacao com nf_cd=True
**O que contém:**
- ✅ NFs que foram faturadas MAS voltaram ao CD
- ✅ Mercadoria física disponível para reagendamento

**Query:**
```sql
SELECT * FROM separacao
WHERE cnpj_cpf = :cnpj
  AND nf_cd = true  -- NF voltou ao CD
```

**Observação:**
- NÃO filtrar por sincronizado_nf aqui
- Apenas nf_cd=True é relevante

---

## ❌ O QUE NÃO FAZER

### NÃO buscar Separacao com sincronizado_nf=False
**Motivo:** CarteiraPrincipal já inclui esses registros. Buscar novamente causaria DUPLICAÇÃO.

### NÃO ignorar status='PREVISAO'
**Motivo:** Pré-separações são agendamentos válidos e devem ser incluídos.

### NÃO filtrar por status em Separacao
**Motivo:** Todos os status são válidos se nf_cd=True.

---

## 🔄 FLUXO DE BUSCA IMPLEMENTADO

```python
def buscar_dados_completos_cnpj(cnpj):
    dados = {'itens': []}

    # 1. CarteiraPrincipal (inclui TUDO não faturado)
    itens_carteira = buscar_carteira_principal(cnpj)
    dados['itens'].extend(itens_carteira)

    # 2. NFs no CD (Separacao com nf_cd=True)
    itens_nf_cd = buscar_nfs_no_cd(cnpj)
    dados['itens'].extend(itens_nf_cd)

    # 3. Garantir pedido_cliente (fallback Odoo se necessário)
    garantir_pedido_cliente(dados['itens'])

    return dados
```

---

## 📊 TABELA DE ONDE VEM CADA TIPO DE ITEM

| Situação do Item | Fonte de Dados | Filtros |
|-----------------|----------------|---------|
| Pedido em carteira (saldo) | CarteiraPrincipal | ativo=True, qtd_saldo > 0 |
| Separado não faturado | CarteiraPrincipal | (já incluído) |
| Pré-separação (PREVISAO) | CarteiraPrincipal | (já incluído) |
| NF que voltou ao CD | Separacao | nf_cd=True |

---

## 🎯 BENEFÍCIOS DA ABORDAGEM CORRETA

1. **Sem duplicação**: Cada item vem de uma única fonte
2. **Performance**: Menos queries ao banco
3. **Simplicidade**: Lógica mais clara e direta
4. **Completude**: Todos os itens válidos são incluídos

---

## 📝 NOTAS IMPORTANTES

### Sobre sincronizado_nf
- `sincronizado_nf=False`: Item NÃO foi faturado (está na CarteiraPrincipal)
- `sincronizado_nf=True`: Item FOI faturado (tem NF)
- Se `sincronizado_nf=True AND nf_cd=True`: NF voltou ao CD (buscar em Separacao)

### Sobre status='PREVISAO'
- É um status VÁLIDO em Separacao
- Representa pré-separações ou previsões de separação
- DEVE ser incluído no agendamento
- NUNCA filtrar para excluir

### Sobre pedido_cliente
- Geralmente vem preenchido da CarteiraPrincipal
- Se NULL, buscar do Odoo como fallback
- Crítico para matching na planilha Sendas

---

## 🔍 VALIDAÇÃO

Para validar que está correto, verificar:

1. **Sem duplicatas**: Nenhum item aparece 2x
2. **Todos incluídos**: Conferir com relatório manual
3. **pedido_cliente presente**: Todos os itens têm esse campo
4. **Performance**: Tempo de busca < 2 segundos por CNPJ