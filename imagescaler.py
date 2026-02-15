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

        # ===== Layout =====
        self.left_frame = ctk.CTkFrame(root, width=220, fg_color="#2b2b2b")
        self.right_frame = ctk.CTkFrame(root, fg_color="#2b2b2b")

        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        # ===== Controls =====
        self.load_btn = ctk.CTkButton(self.left_frame, text="Load Image", command=self.load_image)
        self.load_btn.pack(pady=10, fill="x")

        self.multiplier_label = ctk.CTkLabel(self.left_frame, text="Resize Multiplier")
        self.multiplier_label.pack(pady=(15, 0))

        self.multiplier_entry = ctk.CTkEntry(self.left_frame)
        self.multiplier_entry.insert(0, "2")
        self.multiplier_entry.pack(fill="x", pady=5)

        self.preview_btn = ctk.CTkButton(self.left_frame, text="Generate Preview", command=self.generate_preview)
        self.preview_btn.pack(pady=10, fill="x")

        self.save_btn = ctk.CTkButton(self.left_frame, text="Save Image", command=self.save_image)
        self.save_btn.pack(pady=5, fill="x")

        # ===== Drag & Drop Label =====
        self.drop_label = ctk.CTkLabel(
            self.left_frame,
            text="Drag & Drop Image Here",
            height=80
        )
        self.drop_label.pack(pady=20, fill="x")

        try:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self.drop_image)
        except Exception:
            self.drop_label.configure(text="Drag & Drop Unavailable\n(use Load Image)")

        # ===== Preview Canvas =====
        self.canvas = ctk.CTkCanvas(
            self.right_frame,
            bg="#2b2b2b",
            highlightthickness=0
        )

        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self.refresh_preview)

    # ---------- Load ----------
    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )

        if path:
            self.open_image(path)

    def drop_image(self, event):
        path = event.data.strip("{}")
        self.open_image(path)

    def open_image(self, path):
        try:
            self.image = Image.open(path).convert("RGBA")
            self.tiled_result = None
            messagebox.showinfo("Loaded", "Image loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Tile ----------
    def tile_image(self, img, multiplier):
        w, h = img.size
        new_img = Image.new("RGBA", (w * multiplier, h * multiplier))

        for x in range(multiplier):
            for y in range(multiplier):
                new_img.paste(img, (x * w, y * h))

        return new_img

    # ---------- Preview ----------
    def generate_preview(self):
        if self.image is None:
            messagebox.showwarning("No Image", "Load an image first.")
            return

        try:
            multiplier = int(self.multiplier_entry.get())
            if multiplier <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Multiplier must be positive integer.")
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

