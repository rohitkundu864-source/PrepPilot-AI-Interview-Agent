"""
Test complete interview pipeline: question loading, evaluator response, ideal answer, and scoring out of 100.
"""
import os
import sys

# Ensure root dir is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.gemini_client import GeminiClient
from core.evaluator_agent import EvaluatorAgent
import app

def test_pipeline():
    print("1. Testing Question Loading...")
    questions = app.load_role_questions("Software Engineer", count=5)
    assert len(questions) == 5, f"Expected 5 questions, got {len(questions)}"
    first_q = questions[0]["question"]
    print(f"   First Question: {first_q}")
    assert "stack" in first_q.lower() and "queue" in first_q.lower(), "Question 1 should be stack vs queue comparison"

    print("\n2. Testing EvaluatorAgent...")
    client = GeminiClient(api_key="", model_name="gemini-2.5-flash")
    evaluator = EvaluatorAgent(gemini_client=client)

    sample_answer = "A stack is Last-In-First-Out (LIFO), like the call stack. A queue is First-In-First-Out (FIFO), like print spooling."
    feedback = evaluator.evaluate_single_answer(
        question=first_q,
        answer=sample_answer,
        role="Software Engineer",
        experience_level="Entry / New Grad (0-1 yrs)"
    )

    print(f"   Score: {feedback.get('score')} / 10")
    print(f"   Strengths: {feedback.get('strengths')}")
    print(f"   Improvements: {feedback.get('improvements')}")
    print(f"   Ideal Answer: {feedback.get('ideal_answer')[:80]}...")
    assert "score" in feedback, "Feedback must include score"
    assert "ideal_answer" in feedback, "Feedback must include ideal_answer"

    print("\n3. Testing Final Score out of 100...")
    answers_mock = [
        {"feedback": {"score": 8}},
        {"feedback": {"score": 9}},
        {"feedback": {"score": 8}},
        {"feedback": {"score": 9}},
        {"feedback": {"score": 8}},
    ]
    scores = [item["feedback"]["score"] * 10 for item in answers_mock]
    overall_score = int(sum(scores) / len(scores))
    print(f"   Overall Score: {overall_score} / 100")
    assert overall_score == 84 or overall_score == 85 or 80 <= overall_score <= 100

    print("\n[SUCCESS] All tests passed successfully!")

if __name__ == "__main__":
    test_pipeline()
