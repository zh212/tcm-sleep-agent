# 当前项目第四阶段 — 动态 Few-shot + 企业级知识层 实现步骤与代码讲解

本文档是第三阶段文档的续篇，用于解释第四阶段的新增和改进内容。

**第三阶段**已完成：通义千问 Embedding v4 语义编码 → Chroma 语义检索 → DeepSeek 生成。

**第四阶段**在此基础上：

```text
语义检索 Top 5
→ 动态 Few-shot 示例构建（自适应数量 + MMR 多样性 + 末尾强化）
→ SQLite + Chroma 双存储知识管理
→ DeepSeek 参考医案推理链 + 检索知识双重上下文生成
```

---

# 1. 第四阶段新增和改动的文件

```text
tcm_sleep_agent/
├── data/
│   ├── insomnia_formulas.json   ← 扩充：10→20条，新增 category/source/example_case
│   ├── formulas.db              ← 新增：SQLite 结构化知识库
│   └── vector_store/            ← Chroma 持久化向量库（重建）
├── src/
│   └── services/
│       ├── embedding_service.py ← 未变
│       ├── knowledge_service.py ← 新增：SQLite 知识管理服务
│       ├── retrieval_service.py ← 升级：构建索引时同步 SQLite
│       ├── fewshot_service.py   ← 新增：动态 Few-shot 选例服务
│       └── generation_service.py← 升级：接收 Few-shot 示例注入 Prompt
├── app.py                       ← 升级：Few-shot 展示 + 双存储统计
└── requirements.txt             ← 未变（SQLite 是 Python 内置模块）
```

改动清单：

| 文件 | 操作 | 说明 |
|---|---|---|
| `data/insomnia_formulas.json` | 扩充 | 10→20条，新增 category/source/example_case 字段 |
| `src/services/knowledge_service.py` | 新增 | SQLite 管理：CRUD、同步、溯源 |
| `src/services/retrieval_service.py` | 升级 | build_index 同时同步 SQLite |
| `src/services/fewshot_service.py` | 新增 | 动态 Few-shot：自适应 + MMR + 末尾强化 |
| `src/services/generation_service.py` | 升级 | 接收 fewshot_examples 参数，注入 Prompt |
| `app.py` | 升级 | Few-shot 展示区块、双存储统计、V4 版本栏 |

---

# 2. 核心变化：为什么要有 Few-shot？

## RAG 和 Few-shot 的区别

**V3（纯 RAG）**给 DeepSeek 的内容：

```
检索到的知识：
归脾汤：心脾两虚，益气补血，健脾养心，组成：党参、白术...
酸枣仁汤：肝血不足，养血安神，清热除烦，组成：酸枣仁...
```

这些只是"方剂说明书"。模型需要自己推理"症状→证型→治法→方药"的完整流程。

**V4（RAG + Few-shot）**在此基础上增加：

```
【参考医案1】
患者失眠多梦半年余，伴心悸健忘，食少纳呆...证属心脾两虚。
治以益气补血，健脾养心。方选归脾汤加减：
参芪术草健脾益气，归枣龙眼肉养血安神...

【参考医案2】
患者失眠多梦，心悸健忘，气短神疲...证属心血亏虚。
治以补气养血，养心安神。方选柏子养心丸：
柏子仁养心安神为君...
```

模型看到的是**完整的推理链**——症状→证型→治法→方药→思路。它能照这个格式输出，质量明显更高。

---

# 3. 新增文件详细讲解

## 3.1 `data/insomnia_formulas.json`（扩充后）

### 新增字段

每条知识新增三个字段：

```json
{
  "id": "guipi-tang",
  "name": "归脾汤",
  "syndrome": "心脾两虚",
  "symptoms": ["失眠", "多梦", "心悸", "健忘", "食少", "乏力"],
  "effects": "益气补血，健脾养心",
  "ingredients": ["党参", "白术", "黄芪", "当归", "酸枣仁", "龙眼肉", "远志", "木香", "甘草"],
  "notes": "外感发热期间慎用。",
  "category": "补益剂",
  "source": "《济生方》",
  "example_case": "患者失眠多梦半年余...证属心脾两虚...方选归脾汤加减..."
}
```

| 字段 | 用途 | Few-shot 使用 |
|---|---|---|
| `category` | 方剂分类（安神剂/补益剂/祛痰剂） | ❌ 仅展示 |
| `source` | 文献出处 | ❌ 仅展示和溯源 |
| `example_case` | 完整医案推理链 | ✅ **Few-shot 的核心内容** |

### 扩充后的方剂覆盖

20 条方剂覆盖 17 个证型，涵盖失眠临床常见证型：

- 安神剂：酸枣仁汤、天王补心丹、朱砂安神丸、柏子养心丸、黄连阿胶汤、交泰丸
- 补益剂：归脾汤、甘麦大枣汤、安神定志丸、生脉散、肾气丸、二仙汤
- 和解剂：柴胡加龙骨牡蛎汤、加味逍遥散
- 祛痰剂：温胆汤
- 清热剂：连朴饮、导赤散
- 祛湿剂：苓桂术甘汤
- 治风剂：镇肝熄风汤
- 理血剂：安神温经汤

---

## 3.2 `src/services/knowledge_service.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\src\services\knowledge_service.py
```

作用：SQLite 结构化知识管理。解决"JSON 太简陋，不能增删改查，不能按证型/分类查询"的问题。

### 为什么需要 SQLite？

| 操作 | JSON 方式 | SQLite 方式 |
|---|---|---|
| 读取全部 20 条 | `json.load()` | `SELECT * FROM formulas` |
| 查某一条 | 遍历全数组 | `SELECT WHERE id=?` |
| 按证型筛选 | 手写循环 | `SELECT WHERE syndrome LIKE '%心脾%'` |
| 新增一条 | 手动编辑 JSON 文件 | `INSERT INTO formulas` |
| 统计数据 | 遍历计数 | `SELECT COUNT(*)` |
| 修改一条 | 手动编辑 + 全文比对 | `UPDATE WHERE id=?` |
| 数据溯源 | 无 | source 字段可查 |

JSON 在 10 条时够用，20 条时勉强，100 条时翻车。SQLite 从 10 条到 10000 条都一样快。

### 核心函数

```python
def init_db():
    """创建 formulas 表（如果不存在）。"""

def sync_from_json() -> int:
    """从 JSON 同步到 SQLite，INSERT OR REPLACE 策略。
    每次调用都是幂等的——重复调用不会产生重复数据。"""

def list_all() -> list[dict]:
    """返回所有方剂，用于 Chroma 索引构建。"""

def get_by_id(formula_id: str) -> dict | None:
    """按 ID 查询单条，用于 Few-shot 获取完整医案。"""
```

### `sync_from_json()` 的幂等设计

```python
conn.execute("""
    INSERT OR REPLACE INTO formulas
    (id, name, syndrome, symptoms, effects, ingredients, notes, category, source, example_case)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (...))
```

`INSERT OR REPLACE` 保证：
- ID 不存在 → 插入新行
- ID 已存在 → 用新值覆盖旧值
- 调用 100 次不会产生重复数据

---

## 3.3 `src/services/fewshot_service.py`

路径：

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\src\services\fewshot_service.py
```

作用：从检索结果中自适应选取多样化的 Few-shot 示例。

### 完整代码

```python
"""Dynamic Few-shot example selection with MMR diversity control."""

from src.services.knowledge_service import get_by_id


def _mmr_select(items, n, lambda_param=0.7):
    """Maximum Marginal Relevance selection."""

def _syndrome_overlap(a, b):
    """Compute syndrome overlap (character Jaccard similarity)."""

def build_fewshot_examples(retrieved):
    """Adaptive count + MMR + sort by similarity ascending."""

def format_fewshot_prompt(examples):
    """Format examples into prompt string."""
```

### 3.3.1 自适应数量策略

```python
top_score = scored[0]["similarity_score"]
if top_score >= 0.75:
    n = min(3, len(scored))   # 高度匹配 → 3条
elif top_score >= 0.55:
    n = min(2, len(scored))   # 中度匹配 → 2条
elif top_score >= 0.35:
    n = 1                     # 低度匹配 → 1条
else:
    return []                 # 极低匹配 → 不用Few-shot
```

自适应逻辑：匹配度高时多放示例（模型可以学得更细），匹配度低时少放或不放（强行塞不相关的示例反而误导模型）。

### 3.3.2 MMR 多样性控制

```python
def _mmr_select(items, n, lambda_param=0.7):
    selected = [items[0]]  # 最相关的一定要选
    remaining = items[1:]

    while len(selected) < n and remaining:
        best_idx = 0
        best_score = -1.0
        for idx, candidate in enumerate(remaining):
            relevance = candidate["similarity_score"]
            max_dup = max(
                _syndrome_overlap(selected_item, candidate)
                for selected_item in selected
            )
            mmr = lambda_param * relevance - (1 - lambda_param) * max_dup
            if mmr > best_score:
                best_score = mmr
                best_idx = idx
        selected.append(remaining.pop(best_idx))
    return selected
```

MMR 公式：

```text
MMR = λ × 相关性 - (1 - λ) × 最大重叠

λ = 0.7（偏重相关性）
```

这意味着：从 5 条检索结果中选 2 条时，优先选"与查询相关 + 与已选示例证型不重复"的组合。比如检索结果是"归脾汤(心脾两虚)、柏子养心丸(心血亏虚)、天王补心丹(心肾阴虚)"，MMR 会选归脾汤 + 柏子养心丸（证型差异大），而不是归脾汤 + 天王补心丹。

### 3.3.3 证型重叠计算

```python
def _syndrome_overlap(a, b):
    syn_a = a.get("syndrome", "")
    syn_b = b.get("syndrome", "")
    chars_a = set(syn_a.replace("，", "").replace(",", "").replace("、", ""))
    chars_b = set(syn_b.replace("，", "").replace(",", "").replace("、", ""))
    intersection = chars_a & chars_b
    union = chars_a | chars_b
    return len(intersection) / len(union)  # Jaccard 相似度
```

用字符集 Jaccard 相似度衡量两个证型的重叠程度：

- "心脾两虚" vs "心血亏虚" → 两个字符"心""虚"相同 → 重叠 ≈ 0.29（低，多样性好）
- "心脾两虚" vs "心肾阴虚" → 三个字符"心""虚"相同 → 重叠 ≈ 0.43（中等）
- "心脾两虚" vs "心脾两虚" → 完全重叠 → 重叠 = 1.0（高，重复了）

### 3.3.4 末尾强化

```python
diverse.sort(key=lambda x: x["similarity_score"])  # 升序：最相似的放最后
```

认知科学中叫做 **Recency Effect**——人（和大模型）对刚看到的内容记忆最深。把相似度最高的示例放在 Prompt 末尾，模型生成时更倾向于参考它。

### 3.3.5 获取完整医案

```python
for item in diverse:
    full = get_by_id(item.get("id", ""))
    if full and full.get("example_case"):
        item["example_case"] = full["example_case"]
```

检索结果中只有向量相似度和元数据，没有完整 `example_case`。这里从 SQLite 中按 ID 查询完整医案，补全到 Few-shot 示例中。

---

## 3.4 升级后的 `retrieval_service.py`

改动点只有 `build_index()`：

```python
def build_index(force_rebuild=False):
    # 1. 先同步 SQLite（新增）
    sqlite_count = sync_from_json()

    # 2. 从 SQLite 读数据（而非 JSON）
    formulas = list_all()

    # 3. 向量化 + 写入 Chroma（同 V3）
    ...
```

构建索引时自动同步 SQLite，保证两个存储层的数据一致。

---

## 3.5 升级后的 `generation_service.py`

### 新增参数

```python
def generate_analysis(
    user_input: str,
    retrieved_items: list[dict] | None = None,
    fewshot_examples: list[dict] | None = None,   # 新增
) -> str:
```

### Prompt 组装逻辑

```python
user_content = f"当前患者主诉失眠相关症状如下：\n{cleaned_input}\n\n"

if fewshot_text:
    user_content += f"{fewshot_text}\n\n"     # ← Few-shot 医案示例

user_content += (
    "以下是从中医失眠知识库中语义检索到的相关方剂知识：\n"
    f"{knowledge_text}\n\n"                   # ← RAG 检索知识
    "请基于上述检索内容和参考医案，进行辨证论治分析。"
)
```

Prompt 结构：

```text
1. 当前患者症状
2. ⭐ 参考医案示例（动态 Few-shot）
3. 检索到的方剂知识（RAG）
4. 分析指令
```

### 升级后的系统提示词

```python
SYSTEM_PROMPT = """你是一个部署在中医失眠智能辅助系统中的
RAG + 动态 Few-shot 处方分析引擎。

1. 参考「相似医案示例」的分析思路和格式，为当前患者进行辨证论治分析。
2. 仅基于检索知识和参考医案提供的内容进行辅助分析...
...
"""
```

相比 V3，增加了"参考相似医案示例的分析思路和格式"的指令。

---

# 4. 升级后的 `app.py`

### 4.1 启动时自动初始化知识库

```python
@st.cache_resource
def init_knowledge_base():
    sqlite_count = sync_from_json()
    chroma_count = build_index(force_rebuild=True)
    return sqlite_count, chroma_count
```

`@st.cache_resource` 保证只执行一次（除非点「重建索引」清除缓存）。

### 4.2 Sidebar 统计数据

```python
sqlite_n, chroma_n = init_knowledge_base()
st.metric("知识库条目", sqlite_n)    # 20
st.metric("向量索引", chroma_n)      # 20
st.caption("SQLite + Chroma 双存储架构")
```

### 4.3 新增：动态 Few-shot 展示

```python
fewshot = build_fewshot_examples(retrieved)  # 第一步：选出Few-shot

st.subheader("📖 动态 Few-shot 参考医案")
st.caption(f"自适应数量：{len(fewshot)} 条 | MMR 多样性控制 | 末尾强化")

for i, ex in enumerate(fewshot, 1):
    with st.expander(f"参考医案 {i} ｜ {ex['name']}（{ex['syndrome']}）｜ 相似度 {sim:.0%}"):
        st.markdown(ex.get('example_case', ''))
```

### 4.4 检索结果标注

```python
# 哪些检索结果被选为了 Few-shot？标注出来
f"已选为Few-shot示例" if any(f.get('id') == item.get('id') for f in fewshot) else ''
```

### 4.5 生成调用

```python
result = generate_analysis(user_input, retrieved, fewshot)
```

---

# 5. 第四阶段运行流程总览

```text
1. 用户打开 http://127.0.0.1:8501
   ↓
2. 首次启动：sync_from_json() → build_index(force_rebuild=True)
   - SQLite: 20条公式数据
   - Chroma: 20条向量索引
   ↓
3. 用户输入症状，点击「开始分析」
   ↓
4. search(query, top_k=5) → 语义检索 5 条相关方剂
   ↓
5. build_fewshot_examples(retrieved) → 动态 Few-shot 选例
   - 自适应数量（top_sim 0.66 → n=2）
   - MMR 多样性（归脾汤 + 柏子养心丸，不同证型）
   - 末尾强化（相似度升序排列）
   - SQLite 补全完整医案
   ↓
6. generate_analysis(user_input, retrieved, fewshot)
   - 拼装 Prompt：症状 + Few-shot医案 + 检索知识
   - 请求 DeepSeek
   ↓
7. 页面展示：
   - 执行管道
   - 动态 Few-shot 参考医案
   - 语义检索依据（标注哪些被选为Few-shot）
   - AI处方辅助分析
```

---

# 6. 核心设计思想

## 6.1 JSON → SQLite + Chroma 双存储

- SQLite 负责"管理"（增删改查、溯源、统计）
- Chroma 负责"检索"（语义相似度）
- 各司其职，互不越界

## 6.2 Few-shot 不是固定模板

三个"动态"：

1. **动态数量**：匹配度高多放，低少放
2. **动态组合**：MMR 保证证型不重复
3. **动态顺序**：最相似的放最后

## 6.3 分层演进，渐进增强

```text
V1: app → llm → DeepSeek
V2: app → retriever → llm → DeepSeek
V3: app → retrieval_service → embedding_service → Chroma
    app → generation_service → DeepSeek
V4: app → retrieval_service → fewshot_service → knowledge_service(SQLite)
    app → generation_service(fewshot) → DeepSeek
```

每一层都在已有基础上叠加，从不推翻重来。

---

# 7. 常见问题排查

## 7.1 页面打开后 sidebar 显示"知识库初始化中"

这是 `init_knowledge_base()` 正在执行（首次启动可能需要 10-20 秒做 embedding 调用），等一会儿就会显示数据。

## 7.2 Few-shot 条数不对

检查检索结果的 `similarity_score`：

- ≥ 0.75 应显示 3 条
- 0.55-0.75 应显示 2 条
- 0.35-0.55 应显示 1 条
- < 0.35 应不显示

如果实际看到的不一致，点「重建索引」试试。

## 7.3 点「开始分析」没有反应

检查：
- `.env` 里 DeepSeek API Key 还有余额吗
- 控制台有没有红色错误信息

---

# 8. 第四阶段核心知识点

1. RAG 提供"方剂说明书"，Few-shot 提供"推理链示例"；
2. MMR 从检索结果中选取既相关又多样的子集；
3. 末尾强化让最相似的示例放在 Prompt 最后；
4. SQLite + Chroma 双存储：管理用 SQLite，检索用 Chroma；
5. 自适应数量：匹配度高多放示例，低少放或不放。

一句话总结：

> 这是一个用 SQLite 管理知识、Chroma 做语义检索、通义千问 Embedding v4 做向量编码、MMR 自适应动态 Few-shot 选取医案示例、DeepSeek 基于参考医案和检索知识生成结构化处方分析的中医失眠智能辅助系统原型。
