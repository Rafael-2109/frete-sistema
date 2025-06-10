# 🏙️ GUIA COMPLETO - IMPORTAR CIDADES (UMA VEZ APENAS)

## 📋 **RESUMO SIMPLES:**
1. Use o Excel modelo que já existe
2. Preencha com suas cidades
3. Coloque na pasta do sistema
4. Execute 1 comando
5. Pronto!

---

## 🎯 **PASSO 1: ABRIR O EXCEL MODELO**

**Arquivo que já existe:** `modelo_cidades_20250610.xlsx`

### Abra o Excel e vá para a aba: **"Template Vazio"**
- ❌ NÃO use "Dados de Exemplo" (são só exemplos)
- ✅ USE "Template Vazio" (é onde você vai preencher)

---

## 📊 **PASSO 2: NOMES DAS COLUNAS (EXATOS)**

**IMPORTANTE:** Use EXATAMENTE estes nomes (com maiúsculas):

### ✅ **COLUNAS OBRIGATÓRIAS:**
```
CIDADE      UF      IBGE        ICMS
```

### ✅ **COLUNAS OPCIONAIS:** 
```
ISS         MICRORREGIAO        MESORREGIAO
```

### 📝 **Exemplo de linha:**
```
Goiânia     GO      5208707     7,00%     NÃO     Goiânia     Centro Goiano
```

---

## 🎯 **PASSO 3: PREENCHER O EXCEL**

### **Coluna CIDADE:**
- Nome da cidade
- Exemplo: `Goiânia`, `São Paulo`, `Rio de Janeiro`

### **Coluna UF:**
- Estado com 2 letras MAIÚSCULAS
- Exemplo: `GO`, `SP`, `RJ`, `MG`

### **Coluna IBGE:**
- Código IBGE da cidade (7 dígitos)
- Exemplo: `5208707`, `3550308`

### **Coluna ICMS:**
- Alíquota do ICMS
- Aceita: `7,00%` ou `7.00%` ou `0.07`
- Exemplo: `7,00%`, `12,00%`, `18,00%`

### **Coluna ISS (Opcional):**
- Se a cidade substitui ICMS por ISS
- Aceita: `SIM`, `S`, `NÃO`, `N`
- Pode ficar vazio

### **Colunas MICRORREGIAO e MESORREGIAO (Opcionais):**
- Podem ficar vazias
- Exemplo: `Goiânia`, `Centro Goiano`

---

## 📍 **PASSO 4: ONDE SALVAR O ARQUIVO**

### **Local:** Na mesma pasta do sistema
```
C:\Users\rafael.nascimento\Desktop\Sistema Online\frete_sistema\
```

### **Nome sugerido:** 
- `minhas_cidades.xlsx`
- `cidades_goias.xlsx` 
- `base_cidades_2024.xlsx`
- Qualquer nome que preferir

---

## ⚙️ **PASSO 5: IMPORTAR NO SISTEMA**

### **Comando:**
```bash
python importar_cidades_unico.py NOME_DO_SEU_ARQUIVO.xlsx
```

### **Exemplos:**
```bash
python importar_cidades_unico.py minhas_cidades.xlsx
python importar_cidades_unico.py cidades_goias.xlsx
python importar_cidades_unico.py base_completa.xlsx
```

---

## 📊 **EXEMPLO PRÁTICO COMPLETO**

### **1. Seu Excel (aba "Template Vazio"):**
```
CIDADE          UF    IBGE      ICMS     ISS    MICRORREGIAO    MESORREGIAO
Goiânia         GO    5208707   7,00%    NÃO    Goiânia         Centro Goiano
Anápolis        GO    5201108   7,00%    NÃO    Anápolis        Centro Goiano
Aparecida       GO    5201405   7,00%    NÃO    Goiânia         Centro Goiano
Catalão         GO    5205109   7,00%    NÃO    Catalão         Sul Goiano
```

### **2. Salvar como:** `cidades_goias.xlsx`

### **3. Executar:**
```bash
python importar_cidades_unico.py cidades_goias.xlsx
```

### **4. Resultado esperado:**
```
🏙️ === IMPORTAÇÃO ÚNICA DE CIDADES ===
📁 Arquivo: cidades_goias.xlsx
🔍 Cidades já cadastradas: 0
📖 Lendo arquivo Excel...
✅ Arquivo lido: 4 linhas encontradas
⚙️ Processando dados...
✅ === IMPORTAÇÃO CONCLUÍDA ===
🎯 Cidades importadas: 4
⚠️ Linhas com erro: 0
📊 Total no banco: 4
```

---

## 🚨 **SE DER ERRO:**

### **Erro: "Arquivo não encontrado"**
- ✅ Verifique se o arquivo está na pasta correta
- ✅ Verifique se o nome está certo (com .xlsx)

### **Erro: "Colunas obrigatórias faltando"**
- ✅ Use EXATAMENTE os nomes: `CIDADE`, `UF`, `IBGE`, `ICMS`
- ✅ Tudo em MAIÚSCULA

### **Erro: "Já existem cidades cadastradas"**
- ✅ Digite `s` para continuar mesmo assim
- ✅ Ou digite `n` para cancelar

---

## 💡 **DICAS IMPORTANTES:**

✅ **Faça backup** antes de importar  
✅ **Teste com poucas cidades** primeiro  
✅ **Use o modelo Excel** que já foi criado  
✅ **Não misture formatos** de ICMS (use sempre %)  
✅ **UF sempre maiúscula** (GO, SP, RJ)  

---

## 🎉 **RESUMO DOS ARQUIVOS:**

### **Arquivos que já existem:**
- ✅ `modelo_cidades_20250610.xlsx` - Modelo para você usar
- ✅ `importar_cidades_unico.py` - Script de importação
- ✅ `verificar_modelo.py` - Mostra exemplo

### **Arquivo que você vai criar:**
- 📝 `SEU_ARQUIVO.xlsx` - Com suas cidades

---

## 📞 **SE PRECISAR DE AJUDA:**

Execute para ver exemplo:
```bash
python verificar_modelo.py
```

Execute para ver ajuda do importador:
```bash
python importar_cidades_unico.py
```

**🎯 É isso! Super simples: Excel + 1 comando = Todas as cidades importadas!** 