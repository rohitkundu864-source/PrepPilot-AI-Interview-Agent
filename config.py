import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

APP_NAME = "InterviewIQ"
APP_TAGLINE = "Next-Generation Autonomous Multi-Agent Interviewer & Career Coach"
APP_VERSION = "2.0.0"

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

DEFAULT_MODEL = "gemini-2.5-flash"

INTERVIEWER_PERSONAS = {
    "Dr. Elena Vance": {
        "title": "Principal Systems Architect",
        "style": "Rigorous, analytical, asks deep architectural trade-off questions, polite yet incisive.",
        "voice": "en-US-JennyNeural",
        "avatar": "👩‍💻",
        "greeting": "Hello! I am Dr. Elena Vance. Today we will explore your technical depth, architectural instincts, and problem-solving methodology. Let's make this an engaging conversation."
    },
    "Marcus Reed": {
        "title": "Engineering Director & Talent Lead",
        "style": "Balanced, supportive, evaluates leadership, team dynamics, STAR behavioral responses, and high-level technical decisions.",
        "voice": "en-US-GuyNeural",
        "avatar": "👨‍💼",
        "greeting": "Welcome! I'm Marcus Reed. My goal today is to understand not just what you've built, but how you collaborate, make trade-offs, and handle challenging engineering problems."
    },
    "Aria Chen": {
        "title": "Startup Founder & CTO",
        "style": "Fast-paced, pragmatic, focused on speed of execution, full-stack instincts, and real-world impact.",
        "voice": "en-US-AriaNeural",
        "avatar": "🚀",
        "greeting": "Hey there! I'm Aria Chen. We move fast and love candidates who can think on their feet, balance clean code with business delivery, and solve tricky challenges."
    },
    "Sophia Sterling": {
        "title": "Executive Talent & Behavioral Partner",
        "style": "Empathetic, observant, probes behavioral situations (STAR method), communication clarity, and conflict management.",
        "voice": "en-GB-SoniaNeural",
        "avatar": "💼",
        "greeting": "Good day! I'm Sophia Sterling. I'm excited to learn more about your career trajectory, how you work with cross-functional teams, and how you approach professional challenges."
    }
}

INTERVIEW_ROLES = {
    "Software Engineer": {
        "skills": ["Data Structures", "Algorithms", "System Architecture", "Concurrency", "APIs & CI/CD", "Problem Solving"],
        "description": "Comprehensive engineering evaluation covering data structures, algorithmic efficiency, clean code, REST APIs, and system fundamentals."
    },
    "Fresher / Graduate Software Engineer": {
        "skills": ["Data Structures & Algorithms", "OOP Fundamentals", "SQL & Database Basics", "Web Fundamentals (HTML/CSS/JS/APIs)", "Problem Solving", "Academic Projects"],
        "description": "Tailored for fresh college graduates and campus hiring: focuses on core CS fundamentals, OOP, SQL queries, data structures, and capstone project walkthroughs."
    },
    "Full-Stack Software Engineer": {
        "skills": ["JavaScript / TypeScript", "React / Vue", "Node / Python / Go", "REST / GraphQL", "Databases & ORMs", "System Design"],
        "description": "Evaluates end-to-end development capabilities from responsive frontend design to scalable backend APIs and database modeling."
    },
    "Backend & Distributed Systems Engineer": {
        "skills": ["Microservices", "Concurrency & Async", "Caching & Redis", "Kafka / Messaging", "SQL & NoSQL optimization", "API Security"],
        "description": "Focuses on high-throughput backend services, data consistency, scalability, fault tolerance, and API architecture."
    },
    "Frontend & UI/UX Engineer": {
        "skills": ["React / Modern Web", "Web Performance (Core Web Vitals)", "State Management", "CSS / Responsive UI", "Browser Internals", "Accessibility"],
        "description": "Tests deep UI engineering, DOM performance, rendering pipelines, state architecture, and accessible user experiences."
    },
    "AI / Machine Learning Engineer": {
        "skills": ["PyTorch / TensorFlow", "LLMs & Prompt Engineering", "Vector DBs & RAG", "Model Evaluation", "MLOps & Pipelines", "Transformers"],
        "description": "Examines generative AI applications, deep learning fundamentals, RAG pipelines, model deployment, and optimization."
    },
    "Data Scientist & Analyst": {
        "skills": ["Python & Pandas", "SQL & BigQuery", "Statistical Modeling", "A/B Testing", "Feature Engineering", "Data Storytelling"],
        "description": "Explores statistical experimentation, hypothesis testing, machine learning algorithms, and deriving business insights from data."
    },
    "Product Manager (Technical)": {
        "skills": ["Product Strategy", "User Journey Mapping", "Metrics & KPIs (North Star)", "Technical Feasibility", "Prioritization Frameworks (RICE)", "Stakeholder Management"],
        "description": "Evaluates product vision, data-informed prioritization, cross-functional engineering alignment, and user empathy."
    },
    "DevOps & Cloud SRE": {
        "skills": ["Kubernetes & Docker", "CI/CD Pipelines", "Terraform / IaC", "AWS / GCP / Azure", "Monitoring & Observability (Prometheus/Grafana)", "Incident Response"],
        "description": "Tests reliability engineering, automated deployments, infrastructure as code, cloud security, and zero-downtime architecture."
    },
    "Behavioral & Leadership Screening": {
        "skills": ["STAR Method", "Conflict Resolution", "Mentorship", "Cross-Functional Influence", "Resilience & Ownership", "Handling Ambiguity"],
        "description": "Comprehensive behavioral screening focusing on culture fit, team leadership, navigating failures, and high-impact accomplishments."
    },
    "Custom Role": {
        "skills": ["Domain-Specific Expertise", "Communication", "Problem Solving"],
        "description": "Define your custom job title and job description to generate ultra-tailored interview sessions."
    }
}

EXPERIENCE_LEVELS = [
    "Entry / New Grad (0-1 yrs)",
    "Mid-Level (2-4 yrs)",
    "Senior (5-8 yrs)",
    "Staff / Principal / Lead (8+ yrs)"
]

INTERVIEW_MODES = {
    "Interactive Practice Mode": {
        "description": "Includes real-time feedback, STAR structure detection, coaching tips, and hints after each question.",
        "badge": "🎓 Practice & Coach"
    },
    "Strict Mock Interview": {
        "description": "Simulates a formal real-world interview session without interruptions. Generates a comprehensive Scorecard & Evaluation Report at the end.",
        "badge": "⏱️ Real Simulation"
    }
}

INTERVIEW_FOCUS_AREAS = [
    "💻 Coding & Data Structures (DSA)",
    "🏗️ Core CS Fundamentals (OOP, SQL, Web)",
    "🚀 Practical Architecture & Systems",
    "🎯 Balanced Full Technical Assessment",
]
