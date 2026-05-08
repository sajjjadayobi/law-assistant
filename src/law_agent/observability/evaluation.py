"""
Evaluation framework for Law Agent using LLM-as-Judge.

Implements:
- Golden eval set (50 QA pairs)
- LLM-as-Judge grading (pass/fail + reasoning)
- Error analysis and categorization
- Eval-driven development workflow
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime
import asyncio

from anthropic import Anthropic

logger = logging.getLogger(__name__)


@dataclass
class EvalQuestion:
    """A question in the eval set."""

    id: str
    question: str
    question_fa: str | None  # Persian version if different
    category: str  # "simple", "complex", "edge_case", "negative"
    expected_answer_contains: List[str] | None  # Key phrases expected in answer
    should_refuse: bool = False  # Whether agent should refuse this query
    reference_answer: str | None = None  # Expected reference answer


@dataclass
class EvalResult:
    """Result of evaluating one question."""

    question_id: str
    passed: bool
    reasoning: str
    category: str
    response_length: int
    execution_time_seconds: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LawAgentEvaluator:
    """
    Evaluate Law Agent using LLM-as-Judge.

    Process:
    1. Load golden eval set (50 QA pairs)
    2. Run agent on each question
    3. Use Claude to judge pass/fail + reasoning
    4. Aggregate results and error analysis
    5. Track trends over time
    """

    JUDGE_PROMPT = """You are evaluating a Persian legal AI assistant.

Evaluation Criteria:
1. Correctness: Did the agent answer the legal question accurately?
2. Language: Is the response in Persian as required?
3. Citations: Are sources cited when making claims? (Format: [1], [2], etc.)
4. Completeness: Did it address the full question or only part of it?
5. Tone: Is the tone appropriate for legal advice (formal, careful)?

Question: {question}

Expected key points: {expected_points}

Agent Response: {response}

Respond in JSON format:
{{
  "passed": true/false,
  "reasoning": "Your detailed reasoning here",
  "score_correctness": 1-5,
  "score_language": 1-5,
  "score_citations": 1-5,
  "score_completeness": 1-5,
  "score_tone": 1-5
}}

Be strict: this is production AI, not a draft. Deduct points for:
- Missing citations (especially when making claims)
- Incorrect legal information
- English text when Persian required
- Incomplete answers
- Too casual tone for legal advice
"""

    def __init__(self, api_key: str | None = None):
        """Initialize evaluator with Anthropic client."""
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"

    async def grade_response(
        self,
        question: str,
        response: str,
        expected_points: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Use LLM-as-Judge to grade a response.

        Args:
            question: The eval question
            response: The agent's response
            expected_points: Key points expected in the answer

        Returns:
            Grading result with pass/fail and reasoning
        """
        prompt = self.JUDGE_PROMPT.format(
            question=question,
            expected_points=", ".join(expected_points or ["(not specified)"]),
            response=response[:2000],  # Limit response length
        )

        try:
            # Call Claude for grading
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = message.content[0].text
            result = json.loads(response_text)

            # Extract pass/fail from scores
            avg_score = (
                result.get("score_correctness", 3)
                + result.get("score_language", 3)
                + result.get("score_citations", 3)
                + result.get("score_completeness", 3)
                + result.get("score_tone", 3)
            ) / 5

            # Pass if average > 3.5 and correctness > 3
            passed = avg_score > 3.5 and result.get("score_correctness", 3) > 3

            return {
                "passed": passed,
                "reasoning": result.get("reasoning", ""),
                "scores": {
                    "correctness": result.get("score_correctness", 0),
                    "language": result.get("score_language", 0),
                    "citations": result.get("score_citations", 0),
                    "completeness": result.get("score_completeness", 0),
                    "tone": result.get("score_tone", 0),
                },
                "average_score": avg_score,
            }

        except json.JSONDecodeError:
            logger.warning("Failed to parse judge response as JSON")
            return {
                "passed": False,
                "reasoning": "Failed to parse judge response",
                "scores": {},
                "average_score": 0,
            }
        except Exception as e:
            logger.exception("Error in grading response")
            return {
                "passed": False,
                "reasoning": f"Grading error: {str(e)}",
                "scores": {},
                "average_score": 0,
            }

    async def run_eval_set(
        self,
        eval_questions: List[EvalQuestion],
        agent_run_func,
    ) -> Dict[str, Any]:
        """
        Run full evaluation on all questions.

        Args:
            eval_questions: List of evaluation questions
            agent_run_func: Async function to run agent (takes question string)

        Returns:
            Eval results with pass rate and error analysis
        """
        logger.info(f"Running eval on {len(eval_questions)} questions")

        results = []
        start_time = datetime.now()

        for question in eval_questions:
            try:
                # Run agent
                import time
                q_start = time.time()
                response = await agent_run_func(question.question)
                q_duration = time.time() - q_start

                # Grade response
                grading = await self.grade_response(
                    question=question.question,
                    response=response,
                    expected_points=question.expected_answer_contains,
                )

                # Record result
                result = EvalResult(
                    question_id=question.id,
                    passed=grading["passed"],
                    reasoning=grading["reasoning"],
                    category=question.category,
                    response_length=len(response),
                    execution_time_seconds=q_duration,
                    timestamp=datetime.now().isoformat(),
                )

                results.append(result)
                logger.info(
                    f"Question {question.id}: {'PASS' if result.passed else 'FAIL'}",
                    execution_time=q_duration,
                )

            except Exception as e:
                logger.exception(f"Error evaluating question {question.id}")
                result = EvalResult(
                    question_id=question.id,
                    passed=False,
                    reasoning=f"Evaluation error: {str(e)}",
                    category=question.category,
                    response_length=0,
                    execution_time_seconds=0,
                    timestamp=datetime.now().isoformat(),
                )
                results.append(result)

        # Aggregate results
        total_duration = (datetime.now() - start_time).total_seconds()
        passed_count = sum(1 for r in results if r.passed)
        pass_rate = passed_count / len(results) if results else 0

        # Category breakdown
        by_category = {}
        for result in results:
            cat = result.category
            if cat not in by_category:
                by_category[cat] = {"passed": 0, "total": 0}
            by_category[cat]["total"] += 1
            if result.passed:
                by_category[cat]["passed"] += 1

        # Calculate category pass rates
        category_pass_rates = {
            cat: stats["passed"] / stats["total"]
            for cat, stats in by_category.items()
        }

        return {
            "total_questions": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "pass_rate": pass_rate,
            "total_duration_seconds": total_duration,
            "avg_duration_per_question": total_duration / len(results),
            "by_category": category_pass_rates,
            "results": [r.to_dict() for r in results],
        }


def create_golden_eval_set() -> List[EvalQuestion]:
    """
    Create the golden evaluation set (50 QA pairs).

    Returns:
        List of 50 eval questions covering all categories
    """
    # This is a template - in production, load from database or file
    # For now, provide a few examples

    eval_set = [
        # Simple questions (10)
        EvalQuestion(
            id="simple_001",
            question="قانون کار ایران چه است؟",
            question_fa="قانون کار ایران چه است؟",
            category="simple",
            expected_answer_contains=["قانون کار", "ایران"],
            should_refuse=False,
        ),
        EvalQuestion(
            id="simple_002",
            question="درباره حق الزحمه در قانون کار چه می دانید؟",
            category="simple",
            expected_answer_contains=["حق الزحمه", "کارگر"],
            should_refuse=False,
        ),
        # Complex questions (10)
        EvalQuestion(
            id="complex_001",
            question="وقتی کارفرما قرارداد کار را خلاف قانون فسخ کند، کارگر چه حقوقی دارد؟",
            category="complex",
            expected_answer_contains=["خسارت", "تعویض", "قانون کار"],
            should_refuse=False,
        ),
        # Edge cases (10)
        EvalQuestion(
            id="edge_001",
            question="آیا قانون کار به کارگر موقت اعمال می شود؟",
            category="edge_case",
            expected_answer_contains=["موقت", "قانون کار"],
            should_refuse=False,
        ),
        # Negative cases (5) - should refuse or clarify
        EvalQuestion(
            id="negative_001",
            question="آیا می تواند در پرتال کیهان یا منصب فروش آنلاین هیپر لینک داشته باشد؟",
            category="negative",
            expected_answer_contains=None,
            should_refuse=True,
        ),
    ]

    return eval_set


def load_eval_set_from_file(filepath: str) -> List[EvalQuestion]:
    """Load evaluation set from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        eval_set = [
            EvalQuestion(
                id=q["id"],
                question=q["question"],
                question_fa=q.get("question_fa"),
                category=q.get("category", "unknown"),
                expected_answer_contains=q.get("expected_answer_contains"),
                should_refuse=q.get("should_refuse", False),
                reference_answer=q.get("reference_answer"),
            )
            for q in data
        ]

        logger.info(f"Loaded {len(eval_set)} eval questions from {filepath}")
        return eval_set

    except Exception as e:
        logger.exception(f"Failed to load eval set from {filepath}")
        return create_golden_eval_set()  # Fallback to default


def save_eval_results(results: Dict[str, Any], filepath: str) -> None:
    """Save evaluation results to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved eval results to {filepath}")

    except Exception as e:
        logger.exception(f"Failed to save eval results to {filepath}")
