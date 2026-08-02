# ExifTool Date & GPS Editor for Windows

A small Python/Tkinter GUI that applies the same **date taken** and **GPS
location** to all supported images in a selected folder. It invokes ExifTool
directly and does not require third-party Python packages.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer with Tkinter (included in the standard Windows Python
  installer)
- [ExifTool](https://exiftool.org/) installed as `exiftool.exe` and available
  in the system `PATH`

Verify ExifTool from a new Command Prompt:

```cmd
exiftool -ver
```

If the command is not recognized, add the directory containing
`exiftool.exe` to the Windows `PATH`, then restart the application. The GUI
also checks the executable and displays its version on startup.

## Run

From Command Prompt in the project directory:

```cmd
python exiftool_wrapper_win.pyw
```

The `.pyw` extension launches the application without a separate console
window. It can also be started by double-clicking `exiftool_wrapper_win.pyw`.

## Usage

1. Select the folder containing the images.
2. Optionally enable **Include subfolders**.
3. Enter the date and time in `YYYY-MM-DD` and `HH:MM:SS` format.
4. Enter decimal GPS coordinates. Negative latitude means south; negative
   longitude means west.
5. Choose whether ExifTool should retain `.original` backup files.
6. Click **Apply metadata to all images** and verify the confirmation dialog.

The application writes these metadata fields:

- `FileCreateDate` (the Windows filesystem creation date)
- `EXIF:DateTimeOriginal`
- `EXIF:CreateDate`
- `EXIF:ModifyDate`
- `XMP:DateTimeOriginal`
- `EXIF:GPSLatitude` and `EXIF:GPSLatitudeRef`
- `EXIF:GPSLongitude` and `EXIF:GPSLongitudeRef`

Backups are enabled by default. When enabled, ExifTool creates an adjacent
`.original` copy before changing a file. Test the operation on copied images
before processing irreplaceable files.

## Supported image extensions

`ARW`, `AVIF`, `CR2`, `CR3`, `DNG`, `HEIC`, `HEIF`, `JPEG`, `JPG`, `NEF`,
`ORF`, `PEF`, `PNG`, `RAF`, `RW2`, `TIF`, `TIFF`, and `WEBP`.

Actual metadata-writing support depends on the installed ExifTool version and
the individual file format. `FileCreateDate` is a Windows-specific filesystem
timestamp. Any ExifTool warnings or errors appear in the progress log.

## Tests

The unit tests do not modify images or require ExifTool:

```cmd
python -m unittest -v
```
