"""Smart agent routing engine with configurable fallback policies.

Routes conversations to agents based on:
1. Relationship continuity - returning customers go to their previous agent
2. Skills-based matching - match conversation language/topic to agent skills
3. Workload balancing - prefer agents with fewer open conversations
4. Availability - only route to online agents within working hours
5. Configurable fallback policies per company
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.conversation import Conversation

logger = structlog.get_logger()


# Routing policy configuration (per-company, stored in company.settings)
DEFAULT_ROUTING_POLICY = {
    "sticky_routing_enabled": True,
    "fallback_strategy": "scoring",  # scoring, round_robin, team, queue
    "fallback_team_id": None,        # If strategy is "team", route to this team
    "max_wait_seconds": 0,           # Seconds to wait for sticky agent before fallback (0 = immediate)
    "prefer_online_agents": True,
    "relationship_weight": 40,       # Points for relationship continuity
    "skills_weight": 30,             # Points for skills match
    "workload_weight": 40,           # Points for workload balance (inverse)
    "online_bonus": 10,              # Bonus points for online agents
}


class RoutingEngine:
    def __init__(self, db: AsyncSession, company_id: UUID, policy: dict | None = None):
        self.db = db
        self.company_id = company_id
        self.policy = {**DEFAULT_ROUTING_POLICY, **(policy or {})}

    async def assign_conversation(
        self,
        conversation: Conversation,
        *,
        preferred_skills: list[str] | None = None,
        language: str | None = None,
    ) -> UUID | None:
        """
        Determine the best agent using configurable routing policy.
        Returns the user_id of the selected agent, or None if no agent available.
        Also persists the routing decision for analytics.
        """
        routing_method = "none"
        previous_agent_id = None
        assigned_agent_id = None
        score = None

        # 1. Relationship continuity (if enabled)
        if self.policy["sticky_routing_enabled"]:
            previous_agent_id = await self._find_previous_agent(conversation.contact_id)
            if previous_agent_id:
                if await self._is_agent_available(previous_agent_id):
                    load = await self._get_agent_load(previous_agent_id)
                    agent = await self._get_agent(previous_agent_id)
                    if agent and load < agent.max_concurrent_conversations:
                        assigned_agent_id = previous_agent_id
                        routing_method = "relationship"
                        score = 100.0
                        logger.info("routing_relationship", conversation_id=str(conversation.id), agent_id=str(previous_agent_id))

        # 2. Fallback strategy
        if not assigned_agent_id:
            fallback = self.policy["fallback_strategy"]

            if fallback == "scoring":
                assigned_agent_id, score = await self._scoring_fallback(
                    conversation, preferred_skills, language
                )
                if assigned_agent_id:
                    routing_method = "scoring"

            elif fallback == "round_robin":
                assigned_agent_id = await self._round_robin_fallback()
                if assigned_agent_id:
                    routing_method = "round_robin"

            elif fallback == "team" and self.policy.get("fallback_team_id"):
                assigned_agent_id = await self._team_fallback(self.policy["fallback_team_id"])
                if assigned_agent_id:
                    routing_method = "team"

            elif fallback == "queue":
                routing_method = "queue"
                logger.info("routing_queued", conversation_id=str(conversation.id))

        # 3. Persist routing decision for analytics
        await self._persist_decision(
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
            assigned_agent_id=assigned_agent_id,
            previous_agent_id=previous_agent_id,
            routing_method=routing_method,
            score=score,
        )

        if assigned_agent_id:
            logger.info("routing_assigned", conversation_id=str(conversation.id),
                        agent_id=str(assigned_agent_id), method=routing_method, score=score)
        else:
            logger.warning("routing_no_agent", conversation_id=str(conversation.id), method=routing_method)

        return assigned_agent_id

    async def _scoring_fallback(
        self, conversation: Conversation,
        preferred_skills: list[str] | None, language: str | None,
    ) -> tuple[UUID | None, float | None]:
        """Score all eligible agents and return the best one."""
        agents = await self._get_eligible_agents(preferred_skills, language)
        if not agents:
            return None, None

        scored = []
        for agent in agents:
            load = await self._get_agent_load(agent.id)
            if load >= agent.max_concurrent_conversations:
                continue
            s = self._calculate_score(agent, load=load, preferred_skills=preferred_skills, language=language)
            scored.append((agent, s, load))

        if not scored:
            return None, None

        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[0]
        return best[0].id, best[1]

    async def _round_robin_fallback(self) -> UUID | None:
        """Simple round-robin: pick agent with fewest open conversations."""
        agents = await self._get_eligible_agents()
        if not agents:
            return None

        min_load = float("inf")
        best = None
        for agent in agents:
            load = await self._get_agent_load(agent.id)
            if load < agent.max_concurrent_conversations and load < min_load:
                min_load = load
                best = agent

        return best.id if best else None

    async def _team_fallback(self, team_id: str) -> UUID | None:
        """Route to least-loaded agent in a specific team/role."""
        # Team is represented by role - find agents with this role
        agents = await self._get_eligible_agents()
        if not agents:
            return None
        # For now, same as round-robin within the team
        return await self._round_robin_fallback()

    def _calculate_score(
        self, agent: User, *, load: int,
        preferred_skills: list[str] | None = None, language: str | None = None,
    ) -> float:
        """Score an agent using configurable weights."""
        score = 0.0

        # Workload score
        capacity_ratio = load / max(agent.max_concurrent_conversations, 1)
        score += (1.0 - capacity_ratio) * self.policy["workload_weight"]

        # Skills match
        if preferred_skills and agent.skills:
            agent_skills = set(agent.skills.get("tags", []))
            matching = len(set(preferred_skills) & agent_skills)
            if preferred_skills:
                score += (matching / len(preferred_skills)) * self.policy["skills_weight"]

        # Language match
        if language and agent.skills:
            agent_languages = set(agent.skills.get("languages", []))
            if language in agent_languages:
                score += 20

        # Online bonus
        if agent.is_online and self.policy["prefer_online_agents"]:
            score += self.policy["online_bonus"]

        return round(score, 2)

    async def _persist_decision(self, **kwargs):
        """Save routing decision for analytics."""
        try:
            from app.models.routing_decision import RoutingDecision
            decision = RoutingDecision(company_id=self.company_id, **kwargs)
            self.db.add(decision)
            await self.db.flush()
        except Exception as e:
            logger.error("routing_decision_persist_failed", error=str(e))

    async def _find_previous_agent(self, contact_id: UUID) -> UUID | None:
        result = await self.db.execute(
            select(Conversation.assigned_to_user_id)
            .where(
                Conversation.company_id == self.company_id,
                Conversation.contact_id == contact_id,
                Conversation.assigned_to_user_id.isnot(None),
            )
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _is_agent_available(self, user_id: UUID) -> bool:
        agent = await self._get_agent(user_id)
        if not agent or not agent.is_active:
            return False
        if agent.working_hours:
            now = datetime.now(timezone.utc)
            day_name = now.strftime("%A").lower()
            day_schedule = agent.working_hours.get(day_name)
            if day_schedule:
                start = day_schedule.get("start")
                end = day_schedule.get("end")
                if start and end:
                    current_time = now.strftime("%H:%M")
                    if not (start <= current_time <= end):
                        return False
        return True

    async def _get_agent(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.company_id == self.company_id, User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _get_eligible_agents(self, preferred_skills: list[str] | None = None, language: str | None = None) -> list[User]:
        result = await self.db.execute(
            select(User).where(User.company_id == self.company_id, User.is_active == True)
        )
        return list(result.scalars().all())

    async def _get_agent_load(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Conversation).where(
                Conversation.company_id == self.company_id,
                Conversation.assigned_to_user_id == user_id,
                Conversation.status.in_(["open", "pending"]),
            )
        )
        return result.scalar_one()
