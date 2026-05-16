"""
Garmin Agent - Main Entry Point

Interactive chat with the Garmin training assistant.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from garmin_agent.agent import GarminAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded config from {env_file}")
    else:
        load_dotenv()
        logger.info("Using system environment variables")


def print_banner():
    """Print welcome banner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║       🏃 Garmin 训练助手 v0.4.0 (Manual Dispatch)       ║
╚══════════════════════════════════════════════════════════╝
""")


def check_config():
    """Check configuration and return issues"""
    issues = []

    # Check API key
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        issues.append("❌ 缺少 ZHIPU_API_KEY")
    elif api_key == "你的API_KEY填在这里":
        issues.append("❌ 请在 .env 中填入真实的 ZHIPU_API_KEY")

    # Check tokens
    tokens_dir = Path(__file__).parent / "tokens"
    if not tokens_dir.exists():
        issues.append("⚠️  缺少 tokens/ 目录，首次登录需要账号密码")
    else:
        token_files = list(tokens_dir.glob("*.json"))
        if not token_files:
            issues.append("⚠️  tokens/ 目录为空，首次登录需要账号密码")

    return issues


def main():
    """Main entry point"""
    # Load configuration
    load_config()

    # Check config
    issues = check_config()
    if issues:
        print("配置问题：\n")
        for issue in issues:
            print(f"  {issue}")
        print("\n请检查 .env 文件配置")
        return 1

    print_banner()

    # Initialize agent
    print("🔄 正在连接 Garmin...")
    try:
        agent = GarminAgent()
        if not agent.connect():
            print("❌ 连接 Garmin 失败")
            print("   提示: TOKEN 可能已过期，请重新登录")
            return 1
        print("✅ 连接成功！\n")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        logger.exception("Init error")
        return 1

    # Show welcome
    print(agent.get_welcome_message())

    # Chat loop
    print("\n(输入 quit 退出, clear 清除记忆)\n")

    while True:
        try:
            user_input = input("你: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\n👋 再见！")
                break

            if user_input.lower() == "clear":
                agent.clear_memory()
                print("🧹 记忆已清除\n")
                continue

            # Get response
            print()
            response = agent.chat(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\n❌ 出错了: {e}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
