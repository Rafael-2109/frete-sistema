import click
from flask.cli import with_appcontext
from app import db

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
        func.count(Pedido.id).label('count')
    ).filter(
        (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == ''),
        Pedido.cidade_normalizada.isnot(None)
    ).group_by(
        Pedido.cidade_normalizada,
        Pedido.uf_normalizada
    ).order_by(
        func.count(Pedido.id).desc()
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


@click.command('criar-vinculos-faltantes')
@with_appcontext
def criar_vinculos_faltantes():
    """Cria vínculos para tabelas órfãs baseado em cidades existentes"""
    print("🔧 Criando vínculos para tabelas órfãs...")
    
    from app.vinculos.models import CidadeAtendida
    from app.tabelas.models import TabelaFrete
    from app.localidades.models import Cidade
    
    # Busca tabelas órfãs
    tabelas_orfas = []
    tabelas = TabelaFrete.query.all()
    
    for tabela in tabelas:
        vinculo_existe = CidadeAtendida.query.filter_by(
            transportadora_id=tabela.transportadora_id,
            nome_tabela=tabela.nome_tabela
        ).first()
        
        if not vinculo_existe:
            tabelas_orfas.append(tabela)
    
    print(f"📊 Encontradas {len(tabelas_orfas)} tabelas órfãs")
    
    criados = 0
    for tabela in tabelas_orfas:
        # Busca cidades do UF de destino da tabela
        cidades_uf = Cidade.query.filter_by(uf=tabela.uf_destino).all()
        
        if cidades_uf:
            # Cria vínculo para a primeira cidade encontrada (pode ser refinado)
            cidade = cidades_uf[0]
            
            novo_vinculo = CidadeAtendida(
                cidade_id=cidade.id,
                codigo_ibge=cidade.codigo_ibge,
                uf=cidade.uf,
                transportadora_id=tabela.transportadora_id,
                nome_tabela=tabela.nome_tabela,
                lead_time=None
            )
            
            db.session.add(novo_vinculo)
            criados += 1
            
            print(f"➕ Criando vínculo para tabela {tabela.nome_tabela} → {cidade.nome}/{cidade.uf}")
    
    if criados > 0:
        db.session.commit()
        print(f"✅ {criados} vínculos criados com sucesso!")
    else:
        print("ℹ️ Nenhuma tabela órfã encontrada para criar vínculos")
    
    print("🏁 Criação concluída!") 