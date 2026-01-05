import os
from dotenv import load_dotenv
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
import pathlib
import shutil  # Added for cleanup

# Load environment variables
load_dotenv()

def ingest_manual():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    manual_path = pathlib.Path("data/manuals/orbit_5g_guide.md")
    if not manual_path.exists():
        print(f"Error: Manual file not found at {manual_path}")
        return

    # 1. CLEANUP: Delete old DB to prevent duplicates/ghost data
    db_path = "./chroma_db"
    if os.path.exists(db_path):
        print(f"Removing old database at {db_path}...")
        shutil.rmtree(db_path)

    print(f"Loading manual from {manual_path}...")
    with open(manual_path, "r", encoding="utf-8") as f:
        markdown_document = f.read()

    headers_to_split_on = [
        ("#", "Title"),
        ("##", "Category"),
        ("###", "Error_Code"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    docs = markdown_splitter.split_text(markdown_document)
    
    print(f"Split document into {len(docs)} chunks.")

    # 2. THE FIX: Inject Metadata back into Page Content for Embedding
    print("Injecting headers into vector content...")
    for doc in docs:
        # We prepend the Error Code and Category to the text so the vector 'sees' it.
        header_context = f"{doc.metadata.get('Category', '')} - {doc.metadata.get('Error_Code', '')}"
        doc.page_content = f"{header_context}\n\n{doc.page_content}"

    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
    
    print(f"Ingesting into ChromaDB at {db_path}...")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=db_path
    )
    
    print("Ingestion complete! Database persisted.")
    if docs:
        print("Example enriched chunk:", docs[0].page_content[:100] + "...")

if __name__ == "__main__":
    ingest_manual()