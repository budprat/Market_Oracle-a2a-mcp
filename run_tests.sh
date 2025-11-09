#!/bin/bash

# Test runner script for A2A-MCP framework
# This script provides an easy way to run tests with various options

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
PARALLEL=false
WATCH=false
MARKERS=""

# Function to display help
show_help() {
    echo "Usage: ./run_tests.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -u, --unit          Run only unit tests"
    echo "  -i, --integration   Run only integration tests"
    echo "  -a, --all           Run all tests (default)"
    echo "  -c, --coverage      Generate coverage report"
    echo "  -v, --verbose       Verbose output with logging"
    echo "  -p, --parallel      Run tests in parallel"
    echo "  -w, --watch         Run tests in watch mode"
    echo "  -m, --markers       Pytest markers (e.g., 'not slow')"
    echo "  -f, --failed        Re-run only failed tests"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                    # Run all tests"
    echo "  ./run_tests.sh -u -c              # Unit tests with coverage"
    echo "  ./run_tests.sh -i -v              # Integration tests with verbose output"
    echo "  ./run_tests.sh -a -c -p           # All tests with coverage in parallel"
    echo "  ./run_tests.sh -m 'not slow'      # All tests except slow ones"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--unit)
            TEST_TYPE="unit"
            shift
            ;;
        -i|--integration)
            TEST_TYPE="integration"
            shift
            ;;
        -a|--all)
            TEST_TYPE="all"
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -f|--failed)
            FAILED=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Run: uv venv && source .venv/bin/activate"
fi

# Build pytest command
PYTEST_CMD="uv run pytest"

# Add test path based on type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit"
        if [ -z "$MARKERS" ]; then
            MARKERS="unit"
        fi
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration"
        if [ -z "$MARKERS" ]; then
            MARKERS="integration and not slow"
        fi
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests/"
        if [ -z "$MARKERS" ]; then
            MARKERS="not slow"
        fi
        ;;
esac

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s --log-cli-level=INFO"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage flags
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/a2a_mcp --cov-report=html --cov-report=term-missing --cov-report=xml"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Add markers
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

# Add failed flag
if [ "$FAILED" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --lf"
fi

# Print test configuration
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}A2A-MCP Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Test type:    ${GREEN}$TEST_TYPE${NC}"
echo -e "Coverage:     $([ "$COVERAGE" = true ] && echo -e "${GREEN}enabled${NC}" || echo -e "${YELLOW}disabled${NC}")"
echo -e "Verbose:      $([ "$VERBOSE" = true ] && echo -e "${GREEN}enabled${NC}" || echo -e "disabled")"
echo -e "Parallel:     $([ "$PARALLEL" = true ] && echo -e "${GREEN}enabled${NC}" || echo -e "disabled")"
[ -n "$MARKERS" ] && echo -e "Markers:      ${GREEN}$MARKERS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Watch mode uses different command
if [ "$WATCH" = true ]; then
    echo -e "${YELLOW}Running in watch mode...${NC}"
    uv run pytest-watch tests/ -v
    exit 0
fi

# Run tests
echo -e "${YELLOW}Running: $PYTEST_CMD${NC}"
echo ""

eval $PYTEST_CMD
TEST_EXIT_CODE=$?

# Print results
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report generated:${NC}"
        echo -e "  HTML: ${GREEN}htmlcov/index.html${NC}"
        echo -e "  XML:  ${GREEN}coverage.xml${NC}"
    fi
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit $TEST_EXIT_CODE
fi
