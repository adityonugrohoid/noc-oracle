import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

class NOCEngine:
    def __init__(self):
        """
        Initializes the NOCEngine with Hybrid Retrieval capabilities.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found.")

        # 1. GENERATION (LLM)
        genai.configure(api_key=api_key)
        # We stick to the model that works for your key/region
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

        # 2. RETRIEVAL (Vector DB)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=api_key
        )
        
        self.vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddings
        )

    def _extract_error_codes(self, text: str):
        """
        Helper: Finds patterns like 'E-101', 's304', 'HW-1002' (Case insensitive, optional hyphen).
        """
        # Regex explanation:
        # \b        = Word boundary
        # [A-Za-z]+ = One or more letters
        # -?        = Optional hyphen
        # \d+       = One or more digits
        # \b        = Word boundary
        return re.findall(r"\b[A-Za-z]+-?\d+\b", text)

    def get_solution(self, query: str) -> dict:
        """
        Performs Hybrid Search (Vector + Keyword Boost) to ensure exact matches.
        """
        try:
            # STEP 1: Cast a wider net
            raw_docs = self.vectorstore.similarity_search(query, k=10)
            
            # STEP 2: Keyword Boosting (Updated for Fuzzy Match)
            query_codes = self._extract_error_codes(query)
            
            final_docs = []
            
            if query_codes:
                print(f"DEBUG: Detected specific Error Codes in query: {query_codes}")
                priority_docs = []
                other_docs = []
                
                # Normalize query codes (e.g., "s304" -> "S304")
                norm_query_codes = [c.replace("-", "").upper() for c in query_codes]
                
                for doc in raw_docs:
                    # Normalize doc content for search (e.g., "S-304" -> "S304")
                    # We search in metadata AND content to be safe
                    doc_blob = (doc.page_content + str(doc.metadata)).replace("-", "").upper()
                    
                    # Check if ANY of the normalized query codes exist in the normalized doc
                    if any(code in doc_blob for code in norm_query_codes):
                        priority_docs.append(doc)
                    else:
                        other_docs.append(doc)
                
                # Stack priority docs first
                final_docs = priority_docs + other_docs
            else:
                final_docs = raw_docs

            # STEP 3: Trim back to top 3 for the LLM
            final_docs = final_docs[:3]

            if not final_docs:
                return {"answer": "No relevant information found.", "source_documents": []}

            # STEP 4: Construct Prompt
            context_parts = []
            for i, doc in enumerate(final_docs, 1):
                chunk_text = f"Context Chunk {i}:\n{doc.page_content}\n"
                context_parts.append(chunk_text)
            
            context_str = "\n---\n".join(context_parts)

            prompt = f"""
            You are a Level 3 Field Engineer. 
            Use ONLY the context below to answer. 
            
            Context: 
            {context_str}
            
            Question: {query}
            
            If the answer is not in the context, say "Procedure not found in standard operating manual."
            """

            response = self.model.generate_content(prompt)
            
            return {
                "answer": response.text,
                "source_documents": final_docs
            }

        except Exception as e:
            return {"answer": f"Error processing request: {e}", "source_documents": []}

    def get_baseline_response(self, query: str) -> str:
        """
        Generates a response WITHOUT RAG (Pure LLM) for comparison.
        """
        try:
            prompt = f"""
            You are a helpful technical support assistant.
            The user is asking a technical question about a telecom base station.
            Question: {query}
            Provide a technical resolution step-by-step.
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating baseline: {e}"

if __name__ == "__main__":
    engine = NOCEngine()
    
    # We test both formatted and unformatted queries
    test_queries = ["How to fix S-304", "s304"]
    
    for q in test_queries:
        print(f"\n{'='*50}")
        print(f"🔎 TESTING QUERY: '{q}'")
        print(f"{'='*50}")
        
        result = engine.get_solution(q)
        
        print(f"\n--- 📄 RANKED CHUNKS (Proof of Hybrid Search) ---")
        if not result["source_documents"]:
            print("No documents found.")
        else:
            for i, doc in enumerate(result["source_documents"], 1):
                # We grab the Error Code from metadata to verify sorting
                code = doc.metadata.get('Error_Code', 'Unknown')
                category = doc.metadata.get('Category', 'Unknown')
                print(f"Rank #{i} | Code: {code} | Section: {category}")
        
        print(f"\n--- 🤖 AI ANSWER ---")
        print(result["answer"].strip())
        print("\n" + "-"*50)