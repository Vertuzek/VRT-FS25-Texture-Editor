import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk



class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        TkinterDnD.DnDWrapper.__init__(self, *args, **kwargs)

# ===== App =====
class TileResizerApp:

    def __init__(self, root):
        self.root = root
        self.image = None
        self.tiled_result = None
        self.preview_img = None
        self.atlas_result = None
        
        # Atlas data: list of dicts with 'image' and 'scale'
        self.atlas_slots = [
            {'image': None, 'scale': 1},
            {'image': None, 'scale': 1},
            {'image': None, 'scale': 1},
            {'image': None, 'scale': 1}
        ]
        
        # UI references for each slot
        self.slot_frames = []
        self.slot_labels = []
        self.slot_scale_entries = []

        # ===== Layout =====
        self.left_frame = ctk.CTkScrollableFrame(root, width=250, fg_color="#2b2b2b")
        self.right_frame = ctk.CTkFrame(root, fg_color="#2b2b2b")

        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        # ===== Single Image Controls =====
        self.single_title = ctk.CTkLabel(self.left_frame, text="Single Image Tiling", font=("Arial", 14, "bold"))
        self.single_title.pack(pady=(5, 10))
        
        self.load_btn = ctk.CTkButton(self.left_frame, text="Load Image", command=self.load_image)
        self.load_btn.pack(pady=5, fill="x")

        self.multiplier_label = ctk.CTkLabel(self.left_frame, text="Resize Multiplier")
        self.multiplier_label.pack(pady=(10, 0))

        self.multiplier_entry = ctk.CTkEntry(self.left_frame)
        self.multiplier_entry.insert(0, "2")
        self.multiplier_entry.pack(fill="x", pady=5)
        self.multiplier_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())

        self.save_btn = ctk.CTkButton(self.left_frame, text="Save Image", command=self.save_image)
        self.save_btn.pack(pady=5, fill="x")

        # ===== ATLAS CREATION =====
        self.atlas_separator = ctk.CTkLabel(self.left_frame, text="─" * 35)
        self.atlas_separator.pack(pady=(20, 10))

        self.atlas_title = ctk.CTkLabel(self.left_frame, text="Atlas Creation", font=("Arial", 14, "bold"))
        self.atlas_title.pack(pady=5)

        self.tile_size_label = ctk.CTkLabel(self.left_frame, text="Target Atlas Width")
        self.tile_size_label.pack(pady=(5, 0))

        self.tile_size_entry = ctk.CTkEntry(self.left_frame)
        self.tile_size_entry.insert(0, "1024")
        self.tile_size_entry.pack(fill="x", pady=5)
        self.tile_size_entry.bind("<KeyRelease>", lambda e: self.schedule_atlas_update())

        # Create 4 image slots
        for i in range(4):
            self.create_atlas_slot(i)

        self.clear_atlas_btn = ctk.CTkButton(self.left_frame, text="Clear All Slots", command=self.clear_atlas)
        self.clear_atlas_btn.pack(pady=2, fill="x")

        # ===== Preview Canvas =====
        self.canvas = ctk.CTkCanvas(
            self.right_frame,
            bg="#2b2b2b",
            highlightthickness=0
        )

        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self.refresh_preview)
    
    def create_atlas_slot(self, slot_index):
        """Create UI for one atlas slot"""
        frame = ctk.CTkFrame(self.left_frame, fg_color="#1e1e1e")
        frame.pack(pady=8, fill="x", padx=5)
        
        # Title
        title = ctk.CTkLabel(frame, text=f"Slot {slot_index + 1}", font=("Arial", 12, "bold"))
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
        
        # Store references
        self.slot_frames.append(frame)
        self.slot_labels.append(status_label)
        self.slot_scale_entries.append(scale_entry)

    # ---------- Single Image Load ----------
    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )

        if path:
            self.open_image(path)

    def open_image(self, path):
        try:
            self.image = Image.open(path).convert("RGBA")
            self.tiled_result = None
            self.auto_generate_preview()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    # ---------- Atlas Slot Management ----------
    def load_atlas_slot(self, slot_index):
        """Load or replace an image in a specific atlas slot"""
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        
        if path:
            try:
                img = Image.open(path).convert("RGBA")
                self.atlas_slots[slot_index]['image'] = img
                
                # Update UI
                filename = path.split('/')[-1].split('\\')[-1]
                if len(filename) > 20:
                    filename = filename[:17] + "..."
                self.slot_labels[slot_index].configure(
                    text=filename,
                    text_color="#00FF00"
                )
                
                # Auto-generate atlas after loading
                self.auto_generate_atlas()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def clear_atlas_slot(self, slot_index):
        """Clear a specific atlas slot"""
        self.atlas_slots[slot_index]['image'] = None
        self.slot_labels[slot_index].configure(
            text="No image loaded",
            text_color="#888888"
        )
        self.schedule_atlas_update()
    
    def clear_atlas(self):
        """Clear all atlas slots"""
        for i in range(4):
            self.atlas_slots[i]['image'] = None
            self.slot_labels[i].configure(
                text="No image loaded",
                text_color="#888888"
            )
        self.atlas_result = None
        self.tiled_result = None
        self.canvas.delete("all")

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
    def save_image(self):
        if self.tiled_result is None:
            messagebox.showwarning("Nothing to Save", "Generate preview first.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
        )

        if path:
            self.tiled_result.convert("RGB").save(path)
            messagebox.showinfo("Saved", "Image saved successfully.")

    # ---------- Atlas Creation ----------
    def auto_generate_atlas(self):
        """Auto-generate atlas (silent)"""
        # Check if at least one image is loaded
        loaded_slots = [slot for slot in self.atlas_slots if slot['image'] is not None]
        if not loaded_slots:
            # Clear canvas if no images
            self.tiled_result = None
            self.canvas.delete("all")
            return
        
        try:
            target_size = int(self.tile_size_entry.get())
            if target_size <= 0:
                return
        except:
            return
        
        try:
            # Process each slot with its individual scale
            processed_images = []
            last_valid_image = None
            
            for i, slot in enumerate(self.atlas_slots):
                if slot['image'] is not None:
                    # Get scale for this slot
                    try:
                        scale = int(self.slot_scale_entries[i].get())
                        if scale <= 0:
                            scale = 1
                    except:
                        scale = 1
                    
                    # Tile the image with its scale
                    tiled_img = self.tile_image(slot['image'], scale)
                    
                    # Resize to target size (nearest neighbor to preserve pixels)
                    square_img = tiled_img.resize((target_size, target_size), Image.Resampling.NEAREST)
                    processed_images.append(square_img)
                    last_valid_image = square_img
                else:
                    processed_images.append(None)
            
            # Count loaded images
            num_loaded = sum(1 for img in processed_images if img is not None)
            
            # Determine number of slots: if 3 images, use 4 slots; otherwise use num_loaded
            if num_loaded == 3:
                num_slots = 4
            else:
                num_slots = num_loaded
            
            atlas_width = target_size
            atlas_height = target_size * num_slots
            
            # Create the atlas
            atlas = Image.new("RGBA", (atlas_width, atlas_height))
            
            # Paste loaded images and fill empty slots if needed
            slot_idx = 0
            for i in range(4):
                if processed_images[i] is not None:
                    y_pos = slot_idx * target_size
                    atlas.paste(processed_images[i], (0, y_pos))
                    slot_idx += 1
            
            # If we have 3 images, fill the 4th slot with inverted color
            if num_loaded == 3 and last_valid_image is not None:
                avg_color = self.get_average_color(last_valid_image)
                inverted_color = self.invert_color(avg_color)
                fill_img = Image.new("RGBA", (target_size, target_size), inverted_color)
                atlas.paste(fill_img, (0, 3 * target_size))
            
            self.atlas_result = atlas
            self.tiled_result = atlas  # Use tiled_result for preview/save
            self.refresh_preview()
            
        except Exception as e:
            # Silent error handling for auto-generation
            pass
    
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

    root.title("Tile Image Resizer")
    root.geometry("1000x650")
    root.minsize(800, 550)

    app = TileResizerApp(root)

    root.update()
    root.mainloop()

