<!-- doc:meta
tipo: how-to
camada: L2
sot_de: Como usar o ExtratorCNPJ (service + script) para extrair CNPJ de planilhas Excel
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 📋 EXTRATOR DE CNPJ DE PLANILHAS EXCEL

> **Papel:** Guia de uso do `ExtratorCNPJ` (service e script CLI) para localizar e extrair CNPJ de múltiplas planilhas Excel via 3 padrões de busca.

Sistema inteligente para buscar CNPJ em múltiplas planilhas Excel usando 3 padrões diferentes.

---

## Indice

- [Padrões de Busca](#-padrões-de-busca)
- [Como Usar](#-como-usar)
- [Estrutura do Resultado](#-estrutura-do-resultado)
- [Exportação de Resultados](#-exportação-de-resultados)
- [Funcionalidades Especiais](#-funcionalidades-especiais)
- [Modo Debug](#-modo-debug)
- [Exemplo Completo de Uso Real](#-exemplo-completo-de-uso-real)
- [Observações Importantes](#️-observações-importantes)
- [Integração com Carga Inicial](#-integração-com-carga-inicial)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 PADRÕES DE BUSCA

### **Padrão 1: Célula ao lado de "CNPJ"**
```
| CNPJ:  | 12.345.678/0001-90 |   ← Busca à direita
| CNPJ   | 12345678000190     |   ← Busca à direita
```

Ou:
```
| CNPJ:              |
| 12.345.678/0001-90 |   ← Busca abaixo
```

### **Padrão 2: CNPJ colado (sem espaço)**
```
"CNPJ12.345.678/0001-90"
"CNPJ12345678000190"
"C.N.P.J.12345678000190"
```

### **Padrão 3: Máscara ##.###.###/####-##**
Busca qualquer texto com a máscara de CNPJ:
```
"Empresa XYZ - CNPJ: 12.345.678/0001-90"
"Cliente: ABC (12.345.678/0001-90)"
"12.345.678/0001-90"
```

---

## 🚀 COMO USAR

### **1. Via Script de Linha de Comando**

```bash
# Processar todas planilhas de uma pasta
python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta

# Processar arquivos específicos
python3 scripts/extrair_cnpj_planilhas.py arquivo1.xlsx arquivo2.xls arquivo3.xlsx

# Com modo debug (mostra logs detalhados)
python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta --debug

# Exportar resultados para Excel
python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta --output resultados.xlsx

# Exportar resultados para CSV
python3 scripts/extrair_cnpj_planilhas.py /caminho/para/pasta --output resultados.csv
```

### **2. Via Código Python**

```python
from app.motochefe.services.extrator_cnpj_planilhas import ExtratorCNPJ

# Criar extrator
extrator = ExtratorCNPJ()

# Lista de arquivos
arquivos = [
    '/pasta/planilha1.xlsx',
    '/pasta/planilha2.xls',
    '/pasta/planilha3.xlsx'
]

# Buscar CNPJs
resultados = extrator.buscar_cnpj_em_multiplas_planilhas(arquivos)

# Processar resultados
for resultado in resultados:
    if resultado['sucesso']:
        print(f"Arquivo: {resultado['arquivo']}")
        print(f"CNPJ: {resultado['cnpj_formatado']}")
        print(f"Padrão: {resultado['padrao']}")
        print(f"Localização: {resultado['aba']} - {resultado['celula']}")
    else:
        print(f"Erro em {resultado['arquivo']}: {resultado['erro']}")

# Exportar para Excel
extrator.exportar_resultados_excel(resultados, 'cnpjs_encontrados.xlsx')
```

### **3. Processamento Avançado**

```python
from app.motochefe.services.extrator_cnpj_planilhas import ExtratorCNPJ
from pathlib import Path

extrator = ExtratorCNPJ()
extrator.ativar_debug()  # Ver logs detalhados

# Processar apenas 1 arquivo
resultado = extrator.buscar_cnpj_em_arquivo('/pasta/planilha.xlsx')

if resultado['sucesso']:
    print(f"✅ CNPJ: {resultado['cnpj_formatado']}")
    print(f"📋 Padrão usado: {resultado['padrao']}")
    print(f"📄 Aba: {resultado['aba']}")
    print(f"📍 Célula: {resultado['celula']}")
    print(f"📝 Valor original: {resultado['valor_original']}")
else:
    print(f"❌ {resultado['erro']}")
```

---

## 📊 ESTRUTURA DO RESULTADO

Cada arquivo processado retorna um dicionário com:

```python
{
    'arquivo': 'planilha.xlsx',                  # Nome do arquivo
    'caminho_completo': '/caminho/completo/...',  # Caminho absoluto
    'cnpj': '12345678000190',                    # CNPJ sem máscara (14 dígitos)
    'cnpj_formatado': '12.345.678/0001-90',      # CNPJ formatado
    'padrao': 'Padrão 1: Célula ao lado...',     # Padrão usado
    'aba': 'Dados',                              # Nome da aba
    'celula': 'B5',                              # Célula onde foi encontrado
    'valor_original': '12.345.678/0001-90',      # Valor original da célula
    'sucesso': True,                             # Status da busca
    'erro': None                                 # Mensagem de erro (se houver)
}
```

---

## 📁 EXPORTAÇÃO DE RESULTADOS

### **Excel (.xlsx)**
```python
extrator.exportar_resultados_excel(resultados, 'saida.xlsx')
```

Gera planilha com colunas:
- arquivo
- cnpj
- cnpj_formatado
- padrao
- aba
- celula
- sucesso
- erro

### **CSV (.csv)**
```python
extrator.exportar_resultados_csv(resultados, 'saida.csv')
```

Mesmas colunas, formato CSV com UTF-8 BOM (compatível com Excel).

---

## 🔍 FUNCIONALIDADES ESPECIAIS

### **Validação de CNPJ**
```python
extrator = ExtratorCNPJ()

# Validar se tem 14 dígitos
valido = extrator.validar_cnpj('12.345.678/0001-90')  # True
valido = extrator.validar_cnpj('123456')               # False
```

### **Limpar CNPJ**
```python
# Remove caracteres especiais
cnpj_limpo = extrator.limpar_cnpj('12.345.678/0001-90')
# Resultado: '12345678000190'
```

### **Formatar CNPJ**
```python
# Formata CNPJ no padrão ##.###.###/####-##
cnpj_formatado = extrator.formatar_cnpj('12345678000190')
# Resultado: '12.345.678/0001-90'
```

---

## 🐛 MODO DEBUG

Ativa logs detalhados do processo:

```python
extrator = ExtratorCNPJ()
extrator.ativar_debug()

# Agora verá logs como:
# [DEBUG] [Padrão 1] Buscando em aba 'Dados'...
# [DEBUG]   Palavra-chave encontrada em (5, 2): 'CNPJ:'
# [DEBUG] ✅ CNPJ encontrado com Padrão 1: 12.345.678/0001-90
```

Ou via linha de comando:
```bash
python3 scripts/extrair_cnpj_planilhas.py /pasta --debug
```

---

## 📈 EXEMPLO COMPLETO DE USO REAL

```python
#!/usr/bin/env python3
"""
Exemplo: Processar 100 planilhas de clientes
"""
from app.motochefe.services.extrator_cnpj_planilhas import ExtratorCNPJ
from pathlib import Path

# Criar extrator
extrator = ExtratorCNPJ()

# Buscar todos arquivos Excel em uma pasta
pasta = Path('/meu/projeto/planilhas_clientes')
arquivos_excel = list(pasta.glob('**/*.xlsx'))  # Busca recursiva

print(f"Encontrados {len(arquivos_excel)} arquivos")

# Processar em lote
resultados = extrator.buscar_cnpj_em_multiplas_planilhas(
    [str(f) for f in arquivos_excel]
)

# Filtrar apenas sucessos
cnpjs_encontrados = [r for r in resultados if r['sucesso']]
cnpjs_nao_encontrados = [r for r in resultados if not r['sucesso']]

print(f"\n✅ CNPJs encontrados: {len(cnpjs_encontrados)}")
print(f"❌ CNPJs não encontrados: {len(cnpjs_nao_encontrados)}")

# Exportar
extrator.exportar_resultados_excel(resultados, 'relatorio_cnpjs.xlsx')

# Criar dicionário arquivo → CNPJ
mapa_cnpj = {
    r['arquivo']: r['cnpj_formatado']
    for r in cnpjs_encontrados
}

# Usar CNPJs para importação
for arquivo, cnpj in mapa_cnpj.items():
    print(f"{arquivo} → {cnpj}")
    # Aqui você pode usar o CNPJ para vincular dados, etc.
```

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

### **Prioridade de Busca**
O sistema busca na seguinte ordem:
1. **Padrão 1** (célula ao lado) - MAIS CONFIÁVEL
2. **Padrão 2** (CNPJ colado)
3. **Padrão 3** (regex máscara) - MENOS CONFIÁVEL

Para na primeira ocorrência encontrada em qualquer aba.

### **Múltiplas Abas**
- Processa todas as abas do arquivo
- Para na primeira aba que encontrar CNPJ
- Ordem de processamento = ordem das abas no Excel

### **Validação**
- **Valida apenas quantidade de dígitos** (14 dígitos)
- **NÃO valida dígitos verificadores** (seria necessário algoritmo específico)
- Se precisar validação completa, adicione biblioteca `validate-docbr`

### **Performance**
- Lê arquivo completo na memória
- Para arquivos muito grandes (>100MB), considere otimizações
- Processa ~10-20 arquivos/segundo (depende do tamanho)

---

## 🔧 INTEGRAÇÃO COM CARGA INICIAL

Pode usar este extrator **antes** da importação para mapear CNPJs:

```python
from app.motochefe.services.extrator_cnpj_planilhas import ExtratorCNPJ
from app.motochefe.services.importacao_carga_inicial import ImportacaoCargaInicialService

# 1. Extrair CNPJs de planilhas antigas
extrator = ExtratorCNPJ()
resultados = extrator.buscar_cnpj_em_multiplas_planilhas([...])

# 2. Criar mapeamento
mapa_cnpj = {r['arquivo']: r['cnpj'] for r in resultados if r['sucesso']}

# 3. Usar na importação
# (Adicionar CNPJ às linhas da planilha de importação)
```

---

## 📞 TROUBLESHOOTING

### "Nenhum CNPJ encontrado"
- ✅ Verificar se CNPJ está visível (não oculto)
- ✅ Verificar se está em aba não protegida
- ✅ Tentar modo debug para ver onde está procurando
- ✅ Verificar se formato está correto (14 dígitos)

### "Erro ao processar arquivo"
- ✅ Arquivo pode estar corrompido
- ✅ Senha protegido
- ✅ Formato não suportado (.xlsb, .ods)
- ✅ Verificar extensão real do arquivo

### CNPJ errado encontrado
- ⚠️ Se houver múltiplos CNPJs na planilha, pega o primeiro
- ⚠️ Validar resultado manualmente
- ⚠️ Considerar adicionar filtros adicionais

---

**FIM DA DOCUMENTAÇÃO**
