"""CSAT/Survey API."""

from uuid import UUID
from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select, func
from app.dependencies import AuthUser, TenantDbSession
from app.models.survey import Survey, SurveyResponse as SurveyResponseModel
from app.schemas.common import CamelModel, SuccessResponse
from typing import Any

router = APIRouter()


class SurveyCreate(CamelModel):
    name: str = Field(..., min_length=1)
    survey_type: str = "csat"
    question: str = "How would you rate your experience?"
    options: list[dict[str, Any]] = Field(default_factory=lambda: [
        {"label": "Very Bad", "value": 1}, {"label": "Bad", "value": 2},
        {"label": "OK", "value": 3}, {"label": "Good", "value": 4}, {"label": "Excellent", "value": 5},
    ])
    trigger: str = "conversation_closed"


class SurveyOut(CamelModel):
    id: UUID
    name: str
    survey_type: str
    question: str
    total_responses: int
    avg_score: int | None
    created_at: str


@router.get("")
async def list_surveys(db: TenantDbSession, user: AuthUser):
    result = await db.execute(select(Survey).where(Survey.company_id == user.company_id).order_by(Survey.name))
    return [SurveyOut(id=s.id, name=s.name, survey_type=s.survey_type, question=s.question,
                       total_responses=s.total_responses, avg_score=s.avg_score, created_at=s.created_at.isoformat())
            for s in result.scalars().all()]


@router.post("", response_model=SurveyOut, status_code=201)
async def create_survey(data: SurveyCreate, db: TenantDbSession, user: AuthUser):
    survey = Survey(company_id=user.company_id, name=data.name, survey_type=data.survey_type,
                    question=data.question, options=data.options, trigger=data.trigger)
    db.add(survey)
    await db.commit()
    return SurveyOut(id=survey.id, name=survey.name, survey_type=survey.survey_type, question=survey.question,
                     total_responses=0, avg_score=None, created_at=survey.created_at.isoformat())


@router.get("/{survey_id}/stats")
async def survey_stats(survey_id: UUID, db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(func.count(), func.avg(SurveyResponseModel.score))
        .where(SurveyResponseModel.survey_id == survey_id)
    )
    row = result.one()
    return {"total_responses": row[0], "avg_score": round(float(row[1]), 1) if row[1] else None}
