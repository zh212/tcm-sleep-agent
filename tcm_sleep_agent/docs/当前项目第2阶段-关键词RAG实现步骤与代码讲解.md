# 当前项目第二阶段—关键词检索 RAG 实现步骤与代码讲解

本文档是第一阶段 `当前项目实现步骤与代码讲解.md` 的续篇，用于解释第二阶段关键词检索 RAG Demo 的新增和改进内容。

**第一阶段**已完成：Streamlit 页面输入症状 → 调用 DeepSeek → 返回分析文本。

**第二阶段**在此基础上加入：

```text
页面输入症状
→ 关键词检索本地中医失眠方剂/证型知识库
→ 将检索结果注入 DeepSeek 提示词
→ DeepSeek 基于检索知识生成结构化辅助分析
→ 页面展示 RAG 执行过程和检索依据
```

---

# 1. 第二阶段新增和改动的文件

```text
tcm_sleep_agent/
├── data/                                    ← 新增目录
│   └── insomnia_formulas.json               ← 新增：本地中医失眠知识库
├── src/
│   ├── __init__.py                          ← 未变
│   ├── llm.py                               ← 已改动：接收检索结果注入提示词
│   └── retriever.py                         ← 新增：关键词检索模块
├── app.py                                   ← 已改动：展示 RAG 执行过程和检索依据
├── .env / .env.example / requirements.txt   ← 未变
└── docs/
    ├── 当前项目实现步骤与代码讲解.md           ← 第一阶段文档
    └── 当前项目第二阶段-关键词RAG实现步骤与代码讲解.md  ← 本文档
```

改动清单：

| 文件 | 操作 | 说明 |
|---|---|---|
| `data/insomnia_formulas.json` | 新增 | 10 条失眠方剂/证型演示知识 |
| `src/retriever.py` | 新增 | 关键词检索，从知识库召回相关条目 |
| `src/llm.py` | 改写 | 新增 `_format_retrieved_knowledge()`，`chat_with_deepseek()` 改为接收检索结果 |
| `app.py` | 改写 | 新增检索调用、RAG 执行过程展示、检索依据展示 |

---

# 2. 新增文件详细讲解

## 2.1 `data/insomnia_formulas.json`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\data\insomnia_formulas.json
```

作用：本地的中医失眠方剂/证型演示知识库。

### 为什么是 JSON？

JSON 格式简单、Python 自带解析、不需要额外依赖，适合当前阶段。后续可以升级为向量数据库中的节点。

### 为什么不用向量检索？

第二阶段故意先用关键词匹配，目的：

1. 不引入 embedding 模型和向量数据库，降低环境复杂度；
2. 先验证"知识库 + 检索 + 生成"的完整 RAG 链路；
3. 后续可以平滑替换检索方式，不影响 UI 和 LLM 模块。

### 数据格式

每条知识包含 7 个字段：

```json
{
  "id": "guipi-tang",
  "name": "归脾汤",
  "syndrome": "心脾两虚",
  "symptoms": ["失眠", "多梦", "心悸", "健忘", "食少", "乏力"],
  "effects": "益气补血，健脾养心",
  "ingredients": ["党参", "白术", "黄芪", "当归", "酸枣仁", "龙眼肉", "远志", "木香", "甘草"],
  "notes": "课程演示知识，不作为真实处方依据。"
}
```

| 字段 | 含义 | 检索时是否使用 |
|---|---|---|
| `id` | 唯一标识 | 否 |
| `name` | 方剂名称 | 是，命中 +1 分 |
| `syndrome` | 证型 | 是，命中 +2 分 |
| `symptoms` | 适用症状列表 | 是，命中每个 +2 分 |
| `effects` | 功效 | 是，功效关键词命中 +1 分 |
| `ingredients` | 药物组成 | 否（仅做展示） |
| `notes` | 注意事项 | 否（仅做展示） |

### 首批知识（10 条）

| # | 方剂 | 证型 |
|---|---|---|
| 1 | 酸枣仁汤 | 肝血不足，虚热内扰 |
| 2 | 归脾汤 | 心脾两虚 |
| 3 | 天王补心丹 | 心肾阴虚 |
| 4 | 温胆汤 | 痰热扰心 |
| 5 | 黄连阿胶汤 | 阴虚火旺，心肾不交 |
| 6 | 甘麦大枣汤 | 心脾血虚，脏躁 |
| 7 | 安神定志丸 | 心胆气虚 |
| 8 | 朱砂安神丸 | 心火亢盛 |
| 9 | 柴胡加龙骨牡蛎汤 | 肝郁化火，烦躁惊悸 |
| 10 | 柏子养心丸 | 心气不足，心血亏虚 |

所有条目的 `notes` 字段都明确标注"课程演示知识，不作为真实处方依据"。

---

## 2.2 `src/retriever.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\src\retriever.py
```

作用：从本地 JSON 知识库中按关键词检索相关方剂/证型。

### 完整代码

```python
"""Keyword-based retriever for the local TCM insomnia knowledge base."""

import json
import os


_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "insomnia_formulas.json")


def load_knowledge_base() -> list[dict]:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _score(item: dict, user_input: str) -> tuple[int, list[str]]:
    text = user_input
    score = 0
    matched: list[str] = []

    for symptom in item.get("symptoms", []):
        if symptom in text:
            score += 2
            matched.append(symptom)

    syndrome = item.get("syndrome", "")
    if syndrome and any(part in text for part in syndrome.replace("，", ",").replace("、", ",").split(",")):
        for part in syndrome.replace("，", ",").replace("、", ",").split(","):
            part = part.strip()
            if part and part in text:
                score += 2
                if part not in matched:
                    matched.append(part)

    name = item.get("name", "")
    if name and name in text:
        score += 1
        if name not in matched:
            matched.append(name)

    effects = item.get("effects", "")
    if effects:
        for word in ["安神", "养血", "清心", "滋阴", "益气", "补血", "健脾", "养心", "化痰", "清热", "除烦", "疏肝", "镇惊", "交通心肾"]:
            if word in effects and word in text:
                score += 1
                if word not in matched:
                    matched.append(word)

    return score, matched


def retrieve_formulas(user_input: str, top_k: int = 3) -> list[dict]:
    items = load_knowledge_base()
    scored = []
    for item in items:
        score, matched = _score(item, user_input)
        result = {**item, "match_score": score, "matched_keywords": matched}
        scored.append(result)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    top = scored[:top_k]
    top = [r for r in top if r["match_score"] > 0]

    if not top:
        top = [
            {**scored[0], "match_score": 0, "matched_keywords": ["无直接命中，返回通用参考"]},
        ]
        return top

    return top
```

### 2.2.1 知识库路径计算

```python
_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "insomnia_formulas.json")
```

这行代码动态计算 JSON 文件路径，不写死绝对路径。
os.path.dirname(路径)
功能：拿到传入路径的上级文件夹目录

拆解：

1. `__file__` → 当前文件路径：`.../src/retriever.py`
2. `os.path.dirname(__file__)` → `.../src`
3. `os.path.dirname(...)` 再套一层 → `.../`（项目根目录）
4. `os.path.join(..., "data", "insomnia_formulas.json")` → `.../data/insomnia_formulas.json`

好处：无论项目放在哪里，都能找到知识库文件。

### 2.2.2 `load_knowledge_base()`

```python
def load_knowledge_base() -> list[dict]:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
```

作用：读取 JSON 文件并解析为 Python 列表。

`encoding="utf-8"` 是为了正确处理中文。

### 2.2.3 `_score(item, user_input)` — 评分函数

```python
def _score(item: dict, user_input: str) -> tuple[int, list[str]]:
```

这是一个内部函数（前缀 `_` 表示它是模块私有的），负责计算一条知识条目与用户输入的匹配程度。

返回值是 `(总分, 命中的关键词列表)`。

**评分规则：**

| 匹配类型 | 分值 | 说明 |
|---|---|---|
| 症状关键词命中 | +2 分/个 | 例如用户输入包含"心悸"，且知识库条目症状列表中有"心悸" |
| 证型关键词命中 | +2 分/个 | 例如用户输入包含"心脾两虚"相关关键词 |
| 方剂名称命中 | +1 分 | 例如用户明确提到"归脾汤" |
| 功效关键词命中 | +1 分/个 | 例如用户提到"安神"，且知识条目功效字段包含"安神" |

**症状匹配逻辑：**

```python
for symptom in item.get("symptoms", []):
    if symptom in text:
        score += 2
        matched.append(symptom)
```

遍历知识库条目中每个症状，检查是否出现在用户输入文本中。

**证型匹配逻辑：**

```python
syndrome = item.get("syndrome", "")
if syndrome and any(part in text for part in syndrome.replace("，", ",").replace("、", ",").split(",")):
```

按逗号拆分证型字段（因为证型像"肝血不足，虚热内扰"是两部分），然后逐 part 检查。

**功效匹配逻辑：**

```python
for word in ["安神", "养血", "清心", "滋阴", "益气", ...]:
    if word in effects and word in text:
        score += 1
```

预设一个中医功效关键词表，如果功效包含该词且用户输入也包含该词，则命中。这是一个简单的领域关键词映射。

### 2.2.4 `retrieve_formulas(user_input, top_k=3)` — 检索函数

```python
def retrieve_formulas(user_input: str, top_k: int = 3) -> list[dict]:
```

这是检索模块暴露给外部的唯一函数（`app.py` 会调用它）。

执行流程：

```text
1. 调用 load_knowledge_base() 加载知识库
2. 对每条知识调用 _score() 计算分数
3. 按分数从高到低排序
4. 取 Top K 条
5. 过滤掉分数为 0 的结果
6. 如果全部 0 分，返回一条低置信度通用参考
7. 返回结果列表
```

**边缘情况处理：**

```python
if not top:
    top = [
        {**scored[0], "match_score": 0, "matched_keywords": ["无直接命中，返回通用参考"]},
    ]
```

如果没有任何匹配（所有条目都是 0 分），仍然返回一条，但标记匹配分数为 0 且注明"无直接命中"。这样页面不会空白，LLM 也会在分析中如实说明匹配度低。

---

# 3. 改动文件详细讲解

## 3.1 `src/llm.py`（升级后）

### 改动对比

**第一阶段：**

```python
def chat_with_deepseek(user_input: str) -> str:
```

系统提示词是简单的身份设定，用户消息中不包含检索知识。

**第二阶段：**

```python
def chat_with_deepseek(user_input: str, retrieved_items: list[dict] | None = None) -> str:
```

新增参数 `retrieved_items`，可接收检索模块的输出。

### 新增函数：`_format_retrieved_knowledge()`

```python
def _format_retrieved_knowledge(items: list[dict]) -> str:
    if not items:
        return "未检索到相关知识。"
    parts = []
    for i, item in enumerate(items, 1):
        parts.append(
            f"【检索条目 {i}】\n"
            f"方剂：{item['name']}\n"
            f"证型：{item['syndrome']}\n"
            f"适用症状：{'、'.join(item['symptoms'])}\n"
            f"功效：{item['effects']}\n"
            f"组成：{'、'.join(item['ingredients'])}\n"
            f"注意事项：{item['notes']}\n"
            f"匹配关键词：{'、'.join(item.get('matched_keywords', []))}\n"
        )
    return "\n".join(parts)
```

作用：把检索结果的 Python dict 列表格式化为一段可读的文本，用于注入 DeepSeek 提示词。

格式示例：

```text
【检索条目 1】
方剂：归脾汤
证型：心脾两虚
适用症状：失眠、多梦、心悸、健忘、食少、乏力
功效：益气补血，健脾养心
组成：党参、白术、黄芪、当归、酸枣仁、龙眼肉、远志、木香、甘草
注意事项：外感发热期间慎用。课程演示知识，不作为真实处方依据。
匹配关键词：心悸、健忘、乏力
```

### 升级后的用户消息结构

```python
"用户输入的失眠相关症状如下：\n"
f"{cleaned_input}\n\n"
"以下是系统从本地知识库中检索到的相关知识：\n"
f"{knowledge_text}\n\n"
"请基于上述检索内容，按照系统提示的结构生成辅助分析。"
"如果检索内容匹配度低，请如实说明。"
```

这是 RAG 的核心：**把检索到的知识作为上下文拼接进 Prompt，让模型基于它生成回答**。

### 升级后的系统提示词

```python
SYSTEM_PROMPT = """你是一个基于本地中医失眠知识库的 RAG 辅助分析助手。
当前系统处于课程学习与技术演示阶段，不能替代医生诊断，也不能给出真实处方剂量。

你必须遵守以下规则：
1. 仅基于「检索知识」部分提供的内容进行辅助分析，不要编造知识库中没有的方剂。
2. 如果检索结果匹配度低，请明确说明"当前知识库未检索到高度匹配内容"...
3. 不要给出具体药物剂量。
4. 不要声称可以替代执业医师。
5. 必须包含医疗免责声明。

请按以下结构输出：
## 症状摘要
## 可能证型
## 参考方剂
## 推荐理由
## 注意事项
## 医疗免责声明
"""
```

对比第一阶段：

| 方面 | 第一阶段 | 第二阶段 |
|---|---|---|
| 身份 | 说明型助手 | 基于本地知识库的 RAG 辅助分析助手 |
| 知识约束 | 无 | 只能基于检索知识，不编造方剂 |
| 输出格式 | 不强制 | 强制结构化 6 部分 |
| 免责声明 | 在用户消息中要求 | 在系统提示词中强制要求 |

---

## 3.2 `app.py`（升级后）

### 新增导入

```python
from src.retriever import load_knowledge_base, retrieve_formulas
```

### 按钮点击后的新流程

```python
if st.button("开始分析", type="primary"):
    with st.spinner("正在检索本地知识库并调用 DeepSeek 生成分析结果……"):
        try:
            kb = load_knowledge_base()
            retrieved = retrieve_formulas(user_input)

            # 新增：展示 RAG 执行过程
            st.subheader("RAG 执行过程")
            st.markdown(...)

            # 新增：展示检索依据
            st.subheader("检索依据")
            for i, item in enumerate(retrieved, 1):
                with st.expander(...):
                    st.markdown(...)

            # 传递检索结果给模型
            result = chat_with_deepseek(user_input, retrieved)
```

对比第一阶段流程：

| 步骤 | 第一阶段 | 第二阶段 |
|---|---|---|
| 1 | 接收用户输入 | 接收用户输入 |
| 2 | 直接调用 DeepSeek | 加载知识库 |
| 3 | 展示 AI 分析结果 | 执行关键词检索 |
| 4 | — | 展示 RAG 执行过程 |
| 5 | — | 展示检索依据 |
| 6 | — | 将检索结果传给 DeepSeek |
| 7 | — | 展示 AI 分析结果 |

### RAG 执行过程展示

```python
st.markdown(
    f"- ✅ 已接收症状输入\n"
    f"- ✅ 已加载本地知识库（共 {len(kb)} 条）\n"
    f"- ✅ 已检索并召回 {len(retrieved)} 条相关知识\n"
    f"- ✅ 已将检索结果交由 DeepSeek 生成辅助分析"
)
```

作用：在页面上模拟 Agent 步骤展示，让老师看到系统不是一个普通聊天机器人，而是经历了"检索→生成"的 RAG 流程。

### 检索依据展示

```python
for i, item in enumerate(retrieved, 1):
    with st.expander(
        f"{i}. {item['name']}｜证型：{item['syndrome']}"
        f"｜匹配关键词：{'、'.join(item.get('matched_keywords', []))}｜匹配分数：{item.get('match_score', 0)}"
    ):
        st.markdown(
            f"**方剂名称**：{item['name']}\n\n"
            f"**证型**：{item['syndrome']}\n\n"
            f"**适用症状**：{'、'.join(item['symptoms'])}\n\n"
            ...
        )
```

使用 `st.expander()` 做可折叠卡片，每条检索结果一个卡片。卡片的标题行显示方剂名、证型、匹配关键词和分数，展开后看到完整详情。

这样做的好处：老师能看到系统确实从本地知识库检索到了具体内容，回答不是纯靠模型记忆。

---

# 4. 第二阶段运行流程总览

```text
1. 用户打开 http://127.0.0.1:8501
   ↓
2. Streamlit 运行 app.py
   ↓
3. 页面显示标题、免责声明、输入框、按钮
   ↓
4. 用户输入失眠症状
   ↓
5. 用户点击"开始分析"
   ↓
6. app.py 调用 load_knowledge_base() 加载 10 条知识
   ↓
7. app.py 调用 retrieve_formulas(user_input) 进行关键词检索
   ↓
8. retriever.py 对每条知识调用 _score() 计算匹配分数
   ↓
9. 按分数排序，取 Top 3
   ↓
10. app.py 展示 RAG 执行过程
   ↓
11. app.py 展示检索依据（可折叠卡片）
   ↓
12. app.py 调用 chat_with_deepseek(user_input, retrieved_items)
   ↓
13. llm.py 的 _format_retrieved_knowledge() 把检索结果格式化为文本
   ↓
14. 检索文本 + 用户输入 + 系统提示词 → 拼成完整 Prompt
   ↓
15. 通过 OpenAI SDK 请求 DeepSeek API
   ↓
16. DeepSeek 基于检索知识生成结构化分析
   ↓
17. 页面展示 AI 分析结果
```

---

# 5. 第二阶段实现步骤回顾

## 第一步：创建 `data/` 目录

```powershell
New-Item -ItemType Directory -Force "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\data"
```

## 第二步：写知识库文件

创建 `data/insomnia_formulas.json`，包含 10 条失眠方剂/证型知识。

## 第三步：写检索模块

创建 `src/retriever.py`，实现：

- `load_knowledge_base()`：加载 JSON 知识库；
- `_score()`：关键词匹配评分；
- `retrieve_formulas()`：返回 Top K 检索结果。

## 第四步：升级 LLM 模块

修改 `src/llm.py`：

- 新增 `_format_retrieved_knowledge()` 格式化检索结果；
- `chat_with_deepseek()` 新增 `retrieved_items` 参数；
- 升级系统提示词和用户消息结构。

## 第五步：升级页面

修改 `app.py`：

- 导入检索模块；
- 在按钮点击后加入检索调用；
- 新增 RAG 执行过程展示；
- 新增检索依据展示；
- 将检索结果传给 LLM。

## 第六步：验证

```powershell
# 语法检查
python -m py_compile app.py src\llm.py src\retriever.py

# 检索功能手动验证
python -c "from src.retriever import retrieve_formulas; r = retrieve_formulas('入睡困难，多梦易醒，心悸健忘'); print(r)"

# 启动
.\.venv\Scripts\python.exe -m streamlit run app.py
```

---

# 6. 第二阶段为什么还不算完整的 RAG 系统？

当前实现的是**关键词检索版 RAG**，它具备 RAG 的核心三要素：

```text
检索（Retrieve） → 增强（Augment） → 生成（Generate）
```

但距离完整 RAG 系统还有差距：

| 方面 | 当前阶段 | 完整 RAG 系统 |
|---|---|---|
| 检索方式 | 关键词匹配 | 向量语义检索 + 关键词混合 |
| Embedding | 无 | BGE-M3 / text2vec 等 |
| 向量数据库 | 无 | FAISS / Milvus / Chroma |
| 重排 | 无 | Cross-Encoder / BGE reranker |
| 检索精度 | 依赖同词匹配 | 支持同义词、模糊语义 |
| 动态 Few-shot | 无 | 基于相似度阈值自适应选例 |
| 安全规则 | 无 | 十八反、十九畏等规则 |
| 知识库规模 | 10 条演示样例 | 数百条真实病案 |

这些是后续阶段的升级方向。当前阶段的价值是：

1. 完整的 RAG 链路已跑通；
2. 工程分层已建立（知识库 / 检索 / 生成 / 页面）；
3. 后续只需要替换检索模块，不改 UI 和 LLM 模块。

---

# 7. 第二阶段的模块职责总结

| 模块 | 文件 | 职责 |
|---|---|---|
| 知识库 | `data/insomnia_formulas.json` | 存储 10 条演示方剂/证型知识 |
| 检索 | `src/retriever.py` | 加载知识库，关键词评分，返回 Top K |
| 生成 | `src/llm.py` | 格式化检索结果、注入 Prompt、调用 DeepSeek |
| 页面 | `app.py` | 接收输入、调用检索和生成、展示结果和依据 |

这个分层意味着：后续换成向量检索，只需改 `retriever.py`；换成别的模型，只需改 `llm.py`；换 UI 框架，只需改 `app.py`。每一层独立演进。

---

# 8. 当前版本的关键设计思想

## 8.1 检索结果注入而非直接拼接

检索结果不直接拼进页面文本，而是通过 `_format_retrieved_knowledge()` 格式化为结构化文本，再注入 LLM 消息中。这样 LLM 能准确理解每条检索知识的来源和内容。

## 8.2 匹配分数透明展示

页面上每条检索依据都显示 `match_score` 和 `matched_keywords`，用户能看到为什么系统推荐某条方剂。这对课堂演示和可信度很重要。

## 8.3 低置信度处理

当检索全部 0 分时，不隐藏问题，而是返回一条低置信度条目并标明"无直接命中"。同时 LLM 提示词要求在这种情况下如实说明匹配不足。

## 8.4 知识库与代码分离

知识以 JSON 文件存储，与 Python 代码分离。后续扩充知识库只需编辑 JSON 文件，不需要改任何代码。

---

# 9. 常见问题排查

## 9.1 检索结果为空

如果页面显示"无直接命中，返回通用参考"，说明用户输入的症状与知识库中的症状关键词没有匹配。

解决方法：

- 增加知识库条目；
- 在知识库的症状列表中增加更多同义词（例如加上"睡不着"在已有"失眠"之外）。

## 9.2 检索结果不准确

当前是关键词匹配，不能识别语义相似但用词不同的情况。例如用户说"睡不着"，知识库里写的是"失眠"，关键字匹配就不会命中。

这是关键词检索的已知局限，后续换向量检索后自然解决。

## 9.3 知识库加载失败

如果页面显示"知识库加载失败"，检查：

```
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\data\insomnia_formulas.json
```

是否存在、是否格式正确（可以用在线 JSON 校验器检查）。

## 9.4 DeepSeek 返回"未检索到高度匹配内容"

这是 LLM 按照提示词的要求，在检索匹配度低时如实说明。不是 bug，是预期行为。

---

# 10. 第二阶段核心知识点

理解当前项目，需要掌握：

1. `data/insomnia_formulas.json` 是本地知识库；
2. `src/retriever.py` 负责关键词匹配检索；
3. `src/llm.py` 的 `_format_retrieved_knowledge()` 把检索结果格式化为 LLM 可读文本；
4. `src/llm.py` 的 `chat_with_deepseek()` 接收 `retrieved_items` 参数注入上下文；
5. `app.py` 调用检索模块后再调 LLM 模块，构成完整 RAG 链路；
6. 页面展示了 RAG 执行过程和检索依据。

一句话总结当前项目：

> 这是一个用 Streamlit 做界面、用关键词检索本地中医失眠知识库、用 DeepSeek 基于检索知识生成结构化辅助分析的轻量 RAG Demo。

---

# 11. 下一阶段建议方向

## 11.1 向量检索升级

将 `src/retriever.py` 中的关键词匹配替换为：

- 文本 embedding（如 BGE-M3 / bge-small-zh）；
- 向量存储（FAISS / Chroma）；
- 相似度检索。

## 11.2 知识库扩充

增加方剂数据和真实脱敏病历数据，提升检索覆盖度。

## 11.3 动态 Few-shot

在检索结果中选取最相似的若干案例作为 Few-shot 示例，自适应控制示例数量。

## 11.4 安全规则校验

加入"十八反""十九畏"等中药配伍禁忌检查。

## 11.5 Agent 流程化

将分析流程拆为多个明确步骤（症状抽取 → 证型分析 → 知识检索 → 生成建议），页面展示完整执行过程。

---

# 12. 第二阶段结论

第二阶段已成功将系统从"纯 DeepSeek 调用 Demo"升级为"有本地知识库依据的关键词检索 RAG Demo"。

核心变化：

1. 系统回答不再来自模型自身记忆，而是来自本地检索知识；
2. 用户可以查看检索依据，验证系统推荐的来源；
3. 工程分层已建立，后续升级可以平滑进行。

项目当前状态可准确表述为：**关键词检索版中医失眠 RAG 原型系统**。
