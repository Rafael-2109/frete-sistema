# PROMPT — Próxima sessão (Industrialização FB↔LF)

## Como começar
Leia nesta ordem: `README.md` → `DIRETRIZ.md` → `ACHADOS_TECNICOS.md` → `PLANO_EXECUCAO.md` → `00_FLUXO_ATUAL_VS_IDEAL.md`.
**Ignore `HISTORICO/`** — é a execução "Opção 2 / inter-company" revertida; serve só como referência de IDs/cadastros, o fluxo descrito ali está ABANDONADO.

## Estado (fechado em 2026-05-29)
- "Opção 2 / inter-company" **abandonada e revertida**. `res.company.rule_type` em FB(1)+LF(5) = `not_synchronize`. **NÃO reativar `sale_purchase`** (era company-wide e disparava SO espúria em toda transferência, inclusive CD↔FB).
- **Diretriz definida**: fluxo por **picking físico + material em terceiros**; na LF, apontar as contas de estoque das **categorias (por-empresa, `ir.property`)** para o par terceiros `1150200001` (valoração) / `1150200002` (entrada e saída) → toda movimentação na LF fica **net-zero em terceiros, por configuração** (a LF não tem estoque próprio).
- Documentação reescrita e canônica (5 arquivos na raiz).

## GATILHO — já ATINGIDO
Os **16 insumos do piloto já voltaram para FB/Estoque** (NF 725676 cancelada + picking 322049 revertido, 2026-05-29). O gatilho está atingido — falta só o **"go" do Rafael** para iniciar a execução (Passo 0 abaixo). NÃO executar sem o "go".

## Próximos passos (quando o gatilho disparar — detalhe em `PLANO_EXECUCAO.md`)
1. **Passo 0 (base de tudo)**: levantar TODAS as categorias que os produtos da industrialização usam na LF; validar com o Contador o par de contas (valoração=1150200001, entrada/saída=1150200002, + tratamento da conta de Produção 1150100004); aplicar **no contexto da LF**. → **Apresentar a Rafael ANTES de aplicar.**
2. Corrigir o picking type **64** → `default_location_dest_id = 31092` (LF/Materiais de Terceiros).
3. Executar as **5 etapas** com o produto piloto, validando cada NF e a contabilização (fatura + valoração de estoque).
4. Validar fechamento: Em Trânsito (26489) zera; `1150200001` zera no fim do ciclo; estoque LF e FB não inflam.

## Pendências ABERTAS (resolver com Rafael / Contador)
- **🔴 CRÍTICO — Lado FB (Etapa 5)**: a baixa dos componentes no recebimento do retorno na FB. A FB **TEM estoque próprio** → "tudo=terceiros" NÃO se aplica lá. É onde está o passivo de **R$ 785.569,62** (componentes re-inflando o estoque da FB). Mecanismo ainda a definir com o Contador.
- **Validar empiricamente** o approach de configuração (trocar as contas da categoria na LF → confirmar net-zero + MO consumindo certo) ANTES de rodar em PROD com volume. Hoje está **raciocinado, não testado**.
- Perguntas ao Contador (`PLANO_EXECUCAO.md` → "Perguntas pendentes").
- Levantar a lista exata de categorias da LF (Passo 0) — ainda não feito.

## Regras invioláveis
- NÃO reativar `rule_type=sale_purchase`.
- Entrada na LF = **picking físico (pt 64)**, NÃO DFe→PO (não é compra).
- MO em LF = criada **manualmente** (não depender de MTO/procurement cross-company — bloqueado/inexistente).
- Dados sempre do **Odoo PROD via XML-RPC** (não dados locais). Toda escrita: dry-run/apresentar antes.
- `action_gerar_po_dfe` herda company do user — se usar, forçar `allowed_company_ids=[5]`.
