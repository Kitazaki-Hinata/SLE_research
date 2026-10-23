"""Execute notebook cells with the project's real Jupyter kernel.

This temporary helper deliberately uses JSON rather than nbformat/nbclient.
The notebook is replaced only after every cell completes successfully.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from queue import Empty
import sys
import time
import uuid

from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--cwd", type=Path, help="Kernel working directory; defaults to notebook directory")
    parser.add_argument("--no-save", action="store_true", help="Execute and validate without changing the notebook")
    parser.add_argument("--timeout", type=float, default=120, help="Per-cell timeout in seconds")
    parser.add_argument("--startup-timeout", type=float, default=60)
    return parser.parse_args()


def collect_cell(client, manager, source, cell_number, timeout, displays):
    message_id = client.execute(source, silent=False, store_history=True, allow_stdin=False)
    outputs = []
    execution_count = None
    failure = None
    clear_on_output = False
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Cell {cell_number} exceeded {timeout:g} seconds")
        try:
            message = client.get_iopub_msg(timeout=min(1, remaining))
        except Empty:
            if not manager.is_alive():
                raise RuntimeError(f"Kernel exited during cell {cell_number}")
            continue
        if message.get("parent_header", {}).get("msg_id") != message_id:
            continue
        kind = message["header"]["msg_type"]
        content = message["content"]
        if kind == "status" and content["execution_state"] == "idle":
            break
        if kind == "execute_input":
            execution_count = content["execution_count"]
        elif kind == "clear_output":
            clear_on_output = content.get("wait", False)
            if not clear_on_output:
                outputs.clear()
        elif kind in {"stream", "execute_result", "display_data", "update_display_data", "error"}:
            if clear_on_output:
                outputs.clear()
                clear_on_output = False
            if kind == "stream":
                if outputs and outputs[-1]["output_type"] == "stream" and outputs[-1]["name"] == content["name"]:
                    outputs[-1]["text"] += content["text"]
                else:
                    outputs.append({"output_type": "stream", "name": content["name"], "text": content["text"]})
            elif kind == "error":
                failure = {key: content[key] for key in ("ename", "evalue", "traceback")}
                outputs.append({"output_type": "error", **failure})
            else:
                display_id = content.get("transient", {}).get("display_id")
                if kind == "update_display_data":
                    for previous in displays.get(display_id, []):
                        previous["data"] = copy.deepcopy(content["data"])
                        previous["metadata"] = copy.deepcopy(content["metadata"])
                    continue
                output = {
                    "output_type": kind,
                    "data": content["data"],
                    "metadata": content["metadata"],
                }
                if kind == "execute_result":
                    output["execution_count"] = content["execution_count"]
                outputs.append(output)
                if display_id:
                    displays.setdefault(display_id, []).append(output)

    # The shell reply provides a second check after the IOPub idle message.
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Missing execution reply for cell {cell_number}")
        reply = client.get_shell_msg(timeout=remaining)
        if reply.get("parent_header", {}).get("msg_id") == message_id:
            break
    reply_content = reply["content"]
    execution_count = reply_content.get("execution_count", execution_count)
    if reply_content.get("status") != "ok" or failure is not None:
        details = failure or reply_content
        traceback = "\n".join(details.get("traceback", []))
        raise RuntimeError(f"Cell {cell_number} failed: {details.get('ename', 'error')}: {details.get('evalue', '')}\n{traceback}")
    return execution_count, outputs


def main() -> int:
    args = parse_args()
    notebook_path = args.notebook.resolve(strict=True)
    kernel_cwd = (args.cwd or notebook_path.parent).resolve(strict=True)
    if not kernel_cwd.is_dir():
        raise NotADirectoryError(kernel_cwd)
    workspace = Path(__file__).resolve().parent.parent
    kernel_python = workspace / ".venv" / "Scripts" / "python.exe"
    if not kernel_python.is_file():
        raise FileNotFoundError(f"Project interpreter missing: {kernel_python}")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8-sig"))
    if notebook.get("nbformat") != 4:
        raise ValueError("This helper supports notebook format 4 only")

    # All Jupyter, IPython, and matplotlib state stays inside the workspace.
    run_dir = workspace / ".tmp_collinearity" / "runtime" / uuid.uuid4().hex
    directories = {name: run_dir / name for name in ("runtime", "config", "data", "ipython", "matplotlib", "kernels")}
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({
        "JUPYTER_RUNTIME_DIR": str(directories["runtime"]),
        "JUPYTER_CONFIG_DIR": str(directories["config"]),
        "JUPYTER_DATA_DIR": str(directories["data"]),
        "IPYTHONDIR": str(directories["ipython"]),
        "MPLCONFIGDIR": str(directories["matplotlib"]),
        "MPLBACKEND": "module://matplotlib_inline.backend_inline",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "JUPYTER_PLATFORM_DIRS": "1",
    })
    # Apply these to the manager as well as the kernel subprocess.
    for name in ("JUPYTER_RUNTIME_DIR", "JUPYTER_CONFIG_DIR", "JUPYTER_DATA_DIR", "IPYTHONDIR", "MPLCONFIGDIR", "JUPYTER_PLATFORM_DIRS"):
        os.environ[name] = environment[name]
    spec_dir = directories["kernels"] / "collinearity-project"
    spec_dir.mkdir()
    spec = {
        "argv": [str(kernel_python), "-m", "ipykernel_launcher", "-f", "{connection_file}", "--IPKernelApp.matplotlib=inline"],
        "display_name": "SLE project Python",
        "language": "python",
    }
    (spec_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
    spec_manager = KernelSpecManager(kernel_dirs=[str(directories["kernels"])], ensure_native_kernel=False)
    manager = KernelManager(
        kernel_name="collinearity-project",
        kernel_spec_manager=spec_manager,
        connection_file=str(directories["runtime"] / "kernel.json"),
    )
    client = None
    displays = {}
    started_at = time.monotonic()
    print(f"Notebook: {notebook_path}", flush=True)
    print(f"Kernel cwd: {kernel_cwd}", flush=True)
    print(f"Kernel log: {run_dir / 'kernel.log'}", flush=True)
    try:
        with (run_dir / "kernel.log").open("w", encoding="utf-8") as kernel_log:
            manager.start_kernel(cwd=str(kernel_cwd), env=environment, stdout=kernel_log, stderr=kernel_log)
            client = manager.blocking_client()
            client.start_channels()
            client.wait_for_ready(timeout=args.startup_timeout)
            for number, cell in enumerate(notebook["cells"], start=1):
                if cell["cell_type"] != "code":
                    continue
                source = cell["source"]
                source = "".join(source) if isinstance(source, list) else source
                cell["execution_count"] = None
                cell["outputs"] = []
                if not source.strip():
                    continue
                cell_start = time.monotonic()
                count, outputs = collect_cell(client, manager, source, number, args.timeout, displays)
                cell["execution_count"] = count
                cell["outputs"] = outputs
                kinds = ", ".join(output["output_type"] for output in outputs) or "no output"
                print(f"Cell {number}: execution {count}, {time.monotonic() - cell_start:.2f}s, {kinds}", flush=True)
    finally:
        if client is not None:
            client.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
        manager.cleanup_resources()

    if not args.no_save:
        temporary = notebook_path.with_name(f".{notebook_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            temporary.replace(notebook_path)
        finally:
            if temporary.exists():
                temporary.unlink()
    action = "Validated without saving" if args.no_save else "Executed and saved"
    print(f"{action} in {time.monotonic() - started_at:.2f}s", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Execution failed; notebook was not saved: {error}", file=sys.stderr)
        raise SystemExit(1)
