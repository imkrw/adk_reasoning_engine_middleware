from pydantic import BaseModel, Field, ConfigDict


class ReceivePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)
    company_id: str = Field(..., alias="companyId")
    user_id: str = Field(..., alias="userId")
    user_message: str = Field(..., alias="message")
    webhook: str = Field(..., alias="webhook")
    webhook_notify: str | None = Field(default=None, alias="webhookNotify")


class OutPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    session_exists: bool = Field(..., alias="sessionExists")
    session_id: str = Field(..., alias="sessionId")
    response_message: str = Field(..., alias="message")
    service_timings_usage: dict[str, float] = Field(
        default_factory=dict, alias="serviceTimingsUsage"
    )
