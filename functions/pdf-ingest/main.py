import os
import functions_framework
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_postgres import PGVector
from google.cloud import storage
import asyncio

# Config from Env Vars
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Constants
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Global clients to reuse connection if warm
embeddings_client = None

def get_embeddings():
    global embeddings_client
    if not embeddings_client:
        embeddings_client = VertexAIEmbeddings(
            model_name="textembedding-gecko@003",
            project=PROJECT_ID,
            location=REGION
        )
    return embeddings_client

async def process_document(local_path):
    print(f"📄 Processing {local_path}...")
    
    # 1. Load
    loader = PyPDFLoader(local_path)
    docs = loader.load()
    if not docs:
        print("⚠️ No content found.")
        return

    # 2. Split
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, 
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(docs)
    print(f"🧩 Split into {len(chunks)} chunks.")

    # 3. Vector Store
    # Connection string
    connection_string = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    
    vector_store = PGVector(
        embeddings=get_embeddings(),
        collection_name="knowledge_base",
        connection=connection_string,
        use_jsonb=True,
    )

    # 4. Upsert
    await vector_store.add_documents(chunks)
    print("✅ Successfully ingested chunks.")


@functions_framework.cloud_event
def ingest_pdf(cloud_event):
    """
    Triggered by a change to a Cloud Storage bucket.
    """
    data = cloud_event.data
    event_id = cloud_event["id"]
    event_type = cloud_event["type"]
    bucket_name = data["bucket"]
    file_name = data["name"]

    print(f"Received event {event_id}: {event_type} for {bucket_name}/{file_name}")

    # Only process PDFs
    if not file_name.lower().endswith('.pdf'):
        print(f"Skipping non-PDF file: {file_name}")
        return

    # Download file to /tmp
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    local_path = f"/tmp/{os.path.basename(file_name)}"
    blob.download_to_filename(local_path)
    print(f"Downloaded to {local_path}")

    try:
        # Run async process
        asyncio.run(process_document(local_path))
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        raise e
    finally:
        # Cleanup
        if os.path.exists(local_path):
            os.remove(local_path)
