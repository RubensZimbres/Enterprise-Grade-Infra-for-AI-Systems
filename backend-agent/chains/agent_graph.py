from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains.rag_chain import conversational_rag_chain, llm, settings
from .guardrails import check_security, deidentify_content
import logging
import httpx
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable

logger = logging.getLogger(__name__)


# 1. Define State
class AgentState(TypedDict):
    question: str
    history: list
    answer: str
    intent: str
    session_id: str  # Added for Firestore history management


# 2. Define Nodes


# Node 1: Triage (Router)
async def triage_node(state: AgentState):
    """
    Determines if the user's query needs the RAG knowledge base or is just general chat.
    """
    logger.info("--- TRIAGE NODE ---")
    question = state["question"]

    # Simple classifier prompt
    system_prompt = """You are a router. Your job is to classify the user's intent.

    OPTIONS:
    - "RAG": If the user asks a technical question, asks about data, documentation, specific facts, or complex topics.
    - "GENERAL": If the user asks a simple greeting (hi, hello), asks "how are you", or makes small talk.

    Return ONLY the word "RAG" or "GENERAL"."""

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{question}")]
    )

    classifier = prompt | llm | StrOutputParser()
    intent = await classifier.ainvoke({"question": question})

    logger.info(f"Intent Classified: {intent}")
    return {"intent": intent.strip()}


# Node 2: General Chat
async def general_node(state: AgentState):
    """
    Handles general chit-chat without invoking the vector store.
    """
    logger.info("--- GENERAL NODE ---")
    question = state["question"]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful and polite AI assistant. Answer the user's greeting or small talk concisely.",
            ),
            ("human", "{question}"),
        ]
    )

    chain = prompt | llm | StrOutputParser()
    response = await chain.ainvoke({"question": question})
    return {"answer": response}


# Node 3: RAG (Knowledge Base)
async def rag_node(state: AgentState):
    """
    Invokes the existing RAG chain for technical queries.
    Uses conversational_rag_chain which handles history via Firestore automatically.
    """
    logger.info("--- RAG NODE ---")
    # Get session_id from state (passed through from protected_graph_invoke)
    session_id = state.get("session_id", "default_session")
    response = await conversational_rag_chain.ainvoke(
        {"question": state["question"]},
        config={"configurable": {"session_id": session_id}},
    )
    # conversational_rag_chain returns an AIMessage
    return {"answer": response.content}


# 3. Define Conditional Logic
def decide_route(state: AgentState):
    intent = state["intent"]
    if "RAG" in intent:
        return "rag"
    else:
        return "general"


# 4. Build Graph
workflow = StateGraph(AgentState)

workflow.add_node("triage", triage_node)
workflow.add_node("general", general_node)
workflow.add_node("rag", rag_node)

workflow.set_entry_point("triage")

workflow.add_conditional_edges(
    "triage", decide_route, {"rag": "rag", "general": "general"}
)

workflow.add_edge("general", END)
workflow.add_edge("rag", END)

# Compile
graph_app = workflow.compile()


# 5. Protected Invocation (Graph Version)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(
        (
            GoogleAPICallError,
            ServiceUnavailable,
            httpx.RequestError,
            asyncio.TimeoutError,
        )
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def protected_graph_invoke(input_text: str, session_id: str):
    """
    Asynchronously invokes the Agent Graph with Security Judge and DLP guardrails.
    """
    # Step A: Security Check
    security_check = await check_security(input_text)
    if security_check == "BLOCKED":
        return "I'm sorry, but I cannot process this request due to security policy violations."

    # Step B: Sanitize Input (DLP)
    safe_input = await deidentify_content(input_text, settings.PROJECT_ID)

    # Step C: Run Graph
    # History is managed by conversational_rag_chain via Firestore in the rag_node
    inputs = {
        "question": safe_input,
        "history": [],  # Placeholder - actual history managed by conversational_rag_chain
        "intent": "",
        "answer": "",
        "session_id": session_id,  # Passed to rag_node for Firestore history
    }

    result = await graph_app.ainvoke(inputs)
    response_text = result["answer"]

    # Step D: Sanitize Output
    safe_output = await deidentify_content(response_text, settings.PROJECT_ID)
    return safe_output


async def protected_graph_stream(input_text: str, session_id: str):
    """
    Streaming version for the Graph.
    """
    security_check = await check_security(input_text)
    if security_check == "BLOCKED":
        yield "I'm sorry, but I cannot process this request due to security policy violations."
        return

    safe_input = await deidentify_content(input_text, settings.PROJECT_ID)

    inputs = {
        "question": safe_input,
        "history": [],
        "intent": "",
        "answer": "",
        "session_id": session_id,  # Pass session_id for Firestore history
    }

    # Stream the OUTPUT of the final node
    async for event in graph_app.astream(inputs):
        for key, value in event.items():
            if key in ["rag", "general"]:
                yield value["answer"]
