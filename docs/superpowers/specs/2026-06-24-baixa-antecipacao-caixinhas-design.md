<!-- doc:meta
tipo: explanation
camada: L3
sot_de: refactor baixa antecipacao (modelo de caixinhas / reconciliacao por estado-alvo)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-24
-->

# Spec — Baixa de antecipação por reconciliação de "caixinhas" (estado-alvo determinístico)

> **Papel:** especificação de design (diagnóstico + arquitetura-alvo + fontes de verdade + critérios)
> do refactor da baixa de antecipação no `app/financeiro/services/baixa_titulos_service.py`.
> **Status:** EM IMPLEMENTACAO — Etapas 1-3 feitas no working tree (NAO commitado/deployado);
> 167 testes financeiros verdes (22 novos do modelo de caixinhas). Pendente: (a) remover a
> heuristica `desconto_ja_embutido` do fluxo classico (hoje inalcancavel p/ clientes com desconto
> contratual, ainda roda p/ os sem — v2 apos validar); (b) primeira baixa real com 1 titulo no Odoo
> (nao testavel em CI). A correcao operacional anterior (coluna ENCARGOS, commit `184e27fa7`) ja em prod.

## Indice

- [Contexto](#contexto)
- [1. Problema](#1-problema)
- [2. Fontes de verdade](#2-fontes-de-verdade-deterministicas-lidas-ao-vivo-do-odoo)
- [3. Função pura — calcular_caixinhas](#3-funcao-pura--calcular_caixinhas)
- [4. Reconciliador](#4-reconciliador--reconciliarcaixinhas-estado_odoo---operacoes)
- [5. Validações](#5-validacoes-antes-de-qualquer-escrita-no-odoo)
- [6. O que muda no código](#6-o-que-muda-no-codigo)
- [7. Pontos em aberto](#7-pontos-em-aberto-decisao-de-negocio)
- [8. Critérios de aceite](#8-criterios-de-aceite)
- [9. Riscos](#9-riscos)

## Contexto

Caso real: baixa de **antecipação de recebíveis Sendas/Assaí** (cliente REDE ASSAI) no template de
baixa de títulos a receber (`/financeiro/contas-receber/baixas`). O título no Odoo já vem líquido do
desconto contratual; o saldo decompõe em **líquido (banco) + encargos**, e o desconto é **0,5%** da
face. A lógica atual mistura três tratamentos ad-hoc do mesmo desconto e falhou em 74/76 itens do
lote 104. Esta spec define o modelo determinístico que substitui essa lógica. Investigação e dados de
apoio: memória `projeto_baixa_template_antecipacao_sendas`; baixas já executadas via agente
(`PSIC/1502/01244-01279`). Lido por: dev (refactor 4-mãos). Não é para o agente web.

## 1. Problema

A lógica atual de baixa trata o desconto concedido como **vários casos distintos**, cada um com
heurística própria:
- `_corrigir_titulo_ano_2000()` — trata o estado "linha-fantasma `2000-01-01`";
- rede `desconto_ja_embutido` — **adivinha** por comparação de saldo se o desconto já está aplicado;
- validação por **soma** das colunas (`VALOR+DESCONTO+...`) contra o saldo.

Isso é frágil: no lote 104, **74/76** itens Sendas deram "Soma dos valores maior que saldo".

**Insight (Rafael):** "ano-2000" e "desconto embutido" não são naturezas diferentes — são **2 momentos
da mesma entidade** (o desconto concedido). A avaliação deve ser **determinística**: dimensionar as
"caixinhas" a partir da fonte de verdade (face da NF + taxa do cliente) **antes** de olhar o Odoo, e
só então reconciliar o estado atual contra esse alvo. As caixinhas são invariantes; só as **operações**
variam conforme o estado no Odoo.

## 2. Fontes de verdade (deterministicas, lidas AO VIVO do Odoo)

| Caixinha / dado | Fonte canônica | Observação |
|---|---|---|
| **Face** (NF sem abatimentos) | `account.move.l10n_br_total_nfe` | 149407 = 5.999,54; 148363 = 481,92. Não precisa do XML. |
| **Taxa de desconto** | `res.partner.x_studio_desconto` (%) + flag `x_studio_desconto_contratual` | REDE ASSAI = **0,5%**. `contract_ids` vazio. |
| **amount_total** (= título) | `account.move.amount_total` | = face − desconto. 149407 = 5.969,54; 148363 = 479,51. |
| **Saldo a baixar** | `account.move.line.amount_residual` | do título receivable. |
| **Encargos** | planilha (`Vlr.encargos`) | depende do **prazo** da antecipação — não derivável só da face (ver §7). |
| **Líquido** | resíduo: `amount_total − encargos` | o que entra no banco (Sicoob). |

**NÃO usar** `contas_a_receber.desconto_percentual`/`desconto` (sincronizado) como fonte: provado
**furado** na NF 148815 (veio `0` quando o correto é 0,5%). A fonte é o Odoo ao vivo.

Relação determinística confirmada (2 NFs):
`l10n_br_total_nfe − (l10n_br_total_nfe × x_studio_desconto%) = amount_total`
- 5.999,54 − 30,00 = 5.969,54 ✓ · 481,92 − 2,41 = 479,51 ✓

## 3. Funcao pura — calcular_caixinhas

Determinística, testável sem Odoo.

```python
TOL = 0.05  # R$ — tolerância de centavos (arredondamento)

def calcular_caixinhas(face: float, taxa_desconto: float, encargos: float) -> Caixinhas:
    """
    face          = account.move.l10n_br_total_nfe
    taxa_desconto = res.partner.x_studio_desconto / 100   (ex: 0.005)
    encargos      = Vlr.encargos da planilha (>= 0)
    """
    desconto = round(face * taxa_desconto, 2)
    titulo   = round(face - desconto, 2)          # == amount_total esperado
    liquido  = round(titulo - encargos, 2)        # entra no banco
    # INVARIANTE: liquido + encargos + desconto == face
    if abs((liquido + encargos + desconto) - face) > TOL:
        raise ValueError(f"Invariante violada: {liquido}+{encargos}+{desconto} != face {face}")
    if liquido < -TOL:
        raise ValueError(f"Encargos ({encargos}) > titulo ({titulo}) — liquido negativo")
    return Caixinhas(face=face, desconto=desconto, titulo=titulo,
                     encargos=encargos, liquido=liquido)
```

## 4. Reconciliador — reconciliar(caixinhas, estado_odoo) -> operacoes

Detecta em qual estado o título está e emite **apenas as operações que faltam** para honrar as
caixinhas. O alvo (caixinhas) é o mesmo nos 3 estados.

| Estado no Odoo | Detecção determinística | Operações para honrar a caixinha |
|---|---|---|
| **Embutido** (Sendas atual) | linha DESCONTOS CONCEDIDOS na venda **e** `amount_residual ≈ titulo` (= face−desconto); sem linha `2000-01-01` | pagar **LÍQUIDO** (journal Sicoob) + **write-off ENCARGOS** → fecha. DESCONTO **não** relança. |
| **Ano-2000** | existe `account.move.line` receivable com `date_maturity='2000-01-01'` | **normalizar**: zerar a linha-fantasma e garantir `amount_total = face − desconto` (vira estado "Embutido") → depois pagar LÍQUIDO + ENCARGOS. |
| **Nada aplicado** | `amount_residual ≈ face` (desconto ainda não abatido); sem linha desconto na venda | lançar **DESCONTO** (journal DESCONTO CONCEDIDO, conta 25338) + **LÍQUIDO** + **ENCARGOS** → fecha. |

Conta de ENCARGOS = `CONTA_ENCARGOS_POR_COMPANY[company_do_journal]` (mantém o que já está em prod;
company do **journal** Sicoob, não do título — gotcha O8). Write-off via wizard `account.payment.register`.

## 5. Validacoes (antes de qualquer escrita no Odoo)

1. **Invariante**: `LÍQUIDO + ENCARGOS + DESCONTO == face` (tol `TOL`).
2. **Desconto calculado vs Odoo**: quando existir a linha DESCONTOS CONCEDIDOS (25338), seu valor
   deve bater com `face × taxa` (tol `TOL`). Divergência → erro (cadastro/taxa inconsistente).
3. **Saldo coerente com o estado**: estado Embutido → `amount_residual ≈ LÍQUIDO + ENCARGOS`;
   estado Nada → `amount_residual ≈ face`. Se não casa nenhum estado → erro explícito (não adivinhar).
4. **Líquido ≥ 0** e **encargos ≥ 0**.

## 6. O que muda no codigo

- **Remove** a rede heurística `desconto_ja_embutido` (substituída por cálculo determinístico).
- **`_corrigir_titulo_ano_2000`** deixa de ser um passo cego no início e vira o **normalizador do
  estado "Ano-2000"** dentro do reconciliador (mesma máquina, sem lógica duplicada).
- **Novo**: leitura ao vivo de `l10n_br_total_nfe` (face) e `x_studio_desconto` (taxa) no momento da
  baixa (1-2 reads extras por título).
- O write-off de ENCARGOS (já implementado hoje) é reaproveitado.

### Arquivos afetados
- `app/financeiro/services/baixa_titulos_service.py` — núcleo (caixinhas + reconciliador).
- `app/financeiro/constants.py` — `TOL`; `CONTA_ENCARGOS_POR_COMPANY` (já existe).
- `tests/financeiro/` — testes de `calcular_caixinhas` (puro) + reconciliador por estado.
- `app/financeiro/CLAUDE.md` — documentar o modelo (gotchas O7/O10 ficam obsoletos/refinados).

## 7. Pontos em aberto (decisao de negocio)

- **Encargos determinísticos?** Hoje vêm da planilha. O `property_payment_term_id` do cliente é
  "45 DDL" (prazo no Odoo). Se houver uma **taxa de antecipação** conhecida, encargos poderiam ser
  derivados (`titulo × taxa_antecip × dias/30`), eliminando mais um input manual. **Default desta spec:
  encargos vêm da planilha**; derivação fica como evolução se você confirmar a fórmula/taxa.
- **Cross-company encargos** (verificado nas 36 baixas em prod, 2026-06-24): TODAS lançaram
  encargos na conta **22768 (FB)** com journal **SICOOB 10 (FB)**, título sempre **CD(4)** →
  segue a company do **journal**, não do título (a conta CD equivalente 25334 não foi usada).
  Padrão mantido (`CONTA_ENCARGOS_POR_COMPANY[company_do_journal]`, consistente com O8).
  Ressalva: a amostra é toda CD+SicoobFB, logo não desambigua "company do journal" de "constante
  22768 fixa" — se surgir journal de outra company (ex. Sicoob LF 386), revisar. Contabilidade
  ratifica se os encargos da CD devem mesmo ficar em FB ou na conta da CD (25334).

## 8. Criterios de aceite

- [ ] `calcular_caixinhas` pura e testada (invariante, tolerância, líquido negativo, taxa 0,5%).
- [ ] Taxa lida de `res.partner.x_studio_desconto` (ao vivo) — **não** do campo sincronizado.
- [ ] Face lida de `account.move.l10n_br_total_nfe`.
- [ ] Reconciliador detecta os 3 estados e fecha o título (residual 0) em cada um (1 teste por estado).
- [ ] Caso NF 148815 (sincronizado furado = 0) é tratado certo: taxa real 0,5% calculada da fonte.
- [ ] Desconto já abatido **não** é relançado; invariante validada **antes** de escrever no Odoo.
- [ ] Erro explícito (sem adivinhação) quando o saldo não casa nenhum estado.
- [ ] `_corrigir_titulo_ano_2000` integrado como normalizador (sem lógica duplicada).
- [ ] Não-regressão: suíte `tests/financeiro/` verde; baixa por ENCARGOS (já em prod) preservada.
- [ ] Primeira execução real com **1 título** antes de lote.

## 9. Riscos

- Baixa real depende de título aberto no Odoo (não testável em CI) — validar com 1 título.
- Leitura ao vivo de `l10n_br_total_nfe`/`x_studio_desconto` adiciona 1-2 RPC por item (aceitável).
- Mudança no coração do `baixa_titulos_service` — fazer atrás de testes por estado antes de migrar.
