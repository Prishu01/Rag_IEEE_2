import streamlit as st
import requests
import uuid
import base64

API_BASE_URL = 'https://pawani09-sistec-bot.hf.space'

# Setup page configuration
st.set_page_config(page_title="SISTec Bot Interface", page_icon="🤖")
st.title("SISTec Bot")

# Initialize device ID
if 'device_id' not in st.session_state:
    st.session_state.device_id = f"web-client-{uuid.uuid4().hex[:8]}"

# Initialize chat history by fetching from API
if 'messages' not in st.session_state:
    st.session_state.messages = []
    
    # Try to load existing history
    try:
        # Hugging Face spaces can sleep, add a timeout so it doesn't hang forever
        response = requests.get(f"{API_BASE_URL}/session/{st.session_state.device_id}/history", timeout=10)
        if response.ok:
            data = response.json()
            if data.get("turns") and len(data["turns"]) > 0:
                for turn in data["turns"]:
                    if "question" in turn or "user" in turn:
                        st.session_state.messages.append({"role": "user", "content": turn.get("question", turn.get("user")), "audio": None})
                    if "answer" in turn or "bot" in turn or "response" in turn:
                        st.session_state.messages.append({"role": "assistant", "content": turn.get("answer", turn.get("bot", turn.get("response"))), "audio": None})
    except Exception as e:
        pass # If history fails, we just start fresh
    
    # If no history, add welcome message
    if len(st.session_state.messages) == 0:
         st.session_state.messages.append({
             "role": "assistant", 
             "content": "Hello! I am the SISTec Bot. How can I help you today?", 
             "audio": None
         })

# Sidebar for configuration and actions
with st.sidebar:
    st.image("https://commons.wikimedia.org/wiki/Special:FilePath/SISTec_Logo.png", width=150)
    st.markdown("### Settings")
    voice_enabled = st.checkbox("Enable Voice Responses", value=False)
    
    voice_name = st.selectbox("Voice", [
        "en-IN-NeerjaNeural", 
        "en-IN-PrabhatNeural", 
        "en-US-JennyNeural", 
        "en-US-GuyNeural", 
        "en-GB-SoniaNeural"
    ], format_func=lambda x: {
        "en-IN-NeerjaNeural": "Neerja (IN)",
        "en-IN-PrabhatNeural": "Prabhat (IN)",
        "en-US-JennyNeural": "Jenny (US)",
        "en-US-GuyNeural": "Guy (US)",
        "en-GB-SoniaNeural": "Sonia (UK)"
    }[x])
    
    st.divider()
    if st.button("🗑️ Clear Session", use_container_width=True):
        try:
            requests.delete(f"{API_BASE_URL}/session/{st.session_state.device_id}", timeout=5)
            st.session_state.device_id = f"web-client-{uuid.uuid4().hex[:8]}" # Generate new ID to be safe
            st.session_state.messages = [{"role": "assistant", "content": "Session cleared. How can I help you now?", "audio": None}]
            st.rerun()
        except Exception as e:
            st.error("Failed to clear session.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("audio"):
            st.audio(msg["audio"])

# Handle user input
if prompt := st.chat_input("Ask something..."):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": prompt, "audio": None})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("Typing..."):
            params = {
                "question": prompt,
                "device_id": st.session_state.device_id,
                "voice": str(voice_enabled).lower(),
                "voice_name": voice_name
            }
            try:
                response = requests.get(f"{API_BASE_URL}/ask", params=params)
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '')
                audio_data = None
                answer_text = ""
                
                # Handle Audio vs Text JSON response
                if 'audio' in content_type:
                    audio_data = response.content
                    b64_answer = response.headers.get('x-answer-b64')
                    if b64_answer:
                        try:
                            # Try to decode utf-8 properly
                            import urllib.parse
                            answer_text = urllib.parse.unquote(base64.b64decode(b64_answer).decode('utf-8'))
                        except:
                            answer_text = base64.b64decode(b64_answer).decode('utf-8', errors='ignore')
                    else:
                        answer_text = "Audio response received."
                else:
                    data = response.json()
                    answer_text = data.get("answer", data.get("response", data.get("text", str(data))))
                    if data.get("audio"):
                        audio_data = base64.b64decode(data["audio"])
                    elif data.get("audio_url"):
                        audio_data = data["audio_url"]
                
                # Display output
                st.markdown(answer_text)
                if audio_data:
                    st.audio(audio_data)
                
                # Add to history
                st.session_state.messages.append({"role": "assistant", "content": answer_text, "audio": audio_data})
                
            except Exception as e:
                error_msg = "Sorry, I'm having trouble connecting to the server. Please check your connection and try again."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "audio": None})
