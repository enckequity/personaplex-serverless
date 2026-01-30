"""
PersonaPlex Serverless Handler for RunPod
Starts the PersonaPlex WebSocket server and reports connection details.
"""
import os
import sys
import subprocess
import time
import socket
import runpod

# Server process
server_process = None

def start_personaplex_server():
    """Start the PersonaPlex server as a subprocess."""
    global server_process

    # Create SSL directory
    ssl_dir = "/app/ssl"
    os.makedirs(ssl_dir, exist_ok=True)

    # Use the venv Python to run the server
    python_path = "/app/moshi/.venv/bin/python"

    cmd = [
        python_path, "-m", "moshi.server",
        "--ssl", ssl_dir,
        "--host", "0.0.0.0",
        "--port", "8998"
    ]

    print(f"Starting PersonaPlex server: {' '.join(cmd)}")
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Wait for server to be ready
    start_time = time.time()
    timeout = 180  # 3 minutes max for model loading (first run downloads weights)

    while time.time() - start_time < timeout:
        if server_process.poll() is not None:
            # Process died - read output
            output = server_process.stdout.read() if server_process.stdout else "No output"
            raise RuntimeError(f"Server died during startup: {output}")

        # Check if port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8998))
        sock.close()

        if result == 0:
            print("PersonaPlex server is ready!")
            return True

        # Print server output while waiting
        if server_process.stdout:
            import select
            if select.select([server_process.stdout], [], [], 0.1)[0]:
                line = server_process.stdout.readline()
                if line:
                    print(f"[server] {line.strip()}")

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

    # Get connection details from environment
    public_ip = os.environ.get('RUNPOD_PUBLIC_IP', 'localhost')
    tcp_port = os.environ.get('RUNPOD_TCP_PORT_8998', '8998')

    print(f"Public IP: {public_ip}")
    print(f"TCP Port: {tcp_port}")

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
