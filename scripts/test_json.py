"""
测试 2: JSON 结构化输出
Hermes LLM 可以解析并重组成飞书友好的格式
"""
import json

def report():
    data = {
        "score": 85,
        "level": "极佳",
        "items": [
            {"name": "HRV", "value": "62ms", "status": "normal"},
            {"name": "静息心率", "value": "48bpm", "status": "good"},
            {"name": "睡眠时长", "value": "7h22min", "status": "good"},
            {"name": "深睡占比", "value": "18%", "status": "ideal"},
            {"name": "训练准备度", "value": "85/100", "status": "excellent"}
        ],
        "suggestion": "今天状态在线，可以安排高强度训练。",
        "trend": "训练准备度呈上升趋势，身体状态在改善。"
    }
    return json.dumps(data, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print(report())