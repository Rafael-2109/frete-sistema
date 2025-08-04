#!/usr/bin/env python3
"""Run comprehensive database optimization analysis."""

import os
import sys
import argparse
import logging
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from query_analyzer import QueryAnalyzer
from index_optimizer import IndexOptimizer
from cache_optimizer import CacheOptimizer
from connection_pool_optimizer import ConnectionPoolOptimizer
from performance_dashboard import PerformanceDashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file: str = None) -> dict:
    """Load database configuration."""
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default configuration
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 5432)),
        'database': os.environ.get('DB_NAME', 'frete_db'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'postgres')
    }


def run_query_analysis(analyzer: QueryAnalyzer, options: dict):
    """Run query performance analysis."""
    logger.info("Starting query analysis...")
    
    # Analyze specific queries if provided
    if options.get('analyze_query'):
        result = analyzer.analyze_query(options['analyze_query'])
        print("\nQuery Analysis Result:")
        print(json.dumps(result, indent=2, default=str))
        return
    
    # Monitor queries for specified duration
    duration = options.get('monitor_duration', 5)
    logger.info(f"Monitoring queries for {duration} minutes...")
    analyzer.monitor_queries(duration)
    
    # Generate report
    report = analyzer.generate_report()
    print("\nQuery Analysis Summary:")
    print(f"Total queries analyzed: {report['summary']['total_queries_analyzed']}")
    print(f"Slow queries found: {report['summary']['slow_queries']}")
    print(f"Total execution time: {report['summary']['total_execution_time']:.2f}s")
    
    # Show top slow queries
    if report['slow_queries']:
        print("\nTop Slow Queries:")
        for i, query in enumerate(report['slow_queries'][:5], 1):
            print(f"\n{i}. Query: {query['query'][:100]}...")
            print(f"   Avg Time: {query['avg_time']:.3f}s")
            print(f"   Executions: {query['execution_count']}")
            if query['analysis'].get('issues'):
                print(f"   Issues: {', '.join(query['analysis']['issues'])}")


def run_index_optimization(optimizer: IndexOptimizer, options: dict):
    """Run index optimization analysis."""
    logger.info("Starting index optimization...")
    
    # Analyze missing indexes
    missing = optimizer.analyze_missing_indexes()
    print(f"\nFound {len(missing)} missing indexes")
    
    if missing and options.get('verbose'):
        print("\nMissing Indexes:")
        for idx in missing[:10]:
            print(f"- {idx.table_name}.{', '.join(idx.columns)}")
            print(f"  Reason: {idx.reason}")
            print(f"  SQL: {idx.create_statement}")
    
    # Analyze unused indexes
    unused = optimizer.analyze_unused_indexes()
    print(f"\nFound {len(unused)} unused indexes")
    
    if unused and options.get('verbose'):
        print("\nUnused Indexes:")
        for idx in unused[:10]:
            print(f"- {idx['index']} on {idx['table']} (Size: {idx['size']}, Scans: {idx['scans']})")
    
    # Analyze duplicate indexes
    duplicates = optimizer.analyze_duplicate_indexes()
    print(f"\nFound {len(duplicates)} duplicate indexes")
    
    # Generate optimization script
    script_file = optimizer.generate_optimization_script(
        options.get('output_file', 'index_optimization.sql')
    )
    print(f"\nOptimization script generated: {script_file}")
    
    # Apply recommendations if requested
    if options.get('apply'):
        logger.warning("Applying index recommendations...")
        results = optimizer.apply_recommendations(dry_run=not options.get('force'))
        print(f"\nApplied {len([r for r in results if r['status'] == 'success'])} recommendations")


def run_cache_optimization(optimizer: CacheOptimizer, options: dict):
    """Run cache optimization analysis."""
    logger.info("Starting cache optimization...")
    
    # Analyze cache performance
    analysis = optimizer.analyze_cache_performance()
    
    print("\nCache Performance:")
    print(f"Hit Rate: {analysis['stats']['hit_rate']:.1%}")
    print(f"Total Requests: {analysis['stats']['total_requests']:,}")
    print(f"Cache Size: {analysis['memory_usage']['used_mb']:.1f} MB / {analysis['memory_usage']['max_mb']:.1f} MB")
    
    # Show hot patterns
    if analysis.get('hot_patterns'):
        print("\nHot Query Patterns:")
        for pattern in analysis['hot_patterns'][:5]:
            print(f"- {pattern['pattern'][:80]}...")
            print(f"  Accesses: {pattern['access_count']}, Avg Interval: {pattern['avg_interval']:.1f}s")
    
    # Show recommendations
    if analysis.get('recommendations'):
        print("\nCache Recommendations:")
        for rec in analysis['recommendations']:
            print(f"[{rec['severity'].upper()}] {rec['message']}")
    
    # Generate detailed report
    print("\n" + optimizer.get_cache_report())


def run_connection_pool_optimization(optimizer: ConnectionPoolOptimizer, options: dict):
    """Run connection pool optimization."""
    logger.info("Starting connection pool optimization...")
    
    # Let it run for a bit to collect metrics
    import time
    logger.info("Collecting connection pool metrics (30 seconds)...")
    time.sleep(30)
    
    # Get optimization report
    report = optimizer.get_optimization_report()
    
    print("\nConnection Pool Status:")
    status = report.get('current_status', {})
    for key, value in status.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\nPerformance Metrics:")
    metrics = report.get('performance_metrics', {})
    for key, value in metrics.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\nConnection Analysis:")
    analysis = report.get('connection_analysis', {})
    for key, value in analysis.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    # Show recommendations
    if report.get('recommendations'):
        print("\nPool Optimization Recommendations:")
        for rec in report['recommendations']:
            print(f"- [{rec['category']}] {rec['recommendation']}")
            print(f"  Reason: {rec['reason']}")
    
    # Export metrics if requested
    if options.get('export_metrics'):
        metrics_file = optimizer.export_metrics()
        print(f"\nMetrics exported to: {metrics_file}")


def run_comprehensive_analysis(config: dict, options: dict):
    """Run all optimization analyses."""
    logger.info("Starting comprehensive database optimization analysis...")
    
    # Initialize all optimizers
    query_analyzer = QueryAnalyzer(config)
    index_optimizer = IndexOptimizer(config)
    cache_optimizer = CacheOptimizer(max_memory_mb=256)
    pool_optimizer = ConnectionPoolOptimizer(config)
    
    # Create output directory
    output_dir = options.get('output_dir', 'optimization_results')
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'database': config['database'],
        'analyses': {}
    }
    
    # Run query analysis
    try:
        logger.info("\n=== QUERY ANALYSIS ===")
        query_analyzer.monitor_queries(2)  # Monitor for 2 minutes
        query_report = query_analyzer.generate_report(
            os.path.join(output_dir, 'query_analysis.json')
        )
        results['analyses']['queries'] = query_report['summary']
        print("✓ Query analysis complete")
    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        results['analyses']['queries'] = {'error': str(e)}
    
    # Run index optimization
    try:
        logger.info("\n=== INDEX OPTIMIZATION ===")
        missing = index_optimizer.analyze_missing_indexes()
        unused = index_optimizer.analyze_unused_indexes()
        duplicates = index_optimizer.analyze_duplicate_indexes()
        
        index_optimizer.generate_optimization_script(
            os.path.join(output_dir, 'index_optimization.sql')
        )
        
        results['analyses']['indexes'] = {
            'missing': len(missing),
            'unused': len(unused),
            'duplicates': len(duplicates)
        }
        print("✓ Index optimization complete")
    except Exception as e:
        logger.error(f"Index optimization failed: {e}")
        results['analyses']['indexes'] = {'error': str(e)}
    
    # Run cache optimization
    try:
        logger.info("\n=== CACHE OPTIMIZATION ===")
        cache_analysis = cache_optimizer.analyze_cache_performance()
        results['analyses']['cache'] = cache_analysis['stats']
        
        with open(os.path.join(output_dir, 'cache_report.txt'), 'w') as f:
            f.write(cache_optimizer.get_cache_report())
        
        print("✓ Cache optimization complete")
    except Exception as e:
        logger.error(f"Cache optimization failed: {e}")
        results['analyses']['cache'] = {'error': str(e)}
    
    # Run connection pool optimization
    try:
        logger.info("\n=== CONNECTION POOL OPTIMIZATION ===")
        pool_report = pool_optimizer.get_optimization_report()
        results['analyses']['connection_pool'] = pool_report.get('current_status', {})
        
        pool_optimizer.export_metrics(
            os.path.join(output_dir, 'pool_metrics.json')
        )
        
        print("✓ Connection pool optimization complete")
    except Exception as e:
        logger.error(f"Connection pool optimization failed: {e}")
        results['analyses']['connection_pool'] = {'error': str(e)}
    finally:
        pool_optimizer.shutdown()
    
    # Save comprehensive results
    with open(os.path.join(output_dir, 'optimization_results.json'), 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Comprehensive analysis complete!")
    print(f"Results saved to: {output_dir}/")
    
    # Generate summary report
    generate_summary_report(results, output_dir)


def generate_summary_report(results: dict, output_dir: str):
    """Generate a human-readable summary report."""
    report_lines = [
        "DATABASE OPTIMIZATION SUMMARY REPORT",
        "=" * 50,
        f"Generated: {results['timestamp']}",
        f"Database: {results['database']}",
        "",
        "ANALYSIS RESULTS:",
        "-" * 30
    ]
    
    # Query analysis
    if 'queries' in results['analyses']:
        q = results['analyses']['queries']
        if 'error' not in q:
            report_lines.extend([
                "\nQuery Performance:",
                f"  - Total queries analyzed: {q.get('total_queries_analyzed', 0)}",
                f"  - Slow queries found: {q.get('slow_queries', 0)}",
                f"  - Total execution time: {q.get('total_execution_time', 0):.2f}s"
            ])
    
    # Index optimization
    if 'indexes' in results['analyses']:
        i = results['analyses']['indexes']
        if 'error' not in i:
            report_lines.extend([
                "\nIndex Optimization:",
                f"  - Missing indexes: {i.get('missing', 0)}",
                f"  - Unused indexes: {i.get('unused', 0)}",
                f"  - Duplicate indexes: {i.get('duplicates', 0)}"
            ])
    
    # Cache performance
    if 'cache' in results['analyses']:
        c = results['analyses']['cache']
        if 'error' not in c:
            report_lines.extend([
                "\nCache Performance:",
                f"  - Hit rate: {c.get('hit_rate', 0):.1%}",
                f"  - Total requests: {c.get('total_requests', 0):,}",
                f"  - Evictions: {c.get('evictions', 0):,}"
            ])
    
    # Connection pool
    if 'connection_pool' in results['analyses']:
        p = results['analyses']['connection_pool']
        if 'error' not in p:
            report_lines.extend([
                "\nConnection Pool:",
                f"  - Total connections: {p.get('total_connections', 0)}",
                f"  - Active connections: {p.get('active_connections', 0)}",
                f"  - Pool utilization: {p.get('pool_utilization', '0%')}"
            ])
    
    report_lines.extend([
        "",
        "RECOMMENDATIONS:",
        "-" * 30,
        "1. Review and apply index recommendations in index_optimization.sql",
        "2. Monitor slow queries identified in query_analysis.json",
        "3. Adjust cache size based on hit rate analysis",
        "4. Fine-tune connection pool size based on utilization metrics",
        "",
        "For detailed results, see individual report files in the output directory."
    ])
    
    with open(os.path.join(output_dir, 'summary_report.txt'), 'w') as f:
        f.write('\n'.join(report_lines))
    
    print("\n" + '\n'.join(report_lines))


def main():
    parser = argparse.ArgumentParser(description='Database Performance Optimization Tool')
    parser.add_argument('--config', help='Database configuration file (JSON)')
    parser.add_argument('--mode', choices=['query', 'index', 'cache', 'pool', 'all', 'dashboard'], 
                       default='all', help='Optimization mode')
    parser.add_argument('--output-dir', help='Output directory for results')
    parser.add_argument('--output-file', help='Output file for specific results')
    parser.add_argument('--monitor-duration', type=int, default=5, 
                       help='Query monitoring duration in minutes')
    parser.add_argument('--analyze-query', help='Analyze a specific query')
    parser.add_argument('--apply', action='store_true', help='Apply recommendations')
    parser.add_argument('--force', action='store_true', help='Force apply without dry run')
    parser.add_argument('--export-metrics', action='store_true', help='Export detailed metrics')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--dashboard-port', type=int, default=5000, 
                       help='Port for web dashboard')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Prepare options
    options = vars(args)
    
    try:
        if args.mode == 'dashboard':
            # Start performance dashboard
            dashboard = PerformanceDashboard(config)
            logger.info(f"Starting performance dashboard on port {args.dashboard_port}")
            logger.info("Press Ctrl+C to stop")
            dashboard.create_web_dashboard(args.dashboard_port)
        elif args.mode == 'all':
            # Run comprehensive analysis
            run_comprehensive_analysis(config, options)
        else:
            # Run specific optimization
            if args.mode == 'query':
                analyzer = QueryAnalyzer(config)
                run_query_analysis(analyzer, options)
            elif args.mode == 'index':
                optimizer = IndexOptimizer(config)
                run_index_optimization(optimizer, options)
            elif args.mode == 'cache':
                optimizer = CacheOptimizer()
                run_cache_optimization(optimizer, options)
            elif args.mode == 'pool':
                optimizer = ConnectionPoolOptimizer(config)
                try:
                    run_connection_pool_optimization(optimizer, options)
                finally:
                    optimizer.shutdown()
    
    except KeyboardInterrupt:
        logger.info("\nOptimization interrupted by user")
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()