import os
import sys
import hashlib
import warnings
import logging
import json
from datetime import datetime, timezone, timezone

# Suppress Windows asyncio warnings
warnings.filterwarnings('ignore', category=ResourceWarning)
logging.getLogger('asyncio').setLevel(logging.ERROR)

os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

import streamlit as st

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import graph
from ingest import ingest_document
from utils import is_already_indexed, save_indexed_doc, load_indexed_docs
from dotenv import load_dotenv
from prompts import (
    CONVERSATIONAL_FALLBACK_RESPONSE,
    is_unavailable_answer,
)

load_dotenv()

# Setup structured logging for Streamlit
class StreamlitLogger:
    @staticmethod
    def log(level, message, **kwargs):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "app": "streamlit",
            **kwargs
        }
        print(json.dumps(log_entry), flush=True)
    
    @staticmethod
    def info(message, **kwargs):
        StreamlitLogger.log("INFO", message, **kwargs)
    
    @staticmethod
    def error(message, **kwargs):
        StreamlitLogger.log("ERROR", message, **kwargs)
    
    @staticmethod
    def warning(message, **kwargs):
        StreamlitLogger.log("WARNING", message, **kwargs)

logger = StreamlitLogger()


# Page config
st.set_page_config(
    page_title="Knowledge Assistant Agent",
    layout="wide",
    page_icon="KA",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("authenticated_user", "Guest")
st.session_state.setdefault("user_role", "public")

# Custom CSS - Professional & Beautiful Design
st.markdown("""
    <style>
        /* Professional Gradient Sidebar */
        [data-testid="stSidebar"][aria-expanded="true"] {
            background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%) !important;
            min-width: 300px !important;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%) !important;
        }
        [data-testid="stSidebar"] * {
            color: #ecf0f1 !important;
        }
        
        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background: transparent;}
        
        /* Sidebar styling */
        .sidebar-title {
            font-size: 24px;
            font-weight: 700;
            padding: 10px 0 5px 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .pro-text {
            background: linear-gradient(90deg, #3498db, #2ecc71);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* Knowledge Base button */
        .kb-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 14px 16px;
            border-radius: 12px;
            margin: 5px 0 10px 0;
            text-align: left;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
            cursor: pointer;
            font-weight: 600;
        }
        .kb-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        /* Upload section */
        [data-testid="stFileUploader"] {
            background: #825ee4 !important;
            border: 2px dashed #5e72e4 !important;
            border-radius: 12px !important;
            padding: 20px !important;
        }
        [data-testid="stFileUploader"] label {
            color: #825ee4 !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background-color: #825ee4 !important;
            border: 2px dashed #5e72e4 !important;
            border-radius: 8px !important;
            min-height: 120px !important;
            padding: 16px !important;
        }
        [data-testid="stFileUploaderDropzone"] svg {
            color: #5e72e4 !important;
            fill: #5e72e4 !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background-color: #5e72e4 !important;
            border: 1px solid #5e72e4 !important;
            color: white !important;
            font-weight: 600 !important;
        }
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] div {
            color: #1a202c !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }
        /* Force all text in dropzone to be dark */
        [data-testid="stFileUploaderDropzone"] * {
            color: #1a202c !important;
        }
        /* Override button text to white */
        [data-testid="stFileUploaderDropzone"] button * {
            color: white !important;
        }
        [data-testid="stFileUploaderFile"] {
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%) !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px !important;
        }
        [data-testid="stFileUploaderFile"] * {
            color: #ffffff !important;
            font-weight: 600 !important;
        }
        [data-testid="stFileUploaderFile"] small {
            color: #e8eaf6 !important;
        }
        [data-testid="stFileUploaderDeleteBtn"] {
            background-color: #ffffff !important;
            border-radius: 999px !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stFileUploaderDeleteBtn"]:hover {
            background-color: #f56565 !important;
            transform: scale(1.1) !important;
        }
        [data-testid="stFileUploaderDeleteBtn"] svg {
            color: #5e72e4 !important;
        }
        [data-testid="stFileUploaderDeleteBtn"]:hover svg {
            color: white !important;
        }
        
        /* Indexed files */
        .indexed-item {
            background: linear-gradient(135deg, rgba(46, 204, 113, 0.2) 0%, rgba(52, 152, 219, 0.2) 100%);
            padding: 12px 14px;
            border-radius: 10px;
            margin: 10px 0;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid rgba(46, 204, 113, 0.3);
            transition: all 0.3s ease;
        }
        .indexed-item:hover {
            transform: translateX(5px);
            border-color: rgba(46, 204, 113, 0.6);
        }
        .indexed-badge {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 700;
            margin-left: auto;
            box-shadow: 0 2px 8px rgba(46, 204, 113, 0.3);
        }
        
        /* Main content area - Light & Professional */
        .main .block-container {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            padding: 2rem;
            padding-bottom: 0 !important;
        }
        
        .stApp {
            background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        }
        
        /* Bottom container - merge with main */
        section[data-testid="stBottom"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
            padding: 0 2rem 2rem 2rem !important;
            margin: 0 !important;
        }
        
        section[data-testid="stBottom"] > div {
            background: transparent !important;
        }
        
        /* Force bottom container background */
        .stBottom {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
        }
        
        [data-testid="stBottom"] > div > div {
            background: transparent !important;
        }
        
        /* Remove any default bottom styling */
        .main > div:last-child {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
        }
        
        /* Main header */
        .main-header {
            font-size: 38px;
            font-weight: 800;
            margin-bottom: 30px;
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }
        
        /* Chat messages */
        [data-testid="stChatMessageContent"] {
            background: white;
            border-radius: 20px;
            padding: 18px 24px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.04);
        }
        
        /* User message */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            color: white !important;
            border: none;
            box-shadow: 0 6px 20px rgba(94, 114, 228, 0.25);
        }
        
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] p {
            color: white !important;
        }
        
        /* Assistant message */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] {
            background: white;
            border: 1px solid #e8eaf6;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        }
        
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] p {
            color: #2d3748 !important;
            line-height: 1.6;
        }
        
        /* Chat avatars */
        [data-testid="chatAvatarIcon-user"] {
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(94, 114, 228, 0.3);
        }
        
        [data-testid="chatAvatarIcon-assistant"] {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(72, 187, 120, 0.3);
        }
        
        /* Sample question buttons */
        .stButton > button {
            border-radius: 30px;
            padding: 14px 32px;
            font-weight: 600;
            border: none;
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            color: white;
            box-shadow: 0 6px 20px rgba(94, 114, 228, 0.25);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-size: 15px;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #4c5fd5 0%, #7049d5 100%);
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(94, 114, 228, 0.35);
        }
        
        /* Chat input */
        [data-testid="stChatInput"] {
            border-radius: 30px;
            background: white;
            box-shadow: 0 8px 30px rgba(0,0,0,0.08);
            border: 2px solid #f0f0f0;
        }
        
        [data-testid="stChatInput"] textarea {
            border-radius: 30px;
            border: none;
            padding: 14px 24px;
            font-size: 15px;
            color: #2d3748;
            background: transparent;
        }
        
        [data-testid="stChatInput"] textarea:focus {
            outline: none;
            box-shadow: none;
        }
        
        [data-testid="stChatInput"] textarea::placeholder {
            color: #a0aec0;
        }
        
        [data-testid="stChatInput"] button {
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            border-radius: 50%;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(94, 114, 228, 0.3);
        }
        
        [data-testid="stChatInput"] button:hover {
            transform: scale(1.15);
            box-shadow: 0 6px 16px rgba(94, 114, 228, 0.4);
        }
        
        /* Spinner */
        .stSpinner > div {
            border-top-color: #5e72e4 !important;
        }
        
        /* Success/Info/Error messages */
        .stSuccess {
            background: linear-gradient(135deg, rgba(72, 187, 120, 0.08) 0%, rgba(56, 161, 105, 0.08) 100%);
            border-left: 4px solid #48bb78;
            border-radius: 12px;
            padding: 16px;
        }
        
        .stInfo {
            background: linear-gradient(135deg, rgba(66, 153, 225, 0.08) 0%, rgba(49, 130, 206, 0.08) 100%);
            border-left: 4px solid #4299e1;
            border-radius: 12px;
            padding: 16px;
        }
        
        .stError {
            background: linear-gradient(135deg, rgba(245, 101, 101, 0.08) 0%, rgba(229, 62, 62, 0.08) 100%);
            border-left: 4px solid #f56565;
            border-radius: 12px;
            padding: 16px;
        }
        
        /* Welcome section styling */
        .welcome-section {
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,249,250,0.9) 100%);
            border-radius: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.06);
            margin: 40px auto;
            max-width: 800px;
        }
        
        .welcome-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        
        .welcome-title {
            font-size: 32px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 12px;
        }
        
        .welcome-subtitle {
            font-size: 18px;
            color: #718096;
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
        <div class="sidebar-title">Knowledge Assistant <span class="pro-text">Agent</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Knowledge Base button
    st.markdown("""
        <div class="kb-button">Knowledge Base</div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    st.markdown("**Upload Documents**")
    
    uploaded_file = st.file_uploader(
        "Upload a document (PDF, Word, Excel, PowerPoint, Markdown, CSV, TXT)",
        type=["pdf", "txt", "docx", "csv", "xlsx", "xls", "pptx", "ppt", "md"],
        label_visibility="visible"
    )
    
    if uploaded_file:
        file_name = os.path.basename(uploaded_file.name)
        already_indexed = is_already_indexed(file_name)

        if already_indexed:
            st.info("This file is already in the local indexed list. Click re-index to upload it to Pinecone again.")

        button_label = "Re-index in Pinecone" if already_indexed else "Upload to Pinecone"
        if st.button(button_label, use_container_width=True):
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, file_name)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Log upload start
            logger.info(
                "Document upload started",
                filename=file_name,
                user=st.session_state.get('authenticated_user', 'unknown'),
                component="upload"
            )

            try:
                with st.spinner(f"Indexing {file_name}..."):
                    vector_count = ingest_document(file_path)
                    save_indexed_doc(file_name)
                
                # Log upload success
                logger.info(
                    "Document uploaded successfully",
                    filename=file_name,
                    chunks=vector_count,
                    user=st.session_state.get('authenticated_user', 'unknown'),
                    component="upload"
                )
                
                st.success(f"{file_name} uploaded to Pinecone with {vector_count} chunks.")
                st.rerun()
            except Exception as exc:
                # Log upload error
                logger.error(
                    "Document upload failed",
                    filename=file_name,
                    error=str(exc),
                    user=st.session_state.get('authenticated_user', 'unknown'),
                    component="upload"
                )
                st.error(f"Upload to Pinecone failed: {exc}")
    
    st.markdown("")
    
    # Show indexed files
    indexed_docs = load_indexed_docs()
    if indexed_docs:
        for doc in indexed_docs:
            st.markdown(f"""
                <div class="indexed-item">{doc}
                    <span class="indexed-badge">Indexed</span>
                </div>
            """, unsafe_allow_html=True)

# Main content
st.markdown('<div class="main-header">Knowledge Assistant Chat</div>', unsafe_allow_html=True)
st.markdown("")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"])
        
        # Show confidence and sources for assistant messages
        if (
            msg["role"] == "assistant"
            and "confidence" in msg
            and msg.get("intent") == "documentation_question"
            and msg["content"].strip() != CONVERSATIONAL_FALLBACK_RESPONSE
        ):
            st.markdown("---")
            
            confidence = msg.get("confidence", 0.0)
            confidence_category = msg.get("confidence_category", "UNKNOWN")
            is_from_docs = msg.get("is_from_documents", False)
            confidence_explanation = msg.get("confidence_explanation", "")
            confidence_color = "#48bb78" if confidence > 0.7 else "#f6ad55" if confidence > 0.5 else "#f56565"
            
            st.markdown(f"""
                <div style="background: #f7fafc; padding: 16px; border-radius: 12px; margin: 10px 0;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-weight: 600; color: #2d3748;">Answer Confidence:</span>
                        <span style="background: {confidence_color}; color: white; padding: 6px 14px; border-radius: 12px; font-weight: 600;">
                            {confidence:.1%} - {confidence_category}
                        </span>
                    </div>
                    <div style="color: #718096; font-size: 14px; margin-top: 8px;">
                        {'Answer is from indexed documents' if is_from_docs else 'Answer may include external knowledge'}
                    </div>
                    <div style="color: #718096; font-size: 13px; margin-top: 6px; font-style: italic;">
                        {confidence_explanation}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            sources = [] if is_unavailable_answer(msg["content"]) else msg.get("sources", [])
            if sources:
                with st.expander(f"View Sources ({len(sources)} documents)", expanded=False):
                    for i, source in enumerate(sources, 1):
                        page_info = f"Page {source['page']}" if source.get('page') else "Page N/A"
                        relevance = source['score']
                        relevance_color = "#48bb78" if relevance > 0.7 else "#4299e1"
                        
                        st.markdown(f"""
                            <div style="background: #f7fafc; padding: 12px 16px; border-radius: 10px; margin: 8px 0; border-left: 4px solid {relevance_color};">
                                <div style="font-weight: 600; color: #2d3748; font-size: 15px; margin-bottom: 6px;">
                                    {source['document']}
                                </div>
                                <div style="color: #718096; font-size: 14px;">{page_info} - Relevance: {relevance:.1%}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Ask your question...")

if user_input:
    # Log question
    logger.info(
        "Question received",
        question_length=len(user_input),
        user=st.session_state.get('authenticated_user', 'unknown'),
        component="chat"
    )
    
    # User message
    memory = st.session_state.messages[-8:]
    with st.chat_message("user", avatar="user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Assistant response
    with st.chat_message("assistant", avatar="assistant"):
        with st.spinner("Thinking..."):
            result = graph.invoke({
                "question": user_input,
                "memory": memory,
                "context": "",
                "intent": "",
                "answer": "",
            })
            answer = result["answer"]
            intent = result.get("intent", "documentation_question")
            confidence = result.get("confidence", {})
            sources = [] if is_unavailable_answer(answer) else result.get("sources", [])
            no_answer_found = is_unavailable_answer(answer)

            logger.info(
                "Answer generated",
                question_length=len(user_input),
                answer_length=len(answer),
                confidence_score=confidence.get("confidence_score"),
                sources_count=len(sources),
                intent=intent,
                selected_tool=result.get("selected_tool"),
                verification=result.get("verification"),
                user=st.session_state.get('authenticated_user', 'unknown'),
                component="agent"
            )

            st.markdown(answer)

            if intent == "documentation_question" and confidence:
                st.markdown("---")

                confidence_score = confidence["confidence_score"]
                confidence_category = confidence["category"]
                is_from_docs = confidence["is_from_documents"]
                confidence_color = "#48bb78" if confidence_score > 0.7 else "#f6ad55" if confidence_score > 0.5 else "#f56565"

                st.markdown(f"""
                    <div style="background: #f7fafc; padding: 16px; border-radius: 12px; margin: 10px 0;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <span style="font-weight: 600; color: #2d3748;">Answer Confidence:</span>
                            <span style="background: {confidence_color}; color: white; padding: 6px 14px; border-radius: 12px; font-weight: 600;">
                                {confidence_score:.1%} - {confidence_category}
                            </span>
                        </div>
                        <div style="color: #718096; font-size: 14px; margin-top: 8px;">
                            {'Answer is from indexed documents' if is_from_docs else 'Answer may include external knowledge'}
                        </div>
                        <div style="color: #718096; font-size: 13px; margin-top: 6px; font-style: italic;">
                            {confidence['explanation']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if sources and not no_answer_found:
                    with st.expander(f"View Sources ({len(sources[:3])} documents)", expanded=False):
                        for i, source in enumerate(sources[:3], 1):
                            page_info = f"Page {source['page']}" if source.get('page') else "Page N/A"
                            relevance = source['score']
                            relevance_color = "#48bb78" if relevance > 0.7 else "#4299e1"

                            st.markdown(f"""
                                <div style="background: #f7fafc; padding: 12px 16px; border-radius: 10px; margin: 8px 0; border-left: 4px solid {relevance_color};">
                                    <div style="font-weight: 600; color: #2d3748; font-size: 15px; margin-bottom: 6px;">
                                        {source['document']}
                                    </div>
                                    <div style="color: #718096; font-size: 14px;">{page_info} - Relevance: {relevance:.1%}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                elif not no_answer_found:
                    st.info("No specific sources found for this query.")

            message = {
                "role": "assistant",
                "content": answer,
                "intent": intent,
                "selected_tool": result.get("selected_tool"),
                "sources": [] if no_answer_found else sources[:3],
            }
            if intent == "documentation_question" and confidence:
                message.update({
                    "confidence": confidence["confidence_score"],
                    "confidence_category": confidence["category"],
                    "is_from_documents": confidence["is_from_documents"],
                    "confidence_explanation": confidence["explanation"],
                })
            st.session_state.messages.append(message)
