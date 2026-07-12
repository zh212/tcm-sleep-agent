# 中医失眠处方智能辅助系统

省级大创项目原型。基于 RAG + 动态 Few-shot 的中医失眠处方智能辅助生成系统。

## 技术架构

```text
症状输入 → 通义千问 Embedding v4 语义编码 → Chroma 向量检索
→ 动态 Few-shot（MMR 多样性 + 自适应数量 + 末尾强化）
→ DeepSeek 生成结构化处方分析
```

- **知识管理**：SQLite + Chroma 双存储
- **语义编码**：通义千问 text-embedding-v4（DashScope API）
- **向量检索**：Chroma 余弦相似度
- **动态 Few-shot**：自适应示例数量 + MMR 多样性控制
- **生成模型**：DeepSeek Chat API

## 运行方式

### 1. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入两个 API Key：

```env
# DeepSeek（生成模型） — 去 https://platform.deepseek.com 获取
DEEPSEEK_API_KEY=你的DeepSeek_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 通义千问 Embedding（向量化模型） — 去 https://dashscope.aliyun.com 获取
DASHSCOPE_API_KEY=你的DashScope_API_Key
```

> 阿里云百炼新用户有 100 万 tokens 免费额度，DeepSeek 新用户有 500 万 tokens 免费额度。

### 3. 启动后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

也可以直接双击 `启动后端.bat`。API 地址为 `http://127.0.0.1:8000`，接口文档为 `http://127.0.0.1:8000/docs`。

首次启动会自动构建知识索引（同步 SQLite + 向量化入库），约需 10-20 秒。

### 4. 启动前端

在项目根目录的 `frontend` 目录中执行：

```powershell
npm install
npm run dev
```

也可以直接双击 `frontend\启动前端.bat`。浏览器访问 `http://127.0.0.1:3000`。

前端默认请求 `http://localhost:8000`；如需修改，可在前端环境文件中设置：

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## 已实现

- Next.js 响应式前端与 FastAPI 后端
- 20 条中医失眠方剂/医案知识库
- SQLite + Chroma 双存储架构
- 通义千问 Embedding v4 语义向量编码
- 语义相似度检索（三档分类）
- 动态 Few-shot 示例构建（自适应 + MMR + 末尾强化）
- DeepSeek 基于检索 + 医案的结构化处方分析
- 检索依据 + Few-shot 医案溯源展示
- 医疗免责声明

## 项目结构

```text
tcm_sleep_agent/
├── backend/main.py                 ← FastAPI 后端入口
├── config/settings.py              ← 集中配置
├── data/insomnia_formulas.json     ← 知识库源数据（20条）
├── src/services/
│   ├── embedding_service.py        ← 通义千问 Embedding API
│   ├── retrieval_service.py        ← Chroma 语义检索
│   ├── generation_service.py       ← DeepSeek RAG 生成
│   ├── fewshot_service.py          ← 动态 Few-shot 选例
│   └── knowledge_service.py        ← SQLite 知识管理
├── docs/                           ← 四阶段实现文档
├── requirements.txt
├── 启动后端.bat
└── .env.example
```

## 免责声明

本系统是省级大创项目原型，仅供技术演示和学术研究，不构成真实医疗诊断或处方建议，不能替代执业医师诊疗。
