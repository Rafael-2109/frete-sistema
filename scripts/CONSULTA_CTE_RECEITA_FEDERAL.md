# 🔍 Consulta Automatizada de CTe na Receita Federal

## 📋 RESUMO

Este documento explica como automatizar a consulta de CTe (Conhecimento de Transporte Eletrônico) na Receita Federal para verificar se está autorizado.

---

## 🎯 OBJETIVO

Verificar automaticamente se um CTe está autorizado consultando diretamente o webservice da SEFAZ, sem necessidade de CAPTCHA ou interação manual.

---

## 📊 EXEMPLO DE USO

### Chaves Testadas:
1. `35251044687723000186570010000026811000061267`
2. `35251144687723000186570010000027121000061927`

**Estrutura da Chave (44 dígitos):**
```
35      25  10  44687723000186  57  001  00000268  1  1000061267
^^      ^^  ^^  ^^^^^^^^^^^^^^  ^^  ^^^  ^^^^^^^^  ^  ^^^^^^^^^^
UF      Ano Mês CNPJ Emitente   Mod Sér  Número    T  Cód+DV
(SP)    (2025/Outubro)          (CTe)
```

---

## 🔧 OPÇÕES DE IMPLEMENTAÇÃO

### **Opção 1: Webservice SOAP da SEFAZ (Gratuito)**

**Vantagens:**
- ✅ Gratuito
- ✅ Oficial da Receita Federal
- ✅ Sem CAPTCHA
- ✅ Sem limites de consultas

**Desvantagens:**
- ⚠️ URL diferente para cada UF
- ⚠️ Pode ter instabilidade
- ⚠️ Requer parsing de XML SOAP

**Script Criado:** `scripts/consultar_cte_receita_federal.py`

---

### **Opção 2: API de Terceiros (NF-e.io, Infosimples)**

**Vantagens:**
- ✅ Mais estável
- ✅ API REST simples
- ✅ JSON como retorno
- ✅ Suporte técnico

**Desvantagens:**
- ❌ Pago (a partir de R$ 0,20 por consulta)
- ❌ Requer cadastro

**Exemplo (NF-e.io):**
```python
import requests

def consultar_cte_nfeio(chave_acesso: str, api_key: str):
    url = f"https://api.nfe.io/v1/cte/{chave_acesso}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    return response.json()
```

---

## 📝 SCRIPT CRIADO

### Arquivo: `scripts/consultar_cte_receita_federal.py`

**Funcionalidades:**
1. ✅ Extrai UF da chave automaticamente
2. ✅ Seleciona URL do webservice correto por UF
3. ✅ Monta envelope SOAP automaticamente
4. ✅ Faz requisição HTTP
5. ✅ Parse do XML de resposta
6. ✅ Retorna status de autorização

**Códigos de Status:**
- `100` = ✅ **Autorizado**
- `217` = ⚠️ CTe não encontrado
- `301` = ❌ Uso irregular
- `999` = ❌ Erro no processamento

---

## 🚀 COMO EXECUTAR

### 1. Em Produção (Render):

```bash
source .venv/bin/activate
python scripts/consultar_cte_receita_federal.py
```

### 2. Consultar chave específica:

```python
from scripts.consultar_cte_receita_federal import consultar_cte_receita_federal

chave = '35251044687723000186570010000026811000061267'
resultado = consultar_cte_receita_federal(chave)

print(f"Autorizado: {resultado['autorizado']}")
print(f"Mensagem: {resultado['mensagem']}")
```

---

## 📦 INTEGRAÇÃO COM O SISTEMA

### Adicionar validação automática de CTe:

**Arquivo sugerido:** `app/fretes/services/validacao_cte_service.py`

```python
from typing import Dict
from app.fretes.models import ConhecimentoTransporte
from scripts.consultar_cte_receita_federal import consultar_cte_receita_federal

def validar_cte_na_receita(cte_id: int) -> Dict:
    """
    Valida CTe na Receita Federal e atualiza status no banco

    Args:
        cte_id: ID do ConhecimentoTransporte

    Returns:
        Resultado da validação
    """
    cte = ConhecimentoTransporte.query.get(cte_id)

    if not cte or not cte.chave_acesso:
        return {'sucesso': False, 'erro': 'CTe não encontrado ou sem chave'}

    # Consultar na Receita
    resultado = consultar_cte_receita_federal(cte.chave_acesso)

    if resultado['sucesso'] and resultado['autorizado']:
        # Atualizar status no banco
        cte.validado_receita = True
        cte.data_validacao_receita = datetime.now()
        cte.protocolo_validacao = resultado.get('numero_protocolo')
        db.session.commit()

    return resultado
```

---

## 🗺️ MAPEAMENTO DE UFs

O script já mapeia automaticamente todas as UFs:

| UF | Código | Webservice |
|----|--------|-----------|
| SP | 35 | SEFAZ-SP |
| RJ | 33 | SVRS |
| PR | 41 | SEFAZ-PR |
| RS | 43 | SVRS |
| MG | 31 | SEFAZ-MG |
| BA | 29 | SVRS |
| ... | ... | ... |

**SVRS**: Sefaz Virtual do Rio Grande do Sul (atende várias UFs)

---

## 🔑 EXEMPLO DE RESPOSTA

### CTe Autorizado:
```json
{
  "sucesso": true,
  "chave": "35251044687723000186570010000026811000061267",
  "uf_codigo": "35",
  "codigo_status": "100",
  "mensagem": "Autorizado o uso do CT-e",
  "autorizado": true,
  "numero_protocolo": "335250000123456",
  "data_autorizacao": "2025-10-15T14:30:00-03:00",
  "consultado_em": "2025-11-17T13:45:00"
}
```

### CTe Não Encontrado:
```json
{
  "sucesso": true,
  "chave": "35251044687723000186570010000026811000061267",
  "uf_codigo": "35",
  "codigo_status": "217",
  "mensagem": "CTe não consta na base de dados da SEFAZ",
  "autorizado": false,
  "consultado_em": "2025-11-17T13:45:00"
}
```

---

## ⚠️ LIMITAÇÕES

1. **Ambiente Local**: O script falhou localmente por falta de acesso à internet (DNS)
2. **Firewall**: Alguns firewalls podem bloquear conexões SOAP
3. **Rate Limit**: SEFAZ pode ter limite de requisições (não documentado oficialmente)
4. **Instabilidade**: Webservices da SEFAZ podem ficar offline

---

## 🎯 PRÓXIMOS PASSOS

### 1. **Testar em Produção (Render)**
Execute o script no servidor Render onde há acesso à internet

### 2. **Adicionar ao Sistema**
Integrar a validação automática:
- Após importar CTe do Odoo
- Botão "Validar na Receita" na tela de CTe
- Validação em massa (batch)

### 3. **Adicionar Campos no Banco**
```sql
ALTER TABLE conhecimento_transporte
ADD COLUMN validado_receita BOOLEAN DEFAULT FALSE,
ADD COLUMN data_validacao_receita TIMESTAMP,
ADD COLUMN protocolo_validacao VARCHAR(50);
```

### 4. **Criar Rota no Sistema**
```python
@cte_bp.route('/<int:cte_id>/validar-receita', methods=['POST'])
def validar_cte_receita(cte_id):
    resultado = validar_cte_na_receita(cte_id)
    if resultado['sucesso'] and resultado['autorizado']:
        flash('✅ CTe validado com sucesso na Receita Federal!', 'success')
    else:
        flash(f'❌ CTe não autorizado: {resultado.get("mensagem")}', 'error')
    return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))
```

---

## 📞 SUPORTE

**Documentação SEFAZ CTe:**
- Portal: https://www.cte.fazenda.gov.br/
- Webservices: https://www.cte.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=/fLbHSZ8tv0=

**APIs Comerciais (alternativas):**
- NF-e.io: https://nfe.io/docs
- Infosimples: https://infosimples.com/api
- Webmania: https://webmaniabr.com/docs/rest-api-cte/
