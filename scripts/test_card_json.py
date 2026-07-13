"""
测试 4: 飞书卡片 JSON（interactive 格式）
最漂亮的飞书消息格式
"""
import json

def report():
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🌅 晨起健康指南"},
            "template": "green"
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**综合评分**\n85/100 🟢"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**状态**\n极佳"}}
                ]
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**HRV**\n62ms"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**静息心率**\n48bpm"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**睡眠时长**\n7h22min"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**训练准备度**\n85/100"}}
                ]
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "💬 **建议**\n今天状态在线，可以安排高强度训练。"}
            },
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": "数据来源: Garmin Connect"}]
            }
        ]
    }
    return json.dumps(card, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print(report())