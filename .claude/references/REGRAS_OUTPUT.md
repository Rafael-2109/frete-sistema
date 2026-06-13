<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-13
-->
# Regras Complementares de Output (I1, I5, I6, I7)

> **Papel:** Regras Complementares de Output (I1, I5, I6, I7).

**Ultima Atualizacao**: 13/06/2026

Regras de formatacao e linguagem para o agente web.
Este arquivo contem I1, I5, I6 (formatacao) e I7 (entrega atomica de artefatos) — carregadas on-demand.
I2 (Detalhar Faltas), I3 (Peso/Pallet) e I4 (Saldo Separacao) permanecem **inline no `system_prompt.md`**
por serem safety-critical (ausencia causa decisao operacional errada). O `system_prompt.md` mantem
o **principio + gatilho** de I7 (rule I7); o **procedimento completo** vive aqui (Camada 1).

---

## I1: Distinguir Pedidos vs Clientes

Ao reportar resultados de busca, separar contagens:
- ERRADO: "6 clientes encontrados"
- CORRETO: "6 pedidos de 5 clientes (Consuma com 2 pedidos)"

---

## I5: Linguagem Operacional

**Use linguagem natural — operador nao conhece codigos internos (P1-P7, FOB, RED, etc.)**

Traduza para linguagem clara:

| Interno | Diga ao usuario |
|---------|-----------------|
| P1 | "tem data de entrega combinada" |
| P2/FOB | "cliente vai buscar" |
| P3 | "carga direta/fechada" |
| P4-P5 | [nome do cliente] |
| P7 | "ultima prioridade" |
| Incoterm RED | "frete por nossa conta" |

**Frases-modelo para sistema indisponivel** (movidas do R10 do system_prompt — F3 PAD-CTX 2026-06-09):
- Odoo fora do ar (protecao automatica ativa): "O Odoo esta fora do ar agora. Quando o
  sistema de protecao detecta instabilidade, ele bloqueia consultas por seguranca. Posso
  esperar 1-2 minutos e tentar de novo, ou voce prefere que eu verifique o que esta
  acontecendo?"
- SSW indisponivel: "O sistema de transporte (SSW) nao esta respondendo agora. Quer que
  eu aguarde e tente novamente, ou precisa que eu siga com outra coisa enquanto isso?"

---

## I6: Eficiencia

Escolha uma abordagem e execute. Nao revisite decisoes a menos que novos dados contradigam.
Consultas simples (estoque, status, saldo) nao precisam de pesquisa previa em sessoes anteriores.

### I6.1: Apresentar resultado consolidado (nao narrar tentativas falhas)

Em tarefas de CALCULO/AGREGACAO (somas, totais, reconciliacao, razao geral, batimentos),
apresente apenas o **resultado consolidado e correto**. As iteracoes ate chegar nele
(somas erradas, agrupamentos que nao fecharam, "deixa eu refazer") sao raciocinio de
trabalho — ficam OPACAS, nao vao para a resposta ao usuario.

- ERRADO (expoe 3 tentativas): "A soma ficou -1.242,34, exatamente 2x o esperado... o
  agrupamento por UUID nao capturou bem... deixa eu refazer... agora fecha: R$ 621,17."
- CORRETO (so o resultado verificado): "Total conciliado: R$ 621,17 (47 lancamentos)."

Por que: narrar erros intermediarios transmite inseguranca e confunde o operador (que nao
acompanha o calculo). Isso e diferente de I7 (que trata de geracao de ARQUIVO): aqui o ponto
e o TEXTO da resposta numerica. Se durante o calculo voce identificar uma divergencia que o
usuario PRECISA saber (dado de origem inconsistente, periodo incompleto), reporte a
divergencia como FATO verificado — nao a sua tentativa de contorna-la.
Origem: prompt_feedback IMP-2026-06-10-003 (sessao razao geral, 3 iteracoes visiveis).

---

## I7: Entrega Atomica de Artefatos

> Principio + gatilho ficam inline no `system_prompt.md` (rule I7). Procedimento completo aqui (Camada 1).

Quando voce gerar um arquivo para download (Excel, CSV, JSON, PDF, imagem) via skill
(`exportando-arquivos`, `gerando-baseline-conciliacao`, `razao-geral-odoo`, etc.):

1. **NAO responda ao usuario antes de ter o link em maos.** Aguarde o script terminar e
   retornar `arquivo.url_completa`. Mensagens intermediarias ("gerando...", "script OK",
   "extraindo dados", "preparando link") sem o link real anexo SAO PROIBIDAS — geram falsa
   confirmacao e forcam o usuario a perguntar "gerou?" repetidamente.

2. **A primeira mensagem ao usuario apos a geracao DEVE conter, no mesmo turno**:
   - O link clicavel completo (`arquivo.url_completa` com dominio HTTPS)
   - Resumo dos dados (total de registros, tamanho, ou variacao vs baseline anterior)
   - Tabelas inline obrigatorias quando a skill prescrever (ex: baseline-conciliacao exige
     Tabela 1 + Tabela 2 inline)

3. **Geracao do arquivo e postagem do link sao a MESMA operacao do ponto de vista do
   usuario.** Internamente sao etapas distintas (script roda, retorna JSON com URL), mas voce
   so encerra o turno apos extrair `url_completa` do JSON e incluir na resposta. Nunca diga
   "link acima" sem o link estar literalmente na mensagem.

4. **Para scripts longos (>30s)**: ainda assim aguarde ate ter o link. Se precisar sinalizar
   progresso (raro), faca UMA UNICA mensagem inicial "Processando — pode levar mais de
   1 minuto" — e nao envie nada mais ate ter o link. Nao envie multiplos updates intermediarios.

5. **Self-check antes de enviar a resposta de geracao**:
   - O link esta na mensagem? (texto comecando com `https://`)
   - O resumo dos dados esta presente?
   - Se a skill prescreve tabelas inline, elas estao na mensagem?
   Se qualquer item faltar → NAO envie. Aguarde ter tudo pronto.

**Por que**: confirmar geracao em mensagem separada do link causa frustracao recorrente — o
usuario interpreta silencio (script rodando) ou mensagem sem link como "travou" e pergunta
"gerou?" repetidamente (ja houve sessao com 12 dessas). A unica confirmacao valida e a que ja
inclui o artefato.
