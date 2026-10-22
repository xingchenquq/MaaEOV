# -*- coding: utf-8 -*-
"""MFA 统一结构化日志。

设计目标（对应需求：统一各 MFA 组件日志输出规范、便于自动化采集与分析、避免凭证泄露）：

1. 统一格式：每条日志输出为单行 JSON，前缀 [MFA]，字段固定：
     ts      时间戳（ISO8601，含毫秒，本地时区）
     module  组件名（危机行动 / 往期活动 / 自动推图 / SoC / ...）
     event   事件类型（如 ticket_count / sweep_set / battle 等）
     result  操作结果：ok / fail / skip / warn / info
     msg     人类可读信息
     error   可选，错误信息（异常时填）
     ...     其它任意附加字段（count、idx 等）
2. 凭证防护：任何写入日志的字符串若含 token / secret / password / cookie /
   authorization / api_key / access_key 等敏感词或 JWT(sk-/ghp_/eyJ…) 模式，
   由 redact 自动打码，绝不明文落盘。Game 资源（如「调令 ticket 数量」）不属于凭证，不误伤。
3. 同时接管 stdlib logging：configure_stdlib_logging() 给 root logger 装上结构化
   Formatter，使既有 log.info/error/warning 也变成同一 [MFA]{json} 格式，做到组件级统一。
4. 性能：每行 flush，保证 MFA 主程序捕获到。

用法：
    from mfalog import mfa_log, mfa_err, mfa_warn, configure_stdlib_logging
    mfa_log("危机行动", "ticket_count", "ok", "记录到危机行动调令数: 5", count=5)
    mfa_err("危机行动", "ticket_ocr", "读取调令 OCR 结果失败", error=e)
    mfa_warn("危机行动", "ticket_ocr", "调令 OCR 读取失败")
"""

import itertools
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

# ── 敏感字段定义 ────────────────────────────────────────────────────────────
# 仅覆盖真正的凭证类关键词；「ticket / 调令 / session / key(单独)」等游戏/普通词故意排除，
# 避免把正常游戏数值误打码。
_SENSITIVE_KEYS = (
    "token", "secret", "password", "passwd", "pwd", "cookie", "authorization",
    "credential", "private_key", "privatekey", "api_key", "apikey",
    "access_key", "accesskey", "secret_key", "secretkey",
)
# 值级模式：JWT / GitHub / Slack / GCP 等典型凭证前缀
_VAL_RE = re.compile(
    r"(?i)(token|secret|password|passwd|pwd|cookie|authorization|bearer|"
    r"api[-_]?key|access[-_]?key|secret[-_]?key)\s*[:=]\s*(\S+)"
)
#: `Authorization: Bearer <token>` —— `_VAL_RE` 的 `(\S+)` 只吃到 "Bearer"，
#: 真正的凭证残留在后面（由 tests/test_agent_pure.py 暴露）。先单独处理 bearer。
_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+([A-Za-z0-9._~+/=-]{6,})")
_JWT_RE = re.compile(r"(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})")
_PREFIX_RE = re.compile(r"\b(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|ya29\.[A-Za-z0-9_-]{8,})\b")


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def _redact_str(s: str) -> str:
    if not isinstance(s, str):
        return s
    out = _BEARER_RE.sub(lambda m: f"{m.group(1)} ****(redacted)****", s)
    out = _VAL_RE.sub(lambda m: f"{m.group(1)}=****(redacted)****", out)
    out = _JWT_RE.sub("****(redacted-jwt)****", out)
    out = _PREFIX_RE.sub("****(redacted)****", out)
    return out


def _redact(v):
    """递归打码：dict 的敏感 key 整体掩码，其余值字符串做模式打码。"""
    if isinstance(v, str):
        return _redact_str(v)
    if isinstance(v, dict):
        return {
            k: ("****(redacted)****" if any(s in str(k).lower() for s in _SENSITIVE_KEYS) else _redact(v))
            for k, v in v.items()
        }
    if isinstance(v, (list, tuple, set)):
        return [_redact(x) for x in v]
    return v


# Agent 子进程的 stdout 会被 MFA GUI 丢弃（不进 GUI 日志、也不进 maafw.log），
# 因此同步落盘一份到 debug/mfa_agent.log 作为唯一可靠的明细载体；超 5MB 轮转一次。
_LOG_PATH = os.path.join("debug", "mfa_agent.log")
_MAX_LOG_BYTES = 5 * 1024 * 1024

# 进程内自增序号 + 当前任务上下文（由 task_trace 维护，自动并入每条日志）
_SEQ = itertools.count(1)
_CTX: dict = {}


def set_context(**kv) -> None:
    """设置/更新当前任务上下文（task_id / entry / node 等），之后每条日志自动携带。"""
    _CTX.update({k: v for k, v in kv.items() if v is not None})


def clear_context(*keys) -> None:
    """清空上下文；不传参数则全清（任务结束时调用）。"""
    if not keys:
        _CTX.clear()
    for k in keys:
        _CTX.pop(k, None)


def context() -> dict:
    return dict(_CTX)


def _emit(rec: dict) -> None:
    # seq：进程内自增序号，保证同一次运行内可按序还原（多线程/回调乱序时仍能排序）
    rec.setdefault("seq", next(_SEQ))
    # ctx：由 task_trace 维护的「当前任务上下文」（task_id / entry / node），
    # 自动并入每条日志 —— 排查时不必再靠时间戳猜"这条属于哪个任务"。
    for _k, _v in _CTX.items():
        rec.setdefault(_k, _v)
    try:
        line = "[MFA]" + json.dumps(rec, ensure_ascii=False, default=str)
    except Exception:
        line = "[MFA]" + json.dumps({"ts": _now(), "module": "mfalog", "event": "serialize", "result": "fail", "msg": "<unserializable record>"}, ensure_ascii=False)
    # 单行 + 立即 flush，确保 MFA 主程序捕获到每一条
    print(line, flush=True)
    # 落盘（GUI 内看不到 agent stdout，文件是排查的唯一明细来源）
    try:
        os.makedirs(os.path.dirname(_LOG_PATH) or ".", exist_ok=True)
        if os.path.exists(_LOG_PATH) and os.path.getsize(_LOG_PATH) > _MAX_LOG_BYTES:
            os.replace(_LOG_PATH, _LOG_PATH + ".1")
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def mfa_log(module: str, event: str, result: str = "info", msg: str = "", error=None, **extra) -> None:
    """主接口：输出一条结构化日志。

    result 取值建议：ok / fail / skip / warn / info。
    error 为异常/错误对象时自动转 str 并打码；extra 任意附加字段（如 count/idx）。
    """
    rec = {
        "ts": _now(),
        "module": module,
        "event": event,
        "result": result,
        "msg": _redact_str(msg) if isinstance(msg, str) else ("" if msg is None else str(msg)),
    }
    if error is not None:
        rec["error"] = _redact_str(str(error))
    if extra:
        rec.update(_redact(extra))
    _emit(rec)


def mfa_err(module: str, event: str, msg: str = "", error=None, **extra) -> None:
    mfa_log(module, event, "fail", msg, error=error, **extra)


def mfa_warn(module: str, event: str, msg: str = "", **extra) -> None:
    mfa_log(module, event, "warn", msg, **extra)


# ── 接管 stdlib logging ───────────────────────────────────────────────────────
class _StructFormatter(logging.Formatter):
    """把 logging 记录转成与 mfa_log 同形的 [MFA]{json}。"""

    # 把 stdlib 级别词统一到我们的结果词表，避免 info/warning/error 与 ok/fail/skip/warn 混用
    _LEVEL_TO_RESULT = {
        "critical": "fail",
        "error": "fail",
        "exception": "fail",
        "warning": "warn",
    }

    def format(self, record: logging.LogRecord) -> str:
        result = self._LEVEL_TO_RESULT.get(record.levelname.lower(), record.levelname.lower())
        rec = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            "module": record.name,
            "event": "log",
            "result": result,
            "msg": _redact_str(record.getMessage()),
        }
        if record.exc_info:
            rec["error"] = _redact_str(self.formatException(record.exc_info))
        return "[MFA]" + json.dumps(rec, ensure_ascii=False, default=str)


_configured = False


def configure_stdlib_logging(level: int = logging.INFO) -> None:
    """给 root logger 装结构化 handler，使既有 log.info/error/warning 统一为 [MFA]{json}。

    幂等：重复调用只配置一次。
    """
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StructFormatter())
    # 防止与 MaaFW 自身 handler 重复：仅在我们还没加过时才加
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, _StructFormatter) for h in root.handlers):
        root.addHandler(handler)
    # stdlib 日志同样落盘到 debug/mfa_agent.log（MaaFW 内部 log.info 等在 GUI 下不可见）
    try:
        os.makedirs("debug", exist_ok=True)
        _fh = logging.FileHandler(_LOG_PATH, encoding="utf-8")
        _fh.setFormatter(_StructFormatter())
        root.addHandler(_fh)
    except Exception:
        pass
    # 关闭 propagation 噪音：保留 MaaFW 自己的 logger 输出，只是统一格式
