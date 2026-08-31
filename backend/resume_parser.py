from __future__ import annotations

import re

import pdfplumber


def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as exc:
        print(f"PDF 解析错误: {exc}")
        return ""
    return text


def parse_resume(text: str) -> dict:
    if not text:
        return {"skills": [], "education": "", "experience": "", "raw_text": ""}

    text_l = text.lower()
    skills = [
        "python",
        "java",
        "c++",
        "c#",
        "javascript",
        "typescript",
        "go",
        "rust",
        "fastapi",
        "flask",
        "django",
        "spring boot",
        "springboot",
        "nodejs",
        "mysql",
        "redis",
        "mongodb",
        "postgresql",
        "elasticsearch",
        "linux",
        "docker",
        "kubernetes",
        "git",
        "jenkins",
        "react",
        "vue",
        "html",
        "css",
        "pandas",
        "numpy",
        "scikit-learn",
        "aws",
        "azure",
        "阿里云",
        "腾讯云",
        "nginx",
        "rabbitmq",
        "kafka",
        "rocketmq",
        "zookeeper",
        "restful",
        "graphql",
        "grpc",
        "websocket",
        "rpc",
    ]
    found_skills = sorted({skill for skill in skills if skill.lower() in text_l})

    education = ""
    education_match = re.search(
        r"(本科|硕士|博士|大专|专科|研究生|Bachelor|Master|PhD)",
        text,
        re.IGNORECASE,
    )
    if education_match:
        education = education_match.group(1)

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
    }
