# vrtFS25TextureEditor

Desktop texture tool (CustomTkinter) for FS25 workflows: single tiling, multi-atlas creation, and specular-map generation.

## Main Features

- **Single tab**
	- Load one image (`.png`, `.jpg`, `.jpeg`, `.dds`)
	- Set tiling multiplier and preview result
	- Save output image

- **Multi Atlas tab**
	- 4 atlas groups, each with up to 4 slots
	- Per-slot scale multiplier
	- Per-slot **Blank Image (Alpha)** toggle
	- Collapsible atlas groups + Expand/Collapse all
	- Per-group **Save Atlas X** button
	- Atlas project save/load (embedded image data)

- **Specular Gen tab**
	- Inputs:
		- Roughness -> Red channel
		- Ambient Occlusion -> Green channel
		- Metalness -> Blue channel
	- Optional **Invert Roughness**
	- Optional **No Metalness (use black)**

- **DDS Save Options**
	- Select DDS format label (BC1/BC2/BC3/BC4/BC5 variants)
	- Optional **Generate Mipmaps** checkbox

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
python vrtFS25TextureEditor.py
```

## Atlas Project Files

- Save from the icon button in preview area (visible on **Multi Atlas** tab)
- Load from the folder icon button
- Project file format: `.atlasproj` (JSON)
- Stored data includes:
	- target atlas width
	- each slot scale
	- each slot blank-alpha state
	- embedded slot images (base64 PNG)

## Build EXE (PyInstaller)

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Build (windowed, one-folder):

```powershell
python -m PyInstaller --noconfirm --windowed --name vrtFS25TextureEditor --collect-all customtkinter --collect-all tkinterdnd2 vrtFS25TextureEditor.py
```

Build (windowed, one-file):

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name vrtFS25TextureEditor --collect-all customtkinter --collect-all tkinterdnd2 vrtFS25TextureEditor.py
```

## Notes

- Drag-and-drop depends on `tkinterdnd2` / `tkdnd` support in your environment.
- If a selected DDS option is not supported by the underlying PIL DDS backend, save falls back to default DDS behavior.
