# 第二阶段：关键词检索版轻量 RAG Demo 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把第一阶段最小调用 Demo 升级为有关键词检索和本地知识库的轻量 RAG Demo。

**Architecture:** 新增 data/ 知识库和检索模块，修改 llm.py 让 DeepSeek 基于检索结果生成回答，升级 app.py 展示检索依据。

**Tech Stack:** Python, Streamlit, python-dotenv, openai (DeepSeek via OpenAI-compatible SDK)

---

## Task 0: 备份第一阶段代码 + 创建第二阶段文件夹

**Files:**
- Rename: `tcm_sleep_agent` → `tcm_sleep_agent_stage1_basic_call`
- Create: `tcm_sleep_agent_stage2_keyword_rag` (全新工程)

- [ ] **Step 1: 备份第一阶段代码**

```powershell
Rename-Item "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent" "tcm_sleep_agent_stage1_basic_call"
```

- [ ] **Step 2: 创建第二阶段项目目录**

```powershell
New-Item -ItemType Directory -Force "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\src"
New-Item -ItemType Directory -Force "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\data"
```

- [ ] **Step 3: 复制依赖和环境变量文件**

```powershell
Copy-Item "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\requirements.txt" "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\"
Copy-Item "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\.env.example" "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\"
Copy-Item "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage1_basic_call\.env" "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\"
```

---

## Task 1: 创建本地知识库

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\data\insomnia_formulas.json`

- [ ] **Step 1: 创建 insomnia_formulas.json**

包含 10 条失眠相关方剂/证型样例，JSON 数组格式，每条包含 id, name, syndrome, symptoms, effects, ingredients, notes。

- [ ] **Step 2: 验证 JSON 可解析**

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag"
python -c "import json; data = json.load(open('data/insomnia_formulas.json', encoding='utf-8')); print(f'Loaded {len(data)} formulas')"
```

---

## Task 2: 创建关键词检索模块

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\src\retriever.py`
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\src\__init__.py`

- [ ] **Step 1: 创建 src/__init__.py**

```python
"""Core modules for the TCM Sleep Agent demo stage 2."""
```

- [ ] **Step 2: 创建 src/retriever.py**

实现 `load_knowledge_base()` 和 `retrieve_formulas(user_input, top_k)` 两个函数。
关键词评分规则：命中症状 +2，命中证型 +2，命中方剂名/功效 +1。
无命中时返回若干低置信度通用条目。

- [ ] **Step 3: 验证检索可正常导入运行**

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag"
python -c "from src.retriever import retrieve_formulas; r = retrieve_formulas('入睡困难，多梦易醒，心悸健忘'); print(len(r), 'results')"
```

---

## Task 3: 升级 LLM 生成模块

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\src\llm.py`

- [ ] **Step 1: 创建 src/llm.py**

保留第一阶段的 DeepSeek 客户端逻辑，但 `chat_with_deepseek` 改为接收 `(user_input, retrieved_items)` 两个参数。
提示词升级为要求模型基于检索知识分析、不要编造知识库以外的方剂、输出结构化内容。

- [ ] **Step 2: 验证导入**

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag"
python -c "from src.llm import chat_with_deepseek; print('import ok')"
```

---

## Task 4: 升级 Streamlit 页面

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag\app.py`

- [ ] **Step 1: 创建 app.py**

保持第一阶段的页面布局，增加：
1. RAG 执行过程展示
2. 检索依据展示
3. 检索回调流程（输入症状 → 检索 → 生成 → 展示）

- [ ] **Step 2: 语法检查**

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag"
python -m py_compile app.py src\llm.py src\retriever.py
```

---

## Task 5: 安装依赖并启动验证

- [ ] **Step 1: 创建虚拟环境并安装依赖**

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent_stage2_keyword_rag"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- [ ] **Step 2: 启动 Streamlit**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

- [ ] **Step 3: 手动测试**

输入: `入睡困难，多梦易醒，心悸健忘，食欲不佳，白天乏力`
预期: 页面展示检索到的方剂、结构化分析结果、检索依据、免责声明。

---

## Task 6: 写第二阶段进度日志

- [ ] **Step 1: 创建 工程日志/2026-07-03-第二阶段关键词RAG进度日志.md**

记录第二阶段实现内容、文件结构、已完成/未完成模块。
