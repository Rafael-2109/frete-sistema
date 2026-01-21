"""
Script de teste para verificar extração de data_credito do CNAB.

Testa:
1. Extração da posição 295:301 (base 0) do arquivo CNAB
2. Comparação entre data_ocorrencia (111-116) e data_credito (296-301)

Uso:
    source .venv/bin/activate
    python scripts/migrations/test_data_credito_extraction.py

Data: 2026-01-21
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.financeiro.services.cnab400_parser_service import Cnab400ParserService


def criar_linha_teste(data_ocorrencia: str, data_credito: str, valor: str, nf_parcela: str) -> str:
    """
    Cria uma linha CNAB de 400 caracteres para teste.

    Layout BMP 274:
    - 0: Tipo registro = '1'
    - 1-2: Tipo inscrição = '02' (CNPJ)
    - 3-16: CNPJ pagador
    - 108-109: Código ocorrência = '06' (liquidação)
    - 110-115: Data ocorrência (DDMMAA)
    - 116-125: Seu número (NF/Parcela)
    - 253-265: Valor pago
    - 295-300: Data crédito (DDMMAA)
    """
    linha = ['0'] * 400

    # Tipo registro
    linha[0] = '1'

    # Tipo inscrição (CNPJ)
    linha[1:3] = list('02')

    # CNPJ pagador (exemplo)
    cnpj = '61724241000178'
    linha[3:17] = list(cnpj)

    # Código ocorrência (06 = liquidação)
    linha[108:110] = list('06')

    # Data ocorrência (posição 110-116, base 0 = 111-116 base 1)
    linha[110:116] = list(data_ocorrencia)

    # Seu número - NF/Parcela (posição 116-126)
    seu_numero = nf_parcela.ljust(10)
    linha[116:126] = list(seu_numero)

    # Valor pago (posição 253-266, 13 dígitos com 2 decimais implícitos)
    valor_formatado = valor.zfill(13)
    linha[253:266] = list(valor_formatado)

    # Data crédito (posição 295-301, base 0 = 296-301 base 1)
    linha[295:301] = list(data_credito)

    return ''.join(linha)


def main():
    print("\n" + "="*60)
    print("TESTE: Extração de data_credito do CNAB")
    print("="*60)

    parser = Cnab400ParserService()

    # Criar linha de teste simulando NF 142941/1 com valor 1.778,47
    # data_ocorrencia = 19/01/2026 (190126)
    # data_credito = 20/01/2026 (200126)
    linha_teste = criar_linha_teste(
        data_ocorrencia='190126',  # 19/01/2026
        data_credito='200126',     # 20/01/2026
        valor='0000000177847',     # R$ 1.778,47
        nf_parcela='142941   /1'   # NF 142941 Parcela 1
    )

    # Verificar tamanho da linha
    print(f"\n1. Tamanho da linha de teste: {len(linha_teste)} caracteres")

    # Mostrar posições relevantes
    print("\n2. Posições extraídas (raw):")
    print(f"   Posição 110:116 (data_ocorrencia): '{linha_teste[110:116]}'")
    print(f"   Posição 295:301 (data_credito): '{linha_teste[295:301]}'")

    # Fazer o parse completo
    print("\n3. Resultado do _parse_detalhe():")
    try:
        resultado = parser._parse_detalhe(linha_teste, 1)

        data_ocorrencia = resultado.get('data_ocorrencia')
        data_credito = resultado.get('data_credito')

        print(f"   data_ocorrencia: {data_ocorrencia}")
        print(f"   data_credito: {data_credito}")

        # Verificar se são diferentes (esperado: sim)
        if data_ocorrencia and data_credito:
            if data_ocorrencia == data_credito:
                print("\n   ⚠️  ALERTA: data_ocorrencia == data_credito (esperava serem diferentes)")
            else:
                print(f"\n   ✅ OK: Datas são diferentes!")
                print(f"      data_ocorrencia (liquidação): {data_ocorrencia.strftime('%d/%m/%Y')}")
                print(f"      data_credito (crédito):       {data_credito.strftime('%d/%m/%Y')}")
        else:
            print(f"\n   ❌ ERRO: Uma das datas é None")
            print(f"      data_ocorrencia: {data_ocorrencia}")
            print(f"      data_credito: {data_credito}")
            return 1

    except Exception as e:
        print(f"   ❌ ERRO no parse: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Mostrar outros campos extraídos
    print("\n4. Outros campos relevantes:")
    print(f"   seu_numero: '{resultado.get('seu_numero')}'")
    print(f"   codigo_ocorrencia: '{resultado.get('codigo_ocorrencia')}'")
    print(f"   valor_pago: {resultado.get('valor_pago')}")

    print("\n" + "="*60)
    print("✅ TESTE CONCLUÍDO COM SUCESSO")
    print("="*60 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
