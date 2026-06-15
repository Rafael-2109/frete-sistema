# 📋 INSTRUÇÕES PARA ATUALIZAR FRETE NO RENDER

## 🚀 OPÇÃO 1: Executar Script Interativo (RECOMENDADO)

### 1️⃣ Fazer Deploy da Correção
Antes de executar, você precisa fazer deploy da correção do bug `optante_simples`:

```bash
git add .
git commit -m "Corrige campo optante_simples para optante no serviço de atualização de peso"
git push
```

Aguarde o Render fazer o deploy automático.

### 2️⃣ Executar o Script no Shell do Render

No shell do Render, execute:

```bash
python atualizar_embarque_frete_manual.py
```

Depois digite as NFs quando solicitado:

```
Digite os números das NFs (separados por vírgula ou espaço)
Exemplo: 140050, 136036
Ou pressione ENTER para sair
--------------------------------------------------------------------------------
NFs: 139906 140050
```

**O script aceita:**
- Vírgulas: `139906, 140050, 141000`
- Espaços: `139906 140050 141000`
- Misto: `139906, 140050 141000`

---

## 🚀 OPÇÃO 2: Comando de Uma Linha (Sem Deploy)

Se você **não pode fazer deploy agora**, use este comando que **não requer** a correção (pula o recálculo de frete com erro):

```bash
python << 'EOF'
from app import create_app, db
from app.faturamento.services.atualizar_peso_service import AtualizadorPesoService

# Digite as NFs aqui:
NFS = ['139906', '140050']

app = create_app()
with app.app_context():
    service = AtualizadorPesoService()

    for nf in NFS:
        print(f"\n🔄 Processando NF {nf}...")
        try:
            # Atualizar EmbarqueItem
            r1 = service._atualizar_embarque_item(nf)
            print(f"   EmbarqueItem: {r1.get('atualizados', 0)} itens, Peso: {r1.get('peso_total', 0):.2f}kg, Pallets: {r1.get('pallets_total', 0):.2f}")

            # Atualizar Embarque
            r2 = service._atualizar_embarque_totais(nf)
            print(f"   Embarque: {r2.get('atualizados', 0)} embarques")

            # Atualizar Frete (pode dar erro, mas continua)
            try:
                r3 = service._atualizar_frete(nf)
                print(f"   Frete: {r3.get('atualizados', 0)} fretes ({r3.get('recalculados', 0)} recalculados)")
            except Exception as e:
                print(f"   ⚠️ Frete: Erro ao recalcular (será corrigido no próximo deploy)")

            db.session.commit()
            print(f"   ✅ Concluído!")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            db.session.rollback()

    print("\n✅ Processo finalizado!")
EOF
```

**Edite a linha 5** para incluir suas NFs:
```python
NFS = ['139906', '140050']  # ← Altere aqui
```

---

## 📊 SAÍDA ESPERADA

### ✅ Sucesso:
```
🔄 Processando NF 139906...
   EmbarqueItem: 1 itens, Peso: 1250.50kg, Pallets: 5.25
   Embarque: 1 embarques
   Frete: 3 fretes (3 recalculados)
   ✅ Concluído!

🔄 Processando NF 140050...
   EmbarqueItem: 1 itens, Peso: 980.00kg, Pallets: 4.00
   Embarque: 1 embarques
   Frete: 2 fretes (2 recalculados)
   ✅ Concluído!

✅ Processo finalizado!
```

### ⚠️ Erro (antes do deploy):
```
   Frete: Erro ao recalcular (será corrigido no próximo deploy)
```

---

## 🔍 O QUE CADA ETAPA FAZ

1. **EmbarqueItem**:
   - Busca TODOS os produtos da NF em FaturamentoProduto
   - Calcula peso de cada produto (qtd × peso_bruto)
   - Calcula pallets de cada produto (qtd ÷ palletizacao)
   - SOMA tudo e atualiza EmbarqueItem

2. **Embarque**:
   - Soma peso e pallets de TODOS os EmbarqueItems ativos
   - Atualiza Embarque.peso_total e pallet_total

3. **Frete**:
   - Soma peso de TODAS as NFs do CNPJ no embarque
   - Atualiza Frete.peso_total
   - RECALCULA Frete.valor_cotado usando CalculadoraFrete

---

## ⚠️ IMPORTANTE

**APÓS O DEPLOY**, execute novamente o script para recalcular os fretes corretamente!

Os EmbarqueItems e Embarques já estarão corretos mesmo antes do deploy.
