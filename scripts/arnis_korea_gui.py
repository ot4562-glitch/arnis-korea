#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import traceback
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "ArnisKorea"
LOG_DIR = APP_DIR / "logs"
LATEST_LOG = LOG_DIR / "latest.log"


def _redact(text: str) -> str:
    for name in ("NAVER_MAPS_CLIENT_ID", "NAVER_MAPS_CLIENT_SECRET"):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "[REDACTED]")
    return text


def write_boot_log(message: str, exc: BaseException | None = None) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        lines = [message]
        if exc is not None:
            lines.append(_redact("".join(traceback.format_exception(type(exc), exc, exc.__traceback__))))
        LATEST_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        print(message, file=sys.stderr)
        if exc is not None:
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)


try:
    from tkinter import BooleanVar, Canvas, Listbox, PhotoImage, StringVar, Tk, filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText
except Exception as tkinter_exc:
    write_boot_log("TKINTER_IMPORT_FAIL", tkinter_exc)
    print(f"Arnis Korea tkinter import failed. See {LATEST_LOG}", file=sys.stderr)
    raise

CORE_IMPORT_ERROR: BaseException | None = None
try:
    from arnis_korea_detailed.static_map_request_planner import split_static_map_requests  # noqa: E402
    from arnis_korea_detailed.trace_editor_core import (  # noqa: E402
        HUFS_BBOX,
        LayerEditSession,
        add_feature,
        approve_suggested,
        bbox_center,
        bbox_to_text,
        create_project,
        empty_feature_collection,
        export_accepted_layers,
        export_synthetic_osm_preview,
        extract_suggested_layers,
        feature,
        iter_geometry_points,
        lng_lat_to_pixel,
        load_project,
        parse_bbox_text,
        project_paths,
        read_json,
        revert_accepted_to_suggested,
        run_self_test,
        save_project,
        validate_project,
        write_layer_validation_report,
        write_json,
    )
except Exception as core_exc:
    CORE_IMPORT_ERROR = core_exc
    write_boot_log("CORE_IMPORT_FAIL", core_exc)

SECRETS_PATH = APP_DIR / "secrets.json"
STATIC_ENDPOINT = "https://maps.apigw.ntruss.com/map-static/v2/raster"


def open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        webbrowser.open(path.as_uri())


def safe_json(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


class TraceEditorApp:
    def __init__(self, root: Tk, safe_mode: bool = False) -> None:
        self.root = root
        self.safe_mode = safe_mode
        self.root.title("Arnis Korea - 네이버 지도 월드 생성기")
        self.root.geometry("1180x780")
        self.root.minsize(1040, 680)

        self.project_dir = StringVar(value=str(ROOT / "trace-editor-project"))
        self.project_name = StringVar(value="HUFS Trace Editor")
        self.bbox = StringVar(value=bbox_to_text(HUFS_BBOX))
        center = bbox_center(HUFS_BBOX)
        self.spawn_lat = StringVar(value=f"{center['lat']:.8f}")
        self.spawn_lng = StringVar(value=f"{center['lng']:.8f}")
        self.client_id = StringVar(value="")
        self.client_secret = StringVar(value="")
        self.allow_static_storage = BooleanVar(value=False)
        self.show_suggested = BooleanVar(value=True)
        self.layer_visible = {name: BooleanVar(value=True) for name in ["road", "building", "water", "green", "rail", "spawn"]}
        self.current_layer = StringVar(value="road")
        self.feature_name = StringVar(value="")
        self.feature_memo = StringVar(value="")
        self.edit_mode = StringVar(value="draw")
        self.canvas_points: list[list[float]] = []
        self.background_image: PhotoImage | None = None
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pan_start: tuple[float, float] | None = None
        self.selected_feature_index: int | None = None
        self.selected_vertex_index: int | None = None
        self.dragging_vertex = False
        self.edit_session = LayerEditSession(Path(self.project_dir.get()))

        self._style()
        if not self.safe_mode:
            self._load_saved_keys()
        self._build()
        self.refresh_project_view()

    def _style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f7f9")
        style.configure("TLabel", background="#f6f7f9", foreground="#1f2933", font=("Malgun Gothic", 10))
        style.configure("Title.TLabel", background="#f6f7f9", foreground="#111827", font=("Malgun Gothic", 16, "bold"))
        style.configure("TButton", font=("Malgun Gothic", 10), padding=(10, 6))
        style.configure("Primary.TButton", font=("Malgun Gothic", 10, "bold"), padding=(12, 8))
        style.configure("TNotebook.Tab", font=("Malgun Gothic", 10), padding=(14, 7))

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Arnis Korea - 네이버 지도 월드 생성기", style="Title.TLabel").pack(anchor="w")
        self.status = StringVar(value="v1.0에서는 레이어 편집과 내보내기까지 지원합니다. Minecraft 월드 생성은 v1.1에서 Arnis Writer와 연결됩니다.")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(4, 10))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        self.tabs: dict[str, ttk.Frame] = {}
        for label in ["프로젝트", "네이버 API", "지도 범위", "레이어 편집", "내보내기", "검수/리포트", "도움말"]:
            frame = ttk.Frame(notebook, padding=12)
            notebook.add(frame, text=label)
            self.tabs[label] = frame
        self._build_project_tab()
        self._build_api_tab()
        self._build_bbox_tab()
        self._build_layer_tab()
        self._build_export_tab()
        self._build_report_tab()
        self._build_help_tab()

    def _row(self, parent: ttk.Frame, label: str, widget: ttk.Widget, row: int, button: ttk.Widget | None = None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        if button is not None:
            button.grid(row=row, column=2, sticky="ew", padx=(8, 0), pady=6)
        parent.columnconfigure(1, weight=1)

    def _build_project_tab(self) -> None:
        tab = self.tabs["프로젝트"]
        form = ttk.Frame(tab)
        form.pack(fill="x")
        self._row(form, "프로젝트 폴더", ttk.Entry(form, textvariable=self.project_dir), 0, ttk.Button(form, text="선택", command=self.choose_project_dir))
        self._row(form, "프로젝트 이름", ttk.Entry(form, textvariable=self.project_name), 1)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="새 프로젝트", style="Primary.TButton", command=self.create_project_action).pack(side="left")
        ttk.Button(actions, text="불러오기", command=self.load_project_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="프로젝트 폴더 열기", command=lambda: open_path(Path(self.project_dir.get()))).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="로그 보기", command=self.open_latest_log).pack(side="left", padx=(8, 0))
        self.project_text = ScrolledText(tab, height=24, font=("Consolas", 10), wrap="word")
        self.project_text.pack(fill="both", expand=True)

    def _build_api_tab(self) -> None:
        tab = self.tabs["네이버 API"]
        form = ttk.Frame(tab)
        form.pack(fill="x")
        self._row(form, "Client ID", ttk.Entry(form, textvariable=self.client_id), 0)
        self._row(form, "Client Secret", ttk.Entry(form, textvariable=self.client_secret, show="*"), 1)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="저장", command=self.save_keys).pack(side="left")
        ttk.Button(actions, text="삭제", command=self.delete_keys).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Static Map API 테스트", command=self.test_static_api).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(actions, text="저장/분석 동의", variable=self.allow_static_storage).pack(side="left", padx=(12, 0))
        ttk.Button(actions, text="Static Map 배경 다운로드", command=self.download_static_background).pack(side="left", padx=(8, 0))
        ttk.Label(tab, text="%APPDATA%\\ArnisKorea\\secrets.json 에 저장합니다. 키 원문은 로그와 프로젝트 폴더에 쓰지 않습니다. 저장/분석 동의가 있을 때만 raster를 프로젝트에 저장합니다.").pack(anchor="w", pady=(0, 8))
        self.api_result = ScrolledText(tab, height=22, font=("Consolas", 10), wrap="word")
        self.api_result.pack(fill="both", expand=True)

    def _build_bbox_tab(self) -> None:
        tab = self.tabs["지도 범위"]
        form = ttk.Frame(tab)
        form.pack(fill="x")
        self._row(form, "bbox", ttk.Entry(form, textvariable=self.bbox), 0)
        self._row(form, "스폰 lat", ttk.Entry(form, textvariable=self.spawn_lat), 1)
        self._row(form, "스폰 lng", ttk.Entry(form, textvariable=self.spawn_lng), 2)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="HUFS 샘플 bbox", command=self.set_hufs_bbox).pack(side="left")
        ttk.Button(actions, text="bbox 중심 자동", command=self.set_spawn_center).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="요청 계획 표시", command=self.show_request_plan).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Dynamic selector 열기", command=self.open_selector).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="selector 결과 JSON import", command=self.import_selector_json).pack(side="left", padx=(8, 0))
        self.map_result = ScrolledText(tab, height=24, font=("Consolas", 10), wrap="word")
        self.map_result.pack(fill="both", expand=True)

    def _build_layer_tab(self) -> None:
        tab = self.tabs["레이어 편집"]
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(left, text="레이어").pack(anchor="w")
        ttk.Combobox(left, textvariable=self.current_layer, values=["road", "building", "water", "green", "rail", "spawn"], state="readonly", width=18).pack(fill="x", pady=(4, 8))
        ttk.Entry(left, textvariable=self.feature_name).pack(fill="x", pady=4)
        ttk.Entry(left, textvariable=self.feature_memo).pack(fill="x", pady=4)
        ttk.Button(left, text="점 초기화", command=self.clear_canvas_points).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="feature 저장", command=self.save_canvas_feature).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="선택 feature 삭제", command=self.delete_selected_accepted).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="mock 후보 생성", command=self.generate_mock_suggested).pack(fill="x", pady=(12, 0))
        ttk.Button(left, text="suggested 승인", command=self.approve_selected_suggested).pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(left, text="suggested 보기", variable=self.show_suggested, command=self.draw_canvas).pack(anchor="w", pady=(12, 0))
        for name, var in self.layer_visible.items():
            ttk.Checkbutton(left, text=name, variable=var, command=self.draw_canvas).pack(anchor="w")
        ttk.Label(left, text="Accepted").pack(anchor="w", pady=(12, 2))
        self.accepted_list = Listbox(left, width=34, height=8)
        self.accepted_list.pack(fill="x")
        ttk.Label(left, text="Suggested").pack(anchor="w", pady=(12, 2))
        self.suggested_list = Listbox(left, width=34, height=8)
        self.suggested_list.pack(fill="x")

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        self.canvas = Canvas(right, background="#f7f3e8", highlightthickness=1, highlightbackground="#d1d5db")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.add_canvas_point)
        ttk.Label(right, text="배경은 mock 또는 저장 동의한 Static Map raster만 표시합니다. 클릭으로 점을 추가한 뒤 feature 저장을 누르세요.").pack(anchor="w", pady=(6, 0))

    def _build_export_tab(self) -> None:
        tab = self.tabs["내보내기"]
        ttk.Label(tab, text="v1.0에서는 레이어 편집과 내보내기까지 지원합니다. Minecraft 월드 생성은 v1.1에서 Arnis Writer와 연결됩니다.").pack(anchor="w")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="accepted_layers.geojson export", command=self.export_accepted).pack(side="left")
        ttk.Button(actions, text="synthetic_osm_preview.json export", command=self.export_synthetic).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="source-policy-report.json 생성", command=self.write_source_policy).pack(side="left", padx=(8, 0))
        self.export_result = ScrolledText(tab, height=24, font=("Consolas", 10), wrap="word")
        self.export_result.pack(fill="both", expand=True)

    def _build_report_tab(self) -> None:
        tab = self.tabs["검수/리포트"]
        actions = ttk.Frame(tab)
        actions.pack(fill="x")
        ttk.Button(actions, text="검수 실행", style="Primary.TButton", command=self.validate_action).pack(side="left")
        ttk.Button(actions, text="reports 폴더 열기", command=lambda: open_path(project_paths(Path(self.project_dir.get()))["reports"])).pack(side="left", padx=(8, 0))
        self.report_result = ScrolledText(tab, height=26, font=("Consolas", 10), wrap="word")
        self.report_result.pack(fill="both", expand=True, pady=(10, 0))

    def _build_help_tab(self) -> None:
        text = (
            "사용 순서\n"
            "1. 프로젝트 탭에서 새 프로젝트를 만듭니다.\n"
            "2. 지도 범위 탭에서 bbox와 스폰포인트를 확인합니다.\n"
            "3. 네이버 API 탭에서 공식 Static Map API 키를 저장하고 테스트합니다.\n"
            "4. 레이어 편집 탭에서 도로/건물/수역/녹지/철도/스폰포인트를 직접 그립니다.\n"
            "5. suggested 후보는 승인 버튼을 눌러야 accepted layer로 들어갑니다.\n"
            "6. 내보내기 탭에서 accepted_layers.geojson과 synthetic_osm_preview.json을 생성합니다.\n\n"
            f"공식 Static Map API와 사용자 수동 trace만 v1.0 입력으로 사용합니다. 월드 생성은 v1.1 목표입니다.\n\n로그 파일: {LATEST_LOG}"
        )
        ttk.Label(self.tabs["도움말"], text=text, justify="left").pack(anchor="nw")
        ttk.Button(self.tabs["도움말"], text="로그 보기", command=self.open_latest_log).pack(anchor="w", pady=(12, 0))

    def _load_saved_keys(self) -> None:
        if not SECRETS_PATH.exists():
            return
        try:
            data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
            self.client_id.set(data.get("client_id", ""))
            self.client_secret.set(data.get("client_secret", ""))
        except Exception:
            return

    def choose_project_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_dir.get() or str(ROOT))
        if selected:
            self.project_dir.set(selected)
            self.refresh_project_view()

    def create_project_action(self) -> None:
        try:
            bbox = parse_bbox_text(self.bbox.get())
            spawn = {"lat": float(self.spawn_lat.get()), "lng": float(self.spawn_lng.get())}
            project = create_project(Path(self.project_dir.get()), self.project_name.get(), bbox, spawn)
            self.write_project_text(project)
            self.refresh_layer_lists()
            self.draw_canvas()
        except Exception as exc:
            messagebox.showerror("프로젝트 생성 실패", str(exc))

    def load_project_action(self) -> None:
        try:
            project = load_project(Path(self.project_dir.get()))
            self.project_name.set(project.get("project_name", ""))
            self.bbox.set(bbox_to_text(project["bbox"]))
            spawn = project.get("spawn_point", {})
            self.spawn_lat.set(str(spawn.get("lat", "")))
            self.spawn_lng.set(str(spawn.get("lng", "")))
            self.write_project_text(project)
            self.refresh_layer_lists()
            self.draw_canvas()
        except Exception as exc:
            messagebox.showerror("불러오기 실패", str(exc))

    def refresh_project_view(self) -> None:
        if self.safe_mode:
            self.write_project_text({"safe_mode": True, "status": "안전 모드입니다. 최근 프로젝트와 API 키를 자동으로 불러오지 않습니다.", "log": str(LATEST_LOG)})
            return
        path = project_paths(Path(self.project_dir.get()))["project"]
        if path.exists():
            self.write_project_text(read_json(path))
        else:
            self.write_project_text({"project_dir": self.project_dir.get(), "status": "프로젝트 파일이 아직 없습니다."})

    def write_project_text(self, data: dict[str, object]) -> None:
        self.project_text.delete("1.0", "end")
        self.project_text.insert("end", safe_json(data))

    def open_latest_log(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if not LATEST_LOG.exists():
            LATEST_LOG.write_text("아직 기록된 오류가 없습니다.\n", encoding="utf-8")
        if sys.platform.startswith("win"):
            os.startfile(str(LATEST_LOG))  # type: ignore[attr-defined]
        else:
            webbrowser.open(LATEST_LOG.as_uri())

    def save_keys(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        write_json(SECRETS_PATH, {"client_id": self.client_id.get().strip(), "client_secret": self.client_secret.get().strip()})
        self.write_api({"saved": True, "path": str(SECRETS_PATH), "client_id_present": bool(self.client_id.get().strip()), "client_secret_present": bool(self.client_secret.get().strip())})

    def delete_keys(self) -> None:
        if SECRETS_PATH.exists():
            SECRETS_PATH.unlink()
        self.client_id.set("")
        self.client_secret.set("")
        self.write_api({"deleted": True, "path": str(SECRETS_PATH)})

    def test_static_api(self) -> None:
        def worker() -> None:
            try:
                plan = split_static_map_requests(parse_bbox_text(self.bbox.get()), level=16, width=640, height=640, scale=1, maptype="basic", fmt="png")
                params = plan["tiles"][0]["params"]
                url = f"{STATIC_ENDPOINT}?{urllib.parse.urlencode(params)}"
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
            self.root.after(0, lambda: self.write_api(result))

        threading.Thread(target=worker, daemon=True).start()

    def download_static_background(self) -> None:
        if not self.allow_static_storage.get():
            messagebox.showwarning("동의 필요", "Static Map raster 저장/분석 동의가 필요합니다.")
            return

        def worker() -> None:
            try:
                project_dir = Path(self.project_dir.get())
                paths = project_paths(project_dir)
                if paths["project"].exists():
                    project = load_project(project_dir)
                    project["bbox"] = parse_bbox_text(self.bbox.get())
                    project["spawn_point"] = {"lat": float(self.spawn_lat.get()), "lng": float(self.spawn_lng.get())}
                    project["naver_static_map_request_plan"] = split_static_map_requests(project["bbox"], level=16, width=1024, height=1024, scale=2, maptype="basic", fmt="png")
                else:
                    project = create_project(project_dir, self.project_name.get(), parse_bbox_text(self.bbox.get()), {"lat": float(self.spawn_lat.get()), "lng": float(self.spawn_lng.get())})
                params = project["naver_static_map_request_plan"]["tiles"][0]["params"]
                headers = {"x-ncp-apigw-api-key-id": self.client_id.get().strip(), "x-ncp-apigw-api-key": self.client_secret.get().strip()}
                if not headers["x-ncp-apigw-api-key-id"] or not headers["x-ncp-apigw-api-key"]:
                    result = {"executed": False, "reason": "키를 먼저 입력하세요."}
                else:
                    request = urllib.request.Request(f"{STATIC_ENDPOINT}?{urllib.parse.urlencode(params)}", headers=headers, method="GET")
                    with urllib.request.urlopen(request, timeout=20) as response:
                        body = response.read()
                        raster_dir = project_paths(project_dir)["raster_dir"]
                        raster_dir.mkdir(parents=True, exist_ok=True)
                        output = raster_dir / "static-map-000.png"
                        output.write_bytes(body)
                        project["raster_files"] = [str(output.relative_to(project_dir))]
                        save_project(project_dir, project)
                        result = {"executed": True, "status": response.status, "content_type": response.headers.get("content-type"), "bytes": len(body), "sha256_prefix": hashlib.sha256(body).hexdigest()[:16], "saved_to": str(output)}
                self.root.after(0, lambda: self.after_static_download(result))
            except Exception as exc:
                result = {"executed": True, "status": "error", "error_type": type(exc).__name__, "message": str(exc)}
                self.root.after(0, lambda: self.after_static_download(result))

        threading.Thread(target=worker, daemon=True).start()

    def after_static_download(self, result: dict[str, object]) -> None:
        self.write_api(result)
        path_text = result.get("saved_to")
        if isinstance(path_text, str):
            self.load_canvas_background(Path(path_text))
            self.refresh_project_view()

    def write_api(self, data: dict[str, object]) -> None:
        self.api_result.delete("1.0", "end")
        self.api_result.insert("end", safe_json(data))

    def set_hufs_bbox(self) -> None:
        self.bbox.set(bbox_to_text(HUFS_BBOX))
        self.set_spawn_center()
        self.show_request_plan()

    def set_spawn_center(self) -> None:
        center = bbox_center(parse_bbox_text(self.bbox.get()))
        self.spawn_lat.set(f"{center['lat']:.8f}")
        self.spawn_lng.set(f"{center['lng']:.8f}")

    def show_request_plan(self) -> None:
        try:
            bbox = parse_bbox_text(self.bbox.get())
            plan = split_static_map_requests(bbox, level=16, width=1024, height=1024, scale=2, maptype="basic", fmt="png")
            warning = "너무 큰 bbox입니다. 작은 범위부터 편집하세요." if plan["grid"]["request_count"] > 4 else "요청 수가 MVP 편집에 적합합니다."
            data = {"request_count": plan["grid"]["request_count"], "plan": plan, "warning": warning}
            self.map_result.delete("1.0", "end")
            self.map_result.insert("end", safe_json(data))
            paths = project_paths(Path(self.project_dir.get()))
            if paths["project"].exists():
                project = load_project(Path(self.project_dir.get()))
                project["bbox"] = bbox
                project["spawn_point"] = {"lat": float(self.spawn_lat.get()), "lng": float(self.spawn_lng.get())}
                project["naver_static_map_request_plan"] = plan
                save_project(Path(self.project_dir.get()), project)
                self.write_project_text(project)
        except Exception as exc:
            self.map_result.delete("1.0", "end")
            self.map_result.insert("end", str(exc))

    def open_selector(self) -> None:
        selector = ROOT / "web" / "dynamic_selector.html"
        webbrowser.open(selector.resolve().as_uri())

    def import_selector_json(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        data = read_json(Path(path))
        bbox = data.get("bbox", data)
        self.bbox.set(bbox_to_text(bbox))
        self.set_spawn_center()
        self.show_request_plan()

    def add_canvas_point(self, event: object) -> None:
        self.canvas_points.append((float(event.x), float(event.y)))  # type: ignore[attr-defined]
        self.draw_canvas()

    def clear_canvas_points(self) -> None:
        self.canvas_points.clear()
        self.draw_canvas()

    def canvas_to_lng_lat(self, point: tuple[float, float]) -> list[float]:
        bbox = parse_bbox_text(self.bbox.get())
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        x, y = point
        lng = bbox["min_lng"] + (x / width) * (bbox["max_lng"] - bbox["min_lng"])
        lat = bbox["max_lat"] - (y / height) * (bbox["max_lat"] - bbox["min_lat"])
        return [round(lng, 8), round(lat, 8)]

    def save_canvas_feature(self) -> None:
        layer = self.current_layer.get()
        coords = [self.canvas_to_lng_lat(point) for point in self.canvas_points]
        if layer == "spawn":
            item = feature("spawn", "Point", [float(self.spawn_lng.get()), float(self.spawn_lat.get())], self.feature_name.get(), self.feature_memo.get())
        elif layer in {"road", "rail"}:
            if len(coords) < 2:
                messagebox.showwarning("점 부족", "polyline은 2개 이상의 점이 필요합니다.")
                return
            item = feature(layer, "LineString", coords, self.feature_name.get(), self.feature_memo.get())
        else:
            if len(coords) < 3:
                messagebox.showwarning("점 부족", "polygon은 3개 이상의 점이 필요합니다.")
                return
            ring = coords + [coords[0]]
            item = feature(layer, "Polygon", [ring], self.feature_name.get(), self.feature_memo.get())
        add_feature(Path(self.project_dir.get()), "accepted", item)
        export_synthetic_osm_preview(Path(self.project_dir.get()))
        self.clear_canvas_points()
        self.refresh_layer_lists()

    def delete_selected_accepted(self) -> None:
        selection = self.accepted_list.curselection()
        if not selection:
            return
        paths = project_paths(Path(self.project_dir.get()))
        data = read_json(paths["accepted"])
        del data["features"][selection[0]]
        write_json(paths["accepted"], data)
        export_synthetic_osm_preview(Path(self.project_dir.get()))
        self.refresh_layer_lists()
        self.draw_canvas()

    def generate_mock_suggested(self) -> None:
        try:
            from arnis_korea_detailed.trace_editor_core import write_mock_raster

            path = write_mock_raster(project_paths(Path(self.project_dir.get()))["previews"] / "mock_background.ppm")
            self.load_canvas_background(path)
            suggested = extract_suggested_layers(Path(self.project_dir.get()), path)
            self.export_result.delete("1.0", "end")
            self.export_result.insert("end", safe_json({"mock_raster": str(path), "suggested_features": len(suggested["features"])}))
            self.refresh_layer_lists()
            self.draw_canvas()
        except Exception as exc:
            messagebox.showerror("후보 생성 실패", str(exc))

    def approve_selected_suggested(self) -> None:
        selection = list(self.suggested_list.curselection())
        if not selection:
            messagebox.showwarning("선택 필요", "승인할 suggested feature를 선택하세요.")
            return
        count = approve_suggested(Path(self.project_dir.get()), selection)
        export_synthetic_osm_preview(Path(self.project_dir.get()))
        self.refresh_layer_lists()
        self.draw_canvas()
        self.status.set(f"{count}개 suggested feature를 accepted layer로 승인했습니다.")

    def refresh_layer_lists(self) -> None:
        paths = project_paths(Path(self.project_dir.get()))
        accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
        suggested = read_json(paths["suggested"]) if paths["suggested"].exists() else empty_feature_collection()
        self.accepted_list.delete(0, "end")
        for idx, item in enumerate(accepted.get("features", [])):
            props = item.get("properties", {})
            self.accepted_list.insert("end", f"{idx}: {props.get('layer')} {props.get('name', '')}")
        self.suggested_list.delete(0, "end")
        for idx, item in enumerate(suggested.get("features", [])):
            props = item.get("properties", {})
            self.suggested_list.insert("end", f"{idx}: {props.get('layer')} confidence={props.get('confidence', '')}")

    def draw_canvas(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if self.background_image is not None:
            self.canvas.create_image(0, 0, image=self.background_image, anchor="nw")
        else:
            self.canvas.create_rectangle(0, 0, width, height, fill="#f7f3e8", outline="")
            self.canvas.create_text(16, 16, anchor="nw", text="Naver Static Map 배경 또는 mock 배경", fill="#6b7280", font=("Malgun Gothic", 10))
        paths = project_paths(Path(self.project_dir.get()))
        if paths["accepted"].exists():
            self.draw_geojson(read_json(paths["accepted"]), dashed=False)
        if self.show_suggested.get() and paths["suggested"].exists():
            self.draw_geojson(read_json(paths["suggested"]), dashed=True)
        for x, y in self.canvas_points:
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#111827", outline="")

    def load_canvas_background(self, path: Path) -> None:
        try:
            self.background_image = PhotoImage(file=str(path))
            self.draw_canvas()
        except Exception:
            self.background_image = None
            self.draw_canvas()

    def lng_lat_to_canvas(self, coord: list[float]) -> tuple[float, float]:
        bbox = parse_bbox_text(self.bbox.get())
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        lng, lat = coord
        x = (lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * width
        y = (bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * height
        return x, y

    def draw_geojson(self, data: dict[str, object], dashed: bool) -> None:
        colors = {"road": "#4b5563", "building": "#9f7aea", "water": "#2563eb", "green": "#16a34a", "rail": "#111827", "spawn": "#dc2626"}
        for item in data.get("features", []):  # type: ignore[union-attr]
            props = item.get("properties", {})  # type: ignore[union-attr]
            layer = props.get("layer", "road")
            if not self.layer_visible.get(layer, BooleanVar(value=True)).get():
                continue
            geometry = item.get("geometry", {})  # type: ignore[union-attr]
            color = colors.get(layer, "#111827")
            dash = (4, 3) if dashed else None
            if geometry.get("type") == "Point":
                x, y = self.lng_lat_to_canvas(geometry["coordinates"])
                self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=color, outline="")
            elif geometry.get("type") == "LineString":
                points = [xy for coord in geometry["coordinates"] for xy in self.lng_lat_to_canvas(coord)]
                if len(points) >= 4:
                    self.canvas.create_line(*points, fill=color, width=3, dash=dash)
            elif geometry.get("type") == "Polygon":
                ring = geometry["coordinates"][0]
                points = [xy for coord in ring for xy in self.lng_lat_to_canvas(coord)]
                if len(points) >= 6:
                    self.canvas.create_polygon(*points, fill=color, stipple="gray25", outline=color, width=2, dash=dash)

    def export_accepted(self) -> None:
        path = export_accepted_layers(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json({"exported": str(path)}))

    def export_synthetic(self) -> None:
        data = export_synthetic_osm_preview(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json(data))

    def write_source_policy(self) -> None:
        from arnis_korea_detailed.trace_editor_core import source_policy_report

        report = source_policy_report(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json(report))

    def validate_action(self) -> None:
        report = validate_project(Path(self.project_dir.get()))
        self.report_result.delete("1.0", "end")
        self.report_result.insert("end", safe_json(report))


def self_test_gui(safe_mode: bool = False) -> int:
    write_boot_log(f"GUI_SELF_TEST_START safe_mode={safe_mode}")
    root = Tk()
    root.withdraw()
    TraceEditorApp(root, safe_mode=safe_mode)
    root.update_idletasks()
    root.destroy()
    write_boot_log(f"GUI_SELF_TEST_PASS safe_mode={safe_mode}")
    print("KOREAN_GUI_SELF_TEST=PASS")
    return 0


def show_startup_error() -> None:
    message = f"Arnis Korea를 시작하지 못했습니다. 자세한 내용은 {LATEST_LOG} 를 확인하세요."
    try:
        root = Tk()
        root.withdraw()
        messagebox.showerror("Arnis Korea 시작 실패", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def run_app(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test-gui", action="store_true")
    parser.add_argument("--safe-mode", action="store_true")
    args = parser.parse_args(argv)
    if CORE_IMPORT_ERROR is not None:
        raise RuntimeError("GUI core import failed") from CORE_IMPORT_ERROR
    if args.self_test_gui:
        return self_test_gui(safe_mode=args.safe_mode)
    write_boot_log(f"GUI_BOOT_START safe_mode={args.safe_mode}")
    root = Tk()
    TraceEditorApp(root, safe_mode=args.safe_mode)
    write_boot_log(f"GUI_BOOT_OK safe_mode={args.safe_mode}")
    root.mainloop()
    return 0


def main() -> int:
    try:
        return run_app()
    except Exception as exc:
        write_boot_log("GUI_BOOT_FAIL", exc)
        show_startup_error()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
