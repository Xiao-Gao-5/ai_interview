import pdfplumber
import re


def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"PDF解析错误: {e}")
        return ""
    return text


def parse_resume(text: str) -> dict:
    if not text:
        return {"skills": [], "education": "", "experience": "", "raw_text": ""}

    text_l = text.lower()

    skills = [
        "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust", "swift",
        "fastapi", "flask", "django", "spring boot", "springboot", "express", "nodejs",
        "mysql", "redis", "mongodb", "postgresql", "oracle", "sqlite", "elasticsearch",
        "linux", "docker", "kubernetes", "git", "github", "gitlab", "jenkins",
        "react", "vue", "angular", "html", "css", "sass", "less", "bootstrap",
        "tensorflow", "pytorch", "keras", "opencv", "pandas", "numpy", "scikit-learn",
        "aws", "azure", "gcp", "阿里云", "腾讯云",
        "nginx", "rabbitmq", "kafka", "rocketmq", "zookeeper",
        "restful", "graphql", "grpc", "websocket", "rpc"
    ]
    found_skills = [s for s in skills if s in text_l]

    education = ""
    m = re.search(r"(本科|硕士|博士|大专|专科|研究生| Bachelor| Master| PhD)", text)
    if m:
        education = m.group(1)

    experience = ""
    exp_patterns = [
        r'(项目经历|项目经验|实习经历|工作经验|实践经历)(.*?)(?:教育背景|自我评价|获奖情况|技能|兴趣爱好|个人评价|$)',
        r'(Project Experience|Internship|Work Experience|Projects)(.*?)(?:Education|Skills|Awards|Summary|$)'
    ]
    for pattern in exp_patterns:
        exp_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if exp_match:
            experience = exp_match.group(2).strip()[:600]
            break

    return {
        "skills": found_skills,
        "education": education,
        "experience": experience,
        "raw_text": text[:2500]
    }