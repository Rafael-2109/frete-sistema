# Opção 491 — E-mails e Telefones da Unidade

> **Módulo**: Comercial
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Cadastro de e-mails e telefones de identificação da unidade e seus setores (comercial, coleta, pendência, entrega, cobrança, compras, salvados).

## Quando Usar
Necessário para configurar contatos específicos de cada setor da unidade, utilizados em processos automatizados de envio de e-mails, relatórios, EDI e identificação de remetente em comunicações com clientes e fornecedores.

## Pré-requisitos
- Unidade cadastrada na opção 401
- Para multiempresas, matriz contábil definida em opção 401/Matriz contábil

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade | Sim | Sigla da unidade (opção 401) para realizar o cadastro |
| Geral (telefone/e-mail) | Não | Telefone e e-mail geral da unidade |
| Comercial (telefone/e-mail) | Não | Contato da área comercial (opção 002, tabelas de fretes) |
| Coleta (telefone/e-mail) | Não | Contato da área de coleta (opção 001) |
| Pendência (telefone/e-mail) | Não | Contato da área de pendência |
| Entrega (telefone/e-mail) | Não | Contato da área de entregas (opção 383) |
| Cobrança (telefone/e-mail) | Não | Contato da área de cobrança |
| Compras (telefone/e-mail) | Não | Contato da área de compras (opções 157 e 158) |
| Salvados (telefone/e-mail) | Não | Contato da área de salvados |

## Fluxo de Uso

1. Escolher uma unidade (opção 401)
2. Preencher telefone e e-mail para cada setor conforme necessidade
3. Dados são utilizados automaticamente pelo sistema em ordem de prioridade de busca

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 401 | Cadastro de unidades — origem dos dados de unidade |
| 401/Matriz contábil | Define matriz para multiempresas (telefones/e-mails da matriz) |
| 903/Site, e-mail e telefones | Fallback setores da transportadora (2ª prioridade) e geral (4ª prioridade) |
| 925 | E-mail e telefone individual do usuário |
| 139 | Localiza funcionários e permite autocadastramento |
| 002 | Área comercial — usa contato cadastrado |
| 001 | Coleta — usa contato cadastrado |
| 383 | Entregas — usa contato cadastrado |
| 157, 158 | Compras — usa contato cadastrado |

## Observações e Gotchas

- **Hierarquia de busca**: E-mails e telefones são buscados na seguinte ordem de prioridades (primeiro que encontrar):
  1. **Opção 491** — Setores da unidade (este cadastro)
  2. **Opção 903/Site, e-mail e telefones** — Setores da transportadora
  3. **Opção 401** — Dados gerais da unidade
  4. **Opção 903/Site, e-mail e telefones** — Geral da transportadora

- **Multiempresas**: Para transportadoras com múltiplas empresas (opção 401), telefones e e-mails das respectivas matrizes devem estar cadastrados nas unidades definidas pela opção 401/Matriz contábil

- **Identificação individual**: Processos que exigem identificação do usuário específico utilizam opção 925 (não esta)

- **Setores não cadastrados**: Se um setor não tiver contato cadastrado na opção 491, o sistema buscará nas opções 903 e 401 conforme hierarquia acima
