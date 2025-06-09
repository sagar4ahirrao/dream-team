import pytest
from fastapi.testclient import TestClient
import pandas as pd
import json
import os
from mcp_analytics_server import app, DATA_DIR
import tempfile
import shutil

# Create a test client
client = TestClient(app)

@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory with test data"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create test data files
    test_data = {
        "sensor.csv": pd.DataFrame({
            "timestamp": pd.date_range(start="2024-01-01", periods=5, freq="H"),
            "sensor_id": ["S1", "S2", "S3", "S1", "S2"],
            "value": [10.5, 20.3, 15.7, 11.2, 21.8],
            "status": ["active", "active", "inactive", "active", "active"]
        }),
        "maintenance.csv": pd.DataFrame({
            "date": pd.date_range(start="2024-01-01", periods=3, freq="D"),
            "equipment_id": ["E1", "E2", "E1"],
            "maintenance_type": ["routine", "repair", "inspection"],
            "cost": [100.0, 250.0, 50.0]
        }),
        "customer_orders.csv": pd.DataFrame({
            "order_id": ["O1", "O2", "O3"],
            "customer_id": ["C1", "C2", "C1"],
            "order_date": pd.date_range(start="2024-01-01", periods=3, freq="D"),
            "amount": [150.0, 200.0, 75.0],
            "status": ["completed", "pending", "completed"]
        })
    }
    
    # Save test data to CSV files
    for filename, df in test_data.items():
        df.to_csv(os.path.join(temp_dir, filename), index=False)
    
    # Store original DATA_DIR
    original_data_dir = DATA_DIR
    
    # Update DATA_DIR for testing
    import mcp_analytics_server
    mcp_analytics_server.DATA_DIR = temp_dir
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)
    mcp_analytics_server.DATA_DIR = original_data_dir

def test_list_tables(test_data_dir):
    """Test the /tables endpoint"""
    response = client.get("/tables")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    assert "sensor" in data["tables"]
    assert "maintenance" in data["tables"]
    assert "customer_orders" in data["tables"]
    
    # Check table descriptions
    assert "description" in data["tables"]["sensor"]
    assert "columns" in data["tables"]["sensor"]
    assert "row_count" in data["tables"]["sensor"]

def test_query_data(test_data_dir):
    """Test the /query endpoint"""
    # Test basic query
    response = client.post("/query", json={
        "table_name": "sensor",
        "limit": 2
    })
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    
    # Test query with filters
    response = client.post("/query", json={
        "table_name": "sensor",
        "filters": {"status": "active"},
        "sort_by": "value"
    })
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "active" for item in data["data"])
    
    # Test query with grouping
    response = client.post("/query", json={
        "table_name": "maintenance",
        "group_by": ["equipment_id"],
        "sort_by": "cost"
    })
    assert response.status_code == 200
    data = response.json()
    assert "data" in data

def test_analyze_data(test_data_dir):
    """Test the /analyze endpoint"""
    # Test trend analysis
    response = client.post("/analyze", json={
        "table_name": "sensor",
        "analysis_type": "trend",
        "parameters": {
            "time_column": "timestamp",
            "value_column": "value"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "trend_analysis" in data
    
    # Test correlation analysis
    response = client.post("/analyze", json={
        "table_name": "maintenance",
        "analysis_type": "correlation",
        "parameters": {
            "columns": ["cost"]
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "correlation_matrix" in data
    
    # Test distribution analysis
    response = client.post("/analyze", json={
        "table_name": "customer_orders",
        "analysis_type": "distribution",
        "parameters": {
            "column": "amount"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "distribution" in data

def test_sse_endpoints(test_data_dir):
    """Test the SSE endpoints"""
    # Test data_provider tool
    response = client.get("/sse/data_provider")
    assert response.status_code == 200
    # Note: SSE responses are streamed, so we can't easily test the content
    
    # Test show_tables tool
    response = client.get("/sse/show_tables")
    assert response.status_code == 200
    
    # Test analyze tool
    response = client.get("/sse/analyze")
    assert response.status_code == 200
    
    # Test invalid tool
    response = client.get("/sse/invalid_tool")
    assert response.status_code == 200

def test_error_handling(test_data_dir):
    """Test error handling"""
    # Test non-existent table
    response = client.post("/query", json={
        "table_name": "non_existent_table"
    })
    assert response.status_code == 404
    
    # Test invalid analysis type
    response = client.post("/analyze", json={
        "table_name": "sensor",
        "analysis_type": "invalid_analysis"
    })
    assert response.status_code == 400
    
    # Test missing required parameters
    response = client.post("/analyze", json={
        "table_name": "sensor",
        "analysis_type": "trend"
    })
    assert response.status_code == 400

def test_visualization(test_data_dir):
    """Test visualization generation"""
    response = client.post("/query", json={
        "table_name": "sensor",
        "visualization_type": "bar",
        "columns": ["sensor_id", "value"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "visualization" in data
    assert data["visualization"] is not None
    
    # Test invalid visualization type
    response = client.post("/query", json={
        "table_name": "sensor",
        "visualization_type": "invalid_type",
        "columns": ["sensor_id", "value"]
    })
    assert response.status_code == 400

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 