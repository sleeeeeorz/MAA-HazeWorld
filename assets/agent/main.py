import sys
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.tasker import Tasker

# 让 import my_xxx 在任意工作目录下都能成立
_AGENT_DIR = Path(__file__).resolve().parent
# 源码形态：agent 在 assets/agent，项目根是 assets 的上一级；
# 打包形态：agent 在包根，项目根就是它的父目录。
_PROJECT_ROOT = (
    _AGENT_DIR.parent.parent
    if _AGENT_DIR.parent.name == "assets"
    else _AGENT_DIR.parent
)
sys.path.insert(0, str(_AGENT_DIR))

import my_action  # noqa: E402,F401  # 导入即注册
import my_reco  # noqa: E402,F401
import my_weekly  # noqa: E402,F401


def main():
    # 客户端（MFAAvalonia / MPE）按 UTF-8 读子进程输出，
    # 而 Windows 下 python 默认用 GBK 写 stdout，中文会变成乱码。
    # 这里强制切到 UTF-8，日志里的中文才能正常显示。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    # 注意：不要再用 Toolkit.init_option("./")。
    # maafw 5.14 下它对 "./" 这种带尾斜杠的路径、以及不存在的目录，
    # 都会在 MaaGlobalSetOption 里抛 OSError 0xe06d7363，直接让 agent 退出。
    # 这里先建好目录再设置绝对路径。
    log_dir = _PROJECT_ROOT / "debug"
    log_dir.mkdir(parents=True, exist_ok=True)
    Tasker.set_log_dir(str(log_dir))

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        print("socket_id 由客户端（MaaPiCli / MPE）拉起 Agent 时传入，不用手动运行")
        sys.exit(1)

    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
