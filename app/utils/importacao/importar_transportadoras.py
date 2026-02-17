import pandas as pd
from app import db
from app.transportadoras.models import Transportadora

def importar_transportadoras(caminho_arquivo):
    df = pd.read_excel(caminho_arquivo)
    
    # Listas para armazenar resultados
    erros = []
    importadas = []
    atualizadas = []
    
    # Converte campo 'OPTANTE' para booleano
    df['OPTANTE'] = df['OPTANTE'].fillna('').astype(str).str.upper().map({'SIM': True, 'S': True, 'NÃO': False, 'NAO': False, 'N': False}).fillna(False)

    # Converte campo 'Aceita NF Pallet' para booleano (opcional)
    # Se a coluna existir, converte. SIM = aceita (nao_aceita_nf_pallet = False)
    if 'Aceita NF Pallet' in df.columns:
        df['_aceita_nf_pallet'] = df['Aceita NF Pallet'].fillna('').astype(str).str.upper().map({'SIM': True, 'S': True, 'NÃO': False, 'NAO': False, 'N': False}).fillna(True)

    # Itera pelas linhas e valida os dados
    for index, row in df.iterrows():
        linha_atual = index + 2  # +2 porque Excel começa em 1 e tem cabeçalho
        
        # Validação dos campos obrigatórios
        if pd.isna(row['CNPJ']):
            erros.append(f"Linha {linha_atual}: CNPJ está vazio")
            continue
            
        if pd.isna(row['Razão Social']):
            erros.append(f"Linha {linha_atual}: Razão Social está vazia")
            continue
            
        if pd.isna(row['Cidade']):
            erros.append(f"Linha {linha_atual}: Cidade está vazia para {row['Razão Social']}")
            continue
            
        if pd.isna(row['UF']):
            erros.append(f"Linha {linha_atual}: UF está vazia para {row['Razão Social']}")
            continue

        try:
            # Verifica se já existe uma transportadora com este CNPJ
            transportadora_existente = Transportadora.query.filter_by(cnpj=str(row['CNPJ']).strip()).first()
            
            dados = {
                'cnpj': str(row['CNPJ']).strip(),
                'razao_social': str(row['Razão Social']).strip(),
                'cidade': str(row['Cidade']).strip(),
                'uf': str(row['UF']).strip().upper(),
                'optante': row['OPTANTE'],
                'condicao_pgto': row.get('Condição de pgto', None) if not pd.isna(row.get('Condição de pgto', None)) else None
            }

            # Adiciona campo nao_aceita_nf_pallet se a coluna existir
            # Inverte a lógica: Aceita NF Pallet = SIM → nao_aceita_nf_pallet = False
            if '_aceita_nf_pallet' in row:
                dados['nao_aceita_nf_pallet'] = not row['_aceita_nf_pallet']

            # Campos financeiros (opcionais)
            campos_financeiros = {
                'Banco': 'banco',
                'Agência': 'agencia',
                'Conta': 'conta',
                'PIX': 'pix',
                'CPF/CNPJ Favorecido': 'cpf_cnpj_favorecido',
                'Obs. Financeira': 'obs_financ'
            }

            for col_excel, campo_db in campos_financeiros.items():
                if col_excel in df.columns and not pd.isna(row.get(col_excel)):
                    dados[campo_db] = str(row[col_excel]).strip()

            # Campo Tipo Conta com mapeamento
            if 'Tipo Conta' in df.columns and not pd.isna(row.get('Tipo Conta')):
                tipo_conta_valor = str(row['Tipo Conta']).strip().lower()
                if 'corrente' in tipo_conta_valor:
                    dados['tipo_conta'] = 'corrente'
                elif 'poupan' in tipo_conta_valor:
                    dados['tipo_conta'] = 'poupanca'
            
            if transportadora_existente:
                # Atualiza os dados da transportadora existente
                for key, value in dados.items():
                    setattr(transportadora_existente, key, value)
                atualizadas.append(f"{dados['razao_social']} (CNPJ: {dados['cnpj']})")
            else:
                # Cria nova transportadora
                transportadora = Transportadora(**dados)
                db.session.add(transportadora)
                importadas.append(f"{dados['razao_social']} (CNPJ: {dados['cnpj']})")
                
        except Exception as e:
            erros.append(f"Linha {linha_atual}: Erro ao processar {row['Razão Social']} - {str(e)}")
            continue
            
    # Commit das alterações
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Erro ao salvar no banco de dados: {str(e)}")
        
    # Prepara o resumo
    resumo = []
    if erros:
        resumo.append("\n=== ERROS ENCONTRADOS ===")
        resumo.extend(erros)
        
    if importadas:
        resumo.append("\n=== TRANSPORTADORAS IMPORTADAS ===")
        resumo.extend(importadas)
        
    if atualizadas:
        resumo.append("\n=== TRANSPORTADORAS ATUALIZADAS ===")
        resumo.extend(atualizadas)
        
    resumo.append(f"\nTotal: {len(importadas)} importadas, {len(atualizadas)} atualizadas, {len(erros)} erros")
    
    return "\n".join(resumo)
