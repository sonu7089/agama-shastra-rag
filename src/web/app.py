import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from src.core.retriever import BookRetriever
from typing import List, Dict

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


def format_context_display(results: List[Dict]) -> str:
    """Format retrieved context for display"""
    if not results:
        return "No relevant context found."
    
    formatted = ""
    for idx, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        score = result.get('relevance_score', 0)
        
        formatted += f"**Context {idx}** (Relevance: {score:.3f})\n"
        
        # Add metadata tags
        tags = []
        if 'book_name' in metadata:
            tags.append(f"📚 {metadata['book_name']}")
        if 'chapter_number' in metadata:
            tags.append(f"📖 Ch. {metadata['chapter_number']}")
        if 'chunk_type' in metadata:
            tags.append(f"🏷️ {metadata['chunk_type']}")
        
        if tags:
            formatted += " • ".join(tags) + "\n"
        
        formatted += f"\n{result['text'][:500]}{'...' if len(result['text']) > 500 else ''}\n\n"
        formatted += "---\n\n"
    
    return formatted


def generate_response_with_gemini(model, query: str, context: str, chat_history: List[Dict]) -> str:
    """Generate response using Gemini with wise guru persona and citation system"""
    
    # Build conversation history
    history_text = ""
    if chat_history:
        for msg in chat_history[-7:]:  # Last 7 messages for better context continuity
            role = msg['role'].capitalize()
            content = msg['content']
            history_text += f"{role}: {content}\n\n"
    
    # Build prompt with wise guru persona
    prompt = f"""You are a revered guru of Agama Shastra, with over 70 years of deep study and practice. You possess profound wisdom accumulated through decades of contemplation, teaching, and living the principles of the sacred texts.

PERSONA & TONE:
- Warm, wise, and genuinely caring about the seeker's spiritual growth
- Conversational like a grandfather sharing wisdom
- Patient, encouraging, never condescending

CRITICAL KNOWLEDGE CONSTRAINT:
- You may ONLY share knowledge present in the Shastra excerpts provided below
- DO NOT use external knowledge about Agama Shastra not in the retrieved Shastra
- If the Shastra does not contain information to answer the question, clearly state: "Our Shastra does not contain specific information about this topic."
- You may use general human wisdom for conversation, but for Agama Shastra content, rely EXCLUSIVELY on provided Shastra

TERMINOLOGY:
- Always refer to retrieved texts as "the Shastra" or "our Shastra" (never "context" or "documents")
- Use phrases like "According to the Shastra [1]...", "The Shastra teaches..."

CITATION SYSTEM (MANDATORY):
- Use inline citations [1], [2], [3] when referencing specific teachings
- Each number corresponds to a Context number in the Shastra below
- At the END, include "References:" section with source (book name, chapter)
- Example: "The garbhagriha must face east [1]."
  
  References:
  [1] Kamika Agama, Chapter 12

RESPONSE STYLE (CRITICAL):
- Get STRAIGHT to the point - answer the question immediately in the first sentence
- Be concise and direct - no lengthy introductions or preambles
- Avoid phrases like "Let me share..." or "Dear seeker..." - just answer directly
- Start with: "According to the Shastra [1]..." or similar, then give the answer
- After the direct answer, you may provide brief supporting details if helpful
- Keep responses focused and avoid repetition
- Use Sanskrit terms when appropriate with brief explanations
- End with the References section

OUT-OF-SCOPE HANDLING:
- If the question is not about Agama Shastra, politely redirect to the topic
- If the Shastra excerpts provided are not relevant to answer the question, respond with:
  "The knowledge currently available in our Shastra does not contain specific information to answer this question. We are continuously expanding our sacred texts and knowledge base. Please check back soon, and our guru will be able to guide you on this topic."
- Do not make up information or use external knowledge

---

Previous Conversation:
{history_text}

Retrieved Shastra Excerpts:
{context}

---

Seeker's Question: {query}

Answer directly:"""
    
    try:
        import time
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if 'rate limit' in error_str or 'quota' in error_str or '429' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return "⏳ **Rate limit reached.** The free tier has usage limits. Please wait a moment and try again, or consider upgrading your API plan for higher limits."
                else:
                    # Other errors
                    return f"Error generating response: {e}"
        
        return "Failed to generate response after multiple retries."
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
        
        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Enter your Gemini API key"
        )
        
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
            # Build filter
            filter_by = {}
            if filter_book != "All Texts":
                filter_by['book_name'] = filter_book
            if filter_type != "All Types":
                filter_by['chunk_type'] = filter_type
            
            filter_by = filter_by if filter_by else None
            
            # Use intelligent retrieval with reranking
            results = retriever.retrieve_with_reranking(
                prompt,
                n_results=n_results,
                initial_k=15,  # Retrieve 15 candidates, rerank to top n_results
                filter_by=filter_by
            )
            
            context_text = retriever.get_context_for_rag(
                prompt,
                n_results=n_results,
                filter_by=filter_by
            )
            
            context_display = format_context_display(results)
        
        # Generate response
        with st.spinner("Sharing wisdom..."):
            model = initialize_gemini(api_key)
            if model:
                response = generate_response_with_gemini(
                    model,
                    prompt,
                    context_text,
                    st.session_state.messages
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
            if show_context:
                with st.expander("📖 Retrieved Shastra Excerpts"):
                    st.markdown(context_display)
        
        st.rerun()


if __name__ == "__main__":
    main()
