#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from urllib.error import HTTPError

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arnis_korea_detailed.static_map_request_planner import split_static_map_requests

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "ArnisKorea"
SECRETS_PATH = APP_DIR / "secrets.json"
DEFAULT_BBOX = "37.5955,127.0555,37.5985,127.0620"
SEOUL_BBOX = "37.5450,126.9550,37.5750,127.0150"
STATIC_ENDPOINT = "https://maps.apigw.ntruss.com/map-static/v2/raster"


def parse_bbox_text(value: str) -> dict[str, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox는 min_lat,min_lng,max_lat,max_lng 형식이어야 합니다.")
    bbox = {"min_lat": parts[0], "min_lng": parts[1], "max_lat": parts[2], "max_lng": parts[3]}
    if bbox["min_lat"] >= bbox["max_lat"] or bbox["min_lng"] >= bbox["max_lng"]:
        raise ValueError("bbox 최소값은 최대값보다 작아야 합니다.")
    return bbox


def bbox_center(value: str) -> tuple[float, float]:
    bbox = parse_bbox_text(value)
    return ((bbox["min_lat"] + bbox["max_lat"]) / 2, (bbox["min_lng"] + bbox["max_lng"]) / 2)


def open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        webbrowser.open(path.as_uri())


class ArnisKoreaApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Arnis Korea")
        self.root.geometry("1060x760")
        self.root.minsize(920, 640)
        self.running = False

        self.output_dir = StringVar(value=str(ROOT / "world-hufs"))
        self.bbox = StringVar(value=DEFAULT_BBOX)
        self.spawn_mode = StringVar(value="auto")
        self.spawn_lat = StringVar(value="")
        self.spawn_lng = StringVar(value="")
        self.terrain = BooleanVar(value=True)
        self.source = StringVar(value="osm")
        self.building_mode = StringVar(value="full")
        self.interior = BooleanVar(value=False)
        self.roof = BooleanVar(value=True)
        self.client_id = StringVar(value="")
        self.client_secret = StringVar(value="")
        self.cli_preview = StringVar(value="")

        self._style()
        self._load_saved_keys()
        self._build()
        self.update_preview()

    def _style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f7f9")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f6f7f9", foreground="#1f2933", font=("Malgun Gothic", 10))
        style.configure("Panel.TLabel", background="#ffffff", foreground="#1f2933", font=("Malgun Gothic", 10))
        style.configure("Title.TLabel", background="#f6f7f9", foreground="#111827", font=("Malgun Gothic", 16, "bold"))
        style.configure("TButton", font=("Malgun Gothic", 10), padding=(10, 6))
        style.configure("Primary.TButton", font=("Malgun Gothic", 10, "bold"), padding=(12, 8))
        style.configure("TNotebook", background="#f6f7f9")
        style.configure("TNotebook.Tab", font=("Malgun Gothic", 10), padding=(14, 7))

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Arnis Korea", style="Title.TLabel").pack(anchor="w")
        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True, pady=(12, 0))
        self.world_tab = ttk.Frame(notebook, padding=14)
        self.map_tab = ttk.Frame(notebook, padding=14)
        self.api_tab = ttk.Frame(notebook, padding=14)
        self.tools_tab = ttk.Frame(notebook, padding=14)
        self.help_tab = ttk.Frame(notebook, padding=14)
        notebook.add(self.world_tab, text="월드 생성")
        notebook.add(self.map_tab, text="지도/범위")
        notebook.add(self.api_tab, text="네이버 API")
        notebook.add(self.tools_tab, text="도구")
        notebook.add(self.help_tab, text="도움말")
        self._build_world_tab()
        self._build_map_tab()
        self._build_api_tab()
        self._build_tools_tab()
        self._build_help_tab()

    def _row(self, parent: ttk.Frame, label: str, widget: ttk.Widget, row: int, button: ttk.Widget | None = None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        if button is not None:
            button.grid(row=row, column=2, sticky="ew", padx=(8, 0), pady=6)
        parent.columnconfigure(1, weight=1)

    def _build_world_tab(self) -> None:
        form = ttk.Frame(self.world_tab)
        form.pack(fill="x")
        self._row(form, "출력 폴더", ttk.Entry(form, textvariable=self.output_dir), 0, ttk.Button(form, text="선택", command=self.choose_output))
        self._row(form, "bbox", ttk.Entry(form, textvariable=self.bbox), 1)
        spawn = ttk.Frame(form)
        for text, value in [("자동", "auto"), ("수동", "manual"), ("Arnis 기본값", "default")]:
            ttk.Radiobutton(spawn, text=text, variable=self.spawn_mode, value=value, command=self.update_preview).pack(side="left", padx=(0, 14))
        self._row(form, "스폰포인트", spawn, 2)
        spawn_values = ttk.Frame(form)
        ttk.Label(spawn_values, text="lat").pack(side="left")
        ttk.Entry(spawn_values, textvariable=self.spawn_lat, width=16).pack(side="left", padx=(6, 16))
        ttk.Label(spawn_values, text="lng").pack(side="left")
        ttk.Entry(spawn_values, textvariable=self.spawn_lng, width=16).pack(side="left", padx=(6, 0))
        self._row(form, "수동 좌표", spawn_values, 3)
        source = ttk.Combobox(form, textvariable=self.source, values=["osm", "mock", "naver-static"], state="readonly")
        self._row(form, "소스", source, 4)
        mode = ttk.Combobox(form, textvariable=self.building_mode, values=["full", "footprint-only", "roads-terrain", "campus-style"], state="readonly")
        self._row(form, "건물 생성 모드", mode, 5)
        checks = ttk.Frame(form)
        ttk.Checkbutton(checks, text="terrain", variable=self.terrain, command=self.update_preview).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(checks, text="내부 생성", variable=self.interior, command=self.update_preview).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(checks, text="지붕 생성", variable=self.roof, command=self.update_preview).pack(side="left")
        self._row(form, "옵션", checks, 6)
        for var in [self.output_dir, self.bbox, self.spawn_lat, self.spawn_lng, self.source, self.building_mode]:
            var.trace_add("write", lambda *_: self.update_preview())

        actions = ttk.Frame(self.world_tab)
        actions.pack(fill="x", pady=(12, 8))
        self.generate_button = ttk.Button(actions, text="Generate World", style="Primary.TButton", command=self.generate_world)
        self.generate_button.pack(side="left")
        ttk.Button(actions, text="월드 폴더 열기", command=lambda: open_path(Path(self.output_dir.get()))).pack(side="left", padx=(8, 0))

        self.log = ScrolledText(self.world_tab, height=18, font=("Consolas", 10), wrap="word")
        self.log.pack(fill="both", expand=True)

    def _build_map_tab(self) -> None:
        form = ttk.Frame(self.map_tab)
        form.pack(fill="x")
        self._row(form, "bbox", ttk.Entry(form, textvariable=self.bbox), 0)
        buttons = ttk.Frame(self.map_tab)
        buttons.pack(fill="x", pady=10)
        ttk.Button(buttons, text="HUFS 샘플 불러오기", command=lambda: self.set_bbox(DEFAULT_BBOX)).pack(side="left")
        ttk.Button(buttons, text="서울 샘플 불러오기", command=lambda: self.set_bbox(SEOUL_BBOX)).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Dynamic Map selector 열기", command=self.open_selector).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="bbox JSON 불러오기", command=self.load_bbox_json).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="요청 수 계산", command=self.plan_static).pack(side="left", padx=(8, 0))
        self.map_result = ScrolledText(self.map_tab, height=22, font=("Consolas", 10), wrap="word")
        self.map_result.pack(fill="both", expand=True)

    def _build_api_tab(self) -> None:
        form = ttk.Frame(self.api_tab)
        form.pack(fill="x")
        self._row(form, "Client ID", ttk.Entry(form, textvariable=self.client_id), 0)
        self._row(form, "Client Secret", ttk.Entry(form, textvariable=self.client_secret, show="*"), 1)
        actions = ttk.Frame(self.api_tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="저장", command=self.save_keys).pack(side="left")
        ttk.Button(actions, text="저장된 키 삭제", command=self.delete_keys).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Static Map API 테스트", command=self.test_static_api).pack(side="left", padx=(8, 0))
        text = (
            "Client ID = x-ncp-apigw-api-key-id\n"
            "Client Secret = x-ncp-apigw-api-key\n"
            "Ncloud 계정 Access Key/Secret Key가 아니라 Maps Application 인증 정보입니다.\n"
            "키 원문은 로그에 출력하지 않습니다."
        )
        ttk.Label(self.api_tab, text=text, justify="left").pack(anchor="w", pady=(2, 10))
        self.api_result = ScrolledText(self.api_tab, height=18, font=("Consolas", 10), wrap="word")
        self.api_result.pack(fill="both", expand=True)

    def _build_tools_tab(self) -> None:
        actions = ttk.Frame(self.tools_tab)
        actions.pack(fill="x")
        ttk.Button(actions, text="Plan Static Map 실행", command=self.plan_static).pack(side="left")
        ttk.Button(actions, text="Mock Vectorize 실행", command=self.mock_vectorize).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="출력 폴더 열기", command=lambda: open_path(Path(self.output_dir.get()))).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="로그 저장", command=self.save_log).pack(side="left", padx=(8, 0))
        ttk.Label(self.tools_tab, text="CLI 명령 미리보기").pack(anchor="w", pady=(14, 4))
        ttk.Entry(self.tools_tab, textvariable=self.cli_preview).pack(fill="x")

    def _build_help_tab(self) -> None:
        text = (
            "사용 순서\n"
            "1. 지도/범위 탭에서 bbox를 정합니다.\n"
            "2. 월드 생성 탭에서 출력 폴더와 스폰포인트, 건물 옵션을 선택합니다.\n"
            "3. Generate World를 누릅니다.\n\n"
            "Minecraft Java saves 폴더\n"
            "%APPDATA%\\.minecraft\\saves\n\n"
            "생성된 world 폴더를 위 saves 폴더로 복사한 뒤 Minecraft Java Edition에서 선택합니다.\n\n"
            "네이버 API 키\n"
            "Naver Cloud Platform Console의 Maps Application에서 Static Map과 Dynamic Map을 켠 뒤 Client ID/Client Secret을 앱에 저장합니다.\n\n"
            "더블클릭 앱은 일반 사용자용 GUI이고, arnis-korea-cli.exe는 고급 사용자와 문제 진단용입니다."
        )
        ttk.Label(self.help_tab, text=text, justify="left").pack(anchor="nw")

    def _load_saved_keys(self) -> None:
        if not SECRETS_PATH.exists():
            return
        try:
            data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
            self.client_id.set(data.get("client_id", ""))
            self.client_secret.set(data.get("client_secret", ""))
        except Exception:
            return

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(ROOT))
        if selected:
            self.output_dir.set(selected)

    def set_bbox(self, value: str) -> None:
        self.bbox.set(value)
        self.plan_static()

    def open_selector(self) -> None:
        selector = ROOT / "web" / "dynamic_selector.html"
        webbrowser.open(selector.resolve().as_uri())

    def load_bbox_json(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        bbox = data.get("bbox", data)
        self.bbox.set(f"{bbox['min_lat']},{bbox['min_lng']},{bbox['max_lat']},{bbox['max_lng']}")
        self.plan_static()

    def save_keys(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        SECRETS_PATH.write_text(json.dumps({"client_id": self.client_id.get().strip(), "client_secret": self.client_secret.get().strip()}, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_api_result({"saved": True, "path": str(SECRETS_PATH), "client_id_present": bool(self.client_id.get().strip()), "client_secret_present": bool(self.client_secret.get().strip())})

    def delete_keys(self) -> None:
        if SECRETS_PATH.exists():
            SECRETS_PATH.unlink()
        self.client_id.set("")
        self.client_secret.set("")
        self._write_api_result({"deleted": True, "path": str(SECRETS_PATH)})

    def test_static_api(self) -> None:
        def worker() -> None:
            try:
                plan = split_static_map_requests(parse_bbox_text(self.bbox.get()), level=16, width=640, height=640, scale=1, maptype="basic", fmt="png", dataversion=None)
                url = f"{STATIC_ENDPOINT}?{urllib.parse.urlencode(plan['tiles'][0]['params'])}"
                headers = {"x-ncp-apigw-api-key-id": self.client_id.get().strip(), "x-ncp-apigw-api-key": self.client_secret.get().strip()}
                if not headers["x-ncp-apigw-api-key-id"] or not headers["x-ncp-apigw-api-key"]:
                    result = {"executed": False, "reason": "키를 먼저 입력하세요."}
                else:
                    request = urllib.request.Request(url, headers=headers, method="GET")
                    try:
                        with urllib.request.urlopen(request, timeout=10) as response:
                            body = response.read()
                            result = {"executed": True, "status": response.status, "content_type": response.headers.get("content-type"), "bytes": len(body), "sha256_prefix": hashlib.sha256(body).hexdigest()[:16]}
                    except HTTPError as exc:
                        body = exc.read()
                        result = {"executed": True, "status": exc.code, "content_type": exc.headers.get("content-type"), "bytes": len(body), "sha256_prefix": hashlib.sha256(body).hexdigest()[:16]}
            except Exception as exc:
                result = {"executed": True, "status": "error", "error_type": type(exc).__name__, "message": str(exc)}
            self.root.after(0, lambda: self._write_api_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def plan_static(self) -> None:
        try:
            plan = split_static_map_requests(parse_bbox_text(self.bbox.get()), level=16, width=1024, height=1024, scale=2, maptype="basic", fmt="png", dataversion=None)
            lat_size = abs(plan["bbox"]["max_lat"] - plan["bbox"]["min_lat"])
            lng_size = abs(plan["bbox"]["max_lng"] - plan["bbox"]["min_lng"])
            warning = "범위가 큽니다. 먼저 작은 bbox로 테스트하세요." if lat_size > 0.02 or lng_size > 0.02 else "범위가 작아 테스트에 적합합니다."
            self.map_result.delete("1.0", "end")
            self.map_result.insert("end", json.dumps({"tile_count": len(plan["tiles"]), "bbox": plan["bbox"], "warning": warning, "endpoint": plan["endpoint"]}, ensure_ascii=False, indent=2))
        except Exception as exc:
            self.map_result.delete("1.0", "end")
            self.map_result.insert("end", str(exc))

    def mock_vectorize(self) -> None:
        self.run_cli(["mock-vectorize", "--bbox", self.bbox.get(), "--output-dir", self.output_dir.get()])

    def save_log(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log", "*.log"), ("Text", "*.txt")])
        if path:
            Path(path).write_text(self.log.get("1.0", "end"), encoding="utf-8")

    def cli_base(self) -> list[str]:
        cli_exe = ROOT / "arnis-korea-cli.exe"
        if cli_exe.exists():
            return [str(cli_exe)]
        return [sys.executable, str(ROOT / "scripts" / "arnis_korea_detailed.py")]

    def build_generate_args(self) -> list[str]:
        args = ["generate", "--bbox", self.bbox.get(), "--output-dir", self.output_dir.get(), "--source", self.source.get(), f"--building-mode={self.building_mode.get()}", f"--interior={str(self.interior.get()).lower()}", f"--roof={str(self.roof.get()).lower()}"]
        if self.terrain.get():
            args.append("--terrain")
        if self.spawn_mode.get() == "auto":
            lat, lng = bbox_center(self.bbox.get())
            args.extend([f"--spawn-lat={lat}", f"--spawn-lng={lng}"])
        elif self.spawn_mode.get() == "manual":
            if self.spawn_lat.get().strip():
                args.append(f"--spawn-lat={float(self.spawn_lat.get())}")
            if self.spawn_lng.get().strip():
                args.append(f"--spawn-lng={float(self.spawn_lng.get())}")
        return args

    def update_preview(self) -> None:
        try:
            self.cli_preview.set(" ".join(self.cli_base() + self.build_generate_args()))
        except Exception:
            self.cli_preview.set("입력값을 확인하세요.")

    def generate_world(self) -> None:
        if self.running:
            return
        if self.source.get() == "naver-static":
            messagebox.showwarning("라이선스 확인 필요", "Naver Static 소스는 명시적인 라이선스 확인이 필요합니다. 먼저 OSM 또는 Mock으로 생성하세요.")
            return
        try:
            args = self.build_generate_args()
        except Exception as exc:
            messagebox.showerror("입력 오류", str(exc))
            return
        self.run_cli(args, verify_world=True)

    def run_cli(self, args: list[str], verify_world: bool = False) -> None:
        def worker() -> None:
            command = self.cli_base() + args
            self.running = True
            self.root.after(0, lambda: self.generate_button.configure(state="disabled"))
            self.root.after(0, lambda: self.append_log(f"$ {' '.join(command)}\n"))
            result = subprocess.run(command, cwd=ROOT, check=False, text=True, encoding="utf-8", errors="replace", capture_output=True)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            self.root.after(0, lambda: self.append_log(stdout + stderr + f"\nreturncode={result.returncode}\n"))
            if verify_world:
                verification = self.verify_world(Path(self.output_dir.get()))
                self.root.after(0, lambda: self.append_log(json.dumps(verification, ensure_ascii=False, indent=2) + "\n"))
            self.running = False
            self.root.after(0, lambda: self.generate_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def verify_world(self, path: Path) -> dict[str, object]:
        return {
            "level_dat": any(path.rglob("level.dat")) if path.exists() else False,
            "region_dir": any(candidate.is_dir() and candidate.name == "region" for candidate in path.rglob("*")) if path.exists() else False,
            "mca_file": any(path.rglob("*.mca")) if path.exists() else False,
        }

    def append_log(self, text: str) -> None:
        self.log.insert("end", text)
        self.log.see("end")

    def _write_api_result(self, data: dict[str, object]) -> None:
        self.api_result.delete("1.0", "end")
        self.api_result.insert("end", json.dumps(data, ensure_ascii=False, indent=2))


def self_test_gui() -> int:
    root = Tk()
    root.withdraw()
    app = ArnisKoreaApp(root)
    app.update_preview()
    root.update_idletasks()
    root.destroy()
    print("GUI_SELF_TEST=PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test-gui", action="store_true")
    args = parser.parse_args()
    if args.self_test_gui:
        return self_test_gui()
    root = Tk()
    ArnisKoreaApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
