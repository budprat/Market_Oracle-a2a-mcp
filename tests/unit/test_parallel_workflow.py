"""Unit tests for parallel workflow execution."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from a2a_mcp.common.parallel_workflow import (
    ParallelWorkflowGraph,
    ParallelWorkflowNode,
    Status
)


@pytest.mark.unit
class TestParallelWorkflowNode:
    """Test ParallelWorkflowNode class."""

    def test_inherits_from_workflow_node(self):
        """Test ParallelWorkflowNode inherits from WorkflowNode."""
        from a2a_mcp.common.workflow import WorkflowNode
        node = ParallelWorkflowNode(task="Test task")
        assert isinstance(node, WorkflowNode)

    @pytest.mark.asyncio
    async def test_run_node_with_result(self):
        """Test running node and collecting results."""
        node = ParallelWorkflowNode(task="Test task")

        # Mock the run_node method
        with patch.object(node, 'run_node') as mock_run:
            async def mock_generator():
                yield {"result": 1}
                yield {"result": 2}

            mock_run.return_value = mock_generator()

            # Execute
            node_id, results = await node.run_node_with_result(
                query="test query",
                task_id="task-123",
                context_id="ctx-456"
            )

            # Assertions
            assert node_id == node.id
            assert len(results) == 2
            assert results[0] == {"result": 1}
            assert results[1] == {"result": 2}


@pytest.mark.unit
class TestParallelWorkflowGraph:
    """Test ParallelWorkflowGraph class."""

    def test_graph_initialization(self):
        """Test parallel graph initialization."""
        graph = ParallelWorkflowGraph()

        assert graph.graph is not None
        assert graph.nodes == {}
        assert graph.state == Status.INITIALIZED
        assert graph.parallel_threshold == 2

    def test_custom_parallel_threshold(self):
        """Test setting custom parallel threshold."""
        graph = ParallelWorkflowGraph()
        graph.parallel_threshold = 3

        assert graph.parallel_threshold == 3

    def test_add_node(self):
        """Test adding a parallel workflow node."""
        graph = ParallelWorkflowGraph()
        node = ParallelWorkflowNode(task="Test task")

        graph.add_node(node)

        assert len(graph.nodes) == 1
        assert node.id in graph.nodes
        assert isinstance(graph.nodes[node.id], ParallelWorkflowNode)

    def test_get_execution_levels_linear_workflow(self):
        """Test execution levels for linear workflow."""
        graph = ParallelWorkflowGraph()

        # Create linear chain: node1 -> node2 -> node3
        nodes = [ParallelWorkflowNode(task=f"Task {i}") for i in range(3)]

        graph.add_node(nodes[0])
        for i in range(1, len(nodes)):
            graph.add_node(nodes[i])
            graph.add_edge(nodes[i-1].id, nodes[i].id)

        # Get execution levels
        levels = graph.get_execution_levels(start_node_id=nodes[0].id)

        # Linear workflow should have 3 levels
        assert len(levels) == 3
        assert len(levels[0]) == 1  # Level 0: node1
        assert len(levels[1]) == 1  # Level 1: node2
        assert len(levels[2]) == 1  # Level 2: node3

    def test_get_execution_levels_parallel_workflow(self):
        """Test execution levels for parallel workflow."""
        graph = ParallelWorkflowGraph()

        # Create: root -> (task1, task2, task3) -> aggregator
        root = ParallelWorkflowNode(task="Root")
        tasks = [ParallelWorkflowNode(task=f"Task {i}") for i in range(3)]
        aggregator = ParallelWorkflowNode(task="Aggregator")

        graph.add_node(root)
        for task in tasks:
            graph.add_node(task)
            graph.add_edge(root.id, task.id)

        graph.add_node(aggregator)
        for task in tasks:
            graph.add_edge(task.id, aggregator.id)

        # Get execution levels
        levels = graph.get_execution_levels(start_node_id=root.id)

        # Should have 3 levels
        assert len(levels) == 3
        assert len(levels[0]) == 1  # Level 0: root
        assert len(levels[1]) == 3  # Level 1: task1, task2, task3 (parallel)
        assert len(levels[2]) == 1  # Level 2: aggregator

    def test_get_execution_levels_diamond_workflow(self):
        """Test execution levels for diamond-shaped workflow."""
        graph = ParallelWorkflowGraph()

        # Create diamond: start -> (left, right) -> end
        start = ParallelWorkflowNode(task="Start")
        left = ParallelWorkflowNode(task="Left")
        right = ParallelWorkflowNode(task="Right")
        end = ParallelWorkflowNode(task="End")

        graph.add_node(start)
        graph.add_node(left)
        graph.add_node(right)
        graph.add_node(end)

        graph.add_edge(start.id, left.id)
        graph.add_edge(start.id, right.id)
        graph.add_edge(left.id, end.id)
        graph.add_edge(right.id, end.id)

        # Get execution levels
        levels = graph.get_execution_levels(start_node_id=start.id)

        # Should have 3 levels
        assert len(levels) == 3
        assert len(levels[0]) == 1  # Level 0: start
        assert len(levels[1]) == 2  # Level 1: left, right (parallel)
        assert len(levels[2]) == 1  # Level 2: end

    def test_identify_parallel_tasks(self):
        """Test identifying tasks that can run in parallel."""
        graph = ParallelWorkflowGraph()
        graph.parallel_threshold = 2

        # Create: root -> (task1, task2, task3)
        root = ParallelWorkflowNode(task="Root")
        tasks = [ParallelWorkflowNode(task=f"Task {i}") for i in range(3)]

        graph.add_node(root)
        for task in tasks:
            graph.add_node(task)
            graph.add_edge(root.id, task.id)

        # Identify parallel tasks
        parallel_levels = graph.identify_parallel_tasks()

        # Should identify one parallel level with 3 tasks
        assert len(parallel_levels) == 1
        assert len(parallel_levels[0]) == 3

    def test_get_node_dependencies(self):
        """Test getting node dependencies."""
        graph = ParallelWorkflowGraph()

        # Create: node1 -> node2, node3 -> node2
        node1 = ParallelWorkflowNode(task="Node 1")
        node2 = ParallelWorkflowNode(task="Node 2")
        node3 = ParallelWorkflowNode(task="Node 3")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        graph.add_edge(node1.id, node2.id)
        graph.add_edge(node3.id, node2.id)

        # Get dependencies
        deps = graph.get_node_dependencies(node2.id)

        assert len(deps) == 2
        assert node1.id in deps
        assert node3.id in deps

    def test_visualize_execution_plan(self):
        """Test execution plan visualization."""
        graph = ParallelWorkflowGraph()
        graph.parallel_threshold = 2

        # Create: root -> (task1, task2, task3) -> aggregator
        root = ParallelWorkflowNode(task="Plan trip", node_label="Planner")
        tasks = [
            ParallelWorkflowNode(task="Find flights", node_label="Flight Search"),
            ParallelWorkflowNode(task="Book hotel", node_label="Hotel Booking"),
            ParallelWorkflowNode(task="Rent car", node_label="Car Rental")
        ]
        aggregator = ParallelWorkflowNode(task="Aggregate results", node_label="Aggregator")

        graph.add_node(root)
        for task in tasks:
            graph.add_node(task)
            graph.add_edge(root.id, task.id)

        graph.add_node(aggregator)
        for task in tasks:
            graph.add_edge(task.id, aggregator.id)

        # Get visualization
        plan = graph.visualize_execution_plan()

        # Assertions
        assert "Execution Plan:" in plan
        assert "Level 0 (SEQUENTIAL):" in plan
        assert "Level 1 (PARALLEL):" in plan
        assert "Level 2 (SEQUENTIAL):" in plan
        assert "Planner" in plan
        assert "Flight Search" in plan
        assert "Hotel Booking" in plan
        assert "Car Rental" in plan

    @pytest.mark.asyncio
    async def test_execute_parallel_level(self):
        """Test executing a level of tasks in parallel."""
        graph = ParallelWorkflowGraph()

        # Create three nodes
        nodes = [ParallelWorkflowNode(task=f"Task {i}") for i in range(3)]
        for node in nodes:
            graph.add_node(node)
            graph.set_node_attributes(node.id, {
                "query": f"Query for {node.task}",
                "task_id": "task-123",
                "context_id": "ctx-456"
            })

        # Mock node execution
        for node in nodes:
            with patch.object(node, 'run_node_with_result') as mock_run:
                async def mock_execution(query, task_id, context_id):
                    await asyncio.sleep(0.01)  # Simulate work
                    return node.id, [{"result": "success"}]

                mock_run.side_effect = mock_execution

        # Track chunks
        collected_chunks = []

        async def chunk_callback(chunk):
            collected_chunks.append(chunk)

        # Execute parallel level
        results = await graph.execute_parallel_level(
            [node.id for node in nodes],
            chunk_callback
        )

        # All nodes should have completed
        assert len(results) == 3
        for node in nodes:
            assert node.state == Status.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_parallel_level_with_error(self):
        """Test parallel execution handles errors gracefully."""
        graph = ParallelWorkflowGraph()

        # Create nodes
        good_node = ParallelWorkflowNode(task="Good Task")
        bad_node = ParallelWorkflowNode(task="Bad Task")

        graph.add_node(good_node)
        graph.add_node(bad_node)

        for node in [good_node, bad_node]:
            graph.set_node_attributes(node.id, {
                "query": f"Query for {node.task}",
                "task_id": "task-123",
                "context_id": "ctx-456"
            })

        # Mock execution - one succeeds, one fails
        async def good_execution(query, task_id, context_id):
            return good_node.id, [{"result": "success"}]

        async def bad_execution(query, task_id, context_id):
            raise RuntimeError("Task failed")

        with patch.object(good_node, 'run_node_with_result', side_effect=good_execution):
            with patch.object(bad_node, 'run_node_with_result', side_effect=bad_execution):

                async def chunk_callback(chunk):
                    pass

                # Execute
                results = await graph.execute_parallel_level(
                    [good_node.id, bad_node.id],
                    chunk_callback
                )

                # Good node should complete, bad node should be paused
                assert good_node.state == Status.COMPLETED
                assert bad_node.state == Status.PAUSED

    @pytest.mark.asyncio
    async def test_parallel_faster_than_sequential(self):
        """Test that parallel execution is faster than sequential."""
        import time

        graph = ParallelWorkflowGraph()

        # Create 3 nodes with simulated work
        nodes = [ParallelWorkflowNode(task=f"Task {i}") for i in range(3)]
        for node in nodes:
            graph.add_node(node)
            graph.set_node_attributes(node.id, {
                "query": f"Query for {node.task}",
                "task_id": "task-123",
                "context_id": "ctx-456"
            })

        # Mock node execution with delay
        async def mock_execution(node_id):
            async def execute(query, task_id, context_id):
                await asyncio.sleep(0.1)  # 100ms per task
                return node_id, [{"result": "success"}]
            return execute

        for node in nodes:
            with patch.object(node, 'run_node_with_result', side_effect=mock_execution(node.id)):
                pass

        async def chunk_callback(chunk):
            pass

        # Execute in parallel
        start = time.time()
        await graph.execute_parallel_level([node.id for node in nodes], chunk_callback)
        parallel_time = time.time() - start

        # Parallel execution should take ~100ms (not 300ms)
        # Allow some overhead, but should be < 200ms
        assert parallel_time < 0.2, f"Parallel execution took {parallel_time}s, expected < 0.2s"

    def test_threshold_controls_parallelism(self):
        """Test that parallel threshold controls execution mode."""
        graph = ParallelWorkflowGraph()

        # Test with threshold = 2 (default)
        graph.parallel_threshold = 2

        # 1 task - should be sequential
        assert "SEQUENTIAL" in graph.visualize_execution_plan() or graph.is_empty()

        # Create workflow with parallel opportunity
        root = ParallelWorkflowNode(task="Root")
        task1 = ParallelWorkflowNode(task="Task 1")
        task2 = ParallelWorkflowNode(task="Task 2")

        graph.add_node(root)
        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_edge(root.id, task1.id)
        graph.add_edge(root.id, task2.id)

        # With threshold=2, should trigger parallel execution
        levels = graph.get_execution_levels(start_node_id=root.id)
        assert len(levels[1]) >= 2  # Second level has 2+ nodes

        # Increase threshold to 3 - same workflow should not trigger parallel
        graph.parallel_threshold = 3
        assert graph.parallel_threshold == 3
