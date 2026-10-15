# 🎙️ InterviewIQ - Autonomous Multi-Agent Interviewer & Career Coach

**InterviewIQ** is an intelligent, multi-agent AI system designed to simulate realistic technical and behavioral interviews, conduct dynamic deep-dive questioning, provide real-time coaching analytics, and produce comprehensive hiring dossiers with actionable feedback.

Built with **Python**, **Streamlit**, and the official **Google Gemini GenAI SDK**.

---

## 🌟 Key Features

1. **Autonomous Interviewer Personas**:
   - **Dr. Elena Vance (Principal Systems Architect)**: Deep architectural trade-offs, scalability, and incisive technical probing.
   - **Marcus Reed (Engineering Director & Talent Lead)**: Leadership, team collaboration, STAR behavioral situations, and technical decisions.
   - **Aria Chen (Startup Founder & CTO)**: Fast-paced execution, full-stack pragmatism, and problem-solving.
   - **Sophia Sterling (Executive Talent & Behavioral Partner)**: Culture alignment, conflict resolution, and communication.

2. **Personalized Context (Resume & Job Description)**:
   - Upload PDF or TXT resumes (or paste candidate bio).
   - Paste target job descriptions.
   - The AI agent tailors questions directly to your background and the target job requirements.

3. **Neural Text-to-Speech (TTS)**:
   - Powered by `edge-tts` to speak questions aloud with natural human neural voices.

4. **Dynamic Probing & Follow-Up Questions**:
   - The interviewer doesn't just read a static script; it listens, reacts to your answer, and asks follow-ups on edge cases, trade-offs, and failure recovery.

5. **Real-Time Coaching & STAR Telemetry**:
   - Live STAR (Situation, Task, Action, Result) detection.
   - Real-time scoring on Clarity and Technical Depth.
   - Staff-level elevation tips after every answer.

6. **Comprehensive Hiring Committee Dossier**:
   - Overall hiring score (0-100) and hiring recommendation (*Strong Hire, Hire, Lean Hire, No Hire*).
   - Core Competency breakdown chart (Technical Proficiency, Architecture, Problem Solving, Clarity, Leadership).
   - Turn-by-turn question analysis with benchmark Staff-level answers.
   - One-click exportable Markdown report.

7. **Smart Simulation Mode (Zero Configuration Required)**:
   - Run immediately out of the box with intelligent fallback simulation.
   - Seamlessly connect your Google Gemini API key to unlock full autonomous reasoning.

---

## 🔄 End-to-End Interview Workflow

1. **📄 Step 1: Submit Resume**:
   - Upload your resume document (PDF, TXT, DOCX), paste candidate bio, or 1-click load pre-built sample profiles (e.g. Senior Full-Stack or Fresher Graduate).
   - Extracts skills, ATS highlights, candidate name, and recommends matching job tracks.

2. **🎯 Step 2: Change / Select Role**:
   - Change or select your target job role from curated tracks (highlighted with recommendation badges based on your resume).
   - Customize seniority level, interviewer persona, and question count.

3. **🎙️ Step 3: Interview (Including Introduction)**:
   - **Introduction Round**: The interviewer persona welcomes you and invites you to introduce yourself. The AI evaluates your opening elevator pitch and offers Staff-level coaching.
   - **Technical Deep-Dives**: Role-specific technical questions with neural audio voice and per-question Bar-Raiser evaluations.

4. **🏆 Step 4: Result Announced**:
   - Grand official result announcement with score out of 100, official hiring verdict (*Strong Hire, Hire, Lean Hire, No Hire*), competency score breakdown, turn-by-turn transcript review, and JSON export.

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Python 3.10+ is installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Set your Gemini API Key
You can get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).

Set it in a `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*Or simply paste it into the Gemini API Settings in the web sidebar.*

### 4. Launch the Streamlit App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📁 Project Architecture

```
e:\ROHIT_AI_AGENT\
├── app.py                     # Main Streamlit Dashboard Application
├── config.py                  # Presets, Personas, Roles & Model configs
├── requirements.txt           # Project dependencies
├── .env.example               # Environment variables template
├── README.md                  # Documentation
├── core/
│   ├── __init__.py
│   ├── gemini_client.py       # Google GenAI SDK integration with fallback
│   ├── interview_agent.py     # Autonomous Interviewer Agent & state machine
│   ├── evaluator_agent.py     # Real-time answer analyzer & evaluation dossier
│   ├── tts_service.py         # Neural TTS voice synthesis (edge-tts)
│   └── resume_parser.py       # PDF/Text resume parser & skill extractor
├── assets/
│   └── style.css              # Dark glassmorphic theme styling
└── data/
    └── interview_roles.json   # Curated questions, probes, and grading criteria
```

---

## 🎯 Supported Interview Tracks
- **Software Engineer (Core CS, Data Structures, System Concepts)**
- **Fresher / Graduate Software Engineer (Campus & New Grad Prep)**
- **Full-Stack Software Engineer**
- **Backend & Distributed Systems Engineer**
- **Frontend & UI/UX Engineer**
- **AI / Machine Learning Engineer**
- **Data Scientist & Analyst**
- **Product Manager (Technical)**
- **DevOps & Cloud SRE**
- **Behavioral & Leadership Screening**
- **Custom Role** (Specify your custom title & JD)

---

## 📄 License
MIT License. Built for candidates and hiring managers to level up interview readiness.
