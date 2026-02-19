# SSW_COMMON — Funcoes compartilhadas, defaults e batch

Documentacao de infraestrutura compartilhada entre scripts SSW.

---

- [ssw_common.py](#ssw_commonpy)
- [ssw_defaults.json](#ssw_defaultsjson)
- [Sequencia Batch](#sequencia-de-execucao-batch)
- [Mapeamento Unidade → Transportadora](#mapeamento-unidade--transportadora)

---

## ssw_common.py

Funcoes Playwright reutilizaveis compartilhadas por todos os scripts.

| Funcao | Descricao |
|--------|-----------|
| `verificar_credenciais()` | Valida env vars SSW obrigatorias |
| `carregar_defaults(path)` | Carrega ssw_defaults.json |
| `login_ssw(page)` | Login no SSW (reutiliza sessao ativa) |
| `abrir_opcao_popup(context, frame, opcao)` | Navega para opcao e captura popup |
| `interceptar_ajax_response(popup, frame, action)` | Executa acao e intercepta response HTML |
| `injetar_html_no_dom(popup, html)` | Injeta HTML via `document.write()` |
| `preencher_campo_js(popup, field, value)` | Preenche campo SEM eventos (evita geocoding) |
| `preencher_campo_no_html(popup, field, value)` | Preenche campo COM eventos change/input |
| `preencher_campo_inline(frame, field_id, value)` | Preenche campo em grids (402) |
| `capturar_campos(target)` | Snapshot de todos campos visiveis |
| `capturar_screenshot(page, nome)` | Screenshot para evidencia |
| `gerar_saida(sucesso, **kwargs)` | Output JSON padrao |
| `verificar_mensagem_ssw(popup)` | Verifica erro/sucesso no DOM |

**Env vars obrigatorias**: `SSW_URL`, `SSW_DOMINIO`, `SSW_CPF`, `SSW_LOGIN`, `SSW_SENHA`

**createNewDoc override** (obrigatorio em TODA operacao de popup):
```javascript
createNewDoc = function(pathname) {
    document.open("text/html", "replace");
    document.write(valSep.toString());
    document.close();
    if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
};
```
Sem isso, `ajaxEnvia()` tenta abrir nova janela em vez de atualizar DOM.

---

## ssw_defaults.json

Valores padrao CarVia para operacoes de escrita no SSW. Estrutura:

| Secao | Conteudo |
|-------|---------|
| `empresa` | CNPJ, IE, razao social, RNTRC |
| `seguro` | Apolice RCTRC, seguradora |
| `banco` | Codigo, agencia, conta (Banco Inter) |
| `endereco_fiscal` | Logradouro, CEP (06530581), DDD, telefone |
| `opcao_401` | Flags unidade (ativa, rodoviario, etc.) |
| `opcao_478` | Defaults fornecedor (contribuinte=N, especialidade=TRANSPORTADORA) |
| `opcao_408` | Defaults comissao (data_ini=180226, despacho=1,00) |
| `opcao_402` | Defaults cidades (tipo_frete=A, coleta=S, entrega=S) |
| `opcao_002` | Defaults cotacao (frete=CIF, coletar=S, entregar=S, contribuinte=S) |

---

## Sequencia de Execucao Batch

Para registrar N transportadoras em lote, **ordem obrigatoria**:

```
1. Batch 478 (fornecedores):
   Para cada CNPJ: PES → preencher campos obrigatorios → GRA
   Verificar: inclusao != 'S' (registro finalizado)

2. Batch 485 (transportadoras):
   Para cada CNPJ: PES → preencher nome + ativo → INC/GRA
   Verificar: nome preenchido no DOM

3. Batch 408 (comissoes):
   Para cada unidade: ENV → preencher CNPJ + data + despacho → ENV2
   Verificar: popup fecha (sucesso) ou acao='A' (ja existe)
```

---

## Mapeamento Unidade → Transportadora

Referencia POP-A10 Feb/2026:

| Unidades | Transportadora | CNPJ |
|----------|---------------|------|
| SSA, JPA, MCZ, NAT | CAZAN | 07797011000193 |
| FLN, AJU, CWB, PAS, POA | DAGO | 11758701000100 |
| VIX | UNI BRASIL | 42769176000152 |
| OAL, LDB, MGF, PVH | TRANSPEROLA | 44433407000188 |
| PAU | MONTENEGRO | 22188831000252 |
| VDC, EUN, IOS, BPS, FEI, TXF, VCQ | REIS ARAGAO | 17706435000744 (VCQ) / 17706435000230 (demais) |
| MAO | ACOLOGIS | 40272996000109 |
| GIG | TRANSMENEZES | 20341933000150 |

**Total**: 23 unidades, 8 transportadoras. 23/23 comissoes 408 criadas (2026-02-18).
