import sys
import io
from functools import wraps

class StdoutCapture(io.StringIO):
    def __enter__(self):
        # 保存原始的 stdout (终端输出)
        self._original_stdout = sys.stdout
        # 将 sys.stdout 替换为当前对象 (self)
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出时，先保存捕获的内容
        self.captured = self.getvalue()
        # 恢复原始的 stdout
        sys.stdout = self._original_stdout

    def write(self, data):
        # 1. 写入内存 (StringIO 的原始功能，用于后续捕获)
        super().write(data)
        
        # 2. 同时写入原始 stdout (确保终端能看到)
        if self._original_stdout:
            self._original_stdout.write(data)
            # 建议立即 flush，防止打印延迟
            self._original_stdout.flush()

    # 最好也覆盖 flush 方法，确保行为一致
    def flush(self):
        super().flush()
        if self._original_stdout:
            self._original_stdout.flush()


def node_wrapper(node_func):
    """
    统一封装所有节点：
    - 捕获 print 输出同时在终端显示
    - 自动塞进 state['stdout']
    - 自动塞入 state['node'] = 节点名
    """
    @wraps(node_func)
    def wrapped(state, *args, **kwargs):
        # 使用修改后的 StdoutCapture
        with StdoutCapture() as cap:
            result = node_func(state, *args, **kwargs)

        # 确保 result 是 dict
        if not isinstance(result, dict):
            result = {"result": result}

        # 加入 stdout 输出 (从 cap.captured 获取)
        result["stdout"] = cap.captured

        # 加上节点名，便于前端显示
        result["node"] = node_func.__name__

        return result

    return wrapped