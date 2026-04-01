# CTE — 004, 007, 101

Gotchas de dominio, FIELD_MAP interno e workflow completo para operacoes CT-e no SSW.
Para parametros e retornos dos scripts, consultar [SCRIPTS.md](../SCRIPTS.md).

---

- [FIELD_MAP — emitir_cte_004.py](#field_map--emitir_cte_004py)
- [Fluxo SSW Detalhado](#fluxo-ssw-detalhado)
- [Dialogs Automaticos](#dialogs-automaticos)
- [Gotchas de Dominio](#gotchas-de-dominio)
- [Restricoes de Cancelamento](#restricoes-de-cancelamento)
- [Workflow CT-e Completo](#workflow-ct-e-completo)

---

## FIELD_MAP — emitir_cte_004.py

Mapeamento dos 3 campos preenchidos pelo script no formulario SSW opcao 004:

| Parametro CLI | Campo SSW (name) | Campo SSW (id) | Notas |
|---------------|------------------|----------------|-------|
| `--placa` | `f13` | `13` | Placa coleta. Blur (`Tab`) dispara validacao SSW. ARMAZEM = fracionado |
| `--chave-nfe` | `chaveAcesso` | `-1` | 44 digitos. `onChange` chama `isSSW(value, 1)` — lookup servidor, aguardar 10s |
| `--frete-peso` | `id_frt_inf_frete_peso` | — | Dentro do painel colapsavel "parc". Abrir com `showhide('parc')`, fechar com `fechafrtparc('C')` |
| `--medidas` | `id_dim_{n}_altu/larg/comp/vezes` | — | Dimensoes de moto. Painel "Volume (m3)": abrir com `showhide('volume')`, confirmar com `acabadim('C')`. Valores em metros. `_vezes` dispara `linhadim()` no blur |

### Campos de volume (dimensoes moto) — emitir_cte_004.py

Painel colapsavel "Volume (m3)" com linhas indexadas (n=1,2,3...):

| Campo SSW (name) | Campo SSW (id) | Tipo | Notas |
|-------------------|----------------|------|-------|
| `id_dim_{n}_altu` | `id_dim_{n}_altu` | currencyedit, 3 casas | Altura em metros |
| `id_dim_{n}_larg` | `id_dim_{n}_larg` | currencyedit, 3 casas | Largura em metros |
| `id_dim_{n}_comp` | `id_dim_{n}_comp` | currencyedit, 3 casas | Comprimento em metros |
| `id_dim_{n}_vezes` | `id_dim_{n}_vezes` | numerico, maxlength 4 | Quantidade. `onblur=linhadim()` calcula cubagem |

Botoes:
- Abrir painel: `<a id="lnk_dim" onclick="showhide('volume')">Volume (m3):</a>`
- Confirmar: `<a id="id_dim_env" onclick="acabadim('C')">►</a>`

Conversao: `carvia_modelos_moto` armazena em CM → dividir por 100 para SSW (metros).

### Campos de consulta — consultar_ctrc_101.py

| Parametro CLI | Campo SSW (id) | Acao AJAX |
|---------------|----------------|-----------|
| `--ctrc` | `t_nro_ctrc` | `ajaxEnvia('P1', 1)` |
| `--nf` | `t_nro_nf` | `ajaxEnvia('P2', 1)` |

### Campos de cancelamento — cancelar_cte_004.py

O script tenta multiplos nomes para cada campo (SSW nao e consistente):

| Campo | Nomes tentados (em ordem) | Fallback |
|-------|---------------------------|----------|
| CTRC | `2`, `ctrc`, `numero`, `num_ctrc`, `nrctrc`, `nr_ctrc` | Primeiro input numerico visivel |
| Motivo | `motivo`, `obs`, `observacao`, `justificativa`, `mot_cancel`, `motivo_cancel` | — |

---

## Fluxo SSW Detalhado

### Emissao (004 → 007 → 101)

```
1. login_ssw()
2. trocar_filial(CAR)
3. abrir_opcao_popup(004)
4. CREATE_NEW_DOC_OVERRIDE (monkey-patch createNewDoc)
5. ajaxEnvia('NORMAL', 1) → formulario CT-e Normal
6. Preencher f13 (placa) → fill() + Tab → aguardar 3s (validacao blur)
7. Campo chaveAcesso aparece automaticamente (popup nfepnl apos Tab no ARMAZEM)
8. Preencher chaveAcesso → fill() + click away → isSSW() lookup → aguardar 10s
9. showhide('parc') → preencher id_frt_inf_frete_peso → fechafrtparc('C')
10. calculafrete(this) → simular frete → aguardar 8s
11. concluindo('C') → GRAVAR → dialogs → capturar CTRC do alert/DOM
12. [--enviar-sefaz] ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024') → aguardar 15s
13. [--consultar-101] abrir opcao 101 → preencher t_nro_ctrc → ajaxEnvia('P1', 1)
```

### Consulta (101)

```
1. login_ssw()
2. Setar filial via elemento #2
3. abrir_opcao_popup(101)
4. Preencher t_nro_ctrc (CTRC) OU t_nro_nf (NF)
5. ajaxEnvia('P1', 1) para CTRC ou ajaxEnvia('P2', 1) para NF
6. CREATE_NEW_DOC_OVERRIDE (so para CTRC, antes do ajax; para NF, 0.5s depois)
7. Extrair 16 campos via regex sobre body.innerText
8. [--baixar-xml] ajaxEnvia('XML', 0) → download ZIP → extrair XML → re-pesquisar
9. [--baixar-dacte] onclick link_imp_dacte → download PDF
```

### Cancelamento (004)

```
1. login_ssw()
2. abrir_opcao_popup(004)
3. CREATE_NEW_DOC_OVERRIDE
4. Encontrar link "Cancelar" (texto match OU 'CAN' em onclick)
5. interceptar_ajax_response → injetar HTML da tela de cancelamento
6. Preencher campo CTRC (multi-estrategia) → ajaxEnvia('PES', 0) → verificar CT-e existe
7. Extrair dados do CT-e (remetente, destinatario, valores, status, chave)
8. [--dry-run] Retornar preview
9. Preencher campo motivo (multi-estrategia)
10. Registrar handler confirm (auto-accept) + listener response
11. ajaxEnvia('CAN', 0) ou ajaxEnvia('EXC', 0) → aguardar 5s SEFAZ
12. Detectar resultado: popup fechou (sucesso), indicadores no body, ou <foc> (erro)
```

---

## Dialogs Automaticos

### emitir_cte_004.py

| Dialog | Tipo | Conteudo (match) | Acao script |
|--------|------|-------------------|-------------|
| Email nao disponivel | `confirm` | "email", "disponivel" | `dismiss()` (rejeita) |
| Confirma emissao | `confirm` | "confirma", "gravar", "emiss" | `accept()` (confirma) |
| CTRC gravado | `alert` | regex `(\d{2,6})` | `accept()` + captura numero |

### cancelar_cte_004.py

| Dialog | Tipo | Acao script |
|--------|------|-------------|
| "Confirma cancelamento?" | `confirm` | `accept()` (confirma) |

---

## Gotchas de Dominio

### Emissao

1. **Placa ARMAZEM = fracionado**: Indica mercadoria ja no armazem CarVia. Para carga direta (POP-C02), usar placa REAL do veiculo.
2. **isSSW() lookup assincrono**: O campo `chaveAcesso` dispara `isSSW(value, 1)` ao perder foco — busca NF-e no servidor. Aguardar 10s. Se falhar, script tenta fallback via `evaluate()`.
3. **Painel "parc" colapsavel**: O campo `id_frt_inf_frete_peso` esta oculto dentro de painel. `showhide('parc')` abre, `fechafrtparc('C')` fecha. Script usa `force=True` no fill.
4. **Pre-CTRC != CT-e autorizado**: Apos gravar na 004, o pre-CTRC NAO tem valor fiscal. So se torna CT-e valido apos envio ao SEFAZ via `--enviar-sefaz` (opcao 007).
5. **CREATE_NEW_DOC_OVERRIDE**: Monkey-patch em `createNewDoc()` para manter referencia DOM do Playwright. Sem ele, SSW abre nova janela e Playwright perde controle.
6. **Ordem do override para NF**: Na consulta 101 por NF (`ajaxEnvia('P2', 1)`), o override deve ser aplicado 0.5s DEPOIS do ajax (nao antes), pois interfere com a validacao de NF.
7. **Filial DEVE ser CAR**: Emissao em MTZ ou outra filial produz dados fiscais incorretos.

### Consulta

8. **Apos baixar XML, DOM e substituido**: O download XML aciona `ajaxEnvia('XML', 0)` que substitui o body. O script re-pesquisa automaticamente para restaurar os dados no DOM.
9. **seq_ctrc e familia**: Extraidos do atributo `onclick` de `link_imp_dacte`. Necessarios para downloads de DACTE/XML.

### Cancelamento

10. **Prazo SEFAZ**: 7 dias corridos a partir da data de autorizacao. Apos esse prazo, SEFAZ rejeita.
11. **Manifesto**: Se CT-e foi incluido em Manifesto (MDF-e), cancelar o Manifesto PRIMEIRO na opcao 024.
12. **Mercadoria embarcada**: NAO cancelar CT-e se mercadoria ja saiu. Risco de sinistro sem cobertura de seguro.
13. **Efeitos colaterais SSW**: Cancelamento cancela automaticamente fatura, boleto e averbacao vinculados.
14. **Popup fechou = sucesso**: No SSW, popup fechar apos submit de cancelamento e indicador de sucesso (padrao `TargetClosedError`).
15. **Resultado inconclusivo**: Se nenhum indicador claro (sucesso ou erro), script retorna `status="inconclusivo"`. Verificar manualmente na opcao 101.

---

## Workflow CT-e Completo

```
1. EMITIR (004)
   emitir_cte_004.py --chave-nfe "..." --frete-peso 600 --placa ARMAZEM --dry-run
   → Confirmar preview
   emitir_cte_004.py --chave-nfe "..." --frete-peso 600 --enviar-sefaz --consultar-101 --baixar-dacte

2. CONSULTAR (101) — a qualquer momento, read-only
   consultar_ctrc_101.py --ctrc 94 --baixar-xml --baixar-dacte

3. CANCELAR (004) — se necessario, dentro de 7 dias
   Checklist pre-cancelamento:
     [ ] Prazo < 7 dias da autorizacao
     [ ] Manifesto cancelado (se existir)
     [ ] Mercadoria NAO embarcada
   cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" --motivo "..." --dry-run
   → Confirmar preview
   cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" --motivo "..."

POPs relacionados:
  POP-C01: Emitir CT-e fracionado (placa ARMAZEM)
  POP-C02: Emitir CT-e carga direta (placa real)
  POP-C05: Imprimir CT-e / DACTE
  POP-C06: Cancelar CT-e
```
