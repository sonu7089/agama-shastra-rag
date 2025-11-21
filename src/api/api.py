import os
import time
import json
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

# Import your existing modules
# Import your existing modules
import sys
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

from src.core.retriever import BookRetriever

# Load environment variables
load_dotenv()

app = FastAPI(title="Agama Shastra Guru API")

# Enable CORS so the HTML frontend can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, specify the domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# GLOBAL STATE
# -----------------------------------------------------------------------------
class GlobalState:
    retriever: Optional[BookRetriever] = None
    model: Optional[Any] = None

state = GlobalState()

# -----------------------------------------------------------------------------
# DATA MODELS
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    api_key: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    context: Optional[str] = None
    citations: List[str] = []

# -----------------------------------------------------------------------------
# LOGIC (Adapted from app_v3.py)
# -----------------------------------------------------------------------------

def get_retriever():
    if state.retriever is None:
        print("Initializing Retriever...")
        try:
            state.retriever = BookRetriever(db_path="data/chroma_db")
            print("Retriever initialized.")
        except Exception as e:
            print(f"Failed to initialize retriever: {e}")
    return state.retriever

def get_model(api_key: str):
    # In a real app, you might handle API keys differently (e.g. env var only)
    # But to match the existing flow where user can provide it:
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")
        return None

def optimize_query(model, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
    if not chat_history:
        history_text = "No prior history."
    else:
        history_text = ""
        for msg in chat_history[-3:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_text += f"{role}: {content}\n"
    
    prompt = f"""
    You are an expert translator and Agama Shastra scholar.
    
    INPUT CONTEXT:
    Chat History:
    {history_text}
    
    Current User Query: {query}
    
    INSTRUCTIONS:
    1. **Analyze Intent**: Does the user need specific information about Agama Shastra, rituals, architecture, or philosophy?
       - YES -> needs_context = true
       - NO (Greetings, "How are you", "Thank you", General questions) -> needs_context = false
    
    2. **Optimize Query** (Only if needs_context is true):
       - Translate Hindi/Hinglish to English.
       - Resolve "it/that" references using history.
       - Expand with Sanskrit terms (e.g., "Base" -> "Adhisthana").
    
    3. **Output JSON**:
    {{
        "optimized_query": "The optimized English search query (or original if no context needed)",
        "needs_context": true/false
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Optimization failed: {e}")
        return {"optimized_query": query, "needs_context": True}

def format_context(results: List[Dict]) -> tuple:
    if not results:
        return "No relevant context found.", [], ""
    
    display_formatted = ""
    citation_list = []
    numbered_context = ""
    
    for idx, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        score = result.get('relevance_score', 0)
        text = result.get('text', '')
        
        citation_parts = []
        if 'book_name' in metadata:
            citation_parts.append(metadata['book_name'])
        if 'chapter_number' in metadata:
            citation_parts.append(f"Ch. {metadata['chapter_number']}")
        
        citation_text = " • ".join(citation_parts) if citation_parts else f"Source {idx}"
        citation_list.append(f"[{idx}] {citation_text}")
        
        # HTML friendly format for the frontend to render
        display_formatted += f"<div class='context-item'><strong>[{idx}] {citation_text}</strong> (Relevance: {score:.3f})<br/>{text[:400]}...</div>"
        
        numbered_context += f"[{idx}] {citation_text}\n{text}\n\n"
    
    return display_formatted, citation_list, numbered_context

def generate_gemini_response(model, query: str, context: str, chat_history: List[Dict], citation_list: List[str] = None) -> str:
    history_text = ""
    if chat_history:
        for msg in chat_history[-5:]:
            role = msg.get('role', '').capitalize()
            content = msg.get('content', '')
            history_text += f"{role}: {content}\n\n"
    
    is_first_message = len(chat_history) == 0
    
    citation_instruction = ""
    if citation_list:
        citation_instruction = f"""
4. **CITATIONS**:
   - When using information from the context, cite the source using [1], [2], etc.
   - Place citations immediately after the relevant statement.
   - At the END of your response, add a "References:" section listing all citations used.
   - Available sources:
{chr(10).join(f"     {cite}" for cite in citation_list)}
   - Example: "The temple base is called Adhisthana [1]."
   - Then at the end: 
   
   **References:**
   [1] Source Name • Ch. X
"""
    
    prompt = f"""You are Shastra Guru, an expert scholar developed by Shastra Life.

CONTEXT FROM SHASTRA:
{context if context else "No specific Shastra context provided."}

CONVERSATION HISTORY:
{history_text if history_text else "(This is the start of the conversation)"}

USER INPUT: {query}

INSTRUCTIONS:

1. **IDENTITY**:
   - You are Shastra Guru, developed by Shastra Life.
   - NEVER mention Google/Gemini.
   - {"Introduce yourself ONLY in your first response." if is_first_message else "DO NOT introduce yourself again - you already did in the first message. Continue the conversation naturally."}

2. **LANGUAGE DETECTION & RESPONSE**:
   - Detect the language of the user's query carefully:
     * If query is in ENGLISH (pure English words) → Respond in ENGLISH
     * If query is in HINGLISH (mix of Hindi + English, Roman script) → Respond in HINGLISH
     * If query is in HINDI (Devanagari script) → Respond in HINDI
   - Match the user's language EXACTLY. This is critical.

3. **Response Style**:
   - If this is a greeting/general question: Answer warmly and naturally.
   - If this is a domain question: Use the provided CONTEXT.
   - Format your response with Markdown (bold, lists, etc.) for readability.

4. **Domain Questions**:
   - Use ONLY the provided Shastra excerpts.
   - Define Sanskrit terms in simple language.
   - If no context is available for a specific question, politely say so.

{citation_instruction}

Answer:"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # If citations exist and weren't already added by the model, append them
        if citation_list and "**References:**" not in response_text and "References:" not in response_text:
            response_text += "\n\n---\n\n**References:**\n"
            for cite in citation_list:
                response_text += f"{cite}\n"
        
        return response_text
    except Exception as e:
        return f"Error generating response: {e}"

# -----------------------------------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    # Initialize retriever on startup
    get_retriever()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # 1. Validate API Key
    api_key = request.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
    
    model = get_model(api_key)
    if not model:
        raise HTTPException(status_code=500, detail="Failed to initialize AI model")
    
    retriever = get_retriever()
    if not retriever:
        raise HTTPException(status_code=500, detail="Retriever system is not ready")

    # 2. Optimize & Route
    optimization_result = optimize_query(model, request.message, request.history)
    search_query = optimization_result.get("optimized_query", request.message)
    needs_context = optimization_result.get("needs_context", True)
    
    context_text = ""
    context_display = ""
    citation_list = []
    
    # 3. Retrieve
    if needs_context:
        try:
            results = retriever.retrieve_with_reranking(
                search_query,
                n_results=5,
                initial_k=15
            )
            context_display, citation_list, numbered_context = format_context(results)
            context_text = numbered_context
        except Exception as e:
            print(f"Retrieval error: {e}")
            # Continue without context if retrieval fails
            pass
            
    # 4. Generate
    response_text = generate_gemini_response(
        model, 
        request.message, 
        context_text, 
        request.history, 
        citation_list
    )
    
    return ChatResponse(
        response=response_text,
        context=context_display if needs_context else None,
        citations=citation_list if needs_context else []
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
