import pytest
from unittest.mock import MagicMock, patch
from chains.agent_graph import triage_node, decide_route, general_node
from langchain_core.messages import AIMessage

# --- Test Triage Node ---

def test_triage_node_rag():
    """Test that triage node correctly identifies RAG intent"""
    state = {"question": "What is the capital of France?", "history": [], "intent": "", "answer": ""}
    
    with patch("chains.agent_graph.llm") as mock_llm:
        # Mock the invoke method to return an AIMessage
        response = AIMessage(content="RAG")
        mock_llm.invoke.return_value = response
        mock_llm.return_value = response
        
        result = triage_node(state)
        assert result["intent"] == "RAG"

def test_triage_node_general():
    """Test that triage node correctly identifies GENERAL intent"""
    state = {"question": "Hi there", "history": [], "intent": "", "answer": ""}
    
    with patch("chains.agent_graph.llm") as mock_llm:
        response = AIMessage(content="GENERAL")
        mock_llm.invoke.return_value = response
        mock_llm.return_value = response
        
        result = triage_node(state)
        assert result["intent"] == "GENERAL"

# --- Test Decision Logic ---

def test_decide_route_rag():
    state = {"intent": "RAG"}
    assert decide_route(state) == "rag"

def test_decide_route_general():
    state = {"intent": "GENERAL"}
    assert decide_route(state) == "general"

def test_decide_route_mixed():
    # If the LLM returns something verbose like "The intent is RAG."
    state = {"intent": "The intent is RAG."}
    assert decide_route(state) == "rag"

# --- Test General Node ---

def test_general_node():
    """Test that general node produces a response"""
    state = {"question": "Hello", "history": [], "intent": "GENERAL", "answer": ""}
    
    with patch("chains.agent_graph.llm") as mock_llm:
        response = AIMessage(content="Hello! How can I help you?")
        mock_llm.invoke.return_value = response
        mock_llm.return_value = response
        
        result = general_node(state)
        assert result["answer"] == "Hello! How can I help you?"
