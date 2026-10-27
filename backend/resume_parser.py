"""简历解析模块：PDF 文本提取 + 技能/学历/项目经历的结构化抽取。

设计原则（分级处理策略）：
- 封闭词表（技能名、学历关键词）用正则精确匹配——零成本、毫秒级、可解释；
- 开放语义（后续增强方向）才考虑调用大模型兜底。
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 词表外置：技能关键词与别名从 JSON 读取（数据驱动，加技能不用改代码）
# ---------------------------------------------------------------------------
_SKILL_FILE = Path(__file__).resolve().parent / "skill_keywords.json"
with _SKILL_FILE.open("r", encoding="utf-8") as _f:
    _SKILL_CONF = json.load(_f)

SKILLS: list[str] = _SKILL_CONF["skills"]
# 别名表：简历里的各种写法 → 标准名（匹配后统一归一，避免 js/golang 重复计）
SKILL_ALIASES: dict[str, str] = _SKILL_CONF.get("aliases", {})

# 学历优先级：简历多处提及学历时取最高档（如"预计 2027 年本科毕业"不影响硕士在读判定）
EDU_PRIORITY = ["博士", "phd", "硕士", "master", "研究生", "本科", "bachelor", "大专", "专科"]

# 项目/经历切分的标题词（中英文都支持）
_PROJECT_SPLIT_PATTERN = (
    r"项目经历|项目经验|实习经历|实践经历|工作经历"
    r"|Project Experience|Projects|Internship|Work Experience"
)


def extract_text_from_pdf(pdf_path: str) -> str:
    """提取 PDF 全文；失败时记录日志并返回空串（由 parse_resume 统一给出 warning）。"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as exc:
        # 用 logging 替代 print：日志可分级、可收集，且不会混入 stdout 影响服务
        logger.warning("PDF 解析错误 (%s): %s", pdf_path, exc)
        return ""
    return text


def _match_skills(text_l: str) -> list[str]:
    """词边界匹配技能词表，别名归一后去重返回。

    - ASCII 词用 \\b 词边界：保证 "go" 只匹配独立的 go，不误报 django/algorithm/google；
    - c++/c# 这类含特殊字符的词，\\b 在 +/# 附近行为特殊，改用前后 lookaround；
    - 中文词（阿里云/腾讯云）无词边界概念，退回子串匹配（无误报风险）。
    """
    found: set[str] = set()
    # 待检索项 = 标准词本身 + 所有映射到它的别名
    candidates: list[tuple[str, str]] = [(s, s) for s in SKILLS]  # (检索词, 标准名)
    candidates += [(alias, canonical) for alias, canonical in SKILL_ALIASES.items()]

    for term, canonical in candidates:
        term_l = term.lower()
        if term.isascii():
            # c++ / c# 等含特殊字符的词用 lookaround；纯字母数字词用 \b
            if any(ch in term_l for ch in "+#"):
                pattern = r"(?<![a-z0-9])" + re.escape(term_l) + r"(?![a-z0-9])"
            else:
                pattern = r"\b" + re.escape(term_l) + r"\b"
            if re.search(pattern, text_l):
                found.add(canonical)
        else:
            # 中文词：直接子串匹配
            if term_l in text_l:
                found.add(canonical)
    return sorted(found)


def _extract_education(text: str) -> str:
    """提取学历：多处提及时按 博士 > 硕士 > 本科 > 大专 优先级取最高档。"""
    matches = re.findall(
        r"(本科|硕士|博士|大专|专科|研究生|Bachelor|Master|PhD)",
        text,
        re.IGNORECASE,
    )
    if not matches:
        return ""
    matches_l = [m.lower() for m in matches]
    for level in EDU_PRIORITY:
        if level in matches_l:
            # 返回原始中文/英文写法中优先级最高的第一个命中形式
            for m in matches:
                if m.lower() == level:
                    return m
    return matches[0]


def _extract_projects(text: str, experience: str) -> list[str]:
    """按经历标题词切分出项目段落（供面试官深挖出题用）。

    与 interview.py 的旧逻辑统一：parser 是单一数据源，interview 侧只做消费。
    """
    source = experience or text
    if not source:
        return []
    parts = re.split(_PROJECT_SPLIT_PATTERN, source, flags=re.IGNORECASE)
    projects = [part.strip()[:600] for part in parts if len(part.strip()) > 30]
    # 切不出段落时兜底：整段经历前 600 字当作一个"项目"
    return projects[:3] or ([source.strip()[:600]] if source.strip() else [])


def parse_resume(text: str) -> dict:
    """解析简历文本，返回结构化结果。

    兼容性红线：skills/education/experience/raw_text 四个字段名不可改
    （main.py 与 interview.create_session 都在消费）；新字段只增不改名。
    """
    if not text or not text.strip():
        # 明确告诉调用方"为什么空"：前端可据此提示用户换文件，而不是显示 0 技能一脸懵
        return {
            "skills": [],
            "education": "",
            "experience": "",
            "raw_text": "",
            "projects": [],
            "warning": "简历文本为空：文件可能损坏，或是扫描件/图片型 PDF（无文字层），请上传文字版简历",
        }

    text_l = text.lower()
    found_skills = _match_skills(text_l)
    education = _extract_education(text)

    # 经历段落：先按标题词截取（含1200字符上限，防止极端简历拖垮 prompt）
    experience = ""
    patterns = [
        r"(项目经历|项目经验|实习经历|工作经历|实践经历)(.*?)(?:教育背景|技能|获奖|自我评价|个人评价|$)",
        r"(Project Experience|Internship|Work Experience|Projects)(.*?)(?:Education|Skills|Awards|Summary|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            experience = match.group(2).strip()[:1200]
            break

    return {
        "skills": found_skills,
        "education": education,
        "experience": experience,
        "raw_text": text[:3000],
        "projects": _extract_projects(text, experience),
    }
