from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.action_execution import ActionExecution
from app.models.agent_profile import AgentProfile
from app.models.conversation import Conversation, ConversationMessage
from app.models.memory_pattern import MemoryPattern
from app.models.user import User
from app.schemas.agentic import ActionPayload, AgentExecutionRequest, AgentExecutionResponse, LearningUpdate


TRANSFER_PATTERN = re.compile(
    r"transfer\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<currency>pounds|gbp|usd|dollars|eur|euros)?\s+to\s+(?P<beneficiary>[a-zA-Z]+)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class IntentResult:
    intent: str
    action_type: str
    mode: str
    specialists_used: list[str]
    extracted_amount: float | None = None
    extracted_currency: str | None = None
    extracted_beneficiary: str | None = None


class MemoryManagerService:
    def retrieve_patterns(self, db: Session, user_id: uuid.UUID, agent_id: uuid.UUID, message: str) -> list[MemoryPattern]:
        patterns = db.scalars(
            select(MemoryPattern).where(MemoryPattern.user_id == user_id, MemoryPattern.agent_id == agent_id)
        ).all()
        lowered_message = message.lower()
        matches = [pattern for pattern in patterns if pattern.pattern_key in lowered_message or pattern.pattern_text.lower() in lowered_message]
        for pattern in matches:
            pattern.usage_count += 1
            pattern.last_used_at = datetime.now(timezone.utc)
        return matches[:5]


class LearningEngineService:
    def learn_from_conversation(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        agent_id: uuid.UUID,
        intent: str,
        message: str,
        response_text: str,
    ) -> LearningUpdate:
        pattern_key = intent.lower()
        existing = db.scalar(
            select(MemoryPattern).where(
                MemoryPattern.user_id == user_id,
                MemoryPattern.agent_id == agent_id,
                MemoryPattern.pattern_key == pattern_key,
            )
        )

        if existing is None:
            existing = MemoryPattern(
                user_id=user_id,
                agent_id=agent_id,
                pattern_key=pattern_key,
                pattern_text=message,
                response_template=response_text,
                usage_count=1,
                last_used_at=datetime.now(timezone.utc),
            )
            db.add(existing)
            return LearningUpdate(status="created", pattern_key=pattern_key, usage_count=existing.usage_count)

        existing.pattern_text = message
        existing.response_template = response_text
        existing.usage_count += 1
        existing.last_used_at = datetime.now(timezone.utc)
        return LearningUpdate(status="updated", pattern_key=pattern_key, usage_count=existing.usage_count)


class RoleAgentService:
    def handle(
        self,
        db: Session,
        *,
        user: User,
        agent: AgentProfile,
        message: str,
        intent_result: IntentResult,
        conversation: Conversation,
    ) -> tuple[str, ActionPayload]:
        if intent_result.intent == "transfer_money":
            return self._transfer_money(db, user, agent, message, intent_result, conversation)
        if intent_result.intent == "check_balance":
            return self._check_balance(user, agent, message, conversation, db)
        return self._general_response(message)

    def _transfer_money(
        self,
        db: Session,
        user: User,
        agent: AgentProfile,
        message: str,
        intent_result: IntentResult,
        conversation: Conversation,
    ) -> tuple[str, ActionPayload]:
        amount = intent_result.extracted_amount or 0.0
        currency = intent_result.extracted_currency or "GBP"
        beneficiary_name = intent_result.extracted_beneficiary or "Unknown"

        execution = ActionExecution(
            user_id=user.id,
            agent_id=agent.id,
            conversation_id=conversation.id,
            request_message=message,
            intent=intent_result.intent,
            action_type="transfer_money",
            status="completed",
            amount=amount,
            currency=currency,
            beneficiary_name=beneficiary_name,
            response_payload={
                "beneficiary": beneficiary_name,
                "amount": amount,
                "currency": currency,
                "execution_mode": "direct",
                "record_type": "transfer_instruction",
            },
            notes="Transfer instruction recorded by primary role agent.",
        )
        db.add(execution)
        response = f"Recorded transfer instruction for {amount:.2f} {currency} to {beneficiary_name}."
        return response, ActionPayload(
            type="transfer_money",
            status="completed",
            details={
                "beneficiary": beneficiary_name,
                "amount": amount,
                "currency": currency,
                "execution_mode": "direct",
                "record_type": "transfer_instruction",
            },
        )

    def _check_balance(
        self,
        user: User,
        agent: AgentProfile,
        message: str,
        conversation: Conversation,
        db: Session,
    ) -> tuple[str, ActionPayload]:
        execution = ActionExecution(
            user_id=user.id,
            agent_id=agent.id,
            conversation_id=conversation.id,
            request_message=message,
            intent="check_balance",
            action_type="check_balance",
            status="completed",
            response_payload={"record_type": "balance_query", "result": "not_available_in_simplified_schema"},
            notes="Balance query recorded without an accounts table.",
        )
        db.add(execution)
        return (
            "Balance data is not stored in the simplified schema. The request has been recorded as an action execution.",
            ActionPayload(
                type="check_balance",
                status="completed",
                details={"record_type": "balance_query", "result": "not_available_in_simplified_schema"},
            ),
        )

    def _general_response(self, message: str) -> tuple[str, ActionPayload]:
        return (
            f"Direct agent received the request: '{message}'. No executable financial action was detected.",
            ActionPayload(type="respond", status="completed", details={"message_type": "general"}),
        )


class CoordinatorAgentService:
    def handle(
        self,
        *,
        message: str,
        intent_result: IntentResult,
        memory_hits: list[MemoryPattern],
    ) -> tuple[str, ActionPayload]:
        specialists = ", ".join(intent_result.specialists_used)
        memory_note = "; ".join(pattern.pattern_key for pattern in memory_hits) or "none"
        response = (
            f"Coordinator agent analyzed the request with specialists [{specialists}]. "
            f"Intent '{intent_result.intent}' requires orchestration or clarification. Relevant memory patterns: {memory_note}."
        )
        return response, ActionPayload(
            type=intent_result.action_type,
            status="pending_review",
            details={
                "reason": "orchestrator_mode",
                "specialists_used": intent_result.specialists_used,
                "memory_hits": [pattern.pattern_key for pattern in memory_hits],
            },
        )


class AgentExecutionService:
    def __init__(self) -> None:
        self._memory_manager = MemoryManagerService()
        self._learning_engine = LearningEngineService()
        self._role_agent = RoleAgentService()
        self._coordinator_agent = CoordinatorAgentService()

    def execute(self, db: Session, payload: AgentExecutionRequest) -> AgentExecutionResponse:
        user = db.get(User, payload.user_id)
        if user is None:
            raise ValueError("User not found")

        agent = db.scalar(select(AgentProfile).where(AgentProfile.id == payload.agent_id, AgentProfile.user_id == payload.user_id))
        if agent is None:
            raise ValueError("Agent not found for user")

        memory_hits = self._memory_manager.retrieve_patterns(db, user.id, agent.id, payload.message)
        intent_result = self._detect_intent(payload.message)
        prompt = self._build_prompt(user=user, agent=agent, message=payload.message, memory_hits=memory_hits, intent_result=intent_result)
        conversation = self._create_conversation(db, user.id, agent.id, payload.message, intent_result.mode)

        if intent_result.mode == "direct":
            response_text, structured_action = self._role_agent.handle(
                db,
                user=user,
                agent=agent,
                message=payload.message,
                intent_result=intent_result,
                conversation=conversation,
            )
        else:
            response_text, structured_action = self._coordinator_agent.handle(
                message=payload.message,
                intent_result=intent_result,
                memory_hits=memory_hits,
            )
            execution = ActionExecution(
                user_id=user.id,
                agent_id=agent.id,
                conversation_id=conversation.id,
                request_message=payload.message,
                intent=intent_result.intent,
                action_type=intent_result.action_type,
                status="pending_review",
                amount=intent_result.extracted_amount,
                currency=intent_result.extracted_currency,
                beneficiary_name=intent_result.extracted_beneficiary,
                response_payload=structured_action.details,
                notes="Coordinator agent requested orchestration.",
            )
            db.add(execution)

        db.add(
            ConversationMessage(conversation_id=conversation.id, role="user", content=payload.message)
        )
        db.add(
            ConversationMessage(conversation_id=conversation.id, role="assistant", content=response_text)
        )

        learning_update = self._learning_engine.learn_from_conversation(
            db,
            user_id=user.id,
            agent_id=agent.id,
            intent=intent_result.intent,
            message=payload.message,
            response_text=response_text,
        )

        db.commit()

        request_id = uuid.uuid4()
        return AgentExecutionResponse(
            request_id=request_id,
            conversation_id=conversation.id,
            user_id=user.id,
            agent_id=agent.id,
            mode=intent_result.mode,
            intent=intent_result.intent,
            specialists_used=intent_result.specialists_used,
            prompt=prompt,
            response_text=response_text,
            structured_action=structured_action,
            memory_hits=[pattern.pattern_key for pattern in memory_hits],
            learning_update=learning_update,
            created_at=datetime.now(timezone.utc),
        )

    def _create_conversation(self, db: Session, user_id: uuid.UUID, agent_id: uuid.UUID, message: str, mode: str) -> Conversation:
        title = message[:80]
        conversation = Conversation(user_id=user_id, agent_id=agent_id, title=title, mode=mode)
        db.add(conversation)
        db.flush()
        return conversation

    def _build_prompt(
        self,
        *,
        user: User,
        agent: AgentProfile,
        message: str,
        memory_hits: list[MemoryPattern],
        intent_result: IntentResult,
    ) -> str:
        memory_keys = ", ".join(pattern.pattern_key for pattern in memory_hits) or "none"
        return (
            f"User={user.full_name}; Agent={agent.name}; Mode={intent_result.mode}; Intent={intent_result.intent}; "
            f"MemoryHits={memory_keys}; Message={message}"
        )

    def _detect_intent(self, message: str) -> IntentResult:
        lowered = message.lower()
        transfer_match = TRANSFER_PATTERN.search(message)
        if transfer_match:
            currency = transfer_match.group("currency") or "GBP"
            currency = self._normalize_currency(currency)
            return IntentResult(
                intent="transfer_money",
                action_type="transfer_money",
                mode="direct",
                specialists_used=["role_agent"],
                extracted_amount=float(transfer_match.group("amount")),
                extracted_currency=currency,
                extracted_beneficiary=transfer_match.group("beneficiary"),
            )

        if "balance" in lowered:
            return IntentResult(
                intent="check_balance",
                action_type="check_balance",
                mode="direct",
                specialists_used=["role_agent"],
            )

        if any(keyword in lowered for keyword in ["schedule", "policy", "investment", "mortgage", "plan", "compare"]):
            return IntentResult(
                intent="complex_financial_request",
                action_type="orchestrate_request",
                mode="orchestrator",
                specialists_used=["coordinator_agent", "intent_specialist", "memory_specialist"],
            )

        return IntentResult(
            intent="general_request",
            action_type="respond",
            mode="orchestrator",
            specialists_used=["coordinator_agent", "general_specialist"],
        )

    def _normalize_currency(self, currency: str) -> str:
        normalized = currency.strip().lower()
        mapping = {
            "pounds": "GBP",
            "gbp": "GBP",
            "usd": "USD",
            "dollars": "USD",
            "eur": "EUR",
            "euros": "EUR",
        }
        return mapping.get(normalized, normalized.upper())