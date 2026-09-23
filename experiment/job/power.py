# -*- coding: utf-8 -*-
"""Power sampling backends: tegrastats (Jetson), nvidia-smi/NVML, or none."""
import os
import re
import shutil
import subprocess
import threading
import time


class PowerSampler:
    """Collects average power samples during a context window."""

    def __init__(self, backend: str = "none", interval_s: float = 0.1,
                 gpu_index: int = None):
        self.backend = backend
        self.interval_s = max(0.02, interval_s)
        self.gpu_index = self._resolve_gpu_index(gpu_index)
        self.samples = []
        self._stop = threading.Event()
        self._thread = None
        self._proc = None

    @staticmethod
    def _resolve_gpu_index(hint):
        """Map CUDA_VISIBLE_DEVICES to the physical GPU index for nvidia-smi -i."""
        if hint is not None:
            return int(hint)
        vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
        if vis and vis.lower() != "no_device":
            first = vis.split(",")[0].strip()
            if first.isdigit():
                return int(first)
        return 0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def start(self):
        if self.backend == "none":
            return
        if self.backend == "tegrastats":
            exe = shutil.which("tegrastats")
            if not exe:
                print("[power] tegrastats not found; disabling power sampling")
                self.backend = "none"
                return
            self._proc = subprocess.Popen(
                [exe, "--interval", str(int(self.interval_s * 1000))],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except Exception:
                self._proc.kill()
            self._proc = None

    def _loop(self):
        while not self._stop.is_set():
            val = self._sample_once()
            if val is not None:
                self.samples.append(val)
            self._stop.wait(self.interval_s)

    def _sample_once(self):
        if self.backend == "tegrastats" and self._proc:
            return self._read_tegrastats()
        if self.backend in ("nvml", "nvidia-smi"):
            return self._read_nvidia()
        return None

    def _read_tegrastats(self):
        # non-blocking read of the newest complete line
        line = None
        while True:
            chunk = self._proc.stdout.readline() if self._proc.stdout else None
            if not chunk:
                break
            line = chunk.strip()
        if not line:
            return None
        mw = re.search(r"VDD_IN\s+(\d+)mW", line)
        if mw:
            return float(mw.group(1)) / 1000.0
        w = re.search(r"VDD_IN\s+([\d.]+)W", line)
        if w:
            return float(w.group(1))
        # fallback: sum of VDD_CPU/VDD_GPU/VDD_SOC when present
        vals = [float(x) for x in re.findall(r"VDD_(?:CPU|GPU|SOC)\s+(\d+)mW", line)]
        if vals:
            return sum(vals) / 1000.0
        return None

    def _read_nvidia(self):
        if self.backend == "nvml":
            try:
                import pynvml
                if not hasattr(self, "_nvml_handle"):
                    pynvml.nvmlInit()
                    self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_index)
                return pynvml.nvmlDeviceGetPowerUsage(self._nvml_handle) / 1000.0
            except Exception:
                pass  # fall back to nvidia-smi below
        if shutil.which("nvidia-smi"):
            query = ["--query-gpu=power.draw", "--format=csv,noheader,nounits"]
            for base in (["nvidia-smi", "-i", str(self.gpu_index)], ["nvidia-smi"]):
                try:
                    out = subprocess.run(
                        base + query, capture_output=True, text=True, timeout=3.0,
                    ).stdout.strip()
                    line = out.splitlines()[0] if out else ""
                    if line.lower() not in ("", "[n/a]", "n/a"):
                        return float(line)
                    break
                except Exception:
                    continue
        return None

    def average_w(self):
        return (sum(self.samples) / len(self.samples)) if self.samples else None

    @property
    def throttled(self):
        return None  # tegrastats throttle parsing left to analysis on the target
