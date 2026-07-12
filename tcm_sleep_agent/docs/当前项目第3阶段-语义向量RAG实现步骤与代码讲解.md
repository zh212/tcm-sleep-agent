# 当前项目第三阶段 — 语义向量检索 RAG 实现步骤与代码讲解

本文档是第二阶段文档的续篇，用于解释第三阶段语义向量检索 RAG Demo 的新增和改进内容。

**第二阶段**已完成：页面输入症状 → 关键词检索本地知识库 → DeepSeek 生成分析 → 展示检索依据。

**第三阶段**在此基础上：

```text
页面输入症状
→ 通义千问 text-embedding-v4 语义向量编码（1024维）
→ Chroma 向量数据库余弦相似度检索
→ 召回 Top 5 语义相关方剂知识
→ DeepSeek 基于检索上下文生成结构化处方辅助分析
→ 页面展示语义相似度分数、管道执行过程、检索依据
```

---

# 1. 第三阶段新增和改动的文件

```text
tcm_sleep_agent_stage1_basic_call/
├── config/
│   └── settings.py                       ← 新增：集中配置管理
├── src/
│   ├── services/                         ← 新增：服务层目录
│   │   ├── __init__.py
│   │   ├── embedding_service.py          ← 新增：通义千问 Embedding API 封装
│   │   ├── retrieval_service.py          ← 新增：Chroma 向量检索服务
│   │   └── generation_service.py         ← 新增：升级版 LLM 生成服务
│   ├── ui/                               ← 新增：UI 层目录（预留）
│   │   └── __init__.py
│   ├── llm.py                            ← 保留：旧版兼容
│   ├── retriever.py                      ← 保留：关键词检索备选
│   └── __init__.py
├── data/
│   ├── insomnia_formulas.json            ← 未变：源知识库
│   └── vector_store/                     ← 新增：Chroma 持久化向量库
├── app.py                                ← 改写：企业级语义检索 UI
├── requirements.txt                      ← 改动：新增 chromadb 依赖
└── .env                                  ← 改动：新增 DASHSCOPE_API_KEY
```

改动清单：

| 文件 | 操作 | 说明 |
|---|---|---|
| `config/settings.py` | 新增 | 集中管理所有 API Key、路径、参数 |
| `src/services/embedding_service.py` | 新增 | 通义千问 text-embedding-v4 API 调用 |
| `src/services/retrieval_service.py` | 新增 | Chroma 向量库管理 + 语义检索 |
| `src/services/generation_service.py` | 新增 | 升级版 RAG 生成，企业级 Prompt |
| `app.py` | 改写 | sidebar、管道展示、相似度三档分类 |
| `requirements.txt` | 改动 | 新增 `chromadb>=0.5.0` |
| `.env` | 改动 | 新增 `DASHSCOPE_API_KEY` |

---

# 2. 核心架构变化：为什么引入服务分层？

## 第二阶段架构

```text
app.py → src/retriever.py → src/llm.py → DeepSeek API
```

所有模块平级，配置散落在各处，没有清晰的分层。

## 第三阶段架构

```text
app.py（UI 层）
    ↓
src/services/retrieval_service.py（服务层）
    ↓
src/services/embedding_service.py（基础设施层）
    ↓
Chroma 向量库

app.py（UI 层）
    ↓
src/services/generation_service.py（服务层）
    ↓
DeepSeek API

config/settings.py → 所有层共享的集中配置
```

每个模块有明确的职责边界：

| 层 | 职责 | 不负责 |
|---|---|---|
| `config/` | 提供所有配置常量 | 不包含业务逻辑 |
| `src/services/` | 业务逻辑：embedding、检索、生成 | 不处理 UI |
| `app.py` | Streamlit 页面展示 | 不直接调 API |

这样做的好处：

1. 换 Embedding 模型？只改 `embedding_service.py`；
2. 换向量库？只改 `retrieval_service.py`；
3. 换大模型？只改 `generation_service.py`；
4. 换 UI 框架？只改 `app.py`；
5. 评测时可以直接调服务层，不需要启动 Streamlit。

---

# 3. 新增文件详细讲解

## 3.1 `config/settings.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\config\settings.py
```

作用：集中管理所有配置项。所有 API Key、模型名、路径、默认参数都在这里定义，其他模块导入使用。

```python
"""Centralized configuration for the TCM Sleep Agent."""

import os
from dotenv import load_dotenv

load_dotenv()


# -- DeepSeek (LLM Generation) --
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# -- DashScope (Embedding) --
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_MODEL: str = "text-embedding-v4"
EMBEDDING_DIMENSIONS: int = 1024

# -- Chroma Vector Store --
VECTOR_STORE_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "vector_store"
)
COLLECTION_NAME: str = "tcm_insomnia_formulas"

# -- Knowledge Base --
KNOWLEDGE_BASE_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "insomnia_formulas.json"
)

# -- Retrieval --
DEFAULT_TOP_K: int = 5
```

### 设计要点

**为什么不用类或字典？**

用模块级常量，导入就是 `from config.settings import DASHSCOPE_API_KEY`，一行搞定。比类实例简单，比字典有类型提示。

**路径为什么用 `os.path.join(os.path.dirname(...), ...)`？**

不写死绝对路径。项目移动到任何位置，路径自动计算正确。

---

## 3.2 `src/services/embedding_service.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\src\services\embedding_service.py
```

作用：封装通义千问 Embedding API 调用，通过 DashScope OpenAI 兼容协议。

### 为什么选通义千问 Embedding 而不是本地模型？

| 对比项 | 本地 BGE 模型 | 通义千问 Embedding API |
|---|---|---|
| 需要下载 | 1.3 GB 模型文件 | 无需下载 |
| HuggingFace 网络 | 可能被墙 | 不需要 |
| 代码复杂度 | 需装 sentence-transformers | 复用现有 openai SDK |
| 中文效果 | 好 | 更好（CMTEB 71.99） |
| 费用 | 免费 | 0.0005 元/千 token（几乎免费） |
| query/document 分离 | 不支持 | 原生支持，专为检索优化 |

### 与 DeepSeek 调用模式的对比

| 项目 | DeepSeek（生成） | DashScope（Embedding） |
|---|---|---|
| 调用方式 | `client.chat.completions.create()` | `client.embeddings.create()` |
| base_url | `api.deepseek.com` | `dashscope.aliyuncs.com/compatible-mode/v1` |
| 模型 | `deepseek-chat` | `text-embedding-v4` |

同一个 `openai` SDK，两个 base_url，两种 API——这就是 OpenAI 兼容协议的价值。

### 完整代码

```python
"""DashScope embedding service via OpenAI-compatible protocol."""

from openai import OpenAI

from config.settings import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)


def _get_embedding_client() -> OpenAI:
    if not DASHSCOPE_API_KEY:
        raise RuntimeError("请先在 .env 文件中配置 DASHSCOPE_API_KEY。")
    return OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)


def embed_text(text: str, text_type: str = "document") -> list[float]:
    """Convert a single text into an embedding vector.

    Args:
        text: The text to embed.
        text_type: "query" for user queries, "document" for knowledge base entries.
    """
    client = _get_embedding_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
        extra_body={"text_type": text_type},
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], text_type: str = "document") -> list[list[float]]:
    """Convert multiple texts into embedding vectors."""
    if not texts:
        return []
    client = _get_embedding_client()
    all_embeddings = []
    for i in range(0, len(texts), 10):
        batch = texts[i : i + 10]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            dimensions=EMBEDDING_DIMENSIONS,
            extra_body={"text_type": text_type},
        )
        all_embeddings.extend([d.embedding for d in response.data])
    return all_embeddings
```

### 核心概念：`text_type="query"` vs `text_type="document"`

text-embedding-v4 区别对待"查询"和"文档"：

| text_type | 用途 | 编码行为 |
|---|---|---|
| `"query"` | 用户输入的症状描述 | 编码为"问题方向"的向量 |
| `"document"` | 知识库中的方剂条目 | 编码为"内容方向"的向量 |

这意味着同一段文字，用 `query` 编码和用 `document` 编码得到的向量是不同的。对 RAG 检索来说，**查询用 query，文档用 document** 可以显著提升召回精度。

### `extra_body`

```python
extra_body={"text_type": text_type}
```

这是 OpenAI SDK 的扩展字段机制。`text_type` 不是标准 OpenAI 参数（OpenAI 没有 query/document 区分），所以不能直接传在 `create()` 的顶层参数中，必须以 `extra_body` 方式透传到 DashScope API。

### 批量请求

```python
for i in range(0, len(texts), 10):
    batch = texts[i : i + 10]
```

DashScope API 单次最多接收 10 条输入。所以 `embed_batch()` 自动按 10 条一组分批发送。

---

## 3.3 `src/services/retrieval_service.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\src\services\retrieval_service.py
```

作用：管理 Chroma 向量数据库，提供知识索引和语义检索。

### 为什么选 Chroma？

| 向量库 | 安装方式 | 持久化 | Windows 兼容 | 适用场景 |
|---|---|---|---|---|
| FAISS | pip/conda | 需手动保存 | 一般 | 大规模纯内存检索 |
| Chroma | pip install | 自动持久化 | 好 | 本地 Demo → 小规模生产 |
| Milvus | Docker/服务 | 是 | 差（需 Docker） | 企业级大规模生产 |

Chroma 最合适当前阶段：pip 直接装，不需要 Docker，自动持久化，和 sqlite 一样方便。

### 完整代码

```python
"""Chroma-based semantic retrieval service."""

import json
import os

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import (
    VECTOR_STORE_PATH,
    COLLECTION_NAME,
    KNOWLEDGE_BASE_PATH,
    DEFAULT_TOP_K,
)
from src.services.embedding_service import embed_text, embed_batch


def _get_collection() -> chromadb.Collection:
    """Get or create the Chroma collection."""
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    client = chromadb.PersistentClient(
        path=VECTOR_STORE_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
```

### 3.3.1 `_get_collection()` — 获取或创建向量集合

```python
client = chromadb.PersistentClient(path=VECTOR_STORE_PATH, ...)
```

`PersistentClient` 把向量数据持久化到磁盘。路径指向 `data/vector_store/`。

```python
metadata={"hnsw:space": "cosine"}
```

指定相似度算法为余弦相似度（cosine similarity）。这是语义检索最常用的度量方式。

### 3.3.2 `build_index()` — 构建向量索引

```python
def build_index(force_rebuild: bool = False) -> int:
    collection = _get_collection()

    existing = collection.count()
    if existing > 0 and not force_rebuild:
        return existing
```

如果索引已存在且不强制重建，直接返回已有数量。否则从 JSON 读取知识库，逐条向量化后写入 Chroma。

**知识到文本的转换：**

```python
text_parts = [
    f"方剂：{item['name']}",
    f"证型：{item['syndrome']}",
    f"适用症状：{'、'.join(item['symptoms'])}",
    f"功效：{item['effects']}",
    f"组成：{'、'.join(item['ingredients'])}",
    f"注意事项：{item['notes']}",
]
texts.append("\n".join(text_parts))
```

每条知识拼接成一段完整文本，再用 `embed_batch()` 做 `text_type="document"` 编码。

**为什么要拼成一段文本再向量化？**

而不是把每个字段单独向量化再做加权？因为 text-embedding-v4 的 `text_type="document"` 已经针对文档编码做了优化。把完整知识作为一段文本输入，模型能理解上下文关系；拆成碎片反而丢失语义。

### 3.3.3 `search()` — 语义检索

```python
def search(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    collection = _get_collection()

    if collection.count() == 0:
        build_index()

    query_embedding = embed_text(query, text_type="query")
```

关键：查询用 `text_type="query"`。这与建索引时的 `text_type="document"` 配套，利用了 v4 的非对称编码能力。

```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k,
    include=["documents", "metadatas", "distances"],
)
```

Chroma 的 `query()` 返回匹配结果。`distances` 是余弦距离（0-2 之间），我们转换为相似度：

```python
distance = results["distances"][0][i] if results["distances"] else 0.0
similarity = 1.0 - distance
```

- 余弦距离 = 0 → 完全相似 → 相似度 = 1.0
- 余弦距离 = 2 → 完全不相似 → 相似度 = -1.0
- 余弦距离 = 1 → 正交 → 相似度 = 0

实际中相似度通常在 0.3-0.9 之间。

---

## 3.4 `src/services/generation_service.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\src\services\generation_service.py
```

作用：升级版 LLM 生成服务，接收检索结果、构造上下文 Prompt、调用 DeepSeek。

### 与第二阶段 `src/llm.py` 的关键区别

| 方面 | 第二阶段 | 第三阶段 |
|---|---|---|
| 检索结果字段 | `match_score`（关键词分数） | `similarity_score`（余弦相似度） |
| Prompt 定位 | 说明型助手 | RAG 处方分析引擎 |
| 相似度阈值 | 无 | < 0.5 需说明匹配不足 |
| 输出结构 | 6 部分 | 7 部分（新增检索证据摘要） |

### 系统提示词升级

```python
SYSTEM_PROMPT = """你是一个部署在中医失眠智能辅助系统中的 RAG 处方分析引擎。
本系统是省级大创项目原型，长期目标是与中医院合作，作为智能处方辅助工具部署于科室场景。

你必须遵守以下规则：
1. 仅基于「检索知识」部分提供的内容进行辅助分析，不要编造知识库中没有的方剂。
2. 如果检索结果匹配度低（相似度 < 0.5），请在分析中明确说明"当前知识库检索匹配度较低，以下分析仅供参考"。
3. 不要给出具体药物剂量（克数）。
4. 不要声称可以替代执业医师。
5. 必须包含医疗免责声明。

请按以下结构输出：

## 症状摘要
## 证型判断
## 参考方剂（按相似度排序）
## 处方分析思路
## 用药注意事项
## 检索证据摘要
## 医疗免责声明
"""
```

比第二阶段多了一层"检索证据摘要"——让模型明确列出引用了哪些检索依据，方便溯源。

### DeepSeek 收费提醒

你每次分析大概 2000-4000 tokens，DeepSeek 价格 2 元/百万 tokens → **每次分析约 1 分钱**。100 万免费额度够用上千次。

---

## 3.5 `data/vector_store/`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\data\vector_store\
```

作用：Chroma 持久化向量数据库的存储目录。

这是 Chroma 自动创建和维护的目录，里面是向量索引文件。不需要手动编辑。

如果知识库改了（比如 `insomnia_formulas.json` 增加了新条目），需要点「重建知识索引」按钮重新向量化。

---

# 4. 改动文件详细讲解

## 4.1 `app.py`（升级后）

<details>
<summary>完整代码（折叠）</summary>

```python
"""TCM Insomnia Prescription Auxiliary System — Semantic RAG Demo."""

import streamlit as st

from src.services.retrieval_service import build_index, search
from src.services.generation_service import generate_analysis
```
</details>

### 4.1.1 新增：Sidebar

```python
with st.sidebar:
    st.header("⚙️ 系统信息")
    st.markdown(
        """
        **省级大创项目原型**

        基于 RAG + 语义向量检索的中医失眠
        处方智能辅助生成系统。

        目标场景：中医院科室级智能辅诊。
        """
    )
```

左侧 sidebar 显示项目定位，比第二阶段没有 sidebar 更专业。

### 4.1.2 新增：索引管理按钮

```python
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    analyze_btn = st.button("🔍 开始分析", type="primary", use_container_width=True)
with col2:
    rebuild_btn = st.button("🔄 重建知识索引", use_container_width=True)
```

单独提供「重建知识索引」按钮，用户可以在知识库更新后手动刷新向量索引，不需要重启应用。

### 4.1.3 升级：RAG 执行管道展示

```python
pipeline_steps = [
    "症状输入 → 文本预处理",
    "通义千问 text-embedding-v4 语义向量编码",
    "Chroma 向量数据库余弦相似度检索",
    f"召回 Top {len(retrieved)} 条相关知识",
    "DeepSeek 基于检索上下文生成结构化分析",
]
```

比第二阶段更详细地展示了每一步用了什么技术。对评审老师来说，这个管道展示就是最好的技术路线说明。

### 4.1.4 升级：相似度三档分类

```python
sim = item["similarity_score"]
if sim >= 0.7:
    badge = "🟢 高相关"
elif sim >= 0.5:
    badge = "🟡 中相关"
else:
    badge = "🔴 低相关"
```

用颜色标记相关度等级，比第二阶段显示原始分数更直观。

### 4.1.5 新增：版本演进追踪

```python
v1, v2, v3 = st.columns(3)
with v1: st.markdown("**V1 · 最小闭环** ...")
with v2: st.markdown("**V2 · 关键词RAG** ...")
with v3: st.markdown("**V3 · 语义向量RAG** ← 当前 ...")
```

底部展示三个版本的完成情况，评审老师一眼就能看到项目演进路线。

---

# 5. 第三阶段运行流程总览

```text
1. 用户打开 http://127.0.0.1:8501
   ↓
2. Streamlit 运行 app.py
   ↓
3. 页面显示标题、sidebar、输入框、按钮
   ↓
4. 用户输入失眠症状
   ↓
5. 用户点击「开始分析」
   ↓
6. app.py 调用 build_index()（如已存在则跳过）
   ↓
7. app.py 调用 search(user_input, top_k=5)
   ↓
8. search() 调用 embed_text(query, text_type="query")
   ↓
9. embedding_service.py 通过 DashScope API 生成 1024 维查询向量
   ↓
10. Chroma 以余弦相似度检索 Top 5 相关知识
   ↓
11. 返回结果，包含方剂信息 + 相似度分数
   ↓
12. app.py 展示 RAG 执行管道
   ↓
13. app.py 展示检索依据（三档相似度 + 两栏卡片）
   ↓
14. app.py 调用 generate_analysis(user_input, retrieved)
   ↓
15. generation_service.py 格式化检索结果为文本
   ↓
16. 检索文本 + 用户输入 + 系统提示词 → 拼成完整 Prompt
   ↓
17. 通过 OpenAI SDK 请求 DeepSeek API
   ↓
18. DeepSeek 基于检索上下文生成结构化处方分析
   ↓
19. 页面展示 AI 分析结果
```

---

# 6. 第三阶段实现步骤回顾

## 第一步：开通通义千问 Embedding 服务

在 https://dashscope.aliyun.com 注册并获取 API Key。

## 第二步：配置环境变量

在 `.env` 文件中新增一行：

```env
DASHSCOPE_API_KEY=你的阿里云百炼APIKey
```

## 第三步：安装新依赖

```powershell
.\.venv\Scripts\python.exe -m pip install chromadb
```

## 第四步：创建服务层目录

```powershell
New-Item -ItemType Directory -Force src\services, src\ui, config, data\vector_store
```

## 第五步：编写 config/settings.py

集中定义所有配置常量。

## 第六步：编写 embedding_service.py

封装 DashScope Embedding API。

## 第七步：编写 retrieval_service.py

Chroma 向量库管理 + 语义检索。

## 第八步：编写 generation_service.py

升级版 LLM 生成，接收检索结果。

## 第九步：升级 app.py

sidebar、管道展示、相似度三档、版本追踪。

## 第十步：构建索引并验证

```powershell
python -c "from src.services.retrieval_service import build_index; print(build_index(force_rebuild=True))"
python -c "from src.services.retrieval_service import search; r = search('入睡困难，多梦易醒，心悸健忘'); print(r)"
```

---

# 7. 关键词检索 vs 语义检索：为什么这是质变

### 举例说明

| 用户输入 | 关键词检索 | 语义检索 |
|---|---|---|
| "睡不着，心慌" | 0 条命中（"失眠""心悸"不同词） | 召回归脾汤等（语义理解） |
| "晚上躺床上翻来覆去睡不着" | 0 条命中 | 召回酸枣仁汤、温胆汤等 |
| "心里烦躁，睡不着，口干" | 可能命中"失眠""烦躁" | 精准召回黄连阿胶汤（阴虚火旺） |
| "睡觉老做噩梦，容易惊醒" | 可能命中"多梦""易惊" | 召回安神定志丸（心胆气虚） |

语义检索的 1024 维向量空间能够捕捉"睡不着 ≈ 失眠""心慌 ≈ 心悸""烦躁 ≈ 心烦"的同义关系，这是关键词匹配永远做不到的。

---

# 8. 第三阶段的核心设计思想

## 8.1 query/document 非对称编码

查询和文档用不同的 `text_type` 编码，利用 text-embedding-v4 的非对称特性提升检索精度。这是产品级的 Embedding 模型才有的能力，开源模型做不到。

## 8.2 配置集中管理

所有 Key、路径、参数在一个文件里，换环境、换人部署时一目了然。评审老师看代码时也能快速理解项目用了哪些外部服务。

## 8.3 优雅降级

检索结果不足时，LLM 会如实说明匹配度低，而不是强行编造。这在中医院合作场景中非常重要——不能给医生不可靠的建议。

## 8.4 向量索引持久化

Chroma 自动保存到 `data/vector_store/`。应用重启不需要重建索引，减少 Embedding API 调用费用。

---

# 9. 常见问题排查

## 9.1 Embedding API 调用失败

检查：

1. `.env` 中是否配置了 `DASHSCOPE_API_KEY`；
2. 阿里云百炼账号是否有免费额度或余额；
3. 网络是否能访问 `dashscope.aliyuncs.com`。

## 9.2 检索结果全部低相似度

可能原因：

- 用户输入的症状太过模糊（如只写"失眠"两个字）；
- 知识库条目不覆盖该证型；
- 向量索引需要重建（点「重建知识索引」按钮）。

正常范围的相似度在 0.4-0.9 之间。如果全部 < 0.3，说明知识库内容与用户输入差异大。

## 9.3 Chroma 索引为空

如果提示"知识库索引为空"，先点「重建知识索引」按钮。如果失败，检查 `data/insomnia_formulas.json` 是否存在。

## 9.4 DeepSeek 余额不足

去 https://platform.deepseek.com/usage 查看余额。余额不足时充值 10 元即可（约 1000 次分析）。

---

# 10. 第三阶段核心知识点

1. 语义向量检索替代关键词匹配，用 cosine similarity 做度量；
2. text-embedding-v4 支持 query/document 非对称编码，专为检索优化；
3. Chroma 是轻量级向量数据库，pip 安装，自动持久化；
4. 服务层架构：配置 (config) → 服务 (services) → UI (app.py)；
5. 检索结果用三档分类（高/中/低相关）替代原始分数。

一句话总结：

> 这是一个用 Streamlit 做界面、通义千问 Embedding v4 做语义编码、Chroma 做向量检索、DeepSeek 做处方生成的中医失眠智能辅助系统原型。省级大创立项，目标场景为中医院科室级辅诊。

---

# 11. 下一阶段建议方向

1. **混合检索 + Reranker**：BM25 补充关键词信息 + Cross-Encoder 精排；
2. **动态 Few-shot**：根据相似度阈值自适应选择示例数量；
3. **安全规则引擎**：十八反、十九畏配伍禁忌自动检查；
4. **舌脉结构化输入**：新增舌象、脉象字段，纳入检索约束；
5. **离线评测体系**：leave-one-out 评测，Top-5 herb recall >= 80%。

---

# 12. 第三阶段结论

第三阶段已将系统从关键词 RAG 升级为语义向量 RAG。核心变化：

1. 通义千问 Embedding v4 替代关键词匹配，检索从"同词命中"变为"语义理解"；
2. Chroma 向量数据库提供持久化余弦相似度检索；
3. 项目架构升级为企业级三层分离（config / services / ui）；
4. UI 提升为企业级界面（sidebar、管道展示、三档相似度分类）；
5. 项目定位从"课程 Demo"升级为"省级大创原型，中医院合作目标"。
