# Testing Guide for A2A-MCP Framework

Comprehensive guide to the automated testing infrastructure for the Market Oracle A2A-MCP framework.

## 🎯 Overview

The testing framework provides:
- **70%+ code coverage requirement**
- **Unit tests** for fast, isolated component testing
- **Integration tests** for component interaction testing
- **CI/CD automation** via GitHub Actions
- **Coverage reporting** with HTML/XML/terminal output

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Fast, isolated unit tests
│   ├── test_workflow_graph.py        # Workflow graph logic
│   └── test_parallel_workflow.py     # Parallel execution
├── integration/             # Component integration tests
│   ├── test_mcp_server.py            # MCP server functionality
│   └── test_orchestrator.py          # Orchestrator workflows
└── README.md                # Test suite documentation
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install project with dev dependencies
uv sync --all-extras

# Or using make
make install-dev
```

### 2. Run Tests

```bash
# Run all tests (fastest)
make test

# Run with coverage
make coverage

# Run and open coverage report
make coverage-open
```

### 3. View Results

Tests will output:
- ✅ Pass/fail status for each test
- 📊 Coverage percentage
- 📝 Missing coverage details
- 🔍 Failed test details

## 📝 Running Tests

### Using Make (Recommended)

```bash
make test              # All non-slow tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-all          # Including slow tests
make coverage          # With coverage report
make test-parallel     # Parallel execution (faster)
make test-watch        # Watch mode (auto-rerun)
make test-failed       # Re-run only failed tests
```

### Using run_tests.sh Script

```bash
# Basic usage
./run_tests.sh                    # All tests
./run_tests.sh -u                 # Unit tests
./run_tests.sh -i                 # Integration tests
./run_tests.sh -c                 # With coverage
./run_tests.sh -v                 # Verbose output
./run_tests.sh -p                 # Parallel execution

# Combined options
./run_tests.sh -u -c -v           # Unit tests, coverage, verbose
./run_tests.sh -i -p              # Integration tests in parallel
./run_tests.sh -m "not slow"      # Exclude slow tests
```

### Using pytest Directly

```bash
# All tests
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/unit/test_workflow_graph.py -v

# Specific test class
uv run pytest tests/unit/test_workflow_graph.py::TestWorkflowGraph -v

# Specific test method
uv run pytest tests/unit/test_workflow_graph.py::TestWorkflowGraph::test_add_node -v

# By marker
uv run pytest -m "unit" -v
uv run pytest -m "integration and not slow" -v

# By pattern
uv run pytest tests/ -k "workflow" -v

# With coverage
uv run pytest tests/ --cov=src/a2a_mcp --cov-report=html
```

## 🏷️ Test Markers

Tests are organized with pytest markers:

| Marker | Description | Usage |
|--------|-------------|-------|
| `@pytest.mark.unit` | Fast, isolated tests | `-m "unit"` |
| `@pytest.mark.integration` | Component interaction tests | `-m "integration"` |
| `@pytest.mark.e2e` | End-to-end system tests | `-m "e2e"` |
| `@pytest.mark.slow` | Long-running tests | `-m "slow"` |

### Examples

```bash
# Unit tests only
pytest -m "unit"

# Integration tests excluding slow ones
pytest -m "integration and not slow"

# All except slow tests (default)
pytest -m "not slow"

# Slow tests only (CI main branch)
pytest -m "slow"
```

## 📊 Coverage

### Viewing Coverage

```bash
# Terminal report
make coverage

# HTML report (opens in browser)
make coverage-open

# XML report (for CI)
pytest --cov=src/a2a_mcp --cov-report=xml
```

### Coverage Requirements

- **Minimum**: 70% overall coverage
- **Target**: 80%+ for new code
- **Exclusions**: Test files, `__init__.py`, abstract methods

### Coverage Configuration

Configured in `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["src/a2a_mcp"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    ...
]
```

## 🔧 Writing Tests

### Unit Test Example

```python
import pytest
from a2a_mcp.common.workflow import WorkflowGraph, WorkflowNode

@pytest.mark.unit
class TestWorkflowGraph:
    """Test workflow graph functionality."""

    def test_add_node(self):
        """Test adding a node to the graph."""
        graph = WorkflowGraph()
        node = WorkflowNode(task="Test task")

        graph.add_node(node)

        assert node.id in graph.nodes
        assert graph.latest_node == node.id

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test asynchronous operation."""
        result = await some_async_function()
        assert result is not None
```

### Integration Test Example

```python
import pytest
from unittest.mock import patch

@pytest.mark.integration
class TestMCPServer:
    """Test MCP server integration."""

    def test_query_database(self, sqlite_connection, temp_db_path):
        """Test database query functionality."""
        with patch.object(server, 'SQLLITE_DB', temp_db_path):
            result = server.query_travel_data("SELECT * FROM flights")
            data = json.loads(result)

            assert 'results' in data
            assert len(data['results']) > 0
```

### Using Fixtures

```python
def test_with_fixture(sample_agent_card, mock_genai_client):
    """Test using multiple fixtures."""
    # Fixtures are automatically injected
    assert sample_agent_card.name == "Test Agent"
    assert mock_genai_client is not None
```

## 🎭 Available Fixtures

Defined in `tests/conftest.py`:

### Database Fixtures
- `temp_db_path` - Temporary SQLite database path
- `sqlite_connection` - SQLite connection with test data

### Mock Fixtures
- `mock_genai_client` - Mock Google Generative AI client
- `mock_genai_embed` - Mock embedding generation
- `mock_a2a_client` - Mock A2A agent client
- `mock_httpx_client` - Mock async HTTP client
- `mock_mcp_server_config` - Mock MCP configuration

### Data Fixtures
- `sample_agent_card` - Sample AgentCard object
- `sample_agent_card_dict` - Sample agent card dictionary
- `sample_task_list` - Sample planner task list
- `agent_cards_dataframe` - DataFrame with agent cards

### Environment Fixtures
- `temp_agent_cards_dir` - Temporary agent cards directory
- `reset_environment` - Cleanup environment vars (autouse)

## 🔄 CI/CD Integration

### GitHub Actions Workflows

#### 1. tests.yml - Main Test Workflow

Runs on:
- Push to `main`, `develop`, `claude/**` branches
- Pull requests to `main`, `develop`

Jobs:
- **test**: Runs on Python 3.11 & 3.12
  - Linting with ruff
  - Unit tests
  - Integration tests (excluding slow)
  - Coverage upload to Codecov

- **test-slow**: Runs slow tests (main branch only)

- **lint**: Code quality checks

- **type-check**: Type checking with mypy

#### 2. coverage.yml - Coverage Reporting

Runs on:
- Push to `main`
- Pull requests to `main`

Features:
- Full coverage report
- PR comments with coverage diff
- Codecov integration
- Coverage badge generation

### Required GitHub Secrets

Configure in repository settings:

```
GOOGLE_API_KEY_TEST - Test API key for Google services
CODECOV_TOKEN       - Token for Codecov integration
```

### Local CI Simulation

```bash
# Run all CI checks locally
make ci

# Individual checks
make lint
make format-check
make type-check
make test
make coverage
```

## 🐛 Debugging Tests

### Enable Logging

```bash
# Debug level
pytest -v -s --log-cli-level=DEBUG

# Info level
pytest -v -s --log-cli-level=INFO
```

### Use Python Debugger

```python
def test_debugging():
    import pdb; pdb.set_trace()  # Breakpoint
    # ... test code
```

### Verbose Assertions

```bash
# Extra verbose
pytest -vv

# Show full diff
pytest -vv --tb=long
```

### Show Print Statements

```bash
# Capture disabled (show print output)
pytest -s
```

## 💡 Best Practices

### 1. Test Naming

```python
# ✅ Good - descriptive names
def test_workflow_graph_adds_node_correctly():
def test_parallel_execution_faster_than_sequential():

# ❌ Bad - vague names
def test_graph():
def test_works():
```

### 2. Test Structure

```python
# ✅ Good - Arrange, Act, Assert
def test_something():
    # Arrange
    graph = WorkflowGraph()
    node = WorkflowNode(task="Test")

    # Act
    graph.add_node(node)

    # Assert
    assert node.id in graph.nodes
```

### 3. Test Isolation

```python
# ✅ Good - each test is independent
def test_feature_a():
    obj = MyClass()
    assert obj.method_a() == expected

def test_feature_b():
    obj = MyClass()  # Fresh instance
    assert obj.method_b() == expected

# ❌ Bad - tests share state
obj = MyClass()  # Shared!

def test_feature_a():
    assert obj.method_a() == expected

def test_feature_b():
    assert obj.method_b() == expected  # Depends on test_a
```

### 4. Mock External Dependencies

```python
# ✅ Good - mock external APIs
@patch('module.external_api_call')
def test_with_mock(mock_api):
    mock_api.return_value = {"data": "test"}
    result = function_using_api()
    assert result is not None

# ❌ Bad - calling real API
def test_without_mock():
    result = function_using_api()  # Real API call!
    assert result is not None
```

### 5. Test Edge Cases

```python
def test_edge_cases():
    # Empty input
    assert process([]) == []

    # None input
    assert process(None) == None

    # Large input
    assert process(range(10000)) is not None

    # Invalid input
    with pytest.raises(ValueError):
        process("invalid")
```

## 🔍 Troubleshooting

### Tests Pass Locally But Fail in CI

**Possible causes:**
- Environment variable differences
- Python version mismatch
- Timing/race conditions
- Missing dependencies

**Solutions:**
```bash
# Match CI Python version
pyenv install 3.11
pyenv local 3.11

# Check environment
env | grep -i api

# Run in verbose mode
pytest -vvs
```

### Coverage Below Threshold

```bash
# See missing coverage
make coverage

# Open detailed report
make coverage-open

# Focus on specific file
pytest tests/unit/test_workflow_graph.py --cov=src/a2a_mcp/common/workflow --cov-report=term-missing
```

### Import Errors

```bash
# Reinstall dependencies
uv sync --all-extras

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Verify installation
uv run python -c "import a2a_mcp; print(a2a_mcp.__file__)"
```

### Slow Tests

```bash
# Identify slow tests
pytest --durations=10

# Run in parallel
pytest -n auto

# Skip slow tests
pytest -m "not slow"
```

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [Coverage.py](https://coverage.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [GitHub Actions](https://docs.github.com/en/actions)

## 🤝 Contributing Tests

When contributing:

1. **Write tests first** (TDD recommended)
2. **Ensure 70%+ coverage** on new code
3. **Run full test suite** before committing
4. **Fix linting** issues
5. **Update documentation** if needed

```bash
# Pre-commit checklist
make lint
make format
make test
make coverage
```

## 📞 Getting Help

- Check [tests/README.md](tests/README.md)
- Review existing tests for examples
- Ask in pull request reviews
- Open an issue for testing problems
