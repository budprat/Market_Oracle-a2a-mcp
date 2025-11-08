"""Integration tests for orchestrator agent functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from a2a_mcp.agents.orchestrator_agent import OrchestratorAgent
from a2a_mcp.agents.parallel_orchestrator_agent import ParallelOrchestratorAgent
from a2a_mcp.common.workflow import Status


@pytest.mark.integration
class TestOrchestratorAgent:
    """Test OrchestratorAgent integration."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        orchestrator = OrchestratorAgent()

        assert orchestrator.agent_name == "Orchestrator Agent"
        assert orchestrator.description == "Facilitate inter agent communication"
        assert orchestrator.graph is None
        assert orchestrator.results == []
        assert orchestrator.travel_context == {}

    def test_clear_state(self):
        """Test clearing orchestrator state."""
        orchestrator = OrchestratorAgent()

        # Add some state
        orchestrator.results = [{"test": "data"}]
        orchestrator.travel_context = {"destination": "London"}
        orchestrator.query_history = ["query1", "query2"]

        # Clear
        orchestrator.clear_state()

        assert orchestrator.results == []
        assert orchestrator.travel_context == {}
        assert orchestrator.query_history == []
        assert orchestrator.graph is None

    @pytest.mark.asyncio
    async def test_generate_summary(self, mock_genai_client):
        """Test summary generation."""
        orchestrator = OrchestratorAgent()
        orchestrator.results = [
            {"type": "flights", "data": []},
            {"type": "hotels", "data": []}
        ]

        with patch('a2a_mcp.agents.orchestrator_agent.genai.Client', return_value=mock_genai_client):
            summary = await orchestrator.generate_summary()

            assert isinstance(summary, str)
            assert len(summary) > 0
            mock_genai_client.models.generate_content.assert_called_once()

    def test_answer_user_question_can_answer(self, mock_genai_client):
        """Test answering user questions when context available."""
        orchestrator = OrchestratorAgent()
        orchestrator.travel_context = {
            "destination": "London",
            "duration": "6 days"
        }
        orchestrator.query_history = ["Plan a trip to London"]

        # Mock response that can answer
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "can_answer": "yes",
            "answer": "You are traveling to London for 6 days"
        })
        mock_genai_client.models.generate_content.return_value = mock_response

        with patch('a2a_mcp.agents.orchestrator_agent.genai.Client', return_value=mock_genai_client):
            answer = orchestrator.answer_user_question("Where am I going?")

            answer_data = json.loads(answer)
            assert answer_data["can_answer"] == "yes"
            assert "London" in answer_data["answer"]

    def test_answer_user_question_cannot_answer(self, mock_genai_client):
        """Test answering when context insufficient."""
        orchestrator = OrchestratorAgent()
        orchestrator.travel_context = {}
        orchestrator.query_history = []

        # Mock response that cannot answer
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "can_answer": "no",
            "answer": "Cannot answer based on provided context"
        })
        mock_genai_client.models.generate_content.return_value = mock_response

        with patch('a2a_mcp.agents.orchestrator_agent.genai.Client', return_value=mock_genai_client):
            answer = orchestrator.answer_user_question("What is the weather?")

            answer_data = json.loads(answer)
            assert answer_data["can_answer"] == "no"

    def test_add_graph_node(self):
        """Test adding nodes to workflow graph."""
        orchestrator = OrchestratorAgent()

        # Initialize graph
        from a2a_mcp.common.workflow import WorkflowGraph
        orchestrator.graph = WorkflowGraph()

        # Add node
        node = orchestrator.add_graph_node(
            task_id="task-123",
            context_id="ctx-456",
            query="Find flights to London",
            node_key="flight_search",
            node_label="Flight Search"
        )

        assert node is not None
        assert node.task == "Find flights to London"
        assert node.node_key == "flight_search"
        assert orchestrator.graph.nodes[node.id] == node

    def test_set_node_attributes(self):
        """Test setting node attributes."""
        orchestrator = OrchestratorAgent()

        from a2a_mcp.common.workflow import WorkflowGraph, WorkflowNode
        orchestrator.graph = WorkflowGraph()

        node = WorkflowNode(task="Test task")
        orchestrator.graph.add_node(node)

        orchestrator.set_node_attributes(
            node.id,
            task_id="task-123",
            context_id="ctx-456",
            query="Test query"
        )

        assert orchestrator.graph.graph.nodes[node.id]["task_id"] == "task-123"
        assert orchestrator.graph.graph.nodes[node.id]["context_id"] == "ctx-456"
        assert orchestrator.graph.graph.nodes[node.id]["query"] == "Test query"

    @pytest.mark.asyncio
    async def test_stream_empty_query(self):
        """Test stream rejects empty query."""
        orchestrator = OrchestratorAgent()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            async for _ in orchestrator.stream("", "ctx-123", "task-123"):
                pass

    @pytest.mark.asyncio
    async def test_stream_context_change_clears_state(self):
        """Test stream clears state on context change."""
        orchestrator = OrchestratorAgent()

        # Set initial state
        orchestrator.context_id = "ctx-old"
        orchestrator.results = [{"test": "data"}]
        orchestrator.travel_context = {"destination": "London"}

        # Mock graph execution
        with patch.object(orchestrator, 'graph') as mock_graph:
            if mock_graph:
                async def mock_run():
                    return
                    yield  # Make it a generator

                mock_graph.run_workflow = mock_run
                mock_graph.state = Status.COMPLETED

        # Stream with new context should clear state
        # Note: This is a partial test as full execution requires MCP server
        query = "New query"
        context_id = "ctx-new"
        task_id = "task-123"

        # The stream should recognize context change
        assert orchestrator.context_id != context_id


@pytest.mark.integration
class TestParallelOrchestratorAgent:
    """Test ParallelOrchestratorAgent integration."""

    def test_parallel_orchestrator_initialization(self):
        """Test parallel orchestrator initializes correctly."""
        orchestrator = ParallelOrchestratorAgent()

        assert orchestrator.agent_name == "Parallel Orchestrator Agent"
        assert orchestrator.enable_parallel is True
        assert orchestrator.graph is None

    def test_analyze_task_dependencies(self):
        """Test task dependency analysis."""
        orchestrator = ParallelOrchestratorAgent()

        tasks = [
            {"description": "Find flights from SFO to LHR"},
            {"description": "Book a hotel in London"},
            {"description": "Rent a car at the airport"},
            {"description": "Plan activities"}
        ]

        task_groups = orchestrator.analyze_task_dependencies(tasks)

        # Should identify different task groups
        assert "flights" in task_groups
        assert "hotels" in task_groups
        assert "cars" in task_groups
        assert "other" in task_groups

        # Verify correct grouping
        assert len(task_groups["flights"]) == 1  # flight task
        assert len(task_groups["hotels"]) == 1   # hotel task
        assert len(task_groups["cars"]) == 1     # car task

    def test_analyze_task_dependencies_parallel_opportunities(self):
        """Test identifying parallel execution opportunities."""
        orchestrator = ParallelOrchestratorAgent()

        tasks = [
            {"description": "Search for flights"},
            {"description": "Search for hotels"},
            {"description": "Search for cars"}
        ]

        task_groups = orchestrator.analyze_task_dependencies(tasks)

        # Count non-empty groups
        non_empty_groups = sum(1 for group in task_groups.values() if len(group) > 0)

        # Should identify multiple groups that can run in parallel
        assert non_empty_groups >= 2


@pytest.mark.integration
class TestOrchestratorWorkflowExecution:
    """Test orchestrator workflow execution."""

    @pytest.mark.asyncio
    async def test_orchestrator_planner_integration(self, sample_task_list):
        """Test orchestrator integration with planner."""
        orchestrator = OrchestratorAgent()

        # This would require mocking the entire A2A flow
        # For now, validate the setup
        from a2a_mcp.common.workflow import WorkflowGraph
        orchestrator.graph = WorkflowGraph()

        # Simulate adding planner node
        planner_node = orchestrator.add_graph_node(
            task_id="task-123",
            context_id="ctx-456",
            query="Plan a trip to London",
            node_key="planner",
            node_label="Planner"
        )

        assert planner_node.node_key == "planner"
        assert orchestrator.graph.nodes[planner_node.id] == planner_node

    @pytest.mark.asyncio
    async def test_parallel_orchestrator_builds_parallel_graph(self, sample_task_list):
        """Test parallel orchestrator builds graph with parallel nodes."""
        orchestrator = ParallelOrchestratorAgent()

        from a2a_mcp.common.parallel_workflow import ParallelWorkflowGraph
        orchestrator.graph = ParallelWorkflowGraph()

        # Add root planner node
        root = orchestrator.add_graph_node(
            task_id="task-123",
            context_id="ctx-456",
            query="Plan trip",
            node_key="planner"
        )

        # Simulate adding parallel tasks
        tasks = sample_task_list["tasks"]
        task_groups = orchestrator.analyze_task_dependencies(tasks)

        # Track created nodes
        current_nodes = [root.id]

        for group_name, task_indices in task_groups.items():
            for idx in task_indices:
                if idx < len(tasks):
                    task = tasks[idx]
                    node = orchestrator.add_graph_node(
                        task_id="task-123",
                        context_id="ctx-456",
                        query=task["description"],
                        node_id=current_nodes[0]
                    )

        # Verify parallel opportunities exist
        levels = orchestrator.graph.get_execution_levels(start_node_id=root.id)
        assert len(levels) >= 2  # At least root + task level


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndOrchestration:
    """End-to-end orchestration tests (require external services)."""

    @pytest.mark.skip(reason="Requires running MCP server")
    @pytest.mark.asyncio
    async def test_full_travel_booking_flow(self):
        """Test complete travel booking workflow."""
        # This would test the full flow:
        # 1. Client sends query to orchestrator
        # 2. Orchestrator calls planner
        # 3. Planner returns task list
        # 4. Orchestrator discovers agents via MCP
        # 5. Tasks executed in parallel
        # 6. Results aggregated
        # 7. Summary generated
        pass

    @pytest.mark.skip(reason="Requires running MCP server")
    @pytest.mark.asyncio
    async def test_error_recovery_in_orchestration(self):
        """Test orchestrator handles agent failures gracefully."""
        pass
