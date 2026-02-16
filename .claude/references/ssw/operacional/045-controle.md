# Opcao 045 — Controle (Relatorios Pessoais / Login SSWMobile)

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra login e senha de usuario para utilizacao do SSWMobile. Logins criados aqui NAO tem acesso ao sistema SSW, apenas ao mobile.

## Quando Usar
- Liberar acesso de motorista ao SSWMobile
- Criar credenciais para veiculo/motorista
- Definir validade de acesso ao mobile

## Pre-requisitos
- Veiculo cadastrado (Opcao 026)
- Unidade definida para operacao

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| LOGIN | Sim | Login para acesso (recomendado usar placa) |
| PLACA | Sim | Placa do veiculo cadastrado (Opcao 026) |
| UNIDADE | Sim | Sigla da unidade para coletas/entregas |
| SENHA | Sim | Senha de acesso (recomendado 4 caracteres simples) |
| CONFIRMAR SENHA | Sim | Confirmacao da senha |
| VALIDADE | Sim | Validade da liberacao |

## Fluxo de Uso
1. Acessar Opcao 045
2. Informar login (ou pesquisar placa)
3. Preencher dados (placa, unidade, senha, validade)
4. Confirmar cadastro
5. Motorista usa login/senha no SSWMobile

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 026 | Cadastro de veiculos |
| 401 | Cadastro de unidades |
| SSWMobile | Aplicativo que usa este login |

## Observacoes e Gotchas

### Login NAO Acessa Sistema
Logins cadastrados por esta opcao servem **apenas para SSWMobile**, nao tendo acesso ao sistema SSW.

### Recomendacoes
- **Login**: Usar a propria placa do veiculo (facilita lembrar)
- **Senha**: Simples, 4 caracteres numericos (facilita digitacao no mobile)

### Validade
Definir validade considerando periodo de utilizacao do motorista/veiculo.
