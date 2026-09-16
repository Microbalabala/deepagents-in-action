import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from tavily import TavilyClient


# 1. 读取项目根目录的 .env
load_dotenv(Path(__file__).parent.parent / ".env")

# 2. 接入你已经配置的模型
model=ChatOpenAI(
    model=os.environ["AGENTSEEK_MODEL"],
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"] or None,
)

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_deep_agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "北京今天天气怎么样？"}]}
)

print(result["messages"][-1].content)

# 运行结果：
#  % uv run --active python lessons/task2.py
# 北京今天天气晴朗！☀️ 适合出门活动，记得防晒哦~