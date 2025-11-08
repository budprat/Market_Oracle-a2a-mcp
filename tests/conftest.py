"""Pytest configuration and fixtures for A2A-MCP tests."""

import asyncio
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock

import httpx
import pandas as pd
import pytest
from a2a.types import AgentCard

# Set test environment variables
os.environ['GOOGLE_API_KEY'] = 'test_api_key_12345'
os.environ['GEMINI_MODEL'] = 'gemini-2.0-flash-001'


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sqlite_connection(temp_db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Create a SQLite connection with test data."""
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Create flights table
    cursor.execute('''
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carrier TEXT NOT NULL,
            flight_number INTEGER NOT NULL,
            from_airport TEXT NOT NULL,
            to_airport TEXT NOT NULL,
            ticket_class TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    # Insert test data
    cursor.executemany(
        'INSERT INTO flights (carrier, flight_number, from_airport, to_airport, ticket_class, price) VALUES (?, ?, ?, ?, ?, ?)',
        [
            ('United Airlines', 101, 'SFO', 'LHR', 'ECONOMY', 850.00),
            ('British Airways', 201, 'SFO', 'LHR', 'BUSINESS', 3200.00),
            ('Virgin Atlantic', 301, 'SFO', 'LHR', 'ECONOMY', 880.00),
        ]
    )

    # Create hotels table
    cursor.execute('''
        CREATE TABLE hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            hotel_type TEXT NOT NULL,
            room_type TEXT NOT NULL,
            price_per_night REAL NOT NULL
        )
    ''')

    cursor.executemany(
        'INSERT INTO hotels (name, city, hotel_type, room_type, price_per_night) VALUES (?, ?, ?, ?, ?)',
        [
            ('The Savoy', 'London', 'HOTEL', 'SUITE', 650.00),
            ('Premier Inn', 'London', 'HOTEL', 'STANDARD', 120.00),
        ]
    )

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def sample_agent_card() -> AgentCard:
    """Create a sample agent card for testing."""
    return AgentCard(
        name="Test Agent",
        url="http://localhost:10999/",
        description="A test agent for unit testing",
        capabilities=[],
    )


@pytest.fixture
def sample_agent_card_dict() -> dict:
    """Create a sample agent card dictionary."""
    return {
        "name": "Air Ticketing Agent",
        "url": "http://localhost:10103/",
        "description": "Handles flight bookings and air travel",
        "capabilities": [
            {
                "name": "search_flights",
                "description": "Search for available flights",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    }
                }
            }
        ]
    }


@pytest.fixture
def mock_mcp_server_config():
    """Mock MCP server configuration."""
    config = MagicMock()
    config.host = "localhost"
    config.port = 10100
    config.transport = "sse"
    return config


@pytest.fixture
def sample_task_list() -> dict:
    """Sample task list from planner agent."""
    return {
        "trip_info": {
            "destination": "London",
            "origin": "San Francisco",
            "duration": "6 days"
        },
        "tasks": [
            {"description": "Find flights from SFO to LHR"},
            {"description": "Book hotel in London"},
            {"description": "Rent a car in London"}
        ]
    }


@pytest.fixture
def agent_cards_dataframe() -> pd.DataFrame:
    """Create a DataFrame with sample agent cards and embeddings."""
    agent_cards = [
        {
            "name": "Air Ticketing Agent",
            "url": "http://localhost:10103/",
            "description": "Handles flight bookings"
        },
        {
            "name": "Hotel Booking Agent",
            "url": "http://localhost:10104/",
            "description": "Handles hotel reservations"
        },
        {
            "name": "Car Rental Agent",
            "url": "http://localhost:10105/",
            "description": "Handles car rental bookings"
        }
    ]

    # Create fake embeddings (768-dimensional vectors)
    import numpy as np
    embeddings = [np.random.rand(768).tolist() for _ in range(3)]

    df = pd.DataFrame({
        'card_uri': [
            'resource://agent_cards/air_ticketing_agent',
            'resource://agent_cards/hotel_booking_agent',
            'resource://agent_cards/car_rental_agent'
        ],
        'agent_card': agent_cards,
        'card_embeddings': embeddings
    })

    return df


@pytest.fixture
async def mock_httpx_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create a mock async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def mock_genai_client():
    """Mock Google Generative AI client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a test summary of the travel data."
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_genai_embed():
    """Mock embedding generation."""
    def mock_embed(model, content, task_type):
        import numpy as np
        return {'embedding': np.random.rand(768).tolist()}
    return mock_embed


@pytest.fixture
def temp_agent_cards_dir() -> Generator[Path, None, None]:
    """Create temporary agent cards directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cards_dir = Path(tmpdir) / 'agent_cards'
        cards_dir.mkdir()

        # Create sample agent card files
        cards = [
            {
                "name": "Air Ticketing Agent",
                "url": "http://localhost:10103/",
                "description": "Handles flight bookings",
                "capabilities": []
            },
            {
                "name": "Hotel Booking Agent",
                "url": "http://localhost:10104/",
                "description": "Handles hotel reservations",
                "capabilities": []
            }
        ]

        for i, card in enumerate(cards):
            card_file = cards_dir / f'test_agent_{i}.json'
            with open(card_file, 'w') as f:
                json.dump(card, f)

        yield cards_dir


@pytest.fixture
def mock_a2a_client():
    """Mock A2A client for testing."""
    mock_client = AsyncMock()

    # Mock streaming response
    async def mock_stream():
        from a2a.types import (
            SendStreamingMessageSuccessResponse,
            TaskArtifactUpdateEvent,
            TaskStatusUpdateEvent,
            TaskState
        )

        # Simulate status update
        status_event = MagicMock(spec=TaskStatusUpdateEvent)
        status_event.status.state = TaskState.completed
        status_event.contextId = "test-context"

        status_response = MagicMock(spec=SendStreamingMessageSuccessResponse)
        status_response.result = status_event

        yield MagicMock(root=status_response)

        # Simulate artifact update
        artifact = MagicMock()
        artifact.name = "TestAgent-result"
        artifact.parts = [MagicMock(root=MagicMock(data={"results": ["test"]}))]

        artifact_event = MagicMock(spec=TaskArtifactUpdateEvent)
        artifact_event.artifact = artifact

        artifact_response = MagicMock(spec=SendStreamingMessageSuccessResponse)
        artifact_response.result = artifact_event

        yield MagicMock(root=artifact_response)

    mock_client.send_message_streaming = Mock(return_value=mock_stream())
    return mock_client


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
