#!/bin/bash

# Load Testing Runner Script
# Executes various load testing scenarios

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST=${HOST:-"http://localhost:8000"}
USERS=${USERS:-100}
SPAWN_RATE=${SPAWN_RATE:-10}
RUN_TIME=${RUN_TIME:-"5m"}
TEST_ENV=${TEST_ENV:-"local"}

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check dependencies
check_dependencies() {
    print_color $BLUE "Checking dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        print_color $RED "Python 3 is not installed!"
        exit 1
    fi
    
    if ! command -v locust &> /dev/null; then
        print_color $YELLOW "Locust is not installed. Installing dependencies..."
        pip install -r requirements.txt
    fi
    
    print_color $GREEN "✓ Dependencies verified"
}

# Function to run a specific test scenario
run_test() {
    scenario=$1
    test_name=$2
    additional_args=$3
    
    print_color $BLUE "\n🚀 Running $test_name..."
    print_color $YELLOW "Configuration:"
    echo "  - Host: $HOST"
    echo "  - Users: $USERS"
    echo "  - Spawn Rate: $SPAWN_RATE"
    echo "  - Duration: $RUN_TIME"
    echo "  - Environment: $TEST_ENV"
    
    # Create results directory
    timestamp=$(date +%Y%m%d_%H%M%S)
    results_dir="test_results/${scenario}_${timestamp}"
    mkdir -p $results_dir
    
    # Run the test
    if [ "$scenario" == "main" ]; then
        locust -f locustfile.py \
            --host=$HOST \
            --users=$USERS \
            --spawn-rate=$SPAWN_RATE \
            --run-time=$RUN_TIME \
            --headless \
            --html=$results_dir/report.html \
            --csv=$results_dir/results \
            $additional_args
    else
        locust -f scenarios/${scenario}.py \
            --host=$HOST \
            --users=$USERS \
            --spawn-rate=$SPAWN_RATE \
            --run-time=$RUN_TIME \
            --headless \
            --html=$results_dir/report.html \
            --csv=$results_dir/results \
            $additional_args
    fi
    
    # Check results
    if [ $? -eq 0 ]; then
        print_color $GREEN "✓ Test completed successfully"
        print_color $BLUE "Results saved to: $results_dir"
        
        # Generate summary
        python3 -c "
import pandas as pd
import json

# Load CSV results
stats = pd.read_csv('$results_dir/results_stats.csv')

# Calculate summary
total_requests = stats['Request Count'].sum()
total_failures = stats['Failure Count'].sum()
avg_response = stats['Average Response Time'].mean()

print('\n📊 Summary:')
print(f'  Total Requests: {total_requests:,}')
print(f'  Failed Requests: {total_failures:,}')
print(f'  Success Rate: {(1 - total_failures/total_requests)*100:.2f}%')
print(f'  Avg Response Time: {avg_response:.0f}ms')
"
    else
        print_color $RED "✗ Test failed!"
        exit 1
    fi
}

# Function to run all scenarios
run_all_scenarios() {
    print_color $BLUE "🎯 Running all load test scenarios...\n"
    
    # 1. API Load Test - Gradual ramp-up to 1000+ req/min
    USERS=250 SPAWN_RATE=25 RUN_TIME="8m" \
        run_test "api_load" "API Load Test (1000+ req/min)"
    
    # 2. Concurrent Users Test
    USERS=500 SPAWN_RATE=50 RUN_TIME="6m" \
        run_test "concurrent_users" "Concurrent Users Test"
    
    # 3. Spike Test
    USERS=1000 SPAWN_RATE=200 RUN_TIME="12m" \
        run_test "spike_test" "Spike Test"
    
    # 4. Main Scenario Mix
    USERS=200 SPAWN_RATE=20 RUN_TIME="10m" \
        run_test "main" "Mixed Scenario Test"
}

# Function to run stress test
run_stress_test() {
    print_color $YELLOW "⚠️  Running STRESS TEST - This will push the system to its limits!"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        USERS=2000 SPAWN_RATE=100 RUN_TIME="20m" \
            run_test "spike_test" "Stress Test" "--stop-timeout=60"
    else
        print_color $BLUE "Stress test cancelled."
    fi
}

# Function to run smoke test
run_smoke_test() {
    print_color $BLUE "🔍 Running smoke test..."
    USERS=10 SPAWN_RATE=2 RUN_TIME="2m" \
        run_test "api_load" "Smoke Test"
}

# Function to run custom test
run_custom_test() {
    print_color $BLUE "🎨 Running custom test..."
    
    # Get custom parameters
    read -p "Enter number of users (default: 100): " custom_users
    read -p "Enter spawn rate (default: 10): " custom_spawn
    read -p "Enter duration (default: 5m): " custom_time
    read -p "Enter scenario (api_load/concurrent_users/spike_test/main): " custom_scenario
    
    USERS=${custom_users:-100}
    SPAWN_RATE=${custom_spawn:-10}
    RUN_TIME=${custom_time:-"5m"}
    scenario=${custom_scenario:-"main"}
    
    run_test "$scenario" "Custom Test"
}

# Function to show menu
show_menu() {
    echo
    print_color $BLUE "🚀 Load Testing Menu"
    echo "===================="
    echo "1) Run Smoke Test (Quick validation)"
    echo "2) Run API Load Test (1000+ req/min)"
    echo "3) Run Concurrent Users Test"
    echo "4) Run Spike Test"
    echo "5) Run All Scenarios"
    echo "6) Run Stress Test (CAUTION!)"
    echo "7) Run Custom Test"
    echo "8) Exit"
    echo
}

# Main script
main() {
    print_color $GREEN "🏃 Freight System Load Testing Runner"
    print_color $GREEN "====================================="
    
    # Check dependencies
    check_dependencies
    
    # Export environment
    export TEST_ENV=$TEST_ENV
    
    # Handle command line arguments
    if [ $# -gt 0 ]; then
        case $1 in
            smoke)
                run_smoke_test
                ;;
            api)
                USERS=250 SPAWN_RATE=25 RUN_TIME="8m" \
                    run_test "api_load" "API Load Test"
                ;;
            concurrent)
                USERS=500 SPAWN_RATE=50 RUN_TIME="6m" \
                    run_test "concurrent_users" "Concurrent Users Test"
                ;;
            spike)
                USERS=1000 SPAWN_RATE=200 RUN_TIME="12m" \
                    run_test "spike_test" "Spike Test"
                ;;
            all)
                run_all_scenarios
                ;;
            stress)
                run_stress_test
                ;;
            *)
                print_color $RED "Unknown command: $1"
                echo "Usage: $0 [smoke|api|concurrent|spike|all|stress]"
                exit 1
                ;;
        esac
    else
        # Interactive menu
        while true; do
            show_menu
            read -p "Select an option: " choice
            
            case $choice in
                1) run_smoke_test ;;
                2) USERS=250 SPAWN_RATE=25 RUN_TIME="8m" \
                    run_test "api_load" "API Load Test" ;;
                3) USERS=500 SPAWN_RATE=50 RUN_TIME="6m" \
                    run_test "concurrent_users" "Concurrent Users Test" ;;
                4) USERS=1000 SPAWN_RATE=200 RUN_TIME="12m" \
                    run_test "spike_test" "Spike Test" ;;
                5) run_all_scenarios ;;
                6) run_stress_test ;;
                7) run_custom_test ;;
                8) print_color $GREEN "Goodbye!"; exit 0 ;;
                *) print_color $RED "Invalid option!" ;;
            esac
            
            echo
            read -p "Press Enter to continue..."
        done
    fi
}

# Run main function
main "$@"