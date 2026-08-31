# 🎯 AI 模拟面试平台

> 基于简历的智能技术面试训练系统 —— 上传 PDF 简历，AI 面试官自动出题、逐题追问、多维评分并生成评价报告。

---

## 一、项目实现内容

### 1. 核心功能

| 功能模块 | 实现说明 | 状态 |
|----------|----------|------|
| 📄 简历解析 | 上传 PDF 简历，自动提取技能栈（73 个技术关键词）、学历、项目经历段落 | ✅ 已完成 |
| 💬 AI 面试对话 | 基于简历 + RAG 知识库自动生成基础题与项目深挖题，支持追问、重复检测、抱怨检测 | ✅ 已完成 |
| 📚 知识库检索 | 57 条技术面试知识点，DashScope 向量化后存入 FAISS 索引，语义检索出题 | ✅ 已完成 |
| 📊 智能评分 | 五维度加权评分（基础/深度/逻辑/完整性/匹配度）+ LLM 文字评价报告 + 雷达图可视化 | ✅ 已完成 |
| 🎙️ 语音识别 | DashScope ASR 接口，支持音频转文字（API 层已完成） | ✅ 已完成 |
| 📱 前端界面 | 单页应用：上传 → 面试对话 → 评分报告三阶段流程，无框架依赖 | ✅ 已完成 |

### 2. 系统架构

```
index.html（前端 SPA）
      │ HTTP REST
      ▼
main.py（FastAPI 服务，端口 8000）
      │
      ├── resume_parser.py   简历解析（PDF 提取 + 规则匹配）
      ├── interview.py       面试状态机（问候→基础题→项目题→评分）
      ├── rag_engine.py      FAISS 语义检索知识库
      ├── nlp_scoring.py     五维度评分引擎
      ├── llm.py             Qwen 对话调用（多 Key 轮询）
      ├── embeddings.py      文本向量化
      └── speech.py          ASR 语音识别
              │
              ▼
       阿里云 DashScope（Qwen 对话 / text-embedding-v4 / paraformer ASR）
```

### 3. 技术栈

- **后端**：Python 3.10+ · FastAPI · uvicorn
- **AI 能力**：阿里云 DashScope 通义千问 Qwen-plus（对话/评分）、text-embedding-v4（向量）、paraformer-realtime-v2（语音识别）
- **知识库**：FAISS 向量检索 + NumPy
- **前端**：原生 HTML/CSS/JavaScript + Chart.js（雷达图）

### 4. 文件结构

```
ai_interview/
├── main.py                     # 后端入口（FastAPI 应用）
├── index.html                  # 前端单页应用
├── cs_knowledge.json           # 技术面试知识题库（57 条）
├── requirements.txt            # Python 依赖清单
├── .env                        # 环境变量配置（API Key，不入库）
├── .env.example                # 配置模板
├── backend/
│   ├── config.py               # 配置加载
│   ├── interview.py            # 面试流程控制（核心）
│   ├── resume_parser.py        # 简历解析
│   ├── rag_engine.py           # FAISS 知识库检索
│   ├── nlp_scoring.py          # 评分引擎
│   ├── llm.py / embeddings.py  # 大模型与向量调用
│   ├── speech.py               # 语音识别
│   └── build_knowledge_base.py # 知识库构建工具
├── data/                       # FAISS 索引（已预构建）
└── README.md                   # 本说明文档
```

---

## 二、控制台启动方法（Windows）

### 1. 安装依赖

打开 **命令提示符（cmd）或 PowerShell**，进入项目目录：

```powershell
cd D:\Desktop\ai_interview
```

创建虚拟环境（如已有 `.venv` 可跳过）：

```powershell
python -m venv .venv
```

安装依赖：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置 API Key

项目根目录已有 `.env` 文件（内含 API Key），无需额外配置即可运行。
若需更换，编辑 `.env` 中的 `DASHSCOPE_API_KEY` 即可。

### 3. 构建知识库（可选）

`data/` 目录已包含预构建的 FAISS 索引，一般无需重建。
如需重建，执行：

```powershell
.venv\Scripts\python.exe -m backend.build_knowledge_base
```

### 4. 启动服务

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

看到以下输出即启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 5. 打开网页

浏览器访问：**http://127.0.0.1:8000**

进入系统后：点击上传 PDF 简历 → 点击「🚀 开始面试」→ 在对话框回答面试官提问 → 面试结束自动生成评分报告。

其他入口：
- 接口文档（Swagger）：http://127.0.0.1:8000/docs
- 模型配置查询：http://127.0.0.1:8000/models

---

## 三、GitHub 仓库地址

**https://github.com/Xiao-Gao-5/ai_interview**

（对应命令行方式：`git remote add origin https://github.com/Xiao-Gao-5/ai_interview.git`）

---

## 四、API Key 配置

本项目使用阿里云 DashScope（百炼）平台的大模型 API。

- **API Key**：见项目根目录 `.env` 文件中的 `DASHSCOPE_API_KEY`（出于安全考虑不在此公开，请自行前往[阿里云百炼控制台](https://bailian.console.aliyun.com/)申请）
- **配置位置**：项目根目录 `.env` 文件
- **Key 类型**：DashScope API Key（阿里云百炼控制台获取）

> ⚠️ 安全提醒：`.env` 文件已被 `.gitignore` 排除、不会上传到 GitHub。如仓库设置为公开，请前往阿里云百炼控制台重置该 Key。

### 各模型配置项

| 配置项 | 值 | 用途 |
|--------|-----|------|
| `DASHSCOPE_API_KEY` | 见上 | 鉴权 |
| `QWEN_MODEL` | qwen-plus | 面试官对话 |
| `QWEN_EVAL_MODEL` | qwen-plus | 回答评分 |
| `DASHSCOPE_EMBEDDING_MODEL` | text-embedding-v4 | 简历/题目向量化 |
| `DASHSCOPE_ASR_MODEL` | paraformer-realtime-v2 | 语音识别 |

---

## 五、主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 返回前端页面 |
| GET | `/models` | 查询当前模型配置 |
| POST | `/upload-resume` | 上传 PDF 简历并解析 |
| POST | `/start-interview` | 创建会话并开始面试 |
| POST | `/chat` | 面试对话（一问一答） |
| POST | `/end-interview` | 主动结束并生成评分 |
| POST | `/speech-to-text` | 上传音频识别为文字 |

---

## 六、面试流程说明

```
上传简历 → AI 解析（技能/学历/项目）
        → 问候与画像 → 基础问答（3 题，可追问）
        → 项目深挖（每项目 3 题，多项目轮换，可追问）
        → 五维度评分（雷达图 + 文字报告）
```

- 追问策略：单题评分 ≥ 6 分时触发一次深挖追问
- 去重机制：已问题目会传给模型，避免重复出题
- 结束方式：完成全部题目自动评分，或通过接口主动结束
