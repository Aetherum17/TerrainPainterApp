# This code is licensed under the Creative Commons Attribution-NonCommercial 4.0 International Public License.
# See the full license text at https://creativecommons.org/licenses/by-nc/4.0/
# Created by @Aetherum with love for EU4 modding community (2024).

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import atexit

CONFIG_FILE = "provter_config.json"

class ScrollableImage(tk.Frame):
    def __init__(self, master, image_path):
        super().__init__(master)

        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar_y = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.scrollbar_x = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        self.image = Image.open(image_path)
        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
        hbar = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        
        hbar.grid(row=1, column=0, sticky="ew")
        vbar.grid(row=0, column=1, sticky="ns")
        
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

class ProvinceTerrainApp:
    def __init__(self, master):
        self.master = master
        self.master.title("TerrainPainterApp")

        # Create a frame for the top controls
        self.top_frame = tk.Frame(master)
        self.top_frame.grid(row=0, column=0, sticky="ew")
    
        # Configure grid
        self.top_frame.columnconfigure(1, weight=1)  # This makes the middle column expandable
        self.master.columnconfigure(0, weight=1)
    
        # Left side controls
        self.dir_button = tk.Button(self.top_frame, text="Select Root Folder", command=self.select_working_directory)
        self.dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    
        self.directory_label = tk.Label(self.top_frame, text="Mod's Root Folder: Not selected")
        self.directory_label.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        
        self.config = self.load_config()
    
        # Right side control
        self.help_button = tk.Button(self.top_frame, text="Help", command=self.show_help)
        self.help_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")
    
        # Create an empty frame for the main content
        self.main_frame = tk.Frame(master)
        self.main_frame.grid(row=1, column=0, sticky="nsew")
        
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        
        # If config was loaded successfully, initialize components
        if self.config:
            self.initialize_components(self.config['image_path'], self.config['def_file_path'], self.config['terrain_file_path'])
        
        # On Exit
        atexit.register(self.cleanup)
        
    def initialize_components(self, image_path, def_file_path, terrain_file_path):
        # Clear the main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
        # Load definitions.csv
        self.color_to_province = self.load_color_definitions(def_file_path)
        self.color_to_terrain = self.load_terrain_definitions(terrain_file_path)
        # Load terrain.txt
        self.color_to_terrain_color = self.load_terrain_definitions_colors(terrain_file_path)
        # Create a dictionary: province colour - terrain colour
        self.terrain_colour_map = self.get_terrain_color_map(self.color_to_province, self.color_to_terrain, self.color_to_terrain_color)
        
        self.province_list = []  # Initialize the list to store province IDs
        self.selected_terrain_type = False
        self.current_province_type = ""
        
        #print(self.color_to_province)
        #print(self.color_to_terrain)
        #print(self.color_to_terrain_color)
        
        # Load the original image for interactions
        self.province_image = Image.open(image_path)
        
        # Apply terrain colors to the image
        self.terrain_image = self.apply_terrain_colors(image_path)
        
        self.border_image = self.add_borders_to_image(image_path)
        # Overlay border image on terrain image
        self.terrain_image = Image.alpha_composite(self.terrain_image.convert('RGBA'), self.border_image)
        self.terrain_image.save("temp_terrain_image.png")
        
        # Create a ScrollableImage with the terrain image
        self.scrollable_image = ScrollableImage(self.main_frame, "temp_terrain_image.png")
        self.scrollable_image.grid(row=0, column=0, sticky="nsew")
        
        self.canvas = self.scrollable_image.canvas
        
        # Create PhotoImage for terrain images
        self.terrain_photo = ImageTk.PhotoImage(self.terrain_image)
        
        # Display the terrain image on the canvas
        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.terrain_photo)
        
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-2>", self.on_middle_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_hover)
        self.info_label = tk.Label(self.main_frame, text="")
        self.info_label.grid(row=1, column=0, sticky="ew")
        
        # Get terrain types from color_to_terrain dictionary keys
        terrain_types = list(self.color_to_terrain.keys())
        
        # Create the combobox (dropdown)
        self.terrain_combobox = ttk.Combobox(self.top_frame, state="readonly")
        self.terrain_combobox.grid(row=1, column=0, padx=5, pady=5)
        # Populate the combobox with unique terrain types
        self.update_terrain_dropdown(terrain_types)
        # Bind the combobox selection event
        self.terrain_combobox.bind("<<ComboboxSelected>>", self.on_terrain_selected)
        
    def select_working_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_label.config(text=f"Working Directory: {directory}")
            
            # Construct file paths, ensuring we navigate to the 'map' subdirectory
            map_directory = os.path.join(directory, "map").replace("\\","/")
            self.image_path = os.path.join(map_directory, "provinces.bmp").replace("\\","/")
            self.def_file_path = os.path.join(map_directory, "definition.csv").replace("\\","/")
            self.terrain_file_path = os.path.join(map_directory, "terrain.txt").replace("\\","/")
            
            # Check if the files exist
            if not os.path.exists(self.image_path):
                messagebox.showerror("Error", f"File not found: {self.image_path}")
                return
            if not os.path.exists(self.def_file_path):
                messagebox.showerror("Error", f"File not found: {self.def_file_path}")
                return
            if not os.path.exists(self.terrain_file_path):
                messagebox.showerror("Error", f"File not found: {self.terrain_file_path}")
                return
            
            # Save the config
            config = {
                'image_path': self.image_path,
                'def_file_path': self.def_file_path,
                'terrain_file_path': self.terrain_file_path
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            
            # Initialize main components
            self.initialize_components(self.image_path, self.def_file_path, self.terrain_file_path)
            
    def show_help(self):
        help_window = tk.Toplevel(self.master)
        help_window.title("Help")
        help_window.geometry("400x300")  # You can adjust the size as needed
    
        help_text = tk.Text(help_window, wrap=tk.WORD)
        help_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    
        # Insert your help text here
        help_text.insert(tk.END, """
        How to use the TerrainPainterApp:

        1. Select a root folder of the mod using the 'Select Root Folder' button.
            - Root folder is the folder of the mod containing descriptor.mod and such folders like common or map.
            - If there are no issues during loading of map, the used path will be saved for future launches.
            - If you would like to use the TerrainPainterApp for naother mod, just selects its root folder after the launch.
            
        2. Controls: Left Mouse Button, Righ Mouse Button, Middle Mouse Button
            - Left Mouse Button: Deselects every province and terrain selected.
            - Right Mouse Button: 
                1) Adds a province to the Selection.
                2) Multiple provinces can be added to the Selection by continuing clicking on them with the Right Mouse button. If no terrain is selected, the first known province terrain becomes selected.
                3) The type of the selected terrain can be changed using the drop list in top left corner of the app.
                4) Already selected provinces can be removed from the Selection by clicking on them again with the Right Mouse button.
            - Middle Mouse Button:
                1) Applies the selected terrain to all provinces in the Selection. Updates terrain.txt and reloads the map of the TerrainPainterApp.
                
        3. Known limitations of TerrainPainterApp
            - TerrainPainterApp might produce corrupted terrain.txt or not load at all if there are issues with the terrain.txt. 
            - You can use https://codeberg.org/Aetherial-Mods/Audax-Validator-EU4 to check the mod for errors before using the TerrainPainterApp.
            
        4. Report an issue: https://github.com/Aetherum17/TerrainPainterApp
        
        5. Contact support: https://discord.gg/hTKzmak (Ping @Aetherum)
        """)
    
        help_text.config(state=tk.DISABLED)  # Make the text read-only
    
        close_button = tk.Button(help_window, text="Close", command=help_window.destroy)
        close_button.pack(pady=10)
    
    def apply_terrain_colors(self, image_path):
        # Open the image
        original_image = Image.open(image_path)
        img_array = np.array(original_image)
    
        # Create color map arrays
        old_colors = np.array(list(self.terrain_colour_map.keys()), dtype=np.uint8)
        new_colors = np.array(list(self.terrain_colour_map.values()), dtype=np.uint8)
    
        # Create a lookup table
        lut = np.zeros((256, 256, 256, 3), dtype=np.uint8)
        lut[old_colors[:, 0], old_colors[:, 1], old_colors[:, 2]] = new_colors
    
        # Apply the color mapping
        new_img_array = lut[img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]]
    
        # Convert back to PIL Image
        return Image.fromarray(new_img_array)
    
    def add_borders_to_image(self, image_path):
        # Open the image and convert to numpy array
        original_image = Image.open(image_path)
        original_image = original_image.convert('RGBA')
        img_array = np.array(original_image)
    
        # Create shifts in all four directions
        shifts = [
            np.roll(img_array, 1, axis=0),  # down
            np.roll(img_array, -1, axis=0),  # up
            np.roll(img_array, 1, axis=1),  # right
            np.roll(img_array, -1, axis=1)  # left
        ]
    
        # Calculate the differences
        differences = [np.any(shift != img_array, axis=-1) for shift in shifts]
    
        # Combine all differences
        border_mask = np.logical_or.reduce(differences)
    
        # Create the border image
        border_image = np.zeros_like(img_array)
        border_image[border_mask] = [0, 0, 0, 255]  # Black color with full opacity
    
        # Make all non-black pixels transparent
        transparent_mask = np.logical_not(np.all(border_image[:, :, :3] == [0, 0, 0], axis=-1))
        border_image[transparent_mask] = [0, 0, 0, 0]  # Fully transparent
    
        # Convert back to PIL Image
        result = Image.fromarray(border_image.astype(np.uint8))
    
        return result
    
    def load_color_definitions(self, file_path):
        color_to_province = {}
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(';')
                if len(parts) >= 4 and parts[0].isdigit():
                    province_id = int(parts[0])
                    r, g, b = map(int, parts[1:4])
                    color_to_province[(r, g, b)] = province_id
        return color_to_province
    
    def load_terrain_definitions(self, terrain_file_path):
        terrain_to_province = {}
        province_list = []
        with open(terrain_file_path, 'r') as terrain_file:
            terrain_line = terrain_file.read().split()
            depth = 0
            current_terrain = ""
            set_current_terrain = False
            entered_categories = False
            entered_terrain_override = False
            for i, word in enumerate(terrain_line):
                if(word == "{"):
                    depth = depth + 1  
                if(word == "}"):
                    depth = depth - 1
                    if(entered_terrain_override == True):
                        entered_terrain_override = False
                        province_list = list(filter(lambda word: '{' not in word, province_list))
                        terrain_to_province[current_terrain] = province_list
                        province_list = []
                if(depth == 1):
                    entered_categories = True
                    current_terrain = ""
                    set_current_terrain = False
                if(depth == 2 and set_current_terrain == False):
                    current_terrain = terrain_line[i-2]
                    set_current_terrain = True
                if(depth == 3 and terrain_line[i-2] == "terrain_override"):
                    entered_terrain_override = True
                if(entered_terrain_override == True):
                    province_list.append(terrain_line[i]) 
                if(depth == 0 and entered_categories == True):
                    break # log only categories entry
        return(terrain_to_province)
    
    def load_terrain_definitions_colors(self, terrain_file_path):
        terrain_color_to_province = {}
        province_list = []
        with open(terrain_file_path, 'r') as terrain_file:
            terrain_line = terrain_file.read().split()
            depth = 0
            set_current_terrain = False
            entered_categories = False
            entered_terrain_override = False
            for i, word in enumerate(terrain_line):
                if(word == "{"):
                    depth = depth + 1  
                if(word == "}"):
                    depth = depth - 1
                    if(entered_terrain_override == True):
                        entered_terrain_override = False
                        #province_list = list(filter(lambda word: '{' not in word, province_list))
                        province_list = list(filter(lambda x: x.strip().isdigit(), province_list))
                        province_list = []
                if(depth == 1):
                    entered_categories = True
                    current_terrain = ""
                    set_current_terrain = False
                if(depth == 2 and set_current_terrain == False):
                    current_terrain = terrain_line[i-2]
                    set_current_terrain = True
                if(depth == 3 and terrain_line[i-2] == "terrain_override"):
                    entered_terrain_override = True
                if(entered_terrain_override == True):
                    province_list.append(terrain_line[i]) 
                if(depth == 3 and terrain_line[i-2] == "color"):
                    terrain_color_to_province[current_terrain] = (int(terrain_line[i+1]), int(terrain_line[i+2]), int(terrain_line[i+3]))
                if(depth == 0 and entered_categories == True):
                    break # log only categories entry
        return(terrain_color_to_province)
    
    def get_terrain_color_map(self, color_to_province, terrain_id_to_name, color_to_terrain_color):
        color_to_terrain_color_map = {}
        
        for color, province_id in color_to_province.items():
            terrain_name = self.get_terrain_by_province(terrain_id_to_name, province_id)
            if terrain_name:
                terrain_color = color_to_terrain_color.get(terrain_name)
                if terrain_color:
                    color_to_terrain_color_map[color] = terrain_color
                else:
                    color_to_terrain_color_map[color] = (150,150,150)
                
        return(color_to_terrain_color_map)    
    
    def get_terrain_by_province(self, terrain_dict, province_id):
        for terrain, provinces in terrain_dict.items():
            if str(province_id) in provinces:
                return terrain
        return "Unknown"  # Return "Unknown" if the province_id is not found
    
    def on_hover(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        rgb_image = self.province_image.convert('RGB')
        r, g, b = rgb_image.getpixel((x, y))
        
        province_id = self.color_to_province.get((r, g, b), "Unknown")
        terrain_type = self.get_terrain_by_province(self.color_to_terrain, province_id)
        
        self.info_label.config(text=f"Province ID: {province_id}, Terrain Type: {terrain_type}\nSelected Terrain: {self.current_province_type}\nSelected Provinces: {self.province_list}")
    
    def on_left_click(self, event):
        # Convert canvas coordinates to image coordinates
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Get the color of the clicked pixel
        rgb_image = self.province_image.convert('RGB')
        r, g, b = rgb_image.getpixel((x, y))
        
        # Find the corresponding province ID
        province_id = self.color_to_province.get((r, g, b), "Unknown")
        terrain_type = self.get_terrain_by_province(self.color_to_terrain, province_id)
        
        #print(f"Province ID: {province_id}")
        #print(f"Terrain Type: {terrain_type}")
        
        self.province_list = []
        self.selected_terrain_type = False
        self.current_province_type = ""
        
        self.info_label.config(text=f"Province ID: {province_id}, Terrain Type: {terrain_type}\nSelected Terrain: {self.current_province_type}\nSelected Provinces: {self.province_list}")
        
    def on_right_click(self, event):
        # Convert canvas coordinates to image coordinates
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Get the color of the clicked pixel
        rgb_image = self.province_image.convert('RGB')
        r, g, b = rgb_image.getpixel((x, y))
        
        # Find the corresponding province ID
        province_id = self.color_to_province.get((r, g, b), "Unknown")
        terrain_type = self.get_terrain_by_province(self.color_to_terrain, province_id)
        
        # Log first selected terrain type
        if(self.selected_terrain_type == False):
            self.selected_terrain_type = True
            self.current_province_type = terrain_type
        
        print(f"Selected terrain: {self.current_province_type}")
        
        # Add the province ID to the list
        if province_id != "Unknown":
            if province_id not in self.province_list:
                self.province_list.append(province_id)
                print(f"Province ID {province_id} added to the list.")
            else:
                self.province_list.remove(province_id)
                print(f"Province ID {province_id} removed from the list.")
        else:
            print("Clicked on a province of the unknown terrain type.")
        
        # For debugging purposes, print the current list of province IDs
        # print("Current province list:", self.province_list)
        
        self.info_label.config(text=f"Province ID: {province_id}, Terrain Type: {terrain_type}\nSelected Terrain: {self.current_province_type}\nSelected Provinces: {self.province_list}")
        
    def update_terrain_dropdown(self, terrain_types):
        
        # Update the combobox values
        self.terrain_combobox['values'] = terrain_types

    def open_terrain_dropdown(self):
        # This method is called when the button is clicked
        # It doesn't need to do anything special, as the combobox is already created
        pass

    def on_terrain_selected(self, event):
        selected_terrain = self.terrain_combobox.get()
        
        self.current_province_type = selected_terrain
        print(f"Selected terrain: {self.current_province_type}")
        
    def on_middle_click(self, event):
        current_province_type = self.current_province_type
        province_list = self.province_list
        color_to_terrain = self.color_to_terrain
        
        # Remove all elements of self.province_list from ALL values in self.color_to_terrain
        for key in color_to_terrain:
            color_to_terrain[key] = [province for province in color_to_terrain[key] if int(province) not in province_list]
        
        # Ensure all elements in province_list are strings
        province_list = [str(province) for province in province_list]
        
        # Append all elements of self.province_list to values of self.current_province_type key
        if current_province_type in color_to_terrain:
            color_to_terrain[current_province_type].extend(province_list)
        else:
            color_to_terrain[self.current_province_type] = province_list
        
        self.color_to_terrain = color_to_terrain
        # Update dictionary
        self.terrain_colour_map = self.get_terrain_color_map(self.color_to_province, self.color_to_terrain, self.color_to_terrain_color)
        
        # Apply terrain colors to the image
        self.terrain_image = self.apply_terrain_colors(self.image_path)
    
        # Overlay border image on terrain image
        self.terrain_image = Image.alpha_composite(self.terrain_image.convert('RGBA'), self.border_image)
        self.terrain_image.save("temp_terrain_image.png")
    
        # Create PhotoImage for terrain images
        self.terrain_photo = ImageTk.PhotoImage(self.terrain_image)
    
        # Update the canvas with the new image
        self.canvas.itemconfig(self.canvas_image, image=self.terrain_photo)
        
        # Update terrain.txt ######################################################################
        
        with open(self.terrain_file_path, 'r') as terrain_file:
            file_content = terrain_file.read().splitlines(keepends=True)
            
        with open(self.terrain_file_path, 'r') as terrain_file:
            pass
            
        with open(self.terrain_file_path, 'w') as write_terrain_file:
            depth = 0
            terrain_type = ""
            i = 0
            values = []
            while i < len(file_content):
                if("terrain_override" in file_content[i]):
                    while("}" not in file_content[i]):
                        i = i+1
                    write_terrain_file.write("\t\tterrain_override = {\n")
                    write_terrain_file.write("\t\t\t"+' '.join(map(str, values))+"\n")
                    write_terrain_file.write("\t\t}\n")
                    i = i+1
                write_terrain_file.write(file_content[i])
                if("{" in file_content[i]):
                    depth = depth+file_content[i].count('{')
                if("}" in file_content[i]):
                    depth = depth-file_content[i].count('}')
                #print(file_content[i], " ", depth)
                if(depth == 1):
                    terrain_type = ""
                if(depth == 2 and terrain_type == ""):
                    terrain_type = file_content[i].split("=")[0].strip()
                    #print(terrain_type)
                    values = self.color_to_terrain.get(terrain_type, [])
                    #print(values)
                i = i+1
                
    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Verify that all required paths exist
            if all(os.path.exists(config[key]) for key in ['image_path', 'def_file_path', 'terrain_file_path']):
                self.image_path = config['image_path']
                self.def_file_path = config['def_file_path']
                self.terrain_file_path = config['terrain_file_path']
                self.directory_label.config(text=f"Working Directory: {os.path.dirname(os.path.dirname(config['image_path'].rstrip('/')))}")
                return config
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return None
                
    def cleanup(self):
        try:
            os.remove("temp_terrain_image.png")
            print("Temporary image file deleted.")
        except FileNotFoundError:
            print("Temporary image file not found.")
        except Exception as e:
            print(f"Error deleting temporary image file: {e}")
        
root = tk.Tk()
root.rowconfigure(1, weight=1)
root.columnconfigure(0, weight=1)
app = ProvinceTerrainApp(root)
root.mainloop()