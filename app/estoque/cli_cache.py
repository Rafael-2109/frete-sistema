"""
Comandos CLI para gerenciar o cache de estoque
"""

import click
from flask.cli import with_appcontext
from app import db
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
from app.estoque.cache_triggers_safe import configurar_triggers_cache
import logging

logger = logging.getLogger(__name__)


@click.command()
@with_appcontext
def reinicializar_cache():
    """Reinicializa completamente o cache de estoque e projeção"""
    click.echo("🔄 Reinicializando cache de estoque...")
    
    try:
        # Limpar cache antigo
        ProjecaoEstoqueCache.query.delete()
        db.session.commit()
        click.echo("✅ Cache de projeção limpo")
        
        # Reinicializar saldos
        SaldoEstoqueCache.inicializar_cache()
        click.echo("✅ Cache de saldo reinicializado")
        
        # Atualizar todas as projeções
        produtos = SaldoEstoqueCache.query.all()
        total = len(produtos)
        
        click.echo(f"📊 Atualizando projeções para {total} produtos...")
        
        for i, produto in enumerate(produtos, 1):
            ProjecaoEstoqueCache.atualizar_projecao(produto.cod_produto)
            if i % 10 == 0:
                click.echo(f"  Processados {i}/{total} produtos...")
        
        db.session.commit()
        click.echo(f"✅ Cache completamente reinicializado com {total} produtos")
        
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro ao reinicializar cache: {e}", err=True)
        raise


@click.command()
@click.argument('cod_produto')
@with_appcontext
def atualizar_produto(cod_produto):
    """Atualiza cache e projeção para um produto específico"""
    click.echo(f"🔄 Atualizando cache para produto {cod_produto}...")
    
    try:
        # Atualizar saldo
        SaldoEstoqueCache.atualizar_saldo_completo(cod_produto)
        click.echo(f"✅ Saldo atualizado")
        
        # Atualizar projeção
        ProjecaoEstoqueCache.atualizar_projecao(cod_produto)
        click.echo(f"✅ Projeção atualizada")
        
        db.session.commit()
        
        # Mostrar resultado
        cache = SaldoEstoqueCache.query.filter_by(cod_produto=cod_produto).first()
        if cache:
            click.echo(f"\n📊 Status do produto {cod_produto}:")
            click.echo(f"  Nome: {cache.nome_produto}")
            click.echo(f"  Saldo: {cache.saldo_atual}")
            click.echo(f"  Carteira: {cache.qtd_carteira}")
            click.echo(f"  Pré-separação: {cache.qtd_pre_separacao}")
            click.echo(f"  Separação: {cache.qtd_separacao}")
            click.echo(f"  Disponível: {cache.saldo_disponivel}")
        
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro ao atualizar produto: {e}", err=True)
        raise


@click.command()
@with_appcontext
def verificar_triggers():
    """Verifica se os triggers estão funcionando corretamente"""
    click.echo("🔍 Verificando triggers de cache...")
    
    try:
        # Reconfigurar triggers
        configurar_triggers_cache()
        click.echo("✅ Triggers reconfigurados")
        
        # Criar uma movimentação de teste
        from app.estoque.models import MovimentacaoEstoque
        from app.utils.timezone import agora_brasil
        
        teste = MovimentacaoEstoque(
            cod_produto='TESTE_TRIGGER',
            nome_produto='Produto de Teste',
            qtd_movimentacao=100,
            tipo_movimentacao='ENTRADA',
            origem='TESTE',
            data_movimentacao=agora_brasil(),
            ativo=True
        )
        
        db.session.add(teste)
        db.session.commit()
        
        # Verificar se o cache foi atualizado
        cache = SaldoEstoqueCache.query.filter_by(cod_produto='TESTE_TRIGGER').first()
        
        if cache:
            click.echo("✅ Triggers funcionando! Cache foi atualizado automaticamente")
            
            # Limpar teste
            db.session.delete(teste)
            if cache:
                db.session.delete(cache)
            db.session.commit()
        else:
            click.echo("⚠️ Triggers podem não estar funcionando corretamente")
            
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Erro ao verificar triggers: {e}", err=True)
        raise


@click.command()
@with_appcontext
def status_cache():
    """Mostra o status atual do cache"""
    try:
        total_produtos = SaldoEstoqueCache.query.count()
        total_projecoes = ProjecaoEstoqueCache.query.count()
        
        click.echo(f"\n📊 Status do Cache de Estoque:")
        click.echo(f"  Total de produtos em cache: {total_produtos}")
        click.echo(f"  Total de projeções: {total_projecoes}")
        
        # Verificar produtos com ruptura
        produtos_ruptura = SaldoEstoqueCache.query.filter(
            SaldoEstoqueCache.status_ruptura == 'CRÍTICO'
        ).count()
        
        produtos_atencao = SaldoEstoqueCache.query.filter(
            SaldoEstoqueCache.status_ruptura == 'ATENÇÃO'
        ).count()
        
        click.echo(f"\n⚠️ Alertas:")
        click.echo(f"  Produtos em ruptura: {produtos_ruptura}")
        click.echo(f"  Produtos em atenção: {produtos_atencao}")
        
    except Exception as e:
        click.echo(f"❌ Erro ao obter status: {e}", err=True)
        raise


def init_app(app):
    """Registra comandos CLI no app"""
    app.cli.add_command(reinicializar_cache)
    app.cli.add_command(atualizar_produto)
    app.cli.add_command(verificar_triggers)
    app.cli.add_command(status_cache)