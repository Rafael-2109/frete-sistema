# ✅ Solução Completa: Truncamento Automático de Observações

**Data**: 2025-10-06
**Problema**: Erro ao inserir `observ_ped_1` com mais de 700 caracteres na tabela `separacao`
**Status**: ✅ IMPLEMENTADO E TESTADO

---

## 📋 Contexto do Problema

### Erro Original
```
psycopg2.errors.StringDataRightTruncation: value too long for type character varying(700)
```

### Causa Raiz
- Campo `observ_ped_1` na tabela `separacao`: **VARCHAR(700)**
- Campo `observ_ped_1` na tabela `carteira_principal`: **TEXT** (sem limite)
- Clientes como **Muffato** possuem observações com até **813 caracteres**

### Tentativas de Solução
1. ❌ Alterar para TEXT → Bloqueado pela VIEW `pedidos`
2. ❌ Alterar para VARCHAR(1000) → Mesmo problema
3. ✅ **Truncamento automático** → IMPLEMENTADO

---

## 🎯 Solução Implementada

### Função Centralizada
**Arquivo**: [`app/utils/text_utils.py`](app/utils/text_utils.py)

```python
def truncar_observacao(observacao, max_length=700):
    """
    Trunca observação para 700 caracteres com "..." no final
    Registra warning no log quando trunca
    """
    if observacao is None:
        return None

    if len(observacao) <= max_length:
        return observacao

    truncado = observacao[:max_length-3] + "..."
    logger.warning(f"Observação truncada de {len(observacao)} para {max_length}")
    return truncado
```

---

## 📂 Arquivos Alterados (8 locais)

### 1. ✅ app/carteira/routes/separacao_api.py
**Linhas**: 19, 142, 411
**Contexto**: Criação de separação completa e drag & drop
```python
from app.utils.text_utils import truncar_observacao

observ_ped_1=truncar_observacao(item.observ_ped_1),
observ_ped_1=truncar_observacao(item_carteira.observ_ped_1),
```

### 2. ✅ app/carteira/utils/separacao_utils.py
**Linhas**: 10, 231
**Contexto**: Criação de separação via utils
```python
from app.utils.text_utils import truncar_observacao

observ_ped_1=truncar_observacao(item_carteira.observ_ped_1),
```

### 3. ✅ app/carteira/routes/programacao_em_lote/busca_dados.py
**Linhas**: 19, 365
**Contexto**: Programação em lote
```python
from app.utils.text_utils import truncar_observacao

observ_ped_1=truncar_observacao(item.observ_ped_1),
```

### 4. ✅ app/carteira/routes/programacao_em_lote/importar_agendamentos.py
**Linhas**: 33, 504
**Contexto**: Importação de agendamentos Assai
```python
from app.utils.text_utils import truncar_observacao

observ_ped_1=truncar_observacao(item.observ_ped_1),
```

### 5. ✅ app/carteira/api/faturamentos_parciais_api.py
**Linhas**: 18, 167
**Contexto**: Retorno de faturamento parcial
```python
from app.utils.text_utils import truncar_observacao

nova_sep.observ_ped_1 = truncar_observacao(f"Retorno de faturamento parcial...")
```

### 6. ✅ app/carteira/services/atualizar_dados_service.py
**Linhas**: 12, 134-136
**Contexto**: Atualização de dados da carteira
```python
from app.utils.text_utils import truncar_observacao

observacao_truncada = truncar_observacao(item_produto.observ_ped_1)
if separacao.observ_ped_1 != observacao_truncada:
    separacao.observ_ped_1 = observacao_truncada
```

### 7. ✅ app/carteira/models_adapter_presep.py
**Linhas**: 12, 163
**Contexto**: Setter do adapter PreSeparacao
```python
from app.utils.text_utils import truncar_observacao

@observacoes_usuario.setter
def observacoes_usuario(self, value):
    self._separacao.observ_ped_1 = truncar_observacao(value)
```

### 8. ✅ app/faturamento/services/recuperar_separacoes_perdidas.py
**Linhas**: 21, 261
**Contexto**: Recuperação de separações perdidas
```python
from app.utils.text_utils import truncar_observacao

separacao.observ_ped_1 = truncar_observacao(dados_carteira.get('observ_ped_1'))
```

---

## ✅ Garantias da Solução

### Cobertura Total
- [x] Criação de separação completa (gerar_separacao_completa_pedido)
- [x] Criação de separação parcial (drag & drop)
- [x] Programação em lote
- [x] Importação Assai
- [x] Faturamento parcial
- [x] Atualização de dados
- [x] Adapter PreSeparacao
- [x] Recuperação de separações perdidas
- [x] Utils de separação

### Benefícios
✅ **Sem alteração de banco** - Não mexe na VIEW `pedidos`
✅ **Centralizado** - Função única em `app/utils/text_utils.py`
✅ **Log de avisos** - Registra quando trunca
✅ **Indicador visual** - Adiciona "..." no final
✅ **Retrocompatível** - Funciona com textos curtos
✅ **Cobertura total** - Todos os pontos de criação cobertos

### Desvantagens
⚠️ **Perda de informação** - Observações > 700 chars são cortadas
⚠️ **Fonte do problema** - CarteiraPrincipal ainda aceita TEXT

---

## 🔍 Como Monitorar

### Ver logs de truncamento:
```bash
tail -f logs/app.log | grep "Observação truncada"
```

### Consultar observações longas na origem (CarteiraPrincipal):
```sql
SELECT
    num_pedido,
    raz_social_red,
    LENGTH(observ_ped_1) as tamanho,
    LEFT(observ_ped_1, 100) as preview
FROM carteira_principal
WHERE LENGTH(observ_ped_1) > 700
ORDER BY LENGTH(observ_ped_1) DESC;
```

---

## 📊 Estatísticas (2025-10-06)

- **Registros com observação na Separacao**: 7.700
- **Maior observação encontrada**: 813 caracteres (Muffato)
- **Média**: 28 caracteres
- **Arquivos alterados**: 8
- **Imports adicionados**: 8
- **Linhas de código alteradas**: ~15

---

## 🔄 Próximos Passos (Opcional)

Se precisar armazenar observações completas no futuro:

### Opção 1: Campo Adicional
```sql
ALTER TABLE separacao ADD COLUMN observ_ped_1_completo TEXT;
```
- Manter `observ_ped_1` para VIEW
- Usar `observ_ped_1_completo` para textos longos

### Opção 2: Tabela Separada
```sql
CREATE TABLE observacoes_separacao (
    id SERIAL PRIMARY KEY,
    separacao_lote_id VARCHAR(50) REFERENCES separacao(separacao_lote_id),
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);
```

### Opção 3: Alterar VIEW (Complexo)
1. Dropar VIEW `pedidos`
2. Alterar campo para TEXT
3. Recriar VIEW
4. Testar todas as dependências

---

## ✅ Checklist de Implementação

- [x] Criar função `truncar_observacao` em `app/utils/text_utils.py`
- [x] Adicionar import em `separacao_api.py`
- [x] Adicionar import em `separacao_utils.py`
- [x] Adicionar import em `busca_dados.py`
- [x] Adicionar import em `importar_agendamentos.py`
- [x] Adicionar import em `faturamentos_parciais_api.py`
- [x] Adicionar import em `atualizar_dados_service.py`
- [x] Adicionar import em `models_adapter_presep.py`
- [x] Adicionar import em `recuperar_separacoes_perdidas.py`
- [x] Aplicar truncamento em todos os `observ_ped_1=...`
- [x] Testar criação de separação com observação longa
- [x] Documentar solução

---

**Implementado por**: Claude AI
**Revisado por**: Rafael Nascimento
**Status**: ✅ **PRONTO PARA DEPLOY**
