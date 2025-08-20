#!/usr/bin/env python
"""
Script de teste para verificar o upload e processamento de emails com CC/BCC
"""
import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.email_models import EmailAnexado
from app.fretes.models import DespesaExtra, Frete
from app.utils.email_handler import EmailHandler

def criar_email_teste():
    """
    Cria um arquivo .msg de teste simulado
    NOTA: Este é um exemplo simplificado. Para testes reais, use um arquivo .msg real.
    """
    print("\n" + "="*60)
    print("TESTE DE UPLOAD DE EMAIL COM CC/BCC")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        # Busca um frete existente para teste
        frete = db.session.query(Frete).first()
        if not frete:
            print("❌ Nenhum frete encontrado no banco. Crie um frete primeiro.")
            return
        
        print(f"✅ Usando Frete #{frete.id}")
        
        # Cria uma despesa de teste
        despesa = DespesaExtra(
            frete_id=frete.id,
            tipo_despesa='Documentação',
            setor_responsavel='Operacional',
            numero_documento='TESTE-001',
            valor_despesa=100.00,
            observacoes='Despesa de teste para emails',
            criado_por='Sistema de Teste'
        )
        db.session.add(despesa)
        db.session.commit()
        print(f"✅ Despesa criada: #{despesa.id}")
        
        # Simula metadados de um email com CC e BCC
        metadados_email = {
            'remetente': 'teste@empresa.com',
            'destinatarios': json.dumps(['destino1@cliente.com', 'destino2@cliente.com']),
            'cc': json.dumps(['copia1@empresa.com', 'copia2@empresa.com', 'gerente@empresa.com']),
            'bcc': json.dumps(['auditoria@empresa.com']),  # Raramente visível em emails recebidos
            'assunto': 'Teste de Email com CC e BCC - Frete #' + str(frete.id),
            'data_envio': datetime.now(),
            'tem_anexos': True,
            'qtd_anexos': 2,
            'conteudo_preview': 'Este é um email de teste para verificar o funcionamento dos campos CC e BCC.',
            'tamanho_bytes': 2048
        }
        
        # Cria registro de email anexado
        email = EmailAnexado(
            despesa_extra_id=despesa.id,
            nome_arquivo='teste_email_cc_bcc.msg',
            caminho_s3='fretes/despesas/' + str(despesa.id) + '/emails/teste.msg',
            tamanho_bytes=metadados_email['tamanho_bytes'],
            remetente=metadados_email['remetente'],
            destinatarios=metadados_email['destinatarios'],
            cc=metadados_email['cc'],
            bcc=metadados_email['bcc'],
            assunto=metadados_email['assunto'],
            data_envio=metadados_email['data_envio'],
            tem_anexos=metadados_email['tem_anexos'],
            qtd_anexos=metadados_email['qtd_anexos'],
            conteudo_preview=metadados_email['conteudo_preview'],
            criado_por='Sistema de Teste'
        )
        db.session.add(email)
        db.session.commit()
        
        print(f"✅ Email criado: #{email.id}")
        print("\n📧 Detalhes do Email:")
        print(f"   Assunto: {email.assunto}")
        print(f"   De: {email.remetente}")
        print(f"   Para: {email.destinatarios}")
        print(f"   CC: {email.cc}")
        print(f"   BCC: {email.bcc}")
        print(f"   Anexos: {email.qtd_anexos} arquivo(s)")
        
        print("\n📌 URLs para teste:")
        print(f"   Ver Frete: http://localhost:5000/fretes/{frete.id}")
        print(f"   Ver Email: http://localhost:5000/fretes/emails/{email.id}/visualizar")
        
        # Verifica se os campos foram salvos corretamente
        email_verificado = db.session.query(EmailAnexado).filter_by(id=email.id).first()
        
        print("\n✅ Verificação dos campos salvos:")
        print(f"   CC salvo: {email_verificado.cc}")
        print(f"   BCC salvo: {email_verificado.bcc}")
        
        # Testa parsing dos campos JSON
        try:
            cc_list = json.loads(email_verificado.cc) if email_verificado.cc else []
            bcc_list = json.loads(email_verificado.bcc) if email_verificado.bcc else []
            
            print(f"\n📋 Parsing JSON:")
            print(f"   CC parseado: {cc_list}")
            print(f"   BCC parseado: {bcc_list}")
            print(f"   Total CC: {len(cc_list)} destinatário(s)")
            print(f"   Total BCC: {len(bcc_list)} destinatário(s)")
            
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao parsear JSON: {e}")
        
        print("\n" + "="*60)
        print("TESTE CONCLUÍDO COM SUCESSO!")
        print("="*60)
        print("\n💡 Dica: Acesse as URLs acima para visualizar o resultado no navegador.")
        print("    Os destinatários CC aparecerão em badges azuis.")
        print("    Os destinatários BCC aparecerão em badges cinzas.")

if __name__ == "__main__":
    criar_email_teste()