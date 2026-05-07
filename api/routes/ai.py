from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class AnalysisContext(BaseModel):
    sequence: str
    enzyme: str
    grna_count: int
    top_guide: str
    top_score: float


class ChatRequest(BaseModel):
    message: str
    context: AnalysisContext


@router.post("/ai/chat")
def chat(req: ChatRequest) -> JSONResponse:
    ctx = req.context
    system_prompt = (
        "You are Helix AI, a specialized CRISPR and genomics assistant "
        "built into the Helix bioinformatics suite. You have access to "
        "the user's current analysis context. Be concise, scientific, "
        "and precise. Use proper genomics terminology. When discussing "
        "guides, refer to their sequence and score directly. "
        f"Current analysis context: {ctx.model_dump()}"
    )

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": req.message}],
        )
        reply = response.content[0].text
        return JSONResponse({"reply": reply})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
