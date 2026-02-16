# Opcao 525 — Relacionamento com Clientes

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Relaciona clientes em relatorio com aplicacao de diversos filtros. Permite segmentar base de clientes por informacoes cadastrais, comerciais e operacionais. Opcao 461 gera o relatorio, enquanto opcao 525 permite cadastrar CNAE.

## Quando Usar
- Segmentar clientes por criterios multiplos (ABC, vendedor, cidade, segmento)
- Gerar listas de aniversariantes (contatos)
- Identificar clientes com/sem ocorrencias comerciais em periodo
- Localizar clientes com/sem movimento operacional
- Gerar etiquetas de mailing
- Cadastrar CNAE (Classificacao Nacional de Atividades Economicas) do cliente

## Pre-requisitos
- Clientes cadastrados com dados completos
- Vendedores cadastrados (se filtrar por vendedor)
- Unidades cadastradas (se filtrar por unidade)
- Segmentos cadastrados (opcao 483/CLIENTE)
- CNAEs cadastrados (opcao 525) se for filtrar por atividade economica

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade | Nao* | Unidade responsavel do cliente (MTZ pode omitir = todas) |
| Vendedor | Nao | Codigo do vendedor |
| Curva ABC | Nao | A, B, C ou todos |
| Tipo | Nao | Comum, Especial ou todos |
| Da cidade | Nao | Cidade e UF do cliente |
| Aniversario dos contatos | Nao | Periodo de aniversario dos contatos |
| Com ocorrencia | Nao | Periodo de registro de ocorrencias (opcao 483/OCORRENCIAS) |
| Do usuario | Nao | Filtra ocorrencias por usuario (ex: vendedor) |
| Sem ocorrencia | Nao | Periodo de inexistencia de ocorrencias (opcao 483/OCORRENCIAS) |
| Com movimento | Nao | Periodo de emissao de CTRCs (cliente como pagador) |
| Sem movimento | Nao | Periodo sem emissao de CTRCs (cliente como pagador) |
| Tabelas de fretes | Nao | Com tabelas, sem tabelas ou ambas |
| Segmento | Nao | Segmento cadastrado (opcao 483/CLIENTE) |
| Atividade economica CNAE | Nao | Ate 10 codigos CNAE (proprio cliente, compra ou vende) |
| Tipo de impressao | Sim | RELATORIO ou ETIQUETA |
| Incluir no relatorio | Nao | Contatos e/ou ocorrencias |

*Obrigatorio para usuarios de unidade (opcional para MTZ)

## Fluxo de Uso
1. Acessar opcao 461 (relacionamento com clientes)
2. Definir filtros desejados:
   - Cadastrais: unidade, vendedor, ABC, tipo, cidade, segmento, CNAE
   - Comerciais: aniversario, com/sem ocorrencia, usuario
   - Operacionais: com/sem movimento, tabelas de fretes
3. Escolher tipo de impressao (relatorio ou etiqueta)
4. Opcionalmente incluir contatos e/ou ocorrencias no relatorio
5. Executar relatorio

### Cadastrar CNAE (opcao 525)
1. Acessar opcao 525
2. Cadastrar CNAE do cliente (nivel de GRUPO da classificacao CNAE)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 461 | Geracao do relatorio (opcao atual) |
| 525 | Cadastramento de CNAE do cliente |
| 483 | Cadastro de clientes, segmentos e ocorrencias |

## Observacoes e Gotchas

### Tipos de Informacao
- **Cadastrais**: dados do cadastro do cliente (localizacao, classificacao atividade, aniversariantes)
- **Comerciais**: informacoes gravadas por vendedor (relatorio de visitas), reajustes de tabelas automaticas
- **Operacionais**: ultimo movimento, sem movimento, etc.

### Filtros Importantes
- **Unidade**: usuarios MTZ podem omitir (considera todas as unidades)
- **CNAE**: usa nivel de GRUPO da classificacao CNAE, pode informar ate 10 codigos
  - Codigos podem ser do proprio cliente, de quem ele compra ou para quem ele vende
- **Com/Sem ocorrencia**: ocorrencias sao registradas via opcao 483/OCORRENCIAS
- **Com/Sem movimento**: movimento = emissao de CTRCs tendo cliente como pagador
- **Usuario**: permite filtrar ocorrencias por usuario especifico (ex: vendedor)

### Impressao
- **Relatorio**: formato padrao de relatorio
- **Etiqueta**: formato de etiqueta de mailing (ajustes via Equipe SSW)
- **Incluir**: pode adicionar contatos e/ou ocorrencias no relatorio

### CNAE
- **Cadastramento**: opcao 525 permite cadastrar CNAE do cliente
- **Nivel GRUPO**: sistema usa nivel de GRUPO da classificacao CNAE
- **Multiplos codigos**: ate 10 CNAEs podem ser informados como filtro
