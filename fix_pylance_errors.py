#!/usr/bin/env python3
"""
🔧 Script para corrigir erros do Pylance no Claude AI routes.py
"""

import os

def fix_input_validator_import():
    """Corrige o conflito de import do InputValidator"""
    
    print("🔧 Corrigindo erro de import do InputValidator...")
    
    file_path = "app/claude_ai/routes.py"
    
    if not os.path.exists(file_path):
        print(f"❌ Arquivo {file_path} não encontrado")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    with open(file_path + '.backup_pylance', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Corrigir o import condicional do InputValidator
    old_validator_block = """# Import do InputValidator com fallback
try:
    from app.claude_ai.input_validator import InputValidator
except ImportError:
    class InputValidator:
        @staticmethod
        def validate_json_request(data, required_fields=None):
            if not data:
                return False, "Dados JSON inválidos", None
            if required_fields:
                for field in required_fields:
                    if field not in data:
                        return False, f"Campo obrigatório: {field}", None
            return True, "", data"""
    
    new_validator_block = """# Import do InputValidator com fallback
try:
    from app.claude_ai.input_validator import InputValidator as _InputValidator
    InputValidator = _InputValidator
except ImportError:
    # Fallback InputValidator para quando o módulo não está disponível
    class _FallbackInputValidator:
        @staticmethod
        def validate_json_request(data, required_fields=None):
            if not data:
                return False, "Dados JSON inválidos", None
            if required_fields:
                for field in required_fields:
                    if field not in data:
                        return False, f"Campo obrigatório: {field}", None
            return True, "", data
    
    InputValidator = _FallbackInputValidator"""
    
    if old_validator_block in content:
        content = content.replace(old_validator_block, new_validator_block)
        print("✅ Import do InputValidator corrigido")
    else:
        print("⚠️ Bloco InputValidator não encontrado no formato esperado")
    
    # Salvar
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def fix_none_subscriptable():
    """Corrige o erro de None subscriptable"""
    
    print("\n🔧 Corrigindo erro None subscriptable...")
    
    file_path = "app/claude_ai/routes.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Procurar e corrigir as linhas problemáticas
    # Linha ~500: consulta = validated_data['query']
    old_pattern = """        )
        if not valid:
            logger.error(f"❌ Widget: Validação falhou - {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        consulta = validated_data['query']
        csrf_token = validated_data.get('csrf_token', '')"""
    
    new_pattern = """        )
        if not valid:
            logger.error(f"❌ Widget: Validação falhou - {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        # Garantir que validated_data não é None
        if validated_data is None:
            logger.error("❌ Widget: validated_data é None após validação")
            return jsonify({'success': False, 'error': 'Erro de validação'}), 400
            
        consulta = validated_data.get('query', '')
        csrf_token = validated_data.get('csrf_token', '')"""
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("✅ Erro None subscriptable corrigido na linha ~500")
    else:
        print("⚠️ Padrão da linha 500 não encontrado")
    
    # Procurar por outros usos similares
    # Linha ~988: command = validated_data.get('command', validated_data.get('query', ''))
    old_command = """        if not valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        command = validated_data.get('command', validated_data.get('query', ''))"""
    
    new_command = """        if not valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Garantir que validated_data não é None
        if validated_data is None:
            return jsonify({
                'success': False,
                'error': 'Erro de validação'
            }), 400
        
        command = validated_data.get('command', validated_data.get('query', ''))"""
    
    if old_command in content:
        content = content.replace(old_command, new_command)
        print("✅ Outro uso de validated_data corrigido")
    
    # Salvar
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def verify_fixes():
    """Verifica se as correções foram aplicadas"""
    
    print("\n🔍 Verificando correções...")
    
    file_path = "app/claude_ai/routes.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar correções
    checks = [
        ("InputValidator alias", "_FallbackInputValidator" in content),
        ("None check linha 500", "if validated_data is None:" in content),
        ("Import _InputValidator", "from app.claude_ai.input_validator import InputValidator as _InputValidator" in content)
    ]
    
    all_good = True
    for check_name, check_result in checks:
        if check_result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_good = False
    
    return all_good

def main():
    """Função principal"""
    print("🔧 Fix Pylance Errors - Claude AI routes.py")
    print("=" * 50)
    
    # Aplicar correções
    if fix_input_validator_import():
        print("\n✅ Import InputValidator corrigido")
    
    if fix_none_subscriptable():
        print("\n✅ None subscriptable corrigido")
    
    # Verificar
    if verify_fixes():
        print("\n🎉 SUCESSO! Todos os erros Pylance corrigidos!")
        print("\n📝 Próximos passos:")
        print("1. Reinicie o VS Code ou recarregue a janela (Ctrl+Shift+P -> Reload Window)")
        print("2. Os erros do Pylance devem desaparecer")
        print("3. Faça commit das mudanças")
        print("4. Execute: git push")
        
        print("\n💡 Nota: Esses erros não afetam o funcionamento do sistema,")
        print("   mas é bom corrigi-los para melhor manutenção do código.")
    else:
        print("\n❌ Algumas verificações falharam. Revise manualmente.")

if __name__ == "__main__":
    main() 