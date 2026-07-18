#!/usr/bin/env python3
"""
jumpcloud-fill-password.py — secure one-shot password relay for unattended login.

Serves the JumpCloud password (read from macOS Keychain) EXACTLY ONCE over an
ephemeral 127.0.0.1 endpoint guarded by a single-use random token, then exits.
The password is NEVER printed, echoed, logged, or passed as a tool argument —
only the fetch URL (token, no secret) is written to stdout. The login page
fetches it via browser_evaluate and fills the field. The endpoint self-destructs
after the first successful read, or after 25s if never hit.

Flow:  Keychain --> localhost (this process) --> in-page fetch() --> password field
The secret never touches the conversation transcript or the run log.

Usage (from the PB skills' Login Sub-procedure):
    URL=$(python3 ~/.claude/scripts/jumpcloud-fill-password.py)
    # then browser_evaluate a fetch(URL) that sets the password field's value
"""
import os, sys, socket, secrets, subprocess, threading, time, http.server

KEYCHAIN_ACCOUNT = "jcrawley"
KEYCHAIN_SERVICE = "jumpcloud-password"


def get_password():
    return subprocess.check_output(
        ["security", "find-generic-password", "-a", KEYCHAIN_ACCOUNT,
         "-s", KEYCHAIN_SERVICE, "-w"]
    ).decode().rstrip("\n")


def main():
    # Reserve an ephemeral loopback port up front so we can print the URL before forking.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    token = secrets.token_urlsafe(16)

    # Only the URL (no secret) goes to stdout — safe to appear in the run log.
    sys.stdout.write("http://127.0.0.1:%d/%s\n" % (port, token))
    sys.stdout.flush()

    # Background the server so the caller's $(...) returns immediately.
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0); os.dup2(devnull, 1); os.dup2(devnull, 2)

    password = get_password()
    served = [False]

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # never log requests
            pass

        def do_GET(self):
            if self.path == "/" + token and not served[0]:
                served[0] = True
                body = password.encode()
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
            # Shut down right after responding (whether served or 404 on reuse).
            threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)),
                             daemon=True).start()

    httpd = http.server.HTTPServer(("127.0.0.1", port), Handler,
                                   bind_and_activate=False)
    httpd.socket = sock
    httpd.server_activate()
    # Hard self-destruct so a never-fetched endpoint can't linger with the secret in memory.
    threading.Thread(target=lambda: (time.sleep(25), os._exit(0)), daemon=True).start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
