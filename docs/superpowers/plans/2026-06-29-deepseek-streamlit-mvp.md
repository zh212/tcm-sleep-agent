# DeepSeek Streamlit MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable MVP: a Streamlit page where the user enters insomnia symptoms and receives a DeepSeek-generated response.

**Architecture:** Keep this first version intentionally small. `app.py` owns the Streamlit UI; `src/llm.py` owns DeepSeek API configuration and a single `chat_with_deepseek()` function. No RAG, vector database, Agent orchestration, or medical knowledge base is included in this first step.

**Tech Stack:** Python, Streamlit, python-dotenv, OpenAI-compatible Python SDK, DeepSeek online API.

---

## File Structure

Create this project under:

```text
C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent
```

Files:

```text
tcm_sleep_agent/
├── app.py                    # Streamlit UI: input box, button, result display
├── requirements.txt          # Python dependencies for first MVP
├── .env.example              # Safe example env file, no real API key
└── src/
    ├── __init__.py           # Makes src importable
    └── llm.py                # DeepSeek API client wrapper
```

Responsibilities:

- `app.py`: page layout, symptom input, calls `chat_with_deepseek()`, shows result/errors.
- `src/llm.py`: reads environment variables, creates OpenAI-compatible client, calls DeepSeek model.
- `.env.example`: documents required environment variables without exposing secrets.
- `requirements.txt`: pins minimal dependencies needed to run the MVP.

---

### Task 1: Create project skeleton

**Files:**
- Create directory: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent`
- Create directory: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src`
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src\__init__.py`

- [ ] **Step 1: Create directories**

Run in PowerShell:

```powershell
New-Item -ItemType Directory -Force "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src"
```

Expected: directory exists without error.

- [ ] **Step 2: Create package marker**

Create `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src\__init__.py` with this content:

```python
"""Core modules for the TCM Sleep Agent demo."""
```

- [ ] **Step 3: Verify skeleton**

Run:

```powershell
Get-ChildItem "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
Get-ChildItem "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src"
```

Expected: `src` exists and contains `__init__.py`.

---

### Task 2: Add dependency and environment files

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\requirements.txt`
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\.env.example`

- [ ] **Step 1: Create `requirements.txt`**

Create `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\requirements.txt` with:

```text
streamlit>=1.36.0
python-dotenv>=1.0.1
openai>=1.40.0
```

- [ ] **Step 2: Create `.env.example`**

Create `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\.env.example` with:

```env
# Copy this file to .env and replace the placeholder with your real key.
# Do not commit or share your real API key.
DEEPSEEK_API_KEY=replace_with_your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

- [ ] **Step 3: Create local `.env` manually**

Copy `.env.example` to `.env` and put the real DeepSeek API key in `.env` only:

```powershell
Copy-Item "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\.env.example" "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\.env"
notepad "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\.env"
```

Expected `.env` format:

```env
DEEPSEEK_API_KEY=sk-your-real-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Important: do not paste the real API key into chat.

---

### Task 3: Implement DeepSeek client wrapper

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src\llm.py`

- [ ] **Step 1: Create `src/llm.py`**

Create `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\src\llm.py` with:

```python
"""DeepSeek API wrapper for the first Streamlit MVP."""

import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


SYSTEM_PROMPT = """你是一个中医失眠处方辅助 Demo 的说明型助手。
当前系统仍处于课程演示阶段，不能替代医生诊断，也不能给出真实处方。
请用中文回答，语气清晰、谨慎、适合课堂项目演示。
"""


def get_deepseek_client() -> OpenAI:
    """Create an OpenAI-compatible client configured for DeepSeek."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    if not api_key or api_key == "replace_with_your_deepseek_api_key":
        raise RuntimeError("请先在 .env 文件中配置 DEEPSEEK_API_KEY。")

    return OpenAI(api_key=api_key, base_url=base_url)


def chat_with_deepseek(user_input: str) -> str:
    """Send a symptom description to DeepSeek and return the assistant text."""
    cleaned_input = user_input.strip()
    if not cleaned_input:
        raise ValueError("请输入失眠相关症状后再开始分析。")

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    client = get_deepseek_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "用户输入的失眠相关症状如下：\n"
                    f"{cleaned_input}\n\n"
                    "请先做一个简短的中医辅助分析示例，输出包括：\n"
                    "1. 症状摘要\n"
                    "2. 可能的中医分析方向\n"
                    "3. 后续系统接入 RAG 知识库后可以如何进一步分析\n"
                    "4. 医疗免责声明\n"
                    "注意：不要给出真实处方剂量，不要声称可以替代医生。"
                ),
            },
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content or "模型未返回内容。"
```

- [ ] **Step 2: Verify imports manually**

Run from project directory:

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
python -c "from src.llm import chat_with_deepseek; print('import ok')"
```

Expected:

```text
import ok
```

If it fails with missing dependency, run Task 5 dependency installation before retrying.

---

### Task 4: Implement Streamlit UI

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\app.py`

- [ ] **Step 1: Create `app.py`**

Create `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\app.py` with:

```python
"""Streamlit UI for the first TCM Sleep Agent MVP."""

import streamlit as st

from src.llm import chat_with_deepseek


st.set_page_config(
    page_title="中医失眠处方辅助 Agent Demo",
    page_icon="🌙",
    layout="wide",
)

st.title("🌙 中医失眠处方辅助 Agent Demo")

st.warning(
    "本系统仅用于课程学习和技术演示，不构成真实医疗诊断或处方建议。"
)

st.markdown(
    """
    当前版本是第一步最小 Demo：  
    **页面输入症状 → 调用 DeepSeek 在线模型 → 返回辅助分析文本**。  
    后续版本会继续加入 RAG 知识库检索和 Agent 流程。
    """
)

example = "入睡困难，多梦易醒，心悸健忘，食欲不佳，白天乏力。"

user_input = st.text_area(
    "请输入失眠相关症状",
    value=example,
    height=160,
    placeholder="例如：入睡困难，多梦易醒，心悸健忘，食少乏力……",
)

if st.button("开始分析", type="primary"):
    with st.spinner("正在调用 DeepSeek 生成分析结果……"):
        try:
            result = chat_with_deepseek(user_input)
        except Exception as exc:
            st.error(f"调用失败：{exc}")
        else:
            st.subheader("分析结果")
            st.markdown(result)

st.divider()

st.subheader("当前版本说明")
st.markdown(
    """
    - ✅ 已完成：Streamlit 页面输入与 DeepSeek API 调用。
    - ⏳ 下一步：加入本地中医方剂知识库。
    - ⏳ 再下一步：加入 RAG 检索和证据展示。
    - ⏳ 后续：包装为固定流程 Agent。
    """
)
```

- [ ] **Step 2: Verify Python syntax**

Run:

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
python -m py_compile app.py src\llm.py
```

Expected: no output and exit code 0.

---

### Task 5: Install dependencies and run the app

**Files:**
- Uses: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\requirements.txt`
- Uses: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\app.py`

- [ ] **Step 1: Create virtual environment**

Run:

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
python -m venv .venv
```

Expected: `.venv` directory is created.

- [ ] **Step 2: Install dependencies**

Run:

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: packages install successfully.

- [ ] **Step 3: Run syntax check using venv Python**

Run:

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
.\.venv\Scripts\python.exe -m py_compile app.py src\llm.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Start Streamlit**

Run:

```powershell
Set-Location "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Expected: Streamlit starts and prints a local URL similar to:

```text
Local URL: http://localhost:8501
```

- [ ] **Step 5: Manual browser test**

Open the local URL and test:

```text
入睡困难，多梦易醒，心悸健忘，食欲不佳，白天乏力。
```

Expected: page displays a Chinese analysis response from DeepSeek and the medical disclaimer remains visible.

---

### Task 6: Record first-step completion notes

**Files:**
- Create: `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\README.md`

- [ ] **Step 1: Create README**

Create `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\README.md` with:

```markdown
# 中医失眠处方辅助 Agent Demo

这是课程项目的第一步最小 Demo。

## 当前已实现

- Streamlit 交互页面
- 用户输入失眠相关症状
- 调用 DeepSeek 在线 API
- 显示模型返回的中医辅助分析文本
- 页面显示医疗免责声明

## 当前未实现

- RAG 知识库检索
- 方剂知识库
- 向量数据库
- Agent 多步骤流程
- 安全规则检查

## 运行方式

1. 安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. 配置 API Key：

复制 `.env.example` 为 `.env`，填入 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=你的真实key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

3. 启动页面：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 免责声明

本系统仅用于课程学习和技术演示，不构成真实医疗诊断或处方建议。
```

- [ ] **Step 2: Verify README exists**

Run:

```powershell
Get-ChildItem "C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent\README.md"
```

Expected: file exists.

---

## Self-Review

Spec coverage:

- Creates project under `C:\Users\LX\Desktop\Proj_2\tcm_sleep_agent`.
- Adds `app.py`, `src/llm.py`, `requirements.txt`, `.env.example`, and README.
- Implements only the first-step MVP: Streamlit input and DeepSeek API output.
- Excludes RAG, Agent orchestration, vector database, and medical knowledge base as requested.

Placeholder scan:

- The only placeholder is the intentional `.env.example` key value `replace_with_your_deepseek_api_key`; it is safe and required because real secrets must not be stored in the plan.
- No unspecified implementation steps remain.

Type and name consistency:

- `app.py` imports `chat_with_deepseek` from `src.llm`.
- `src/llm.py` defines `chat_with_deepseek(user_input: str) -> str`.
- Environment variable names are consistent across `.env.example`, `src/llm.py`, and README.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-deepseek-streamlit-mvp.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
