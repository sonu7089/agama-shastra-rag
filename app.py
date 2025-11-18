import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from retriever import BookRetriever
from typing import List, Dict

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Book RAG Chat",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .context-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1E88E5;
        margin: 0.5rem 0;
    }
    .metadata-tag {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_retriever(db_path: str = "chroma_db"):
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
        model = genai.GenerativeModel('gemini-2.5-pro')
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
    """Generate response using Gemini with context"""
    
    # Build conversation history
    history_text = ""
    if chat_history:
        for msg in chat_history[-5:]:  # Last 5 messages for context
            role = msg['role'].capitalize()
            content = msg['content']
            history_text += f"{role}: {content}\n"
    
    # Build prompt
    prompt = f"""You are a knowledgeable assistant helping users understand and explore book content. 
You have access to relevant context from the books to answer questions accurately.

Previous Conversation:
{history_text}

Retrieved Context:
{context}

User Question: {query}

Instructions:
- Answer the question based primarily on the provided context
- If the context contains relevant information, cite the source (book name, chapter)
- Be specific and detailed in your answers
- If the context doesn't contain enough information, say so and provide what you can
- Maintain a helpful and conversational tone
- For historical facts, dates, or specific terms, be precise
- If you mention Sanskrit/Hindi terms, include transliterations if available in the context

Answer:"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating response: {e}"


def main():
    # Header
    st.markdown('<div class="main-header">📚 Book RAG Chat Interface</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ask questions about your books and get AI-powered answers with context</div>', unsafe_allow_html=True)
    
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
            value="chroma_db",
            help="Path to ChromaDB database"
        )
        
        # Number of context chunks
        n_results = st.slider(
            "Context Chunks",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of relevant chunks to retrieve"
        )
        
        st.markdown("---")
        
        # Initialize retriever
        retriever = initialize_retriever(db_path)
        
        if retriever:
            st.success("✅ Retriever initialized")
            
            # Show available books
            st.subheader("📚 Available Books")
            books = retriever.get_available_books()
            if books:
                for book in books:
                    st.text(f"• {book}")
            else:
                st.info("No books indexed yet")
            
            st.markdown("---")
            
            # Filter options
            st.subheader("🔍 Filters")
            
            filter_book = st.selectbox(
                "Filter by Book",
                options=["All Books"] + books,
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
            st.error("❌ Retriever not initialized")
            return
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'show_context' not in st.session_state:
        st.session_state.show_context = True
    
    # Main chat interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Chat")
        
        # Display chat messages
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
                    # Show context if available
                    if message["role"] == "assistant" and "context" in message and st.session_state.show_context:
                        with st.expander("📋 Retrieved Context"):
                            st.markdown(message["context"])
        
        # Chat input
        if prompt := st.chat_input("Ask a question about your books..."):
            if not api_key:
                st.error("Please enter your Gemini API key in the sidebar")
                return
            
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Retrieve context
            with st.spinner("Retrieving relevant context..."):
                # Build filter
                filter_by = {}
                if filter_book != "All Books":
                    filter_by['book_name'] = filter_book
                if filter_type != "All Types":
                    filter_by['chunk_type'] = filter_type
                
                filter_by = filter_by if filter_by else None
                
                # Retrieve
                results = retriever.retrieve_with_context(
                    prompt,
                    n_results=n_results,
                    filter_by=filter_by
                )
                
                context_text = retriever.get_context_for_rag(
                    prompt,
                    n_results=n_results,
                    filter_by=filter_by
                )
                
                context_display = format_context_display(results)
            
            # Generate response
            with st.spinner("Generating response..."):
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
                if st.session_state.show_context:
                    with st.expander("📋 Retrieved Context"):
                        st.markdown(context_display)
            
            st.rerun()
    
    with col2:
        st.subheader("ℹ️ Information")
        
        # Statistics
        if retriever:
            total_docs = retriever.collection.count()
            st.metric("Total Documents", total_docs)
            st.metric("Books Indexed", len(retriever.get_available_books()))
        
        st.markdown("---")
        
        # Show context toggle
        st.session_state.show_context = st.checkbox(
            "Show Retrieved Context",
            value=st.session_state.show_context
        )
        
        st.markdown("---")
        
        # Tips
        st.subheader("💡 Tips")
        st.markdown("""
        - Ask specific questions for better results
        - Use filters to narrow down search
        - Mention specific chapters or topics
        - Ask about historical figures, events, or terminology
        - Request summaries or explanations
        """)
        
        st.markdown("---")
        
        # Example queries
        st.subheader("🎯 Example Queries")
        example_queries = [
            "What are the main themes discussed?",
            "Who are the key historical figures?",
            "Explain the term [specific term]",
            "What happened in chapter [X]?",
            "Summarize the main arguments",
        ]
        
        for query in example_queries:
            if st.button(query, key=f"example_{query}", use_container_width=True):
                st.session_state.example_query = query


if __name__ == "__main__":
    main()
