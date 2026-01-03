"""
Pixel Art Automation Tool
Converts images to 32x32 and automates painting in external apps.
Press Ctrl to pause/abort at any time.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import autoit  # PyAutoIt
import keyboard
import threading
import time
import json
import os
import random
import math
from collections import defaultdict

# Settings file path
SETTINGS_FILE = "pixel_painter_settings.json"

class PixelPainterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel Painter Automation")
        self.root.geometry("650x800")
        
        # State variables
        self.image = None
        self.preview_image = None
        self.pixel_colors = []
        self.is_painting = False
        self.is_paused = False
        self.should_abort = False
        
        # Mouse tracking
        self.show_mouse_pos = False
        self.mouse_label = None
        
        # Set AutoIt options
        autoit.opt("MouseCoordMode", 1)  # Absolute screen coordinates
        autoit.opt("SendKeyDelay", 10)   # Faster key sending
        
        self.setup_scrollable_ui()
        self.setup_keyboard_listener()
        self.load_settings()
        
    def setup_scrollable_ui(self):
        """Setup a scrollable main container"""
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas, padding="10")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Button-4>", self.on_mousewheel)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel)
        
        self.setup_ui_content()
        
    def on_canvas_configure(self, event):
        """Adjust the scrollable frame width when canvas is resized"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def setup_ui_content(self):
        """Setup all UI elements inside the scrollable frame"""
        main_frame = self.scrollable_frame
        
        # --- Image Upload Section ---
        upload_frame = ttk.LabelFrame(main_frame, text="Image Upload", padding="10")
        upload_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.upload_btn = ttk.Button(upload_frame, text="Upload Image (PNG/JPEG/WEBP)", 
                                      command=self.upload_image)
        self.upload_btn.pack(fill=tk.X)
        
        self.image_status = ttk.Label(upload_frame, text="No image loaded")
        self.image_status.pack(pady=(5, 0))
        
        # --- Image Preview Section ---
        preview_frame = ttk.LabelFrame(main_frame, text="32x32 Preview", padding="10")
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_canvas = tk.Canvas(preview_frame, width=256, height=256, 
                                         bg="#2a2a2a", highlightthickness=1,
                                         highlightbackground="#555")
        self.preview_canvas.pack()
        
        self.preview_canvas.create_text(128, 128, text="No image loaded", 
                                         fill="#888", font=("Arial", 12),
                                         tags="placeholder")
        
        self.color_count_label = ttk.Label(preview_frame, text="")
        self.color_count_label.pack(pady=(5, 0))
        
        # --- Mouse Position Tracker ---
        mouse_frame = ttk.LabelFrame(main_frame, text="Mouse Position", padding="10")
        mouse_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mouse_toggle_btn = ttk.Button(mouse_frame, text="Show Mouse Position", 
                                            command=self.toggle_mouse_tracking)
        self.mouse_toggle_btn.pack(fill=tk.X)
        
        self.mouse_pos_label = ttk.Label(mouse_frame, text="X: --- Y: ---", font=("Courier", 12))
        self.mouse_pos_label.pack(pady=(5, 0))
        
        # --- Coordinate Settings ---
        coords_frame = ttk.LabelFrame(main_frame, text="Coordinate Settings", padding="10")
        coords_frame.pack(fill=tk.X, pady=(0, 10))
        
        coord_grid = ttk.Frame(coords_frame)
        coord_grid.pack(fill=tk.X)
        
        ttk.Label(coord_grid, text="Start X:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.start_x = ttk.Entry(coord_grid, width=10)
        self.start_x.grid(row=0, column=1, padx=5, pady=2)
        self.start_x.insert(0, "100")
        
        ttk.Label(coord_grid, text="Start Y:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.start_y = ttk.Entry(coord_grid, width=10)
        self.start_y.grid(row=0, column=3, padx=5, pady=2)
        self.start_y.insert(0, "100")
        
        ttk.Label(coord_grid, text="End X:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.end_x = ttk.Entry(coord_grid, width=10)
        self.end_x.grid(row=1, column=1, padx=5, pady=2)
        self.end_x.insert(0, "420")
        
        ttk.Label(coord_grid, text="End Y:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.end_y = ttk.Entry(coord_grid, width=10)
        self.end_y.grid(row=1, column=3, padx=5, pady=2)
        self.end_y.insert(0, "420")
        
        ttk.Label(coord_grid, text="Button X:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.button_x = ttk.Entry(coord_grid, width=10)
        self.button_x.grid(row=2, column=1, padx=5, pady=2)
        self.button_x.insert(0, "50")
        
        ttk.Label(coord_grid, text="Button Y:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.button_y = ttk.Entry(coord_grid, width=10)
        self.button_y.grid(row=2, column=3, padx=5, pady=2)
        self.button_y.insert(0, "500")
        
        ttk.Label(coord_grid, text="Hex Input X:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.hex_x = ttk.Entry(coord_grid, width=10)
        self.hex_x.grid(row=3, column=1, padx=5, pady=2)
        self.hex_x.insert(0, "150")
        
        ttk.Label(coord_grid, text="Hex Input Y:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        self.hex_y = ttk.Entry(coord_grid, width=10)
        self.hex_y.grid(row=3, column=3, padx=5, pady=2)
        self.hex_y.insert(0, "500")
        
        save_btn = ttk.Button(coords_frame, text="💾 Save Settings", command=self.save_settings)
        save_btn.pack(fill=tk.X, pady=(10, 0))
        
        # --- Movement Settings ---
        move_frame = ttk.LabelFrame(main_frame, text="Movement Settings", padding="10")
        move_frame.pack(fill=tk.X, pady=(0, 10))
        
        move_grid = ttk.Frame(move_frame)
        move_grid.pack(fill=tk.X)
        
        ttk.Label(move_grid, text="Mouse Speed (1-100):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.mouse_speed = ttk.Entry(move_grid, width=10)
        self.mouse_speed.grid(row=0, column=1, padx=5)
        self.mouse_speed.insert(0, "10")
        
        ttk.Label(move_grid, text="Action Delay (sec):").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.action_delay = ttk.Entry(move_grid, width=10)
        self.action_delay.grid(row=0, column=3, padx=5)
        self.action_delay.insert(0, "0.08")
        
        ttk.Label(move_grid, text="Color Tolerance:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.color_tolerance = ttk.Entry(move_grid, width=10)
        self.color_tolerance.grid(row=1, column=1, padx=5)
        self.color_tolerance.insert(0, "30")
        
        # --- Control Buttons ---
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_grid = ttk.Frame(control_frame)
        btn_grid.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(btn_grid, text="▶ Start Painting", 
                                     command=self.start_painting)
        self.start_btn.grid(row=0, column=0, padx=2, sticky=tk.EW)
        
        self.pause_btn = ttk.Button(btn_grid, text="⏸ Pause", 
                                     command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.grid(row=0, column=1, padx=2, sticky=tk.EW)
        
        self.abort_btn = ttk.Button(btn_grid, text="⏹ Abort", 
                                     command=self.abort_painting, state=tk.DISABLED)
        self.abort_btn.grid(row=0, column=2, padx=2, sticky=tk.EW)
        
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)
        btn_grid.columnconfigure(2, weight=1)
        
        ttk.Label(control_frame, text="💡 Press F1 anytime to pause/resume", 
                  foreground="#888").pack(pady=(5, 0))
        
        # --- Status ---
        status_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = tk.Text(status_frame, height=6, state=tk.DISABLED, 
                                    bg="#1a1a1a", fg="#00ff00", font=("Courier", 9))
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(5, 0))
        
    def setup_keyboard_listener(self):
        """Setup Ctrl key listener for pause/abort"""
        keyboard.on_press_key('f1', self.on_ctrl_press)
        
    def on_ctrl_press(self, e):
        """Handle Ctrl key press"""
        if self.is_painting:
            self.toggle_pause()
            
    def log_status(self, message):
        """Add message to status log"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
    def save_settings(self):
        """Save current settings to file"""
        settings = {
            'start_x': self.start_x.get(),
            'start_y': self.start_y.get(),
            'end_x': self.end_x.get(),
            'end_y': self.end_y.get(),
            'button_x': self.button_x.get(),
            'button_y': self.button_y.get(),
            'hex_x': self.hex_x.get(),
            'hex_y': self.hex_y.get(),
            'mouse_speed': self.mouse_speed.get(),
            'action_delay': self.action_delay.get(),
            'color_tolerance': self.color_tolerance.get()
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            self.log_status("✓ Settings saved!")
        except Exception as e:
            self.log_status(f"❌ Failed to save settings: {e}")
            
    def load_settings(self):
        """Load settings from file if it exists"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                
                for field, value in [
                    (self.start_x, settings.get('start_x', '100')),
                    (self.start_y, settings.get('start_y', '100')),
                    (self.end_x, settings.get('end_x', '420')),
                    (self.end_y, settings.get('end_y', '420')),
                    (self.button_x, settings.get('button_x', '50')),
                    (self.button_y, settings.get('button_y', '500')),
                    (self.hex_x, settings.get('hex_x', '150')),
                    (self.hex_y, settings.get('hex_y', '500')),
                    (self.mouse_speed, settings.get('mouse_speed', '10')),
                    (self.action_delay, settings.get('action_delay', '0.08')),
                    (self.color_tolerance, settings.get('color_tolerance', '30')),
                ]:
                    field.delete(0, tk.END)
                    field.insert(0, value)
                    
                self.log_status("✓ Settings loaded from file")
            except Exception as e:
                self.log_status(f"⚠ Could not load settings: {e}")
        
    def upload_image(self):
        """Open file dialog and load image"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                img = Image.open(file_path)
                img = img.convert('RGB')
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
                self.image = img
                
                self.pixel_colors = []
                for y in range(32):
                    row = []
                    for x in range(32):
                        r, g, b = img.getpixel((x, y))
                        hex_color = f"{r:02x}{g:02x}{b:02x}"
                        row.append(hex_color)
                    self.pixel_colors.append(row)
                
                self.update_preview()
                
                unique_colors = set()
                for row in self.pixel_colors:
                    unique_colors.update(row)
                
                filename = file_path.split('/')[-1].split('\\')[-1]
                self.image_status.config(text=f"✓ Loaded: {filename}")
                self.color_count_label.config(text=f"🎨 {len(unique_colors)} unique colors")
                self.log_status(f"Image loaded: {filename} → 32x32")
                self.log_status(f"Found {len(unique_colors)} unique colors")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
                
    def update_preview(self):
        """Update the image preview canvas"""
        if self.image:
            preview_img = self.image.resize((256, 256), Image.Resampling.NEAREST)
            self.preview_image = ImageTk.PhotoImage(preview_img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(128, 128, image=self.preview_image)
            
            for i in range(1, 32):
                pos = i * 8
                self.preview_canvas.create_line(pos, 0, pos, 256, fill="#333", width=1)
                self.preview_canvas.create_line(0, pos, 256, pos, fill="#333", width=1)
            
    def toggle_mouse_tracking(self):
        """Toggle mouse position tracking"""
        self.show_mouse_pos = not self.show_mouse_pos
        
        if self.show_mouse_pos:
            self.mouse_toggle_btn.config(text="Hide Mouse Position")
            self.update_mouse_position()
        else:
            self.mouse_toggle_btn.config(text="Show Mouse Position")
            self.mouse_pos_label.config(text="X: --- Y: ---")
            
    def update_mouse_position(self):
        """Update mouse position display using AutoIt"""
        if self.show_mouse_pos:
            pos = autoit.mouse_get_pos()
            x, y = pos[0], pos[1]
            self.mouse_pos_label.config(text=f"X: {x}  Y: {y}")
            self.root.after(50, self.update_mouse_position)
            
    def get_coords(self):
        """Get all coordinate values"""
        try:
            return {
                'start_x': int(self.start_x.get()),
                'start_y': int(self.start_y.get()),
                'end_x': int(self.end_x.get()),
                'end_y': int(self.end_y.get()),
                'button_x': int(self.button_x.get()),
                'button_y': int(self.button_y.get()),
                'hex_x': int(self.hex_x.get()),
                'hex_y': int(self.hex_y.get()),
                'speed': int(self.mouse_speed.get()),
                'delay': float(self.action_delay.get()),
                'tolerance': int(self.color_tolerance.get())
            }
        except ValueError:
            messagebox.showerror("Error", "All coordinate values must be numbers")
            return None

    def get_tile_position(self, x, y, coords, tile_width, tile_height):
        """Calculate the center position of a tile"""
        tile_x = int(coords['start_x'] + (x * tile_width) + (tile_width / 2))
        tile_y = int(coords['start_y'] + (y * tile_height) + (tile_height / 2))
        return tile_x, tile_y

    def human_like_move(self, target_x, target_y, speed):
        """Move mouse with natural human-like motion using AutoIt"""
        target_x += random.randint(-2, 2)
        target_y += random.randint(-2, 2)
        
        autoit_speed = max(1, min(100, 101 - speed))
        autoit.mouse_move(target_x, target_y, speed=autoit_speed)

    def wiggle_mouse(self):
        """Small wiggle to ensure position is registered"""
        pos = autoit.mouse_get_pos()
        x, y = pos[0], pos[1]
        for _ in range(2):
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            autoit.mouse_move(x + offset_x, y + offset_y, speed=0)
            time.sleep(0.01)
        autoit.mouse_move(x, y, speed=0)
        time.sleep(0.01)

    def reliable_click(self, x, y, speed=10):
        """Perform a reliable click with human-like movement using AutoIt"""
        self.human_like_move(x, y, speed)
        self.wiggle_mouse()
        time.sleep(random.uniform(0.02, 0.05))
        autoit.mouse_click("left")
        time.sleep(random.uniform(0.03, 0.06))
            
    def calculate_luminance(self, hex_color):
        """Calculate luminance of a hex color using standard formula"""
        # Parse hex color
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Standard luminance formula: 0.299*R + 0.587*G + 0.114*B
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        
        return luminance

    def calculate_color_distance(self, hex_color1, hex_color2):
        """Calculate Euclidean distance between two hex colors"""
        # Parse first color
        r1 = int(hex_color1[0:2], 16)
        g1 = int(hex_color1[2:4], 16)
        b1 = int(hex_color1[4:6], 16)
        
        # Parse second color
        r2 = int(hex_color2[0:2], 16)
        g2 = int(hex_color2[2:4], 16)
        b2 = int(hex_color2[4:6], 16)
        
        # Calculate Euclidean distance in RGB space
        distance = math.sqrt((r2 - r1) ** 2 + (g2 - g1) ** 2 + (b2 - b1) ** 2)
        
        return distance

    def start_painting(self):
        """Start the painting automation"""
        if not self.pixel_colors:
            messagebox.showwarning("Warning", "Please upload an image first")
            return
            
        coords = self.get_coords()
        if not coords:
            return
            
        self.is_painting = True
        self.is_paused = False
        self.should_abort = False
        
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.abort_btn.config(state=tk.NORMAL)
        
        thread = threading.Thread(target=self.painting_loop, args=(coords,))
        thread.daemon = True
        thread.start()
        
    def painting_loop(self, coords):
        """Main painting automation loop - darkest to brightest"""
        try:
            for i in range(3, 0, -1):
                self.log_status(f"Starting in {i}... Switch to Roblox!")
                time.sleep(1)
            
            self.log_status("🎨 Starting painting (darkest to brightest)...")
            
            grid_width = coords['end_x'] - coords['start_x']
            grid_height = coords['end_y'] - coords['start_y']
            tile_width = grid_width / 32
            tile_height = grid_height / 32
            
            self.log_status(f"Tile size: {tile_width:.1f}x{tile_height:.1f}px")
            
            # Collect all pixels with their colors and calculate luminance
            pixels = []
            for y in range(32):
                for x in range(32):
                    hex_color = self.pixel_colors[y][x].lower()
                    luminance = self.calculate_luminance(hex_color)
                    tile_x, tile_y = self.get_tile_position(x, y, coords, tile_width, tile_height)
                    pixels.append((luminance, hex_color, x, y, tile_x, tile_y))
            
            # Sort by luminance (darkest first)
            pixels.sort(key=lambda p: p[0])
            
            self.log_status(f"Sorted {len(pixels)} pixels by luminance")
            
            total_pixels = len(pixels)
            painted_pixels = 0
            color_changes = 0
            skipped_color_changes = 0
            
            speed = coords['speed']
            delay = coords['delay']
            tolerance = coords['tolerance']
            
            # Track previous color
            previous_color = None
            
            # Process each pixel individually in darkest-to-brightest order
            for pixel_index, (luminance, hex_color, x, y, tile_x, tile_y) in enumerate(pixels):
                if self.should_abort:
                    self.log_status("❌ Painting aborted!")
                    self.finish_painting()
                    return
                
                while self.is_paused:
                    time.sleep(0.1)
                    if self.should_abort:
                        self.finish_painting()
                        return
                
                # Check if we need to change color
                needs_color_change = True
                if previous_color is not None:
                    distance = self.calculate_color_distance(previous_color, hex_color)
                    if distance <= tolerance:
                        # Color is within tolerance, skip color change
                        needs_color_change = False
                        skipped_color_changes += 1
                
                if needs_color_change:
                    # Set the color for this pixel
                    self.log_status(f"Pixel {pixel_index + 1}/{total_pixels} - Color #{hex_color} (Luminance: {luminance:.1f})")
                    
                    # Click color picker button
                    self.reliable_click(coords['button_x'], coords['button_y'], speed)
                    time.sleep(delay)
                    
                    # Click hex input field
                    self.reliable_click(coords['hex_x'], coords['hex_y'], speed)
                    time.sleep(delay * 0.5)
                    
                    # Select all using AutoIt send (^a = Ctrl+A)
                    autoit.send("^a")
                    time.sleep(0.02)
                    
                    # Type hex code with AutoIt
                    for char in hex_color:
                        autoit.send(char)
                        time.sleep(random.uniform(0.015, 0.035))
                    
                    time.sleep(0.03)
                    
                    # Press Enter to confirm
                    autoit.send("{ENTER}")
                    time.sleep(delay * 0.5)
                    
                    # Click button again to close color picker
                    self.reliable_click(coords['button_x'], coords['button_y'], speed)
                    time.sleep(delay)
                    
                    color_changes += 1
                    previous_color = hex_color
                else:
                    self.log_status(f"Pixel {pixel_index + 1}/{total_pixels} - Using same color (within tolerance)")
                
                # Add small random offset for natural movement
                click_x = tile_x + random.uniform(-1, 1)
                click_y = tile_y + random.uniform(-1, 1)
                
                # Click to place pixel
                self.reliable_click(int(click_x), int(click_y), speed)
                time.sleep(delay * 0.3)
                painted_pixels += 1
                
                # Update progress
                progress = ((pixel_index + 1) / total_pixels) * 100
                self.root.after(0, lambda p=progress: self.progress.config(value=p))
            
            self.log_status(f"✅ Painting complete!")
            self.log_status(f"📊 Total pixels painted: {painted_pixels}")
            self.log_status(f"🎨 Color changes: {color_changes} | Skipped: {skipped_color_changes}")
            
        except Exception as e:
            self.log_status(f"❌ Error: {str(e)}")
        finally:
            self.finish_painting()
            
    def toggle_pause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_btn.config(text="▶ Resume")
            self.log_status("⏸ Paused - Press F1 or Resume to continue")
        else:
            self.pause_btn.config(text="⏸ Pause")
            self.log_status("▶ Resumed")
            
    def abort_painting(self):
        """Abort the painting process"""
        self.should_abort = True
        self.is_paused = False
        
    def finish_painting(self):
        """Reset UI after painting finishes"""
        self.is_painting = False
        self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.pause_btn.config(state=tk.DISABLED, text="⏸ Pause"))
        self.root.after(0, lambda: self.abort_btn.config(state=tk.DISABLED))

def main():
    root = tk.Tk()
    app = PixelPainterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
