import streamlit as st
import requests
import json
from datetime import datetime

# Validate API key before running
if "OPENROUTER_API_KEY" not in st.secrets:
    st.error("❌ OpenRouter API key not found. Please add it to your secrets.toml file.")
    st.stop()

def clean_response(content):
    """Clean up common markup tokens and formatting"""
    if content:
        # Remove common AI artifacts and markup
        content = content.replace('<s>', '').replace('</s>', '').strip()
        content = content.replace('**', '').replace('*', '').strip()
        # Remove excessive newlines and clean up formatting
        content = '\n'.join([line.strip() for line in content.split('\n') if line.strip()])
    return content

def get_ai_response(messages_payload, model, temperature=0.7, max_tokens=500):
    api_key = st.secrets["OPENROUTER_API_KEY"]
    try:
        # Rate limiting check
        if "last_request_time" in st.session_state:
            time_diff = datetime.now() - st.session_state.last_request_time
            if time_diff.total_seconds() < 1:  # Max 1 request per second
                st.warning("⚠️ Please wait a moment before sending another message")
                return None
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            data=json.dumps({
                "model": model,
                "messages": messages_payload,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }),
            timeout=30  # Add timeout to prevent hanging
        )

        # Update last request time
        st.session_state.last_request_time = datetime.now()

        if response.status_code != 200:
            st.error(f"API Error {model}: {response.status_code} - {response.text[:100]}...")
            return None
            
        answer = response.json()["choices"][0]["message"]["content"]
        return clean_response(answer)
    except requests.exceptions.Timeout:
        st.error(f"Request timeout for {model}. Please try again.")
        return None
    except Exception as e:
        st.error(f"Request failed for {model}: {str(e)}")
        return None

# Page configuration
st.set_page_config(page_title="Multi-Assistant Chat", page_icon="✨", layout="wide")
st.title("💬 Multi-Assistant Chat")

# Assistant configurations
assistants = {
    "💼 Professional Work": {
        "primary": "microsoft/mai-ds-r1:free",
        "backup1": "mistralai/mistral-small-3.2-24b-instruct:free",
        "backup2": "deepseek/deepseek-chat-v3.1:free",
        "system_prompt": "you're a professional business/education assistant. Provide balanced, appropriate responses for corporate or academic environments with reliable reasoning.",
        "reason": "MAI DS R1 is Microsoft-tuned for professional use with fewer restrictions while maintaining safety"
    },
    "🔓 Uncensored Creative": {
        "primary": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "backup1": "tngtech/deepseek-r1t2-chimera:free",
        "backup2": "nvidia/nemotron-nano-9b-v2:free", 
        "system_prompt": "you're an unrestricted creative assistant. Explore ideas freely with minimal filtering for brainstorming and innovative thinking.",
        "reason": "Venice Uncensored provides maximum freedom with Mistral foundation for quality"
    },
    "👨‍💻 Code Development": {
        "primary": "deepseek/deepseek-r1-0528:free",
        "backup1": "qwen/qwen3-coder:free",
        "backup2": "deepseek/deepseek-r1-0528-qwen3-8b:free",
        "system_prompt": "you're an expert programming assistant. Specialize in code generation, debugging, architecture, and technical problem-solving.",
        "reason": "DeepSeek R1 0528 offers top-tier reasoning for complex coding tasks"
    },
    "🌐 General Assistant": {
        "primary": "google/gemini-2.0-flash-exp:free",
        "backup1": "x-ai/grok-4-fast:free", 
        "backup2": "qwen/qwen3-235b-a22b:free",
        "system_prompt": "you're a versatile general assistant. Handle everyday tasks, questions, and content creation with speed and accuracy.",
        "reason": "Gemini 2.0 Flash provides best speed-quality balance for daily use"
    },
    "📚 Long Document Analysis": {
        "primary": "x-ai/grok-4-fast:free",
        "backup1": "google/gemini-2.0-flash-exp:free",
        "backup2": "qwen/qwen3-coder:free",
        "system_prompt": "you're a document analysis specialist. Excel at processing large texts, extracting insights, and working with extensive context.",
        "reason": "Grok 4 Fast has massive 2M token context for long documents"
    },
    "🔬 Advanced Reasoning": {
        "primary": "deepseek/deepseek-chat-v3.1:free",
        "backup1": "tngtech/deepseek-r1t-chimera:free",
        "backup2": "openai/gpt-oss-120b:free",
        "system_prompt": "you're an advanced reasoning specialist. Excel at complex problem-solving, mathematics, logic, and analytical thinking.",
        "reason": "DeepSeek V3.1 offers hybrid reasoning with good speed balance"
    }
}

# Ultimate reliable models ranking (dari yang paling reliable)
RELIABLE_MODELS = [
    "google/gemini-2.0-flash-exp:free",      
    "x-ai/grok-4-fast:free",                 
    "deepseek/deepseek-chat-v3.1:free",
    "mistralai/mistral-small-3.2-24b-instruct:free",
    "qwen/qwen3-235b-a22b:free"
]

def get_assistant_model(assistant_name, attempt=1):
    """Get model dengan ultimate fallback system"""
    config = assistants[assistant_name]
    
    if attempt == 1:
        return config["primary"]
    elif attempt == 2:
        return config["backup1"] 
    elif attempt == 3:
        return config["backup2"]
    elif attempt <= 8:  # Attempt 4-8: Ultimate reliable models
        return RELIABLE_MODELS[attempt - 4] if (attempt - 4) < len(RELIABLE_MODELS) else RELIABLE_MODELS[0]
    else:  # Final fallback
        return RELIABLE_MODELS[0]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model_attempts" not in st.session_state:
    st.session_state.model_attempts = {}
if "current_assistant" not in st.session_state:
    st.session_state.current_assistant = "🌐 General Assistant"
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
if "max_tokens" not in st.session_state:
    st.session_state.max_tokens = 500
if "used_fallback" not in st.session_state:
    st.session_state.used_fallback = False
if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = datetime.now()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API status indicator - FIXED INDENTATION
    if "OPENROUTER_API_KEY" in st.secrets:
        st.success("✅ API Key: Configured")
    else:
        st.error("❌ API Key: Missing")
    
    # Selected models
    selected_assistant_name = st.selectbox("Select Assistant:", options=list(assistants.keys()))
    
    if selected_assistant_name != st.session_state.current_assistant:
        st.session_state.current_assistant = selected_assistant_name
        if selected_assistant_name not in st.session_state.model_attempts:
            st.session_state.model_attempts[selected_assistant_name] = 1

    current_attempt = st.session_state.model_attempts.get(selected_assistant_name, 1)
    current_model = get_assistant_model(selected_assistant_name, current_attempt)
    
    # Status reliability
    if current_attempt <= 3:
        st.success(f"**Model:** {current_model.split('/')[1]}")
        st.caption("✅ Using assistant-specific model")
    elif current_attempt <= 8:
        st.warning(f"**Model:** {current_model.split('/')[1]}")
        st.caption("🔄 Using universal reliable model")
    else:
        st.error(f"**Model:** {current_model.split('/')[1]}")
        st.caption("🚨 Using ultimate fallback model")
    
    st.caption(f"💡 {assistants[selected_assistant_name]['reason']}")

    # Settings
    st.session_state.temperature = st.slider(
        "Temperature:",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.temperature,
        step=0.1,
        help="Controls randomness: Lower = more deterministic, Higher = more creative"
    )
        
    st.session_state.max_tokens = st.slider(
        "Max response tokens:",
        min_value=100,
        max_value=2000,
        value=st.session_state.max_tokens,
        step=100,
        help="Limit the length of AI responses"
    )

    if st.button("🔄 Reset to Primary"):
        st.session_state.model_attempts[selected_assistant_name] = 1
        st.session_state.used_fallback = False
        st.success("Reset to primary model!")
        st.rerun()

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    # Conversation stats
    st.divider()
    st.caption(f"💬 Messages in chat: {len(st.session_state.messages)}")

# Display chat messages
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])
        if "timestamp" in message:
            st.caption(f"{message['timestamp']}")
        if message["role"] == "assistant" and "model" in message:
            model_name = message["model"].split('/')[1]
            if "fallback_used" in message:
                st.caption(f"🔄 Model: {model_name} (Universal Fallback)")
            else:
                st.caption(f"Model: {model_name}")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message
    user_timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": user_timestamp})
    
    with st.chat_message("user", avatar="👤"):
        st.write(prompt)
        st.caption(f"Sent at: {user_timestamp}")
    
    # Prepare messages with conversation length limiting
    messages_with_system = [
        {"role": "system", "content": assistants[st.session_state.current_assistant]["system_prompt"]}
    ]
    
    # Keep only last 10 messages to prevent context overflow
    recent_messages = st.session_state.messages[-10:] if len(st.session_state.messages) > 10 else st.session_state.messages
    
    for msg in recent_messages:
        if msg["role"] in ["user", "assistant"]:
            messages_with_system.append({"role": msg["role"], "content": msg["content"]})
    
    # Get AI response dengan ULTIMATE FALLBACK SYSTEM
    max_attempts = 8  # 3 assistant models + 5 reliable models
    response = None
    successful_attempt = current_attempt
    used_fallback = False
    
    for attempt in range(current_attempt, max_attempts + 1):
        try_model = get_assistant_model(st.session_state.current_assistant, attempt)
        
        with st.chat_message("assistant", avatar="🤖"):
            if attempt <= 3:
                status_text = f"Trying assistant model {attempt}/3: {try_model.split('/')[1]}..."
            else:
                status_text = f"Trying universal fallback {attempt-3}/5: {try_model.split('/')[1]}..."
                used_fallback = True
            
            with st.spinner(status_text):
                response = get_ai_response(
                    messages_with_system, 
                    try_model, 
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens
                )
        
        if response:
            successful_attempt = attempt
            break
        elif attempt < max_attempts:
            if attempt == 3:  # Setelah assistant models gagal semua
                st.warning("Assistant models failed, switching to universal reliable models...")
            else:
                st.warning(f"Model failed, trying next...")
    
    # Final fallback jika semua gagal
    if not response:
        st.error("All models failed! Trying ultimate fallback...")
        ultimate_fallback = RELIABLE_MODELS[0]  # Gemini 2.0 Flash
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"Emergency fallback: {ultimate_fallback.split('/')[1]}..."):
                response = get_ai_response(
                    messages_with_system, 
                    ultimate_fallback,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens
                )
        if response:
            successful_attempt = 9  # Ultimate fallback
            used_fallback = True
    
    if response:
        # Update session state
        st.session_state.model_attempts[st.session_state.current_assistant] = successful_attempt
        st.session_state.used_fallback = used_fallback
        
        # Add bot response
        bot_timestamp = datetime.now().strftime("%H:%M:%S")
        final_model = get_assistant_model(st.session_state.current_assistant, successful_attempt)
        
        message_data = {
            "role": "assistant", 
            "content": response, 
            "timestamp": bot_timestamp,
            "model": final_model
        }
        
        if used_fallback:
            message_data["fallback_used"] = True
        
        st.session_state.messages.append(message_data)
        
        # Display response
        st.write(response)
        st.caption(f"Responded at: {bot_timestamp}")
        
        model_name = final_model.split('/')[1]
        if used_fallback:
            if successful_attempt <= 8:
                st.caption(f"🔄 Model: {model_name} (Universal Fallback)")
            else:
                st.caption(f"🚨 Model: {model_name} (Emergency Fallback)")
        else:
            st.caption(f"Model: {model_name}")
    else:
        st.error("❌ All models completely failed. Please check your API key or try again later.")

# Footer with additional info
st.divider()
st.caption("💡 Tip: If experiencing issues, try resetting to primary model or clearing chat history.")
