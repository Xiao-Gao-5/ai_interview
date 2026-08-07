import uuid
import json
import re
from .llm import call_qwen
from .rag_engine import SimpleRAG

rag = SimpleRAG()


class InterviewSession:
    """管理单次面试的完整状态与流程"""

    def __init__(self, resume_info):
        self.session_id = str(uuid.uuid4())
        self.resume = resume_info
        self.history = []
        self.phase = "greeting"
        self.basic_count = 0
        self.max_basic = 3
        self.project_index = 0
        self.projects = self._extract_projects()
        self.project_q_count = 0
        self.max_project_q = 3
        self.follow_up_count = 0
        self.max_follow_up = 2
        self.answers_eval = []
        self.profile = ""
        self._generate_profile()

    def _extract_projects(self):
        text = self.resume.get("raw_text", "")
        parts = re.split(
            r'项目经历|项目经验|实习经历|实践经历|项目名称|Project Experience|Projects|工作经历',
            text,
            flags=re.IGNORECASE
        )
        projects = []
        for p in parts[1:]:
            clean = p.strip()
            if len(clean) > 30:
                projects.append(clean[:500])
        if not projects:
            projects = [text[:500]]
        return projects[:3]

    def _generate_profile(self):
        skills = ", ".join(self.resume.get("skills", []))
        edu = self.resume.get("education", "未知")
        prompt = f"""基于以下简历信息，生成一段简洁的用户画像和面试重点（80字以内）：
技能：{skills}
学历：{edu}
简历摘要：{self.resume.get('raw_text', '')[:300]}

要求：直接输出画像内容，不要有任何前缀说明。
"""
        self.profile = call_qwen(prompt, temperature=0.5) or "该同学具备相关技术背景。"

    def next_interviewer_action(self, user_answer=None):
        if user_answer is not None:
            self.history.append({"role": "candidate", "content": user_answer})

            # 检测用户是否指出重复
            if self._is_user_complaining_repeat(user_answer):
                # 强制跳过追问，直接换新题
                self.follow_up_count = self.max_follow_up
                self.answers_eval.append({
                    "accuracy": 5, "completeness": 5, "logic": 5, "depth": 5,
                    "comment": "用户指出题目重复", "key_tech": []
                })
            else:
                self.answers_eval.append(self._evaluate_answer(user_answer))

        if self.phase == "greeting":
            self.phase = "basic"
            self.basic_count = 0
            self.follow_up_count = 0
            profile_msg = f"你好！我是AI面试官。{self.profile}\n\n让我们开始面试。首先考察基础知识："
            self.history.append({"role": "interviewer", "content": profile_msg})
            q = self._generate_basic_question()
            self.history.append({"role": "interviewer", "content": q})
            return f"{profile_msg}\n\n【问题】{q}", False

        elif self.phase == "basic":
            # 检查是否追问
            if (self.answers_eval and
                    self.follow_up_count < self.max_follow_up and
                    self.answers_eval[-1].get("accuracy", 0) >= 6 and
                    self.answers_eval[-1].get("comment", "") != "用户指出题目重复"):
                self.follow_up_count += 1
                q = self._generate_followup_question()
                self.history.append({"role": "interviewer", "content": q})
                return f"【追问】{q}", False

            self.follow_up_count = 0
            self.basic_count += 1

            if self.basic_count >= self.max_basic:
                self.phase = "project"
                self.project_q_count = 0
                self.follow_up_count = 0
                trans_msg = "基础知识考察结束。接下来聊聊你的项目经历："
                self.history.append({"role": "interviewer", "content": trans_msg})
                q = self._generate_project_question()
                self.history.append({"role": "interviewer", "content": q})
                return f"{trans_msg}\n\n【问题】{q}", False

            q = self._generate_basic_question()
            self.history.append({"role": "interviewer", "content": q})
            return f"【问题】{q}", False

        elif self.phase == "project":
            if (self.answers_eval and
                    self.follow_up_count < self.max_follow_up and
                    self.answers_eval[-1].get("depth", 0) >= 6 and
                    self.answers_eval[-1].get("comment", "") != "用户指出题目重复"):
                self.follow_up_count += 1
                q = self._generate_project_deep_question()
                self.history.append({"role": "interviewer", "content": q})
                return f"【追问】{q}", False

            self.follow_up_count = 0
            self.project_q_count += 1

            if self.project_q_count >= self.max_project_q:
                self.project_index += 1
                self.project_q_count = 0
                if self.project_index >= len(self.projects):
                    self.phase = "scoring"
                    return self._generate_final_feedback(), True
                trans_msg = f"我们来看下一个项目（{self.project_index + 1}/{len(self.projects)}）："
                self.history.append({"role": "interviewer", "content": trans_msg})
                q = self._generate_project_question()
                self.history.append({"role": "interviewer", "content": q})
                return f"{trans_msg}\n\n【问题】{q}", False

            q = self._generate_project_question()
            self.history.append({"role": "interviewer", "content": q})
            return f"【问题】{q}", False

        elif self.phase == "scoring":
            return self._generate_final_feedback(), True

        return "面试结束。", True

    def _is_user_complaining_repeat(self, answer):
        """检测用户是否在抱怨题目重复"""
        keywords = ["重复", "一样", "相同", "刚才问过", "已经问过", "换题", "换个问题"]
        answer_lower = answer.lower()
        return any(k in answer_lower for k in keywords)

    def _get_recent_questions(self, n=5):
        """获取最近问过的问题文本，用于去重"""
        qs = []
        for h in reversed(self.history):
            if h["role"] == "interviewer":
                content = h["content"]
                # 提取【问题】或【追问】后面的内容
                if "【问题】" in content:
                    q_text = content.split("【问题】")[-1].strip()
                    qs.append(q_text)
                elif "【追问】" in content:
                    q_text = content.split("【追问】")[-1].strip()
                    qs.append(q_text)
                if len(qs) >= n:
                    break
        return qs

    def _generate_basic_question(self):
        skills = self.resume.get("skills", [])
        skill_str = ", ".join(skills) if skills else "计算机基础"
        docs, _ = rag.retrieve(f"{skill_str} 面试题", top_k=2)
        context = "\n".join([f"知识点：{d['question']}" for d in docs])

        recent_qs = self._get_recent_questions(5)
        avoid_text = ""
        if recent_qs:
            avoid_text = f"\n\n已问过的问题（绝对不要重复类似题目，必须换完全不同的方向）：\n" + "\n".join(
                [f"{i + 1}. {q}" for i, q in enumerate(recent_qs)])

        prompt = f"""你是AI面试官。基于候选人的技能栈({skill_str})和以下相关知识点，生成一道基础面试题：

相关知识点：
{context}
{avoid_text}

要求：
1. 问题与技能栈强相关，但类型要多样化（概念、原理、场景、代码均可）
2. 难度适中，适合校招/实习面试
3. 只输出问题本身，不要有任何解释、答案或前缀
4. 如果已问过的问题和技能栈相关，请换一个完全不同的技术方向出题
"""
        q = call_qwen(prompt, temperature=0.9)
        return q or "请介绍一下你最熟悉的数据结构及其应用场景。"

    def _generate_followup_question(self):
        """基于上一轮回答生成追问"""
        last_answer = ""
        last_q = ""
        for h in reversed(self.history):
            if h["role"] == "candidate" and not last_answer:
                last_answer = h["content"]
            if h["role"] == "interviewer" and not last_q:
                last_q = h["content"]
            if last_answer and last_q:
                break

        prompt = f"""你是AI面试官。候选人刚才回答了以下问题，请针对回答中的技术细节追问一个更深入的问题：

原问题：{last_q}
候选人回答：{last_answer[:300]}

要求：
1. 追问回答中提到的具体技术点、原理或实现细节
2. 问题要更具体，不要泛泛而谈
3. 只输出问题本身
"""
        q = call_qwen(prompt, temperature=0.7)
        return q or "你能详细解释一下刚才提到的技术原理吗？"

    def _generate_project_question(self):
        project = self.projects[self.project_index] if self.project_index < len(self.projects) else "你的项目"
        prompt = f"""你是AI面试官。针对以下项目描述，生成一个面试问题：

项目描述：{project[:400]}

要求：
1. 围绕项目背景、技术选型、个人职责、项目成果提问
2. 问题开放，让候选人能展开描述
3. 只输出问题本身
"""
        q = call_qwen(prompt, temperature=0.8)
        return q or "请详细描述一下这个项目的背景、你在其中的职责以及使用的技术栈。"

    def _generate_project_deep_question(self):
        """项目深挖追问"""
        last_answer = ""
        for h in reversed(self.history):
            if h["role"] == "candidate":
                last_answer = h["content"]
                break

        project = self.projects[self.project_index] if self.project_index < len(self.projects) else ""

        prompt = f"""你是AI面试官。候选人在介绍项目时提到了以下内容，请针对其中的技术细节进行深挖追问：

项目背景：{project[:300]}
候选人回答：{last_answer[:300]}

要求：
1. 追问具体技术原理（如：为什么选这个技术？有没有考虑过替代方案？）
2. 追问性能、优化、难点解决
3. 只输出问题本身
"""
        q = call_qwen(prompt, temperature=0.7)
        return q or "你提到使用了某些技术，能详细说明一下选型原因和实现细节吗？"

    def _evaluate_answer(self, answer):
        last_q = ""
        for h in reversed(self.history):
            if h["role"] == "interviewer":
                last_q = h["content"]
                break

        docs, _ = rag.retrieve(last_q, top_k=2)
        ref_answers = "\n".join([f"参考：{d['answer'][:200]}" for d in docs])

        prompt = f"""评估以下面试回答（输出严格JSON格式，不要markdown标记）：

问题：{last_q}
候选人回答：{answer}

相关知识点参考：
{ref_answers}

请从以下维度评分（1-10分），并给出简要评价：
- accuracy（准确性）：技术细节是否正确
- completeness（完整性）：是否覆盖问题要点
- logic（逻辑性）：表达是否清晰有条理
- depth（深度）：是否有深入思考或扩展

输出格式：
{{"accuracy": 8, "completeness": 7, "logic": 8, "depth": 6, "comment": "评价...", "key_tech": ["提到的技术1"]}}
"""
        result = call_qwen(prompt, temperature=0.3)
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                eval_data = json.loads(json_match.group())
                for key in ["accuracy", "completeness", "logic", "depth"]:
                    if key not in eval_data:
                        eval_data[key] = 7
                if "comment" not in eval_data:
                    eval_data["comment"] = "回答尚可，有提升空间。"
                if "key_tech" not in eval_data:
                    eval_data["key_tech"] = []
                return eval_data
        except Exception:
            pass
        return {"accuracy": 7, "completeness": 7, "logic": 7, "depth": 6, "comment": "回答尚可，有提升空间。",
                "key_tech": []}

    def _generate_final_feedback(self):
        if not self.answers_eval:
            return json.dumps({
                "total_score": 60.0,
                "dimensions": {"基础知识掌握程度": 60, "项目理解深度": 60, "回答逻辑性": 60, "表达完整性": 60,
                               "岗位匹配度": 60},
                "report": "未能获取足够信息生成详细报告。",
                "details": []
            }, ensure_ascii=False)

        basic_scores = [a.get("accuracy", 7) for a in self.answers_eval[:self.max_basic + 1]]
        project_scores = [a.get("depth", 6) for a in self.answers_eval[self.max_basic + 1:]]

        avg_acc = sum(basic_scores) / len(basic_scores) if basic_scores else 7
        avg_depth = sum(project_scores) / len(project_scores) if project_scores else 6
        avg_logic = sum(a.get("logic", 7) for a in self.answers_eval) / len(self.answers_eval)
        avg_comp = sum(a.get("completeness", 7) for a in self.answers_eval) / len(self.answers_eval)

        skills = self.resume.get("skills", [])
        match_score = min(len(skills) * 1.5 + 5, 10)

        basic_score = avg_acc * 10
        project_score = avg_depth * 10 + 20
        logic_score = avg_logic * 10
        complete_score = avg_comp * 10
        match_score_total = match_score * 10

        total = (
                basic_score * 0.25 +
                project_score * 0.25 +
                logic_score * 0.20 +
                complete_score * 0.15 +
                match_score_total * 0.15
        )

        prompt = f"""基于以下面试表现数据，生成一份面试评价报告（200字以内）：

基础知识掌握：{basic_score:.1f}/100
项目理解深度：{project_score:.1f}/100
回答逻辑性：{logic_score:.1f}/100
表达完整性：{complete_score:.1f}/100
岗位匹配度：{match_score_total:.1f}/100
总分：{total:.1f}/100

各轮评价摘要：
{json.dumps([{"comment": a.get("comment", "")} for a in self.answers_eval], ensure_ascii=False)}

要求：
1. 指出2-3个表现好的方面
2. 指出2-3个存在的问题
3. 给出2-3条具体改进建议
4. 语言专业、客观、鼓励性
"""
        report = call_qwen(prompt, temperature=0.5) or "面试完成，建议继续加强技术基础与项目表达。"

        feedback = {
            "total_score": round(total, 1),
            "dimensions": {
                "基础知识掌握程度": round(basic_score, 1),
                "项目理解深度": round(project_score, 1),
                "回答逻辑性": round(logic_score, 1),
                "表达完整性": round(complete_score, 1),
                "岗位匹配度": round(match_score_total, 1)
            },
            "report": report,
            "details": self.answers_eval
        }
        return json.dumps(feedback, ensure_ascii=False)


sessions = {}


def create_session(resume_info):
    session = InterviewSession(resume_info)
    sessions[session.session_id] = session
    return session.session_id


def get_session(session_id):
    return sessions.get(session_id)


def chat(session_id, user_msg):
    session = get_session(session_id)
    if not session:
        return None, True
    reply, is_end = session.next_interviewer_action(user_msg)
    return reply, is_end