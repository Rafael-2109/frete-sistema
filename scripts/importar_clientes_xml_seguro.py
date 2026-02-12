#!/usr/bin/env python3
"""
Script de importação de clientes do arquivo XML para CadastroCliente
Versão segura que trata caracteres especiais sem modificar os dados
"""

import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from app import create_app, db
from app.carteira.models import CadastroCliente
from app.utils.timezone import agora_utc_naive


# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



def limpar_cnpj(cnpj):
    """Remove formatação do CNPJ/CPF"""
    if not cnpj:
        return None
    return ''.join(filter(str.isdigit, cnpj))


def pre_processar_xml(conteudo_xml):
    """
    Pré-processa o conteúdo XML para corrigir problemas comuns
    mas mantendo os dados originais intactos
    """
    # Substitui apenas & que não fazem parte de entidades válidas
    # Isso preserva os dados originais para a importação
    conteudo_processado = re.sub(
        r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)', 
        '&amp;', 
        conteudo_xml
    )
    return conteudo_processado


def importar_clientes_xml(arquivo_xml):
    """
    Importa clientes do arquivo XML para o banco de dados
    Trata caracteres especiais sem modificar os dados originais
    """
    print(f"\n{'='*60}")
    print(f"Importação de Clientes XML (Versão Segura)")
    print(f"{'='*60}")
    print(f"Arquivo: {arquivo_xml}")
    print(f"Início: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Verifica se o arquivo existe
    if not os.path.exists(arquivo_xml):
        print(f"❌ Erro: Arquivo {arquivo_xml} não encontrado!")
        return
    
    # Lê e pré-processa o XML
    try:
        with open(arquivo_xml, 'r', encoding='utf-8') as f:
            conteudo_xml = f.read()
        
        # Pré-processa para corrigir caracteres especiais
        conteudo_processado = pre_processar_xml(conteudo_xml)
        
        # Parse do XML processado
        root = ET.fromstring(conteudo_processado)
        
    except ET.ParseError as e:
        print(f"❌ Erro ao fazer parse do XML: {e}")
        print(f"💡 Tentando localizar o problema...")
        
        # Tenta identificar a linha com problema
        linhas = conteudo_xml.split('\n')
        if hasattr(e, 'position'):
            linha, coluna = e.position
            if linha > 0 and linha <= len(linhas):
                print(f"Linha {linha}: {linhas[linha-1][:100]}...")
        return
        
    except Exception as e:
        print(f"❌ Erro ao processar XML: {e}")
        return
    
    # Contadores
    total_clientes = 0
    clientes_importados = 0
    clientes_atualizados = 0
    clientes_com_erro = 0
    
    # Processa cada cliente
    clientes = root.find('clientes')
    if clientes is None:
        print("❌ Erro: Tag 'clientes' não encontrada no XML")
        return
    
    for cliente_elem in clientes.findall('cliente'):
        total_clientes += 1
        
        try:
            # Extrai dados do XML
            cnpj = cliente_elem.findtext('cnpj', '')
            cnpj_cpf = limpar_cnpj(cnpj)
            
            # Os dados já vêm corretos do XML, não precisamos decodificar
            razao_social = cliente_elem.findtext('razao_social', '')
            nome_fantasia = cliente_elem.findtext('nome_fantasia', '')
            
            # Extrai dados do endereço principal
            endereco_principal = None
            enderecos = cliente_elem.find('enderecos')
            if enderecos is not None:
                for endereco in enderecos.findall('endereco'):
                    if endereco.findtext('principal') == '1':
                        endereco_principal = endereco
                        break
                
                # Se não encontrar endereço principal, pega o primeiro
                if endereco_principal is None and enderecos.findall('endereco'):
                    endereco_principal = enderecos.findall('endereco')[0]
            
            # Dados de localização
            estado = ''
            municipio = ''
            cep = ''
            bairro = ''
            logradouro = ''
            numero = ''
            complemento = ''
            
            if endereco_principal is not None:
                estado = endereco_principal.findtext('sigla_estado', '')
                municipio = endereco_principal.findtext('cidade', '')
                cep = endereco_principal.findtext('cep', '')
                bairro = endereco_principal.findtext('bairro', '')
                logradouro = endereco_principal.findtext('logradouro', '')
                numero = endereco_principal.findtext('numero', '')
                complemento = endereco_principal.findtext('complemento', '')
            
            # Validações básicas
            if not cnpj_cpf:
                print(f"⚠️  Cliente sem CNPJ/CPF: {razao_social}")
                clientes_com_erro += 1
                continue
            
            if not razao_social:
                print(f"⚠️  Cliente {cnpj_cpf} sem razão social")
                clientes_com_erro += 1
                continue
            
            if not estado or not municipio:
                print(f"⚠️  Cliente {cnpj_cpf} ({razao_social}) sem localização completa")
                # Não vamos pular, apenas avisar
            
            # Verifica se o cliente já existe (com no_autoflush para evitar problemas)
            with db.session.no_autoflush:
                cliente_existente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cpf).first()
            
            if cliente_existente:
                # Atualiza cliente existente
                cliente_existente.raz_social = razao_social
                cliente_existente.raz_social_red = nome_fantasia or razao_social
                cliente_existente.estado = estado
                cliente_existente.municipio = municipio
                
                # Atualiza endereço de entrega com os mesmos dados do cliente
                cliente_existente.cnpj_endereco_ent = cnpj_cpf
                cliente_existente.empresa_endereco_ent = razao_social
                cliente_existente.cep_endereco_ent = cep
                cliente_existente.cod_uf = estado
                cliente_existente.nome_cidade = municipio
                cliente_existente.bairro_endereco_ent = bairro
                cliente_existente.rua_endereco_ent = logradouro
                cliente_existente.endereco_ent = numero[:20] if numero else ''  # Trunca para 20 caracteres
                
                # Complemento pode ser adicionado ao bairro ou logradouro se necessário
                if complemento and len(numero) <= 20:
                    # Se o complemento for pequeno e importante, pode ser adicionado ao logradouro
                    if logradouro and len(logradouro) + len(complemento) < 255:
                        cliente_existente.rua_endereco_ent = f"{logradouro} - {complemento}"
                
                print(f"✅ Atualizado: {cnpj_cpf} - {razao_social}")
                clientes_atualizados += 1
                
            else:
                # Cria novo cliente
                novo_cliente = CadastroCliente(
                    cnpj_cpf=cnpj_cpf,
                    raz_social=razao_social,
                    raz_social_red=nome_fantasia or razao_social,
                    estado=estado or 'XX',  # Default se não tiver
                    municipio=municipio or 'NÃO INFORMADO'  # Default se não tiver
                )
                
                # Define endereço de entrega igual ao endereço do cliente
                novo_cliente.cnpj_endereco_ent = cnpj_cpf
                novo_cliente.empresa_endereco_ent = razao_social
                novo_cliente.cep_endereco_ent = cep
                novo_cliente.cod_uf = estado
                novo_cliente.nome_cidade = municipio
                novo_cliente.bairro_endereco_ent = bairro
                novo_cliente.rua_endereco_ent = logradouro
                novo_cliente.endereco_ent = numero[:20] if numero else ''  # Trunca para 20 caracteres
                
                # Complemento pode ser adicionado ao bairro ou logradouro se necessário
                if complemento and len(numero) <= 20:
                    # Se o complemento for pequeno e importante, pode ser adicionado ao logradouro
                    if logradouro and len(logradouro) + len(complemento) < 255:
                        novo_cliente.rua_endereco_ent = f"{logradouro} - {complemento}"
                
                db.session.add(novo_cliente)
                print(f"✅ Importado: {cnpj_cpf} - {razao_social}")
                clientes_importados += 1
            
        except Exception as e:
            print(f"❌ Erro ao processar cliente: {e}")
            if hasattr(e, '__traceback__'):
                import traceback
                traceback.print_exc()
            clientes_com_erro += 1
            db.session.rollback()
            continue
    
    # Commit das alterações
    try:
        db.session.commit()
        print(f"\n{'='*60}")
        print(f"✅ Importação concluída com sucesso!")
        print(f"{'='*60}")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Erro ao salvar no banco de dados: {e}")
        return
    
    # Relatório final
    print(f"\n📊 RESUMO DA IMPORTAÇÃO:")
    print(f"{'='*60}")
    print(f"Total de clientes no XML: {total_clientes}")
    print(f"✅ Clientes importados: {clientes_importados}")
    print(f"🔄 Clientes atualizados: {clientes_atualizados}")
    print(f"❌ Clientes com erro: {clientes_com_erro}")
    print(f"{'='*60}")
    print(f"Término: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}\n")


def main():
    """Função principal"""
    # Cria a aplicação Flask
    app = create_app()
    
    with app.app_context():
        # Define o caminho do arquivo XML
        arquivo_xml = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'app', 'integracoes', 'clientes.xml'
        )
        
        # Executa a importação
        importar_clientes_xml(arquivo_xml)


if __name__ == '__main__':
    main()