# Opcao 925 — Cadastro de Usuarios

> **Modulo**: Cadastros
> **Paginas de ajuda**: 6+ paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao

Cadastra e gerencia usuarios do sistema SSW, incluindo permissoes especificas, vinculos a grupos, unidades, empresas e configuracoes de seguranca. Rastreia acessos e atividades dos usuarios.

## Quando Usar

- Cadastrar novo usuario (funcionario, cliente, conferente)
- Alterar permissoes ou dados de usuario existente
- Bloquear/desbloquear usuario
- Vincular usuario a grupo, unidade ou empresa
- Configurar gerenciamento seguro de senha
- Rastrear atividades e acessos de usuario
- Listar usuarios ativos ou gerar relatorio em Excel

## Pre-requisitos

- Apenas usuario master pode cadastrar/alterar usuarios
- Grupo deve estar cadastrado (opcao 918)
- Unidade deve existir (opcao 401) se for vincular
- Para cliente: CNPJs devem ser liberados (opcao 426)

## Campos / Interface

### Dados Basicos

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Usuario | Sim | Ate 8 caracteres, sem espacos ou caracteres especiais |
| Ativo/Bloqueado | Automatico | Situacao do usuario |
| Empresa | Condicional | Numero da empresa (multi-empresa). 0 = acesso a todas |
| Bloqueio SSW | Nao | Uso Equipe SSW. S = bloqueado (sobrecarga no sistema) |
| Nome | Sim | Nome completo |
| CPF | Sim | CPF do usuario |
| Grupo | Sim | Perfil de acesso as opcoes (opcao 918) |
| Unidade | Condicional | Unidade padrao. NAO preencher para cliente |
| Seleciona unidade | Nao | S = pode selecionar unidades de simulacao |
| Unidade de simulacao | Nao | Unidades que pode simular. Vazio + Seleciona S = todas |

### Permissoes Especificas

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Informa frete | Nao | S = informa frete na emissao CTRC (opcao 004). Permite comandar coleta sem gerenciadora, dar saida SMP rejeitado, liberar doc restrito |
| Emite CTRC Cortesia | Nao | S = emite CTRC cortesia (opcao 004) |
| Desbloqueia resultado | Nao | S = desbloqueia resultado cotacao/frete (opcao 002, 004, 469, 903). NAO sofre limitacoes opcao 399 em CTRBs transferencia |
| Usa SSWBar/SSWBalanca Modo Livre | Nao | S = digita NRs sem leitor (SSWBar) e acessa configuracoes (SSWBalanca) |
| Aponta CTRC na opc 020 | Sim | N = MODO RESTRITO (manifesto so via SSWBAR ou captura codigo barras) |
| Cadastro de clientes | Sim | Inclui, Altera, Altera com restricao, Consulta (opcoes 483, 122, 383, 384, 386, 387, 388, 389) |
| Demais cadastros | Sim | Inclui, Altera, Altera com restricao, Consulta (opcoes 026, 027, 028, 415, 423, 426) |

### Gerenciamento Seguro

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Gerenciamento seguro | Nao | S = ativa controles rigorosos de senha |
| Senha minima | Automatico | 8 caracteres (quando Gerenciamento seguro = S) |
| Senha complexa | Automatico | Letras + numeros + caracteres especiais |
| Historico senha | Automatico | Ultimas 10 senhas nao podem ser reaproveitadas |
| Forcar troca senha | Condicional | S = obriga troca no proximo login (obrigatorio se Gerenciamento seguro = S) |
| Bloqueia por | Condicional | Periodo de bloqueio automatico (obrigatorio se Gerenciamento seguro = S) |
| E-mail | Condicional | E-mail do usuario (obrigatorio se Gerenciamento seguro = S) |

## Fluxo de Uso

### Cadastro de Novo Usuario

1. Acessar opcao 925 (usuario master)
2. Informar login (ate 8 caracteres, sem espacos/caracteres especiais)
3. Preencher dados basicos: nome, CPF
4. Selecionar grupo (opcao 918)
5. Definir unidade padrao (se nao for cliente)
6. Configurar permissoes especificas (informa frete, emite cortesia, etc.)
7. Definir permissoes de cadastro (clientes e demais)
8. (Opcional) Ativar gerenciamento seguro
9. Salvar

### Alteracao de Usuario Existente

1. Acessar opcao 925
2. Buscar usuario por: Usuario, CPF, Nome, Unidade ou Grupo
3. Alterar dados necessarios
4. Salvar

### Bloqueio/Desbloqueio

1. Acessar opcao 925
2. Localizar usuario
3. Alterar campo Ativo/Bloqueado
4. Salvar

### Rastreamento de Atividades

1. No rodape, clicar em "Rastreamento"
2. Informar usuario
3. Sistema mostra todas as opcoes acessadas ao longo do dia
4. Mostra IP de origem (operadora de celular)
5. Disponivel: mes corrente + ultimos meses completos

### Listagens

- **Usuarios ativos**: rodape > Usuarios ativos (conectados no momento)
- **Relacao de usuarios**: rodape > Relacao de usuarios (todos, com hora login e ultimo acesso)
- **Relacao em Excel**: rodape > Relacao em Excel

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 918 | Grupos (vinculo de usuario a grupo) |
| 902 | Controle de acesso a relatorios gerenciais |
| 401 | Unidades (vinculo de usuario a unidade) |
| 426 | Liberar CNPJs para usuario cliente |
| 028 | Motoristas (usuario criado automaticamente, grupo 092) |
| 056 | Relatorio 146 - Rastreamento de usuarios |
| 002 | Cotacao (desbloqueia resultado) |
| 004 | Emissao CTRC (informa frete, cortesia, desbloqueia resultado) |
| 020 | Manifesto (aponta CTRC - modo livre/restrito) |
| 025 | Saida de veiculo (SMP rejeitado) |
| 003 | Coleta (comandar sem gerenciadora) |
| 224 | Documentos restritos (liberar) |
| 399 | Limitacoes CTRB transferencia |
| 469, 903 | Desbloqueia resultado |
| 483, 122, 383, 384, 386, 387, 388, 389 | Cadastro de clientes |
| 026, 027, 028, 415, 423, 426 | Demais cadastros |

## Observacoes e Gotchas

### Usuario Master

- Ate 6 usuarios master podem ser cadastrados pela Equipe SSW
- Acesso irrestrito ao sistema
- Apenas master cadastra/altera usuarios
- Sempre manter pelo menos 2 master ativos (redundancia)

### Usuarios Automaticos

- **Motorista**: criado automaticamente ao cadastrar motorista (opcao 028)
  - Login: 4 primeiros caracteres ultimo nome + 4 primeiros primeiro nome
  - Grupo: 092 SSWMobile (bloqueado para alteracao)
  - CPF: bloqueado para acesso via opcao 925

- **Conferente**: cadastrado manual na opcao 925, SSWMobile habilitado via link no rodape

### Usuario Cliente

- NAO preencher campo Unidade
- Deve ter CNPJs liberados pela opcao 426
- Acesso restrito (links de manutencao, ocorrencia, tabelas nao disponiveis)

### Multi-Empresa

- Empresa = 0: acesso a todas as empresas
- Empresa = N: acesso restrito a empresa N
- Configuracao de multi-empresa: opcao 401

### Limites de Acesso Simultaneo

- Maximo: 250 logins ativos nos ultimos 5 minutos
- Excedendo limite: bloqueio automatico por 1 hora
- Usuario master pode desbloquear antecipadamente

### Gerenciamento Seguro

Ativa controles rigorosos quando Gerenciamento seguro = S:

- Senha minima: 8 caracteres
- Senha complexa: letras + numeros + caracteres especiais
- Historico: ultimas 10 senhas nao podem ser reaproveitadas
- Forcar troca senha: obrigatorio = S
- Bloqueia por: periodo de bloqueio obrigatorio
- E-mail: obrigatorio

### Permissao "Informa Frete"

Usuario com Informa frete = S pode:

- Informar frete na emissao CTRC (opcao 004)
- Comandar coleta sem liberacao gerenciadora de risco (opcao 003)
- Dar saida de veiculo em SMP rejeitado se config = alertar (opcao 025, 903)
- Liberar documentos restritos ao cliente (opcao 004, 006, 224)

### Permissao "Desbloqueia Resultado"

Usuario com Desbloqueia resultado = S:

- Desbloqueia resultado de frete cotado (opcao 002)
- Desbloqueia resultado de frete informado (opcao 004)
- Conforme definido na opcao 469 e 903
- NAO sofre limitacoes da opcao 399 em CTRBs de transferencia

### Modo Restrito (Aponta CTRC = N)

- Manifesto (opcao 020) so pode ser emitido se:
  - Carregamento ja realizado via SSWBAR, OU
  - Carregamento com captura codigo de barras do Manifesto Operacional (opcao 020/link Codigo de barras)
- Evita apontamento manual incorreto

### Permissoes de Cadastro

2 niveis: Cadastro de clientes e Demais cadastros

Opcoes de permissao:
- **Inclui**: inclui todos os dados
- **Altera**: altera todos os dados
- **Altera com restricao**: altera apenas dados basicos (sem comprometimento financeiro/fiscal)
- **Consulta**: apenas consulta

Cadastro de clientes abrange: 483, 122, 383, 384, 386, 387, 388, 389
Demais cadastros abrange: 026, 027, 028, 415, 423, 426

### Rastreamento e Auditoria

- Opcao 925 / Rastreamento: opcoes acessadas pelo usuario ao longo do dia
- Relatorio 146 (opcao 056): estatisticas de acesso e arquivos gerados por usuario
- Relatorio 146 precisa ser liberado pelo master na opcao 902
- IP de origem registrado (util para identificar acessos remotos/suspeitos)

### Unidade de Simulacao

- Permite usuario "simular" operacao de outras unidades
- Util para: suporte, treinamento, gerencia multi-unidade
- Seleciona unidade = S + Unidade simulacao vazio = simula TODAS as unidades
- Seleciona unidade = S + Unidade simulacao informada = simula apenas as informadas
- Seleciona unidade = N = usuario fica restrito a sua unidade padrao

### Bloqueio SSW

- Uso exclusivo Equipe SSW
- S = usuario bloqueado para acesso (sobrecarga no sistema)
- N = usuario desbloqueado
- NAO confundir com campo Ativo/Bloqueado (usado pela transportadora)

### Login e Nomenclatura

- Ate 8 caracteres
- NAO usar espacos ou caracteres especiais
- Padrao sugerido: primeira letra nome + sobrenome (ex: jsilva, mferreira)
- Motorista: automatico (4 caracteres ultimo nome + 4 primeiros primeiro nome)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
