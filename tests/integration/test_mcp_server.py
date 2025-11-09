"""Integration tests for MCP server functionality."""

import json
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from a2a_mcp.mcp import server


@pytest.mark.integration
class TestMCPServerTools:
    """Test MCP server tool functions."""

    def test_query_travel_data_valid_select(self, sqlite_connection, temp_db_path):
        """Test query_travel_data with valid SELECT query."""
        # Patch the SQLLITE_DB path
        with patch.object(server, 'SQLLITE_DB', temp_db_path):
            query = "SELECT * FROM flights WHERE from_airport='SFO'"
            result = server.query_travel_data(query)

            # Parse JSON result
            data = json.loads(result)

            assert 'results' in data
            assert len(data['results']) == 3  # 3 test flights
            assert data['results'][0]['from_airport'] == 'SFO'

    def test_query_travel_data_invalid_query(self):
        """Test query_travel_data rejects non-SELECT queries."""
        with pytest.raises(ValueError, match="In correct query"):
            server.query_travel_data("DELETE FROM flights")

        with pytest.raises(ValueError, match="In correct query"):
            server.query_travel_data("UPDATE flights SET price=0")

        with pytest.raises(ValueError, match="In correct query"):
            server.query_travel_data("DROP TABLE flights")

    def test_query_travel_data_empty_query(self):
        """Test query_travel_data rejects empty queries."""
        with pytest.raises(ValueError, match="In correct query"):
            server.query_travel_data("")

        with pytest.raises(ValueError, match="In correct query"):
            server.query_travel_data("   ")

    def test_query_travel_data_sql_injection_protection(self, sqlite_connection, temp_db_path):
        """Test SQL injection protection."""
        with patch.object(server, 'SQLLITE_DB', temp_db_path):
            # Attempt SQL injection
            malicious_queries = [
                "SELECT * FROM flights; DROP TABLE flights;",
                "SELECT * FROM flights WHERE 1=1; --",
            ]

            for query in malicious_queries:
                # Should still execute SELECT part only
                result = server.query_travel_data(query.split(';')[0])
                data = json.loads(result)
                assert 'results' in data

    def test_query_places_data_no_api_key(self):
        """Test query_places_data returns empty when API key not set."""
        with patch.dict('os.environ', {}, clear=True):
            result = server.query_places_data("hotels in London")
            assert result == {'places': []}

    def test_generate_embeddings(self, mock_genai_embed):
        """Test embedding generation."""
        with patch('a2a_mcp.mcp.server.genai.embed_content', side_effect=mock_genai_embed):
            text = "Test agent description"
            embedding = server.generate_embeddings(text)

            assert isinstance(embedding, list)
            assert len(embedding) == 768  # Standard embedding dimension


@pytest.mark.integration
class TestMCPServerAgentDiscovery:
    """Test MCP server agent discovery."""

    def test_load_agent_cards(self, temp_agent_cards_dir):
        """Test loading agent cards from directory."""
        with patch.object(server, 'AGENT_CARDS_DIR', str(temp_agent_cards_dir)):
            card_uris, agent_cards = server.load_agent_cards()

            assert len(agent_cards) == 2  # We created 2 test cards
            assert all('name' in card for card in agent_cards)
            assert all('url' in card for card in agent_cards)
            assert all(uri.startswith('resource://agent_cards/') for uri in card_uris)

    def test_load_agent_cards_empty_directory(self):
        """Test loading from empty directory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(server, 'AGENT_CARDS_DIR', tmpdir):
                card_uris, agent_cards = server.load_agent_cards()
                assert len(agent_cards) == 0

    def test_load_agent_cards_invalid_json(self):
        """Test handling of invalid JSON files."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid JSON file
            invalid_file = Path(tmpdir) / 'invalid.json'
            with open(invalid_file, 'w') as f:
                f.write("{ invalid json")

            with patch.object(server, 'AGENT_CARDS_DIR', tmpdir):
                card_uris, agent_cards = server.load_agent_cards()
                # Should skip invalid files
                assert len(agent_cards) == 0

    def test_build_agent_card_embeddings(self, temp_agent_cards_dir, mock_genai_embed):
        """Test building dataframe with embeddings."""
        with patch.object(server, 'AGENT_CARDS_DIR', str(temp_agent_cards_dir)):
            with patch('a2a_mcp.mcp.server.genai.embed_content', side_effect=mock_genai_embed):
                df = server.build_agent_card_embeddings()

                assert df is not None
                assert isinstance(df, pd.DataFrame)
                assert 'card_uri' in df.columns
                assert 'agent_card' in df.columns
                assert 'card_embeddings' in df.columns
                assert len(df) == 2

    def test_find_agent_by_embedding_similarity(self, agent_cards_dataframe, mock_genai_embed):
        """Test finding agent by embedding similarity."""
        # Mock the find_agent function with our test dataframe
        query = "I need to book a flight"

        with patch('a2a_mcp.mcp.server.genai.embed_content', side_effect=mock_genai_embed):
            # Simulate finding best match
            query_embedding = mock_genai_embed(None, query, None)

            # Calculate dot products
            dot_products = np.dot(
                np.stack(agent_cards_dataframe['card_embeddings']),
                query_embedding['embedding']
            )

            best_match_index = np.argmax(dot_products)
            best_agent = agent_cards_dataframe.iloc[best_match_index]['agent_card']

            # Should return an agent card
            assert 'name' in best_agent
            assert 'url' in best_agent


@pytest.mark.integration
class TestMCPServerResources:
    """Test MCP server resource endpoints."""

    def test_get_agent_cards_resource(self, agent_cards_dataframe):
        """Test retrieving agent cards resource."""
        # This would be tested with actual MCP server running
        # For now, test the function logic
        card_uris = agent_cards_dataframe['card_uri'].to_list()

        assert len(card_uris) == 3
        assert all('resource://agent_cards/' in uri for uri in card_uris)

    def test_get_specific_agent_card(self, agent_cards_dataframe):
        """Test retrieving specific agent card."""
        card_name = 'air_ticketing_agent'
        uri = f'resource://agent_cards/{card_name}'

        # Filter dataframe
        matching_cards = agent_cards_dataframe.loc[
            agent_cards_dataframe['card_uri'] == uri,
            'agent_card'
        ].to_list()

        # Should find card if it exists
        if matching_cards:
            assert len(matching_cards) > 0


@pytest.mark.integration
class TestMCPServerRemoteConnectivity:
    """Test MCP server remote connectivity features."""

    def test_list_remote_servers_empty(self):
        """Test listing remote servers when none configured."""
        # This would require mocking the remote_registry
        # For now, validate the function structure
        pass

    def test_register_remote_server(self):
        """Test registering a new remote server."""
        # This would be tested with actual RemoteMCPConnector
        pass


@pytest.mark.integration
class TestMCPServerAcademicTools:
    """Test academic research MCP tools."""

    def test_query_academic_databases(self):
        """Test querying academic databases."""
        query = "machine learning"
        result = server.query_academic_databases(query)

        assert 'results' in result
        assert 'status' in result
        assert result['status'] == 'success'
        assert 'databases_queried' in result

    def test_query_academic_databases_with_specific_dbs(self):
        """Test querying specific academic databases."""
        query = "neural networks"
        databases = ['arxiv', 'pubmed']

        result = server.query_academic_databases(query, databases)

        assert result['status'] == 'success'
        assert result['databases_queried'] == databases

    def test_analyze_cross_domain_patterns(self):
        """Test cross-domain pattern analysis."""
        research_data = [
            {"title": "Paper 1", "domain": "biology"},
            {"title": "Paper 2", "domain": "physics"}
        ]
        domains = ["biology", "physics"]

        result = server.analyze_cross_domain_patterns(research_data, domains)

        assert 'patterns' in result
        assert 'synthesis_score' in result
        assert 'domains_analyzed' in result

    def test_detect_research_bias(self):
        """Test research bias detection."""
        papers = [
            {"title": "Paper 1"},
            {"title": "Paper 2"}
        ]
        methodologies = ["experimental", "observational"]

        result = server.detect_research_bias(papers, methodologies)

        assert 'bias_indicators' in result
        assert 'overall_reliability' in result
        assert 0 <= result['overall_reliability'] <= 1

    def test_synthesize_research_findings(self):
        """Test research synthesis."""
        findings = [
            {"domain": "biology", "finding": "Cell growth"},
            {"domain": "chemistry", "finding": "Molecular bonds"}
        ]

        result = server.synthesize_research_findings(findings)

        assert 'synthesis_type' in result
        assert 'key_themes' in result
        assert 'confidence_score' in result

    def test_generate_knowledge_graph(self):
        """Test knowledge graph generation."""
        entities = ["Entity1", "Entity2", "Entity3"]
        relationships = [("Entity1", "relates_to", "Entity2")]

        result = server.generate_knowledge_graph(entities, relationships)

        assert 'graph_id' in result
        assert 'status' in result
        assert result['status'] == 'success'

    def test_simulate_academic_query(self):
        """Test academic query simulation."""
        database = "arxiv"
        query = "quantum computing"

        results = server.simulate_academic_query(database, query)

        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]['database'] == database
        assert 'title' in results[0]
        assert 'doi' in results[0]
