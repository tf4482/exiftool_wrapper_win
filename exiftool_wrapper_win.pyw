"""Windows GUI for applying one date-taken value and GPS position to images."""

from __future__ import annotations

import datetime as dt
import math
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from collections.abc import Callable, Sequence
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


IMAGE_EXTENSIONS = frozenset(
    {
        ".arw",
        ".avif",
        ".cr2",
        ".cr3",
        ".dng",
        ".heic",
        ".heif",
        ".jpeg",
        ".jpg",
        ".nef",
        ".orf",
        ".pef",
        ".png",
        ".raf",
        ".rw2",
        ".tif",
        ".tiff",
        ".webp",
    }
)
MAX_WINDOWS_COMMAND_LENGTH = 24_000


def find_exiftool() -> str | None:
    """Return ExifTool's path only when it is available through PATH."""
    return shutil.which("exiftool") or shutil.which("exiftool.exe")


def exiftool_version(executable: str) -> str:
    """Execute ExifTool once to verify that the discovered executable works."""
    result = subprocess.run(
        [executable, "-ver"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.stdout.strip()


def parse_taken_datetime(date_text: str, time_text: str) -> str:
    """Validate GUI date/time input and return ExifTool's date representation."""
    try:
        value = dt.datetime.strptime(
            f"{date_text.strip()} {time_text.strip()}", "%Y-%m-%d %H:%M:%S"
        )
    except ValueError as error:
        raise ValueError("Date and time must use YYYY-MM-DD and HH:MM:SS.") from error
    return value.strftime("%Y:%m:%d %H:%M:%S")


def parse_coordinates(latitude_text: str, longitude_text: str) -> tuple[float, float]:
    """Parse decimal coordinates and enforce valid geographic ranges."""
    try:
        latitude = float(latitude_text.strip())
        longitude = float(longitude_text.strip())
    except ValueError as error:
        raise ValueError("Latitude and longitude must be decimal numbers.") from error

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Latitude and longitude must be finite decimal numbers.")
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    return latitude, longitude


def discover_images(folder: Path, recursive: bool) -> list[Path]:
    """Find supported image files in a deterministic order."""
    candidates = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(
        (
            path
            for path in candidates
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )


def metadata_arguments(
    taken_at: str, latitude: float, longitude: float, keep_backups: bool
) -> list[str]:
    """Build shared ExifTool arguments for dates and GPS metadata."""
    arguments = [
        "-charset",
        "filename=UTF8",
        f"-FileCreateDate={taken_at}",
        f"-EXIF:DateTimeOriginal={taken_at}",
        f"-EXIF:CreateDate={taken_at}",
        f"-EXIF:ModifyDate={taken_at}",
        f"-XMP:DateTimeOriginal={taken_at}",
        f"-EXIF:GPSLatitude={abs(latitude):.8f}",
        f"-EXIF:GPSLatitudeRef={'N' if latitude >= 0 else 'S'}",
        f"-EXIF:GPSLongitude={abs(longitude):.8f}",
        f"-EXIF:GPSLongitudeRef={'E' if longitude >= 0 else 'W'}",
    ]
    if not keep_backups:
        arguments.append("-overwrite_original")
    return arguments


def chunk_paths(
    paths: Sequence[Path], base_arguments: Sequence[str], limit: int = MAX_WINDOWS_COMMAND_LENGTH
) -> list[list[Path]]:
    """Split paths to remain comfortably below Windows' command-line limit."""
    base_size = sum(len(argument) + 3 for argument in base_arguments)
    chunks: list[list[Path]] = []
    current: list[Path] = []
    current_size = base_size

    for path in paths:
        path_size = len(str(path)) + 3
        if current and current_size + path_size > limit:
            chunks.append(current)
            current = []
            current_size = base_size
        current.append(path)
        current_size += path_size

    if current:
        chunks.append(current)
    return chunks


def run_metadata_update(
    executable: str,
    paths: Sequence[Path],
    taken_at: str,
    latitude: float,
    longitude: float,
    keep_backups: bool,
    report: Callable[[str], None],
) -> tuple[int, int]:
    """Apply metadata in batches and return successful and failed batch counts."""
    common = metadata_arguments(taken_at, latitude, longitude, keep_backups)
    batches = chunk_paths(paths, [executable, *common])
    successful = 0
    failed = 0

    for index, batch in enumerate(batches, start=1):
        report(f"Processing batch {index}/{len(batches)} ({len(batch)} images)...")
        result = subprocess.run(
            [executable, *common, *(str(path) for path in batch)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        if output:
            report(output)
        if result.returncode == 0:
            successful += 1
        else:
            failed += 1
            report(f"Batch {index} failed with ExifTool exit code {result.returncode}.")

    return successful, failed


def create_app() -> tk.Tk:
    """Construct and return the Tk application."""
    root = tk.Tk()
    root.title("ExifTool Date & GPS Editor")
    root.geometry("760x620")
    root.minsize(680, 560)

    now = dt.datetime.now().replace(microsecond=0)
    folder_var = tk.StringVar()
    date_var = tk.StringVar(value=now.strftime("%Y-%m-%d"))
    time_var = tk.StringVar(value=now.strftime("%H:%M:%S"))
    latitude_var = tk.StringVar()
    longitude_var = tk.StringVar()
    recursive_var = tk.BooleanVar(value=False)
    keep_backups_var = tk.BooleanVar(value=True)
    status_var = tk.StringVar(value="Checking for ExifTool in PATH...")
    event_queue: queue.Queue[tuple[str, str]] = queue.Queue()
    state: dict[str, str | None] = {"executable": None}

    main = ttk.Frame(root, padding=16)
    main.pack(fill=tk.BOTH, expand=True)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(7, weight=1)

    ttk.Label(main, text="ExifTool", font=("Segoe UI", 10, "bold")).grid(
        row=0, column=0, sticky=tk.W, pady=(0, 12)
    )
    status_label = ttk.Label(main, textvariable=status_var)
    status_label.grid(row=0, column=1, sticky=tk.W, pady=(0, 12))
    recheck_button = ttk.Button(main, text="Check again")
    recheck_button.grid(row=0, column=2, padx=(8, 0), pady=(0, 12))

    ttk.Label(main, text="Image folder").grid(row=1, column=0, sticky=tk.W, pady=4)
    folder_entry = ttk.Entry(main, textvariable=folder_var)
    folder_entry.grid(row=1, column=1, sticky=tk.EW, pady=4)
    browse_button = ttk.Button(main, text="Browse...")
    browse_button.grid(row=1, column=2, padx=(8, 0), pady=4)

    options = ttk.Frame(main)
    options.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=(2, 12))
    ttk.Checkbutton(options, text="Include subfolders", variable=recursive_var).pack(
        side=tk.LEFT
    )
    ttk.Checkbutton(
        options,
        text="Keep ExifTool backups (.original)",
        variable=keep_backups_var,
    ).pack(side=tk.LEFT, padx=(18, 0))

    ttk.Separator(main).grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=(0, 12))

    ttk.Label(main, text="Date taken").grid(row=4, column=0, sticky=tk.W, pady=4)
    date_frame = ttk.Frame(main)
    date_frame.grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=4)
    date_entry = ttk.Entry(date_frame, textvariable=date_var, width=14)
    date_entry.pack(side=tk.LEFT)
    ttk.Label(date_frame, text="YYYY-MM-DD    Time").pack(side=tk.LEFT, padx=(8, 8))
    time_entry = ttk.Entry(date_frame, textvariable=time_var, width=12)
    time_entry.pack(side=tk.LEFT)
    ttk.Label(date_frame, text="HH:MM:SS").pack(side=tk.LEFT, padx=(8, 0))

    ttk.Label(main, text="GPS latitude").grid(row=5, column=0, sticky=tk.W, pady=4)
    latitude_entry = ttk.Entry(main, textvariable=latitude_var, width=24)
    latitude_entry.grid(row=5, column=1, sticky=tk.W, pady=4)
    ttk.Label(main, text="-90 to 90 (decimal)").grid(row=5, column=2, sticky=tk.W, padx=(8, 0))

    ttk.Label(main, text="GPS longitude").grid(row=6, column=0, sticky=tk.W, pady=4)
    longitude_entry = ttk.Entry(main, textvariable=longitude_var, width=24)
    longitude_entry.grid(row=6, column=1, sticky=tk.W, pady=4)
    ttk.Label(main, text="-180 to 180 (decimal)").grid(
        row=6, column=2, sticky=tk.W, padx=(8, 0)
    )

    log_frame = ttk.LabelFrame(main, text="Progress", padding=8)
    log_frame.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, pady=(16, 12))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
    scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log.yview)
    log.configure(yscrollcommand=scrollbar.set)
    log.grid(row=0, column=0, sticky=tk.NSEW)
    scrollbar.grid(row=0, column=1, sticky=tk.NS)

    apply_button = ttk.Button(main, text="Apply metadata to all images")
    apply_button.grid(row=8, column=0, columnspan=3, pady=(0, 2))

    def append_log(text: str) -> None:
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, text.rstrip() + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    def set_busy(busy: bool) -> None:
        state_value = tk.DISABLED if busy else tk.NORMAL
        for widget in (apply_button, browse_button, recheck_button):
            widget.configure(state=state_value)

    def choose_folder() -> None:
        selected = filedialog.askdirectory(title="Select the image folder", mustexist=True)
        if selected:
            folder_var.set(selected)

    def check_exiftool() -> None:
        executable = find_exiftool()
        state["executable"] = None
        apply_button.configure(state=tk.DISABLED)
        if not executable:
            status_var.set("Not found in PATH")
            messagebox.showerror(
                "ExifTool not found",
                "ExifTool is required but was not found in PATH.\n\n"
                "Install ExifTool, ensure exiftool.exe is in PATH, then click Check again.",
            )
            return
        try:
            version = exiftool_version(executable)
        except (OSError, subprocess.SubprocessError) as error:
            status_var.set("Found, but could not be executed")
            messagebox.showerror("ExifTool error", f"Could not run ExifTool:\n{error}")
            return
        state["executable"] = executable
        status_var.set(f"Ready — version {version} ({executable})")
        apply_button.configure(state=tk.NORMAL)

    def process_events() -> None:
        try:
            while True:
                event, text = event_queue.get_nowait()
                if event == "log":
                    append_log(text)
                elif event == "done":
                    set_busy(False)
                    if state["executable"]:
                        apply_button.configure(state=tk.NORMAL)
                    messagebox.showinfo("Finished", text)
                elif event == "error":
                    set_busy(False)
                    if state["executable"]:
                        apply_button.configure(state=tk.NORMAL)
                    append_log(f"ERROR: {text}")
                    messagebox.showerror("Update failed", text)
        except queue.Empty:
            pass
        root.after(100, process_events)

    def update_worker(
        executable: str,
        images: Sequence[Path],
        taken_at: str,
        latitude: float,
        longitude: float,
        keep_backups: bool,
    ) -> None:
        try:
            successful, failed = run_metadata_update(
                executable,
                images,
                taken_at,
                latitude,
                longitude,
                keep_backups,
                lambda text: event_queue.put(("log", text)),
            )
        except OSError as error:
            event_queue.put(("error", f"Could not execute ExifTool:\n{error}"))
            return

        if failed:
            event_queue.put(
                (
                    "error",
                    (
                        f"Completed with errors: {successful} batch(es) succeeded and "
                        f"{failed} failed. Review the progress log."
                    ),
                )
            )
            return
        event_queue.put(("done", f"Metadata was applied to {len(images)} image(s)."))

    def start_update() -> None:
        executable = state["executable"]
        if not executable:
            messagebox.showerror("ExifTool not ready", "Check the ExifTool installation first.")
            return

        folder = Path(folder_var.get().strip())
        if not folder.is_dir():
            messagebox.showerror("Invalid folder", "Select an existing image folder.")
            return
        try:
            taken_at = parse_taken_datetime(date_var.get(), time_var.get())
            latitude, longitude = parse_coordinates(
                latitude_var.get(), longitude_var.get()
            )
        except ValueError as error:
            messagebox.showerror("Invalid metadata", str(error))
            return

        try:
            images = discover_images(folder, recursive_var.get())
        except OSError as error:
            messagebox.showerror("Folder error", f"Could not scan the folder:\n{error}")
            return
        if not images:
            messagebox.showinfo("No images", "No supported image files were found.")
            return

        backup_note = (
            "ExifTool backup files will be retained."
            if keep_backups_var.get()
            else "Original files will be overwritten without ExifTool backups."
        )
        if not messagebox.askyesno(
            "Confirm metadata update",
            f"Apply the same date and GPS location to {len(images)} image(s)?\n\n"
            f"Date taken: {taken_at}\n"
            f"GPS: {latitude:.8f}, {longitude:.8f}\n\n{backup_note}",
            icon=messagebox.WARNING,
        ):
            return

        append_log(
            f"Starting update for {len(images)} image(s): date={taken_at}, "
            f"GPS={latitude:.8f},{longitude:.8f}"
        )
        set_busy(True)
        threading.Thread(
            target=update_worker,
            args=(
                executable,
                images,
                taken_at,
                latitude,
                longitude,
                keep_backups_var.get(),
            ),
            daemon=True,
        ).start()

    browse_button.configure(command=choose_folder)
    recheck_button.configure(command=check_exiftool)
    apply_button.configure(command=start_update, state=tk.DISABLED)
    root.after(100, process_events)
    root.after(200, check_exiftool)
    return root


def main() -> None:
    create_app().mainloop()


if __name__ == "__main__":
    main()
