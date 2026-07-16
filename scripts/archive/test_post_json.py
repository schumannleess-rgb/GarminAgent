"""
测试 3: 飞书富文本 JSON（post 格式）
直接生成飞书 API 能发的富文本消息结构
"""
import json

def report():
    msg = {
        "zh_cn": {
            "title": "🌅 晨起健康指南",
            "content": [
                [
                    {"tag": "text", "text": "综合评分: "},
                    {"tag": "text", "text": "85/100", "style": ["bold"]},
                    {"tag": "text", "text": " 🟢 极佳"}
                ],
                [{"tag": "text", "text": ""}],
                [
                    {"tag": "text", "text": "HRV: "},
                    {"tag": "text", "text": "62ms", "style": ["bold"]},
                    {"tag": "text", "text": "  静息心率: "},
                    {"tag": "text", "text": "48bpm", "style": ["bold"]}
                ],
                [
                    {"tag": "text", "text": "睡眠: "},
                    {"tag": "text", "text": "7h22min", "style": ["bold"]},
                    {"tag": "text", "text": "  准备度: "},
                    {"tag": "text", "text": "85/100", "style": ["bold"]}
                ],
                [{"tag": "text", "text": ""}],
                [
                    {"tag": "text", "text": "💬 建议: "},
                    {"tag": "text", "text": "今天状态在线，可以安排高强度训练。"}
                ]
            ]
        }
    }
    return json.dumps(msg, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print(report())