"""
InterviewIQ - Autonomous Multi-Agent Interviewer & Career Coach
Built with Streamlit & Google Gemini
End-to-End Interview Flow: Resume Submission -> Role Selection -> Interview (with Intro) -> Result Announced
"""

import datetime
import io
import json
import os
import time
from typing import Any, Optional

from dotenv import load_dotenv
import streamlit as st

# Load .env file automatically
load_dotenv()

import config
from core.evaluator_agent import EvaluatorAgent
from core.gemini_client import GeminiClient
from core.interview_agent import InterviewAgent
from core.resume_parser import parse_resume
from core.tts_service import generate_audio

# Page Configuration
st.set_page_config(
    page_title=f"{config.APP_NAME} - Your AI Interview Partner",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# =========================================================
# HELPER: QUESTION GENERATOR / LOADER
# =========================================================
def load_role_questions(role: str, count: int = 5) -> list[dict]:
    """Loads curated questions from data/interview_roles.json with fallbacks."""
    data_path = os.path.join(os.path.dirname(__file__), "data", "interview_roles.json")
    questions = []
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                roles_db = json.load(f)
                if role in roles_db:
                    questions = roles_db[role].get("questions", [])
                elif "Software Engineer" in roles_db:
                    questions = roles_db["Software Engineer"].get("questions", [])
        except Exception:
            pass

    # If no questions found or empty, provide classic technical questions
    if not questions:
        questions = [
            {
                "phase": "Core Concepts",
                "question": "What is the difference between a stack and a queue? Give real-life examples.",
                "probe": "How would you implement a queue using two stacks?",
                "criteria": "LIFO vs FIFO distinction, real-life analogies, and complexity analysis.",
                "ideal_answer": "A stack is a LIFO (Last In First Out) data structure, while a queue is a FIFO (First In First Out) data structure. For example, a stack is used in function call management (call stack) and undo/redo operations, while a queue is used in print spooling and background job processing."
            },
            {
                "phase": "Algorithms",
                "question": "How does binary search work on a sorted array, and what is its time and space complexity?",
                "probe": "How do you avoid integer overflow when calculating the midpoint?",
                "criteria": "O(log n) time, O(1) space, sorted precondition, and mid calculation.",
                "ideal_answer": "Binary search repeatedly divides the search space in half by comparing the target with the middle element. It has O(log n) time complexity and O(1) space complexity. Precondition is that the array must be sorted. Mid is calculated using low + (high - low) // 2."
            },
            {
                "phase": "Database & SQL",
                "question": "What is the difference between an INNER JOIN and a LEFT JOIN in SQL? When would you use an index?",
                "probe": "What is the performance trade-off of having too many indexes?",
                "criteria": "JOIN semantics, NULL handling, B-Tree index lookup speed vs write penalty.",
                "ideal_answer": "An INNER JOIN returns only records with matching keys in both tables. A LEFT JOIN returns all records from the left table and matched records from the right table (or NULLs). Indexes speed up SELECT queries via B-Trees but add write overhead on INSERT/UPDATE."
            },
            {
                "phase": "System Design",
                "question": "What is the difference between monolithic architecture and microservices? What are the key trade-offs?",
                "probe": "How do microservices handle distributed transactions?",
                "criteria": "Deployment simplicity vs independent scaling, network latency, and eventual consistency.",
                "ideal_answer": "A monolith combines all components into a single deployable unit, making development and transactions simple. Microservices decouple components into independently scalable services communicating over APIs, but introduce network latency and distributed data consistency challenges (e.g. Saga pattern)."
            },
            {
                "phase": "Problem Solving",
                "question": "Describe a complex technical bug you encountered in a project. How did you debug and resolve it?",
                "probe": "What automated tests or monitoring did you add to prevent recurrence?",
                "criteria": "Systematic root cause analysis, logging, unit tests, and post-mortem mindset.",
                "ideal_answer": "An effective response follows the STAR framework: states the symptom, describes how logs and profiling isolated the root cause (e.g. race condition or memory leak), explains the surgical fix implemented, and highlights regression tests added to CI/CD."
            }
        ]

    return questions[:count]


# =========================================================
# SESSION STATE INITIALIZATION
# Workflow sequence:
# Step 1: Submit Resume ('upload')
# Step 2: Change / Select Role ('roles')
# Step 3: Interview with Introduction ('intro', 'intro_feedback', 'question', 'question_feedback')
# Step 4: Result Announced ('results')
# =========================================================
def init_session_state():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "upload"  # First: submit resume on this website!
    if "selected_role" not in st.session_state:
        st.session_state.selected_role = "Software Engineer"
    if "experience_level" not in st.session_state:
        st.session_state.experience_level = "Entry / New Grad (0-1 yrs)"
    if "selected_persona_name" not in st.session_state:
        st.session_state.selected_persona_name = "Dr. Elena Vance"
    if "question_count" not in st.session_state:
        st.session_state.question_count = 5
    if "current_question_index" not in st.session_state:
        st.session_state.current_question_index = 0
    if "questions_list" not in st.session_state or not st.session_state.questions_list:
        st.session_state.questions_list = load_role_questions(st.session_state.selected_role, st.session_state.question_count)
    if "answers_list" not in st.session_state:
        st.session_state.answers_list = []
    if "candidate_intro" not in st.session_state:
        st.session_state.candidate_intro = None
    if "intro_feedback" not in st.session_state:
        st.session_state.intro_feedback = None
    if "current_feedback" not in st.session_state:
        st.session_state.current_feedback = None
    if "dossier" not in st.session_state:
        st.session_state.dossier = None
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")
    if "selected_model" not in st.session_state or st.session_state.selected_model not in config.GEMINI_MODELS:
        st.session_state.selected_model = config.DEFAULT_MODEL
    if "audio_enabled" not in st.session_state:
        st.session_state.audio_enabled = True
    if "resume_data" not in st.session_state:
        st.session_state.resume_data = {
            "has_resume": False,
            "skills_found": [],
            "preview": "",
            "candidate_name": "Candidate",
            "recommended_roles": []
        }
    if "start_time" not in st.session_state or not st.session_state.start_time:
        st.session_state.start_time = None
    if "elapsed_minutes" not in st.session_state:
        st.session_state.elapsed_minutes = 0

init_session_state()


# Core Clients
@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key: str, model_name: str) -> GeminiClient:
    return GeminiClient(api_key=api_key, model_name=model_name)

gemini_client = get_gemini_client(st.session_state.api_key, st.session_state.selected_model)
evaluator_agent = EvaluatorAgent(gemini_client=gemini_client)


# =========================================================
# STEPPER COMPONENT (4 STEPS)
# 1. Submit Resume -> 2. Change Role -> 3. Interview & Intro -> 4. Result Announced
# =========================================================
def render_stepper(current_step: int):
    """
    Renders top 4-step progress stepper:
    Step 1: Submit Resume
    Step 2: Change Role
    Step 3: Interview & Intro
    Step 4: Result Announced
    """
    s1_class = "completed" if current_step > 1 else ("active" if current_step == 1 else "pending")
    s1_icon = "✓" if current_step > 1 else "1"

    s2_class = "completed" if current_step > 2 else ("active" if current_step == 2 else "pending")
    s2_icon = "✓" if current_step > 2 else "2"

    s3_class = "completed" if current_step > 3 else ("active" if current_step == 3 else "pending")
    s3_icon = "✓" if current_step > 3 else "3"

    s4_class = "completed" if current_step >= 4 else "pending"
    s4_icon = "🏆" if current_step >= 4 else "4"

    line1_class = "active" if current_step >= 2 else ""
    line2_class = "active" if current_step >= 3 else ""
    line3_class = "active" if current_step >= 4 else ""

    html = f"""
    <div class="stepper-container">
        <div class="step-node">
            <div class="step-circle {s1_class}">{s1_icon}</div>
            <div class="step-label {s1_class}">1. Submit Resume</div>
        </div>
        <div class="step-line {line1_class}"></div>
        <div class="step-node">
            <div class="step-circle {s2_class}">{s2_icon}</div>
            <div class="step-label {s2_class}">2. Change Role</div>
        </div>
        <div class="step-line {line2_class}"></div>
        <div class="step-node">
            <div class="step-circle {s3_class}">{s3_icon}</div>
            <div class="step-label {s3_class}">3. Interview & Intro</div>
        </div>
        <div class="step-line {line3_class}"></div>
        <div class="step-node">
            <div class="step-circle {s4_class}">{s4_icon}</div>
            <div class="step-label {s4_class}">4. Result Announced</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =========================================================
# SIDEBAR NAVIGATION & SETTINGS
# =========================================================
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
            <span style="font-size: 1.8rem;">🤖</span>
            <div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #ffffff;">InterviewIQ</div>
                <div style="font-size: 0.75rem; color: #94a3b8;">Autonomous AI Interview Agent</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Workflow Navigation Links
    s1_type = "primary" if st.session_state.current_page == "upload" else "secondary"
    if st.button("📄 1. Submit Resume", use_container_width=True, type=s1_type):
        st.session_state.current_page = "upload"
        st.rerun()

    s2_type = "primary" if st.session_state.current_page == "roles" else "secondary"
    if st.button("🎯 2. Change / Select Role", use_container_width=True, type=s2_type):
        st.session_state.current_page = "roles"
        st.rerun()

    interview_active = st.session_state.current_page in ("intro", "intro_feedback", "question", "question_feedback")
    s3_type = "primary" if interview_active else "secondary"
    if st.button("🎙️ 3. Interview & Intro", use_container_width=True, type=s3_type):
        if not st.session_state.get("candidate_intro") and not st.session_state.answers_list:
            st.session_state.current_page = "intro"
        elif st.session_state.current_page not in ("intro", "intro_feedback", "question", "question_feedback"):
            st.session_state.current_page = "question"
        st.rerun()

    s4_type = "primary" if st.session_state.current_page == "results" else "secondary"
    if st.button("🏆 4. Announced Results", use_container_width=True, type=s4_type):
        st.session_state.current_page = "results"
        st.rerun()

    if st.button("🏠 Home / Dashboard", use_container_width=True, type="secondary"):
        st.session_state.current_page = "landing"
        st.rerun()

    st.markdown("---")

    # Active Candidate Status Pill in Sidebar
    if st.session_state.resume_data.get("has_resume"):
        cand_name = st.session_state.resume_data.get("candidate_name", "Candidate")
        skills_ct = len(st.session_state.resume_data.get("skills_found", []))
        st.markdown(
            f"""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 10px 12px; margin-bottom: 14px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #6ee7b7;">✓ RESUME LOADED</div>
                <div style="font-size: 0.85rem; color: #ffffff; font-weight: 600;">{cand_name}</div>
                <div style="font-size: 0.75rem; color: #94a3b8;">{skills_ct} skills detected &bull; {st.session_state.selected_role}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Settings & API Configuration Expander
    with st.expander("⚙️ Settings & API Key", expanded=not bool(st.session_state.api_key)):
        user_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.api_key,
            help="Get free Gemini key from https://aistudio.google.com/"
        )
        if user_key != st.session_state.api_key:
            st.session_state.api_key = user_key
            st.session_state.pop("conn_status", None)
            st.cache_resource.clear()
            st.rerun()

        model_choice = st.selectbox(
            "Gemini Model",
            config.GEMINI_MODELS,
            index=config.GEMINI_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in config.GEMINI_MODELS else 0
        )
        if model_choice != st.session_state.selected_model:
            st.session_state.selected_model = model_choice
            st.session_state.pop("conn_status", None)
            st.cache_resource.clear()
            st.rerun()

        if st.session_state.api_key:
            if st.button("⚡ Test Connection", use_container_width=True):
                with st.spinner("Testing API connection..."):
                    ok, msg = gemini_client.test_connection()
                    st.session_state.conn_status = (ok, msg)

            if "conn_status" in st.session_state:
                ok, msg = st.session_state.conn_status
                if ok:
                    st.success(f"🟢 {msg}")
                else:
                    st.error(f"🔴 {msg}")
            else:
                st.success("🟢 API Key Loaded")
        else:
            st.info("🟡 Simulation Mode (Key optional)")

        st.session_state.audio_enabled = st.checkbox("Enable Neural Audio Voice", value=st.session_state.audio_enabled)


# =========================================================
# TOP NAVIGATION HEADER WITH QUICK WORKFLOW CONTROLS
# =========================================================
col_brand, col_tabs, col_profile = st.columns([1.2, 2.8, 0.8], gap="small")

with col_brand:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; padding-top: 6px;">
            <span style="font-size: 1.6rem;">🤖</span>
            <span style="font-size: 1.35rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">InterviewIQ</span>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_tabs:
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        if st.button("📄 1. Resume", key="top_nav_upload", use_container_width=True, type="primary" if st.session_state.current_page == "upload" else "secondary"):
            st.session_state.current_page = "upload"
            st.rerun()
    with t2:
        if st.button("🎯 2. Role", key="top_nav_roles", use_container_width=True, type="primary" if st.session_state.current_page == "roles" else "secondary"):
            st.session_state.current_page = "roles"
            st.rerun()
    with t3:
        interview_active = st.session_state.current_page in ("intro", "intro_feedback", "question", "question_feedback")
        if st.button("🎙️ 3. Interview", key="top_nav_interview", use_container_width=True, type="primary" if interview_active else "secondary"):
            if not st.session_state.get("candidate_intro") and not st.session_state.answers_list:
                st.session_state.current_page = "intro"
            elif st.session_state.current_page not in ("intro", "intro_feedback", "question", "question_feedback"):
                st.session_state.current_page = "question"
            st.rerun()
    with t4:
        if st.button("🏆 4. Results", key="top_nav_results", use_container_width=True, type="primary" if st.session_state.current_page == "results" else "secondary"):
            st.session_state.current_page = "results"
            st.rerun()

with col_profile:
    candidate_label = st.session_state.resume_data.get("candidate_name", "Candidate")
    if candidate_label == "Candidate":
        candidate_label = "👤 Candidate"
    else:
        candidate_label = f"👤 {candidate_label}"
    st.markdown(
        f"""
        <div style="text-align: right; padding-top: 8px;">
            <span class="avatar-badge">{candidate_label}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<hr style='margin: 12px 0 20px 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)


# =========================================================
# STEP 1: SUBMIT RESUME (FIRST STEP ON LAUNCH)
# =========================================================
if st.session_state.current_page == "upload":
    render_stepper(current_step=1)

    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="color: #ffffff; font-weight: 800; font-size: 1.85rem; margin-bottom: 6px;">Step 1: Submit Your Resume</h2>
            <p style="color: #94a3b8; font-size: 0.95rem; max-width: 680px; margin: 0 auto;">
                First, submit your resume on this website. We'll analyze your skills, extract your background highlights, recommend fitting roles, and personalize your upcoming interview.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)
    c_up1, c_up2 = st.columns([1.3, 1], gap="medium")

    with c_up1:
        st.markdown(
            """
            <div class="upload-card-box" style="padding: 32px 24px; margin-bottom: 16px;">
                <div class="upload-icon" style="font-size: 2.8rem; margin-bottom: 8px;">☁️</div>
                <div class="upload-heading" style="font-size: 1.25rem;">Upload Resume Document</div>
                <div class="upload-formats" style="margin-bottom: 12px;">Supports PDF, TXT, or DOCX (Max 5MB)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        uploaded_file = st.file_uploader("Upload resume file", type=["pdf", "txt", "docx"], label_visibility="collapsed")
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            parsed = parse_resume(file_bytes=file_bytes, filename=uploaded_file.name)
            st.session_state.resume_data = parsed
            st.success(f"✅ Resume Uploaded successfully! Extracted {len(parsed.get('skills_found', []))} skills.")

        with st.expander("📝 Or paste your resume text / profile details directly", expanded=False):
            bio_text = st.text_area(
                "Paste background details",
                height=140,
                placeholder="Paste your resume text, bio, or summary here... (e.g. 4 years Software Engineer proficient in Python, SQL, React, AWS, Docker...)"
            )
            if st.button("Analyze Pasted Resume Text", use_container_width=True):
                if bio_text.strip():
                    parsed = parse_resume(file_bytes=None, raw_text=bio_text)
                    st.session_state.resume_data = parsed
                    st.success("✅ Pasted Profile Analyzed!")

    with c_up2:
        st.markdown(
            """
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 22px; margin-bottom: 16px;">
                <div style="font-weight: 700; color: #ffffff; font-size: 1rem; margin-bottom: 8px;">⚡ Quick Test Sample Profiles</div>
                <p style="color: #94a3b8; font-size: 0.85rem; line-height: 1.4; margin-bottom: 14px;">
                    Don't have a resume file on hand? Click a sample profile below to instantly populate and test the entire interview workflow:
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("👨‍💻 Load Full-Stack Engineer Profile", use_container_width=True):
            sample_fullstack = """
Alex Rivera
Email: alex.rivera@example.com | GitHub: github.com/alexrivera
Senior Full-Stack Software Engineer with 5+ years of experience architecting distributed backend services and modern frontend applications.
Technical Skills: Python, TypeScript, React, Next.js, FastAPI, Node.js, PostgreSQL, Redis, Docker, Kubernetes, AWS, System Design, Microservices, CI/CD, Git, SQL.
Experience:
- Led migration of monolith to FastAPI microservices, reducing P95 latency by 45%.
- Designed and built high-performance responsive web dashboard in React and TypeScript.
            """
            parsed = parse_resume(file_bytes=None, raw_text=sample_fullstack)
            st.session_state.resume_data = parsed
            st.session_state.selected_role = "Full-Stack Software Engineer"
            st.session_state.experience_level = "Senior (5-8 yrs)"
            st.success("✅ Loaded Alex Rivera (Senior Full-Stack Engineer) Profile!")
            st.rerun()

        if st.button("🎓 Load Fresher / Graduate Profile", use_container_width=True):
            sample_fresher = """
Rohan Sharma
Email: rohan.sharma@example.com | B.Tech Computer Science 2024 Graduate
Profile:
Motivated Computer Science graduate with strong foundations in Data Structures, Algorithms, Object-Oriented Programming, and Databases.
Technical Skills: Python, Java, C++, SQL, HTML, CSS, React, MySQL, Git, Data Structures, Algorithms, OOP.
Academic Projects:
- Intelligent Task Manager using Python Flask and MySQL.
- Interactive Pathfinding Algorithm Visualizer in JavaScript.
            """
            parsed = parse_resume(file_bytes=None, raw_text=sample_fresher)
            st.session_state.resume_data = parsed
            st.session_state.selected_role = "Fresher / Graduate Software Engineer"
            st.session_state.experience_level = "Entry / New Grad (0-1 yrs)"
            st.success("✅ Loaded Rohan Sharma (Fresher Graduate) Profile!")
            st.rerun()

    # If resume data exists, display candidate profile preview card
    if st.session_state.resume_data.get("has_resume"):
        cand_name = st.session_state.resume_data.get("candidate_name", "Candidate")
        skills = st.session_state.resume_data.get("skills_found", [])
        recommended = st.session_state.resume_data.get("recommended_roles", ["Software Engineer"])

        skills_pills_html = "".join([f"<span class='skill-badge-pill'>{s}</span>" for s in skills]) if skills else "<span style='color:#94a3b8;'>General technical background</span>"
        rec_pills_html = "".join([f"<span class='recommend-tag' style='margin-right: 8px;'>⭐ {r}</span>" for r in recommended])

        st.markdown(
            f"""
            <div class="resume-profile-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <div style="font-size: 0.8rem; font-weight: 700; color: #10b981; letter-spacing: 0.05em; text-transform: uppercase;">
                            ✓ Profile Analyzed & Ready
                        </div>
                        <div style="font-size: 1.35rem; font-weight: 800; color: #ffffff; margin-top: 2px;">
                            {cand_name}
                        </div>
                    </div>
                    <span class="badge-tag" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); color: #6ee7b7;">
                        {len(skills)} Skills Found
                    </span>
                </div>
                <div style="margin-bottom: 14px;">
                    <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600; margin-bottom: 6px;">Detected Core Skills:</div>
                    {skills_pills_html}
                </div>
                <div style="padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.08);">
                    <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600; margin-bottom: 6px;">Recommended Roles for your Background:</div>
                    {rec_pills_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br/>", unsafe_allow_html=True)
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            if st.button("Confirm Resume & Proceed to Select / Change Role ➔", type="primary", use_container_width=True):
                # Pre-select recommended role if available
                if recommended and recommended[0] in config.INTERVIEW_ROLES:
                    st.session_state.selected_role = recommended[0]
                st.session_state.current_page = "roles"
                st.rerun()
    else:
        st.markdown("<br/>", unsafe_allow_html=True)
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            if st.button("Proceed without Resume (Generic Practice) ➔", use_container_width=True):
                st.session_state.current_page = "roles"
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# STEP 2: SELECT / CHANGE ROLE
# =========================================================
elif st.session_state.current_page == "roles":
    render_stepper(current_step=2)

    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 22px;">
            <h2 style="color: #ffffff; font-weight: 800; font-size: 1.85rem; margin-bottom: 6px;">Step 2: Change / Select Target Job Role</h2>
            <p style="color: #94a3b8; font-size: 0.95rem; max-width: 680px; margin: 0 auto;">
                Next, change or select the role you want to interview for. Questions, deep-dive probes, and grading criteria will adapt immediately.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Active resume banner
    if st.session_state.resume_data.get("has_resume"):
        c_name = st.session_state.resume_data.get("candidate_name", "Candidate")
        skills_summary = ", ".join(st.session_state.resume_data.get("skills_found", [])[:4])
        st.markdown(
            f"""
            <div style="max-width: 820px; margin: 0 auto 16px auto; background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 12px; padding: 12px 18px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #93c5fd; font-weight: 700; font-size: 0.9rem;">📄 Submitted Resume Active:</span>
                    <span style="color: #ffffff; font-weight: 600; font-size: 0.9rem;"> {c_name}</span>
                    <span style="color: #94a3b8; font-size: 0.85rem;"> ({skills_summary})</span>
                </div>
                <span class="recommend-tag">Tailored Mode</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    search_col1, search_col2, search_col3 = st.columns([1, 2, 1])
    with search_col2:
        search_query = st.text_input("Search job role...", placeholder="🔍 Search job role...", label_visibility="collapsed")

    ROLES_LIST = [
        {"id": "Software Engineer", "icon": "</>", "title": "Software Engineer"},
        {"id": "Frontend & UI/UX Engineer", "icon": "🖥️", "title": "Frontend Developer"},
        {"id": "Backend & Distributed Systems Engineer", "icon": "🗄️", "title": "Backend Developer"},
        {"id": "Full-Stack Software Engineer", "icon": "🥞", "title": "Full Stack Developer"},
        {"id": "AI / Machine Learning Engineer", "icon": "🧠", "title": "AI/ML Engineer"},
        {"id": "Data Scientist & Analyst", "icon": "📈", "title": "Data Scientist"},
        {"id": "DevOps & Cloud SRE", "icon": "☁️", "title": "DevOps & Cloud SRE"},
        {"id": "Cybersecurity Analyst", "icon": "🛡️", "title": "Cybersecurity Analyst"},
        {"id": "Fresher / Graduate Software Engineer", "icon": "🎓", "title": "Fresher / Graduate"},
        {"id": "Behavioral & Leadership Screening", "icon": "💼", "title": "Behavioral & Leadership"}
    ]

    recommended_roles = st.session_state.resume_data.get("recommended_roles", [])
    filtered_roles = [r for r in ROLES_LIST if not search_query or search_query.lower() in r["title"].lower()]

    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)
    for row_start in range(0, len(filtered_roles), 3):
        cols = st.columns(3)
        for col_idx in range(3):
            role_idx = row_start + col_idx
            if role_idx < len(filtered_roles):
                role_item = filtered_roles[role_idx]
                is_selected = (st.session_state.selected_role == role_item["id"])
                is_rec = (role_item["id"] in recommended_roles)

                with cols[col_idx]:
                    card_label = f"{role_item['icon']}\n\n**{role_item['title']}**"
                    if is_rec and not is_selected:
                        card_label = f"⭐ {role_item['icon']}\n\n**{role_item['title']}**\n(Recommended)"
                    elif is_selected:
                        card_label = f"✅ {role_item['icon']}\n\n**{role_item['title']}**\n(Selected)"

                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(card_label, key=f"role_btn_{role_item['id']}", use_container_width=True, type=btn_type):
                        st.session_state.selected_role = role_item["id"]
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Configuration for Level, Persona, and Question Count
    st.markdown("<div style='max-width: 820px; margin: 18px auto 0 auto;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight: 700; color: #ffffff; font-size: 1rem; margin-bottom: 10px;'>Interview Configuration</div>", unsafe_allow_html=True)
    cfg1, cfg2, cfg3 = st.columns(3)

    with cfg1:
        st.session_state.experience_level = st.selectbox(
            "Seniority Level",
            config.EXPERIENCE_LEVELS,
            index=config.EXPERIENCE_LEVELS.index(st.session_state.experience_level) if st.session_state.experience_level in config.EXPERIENCE_LEVELS else 0
        )
    with cfg2:
        persona_names = list(config.INTERVIEWER_PERSONAS.keys())
        st.session_state.selected_persona_name = st.selectbox(
            "Interviewer Persona",
            persona_names,
            index=persona_names.index(st.session_state.selected_persona_name) if st.session_state.selected_persona_name in persona_names else 0
        )
    with cfg3:
        st.session_state.question_count = st.selectbox(
            "Question Count",
            [3, 5, 7],
            index=[3, 5, 7].index(st.session_state.question_count) if st.session_state.question_count in [3, 5, 7] else 1
        )

    # Persona preview card
    active_persona = config.INTERVIEWER_PERSONAS.get(st.session_state.selected_persona_name, {})
    st.markdown(
        f"""
        <div style="background: rgba(17, 24, 39, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 14px 18px; margin: 14px 0; display: flex; align-items: center; gap: 14px;">
            <div style="font-size: 2.2rem;">{active_persona.get('avatar', '👩‍💻')}</div>
            <div>
                <div style="color: #ffffff; font-weight: 700; font-size: 0.95rem;">{st.session_state.selected_persona_name} &bull; <span style="color: #93c5fd;">{active_persona.get('title', '')}</span></div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 2px;">{active_persona.get('style', '')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    b_c1, b_c2, b_c3 = st.columns([1, 2, 1])
    with b_c2:
        if st.button(f"Start Interview with Introduction ({st.session_state.selected_role}) ➔", type="primary", use_container_width=True):
            # Load questions for the selected role
            st.session_state.questions_list = load_role_questions(st.session_state.selected_role, st.session_state.question_count)
            # Reset interview tracking
            st.session_state.current_question_index = 0
            st.session_state.answers_list = []
            st.session_state.candidate_intro = None
            st.session_state.intro_feedback = None
            st.session_state.current_feedback = None
            st.session_state.dossier = None
            st.session_state.start_time = datetime.datetime.now()
            # Followed by interview - INCLUDING AN INTRODUCTION!
            st.session_state.current_page = "intro"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# STEP 3A: INTERVIEW - INTRODUCTION ROUND
# =========================================================
elif st.session_state.current_page == "intro":
    render_stepper(current_step=3)

    active_persona = config.INTERVIEWER_PERSONAS.get(st.session_state.selected_persona_name, {})
    interviewer_agent = InterviewAgent(
        gemini_client=gemini_client,
        role=st.session_state.selected_role,
        experience_level=st.session_state.experience_level,
        persona_name=st.session_state.selected_persona_name,
        total_questions=st.session_state.question_count,
        resume_data=st.session_state.resume_data
    )

    intro_prompt_text = interviewer_agent.get_introduction_prompt()

    st.markdown(
        f"""
        <div style="max-width: 820px; margin: 0 auto 16px auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span class="badge-tag" style="background: rgba(139, 92, 246, 0.2); border-color: rgba(139, 92, 246, 0.4); color: #c4b5fd;">
                    🎙️ Round 1: Candidate Introduction & Elevator Pitch
                </span>
                <span style="font-size: 0.85rem; color: #94a3b8; font-weight: 600;">
                    Target Role: <b style="color: #ffffff;">{st.session_state.selected_role}</b>
                </span>
            </div>
            <div class="intro-box">
                <div class="intro-interviewer-header">
                    <div class="intro-avatar">{active_persona.get('avatar', '👩‍💻')}</div>
                    <div>
                        <div style="font-weight: 800; color: #ffffff; font-size: 1.15rem;">{st.session_state.selected_persona_name}</div>
                        <div style="font-size: 0.85rem; color: #93c5fd;">{active_persona.get('title', 'Interviewer')}</div>
                    </div>
                </div>
                <div style="color: #f1f5f9; font-size: 1.1rem; line-height: 1.6; margin-bottom: 14px;">
                    {intro_prompt_text}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Neural audio playback for the introduction invitation
    if st.session_state.audio_enabled:
        audio_key = f"audio_intro_{st.session_state.selected_role}_{st.session_state.selected_persona_name}"
        if audio_key not in st.session_state:
            persona_voice = active_persona.get("voice", "en-US-JennyNeural")
            audio_bytes = generate_audio(intro_prompt_text, persona_voice)
            st.session_state[audio_key] = audio_bytes
        if st.session_state.get(audio_key):
            st.markdown("<div style='max-width: 820px; margin: 0 auto 16px auto;'>", unsafe_allow_html=True)
            st.audio(st.session_state[audio_key], format="audio/mp3")
            st.markdown("</div>", unsafe_allow_html=True)

    # Candidate Introduction Area
    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)

    # Helper button to auto-fill sample intro for rapid testing
    col_h1, col_h2 = st.columns([2, 1])
    with col_h2:
        if st.button("💡 Load Sample Introduction", use_container_width=True):
            cand_name = st.session_state.resume_data.get("candidate_name", "Alex")
            skills_str = ", ".join(st.session_state.resume_data.get("skills_found", ["Python", "System Design", "SQL"])[:3])
            sample_intro = (
                f"Hello {st.session_state.selected_persona_name}! Thank you for having me. "
                f"I'm a software engineer passionate about building scalable, high-throughput systems. "
                f"Over my career, I've specialized in full-stack architecture, API optimization, and distributed systems, working hands-on with {skills_str}. "
                f"In my most recent project, I re-architected our core data pipeline which boosted transaction processing speed by 35%. "
                f"I'm very excited about this {st.session_state.selected_role} position because I want to bring my background in high-performance engineering to your engineering team."
            )
            st.session_state["candidate_intro_text"] = sample_intro
            st.rerun()

    intro_input = st.text_area(
        "Candidate Introduction Input",
        value=st.session_state.get("candidate_intro_text", ""),
        placeholder="Introduce yourself here... Walk through your journey, technical strengths, recent key projects, and what interests you about this role.",
        height=180,
        label_visibility="collapsed"
    )

    char_count = len(intro_input)
    st.markdown(f"<div class='char-counter'>{char_count} / 1200 characters</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    c_btn1, c_btn2, c_btn3 = st.columns([1, 1, 2])

    with c_btn1:
        if st.button("Skip Introduction", use_container_width=True):
            fallback_feedback = {
                "score": 5,
                "clarity": 5,
                "confidence": 4,
                "strengths": ["Skipped introduction to proceed directly to technical questions."],
                "improvements": ["In real interviews, an opening elevator pitch establishes credibility and sets the tone."],
                "ideal_answer": "An effective introduction follows Present-Past-Future: current role, key past technical wins, and why this role fits your future.",
                "interviewer_acknowledgment": f"No problem! Let's jump straight into the technical questions for {st.session_state.selected_role}."
            }
            st.session_state.candidate_intro = "(Candidate skipped introduction)"
            st.session_state.intro_feedback = fallback_feedback
            st.session_state.answers_list.append({
                "question": "Candidate Self-Introduction & Elevator Pitch",
                "answer": "(Candidate skipped introduction)",
                "feedback": fallback_feedback,
                "is_intro": True
            })
            st.session_state.current_page = "intro_feedback"
            st.rerun()

    with c_btn3:
        if st.button("Submit Introduction ➔", type="primary", use_container_width=True):
            if not intro_input.strip():
                st.warning("Please enter your self-introduction above, or click 'Skip Introduction' or 'Load Sample Introduction'.")
            else:
                with st.spinner("AI Bar-Raiser evaluating your introduction..."):
                    feedback = evaluator_agent.evaluate_introduction(
                        introduction=intro_input,
                        role=st.session_state.selected_role,
                        experience_level=st.session_state.experience_level,
                        persona_name=st.session_state.selected_persona_name,
                        skills_found=st.session_state.resume_data.get("skills_found", [])
                    )

                    st.session_state.candidate_intro = intro_input
                    st.session_state.intro_feedback = feedback
                    st.session_state.answers_list.append({
                        "question": "Candidate Self-Introduction & Elevator Pitch",
                        "answer": intro_input,
                        "feedback": feedback,
                        "is_intro": True
                    })
                    st.session_state.current_page = "intro_feedback"
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# STEP 3B: INTERVIEW - INTRODUCTION FEEDBACK & TRANSITION
# =========================================================
elif st.session_state.current_page == "intro_feedback":
    render_stepper(current_step=3)

    feedback = st.session_state.intro_feedback or {
        "score": 8,
        "clarity": 8,
        "confidence": 8,
        "strengths": ["Clear narrative flow from background to technical skills."],
        "improvements": ["Add a quantifiable metric from a recent project."],
        "ideal_answer": "A compelling Staff-level introduction follows Present-Past-Future.",
        "interviewer_acknowledgment": f"Thank you for that introduction! Let's dive into technical questions for {st.session_state.selected_role}."
    }

    score_val = feedback.get("score", 8)
    strengths = feedback.get("strengths", ["Clear explanation of technical background."])
    improvements = feedback.get("improvements", ["Elaborate on specific project impact metrics."])
    ideal_ans = feedback.get("ideal_answer", "")
    ack_msg = feedback.get("interviewer_acknowledgment", f"Thank you for that introduction! Let's dive into our technical questions for {st.session_state.selected_role}.")

    st.markdown(
        """
        <div style="max-width: 820px; margin: 0 auto 20px auto;">
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 20px;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: rgba(16, 185, 129, 0.2); border: 2px solid #10b981; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">✓</div>
                <div>
                    <h2 style="color: #ffffff; font-weight: 800; font-size: 1.55rem; margin: 0;">Introduction Round Complete!</h2>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin: 2px 0 0 0;">Here is the AI Bar-Raiser coaching feedback on your opening introduction.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)
    col_s1, col_s2 = st.columns([1, 2], gap="medium")

    with col_s1:
        st.markdown(
            f"""
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 26px 18px; text-align: center;">
                <div class="eval-score-ring">
                    <span class="eval-score-val">{score_val}</span>
                    <span class="eval-score-max">/ 10</span>
                </div>
                <div style="font-weight: 700; color: #ffffff; font-size: 1.1rem; margin-top: 8px;">Introduction Score</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">First impression & clarity rating</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_s2:
        strengths_html = "".join([
            f"<div class='feedback-bullet'><span class='bullet-icon-good'>✓</span><span style='color: #e2e8f0;'>{s}</span></div>"
            for s in strengths
        ])
        improvements_html = "".join([
            f"<div class='feedback-bullet'><span class='bullet-icon-warn'>⚠️</span><span style='color: #cbd5e1;'>{imp}</span></div>"
            for imp in improvements
        ])

        st.markdown(
            f"""
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 24px;">
                <div style="font-weight: 700; color: #ffffff; font-size: 1.1rem; margin-bottom: 14px;">Coaching Highlights</div>
                {strengths_html}
                {improvements_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Ideal Benchmark Elevator Pitch
    st.markdown(
        f"""
        <div class="ideal-answer-box">
            <div class="ideal-title">
                <span>💡</span>
                <span>Model Staff-Level Elevator Pitch</span>
            </div>
            <div style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">
                {ideal_ans}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Interviewer Persona Acknowledgment Box
    persona = config.INTERVIEWER_PERSONAS.get(st.session_state.selected_persona_name, {})
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 16px; padding: 20px 24px; margin-top: 20px; display: flex; align-items: center; gap: 16px;">
            <div style="font-size: 2.2rem;">{persona.get('avatar', '👩‍💻')}</div>
            <div>
                <div style="font-weight: 700; color: #93c5fd; font-size: 0.9rem;">{st.session_state.selected_persona_name} (Interviewer):</div>
                <div style="color: #ffffff; font-size: 1rem; margin-top: 4px; line-height: 1.5;">"{ack_msg}"</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    c_act1, c_act2 = st.columns([1, 1])
    with c_act2:
        if st.button("Proceed to Technical Questions (Question 1) ➔", type="primary", use_container_width=True):
            st.session_state.current_page = "question"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# STEP 3C: INTERVIEW - TECHNICAL QUESTIONS
# =========================================================
elif st.session_state.current_page == "question":
    render_stepper(current_step=3)

    # Quick Switcher Bar
    st.markdown("<div style='max-width: 820px; margin: 0 auto 12px auto;'>", unsafe_allow_html=True)
    c_role, c_lvl, c_rst = st.columns([1.5, 1.2, 0.9])
    with c_role:
        st.markdown(f"<div style='padding-top: 6px; font-weight: 700; color: #ffffff;'>Role: {st.session_state.selected_role}</div>", unsafe_allow_html=True)
    with c_lvl:
        st.markdown(f"<div style='padding-top: 6px; color: #94a3b8;'>Level: {st.session_state.experience_level}</div>", unsafe_allow_html=True)
    with c_rst:
        if st.button("🔄 Restart Interview", use_container_width=True):
            st.session_state.current_question_index = 0
            st.session_state.answers_list = []
            st.session_state.candidate_intro = None
            st.session_state.intro_feedback = None
            st.session_state.current_feedback = None
            st.session_state.dossier = None
            st.session_state.start_time = datetime.datetime.now()
            st.session_state.current_page = "intro"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.questions_list:
        st.session_state.questions_list = load_role_questions(st.session_state.selected_role, st.session_state.question_count)

    idx = st.session_state.current_question_index
    total_q = len(st.session_state.questions_list)

    if idx >= total_q:
        # All questions finished -> redirect to results
        st.session_state.current_page = "results"
        st.rerun()

    current_q_data = st.session_state.questions_list[idx]
    q_text = current_q_data.get("question", "Explain your technical approach to building scalable software.")
    q_phase = current_q_data.get("phase", "Technical")

    st.markdown(
        f"""
        <div class="question-card" style="max-width: 820px;">
            <div class="question-top-row">
                <span class="question-counter">Technical Question {idx + 1} of {total_q}</span>
                <span class="badge-tag">{q_phase}</span>
            </div>
            <div class="question-text">{q_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Audio synthesis for question
    if st.session_state.audio_enabled:
        audio_key = f"audio_q_{idx}_{st.session_state.selected_role}"
        if audio_key not in st.session_state:
            persona_voice = config.INTERVIEWER_PERSONAS.get(st.session_state.selected_persona_name, {}).get("voice", "en-US-JennyNeural")
            audio_bytes = generate_audio(q_text, persona_voice)
            st.session_state[audio_key] = audio_bytes
        if st.session_state.get(audio_key):
            st.markdown("<div style='max-width: 820px; margin: 0 auto 14px auto;'>", unsafe_allow_html=True)
            st.audio(st.session_state[audio_key], format="audio/mp3")
            st.markdown("</div>", unsafe_allow_html=True)

    # Candidate Answer Area
    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)
    answer_input = st.text_area(
        "Candidate Answer Input",
        key=f"user_ans_{idx}",
        placeholder="Type your answer here...",
        height=180,
        label_visibility="collapsed"
    )

    char_count = len(answer_input)
    st.markdown(f"<div class='char-counter'>{char_count} / 1000 characters</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    col_act1, col_act2, col_act3 = st.columns([1, 1, 2])

    with col_act1:
        if st.button("Skip Question", use_container_width=True):
            feedback = {
                "score": 4,
                "clarity": 5,
                "depth": 3,
                "strengths": ["Skipped to maintain interview pacing."],
                "improvements": ["Try providing foundational concepts or bullet points even on unfamiliar topics."],
                "ideal_answer": current_q_data.get("ideal_answer", "Define the core concepts, time/space complexity, and trade-offs."),
                "pro_tip": "When unsure, explain your thought process out loud to show problem-solving capability."
            }
            st.session_state.answers_list.append({
                "question": q_text,
                "answer": "(Candidate skipped this question)",
                "feedback": feedback,
                "is_intro": False
            })
            st.session_state.current_feedback = feedback
            st.session_state.current_page = "question_feedback"
            st.rerun()

    with col_act3:
        if st.button("Submit Answer ➔", type="primary", use_container_width=True):
            if not answer_input.strip():
                st.warning("Please type your response before submitting, or click 'Skip Question'.")
            else:
                with st.spinner("AI Bar-Raiser evaluating your answer..."):
                    feedback = evaluator_agent.evaluate_single_answer(
                        question=q_text,
                        answer=answer_input,
                        role=st.session_state.selected_role,
                        experience_level=st.session_state.experience_level,
                        criteria=current_q_data.get("criteria", "")
                    )

                    # Ensure ideal_answer is present
                    if not feedback.get("ideal_answer"):
                        feedback["ideal_answer"] = current_q_data.get(
                            "ideal_answer",
                            "A comprehensive Staff-level answer clearly defines the fundamental concepts, explains time/space complexity, and provides concrete real-world use cases."
                        )

                    st.session_state.answers_list.append({
                        "question": q_text,
                        "answer": answer_input,
                        "feedback": feedback,
                        "is_intro": False
                    })
                    st.session_state.current_feedback = feedback
                    st.session_state.current_page = "question_feedback"
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# STEP 3D: INTERVIEW - QUESTION FEEDBACK SCREEN
# =========================================================
elif st.session_state.current_page == "question_feedback":
    render_stepper(current_step=3)

    feedback = st.session_state.current_feedback or {
        "score": 8,
        "strengths": ["You explained the key differences correctly.", "Your examples were relevant and clear."],
        "improvements": ["Try to be more specific about real-world production trade-offs."],
        "ideal_answer": "A comprehensive Staff-level answer covers foundational definitions, complexity analysis, and concrete architecture use cases."
    }

    score_val = feedback.get("score", 8)
    strengths = feedback.get("strengths", ["Clear explanation of core concepts."])
    improvements = feedback.get("improvements", ["Elaborate on production failure modes and trade-offs."])
    ideal_ans = feedback.get("ideal_answer", "A comprehensive Staff-level answer covers foundational definitions, complexity analysis, and concrete architecture use cases.")

    # Header with green checkmark
    st.markdown(
        """
        <div style="max-width: 820px; margin: 0 auto 20px auto;">
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 20px;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: rgba(16, 185, 129, 0.2); border: 2px solid #10b981; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">✓</div>
                <div>
                    <h2 style="color: #ffffff; font-weight: 800; font-size: 1.55rem; margin: 0;">AI Evaluation Complete!</h2>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin: 2px 0 0 0;">Here's your performance and feedback for this question.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)
    col_s1, col_s2 = st.columns([1, 2], gap="medium")

    with col_s1:
        st.markdown(
            f"""
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 26px 18px; text-align: center;">
                <div class="eval-score-ring">
                    <span class="eval-score-val">{score_val}</span>
                    <span class="eval-score-max">/ 10</span>
                </div>
                <div style="font-weight: 700; color: #ffffff; font-size: 1.1rem; margin-top: 8px;">Your Score</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">Question Bar-Raiser Rating</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_s2:
        strengths_html = "".join([
            f"<div class='feedback-bullet'><span class='bullet-icon-good'>✓</span><span style='color: #e2e8f0;'>{s}</span></div>"
            for s in strengths
        ])
        improvements_html = "".join([
            f"<div class='feedback-bullet'><span class='bullet-icon-warn'>⚠️</span><span style='color: #cbd5e1;'>{imp}</span></div>"
            for imp in improvements
        ])

        st.markdown(
            f"""
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 24px;">
                <div style="font-weight: 700; color: #ffffff; font-size: 1.1rem; margin-bottom: 14px;">Feedback</div>
                {strengths_html}
                {improvements_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Ideal Answer Callout
    st.markdown(
        f"""
        <div class="ideal-answer-box">
            <div class="ideal-title">
                <span>💡</span>
                <span>Ideal Answer</span>
            </div>
            <div style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">
                {ideal_ans}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 2])

    current_idx = st.session_state.current_question_index
    total_q = len(st.session_state.questions_list)
    has_more = (current_idx + 1 < total_q)

    with col_nav3:
        if has_more:
            if st.button("Next Question ➔", type="primary", use_container_width=True):
                st.session_state.current_question_index += 1
                st.session_state.current_page = "question"
                st.rerun()
        else:
            if st.button("Complete Interview & Announce Results ➔", type="primary", use_container_width=True):
                with st.spinner("Compiling comprehensive Scorecard & Bar-Raiser Dossier..."):
                    # Calculate overall score taking into account all evaluated turns (including introduction!)
                    scores = [item["feedback"].get("score", 7) * 10 for item in st.session_state.answers_list if item.get("feedback")]
                    avg_score = int(sum(scores) / len(scores)) if scores else 82
                    avg_score = min(98, max(50, avg_score))

                    if avg_score >= 85:
                        recommendation = "Strong Hire"
                    elif avg_score >= 75:
                        recommendation = "Hire"
                    elif avg_score >= 65:
                        recommendation = "Lean Hire"
                    else:
                        recommendation = "No Hire"

                    intro_score = st.session_state.intro_feedback.get("score", 8) * 10 if st.session_state.intro_feedback else avg_score

                    st.session_state.dossier = {
                        "overall_score": avg_score,
                        "recommendation": recommendation,
                        "competencies": {
                            "Introduction & First Impression": min(98, intro_score),
                            "Technical Knowledge": min(98, avg_score + 3),
                            "Architecture & Systems": min(95, avg_score - 1),
                            "Problem Solving": avg_score,
                            "Communication & Clarity": min(95, int((intro_score + avg_score) / 2))
                        }
                    }

                    if st.session_state.start_time:
                        elapsed_secs = (datetime.datetime.now() - st.session_state.start_time).total_seconds()
                        st.session_state.elapsed_minutes = max(1, int(elapsed_secs // 60))

                    st.session_state.current_page = "results"
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# STEP 4: FINAL RESULTS ANNOUNCED SCREEN
# =========================================================
elif st.session_state.current_page == "results":
    render_stepper(current_step=4)

    dossier = st.session_state.dossier or {
        "overall_score": 85,
        "recommendation": "Strong Hire",
        "competencies": {
            "Introduction & First Impression": 85,
            "Technical Knowledge": 88,
            "Architecture & Systems": 82,
            "Problem Solving": 85,
            "Communication & Clarity": 84
        }
    }

    final_score = dossier.get("overall_score", 85)
    rec_verdict = dossier.get("recommendation", "Strong Hire")
    total_rounds = len(st.session_state.answers_list) if st.session_state.answers_list else 5
    elapsed_time = f"{st.session_state.get('elapsed_minutes', 12)} min"
    cand_name = st.session_state.resume_data.get("candidate_name", "Candidate")

    st.markdown(
        f"""
        <div style="max-width: 820px; margin: 0 auto; text-align: center; margin-bottom: 24px;">
            <div class="announcement-badge">🏆 OFFICIAL INTERVIEW RESULT ANNOUNCED</div>
            <h1 class="results-header-title" style="margin-bottom: 6px;">Your Interview Performance Dossier</h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Official evaluation for <b style="color: #ffffff;">{cand_name}</b> applying for <b style="color: #93c5fd;">{st.session_state.selected_role}</b> ({st.session_state.experience_level}) conducted by <b style="color: #ffffff;">{st.session_state.selected_persona_name}</b>.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4 Top KPI Cards
    st.markdown(
        f"""
        <div style="max-width: 820px; margin: 0 auto 24px auto;" class="kpi-row">
            <div class="kpi-card" style="border-color: rgba(59, 130, 246, 0.5); background: rgba(59, 130, 246, 0.1);">
                <div class="kpi-label">Final Score (Out of 100)</div>
                <div class="kpi-value kpi-highlight">{final_score} <span style="font-size: 1.1rem; color: #94a3b8;">/ 100</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Hiring Verdict</div>
                <div class="kpi-value" style="color: #10b981; font-size: 1.6rem; padding-top: 6px;">{rec_verdict}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Rounds Completed</div>
                <div class="kpi-value">{total_rounds} <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 500;">(Intro + Qs)</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Performance Overview Progress Bars
    st.markdown(
        """
        <div style="max-width: 820px; margin: 0 auto; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 18px; padding: 26px 30px; margin-bottom: 24px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-bottom: 20px;">Competency Score Breakdown</div>
        """,
        unsafe_allow_html=True
    )

    competencies = dossier.get("competencies", {
        "Introduction & First Impression": 85,
        "Technical Knowledge": 88,
        "Architecture & Systems": 82,
        "Problem Solving": 85,
        "Communication & Clarity": 84
    })

    bar_colors = ["#8b5cf6", "#3b82f6", "#06b6d4", "#f97316", "#10b981"]
    for i, (comp_name, comp_val) in enumerate(competencies.items()):
        color = bar_colors[i % len(bar_colors)]
        st.markdown(
            f"""
            <div class="perf-bar-row">
                <div class="perf-bar-label">{comp_name}</div>
                <div class="perf-track">
                    <div class="perf-fill" style="width: {comp_val}%; background: {color};"></div>
                </div>
                <div class="perf-bar-score" style="color: {color};">{comp_val} / 100</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Blue Verdict Banner (Trophy Card)
    st.markdown(
        f"""
        <div style="max-width: 820px; margin: 0 auto 24px auto;" class="verdict-blue-card">
            <div class="verdict-trophy-icon">🏆</div>
            <div>
                <div class="verdict-text-title">Result Announced: {rec_verdict}!</div>
                <div class="verdict-text-sub">
                    You completed the comprehensive interview with an overall score of <b>{final_score} out of 100</b>. Your technical readiness and communication indicate strong potential for the <b>{st.session_state.selected_role}</b> track.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Turn-by-Turn Q&A Detailed Breakdown Expander
    if st.session_state.answers_list:
        with st.expander("📋 View Turn-by-Turn Review (Introduction & Technical Questions)", expanded=False):
            for i, item in enumerate(st.session_state.answers_list):
                round_title = f"Round {i+1}: {item['question']}"
                fb = item.get("feedback", {})
                score = fb.get("score", 7)
                st.markdown(f"### {round_title}")
                st.markdown(f"**Your Answer:**\n> {item['answer']}")
                st.markdown(f"**Score:** `{score}/10`")
                if fb.get("strengths"):
                    st.markdown("**Strengths:** " + ", ".join(fb["strengths"]))
                if fb.get("improvements"):
                    st.markdown("**Areas for Growth:** " + ", ".join(fb["improvements"]))
                if fb.get("ideal_answer"):
                    st.markdown(f"**Staff-Level Benchmark Answer:**\n> {fb['ideal_answer']}")
                st.markdown("---")

    # Action Buttons: Download & Restart
    st.markdown("<div style='max-width: 820px; margin: 0 auto;'>", unsafe_allow_html=True)
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        if st.button("🔄 Start New Interview (Submit Resume) ➔", type="primary", use_container_width=True):
            st.session_state.current_page = "upload"
            st.session_state.current_question_index = 0
            st.session_state.answers_list = []
            st.session_state.candidate_intro = None
            st.session_state.intro_feedback = None
            st.session_state.current_feedback = None
            st.session_state.dossier = None
            st.session_state.start_time = None
            st.rerun()

    with col_act2:
        report_data = {
            "candidate_name": cand_name,
            "candidate_role": st.session_state.selected_role,
            "seniority_level": st.session_state.experience_level,
            "interviewer": st.session_state.selected_persona_name,
            "overall_score_out_of_100": final_score,
            "recommendation": rec_verdict,
            "competencies": competencies,
            "total_rounds": total_rounds,
            "time_taken": elapsed_time,
            "rounds_breakdown": [
                {
                    "round_title": a["question"],
                    "candidate_response": a["answer"],
                    "score_out_of_10": a["feedback"].get("score"),
                    "strengths": a["feedback"].get("strengths"),
                    "improvements": a["feedback"].get("improvements"),
                    "ideal_answer": a["feedback"].get("ideal_answer")
                }
                for a in st.session_state.answers_list
            ]
        }
        json_report = json.dumps(report_data, indent=2)
        st.download_button(
            "📥 Download Hiring Committee Report (JSON)",
            data=json_report,
            file_name=f"InterviewIQ_Results_{st.session_state.selected_role.replace(' ', '_')}_{cand_name.replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# SCREEN: LANDING PAGE (OPTIONAL OVERVIEW)
# =========================================================
elif st.session_state.current_page == "landing":
    col_hero_text, col_hero_card = st.columns([1.2, 0.8], gap="large")

    with col_hero_text:
        st.markdown(
            """
            <div class="landing-hero" style="background: transparent; border: none; padding: 10px 0; box-shadow: none;">
                <h1 class="landing-title">Your AI Interview<br/>Partner</h1>
                <p class="landing-subtitle">
                    Submit your resume, change or select your target role, practice with an AI Bar-Raiser—starting with your introduction—and get your comprehensive result announced.
                </p>
                <div class="feature-pill-grid">
                    <div class="feature-pill">
                        <span>📄</span>
                        <div>1. Submit Resume<br/><small style="color: #94a3b8;">(Skill Extraction)</small></div>
                    </div>
                    <div class="feature-pill">
                        <span>🎯</span>
                        <div>2. Change Role<br/><small style="color: #94a3b8;">(Role Matching)</small></div>
                    </div>
                    <div class="feature-pill">
                        <span>🎙️</span>
                        <div>3. Interview & Intro<br/><small style="color: #94a3b8;">(Bar-Raiser Q&A)</small></div>
                    </div>
                    <div class="feature-pill">
                        <span>🏆</span>
                        <div>4. Result Announced<br/><small style="color: #94a3b8;">(Score out of 100)</small></div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Begin Workflow: Submit Resume ➔", type="primary", use_container_width=False):
            st.session_state.current_page = "upload"
            st.rerun()

    with col_hero_card:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 20px; padding: 32px; text-align: center; margin-top: 20px; box-shadow: 0 15px 35px -5px rgba(0,0,0,0.4);">
                <div style="font-size: 4.5rem; margin-bottom: 12px;">📑🤖</div>
                <h3 style="color: #ffffff; margin-bottom: 8px;">InterviewIQ AI Engine</h3>
                <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.5;">
                    Simulate real-world technical and behavioral interviews with autonomous AI bar-raisers. Includes introduction round, live answer evaluation, and official score out of 100.
                </p>
                <div style="margin-top: 24px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 12px; color: #93c5fd; font-weight: 600; font-size: 0.9rem;">
                    🎯 4-Step Structured Interview Workflow
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
