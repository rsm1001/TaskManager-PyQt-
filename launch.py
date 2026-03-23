"""
Task Manager 启动脚本
用于安装依赖和运行应用程序
"""

import subprocess
import sys
import os


def install_requirements():
    """安装依赖包"""
    print("正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("依赖包安装完成！")
        return True
    except subprocess.CalledProcessError:
        print("依赖包安装失败！")
        return False


def run_app():
    """运行应用程序"""
    print("正在启动任务管理系统...")
    try:
        subprocess.check_call([sys.executable, "main.py"])
    except subprocess.CalledProcessError as e:
        print(f"应用程序启动失败: {e}")


def main():
    """主函数"""
    print("任务管理系统 - PyQt版")
    print("="*30)
    
    # 检查是否需要安装依赖
    if not os.path.exists("venv"):
        choice = input("是否创建虚拟环境并安装依赖？(y/n): ").lower()
        if choice == 'y':
            # 创建虚拟环境
            print("正在创建虚拟环境...")
            subprocess.check_call([sys.executable, "-m", "venv", "venv"])
            
            # 根据操作系统决定激活命令
            if os.name == 'nt':  # Windows
                pip_path = os.path.join("venv", "Scripts", "pip.exe")
            else:  # Unix/Linux/MacOS
                pip_path = os.path.join("venv", "bin", "pip")
            
            # 安装依赖
            subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
            print("虚拟环境和依赖安装完成！")
        else:
            # 直接安装到全局环境
            if not install_requirements():
                return
    else:
        print("检测到虚拟环境，正在激活...")
        # 激活虚拟环境并安装依赖
        if os.name == 'nt':  # Windows
            pip_path = os.path.join("venv", "Scripts", "pip.exe")
        else:  # Unix/Linux/MacOS
            pip_path = os.path.join("venv", "bin", "pip")
        
        subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
    
    # 运行应用程序
    run_app()


if __name__ == "__main__":
    main()