"""
Teste de extração de campos do Odoo
"""

def testar_extracao():
    # Simular dados vindos do Odoo
    municipio_odoo = [3830, 'Fortaleza (CE)']
    incoterm_odoo = [6, '[CIF] COST, INSURANCE AND FREIGHT']
    
    print("🔍 TESTE DE EXTRAÇÃO DE CAMPOS\n")
    
    # 1. Extrair município e UF
    print("1️⃣ MUNICÍPIO")
    print(f"   Entrada: {municipio_odoo}")
    
    if isinstance(municipio_odoo, list) and len(municipio_odoo) > 1:
        municipio_completo = municipio_odoo[1]
        if '(' in municipio_completo and ')' in municipio_completo:
            partes = municipio_completo.split('(')
            municipio_nome = partes[0].strip()
            uf_com_parenteses = partes[1]
            estado_uf = uf_com_parenteses.replace(')', '').strip()[:2]
            
            print(f"   Município: '{municipio_nome}'")
            print(f"   Estado: '{estado_uf}'")
    
    # 2. Extrair incoterm
    print("\n2️⃣ INCOTERM")
    print(f"   Entrada: {incoterm_odoo}")
    
    if isinstance(incoterm_odoo, list) and len(incoterm_odoo) > 1:
        incoterm_texto = incoterm_odoo[1]
        if '[' in incoterm_texto and ']' in incoterm_texto:
            inicio = incoterm_texto.find('[')
            fim = incoterm_texto.find(']')
            if inicio >= 0 and fim > inicio:
                incoterm_codigo = incoterm_texto[inicio+1:fim]
                print(f"   Código: '{incoterm_codigo}'")
    
    # 3. Testar outros casos
    print("\n3️⃣ OUTROS CASOS")
    
    # Caso São Paulo
    municipio_sp = [3830, 'São Paulo (SP)']
    municipio_completo = municipio_sp[1]
    partes = municipio_completo.split('(')
    print(f"   '{municipio_sp[1]}' → Cidade: '{partes[0].strip()}', UF: '{partes[1].replace(')', '').strip()[:2]}'")
    
    # Caso FOB
    incoterm_fob = [4, '[FOB] FREE ON BOARD']
    incoterm_texto = incoterm_fob[1]
    inicio = incoterm_texto.find('[')
    fim = incoterm_texto.find(']')
    print(f"   '{incoterm_fob[1]}' → Código: '{incoterm_texto[inicio+1:fim]}'")
    
    # Caso Redespacho
    incoterm_red = [16, '[RED] REDESPACHO']
    incoterm_texto = incoterm_red[1]
    inicio = incoterm_texto.find('[')
    fim = incoterm_texto.find(']')
    print(f"   '{incoterm_red[1]}' → Código: '{incoterm_texto[inicio+1:fim]}'")

if __name__ == "__main__":
    testar_extracao() 