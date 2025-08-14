# 📦 Lógica de Endereço de Entrega para REDESPACHO

## Visão Geral
Este documento descreve a implementação da lógica especial para mapeamento de endereços de entrega quando o incoterm indica REDESPACHO.

## 🎯 Objetivo
Quando um pedido tem incoterm `RED` ou `[RED] REDESPACHO`, o sistema deve usar os dados do **carrier_id** (transportadora) como endereço de entrega, ao invés do **partner_shipping_id** (cliente).

## 📋 Regras de Negócio

### Quando usar carrier_id:
- ✅ `incoterm = "RED"`
- ✅ `incoterm = "[RED] REDESPACHO"`
- ✅ Qualquer valor de incoterm que contenha `"RED"` ou `"REDESPACHO"`

### Quando usar partner_shipping_id (padrão):
- ✅ Todos os outros casos
- ✅ Quando incoterm está vazio/nulo
- ✅ Incoterms normais como CIF, FOB, etc.

## 🔄 Fluxo da Lógica

```python
1. Para cada linha de pedido do Odoo:
   ├── Verificar o valor do campo incoterm
   ├── Se incoterm = RED ou contém REDESPACHO:
   │   └── Usar carrier_id para todos os campos de endereço
   └── Senão:
       └── Usar partner_shipping_id (comportamento padrão)
```

## 📍 Campos de Endereço Afetados

Os seguintes campos da CarteiraPrincipal são ajustados dinamicamente:

| Campo CarteiraPrincipal | Origem Normal | Origem REDESPACHO |
|------------------------|---------------|-------------------|
| cnpj_endereco_ent | partner_shipping_id/l10n_br_cnpj | carrier_id/l10n_br_cnpj |
| empresa_endereco_ent | partner_shipping_id/name | carrier_id/name |
| cep_endereco_ent | partner_shipping_id/zip | carrier_id/zip |
| nome_cidade | partner_shipping_id/l10n_br_municipio_id/name | carrier_id/l10n_br_municipio_id/name |
| cod_uf | partner_shipping_id/l10n_br_municipio_id | carrier_id/l10n_br_municipio_id |
| bairro_endereco_ent | partner_shipping_id/l10n_br_endereco_bairro | carrier_id/l10n_br_endereco_bairro |
| rua_endereco_ent | partner_shipping_id/street | carrier_id/street |
| endereco_ent | partner_shipping_id/l10n_br_endereco_numero | carrier_id/l10n_br_endereco_numero |
| telefone_endereco_ent | partner_shipping_id/phone | carrier_id/phone |

## 🛠️ Implementação

### Arquivo Principal
`app/odoo/utils/carteira_mapper.py`

### Métodos Principais

#### 1. `_deve_usar_carrier_para_endereco(incoterm)`
Determina se deve usar carrier_id baseado no valor do incoterm.

#### 2. `_ajustar_campo_endereco_por_incoterm(campo_carteira, campo_odoo, usar_carrier)`
Ajusta o caminho do campo Odoo substituindo `partner_shipping_id` por `carrier_id` quando necessário.

#### 3. `validar_dados_carrier(linha_odoo)`
Valida se os dados do carrier estão disponíveis e completos quando necessários.

## 📊 Exemplos de Uso

### Exemplo 1: Pedido Normal (CIF)
```python
{
    "order_id": {
        "incoterm": "CIF",
        "partner_shipping_id": {...},  # ← Será usado
        "carrier_id": {...}
    }
}
# Resultado: Endereço do cliente (partner_shipping_id)
```

### Exemplo 2: Pedido com REDESPACHO
```python
{
    "order_id": {
        "incoterm": "RED",
        "partner_shipping_id": {...},
        "carrier_id": {...}  # ← Será usado
    }
}
# Resultado: Endereço da transportadora (carrier_id)
```

## 🧪 Teste

Execute o script de teste para validar a lógica:

```bash
python testar_mapeamento_redespacho.py
```

Este script testa 4 cenários:
1. Incoterm normal (CIF) - deve usar partner_shipping_id
2. Incoterm = RED - deve usar carrier_id
3. Incoterm = [RED] REDESPACHO - deve usar carrier_id
4. Sem incoterm - deve usar partner_shipping_id

## 📝 Logs e Debug

O sistema gera logs informativos para facilitar o debug:

- `✅ Incoterm 'RED' identificado como REDESPACHO` - Quando detecta incoterm de redespacho
- `🔄 Campo X: mudando de partner_shipping_id para carrier_id` - Para cada campo ajustado
- `⚠️ Pedido X com incoterm 'RED' mas sem carrier_id` - Quando falta carrier_id

## ⚠️ Considerações Importantes

1. **Validação de Dados**: Sempre valide se carrier_id existe e tem os campos necessários antes de usá-lo
2. **Fallback**: Se carrier_id não estiver disponível, considere usar partner_shipping_id como fallback
3. **Performance**: A verificação é feita uma vez por pedido, não por campo
4. **Múltiplas Queries**: Campos que requerem múltiplas queries funcionam com ambas as origens

## 🔮 Melhorias Futuras

- [ ] Adicionar configuração para definir quais incoterms usam carrier_id
- [ ] Implementar fallback automático quando carrier_id estiver incompleto
- [ ] Cache dos resultados de validação para melhor performance
- [ ] Interface administrativa para configurar regras de incoterm

## 📅 Histórico de Mudanças

| Data | Versão | Descrição |
|------|---------|-----------|
| 2025-01-14 | 1.0.0 | Implementação inicial da lógica RED/REDESPACHO |

## 👥 Contato

Para dúvidas ou sugestões sobre esta funcionalidade, entre em contato com a equipe de desenvolvimento.