# ExifTool Date & GPS Editor for Windows

A Python/Tkinter GUI that applies the same **date taken**, **Windows file
creation date**, and **GPS location** to every supported image in a selected
folder. It invokes ExifTool directly and requires no third-party Python
packages.

## Features

- Verifies that ExifTool is available in `PATH` and displays its version.
- Processes a selected folder, with optional subfolder recursion.
- Validates date, time, latitude, and longitude before modifying files.
- Writes matching EXIF/XMP dates and the Windows filesystem creation date.
- Converts signed decimal coordinates to the correct GPS hemisphere fields.
- Keeps ExifTool `.original` backups by default.
- Processes large image collections in batches without freezing the GUI.
- Displays ExifTool progress, warnings, and errors.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer with Tkinter (included in the standard Windows Python
  installer)
- [ExifTool](https://exiftool.org/) installed as `exiftool.exe` and available
  in the system `PATH`

After installing ExifTool, open a new Command Prompt and verify that Windows
can find it:

```cmd
exiftool -ver
```

If the command is not recognized, add the directory containing
`exiftool.exe` to the Windows `PATH`. Open a new Command Prompt after changing
`PATH`, then run the verification command again.

## Run

Double-click `exiftool_wrapper_win.pyw`, or launch it from Command Prompt in
the project directory:

```cmd
python exiftool_wrapper_win.pyw
```

When opened through its normal Windows file association, the `.pyw` extension
runs the GUI without a separate console window.

## Usage

1. Select the folder containing the images.
2. Optionally enable **Include subfolders**.
3. Enter the date and time in `YYYY-MM-DD` and `HH:MM:SS` format.
4. Enter decimal GPS coordinates. Latitude must be between `-90` and `90`;
   longitude must be between `-180` and `180`. Negative latitude means south,
   and negative longitude means west.
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

## Safety and backups

Backups are enabled by default. ExifTool creates an adjacent `.original` copy
before changing an image. Disabling backups adds ExifTool's
`-overwrite_original` option and updates the original files without retaining
those copies.

Metadata changes are not automatically reversible when backups are disabled.
Test the application on copied images before processing irreplaceable files.

## Supported image extensions

`ARW`, `AVIF`, `CR2`, `CR3`, `DNG`, `HEIC`, `HEIF`, `JPEG`, `JPG`, `NEF`,
`ORF`, `PEF`, `PNG`, `RAF`, `RW2`, `TIF`, `TIFF`, and `WEBP`.

Actual metadata-writing support depends on the installed ExifTool version and
the individual file format. `FileCreateDate` is a Windows-specific filesystem
timestamp. Any ExifTool warnings or errors appear in the progress log.

## Tests

The unit tests do not modify images, launch the GUI, or require ExifTool:

```cmd
python -m unittest -v test_exiftool_wrapper_win
```
