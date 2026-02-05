# Grupos Empresariais

## Mapeamento Completo

| Grupo | Prefixos CNPJ | Observacoes |
|-------|---------------|-------------|
| **atacadao** | 93.209.76, 75.315.33, 00.063.96 | Carrefour Atacadao (multiplos CNPJs raiz) |
| **assai** | 06.057.22 | Assai Atacadista |
| **tenda** | 01.157.55 | Tenda Atacado |

## Formato CNPJ

Os prefixos sao os **8 primeiros digitos** formatados: `XX.XXX.XX`

### Para buscar no banco:

```sql
-- Atacadao (3 prefixos)
WHERE cnpj_cliente LIKE '93.209.76%'
   OR cnpj_cliente LIKE '75.315.33%'
   OR cnpj_cliente LIKE '00.063.96%'

-- Assai (1 prefixo)
WHERE cnpj_cliente LIKE '06.057.22%'

-- Tenda (1 prefixo)
WHERE cnpj_cliente LIKE '01.157.55%'
```

## Como Identificar Loja

O identificador da loja geralmente esta no campo `raz_social_red`:

| Exemplo raz_social_red | Identificador |
|------------------------|---------------|
| "ATACADAO 183" | loja 183 |
| "ATACADAO JACAREI" | buscar por "jacarei" |
| "ASSAI GUARULHOS" | buscar por "guarulhos" |
| "ASSAI LOJA 045" | loja 045 |

## Tabelas onde Grupos Aparecem

| Tabela | Campo CNPJ | Campo Nome |
|--------|------------|------------|
| CarteiraPrincipal | cnpj_cpf | raz_social_red |
| Separacao | cnpj_cpf | raz_social_red |
| EmbarqueItem | cnpj | nome_cliente |
| Frete | cnpj_cpf | nome_cliente |
| EntregasMonitoradas | cnpj_cliente | cliente |
| NFDevolucao | cnpj_emitente | nome_emitente |
| FaturamentoProduto | cnpj | cliente |

## Expansao Futura

Para adicionar novos grupos, atualizar:

1. `GRUPOS_EMPRESARIAIS` em `resolver_grupo.py`
2. Esta documentacao
3. Testar com `resolver_grupo.py --grupo novo_grupo`
