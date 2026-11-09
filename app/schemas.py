"""Request and response models. FastAPI uses these to build the Swagger docs."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Agent(BaseModel):
    """One agent returned by the Work IQ `list_agents` tool."""

    # The server sends camelCase (agentId); we expose snake_case in Python.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    agent_id: str
    name: str
    provider: str | None = None


class AskRequest(BaseModel):
    """Body for POST /agents/{agent_id}/ask."""

    question: str = Field(..., min_length=1, examples=["What meetings do I have today?"])
    conversation_id: str | None = Field(
        default=None,
        description="Pass the conversation_id from a previous answer to continue that conversation.",
    )


class AskResponse(BaseModel):
    """Answer returned to the caller."""

    agent_id: str
    response: str
    conversation_id: str | None = None
