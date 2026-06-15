<!-- doc:meta
tipo: explanation
camada: L2
sot_de: Conceito, modelo de dados e fluxo de processamento de CTes complementares vinculados a Despesas Extras
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 📋 Sistema de CTe Complementar

> **Papel:** explicar o conceito de CTe complementar, o modelo de dados que o representa e o fluxo de identificação, relacionamento e vinculação a Despesas Extras.

## Contexto

Este documento descreve como CTes complementares (taxas de reentrega, agendamento, armazenagem, etc.) são identificados via análise do XML, relacionados ao CTe original e vinculados a **Despesas Extras** em vez do frete principal. Cobre o conceito fiscal, o modelo `ConhecimentoTransporte`, o fluxo de importação/exibição/vinculação e queries de apoio.

## Indice

- [Conceito de CTe Complementar](#-conceito-de-cte-complementar)
- [Modelo de Dados](#-modelo-de-dados)
- [Fluxo de Processamento](#-fluxo-de-processamento)
- [Migration SQL](#-migration-sql)
- [Exemplo Prático](#-exemplo-prático)
- [Queries Úteis](#-queries-úteis)
- [Interface](#-interface)
- [Próximos Passos](#-próximos-passos)
- [Referências](#-referências)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 OBJETIVO

Identificar, relacionar e gerenciar CTes complementares automaticamente através da análise do XML, permitindo vincular esses CTes a **Despesas Extras** em vez do frete principal.

---

## 📊 CONCEITO DE CTe COMPLEMENTAR

### **O que é um CTe Complementar?**

Um **CTe Complementar** é um documento fiscal que complementa informações ou valores de um CTe original, sem substituí-lo. Exemplos comuns:

- **Reentrega**: Cobrança adicional por nova tentativa de entrega
- **Taxa de Agendamento**: Valor extra por agendamento especial
- **Armazenagem**: Cobrança por período em CD
- **Despacho Adicional**: Taxas extras não previstas no frete original

### **Estrutura no XML**

```xml
<tpCTe>1</tpCTe>  <!-- Tipo: 1 = COMPLEMENTAR -->

<infCteComp>
    <chCTe>35251007797011000193570010002056321594520703</chCTe>  <!-- CTe Original -->
</infCteComp>

<xObs>REFERENTE A REENTREGA</xObs>  <!-- Motivo -->
```

### **Tipos de CTe**

| Código | Descrição | Uso |
|--------|-----------|-----|
| `0` | Normal | Frete padrão |
| `1` | Complementar | Despesas extras |
| `2` | Anulação | Cancelamento |
| `3` | Substituto | Substituição |

---

## 🗄️ MODELO DE DADOS

### **Novos Campos em `ConhecimentoTransporte`**

```python
# Tipo do CTe
tipo_cte = db.Column(db.String(1), default='0', index=True)

# Se for complementar, armazena referência ao CTe original
cte_complementa_chave = db.Column(db.String(44), index=True)  # Chave do CTe original
cte_complementa_id = db.Column(db.Integer, ForeignKey('conhecimento_transporte.id'), index=True)

# Motivo do complemento
motivo_complemento = db.Column(db.Text)

# Relacionamento self-referencial
cte_original = db.relationship('ConhecimentoTransporte', ...)
```

### **Relacionamentos**

```
CTe Original (205632)
    ↓
    ├─ CTe Complementar 1 (207289) - Reentrega
    ├─ CTe Complementar 2 (207350) - Armazenagem
    └─ CTe Complementar 3 (207451) - Taxa Extra
```

---

## 🔄 FLUXO DE PROCESSAMENTO

### **1. Importação do CTe**

```python
# app/odoo/services/cte_service.py

# Extrai XML do Odoo
xml_content = base64.b64decode(cte_data['l10n_br_xml_dfe']).decode('utf-8')

# Parseia e identifica tipo
info_comp = extrair_info_complementar(xml_content)

if info_comp:
    tipo_cte = '1'  # Complementar
    cte_complementa_chave = info_comp['chave_cte_original']
    motivo_complemento = info_comp['motivo']

    # Busca CTe original no banco
    cte_original = ConhecimentoTransporte.query.filter_by(
        chave_acesso=cte_complementa_chave
    ).first()

    if cte_original:
        cte_complementa_id = cte_original.id
```

### **2. Exibição na Interface**

```html
<!-- Lista de CTes -->
<td>
    {% if cte.tipo_cte == '1' %}
    <span class="badge bg-warning text-dark">
        <i class="fas fa-plus-circle"></i> Complementar
    </span>
    {% if cte.cte_original %}
    <br><small>Ref: {{ cte.cte_original.numero_cte }}</small>
    {% endif %}
    {% endif %}
</td>
```

### **3. Vinculação com Despesas Extras** ✅

**Processo Manual (usuário decide):**

1. Usuário acessa tela de **Despesas Extras**
2. Sistema sugere CTes complementares não vinculados (sugestão automática por prioridades em `cte_routes.py:272-288`)
3. Usuário escolhe vincular ou não, via `vincular_cte_despesa.html`
4. Similar ao processo atual de vinculação de CTe → Frete

**Arquivos envolvidos:**

- `app/fretes/services/despesa_cte_service.py` - Service de vinculação CTe Complementar ↔ Despesa Extra (sugestão por 3 prioridades + lançamento Odoo)
- `app/fretes/cte_routes.py` - Sugestão automática de despesas para CTe Complementar (linhas 272-288)
- `app/templates/fretes/vincular_cte_despesa.html` - Interface de sugestão/vinculação
- `app/fretes/models.py` - `DespesaExtra.despesa_cte_id` (FK para `conhecimento_transporte.id`)

---

## 🛠️ MIGRATION SQL

### **Executar Localmente (Python)**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source venv/bin/activate
python migrations/add_cte_complementar_fields.py
```

### **Executar no Render (Shell SQL)**

```sql
-- Copiar e colar o conteúdo de:
migrations/add_cte_complementar_fields.sql
```

---

## 📊 EXEMPLO PRÁTICO

### **Cenário Real**

```
CTe Original: 205632
- Valor: R$ 5.000,00
- NFs: 141768, 141769
- Serviço: Transporte SP → BA

CTe Complementar: 207289
- Valor: R$ 748,88
- Referência: CTe 205632
- Motivo: "REFERENTE A REENTREGA"
```

### **Como Processar**

1. **CTe Original** → Vincula ao **Frete** (custo de transporte)
2. **CTe Complementar** → Vincula a **Despesa Extra** (custo adicional)

### **Consulta SQL para Ver Relacionamento**

```sql
SELECT
    c1.numero_cte AS cte_original,
    c1.valor_total AS valor_original,
    c2.numero_cte AS cte_complementar,
    c2.valor_total AS valor_complementar,
    c2.motivo_complemento
FROM conhecimento_transporte c1
LEFT JOIN conhecimento_transporte c2 ON c2.cte_complementa_id = c1.id
WHERE c2.tipo_cte = '1'
ORDER BY c1.numero_cte, c2.numero_cte;
```

---

## 🔍 QUERIES ÚTEIS

### **Listar CTes Complementares**

```sql
SELECT
    numero_cte,
    valor_total,
    cte_complementa_chave,
    motivo_complemento,
    nome_emitente
FROM conhecimento_transporte
WHERE tipo_cte = '1'
ORDER BY data_emissao DESC;
```

### **CTes Complementares Não Vinculados**

```sql
SELECT
    c.numero_cte,
    c.valor_total,
    c.motivo_complemento,
    co.numero_cte AS cte_original_numero
FROM conhecimento_transporte c
LEFT JOIN conhecimento_transporte co ON co.id = c.cte_complementa_id
WHERE c.tipo_cte = '1'
AND c.frete_id IS NULL  -- Não vinculado a frete
AND NOT EXISTS (
    SELECT 1 FROM despesas_extras de WHERE de.despesa_cte_id = c.id
);  -- E também não vinculado a despesa extra
```

### **Total de Valores Complementares por CTe Original**

```sql
SELECT
    co.numero_cte AS cte_original,
    co.valor_total AS valor_original,
    COUNT(c.id) AS qtd_complementares,
    SUM(c.valor_total) AS total_complementares,
    co.valor_total + COALESCE(SUM(c.valor_total), 0) AS valor_total_final
FROM conhecimento_transporte co
LEFT JOIN conhecimento_transporte c ON c.cte_complementa_id = co.id AND c.tipo_cte = '1'
WHERE co.tipo_cte = '0'  -- Apenas CTes normais
GROUP BY co.id, co.numero_cte, co.valor_total
HAVING COUNT(c.id) > 0
ORDER BY total_complementares DESC;
```

---

## 🎨 INTERFACE

### **Lista de CTes**

```
┌─────────────┬──────────────┬─────────────┬──────────┐
│ CTe         │ Tipo         │ Valor       │ Status   │
├─────────────┼──────────────┼─────────────┼──────────┤
│ 205632      │ [Normal]     │ R$ 5.000,00 │ Concluído│
│ 207289      │ [Compl.]     │ R$ 748,88   │ PO       │
│             │ Ref: 205632  │             │          │
└─────────────┴──────────────┴─────────────┴──────────┘
```

### **Detalhes do CTe Complementar**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CTe Complementar #207289
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 Complementa CTe: #205632
   Transportadora: CAZAN TRANSPORTES
   Valor Original: R$ 5.000,00

💰 Valor Complementar: R$ 748,88
📝 Motivo: REFERENTE A REENTREGA

⚠️ Este CTe NÃO deve ser vinculado ao frete!
   Vincule a Despesas Extras →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ✅ PRÓXIMOS PASSOS

### **Fase 1: Implementado ✅**

- [x] Criar campos no modelo
- [x] Parser de XML
- [x] Integração com importação
- [x] Migration SQL
- [x] Exibição na interface

### **Fase 2: Implementado ✅**

- [x] Integração com Despesas Extras (`app/fretes/services/despesa_cte_service.py`)
- [x] Sugestão de vinculação automática por prioridades (`app/fretes/cte_routes.py:272-288`)
- [x] Interface de vinculação (`app/templates/fretes/vincular_cte_despesa.html`)
- [ ] Validações (não permitir vincular complementar ao frete)
- [ ] Relatório de CTes complementares

### **Fase 3: Futuro 💡**

- [ ] Dashboard com métricas de complementares
- [ ] Alertas para complementares não vinculados
- [ ] Vinculação automática inteligente (opcional)

---

## 📚 REFERÊNCIAS

- **Manual CTe SEFAZ**: [http://www.cte.fazenda.gov.br/](http://www.cte.fazenda.gov.br/)
- **Modelo**: [app/fretes/models.py:699](app/fretes/models.py#L699) (`tipo_cte`) e [:702-706](app/fretes/models.py#L702-L706) (`cte_complementa_chave` / `cte_complementa_id` / `motivo_complemento`)
- **Parser**: [app/odoo/utils/cte_xml_parser.py](app/odoo/utils/cte_xml_parser.py)
- **Serviço**: [app/odoo/services/cte_service.py:399](app/odoo/services/cte_service.py#L399)
- **Vinculação Despesa Extra**: [app/fretes/services/despesa_cte_service.py](app/fretes/services/despesa_cte_service.py)
- **Interface**: [app/templates/fretes/ctes/index.html:196](app/templates/fretes/ctes/index.html#L196)

---

## 🆘 TROUBLESHOOTING

### **CTe complementar não está sendo identificado**

1. Verificar se o XML foi salvo corretamente
2. Conferir namespace do XML (pode variar por transportadora)
3. Testar parser manualmente:

```python
from app.odoo.utils.cte_xml_parser import extrair_info_complementar

with open('caminho/do/xml.xml', 'r') as f:
    xml_content = f.read()

info = extrair_info_complementar(xml_content)
print(info)
```

### **CTe original não é encontrado**

- Importar CTe original primeiro antes do complementar
- Verificar se chave de acesso está correta
- Pode haver atraso: importar novamente depois

### **Relacionamento não aparece na interface**

- Verificar se migration foi executada
- Fazer commit do banco após importação
- Limpar cache do template (Ctrl+F5)

---

**FIM DA DOCUMENTAÇÃO**
