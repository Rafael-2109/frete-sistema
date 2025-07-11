#!/usr/bin/env python3
"""
Teste dos imports corrigidos
"""

def test_validation_utils():
    """Testa ValidationUtils"""
    try:
        from utils.validation_utils import ValidationUtils, get_validation_utils
        
        # Teste 1: Instanciação
        utils = ValidationUtils()
        print("✅ ValidationUtils: Instanciação OK")
        
        # Teste 2: Validação básica
        result = utils.validate("teste")
        print(f"✅ ValidationUtils: Validação básica OK - {result}")
        
        # Teste 3: Função de conveniência
        utils2 = get_validation_utils()
        print("✅ ValidationUtils: Função de conveniência OK")
        
        return True
        
    except Exception as e:
        print(f"❌ ValidationUtils: {e}")
        return False

def test_external_api_integration():
    """Testa ExternalAPIIntegration"""
    try:
        from integration.external_api_integration import ExternalAPIIntegration, get_external_api_integration
        
        # Teste 1: Instanciação
        integration = ExternalAPIIntegration()
        print("✅ ExternalAPIIntegration: Instanciação OK")
        
        # Teste 2: Função de conveniência
        integration2 = get_external_api_integration()
        print("✅ ExternalAPIIntegration: Função de conveniência OK")
        
        return True
        
    except Exception as e:
        print(f"❌ ExternalAPIIntegration: {e}")
        return False

def test_legacy_compatibility():
    """Testa legacy_compatibility"""
    try:
        from utils.legacy_compatibility import ClaudeRealIntegration, ExternalAPIIntegration
        
        # Teste 1: Alias funciona
        print("✅ LegacyCompatibility: Alias ClaudeRealIntegration OK")
        
        # Teste 2: Classe original funciona
        print("✅ LegacyCompatibility: ExternalAPIIntegration OK")
        
        return True
        
    except Exception as e:
        print(f"❌ LegacyCompatibility: {e}")
        return False

def test_utils_manager():
    """Testa UtilsManager"""
    try:
        from utils.utils_manager import UtilsManager, get_utilsmanager
        
        # Teste 1: Instanciação
        manager = UtilsManager()
        print("✅ UtilsManager: Instanciação OK")
        
        # Teste 2: Função de conveniência
        manager2 = get_utilsmanager()
        print("✅ UtilsManager: Função de conveniência OK")
        
        # Teste 3: Componentes
        status = manager.get_status()
        print(f"✅ UtilsManager: Status OK - {status['total_components']} componentes")
        
        return True
        
    except Exception as e:
        print(f"❌ UtilsManager: {e}")
        return False

def test_validators():
    """Testa Validators"""
    try:
        from validators.validator_manager import ValidatorManager, get_validator_manager
        
        # Teste 1: Instanciação
        manager = ValidatorManager()
        print("✅ ValidatorManager: Instanciação OK")
        
        # Teste 2: Função de conveniência
        manager2 = get_validator_manager()
        print("✅ ValidatorManager: Função de conveniência OK")
        
        # Teste 3: Status
        status = manager.get_validation_status()
        print(f"✅ ValidatorManager: Status OK - {len(status.get('validators', {}))} validadores")
        
        return True
        
    except Exception as e:
        print(f"❌ ValidatorManager: {e}")
        return False

def main():
    """Função principal"""
    print("🧪 TESTE DOS IMPORTS CORRIGIDOS")
    print("=" * 50)
    
    tests = [
        ("ValidationUtils", test_validation_utils),
        ("ExternalAPIIntegration", test_external_api_integration),
        ("LegacyCompatibility", test_legacy_compatibility),
        ("UtilsManager", test_utils_manager),
        ("Validators", test_validators)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testando {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Erro geral - {e}")
            results.append((test_name, False))
    
    # Resumo
    print("\n📊 RESUMO DOS TESTES:")
    print("-" * 30)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 RESULTADO FINAL: {passed}/{total} testes passaram ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 TODOS OS IMPORTS ESTÃO FUNCIONANDO!")
    elif passed >= total * 0.8:
        print("🟡 MAIORIA DOS IMPORTS FUNCIONA - Algumas correções menores necessárias")
    else:
        print("🔴 VÁRIOS IMPORTS COM PROBLEMAS - Correções adicionais necessárias")

if __name__ == "__main__":
    main() 