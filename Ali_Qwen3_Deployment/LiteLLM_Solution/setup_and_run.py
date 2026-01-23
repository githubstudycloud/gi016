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

    # 尝试多种方式启动 LiteLLM
    # 方式 1: 直接使用 litellm 命令 (如果已在 PATH 中)
    print("📋 尝试方式 1: 使用 'litellm' 命令...")
    cmd = [
        "litellm",
        "--config", config_path,
        "--port", "4000",
        "--detailed_debug"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return
    except FileNotFoundError:
        print("⚠️ 'litellm' 命令未找到，尝试方式 2...")
    except Exception as e:
        print(f"⚠️ 方式 1 失败: {e}")

    # 方式 2: 使用 sys.executable -m litellm (如果支持)
    print("📋 尝试方式 2: 使用 'python -m litellm'...")
    cmd = [
        sys.executable, "-m", "litellm",
        "--config", config_path,
        "--port", "4000",
        "--detailed_debug"
    ]
    try:
        subprocess.run(cmd, check=True)
        return
    except subprocess.CalledProcessError as e:
         print(f"⚠️ 方式 2 失败 (可能是包结构不支持): {e}")
    except Exception as e:
         print(f"⚠️ 方式 2 失败: {e}")

    # 方式 3: 尝试从 Python 脚本内部调用 (终极方案)
    print("📋 尝试方式 3: 使用 Python 代码直接调用...")
    try:
        from litellm.proxy.proxy_cli import run_server
        # 构造参数列表 (模拟 argv)
        sys.argv = [
            "litellm",
            "--config", config_path,
            "--port", "4000",
            "--detailed_debug"
        ]
        run_server()
        return
    except ImportError:
        print("❌ 无法导入 litellm.proxy.proxy_cli，请检查安装！")
    except Exception as e:
        print(f"❌ 方式 3 失败: {e}")

    print("\n❌ 所有启动方式均失败。")
    print("请尝试手动运行: litellm --config litellm_config.yaml --port 4000")

if __name__ == "__main__":
    # 1. 检查并安装依赖
    install_litellm()
    
    # 2. 启动服务
    run_litellm_proxy()
