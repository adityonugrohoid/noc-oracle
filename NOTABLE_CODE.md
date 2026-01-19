# Notable Code: NOC Oracle

**Production Readiness Level:** MVP

This document highlights key code sections that demonstrate the technical strengths and architectural patterns implemented in this RAG system.

## Overview

NOC Oracle is a Retrieval-Augmented Generation (RAG) system specialized for telecommunications troubleshooting. It demonstrates sophisticated RAG patterns including hybrid search, context-aware chunking, and strict context enforcement to prevent LLM hallucination.

---

## 1. Hybrid Search with Keyword Boosting

**File:** `src/engine.py`  
**Lines:** 36-86

The hybrid search implementation combines semantic vector search with keyword boosting to ensure exact matches for error codes while maintaining semantic understanding for vague queries.

```python
def _extract_error_codes(self, text: str):
    """
    Helper: Finds patterns like 'E-101', 's304', 'HW-1002' (Case insensitive, optional hyphen).
    """
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
```

**Why it's notable:**
- Two-stage retrieval: semantic search first, then keyword boosting
- Normalizes error codes (handles "S-304", "s304", "S304" variations)
- Searches both content and metadata for comprehensive matching
- Prioritizes exact matches while preserving semantic results
- Handles both specific codes and vague queries gracefully

---

## 2. Context-Aware Chunking with Metadata Injection

**File:** `src/ingestor.py`  
**Lines:** 33-49

The context-aware chunking strategy preserves the relationship between error codes and their solutions by injecting parent headers into chunk content.

```python
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
```

**Why it's notable:**
- Uses `MarkdownHeaderTextSplitter` to chunk at header boundaries
- Preserves document hierarchy (Title → Category → Error_Code)
- Injects parent headers into chunk content for embedding
- Ensures error codes and solutions are treated as atomic units
- Prevents splitting error codes from their repair procedures

---

## 3. Strict Context Enforcement for Hallucination Prevention

**File:** `src/engine.py`  
**Lines:** 91-109

The prompt engineering enforces strict context-only responses, preventing the LLM from inventing procedures not in the manual.

```python
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
```

**Why it's notable:**
- Explicit instruction: "Use ONLY the context below to answer"
- Clear fallback: "Procedure not found" if code missing
- No fallback to general knowledge
- Structured context presentation with chunk numbering
- Role-based prompting ("Level 3 Field Engineer") for appropriate tone

---

## 4. Hallucination Risk Comparison Feature

**File:** `src/engine.py`  
**Lines:** 121-135

The system includes a baseline comparison feature that demonstrates the value of RAG by showing what a generic LLM would guess.

```python
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
```

**Why it's notable:**
- Demonstrates RAG value through side-by-side comparison
- Shows ungrounded LLM responses vs RAG-verified answers
- Builds trust through explainability
- Educational tool for understanding hallucination risks
- No context provided to baseline, showing pure LLM behavior

---

## Architecture Highlights

### RAG Pipeline Stages

1. **Ingestion**: Context-aware chunking with metadata injection
2. **Retrieval**: Hybrid search (semantic + keyword boosting)
3. **Generation**: Strict context enforcement with fallback

### Design Patterns Used

1. **Hybrid Search Pattern**: Combines semantic and keyword search
2. **Context Injection Pattern**: Embeds metadata in chunk content
3. **Strict Prompting Pattern**: Enforces context-only responses
4. **Comparison Pattern**: Side-by-side RAG vs baseline

---

## Technical Strengths Demonstrated

- **Hybrid Search**: Combines best of semantic and keyword matching
- **Context Preservation**: Maintains error-solution relationships through chunking
- **Hallucination Prevention**: Strict prompt engineering prevents ungrounded responses
- **Fuzzy Matching**: Handles error code variations (S-304, s304, S304)
- **Explainability**: Source citations and comparison mode build trust
