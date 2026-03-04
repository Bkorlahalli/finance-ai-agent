"""
Categorization Agent — LLM-powered expense categorization using LangChain + OpenAI.

Responsibilities:
- Send transaction descriptions to OpenAI for categorization
- Parse structured category output with confidence scores
- Apply fallback rules when LLM is unavailable
- Batch process transactions efficiently
"""

import json
from typing import List, Tuple, Optional

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.schemas.transaction_schema import (
    ParsedTransaction,
    CategorizedTransaction,
    TransactionCategory,
)

logger = get_logger("categorization_agent")

# Categorization prompt template
CATEGORIZATION_PROMPT = """You are a financial transaction categorizer. 
Given a transaction description and merchant name, classify it into exactly ONE of these categories:
- Food (restaurants, food delivery, groceries, cafes)
- Travel (rides, flights, hotels, fuel, tolls)
- Rent (house rent, society maintenance, property)
- Shopping (clothing, electronics, home goods, online shopping)
- Recharge (mobile recharge, DTH, broadband, utilities, electricity, water)
- Investment (mutual funds, stocks, SIP, fixed deposits, gold)
- Misc (anything that doesn't fit above)

Transaction:
- Description: {description}
- Merchant: {merchant}
- Amount: ₹{amount}
- Payment Mode: {mode}

Respond ONLY with a valid JSON object in this exact format (no extra text):
{{"category": "<category_name>", "confidence": <0.0_to_1.0>}}
"""

# Rule-based fallback keywords
FALLBACK_RULES = {
    TransactionCategory.FOOD: [
        "swiggy", "zomato", "restaurant", "food", "pizza", "burger",
        "cafe", "coffee", "tea", "biryani", "dominos", "mcdonalds",
        "kfc", "subway", "starbucks", "bigbasket", "blinkit", "grofers",
        "dunzo", "grocery", "kitchen", "eat", "dine",
    ],
    TransactionCategory.TRAVEL: [
        "uber", "ola", "rapido", "taxi", "cab", "flight", "train",
        "irctc", "makemytrip", "goibibo", "fuel", "petrol", "diesel",
        "toll", "parking", "metro", "bus", "hotel", "oyo",
    ],
    TransactionCategory.RENT: [
        "rent", "house", "flat", "apartment", "maintenance", "society",
        "landlord", "property", "lease",
    ],
    TransactionCategory.SHOPPING: [
        "amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho",
        "shopping", "mall", "store", "electronics", "fashion", "clothes",
        "shoes", "reliance", "dmart", "croma", "vijay sales",
    ],
    TransactionCategory.RECHARGE: [
        "recharge", "airtel", "jio", "vodafone", "vi", "bsnl",
        "broadband", "wifi", "dth", "tatasky", "electricity", "bill",
        "water", "gas", "utility", "mobile",
    ],
    TransactionCategory.INVESTMENT: [
        "zerodha", "groww", "upstox", "kuvera", "coin", "sip",
        "mutual fund", "stock", "share", "demat", "investment",
        "gold", "fixed deposit", "fd", "ppf", "nps",
    ],
}


class CategorizationAgent:
    """
    Agent responsible for categorizing transactions using LLM with rule-based fallback.

    Uses OpenAI via LangChain for intelligent categorization,
    falling back to keyword-based rules if the API is unavailable.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = None
        self._init_llm()
        logger.info("CategorizationAgent initialized (LLM available: %s)", self.llm is not None)

    def _init_llm(self) -> None:
        """Initialize LangChain OpenAI LLM if API key is configured."""
        if self.settings.is_openai_configured:
            try:
                from langchain_openai import ChatOpenAI

                self.llm = ChatOpenAI(
                    model=self.settings.openai_model,
                    temperature=0.1,  # Low temperature for consistent categorization
                    api_key=self.settings.openai_api_key,
                    max_retries=2,
                    request_timeout=15,
                )
                logger.info("LLM initialized with model: %s", self.settings.openai_model)
            except Exception as e:
                logger.warning("Failed to initialize LLM: %s. Using fallback rules.", e)
                self.llm = None
        else:
            logger.warning(
                "OpenAI API key not configured. Using rule-based categorization fallback."
            )

    def _categorize_with_llm(self, txn: ParsedTransaction) -> Tuple[TransactionCategory, float]:
        """
        Categorize a single transaction using LLM.

        Args:
            txn: Parsed transaction to categorize.

        Returns:
            Tuple of (category, confidence_score).
        """
        try:
            from langchain_core.messages import HumanMessage

            prompt = CATEGORIZATION_PROMPT.format(
                description=txn.description,
                merchant=txn.merchant,
                amount=txn.amount,
                mode=txn.mode.value,
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()

            # Parse JSON response
            # Handle potential markdown code block wrapping
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)
            category_str = result.get("category", "Misc")
            confidence = float(result.get("confidence", 0.5))

            # Validate category
            try:
                category = TransactionCategory(category_str)
            except ValueError:
                logger.warning("LLM returned invalid category: %s", category_str)
                category = TransactionCategory.MISC
                confidence = 0.3

            return category, min(max(confidence, 0.0), 1.0)

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response as JSON: %s", e)
            return self._categorize_with_rules(txn)
        except Exception as e:
            logger.warning("LLM categorization failed: %s. Using fallback.", e)
            return self._categorize_with_rules(txn)

    def _categorize_with_rules(self, txn: ParsedTransaction) -> Tuple[TransactionCategory, float]:
        """
        Fallback rule-based categorization using keyword matching.

        Args:
            txn: Parsed transaction to categorize.

        Returns:
            Tuple of (category, confidence_score).
        """
        text = f"{txn.description} {txn.merchant}".lower()

        for category, keywords in FALLBACK_RULES.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                # Confidence based on number of keyword matches
                confidence = min(0.5 + (matches * 0.1), 0.85)
                return category, confidence

        return TransactionCategory.MISC, 0.3

    def categorize_transactions(
        self, parsed_transactions: List[ParsedTransaction]
    ) -> Tuple[List[CategorizedTransaction], List[str]]:
        """
        Categorize a batch of parsed transactions.

        Uses LLM when available, falls back to rule-based categorization.

        Args:
            parsed_transactions: List of parsed transactions.

        Returns:
            Tuple of (categorized transactions, error messages).
        """
        errors: List[str] = []
        categorized: List[CategorizedTransaction] = []

        for idx, txn in enumerate(parsed_transactions):
            try:
                if self.llm is not None:
                    category, confidence = self._categorize_with_llm(txn)
                else:
                    category, confidence = self._categorize_with_rules(txn)

                cat_txn = CategorizedTransaction(
                    date=txn.date,
                    amount=txn.amount,
                    merchant=txn.merchant,
                    description=txn.description,
                    mode=txn.mode,
                    reference_id=txn.reference_id,
                    category=category,
                    confidence_score=confidence,
                )
                categorized.append(cat_txn)

                logger.debug(
                    "Categorized [%s] → %s (%.0f%% confidence)",
                    txn.merchant,
                    category.value,
                    confidence * 100,
                )

            except Exception as e:
                error_msg = f"Transaction {idx + 1} ({txn.merchant}): Categorization error — {e}"
                errors.append(error_msg)
                logger.warning(error_msg)

        logger.info(
            "Categorization complete: %d/%d transactions categorized.",
            len(categorized),
            len(parsed_transactions),
        )
        return categorized, errors
