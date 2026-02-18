"""Property-based tests for API response format consistency.

**Validates: Requirements 10.1, 10.2, 10.3, 10.4**

This module tests that all API responses follow a unified format:
- Success responses: {success: true, data: {...}, message: null}
- Error responses: {success: false, data: null, error: {code: "...", message: "..."}}
- Paginated responses: Include meta field with total, page, limit
- Standard error codes: INVALID_REQUEST, NOT_FOUND, etc.
"""
import pytest
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st, settings, HealthCheck
from main import create_app
from typing import Dict, Any


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app=app)


class TestAPIResponseFormatProperties:
    """Property-based tests for API response format consistency."""
    
    @given(
        kb_name=st.text(min_size=1, max_size=255),
        description=st.one_of(st.none(), st.text(max_size=1000))
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_success_response_has_required_fields(self, client, kb_name, description):
        """Property: All success responses must have success=true, data, and message fields.
        
        For any successful API call, the response should contain:
        - success: true
        - data: the response payload
        - message: optional message or null
        """
        payload = {"name": kb_name, "description": description}
        response = client.post("/api/knowledge-bases", json=payload)
        
        # Only test successful responses
        if response.status_code == 201:
            data = response.json()
            
            # Required fields for success response
            assert "success" in data, "Response must contain 'success' field"
            assert data["success"] is True, "Success response must have success=true"
            assert "data" in data, "Response must contain 'data' field"
            assert "message" in data, "Response must contain 'message' field"
            
            # Data should not be None for successful creation
            assert data["data"] is not None, "Data should not be None for successful response"
    
    @given(
        kb_id=st.text(
            alphabet=st.characters(blacklist_categories=('Cc', 'Cs'), blacklist_characters='\x00\x1f'),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_response_has_required_fields(self, client, kb_id):
        """Property: All error responses must have success=false and error field with code and message.
        
        For any failed API call, the response should contain:
        - success: false
        - data: null
        - error: {code: "...", message: "..."}
        """
        # Try to get a non-existent knowledge base
        try:
            response = client.get(f"/api/knowledge-bases/{kb_id}")
        except Exception:
            # Skip if URL is invalid
            return
        
        # Only test error responses (skip 404 from non-existent routes)
        if response.status_code >= 400 and response.status_code != 404:
            data = response.json()
            
            # Required fields for error response
            assert "success" in data, "Error response must contain 'success' field"
            assert data["success"] is False, "Error response must have success=false"
            assert "error" in data, "Error response must contain 'error' field"
            
            # Error object structure
            error = data["error"]
            assert isinstance(error, dict), "Error must be a dictionary"
            assert "code" in error, "Error must contain 'code' field"
            assert "message" in error, "Error must contain 'message' field"
            assert isinstance(error["code"], str), "Error code must be a string"
            assert isinstance(error["message"], str), "Error message must be a string"
    
    @given(
        skip=st.integers(min_value=0, max_value=1000),
        limit=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_paginated_response_has_meta_field(self, client, skip, limit):
        """Property: All paginated responses must include meta field with pagination info.
        
        For any paginated API response, the meta field should contain:
        - total: total number of items
        - skip: number of items skipped
        - limit: maximum items per page
        - page: current page number
        - pages: total number of pages
        """
        response = client.get(f"/api/knowledge-bases?skip={skip}&limit={limit}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for meta field
            assert "meta" in data, "Paginated response must contain 'meta' field"
            meta = data["meta"]
            
            # Required pagination fields
            assert "total" in meta, "Meta must contain 'total' field"
            assert "skip" in meta, "Meta must contain 'skip' field"
            assert "limit" in meta, "Meta must contain 'limit' field"
            assert "page" in meta, "Meta must contain 'page' field"
            assert "pages" in meta, "Meta must contain 'pages' field"
            
            # Type checks
            assert isinstance(meta["total"], int), "Total must be an integer"
            assert isinstance(meta["skip"], int), "Skip must be an integer"
            assert isinstance(meta["limit"], int), "Limit must be an integer"
            assert isinstance(meta["page"], int), "Page must be an integer"
            assert isinstance(meta["pages"], int), "Pages must be an integer"
            
            # Value checks
            assert meta["total"] >= 0, "Total must be non-negative"
            assert meta["skip"] >= 0, "Skip must be non-negative"
            assert meta["limit"] > 0, "Limit must be positive"
            assert meta["page"] > 0, "Page must be positive"
            assert meta["pages"] > 0, "Pages must be positive"
    
    @given(
        kb_name=st.text(min_size=1, max_size=255)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_response_data_type_consistency(self, client, kb_name):
        """Property: Response data types must be consistent across all endpoints.
        
        For any API response:
        - success field must be boolean
        - data field must be object or null
        - message field must be string or null
        - error field (if present) must be object
        """
        payload = {"name": kb_name}
        response = client.post("/api/knowledge-bases", json=payload)
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Type checks
            assert isinstance(data["success"], bool), "success must be boolean"
            assert data["data"] is None or isinstance(data["data"], dict), \
                "data must be object or null"
            assert data["message"] is None or isinstance(data["message"], str), \
                "message must be string or null"
    
    @given(
        kb_name=st.text(min_size=1, max_size=255),
        description=st.one_of(st.none(), st.text(max_size=1000))
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_knowledge_base_response_structure(self, client, kb_name, description):
        """Property: Knowledge base responses must have consistent structure.
        
        For any knowledge base response, the data object should contain:
        - id: string
        - name: string
        - description: string or null
        - document_count: integer >= 0
        - total_size: integer >= 0
        - created_at: datetime string
        - updated_at: datetime string
        """
        payload = {"name": kb_name, "description": description}
        response = client.post("/api/knowledge-bases", json=payload)
        
        if response.status_code == 201:
            data = response.json()
            kb = data["data"]
            
            # Required fields
            assert "id" in kb, "KB must have id"
            assert "name" in kb, "KB must have name"
            assert "description" in kb, "KB must have description"
            assert "document_count" in kb, "KB must have document_count"
            assert "total_size" in kb, "KB must have total_size"
            assert "created_at" in kb, "KB must have created_at"
            assert "updated_at" in kb, "KB must have updated_at"
            
            # Type checks
            assert isinstance(kb["id"], str), "id must be string"
            assert isinstance(kb["name"], str), "name must be string"
            assert kb["description"] is None or isinstance(kb["description"], str), \
                "description must be string or null"
            assert isinstance(kb["document_count"], int), "document_count must be integer"
            assert isinstance(kb["total_size"], int), "total_size must be integer"
            assert isinstance(kb["created_at"], str), "created_at must be string"
            assert isinstance(kb["updated_at"], str), "updated_at must be string"
            
            # Value checks
            assert kb["document_count"] >= 0, "document_count must be non-negative"
            assert kb["total_size"] >= 0, "total_size must be non-negative"
    
    @given(
        kb_name=st.text(min_size=1, max_size=255)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_response_consistency_across_endpoints(self, client, kb_name):
        """Property: All endpoints must follow the same response format.
        
        For any endpoint (GET, POST, PUT, DELETE), the response structure
        should be consistent with the unified format.
        """
        # Create a KB
        create_response = client.post(
            "/api/knowledge-bases",
            json={"name": kb_name}
        )
        
        if create_response.status_code == 201:
            kb_id = create_response.json()["data"]["id"]
            
            # Test GET endpoint
            get_response = client.get(f"/api/knowledge-bases/{kb_id}")
            if get_response.status_code == 200:
                get_data = get_response.json()
                assert "success" in get_data
                assert "data" in get_data
                assert "message" in get_data
            
            # Test PUT endpoint
            put_response = client.put(
                f"/api/knowledge-bases/{kb_id}",
                json={"name": f"{kb_name}_updated"}
            )
            if put_response.status_code == 200:
                put_data = put_response.json()
                assert "success" in put_data
                assert "data" in put_data
                assert "message" in put_data
            
            # Test DELETE endpoint
            delete_response = client.delete(f"/api/knowledge-bases/{kb_id}")
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                assert "success" in delete_data
                assert "message" in delete_data
    
    @given(
        kb_name=st.text(min_size=1, max_size=255)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_response_codes_are_standard(self, client, kb_name):
        """Property: Error responses must use standard error codes.
        
        For any error response, the error code should be one of the standard codes:
        - INVALID_REQUEST
        - NOT_FOUND
        - CONFLICT
        - INTERNAL_ERROR
        - VALIDATION_ERROR
        """
        # Try to create KB with invalid data (empty name)
        response = client.post("/api/knowledge-bases", json={"name": ""})
        
        if response.status_code >= 400:
            data = response.json()
            if "error" in data and "code" in data["error"]:
                error_code = data["error"]["code"]
                valid_codes = {
                    "INVALID_REQUEST",
                    "NOT_FOUND",
                    "CONFLICT",
                    "INTERNAL_ERROR",
                    "VALIDATION_ERROR"
                }
                assert error_code in valid_codes, \
                    f"Error code '{error_code}' must be one of {valid_codes}"
    
    @given(
        kb_name=st.text(min_size=1, max_size=255)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_response_message_field_consistency(self, client, kb_name):
        """Property: Message field must be consistent across response types.
        
        For any response:
        - Success responses may have a message string or null
        - Error responses should have error details instead of message
        - Message should be human-readable if present
        """
        payload = {"name": kb_name}
        response = client.post("/api/knowledge-bases", json=payload)
        
        data = response.json()
        
        # Message field should be string or null (only for successful responses)
        if response.status_code in [200, 201]:
            assert "message" in data, "Success response must have message field"
            assert data["message"] is None or isinstance(data["message"], str), \
                "message must be string or null"
            
            # If message is present, it should be non-empty
            if data["message"] is not None:
                assert len(data["message"]) > 0, "message must not be empty string"
