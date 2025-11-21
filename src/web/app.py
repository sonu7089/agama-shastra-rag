import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

from src.core.retriever import BookRetriever
from typing import List, Dict, Any
import json

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Agama Shastra Guru",
    page_icon="🕉️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #7f8c8d;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_retriever(db_path: str = "data/chroma_db"):
    """Initialize the retriever (cached)"""
    try:
        retriever = BookRetriever(db_path=db_path)
        return retriever
    except Exception as e:
        st.error(f"Failed to initialize retriever: {e}")
        st.info("Please run indexer.py first to create the index.")
        return None


@st.cache_resource
def initialize_gemini(api_key: str):
    """Initialize Gemini API (cached)"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model
    except Exception as e:
        st.error(f"Failed to initialize Gemini API: {e}")
        return None


def optimize_query(model, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
    """Optimize query using chat history for better retrieval"""
    if not chat_history:
        history_text = "No prior history."
    else:
        history_text = ""
        for msg in chat_history[-3:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_text += f"{role}: {content}\\n"
    
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
    
    2. **Generate Output**:
       - If needs_context = false:
         * Provide a warm, polite, and helpful "direct_response" to the user's input.
         * "optimized_queries" can be empty.
       - If needs_context = true:
         * "direct_response" should be null.
         * Generate 3 diverse search queries in "optimized_queries":
           1. A specific keyword-based query.
           2. A conceptual/semantic query.
           3. A query resolving any "it/that" references and translating terms to English/Sanskrit.
    
    3. **Output JSON**:
    {{
        "needs_context": true/false,
        "direct_response": "Your response here if no context needed, else null",
        "optimized_queries": ["query 1", "query 2", "query 3"]
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Optimization failed: {e}")
        return {"needs_context": True, "optimized_queries": [query], "direct_response": None}


def format_context(results: List[Dict]) -> tuple:
    """Format retrieved context for display and generation"""
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
        
        # Markdown format for Streamlit
        display_formatted += f"**[{idx}] {citation_text}** (Relevance: {score:.3f})\n\n"
        display_formatted += f"{text[:500]}{'...' if len(text) > 500 else ''}\n\n---\n\n"
        
        numbered_context += f"[{idx}] {citation_text}\n{text}\n\n"
    
    return display_formatted, citation_list, numbered_context


def generate_response_with_gemini(model, query: str, context: str, chat_history: List[Dict], citation_list: List[str] = None) -> str:
    """Generate response using Gemini with wise guru persona and citation system"""
    
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
            response_text += "\\n\\n---\\n\\n**References:**\\n"
            for cite in citation_list:
                response_text += f"{cite}\\n"
        
        return response_text
    except Exception as e:
        return f"Error generating response: {e}"


def main():
    # Header
    st.markdown('<div class="main-header">🕉️ Agama Shastra Guru</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Seek wisdom from the ancient sacred texts</div>', unsafe_allow_html=True)
    st.info("🚧 **Under Development** - We are continuously expanding our knowledge base to serve you better.")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key loading
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ GEMINI_API_KEY not found in .env file")
            st.stop()
        
        # Database path
        db_path = st.text_input(
            "Database Path",
            value="data/chroma_db",
            help="Path to ChromaDB database"
        )
        
        # Number of context chunks
        n_results = st.slider(
            "Shastra Excerpts to Retrieve",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of relevant excerpts from Shastra"
        )
        
        st.markdown("---")
        
        # Initialize retriever
        retriever = initialize_retriever(db_path)
        
        if retriever:
            st.success("✅ Connected to Shastra")
            
            # Show available books
            books = retriever.get_available_books()
            if books:
                with st.expander("📚 Available Texts"):
                    for book in books:
                        st.text(f"• {book}")
            
            st.markdown("---")
            
            # Filter options
            with st.expander("🔍 Filter Options"):
                filter_book = st.selectbox(
                    "Filter by Text",
                    options=["All Texts"] + books,
                    index=0
                )
                
                filter_type = st.selectbox(
                    "Filter by Type",
                    options=[
                        "All Types",
                        "chapter_summary",
                        "section_content",
                        "historical_figure",
                        "historical_event",
                        "geographic_location",
                        "terminology",
                        "quotation",
                        "reference_note"
                    ],
                    index=0
                )
        else:
            st.error("❌ Cannot connect to Shastra database")
            st.info("Please run indexer.py first to create the index.")
            return
        
        st.markdown("---")
        
        # Show context toggle
        show_context = st.checkbox(
            "Show Retrieved Excerpts",
            value=True,
            help="Display the Shastra excerpts used for responses"
        )
        
        # Clear chat button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Main chat interface
    st.subheader("💬 Conversation")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show context if available
                if message["role"] == "assistant" and "context" in message and show_context:
                    with st.expander("📖 Retrieved Shastra Excerpts"):
                        st.markdown(message["context"])
    
    # Chat input
    if prompt := st.chat_input("Ask your question about Agama Shastra..."):
        if not api_key:
            st.error("Please enter your Gemini API key in the sidebar")
            return
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Retrieve context with intelligent reranking
        with st.spinner("Consulting the Shastra..."):
            # Initialize model for query optimization
            model = initialize_gemini(api_key)
            
            # Optimize query based on history
            if model:
                optimization_result = optimize_query(model, prompt, st.session_state.messages)
                needs_context = optimization_result.get("needs_context", True)
                direct_response = optimization_result.get("direct_response")
                search_queries = optimization_result.get("optimized_queries", [prompt])
            else:
                search_queries = [prompt]
                needs_context = True
                direct_response = None
            
            context_display = ""
            citation_list = []
            context_text = ""
            
            if not needs_context and direct_response:
                # Short-circuit: Use direct response
                response = direct_response
                # We skip the second LLM call entirely
            else:
                # Proceed with RAG
                if needs_context:
                    # Build filter
                    filter_by = {}
                    if filter_book != "All Texts":
                        filter_by['book_name'] = filter_book
                    if filter_type != "All Types":
                        filter_by['chunk_type'] = filter_type
                    
                    filter_by = filter_by if filter_by else None
                    
                    # Use multi-query retrieval for richer content
                    # This fetches results for all 3 generated queries
                    results = retriever.multi_query_retrieve(
                        queries=search_queries,
                        n_results_per_query=3,  # 3 results per query * 3 queries = ~9 potential chunks
                        filter_by=filter_by
                    )
                    
                    context_display, citation_list, context_text = format_context(results)
                else:
                    context_text = ""
                    context_display = "No context needed for this query."
                
                # Generate response (Second LLM call)
                with st.spinner("Sharing wisdom..."):
                    if model:
                        response = generate_response_with_gemini(
                            model,
                            prompt,
                            context_text,
                            st.session_state.messages,
                            citation_list
                        )
                    else:
                        response = "Failed to initialize Gemini API. Please check your API key."
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "context": context_display
        })
        
        with st.chat_message("assistant"):
            st.markdown(response)
            if show_context and needs_context:
                with st.expander("📖 Retrieved Shastra Excerpts"):
                    st.markdown(context_display)
        
        st.rerun()


if __name__ == "__main__":
    main()
