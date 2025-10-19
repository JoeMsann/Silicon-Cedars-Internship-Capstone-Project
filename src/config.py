import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

class Config:
    """
    Configuration class to hold API keys and other parameters.
    """
    def __init__(self):
        """
        Initializes the configuration by loading environment variables and LLM models.
        """
        self.groq_api_key: str = os.getenv("GROQ_API_KEY")
        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY")
        self.langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY")
        
        # Initialize models
        # GPT OSS 120B
        self.tool_model = ChatGroq(
            model="openai/gpt-oss-120b",
            response_format={"type": "json_object"},
            api_key=self.groq_api_key
        )
        self.sql_model = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=self.groq_api_key
        )
        # Kimi K2 Instruct
        self.conversation_model = ChatGroq(
            model="moonshotai/kimi-k2-instruct-0905",
            temperature=1,
            api_key=self.groq_api_key
        )
        # Qwen 3 32B 
        self.rag_model = ChatGroq(
            model="qwen/qwen3-32b",
            temperature=0,
            api_key=self.groq_api_key
        )
        # GPT OSS 20B
        self.reasoning_model = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            api_key=self.groq_api_key
        )
        self.search_tool_model = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            api_key=self.groq_api_key
        )


# A single instance to be imported across the project
app_config = Config()
