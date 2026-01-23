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
    
    # 强制设置 Python UTF-8 模式，解决 Windows 下 GBK 编码问题
    os.environ["PYTHONUTF8"] = "1"
    # 设置编码相关的环境变量
    os.environ["LANG"] = "en_US.UTF-8"
    
    # 获取配置文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "litellm_config.yaml")
    
    if not os.path.exists(config_path):
        print(f"❌ 找不到配置文件: {config_path}")
        return

    # 尝试多种方式启动 LiteLLM
    
    # 方式 0: 查找 Scripts 目录下的 litellm.exe (Windows 特有)
    print("📋 尝试方式 0: 查找 Python Scripts 目录下的 litellm.exe...")
    scripts_dir = os.path.join(os.path.dirname(sys.executable), "Scripts")
    litellm_exe = os.path.join(scripts_dir, "litellm.exe")
    if os.path.exists(litellm_exe):
        print(f"✅ 找到可执行文件: {litellm_exe}")
        cmd = [
            litellm_exe,
            "--config", config_path,
            "--port", "4000",
            "--detailed_debug"
        ]
        try:
            subprocess.run(cmd, check=True)
            return
        except Exception as e:
            print(f"⚠️ 方式 0 失败: {e}")
    else:
        print(f"⚠️ 未找到 {litellm_exe}")

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

    # 方式 2: 使用 python -m litellm (部分版本支持)
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
        # 再次强制重新设置编码，防止 subprocess 没生效
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        
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
