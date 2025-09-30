from typing import Awaitable, Protocol, Type, Union

from pydantic import BaseModel


class ToolContext(BaseModel):
    user_id: str | None = None
    session_id: str | None = None


class Tool(Protocol):
    name: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]

    def __call__(
        self, args: BaseModel, ctx: ToolContext
    ) -> Union[BaseModel, Awaitable[BaseModel]]: ...
