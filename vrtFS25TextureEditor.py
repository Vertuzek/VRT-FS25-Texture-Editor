import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os
import io
import json
import base64



class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        TkinterDnD.DnDWrapper.__init__(self, *args, **kwargs)

# ===== App =====
class TileResizerApp:

    ATLAS_COUNT = 4
    SLOTS_PER_ATLAS = 4
    DDS_FORMAT_OPTIONS = [
        "Auto",
        "BC1 (Linear, DXT1)",
        "BC1 (sRGB, DX 10+)",
        "BC2 (Linear, DXT3)",
        "BC2 (sRGB, DX 10+)",
        "BC3 (Linear, DXT5)",
        "BC3 (sRGB, DX 10+)",
        "BC3 (Linear, RGB)",
        "BC4 (Linear, Unsigned)",
        "BC4 (Linear, Unsigned, ATI1)",
        "BC5 (Linear, Unsigned)",
        "BC5 (Linear, Unsigned, ATI2)",
        "BC5 (Linear, Signed)",
        "BC6H (Linear, Unsigned, DX 11+)",
        "BC7 (Linear, DX 11+)",
        "BC7 (sRGB, DX 11+)",
    ]

    DDS_OPTION_TO_PIXEL_FORMAT = {
        "BC1 (Linear, DXT1)": "DXT1",
        "BC1 (sRGB, DX 10+)": "DXT1",
        "BC2 (Linear, DXT3)": "DXT3",
        "BC2 (sRGB, DX 10+)": "DXT3",
        "BC3 (Linear, DXT5)": "DXT5",
        "BC3 (sRGB, DX 10+)": "DXT5",
        "BC3 (Linear, RGB)": "DXT5",
        "BC4 (Linear, Unsigned)": "ATI1",
        "BC4 (Linear, Unsigned, ATI1)": "ATI1",
        "BC5 (Linear, Unsigned)": "ATI2",
        "BC5 (Linear, Unsigned, ATI2)": "ATI2",
        "BC5 (Linear, Signed)": "ATI2",
    }

    def __init__(self, root):
        self.root = root
        self.image = None
        self.tiled_result = None
        self.preview_img = None
        self.atlas_result = None
        self.atlas_results = []
        self.specular_result = None
        self.current_output_mode = None
        self.input_path = None
        self.input_ext = None
        self.input_dds_format = None

        self.specular_inputs = {
            "roughness": None,
            "ambient_occlusion": None,
            "metalness": None,
        }
        self.specular_labels = {}
        self.specular_input_names = {}
        
        # Atlas data: list of dicts with 'image' and 'scale'
        self.atlas_slots = [
            {'image': None, 'scale': 1}
            for _ in range(self.ATLAS_COUNT * self.SLOTS_PER_ATLAS)
        ]
        
        # UI references for each slot
        self.slot_frames = []
        self.slot_labels = []
        self.slot_scale_entries = []
        self.slot_blank_vars = []
        self.atlas_group_buttons = []
        self.atlas_group_bodies = []
        self.atlas_group_expanded = []

        # ===== Layout =====
        self.left_frame = ctk.CTkFrame(root, width=290, fg_color="#2b2b2b")
        self.right_frame = ctk.CTkFrame(root, fg_color="#2b2b2b")

        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        self.controls_tabs = ctk.CTkTabview(self.left_frame, width=270)
        self.controls_tabs.pack(fill="both", expand=True, padx=8, pady=(8, 6))
        self.controls_tabs.add("Single")
        self.controls_tabs.add("Multi Atlas")
        self.controls_tabs.add("Specular Gen")

        self.single_controls_frame = self.controls_tabs.tab("Single")
        self.atlas_controls_frame = ctk.CTkScrollableFrame(self.controls_tabs.tab("Multi Atlas"), fg_color="transparent")
        self.atlas_controls_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.specular_controls_frame = ctk.CTkScrollableFrame(self.controls_tabs.tab("Specular Gen"), fg_color="transparent")
        self.specular_controls_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.bottom_actions = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.bottom_actions.pack(fill="x", padx=8, pady=(0, 8))

        # ===== Single Image Controls =====
        self.single_title = ctk.CTkLabel(self.single_controls_frame, text="Single Image Tiling", font=("Arial", 14, "bold"))
        self.single_title.pack(pady=(5, 10))
        
        self.load_btn = ctk.CTkButton(self.single_controls_frame, text="Load Image", command=self.load_image)
        self.load_btn.pack(pady=5, fill="x")

        self.multiplier_label = ctk.CTkLabel(self.single_controls_frame, text="Resize Multiplier")
        self.multiplier_label.pack(pady=(10, 0))

        self.multiplier_entry = ctk.CTkEntry(self.single_controls_frame)
        self.multiplier_entry.insert(0, "2")
        self.multiplier_entry.pack(fill="x", pady=5)
        self.multiplier_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())

        self.register_drop_target(self.single_title, self.on_single_section_drop)
        self.register_drop_target(self.load_btn, self.on_single_section_drop)
        self.register_drop_target(self.multiplier_label, self.on_single_section_drop)
        self.register_drop_target(self.multiplier_entry, self.on_single_section_drop)

        # ===== ATLAS CREATION =====
        self.atlas_title = ctk.CTkLabel(self.atlas_controls_frame, text="Atlas Creation", font=("Arial", 14, "bold"))
        self.atlas_title.pack(pady=5)

        self.tile_size_label = ctk.CTkLabel(self.atlas_controls_frame, text="Target Atlas Width")
        self.tile_size_label.pack(pady=(5, 0))

        self.tile_size_entry = ctk.CTkEntry(self.atlas_controls_frame)
        self.tile_size_entry.insert(0, "1024")
        self.tile_size_entry.pack(fill="x", pady=5)
        self.tile_size_entry.bind("<KeyRelease>", lambda e: self.schedule_atlas_update())

        self.atlas_group_actions = ctk.CTkFrame(self.atlas_controls_frame, fg_color="transparent")
        self.atlas_group_actions.pack(fill="x", pady=(2, 6))

        self.expand_all_btn = ctk.CTkButton(
            self.atlas_group_actions,
            text="Expand All",
            command=self.expand_all_atlas_groups,
            height=28
        )
        self.expand_all_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.collapse_all_btn = ctk.CTkButton(
            self.atlas_group_actions,
            text="Collapse All",
            command=self.collapse_all_atlas_groups,
            height=28
        )
        self.collapse_all_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Create 4 atlas groups x 4 image slots
        for atlas_index in range(self.ATLAS_COUNT):
            atlas_toggle_btn = ctk.CTkButton(
                self.atlas_controls_frame,
                text="",
                font=("Arial", 12, "bold"),
                anchor="w",
                command=lambda idx=atlas_index: self.toggle_atlas_group(idx)
            )
            atlas_toggle_btn.pack(pady=(10, 3), fill="x")
            self.register_drop_target(atlas_toggle_btn, lambda e, idx=atlas_index: self.on_atlas_group_drop(e, idx))

            atlas_group_body = ctk.CTkFrame(self.atlas_controls_frame, fg_color="transparent")
            atlas_group_body.pack(fill="x", pady=(0, 4))
            self.register_drop_target(atlas_group_body, lambda e, idx=atlas_index: self.on_atlas_group_drop(e, idx))

            self.atlas_group_buttons.append(atlas_toggle_btn)
            self.atlas_group_bodies.append(atlas_group_body)
            self.atlas_group_expanded.append(True)

            for slot_index in range(self.SLOTS_PER_ATLAS):
                absolute_slot = atlas_index * self.SLOTS_PER_ATLAS + slot_index
                self.create_atlas_slot(atlas_group_body, absolute_slot)

            save_atlas_btn = ctk.CTkButton(
                atlas_group_body,
                text=f"Save Atlas {atlas_index + 1}",
                command=lambda idx=atlas_index: self.save_single_atlas(idx),
                height=28
            )
            save_atlas_btn.pack(fill="x", padx=5, pady=(2, 8))

        for atlas_index in range(self.ATLAS_COUNT):
            if atlas_index > 0:
                self.atlas_group_expanded[atlas_index] = False
                self.atlas_group_bodies[atlas_index].pack_forget()
            self.update_atlas_group_button_text(atlas_index)

        # ===== SPECULAR GENERATION =====
        self.specular_title = ctk.CTkLabel(self.specular_controls_frame, text="Specular Generation", font=("Arial", 14, "bold"))
        self.specular_title.pack(pady=5)

        self.create_specular_input_row("roughness", "Roughness (RED)", "#FF6A6A")
        self.create_specular_input_row("ambient_occlusion", "Ambient Occlusion (GREEN)", "#7CFC00")
        self.create_specular_input_row("metalness", "Metalness (BLUE)", "#87CEFA")

        self.invert_roughness_var = ctk.BooleanVar(value=False)
        self.invert_roughness_check = ctk.CTkCheckBox(
            self.specular_controls_frame,
            text="Invert Roughness",
            variable=self.invert_roughness_var,
            command=self.auto_generate_specular
        )
        self.invert_roughness_check.pack(pady=(8, 4), anchor="w")

        self.no_metalness_var = ctk.BooleanVar(value=False)
        self.no_metalness_check = ctk.CTkCheckBox(
            self.specular_controls_frame,
            text="No Metalness (use black)",
            variable=self.no_metalness_var,
            command=self.on_no_metalness_toggle
        )
        self.no_metalness_check.pack(pady=(0, 4), anchor="w")

        self.clear_specular_btn = ctk.CTkButton(
            self.specular_controls_frame,
            text="Clear Specular Inputs",
            command=self.clear_specular_inputs
        )
        self.clear_specular_btn.pack(fill="x", pady=(4, 8))

        self.clear_atlas_btn = ctk.CTkButton(self.bottom_actions, text="Clear All Slots", command=self.clear_atlas)
        self.clear_atlas_btn.pack(pady=2, fill="x")

        self.dds_format_label = ctk.CTkLabel(self.bottom_actions, text="DDS Save Format")
        self.dds_format_label.pack(pady=(10, 0), anchor="w")

        self.dds_format_var = ctk.StringVar(value="Auto")
        self.dds_format_menu = ctk.CTkOptionMenu(
            self.bottom_actions,
            values=self.DDS_FORMAT_OPTIONS,
            variable=self.dds_format_var
        )
        self.dds_format_menu.pack(fill="x", pady=(4, 6))

        self.generate_mipmaps_var = ctk.BooleanVar(value=False)
        self.generate_mipmaps_check = ctk.CTkCheckBox(
            self.bottom_actions,
            text="Generate Mipmaps",
            variable=self.generate_mipmaps_var
        )
        self.generate_mipmaps_check.pack(anchor="w", pady=(0, 8))

        self.save_btn = ctk.CTkButton(self.bottom_actions, text="Save Image", command=self.save_image)
        self.save_btn.pack(pady=(14, 5), fill="x")
        self.save_btn_hidden_for_atlas = False

        # ===== Preview Canvas =====
        self.canvas = ctk.CTkCanvas(
            self.right_frame,
            bg="#2b2b2b",
            highlightthickness=0
        )

        self.canvas.pack(fill="both", expand=True)

        self.preview_project_actions = ctk.CTkFrame(self.right_frame, fg_color="#2b2b2b")

        self.save_project_icon_btn = ctk.CTkButton(
            self.preview_project_actions,
            text="💾",
            width=44,
            height=36,
            font=("Arial", 18),
            command=self.save_atlas_project
        )
        self.save_project_icon_btn.pack(side="left", padx=(0, 4))

        self.load_project_icon_btn = ctk.CTkButton(
            self.preview_project_actions,
            text="📂",
            width=44,
            height=36,
            font=("Arial", 18),
            command=self.load_atlas_project
        )
        self.load_project_icon_btn.pack(side="left")

        self.canvas.bind("<Configure>", self.refresh_preview)
        self.refresh_project_buttons_visibility()

    def refresh_project_buttons_visibility(self):
        is_atlas_tab = self.controls_tabs.get() == "Multi Atlas"

        if is_atlas_tab:
            self.preview_project_actions.place(relx=0.99, rely=0.99, anchor="se")
        else:
            self.preview_project_actions.place_forget()

        if is_atlas_tab and not self.save_btn_hidden_for_atlas:
            self.save_btn.pack_forget()
            self.save_btn_hidden_for_atlas = True
        elif not is_atlas_tab and self.save_btn_hidden_for_atlas:
            self.save_btn.pack(pady=(14, 5), fill="x")
            self.save_btn_hidden_for_atlas = False

        self.root.after(150, self.refresh_project_buttons_visibility)
    
    def create_atlas_slot(self, parent, slot_index):
        """Create UI for one atlas slot"""
        frame = ctk.CTkFrame(parent, fg_color="#1e1e1e")
        frame.pack(pady=8, fill="x", padx=5)

        atlas_num = (slot_index // self.SLOTS_PER_ATLAS) + 1
        slot_num = (slot_index % self.SLOTS_PER_ATLAS) + 1
        
        # Title
        title = ctk.CTkLabel(frame, text=f"A{atlas_num} / Slot {slot_num}", font=("Arial", 12, "bold"))
        title.pack(pady=(5, 2))
        
        # Status label
        status_label = ctk.CTkLabel(frame, text="No image loaded", text_color="#888888")
        status_label.pack(pady=2)
        
        # Load/Replace button
        load_btn = ctk.CTkButton(
            frame, 
            text="Load Image", 
            command=lambda idx=slot_index: self.load_atlas_slot(idx),
            height=28
        )
        load_btn.pack(pady=3, fill="x", padx=10)
        
        # Scale label and entry
        scale_label = ctk.CTkLabel(frame, text="Scale Multiplier")
        scale_label.pack(pady=(5, 0))
        
        scale_entry = ctk.CTkEntry(frame, height=28)
        scale_entry.insert(0, "1")
        scale_entry.pack(fill="x", pady=3, padx=10)
        scale_entry.bind("<KeyRelease>", lambda e: self.schedule_atlas_update())

        blank_var = ctk.BooleanVar(value=False)
        blank_check = ctk.CTkCheckBox(
            frame,
            text="Blank Image (Alpha)",
            variable=blank_var,
            command=self.schedule_atlas_update
        )
        blank_check.pack(pady=(2, 3), anchor="w", padx=10)
        
        # Clear button
        clear_btn = ctk.CTkButton(
            frame, 
            text="Clear", 
            command=lambda idx=slot_index: self.clear_atlas_slot(idx),
            height=25,
            fg_color="#8B0000",
            hover_color="#A52A2A"
        )
        clear_btn.pack(pady=(3, 8), fill="x", padx=10)

        self.register_drop_target(frame, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        self.register_drop_target(title, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        self.register_drop_target(status_label, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        self.register_drop_target(load_btn, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        self.register_drop_target(scale_label, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        self.register_drop_target(scale_entry, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        self.register_drop_target(blank_check, lambda e, idx=slot_index: self.on_slot_section_drop(e, idx))
        
        # Store references
        self.slot_frames.append(frame)
        self.slot_labels.append(status_label)
        self.slot_scale_entries.append(scale_entry)
        self.slot_blank_vars.append(blank_var)

    def create_specular_input_row(self, key, title_text, color):
        row = ctk.CTkFrame(self.specular_controls_frame, fg_color="#1e1e1e")
        row.pack(pady=6, fill="x", padx=5)

        title = ctk.CTkLabel(row, text=title_text, text_color=color, font=("Arial", 12, "bold"))
        title.pack(pady=(6, 2), anchor="w", padx=10)

        status = ctk.CTkLabel(row, text="No image loaded", text_color="#888888")
        status.pack(pady=2, anchor="w", padx=10)

        load_button = ctk.CTkButton(
            row,
            text="Load Image",
            command=lambda channel=key: self.load_specular_input(channel),
            height=28
        )
        load_button.pack(pady=(4, 8), fill="x", padx=10)

        self.specular_labels[key] = status

        self.register_drop_target(row, lambda e, channel=key: self.on_specular_section_drop(e, channel))
        self.register_drop_target(title, lambda e, channel=key: self.on_specular_section_drop(e, channel))
        self.register_drop_target(status, lambda e, channel=key: self.on_specular_section_drop(e, channel))
        self.register_drop_target(load_button, lambda e, channel=key: self.on_specular_section_drop(e, channel))

    # ---------- Single Image Load ----------
    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.dds")]
        )

        if path:
            self.open_image(path)

    def open_image(self, path):
        try:
            self.input_path = path
            self.input_ext = os.path.splitext(path)[1].lower()
            self.input_dds_format = self.detect_dds_pixel_format(path) if self.input_ext == ".dds" else None
            self.image = Image.open(path).convert("RGBA")
            self.tiled_result = None
            self.auto_generate_preview()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Specular Generation ----------
    def load_specular_input(self, channel_key):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.dds")]
        )

        if path:
            self.open_specular_input(channel_key, path)

    def open_specular_input(self, channel_key, path):
        try:
            image = Image.open(path).convert("RGBA")
            self.specular_inputs[channel_key] = image

            if self.input_ext is None:
                self.input_ext = os.path.splitext(path)[1].lower()
                self.input_dds_format = self.detect_dds_pixel_format(path) if self.input_ext == ".dds" else None

            filename = os.path.basename(path)
            if len(filename) > 20:
                filename = filename[:17] + "..."

            self.specular_input_names[channel_key] = filename
            self.specular_labels[channel_key].configure(text=filename, text_color="#00FF00")
            self.auto_generate_specular()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def clear_specular_inputs(self):
        for channel_key in self.specular_inputs:
            self.specular_inputs[channel_key] = None
            self.specular_input_names[channel_key] = None
            if channel_key in self.specular_labels:
                self.specular_labels[channel_key].configure(text="No image loaded", text_color="#888888")

        self.no_metalness_var.set(False)

        self.specular_result = None
        if self.current_output_mode == "specular":
            self.current_output_mode = None
            self.tiled_result = None
            self.canvas.delete("all")

    def on_no_metalness_toggle(self):
        if self.no_metalness_var.get():
            self.specular_labels["metalness"].configure(text="Using black image", text_color="#AAAAAA")
        else:
            metalness = self.specular_inputs["metalness"]
            if metalness is None:
                self.specular_labels["metalness"].configure(text="No image loaded", text_color="#888888")
            else:
                display_name = self.specular_input_names.get("metalness") or "Image loaded"
                self.specular_labels["metalness"].configure(text=display_name, text_color="#00FF00")

        self.auto_generate_specular()

    def auto_generate_specular(self):
        roughness = self.specular_inputs["roughness"]
        ambient_occlusion = self.specular_inputs["ambient_occlusion"]
        metalness = self.specular_inputs["metalness"]

        use_black_metalness = self.no_metalness_var.get()

        if roughness is None or ambient_occlusion is None or (metalness is None and not use_black_metalness):
            if self.current_output_mode == "specular":
                self.specular_result = None
                self.tiled_result = None
                self.canvas.delete("all")
            return

        try:
            target_size = roughness.size

            roughness_l = roughness.resize(target_size, Image.Resampling.NEAREST).convert("L")
            ao_l = ambient_occlusion.resize(target_size, Image.Resampling.NEAREST).convert("L")
            if use_black_metalness:
                metal_l = Image.new("L", target_size, 0)
            else:
                metal_l = metalness.resize(target_size, Image.Resampling.NEAREST).convert("L")

            if self.invert_roughness_var.get():
                roughness_l = ImageOps.invert(roughness_l)

            combined_rgb = Image.merge("RGB", (roughness_l, ao_l, metal_l))
            alpha = Image.new("L", target_size, 255)
            combined_rgba = Image.merge("RGBA", (*combined_rgb.split(), alpha))

            self.specular_result = combined_rgba
            self.tiled_result = combined_rgba
            self.atlas_results = []
            self.current_output_mode = "specular"
            self.refresh_preview()
        except Exception:
            pass

    def register_drop_target(self, widget, handler):
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", handler)
        except Exception:
            pass

    def get_first_supported_path(self, event_data):
        paths = self.parse_dnd_paths(event_data)
        if not paths:
            return None

        path = paths[0]
        ext = os.path.splitext(path)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".dds"}:
            messagebox.showwarning("Unsupported File", "Please drop a PNG, JPG, JPEG, or DDS file.")
            return None

        return path

    def on_single_section_drop(self, event):
        path = self.get_first_supported_path(event.data)
        if path:
            self.open_image(path)

    def on_slot_section_drop(self, event, slot_index):
        path = self.get_first_supported_path(event.data)
        if path:
            self.open_atlas_slot_image(slot_index, path)

    def on_atlas_group_drop(self, event, atlas_index):
        paths = self.parse_dnd_paths(event.data)
        if not paths:
            return

        supported_paths = []
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext in {".png", ".jpg", ".jpeg", ".dds"}:
                supported_paths.append(path)

        if not supported_paths:
            messagebox.showwarning("Unsupported File", "Please drop PNG, JPG, JPEG, or DDS files.")
            return

        base_slot = atlas_index * self.SLOTS_PER_ATLAS
        for i, path in enumerate(supported_paths[:self.SLOTS_PER_ATLAS]):
            self.open_atlas_slot_image(base_slot + i, path)

    def on_specular_section_drop(self, event, channel_key):
        path = self.get_first_supported_path(event.data)
        if path:
            self.open_specular_input(channel_key, path)

    def update_atlas_group_button_text(self, atlas_index):
        icon = "▼" if self.atlas_group_expanded[atlas_index] else "▶"
        text = f"{icon} Atlas {atlas_index + 1}"
        self.atlas_group_buttons[atlas_index].configure(text=text)

    def toggle_atlas_group(self, atlas_index):
        self.set_atlas_group_expanded(atlas_index, not self.atlas_group_expanded[atlas_index])

    def set_atlas_group_expanded(self, atlas_index, expanded):
        is_expanded = self.atlas_group_expanded[atlas_index]
        if expanded == is_expanded:
            return

        if expanded:
            if atlas_index + 1 < len(self.atlas_group_buttons):
                self.atlas_group_bodies[atlas_index].pack(
                    fill="x",
                    pady=(0, 4),
                    before=self.atlas_group_buttons[atlas_index + 1]
                )
            else:
                self.atlas_group_bodies[atlas_index].pack(fill="x", pady=(0, 4))
        else:
            self.atlas_group_bodies[atlas_index].pack_forget()

        self.atlas_group_expanded[atlas_index] = expanded
        self.update_atlas_group_button_text(atlas_index)

    def expand_all_atlas_groups(self):
        for atlas_index in range(self.ATLAS_COUNT):
            self.set_atlas_group_expanded(atlas_index, True)

    def collapse_all_atlas_groups(self):
        for atlas_index in range(self.ATLAS_COUNT):
            self.set_atlas_group_expanded(atlas_index, False)

    def parse_dnd_paths(self, raw_data):
        try:
            return list(self.root.tk.splitlist(raw_data))
        except Exception:
            return [raw_data]

    def detect_dds_pixel_format(self, path):
        try:
            with open(path, "rb") as file:
                header = file.read(132)

            if len(header) < 128 or header[:4] != b"DDS ":
                return None

            fourcc = header[84:88]

            fourcc_map = {
                b"DXT1": "DXT1",
                b"DXT3": "DXT3",
                b"DXT5": "DXT5",
                b"ATI1": "ATI1",
                b"ATI2": "ATI2",
                b"BC4U": "ATI1",
                b"BC5U": "ATI2",
            }
            if fourcc in fourcc_map:
                return fourcc_map[fourcc]

            if fourcc == b"DX10" and len(header) >= 132:
                dxgi_format = int.from_bytes(header[128:132], byteorder="little", signed=False)
                dxgi_map = {
                    71: "DXT1",  # BC1_UNORM
                    72: "DXT1",  # BC1_UNORM_SRGB
                    74: "DXT3",  # BC2_UNORM
                    75: "DXT3",  # BC2_UNORM_SRGB
                    77: "DXT5",  # BC3_UNORM
                    78: "DXT5",  # BC3_UNORM_SRGB
                    80: "ATI1",  # BC4_UNORM
                    83: "ATI2",  # BC5_UNORM
                }
                return dxgi_map.get(dxgi_format)
        except Exception:
            return None

        return None
    
    # ---------- Atlas Slot Management ----------
    def load_atlas_slot(self, slot_index):
        """Load or replace an image in a specific atlas slot"""
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.dds")]
        )
        
        if path:
            self.open_atlas_slot_image(slot_index, path)

    def open_atlas_slot_image(self, slot_index, path):
        try:
            img = Image.open(path).convert("RGBA")
            self.atlas_slots[slot_index]['image'] = img
            self.slot_blank_vars[slot_index].set(False)

            filename = path.split('/')[-1].split('\\')[-1]
            if len(filename) > 20:
                filename = filename[:17] + "..."
            self.slot_labels[slot_index].configure(
                text=filename,
                text_color="#00FF00"
            )

            self.auto_generate_atlas()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def clear_atlas_slot(self, slot_index):
        """Clear a specific atlas slot"""
        self.atlas_slots[slot_index]['image'] = None
        self.slot_blank_vars[slot_index].set(False)
        self.slot_labels[slot_index].configure(
            text="No image loaded",
            text_color="#888888"
        )
        self.schedule_atlas_update()
    
    def clear_atlas(self):
        """Clear all atlas slots"""
        for i in range(self.ATLAS_COUNT * self.SLOTS_PER_ATLAS):
            self.atlas_slots[i]['image'] = None
            self.slot_blank_vars[i].set(False)
            self.slot_labels[i].configure(
                text="No image loaded",
                text_color="#888888"
            )
        self.atlas_result = None
        self.atlas_results = []
        if self.current_output_mode == "atlas":
            self.current_output_mode = None
        self.tiled_result = None
        self.canvas.delete("all")

    def encode_image_to_base64(self, image):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def decode_image_from_base64(self, data):
        image_bytes = base64.b64decode(data.encode("utf-8"))
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    def save_atlas_project(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".atlasproj",
            filetypes=[("Atlas Project", "*.atlasproj"), ("JSON", "*.json")],
            title="Save Atlas Project"
        )
        if not path:
            return

        project_data = {
            "version": 1,
            "target_size": self.tile_size_entry.get().strip() or "1024",
            "slots": []
        }

        for i in range(self.ATLAS_COUNT * self.SLOTS_PER_ATLAS):
            image = self.atlas_slots[i]['image']
            slot_data = {
                "scale": self.slot_scale_entries[i].get().strip() or "1",
                "blank_alpha": bool(self.slot_blank_vars[i].get()),
                "label": self.slot_labels[i].cget("text"),
                "image_base64": self.encode_image_to_base64(image) if image is not None else None,
            }
            project_data["slots"].append(slot_data)

        try:
            with open(path, "w", encoding="utf-8") as project_file:
                json.dump(project_data, project_file)
            messagebox.showinfo("Saved", "Atlas project saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {str(e)}")

    def load_atlas_project(self):
        path = filedialog.askopenfilename(
            filetypes=[("Atlas Project", "*.atlasproj"), ("JSON", "*.json")],
            title="Load Atlas Project"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as project_file:
                project_data = json.load(project_file)

            slots = project_data.get("slots", [])
            target_size = str(project_data.get("target_size", "1024"))

            self.tile_size_entry.delete(0, "end")
            self.tile_size_entry.insert(0, target_size)

            total_slots = self.ATLAS_COUNT * self.SLOTS_PER_ATLAS
            for i in range(total_slots):
                slot_data = slots[i] if i < len(slots) else {}

                scale_value = str(slot_data.get("scale", "1"))
                self.slot_scale_entries[i].delete(0, "end")
                self.slot_scale_entries[i].insert(0, scale_value)

                blank_alpha = bool(slot_data.get("blank_alpha", False))
                self.slot_blank_vars[i].set(blank_alpha)

                image_data = slot_data.get("image_base64")
                if image_data:
                    image = self.decode_image_from_base64(image_data)
                    self.atlas_slots[i]['image'] = image
                    label_text = slot_data.get("label", "Loaded")
                    self.slot_labels[i].configure(text=label_text, text_color="#00FF00")
                else:
                    self.atlas_slots[i]['image'] = None
                    if blank_alpha:
                        self.slot_labels[i].configure(text="Blank alpha", text_color="#AAAAAA")
                    else:
                        self.slot_labels[i].configure(text="No image loaded", text_color="#888888")

            self.controls_tabs.set("Multi Atlas")
            self.auto_generate_atlas()
            messagebox.showinfo("Loaded", "Atlas project loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {str(e)}")

    # ---------- Tile ----------
    def tile_image(self, img, multiplier):
        w, h = img.size
        new_img = Image.new("RGBA", (w * multiplier, h * multiplier))

        for x in range(multiplier):
            for y in range(multiplier):
                new_img.paste(img, (x * w, y * h))

        return new_img

    # ---------- Preview ----------
    def schedule_preview_update(self):
        """Debounce preview updates"""
        if hasattr(self, '_preview_job'):
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(300, self.auto_generate_preview)
    
    def schedule_atlas_update(self):
        """Debounce atlas updates"""
        if hasattr(self, '_atlas_job'):
            self.root.after_cancel(self._atlas_job)
        self._atlas_job = self.root.after(300, self.auto_generate_atlas)
    
    def auto_generate_preview(self):
        """Auto-generate preview for single image (silent)"""
        if self.image is None:
            return

        try:
            multiplier = int(self.multiplier_entry.get())
            if multiplier <= 0:
                return
        except:
            return

        self.tiled_result = self.tile_image(self.image, multiplier)
        self.atlas_results = []
        self.current_output_mode = "single"
        self.refresh_preview()

    def refresh_preview(self, event=None):
        if self.tiled_result is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        preview = self.tiled_result.copy()
        preview.thumbnail((canvas_w, canvas_h))

        self.preview_img = ImageTk.PhotoImage(preview)

        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_w // 2,
            canvas_h // 2,
            image=self.preview_img,
            anchor="center"
        )

    # ---------- Save ----------
    def save_single_atlas(self, atlas_index):
        try:
            target_size = int(self.tile_size_entry.get())
            if target_size <= 0:
                messagebox.showwarning("Invalid Size", "Target Atlas Width must be a positive number.")
                return
        except Exception:
            messagebox.showwarning("Invalid Size", "Target Atlas Width must be a positive number.")
            return

        atlas = self.build_atlas_for_index(atlas_index, target_size)
        if atlas is None:
            messagebox.showwarning("Nothing to Save", f"Atlas {atlas_index + 1} has no content.")
            return

        default_ext = ".dds" if self.input_ext == ".dds" else ".png"
        path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=[("DDS", "*.dds"), ("PNG", "*.png"), ("JPEG", "*.jpg")],
            title=f"Save Atlas {atlas_index + 1}"
        )

        if not path:
            return

        ext = os.path.splitext(path)[1].lower() or default_ext
        if ext not in {".dds", ".png", ".jpg", ".jpeg"}:
            ext = default_ext
            path = path + ext

        self.save_image_with_extension(atlas, path, ext)
        messagebox.showinfo("Saved", f"Atlas {atlas_index + 1} saved successfully.")

    def save_image(self):
        if self.tiled_result is None:
            messagebox.showwarning("Nothing to Save", "Generate preview first.")
            return

        if self.current_output_mode == "atlas" and self.atlas_results:
            default_ext = ".dds" if self.input_ext == ".dds" else ".png"
            saved_paths = []
            for i, atlas in enumerate(self.atlas_results):
                atlas_path = filedialog.asksaveasfilename(
                    defaultextension=default_ext,
                    filetypes=[("DDS", "*.dds"), ("PNG", "*.png"), ("JPEG", "*.jpg")],
                    title=f"Save Atlas {i + 1}"
                )

                if not atlas_path:
                    continue

                ext = os.path.splitext(atlas_path)[1].lower() or default_ext
                if ext not in {".dds", ".png", ".jpg", ".jpeg"}:
                    ext = default_ext
                    atlas_path = atlas_path + ext

                self.save_image_with_extension(atlas, atlas_path, ext)
                saved_paths.append(os.path.basename(atlas_path))

            if saved_paths:
                messagebox.showinfo("Saved", f"Saved {len(saved_paths)} atlases:\n" + "\n".join(saved_paths))
            return

        default_ext = ".dds" if self.input_ext == ".dds" else ".png"
        path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=[("DDS", "*.dds"), ("PNG", "*.png"), ("JPEG", "*.jpg")]
        )

        if path:
            ext = os.path.splitext(path)[1].lower()

            self.save_image_with_extension(self.tiled_result, path, ext)

            messagebox.showinfo("Saved", "Image saved successfully.")

    def save_image_with_extension(self, image, path, ext):
        if ext == ".dds":
            selected_dds = self.dds_format_var.get()
            should_generate_mipmaps = self.generate_mipmaps_var.get()
            if selected_dds == "Auto":
                save_format = self.input_dds_format or "DXT5"
            else:
                save_format = self.DDS_OPTION_TO_PIXEL_FORMAT.get(selected_dds)
            try:
                if save_format:
                    image.save(path, format="DDS", pixel_format=save_format, mipmaps=should_generate_mipmaps)
                else:
                    image.save(path, format="DDS", mipmaps=should_generate_mipmaps)
            except TypeError:
                if save_format:
                    image.save(path, format="DDS", pixel_format=save_format)
                else:
                    image.save(path, format="DDS")
        elif ext in {".jpg", ".jpeg"}:
            image.convert("RGB").save(path)
        else:
            image.save(path)

    # ---------- Atlas Creation ----------
    def build_atlas_for_index(self, atlas_index, target_size):
        start = atlas_index * self.SLOTS_PER_ATLAS
        end = start + self.SLOTS_PER_ATLAS

        processed_images = []
        for i in range(start, end):
            slot = self.atlas_slots[i]

            if slot['image'] is not None:
                try:
                    scale = int(self.slot_scale_entries[i].get())
                    if scale <= 0:
                        scale = 1
                except Exception:
                    scale = 1

                tiled_img = self.tile_image(slot['image'], scale)
                square_img = tiled_img.resize((target_size, target_size), Image.Resampling.NEAREST)
                processed_images.append(square_img)
            elif self.slot_blank_vars[i].get():
                processed_images.append(Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0)))
            else:
                processed_images.append(None)

        return self.build_single_atlas(processed_images, target_size)

    def auto_generate_atlas(self):
        """Auto-generate atlas (silent)"""
        # Check if at least one image is loaded
        has_content = any(
            slot['image'] is not None or self.slot_blank_vars[i].get()
            for i, slot in enumerate(self.atlas_slots)
        )
        if not has_content:
            # Clear canvas if no images
            self.tiled_result = None
            self.atlas_results = []
            self.canvas.delete("all")
            return
        
        try:
            target_size = int(self.tile_size_entry.get())
            if target_size <= 0:
                return
        except:
            return
        
        try:
            atlas_results = []
            for atlas_index in range(self.ATLAS_COUNT):
                atlas = self.build_atlas_for_index(atlas_index, target_size)
                if atlas is not None:
                    atlas_results.append(atlas)

            if not atlas_results:
                self.atlas_results = []
                self.tiled_result = None
                self.canvas.delete("all")
                return

            self.atlas_results = atlas_results
            self.atlas_result = atlas_results[0]
            self.tiled_result = self.build_multi_atlas_preview(atlas_results, target_size)
            self.current_output_mode = "atlas"
            self.refresh_preview()
            
        except Exception as e:
            # Silent error handling for auto-generation
            pass

    def build_single_atlas(self, processed_images, target_size):
        loaded_images = [img for img in processed_images if img is not None]
        if not loaded_images:
            return None

        num_loaded = len(loaded_images)
        num_slots = 4 if num_loaded == 3 else num_loaded

        atlas_width = target_size
        atlas_height = target_size * num_slots
        atlas = Image.new("RGBA", (atlas_width, atlas_height))

        slot_idx = 0
        last_valid_image = None
        for img in processed_images:
            if img is not None:
                y_pos = slot_idx * target_size
                atlas.paste(img, (0, y_pos))
                last_valid_image = img
                slot_idx += 1

        if num_loaded == 3 and last_valid_image is not None:
            avg_color = self.get_average_color(last_valid_image)
            inverted_color = self.invert_color(avg_color)
            fill_img = Image.new("RGBA", (target_size, target_size), inverted_color)
            atlas.paste(fill_img, (0, 3 * target_size))

        return atlas

    def build_multi_atlas_preview(self, atlas_results, target_size):
        max_height = max(atlas.height for atlas in atlas_results)

        preview = Image.new("RGBA", (target_size * len(atlas_results), max_height))
        for i, atlas in enumerate(atlas_results):
            x_offset = i * target_size
            preview.paste(atlas, (x_offset, 0))
        return preview
    
    def make_square_by_tiling(self, img, target_size):
        """Tile an image to make it square at target_size x target_size"""
        w, h = img.size
        
        # If already the right size, return as is
        if w == target_size and h == target_size:
            return img
        
        # Create new square image
        new_img = Image.new("RGBA", (target_size, target_size))
        
        # Tile the image to fill the square
        tiles_x = (target_size + w - 1) // w  # Ceiling division
        tiles_y = (target_size + h - 1) // h
        
        for x in range(tiles_x):
            for y in range(tiles_y):
                paste_x = x * w
                paste_y = y * h
                
                # Crop if we go beyond target_size
                if paste_x < target_size and paste_y < target_size:
                    # Calculate how much of the image we can paste
                    crop_w = min(w, target_size - paste_x)
                    crop_h = min(h, target_size - paste_y)
                    
                    if crop_w < w or crop_h < h:
                        cropped = img.crop((0, 0, crop_w, crop_h))
                        new_img.paste(cropped, (paste_x, paste_y))
                    else:
                        new_img.paste(img, (paste_x, paste_y))
        
        return new_img

    def get_average_color(self, img):
        """Calculate the average color of an image"""
        # Resize to 1x1 to get average color
        avg_img = img.resize((1, 1), Image.Resampling.LANCZOS)
        return avg_img.getpixel((0, 0))

    def invert_color(self, color):
        """Invert an RGBA color"""
        r, g, b, a = color
        return (255 - r, 255 - g, 255 - b, a)


# ===== Main =====
if __name__ == "__main__":

    root = TkinterDnD.Tk()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root.configure(bg="#242424")

    root.title("VRT FS25 Texture Editor")
    root.geometry("1000x650")
    root.minsize(800, 550)

    app = TileResizerApp(root)

    root.update()
    root.mainloop()

