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
from src.web.prompts.templates import get_optimization_prompt, get_response_prompt
from typing import List, Dict, Any
import json

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Agama Shastra Expert",
    page_icon="assets/guru_icon.svg",
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
        text-align: left;
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
    """Optimize query using chat history for better retrieval with enhanced context awareness"""
    
    # Enhanced chat history processing
    if not chat_history:
        history_text = "No prior history."
        conversation_summary = "This is the first message in the conversation."
    else:
        # Use last 5 messages for better context (increased from 3)
        recent_messages = chat_history[-5:]
        
        # Build structured history
        history_text = ""
        topics_discussed = []
        last_assistant_response = None
        
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_text += f"{role}: {content}\\n"
            
            # Track topics and last assistant response
            if role == 'assistant':
                last_assistant_response = content
            elif role == 'user':
                # Extract potential topics (simple heuristic)
                topics_discussed.append(content[:100])  # First 100 chars as topic indicator
        
        # Create conversation summary
        conversation_summary = f"""
Recent conversation:
{history_text}

Last assistant response: {last_assistant_response[:200] if last_assistant_response else 'None'}
Topics discussed: {len(topics_discussed)} previous questions
"""
    
    prompt = get_optimization_prompt(conversation_summary, query)
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Optimization failed: {e}")
        # Default to searching in knowledge base (conservative approach)
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
    """Generate response using Gemini with enhanced context grounding, citation system, and quality controls"""
    
    # Build conversation history with better structure
    history_text = ""
    previous_topics = []
    last_user_query = None
    last_assistant_response = None
    
    if chat_history:
        for msg in chat_history[-5:]:  # Last 5 messages for context
            role = msg.get('role', '').capitalize()
            content = msg.get('content', '')
            history_text += f"{role}: {content}\n\n"
            
            if role == 'User':
                last_user_query = content
                previous_topics.append(content[:100])
            elif role == 'Assistant':
                last_assistant_response = content[:300]  # First 300 chars
    
    is_first_message = len(chat_history) == 0
    
    # Enhanced citation instruction
    citation_instruction = ""
    if citation_list:
        citation_instruction = f"""
5. **CITATIONS - CRITICAL**:
   **When to cite:**
   - Cite EVERY factual statement derived from the context
   - Cite immediately after the claim, before any elaboration
   - Even when paraphrasing, cite the source
   
   **How to cite:**
   - Use [1], [2], [3] format
   - Place citation right after the statement: "The gopuram is a tower [1]."
   - If multiple sources support a claim: "Temples face east [1][2]."
   - If quoting directly, use quotes: "The temple is called 'house of god' [1]."
   
   **Available sources:**
{chr(10).join(f"     {cite}" for cite in citation_list)}
   
   **References section:**
   - At the END of your response, add a "**References:**" section
   - List all citations you used
   - Format:
   
   **References:**
   [1] Source Name • Ch. X
   [2] Source Name • Ch. Y
"""
    
    # Determine if this is a follow-up question
    is_follow_up = len(previous_topics) > 0
    
    prompt = get_response_prompt(context, history_text, query, is_first_message, citation_instruction, is_follow_up)
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Fallback: If citations exist but weren't added by the model, append them
        if citation_list and "**References:**" not in response_text and "References:" not in response_text:
            response_text += "\n\n---\n\n**References:**\n"
            for cite in citation_list:
                response_text += f"{cite}\n"
        
        return response_text
    except Exception as e:
        return f"I apologize, but I encountered an error while generating a response: {e}\n\nPlease try rephrasing your question or ask something else."


def main():
    # Header
    st.markdown('<div class="main-header">Agama Shastra Expert</div>', unsafe_allow_html=True)
    st.info("**Under Development** - We are working on making response better.")
    
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
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            avatar = "assets/user_icon.svg" if message["role"] == "user" else "assets/guru_icon.svg"
            with st.chat_message(message["role"], avatar=avatar):
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
        
        with st.chat_message("user", avatar="assets/user_icon.svg"):
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
        
        with st.chat_message("assistant", avatar="assets/guru_icon.svg"):
            st.markdown(response)
            if show_context and needs_context:
                with st.expander("📖 Retrieved Shastra Excerpts"):
                    st.markdown(context_display)
        
        st.rerun()


if __name__ == "__main__":
    main()
