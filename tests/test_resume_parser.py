# -*- coding: utf-8 -*-
"""resume_parser 最小回归测试：python tests/test_resume_parser.py 直接运行。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.resume_parser import parse_resume  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}  {detail}")


# ── 用例 1：词边界修复——go 不得误报 ─────────────────────────────
r = parse_resume("熟练使用 django flask algorithm google，懂 linux")
print("[用例1] 词边界匹配（go 不误报）")
check("go 不再误报 django/algorithm/google", "go" not in r["skills"], f"got {r['skills']}")
check("linux 正常识别", "linux" in r["skills"], f"got {r['skills']}")
# golang 别名单独验证
r_golang = parse_resume("写过 golang 服务")
check("golang 别名归一为 go", "go" in r_golang["skills"], f"got {r_golang['skills']}")

# ── 用例 2：别名与特殊字符 ──────────────────────────────────────
r = parse_resume("技术栈：js k8s postgres c++ c# python fastapi mysql redis docker")
print("[用例2] 别名归一与 c++/c#")
check("js → javascript", "javascript" in r["skills"], f"got {r['skills']}")
check("k8s → kubernetes", "kubernetes" in r["skills"], f"got {r['skills']}")
check("postgres → postgresql", "postgresql" in r["skills"], f"got {r['skills']}")
check("c++ 正确识别", "c++" in r["skills"], f"got {r['skills']}")
check("c# 正确识别", "c#" in r["skills"], f"got {r['skills']}")

# ── 用例 3：学历取最高 ─────────────────────────────────────────
r = parse_resume("教育背景：某某大学 本科 2020-2024；2024 至今 硕士在读")
print("[用例3] 学历取最高档")
check("本科+硕士并存时取硕士", r["education"] == "硕士", f"got {r['education']!r}")
r2 = parse_resume("预计 2027 年获得本科学位")
check("仅本科时返回本科", r2["education"] == "本科", f"got {r2['education']!r}")

# ── 用例 4：空文本 → 明确 warning ───────────────────────────────
r = parse_resume("")
print("[用例4] 空文本警告")
check("返回 warning 字段", bool(r.get("warning")), f"got {r}")
check("兼容字段仍在", r["skills"] == [] and r["education"] == "" and "raw_text" in r)

# ── 用例 5：项目切分 ───────────────────────────────────────────
resume_text = """张三 求职意向：后端开发
技能：python fastapi mysql redis docker
项目经历
电商订单系统：负责订单服务设计，使用 fastapi + mysql，QPS 从 200 提升到 2000，引入 redis 缓存热点数据。
教育背景
某某大学 本科"""
r = parse_resume(resume_text)
print("[用例5] 项目切分")
check("切出至少 1 个项目段落", len(r.get("projects", [])) >= 1, f"got {r.get('projects')}")
check("项目段落包含订单系统", any("订单" in p for p in r.get("projects", [])), f"got {r.get('projects')}")

# ── 用例 6：兼容红线——消费方字段齐全 ─────────────────────────────
need = {"skills", "education", "experience", "raw_text"}
print("[用例6] 兼容性红线")
check("四个既有字段全部存在", need.issubset(r.keys()), f"got {sorted(r.keys())}")

print(f"\n结果：{passed} 通过 / {failed} 失败")
sys.exit(1 if failed else 0)
