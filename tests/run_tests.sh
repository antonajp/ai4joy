#!/bin/bash
# Improv Olympics Test Execution Script
# Provides quick commands for common test scenarios

set -e  # Exit on error

PROJECT_ROOT="/Users/jpantona/Documents/code/ai4joy"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment is activated
check_venv() {
    if [[ -z "${VIRTUAL_ENV}" ]]; then
        print_warn "Virtual environment not activated. Activate with: source venv/bin/activate"
    fi
}

# Check if required environment variables are set
check_env() {
    if [[ -z "${GCP_PROJECT_ID}" ]]; then
        print_error "GCP_PROJECT_ID not set"
        exit 1
    fi
    if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
        print_error "GOOGLE_APPLICATION_CREDENTIALS not set"
        exit 1
    fi
    print_info "Environment configuration validated"
}

# Usage information
usage() {
    cat << EOF
Usage: ./run_tests.sh [COMMAND]

Commands:
  all                 Run all tests
  pre-deploy          Run pre-deployment tests (container, agents, tools)
  integration         Run integration tests
  performance         Run performance tests
  evaluation          Run agent evaluation tests
  quick               Run quick tests (exclude slow tests)
  specific TEST       Run specific test file or function
  coverage            Run tests with coverage report

Examples:
  ./run_tests.sh pre-deploy
  ./run_tests.sh integration
  ./run_tests.sh specific test_e2e_session.py
  ./run_tests.sh coverage

EOF
}

# Main command handling
case "${1:-}" in
    all)
        print_info "Running all tests..."
        check_venv
        check_env
        pytest tests/ -v
        ;;

    pre-deploy)
        print_info "Running pre-deployment tests..."
        check_venv
        check_env
        pytest tests/test_container_build.py \
               tests/test_agent_initialization.py \
               tests/test_model_integration.py \
               tests/test_tools/ \
               -v
        ;;

    integration)
        print_info "Running integration tests..."
        check_venv
        check_env
        pytest tests/test_integration/ -v -m integration
        ;;

    performance)
        print_info "Running performance tests..."
        check_venv
        check_env
        pytest tests/test_performance/ -v -m performance
        ;;

    evaluation)
        print_info "Running agent evaluation tests..."
        check_venv
        check_env
        pytest tests/test_evaluation/ -v -m evaluation
        ;;

    quick)
        print_info "Running quick tests (excluding slow tests)..."
        check_venv
        check_env
        pytest tests/ -v -m "not slow"
        ;;

    specific)
        if [[ -z "${2:-}" ]]; then
            print_error "Please specify test file or function"
            echo "Example: ./run_tests.sh specific test_e2e_session.py"
            exit 1
        fi
        print_info "Running specific test: $2"
        check_venv
        check_env
        pytest "tests/$2" -v
        ;;

    coverage)
        print_info "Running tests with coverage..."
        check_venv
        check_env
        pytest tests/ --cov=improv_olympics --cov-report=html --cov-report=term
        print_info "Coverage report generated in htmlcov/index.html"
        ;;

    parallel)
        print_info "Running tests in parallel..."
        check_venv
        check_env
        pytest tests/ -v -n auto
        ;;

    smoke)
        print_info "Running smoke tests (critical paths only)..."
        check_venv
        check_env
        pytest tests/test_integration/test_e2e_session.py::TestE2ESession::test_session_initialization \
               tests/test_model_integration.py::TestModelIntegration::test_flash_model_access \
               -v
        ;;

    help|--help|-h)
        usage
        ;;

    *)
        print_error "Unknown command: $1"
        usage
        exit 1
        ;;
esac

print_info "Test execution complete!"
