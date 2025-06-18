#!/usr/bin/env python3
"""
Script para migrar arquivos do sistema local para AWS S3
Execute este script após configurar as variáveis de ambiente do S3
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.portaria.models import Motorista
from app.fretes.models import FaturaFrete
from app.utils.file_storage import get_file_storage

def migrar_fotos_motoristas():
    """Migra fotos de motoristas para S3"""
    print("🚗 Migrando fotos de motoristas...")
    
    storage = get_file_storage()
    migrados = 0
    erros = 0
    
    # Busca motoristas com fotos
    motoristas = Motorista.query.filter(Motorista.foto_documento.isnot(None)).all()
    
    for motorista in motoristas:
        if not motorista.foto_documento:
            continue
            
        # Verifica se já está no S3
        if motorista.foto_documento.startswith('s3://'):
            print(f"  ⏭️ Motorista {motorista.nome_completo}: já migrado")
            continue
        
        try:
            # Caminho do arquivo local
            arquivo_local = os.path.join('app', 'static', motorista.foto_documento)
            
            if not os.path.exists(arquivo_local):
                print(f"  ❌ Motorista {motorista.nome_completo}: arquivo não encontrado ({arquivo_local})")
                erros += 1
                continue
            
            # Lê o arquivo local
            with open(arquivo_local, 'rb') as f:
                # Simula um objeto FileStorage
                class FakeFileStorage:
                    def __init__(self, file_obj, filename):
                        self.file_obj = file_obj
                        self.filename = filename
                    
                    def save(self, path):
                        with open(path, 'wb') as dest:
                            dest.write(self.file_obj.read())
                        self.file_obj.seek(0)
                    
                    def read(self):
                        return self.file_obj.read()
                    
                    def seek(self, pos):
                        return self.file_obj.seek(pos)
                
                fake_file = FakeFileStorage(f, os.path.basename(arquivo_local))
                
                # Salva no S3
                novo_caminho = storage.save_file(
                    file=fake_file,
                    folder='motoristas',
                    allowed_extensions=['jpg', 'jpeg', 'png']
                )
                
                if novo_caminho:
                    # Atualiza o banco
                    motorista.foto_documento = novo_caminho
                    db.session.add(motorista)
                    
                    print(f"  ✅ Motorista {motorista.nome_completo}: migrado")
                    migrados += 1
                else:
                    print(f"  ❌ Motorista {motorista.nome_completo}: erro ao salvar no S3")
                    erros += 1
                    
        except Exception as e:
            print(f"  ❌ Motorista {motorista.nome_completo}: erro - {str(e)}")
            erros += 1
    
    # Salva mudanças
    if migrados > 0:
        db.session.commit()
        print(f"✅ Fotos de motoristas: {migrados} migrados, {erros} erros")
    else:
        print(f"ℹ️ Nenhuma foto de motorista para migrar")

def migrar_pdfs_faturas():
    """Migra PDFs de faturas para S3"""
    print("📄 Migrando PDFs de faturas...")
    
    storage = get_file_storage()
    migrados = 0
    erros = 0
    
    # Busca faturas com PDFs
    faturas = FaturaFrete.query.filter(FaturaFrete.arquivo_pdf.isnot(None)).all()
    
    for fatura in faturas:
        if not fatura.arquivo_pdf:
            continue
            
        # Verifica se já está no S3
        if fatura.arquivo_pdf.startswith('s3://'):
            print(f"  ⏭️ Fatura {fatura.numero_fatura}: já migrada")
            continue
        
        try:
            # Caminho do arquivo local
            arquivo_local = fatura.arquivo_pdf
            if not arquivo_local.startswith('/'):
                arquivo_local = os.path.join(arquivo_local)
            
            if not os.path.exists(arquivo_local):
                print(f"  ❌ Fatura {fatura.numero_fatura}: arquivo não encontrado ({arquivo_local})")
                erros += 1
                continue
            
            # Lê o arquivo local
            with open(arquivo_local, 'rb') as f:
                # Simula um objeto FileStorage
                class FakeFileStorage:
                    def __init__(self, file_obj, filename):
                        self.file_obj = file_obj
                        self.filename = filename
                    
                    def save(self, path):
                        with open(path, 'wb') as dest:
                            dest.write(self.file_obj.read())
                        self.file_obj.seek(0)
                    
                    def read(self):
                        return self.file_obj.read()
                    
                    def seek(self, pos):
                        return self.file_obj.seek(pos)
                
                fake_file = FakeFileStorage(f, os.path.basename(arquivo_local))
                
                # Salva no S3
                novo_caminho = storage.save_file(
                    file=fake_file,
                    folder='faturas',
                    allowed_extensions=['pdf']
                )
                
                if novo_caminho:
                    # Atualiza o banco
                    fatura.arquivo_pdf = novo_caminho
                    db.session.add(fatura)
                    
                    print(f"  ✅ Fatura {fatura.numero_fatura}: migrada")
                    migrados += 1
                else:
                    print(f"  ❌ Fatura {fatura.numero_fatura}: erro ao salvar no S3")
                    erros += 1
                    
        except Exception as e:
            print(f"  ❌ Fatura {fatura.numero_fatura}: erro - {str(e)}")
            erros += 1
    
    # Salva mudanças
    if migrados > 0:
        db.session.commit()
        print(f"✅ PDFs de faturas: {migrados} migrados, {erros} erros")
    else:
        print(f"ℹ️ Nenhum PDF de fatura para migrar")

def verificar_configuracao():
    """Verifica se o S3 está configurado corretamente"""
    print("🔍 Verificando configuração do S3...")
    
    from flask import current_app
    
    use_s3 = current_app.config.get('USE_S3', False)
    aws_key = current_app.config.get('AWS_ACCESS_KEY_ID')
    aws_secret = current_app.config.get('AWS_SECRET_ACCESS_KEY')
    bucket = current_app.config.get('S3_BUCKET_NAME')
    
    if not use_s3:
        print("❌ USE_S3 não está habilitado. Configure USE_S3=true")
        return False
    
    if not aws_key:
        print("❌ AWS_ACCESS_KEY_ID não configurado")
        return False
    
    if not aws_secret:
        print("❌ AWS_SECRET_ACCESS_KEY não configurado")
        return False
    
    if not bucket:
        print("❌ S3_BUCKET_NAME não configurado")
        return False
    
    print("✅ Configuração do S3 parece correta")
    return True

def main():
    """Função principal"""
    print("=" * 50)
    print("🚀 MIGRAÇÃO DE ARQUIVOS PARA AWS S3")
    print("=" * 50)
    
    # Cria app e contexto
    app = create_app()
    
    with app.app_context():
        # Verifica configuração
        if not verificar_configuracao():
            print("\n❌ Configure as variáveis de ambiente do S3 antes de executar a migração")
            print("\nVariáveis necessárias:")
            print("- USE_S3=true")
            print("- AWS_ACCESS_KEY_ID=sua_access_key")
            print("- AWS_SECRET_ACCESS_KEY=sua_secret_key")
            print("- S3_BUCKET_NAME=nome_do_bucket")
            sys.exit(1)
        
        print("\n📋 Iniciando migração...")
        
        try:
            # Migra fotos de motoristas
            migrar_fotos_motoristas()
            print()
            
            # Migra PDFs de faturas
            migrar_pdfs_faturas()
            print()
            
            print("✅ Migração concluída!")
            
        except Exception as e:
            print(f"\n❌ Erro durante a migração: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main() 