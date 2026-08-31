from __future__ import annotations

import json
import re
import uuid

from .llm import call_qwen
from .nlp_scoring import SemanticScorer
from .rag_engine import VectorRAG

rag = VectorRAG()
scorer = SemanticScorer()
sessions: dict[str, "InterviewSession"] = {}


class InterviewSession:
    def __init__(self, resume_info: dict):
        self.session_id = str(uuid.uuid4())
        self.resume = resume_info or {}
        self.history: list[dict[str, str]] = []
        self.phase = "greeting"
        self.basic_count = 0
        self.max_basic = 3
        self.project_index = 0
        self.project_q_count = 0
        self.max_project_q = 3
        self.follow_up_count = 0
        self.max_follow_up = 1
        self.answers_eval: list[dict] = []
        self.projects = self._extract_projects()
        self.profile = self._generate_profile()

    def next_interviewer_action(self, user_answer: str | None = None) -> tuple[str, bool]:
        if user_answer:
            self.history.append({"role": "candidate", "content": user_answer})
            if self._is_repeat_complaint(user_answer):
                self.follow_up_count = self.max_follow_up
            else:
                self.answers_eval.append(self._evaluate_answer(user_answer))

        if self.phase == "greeting":
            self.phase = "basic"
            greeting = f"你好，我是 AI 面试官。{self.profile}\n\n我们先从基础知识开始。"
            question = self._generate_basic_question()
            self._record_interviewer(question)
            return f"{greeting}\n\n【问题】{question}", False

        if self.phase == "basic":
            if self._should_follow_up("accuracy"):
                question = self._generate_followup_question()
                self._record_interviewer(question)
                return f"【追问】{question}", False

            self.follow_up_count = 0
            self.basic_count += 1
            if self.basic_count >= self.max_basic:
                self.phase = "project"
                question = self._generate_project_question()
                self._record_interviewer(question)
                return f"基础知识部分结束。接下来聊聊你的项目经历。\n\n【问题】{question}", False

            question = self._generate_basic_question()
            self._record_interviewer(question)
            return f"【问题】{question}", False

        if self.phase == "project":
            if self._should_follow_up("depth"):
                question = self._generate_project_deep_question()
                self._record_interviewer(question)
                return f"【追问】{question}", False

            self.follow_up_count = 0
            self.project_q_count += 1
            if self.project_q_count >= self.max_project_q:
                self.project_index += 1
                self.project_q_count = 0
                if self.project_index >= len(self.projects):
                    self.phase = "scoring"
                    return self._generate_final_feedback(), True

            question = self._generate_project_question()
            self._record_interviewer(question)
            return f"【问题】{question}", False

        return self._generate_final_feedback(), True

    def _record_interviewer(self, content: str) -> None:
        self.history.append({"role": "interviewer", "content": content})

    def _extract_projects(self) -> list[str]:
        text = self.resume.get("experience") or self.resume.get("raw_text", "")
        if not text:
            return ["候选人的简历中未提取到明确项目，请围绕其技能栈展开项目经验追问。"]

        parts = re.split(
            r"项目经历|项目经验|实习经历|实践经历|工作经历|Project Experience|Projects|Internship|Work Experience",
            text,
            flags=re.IGNORECASE,
        )
        projects = [part.strip()[:600] for part in parts if len(part.strip()) > 30]
        return projects[:3] or [text[:600]]

    def _generate_profile(self) -> str:
        skills = ", ".join(self.resume.get("skills", [])) or "未提取到明确技能"
        education = self.resume.get("education") or "未知"
        prompt = f"""基于候选人简历生成一句 80 字以内的面试画像，只输出画像内容。

技能：{skills}
学历：{education}
简历摘要：{self.resume.get("raw_text", "")[:500]}
"""
        return call_qwen(prompt, temperature=0.4) or f"我会围绕 {skills}、项目经历和基础能力进行考察。"

    def _generate_basic_question(self) -> str:
        skills = ", ".join(self.resume.get("skills", [])) or "计算机基础"
        docs, _ = rag.retrieve(f"{skills} 面试题", top_k=3)
        context = "\n".join(
            f"- {doc.get('question', '')}：{doc.get('answer', '')[:160]}" for doc in docs
        )
        recent = "\n".join(f"- {q}" for q in self._recent_questions())
        prompt = f"""你是技术面试官。请基于候选人技能和知识库生成一道基础技术面试题，只输出问题。

候选人技能：{skills}

知识库片段：
{context}

已经问过的问题，避免重复：
{recent or "无"}

要求：问题具体、适合校招或实习面试，可考察概念、原理、场景或代码思路。
"""
        return call_qwen(prompt, temperature=0.8) or "请介绍一个你熟悉的数据结构，并说明它适合解决什么问题。"

    def _generate_followup_question(self) -> str:
        last_q = self._last_by_role("interviewer")
        last_answer = self._last_by_role("candidate")
        prompt = f"""你是技术面试官。请针对候选人刚才的回答生成一个更深入但具体的追问，只输出问题。

原问题：{last_q}
候选人回答：{last_answer[:500]}
"""
        self.follow_up_count += 1
        return call_qwen(prompt, temperature=0.6) or "你能进一步说明其中的关键原理和边界情况吗？"

    def _generate_project_question(self) -> str:
        project = self.projects[min(self.project_index, len(self.projects) - 1)]
        prompt = f"""你是技术面试官。请基于下面项目经历生成一个开放但具体的面试问题，只输出问题。

项目经历：
{project[:700]}

要求：优先考察候选人的职责、技术选型、实现难点、性能优化或结果复盘。
"""
        return call_qwen(prompt, temperature=0.75) or "请介绍一个你参与最深的项目，包括你的职责、技术方案和遇到的难点。"

    def _generate_project_deep_question(self) -> str:
        project = self.projects[min(self.project_index, len(self.projects) - 1)]
        answer = self._last_by_role("candidate")
        prompt = f"""你是技术面试官。请基于项目背景和候选人回答生成一个技术深挖追问，只输出问题。

项目背景：{project[:500]}
候选人回答：{answer[:500]}
"""
        self.follow_up_count += 1
        return call_qwen(prompt, temperature=0.6) or "这个方案在性能、可靠性或扩展性上有哪些取舍？"

    def _evaluate_answer(self, answer: str) -> dict:
        question = self._last_by_role("interviewer")
        docs, _ = rag.retrieve(question, top_k=3)
        reference = "\n".join(
            f"{doc.get('question', '')}\n{doc.get('answer', '')}" for doc in docs
        )
        return scorer.evaluate_answer(question, answer, reference)

    def _generate_final_feedback(self) -> str:
        if not self.answers_eval:
            feedback = {
                "total_score": 60.0,
                "dimensions": {
                    "基础知识掌握程度": 60.0,
                    "项目理解深度": 60.0,
                    "回答逻辑性": 60.0,
                    "表达完整性": 60.0,
                    "岗位匹配度": 60.0,
                },
                "report": "面试信息不足，建议补充完整回答后再生成详细评价。",
                "details": [],
            }
            return json.dumps(feedback, ensure_ascii=False)

        avg_acc = self._avg("accuracy")
        avg_depth = self._avg("depth")
        avg_logic = self._avg("logic")
        avg_complete = self._avg("completeness")
        match_score = min(10.0, 5.0 + len(self.resume.get("skills", [])) * 1.2)

        dimensions = {
            "基础知识掌握程度": round(avg_acc * 10, 1),
            "项目理解深度": round(avg_depth * 10, 1),
            "回答逻辑性": round(avg_logic * 10, 1),
            "表达完整性": round(avg_complete * 10, 1),
            "岗位匹配度": round(match_score * 10, 1),
        }
        total = round(
            dimensions["基础知识掌握程度"] * 0.25
            + dimensions["项目理解深度"] * 0.25
            + dimensions["回答逻辑性"] * 0.2
            + dimensions["表达完整性"] * 0.15
            + dimensions["岗位匹配度"] * 0.15,
            1,
        )

        report_prompt = f"""请根据面试评分生成 200 字以内的中文评价报告，语气专业、客观、可执行。

维度分：{json.dumps(dimensions, ensure_ascii=False)}
总分：{total}
各轮评价：{json.dumps([item.get("comment", "") for item in self.answers_eval], ensure_ascii=False)}
"""
        report = call_qwen(report_prompt, temperature=0.4) or "候选人具备一定基础，需要继续加强技术细节表达、项目复盘和方案取舍分析。"
        return json.dumps(
            {
                "total_score": total,
                "dimensions": dimensions,
                "report": report,
                "details": self.answers_eval,
            },
            ensure_ascii=False,
        )

    def _avg(self, key: str) -> float:
        return sum(item.get(key, 6.0) for item in self.answers_eval) / len(self.answers_eval)

    def _last_by_role(self, role: str) -> str:
        for item in reversed(self.history):
            if item["role"] == role:
                return item["content"]
        return ""

    def _recent_questions(self, n: int = 5) -> list[str]:
        return [
            item["content"]
            for item in reversed(self.history)
            if item["role"] == "interviewer"
        ][:n]

    def _should_follow_up(self, score_key: str) -> bool:
        if not self.answers_eval:
            return False
        score = self.answers_eval[-1].get(score_key, 0)
        return self.follow_up_count < self.max_follow_up and score >= 6

    def _is_repeat_complaint(self, answer: str) -> bool:
        phrases = ["重复", "一样", "相同", "刚才问过", "已经问过", "换题", "换个问题"]
        return any(phrase in answer for phrase in phrases)


def create_session(resume_info: dict) -> str:
    session = InterviewSession(resume_info)
    sessions[session.session_id] = session
    return session.session_id


def get_session(session_id: str) -> InterviewSession | None:
    return sessions.get(session_id)


def chat(session_id: str, user_msg: str | None) -> tuple[str | None, bool]:
    session = get_session(session_id)
    if not session:
        return None, True
    return session.next_interviewer_action(user_msg)
