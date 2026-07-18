#!/usr/bin/env python3
"""
jumpcloud-totp-relay.py — one-shot TOTP relay for unattended MFA.

Generates a JumpCloud TOTP code (via jumpcloud-totp.py, which reads the seed
from macOS Keychain) and serves it EXACTLY ONCE over an ephemeral 127.0.0.1
endpoint guarded by a single-use random token, then exits. The code is NEVER
printed, echoed, logged, or passed as a tool argument — only the fetch URL
(token, no secret) is written to stdout. The login page fetches it via
page.request and enters it. Self-destructs after first read or 25s.

Mirrors jumpcloud-fill-password.py's security model. Never logs the code/seed.
"""
import os, sys, socket, secrets, subprocess, threading, time, http.server

TOTP_HELPER = os.path.expanduser("~/.claude/scripts/jumpcloud-totp.py")


def get_code():
    out = subprocess.check_output(["python3", TOTP_HELPER]).decode().strip()
    if not (len(out) == 6 and out.isdigit()):
        raise ValueError("totp helper did not return a 6-digit code")
    return out


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    token = secrets.token_urlsafe(16)

    # Generate the code up front so a failure surfaces on stderr before we fork.
    try:
        code = get_code()
    except Exception as e:
        sys.stderr.write("TOTP_RELAY_FAIL: %s\n" % e)
        sys.exit(1)

    sys.stdout.write("http://127.0.0.1:%d/%s\n" % (port, token))
    sys.stdout.flush()

    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0); os.dup2(devnull, 1); os.dup2(devnull, 2)

    served = [False]

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/" + token and not served[0]:
                served[0] = True
                body = code.encode()
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()
            threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)),
                             daemon=True).start()

    httpd = http.server.HTTPServer(("127.0.0.1", port), Handler,
                                   bind_and_activate=False)
    httpd.socket = sock
    httpd.server_activate()
    threading.Thread(target=lambda: (time.sleep(25), os._exit(0)), daemon=True).start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
