import subprocess
import sys
import os
import time

def install_litellm():
    """安装 LiteLLM 及其代理依赖"""
    print("🚀 正在安装 LiteLLM [proxy]...")
    try:
        # 使用 pip 安装 litellm[proxy]
        subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm[proxy]"])
        print("✅ LiteLLM 安装成功!")
    except subprocess.CalledProcessError as e:
        print(f"❌ LiteLLM 安装失败: {e}")
        print("请尝试手动运行: pip install 'litellm[proxy]'")
        sys.exit(1)

def run_litellm_proxy():
    """启动 LiteLLM 代理服务"""
    print("\n🚀 正在启动 LiteLLM 代理服务 (端口 4000)...")
    
    # 获取配置文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "litellm_config.yaml")
    
    if not os.path.exists(config_path):
        print(f"❌ 找不到配置文件: {config_path}")
        return

    # 构建启动命令
    # litellm --config <path> --port 4000
    cmd = [
        sys.executable, "-m", "litellm",
        "--config", config_path,
        "--port", "4000",
        "--detailed_debug" # 开启详细调试
    ]
    
    print(f"📋 执行命令: {' '.join(cmd)}")
    print("💡 提示: 请确保 vLLM 已在 8001 端口启动 (API Base: http://localhost:8001/v1)")
    print("💡 提示: 客户端连接地址: http://localhost:4000")
    print("💡 提示: 客户端 API Key: sk-1234")
    print("-" * 50)

    try:
        # 启动子进程
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止 (用户中断)")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 服务异常退出: {e}")
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")

if __name__ == "__main__":
    # 1. 检查并安装依赖
    install_litellm()
    
    # 2. 启动服务
    run_litellm_proxy()
