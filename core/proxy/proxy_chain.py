# -*- coding: utf-8 -*-
"""
链式代理中转模块

Chrome 的 --proxy-server 只支持单层代理，无法表达
"先走系统代理出墙，再走海外住宅代理" 这种链式结构。

本模块在本地启动一个轻量级 HTTP CONNECT 中转服务：

    Chrome ──► 127.0.0.1:本地端口 (本模块) ──► 上游代理 ──► 下游代理 ──► 目标

实现方式：标准的 HTTP CONNECT 隧道嵌套。
1. Chrome 发 `CONNECT target:port HTTP/1.1` 给本中转
2. 本中转 TCP 连上游代理，发 `CONNECT 下游host:下游port HTTP/1.1`
3. 上游回 200 后，TCP 隧道实际通到了下游代理
4. 本中转再通过此隧道发 `CONNECT target:port HTTP/1.1` （加下游鉴权）
5. 下游回 200 后，整条链路打通
6. 本中转回 Chrome 200，开始双向 pipe 数据
"""
from __future__ import annotations

import asyncio
import base64
import socket
import threading
from typing import Optional

from utils.logger import logger
from .proxy_manager import ProxyConfig


def _basic_auth_header(username: Optional[str], password: Optional[str]) -> Optional[str]:
    """生成 Proxy-Authorization 头的值，无认证时返回 None"""
    if not username:
        return None
    raw = f"{username}:{password or ''}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _build_connect_request(target_host: str, target_port: int,
                           auth_header_value: Optional[str]) -> bytes:
    """构造一条 CONNECT 请求"""
    lines = [
        f"CONNECT {target_host}:{target_port} HTTP/1.1",
        f"Host: {target_host}:{target_port}",
        "Proxy-Connection: Keep-Alive",
        "User-Agent: ChainProxy/1.0",
    ]
    if auth_header_value:
        lines.append(f"Proxy-Authorization: {auth_header_value}")
    lines.append("")
    lines.append("")
    return ("\r\n".join(lines)).encode("ascii")


async def _read_http_status_line(reader: asyncio.StreamReader, timeout: float = 15.0) -> tuple[int, str]:
    """读完一段 HTTP 响应（直到 \\r\\n\\r\\n），返回 (status_code, raw_response)"""
    data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=timeout)
    text = data.decode("iso-8859-1", errors="replace")
    first_line = text.split("\r\n", 1)[0]
    parts = first_line.split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError(f"非法 HTTP 响应: {first_line!r}")
    return int(parts[1]), text


async def _safe_close(writer: Optional[asyncio.StreamWriter]) -> None:
    if writer is None:
        return
    try:
        if not writer.is_closing():
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    except Exception:
        pass


async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter, name: str) -> None:
    """单向数据转发，遇到 EOF 或错误时退出"""
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        logger.debug(f"[chain-proxy] {name} pipe 异常: {e}")
    finally:
        try:
            if dst.can_write_eof():
                dst.write_eof()
        except Exception:
            pass


# ============================== SOCKS5 协议辅助 ==============================
# RFC 1928 (SOCKS5) + RFC 1929 (Username/Password Auth)
#
# 阶段 1：方法协商
#   C → S:  VER(0x05) NMETHODS METHOD[1..]
#   S → C:  VER(0x05) METHOD            (0x00=无认证, 0x02=用户名密码, 0xFF=拒绝)
# 阶段 2：用户名/密码认证（仅 METHOD=0x02）
#   C → S:  0x01 ULEN USER PLEN PASS
#   S → C:  0x01 STATUS                 (0x00=成功)
# 阶段 3：CONNECT 命令
#   C → S:  VER(0x05) CMD(0x01) RSV(0x00) ATYP DST.ADDR DST.PORT
#   S → C:  VER(0x05) REP RSV ATYP BND.ADDR BND.PORT  (REP=0x00 即成功)

_SOCKS5_REP_MSG = {
    0x01: "general SOCKS server failure",
    0x02: "connection not allowed by ruleset",
    0x03: "Network unreachable",
    0x04: "Host unreachable",
    0x05: "Connection refused",
    0x06: "TTL expired",
    0x07: "Command not supported",
    0x08: "Address type not supported",
}


async def _socks5_open(reader: asyncio.StreamReader,
                       writer: asyncio.StreamWriter,
                       target_host: str,
                       target_port: int,
                       username: Optional[str],
                       password: Optional[str],
                       timeout: float) -> None:
    """
    在已建立的 TCP 流（必须已经通到 SOCKS5 服务器）上完成
    SOCKS5 握手 + 可选用户名/密码鉴权 + CONNECT 到目标。

    成功返回时，writer / reader 这条流就是一条到 target 的透明字节通道。
    任何协议层错误一律抛 IOError。
    """
    # ---------- 阶段 1：方法协商 ----------
    if username:
        # 同时支持无认证和用户名密码两种方法，让服务端选
        writer.write(b"\x05\x02\x00\x02")
    else:
        writer.write(b"\x05\x01\x00")
    await writer.drain()

    greet_resp = await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
    if greet_resp[0] != 0x05:
        raise IOError(f"SOCKS5: 非 v5 响应 (ver=0x{greet_resp[0]:02x})")
    method = greet_resp[1]
    if method == 0xFF:
        raise IOError("SOCKS5: 服务器拒绝所有认证方法")

    # ---------- 阶段 2：用户名/密码鉴权 ----------
    if method == 0x02:
        if not username:
            raise IOError("SOCKS5: 服务器要求用户名密码认证，但未提供凭据")
        u_bytes = username.encode("utf-8")
        p_bytes = (password or "").encode("utf-8")
        if len(u_bytes) > 255 or len(p_bytes) > 255:
            raise IOError("SOCKS5: 用户名或密码超过 255 字节")
        auth_pkt = (
            b"\x01"
            + bytes([len(u_bytes)]) + u_bytes
            + bytes([len(p_bytes)]) + p_bytes
        )
        writer.write(auth_pkt)
        await writer.drain()

        auth_resp = await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
        if auth_resp[0] != 0x01:
            raise IOError(f"SOCKS5: 非法的认证子协议响应 ver=0x{auth_resp[0]:02x}")
        if auth_resp[1] != 0x00:
            raise IOError(f"SOCKS5: 用户名/密码认证失败 status=0x{auth_resp[1]:02x}")
    elif method == 0x00:
        # 无认证，直接进入 CONNECT 阶段
        pass
    else:
        raise IOError(f"SOCKS5: 服务器选择了不支持的方法 0x{method:02x}")

    # ---------- 阶段 3：CONNECT 命令 ----------
    # 简单起见，目标地址统一以域名(0x03)形式发送，让 SOCKS5 服务端自己解析
    host_bytes = target_host.encode("idna") if any(ord(c) > 127 for c in target_host) \
        else target_host.encode("ascii", errors="strict")
    if len(host_bytes) > 255:
        raise IOError("SOCKS5: 目标域名超过 255 字节")

    connect_pkt = (
        b"\x05\x01\x00\x03"
        + bytes([len(host_bytes)]) + host_bytes
        + target_port.to_bytes(2, "big")
    )
    writer.write(connect_pkt)
    await writer.drain()

    head = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
    if head[0] != 0x05:
        raise IOError(f"SOCKS5 reply: invalid version 0x{head[0]:02x}")
    rep = head[1]
    if rep != 0x00:
        msg = _SOCKS5_REP_MSG.get(rep, f"unknown rep=0x{rep:02x}")
        raise IOError(f"SOCKS5 CONNECT 失败：{msg}")

    atyp = head[3]
    # 把 BND.ADDR + BND.PORT 读完丢弃
    if atyp == 0x01:                          # IPv4
        await asyncio.wait_for(reader.readexactly(4 + 2), timeout=timeout)
    elif atyp == 0x03:                        # 域名
        ln_byte = await asyncio.wait_for(reader.readexactly(1), timeout=timeout)
        await asyncio.wait_for(reader.readexactly(ln_byte[0] + 2), timeout=timeout)
    elif atyp == 0x04:                        # IPv6
        await asyncio.wait_for(reader.readexactly(16 + 2), timeout=timeout)
    else:
        raise IOError(f"SOCKS5: 未知地址类型 0x{atyp:02x}")


class ChainedProxyServer:
    """
    本地 HTTP CONNECT 链式中转代理。

    用法：
        server = ChainedProxyServer(upstream, downstream)
        server.start()                  # 阻塞直到监听就绪
        proxy_url = server.local_url    # http://127.0.0.1:xxxxx
        ...
        server.stop()                   # 关闭

    线程模型：
        - 在独立后台线程跑 asyncio event loop
        - start() / stop() 在调用方线程同步等待 loop 就绪/退出
    """

    def __init__(self,
                 upstream: ProxyConfig,
                 downstream: ProxyConfig,
                 bind_host: str = "127.0.0.1",
                 connect_timeout: float = 15.0):
        self._upstream = upstream
        self._downstream = downstream
        self._bind_host = bind_host
        self._connect_timeout = connect_timeout

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[asyncio.AbstractServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port: Optional[int] = None
        self._ready_event = threading.Event()
        self._stop_event = threading.Event()
        self._start_error: Optional[BaseException] = None

    # ---------- 公共 API ----------

    @property
    def port(self) -> int:
        if self._port is None:
            raise RuntimeError("ChainedProxyServer 尚未启动")
        return self._port

    @property
    def local_url(self) -> str:
        return f"http://{self._bind_host}:{self.port}"

    def start(self) -> None:
        """启动监听，阻塞直到端口就绪"""
        if self._thread and self._thread.is_alive():
            return

        self._ready_event.clear()
        self._stop_event.clear()
        self._start_error = None

        self._thread = threading.Thread(
            target=self._thread_main,
            name="ChainedProxyServer",
            daemon=True,
        )
        self._thread.start()

        # 等待启动结果
        if not self._ready_event.wait(timeout=10.0):
            self.stop()
            raise RuntimeError("ChainedProxyServer 启动超时")
        if self._start_error is not None:
            err = self._start_error
            self._start_error = None
            raise err

        logger.info(
            f"🔗 链式代理已启动: {self.local_url} "
            f"→ 上游 {self._upstream.host}:{self._upstream.port} "
            f"→ 下游 {self._downstream.host}:{self._downstream.port}"
        )

    def stop(self) -> None:
        """停止服务并等待线程退出"""
        if not self._thread:
            return
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._stop_event.set)
            loop.call_soon_threadsafe(self._shutdown_server)
        self._thread.join(timeout=5.0)
        self._thread = None
        self._loop = None
        self._server = None
        self._port = None
        logger.info("🔗 链式代理已关闭")

    # ---------- 线程主体 ----------

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._serve())
        except Exception as e:
            self._start_error = e
            self._ready_event.set()
        finally:
            try:
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                for t in pending:
                    t.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass

    def _shutdown_server(self) -> None:
        if self._server is not None:
            self._server.close()

    async def _serve(self) -> None:
        try:
            server = await asyncio.start_server(
                self._handle_client,
                host=self._bind_host,
                port=0,           # 让 OS 分配可用端口
                family=socket.AF_INET,
            )
        except Exception as e:
            self._start_error = e
            self._ready_event.set()
            return

        self._server = server
        sockets = server.sockets or []
        if not sockets:
            self._start_error = RuntimeError("无法获取本地端口")
            self._ready_event.set()
            return
        self._port = sockets[0].getsockname()[1]
        self._ready_event.set()

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"[chain-proxy] serve_forever 退出: {e}")

    # ---------- 单连接处理 ----------

    async def _handle_client(self,
                             client_reader: asyncio.StreamReader,
                             client_writer: asyncio.StreamWriter) -> None:
        peer = client_writer.get_extra_info("peername")
        upstream_writer: Optional[asyncio.StreamWriter] = None
        try:
            # 1. 解析 Chrome 发来的请求行 + 头部
            try:
                head_data = await asyncio.wait_for(
                    client_reader.readuntil(b"\r\n\r\n"),
                    timeout=self._connect_timeout,
                )
            except asyncio.IncompleteReadError as e:
                head_data = e.partial
            except asyncio.TimeoutError:
                logger.debug(f"[chain-proxy] 客户端 {peer} 请求头读取超时")
                return

            head_text = head_data.decode("iso-8859-1", errors="replace")
            first_line = head_text.split("\r\n", 1)[0]
            parts = first_line.split(" ")
            if len(parts) < 3:
                await self._reply_and_close(client_writer, 400, "Bad Request")
                return

            method, target, _version = parts[0], parts[1], parts[2]
            method_u = method.upper()

            # 解析目标 host:port + 决定后续模式
            #   CONNECT 模式：HTTPS / WSS，建立隧道后直接 pipe，不需要改写请求
            #   明文 HTTP 模式：GET/POST/... + 绝对 URL，需要改写请求头为相对路径
            rewritten_head: Optional[bytes] = None

            if method_u == "CONNECT":
                if ":" not in target:
                    await self._reply_and_close(client_writer, 400, "Bad Request")
                    return
                target_host, target_port_str = target.rsplit(":", 1)
                try:
                    target_port = int(target_port_str)
                except ValueError:
                    await self._reply_and_close(client_writer, 400, "Bad Request")
                    return
            else:
                # 明文 HTTP：必须是绝对 URL（HTTP 代理协议要求）
                if "://" not in target:
                    logger.warning(
                        f"[chain-proxy] 非 CONNECT 请求但 target 不是绝对 URL: {method} {target}"
                    )
                    await self._reply_and_close(client_writer, 400, "Bad Request: absolute URL required")
                    return
                try:
                    from urllib.parse import urlsplit
                    parsed = urlsplit(target)
                    target_host = parsed.hostname or ""
                    target_port = parsed.port or (443 if parsed.scheme == "https" else 80)
                except Exception:
                    await self._reply_and_close(client_writer, 400, "Bad Request: cannot parse URL")
                    return
                if not target_host:
                    await self._reply_and_close(client_writer, 400, "Bad Request: no host")
                    return

                # 重写请求头：把 "GET http://host:port/path?q HTTP/1.1" 改成 "GET /path?q HTTP/1.1"
                # 同时去掉 Proxy-Connection / Proxy-Authorization 这些只给代理看的头
                relative_path = parsed.path or "/"
                if parsed.query:
                    relative_path += "?" + parsed.query

                new_lines = []
                for idx, line in enumerate(head_text.split("\r\n")):
                    if idx == 0:
                        new_lines.append(f"{method} {relative_path} HTTP/1.1")
                    elif line == "":
                        new_lines.append("")
                    else:
                        lower = line.lower()
                        if lower.startswith("proxy-connection:") or lower.startswith("proxy-authorization:"):
                            continue
                        new_lines.append(line)
                rewritten_head = "\r\n".join(new_lines).encode("iso-8859-1")

            # 2. 连上游代理
            try:
                upstream_reader, upstream_writer = await asyncio.wait_for(
                    asyncio.open_connection(self._upstream.host, self._upstream.port),
                    timeout=self._connect_timeout,
                )
            except Exception as e:
                logger.warning(f"[chain-proxy] 连接上游代理失败: {e}")
                await self._reply_and_close(client_writer, 502, "Upstream Connect Failed")
                return

            # 3. 通过上游 CONNECT 到下游代理（建立 TCP 隧道，与下游协议无关）
            up_auth = _basic_auth_header(self._upstream.username, self._upstream.password)
            req1 = _build_connect_request(self._downstream.host, self._downstream.port, up_auth)
            upstream_writer.write(req1)
            await upstream_writer.drain()

            try:
                status1, raw1 = await _read_http_status_line(upstream_reader, self._connect_timeout)
            except Exception as e:
                logger.warning(f"[chain-proxy] 读上游 CONNECT 响应失败: {e}")
                await self._reply_and_close(client_writer, 502, "Upstream Bad Response")
                return

            if status1 != 200:
                logger.warning(
                    f"[chain-proxy] 上游 CONNECT 到下游失败 status={status1}, "
                    f"resp={raw1.splitlines()[0] if raw1 else ''}"
                )
                await self._reply_and_close(client_writer, 502, f"Upstream {status1}")
                return

            # 4. 在已建立的隧道上完成"下游代理 → 目标"这一跳
            #    根据下游代理协议分流：HTTP CONNECT 嵌套 / SOCKS5 二进制握手
            down_proto = (self._downstream.protocol or "http").lower()

            if down_proto in ("http", "https"):
                down_auth = _basic_auth_header(self._downstream.username, self._downstream.password)
                req2 = _build_connect_request(target_host, target_port, down_auth)
                upstream_writer.write(req2)
                await upstream_writer.drain()

                try:
                    status2, raw2 = await _read_http_status_line(upstream_reader, self._connect_timeout)
                except Exception as e:
                    logger.warning(f"[chain-proxy] 读下游 CONNECT 响应失败: {e}")
                    await self._reply_and_close(client_writer, 502, "Downstream Bad Response")
                    return

                if status2 != 200:
                    logger.warning(
                        f"[chain-proxy] 下游 HTTP CONNECT 到目标失败 status={status2}, "
                        f"target={target}, resp={raw2.splitlines()[0] if raw2 else ''}"
                    )
                    await self._reply_and_close(client_writer, 502, f"Downstream {status2}")
                    return

            elif down_proto in ("socks5", "socks5h", "socks"):
                try:
                    await _socks5_open(
                        upstream_reader, upstream_writer,
                        target_host, target_port,
                        self._downstream.username, self._downstream.password,
                        self._connect_timeout,
                    )
                except Exception as e:
                    logger.warning(f"[chain-proxy] SOCKS5 握手/鉴权/CONNECT 失败: {e}")
                    await self._reply_and_close(client_writer, 502, "SOCKS5 Handshake Failed")
                    return

            else:
                logger.warning(f"[chain-proxy] 不支持的下游协议: {down_proto}")
                await self._reply_and_close(client_writer, 502, "Unsupported Downstream Protocol")
                return

            # 5. CONNECT 模式回 Chrome 200；明文 HTTP 模式直接把改写过的请求头送进隧道
            if method_u == "CONNECT":
                client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await client_writer.drain()
            else:
                # 把改写后的请求头送进隧道（隧道另一端是目标服务器）
                if rewritten_head is not None:
                    upstream_writer.write(rewritten_head)
                    await upstream_writer.drain()

            # 6. 双向 pipe
            await asyncio.gather(
                _pipe(client_reader, upstream_writer, "c2u"),
                _pipe(upstream_reader, client_writer, "u2c"),
            )

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.debug(f"[chain-proxy] 处理客户端 {peer} 异常: {e}")
        finally:
            await _safe_close(upstream_writer)
            await _safe_close(client_writer)

    @staticmethod
    async def _reply_and_close(writer: asyncio.StreamWriter, code: int, reason: str) -> None:
        try:
            writer.write(f"HTTP/1.1 {code} {reason}\r\nContent-Length: 0\r\n\r\n".encode("ascii"))
            await writer.drain()
        except Exception:
            pass
        await _safe_close(writer)


__all__ = ["ChainedProxyServer"]
