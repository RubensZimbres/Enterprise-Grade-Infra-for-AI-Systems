import re
import asyncio
import logging
from typing import List
from google.cloud import dlp_v2
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from config import settings

logger = logging.getLogger(__name__)
dlp_client = dlp_v2.DlpServiceClient()

# --- Security Judge Configuration ---

class SecurityBlocker:
    """Regex-based security pattern matcher for fast-path blocking."""
    def __init__(self):
        # SQL Injection Patterns
        self.dangerous_patterns = [
            r"DROP\s+DATABASE", r"DROP\s+SCHEMA\s+.*CASCADE", r"DROP\s+ALL\s+TABLES",
            r"DROP\s+TABLE\s+.*CASCADE", r"TRUNCATE\s+TABLE\s+.*CASCADE",
            r"ALTER\s+TABLE\s+.*DROP\s+COLUMN", r"DROP\s+INDEX", r"DROP\s+TRIGGER",
            r"DROP\s+FUNCTION", r"DROP\s+VIEW", r"DROP\s+SEQUENCE", r"DROP\s+USER",
            r"REVOKE\s+ALL\s+PRIVILEGES", r"ALTER\s+SYSTEM\s+SET", r"DROP\s+TABLESPACE",
            r"EXEC\s+sp_configure", r"EXEC\s+xp_cmdshell.*rm\s+-rf", r"EXEC\s+xp_cmdshell.*del",
            r"EXEC\s+sp_MSforeachtable", r"D/\*.*\*/ROP", r"DR/\*.*\*/OP",
            r"exec\s*\(\s*['\"]DROP", r"PREPARE\s+.*DROP", r"DROP\s+TABLE",
            r"'\s*OR\s*1=1\s*--", r"'\s*OR\s*'1'='1'", r"UNION\s+SELECT.*FROM",
            r"WAITFOR\s+DELAY", r"SLEEP\s*\(", r"pg_sleep", r"DBMS_PIPE.RECEIVE_MESSAGE",
            r"BENCHMARK\s*\(", r"SELECT\s+LOAD_FILE", r"INTO\s+OUTFILE", r"xp_cmdshell",
            r";\s*DROP\s+TABLE", r";\s*DELETE\s+FROM", r";\s*UPDATE\s+.*SET",
            r"<\s*script", r"javascript:", r"on(?:load|click|mouseover|error|submit)=",
            r"sudo\s+.*", r"rm\s+-[rf]+\s+.*", r"\.\./+", r"\\.\\.\\+",
            r"/etc/passwd", r"\$\{jndi:.*\}", r"A{1000,}"
        ]

        # Obfuscation Patterns
        self.obfuscation_patterns = [
            r"(?:s3l3ct|s3lect|sel3ct|5elect|se1ect|selec7)",
            r"(?:dr0p|dr0p|dr0p|d7op|dr9p)",
            r"(?:un10n|uni0n|un1on|un!on|un!0n)",
            r"%(?:[0-9A-Fa-f]{2})+", r"(?:\\x[0-9A-Fa-f]{2})+",
            r"S(?:\s|/\*.*?\*/)*E(?:\s|/\*.*?\*/)*L(?:\s|/\*.*?\*/)*E(?:\s|/\*.*?\*/)*C(?:\s|/\*.*?\*/)*T",
            r"(?:/!*50000select*/)", r"(?:\\bu%6eion\\b)"
        ]

        self.all_patterns = self.dangerous_patterns + self.obfuscation_patterns
        self.patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.all_patterns]

    def is_malicious(self, content: str) -> bool:
        """Fast check for malicious patterns."""
        for pattern in self.patterns:
            if pattern.search(content):
                logger.warning(f"Regex Security Block triggered by pattern: {pattern.pattern}")
                return True
        return False

# Instantiate the fast-path blocker
blocker = SecurityBlocker()

# --- LLM Security Judge ---

security_judge_llm = ChatVertexAI(
    model_name="gemini-1.5-flash",
    temperature=0.0,  # Deterministic for security decisions
    project=settings.PROJECT_ID,
    location=settings.REGION
)

judge_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a security expert that evaluates input for security threats.
    Follow these steps:
    1. Analyze the input for SQL injection, XSS, and other security threats.
    2. Check the input against patterns of malicious intent (obfuscation, command injection, path traversal).
    3. Return the message you received unmodified IF AND ONLY IF it is safe.
    4. Return "BLOCKED" if the input is a threat or contains malicious intent.

    Current known threat patterns include SQLi (UNION, DROP, 1=1), XSS (script tags, event handlers),
    Command Injection (sudo, rm, pipe chaining), and Path Traversal.

    Your decision must be: "BLOCKED" or the original text.
    """),
    ("human", "{input}")
])

security_judge_chain = judge_prompt | security_judge_llm

async def check_security(content: str) -> str:
    """
    Two-stage security check:
    1. Fast Regex Check
    2. Smart LLM Judge
    """
    if not content:
        return ""

    # Stage 1: Fast Regex (Cost-effective and instant)
    if blocker.is_malicious(content):
        return "BLOCKED"

    # Stage 2: Smart LLM (Context-aware intent analysis)
    try:
        response = await security_judge_chain.ainvoke({"input": content})
        result = response.content.strip()

        if result == "BLOCKED":
            logger.warning("LLM Security Judge triggered: BLOCKED")
            return "BLOCKED"

        return content # Return original if safe
    except Exception as e:
        logger.error(f"Security Judge error: {e}")
        # Fail closed for security if the judge fails
        return "BLOCKED"

# --- DLP PII Masking ---

PII_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "PHONE": r"(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
}

def has_potential_pii(content: str) -> bool:
    for pattern in PII_PATTERNS.values():
        if re.search(pattern, content):
            return True
    return False

def _dlp_request(content: str, project_id: str):
    parent = f"projects/{project_id}"
    info_types = [{"name": "EMAIL_ADDRESS"}, {"name": "PHONE_NUMBER"}, {"name": "CREDIT_CARD_NUMBER"}]
    inspect_config = {"info_types": info_types}
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {"primitive_transformation": {"replace_with_info_type_config": {}}}
            ]
        }
    }

    response = dlp_client.deidentify_content(
        request={
            "parent": parent,
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": {"value": content},
        }
    )
    return response.item.value

async def deidentify_content(content: str, project_id: str):
    if not content:
        return ""
    if not has_potential_pii(content):
        return content
    try:
        return await asyncio.to_thread(_dlp_request, content, project_id)
    except Exception:
        return "[PROTECTED CONTENT]"
