import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from tavily import TavilyClient
from typing import Literal

# 1. 读取项目根目录的 .env
load_dotenv(Path(__file__).parent.parent / ".env")

# 2. 接入你已经配置的模型
model = ChatOpenAI(
    model=os.environ["AGENTSEEK_MODEL"],
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_API_BASE"] or None,
)

# 2. 初始化搜索客户端
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


# 3. 定义搜索工具
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search for the given query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        topic: The topic category for the search.
        include_raw_content: Whether to include raw page content.
    """
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


# 4. 定义系统提示词
research_instructions = """你是一位专业的研究员。
你的工作是进行深入研究，然后撰写一份完整的研究报告。

你可以使用 internet_search 工具搜索互联网获取信息。
"""

# 5. 创建 Agent
agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt=research_instructions,
)

# 6. 运行
result = agent.invoke({"messages": [{"role": "user", "content": "什么是 LangGraph？"}]})
print(result["messages"][-1].content)


# 实验结果：
# % uv run --active python lessons/task2-3.py
# ### LangGraph 研究报告

# **1. 定义与背景**
# LangGraph 是由 **LangChain** 开发的开源 AI 代理框架，专注于构建、部署和管理复杂的生成式 AI 代理工作流。它采用图结构（graph-based architecture）来建模代理流程中各组件的关系，支持状态化、循环和分支逻辑，适用于需要动态路由和多步骤交互的场景。

# ---

# **2. 核心特点**
# - **图结构工作流**：
#   工作流被建模为 **有向图**，节点（Node）表示具体操作（如调用模型、工具或确定性逻辑），边（Edge）定义操作间的依赖关系和数据流动。支持循环、并行分支等复杂结构，突破传统线性流程限制。
# - **混合逻辑支持**：
#   允许将 **确定性步骤**（如代码逻辑）与 **LLM驱动的代理步骤** 集成到同一图中，实现灵活的业务逻辑组合。例如：
#   ```python
#   # 示例伪代码（混合步骤）
#   state = {"input": "用户请求"}
#   node1 = DeterministicStep(process_input)
#   node2 = LLMStep(prompt="生成响应")
#   graph = NodeSequence(node1, node2)
#   ```
# - **状态管理（State）**：
#   提供全局状态存储机制，记录代理执行过程中的关键信息（如上下文、中间结果），支持跨节点的数据共享与持久化。
# - **生产级能力**：
#   支持 **持久化执行**（durable execution）、**流式处理**（streaming）、**人工介入**（human-in-the-loop）等特性，适用于长期运行的复杂系统。

# ---

# **3. 与 LangChain 的区别**
# | 维度         | LangGraph                          | LangChain                          |
# |--------------|------------------------------------|------------------------------------|
# | **适用场景** | 复杂、状态化的工作流（如多轮对话、任务分解） | 简单线性流程（如问答链、检索链）     |
# | **抽象层级** | 底层框架（需手动定义图结构）         | 高层接口（提供预设组件和流程）       |
# | **灵活性**   | 更高（支持任意图拓扑）               | 较低（更适合标准流程）              |
# | **典型用途** | 自动化系统、多代理协作、长期任务管理    | 快速构建原型、简单 AI 应用           |

# > **关键优势**：LangGraph 不绑定特定模型架构，允许开发者根据需求定制逻辑，而 LangChain 更注重标准化接口。

# ---

# **4. 实际应用**
# - **企业案例**：
#   - **挪威邮轮公司**：用于构建客舱AI系统，通过状态记录提升用户体验。
#   - **Klarna、Uber、J.P. Morgan**：用于金融、出行等领域的复杂代理系统。
# - **技术场景**：
#   支持 **多代理协作**（如分工处理任务）、**循环验证**（如多次调用模型优化结果）、**条件分支**（如根据用户输入动态调整流程）。

# ---

# **5. 开发与部署**
# - **开源属性**：
#   使用 **MIT 协议** 开源，可自由集成到项目中。
# - **安装方式**：
#   通过 `pip install -U langgraph` 安装，配套工具包括：
#   - **LangSmith Deployment**：一键部署代理，提供可扩展的基础设施。
#   - **Deep Agents**（基于 LangGraph 的高级封装）：支持子代理调用、文件系统交互等复杂功能。
# - **技术生态**：
#   提供 Python（LangGraph）、JavaScript（LangGraph.js）等多语言支持，并与 VSCode、Claude 等工具集成。

# ---

# **6. 技术启示**
# LangGraph 的设计反映了 AI 代理开发的趋势：
# 1. **从线性到图结构**：解决传统流程无法处理的复杂逻辑问题。
# 2. **状态透明化**：通过状态追踪实现流程可审计性和调试能力。
# 3. **模块化扩展**：开发者可自由组合节点和边，适应个性化需求。
