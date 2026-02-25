import click
from flask.cli import with_appcontext
from app import db
import os

@click.command('normalizar-dados')
@with_appcontext
def normalizar_dados():
    """Normaliza os dados de cidade/UF de todos os pedidos."""
    from app.utils.frete_simulador import normalizar_dados_existentes
    normalizar_dados_existentes()

@click.command('atualizar-ibge')
@with_appcontext
def atualizar_ibge():
    """Atualiza os códigos IBGE de todos os pedidos automaticamente."""
    from app.utils.localizacao import LocalizacaoService
    
    print("🔄 Iniciando atualização dos códigos IBGE...")
    print("⚠️  Este processo pode demorar alguns minutos dependendo do volume de dados.")
    
    # Executa a atualização
    atualizados, nao_encontrados = LocalizacaoService.atualizar_todos_codigos_ibge()
    
    print(f"\n✅ Processo concluído:")
    print(f"📊 Pedidos atualizados: {atualizados}")
    print(f"⚠️  Pedidos não encontrados: {nao_encontrados}")
    
    if nao_encontrados > 0:
        print(f"\n💡 Dica: {nao_encontrados} pedidos não tiveram suas cidades encontradas.")
        print("   Verifique se as cidades estão cadastradas na tabela 'cidades'.")

@click.command('limpar-cache-localizacao')
@with_appcontext
def limpar_cache_localizacao():
    """Limpa o cache de localização."""
    from app.utils.localizacao import LocalizacaoService
    
    LocalizacaoService.limpar_cache()
    print("✅ Cache de localização limpo!")


@click.command('validar-localizacao')
@with_appcontext 
def validar_localizacao():
    """Valida dados de localização e mostra estatísticas."""
    from app.pedidos.models import Pedido
    from app.localidades.models import Cidade
    
    print("📊 Validando dados de localização...\n")
    
    # Estatísticas gerais
    total_pedidos = Pedido.query.count()
    pedidos_com_ibge = Pedido.query.filter(
        Pedido.codigo_ibge.isnot(None),
        Pedido.codigo_ibge != ''
    ).count()
    pedidos_sem_ibge = total_pedidos - pedidos_com_ibge
    
    total_cidades = Cidade.query.count()
    
    print(f"📋 ESTATÍSTICAS GERAIS:")
    print(f"   Total de pedidos: {total_pedidos}")
    print(f"   Pedidos com código IBGE: {pedidos_com_ibge} ({pedidos_com_ibge/total_pedidos*100:.1f}%)")
    print(f"   Pedidos sem código IBGE: {pedidos_sem_ibge} ({pedidos_sem_ibge/total_pedidos*100:.1f}%)")
    print(f"   Total de cidades cadastradas: {total_cidades}")
    
    # Valida algumas cidades problemáticas
    print(f"\n🔍 VALIDAÇÃO DE CIDADES PROBLEMÁTICAS:")
    
    # Pedidos com cidade normalizada mas sem IBGE
    pedidos_problema = Pedido.query.filter(
        Pedido.cidade_normalizada.isnot(None),
        (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == '')
    ).limit(10).all()
    
    if pedidos_problema:
        print(f"   Exemplos de pedidos sem IBGE:")
        for p in pedidos_problema:
            print(f"   - Pedido {p.num_pedido}: {p.cidade_normalizada}/{p.uf_normalizada}")
    
    # Verifica cidades mais comuns sem IBGE
    from sqlalchemy import func
    cidades_sem_ibge = db.session.query(
        Pedido.cidade_normalizada,
        Pedido.uf_normalizada,
        func.count(Pedido.separacao_lote_id).label('count')
    ).filter(
        (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == ''),
        Pedido.cidade_normalizada.isnot(None)
    ).group_by(
        Pedido.cidade_normalizada,
        Pedido.uf_normalizada
    ).order_by(
        func.count(Pedido.separacao_lote_id).desc()
    ).limit(5).all()
    
    if cidades_sem_ibge:
        print(f"\n🏙️  CIDADES MAIS FREQUENTES SEM IBGE:")
        for cidade, uf, count in cidades_sem_ibge:
            print(f"   - {cidade}/{uf}: {count} pedidos")
    
    print(f"\n💡 RECOMENDAÇÕES:")
    if pedidos_sem_ibge > 0:
        print(f"   1. Execute: flask atualizar-ibge")
        print(f"   2. Verifique se as cidades estão cadastradas")
        print(f"   3. Considere importar mais cidades se necessário")


@click.command('diagnosticar-vinculos')
@with_appcontext
def diagnosticar_vinculos():
    """Diagnóstica problemas nos vínculos e tabelas"""
    print("🔍 Diagnosticando vínculos e tabelas...")
    
    from app.vinculos.models import CidadeAtendida
    from app.tabelas.models import TabelaFrete
    
    vinculos = CidadeAtendida.query.all()
    tabelas = TabelaFrete.query.all()
    
    # Estatísticas de vínculos
    status_vinculos = {}
    for vinculo in vinculos:
        status = vinculo.status_vinculo
        status_vinculos[status] = status_vinculos.get(status, 0) + 1
    
    # Estatísticas de tabelas
    status_tabelas = {}
    for tabela in tabelas:
        status = tabela.status_tabela
        status_tabelas[status] = status_tabelas.get(status, 0) + 1
    
    print(f"\n📊 ESTATÍSTICAS DOS VÍNCULOS:")
    for status, count in status_vinculos.items():
        perc = count / len(vinculos) * 100
        print(f"   • {status}: {count} ({perc:.1f}%)")
    
    print(f"\n📊 ESTATÍSTICAS DAS TABELAS:")
    for status, count in status_tabelas.items():
        perc = count / len(tabelas) * 100
        print(f"   • {status}: {count} ({perc:.1f}%)")
    
    print(f"\n📈 RESUMO GERAL:")
    print(f"   • Total de vínculos: {len(vinculos)}")
    print(f"   • Total de tabelas: {len(tabelas)}")
    
    problemas = status_vinculos.get('orfao', 0) + status_vinculos.get('transportadora_errada', 0) + status_tabelas.get('orfa', 0)
    problemas_grupo = status_vinculos.get('grupo_empresarial', 0) + status_tabelas.get('grupo_empresarial', 0)
    
    print(f"   • Problemas críticos: {problemas}")
    print(f"   • Problemas de grupo empresarial: {problemas_grupo}")


@click.command('corrigir-vinculos-grupo')
@with_appcontext 
def corrigir_vinculos_grupo():
    """Corrige vínculos que estão em transportadoras do mesmo grupo empresarial"""
    print("🔧 Corrigindo vínculos de grupos empresariais...")
    
    from app.vinculos.models import CidadeAtendida
    from app.tabelas.models import TabelaFrete
    from app.transportadoras.models import Transportadora
    from sqlalchemy import func
    
    correcoes = 0
    erros = 0
    
    # Busca todos os vínculos com status 'grupo_empresarial'
    vinculos = CidadeAtendida.query.all()
    
    for vinculo in vinculos:
        if vinculo.status_vinculo == 'grupo_empresarial':
            try:
                # Encontra a transportadora correta do mesmo grupo
                transportadora_atual = vinculo.transportadora.razao_social.upper()
                nome_base = transportadora_atual.replace('LTDA', '').replace('EIRELI', '').replace('S.A.', '').replace('S/A', '').strip()
                
                transportadoras_grupo = Transportadora.query.filter(
                    func.upper(Transportadora.razao_social).like(f'%{nome_base[:20]}%'),
                    Transportadora.id != vinculo.transportadora_id
                ).all()
                
                for transp in transportadoras_grupo:
                    tabela_grupo = TabelaFrete.query.filter_by(
                        transportadora_id=transp.id,
                        nome_tabela=vinculo.nome_tabela
                    ).first()
                    
                    if tabela_grupo:
                        print(f"   🔄 Corrigindo vínculo IBGE {vinculo.codigo_ibge}")
                        print(f"      De: {vinculo.transportadora.razao_social} (ID: {vinculo.transportadora_id})")
                        print(f"      Para: {transp.razao_social} (ID: {transp.id})")
                        
                        vinculo.transportadora_id = transp.id
                        correcoes += 1
                        break
                        
            except Exception as e:
                print(f"   ❌ Erro ao corrigir vínculo {vinculo.id}: {str(e)}")
                erros += 1
    
    try:
        db.session.commit()
        print(f"✅ Correção concluída!")
        print(f"   • {correcoes} vínculos corrigidos")
        print(f"   • {erros} erros encontrados")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao salvar: {str(e)}")


@click.command()
@click.argument('arquivo_excel')
@with_appcontext
def importar_cidades_cli(arquivo_excel):
    """Importa cidades de arquivo Excel (uso único)"""
    import pandas as pd  # Lazy import
    from app.localidades.models import Cidade
    
    if not os.path.exists(arquivo_excel):
        click.echo(f"❌ Arquivo não encontrado: {arquivo_excel}")
        return
    
    # Verificar se já existem cidades
    total_existentes = Cidade.query.count()
    if total_existentes > 0:
        if not click.confirm(f"⚠️ Já existem {total_existentes} cidades. Continuar?"):
            click.echo("❌ Importação cancelada.")
            return
    
    try:
        df = pd.read_excel(arquivo_excel, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        
        cidades_importadas = 0
        for _, row in df.iterrows():
            if pd.isna(row.get('CIDADE')) or pd.isna(row.get('UF')):
                continue
                
            cidade = Cidade(
                nome=row['CIDADE'].strip(),
                uf=row['UF'].strip().upper(),
                codigo_ibge=row.get('IBGE', '').strip(),
                icms=float(row.get('ICMS', '0').replace('%', '').replace(',', '.')) / 100,
                substitui_icms_por_iss=str(row.get('ISS', '')).upper() == 'SIM',
                microrregiao=row.get('MICRORREGIAO', '').strip() if not pd.isna(row.get('MICRORREGIAO')) else None,
                mesorregiao=row.get('MESORREGIAO', '').strip() if not pd.isna(row.get('MESORREGIAO')) else None
            )
            db.session.add(cidade)
            cidades_importadas += 1
        
        db.session.commit()
        click.echo(f"✅ {cidades_importadas} cidades importadas com sucesso!")
        
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro na importação: {e}") 