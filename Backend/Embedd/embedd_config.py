import os
from dotenv import load_dotenv

from langchain_openai import AzureOpenAIEmbeddings


load_dotenv()

embedding_model = AzureOpenAIEmbeddings(
    model=os.getenv("EMBEDD_MODEL"),
    dimensions=os.getenv("EMBEDD_DIMENSIONS"),
    api_version=os.getenv("EMBEDD_VERSION"),
    azure_endpoint=os.getenv("EMBED_ENDPOINT"),
    api_key=os.getenv("EMBED_KEY")
)