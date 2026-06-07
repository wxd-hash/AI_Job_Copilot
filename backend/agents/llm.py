"""LangChain 兼容的 DashScope Qwen ChatModel 封装。

使 DashScope 的 Generation API 可以像 LangChain 原生模型一样使用：
    model = DashScopeChatModel(model="qwen-plus")
    chain = prompt | model | StrOutputParser()
"""

from typing import Any, Iterator, Optional

import dashscope
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage, AIMessage, HumanMessage, SystemMessage,
)
from langchain_core.outputs import ChatResult, ChatGeneration

from backend.core.config import settings


class DashScopeChatModel(BaseChatModel):
    """DashScope Qwen 的 LangChain ChatModel 封装。

    使用 DashScope Generation API 调用通义千问系列模型。
    支持 qwen-turbo、qwen-plus、qwen-max 等。
    """

    model: str = "qwen-plus"
    temperature: float = 0.1
    _api_key_set: bool = False

    def __init__(self, model: str | None = None, temperature: float = 0.1, **kwargs):
        super().__init__(model=model or settings.MODEL_NAME, temperature=temperature, **kwargs)
        if not dashscope.api_key:
            dashscope.api_key = settings.DASHSCOPE_API_KEY

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """调用 DashScope Generation API，返回 ChatResult。"""
        payload = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                payload.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                payload.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                payload.append({"role": "assistant", "content": msg.content})

        response = dashscope.Generation.call(
            model=self.model,
            messages=payload,
            result_format="message",
            temperature=self.temperature,
            stop=stop,
            **kwargs,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope API error: code={response.code}, message={response.message}"
            )

        content = response.output.choices[0].message.content
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """流式调用（暂未实现，按需扩展）。"""
        raise NotImplementedError("Streaming is not yet supported for DashScope")

    @property
    def _llm_type(self) -> str:
        return f"dashscope-{self.model}"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model, "temperature": self.temperature}
