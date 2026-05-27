import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen-plus")
    MODEL_NAME_SIMPLE: str = os.getenv("MODEL_NAME_SIMPLE", "qwen-turbo")
    MODEL_NAME_COMPLEX: str = os.getenv("MODEL_NAME_COMPLEX", "qwen-plus")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "ai-job-copilot")

    TEMP_DIR: str = os.getenv("TEMP_DIR", "./tmp")

    def validate(self) -> bool:
        if not self.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set in .env")
        return True


settings = Settings()
