# IA Trainer - Sistema de Ensino do Claude

## Visao Geral

O IA Trainer permite que voce **ensine o Claude** a responder novas perguntas sem precisar codificar manualmente. Atraves de uma interface visual, voce:

1. Seleciona uma pergunta que o sistema nao conseguiu responder
2. Decompoe a pergunta em partes explicando cada termo
3. O Claude gera codigo automaticamente
4. Voce debate e refina o codigo gerado
5. Testa e valida antes de ativar
6. Ativa e a pergunta passa a ser respondida!

**Criado em:** 23/11/2025

---

## Como Acessar

```
/claude-lite/trainer/
```

Acesso restrito a **administradores**.

---

## Fluxo de Ensino

```
┌─────────────────────────────────────────────────────────────────┐
│                         FLUXO DO IA TRAINER                      │
└─────────────────────────────────────────────────────────────────┘

1. PERGUNTA NAO RESPONDIDA
   "Tem item parcial pendente pro Atacadao 183?"
                    │
                    ▼
2. DECOMPOSICAO (voce explica)
   ┌─────────────────────────────────────────────────┐
   │ Parte 1: "item parcial pendente"                │
   │   Significa: Item com parte faturada e parte    │
   │              ainda na carteira                  │
   │   Tipo: filtro                                  │
   │   Condicao: qtd_saldo > 0 AND qtd > qtd_saldo  │
   ├─────────────────────────────────────────────────┤
   │ Parte 2: "Atacadao 183"                         │
   │   Significa: Nome do cliente                    │
   │   Tipo: entidade (cliente)                      │
   │   Campo: raz_social_red                         │
   └─────────────────────────────────────────────────┘
                    │
                    ▼
3. GERACAO DE CODIGO (Claude gera)
   {
     "tipo_codigo": "filtro",
     "nome": "item_parcial_pendente",
     "gatilhos": ["parcial pendente", "item parcial"],
     "definicao_tecnica": "CarteiraPrincipal.qtd_saldo > 0 AND ...",
     ...
   }
                    │
                    ▼
4. DEBATE (voce refina)
   - "E se o cliente nao existir?"
   - "Precisa filtrar por status?"
   - Claude ajusta conforme feedback
                    │
                    ▼
5. TESTE
   - Valida campos e tabelas
   - Executa com timeout
   - Mostra resultado
                    │
                    ▼
6. ATIVACAO
   - Codigo salvo no banco
   - Pergunta marcada como solucionada
   - Proxima vez FUNCIONA!
```

---

## Estrutura do Modulo

```
app/claude_ai_lite/ia_trainer/
│
├── __init__.py           # Exports
├── models.py             # Modelos do banco
├── routes.py             # Rotas/endpoints
├── README.md             # Esta documentacao
│
└── services/
    ├── __init__.py
    ├── codebase_reader.py   # Acesso ao codigo-fonte
    ├── code_validator.py    # Validacao de seguranca
    ├── code_executor.py     # Execucao controlada
    ├── code_generator.py    # Geracao via Claude
    └── trainer_service.py   # Orquestracao do fluxo
```

---

## Modelos de Dados

### CodigoSistemaGerado

Codigo gerado pelo Claude atraves do ensino.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| nome | String | Identificador unico (snake_case) |
| tipo_codigo | String | filtro, loader, prompt, conceito, entidade |
| dominio | String | carteira, estoque, fretes, etc |
| gatilhos | JSON | Palavras que ativam este codigo |
| definicao_tecnica | Text | Codigo ou expressao |
| descricao_claude | Text | Descricao para o Claude usar |
| ativo | Boolean | Se esta sendo usado |
| validado | Boolean | Se passou nos testes |
| versao_atual | Integer | Numero da versao |

### VersaoCodigoGerado

Historico de versoes (nada e substituido sem historico).

### SessaoEnsinoIA

Sessao de ensino do inicio ao fim.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| pergunta_original | Text | Pergunta que gerou a sessao |
| decomposicao | JSON | Partes explicadas pelo usuario |
| historico_debate | JSON | Mensagens de debate |
| status | String | iniciada, decomposta, codigo_gerado, etc |
| solucao_criada | Boolean | Se foi concluido com sucesso |

---

## Roteiro de Seguranca

O Claude segue regras rigorosas ao gerar codigo:

### O que PODE gerar:
- Filtros ORM
- Queries complexas com JOINs
- Loaders de dados
- Capacidades de consulta
- Novas entidades e conceitos

### O que NAO PODE gerar:
- Codigo que altera dados (INSERT, UPDATE, DELETE)
- Imports perigosos (os, subprocess, etc)
- Acesso a arquivos do sistema
- Conexoes de rede
- Loops infinitos

### Validacoes automaticas:
- Todos os Models referenciados devem existir
- Todos os campos referenciados devem existir
- Timeout de 2 segundos em execucoes
- Limite de 1000 registros por consulta

---

## API Endpoints

### Perguntas
```
GET  /claude-lite/trainer/api/perguntas
GET  /claude-lite/trainer/api/perguntas/estatisticas
```

### Sessoes
```
POST /claude-lite/trainer/api/sessao/iniciar
GET  /claude-lite/trainer/api/sessao/<id>
POST /claude-lite/trainer/api/sessao/<id>/sugerir-decomposicao
POST /claude-lite/trainer/api/sessao/<id>/decomposicao
POST /claude-lite/trainer/api/sessao/<id>/gerar
POST /claude-lite/trainer/api/sessao/<id>/debater
POST /claude-lite/trainer/api/sessao/<id>/testar
POST /claude-lite/trainer/api/sessao/<id>/ativar
POST /claude-lite/trainer/api/sessao/<id>/cancelar
GET  /claude-lite/trainer/api/sessoes
```

### Codigos
```
GET  /claude-lite/trainer/api/codigos
POST /claude-lite/trainer/api/codigos/<id>/toggle
```

---

## Scripts de Migracao

Antes de usar, execute:

```bash
python scripts/migrations/criar_tabelas_ia_trainer.py
```

Ou no Render:
```sql
-- Execute o conteudo de:
scripts/migrations/criar_tabelas_ia_trainer.sql
```

---

## Exemplo Pratico

### Pergunta: "Tem item parcial pendente pro Atacadao 183?"

**1. Acesse:** `/claude-lite/trainer/`

**2. Clique em "Ensinar"** na pergunta

**3. Decomponha:**

| Parte | Explicacao | Tipo | Campo |
|-------|------------|------|-------|
| item parcial pendente | Item com parte faturada e parte na carteira | filtro | - |
| Atacadao 183 | Nome do cliente | entidade | raz_social_red |

**4. Clique "Gerar Codigo"**

O Claude gera:
```json
{
  "tipo_codigo": "filtro",
  "nome": "item_parcial_pendente",
  "gatilhos": ["parcial pendente", "item parcial", "pendencia parcial"],
  "definicao_tecnica": "CarteiraPrincipal.qtd_saldo_produto_pedido > 0 AND CarteiraPrincipal.qtd_produto_pedido > CarteiraPrincipal.qtd_saldo_produto_pedido",
  "models_referenciados": ["CarteiraPrincipal"],
  "campos_referenciados": ["qtd_saldo_produto_pedido", "qtd_produto_pedido"],
  "descricao_claude": "Filtra itens onde parte foi faturada mas ainda resta quantidade na carteira"
}
```

**5. Debate (se necessario):**
- "E se o saldo for zero?"
- "Precisa verificar sincronizado_nf?"

**6. Teste e Ative!**

---

## Proximos Passos

- [ ] Integracao dos codigos gerados no fluxo principal do Claude AI Lite
- [ ] Interface para visualizar e editar codigos existentes
- [ ] Metricas de uso dos codigos gerados
- [ ] Export/import de codigos entre ambientes
