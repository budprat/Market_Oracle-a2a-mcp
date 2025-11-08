"""Unit tests for workflow graph functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from a2a_mcp.common.workflow import Status, WorkflowGraph, WorkflowNode


@pytest.mark.unit
class TestWorkflowNode:
    """Test WorkflowNode class."""

    def test_node_initialization(self):
        """Test node is initialized with correct properties."""
        task = "Find flights to London"
        node = WorkflowNode(task=task, node_key="flight_search", node_label="Flight Search")

        assert node.task == task
        assert node.node_key == "flight_search"
        assert node.node_label == "Flight Search"
        assert node.state == Status.READY
        assert node.results is None
        assert node.id is not None

    def test_node_unique_ids(self):
        """Test that each node gets a unique ID."""
        node1 = WorkflowNode(task="Task 1")
        node2 = WorkflowNode(task="Task 2")

        assert node1.id != node2.id

    @pytest.mark.asyncio
    async def test_get_planner_resource(self, mock_mcp_server_config, sample_agent_card_dict):
        """Test retrieving planner agent resource."""
        node = WorkflowNode(task="Plan trip", node_key="planner")

        with patch('a2a_mcp.common.workflow.get_mcp_server_config', return_value=mock_mcp_server_config):
            with patch('a2a_mcp.common.workflow.client.init_session') as mock_session:
                # Mock MCP client response
                mock_mcp_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.contents = [
                    MagicMock(text=f'{{"agent_card": [{sample_agent_card_dict}]}}')
                ]
                mock_mcp_client.find_resource = AsyncMock(return_value=mock_response)

                mock_session.return_value.__aenter__.return_value = mock_mcp_client

                # Execute
                agent_card = await node.get_planner_resource()

                # Assertions
                assert agent_card is not None
                assert agent_card.name == sample_agent_card_dict["name"]
                assert agent_card.url == sample_agent_card_dict["url"]

    @pytest.mark.asyncio
    async def test_find_agent_for_task(self, mock_mcp_server_config, sample_agent_card_dict):
        """Test finding an agent for a specific task."""
        node = WorkflowNode(task="Book a flight to London")

        with patch('a2a_mcp.common.workflow.get_mcp_server_config', return_value=mock_mcp_server_config):
            with patch('a2a_mcp.common.workflow.client.init_session') as mock_session:
                # Mock MCP client response
                mock_mcp_client = AsyncMock()
                mock_result = MagicMock()
                mock_result.content = [
                    MagicMock(text=f'{sample_agent_card_dict}')
                ]
                mock_mcp_client.find_agent = AsyncMock(return_value=mock_result)

                mock_session.return_value.__aenter__.return_value = mock_mcp_client

                # Execute
                agent_card = await node.find_agent_for_task()

                # Assertions
                assert agent_card is not None
                mock_mcp_client.find_agent.assert_called_once()


@pytest.mark.unit
class TestWorkflowGraph:
    """Test WorkflowGraph class."""

    def test_graph_initialization(self):
        """Test graph is initialized correctly."""
        graph = WorkflowGraph()

        assert graph.graph is not None
        assert graph.nodes == {}
        assert graph.latest_node is None
        assert graph.state == Status.INITIALIZED
        assert graph.paused_node_id is None

    def test_add_single_node(self):
        """Test adding a single node to the graph."""
        graph = WorkflowGraph()
        node = WorkflowNode(task="Test task")

        graph.add_node(node)

        assert len(graph.nodes) == 1
        assert node.id in graph.nodes
        assert graph.latest_node == node.id
        assert graph.graph.has_node(node.id)

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes to the graph."""
        graph = WorkflowGraph()
        node1 = WorkflowNode(task="Task 1")
        node2 = WorkflowNode(task="Task 2")
        node3 = WorkflowNode(task="Task 3")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        assert len(graph.nodes) == 3
        assert graph.latest_node == node3.id

    def test_add_edge(self):
        """Test adding edges between nodes."""
        graph = WorkflowGraph()
        node1 = WorkflowNode(task="Task 1")
        node2 = WorkflowNode(task="Task 2")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(node1.id, node2.id)

        assert graph.graph.has_edge(node1.id, node2.id)
        assert list(graph.graph.successors(node1.id)) == [node2.id]
        assert list(graph.graph.predecessors(node2.id)) == [node1.id]

    def test_add_edge_invalid_nodes(self):
        """Test adding edge with invalid node IDs raises error."""
        graph = WorkflowGraph()
        node1 = WorkflowNode(task="Task 1")
        graph.add_node(node1)

        with pytest.raises(ValueError, match="Invalid node IDs"):
            graph.add_edge(node1.id, "invalid_node_id")

        with pytest.raises(ValueError, match="Invalid node IDs"):
            graph.add_edge("invalid_node_id", node1.id)

    def test_set_node_attribute(self):
        """Test setting individual node attribute."""
        graph = WorkflowGraph()
        node = WorkflowNode(task="Test task")
        graph.add_node(node)

        graph.set_node_attribute(node.id, "test_attr", "test_value")

        assert graph.graph.nodes[node.id]["test_attr"] == "test_value"

    def test_set_node_attributes(self):
        """Test setting multiple node attributes."""
        graph = WorkflowGraph()
        node = WorkflowNode(task="Test task")
        graph.add_node(node)

        attributes = {
            "task_id": "task-123",
            "context_id": "ctx-456",
            "query": "Find flights"
        }
        graph.set_node_attributes(node.id, attributes)

        for key, value in attributes.items():
            assert graph.graph.nodes[node.id][key] == value

    def test_is_empty(self):
        """Test checking if graph is empty."""
        graph = WorkflowGraph()
        assert graph.is_empty() is True

        node = WorkflowNode(task="Task 1")
        graph.add_node(node)
        assert graph.is_empty() is False

    def test_linear_workflow_topology(self):
        """Test linear workflow creates correct topology."""
        graph = WorkflowGraph()
        nodes = [WorkflowNode(task=f"Task {i}") for i in range(3)]

        # Add nodes in linear chain
        graph.add_node(nodes[0])
        for i in range(1, len(nodes)):
            graph.add_node(nodes[i])
            graph.add_edge(nodes[i-1].id, nodes[i].id)

        # Verify topology
        assert graph.graph.number_of_nodes() == 3
        assert graph.graph.number_of_edges() == 2

        # Check in-degree (number of incoming edges)
        assert graph.graph.in_degree(nodes[0].id) == 0  # Start node
        assert graph.graph.in_degree(nodes[1].id) == 1
        assert graph.graph.in_degree(nodes[2].id) == 1

    def test_parallel_workflow_topology(self):
        """Test parallel workflow creates correct topology."""
        graph = WorkflowGraph()

        # Create: root -> (task1, task2, task3)
        root = WorkflowNode(task="Root")
        tasks = [WorkflowNode(task=f"Task {i}") for i in range(3)]

        graph.add_node(root)
        for task in tasks:
            graph.add_node(task)
            graph.add_edge(root.id, task.id)

        # Verify topology
        assert graph.graph.number_of_nodes() == 4
        assert graph.graph.number_of_edges() == 3

        # All tasks should have root as predecessor
        for task in tasks:
            assert list(graph.graph.predecessors(task.id)) == [root.id]

        # Root should have all tasks as successors
        successors = list(graph.graph.successors(root.id))
        assert len(successors) == 3

    @pytest.mark.asyncio
    async def test_run_workflow_empty_graph(self):
        """Test running workflow on empty graph."""
        graph = WorkflowGraph()

        results = []
        async for chunk in graph.run_workflow():
            results.append(chunk)

        # Empty graph should not yield any results
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, mock_a2a_client):
        """Test workflow state transitions during execution."""
        graph = WorkflowGraph()
        node = WorkflowNode(task="Test task")
        graph.add_node(node)
        graph.set_node_attributes(node.id, {
            "query": "test query",
            "task_id": "task-123",
            "context_id": "ctx-456"
        })

        # Mock node execution
        with patch.object(node, 'run_node') as mock_run:
            async def mock_generator():
                from a2a.types import SendStreamingMessageSuccessResponse, TaskStatusUpdateEvent, TaskState

                # Simulate completed task
                status_event = MagicMock(spec=TaskStatusUpdateEvent)
                status_event.status.state = TaskState.completed
                status_event.contextId = "ctx-456"

                response = MagicMock(spec=SendStreamingMessageSuccessResponse)
                response.result = status_event

                yield MagicMock(root=response)

            mock_run.return_value = mock_generator()

            # Execute
            assert graph.state == Status.INITIALIZED

            results = []
            async for chunk in graph.run_workflow(start_node_id=node.id):
                results.append(chunk)
                if graph.state == Status.RUNNING:
                    pass  # State check during execution

            # Final state should be COMPLETED
            assert graph.state == Status.COMPLETED
            assert node.state == Status.COMPLETED
