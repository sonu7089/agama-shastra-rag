import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from retriever import BookRetriever
from typing import List, Dict, Any
import time
import json

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Agama Shastra Guru",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* General Reset */
    .stApp {
        background-color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ----------------------------------------------------------------------
       FIXED HEADER
       ---------------------------------------------------------------------- */
    /* Target the first block container to act as our fixed header */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: #ffffff;
        z-index: 99999;
        padding: 1rem 2rem;
        border-bottom: 2px solid #000000;
        height: 80px;
        align-items: center;
    }

    /* Adjust main content to not be hidden behind header */
    .main .block-container {
        padding-top: 100px !important; /* Height of header + padding */
        padding-bottom: 100px !important; /* Space for input */
        max-width: 900px;
    }

    /* Header Text Styling */
    .header-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #000000;
        white-space: nowrap;
    }
    
    .header-warning {
        font-size: 0.85rem;
        color: #ef4444;
        text-align: center;
        width: 100%;
    }

    /* New Chat Button Styling */
    div[data-testid="stButton"] button {
        border: 2px solid #000000;
        border-radius: 0; /* Sharp corners */
        background-color: #ffffff;
        color: #000000;
        font-weight: 500;
        padding: 0.25rem 1rem;
        transition: all 0.2s;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #000000;
        color: #ffffff;
        border-color: #000000;
    }

    /* ----------------------------------------------------------------------
       CHAT MESSAGES
       ---------------------------------------------------------------------- */
    /* Remove default background and padding from message containers */
    .stChatMessage {
        background-color: transparent;
        padding: 1rem 0;
    }

    /* Avatar */
    .stChatMessage .avatar {
        border: 2px solid #000000;
        border-radius: 0 !important; /* Square avatars */
    }

    /* Message Content Box */
    .stChatMessageContent {
        border: 2px solid #000000 !important;
        border-radius: 0 !important; /* Sharp corners */
        background-color: #ffffff !important;
        padding: 1.5rem !important;
        box-shadow: 4px 4px 0px #000000 !important; /* Neo-brutalist shadow */
        color: #000000 !important;
    }

    /* User Message Specifics */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse;
    }
    
    /* Assistant Message Specifics */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        /* Default is fine */
    }

    /* ----------------------------------------------------------------------
       INPUT AREA
       ---------------------------------------------------------------------- */
    .stChatInputContainer {
        padding-bottom: 2rem;
        padding-top: 1rem;
        background: #ffffff;
        border-top: 2px solid #000000;
    }
    
    .stChatInputContainer textarea {
        border: 2px solid #000000 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }
    
    .stChatInputContainer button {
        border: none !important;
        color: #000000 !important;
    }

</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# BACKEND LOGIC (Cached)
# -----------------------------------------------------------------------------

@st.cache_resource
def initialize_retriever(db_path: str = "chroma_db"):
    """Initialize the retriever (cached)"""
    try:
        retriever = BookRetriever(db_path=db_path)
        return retriever
    except Exception as e:
        st.error(f"Failed to initialize retriever: {e}")
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


def optimize_query_for_retrieval(model, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
    """
    Optimize the user query and determine if context is needed.
    Returns JSON: {"optimized_query": str, "needs_context": bool}
    """
    if not chat_history:
        history_text = "No prior history."
    else:
        history_text = ""
        for msg in chat_history[-3:]:
            role = msg['role']
            content = msg['content']
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


def format_context_display(results: List[Dict]) -> tuple:
    """
    Format retrieved context for display and citation.
    Returns: (display_text, citation_list, numbered_context_for_llm)
    """
    if not results:
        return "No relevant context found.", [], ""
    
    display_formatted = ""
    citation_list = []
    numbered_context = ""
    
    for idx, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        score = result.get('relevance_score', 0)
        text = result.get('text', '')
        
        # Build citation reference
        citation_parts = []
        if 'book_name' in metadata:
            citation_parts.append(metadata['book_name'])
        if 'chapter_number' in metadata:
            citation_parts.append(f"Ch. {metadata['chapter_number']}")
        
        citation_text = " • ".join(citation_parts) if citation_parts else f"Source {idx}"
        citation_list.append(f"[{idx}] {citation_text}")
        
        # Display format (for expander)
        display_formatted += f"**[{idx}]** {citation_text} (Relevance: {score:.3f})\n"
        display_formatted += f"\n{text[:400]}...\n\n"
        display_formatted += "---\n\n"
        
        # Numbered context for LLM (full text with citation marker)
        numbered_context += f"[{idx}] {citation_text}\n{text}\n\n"
    
    return display_formatted, citation_list, numbered_context


def generate_response_with_gemini(model, query: str, context: str, chat_history: List[Dict], citation_list: List[str] = None) -> str:
    """Generate response using Gemini with inline citations"""
    
    history_text = ""
    if chat_history:
        for msg in chat_history[-5:]:
            role = msg['role'].capitalize()
            content = msg['content']
            history_text += f"{role}: {content}\n\n"
    
    # Check if this is the first message (no history)
    is_first_message = len(chat_history) == 0
    
    # Build citation instruction
    citation_instruction = ""
    if citation_list:
        citation_instruction = f"""
4. **CITATIONS**:
   - When using information from the context, cite the source using [1], [2], etc.
   - Place citations immediately after the relevant statement.
   - Available sources:
{chr(10).join(f"     {cite}" for cite in citation_list)}
   - Example: "The temple base is called Adhisthana [1]."
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

2. **Response Style**:
   - If this is a greeting/general question: Answer warmly and naturally.
   - If this is a domain question: Use the provided CONTEXT.
   - ALWAYS answer in the SAME LANGUAGE as the user's input.

3. **Domain Questions**:
   - Use ONLY the provided Shastra excerpts.
   - Define Sanskrit terms in simple language.
   - If no context is available for a specific question, politely say so.

{citation_instruction}

Answer:"""
    
    try:
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                return "I apologize, but I am unable to generate a response at this moment due to high traffic. Please try again."
        
    except Exception as e:
        return f"Error: {e}"


def main():
    # Session State
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # ----------------------------------------------------------------------
    # HEADER (Fixed via CSS)
    # ----------------------------------------------------------------------
    # We use columns here, and the CSS above targets this specific block to fix it to the top
    header_col1, header_col2, header_col3 = st.columns([2, 4, 1], gap="small", vertical_alignment="center")
    
    with header_col1:
        st.markdown('<div class="header-title">Agama Shastra Guru</div>', unsafe_allow_html=True)
    
    with header_col2:
        st.markdown('<div class="header-warning">We are working on improving our responses</div>', unsafe_allow_html=True)
        
    with header_col3:
        if st.button("new chat", key="new_chat_btn", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # ----------------------------------------------------------------------
    # SIDEBAR (Hidden by default but accessible)
    # ----------------------------------------------------------------------
    with st.sidebar:
        st.title("Settings")
        api_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
        db_path = st.text_input("Database Path", value="chroma_db")
        n_results = st.slider("Context Sources", 1, 10, 5)
        st.divider()
        retriever = initialize_retriever(db_path)
        if retriever:
            st.success("Database Connected")
        else:
            st.error("Database Disconnected")

    # ----------------------------------------------------------------------
    # CHAT INTERFACE
    # ----------------------------------------------------------------------
    for message in st.session_state.messages:
        role = message["role"]
        # Use simple text avatars or icons if files are missing, but here we assume assets exist or fallback
        avatar_icon = "👤" if role == "user" else "🕉️"
        
        with st.chat_message(role, avatar=avatar_icon):
            st.markdown(message["content"])
            if role == "assistant" and "context" in message and message["context"]:
                with st.expander("View Sources & References"):
                    st.markdown(message["context"])

    # ----------------------------------------------------------------------
    # INPUT AREA
    # ----------------------------------------------------------------------
    if prompt := st.chat_input("User types query here!!!"):
        if not api_key:
            st.warning("Please enter your Gemini API Key in the sidebar.")
            return

        # User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Processing
        model = initialize_gemini(api_key)
        if not model:
            st.error("Invalid API Key")
            return

        with st.spinner("Thinking..."):
            # 1. Optimize & Route
            optimization_result = optimize_query_for_retrieval(model, prompt, st.session_state.messages[:-1])
            search_query = optimization_result.get("optimized_query", prompt)
            needs_context = optimization_result.get("needs_context", True)
            
            context_text = ""
            context_display = ""
            citation_list = []
            
            # 2. Retrieve (Only if needed)
            if needs_context:
                filter_by = {}
                results = retriever.retrieve_with_reranking(
                    search_query,
                    n_results=n_results,
                    initial_k=15,
                    filter_by=filter_by if filter_by else None
                )
                # Unpack the tuple: display, citations, numbered_context
                context_display, citation_list, numbered_context = format_context_display(results)
                # Use numbered context for LLM
                context_text = numbered_context
            
            # 3. Generate with citations
            response = generate_response_with_gemini(model, prompt, context_text, st.session_state.messages, citation_list)

        # Assistant Message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response,
            "context": context_display if needs_context else None,
            "citations": citation_list if needs_context else []
        })
        
        with st.chat_message("assistant", avatar="🕉️"):
            st.markdown(response)
            if needs_context and context_display:
                with st.expander("View Sources & References"):
                    st.markdown(context_display)

if __name__ == "__main__":
    main()
