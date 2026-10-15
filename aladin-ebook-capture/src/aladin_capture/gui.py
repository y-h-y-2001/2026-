"""Optional Tkinter UI (ported from upstream ebookAutoCapture).

Prefer the CLI + YAML config for AI-agent runs on macOS. This GUI remains
useful for interactive coordinate picking (logical points on Retina).
"""

from __future__ import annotations

# Upstream credit: p0tat0-113/ebookAutoCapture
# Kept intentionally thin; agents should use `python -m aladin_capture capture`.


def main() -> None:
    from tkinter import Tk, ttk, StringVar, IntVar, DoubleVar, N, W, E, S, HORIZONTAL
    from tkinter import filedialog
    import pyautogui

    from .config import CaptureConfig, Region
    from .capture import run_capture
    from .export_pdf import export_pdf
    from pathlib import Path

    root = Tk()
    root.title("Aladin Ebook Capture (macOS)")
    root.resizable(width=False, height=False)

    x1 = y1 = x2 = y2 = 0
    pos1 = StringVar(value="[0,0]")
    pos2 = StringVar(value="[0,0]")
    pages = IntVar(value=10)
    name = StringVar(value="book")
    dir_path = StringVar(value=str(Path.cwd() / "output"))
    speed = IntVar(value=500)
    move_opt = IntVar(value=0)
    progress = DoubleVar(value=0.0)

    frame = ttk.Frame(root, padding="8 8 8 8")
    frame.grid(column=0, row=0, sticky=(N, W, E, S))

    ttk.Label(frame, text="Personal use · 알라딘 eBook (Mac) screenshots").grid(
        column=1, row=0, columnspan=3, sticky=W
    )
    ttk.Label(frame, text="Click 좌표 설정, move mouse, press Space (logical points)").grid(
        column=1, row=1, columnspan=3, sticky=W
    )

    def bind_pos(which: int) -> None:
        def handler(_event=None) -> None:
            nonlocal x1, y1, x2, y2
            px, py = pyautogui.position()
            if which == 1:
                x1, y1 = px, py
                pos1.set(str([px, py]))
            else:
                x2, y2 = px, py
                pos2.set(str([px, py]))

        root.bind("<Key-space>", handler)
        root.focus_set()

    ttk.Label(frame, text="좌측 상단").grid(column=1, row=2, sticky=W)
    ttk.Label(frame, textvariable=pos1).grid(column=2, row=2, sticky=(W, E))
    ttk.Button(frame, text="좌표 설정", command=lambda: bind_pos(1)).grid(
        column=3, row=2, sticky=(W, E)
    )
    ttk.Label(frame, text="우측 하단").grid(column=1, row=3, sticky=W)
    ttk.Label(frame, textvariable=pos2).grid(column=2, row=3, sticky=(W, E))
    ttk.Button(frame, text="좌표 설정", command=lambda: bind_pos(2)).grid(
        column=3, row=3, sticky=(W, E)
    )

    ttk.Label(frame, text="총 페이지 수").grid(column=1, row=4, sticky=W)
    ttk.Entry(frame, textvariable=pages, width=10).grid(column=3, row=4, sticky=(W, E))
    ttk.Label(frame, text="파일 이름").grid(column=1, row=5, sticky=W)
    ttk.Entry(frame, textvariable=name, width=10).grid(column=3, row=5, sticky=(W, E))
    ttk.Label(frame, text="캡쳐 간격(ms)").grid(column=1, row=6, sticky=W)
    ttk.Label(frame, textvariable=speed).grid(column=2, row=6, sticky=(W, E))
    ttk.Scale(
        frame,
        orient=HORIZONTAL,
        length=120,
        from_=1,
        to=1000,
        variable=speed,
        command=lambda _v: speed.set(round(speed.get())),
    ).grid(column=3, row=6, sticky=(W, E))

    ttk.Radiobutton(frame, text="키보드 →", variable=move_opt, value=0).grid(
        column=2, row=7, sticky=W
    )
    ttk.Radiobutton(frame, text="마우스 클릭", variable=move_opt, value=1).grid(
        column=3, row=7, sticky=W
    )
    ttk.Progressbar(
        frame, orient=HORIZONTAL, mode="determinate", maximum=10000, variable=progress
    ).grid(column=1, row=8, columnspan=3, sticky=(W, E))

    def choose_dir() -> None:
        chosen = filedialog.askdirectory()
        if chosen:
            dir_path.set(chosen)

    def start() -> None:
        next_page = "key:right" if move_opt.get() == 0 else "click"
        cfg = CaptureConfig(
            title=name.get().strip() or "book",
            pages=int(pages.get()),
            region=Region(left=x1, top=y1, right=x2, bottom=y2),
            delay_ms=int(speed.get()),
            start_delay_sec=2,
            next_page=next_page,
            output_dir=Path(dir_path.get()),
            save_images=True,
            save_pdf=True,
            zero_pad=4,
            min_region_px=50,
            personal_use_notice=True,
            coordinate_space="logical",
            retina_scale=None,
        )

        def job() -> None:
            book_dir = run_capture(cfg)
            export_pdf(cfg, book_dir)
            progress.set(10000)

        root.after(100, job)

    ttk.Button(frame, text="작업 시작", command=start).grid(
        column=1, row=9, columnspan=3, sticky=(W, E)
    )
    ttk.Button(frame, text="저장 경로 설정", command=choose_dir).grid(
        column=1, row=10, columnspan=3, sticky=(W, E)
    )
    ttk.Label(frame, textvariable=dir_path, width=48).grid(
        column=1, row=11, columnspan=3, sticky=W
    )

    for child in frame.winfo_children():
        child.grid_configure(padx=5, pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()
