"""
PersonaPlex Serverless Handler for RunPod
Starts the PersonaPlex WebSocket server and reports connection details.
"""
import os
import sys
import subprocess
import time
import socket
import threading
import runpod

print("=" * 50)
print("HANDLER MODULE LOADED")
print(f"Python: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print("=" * 50)
sys.stdout.flush()

# Server process
server_process = None

def log_output(proc):
    """Thread to continuously log server output."""
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                print(f"[moshi] {line.strip()}")
                sys.stdout.flush()
    except Exception as e:
        print(f"[log_output error] {e}")
        sys.stdout.flush()

def start_personaplex_server():
    """Start the PersonaPlex server as a subprocess."""
    global server_process

    print("start_personaplex_server() called")
    sys.stdout.flush()

    # Create SSL directory
    ssl_dir = "/app/ssl"
    os.makedirs(ssl_dir, exist_ok=True)
    print(f"SSL dir: {ssl_dir}")

    # Use the venv Python to run the server
    python_path = "/app/.venv/bin/python"
    print(f"Python path: {python_path}")
    print(f"Python exists: {os.path.exists(python_path)}")

    cmd = [
        python_path, "-m", "moshi.server",
        "--ssl", ssl_dir,
        "--host", "0.0.0.0",
        "--port", "8998"
    ]

    print(f"Starting PersonaPlex server: {' '.join(cmd)}")
    sys.stdout.flush()

    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    print(f"Server process started, PID: {server_process.pid}")
    sys.stdout.flush()

    # Start output logging thread
    log_thread = threading.Thread(target=log_output, args=(server_process,), daemon=True)
    log_thread.start()
    print("Log thread started")
    sys.stdout.flush()

    # Wait for server to be ready
    start_time = time.time()
    timeout = 180  # 3 minutes max for model loading

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)

        if server_process.poll() is not None:
            # Process died
            print(f"SERVER DIED! Exit code: {server_process.returncode}")
            sys.stdout.flush()
            raise RuntimeError(f"Server died with exit code {server_process.returncode}")

        # Check if port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8998))
        sock.close()

        if result == 0:
            print(f"PersonaPlex server is ready after {elapsed}s!")
            sys.stdout.flush()
            return True

        if elapsed % 10 == 0:
            print(f"Waiting for server... {elapsed}s elapsed")
            sys.stdout.flush()

        time.sleep(1)

    raise RuntimeError("Server startup timed out after 3 minutes")


def stop_server():
    """Stop the PersonaPlex server."""
    global server_process
    if server_process:
        print("Stopping PersonaPlex server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None


def handler(event):
    """RunPod job handler - starts PersonaPlex and waits for shutdown."""
    print("=" * 50)
    print("HANDLER CALLED")
    print(f"Event: {event}")
    print("=" * 50)
    sys.stdout.flush()

    # Get connection details from environment
    public_ip = os.environ.get('RUNPOD_PUBLIC_IP', 'localhost')
    tcp_port = os.environ.get('RUNPOD_TCP_PORT_8998', '8998')

    print(f"Public IP: {public_ip}")
    print(f"TCP Port: {tcp_port}")
    print(f"HF_TOKEN set: {'HF_TOKEN' in os.environ}")
    sys.stdout.flush()

    try:
        # Start the PersonaPlex server
        start_personaplex_server()

        # Build the WebSocket URL
        # RunPod proxies through their domain, so we use their format
        ws_url = f"wss://{public_ip}:{tcp_port}/api/chat"

        # Report connection details via progress update
        connection_info = {
            "status": "ready",
            "public_ip": public_ip,
            "tcp_port": tcp_port,
            "ws_url": ws_url
        }
        runpod.serverless.progress_update(event, connection_info)

        print(f"PersonaPlex ready at {ws_url}")

        # Keep running until RunPod terminates us (idle timeout)
        # The server handles WebSocket connections independently
        while True:
            time.sleep(10)

            # Check if server is still running
            if server_process and server_process.poll() is not None:
                return {"status": "error", "message": "Server died unexpectedly"}

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        stop_server()
        return {"status": "error", "message": str(e)}

    finally:
        stop_server()

    return {"status": "completed"}


if __name__ == "__main__":
    print("Starting PersonaPlex Serverless Worker...")
    runpod.serverless.start({"handler": handler})
