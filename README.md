# ImageScaler

ImageScaler is a desktop GUI app (CustomTkinter) that loads an image and creates a tiled version by repeating it using a numeric multiplier.

## Features

- Load image from file dialog (`.png`, `.jpg`, `.jpeg`)
- Optional drag-and-drop support (depends on `tkinterdnd2` / `tkdnd` availability)
- Generate tiled preview in-app
- Save output as PNG or JPEG

## Requirements

- Windows (tested)
- Python 3.10+

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run

From this folder:

```powershell
python imagescaler.py
```

## Build EXE (PyInstaller)

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Build (windowed, one-folder):

```powershell
python -m PyInstaller --noconfirm --windowed --name ImageScaler --collect-all customtkinter --collect-all tkinterdnd2 imagescaler.py
```

Output executable:

- `dist/ImageScaler/ImageScaler.exe`

## Notes about drag-and-drop

If `tkdnd` is not available in your Python/Tk setup, the app still runs and shows a fallback message in the drag-drop area. The **Load Image** button will continue to work normally.
