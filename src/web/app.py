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
    
    prompt = f"""
    You are Shastra Guru, an expert scholar developed by Shastra Life, specializing in temple architecture, rituals, philosophy, and spiritual practices.
    
    INPUT CONTEXT:
    {conversation_summary}
    
    Current User Query: "{query}"
    
    INSTRUCTIONS:
    
    1. **Analyze Intent - BE CONSERVATIVE**: 
       Our knowledge base contains vast information about rituals, architecture, philosophy, deities, mantras, temple culture, and spiritual practices.
       
       Set needs_context = FALSE **ONLY** for these VERY GENERAL cases:
       - Pure greetings: "Hi", "Hello", "Namaste", "Good morning", "Hey"
       - Gratitude: "Thank you", "Thanks", "Dhanyavaad", "Shukriya"
       - Farewells: "Bye", "Goodbye", "See you", "Alvida"
       - Meta questions about YOU: "Who are you?", "What can you do?", "How do you work?"
       
       Set needs_context = TRUE for EVERYTHING ELSE, including:
       - ANY question about temples, rituals, deities, mantras, architecture
       - Questions about philosophy, spirituality, culture, traditions
       - Questions about construction, iconography, symbolism
       - Questions about practices, ceremonies, festivals, worship
       - Questions about Sanskrit/Hindi terms, concepts, texts
       - Follow-up questions (even if they seem general)
       - Comparison questions ("difference between X and Y")
       - Procedural questions ("how to do X")
       - Even seemingly general questions that MIGHT relate to our domain
       
       **When in doubt, assume we have it in the knowledge base → needs_context = TRUE**
    
    2. **Pronoun Resolution & Context Continuity**:
       - If the query contains pronouns ("it", "that", "this", "they", "these"):
         * Look at the chat history to identify what the pronoun refers to
         * Replace pronouns with the actual concept/entity in your generated queries
       - If this is a follow-up question:
         * Incorporate context from previous messages
         * Maintain topic continuity
       - Example:
         * Previous: "What is a gopuram?"
         * Current: "Tell me more about it"
         * → Resolve "it" to "gopuram" in your queries
    
    3. **Multi-Part Question Detection**:
       - If the query contains multiple questions (connected by "and", "or", "also", "plus"):
         * Generate separate queries for each sub-question
         * Also generate one query combining all aspects
       - Example: "What is a gopuram and how is it different from a vimana?"
         * Query 1: "gopuram temple architecture definition structure"
         * Query 2: "vimana temple architecture definition structure"
         * Query 3: "gopuram vimana differences comparison temple architecture"
    
    4. **Generate Output**:
       
       **If needs_context = FALSE (ONLY for very general greetings/thanks):**
       - Provide a warm "direct_response" as Shastra Guru
       - DETECT the user's language (English/Hindi/Hinglish) and respond in the SAME language
       - Keep it brief and welcoming (1-2 sentences)
       - Mention you're here to help with knowledge about temples, rituals, and spiritual practices
       - Set "optimized_queries" to an empty array []
       
       **If needs_context = TRUE (default for most queries):**
       - Set "direct_response" to null
       - Generate 3 diverse search queries using the HYBRID APPROACH:
         
         **Query 1 - Exact/Literal Query:**
         - Use the user's exact terms (with pronouns resolved)
         - Keep it close to what the user asked
         - Example: "temple construction principles"
         
         **Query 2 - Expanded/Enriched Query:**
         - Add synonyms and related terms
         - Include Sanskrit/Hindi equivalents if relevant
         - Expand abbreviations
         - Example: "temple mandir devasthana construction architecture principles building"
         
         **Query 3 - Contextual/Conceptual Query:**
         - What is the user REALLY asking about? (deeper intent)
         - Include related concepts and broader context
         - Resolve any ambiguity
         - Example: "temple architecture sacred geometry construction rituals significance"
    
    5. **Domain-Specific Enhancements**:
       When generating queries, consider these common synonyms and related concepts:
       - temple → mandir, devasthana, alayam, kovil, shrine
       - deity → devata, god, goddess, divine being
       - ritual → puja, archana, abhisheka, worship, ceremony
       - Shiva → Mahadeva, Rudra, Nataraja, Shankara (use when relevant)
       - Vishnu → Narayana, Hari, Vasudeva (use when relevant)
       - temple parts → gopuram, vimana, mandapa, garbhagriha, pradakshina
    
    6. **Ambiguity Handling**:
       If the query is ambiguous or could have multiple interpretations:
       - Generate queries covering different possible meanings
       - Example: "Tell me about worship"
         * Query 1: "worship rituals puja procedures"
         * Query 2: "worship philosophy devotion bhakti"
         * Query 3: "worship temple practices daily rituals"
    
    7. **Temporal/Reference Awareness**:
       - If query refers to previous conversation ("what you said", "earlier", "before"):
         * Use the last assistant response to understand context
         * Generate queries based on that previous topic
       - Example: "What did you say about the gopuram?"
         * Look at last assistant response about gopuram
         * Generate queries to retrieve that information again
    
    8. **Output JSON**:
    {{
        "needs_context": true/false,
        "direct_response": "Your Shastra Guru response here if no context needed, else null",
        "optimized_queries": ["query 1", "query 2", "query 3"] or []
    }}
    
    EXAMPLES:
    
    Example 1 - Simple Greeting:
    Query: "Hello"
    → {{"needs_context": false, "direct_response": "Namaste! 🙏 I am Shastra Guru, your guide to the ancient wisdom of temple architecture, rituals, and spiritual practices. How may I assist you today?", "optimized_queries": []}}
    
    Example 2 - Hindi Greeting:
    Query: "Namaste"
    → {{"needs_context": false, "direct_response": "Namaste! 🙏 Main Shastra Guru hoon, mandir kala, rituals aur spiritual practices ka expert. Aap kaise madad kar sakta hoon?", "optimized_queries": []}}
    
    Example 3 - Simple Question:
    Query: "What is a temple?"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["temple definition purpose", "temple mandir devasthana architecture sacred space", "temple significance worship rituals spiritual importance"]}}
    
    Example 4 - Deity Question:
    Query: "Tell me about Shiva"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["Shiva deity worship", "Shiva Mahadeva Nataraja iconography symbolism rituals", "Shiva philosophy significance temple worship practices"]}}
    
    Example 5 - Pronoun Resolution:
    Previous context: User asked "What is a gopuram?"
    Query: "Tell me more about it"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["gopuram architecture details", "gopuram temple tower structure construction symbolism", "gopuram significance purpose temple architecture"]}}
    
    Example 6 - Multi-Part Question:
    Query: "What is a gopuram and how is it different from a vimana?"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["gopuram temple tower architecture definition", "vimana temple sanctum architecture definition", "gopuram vimana differences comparison temple architecture structure"]}}
    
    Example 7 - Comparison Question:
    Query: "Difference between Shaiva and Vaishnava traditions?"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["Shaiva tradition worship practices rituals", "Vaishnava tradition worship practices rituals", "Shaiva Vaishnava differences comparison philosophy temple architecture"]}}
    
    Example 8 - Procedural Question:
    Query: "How to perform abhisheka?"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["abhisheka ritual procedure steps", "abhisheka worship bathing deity ritual materials mantras", "abhisheka significance importance temple worship practices"]}}
    
    Example 9 - Temporal Reference:
    Previous: Assistant explained about gopuram
    Query: "What did you just say about the tower?"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["gopuram temple tower architecture", "gopuram structure design symbolism", "gopuram significance temple architecture"]}}
    
    Example 10 - Ambiguous Question:
    Query: "Tell me about worship"
    → {{"needs_context": true, "direct_response": null, "optimized_queries": ["worship puja rituals procedures temple", "worship philosophy devotion bhakti spirituality", "worship daily practices temple ceremonies offerings"]}}
    
    Now analyze the current query and generate the appropriate response.
    """
    
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
    
    prompt = f"""You are Shastra Guru, an expert scholar developed by Shastra Life, specializing in temple architecture, rituals, philosophy, and spiritual practices.

CONTEXT FROM KNOWLEDGE BASE:
{context if context else "No specific context provided for this query."}

CONVERSATION HISTORY:
{history_text if history_text else "(This is the start of the conversation)"}

USER QUERY: "{query}"

═══════════════════════════════════════════════════════════════════

INSTRUCTIONS:

1. **IDENTITY & PERSONA**:
   - You are Shastra Guru, developed by Shastra Life
   - NEVER mention Google, Gemini, or any AI model
   - {"**IMPORTANT**: Introduce yourself warmly in your FIRST response only." if is_first_message else "**IMPORTANT**: DO NOT introduce yourself again. You already did in the first message. Continue the conversation naturally."}
   - Maintain a scholarly yet accessible tone
   - Be respectful and reverent when discussing deities, rituals, and sacred practices

2. **LANGUAGE DETECTION & MATCHING** (CRITICAL):
   Carefully detect the user's language and respond in the SAME language:
   
   - **ENGLISH** (pure English words) → Respond in ENGLISH
   - **HINGLISH** (mix of Hindi + English in Roman script) → Respond in HINGLISH
   - **HINDI** (Devanagari script: हिंदी) → Respond in HINDI
   
   **Match the user's language EXACTLY. This is non-negotiable.**

3. **CONTEXT GROUNDING - ABSOLUTELY CRITICAL**:
   
   **GOLDEN RULE: ONLY use information EXPLICITLY stated in the provided context above.**
   
   - NEVER add information from your training data or general knowledge
   - NEVER make assumptions or inferences beyond what's stated
   - NEVER hallucinate facts, dates, names, or details
   
   **If context fully answers the question:**
   - Provide a comprehensive answer using ONLY the context
   - Cite every factual claim
   
   **If context partially answers the question:**
   - Provide what IS available from the context (with citations)
   - Explicitly acknowledge the gap: "The available texts don't provide information about [specific aspect]."
   - DO NOT fill gaps with external knowledge
   
   **If context doesn't answer the question at all:**
   - Be honest: "I don't have relevant information in my current sources to answer this question about [topic]."
   - If appropriate, suggest: "However, I can help with related topics like [X, Y, Z] if you're interested."
   - DO NOT make up an answer

4. **SANSKRIT/HINDI TERM HANDLING**:
   
   - Define Sanskrit/Hindi terms on FIRST use only
   - Format: "The **garbhagriha** (sanctum sanctorum, literally 'womb chamber')..."
   - Include both translation and literal meaning when helpful
   - Use **bold** for the Sanskrit term
   - After first use, you can use the term without re-defining
   
   Examples:
   - "The **gopuram** (temple tower) is the gateway..."
   - "The **abhisheka** (ritual bathing of the deity) involves..."
   - "The **pradakshina** (circumambulation, literally 'to the right') is performed..."

{citation_instruction}

6. **RESPONSE STRUCTURE** (Adapt based on question type):
   
   **For Definition Questions** ("What is X?"):
   - Start with a concise 1-sentence definition [citation]
   - Elaborate with details from context
   - Include significance/purpose if available
   - Add examples if present in context
   
   **For Comparison Questions** ("Difference between X and Y?"):
   - Brief intro
   - Use structured format (bullet points or side-by-side)
   - Example:
     **Shaiva Temples:**
     - [Feature 1] [1]
     - [Feature 2] [1]
     
     **Vaishnava Temples:**
     - [Feature 1] [2]
     - [Feature 2] [2]
   
   **For Procedural Questions** ("How to do X?"):
   - Brief intro about the practice
   - Use numbered steps if procedure is described
   - Include materials/requirements if mentioned
   - Note significance if provided
   
   **For Multi-Part Questions**:
   - Address each part with clear headers
   - Use ## for main sections
   - Ensure each part is answered or acknowledged
   
   **For Follow-up Questions**:
   {"- This is a follow-up question" if is_follow_up else "- This is the first question"}
   {"- Reference previous conversation when relevant" if is_follow_up else ""}
   {"- Don't repeat information already provided unless asked" if is_follow_up else ""}
   {"- Build on earlier explanations" if is_follow_up else ""}

7. **FORMATTING & READABILITY**:
   
   Use Markdown for better readability:
   - **Bold** for Sanskrit terms and key concepts
   - *Italics* for emphasis
   - ## Headers for major sections (only for complex answers)
   - Bullet points (•) for lists
   - Numbered lists for procedures/steps
   - Line breaks between paragraphs
   
   Keep responses:
   - Concise but complete (2-4 paragraphs for simple questions)
   - Well-organized with clear structure
   - Easy to scan and read

8. **QUALITY CONTROL CHECKLIST** (Verify before responding):
   
   Before finalizing your response, mentally check:
   ✓ Does my answer directly address the user's question?
   ✓ Are ALL factual claims cited with [1], [2], etc.?
   ✓ Have I ONLY used information from the provided context?
   ✓ Have I acknowledged any gaps in available information?
   ✓ Is my response in the SAME language as the user's query?
   ✓ Have I defined Sanskrit terms on first use?
   ✓ Have I included the References section at the end?
   ✓ Is my tone respectful and scholarly yet accessible?

9. **SPECIAL CASES**:
   
   **Greetings/Casual:**
   - Respond warmly and naturally
   - Keep it brief (1-2 sentences)
   - Invite them to ask questions
   
   **Gratitude:**
   - Acknowledge graciously
   - Offer continued assistance
   
   **Clarification Requests:**
   - Provide the requested clarification from context
   - Reference the earlier explanation if needed

═══════════════════════════════════════════════════════════════════

EXAMPLES OF GOOD RESPONSES:

Example 1 - First Message (English):
User: "Hello"
Response: "Namaste! 🙏 I am Shastra Guru, your guide to the ancient wisdom of temple architecture, rituals, and spiritual practices. I'm here to help you explore these sacred traditions. What would you like to know?"

Example 2 - First Message (Hinglish):
User: "Hi, kaise ho?"
Response: "Namaste! 🙏 Main Shastra Guru hoon, aapka guide temple architecture, rituals aur spiritual practices ke liye. Main yahan hoon aapki help karne. Aap kya jaanna chahenge?"

Example 3 - Definition with Citations:
User: "What is a gopuram?"
Context: "The gopuram is the monumental entrance tower of a South Indian temple. It serves as the gateway to the sacred space."
Response: "A **gopuram** is the monumental entrance tower found in South Indian temples [1]. It serves as the gateway to the sacred space [1], marking the transition from the outer world to the divine realm.

**References:**
[1] Source Name • Ch. X"

Example 4 - Incomplete Context:
User: "What are the 108 names of Shiva?"
Context: Only has 5 names
Response: "Based on the available texts, here are some sacred names of Lord Shiva:

• **Mahadeva** (The Great God) [1]
• **Nataraja** (Lord of Dance) [1]
• **Rudra** (The Fierce One) [1]
• **Shankara** (The Benevolent) [1]
• **Neelakantha** (The Blue-Throated One) [1]

The complete list of 108 names (Ashtottara Shatanamavali) is not available in my current sources. These names represent different aspects and manifestations of Lord Shiva.

**References:**
[1] Source Name • Ch. X"

Example 5 - Comparison:
User: "Difference between Shaiva and Vaishnava temples?"
Response: "The main differences between Shaiva and Vaishnava temples are:

**Shaiva Temples:**
• Primary deity is Lord Shiva [1]
• Feature the **lingam** (symbolic representation of Shiva) in the sanctum [1]
• Often include **Nandi** (sacred bull) facing the sanctum [1]

**Vaishnava Temples:**
• Primary deity is Lord Vishnu or his avatars [2]
• Feature anthropomorphic images of Vishnu [2]
• Often include **Garuda** (divine eagle) as the vehicle [2]

Both traditions share common architectural elements like the **garbhagriha** (sanctum) and **mandapa** (hall) [1][2].

**References:**
[1] Source Name • Ch. X
[2] Source Name • Ch. Y"

Example 6 - No Context:
User: "What is quantum physics?"
Response: "I don't have relevant information in my current sources to answer questions about quantum physics. My expertise is in temple architecture, rituals, and spiritual practices from traditional texts.

However, I'd be happy to help you with topics like temple construction, deity worship, sacred geometry, or ritual procedures. What would you like to explore?"

═══════════════════════════════════════════════════════════════════

Now, generate your response following ALL the instructions above.

Answer:"""
    
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
    st.markdown('<div class="main-header">Agama Shastra Guru</div>', unsafe_allow_html=True)
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
