"""
Script: Popular endereço do emitente nas NFDs existentes
Data: 2026-01-02
Descrição: Extrai UF e município do emitente a partir do XML local ou S3
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import current_app
from app import create_app, db
from app.devolucao.models import NFDevolucao
from app.devolucao.services.nfd_xml_parser import NFDXMLParser
from app.utils.file_storage import FileStorage


def popular_endereco_emitente():
    app = create_app()
    with app.app_context():
        try:
            storage = FileStorage()

            # Buscar NFDs que têm XML mas não têm uf_emitente
            nfds = NFDevolucao.query.filter(
                NFDevolucao.nfd_xml_path.isnot(None),
                NFDevolucao.uf_emitente.is_(None)
            ).all()

            print(f"NFDs a processar: {len(nfds)}")

            atualizadas = 0
            erros = 0

            for nfd in nfds:
                try:
                    xml_content = None

                    if storage.use_s3:
                        # Baixar XML do S3
                        import boto3
                        s3 = boto3.client(
                            's3',
                            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                            region_name=os.environ.get('AWS_REGION', 'us-east-2')
                        )
                        bucket = os.environ.get('AWS_S3_BUCKET')

                        try:
                            response = s3.get_object(Bucket=bucket, Key=nfd.nfd_xml_path)
                            xml_content = response['Body'].read()
                        except Exception as e:
                            print(f"  NFD {nfd.id}: Erro S3 - {e}")
                            erros += 1
                            continue
                    else:
                        # Ler XML do diretório local (app/static/{path})
                        file_path = os.path.join(current_app.root_path, 'static', nfd.nfd_xml_path)
                        if os.path.exists(file_path):
                            with open(file_path, 'rb') as f:
                                xml_content = f.read()
                        else:
                            print(f"  NFD {nfd.id}: Arquivo não encontrado: {file_path}")
                            erros += 1
                            continue

                    if not xml_content:
                        print(f"  NFD {nfd.id}: XML vazio")
                        erros += 1
                        continue

                    # Decodificar XML
                    try:
                        xml_str = xml_content.decode('utf-8')
                    except UnicodeDecodeError:
                        xml_str = xml_content.decode('iso-8859-1')

                    # Extrair dados do emitente
                    parser = NFDXMLParser(xml_str)
                    dados_emitente = parser.get_dados_emitente()

                    if dados_emitente:
                        uf = dados_emitente.get('uf')
                        municipio = dados_emitente.get('municipio')

                        if uf or municipio:
                            nfd.uf_emitente = uf
                            nfd.municipio_emitente = municipio
                            atualizadas += 1
                            print(f"  NFD {nfd.id} ({nfd.numero_nfd}): {uf}/{municipio}")
                        else:
                            print(f"  NFD {nfd.id}: UF/município não encontrados no XML")
                    else:
                        print(f"  NFD {nfd.id}: Dados do emitente não encontrados")

                except Exception as e:
                    print(f"  NFD {nfd.id}: Erro - {e}")
                    erros += 1

            db.session.commit()

            print(f"\n=== RESULTADO ===")
            print(f"Total processadas: {len(nfds)}")
            print(f"Atualizadas: {atualizadas}")
            print(f"Erros: {erros}")

        except Exception as e:
            print(f"Erro geral: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    popular_endereco_emitente()
