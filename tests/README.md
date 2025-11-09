# A2A-MCP Test Suite

Comprehensive automated testing infrastructure for the Market Oracle A2A-MCP framework.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_workflow_graph.py
│   └── test_parallel_workflow.py
├── integration/             # Integration tests (require components)
│   ├── test_mcp_server.py
│   └── test_orchestrator.py
└── e2e/                     # End-to-end tests (require full system)
    └── (future tests)
```

## Running Tests

### Quick Start

```bash
# Install dependencies (first time only)
make install-dev

# Run all tests
make test

# Run unit tests only (fastest)
make test-unit

# Run integration tests only
make test-integration

# Run with coverage report
make coverage
```

### Advanced Usage

```bash
# Run specific test file
uv run pytest tests/unit/test_workflow_graph.py -v

# Run specific test class
uv run pytest tests/unit/test_workflow_graph.py::TestWorkflowGraph -v

# Run specific test method
uv run pytest tests/unit/test_workflow_graph.py::TestWorkflowGraph::test_add_node -v

# Run tests matching pattern
uv run pytest tests/ -k "workflow" -v

# Run tests in parallel (faster)
make test-parallel

# Run with verbose logging
make test-verbose

# Re-run only failed tests
make test-failed
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests requiring multiple components
- `@pytest.mark.e2e` - End-to-end tests requiring full system
- `@pytest.mark.slow` - Slow running tests (skipped in CI)

### Running by Marker

```bash
# Run only unit tests
pytest -m "unit"

# Run integration tests excluding slow ones
pytest -m "integration and not slow"

# Run all except slow tests
pytest -m "not slow"
```

## Coverage Requirements

The project maintains **70% minimum code coverage**. Coverage reports are:

- **Terminal**: Shown after test run with `make coverage`
- **HTML**: Generated in `htmlcov/index.html`
- **XML**: Generated in `coverage.xml` (for CI)

View coverage report:
```bash
make coverage-open
```

## Fixtures

Common fixtures are defined in `conftest.py`:

### Database Fixtures
- `temp_db_path` - Temporary SQLite database file
- `sqlite_connection` - SQLite connection with test data

### Mock Fixtures
- `mock_genai_client` - Mock Google Generative AI client
- `mock_genai_embed` - Mock embedding generation
- `mock_a2a_client` - Mock A2A client for agent communication
- `mock_httpx_client` - Mock async HTTP client

### Data Fixtures
- `sample_agent_card` - Sample agent card object
- `sample_agent_card_dict` - Sample agent card dictionary
- `sample_task_list` - Sample planner task list
- `agent_cards_dataframe` - DataFrame with agent cards and embeddings

### Configuration Fixtures
- `mock_mcp_server_config` - Mock MCP server configuration
- `temp_agent_cards_dir` - Temporary agent cards directory

## Writing Tests

### Unit Test Example

```python
import pytest
from a2a_mcp.common.workflow import WorkflowGraph, WorkflowNode

@pytest.mark.unit
class TestMyFeature:
    """Test my feature."""

    def test_basic_functionality(self):
        """Test basic functionality works."""
        graph = WorkflowGraph()
        node = WorkflowNode(task="Test task")
        graph.add_node(node)

        assert node.id in graph.nodes

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality."""
        result = await some_async_function()
        assert result is not None
```

### Integration Test Example

```python
import pytest
from unittest.mock import patch

@pytest.mark.integration
class TestIntegration:
    """Test component integration."""

    @pytest.mark.asyncio
    async def test_mcp_integration(self, mock_mcp_server_config):
        """Test MCP server integration."""
        with patch('module.get_config', return_value=mock_mcp_server_config):
            result = await call_mcp_server()
            assert result is not None
```

## Continuous Integration

Tests run automatically on:

- **Push** to `main`, `develop`, or `claude/**` branches
- **Pull requests** to `main` or `develop`

### GitHub Actions Workflows

1. **tests.yml** - Main test workflow
   - Runs on Python 3.11 and 3.12
   - Unit and integration tests
   - Uploads coverage to Codecov

2. **coverage.yml** - Coverage reporting
   - Generates coverage reports
   - Posts coverage comments on PRs
   - Uploads to Codecov

### Required Secrets

Configure in GitHub repository settings:

- `GOOGLE_API_KEY_TEST` - Test API key for Google services
- `CODECOV_TOKEN` - Token for Codecov integration

## Development Workflow

1. **Write tests first** (TDD approach recommended)
2. **Run tests locally** before committing
3. **Check coverage** - aim for 70%+ on new code
4. **Fix linting** issues before pushing
5. **Ensure CI passes** before merging

```bash
# Full pre-commit check
make check

# Or run individual checks
make lint
make format
make type-check
make test
```

## Debugging Tests

### Enable Logging

```bash
# Show all log output
pytest -v -s --log-cli-level=DEBUG

# Show only INFO and above
pytest -v -s --log-cli-level=INFO
```

### Use Debugger

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # ... test code
```

### Verbose Assertion Output

```bash
# Show detailed assertion information
pytest -vv
```

## Best Practices

1. **Keep tests isolated** - Each test should be independent
2. **Use fixtures** - Reuse test setup via fixtures
3. **Mock external dependencies** - Don't call real APIs in tests
4. **Test edge cases** - Empty inputs, errors, boundaries
5. **Use descriptive names** - Test names should explain what they test
6. **One assertion per test** - Makes failures easier to diagnose
7. **Fast tests** - Unit tests should run in milliseconds
8. **Clean up** - Use fixtures to ensure cleanup happens

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check environment variables
- Verify Python version matches CI
- Check for timing/race conditions

### Coverage Below Threshold

```bash
# See which lines are missing coverage
make coverage

# Open HTML report to see details
make coverage-open
```

### Import Errors

```bash
# Ensure dependencies are installed
make install-dev

# Check PYTHONPATH is set correctly
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Database Tests Fail

```bash
# Reinitialize test database
make init-db
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [Coverage.py](https://coverage.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
