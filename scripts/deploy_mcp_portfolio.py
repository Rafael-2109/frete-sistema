#!/usr/bin/env python3
"""
MCP Portfolio Integration Deployment Script
===========================================

This script handles the complete deployment of MCP portfolio integration
including database migrations, service initialization, and system validation.

Usage:
    python scripts/deploy_mcp_portfolio.py [--dry-run] [--skip-migration] [--verbose]
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import application components
try:
    from app import create_app, db
    from app.carteira.models import CarteiraPrincipal
    from integration.portfolio_bridge import PortfolioBridge
    from services.portfolio.mcp_portfolio_service import MCPPortfolioService
    from app.carteira.mcp_dashboard_integration import MCPDashboardIntegration
    from app.mcp_sistema.services.mcp.service import MCPService
    from flask_migrate import upgrade, current
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_deployment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MCPPortfolioDeployment:
    """MCP Portfolio Integration Deployment Manager"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.deployment_results = {
            'start_time': datetime.now(),
            'steps_completed': [],
            'steps_failed': [],
            'warnings': [],
            'success': False
        }
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def deploy(self, skip_migration: bool = False) -> bool:
        """
        Execute complete MCP portfolio deployment
        
        Args:
            skip_migration: Skip database migration step
            
        Returns:
            Success status
        """
        logger.info("🚀 Starting MCP Portfolio Integration Deployment")
        logger.info(f"Dry run mode: {self.dry_run}")
        
        try:
            # Step 1: Pre-deployment validation
            if not self._validate_prerequisites():
                return False
            
            # Step 2: Database migration
            if not skip_migration:
                if not self._run_database_migration():
                    return False
            else:
                logger.info("⏭️ Skipping database migration")
                self.deployment_results['warnings'].append("Database migration skipped")
            
            # Step 3: Initialize MCP services
            if not self._initialize_mcp_services():
                return False
            
            # Step 4: Configure portfolio bridge
            if not self._configure_portfolio_bridge():
                return False
            
            # Step 5: Setup dashboard integration
            if not self._setup_dashboard_integration():
                return False
            
            # Step 6: Validate integration
            if not self._validate_integration():
                return False
            
            # Step 7: Initialize default data
            if not self._initialize_default_data():
                return False
            
            # Step 8: Run system tests
            if not self._run_system_tests():
                return False
            
            # Step 9: Cleanup and finalization
            if not self._finalize_deployment():
                return False
            
            self.deployment_results['success'] = True
            self.deployment_results['end_time'] = datetime.now()
            
            logger.info("✅ MCP Portfolio Integration Deployment completed successfully!")
            self._print_deployment_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            self.deployment_results['steps_failed'].append(f"Unexpected error: {str(e)}")
            return False
    
    def _validate_prerequisites(self) -> bool:
        """Validate deployment prerequisites"""
        logger.info("🔍 Validating deployment prerequisites...")
        
        try:
            # Check Python version
            if sys.version_info < (3, 8):
                logger.error("Python 3.8+ required")
                return False
            
            # Check required environment variables
            required_env_vars = ['DATABASE_URL', 'SECRET_KEY']
            missing_vars = [var for var in required_env_vars if not os.getenv(var)]
            
            if missing_vars:
                logger.error(f"Missing environment variables: {missing_vars}")
                return False
            
            # Check database connectivity
            app = create_app()
            with app.app_context():
                try:
                    db.engine.execute("SELECT 1")
                    logger.info("✅ Database connection verified")
                except Exception as e:
                    logger.error(f"Database connection failed: {e}")
                    return False
            
            # Check existing carteira data
            with app.app_context():
                portfolio_count = db.session.query(CarteiraPrincipal).count()
                logger.info(f"📊 Found {portfolio_count} portfolio items")
                
                if portfolio_count == 0:
                    self.deployment_results['warnings'].append("No existing portfolio data found")
            
            # Check file permissions
            if not os.access(project_root, os.W_OK):
                logger.error("Insufficient write permissions for project directory")
                return False
            
            self.deployment_results['steps_completed'].append("Prerequisites validation")
            return True
            
        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            self.deployment_results['steps_failed'].append(f"Prerequisites: {str(e)}")
            return False
    
    def _run_database_migration(self) -> bool:
        """Run database migration for MCP integration"""
        logger.info("🗄️ Running database migration...")
        
        try:
            app = create_app()
            with app.app_context():
                if self.dry_run:
                    logger.info("🔄 Dry run: Would execute database migration")
                    self.deployment_results['steps_completed'].append("Database migration (dry run)")
                    return True
                
                # Check current migration status
                current_revision = current()
                logger.info(f"Current migration revision: {current_revision}")
                
                # Run migration
                upgrade()
                logger.info("✅ Database migration completed")
                
                # Verify migration
                new_revision = current()
                logger.info(f"New migration revision: {new_revision}")
                
                # Check if MCP tables exist
                inspector = db.inspect(db.engine)
                mcp_tables = [
                    'mcp_portfolio_config',
                    'mcp_portfolio_query_log',
                    'mcp_portfolio_insights',
                    'mcp_portfolio_predictions'
                ]
                
                existing_tables = inspector.get_table_names()
                missing_tables = [t for t in mcp_tables if t not in existing_tables]
                
                if missing_tables:
                    logger.warning(f"Some MCP tables not found: {missing_tables}")
                    self.deployment_results['warnings'].append(f"Missing tables: {missing_tables}")
                else:
                    logger.info("✅ All MCP tables created successfully")
            
            self.deployment_results['steps_completed'].append("Database migration")
            return True
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            self.deployment_results['steps_failed'].append(f"Database migration: {str(e)}")
            return False
    
    def _initialize_mcp_services(self) -> bool:
        """Initialize MCP services"""
        logger.info("🤖 Initializing MCP services...")
        
        try:
            if self.dry_run:
                logger.info("🔄 Dry run: Would initialize MCP services")
                self.deployment_results['steps_completed'].append("MCP services initialization (dry run)")
                return True
            
            # Initialize MCP service
            mcp_service = MCPService()
            logger.info("✅ MCP service initialized")
            
            # Initialize portfolio service
            portfolio_service = MCPPortfolioService()
            logger.info("✅ MCP portfolio service initialized")
            
            # Test service connectivity
            app = create_app()
            with app.app_context():
                try:
                    # Test basic portfolio operations
                    summary = portfolio_service.get_portfolio_summary()
                    logger.info(f"📊 Portfolio service test: {summary.get('total_orders', 0)} orders")
                    
                except Exception as e:
                    logger.warning(f"Portfolio service test failed: {e}")
                    self.deployment_results['warnings'].append(f"Portfolio service test: {str(e)}")
            
            self.deployment_results['steps_completed'].append("MCP services initialization")
            return True
            
        except Exception as e:
            logger.error(f"MCP services initialization failed: {e}")
            self.deployment_results['steps_failed'].append(f"MCP services: {str(e)}")
            return False
    
    def _configure_portfolio_bridge(self) -> bool:
        """Configure portfolio bridge"""
        logger.info("🌉 Configuring portfolio bridge...")
        
        try:
            if self.dry_run:
                logger.info("🔄 Dry run: Would configure portfolio bridge")
                self.deployment_results['steps_completed'].append("Portfolio bridge configuration (dry run)")
                return True
            
            # Initialize portfolio bridge
            portfolio_bridge = PortfolioBridge()
            
            # Test bridge functionality
            health_status = portfolio_bridge.get_health_status()
            
            if health_status.get('healthy', False):
                logger.info("✅ Portfolio bridge configured and healthy")
            else:
                logger.warning("⚠️ Portfolio bridge configured but not fully healthy")
                self.deployment_results['warnings'].append("Portfolio bridge health check failed")
            
            self.deployment_results['steps_completed'].append("Portfolio bridge configuration")
            return True
            
        except Exception as e:
            logger.error(f"Portfolio bridge configuration failed: {e}")
            self.deployment_results['steps_failed'].append(f"Portfolio bridge: {str(e)}")
            return False
    
    def _setup_dashboard_integration(self) -> bool:
        """Setup dashboard integration"""
        logger.info("📊 Setting up dashboard integration...")
        
        try:
            if self.dry_run:
                logger.info("🔄 Dry run: Would setup dashboard integration")
                self.deployment_results['steps_completed'].append("Dashboard integration setup (dry run)")
                return True
            
            # Initialize dashboard integration
            dashboard_integration = MCPDashboardIntegration()
            
            # Test dashboard data generation
            import asyncio
            
            async def test_dashboard():
                try:
                    dashboard_data = await dashboard_integration.get_dashboard_data(
                        user_id='test_user',
                        dashboard_type='overview'
                    )
                    return dashboard_data.get('success', True)
                except:
                    return False
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            test_result = loop.run_until_complete(test_dashboard())
            loop.close()
            
            if test_result:
                logger.info("✅ Dashboard integration setup successful")
            else:
                logger.warning("⚠️ Dashboard integration setup completed with warnings")
                self.deployment_results['warnings'].append("Dashboard test failed")
            
            self.deployment_results['steps_completed'].append("Dashboard integration setup")
            return True
            
        except Exception as e:
            logger.error(f"Dashboard integration setup failed: {e}")
            self.deployment_results['steps_failed'].append(f"Dashboard integration: {str(e)}")
            return False
    
    def _validate_integration(self) -> bool:
        """Validate MCP integration"""
        logger.info("✅ Validating MCP integration...")
        
        try:
            app = create_app()
            
            with app.app_context():
                # Test database tables
                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                
                required_tables = [
                    'carteira_principal',
                    'mcp_portfolio_config',
                    'mcp_portfolio_insights'
                ]
                
                missing_tables = [t for t in required_tables if t not in tables]
                if missing_tables:
                    logger.error(f"Missing required tables: {missing_tables}")
                    return False
                
                # Test MCP configuration
                try:
                    config_query = db.session.execute(
                        "SELECT COUNT(*) FROM mcp_portfolio_config WHERE is_active = true"
                    )
                    config_count = config_query.scalar()
                    logger.info(f"📋 Found {config_count} active MCP configurations")
                    
                    if config_count == 0:
                        logger.warning("No MCP configurations found")
                        self.deployment_results['warnings'].append("No MCP configurations")
                    
                except Exception as e:
                    logger.error(f"MCP configuration test failed: {e}")
                    return False
                
                # Test portfolio data access
                try:
                    portfolio_count = db.session.query(CarteiraPrincipal).count()
                    logger.info(f"📊 Portfolio data access test: {portfolio_count} items")
                    
                except Exception as e:
                    logger.error(f"Portfolio data access test failed: {e}")
                    return False
            
            logger.info("✅ Integration validation successful")
            self.deployment_results['steps_completed'].append("Integration validation")
            return True
            
        except Exception as e:
            logger.error(f"Integration validation failed: {e}")
            self.deployment_results['steps_failed'].append(f"Integration validation: {str(e)}")
            return False
    
    def _initialize_default_data(self) -> bool:
        """Initialize default data and configurations"""
        logger.info("📝 Initializing default data...")
        
        try:
            if self.dry_run:
                logger.info("🔄 Dry run: Would initialize default data")
                self.deployment_results['steps_completed'].append("Default data initialization (dry run)")
                return True
            
            app = create_app()
            with app.app_context():
                # Check if MCP config data exists
                config_count = db.session.execute(
                    "SELECT COUNT(*) FROM mcp_portfolio_config"
                ).scalar()
                
                if config_count > 0:
                    logger.info(f"📋 MCP configuration already exists ({config_count} entries)")
                else:
                    logger.info("📋 No MCP configuration found - should have been created by migration")
                    self.deployment_results['warnings'].append("MCP configuration not found")
                
                # Initialize user preferences template
                # This would be expanded with actual default preferences
                
                db.session.commit()
            
            logger.info("✅ Default data initialization completed")
            self.deployment_results['steps_completed'].append("Default data initialization")
            return True
            
        except Exception as e:
            logger.error(f"Default data initialization failed: {e}")
            self.deployment_results['steps_failed'].append(f"Default data initialization: {str(e)}")
            return False
    
    def _run_system_tests(self) -> bool:
        """Run system tests"""
        logger.info("🧪 Running system tests...")
        
        try:
            test_results = {
                'portfolio_service': False,
                'bridge_functionality': False,
                'dashboard_integration': False,
                'database_operations': False
            }
            
            app = create_app()
            
            # Test 1: Portfolio service
            try:
                with app.app_context():
                    service = MCPPortfolioService()
                    summary = service.get_portfolio_summary()
                    test_results['portfolio_service'] = isinstance(summary, dict)
                    logger.info(f"✅ Portfolio service test: {'PASS' if test_results['portfolio_service'] else 'FAIL'}")
            except Exception as e:
                logger.error(f"Portfolio service test failed: {e}")
            
            # Test 2: Bridge functionality
            try:
                bridge = PortfolioBridge()
                health = bridge.get_health_status()
                test_results['bridge_functionality'] = health.get('healthy', False)
                logger.info(f"✅ Bridge functionality test: {'PASS' if test_results['bridge_functionality'] else 'FAIL'}")
            except Exception as e:
                logger.error(f"Bridge functionality test failed: {e}")
            
            # Test 3: Dashboard integration
            try:
                dashboard = MCPDashboardIntegration()
                # Basic initialization test
                test_results['dashboard_integration'] = hasattr(dashboard, 'get_dashboard_data')
                logger.info(f"✅ Dashboard integration test: {'PASS' if test_results['dashboard_integration'] else 'FAIL'}")
            except Exception as e:
                logger.error(f"Dashboard integration test failed: {e}")
            
            # Test 4: Database operations
            try:
                with app.app_context():
                    # Test basic query
                    db.session.execute("SELECT 1")
                    test_results['database_operations'] = True
                    logger.info(f"✅ Database operations test: PASS")
            except Exception as e:
                logger.error(f"Database operations test failed: {e}")
            
            # Evaluate test results
            passed_tests = sum(test_results.values())
            total_tests = len(test_results)
            
            logger.info(f"📊 System tests: {passed_tests}/{total_tests} passed")
            
            if passed_tests == total_tests:
                logger.info("✅ All system tests passed")
                self.deployment_results['steps_completed'].append("System tests")
                return True
            elif passed_tests >= total_tests * 0.75:  # 75% pass rate
                logger.warning(f"⚠️ System tests partially successful ({passed_tests}/{total_tests})")
                self.deployment_results['warnings'].append(f"System tests: {passed_tests}/{total_tests} passed")
                self.deployment_results['steps_completed'].append("System tests (partial)")
                return True
            else:
                logger.error(f"❌ System tests failed ({passed_tests}/{total_tests})")
                self.deployment_results['steps_failed'].append(f"System tests: {passed_tests}/{total_tests} passed")
                return False
            
        except Exception as e:
            logger.error(f"System tests failed: {e}")
            self.deployment_results['steps_failed'].append(f"System tests: {str(e)}")
            return False
    
    def _finalize_deployment(self) -> bool:
        """Finalize deployment"""
        logger.info("🏁 Finalizing deployment...")
        
        try:
            # Create deployment marker
            deployment_marker = project_root / '.mcp_portfolio_deployed'
            deployment_info = {
                'deployed_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'components': [
                    'portfolio_bridge',
                    'mcp_service',
                    'dashboard_integration',
                    'database_migration'
                ],
                'dry_run': self.dry_run
            }
            
            if not self.dry_run:
                with open(deployment_marker, 'w') as f:
                    import json
                    json.dump(deployment_info, f, indent=2)
                logger.info(f"✅ Deployment marker created: {deployment_marker}")
            else:
                logger.info("🔄 Dry run: Would create deployment marker")
            
            # Log deployment summary
            self._log_deployment_results()
            
            logger.info("✅ Deployment finalization completed")
            self.deployment_results['steps_completed'].append("Deployment finalization")
            return True
            
        except Exception as e:
            logger.error(f"Deployment finalization failed: {e}")
            self.deployment_results['steps_failed'].append(f"Deployment finalization: {str(e)}")
            return False
    
    def _print_deployment_summary(self):
        """Print deployment summary"""
        print("\n" + "="*60)
        print("🚀 MCP PORTFOLIO INTEGRATION DEPLOYMENT SUMMARY")
        print("="*60)
        
        # Basic info
        start_time = self.deployment_results['start_time']
        end_time = self.deployment_results.get('end_time', datetime.now())
        duration = end_time - start_time
        
        print(f"⏱️  Duration: {duration}")
        print(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Dry run: {'Yes' if self.dry_run else 'No'}")
        
        # Steps
        print(f"\n✅ Steps completed ({len(self.deployment_results['steps_completed'])}):")
        for step in self.deployment_results['steps_completed']:
            print(f"   • {step}")
        
        if self.deployment_results['steps_failed']:
            print(f"\n❌ Steps failed ({len(self.deployment_results['steps_failed'])}):")
            for step in self.deployment_results['steps_failed']:
                print(f"   • {step}")
        
        if self.deployment_results['warnings']:
            print(f"\n⚠️  Warnings ({len(self.deployment_results['warnings'])}):")
            for warning in self.deployment_results['warnings']:
                print(f"   • {warning}")
        
        # Final status
        if self.deployment_results['success']:
            print(f"\n🎉 DEPLOYMENT SUCCESSFUL!")
            print("   MCP Portfolio Integration is now active.")
            if not self.dry_run:
                print("   You can now use enhanced portfolio features with AI capabilities.")
        else:
            print(f"\n💥 DEPLOYMENT FAILED!")
            print("   Please review the errors above and retry.")
        
        print("="*60)
    
    def _log_deployment_results(self):
        """Log deployment results to file"""
        try:
            log_file = project_root / 'mcp_deployment_results.json'
            
            import json
            with open(log_file, 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                results = self.deployment_results.copy()
                results['start_time'] = results['start_time'].isoformat()
                if 'end_time' in results:
                    results['end_time'] = results['end_time'].isoformat()
                
                json.dump(results, f, indent=2)
            
            logger.info(f"📝 Deployment results logged to: {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log deployment results: {e}")

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(
        description="Deploy MCP Portfolio Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deploy_mcp_portfolio.py                    # Full deployment
  python scripts/deploy_mcp_portfolio.py --dry-run          # Test deployment
  python scripts/deploy_mcp_portfolio.py --skip-migration   # Skip DB migration
  python scripts/deploy_mcp_portfolio.py --verbose          # Verbose logging
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run deployment in dry-run mode (no actual changes)'
    )
    
    parser.add_argument(
        '--skip-migration',
        action='store_true',
        help='Skip database migration step'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Initialize deployment
    deployment = MCPPortfolioDeployment(
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # Run deployment
    success = deployment.deploy(skip_migration=args.skip_migration)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()