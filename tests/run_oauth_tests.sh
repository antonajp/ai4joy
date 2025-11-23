#!/bin/bash
#
# OAuth and Rate Limiting Test Execution Script
# Runs comprehensive tests for IQS-45 deployment validation
#
# Usage:
#   ./run_oauth_tests.sh [test-suite]
#
# Test Suites:
#   all              - Run all OAuth and rate limiting tests
#   oauth            - Run only OAuth authentication tests
#   ratelimit        - Run only rate limiting tests
#   infra            - Run only infrastructure validation tests
#   unit             - Run fast unit tests only
#   integration      - Run integration tests (requires deployment)
#   manual           - List manual tests requiring human execution
#
# Environment Variables:
#   SERVICE_URL      - Base URL for deployed service (default: https://ai4joy.org)
#   GCP_PROJECT_ID   - GCP project ID (default: improvOlympics)
#   TEST_USER_ID     - OAuth subject ID for test user
#   TEST_USER_EMAIL  - Test user email address
#   GOOGLE_APPLICATION_CREDENTIALS - Path to service account key

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
export SERVICE_URL="${SERVICE_URL:-https://ai4joy.org}"
export GCP_PROJECT_ID="${GCP_PROJECT_ID:-improvOlympics}"

# Test suite selection
TEST_SUITE="${1:-all}"

# Functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "$1"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python installed: $PYTHON_VERSION"
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi

    # Check pytest installed
    if python3 -m pytest --version &> /dev/null; then
        PYTEST_VERSION=$(python3 -m pytest --version | head -1)
        print_success "$PYTEST_VERSION installed"
    else
        print_error "pytest not found. Installing test dependencies..."
        pip install -r "$SCRIPT_DIR/requirements-test.txt"
    fi

    # Check environment variables
    print_info ""
    print_info "Environment Configuration:"
    print_info "  SERVICE_URL: $SERVICE_URL"
    print_info "  GCP_PROJECT_ID: $GCP_PROJECT_ID"

    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_warning "GOOGLE_APPLICATION_CREDENTIALS not set"
        print_info "  Some tests may be skipped (Firestore access required)"
    else
        print_success "GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
    fi

    if [ -z "$TEST_USER_ID" ]; then
        print_warning "TEST_USER_ID not set"
        print_info "  Rate limiting tests will be skipped"
    else
        print_success "TEST_USER_ID: $TEST_USER_ID"
    fi

    print_info ""
}

# Run OAuth authentication tests
run_oauth_tests() {
    print_header "Running OAuth Authentication Tests"

    python3 -m pytest \
        "$SCRIPT_DIR/test_oauth_authentication.py" \
        -v \
        --tb=short \
        --capture=no \
        -m "not manual" \
        || {
            print_error "OAuth authentication tests failed"
            return 1
        }

    print_success "OAuth authentication tests completed"
}

# Run rate limiting tests
run_ratelimit_tests() {
    print_header "Running Rate Limiting Tests"

    if [ -z "$TEST_USER_ID" ]; then
        print_warning "TEST_USER_ID not set - skipping rate limiting tests"
        print_info "Set TEST_USER_ID to run these tests:"
        print_info "  export TEST_USER_ID=your-oauth-subject-id"
        return 0
    fi

    python3 -m pytest \
        "$SCRIPT_DIR/test_rate_limiting.py" \
        -v \
        --tb=short \
        --capture=no \
        || {
            print_error "Rate limiting tests failed"
            return 1
        }

    print_success "Rate limiting tests completed"
}

# Run infrastructure validation tests
run_infra_tests() {
    print_header "Running Infrastructure Validation Tests"

    python3 -m pytest \
        "$SCRIPT_DIR/test_infrastructure_validation.py" \
        -v \
        --tb=short \
        --capture=no \
        -m "not manual" \
        || {
            print_error "Infrastructure validation tests failed"
            return 1
        }

    print_success "Infrastructure validation tests completed"
}

# Run unit tests only (fast, no deployment required)
run_unit_tests() {
    print_header "Running Unit Tests (No Deployment Required)"

    python3 -m pytest \
        "$SCRIPT_DIR/test_oauth_authentication.py::TestIAPHeaderExtraction" \
        -v \
        --tb=short \
        || {
            print_error "Unit tests failed"
            return 1
        }

    print_success "Unit tests completed"
}

# Run integration tests (requires deployment)
run_integration_tests() {
    print_header "Running Integration Tests (Requires Deployment)"

    # Check if service is accessible
    if ! curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" | grep -q "200"; then
        print_error "Service not accessible at $SERVICE_URL"
        print_info "Please ensure the application is deployed before running integration tests"
        exit 1
    fi

    print_success "Service accessible at $SERVICE_URL"

    python3 -m pytest \
        "$SCRIPT_DIR/test_oauth_authentication.py" \
        "$SCRIPT_DIR/test_infrastructure_validation.py" \
        -v \
        --tb=short \
        --capture=no \
        -m "not manual and integration" \
        || {
            print_error "Integration tests failed"
            return 1
        }

    print_success "Integration tests completed"
}

# List manual tests
list_manual_tests() {
    print_header "Manual Tests Requiring Human Execution"

    print_info ""
    print_info "The following tests require manual execution with a web browser:"
    print_info ""

    python3 -m pytest \
        "$SCRIPT_DIR/test_oauth_authentication.py" \
        "$SCRIPT_DIR/test_rate_limiting.py" \
        "$SCRIPT_DIR/test_infrastructure_validation.py" \
        --collect-only \
        -m "manual" \
        -q

    print_info ""
    print_info "To run manual tests:"
    print_info "  1. Open an incognito/private browser window"
    print_info "  2. Navigate to $SERVICE_URL"
    print_info "  3. Follow the test procedures documented in each test case"
    print_info ""
}

# Run all tests
run_all_tests() {
    print_header "Running Complete OAuth & Rate Limiting Test Suite"

    local failed=0

    # Run unit tests first (fast)
    run_unit_tests || failed=$((failed + 1))

    # Run infrastructure tests (no auth required)
    run_infra_tests || failed=$((failed + 1))

    # Run OAuth tests (may have skips)
    run_oauth_tests || failed=$((failed + 1))

    # Run rate limiting tests (may have skips)
    run_ratelimit_tests || failed=$((failed + 1))

    # Summary
    print_info ""
    print_header "Test Execution Summary"

    if [ $failed -eq 0 ]; then
        print_success "All automated tests passed!"
        print_info ""
        print_info "Next steps:"
        print_info "  1. Review manual tests: ./run_oauth_tests.sh manual"
        print_info "  2. Execute manual OAuth flow validation"
        print_info "  3. Deploy to production once all tests pass"
    else
        print_error "Some tests failed. Please review the output above."
        return 1
    fi
}

# Generate test report
generate_report() {
    print_header "Generating Test Report"

    local REPORT_FILE="$SCRIPT_DIR/test_results_$(date +%Y%m%d_%H%M%S).html"

    python3 -m pytest \
        "$SCRIPT_DIR/test_oauth_authentication.py" \
        "$SCRIPT_DIR/test_rate_limiting.py" \
        "$SCRIPT_DIR/test_infrastructure_validation.py" \
        --html="$REPORT_FILE" \
        --self-contained-html \
        -m "not manual" \
        || true

    if [ -f "$REPORT_FILE" ]; then
        print_success "Test report generated: $REPORT_FILE"
        print_info "Open in browser: open $REPORT_FILE"
    else
        print_warning "Failed to generate HTML report (pytest-html may not be installed)"
        print_info "Install with: pip install pytest-html"
    fi
}

# Main execution
main() {
    check_prerequisites

    case "$TEST_SUITE" in
        all)
            run_all_tests
            ;;
        oauth)
            run_oauth_tests
            ;;
        ratelimit)
            run_ratelimit_tests
            ;;
        infra)
            run_infra_tests
            ;;
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        manual)
            list_manual_tests
            ;;
        report)
            generate_report
            ;;
        *)
            print_error "Unknown test suite: $TEST_SUITE"
            print_info ""
            print_info "Usage: $0 [test-suite]"
            print_info ""
            print_info "Available test suites:"
            print_info "  all         - Run all OAuth and rate limiting tests (default)"
            print_info "  oauth       - Run only OAuth authentication tests"
            print_info "  ratelimit   - Run only rate limiting tests"
            print_info "  infra       - Run only infrastructure validation tests"
            print_info "  unit        - Run fast unit tests only"
            print_info "  integration - Run integration tests (requires deployment)"
            print_info "  manual      - List manual tests requiring human execution"
            print_info "  report      - Generate HTML test report"
            exit 1
            ;;
    esac
}

# Run main function
main
