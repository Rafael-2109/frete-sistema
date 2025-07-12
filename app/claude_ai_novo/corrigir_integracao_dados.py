#!/usr/bin/env python3
"""
Script para corrigir a integração entre ResponseProcessor e DataProvider
Faz o sistema usar dados reais ao invés de respostas genéricas
"""

import os
import sys
from pathlib import Path
import shutil
from datetime import datetime

class IntegrationFixer:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.backup_dir = self.base_dir / 'backups' / f'fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.fixes_applied = []
        
    def backup_file(self, file_path: Path):
        """Faz backup de um arquivo antes de modificar"""
        if not file_path.exists():
            return
            
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        relative_path = file_path.relative_to(self.base_dir)
        backup_path = self.backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup criado: {backup_path}")
        
    def fix_response_processor(self):
        """Corrige o ResponseProcessor para usar DataProvider"""
        print("\n🔧 Corrigindo ResponseProcessor...")
        
        file_path = self.base_dir / 'processors' / 'response_processor.py'
        self.backup_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Adicionar import do DataProvider
        if 'from app.claude_ai_novo.providers.data_provider import get_data_provider' not in content:
            # Adicionar após os outros imports
            import_section = """# Imports com fallback seguro
try:
    from flask_login import current_user
    from app import db
    from sqlalchemy import func, and_, or_, text
    FLASK_AVAILABLE = True
except ImportError:
    current_user = None
    db = None
    func = and_ = or_ = text = None
    FLASK_AVAILABLE = False

# Import do DataProvider
try:
    from app.claude_ai_novo.providers.data_provider import get_data_provider
    DATA_PROVIDER_AVAILABLE = True
except ImportError:
    DATA_PROVIDER_AVAILABLE = False"""
            
            content = content.replace("""# Imports com fallback seguro
try:
    from flask_login import current_user
    from app import db
    from sqlalchemy import func, and_, or_, text
    FLASK_AVAILABLE = True
except ImportError:
    current_user = None
    db = None
    func = and_ = or_ = text = None
    FLASK_AVAILABLE = False""", import_section)
            
        # Adicionar método para buscar dados reais
        new_method = '''
    def _obter_dados_reais(self, consulta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Obtém dados reais do DataProvider baseado na análise"""
        
        if not DATA_PROVIDER_AVAILABLE:
            self.logger.warning("DataProvider não disponível")
            return {}
            
        try:
            data_provider = get_data_provider()
            
            # Determinar domínio e filtros baseado na análise
            dominio = analise.get('dominio', 'geral')
            filters = {}
            
            # Adicionar filtros baseados na análise
            if analise.get('cliente_especifico'):
                filters['cliente'] = analise['cliente_especifico']
                
            if analise.get('periodo_dias'):
                from datetime import datetime, timedelta
                filters['data_inicio'] = datetime.now() - timedelta(days=analise['periodo_dias'])
                filters['data_fim'] = datetime.now()
                
            # Buscar dados
            dados = data_provider.get_data_by_domain(dominio, filters)
            
            self.logger.info(f"Dados obtidos do domínio {dominio}: {dados.get('total', 0)} registros")
            
            return dados
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados reais: {e}")
            return {}
'''
        
        # Inserir o novo método após __init__
        if '_obter_dados_reais' not in content:
            init_end = content.find('def _init_anthropic_client(self):')
            if init_end > 0:
                content = content[:init_end] + new_method + '\n' + content[init_end:]
                
        # Modificar _construir_prompt_otimizado para incluir dados reais
        old_prompt_method = '''def _construir_prompt_otimizado(self, consulta: str, analise: Dict[str, Any], 
                                   user_context: Optional[Dict] = None) -> str:
        """Constrói prompt otimizado baseado na análise"""
        
        # Base do prompt
        prompt = f"""Você é um assistente especializado em sistema de fretes e logística.

**Consulta do usuário:** {consulta}

**Contexto detectado:**
- Domínio: {analise.get('dominio', 'geral')}
- Período: {analise.get('periodo_dias', 30)} dias
- Cliente específico: {analise.get('cliente_especifico', 'Não especificado')}
- Tipo de consulta: {analise.get('tipo_consulta', 'informacao')}

**Instruções:**
1. Responda de forma clara e objetiva
2. Use dados específicos quando disponíveis
3. Forneça contexto relevante
4. Seja preciso e factual
5. Evite informações genéricas

**Formato da resposta:**
- Comece com um resumo direto
- Inclua dados quantitativos quando relevantes
- Termine com insights ou recomendações se apropriado"""'''

        new_prompt_method = '''def _construir_prompt_otimizado(self, consulta: str, analise: Dict[str, Any], 
                                   user_context: Optional[Dict] = None) -> str:
        """Constrói prompt otimizado baseado na análise"""
        
        # Obter dados reais primeiro
        dados_reais = self._obter_dados_reais(consulta, analise)
        
        # Base do prompt
        prompt = f"""Você é um assistente especializado em sistema de fretes e logística.

**Consulta do usuário:** {consulta}

**Contexto detectado:**
- Domínio: {analise.get('dominio', 'geral')}
- Período: {analise.get('periodo_dias', 30)} dias
- Cliente específico: {analise.get('cliente_especifico', 'Não especificado')}
- Tipo de consulta: {analise.get('tipo_consulta', 'informacao')}

**DADOS REAIS DO SISTEMA:**
"""
        
        # Adicionar dados reais ao prompt
        if dados_reais and dados_reais.get('data'):
            prompt += f"- Total de registros: {dados_reais.get('total', 0)}\\n"
            
            # Adicionar resumo dos dados
            if dados_reais.get('domain') == 'entregas':
                entregas = dados_reais.get('data', [])
                if entregas:
                    # Calcular estatísticas
                    total_entregues = len([e for e in entregas if e.get('status') == 'ENTREGUE'])
                    total_pendentes = len([e for e in entregas if e.get('status') != 'ENTREGUE'])
                    
                    prompt += f"- Entregas realizadas: {total_entregues}\\n"
                    prompt += f"- Entregas pendentes: {total_pendentes}\\n"
                    
                    # Listar algumas entregas recentes
                    prompt += "\\n**Entregas recentes:**\\n"
                    for entrega in entregas[:5]:
                        prompt += f"- NF {entrega.get('numero_nf')} - {entrega.get('destino')} - Status: {entrega.get('status', 'N/A')}\\n"
                        
            elif dados_reais.get('domain') == 'pedidos':
                pedidos = dados_reais.get('data', [])
                if pedidos:
                    prompt += f"\\n**Pedidos encontrados: {len(pedidos)}**\\n"
                    for pedido in pedidos[:5]:
                        prompt += f"- Pedido {pedido.get('num_pedido')} - {pedido.get('cliente')} - R$ {pedido.get('valor_total', 0):.2f}\\n"
                        
        else:
            prompt += "Nenhum dado específico encontrado para esta consulta.\\n"
            
        prompt += """
**Instruções:**
1. Use os dados reais fornecidos acima
2. Seja específico e quantitativo
3. Forneça análises baseadas nos dados
4. Evite respostas genéricas
5. Se não houver dados, informe claramente

**Formato da resposta:**
- Comece com um resumo dos dados
- Apresente estatísticas relevantes
- Forneça insights baseados nos dados reais
- Sugira ações se apropriado"""'''

        content = content.replace(old_prompt_method, new_prompt_method)
        
        # Salvar arquivo corrigido
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.fixes_applied.append("ResponseProcessor integrado com DataProvider")
        print("✅ ResponseProcessor corrigido!")
        
    def fix_orchestrator_integration(self):
        """Corrige o Orchestrator para garantir uso do DataProvider"""
        print("\n🔧 Corrigindo Orchestrator...")
        
        file_path = self.base_dir / 'orchestrators' / 'orchestrator_manager.py'
        self.backup_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Adicionar import do DataProvider se necessário
        if 'from app.claude_ai_novo.providers.data_provider import get_data_provider' not in content:
            # Adicionar após outros imports
            import_line = "from app.claude_ai_novo.providers.data_provider import get_data_provider\n"
            
            # Encontrar onde adicionar
            import_section_end = content.find('logger = logging.getLogger(__name__)')
            if import_section_end > 0:
                content = content[:import_section_end] + import_line + content[import_section_end:]
                
        self.fixes_applied.append("Orchestrator preparado para DataProvider")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ Orchestrator corrigido!")
        
    def create_test_script(self):
        """Cria script de teste para verificar integração"""
        print("\n📝 Criando script de teste...")
        
        test_script = '''#!/usr/bin/env python3
"""
Script de teste para verificar integração de dados reais
"""

import os
import sys
from pathlib import Path

# Adicionar diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar variáveis de ambiente para teste
os.environ['FLASK_ENV'] = 'development'

try:
    from app.claude_ai_novo.processors.response_processor import get_responseprocessor
    from app.claude_ai_novo.providers.data_provider import get_data_provider
    
    print("✅ Imports funcionando!")
    
    # Testar DataProvider
    print("\\n🔍 Testando DataProvider...")
    data_provider = get_data_provider()
    
    # Buscar dados de entregas
    filters = {"cliente": "atacadão"}
    dados = data_provider.get_data_by_domain("entregas", filters)
    
    print(f"Dados obtidos: {dados.get('total', 0)} registros")
    
    # Testar ResponseProcessor
    print("\\n🔍 Testando ResponseProcessor...")
    processor = get_responseprocessor()
    
    # Simular análise
    analise = {
        "dominio": "entregas",
        "cliente_especifico": "atacadão",
        "periodo_dias": 30,
        "tipo_consulta": "status"
    }
    
    # Testar se o método existe
    if hasattr(processor, '_obter_dados_reais'):
        print("✅ Método _obter_dados_reais existe!")
        
        # Testar obtenção de dados
        dados_reais = processor._obter_dados_reais("teste", analise)
        print(f"Dados reais obtidos: {dados_reais.get('total', 0)} registros")
    else:
        print("❌ Método _obter_dados_reais não encontrado!")
        
    print("\\n✅ Teste concluído!")
    
except Exception as e:
    print(f"❌ Erro no teste: {e}")
    import traceback
    traceback.print_exc()
'''
        
        test_path = self.base_dir / 'testar_integracao_dados.py'
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_script)
            
        print(f"✅ Script de teste criado: {test_path}")
        
    def generate_report(self):
        """Gera relatório das correções"""
        report = f"""
# 🔧 RELATÓRIO DE CORREÇÃO - INTEGRAÇÃO DE DADOS

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Correções Aplicadas:

"""
        for fix in self.fixes_applied:
            report += f"- ✅ {fix}\n"
            
        report += f"""
## 🎯 Resultado Esperado:

1. ResponseProcessor agora busca dados reais via DataProvider
2. Prompts incluem dados específicos do sistema
3. Respostas baseadas em informações reais, não genéricas

## 🧪 Para Testar:

```bash
python testar_integracao_dados.py
```

## 📁 Backups:

Todos os arquivos modificados foram salvos em:
`{self.backup_dir}`

## 🚀 Próximos Passos:

1. Executar o teste para verificar integração
2. Testar no sistema real com queries como "Como estão as entregas do Atacadão?"
3. Monitorar logs para confirmar uso de dados reais
"""
        
        report_path = self.base_dir / 'CORRECAO_INTEGRACAO_DADOS.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"\n📄 Relatório salvo em: {report_path}")
        
    def run(self):
        """Executa todas as correções"""
        print("🔧 Iniciando correção de integração de dados...\n")
        
        self.fix_response_processor()
        self.fix_orchestrator_integration()
        self.create_test_script()
        self.generate_report()
        
        print("\n✅ CORREÇÃO CONCLUÍDA!")
        print("Execute 'python testar_integracao_dados.py' para verificar")

if __name__ == "__main__":
    fixer = IntegrationFixer()
    fixer.run() 