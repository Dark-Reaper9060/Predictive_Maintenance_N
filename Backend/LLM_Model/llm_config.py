from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv

load_dotenv()

llm_model = init_chat_model(
    model="gpt-5-chat",
    model_provider= "azure_openai",
    api_version = "2025-01-01-preview",
    azure_endpoint = os.getenv("MODEL_ENDPOINT"),
    api_key = os.getenv("MODEL_KEY")
)
