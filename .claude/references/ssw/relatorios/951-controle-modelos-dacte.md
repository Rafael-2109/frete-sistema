# Opção 951 — Modelos Padrões de DACTEs

> **Módulo**: Sistema (Controle)
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Define os modelos de DACTEs (Documento Auxiliar do CT-e) a serem utilizados pela transportadora, incluindo modelo padrão e modelos específicos por cliente, tipo de documento ou mercadoria.

## Quando Usar
- Definir modelo padrão de DACTE para transportadora
- Configurar modelos específicos por cliente pagador
- Configurar modelos por tipo de documento fiscal
- Configurar modelos por tipo de mercadoria
- Cadastrar imagem para modelo 04 (marketing)
- Configurar marcas d'água para identificação de situações

## Pré-requisitos
- Para modelo 04: imagem JPG 737x272 pixels

## Modelos Disponíveis

### Modelo 01
1 DACTE por folha A4

### Modelos 02 e 03
- **Modelo 02**: 2 DACTEs do mesmo CTRC por folha A4
- **Modelo 03**: 2 DACTEs de CTRCs diferentes por folha A4

### Modelo 04
1 DACTE com imagem e termo de conformidade por folha A4
- **(1)**: área de impressão da imagem (gravar via opção 951, link imagem)
- **(2)**: linha de corte para separar Comprovante de Entrega do DACTE

### Modelos 05 e 06
- **Modelo 05**: 2 DACTEs do mesmo CTRC com declaração 1 por folha A4
- **Modelo 06**: 2 DACTEs de CTRCs diferentes com declaração 1 por folha A4

### Modelos 07 e 08
- **Modelo 07**: 2 DACTEs do mesmo CTRC Reversa por folha A4
- **Modelo 08**: 2 DACTEs de CTRCs Reversa diferentes por folha A4

### Modelo 09
1 DACTE similar ao modelo 02 em meia folha A4. Meia página fica sem impressão

### Modelos 10 e 11
- **Modelo 10**: 2 DACTEs do mesmo CTRC com declaração 2 por folha A4
- **Modelo 11**: 2 DACTEs de CTRCs diferentes com declaração 2 por folha A4

### Modelos 12 e 13
- **Modelo 12**: 2 DACTEs do mesmo CTRC com declaração 3 por folha A4
- **Modelo 13**: 2 DACTEs de CTRCs diferentes com declaração 3 por folha A4

### Modelos 14 e 15
- **Modelo 14**: 2 DACTEs do mesmo CTRC com declaração modelo Natura por folha A4
- **Modelo 15**: 2 DACTEs de CTRCs diferentes com declaração modelo Natura por folha A4

### Modelo 16
1 DACTE por folha A4 inteira com modelo GOL

### Modelo 17
2 DACTEs do mesmo CTRC por folha A4 com componentes do frete e impostos ocultados no segundo DACTE

## Campos / Interface

### Tela

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Modelo de DACTE padrão** | Sim | Modelo padrão para transportadora |
| **Imagem padrão** | Não | Imagem a ser utilizada no modelo 04 |

### Uso Diferenciado

Permite configurar modelos específicos por parâmetros:

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Prioridade** | Sim | Numérica 1-99. Maior prioridade é utilizada quando múltiplos modelos disponíveis |
| **Cliente pagador (opc)** | Não | Cliente pagador no CT-e |
| **Tipo documento (opc)** | Não | Tipo de documento fiscal do CT-e |
| **Mercadoria (opc)** | Não | Tipo de mercadoria do CT-e |
| **Modelo de DACTE** | Sim | Modelo escolhido para impressão individual (opção 101) |
| **Imagem** | Não | Link para capturar imagem modelo 04 (JPG 737x272 pixels) |

## Fluxo de Uso

### Definir Modelo Padrão

1. Acesse opção 951
2. Selecione "Modelo de DACTE padrão"
3. Confirme

### Configurar Modelo Específico

1. Acesse opção 951
2. Na seção "Uso diferenciado":
   - Informe prioridade (1-99)
   - Informe cliente pagador (opcional)
   - Informe tipo documento (opcional)
   - Informe mercadoria (opcional)
   - Selecione modelo de DACTE
3. Se modelo 04, clique em link "Imagem" e faça upload (JPG 737x272 pixels)
4. Confirme

### Upload de Imagem (Modelo 04)

1. Preparar imagem JPG 737x272 pixels
2. Na configuração do modelo 04, clicar em link "Imagem"
3. Fazer upload
4. Confirme

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 101 | Impressão individual de DACTE usando modelo configurado |

## Observações e Gotchas

### Tamanho Meia Página A4
- Modelos 02-03, 05-08, 10-15, 17: meia página A4
- **Impressão duplicada**: existe modelo para 2 DACTEs iguais na mesma página
- **Impressão associada a documentos** (fatura, manifesto, romaneio): não duplica, mesmo que modelo seja duplicado

### Prioridade
- Quando múltiplos modelos disponíveis, **maior** prioridade é utilizada
- Escala: 1 a 99

### Parâmetros Opcionais
- Cliente pagador, tipo documento, mercadoria: todos opcionais
- Quanto mais específico, maior deve ser a prioridade

### Imagem Modelo 04
- Formato: **JPG**
- Dimensão: **737x272 pixels** (exata)
- Área **(1)** na imagem: marketing
- Linha **(2)**: corte para separar comprovante

### Marcas d'Água
- Utilizadas para identificar situação específica
- Facilita identificação visual
- Configuração por parâmetros (cliente, documento, mercadoria)

### Impressão Individual vs Associada
- **Individual** (opção 101): respeita modelo duplicado
- **Associada** (fatura, manifesto, romaneio): sempre simples, mesmo se modelo duplicado

### Modelo Duplicado
- Imprime 2 DACTEs iguais na mesma página A4
- Útil para: via transportadora + via cliente
- Exemplo: modelo 02 (2 do mesmo CTRC)

### Modelo Diferenciado
- Imprime 2 DACTEs de CTRCs diferentes na mesma página
- Exemplo: modelo 03 (2 CTRCs diferentes)

### Ocultação de Valores (Modelo 17)
- Segundo DACTE oculta componentes de frete e impostos
- Útil para privacidade de valores

### Declarações
- Modelos com declaração: 05-06 (decl 1), 10-11 (decl 2), 12-13 (decl 3), 14-15 (Natura)
- Texto da declaração específico de cada modelo

### Reversa
- Modelos específicos para operação reversa: 07-08
- Formatação diferenciada para este tipo de operação

### GOL
- Modelo 16: específico com identidade visual GOL
- Folha A4 inteira
