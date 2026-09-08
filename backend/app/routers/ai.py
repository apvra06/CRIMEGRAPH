from fastapi import APIRouter
from app.schemas import AskQuestionRequest, AskQuestionResponse, CaseBreakdownResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskQuestionResponse)
def ask_question(body: AskQuestionRequest):
    res = ai_service.answer_question(body.question)
    return AskQuestionResponse(
        answer=res["answer"],
        citations=res.get("citations", []),
        related_entities=res.get("related_entities", [])
    )


@router.get("/breakdown", response_model=CaseBreakdownResponse)
def case_breakdown():
    res = ai_service.get_case_breakdown()
    return CaseBreakdownResponse(**res)

