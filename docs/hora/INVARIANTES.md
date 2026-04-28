# Invariantes do Módulo HORA (Lojas Motochefe)

**Data**: 2026-04-18
**Status**: contrato de design — aprovado antes de qualquer modelo SQLAlchemy.
**Origem**: `/home/rafaelnascimento/.claude/plans/toasty-snuggling-sunrise.md` (análise de primeiros princípios).

---

## Contexto

HORA é uma pessoa jurídica distinta que opera lojas físicas da marca Motochefe. Compra motos elétricas da Motochefe-distribuidora (três emissores: B2B, Laiouns, Q.P.A) e vende ao consumidor final (pessoa física, NF emitida pela própria HORA). O módulo existe para controle de estoque unitário desde o pedido até a venda, com Fase 2 futura de financeiro.

A modelagem deste módulo **não é intuitiva a partir de padrões de ERP de varejo**. Motos não são mercadorias fungíveis — cada unidade é um ativo com identidade jurídica própria (chassi atribuído pela fábrica, declarado em documento fiscal). Os invariantes abaixo derivam dos primeiros princípios do negócio, não de convenção de indústria.

---

## Os 5 invariantes

### 1. `hora_moto.chassi` é a chave de rastreamento universal do módulo.

Toda pergunta relevante do negócio é uma pergunta sobre **uma moto específica** ou sobre um **conjunto de motos específicas**. "Quanto paguei por esta moto?" "Onde esta moto está agora?" "Qual foi a margem desta moto?" "Esta moto teve divergência na conferência?" Todas respondem por chassi.

Consequência: consultas cross-tabela sempre usam `chassi` como chave de junção ou filtro. Nunca `id` sequencial de pedido/NF/venda como raiz de relatório gerencial.

### 2. Toda tabela transacional DEVE ter `chassi` como coluna indexada, FK para `hora_moto.chassi`.

Tabelas transacionais incluem (mas não se limitam a): `hora_pedido_item`, `hora_nf_entrada_item`, `hora_recebimento_conferencia`, `hora_venda_item`, `hora_moto_evento`, e na Fase 2 `hora_titulo_pagar` e `hora_titulo_receber`.

Exceções: tabelas de cadastro (`hora_loja`, `hora_modelo`, `hora_tabela_preco`) e headers puros (`hora_pedido`, `hora_nf_entrada`, `hora_recebimento`, `hora_venda`) **não** têm `chassi` — o chassi vive nos itens filhos.

Consequência: o schema resiste a refactor na Fase 2. Perguntas novas encontram o chassi onde esperam.

### 3. `hora_moto` contém APENAS atributos imutáveis da unidade física.

Colunas permitidas em `hora_moto`: `chassi` (PK), `modelo_id`, `cor`, `motor`, `ano_modelo`, `criada_em`. Atributos que são fato físico-fiscal sobre a moto e não mudam durante sua vida no sistema HORA.

Colunas PROIBIDAS em `hora_moto`: `status`, `loja_atual_id`, `preco_compra`, `preco_venda`, `data_recebimento`, `data_venda`, ou qualquer coisa que varie no tempo.

Status, localização, preço e histórico vivem em tabelas satélite (`hora_moto_evento`, `hora_recebimento_conferencia`, `hora_venda_item`, `hora_nf_entrada_item`).

Consequência: `hora_moto` é uma tabela insert-once, update-never. Toda mudança de estado é um novo registro em `hora_moto_evento`. Elimina race conditions em UPDATE e cria trilha de auditoria natural.

### 4. Estado atual da moto é uma VIEW sobre `hora_moto_evento`, não um UPDATE na linha da moto.

Para saber "onde está a moto X agora?", a consulta é:
```sql
SELECT * FROM hora_moto_evento
WHERE chassi = :chassi
ORDER BY timestamp DESC
LIMIT 1;
```

Para performance em telas de listagem, pode-se manter uma VIEW materializada `hora_moto_status_atual` refreshada por trigger ao inserir em `hora_moto_evento`. A VIEW é derivada; a fonte da verdade é a tabela de eventos.

Consequência: não existe "perder histórico por UPDATE". Toda transição (RECEBIDA, TRANSFERIDA, RESERVADA, VENDIDA, DEVOLVIDA, AVARIADA) é permanente e ordenada.

### 5. `HoraVenda.status` é uma máquina de estado fechada com transições registradas em auditoria.

Estados válidos (constantes em `app/hora/models/venda.py`):
```
COTACAO    → CONFIRMADO  (confirmar_venda; perm 'vendas/aprovar')
CONFIRMADO → FATURADO    (webhook nfe_aprovada do TagPlus)
FATURADO   → CONFIRMADO  (webhook nfe_cancelada — NFe cancelada SEFAZ)
*          → CANCELADO   (cancelar_venda; FATURADO só após NFe cancelada SEFAZ)
DANFE legado → FATURADO direto (importar_nf_saida_pdf)
```

**Reserva de chassi**: COTACAO, CONFIRMADO e FATURADO reservam o chassi (sai do estoque disponível). CANCELADO devolve via evento `DEVOLVIDA`. Implementação via eventos em `hora_moto_evento` (RESERVADA / VENDIDA / NF_EMITIDA / DEVOLVIDA), não via flag.

**Lock pessimista**: `criar_venda_manual`, `adicionar_item_pedido` e troca de chassi em `editar_item_pedido` fazem `SELECT FOR UPDATE` em `hora_moto` para impedir reserva concorrente.

**Auditoria obrigatória**: toda transição (CRIOU, CONFIRMOU, EMITIU_NFE, FATURADO, CANCELOU_NFE, NFE_CANCELADA_SEFAZ, EMITIU_CCE, CANCELOU) registra entrada em `hora_venda_auditoria` (append-only).

**Janela de cancelamento NFe**: 24h validadas localmente em `cancelador_nfe._validar_janela` — defesa em profundidade (TagPlus também valida na SEFAZ).

Detalhes do workflow: `app/hora/CLAUDE.md` seção 9.

---

## Anti-padrões explicitamente rejeitados

- **Copiar `pedido_venda_moto` / `pedido_venda_moto_item` do Motochefe-distribuidora** (`app/motochefe/models/vendas.py:120`). Aquele padrão é B2B com fungibilidade por modelo ao cliente B2B; HORA é B2C com chassi declarado ao consumidor. Modelo errado para o problema.

- **UPDATE de status na linha de `hora_moto`** como faz `app/motochefe/models/produto.py:45`. No Motochefe é aceitável porque não há múltiplas transições complexas nem multi-loja com transferência. Em HORA viola invariante 3.

- **Schema PostgreSQL separado**. Considerado e rejeitado: zero precedente no sistema, custo operacional alto (Alembic multi-schema, dumps, permissões), mesmo isolamento lógico alcançável por prefixo `hora_` + CLAUDE.md + code review.

- **Bind SQLAlchemy dedicado** (`SQLALCHEMY_BINDS['hora']`). Considerado e rejeitado pelo usuário a favor de simplicidade máxima: schema `public` compartilhado, separação por prefixo.

---

## Como este documento se comporta

- Este é um **contrato de design**, não um arquivo vivo. Alterar um invariante exige reunião formal e atualização de data.
- Toda migration, modelo SQLAlchemy, service ou route do módulo HORA **deve** respeitar os 4 invariantes. Code reviews rejeitam PRs que violam.
- `app/hora/CLAUDE.md` faz referência a este documento e resume as consequências operacionais para o dia-a-dia de desenvolvimento.

---

## Referências

- Plano de análise: `/home/rafaelnascimento/.claude/plans/toasty-snuggling-sunrise.md`
- Precedente de chassi como PK: `app/motochefe/models/produto.py:45`
- Parsers reusáveis (não duplicar): `app/carvia/services/parsers/danfe_pdf_parser.py:1418`, `app/carvia/services/pricing/moto_recognition_service.py:48`
- Plano de pedido HORA (contexto original): `.claude/plans/CONTROLE_MOTOS.md`
