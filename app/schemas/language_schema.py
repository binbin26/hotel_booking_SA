from pydantic import BaseModel, Field


class LanguageUpdateRequest(BaseModel):
    """Body for POST /api/language."""

    language: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Locale code, e.g. en or vi",
        examples=["en", "vi"],
    )


class LanguageUpdateResponse(BaseModel):
    success: bool = True
    language: str
