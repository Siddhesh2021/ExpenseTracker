from abc import ABC, abstractmethod

from app.schemas.expense import ExpenseExtraction, ExtractionContext


class AIProvider(ABC):
    """Business logic talks to this interface, never to Gemini directly."""

    @abstractmethod
    def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
        raise NotImplementedError
