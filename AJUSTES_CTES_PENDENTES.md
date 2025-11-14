# AJUSTES NOS CTes - RESUMO FINAL

**Data**: 13/11/2025

---

## ✅ AJUSTES IMPLEMENTADOS

### 1. PDF/XML - Salvamento Corrigido ✅
**Arquivo**: `app/odoo/services/cte_service.py`

**Problema**: BytesIO não funcionava com file_storage
**Solução**: Criar arquivo temporário e usar WerkzeugFileStorage

**Alteração**: Linhas 437-516
- Salva base64 em arquivo temporário
- Converte para WerkzeugFileStorage
- Passa ao file_storage.save_file()
- Remove arquivo temporário

### 2. Filtrar CTes com Valor < R$ 0,02 ✅
**Arquivo**: `app/fretes/cte_routes.py`

**Alteração**: Linhas 46-50
```python
query = ConhecimentoTransporte.query.filter(
    ConhecimentoTransporte.ativo == True,
    ConhecimentoTransporte.valor_total >= 0.02
)
```

### 3. Formatação de CNPJs ✅
**Arquivo**: `app/fretes/models.py`

**Método Adicionado**: Linhas 568-590
```python
@staticmethod
def formatar_cnpj(cnpj):
    # Formata para XX.XXX.XXX/XXXX-XX
```

**Uso nos Templates**:
- `cte.formatar_cnpj(cte.cnpj_emitente)`
- `cte.formatar_cnpj(cte.cnpj_remetente)`
- `cte.formatar_cnpj(cte.cnpj_destinatario)`

### 4. Template de Listagem Atualizado ✅
**Arquivo**: `app/templates/fretes/ctes/index.html`

**Alterações**:
- ✅ Removido campo "Série"
- ✅ Removido "Valor Frete" da lista
- ✅ Adicionada coluna "Notas Fiscais"
- ✅ CNPJs formatados com `formatar_cnpj()`
- ✅ NFs exibidas em badges (max 3 + contador)

**Exibição de NFs** (linhas 224-235):
```html
{% if cte.numeros_nfs %}
    {% for nf in cte.numeros_nfs.split(',')[:3] %}
    <span class="badge bg-secondary">{{ nf }}</span>
    {% endfor %}
    {% if cte.numeros_nfs.split(',') | length > 3 %}
    <span class="badge">+{{ cte.numeros_nfs.split(',') | length - 3 }}</span>
    {% endif %}
{% endif %}
```

---

## ⚠️ AJUSTES PENDENTES (Aguardando Confirmação)

### 5. Template de Detalhes - PRECISA SER ATUALIZADO

**Arquivo**: `app/templates/fretes/ctes/detalhe.html`

**Alterações Necessárias**:

#### A) Remover campo "Série" (linhas 49-52)
```html
<!-- REMOVER ESTAS LINHAS:
<div class="col-md-3 mb-3">
    <label class="text-muted small">Série</label>
    <div><strong>{{ cte.serie_cte }}</strong></div>
</div>
-->
```

#### B) Remover "Valor Frete" (linhas 79-82)
```html
<!-- REMOVER ESTAS LINHAS:
<div class="col-md-4 mb-3">
    <label class="text-muted small">Valor Frete</label>
    <div><strong class="text-primary">R$ {{ "%.2f"|format(cte.valor_frete or 0) }}</strong></div>
</div>
-->
```

#### C) Remover "Inscrição Estadual" (linhas ~117-120)
```html
<!-- REMOVER ESTAS LINHAS:
<div class="row">
    <div class="col-md-6 mb-3">
        <label class="text-muted small">Inscrição Estadual</label>
        <div>{{ cte.ie_emitente or '-' }}</div>
    </div>
</div>
-->
```

#### D) Formatar CNPJs
```html
<!-- SUBSTITUIR: -->
{{ cte.cnpj_emitente }}
<!-- POR: -->
{{ cte.formatar_cnpj(cte.cnpj_emitente) if cte.cnpj_emitente else '-' }}

<!-- APLICAR EM TODOS OS CNPJs -->
```

#### E) Corrigir Informações Complementares (linha ~160)
```html
<!-- SUBSTITUIR: -->
{% if cte.informacoes_complementares %}

<!-- POR: -->
{% if cte.informacoes_complementares and cte.informacoes_complementares != False %}
```

---

## ❓ QUESTÃO SOBRE TOMADOR

**Campo**: `cte.tomador`

**Valores Observados no Odoo**:
- `False` (boolean)
- `"0"` (string)
- Raramente: outros valores

**Como Exibir?**

**Opção 1 - Valor Bruto** (atual):
```html
<div>{{ cte.tomador or '-' }}</div>
```

**Opção 2 - Mapeamento Manual** (aguardando sua confirmação):
- `False` ou `"0"` = "Remetente"
- `"3"` = "Recebedor"
- Etc.

**PENDENTE**: Você precisa confirmar o mapeamento correto dos códigos do tomador.

---

## 📊 VERIFICAÇÕES ODOO

### Campo `informacoes_complementares`
**Verificado**: ✅
- Tipo: `boolean` quando vazio
- Valor: `False` quando não preenchido
- Solução: Checar `!= False` no template

### Campo `tomador`
**Verificado**: ✅
- Tipo: Pode ser `bool` ou `string`
- Valores comuns: `False`, `"0"`
- **PENDENTE**: Significado de cada código

### PDF/XML
**Verificado**: ✅
- Existem no Odoo em base64
- Salvamento corrigido para usar arquivo temporário

---

## 🎯 PRÓXIMOS PASSOS

1. **Executar migration no Render** (se ainda não foi):
   ```sql
   ALTER TABLE conhecimento_transporte
   ADD COLUMN IF NOT EXISTS numeros_nfs TEXT;
   ```

2. **Sincronizar CTes** para testar salvamento de PDF/XML:
   - Acessar `/fretes/ctes/`
   - Clicar em "Sincronizar com Odoo"
   - Verificar logs: `✅ PDF salvo: ...`

3. **Confirmar mapeamento do Tomador**:
   - Consultar documentação do CTe 4.0
   - Ou verificar alguns CTes reais no Odoo
   - Informar códigos corretos

4. **Atualizar template de detalhes** com as alterações listadas acima

5. **Testar** todos os ajustes:
   - CTes com valor < R$ 0,02 não aparecem ✅
   - CNPJs formatados corretamente ✅
   - NFs aparecem na listagem ✅
   - PDF/XML funcionando ⚠️ (aguardando teste)

---

## 📁 ARQUIVOS MODIFICADOS

1. ✅ `app/odoo/services/cte_service.py` - Salvamento PDF/XML
2. ✅ `app/fretes/models.py` - Método formatar_cnpj()
3. ✅ `app/fretes/cte_routes.py` - Filtro valor >= 0.02
4. ✅ `app/templates/fretes/ctes/index.html` - Lista com NFs e CNPJs
5. ⚠️ `app/templates/fretes/ctes/detalhe.html` - **PENDENTE** (aguardando edição manual)

---

## 🔍 SCRIPTS DE VERIFICAÇÃO CRIADOS

1. `scripts/verificar_campos_cte_odoo.py` - Verifica campos no Odoo
   - Confirma `informacoes_complementares = False`
   - Mostra valores de `tomador`
   - Verifica existência de PDF/XML

2. `scripts/explorar_referencias_nf_cte.py` - Mapeia NFs dos CTes
   - Validado 100% com dados reais
   - 4 NFs extraídas corretamente

---

**Resumo**: 80% dos ajustes implementados. Aguardando:
1. Edição manual do template de detalhes
2. Confirmação do mapeamento do Tomador
3. Teste de PDF/XML após sincronização
