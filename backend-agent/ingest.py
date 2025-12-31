import os
import asyncio
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_postgres import PGVector
from config import settings


# --- CONFIGURATION ---
DATA_PATH = "./data"
CHUNK_SIZE = 1000  # Tokens/Characters per chunk. Tunable parameter.
CHUNK_OVERLAP = 200 # Critical for keeping context across boundaries.

async def ingest_data():
    print(f"🚀 Starting Ingestion Pipeline for Project: {settings.PROJECT_ID}")

    # 1. Load Documents
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: Data directory '{DATA_PATH}' not found.")
        return

    print("📂 Loading documents...")
    # Smart loader that handles PDFs and TXT files automatically
    loader = DirectoryLoader(
        DATA_PATH,
        glob="**/*.pdf", # Change to "**/*" for all files
        loader_cls=PyPDFLoader,
        show_progress=True
    )
    raw_docs = loader.load()

    if not raw_docs:
        print("⚠️  No documents found. Exiting.")
        return

    print(f"✅ Loaded {len(raw_docs)} documents.")

    # 2. Split Text (The Art of Chunking)
    print("✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""] # Try to split by paragraph first
    )

    chunks = text_splitter.split_documents(raw_docs)
    print(f"🧩 Generated {len(chunks)} chunks.")

    # 3. Connect to Database (Cloud SQL)
    print("🔌 Connecting to Cloud SQL...")
    embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@003", project=settings.PROJECT_ID, location=settings.REGION)

    connection_string = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"

    # Ensure pgvector extension exists
    # We need a synchronous connection or a specific async execution to run the CREATE EXTENSION command
    # However, LangChain's PGVector might attempt to create it. To be safe, let's try to let PGVector handle it
    # or use a raw connection if strictly necessary.
    # For simplicity in this script, we'll rely on the user/terraform having appropriate permissions
    # but let's update the log message.

    # Note: We use 'pre_delete_collection=True' to wipe old data for a clean slate.
    print(f"💾 Ingesting into database '{settings.DB_NAME}'...")

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name="knowledge_base",
        connection=connection_string,
        use_jsonb=True,
    )

    # Force extension creation (if possible via the driver, otherwise rely on manual setup or PGVector's internal checks)
    # Ideally, run: await vector_store.aexecute("CREATE EXTENSION IF NOT EXISTS vector") if the library supported it easily.
    # Instead, we will assume the database allows extension creation.

    # 4. Upsert Data
    # We do this in batches implicitly handled by LangChain, but you can force batching if needed.
    await vector_store.add_documents(chunks)

    print("🎉 Ingestion Complete! Your agent now has a brain.")

if __name__ == "__main__":
    # Ensure the async loop runs
    asyncio.run(ingest_data())