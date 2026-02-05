# Glossario de Frete

## Componentes do Calculo

| Sigla | Nome Completo | O que e |
|-------|---------------|---------|
| GRIS | Gerenciamento de Risco | Taxa de seguro sobre valor da mercadoria |
| ADV | Ad Valorem | Taxa adicional sobre valor da mercadoria |
| RCA | Risco de Carga Aquaviaria | Seguro para cargas que passam por balsa/navio |
| TAS | Taxa de Administracao de Servico | Valor fixo cobrado por embarque |
| CTE | Conhecimento de Transporte Eletronico | Taxa pela emissao do documento fiscal de frete |
| ICMS | Imposto sobre Circulacao de Mercadorias e Servicos | Imposto estadual sobre o frete |

## Tipos de Carga

| Tipo | Quando usar | Caracteristica |
|------|-------------|----------------|
| FRACIONADA | < 26 pallets E < 20.000 kg | Calculo individual por CNPJ |
| DIRETA | >= 26 pallets OU >= 20.000 kg | Veiculo dedicado, rateio por peso |

## Veiculos (Carga DIRETA)

| Veiculo | Capacidade Tipica |
|---------|-------------------|
| VAN | ~1.500 kg |
| TOCO | ~6.000 kg |
| TRUCK | ~12.000 kg |
| CARRETA | ~25.000 kg |
| BITREM | ~37.000 kg |

## Termos de Calculo

| Termo | Significado |
|-------|-------------|
| `valor_kg` | Preco cobrado por kg de peso |
| `percentual_valor` | % cobrado sobre o valor da mercadoria |
| `frete_minimo_peso` | Peso MINIMO para calculo (nao e valor em R$) |
| `frete_minimo_valor` | Valor MINIMO do frete (piso em R$) |
| `icms_incluso` | Se True, ICMS ja esta embutido nos valores da tabela |
| `icms_proprio` | ICMS fixo da tabela (ignora ICMS da cidade) |
| `optante` | Transportadora do Simples Nacional (nao destaca ICMS) |
| `pedagio_por_fracao` | Se True, arredonda peso para cima em fracoes de 100kg |
| `lead_time` | Prazo de entrega em DIAS UTEIS |

## Frete Minimo: Peso vs Valor

**PESO** (`frete_minimo_peso`): "Cobro no minimo por X kg"
- Se a carga pesa 50kg e o minimo e 100kg, calcula como se fossem 100kg

**VALOR** (`frete_minimo_valor`): "O frete nao sai por menos de R$ X"
- Se o calculo deu R$200 e o minimo e R$350, cobra R$350

## Incoterms Relevantes

| Incoterm | Significado | Frete |
|----------|-------------|-------|
| CIF | Cost, Insurance and Freight | Frete por conta do remetente (Nacom) |
| FOB | Free on Board | Frete por conta do destinatario (cliente busca) |
| RED | Redespacho | Frete por conta do remetente (Nacom), similar a CIF |

## Grupo Empresarial

Transportadoras que pertencem ao mesmo grupo (mesmo CNPJ raiz) compartilham tabelas de frete.
A funcao `grupo_service.obter_transportadoras_grupo()` retorna todos os IDs do grupo.

FONTE: `app/utils/grupo_empresarial.py`
