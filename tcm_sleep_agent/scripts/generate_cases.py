"""Batch generate 100 TCM insomnia cases via DeepSeek and write to SQLite + Chroma."""

import json
import os
import sys
import time

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# ── Generation targets ────────────────────────────────────────────────────────

SYNDROMES = [
    {
        "syndrome": "心脾两虚",
        "prescription": "归脾汤加减",
        "key_symptoms": "失眠多梦、心悸健忘、食少纳呆、神疲乏力、面色萎黄",
        "tongue_pulse": "舌淡苔薄白，脉细弱",
        "treatment": "益气补血，健脾养心",
        "count": 18,
    },
    {
        "syndrome": "阴虚火旺",
        "prescription": "黄连阿胶汤加减",
        "key_symptoms": "入睡困难、心烦易怒、口干咽燥、盗汗、手足心热",
        "tongue_pulse": "舌红少苔，脉细数",
        "treatment": "滋阴降火，养心安神",
        "count": 18,
    },
    {
        "syndrome": "心肾不交",
        "prescription": "交泰丸合六味地黄丸加减",
        "key_symptoms": "心烦不寐、腰膝酸软、头晕耳鸣、遗精、五心烦热",
        "tongue_pulse": "舌红，脉细数",
        "treatment": "交通心肾，滋阴降火",
        "count": 16,
    },
    {
        "syndrome": "肝郁化火",
        "prescription": "龙胆泻肝汤加减",
        "key_symptoms": "急躁易怒、不寐多梦、头晕头胀、目赤耳鸣、口苦便秘",
        "tongue_pulse": "舌红苔黄，脉弦数",
        "treatment": "疏肝泻火，镇心安神",
        "count": 16,
    },
    {
        "syndrome": "痰热内扰",
        "prescription": "黄连温胆汤加减",
        "key_symptoms": "心烦不寐、胸闷脘痞、口苦痰多、头重目眩、恶心",
        "tongue_pulse": "舌红苔黄腻，脉滑数",
        "treatment": "清热化痰，和中安神",
        "count": 16,
    },
    {
        "syndrome": "心胆气虚",
        "prescription": "安神定志丸加减",
        "key_symptoms": "虚烦不寐、触事易惊、心悸胆怯、气短倦怠、遇事善惊",
        "tongue_pulse": "舌淡，脉弦细",
        "treatment": "益气镇惊，安神定志",
        "count": 16,
    },
]

# ── Prompt template ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是中医失眠症专家。请严格按照JSON格式生成中医失眠病历数据，用于AI训练数据集。
所有内容必须是合理的中医临床表现，不同病历的症状描述要有细微差异，体现真实临床多样性。
只输出JSON数组，不要有任何额外说明。"""

def make_user_prompt(syndrome_info: dict, batch_num: int, batch_size: int, start_idx: int) -> str:
    return f"""请生成{batch_size}条中医失眠症病历，证型为【{syndrome_info['syndrome']}】。

要求：
- 每条病历主诉、现病史、伴随症状要有差异（年龄18-70岁，病程1周-2年不等）
- 症状围绕：{syndrome_info['key_symptoms']}，但每条要有不同侧重
- 舌脉基本特征：{syndrome_info['tongue_pulse']}，允许有细微变化
- 治法：{syndrome_info['treatment']}
- 方剂：{syndrome_info['prescription']}
- 药物组成根据症状有合理加减（5-12味药，剂量3-30g）

严格输出JSON数组，每条格式如下：
[
  {{
    "id": "case_{start_idx + 1:03d}",
    "syndrome": "{syndrome_info['syndrome']}",
    "chief_complaint": "主诉文字",
    "present_illness": "现病史简述（2-3句）",
    "symptoms": ["症状1", "症状2", "症状3", "症状4", "症状5"],
    "tongue": "舌象描述",
    "pulse": "脉象描述",
    "treatment": "{syndrome_info['treatment']}",
    "prescription": "{syndrome_info['prescription']}",
    "herbs": [
      {{"name": "药名", "dose": "剂量g", "effect": "功效"}},
      ...
    ],
    "effects": "方剂总体功效",
    "ingredients": "药物列表（逗号分隔）",
    "name": "方剂名称",
    "category": "安神剂",
    "source": "LLM合成数据",
    "notes": "注意事项（如有）",
    "example_case": "简要病案分析（3-4句，说明辨证思路）"
  }}
]"""


# ── DeepSeek call ─────────────────────────────────────────────────────────────

def call_deepseek(prompt: str) -> str:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
        max_tokens=6000,
    )
    return response.choices[0].message.content.strip()


def parse_json_response(text: str) -> list[dict]:
    """Extract JSON array from LLM response, stripping markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # Find the JSON array boundaries robustly
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in response: {text[:200]}")
    text = text[start:end+1]
    return json.loads(text)


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_all() -> list[dict]:
    all_cases = []
    global_idx = 0

    for syndrome_info in SYNDROMES:
        total = syndrome_info["count"]
        batch_size = 4  # 每次请求生成4条，避免超长输出
        batches = (total + batch_size - 1) // batch_size

        print(f"\n生成证型：{syndrome_info['syndrome']} ({total}条，分{batches}批)")

        for b in range(batches):
            this_batch = min(batch_size, total - b * batch_size)
            start_idx = global_idx

            prompt = make_user_prompt(syndrome_info, b, this_batch, start_idx)

            for attempt in range(3):
                try:
                    print(f"  批次 {b+1}/{batches} (start_idx={start_idx+1})...", end=" ")
                    raw = call_deepseek(prompt)
                    cases = parse_json_response(raw)

                    # Re-assign IDs to ensure uniqueness
                    for i, case in enumerate(cases):
                        case["id"] = f"gen_{global_idx + i + 1:03d}"

                    all_cases.extend(cases)
                    global_idx += len(cases)
                    print(f"✓ {len(cases)}条")
                    time.sleep(0.5)  # rate limit buffer
                    break
                except Exception as e:
                    print(f"✗ 第{attempt+1}次失败: {e}")
                    if attempt == 2:
                        print("  跳过该批次")
                    else:
                        time.sleep(2)

    return all_cases


def save_and_import(cases: list[dict]) -> None:
    """Save to JSON file and import into SQLite + Chroma."""
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "generated_cases.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到 {output_path}")

    # Import into SQLite via ORM
    from src.db.session import init_db
    from src.db.crud import upsert_many
    init_db()
    count = upsert_many(cases)
    print(f"已写入 SQLite: {count} 条")

    # Rebuild Chroma index
    from src.services.retrieval_service import build_index
    chroma_count = build_index(force_rebuild=True)
    print(f"Chroma 索引重建完成: {chroma_count} 条")


if __name__ == "__main__":
    print("开始生成中医失眠症知识库...")
    print(f"目标：{sum(s['count'] for s in SYNDROMES)} 条，覆盖 {len(SYNDROMES)} 个证型\n")

    cases = generate_all()
    print(f"\n共生成 {len(cases)} 条病历")

    if cases:
        save_and_import(cases)
        print("\n✅ 知识库生成完成！")
    else:
        print("\n❌ 未生成任何数据，请检查 API Key 配置")
