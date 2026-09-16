"""
Planner Agent for MentorOS (Phase 4).
Routes incoming user queries to appropriate action handlers:
  - RETRIEVE: Content / concept questions needing RAG vector retrieval
  - MEMORY: Questions about student mastery, weak topics, or progress history
  - QUIZ: Practice quiz / self-assessment requests
  - PODCAST: Audio / podcast script explainer requests
  - GENERAL: Greetings or general conversational queries

Uses hybrid routing: instant rule-based fast path + Ollama LLM classifier fallback.
"""

from dataclasses import dataclass
from enum import Enum
import json
import logging
import re
from typing import Optional

from llm.ollama_client import OllamaClient

# Configure logger for visible planner routing decisions
logger = logging.getLogger("MentorOS.PlannerAgent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


class PlannerAction(str, Enum):
    RETRIEVE = "RETRIEVE"
    MEMORY = "MEMORY"
    QUIZ = "QUIZ"
    PODCAST = "PODCAST"
    GENERAL = "GENERAL"


@dataclass
class PlanDecision:
    """Represents the routing decision made by the Planner Agent."""
    query: str
    action: PlannerAction
    confidence: float
    reasoning: str
    route_method: str  # "rule_based" or "llm_classifier"

    def log(self):
        """Log routing decision visibly to console."""
        logger.info(
            f"Query: '{self.query}' | Action: [{self.action.value}] | "
            f"Method: {self.route_method} | Confidence: {self.confidence * 100:.0f}% | "
            f"Reason: {self.reasoning}"
        )


class PlannerAgent:
    """Intent router for MentorOS."""

    # Fast-path keyword rules for instant 0-ms routing
    MEMORY_PATTERNS = [
        r"\b(weak|weakness|weaknesses|mistake|mistakes)\b",
        r"\b(my progress|what should i revise|what do i need to review)\b",
        r"\b(learning memory|topics i struggled|how am i doing)\b",
    ]

    QUIZ_PATTERNS = [
        r"\b(quiz|test me|practice question|exam|multiple choice|questions for me)\b",
        r"\b(test my knowledge|check my understanding|give me a problem)\b",
    ]

    PODCAST_PATTERNS = [
        r"\b(podcast|audio|dialogue|host and student|two person|audio explainer)\b",
        r"\b(listen to this|audio version)\b",
    ]

    GENERAL_PATTERNS = [
        r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening|thanks|thank you)\b",
        r"^(who are you|what can you do|help|what is mentoros)\b",
    ]

    SYSTEM_PROMPT = """You are an intent classification router for MentorOS, an AI tutor.
Analyze the user query and classify it into EXACTLY ONE of these 5 categories:

1. RETRIEVE - Questions asking for concepts, facts, summaries, or explanations from documents.
2. MEMORY - Questions about student performance, weak topics, score history, or what to revise.
3. QUIZ - Requests to be tested, generate quiz questions, or practice problems.
4. PODCAST - Requests for audio explainer, podcast script, or two-person dialogue.
5. GENERAL - Simple greetings, thank yous, or general questions about what the tutor is.

Respond in valid JSON format ONLY:
{"action": "<RETRIEVE|MEMORY|QUIZ|PODCAST|GENERAL>", "confidence": <float 0.0-1.0>, "reasoning": "<brief explanation>"}"""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama_client = ollama_client or OllamaClient()

    def _check_fast_path(self, query: str) -> Optional[PlanDecision]:
        """Check regex rules for instant, deterministic routing."""
        text = query.strip().lower()

        for pattern in self.MEMORY_PATTERNS:
            if re.search(pattern, text):
                return PlanDecision(
                    query=query,
                    action=PlannerAction.MEMORY,
                    confidence=0.95,
                    reasoning=f"Matched memory pattern: '{pattern}'",
                    route_method="rule_based",
                )

        for pattern in self.QUIZ_PATTERNS:
            if re.search(pattern, text):
                return PlanDecision(
                    query=query,
                    action=PlannerAction.QUIZ,
                    confidence=0.95,
                    reasoning=f"Matched quiz pattern: '{pattern}'",
                    route_method="rule_based",
                )

        for pattern in self.PODCAST_PATTERNS:
            if re.search(pattern, text):
                return PlanDecision(
                    query=query,
                    action=PlannerAction.PODCAST,
                    confidence=0.95,
                    reasoning=f"Matched podcast pattern: '{pattern}'",
                    route_method="rule_based",
                )

        for pattern in self.GENERAL_PATTERNS:
            if re.search(pattern, text):
                return PlanDecision(
                    query=query,
                    action=PlannerAction.GENERAL,
                    confidence=0.95,
                    reasoning=f"Matched greeting/general pattern: '{pattern}'",
                    route_method="rule_based",
                )

        return None

    def route(self, query: str) -> PlanDecision:
        """
        Route user query to appropriate action.
        1. Try fast-path rule matching first (0ms).
        2. Fallback to lightweight Ollama LLM classifier.
        3. Default to RETRIEVE if ambiguous.
        """
        query_str = query.strip()

        # Step 1: Fast path
        decision = self._check_fast_path(query_str)
        if decision:
            decision.log()
            return decision

        # Step 2: LLM Classifier fallback
        try:
            raw_response = self.ollama_client.generate(
                prompt=f"User Query: \"{query_str}\"\nJSON Classification:",
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.0,  # deterministic classification
            )

            # Extract JSON object from response
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                act_str = data.get("action", "RETRIEVE").upper()

                # Validate enum
                try:
                    action = PlannerAction(act_str)
                except ValueError:
                    action = PlannerAction.RETRIEVE

                confidence = float(data.get("confidence", 0.85))
                reasoning = data.get("reasoning", "LLM intent classification")

                decision = PlanDecision(
                    query=query_str,
                    action=action,
                    confidence=confidence,
                    reasoning=reasoning,
                    route_method="llm_classifier",
                )
                decision.log()
                return decision

        except Exception as e:
            logger.warning(f"LLM router fallback error: {e}. Defaulting to RETRIEVE.")

        # Step 3: Default fallback
        decision = PlanDecision(
            query=query_str,
            action=PlannerAction.RETRIEVE,
            confidence=0.70,
            reasoning="Default content query fallback",
            route_method="default_fallback",
        )
        decision.log()
        return decision
