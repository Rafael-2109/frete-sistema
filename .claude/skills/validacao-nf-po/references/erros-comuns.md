# Erros Comuns na Validacao NF x PO

## Armadilhas Encontradas e Solucoes

---

## ERRO 1: Campo `nfe_infnfe_dest_xnome` NAO Existe no Odoo

**Sintoma**:
```
ValueError: Invalid field 'nfe_infnfe_dest_xnome' on model 'l10n_br_ciel_it_account.dfe'
```

**Causa**: O modelo DFE do Odoo (`l10n_br_ciel_it_account.dfe`) NAO tem o campo `nfe_infnfe_dest_xnome` (razao social do destinatario).

**Campos que EXISTEM**:
- `nfe_infnfe_dest_cnpj` - CNPJ do destinatario (empresa compradora)
- `nfe_infnfe_emit_xnome` - Razao social do EMITENTE (fornecedor)
- `nfe_infnfe_emit_cnpj` - CNPJ do emitente

**Campos que NAO EXISTEM**:
- `nfe_infnfe_dest_xnome` - NAO existe
- `nfe_infnfe_dest_xfant` - NAO existe
- `lines_ids` - NAO existe (usar search em dfe.line com filtro dfe_id)

**Solucao**: Para obter razao social da empresa compradora, buscar via `res.partner` pelo CNPJ, ou usar dado local da tabela `ValidacaoNfPoDfe.razao_empresa_compradora`.

**Confirmacao**: Arquivo `scripts/exploracao_dfe_campos.txt` e `app/devolucao/services/nfd_service.py` (linhas 336, 550) confirmam a inexistencia.

---

## ERRO 2: Preview Chamando Odoo (Deveria Ser 100% Local)

**Sintoma**: Modal "POs Candidatos" demora 3-5s ou falha com erro de conexao Odoo.

**Causa**: O metodo `buscar_preview_pos_candidatos()` estava chamando `_buscar_dfe()` e `_buscar_dfe_lines()` que fazem XML-RPC para o Odoo.

**Regra**: O preview NUNCA deve chamar Odoo. Os dados ja foram importados pela validacao (`validar_dfe()`) e estao nas tabelas locais:
- `ValidacaoNfPoDfe` → cabecalho (numero_nf, cnpjs, razoes, data, valor)
- `MatchNfPoItem` → itens ja convertidos (cod_produto_interno, qtd_nf, preco_nf, fator)
- `PedidoCompras` → POs candidatos (cod_produto, saldo, preco)

**Solucao Correta**:
```python
# ERRADO (chama Odoo):
dfe_data = self._buscar_dfe(odoo_dfe_id)
dfe_lines = self._buscar_dfe_lines(odoo_dfe_id)

# CORRETO (100% local):
validacao = ValidacaoNfPoDfe.query.filter_by(odoo_dfe_id=odoo_dfe_id).first()
itens_match = MatchNfPoItem.query.filter_by(validacao_id=validacao.id).all()
```

---

## ERRO 3: Assinatura Incorreta de _buscar_dfe_lines()

**Sintoma**: `TypeError: _buscar_dfe_lines() takes 2 positional arguments but 3 were given`

**Causa**: O metodo aceita APENAS `odoo_dfe_id` como argumento. Ele busca as linhas via `odoo.search()` com filtro `('dfe_id', '=', odoo_dfe_id)`.

**Assinatura correta**:
```python
def _buscar_dfe_lines(self, odoo_dfe_id: int) -> List[Dict[str, Any]]:
```

**ERRADO**: `self._buscar_dfe_lines(odoo_dfe_id, line_ids)` ← 2 argumentos
**CORRETO**: `self._buscar_dfe_lines(odoo_dfe_id)` ← 1 argumento

**Observacao**: NAO existe campo `lines_ids` no modelo DFE do Odoo. O metodo faz search separado.

---

## ERRO 4: Tolerancia de Preco 5% no Preview vs 0% na Validacao

**Sintoma**: Modal preview mostra "preco_ok: true" mas validacao real bloqueia por preco.

**Causa**: Codigo antigo (routes) usava tolerancia hardcoded de 5%. O service usa constantes centralizadas com 0%.

**Valores CORRETOS (service linhas 52-56)**:
```python
TOLERANCIA_QTD_PERCENTUAL = Decimal('10.0')    # 10% para quantidade
TOLERANCIA_PRECO_PERCENTUAL = Decimal('0.0')   # 0% para preco (EXATO!)
```

**Valores ERRADOS (codigo antigo routes)**:
```python
'qtd_ok': abs(dif_qtd_pct) <= 5    # ERRADO: era 5%
'preco_ok': abs(dif_preco_pct) <= 5  # ERRADO: era 5%
```

**Regra**: SEMPRE usar as constantes do service. NUNCA hardcodar tolerancias.

---

## ERRO 5: Dados do MatchNfPoItem ja Estao CONVERTIDOS

**Sintoma**: Valores duplicados de conversao (converter duas vezes).

**Causa**: Os campos `qtd_nf` e `preco_nf` no `MatchNfPoItem` ja contem valores APOS conversao De-Para. NAO reconverter.

**Campos JA CONVERTIDOS no MatchNfPoItem**:
```python
item.qtd_nf       # Quantidade JA convertida (ex: 60000 UNITS, nao 60 ML)
item.preco_nf     # Preco JA convertido (ex: R$ 0.041/UNIT, nao R$ 41/ML)
item.fator_conversao  # Fator usado (ex: 1000)
```

**Para obter valores ORIGINAIS (antes da conversao)**:
```python
qtd_original = qtd_convertida / fator    # 60000 / 1000 = 60 ML
preco_original = preco_convertido * fator  # 0.041 * 1000 = R$ 41/ML
```

---

## ERRO 6: PedidoCompras.cod_produto vs cod_produto_interno

**Sintoma**: Match nao encontra correspondencia entre itens NF e POs.

**Causa**: Na tabela `pedido_compras`, o campo `cod_produto` JA e o codigo interno (ex: 'PROD-001'). NAO confundir com `cod_produto_fornecedor`.

**Fluxo de codigos**:
```
NF (Odoo):        det_prod_cprod = 'ABC-123'  (codigo DO FORNECEDOR)
                         ↓ De-Para
MatchNfPoItem:    cod_produto_interno = 'PROD-001'  (codigo INTERNO)
                         ↕ Match
PedidoCompras:    cod_produto = 'PROD-001'  (codigo INTERNO - mesmo!)
```

---

## ERRO 7: Filtro de POs sem dfe_id

**Sintoma**: POs ja usados aparecem como candidatos novamente.

**Causa**: O filtro `dfe_id IS NULL OR dfe_id = ''` so funciona se o campo for limpo apos uso.

**Criterios corretos para PO candidato**:
```python
PedidoCompras.query.filter(
    cnpj_fornecedor == cnpj,           # Mesmo fornecedor
    status_odoo.in_(['purchase', 'done']),  # Confirmado
    db.or_(dfe_id.is_(None), dfe_id == ''),  # SEM NF vinculada
    (qtd_produto_pedido - coalesce(qtd_recebida, 0)) > 0  # COM saldo
)
```

---

## ERRO 8: Nao Verificar se Validacao Existe Antes do Preview

**Sintoma**: `DFE X nao encontrado localmente`

**Causa**: O preview so funciona APOS `validar_dfe()` ter sido executado pelo menos uma vez. Se o DFE nunca foi validado, nao existe registro em `ValidacaoNfPoDfe`.

**Fluxo correto**:
1. Usuario clica "Validar" → `validar_dfe()` → importa dados do Odoo → cria registros locais
2. Usuario clica "Ver POs" → `buscar_preview_pos_candidatos()` → le dados locais

Se passo 1 nao ocorreu, passo 2 falha.

---

## CHECKLIST: Antes de Modificar o Preview

- [ ] NAO chamar `get_odoo_connection()` no preview
- [ ] NAO chamar `_buscar_dfe()` no preview
- [ ] NAO chamar `_buscar_dfe_lines()` no preview
- [ ] Usar `ValidacaoNfPoDfe.query` para cabecalho
- [ ] Usar `MatchNfPoItem.query` para itens
- [ ] Usar `_buscar_pos_fornecedor_local()` para POs
- [ ] Usar constantes TOLERANCIA_* (nao hardcodar)
- [ ] Lembrar que qtd_nf/preco_nf no MatchNfPoItem JA ESTAO convertidos
