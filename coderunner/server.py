"""Iga code runner: compiles and runs students' C++ and Java programs, like a real terminal.

Only the Django backend talks to it, on an internal Docker network with no internet access, with a shared
token. Each program runs in a fresh folder as its slot's own unprivileged user, with CPU, memory, process,
file-size and output limits, and is killed with everything it started when it ends or times out.

A session runs until the program finishes or waits for keyboard input. The program's stdin is a pipe;
when every thread of the program is blocked reading it (seen in /proc/<pid>/task/*/syscall) and nothing is
left in the pipe, the session pauses and returns the output so far. Every process of the slot is then
stopped (SIGSTOP), so nothing it started can use the CPU while the student thinks. The student's answer is
written to the pipe, the processes continue (SIGCONT) and the program goes on.

Each step result says how much CPU time the step used ("cpu_ms": compiling, and the program with every
process it started, as the kernel counts it), so Django can keep each student's daily CPU allowance.

API (JSON over HTTP, header "Authorization: Bearer <CODE_RUNNER_TOKEN>"):
    GET  /health                          -> {"ok": true, "languages": [...], "slots": n, "busy": n}
    POST /run    {"language", "code"}     -> step result
    POST /input  {"session", "text"}      -> step result
    POST /stop   {"session"}              -> {"stopped": true}
Step result: {"session", "state": "waiting"|"finished", "output": [{"stream", "text"}], "cpu_ms",
              "verdict": "ok"|"compile_error"|"runtime_error"|"time_limit"|"output_limit"|"busy", "exit_code", "signal"}
"""

import fcntl
import hmac
import json
import os
import platform
import re
import secrets
import shutil
import signal
import struct
import subprocess
import termios
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("CODE_RUNNER_TOKEN", "")
SLOTS = min(int(os.environ.get("CODE_RUNNER_SLOTS", "4")), 8)  # the image has users job1..job8
BASE_UID = 2000
WORK_ROOT = os.environ.get("CODE_RUNNER_WORK", "/tmp/jobs")

MAX_CODE = 20_000
MAX_INPUT = 4_000
MAX_BODY = 64 * 1024
OUTPUT_LIMIT = 64 * 1024  # bytes of stdout + stderr per session
COMPILE_SECONDS = 30  # wall clock
STEP_SECONDS = float(os.environ.get("CODE_RUNNER_STEP_SECONDS", "10"))  # to finish or ask for input
RUN_CPU_SECONDS = 10  # CPU time for the whole program
IDLE_SECONDS = float(os.environ.get("CODE_RUNNER_IDLE_SECONDS", "120"))  # waiting for the student's answer
SESSION_SECONDS = 600
READ_SYSCALL = {"x86_64": 0, "aarch64": 63}.get(platform.machine())
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")

JVM = ["-Xmx256m", "-Xss16m", "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1", "-XX:CICompilerCount=1",
       "-XX:ReservedCodeCacheSize=32m", "-XX:MaxMetaspaceSize=128m", "-XX:CompressedClassSpaceSize=64m",
       "-XX:-UsePerfData", "-Xshare:auto", "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8"]

GB = 1024**3
MB = 1024**2


def _java_names(code):
    """(file name, class to run): a public class decides the file name; main() decides what to run."""
    public = re.search(r"\bpublic\s+(?:(?:final|abstract)\s+)*class\s+([A-Za-z_]\w*)", code)
    main_at = re.search(r"\bstatic\s+(?:final\s+)?void\s+main\s*\(", code)
    to_run = "Main"
    if main_at:
        before = [m.group(1) for m in re.finditer(r"\b(?:class|record|enum|interface)\s+([A-Za-z_]\w*)", code[: main_at.start()])]
        if before:
            to_run = before[-1]
    file_name = f"{public.group(1)}.java" if public else f"{to_run}.java"
    return file_name, to_run


LANGUAGES = {
    "cpp": {
        "files": lambda code: ("main.cpp", None),
        "compile": lambda f, c: ["g++", "-std=c++17", "-O1", "-pipe", "-o", "main", f],
        "run": lambda f, c: ["./main"],
        "compile_limits": {"as": 2 * GB, "nproc": 32, "cpu": 20},
        "run_limits": {"as": 512 * MB, "nproc": 32, "cpu": RUN_CPU_SECONDS},
    },
    "java": {
        "files": _java_names,
        "compile": lambda f, c: ["javac", "-J-Xmx384m", "-J-XX:+UseSerialGC", "-J-XX:TieredStopAtLevel=1", "-J-XX:-UsePerfData",
                                 "-J-XX:CompressedClassSpaceSize=64m", "-encoding", "UTF-8", "-Xlint:none", f],
        "run": lambda f, c: ["java", *JVM, "-cp", ".", c],
        "compile_limits": {"as": 4 * GB, "nproc": 128, "cpu": 25},
        "run_limits": {"as": 4 * GB, "nproc": 128, "cpu": RUN_CPU_SECONDS},
    },
}


def limited(cmd, limits):
    """Wrap a command with prlimit so it runs with CPU, memory, process, file and core-dump limits."""
    return [
        "prlimit",
        f"--cpu={limits['cpu']}:{limits['cpu'] + 1}",
        f"--as={limits['as']}",
        f"--nproc={limits['nproc']}",
        f"--fsize={8 * MB}",
        "--nofile=64",
        "--core=0",
        "--",
        *cmd,
    ]


def _pids_of(uid, zombies=False):
    pids = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/status") as status:
                fields = dict(line.split(":", 1) for line in status if ":" in line)
            if int(fields["Uid"].split()[0]) == uid and (zombies or fields["State"].split()[0] != "Z"):
                pids.append(int(pid))
        except (OSError, KeyError, ValueError, IndexError):
            pass
    return pids


def cpu_of(pids):
    """CPU seconds the processes have used, with the children they have waited for (/proc/<pid>/stat)."""
    total = 0
    for pid in pids:
        try:
            with open(f"/proc/{pid}/stat") as stat:
                fields = stat.read().rsplit(")", 1)[1].split()
            total += sum(int(value) for value in fields[11:15])  # utime, stime, cutime, cstime
        except (OSError, ValueError, IndexError):
            pass
    return total / CLOCK_TICKS


def signal_user(uid, sig):
    for pid in _pids_of(uid):
        try:
            os.kill(pid, sig)
        except OSError:
            pass


def kill_user(uid):
    """Kill every process that runs as this slot's user, including any the program started (a program that
    keeps forking needs several sweeps). Dead processes are reaped by the container's init (tini)."""
    for _ in range(50):
        pids = _pids_of(uid)
        if not pids:
            return
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.02)


class Session:
    def __init__(self, slot, language, code):
        self.id = secrets.token_urlsafe(16)
        self.slot = slot
        self.uid = BASE_UID + slot
        self.language = language
        self.spec = LANGUAGES[language]
        self.code = code
        self.dir = os.path.join(WORK_ROOT, self.id)
        self.started = self.touched = time.monotonic()
        self.lock = threading.Lock()
        self.chunks = []  # (stream, text) not yet returned
        self.chunks_lock = threading.Lock()
        self.output_bytes = 0
        self.truncated = False
        self.proc = None
        self.stdin_w = self.stdin_r = None
        self.finished = False
        self.paused = False
        # CPU seconds: of processes that have ended and been waited for (the compiler, the program), the
        # highest total seen so far, and how much of it the steps have reported.
        self.cpu_done = 0.0
        self.cpu_seen = 0.0
        self.cpu_reported = 0.0

    # --- files and processes -------------------------------------------------------------------------
    def prepare(self):
        file_name, self.main_class = self.spec["files"](self.code)
        self.file_name = file_name
        os.makedirs(self.dir, mode=0o700)
        os.chown(self.dir, self.uid, self.uid)
        path = os.path.join(self.dir, file_name)
        with open(path, "w", encoding="utf-8") as source:
            source.write(self.code)
        os.chown(path, self.uid, self.uid)

    def popen(self, cmd, limits, stdin):
        env = {"PATH": os.environ["PATH"], "HOME": self.dir, "LANG": "C.UTF-8", "JAVA_HOME": os.environ.get("JAVA_HOME", "")}
        return subprocess.Popen(
            limited(cmd, limits),
            cwd=self.dir,
            env=env,
            user=self.uid,
            group=self.uid,
            extra_groups=[],
            process_group=0,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )

    def reap(self, proc, timeout):
        """Wait up to `timeout` seconds (None: as long as it takes) for `proc` to end, and add the CPU time it
        and the children it waited for used. False while it is still running."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while proc.returncode is None:
            try:
                pid, status, usage = os.wait4(proc.pid, 0 if deadline is None else os.WNOHANG)
            except ChildProcessError:
                break
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                self.cpu_done += usage.ru_utime + usage.ru_stime
                break
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.02)
        return True

    def take_cpu_ms(self):
        """CPU milliseconds used since the last step: the processes that ended, and those still alive."""
        self.cpu_seen = max(self.cpu_seen, self.cpu_done + cpu_of(_pids_of(self.uid, zombies=True)))
        ms = int((self.cpu_seen - self.cpu_reported) * 1000)
        self.cpu_reported += ms / 1000
        return ms

    def compile(self):
        """Returns None when it compiled, else the compiler's messages."""
        proc = self.popen(self.spec["compile"](self.file_name, self.main_class), self.spec["compile_limits"], subprocess.DEVNULL)
        out, err = [], []
        readers = [
            threading.Thread(target=lambda pipe=pipe, into=into: into.append(pipe.read()), daemon=True)
            for pipe, into in ((proc.stdout, out), (proc.stderr, err))
        ]
        for reader in readers:
            reader.start()
        in_time = self.reap(proc, COMPILE_SECONDS)
        if not in_time:
            self.kill_group(proc)
            self.reap(proc, None)
        for reader in readers:
            reader.join(5)
        for pipe, reader in zip((proc.stdout, proc.stderr), readers):
            if not reader.is_alive():
                pipe.close()
        if not in_time:
            return "Compiling took too long."
        if proc.returncode == 0:
            return None
        text = b"".join(err).decode("utf-8", "replace") + b"".join(out).decode("utf-8", "replace")
        return text[:OUTPUT_LIMIT] or f"The compiler stopped (code {proc.returncode})."

    def start(self):
        self.stdin_r, self.stdin_w = os.pipe()
        try:
            self.proc = self.popen(self.spec["run"](self.file_name, self.main_class), self.spec["run_limits"], self.stdin_r)
        except Exception:
            os.close(self.stdin_w)
            self.stdin_w = None
            raise
        for pipe, stream in ((self.proc.stdout, "stdout"), (self.proc.stderr, "stderr")):
            threading.Thread(target=self._read, args=(pipe, stream), daemon=True).start()

    def _read(self, pipe, stream):
        fd = pipe.fileno()
        while True:
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            with self.chunks_lock:
                room = OUTPUT_LIMIT - self.output_bytes
                if room <= 0:
                    self.truncated = True
                    continue
                if len(data) > room:
                    data = data[:room]
                    self.truncated = True
                self.output_bytes += len(data)
                self.chunks.append((stream, data))
            if self.truncated:
                self.kill_group(self.proc)
        pipe.close()

    def take_output(self):
        with self.chunks_lock:
            chunks, self.chunks = self.chunks, []
        merged = []
        for stream, data in chunks:
            if merged and merged[-1][0] == stream:
                merged[-1] = (stream, merged[-1][1] + data)
            else:
                merged.append((stream, data))
        return [{"stream": s, "text": d.decode("utf-8", "replace")} for s, d in merged]

    def kill_group(self, proc):
        if proc and proc.returncode is None:  # not waited for yet, so its process group is still its own
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass

    def cleanup(self):
        self.finished = True
        self.kill_group(self.proc)
        kill_user(self.uid)  # stopped (paused) processes die too
        for fd in (self.stdin_w, self.stdin_r):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self.stdin_w = self.stdin_r = None
        shutil.rmtree(self.dir, ignore_errors=True)

    # --- waiting for input ---------------------------------------------------------------------------
    def _unread_input(self):
        buf = fcntl.ioctl(self.stdin_r, termios.FIONREAD, struct.pack("i", 0))
        return struct.unpack("i", buf)[0]

    def waiting_for_input(self):
        """True when the program is blocked reading stdin and every line sent so far has been read."""
        if self._unread_input():
            return False
        try:
            tasks = os.listdir(f"/proc/{self.proc.pid}/task")
        except OSError:
            return False
        for task in tasks:
            try:
                with open(f"/proc/{self.proc.pid}/task/{task}/syscall") as f:
                    fields = f.read().split()
            except OSError:
                continue
            if len(fields) >= 2 and fields[0].isdigit() and int(fields[0]) == READ_SYSCALL and int(fields[1], 16) == 0:
                return True
        return False

    def _output_pending(self):
        total = 0
        for pipe in (self.proc.stdout, self.proc.stderr):
            try:
                total += struct.unpack("i", fcntl.ioctl(pipe.fileno(), termios.FIONREAD, struct.pack("i", 0)))[0]
            except (OSError, ValueError):
                pass
        return total

    def pause(self):
        """Stop every process of the slot while the program waits for the student's answer."""
        signal_user(self.uid, signal.SIGSTOP)
        self.paused = True
        # Let the reader threads collect what the program wrote before it asked.
        deadline = time.monotonic() + 0.5
        while self._output_pending() and time.monotonic() < deadline:
            time.sleep(0.01)
        time.sleep(0.02)

    def resume(self):
        if self.paused:
            signal_user(self.uid, signal.SIGCONT)
            self.paused = False

    def step(self):
        """Run until the program ends, waits for input, or hits a limit."""
        deadline = time.monotonic() + STEP_SECONDS
        while True:
            if self.reap(self.proc, 0):
                time.sleep(0.05)  # let the reader threads collect the last output
                return self._finished(self.proc.returncode)
            if self.truncated:
                self.kill_group(self.proc)
                self.reap(self.proc, None)
                return self._finished(self.proc.returncode, verdict="output_limit")
            if self.waiting_for_input():
                self.pause()
                self.touched = time.monotonic()
                return {"session": self.id, "state": "waiting", "output": self.take_output(), "cpu_ms": self.take_cpu_ms()}
            if time.monotonic() > deadline:
                self.kill_group(self.proc)
                self.reap(self.proc, None)
                return self._finished(self.proc.returncode, verdict="time_limit")
            time.sleep(0.02)

    def _finished(self, code, verdict=None):
        output = self.take_output()
        sig = None
        if code is not None and code < 0:
            sig = signal.Signals(-code).name if -code in signal.Signals._value2member_map_ else str(-code)
        if verdict is None:
            if sig == "SIGXCPU":  # used up its CPU time
                verdict = "time_limit"
            elif code == 0:
                verdict = "ok"
            else:
                verdict = "runtime_error"
        cpu_ms = self.take_cpu_ms()  # with anything the program left running, before it is killed
        self.cleanup()
        return {
            "session": self.id,
            "state": "finished",
            "output": output,
            "verdict": verdict,
            "exit_code": code,
            "signal": sig,
            "cpu_ms": cpu_ms,
        }

    def send(self, text):
        self.resume()
        os.write(self.stdin_w, (text + "\n").encode("utf-8"))


class Runner:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions = {}
        os.makedirs(WORK_ROOT, mode=0o711, exist_ok=True)
        threading.Thread(target=self._reap, daemon=True).start()

    def busy(self):
        with self.lock:
            return len(self.sessions)

    def _free_slot(self):
        used = {s.slot for s in self.sessions.values()}
        return next((slot for slot in range(1, SLOTS + 1) if slot not in used), None)

    def run(self, language, code):
        with self.lock:
            slot = self._free_slot()
            if slot is None:
                return {"state": "finished", "verdict": "busy", "output": []}
            session = Session(slot, language, code)
            self.sessions[session.id] = session
        with session.lock:
            try:
                session.prepare()
                errors = session.compile()
                if errors is not None:
                    cpu_ms = session.take_cpu_ms()
                    session.cleanup()
                    return {"session": session.id, "state": "finished", "verdict": "compile_error",
                            "output": [{"stream": "compile", "text": errors}], "exit_code": None, "signal": None,
                            "cpu_ms": cpu_ms}
                session.start()
                result = session.step()
            except Exception as exc:  # never leave a slot taken
                cpu_ms = session.take_cpu_ms()
                session.cleanup()
                result = {"session": session.id, "state": "finished", "verdict": "error", "output": [], "message": str(exc),
                          "cpu_ms": cpu_ms}
            finally:
                if session.finished:
                    self._forget(session)
            return result

    def send_input(self, session_id, text):
        session = self.sessions.get(session_id)
        if session is None or session.finished:
            return None
        with session.lock:
            if session.finished:
                return None
            try:
                session.send(text)
                result = session.step()
            except OSError:  # the program closed its input or ended meanwhile
                session.resume()
                session.reap(session.proc, None)
                result = session._finished(session.proc.returncode)
            if session.finished:
                self._forget(session)
            return result

    def stop(self, session_id):
        session = self.sessions.get(session_id)
        if session is None:
            return False
        session.cleanup()
        self._forget(session)
        return True

    def _forget(self, session):
        with self.lock:
            self.sessions.pop(session.id, None)

    def _reap(self):
        while True:
            time.sleep(2)
            now = time.monotonic()
            for session in list(self.sessions.values()):
                idle = now - session.touched > IDLE_SECONDS
                old = now - session.started > SESSION_SECONDS
                if (idle or old) and session.lock.acquire(blocking=False):
                    try:
                        session.cleanup()
                        self._forget(session)
                    finally:
                        session.lock.release()


RUNNER = None


class Handler(BaseHTTPRequestHandler):
    server_version = "IgaCodeRunner/1"

    def log_message(self, fmt, *args):
        pass  # never log students' code or input

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorised(self):
        if not TOKEN:
            return True
        given = self.headers.get("Authorization", "")
        return hmac.compare_digest(given.encode(), f"Bearer {TOKEN}".encode())

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path != "/health":
            return self._send(404, {"error": "not found"})
        if not self._authorised():
            return self._send(401, {"error": "unauthorised"})
        self._send(200, {"ok": True, "languages": sorted(LANGUAGES), "slots": SLOTS, "busy": RUNNER.busy()})

    def do_POST(self):
        if not self._authorised():
            return self._send(401, {"error": "unauthorised"})
        try:
            body = self._body()
        except ValueError:
            return self._send(400, {"error": "bad request"})
        if self.path == "/run":
            language, code = body.get("language"), body.get("code")
            if language not in LANGUAGES or not isinstance(code, str) or not code.strip() or len(code) > MAX_CODE:
                return self._send(400, {"error": "bad request"})
            return self._send(200, RUNNER.run(language, code))
        if self.path == "/input":
            text = body.get("text")
            if not isinstance(text, str) or len(text) > MAX_INPUT:
                return self._send(400, {"error": "bad request"})
            result = RUNNER.send_input(str(body.get("session", "")), text)
            return self._send(200, result) if result else self._send(404, {"error": "no such session"})
        if self.path == "/stop":
            return self._send(200, {"stopped": RUNNER.stop(str(body.get("session", "")))})
        self._send(404, {"error": "not found"})


def main():
    global RUNNER
    RUNNER = Runner()
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("CODE_RUNNER_PORT", "2000"))), Handler)
    server.daemon_threads = True
    print(f"Iga code runner listening on {server.server_address[1]} with {SLOTS} slots", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
