#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
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
    from tkinter import BooleanVar, Canvas, Listbox, PhotoImage, StringVar, Tk, Toplevel, filedialog, messagebox, ttk
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
        export_ai_trace_package,
        export_synthetic_osm_preview,
        extract_suggested_layers,
        feature,
        iter_geometry_points,
        lng_lat_to_pixel,
        pixel_to_lng_lat,
        load_project,
        parse_bbox_text,
        project_paths,
        read_json,
        import_ai_trace_results,
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
RECENTS_PATH = APP_DIR / "recent_projects.json"
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
        self.drag_snapshot_taken = False
        self.edit_session = LayerEditSession(Path(self.project_dir.get()))
        self.world_name = StringVar(value="HUFS Trace World")
        self.world_output_dir = StringVar(value=str(Path(self.project_dir.get()) / "playable_world"))
        self.copy_to_saves = BooleanVar(value=False)
        self.overwrite_saves = BooleanVar(value=False)
        self.run_local_load_smoke = BooleanVar(value=False)
        self.minecraft_saves_dir = StringVar(value=str(Path.home() / "AppData" / "Roaming" / ".minecraft" / "saves"))
        self.building_height_mode = StringVar(value="low-rise")
        self.world_terrain = BooleanVar(value=False)
        self.world_roof = BooleanVar(value=True)
        self.world_interior = BooleanVar(value=False)
        self.world_scale = StringVar(value="1.0")
        self.ai_package_dir = StringVar(value=str(Path(self.project_dir.get()) / "ai_trace_package"))
        self.ai_results_dir = StringVar(value=str(Path(self.project_dir.get()) / "ai_trace_results"))
        self.current_step = StringVar(value="start")
        self.api_key_status = StringVar(value="미설정")
        self.layer_counts = StringVar(value="도로 0개  건물 0개  녹지 0개  수역 0개  철도 0개")
        self.wizard_status_vars = {
            "bbox": StringVar(value="필요함"),
            "layers": StringVar(value="필요함"),
            "world_name": StringVar(value="필요함"),
            "worldgen": StringVar(value="필요함"),
            "saves": StringVar(value="필요함"),
        }
        self.recent_projects = self._load_recent_projects() if not safe_mode else []
        self.advanced_window = None
        self.api_settings_window = None
        self.troubleshooting_window = None

        self._style()
        if not self.safe_mode:
            self._load_saved_keys()
        self._build()
        self.refresh_api_status()
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
        self.outer = outer
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Arnis Korea - 네이버 지도 월드 생성기", style="Title.TLabel").pack(anchor="w")
        self.status = StringVar(value="3단계로 지도 범위를 정하고, 승인된 레이어를 확인한 뒤 Minecraft 월드로 내보냅니다.")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(4, 10))

        self.advanced_host = ttk.Frame(outer)
        advanced_bar = ttk.Frame(self.advanced_host)
        advanced_bar.pack(fill="x", pady=(0, 8))
        ttk.Button(advanced_bar, text="초보자 모드로 돌아가기", command=self.close_advanced_settings).pack(side="left")
        notebook = ttk.Notebook(self.advanced_host)
        notebook.pack(fill="both", expand=True)
        self.advanced_notebook = notebook
        self.tabs: dict[str, ttk.Frame] = {}
        for label in ["프로젝트", "네이버 API", "지도 범위", "레이어 편집", "AI Trace", "내보내기", "월드 생성", "최종 생성 마법사", "문제 해결", "검수/리포트", "도움말"]:
            frame = ttk.Frame(notebook, padding=12)
            notebook.add(frame, text=label)
            self.tabs[label] = frame
        self._build_project_tab()
        self._build_api_tab()
        self._build_bbox_tab()
        self._build_layer_tab()
        self._build_ai_trace_tab()
        self._build_export_tab()
        self._build_worldgen_tab()
        self._build_final_wizard_tab()
        self._build_troubleshooting_tab()
        self._build_report_tab()
        self._build_help_tab()
        self._build_simple_wizard(outer)

    def _build_simple_wizard(self, outer: ttk.Frame) -> None:
        shell = ttk.Frame(outer)
        self.simple_shell = shell
        shell.pack(fill="both", expand=True)
        progress = ttk.Frame(shell)
        progress.pack(side="left", fill="y", padx=(0, 14))
        self.step_buttons = {}
        for key, label in [("start", "1. 시작하기"), ("map", "2. 지도 만들기"), ("export", "3. 마인크래프트로 내보내기")]:
            button = ttk.Button(progress, text=label, command=lambda key=key: self.show_wizard_step(key))
            button.pack(fill="x", pady=(0, 8))
            self.step_buttons[key] = button
        ttk.Separator(progress).pack(fill="x", pady=8)
        ttk.Button(progress, text="고급 설정 열기", command=self.open_advanced_settings).pack(fill="x", pady=(0, 8))

        content = ttk.Frame(shell)
        content.pack(side="left", fill="both", expand=True)
        self.wizard_frames: dict[str, ttk.Frame] = {}
        for key in ["start", "map", "export"]:
            frame = ttk.Frame(content)
            frame.grid(row=0, column=0, sticky="nsew")
            self.wizard_frames[key] = frame
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self._build_wizard_start(self.wizard_frames["start"])
        self._build_wizard_map(self.wizard_frames["map"])
        self._build_wizard_export(self.wizard_frames["export"])

        footer = ttk.Frame(outer)
        self.simple_footer = footer
        footer.pack(fill="x", pady=(10, 0))
        ttk.Button(footer, text="로그", command=self.open_latest_log).pack(side="right")
        ttk.Button(footer, text="문제 해결", command=self.open_troubleshooting).pack(side="right", padx=(0, 8))
        self.show_wizard_step("start")

    def _build_wizard_start(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="시작하기", style="Title.TLabel").pack(anchor="w")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(14, 10))
        ttk.Button(actions, text="새 지도 만들기", style="Primary.TButton", command=self.create_project_from_wizard).pack(side="left")
        ttk.Button(actions, text="기존 프로젝트 열기", command=self.open_project_from_wizard).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="도움말", command=self.show_beginner_help).pack(side="left", padx=(8, 0))
        api = ttk.Frame(frame)
        api.pack(fill="x", pady=(4, 10))
        ttk.Label(api, text="네이버 API 키 상태").pack(side="left")
        ttk.Label(api, textvariable=self.api_key_status).pack(side="left", padx=(8, 16))
        ttk.Button(api, text="API 키 설정", command=self.open_api_settings).pack(side="left")
        ttk.Label(frame, text="최근 프로젝트").pack(anchor="w", pady=(12, 4))
        self.recent_list = Listbox(frame, height=8)
        self.recent_list.pack(fill="x")
        self.recent_list.bind("<Double-Button-1>", lambda _event: self.open_selected_recent_project())
        ttk.Button(frame, text="최근 프로젝트 열기", command=self.open_selected_recent_project).pack(anchor="w", pady=(8, 0))

    def _build_wizard_map(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="지도 만들기", style="Title.TLabel").pack(anchor="w")
        form = ttk.Frame(frame)
        form.pack(fill="x", pady=(14, 8))
        self._row(form, "지도 범위", ttk.Entry(form, textvariable=self.bbox), 0)
        self._row(form, "스폰 lat", ttk.Entry(form, textvariable=self.spawn_lat), 1)
        self._row(form, "스폰 lng", ttk.Entry(form, textvariable=self.spawn_lng), 2)
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="위치/범위 선택", command=self.open_selector).pack(side="left")
        ttk.Button(actions, text="네이버 지도 불러오기", command=self.download_static_background).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="AI 후보 생성", command=self.generate_mock_suggested).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="레이어 확인/수정", command=self.open_layer_editor).pack(side="left", padx=(8, 0))
        ttk.Label(frame, text="승인된 레이어 수").pack(anchor="w", pady=(12, 4))
        ttk.Label(frame, textvariable=self.layer_counts).pack(anchor="w")
        ttk.Button(frame, text="다음: 월드 생성", style="Primary.TButton", command=lambda: self.show_wizard_step("export")).pack(anchor="w", pady=(18, 0))

    def _build_wizard_export(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="마인크래프트로 내보내기", style="Title.TLabel").pack(anchor="w")
        status = ttk.Frame(frame)
        status.pack(fill="x", pady=(14, 10))
        for row, (key, label) in enumerate([
            ("bbox", "1. 지도 범위 확인"),
            ("layers", "2. 승인된 레이어 확인"),
            ("world_name", "3. 월드 이름 입력"),
            ("worldgen", "4. 월드 생성"),
            ("saves", "5. Minecraft saves로 복사"),
        ]):
            ttk.Label(status, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Label(status, textvariable=self.wizard_status_vars[key]).grid(row=row, column=1, sticky="w", padx=(14, 0), pady=3)
        form = ttk.Frame(frame)
        form.pack(fill="x", pady=(6, 8))
        self._row(form, "월드 이름", ttk.Entry(form, textvariable=self.world_name), 0)
        self._row(form, "출력 폴더", ttk.Entry(form, textvariable=self.world_output_dir), 1, ttk.Button(form, text="선택", command=self.choose_world_output_dir))
        self._row(form, "Minecraft saves", ttk.Entry(form, textvariable=self.minecraft_saves_dir), 2, ttk.Button(form, text="선택", command=self.choose_saves_dir))
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(6, 10))
        ttk.Button(actions, text="월드 생성", style="Primary.TButton", command=self.generate_world_action).pack(side="left")
        ttk.Button(actions, text="Minecraft saves로 복사", command=self.copy_world_to_saves_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="생성된 월드 폴더 열기", command=self.open_generated_world).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="게임에서 여는 방법 보기", command=self.show_minecraft_open_help).pack(side="left", padx=(8, 0))
        self.wizard_export_result = ScrolledText(frame, height=12, font=("Consolas", 10), wrap="word")
        self.wizard_export_result.pack(fill="both", expand=True)

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
        self._row(form, "지도 범위", ttk.Entry(form, textvariable=self.bbox), 0)
        self._row(form, "스폰 lat", ttk.Entry(form, textvariable=self.spawn_lat), 1)
        self._row(form, "스폰 lng", ttk.Entry(form, textvariable=self.spawn_lng), 2)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="HUFS 샘플 지도 범위", command=self.set_hufs_bbox).pack(side="left")
        ttk.Button(actions, text="지도 범위 중심 자동", command=self.set_spawn_center).pack(side="left", padx=(8, 0))
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
        modes = ttk.Frame(left)
        modes.pack(fill="x", pady=(0, 8))
        for text, value in [("그리기", "draw"), ("선택", "select"), ("이동", "pan")]:
            ttk.Radiobutton(modes, text=text, variable=self.edit_mode, value=value).pack(side="left")
        ttk.Entry(left, textvariable=self.feature_name).pack(fill="x", pady=4)
        ttk.Entry(left, textvariable=self.feature_memo).pack(fill="x", pady=4)
        zoom = ttk.Frame(left)
        zoom.pack(fill="x", pady=(6, 0))
        ttk.Button(zoom, text="+", command=lambda: self.zoom_canvas(1.25)).pack(side="left", fill="x", expand=True)
        ttk.Button(zoom, text="-", command=lambda: self.zoom_canvas(0.8)).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ttk.Button(zoom, text="Reset", command=self.reset_view).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ttk.Button(left, text="점 초기화", command=self.clear_canvas_points).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="레이어 저장", command=self.save_canvas_feature).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="이름/메모/종류 적용", command=self.apply_selected_properties).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="선택 점 삭제", command=self.delete_selected_vertex).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="선택 레이어 삭제", command=self.delete_selected_accepted).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="Undo", command=self.undo_edit).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="Redo", command=self.redo_edit).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="AI 후보 생성", command=self.generate_mock_suggested).pack(fill="x", pady=(12, 0))
        ttk.Button(left, text="AI 후보 승인", command=self.approve_selected_suggested).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="승인된 레이어를 AI 후보로 되돌리기", command=self.revert_selected_accepted).pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(left, text="AI 후보 보기", variable=self.show_suggested, command=self.draw_canvas).pack(anchor="w", pady=(12, 0))
        for name, var in self.layer_visible.items():
            ttk.Checkbutton(left, text=name, variable=var, command=self.draw_canvas).pack(anchor="w")
        ttk.Label(left, text="승인된 레이어").pack(anchor="w", pady=(12, 2))
        self.accepted_list = Listbox(left, width=34, height=8)
        self.accepted_list.pack(fill="x")
        self.accepted_list.bind("<<ListboxSelect>>", self.on_accepted_select)
        ttk.Label(left, text="AI 후보").pack(anchor="w", pady=(12, 2))
        self.suggested_list = Listbox(left, width=34, height=8)
        self.suggested_list.pack(fill="x")

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        self.canvas = Canvas(right, background="#f7f3e8", highlightthickness=1, highlightbackground="#d1d5db")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_down)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_up)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self.zoom_canvas(1.1, event.x, event.y))
        self.canvas.bind("<Button-5>", lambda event: self.zoom_canvas(0.9, event.x, event.y))
        ttk.Label(right, text="그리기: 점 추가 후 레이어 저장. 선택: 레이어/점을 선택하고 점 이동/삭제. 이동: 배경 이동. 휠: 확대/축소.").pack(anchor="w", pady=(6, 0))

    def _build_export_tab(self) -> None:
        tab = self.tabs["내보내기"]
        ttk.Label(tab, text="승인된 레이어와 월드 생성용 변환 데이터만 월드 생성에 사용합니다. AI 후보는 월드 생성 입력이 아닙니다.").pack(anchor="w")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="승인된 레이어 직접 내보내기", command=self.export_accepted).pack(side="left")
        ttk.Button(actions, text="월드 생성용 변환 데이터 미리보기", command=self.export_synthetic).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="월드 생성용 변환 데이터 내보내기", command=self.export_synthetic_osm_v11).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="레이어 검사 결과 생성", command=self.export_layer_validation).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="데이터 사용 안전 검사", command=self.write_source_policy).pack(side="left", padx=(8, 0))
        self.export_result = ScrolledText(tab, height=24, font=("Consolas", 10), wrap="word")
        self.export_result.pack(fill="both", expand=True)

    def _build_ai_trace_tab(self) -> None:
        tab = self.tabs["AI Trace"]
        ttk.Label(tab, text="AI 분석은 고급 도구에서 수행합니다. 결과는 AI 후보로 가져오며 사용자가 승인해야 승인된 레이어가 됩니다.").pack(anchor="w")
        form = ttk.Frame(tab)
        form.pack(fill="x", pady=(10, 0))
        self._row(form, "분석 패키지 폴더", ttk.Entry(form, textvariable=self.ai_package_dir), 0, ttk.Button(form, text="선택", command=self.choose_ai_package_dir))
        self._row(form, "분석 결과 폴더", ttk.Entry(form, textvariable=self.ai_results_dir), 1, ttk.Button(form, text="선택", command=self.choose_ai_results_dir))
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="OCI AI 분석용 패키지 내보내기", command=self.export_ai_trace_package_action).pack(side="left")
        ttk.Button(actions, text="AI 분석 결과 가져오기", command=self.import_ai_trace_results_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="패키지 폴더 열기", command=lambda: open_path(Path(self.ai_package_dir.get()))).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="결과 폴더 열기", command=lambda: open_path(Path(self.ai_results_dir.get()))).pack(side="left", padx=(8, 0))
        self.ai_trace_result = ScrolledText(tab, height=22, font=("Consolas", 10), wrap="word")
        self.ai_trace_result.pack(fill="both", expand=True)

    def _build_worldgen_tab(self) -> None:
        tab = self.tabs["월드 생성"]
        ttk.Label(tab, text="월드 생성은 승인된 레이어만 사용합니다. 승인되지 않은 AI 후보는 포함하지 않습니다.").pack(anchor="w")
        form = ttk.Frame(tab)
        form.pack(fill="x", pady=(10, 0))
        self._row(form, "월드 이름", ttk.Entry(form, textvariable=self.world_name), 0)
        self._row(form, "출력 폴더", ttk.Entry(form, textvariable=self.world_output_dir), 1, ttk.Button(form, text="선택", command=self.choose_world_output_dir))
        self._row(form, "Minecraft saves", ttk.Entry(form, textvariable=self.minecraft_saves_dir), 2, ttk.Button(form, text="선택", command=self.choose_saves_dir))
        options = ttk.Frame(tab)
        options.pack(fill="x", pady=8)
        ttk.Label(options, text="건물 높이").pack(side="left")
        ttk.Combobox(options, textvariable=self.building_height_mode, values=["footprint", "low-rise", "experimental_full"], state="readonly", width=18).pack(side="left", padx=(6, 14))
        ttk.Checkbutton(options, text="roof", variable=self.world_roof).pack(side="left")
        ttk.Checkbutton(options, text="interior", variable=self.world_interior).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(options, text="terrain experimental", variable=self.world_terrain).pack(side="left", padx=(8, 0))
        ttk.Label(options, text="scale").pack(side="left", padx=(14, 4))
        ttk.Entry(options, textvariable=self.world_scale, width=8).pack(side="left")
        ttk.Checkbutton(options, text="Minecraft saves로 바로 복사", variable=self.copy_to_saves).pack(side="left", padx=(14, 0))
        ttk.Checkbutton(options, text="같은 이름 덮어쓰기", variable=self.overwrite_saves).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(options, text="로컬 마인크래프트 호환성 검사", variable=self.run_local_load_smoke).pack(side="left", padx=(8, 0))
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(4, 10))
        self.worldgen_button = ttk.Button(actions, text="월드 생성", style="Primary.TButton", command=self.generate_world_action)
        self.worldgen_button.pack(side="left")
        ttk.Button(actions, text="생성된 월드 폴더 열기", command=self.open_generated_world).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="프로젝트 폴더 열기", command=lambda: open_path(Path(self.project_dir.get()))).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Minecraft saves로 복사", command=self.copy_world_to_saves_action).pack(side="left", padx=(8, 0))
        self.worldgen_result = ScrolledText(tab, height=22, font=("Consolas", 10), wrap="word")
        self.worldgen_result.pack(fill="both", expand=True)

    def _build_final_wizard_tab(self) -> None:
        tab = self.tabs["최종 생성 마법사"]
        ttk.Label(tab, text="프로젝트 검수부터 월드 생성용 변환 데이터 생성, 월드 생성, 마인크래프트 호환성 검사 선택 실행, Minecraft saves 복사까지 한 화면에서 진행합니다.").pack(anchor="w")
        ttk.Label(tab, text="마법사는 승인된 레이어만 사용합니다. AI 후보는 승인 전까지 후보일 뿐입니다.").pack(anchor="w", pady=(2, 8))
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="1. 프로젝트 상태 체크", command=self.final_check_project).pack(side="left")
        ttk.Button(actions, text="2. 월드 생성용 변환 데이터 생성", command=self.export_synthetic_osm_v11).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="3. 월드 생성 실행", style="Primary.TButton", command=self.generate_world_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="4. Minecraft saves로 복사", command=self.copy_world_to_saves_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="생성된 월드 열기", command=self.open_generated_world).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="검사 결과 열기", command=self.open_reports_dir).pack(side="left", padx=(8, 0))
        self.final_result = ScrolledText(tab, height=24, font=("Consolas", 10), wrap="word")
        self.final_result.pack(fill="both", expand=True)

    def _build_troubleshooting_tab(self) -> None:
        tab = self.tabs["문제 해결"]
        ttk.Label(tab, text="앱이 열리지 않거나 월드 생성이 실패하면 로그와 검사 결과 폴더를 먼저 확인하세요. 키 원문은 공유하지 마세요.").pack(anchor="w")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="로그 열기", command=self.open_latest_log).pack(side="left")
        ttk.Button(actions, text="검사 결과 폴더 열기", command=self.open_reports_dir).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="프로젝트 검수 실행", command=self.validate_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="데이터 사용 안전 검사", command=self.write_source_policy).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="로컬 프로젝트 진단", command=self.local_project_diagnosis).pack(side="left", padx=(8, 0))
        self.troubleshooting_result = ScrolledText(tab, height=24, font=("Consolas", 10), wrap="word")
        self.troubleshooting_result.pack(fill="both", expand=True)

    def _build_report_tab(self) -> None:
        tab = self.tabs["검수/리포트"]
        actions = ttk.Frame(tab)
        actions.pack(fill="x")
        ttk.Button(actions, text="검수 실행", style="Primary.TButton", command=self.validate_action).pack(side="left")
        ttk.Button(actions, text="검사 결과 폴더 열기", command=lambda: open_path(project_paths(Path(self.project_dir.get()))["reports"])).pack(side="left", padx=(8, 0))
        self.report_result = ScrolledText(tab, height=26, font=("Consolas", 10), wrap="word")
        self.report_result.pack(fill="both", expand=True, pady=(10, 0))

    def _build_help_tab(self) -> None:
        text = (
            "사용 순서\n"
            "1. 시작하기 단계에서 새 지도 만들기를 누릅니다.\n"
            "2. 지도 만들기 단계에서 지도 범위와 스폰포인트를 확인합니다.\n"
            "3. 네이버 API 탭에서 공식 Static Map API 키를 저장하고 테스트합니다.\n"
            "4. 레이어 편집 탭에서 도로/건물/수역/녹지/철도/스폰포인트를 직접 그립니다.\n"
            "5. AI 후보는 승인 버튼을 눌러야 승인된 레이어로 들어갑니다.\n"
            "6. 마인크래프트로 내보내기 단계에서 월드를 생성하고 Minecraft saves로 복사합니다.\n\n"
            f"공식 Static Map API와 사용자 수동 편집만 입력으로 사용합니다. 월드 생성은 승인된 레이어만 사용합니다.\n\n로그 파일: {LATEST_LOG}"
        )
        ttk.Label(self.tabs["도움말"], text=text, justify="left").pack(anchor="nw")
        ttk.Button(self.tabs["도움말"], text="로그 보기", command=self.open_latest_log).pack(anchor="w", pady=(12, 0))

    def _load_recent_projects(self) -> list[str]:
        try:
            data = json.loads(RECENTS_PATH.read_text(encoding="utf-8"))
            return [str(item) for item in data if isinstance(item, str)][:8]
        except Exception:
            return []

    def _save_recent_projects(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RECENTS_PATH, self.recent_projects[:8])

    def remember_project(self, path: Path) -> None:
        text = str(path)
        self.recent_projects = [text] + [item for item in self.recent_projects if item != text]
        self.recent_projects = self.recent_projects[:8]
        if not self.safe_mode:
            self._save_recent_projects()
        self.refresh_recent_projects()

    def refresh_recent_projects(self) -> None:
        if not hasattr(self, "recent_list"):
            return
        self.recent_list.delete(0, "end")
        for item in self.recent_projects:
            self.recent_list.insert("end", item)

    def refresh_api_status(self, tested: bool = False) -> None:
        if not self.client_id.get().strip() or not self.client_secret.get().strip():
            self.api_key_status.set("미설정")
        elif tested:
            self.api_key_status.set("설정됨")
        else:
            self.api_key_status.set("테스트 필요")

    def show_wizard_step(self, key: str) -> None:
        self.current_step.set(key)
        self.refresh_api_status(tested=self.api_key_status.get() == "설정됨")
        self.refresh_layer_summary()
        self.refresh_recent_projects()
        self.update_final_wizard_statuses()
        self.wizard_frames[key].tkraise()

    def create_project_from_wizard(self) -> None:
        self.create_project_action()
        self.remember_project(Path(self.project_dir.get()))
        self.show_wizard_step("map")

    def open_project_from_wizard(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_dir.get() or str(ROOT))
        if selected:
            self.project_dir.set(selected)
            self.load_project_action()
            self.remember_project(Path(selected))
            self.show_wizard_step("map")

    def open_selected_recent_project(self) -> None:
        selection = self.recent_list.curselection()
        if not selection:
            return
        self.project_dir.set(self.recent_list.get(selection[0]))
        self.load_project_action()
        self.remember_project(Path(self.project_dir.get()))
        self.show_wizard_step("map")

    def open_advanced_settings(self) -> None:
        self.simple_shell.pack_forget()
        self.simple_footer.pack_forget()
        self.advanced_host.pack(fill="both", expand=True)

    def close_advanced_settings(self) -> None:
        self.advanced_host.pack_forget()
        self.simple_shell.pack(fill="both", expand=True)
        self.simple_footer.pack(fill="x", pady=(10, 0))

    def open_troubleshooting(self) -> None:
        if self.troubleshooting_window is not None and self.troubleshooting_window.winfo_exists():
            self.troubleshooting_window.lift()
            return
        window = Toplevel(self.root)
        self.troubleshooting_window = window
        window.title("문제 해결")
        window.geometry("760x420")
        body = ttk.Frame(window, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="문제가 생기면 로그와 검사 결과를 확인하세요. 키 원문은 공유하지 마세요.").pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="로그 열기", command=self.open_latest_log).pack(side="left")
        ttk.Button(actions, text="검사 결과 폴더 열기", command=self.open_reports_dir).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="프로젝트 검수 실행", command=self.validate_action).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="닫기", command=window.destroy).pack(side="left", padx=(8, 0))
        self.beginner_troubleshooting_result = ScrolledText(body, height=14, font=("Consolas", 10), wrap="word")
        self.beginner_troubleshooting_result.pack(fill="both", expand=True)
        self.beginner_troubleshooting_result.insert("end", safe_json({"latest_log": str(LATEST_LOG), "project_dir": self.project_dir.get()}))

    def open_api_settings(self) -> None:
        if self.api_settings_window is not None and self.api_settings_window.winfo_exists():
            self.api_settings_window.lift()
            return
        window = Toplevel(self.root)
        self.api_settings_window = window
        window.title("API 키 설정")
        window.geometry("560x220")
        body = ttk.Frame(window, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="네이버 API 키 상태").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Label(body, textvariable=self.api_key_status).grid(row=0, column=1, sticky="w", pady=6)
        self._row(body, "Client ID", ttk.Entry(body, textvariable=self.client_id), 1)
        self._row(body, "Client Secret", ttk.Entry(body, textvariable=self.client_secret, show="*"), 2)
        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Button(actions, text="저장", command=self.save_keys).pack(side="left")
        ttk.Button(actions, text="삭제", command=self.delete_keys).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="테스트", command=self.test_static_api).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="닫기", command=window.destroy).pack(side="left", padx=(8, 0))

    def open_layer_editor(self) -> None:
        self.open_advanced_settings()
        self.advanced_notebook.select(self.tabs["레이어 편집"])

    def open_help(self) -> None:
        self.open_advanced_settings()
        self.advanced_notebook.select(self.tabs["도움말"])

    def show_beginner_help(self) -> None:
        messagebox.showinfo(
            "도움말",
            "1. 시작하기에서 새 지도 만들기 또는 기존 프로젝트 열기를 선택합니다.\n"
            "2. 지도 만들기에서 지도 범위, 네이버 지도, AI 후보, 승인된 레이어를 확인합니다.\n"
            "3. 마인크래프트로 내보내기에서 월드 이름을 입력하고 월드를 생성한 뒤 Minecraft saves로 복사합니다.",
        )

    def show_minecraft_open_help(self) -> None:
        messagebox.showinfo("게임에서 여는 방법", "월드를 생성한 뒤 Minecraft saves로 복사하세요. Minecraft Java Edition을 열고 싱글플레이에서 월드 이름을 선택하면 됩니다.")

    def refresh_layer_summary(self) -> None:
        paths = project_paths(Path(self.project_dir.get()))
        accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
        counts = {"road": 0, "building": 0, "green": 0, "water": 0, "rail": 0}
        for item in accepted.get("features", []):
            layer = item.get("properties", {}).get("layer")
            if layer in counts:
                counts[layer] += 1
        self.layer_counts.set(f"도로 {counts['road']}개  건물 {counts['building']}개  녹지 {counts['green']}개  수역 {counts['water']}개  철도 {counts['rail']}개")

    def update_final_wizard_statuses(self, worldgen_done: bool = False, saves_done: bool = False) -> None:
        try:
            parse_bbox_text(self.bbox.get())
            self.wizard_status_vars["bbox"].set("완료")
        except Exception:
            self.wizard_status_vars["bbox"].set("오류")
        paths = project_paths(Path(self.project_dir.get()))
        accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
        self.wizard_status_vars["layers"].set("완료" if accepted.get("features") else "필요함")
        self.wizard_status_vars["world_name"].set("완료" if self.world_name.get().strip() else "필요함")
        if worldgen_done or self._world_dir().exists():
            self.wizard_status_vars["worldgen"].set("완료")
        elif not accepted.get("features"):
            self.wizard_status_vars["worldgen"].set("필요함")
        if saves_done:
            self.wizard_status_vars["saves"].set("완료")

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
            self.sync_edit_session()
            self.refresh_project_view()
            self.remember_project(Path(selected))

    def choose_world_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.world_output_dir.get() or self.project_dir.get() or str(ROOT))
        if selected:
            self.world_output_dir.set(selected)

    def choose_saves_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.minecraft_saves_dir.get() or str(Path.home()))
        if selected:
            self.minecraft_saves_dir.set(selected)

    def choose_ai_package_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.ai_package_dir.get() or self.project_dir.get() or str(ROOT))
        if selected:
            self.ai_package_dir.set(selected)

    def choose_ai_results_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.ai_results_dir.get() or self.project_dir.get() or str(ROOT))
        if selected:
            self.ai_results_dir.set(selected)

    def sync_edit_session(self) -> None:
        self.edit_session = LayerEditSession(Path(self.project_dir.get()))
        self.world_output_dir.set(str(Path(self.project_dir.get()) / "playable_world"))
        self.ai_package_dir.set(str(Path(self.project_dir.get()) / "ai_trace_package"))
        self.ai_results_dir.set(str(Path(self.project_dir.get()) / "ai_trace_results"))
        try:
            from arnis_korea_detailed.trace_worldgen import detect_minecraft_saves_dir

            self.minecraft_saves_dir.set(str(detect_minecraft_saves_dir()))
        except Exception:
            pass

    def create_project_action(self) -> None:
        try:
            bbox = parse_bbox_text(self.bbox.get())
            spawn = {"lat": float(self.spawn_lat.get()), "lng": float(self.spawn_lng.get())}
            project = create_project(Path(self.project_dir.get()), self.project_name.get(), bbox, spawn)
            self.sync_edit_session()
            self.write_project_text(project)
            self.refresh_layer_lists()
            self.draw_canvas()
            self.remember_project(Path(self.project_dir.get()))
        except Exception as exc:
            messagebox.showerror("프로젝트 생성 실패", str(exc))

    def load_project_action(self) -> None:
        try:
            project = load_project(Path(self.project_dir.get()))
            self.sync_edit_session()
            self.project_name.set(project.get("project_name", ""))
            self.world_name.set(project.get("project_name", "Arnis Korea World"))
            self.bbox.set(bbox_to_text(project["bbox"]))
            spawn = project.get("spawn_point", {})
            self.spawn_lat.set(str(spawn.get("lat", "")))
            self.spawn_lng.set(str(spawn.get("lng", "")))
            self.write_project_text(project)
            self.refresh_layer_lists()
            self.draw_canvas()
            self.remember_project(Path(self.project_dir.get()))
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
        self.refresh_api_status()
        self.write_api({"saved": True, "path": str(SECRETS_PATH), "client_id_present": bool(self.client_id.get().strip()), "client_secret_present": bool(self.client_secret.get().strip())})

    def delete_keys(self) -> None:
        if SECRETS_PATH.exists():
            SECRETS_PATH.unlink()
        self.client_id.set("")
        self.client_secret.set("")
        self.refresh_api_status()
        self.write_api({"deleted": True, "path": str(SECRETS_PATH)})

    def test_static_api(self) -> None:
        def worker() -> None:
            try:
                plan = split_static_map_requests(parse_bbox_text(self.bbox.get()), level=16, width=640, height=640, scale=1, maptype="basic", fmt="png")
                params = plan["tiles"][0]["params"]
                url = f"{STATIC_ENDPOINT}?{urllib.parse.urlencode(params)}"
                headers = {"x-ncp-apigw-api-key-id": self.client_id.get().strip(), "x-ncp-apigw-api-key": self.client_secret.get().strip()}
                if not headers["x-ncp-apigw-api-key-id"] or not headers["x-ncp-apigw-api-key"]:
                    result = {"executed": False, "reason": "네이버 API 키가 설정되지 않았습니다."}
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
                    result = {"executed": False, "reason": "네이버 API 키가 설정되지 않았습니다."}
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
        if data.get("executed") is True and data.get("status") == 200:
            self.refresh_api_status(tested=True)
        elif data.get("executed") is True:
            self.refresh_api_status(tested=False)
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

    def on_canvas_down(self, event: object) -> None:
        x = float(event.x)  # type: ignore[attr-defined]
        y = float(event.y)  # type: ignore[attr-defined]
        if self.edit_mode.get() == "pan":
            self.pan_start = (x, y)
            return
        if self.edit_mode.get() == "select":
            self.select_at_canvas(x, y)
            if self.selected_feature_index is not None and self.selected_vertex_index is not None:
                self.dragging_vertex = True
                self.drag_snapshot_taken = False
            self.draw_canvas()
            return
        coord = self.canvas_to_lng_lat((x, y))
        if self.current_layer.get() == "spawn":
            self.canvas_points = [coord]
        else:
            self.canvas_points.append(coord)
        self.draw_canvas()

    def on_canvas_drag(self, event: object) -> None:
        x = float(event.x)  # type: ignore[attr-defined]
        y = float(event.y)  # type: ignore[attr-defined]
        if self.edit_mode.get() == "pan" and self.pan_start is not None:
            start_x, start_y = self.pan_start
            self.pan_x += x - start_x
            self.pan_y += y - start_y
            self.pan_start = (x, y)
            self.draw_canvas()
            return
        if self.dragging_vertex and self.selected_feature_index is not None and self.selected_vertex_index is not None:
            if not self.drag_snapshot_taken:
                self.edit_session.snapshot()
                self.drag_snapshot_taken = True
            data = self.edit_session.read()
            if self.set_feature_vertex(data, self.selected_feature_index, self.selected_vertex_index, self.canvas_to_lng_lat((x, y))):
                self.edit_session.write(data)
                self.refresh_layer_lists(preserve_selection=True)
                self.draw_canvas()

    def on_canvas_up(self, _event: object) -> None:
        self.pan_start = None
        self.dragging_vertex = False
        self.drag_snapshot_taken = False

    def on_mousewheel(self, event: object) -> None:
        delta = int(event.delta)  # type: ignore[attr-defined]
        factor = 1.1 if delta > 0 else 0.9
        self.zoom_canvas(factor, float(event.x), float(event.y))  # type: ignore[attr-defined]

    def zoom_canvas(self, factor: float, center_x: float | None = None, center_y: float | None = None) -> None:
        old = self.zoom_scale
        self.zoom_scale = max(0.3, min(8.0, self.zoom_scale * factor))
        if center_x is not None and center_y is not None and old > 0:
            self.pan_x = center_x - (center_x - self.pan_x) * (self.zoom_scale / old)
            self.pan_y = center_y - (center_y - self.pan_y) * (self.zoom_scale / old)
        self.draw_canvas()

    def reset_view(self) -> None:
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.draw_canvas()

    def clear_canvas_points(self) -> None:
        self.canvas_points.clear()
        self.draw_canvas()

    def canvas_to_lng_lat(self, point: tuple[float, float]) -> list[float]:
        bbox = parse_bbox_text(self.bbox.get())
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        x, y = point
        base_x = (x - self.pan_x) / self.zoom_scale
        base_y = (y - self.pan_y) / self.zoom_scale
        return pixel_to_lng_lat(base_x, base_y, width, height, bbox)

    def save_canvas_feature(self) -> None:
        layer = self.current_layer.get()
        coords = list(self.canvas_points)
        if layer == "spawn":
            point = coords[0] if coords else [float(self.spawn_lng.get()), float(self.spawn_lat.get())]
            item = feature("spawn", "Point", point, self.feature_name.get(), self.feature_memo.get())
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
        self.edit_session.add(item)
        self.clear_canvas_points()
        self.refresh_layer_lists()

    def delete_selected_accepted(self) -> None:
        selection = self.accepted_list.curselection()
        if not selection:
            return
        self.edit_session.delete_feature(selection[0])
        self.selected_feature_index = None
        self.selected_vertex_index = None
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
            messagebox.showwarning("선택 필요", "승인할 AI 후보를 선택하세요.")
            return
        count = approve_suggested(Path(self.project_dir.get()), selection)
        export_synthetic_osm_preview(Path(self.project_dir.get()))
        self.refresh_layer_lists()
        self.draw_canvas()
        self.refresh_layer_summary()
        self.update_final_wizard_statuses()
        self.status.set(f"{count}개 AI 후보를 승인된 레이어로 승인했습니다.")

    def refresh_layer_lists(self, preserve_selection: bool = False) -> None:
        paths = project_paths(Path(self.project_dir.get()))
        accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
        suggested = read_json(paths["suggested"]) if paths["suggested"].exists() else empty_feature_collection()
        self.accepted_list.delete(0, "end")
        for idx, item in enumerate(accepted.get("features", [])):
            props = item.get("properties", {})
            self.accepted_list.insert("end", f"{idx}: {props.get('layer')} {props.get('name', '')}")
        if preserve_selection and self.selected_feature_index is not None and self.selected_feature_index < len(accepted.get("features", [])):
            self.accepted_list.selection_set(self.selected_feature_index)
        self.suggested_list.delete(0, "end")
        for idx, item in enumerate(suggested.get("features", [])):
            props = item.get("properties", {})
            self.suggested_list.insert("end", f"{idx}: {props.get('layer')} 신뢰도={props.get('confidence', '')}")
        if hasattr(self, "worldgen_button"):
            enabled = bool(accepted.get("features", []))
            self.worldgen_button.configure(state="normal" if enabled else "disabled")
        if hasattr(self, "layer_counts"):
            self.refresh_layer_summary()
            self.update_final_wizard_statuses()

    def on_accepted_select(self, _event: object) -> None:
        selection = self.accepted_list.curselection()
        if not selection:
            return
        self.selected_feature_index = selection[0]
        self.selected_vertex_index = None
        data = self.edit_session.read()
        if self.selected_feature_index < len(data.get("features", [])):
            props = data["features"][self.selected_feature_index].get("properties", {})
            self.current_layer.set(props.get("layer", "road"))
            self.feature_name.set(props.get("name", ""))
            self.feature_memo.set(props.get("memo", ""))
        self.draw_canvas()

    def apply_selected_properties(self) -> None:
        index = self.selected_feature_index
        if index is None:
            selection = self.accepted_list.curselection()
            index = selection[0] if selection else None
        if index is None:
            return
        self.edit_session.update_properties(index, layer=self.current_layer.get(), name=self.feature_name.get(), memo=self.feature_memo.get())
        self.refresh_layer_lists(preserve_selection=True)
        self.draw_canvas()

    def delete_selected_vertex(self) -> None:
        if self.selected_feature_index is None or self.selected_vertex_index is None:
            return
        if self.edit_session.delete_vertex(self.selected_feature_index, self.selected_vertex_index):
            self.selected_vertex_index = None
            self.refresh_layer_lists(preserve_selection=True)
            self.draw_canvas()

    def undo_edit(self) -> None:
        if self.edit_session.undo():
            self.refresh_layer_lists(preserve_selection=True)
            self.draw_canvas()

    def redo_edit(self) -> None:
        if self.edit_session.redo():
            self.refresh_layer_lists(preserve_selection=True)
            self.draw_canvas()

    def revert_selected_accepted(self) -> None:
        selection = list(self.accepted_list.curselection())
        if not selection:
            return
        moved = revert_accepted_to_suggested(Path(self.project_dir.get()), selection)
        self.sync_edit_session()
        self.selected_feature_index = None
        self.selected_vertex_index = None
        self.refresh_layer_lists()
        self.draw_canvas()
        self.status.set(f"{moved}개 승인된 레이어를 AI 후보로 되돌렸습니다.")

    def draw_canvas(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if self.background_image is not None:
            self.canvas.create_image(self.pan_x, self.pan_y, image=self.background_image, anchor="nw")
        else:
            self.canvas.create_rectangle(0, 0, width, height, fill="#f7f3e8", outline="")
            self.canvas.create_text(16, 16, anchor="nw", text="네이버 지도 배경 또는 샘플 배경", fill="#6b7280", font=("Malgun Gothic", 10))
        paths = project_paths(Path(self.project_dir.get()))
        if paths["accepted"].exists():
            self.draw_geojson(read_json(paths["accepted"]), dashed=False)
        if self.show_suggested.get() and paths["suggested"].exists():
            self.draw_geojson(read_json(paths["suggested"]), dashed=True)
        for coord in self.canvas_points:
            x, y = self.lng_lat_to_canvas(coord)
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
        x, y = lng_lat_to_pixel(lng, lat, width, height, bbox)
        return x * self.zoom_scale + self.pan_x, y * self.zoom_scale + self.pan_y

    def set_feature_vertex(self, data: dict[str, object], feature_index: int, vertex_index: int, coord: list[float]) -> bool:
        features = data.get("features", [])  # type: ignore[assignment]
        if feature_index < 0 or feature_index >= len(features):  # type: ignore[arg-type]
            return False
        geometry = features[feature_index].get("geometry", {})  # type: ignore[index,union-attr]
        if geometry.get("type") == "Point":
            geometry["coordinates"] = coord
        elif geometry.get("type") == "LineString":
            coords = geometry.get("coordinates", [])
            if vertex_index < 0 or vertex_index >= len(coords):
                return False
            coords[vertex_index] = coord
        elif geometry.get("type") == "Polygon":
            ring = geometry.get("coordinates", [[]])[0]
            if vertex_index < 0 or vertex_index >= len(ring):
                return False
            ring[vertex_index] = coord
            if vertex_index == 0:
                ring[-1] = coord
            elif vertex_index == len(ring) - 1:
                ring[0] = coord
        else:
            return False
        features[feature_index].setdefault("properties", {})["updated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # type: ignore[index,union-attr]
        return True

    def select_at_canvas(self, x: float, y: float) -> None:
        data = self.edit_session.read()
        best: tuple[float, int, int | None] | None = None
        for feature_index, item in enumerate(data.get("features", [])):
            geometry = item.get("geometry", {})
            for vertex_index, coord in enumerate(iter_geometry_points(geometry)):
                cx, cy = self.lng_lat_to_canvas(coord)
                distance = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                if best is None or distance < best[0]:
                    best = (distance, feature_index, vertex_index)
        if best is not None and best[0] <= 14:
            self.selected_feature_index = best[1]
            self.selected_vertex_index = best[2]
            self.accepted_list.selection_clear(0, "end")
            self.accepted_list.selection_set(best[1])
            self.on_accepted_select(None)
            self.selected_vertex_index = best[2]
        elif best is not None and best[0] <= 36:
            self.selected_feature_index = best[1]
            self.selected_vertex_index = None
            self.accepted_list.selection_clear(0, "end")
            self.accepted_list.selection_set(best[1])
            self.on_accepted_select(None)
        else:
            self.selected_feature_index = None
            self.selected_vertex_index = None
            self.accepted_list.selection_clear(0, "end")

    def draw_geojson(self, data: dict[str, object], dashed: bool) -> None:
        colors = {"road": "#4b5563", "building": "#9f7aea", "water": "#2563eb", "green": "#16a34a", "rail": "#111827", "spawn": "#dc2626"}
        for feature_index, item in enumerate(data.get("features", [])):  # type: ignore[union-attr]
            props = item.get("properties", {})  # type: ignore[union-attr]
            layer = props.get("layer", "road")
            if not self.layer_visible.get(layer, BooleanVar(value=True)).get():
                continue
            geometry = item.get("geometry", {})  # type: ignore[union-attr]
            color = colors.get(layer, "#111827")
            dash = (4, 3) if dashed else None
            if geometry.get("type") == "Point":
                x, y = self.lng_lat_to_canvas(geometry["coordinates"])
                outline = "#f59e0b" if feature_index == self.selected_feature_index else ""
                self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=color, outline=outline, width=3)
            elif geometry.get("type") == "LineString":
                points = [xy for coord in geometry["coordinates"] for xy in self.lng_lat_to_canvas(coord)]
                if len(points) >= 4:
                    width = 5 if feature_index == self.selected_feature_index else 3
                    self.canvas.create_line(*points, fill=color, width=width, dash=dash)
            elif geometry.get("type") == "Polygon":
                ring = geometry["coordinates"][0]
                points = [xy for coord in ring for xy in self.lng_lat_to_canvas(coord)]
                if len(points) >= 6:
                    width = 4 if feature_index == self.selected_feature_index else 2
                    self.canvas.create_polygon(*points, fill=color, stipple="gray25", outline=color, width=width, dash=dash)
            if not dashed and feature_index == self.selected_feature_index:
                for vertex_index, coord in enumerate(iter_geometry_points(geometry)):
                    x, y = self.lng_lat_to_canvas(coord)
                    fill = "#f59e0b" if vertex_index == self.selected_vertex_index else "#ffffff"
                    self.canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4, fill=fill, outline="#111827")

    def export_accepted(self) -> None:
        path = export_accepted_layers(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json({"exported": str(path)}))

    def export_synthetic(self) -> None:
        data = export_synthetic_osm_preview(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json(data))

    def export_synthetic_osm_v11(self) -> None:
        try:
            from arnis_korea_detailed.trace_worldgen import export_synthetic_osm

            data = export_synthetic_osm(Path(self.project_dir.get()), building_height_mode=self.building_height_mode.get())
            self.export_result.delete("1.0", "end")
            self.export_result.insert("end", safe_json({"exported": str(Path(self.project_dir.get()) / "synthetic_osm.json"), "summary": data}))
        except Exception as exc:
            write_boot_log("SYNTHETIC_OSM_EXPORT_FAIL", exc)
            messagebox.showerror("synthetic_osm export 실패", str(exc))

    def export_layer_validation(self) -> None:
        data = write_layer_validation_report(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json(data))

    def write_source_policy(self) -> None:
        try:
            from arnis_korea_detailed.trace_worldgen import write_v11_source_policy_report

            report = write_v11_source_policy_report(Path(self.project_dir.get()))
        except Exception:
            from arnis_korea_detailed.trace_editor_core import source_policy_report

            report = source_policy_report(Path(self.project_dir.get()))
        self.export_result.delete("1.0", "end")
        self.export_result.insert("end", safe_json(report))

    def export_ai_trace_package_action(self) -> None:
        try:
            manifest = export_ai_trace_package(Path(self.project_dir.get()), Path(self.ai_package_dir.get()))
            self.ai_trace_result.delete("1.0", "end")
            self.ai_trace_result.insert("end", safe_json({"exported": True, "package_dir": self.ai_package_dir.get(), "manifest": manifest, "contains_key": False}))
        except Exception as exc:
            write_boot_log("AI_TRACE_PACKAGE_EXPORT_FAIL", exc)
            messagebox.showerror("AI Trace 패키지 내보내기 실패", str(exc))

    def import_ai_trace_results_action(self) -> None:
        try:
            result = import_ai_trace_results(Path(self.project_dir.get()), Path(self.ai_results_dir.get()))
            self.refresh_layer_lists()
            self.draw_canvas()
            self.ai_trace_result.delete("1.0", "end")
            self.ai_trace_result.insert("end", safe_json(result))
            self.status.set("AI 분석 결과를 AI 후보로 가져왔습니다. 월드 생성에는 사용자가 승인한 레이어만 사용됩니다.")
        except Exception as exc:
            write_boot_log("AI_TRACE_RESULT_IMPORT_FAIL", exc)
            messagebox.showerror("AI Trace 결과 가져오기 실패", str(exc))

    def validate_action(self) -> None:
        report = validate_project(Path(self.project_dir.get()))
        self.report_result.delete("1.0", "end")
        self.report_result.insert("end", safe_json(report))
        if hasattr(self, "troubleshooting_result"):
            self.troubleshooting_result.delete("1.0", "end")
            self.troubleshooting_result.insert("end", safe_json(report))
        if hasattr(self, "beginner_troubleshooting_result"):
            self.beginner_troubleshooting_result.delete("1.0", "end")
            self.beginner_troubleshooting_result.insert("end", safe_json(report))

    def open_reports_dir(self) -> None:
        open_path(project_paths(Path(self.project_dir.get()))["reports"])

    def final_check_project(self) -> None:
        try:
            paths = project_paths(Path(self.project_dir.get()))
            project = load_project(Path(self.project_dir.get())) if paths["project"].exists() else {}
            accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
            suggested = read_json(paths["suggested"]) if paths["suggested"].exists() else empty_feature_collection()
            data = {
                "project_file": paths["project"].exists(),
                "project_name": project.get("project_name", ""),
                "bbox": project.get("bbox", {}),
                "spawn_point": project.get("spawn_point", {}),
                "accepted_features": len(accepted.get("features", [])),
                "suggested_features": len(suggested.get("features", [])),
                "worldgen_input": "accepted_layers_only",
                "ready_for_worldgen": bool(accepted.get("features")),
            }
            self.final_result.delete("1.0", "end")
            self.final_result.insert("end", safe_json(data))
        except Exception as exc:
            write_boot_log("FINAL_CHECK_PROJECT_FAIL", exc)
            messagebox.showerror("프로젝트 상태 체크 실패", str(exc))

    def local_project_diagnosis(self) -> None:
        try:
            paths = project_paths(Path(self.project_dir.get()))
            files = sorted(str(path.relative_to(Path(self.project_dir.get()))) for path in Path(self.project_dir.get()).rglob("*") if path.is_file())
            data = {
                "project_dir": self.project_dir.get(),
                "latest_log": str(LATEST_LOG),
                "reports_dir": str(paths["reports"]),
                "files": files[:200],
                "file_count": len(files),
                "diagnosis_scope": "local_project_only",
            }
            self.troubleshooting_result.delete("1.0", "end")
            self.troubleshooting_result.insert("end", safe_json(data))
        except Exception as exc:
            write_boot_log("LOCAL_PROJECT_DIAGNOSIS_FAIL", exc)
            messagebox.showerror("진단 실패", str(exc))

    def _world_dir(self) -> Path:
        name = self.world_name.get().strip() or self.project_name.get().strip() or "Arnis Korea World"
        name = re.sub(r"[^A-Za-z0-9가-힣._ -]+", "_", name).strip(" .") or "Arnis Korea World"
        return Path(self.project_dir.get()) / "playable_world" / name

    def write_worldgen(self, data: dict[str, object]) -> None:
        self.worldgen_result.delete("1.0", "end")
        self.worldgen_result.insert("end", safe_json(data))

    def generate_world_action(self) -> None:
        paths = project_paths(Path(self.project_dir.get()))
        accepted = read_json(paths["accepted"]) if paths["accepted"].exists() else empty_feature_collection()
        if not accepted.get("features"):
            messagebox.showwarning("승인된 레이어 없음", "승인된 레이어가 없습니다. 지도 만들기 단계에서 도로/건물/녹지 등을 승인해 주세요.")
            self.update_final_wizard_statuses()
            return
        self.worldgen_button.configure(state="disabled")
        self.status.set("Arnis Writer로 월드 생성 중입니다.")
        self.write_worldgen({"status": "월드 생성 시작", "worldgen_input": "accepted_layers_only", "suggested_layers_used_for_worldgen": False})

        def worker() -> None:
            try:
                from arnis_korea_detailed.trace_worldgen import copy_world_to_saves, generate_world_from_project

                report = generate_world_from_project(
                    Path(self.project_dir.get()),
                    ROOT,
                    self.world_name.get(),
                    building_height_mode=self.building_height_mode.get(),
                    terrain=self.world_terrain.get(),
                    interior=self.world_interior.get(),
                    roof=self.world_roof.get(),
                    scale=float(self.world_scale.get()),
                    run_load_smoke=self.run_local_load_smoke.get(),
                )
                if self.copy_to_saves.get():
                    target = copy_world_to_saves(Path(report["world_dir"]), Path(self.minecraft_saves_dir.get()), overwrite=self.overwrite_saves.get())
                    report["copied_to_minecraft_saves"] = str(target)
                self.root.after(0, lambda report=report: self.after_worldgen(report, None))
            except Exception as exc:
                write_boot_log("WORLDGEN_FAIL", exc)
                self.root.after(0, lambda exc=exc: self.after_worldgen({}, exc))

        threading.Thread(target=worker, daemon=True).start()

    def after_worldgen(self, report: dict[str, object], exc: BaseException | None) -> None:
        self.worldgen_button.configure(state="normal")
        if exc is not None:
            self.status.set("월드 생성 실패")
            message = "월드 생성에 실패했습니다. 문제 해결 화면에서 로그를 확인하세요."
            self.write_worldgen({"passed": False, "message": message, "detail": str(exc), "latest_log": str(LATEST_LOG)})
            if hasattr(self, "wizard_export_result"):
                self.wizard_export_result.delete("1.0", "end")
                self.wizard_export_result.insert("end", safe_json({"passed": False, "message": message, "latest_log": str(LATEST_LOG)}))
            self.update_final_wizard_statuses()
            messagebox.showerror("월드 생성 실패", message)
            return
        self.status.set("월드 생성 완료")
        self.write_worldgen(report)
        if hasattr(self, "wizard_export_result"):
            self.wizard_export_result.delete("1.0", "end")
            self.wizard_export_result.insert("end", safe_json(report))
        self.update_final_wizard_statuses(worldgen_done=True)
        if hasattr(self, "final_result"):
            self.final_result.delete("1.0", "end")
            self.final_result.insert("end", safe_json(report))

    def open_generated_world(self) -> None:
        open_path(self._world_dir())

    def copy_world_to_saves_action(self) -> None:
        try:
            from arnis_korea_detailed.trace_worldgen import copy_world_to_saves

            target = copy_world_to_saves(self._world_dir(), Path(self.minecraft_saves_dir.get()), overwrite=self.overwrite_saves.get())
            self.write_worldgen({"copied_to_minecraft_saves": str(target), "copied_only_world_dir": True})
            if hasattr(self, "wizard_export_result"):
                self.wizard_export_result.delete("1.0", "end")
                self.wizard_export_result.insert("end", safe_json({"copied_to_minecraft_saves": str(target), "copied_only_world_dir": True}))
            self.update_final_wizard_statuses(saves_done=True)
        except Exception as exc:
            write_boot_log("COPY_WORLD_TO_SAVES_FAIL", exc)
            messagebox.showerror("복사 실패", str(exc))


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


def _visible_widget_texts(widget: object) -> list[str]:
    texts: list[str] = []
    try:
        mapped = bool(widget.winfo_ismapped())  # type: ignore[attr-defined]
    except Exception:
        mapped = False
    if mapped:
        try:
            text = widget.cget("text")  # type: ignore[attr-defined]
            if text:
                texts.append(str(text))
        except Exception:
            pass
    try:
        children = widget.winfo_children()  # type: ignore[attr-defined]
    except Exception:
        children = []
    for child in children:
        texts.extend(_visible_widget_texts(child))
    return texts


def self_test_simple_wizard() -> int:
    write_boot_log("SIMPLE_WIZARD_SELF_TEST_START")
    root = Tk()
    app = TraceEditorApp(root, safe_mode=True)
    root.update()
    if app.current_step.get() != "start":
        raise RuntimeError("default step is not start")
    if app.advanced_host.winfo_ismapped():
        raise RuntimeError("advanced settings are visible in beginner mode")
    visible = "\n".join(_visible_widget_texts(root)).lower()
    required = [
        "1. 시작하기",
        "2. 지도 만들기",
        "3. 마인크래프트로 내보내기",
        "새 지도 만들기",
        "기존 프로젝트 열기",
        "최근 프로젝트",
        "도움말",
        "네이버 api 키 상태",
        "api 키 설정",
        "로그",
        "문제 해결",
    ]
    missing = [term for term in required if term.lower() not in visible]
    if missing:
        root.destroy()
        raise RuntimeError(f"required beginner UI text missing: {missing}")
    forbidden = [
        "source policy",
        "synthetic osm",
        "debug",
        "reports",
        "schema",
        "artifact",
        "renderer",
        "cli",
        "ai worker",
        "paper",
        "dev-tools",
        "threshold",
        "api 키 테스트",
        "검사 결과",
        "월드 생성 엔진",
        "마인크래프트 호환성 검사",
    ]
    leaked = [term for term in forbidden if term in visible]
    original_showinfo = messagebox.showinfo
    try:
        messagebox.showinfo = lambda *_args, **_kwargs: "ok"  # type: ignore[assignment]
        app.show_beginner_help()
        root.update()
        if app.advanced_host.winfo_ismapped():
            root.destroy()
            raise RuntimeError("beginner help opened advanced settings")
    finally:
        messagebox.showinfo = original_showinfo  # type: ignore[assignment]
    app.open_api_settings()
    root.update()
    if app.advanced_host.winfo_ismapped():
        root.destroy()
        raise RuntimeError("API key settings opened advanced settings")
    if app.api_settings_window is None or not app.api_settings_window.winfo_exists():
        root.destroy()
        raise RuntimeError("API key settings dialog did not open")
    app.api_settings_window.destroy()
    app.open_troubleshooting()
    root.update()
    if app.advanced_host.winfo_ismapped():
        root.destroy()
        raise RuntimeError("troubleshooting opened advanced settings")
    if app.troubleshooting_window is None or not app.troubleshooting_window.winfo_exists():
        root.destroy()
        raise RuntimeError("troubleshooting dialog did not open")
    app.troubleshooting_window.destroy()
    root.destroy()
    if leaked:
        raise RuntimeError(f"advanced terms visible in default UI: {leaked}")
    write_boot_log("SIMPLE_WIZARD_SELF_TEST_PASS")
    print("SIMPLE_WIZARD_SELF_TEST=PASS")
    return 0


def self_test_advanced_mode() -> int:
    write_boot_log("ADVANCED_MODE_SELF_TEST_START")
    root = Tk()
    app = TraceEditorApp(root, safe_mode=True)
    root.update()
    app.open_advanced_settings()
    root.update()
    if not app.advanced_host.winfo_ismapped():
        raise RuntimeError("advanced settings did not open")
    app.close_advanced_settings()
    root.update()
    if app.advanced_host.winfo_ismapped() or not app.simple_shell.winfo_ismapped():
        raise RuntimeError("beginner mode did not restore")
    root.destroy()
    write_boot_log("ADVANCED_MODE_SELF_TEST_PASS")
    print("ADVANCED_MODE_SELF_TEST=PASS")
    return 0


def self_test_beginner_flow() -> int:
    write_boot_log("BEGINNER_FLOW_SELF_TEST_START")
    root = Tk()
    app = TraceEditorApp(root, safe_mode=True)
    root.update()
    for step in ["start", "map", "export"]:
        app.show_wizard_step(step)
        root.update()
        if app.current_step.get() != step:
            raise RuntimeError(f"wizard step failed: {step}")
    if app.api_key_status.get() != "미설정":
        raise RuntimeError("safe-mode API status should be missing")
    app.update_final_wizard_statuses()
    if app.wizard_status_vars["layers"].get() != "필요함":
        raise RuntimeError("empty project should require approved layers")
    root.destroy()
    write_boot_log("BEGINNER_FLOW_SELF_TEST_PASS")
    print("BEGINNER_FLOW_SELF_TEST=PASS")
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
    parser.add_argument("--self-test-simple-wizard", action="store_true")
    parser.add_argument("--self-test-beginner-flow", action="store_true")
    parser.add_argument("--self-test-advanced-mode", action="store_true")
    parser.add_argument("--safe-mode", action="store_true")
    args = parser.parse_args(argv)
    if CORE_IMPORT_ERROR is not None:
        if args.self_test_gui:
            write_boot_log("GUI_SELF_TEST_FAIL_CORE_IMPORT", CORE_IMPORT_ERROR)
            print(f"GUI_SELF_TEST=FAIL latest_log={LATEST_LOG}", file=sys.stderr)
            return 1
        raise RuntimeError("GUI core import failed") from CORE_IMPORT_ERROR
    if args.self_test_gui:
        return self_test_gui(safe_mode=args.safe_mode)
    if args.self_test_simple_wizard:
        return self_test_simple_wizard()
    if args.self_test_beginner_flow:
        return self_test_beginner_flow()
    if args.self_test_advanced_mode:
        return self_test_advanced_mode()
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
        if "--self-test-gui" not in sys.argv:
            show_startup_error()
        else:
            print(f"GUI_SELF_TEST=FAIL latest_log={LATEST_LOG}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
