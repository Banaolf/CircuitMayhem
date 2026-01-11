import os
import importlib.util
import json
import arcade
from enum import IntEnum
from pathlib import Path
TILE_SIZE = 16 # ALSO UPDATE IN GAME.PY IF CHANGED

# Constants derived from your setup
ROOT_DIR = Path(__file__).parent.parent
SPRITE_DIR = ROOT_DIR / "sprites"

class Sides(IntEnum):
    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3
# ==========================================================
# 1. THE COMPONENT CLASS (The physical object)
# ==========================================================
class component(arcade.Sprite):
    def __init__(self, display_name:str="PLACEHOLDER", img=(SPRITE_DIR / "default.png"), scale=1.0, position=(0, 0), rotation=0, connectivity=2, generator=False, max_energy=3, consume=3,
                 current_load=0, max_output=1, thermal_cost=0.1, is_pwrd=False, resistance=0, inputs=[0, 2], img_on=None, _tex_off=None, _tex_on=None,
                 outputs=[1, 3], energy_inbox=0, energy_outbox=0, integrity=100, temperature=20, cooling_rate=0.1, connected_inputs=None, connected_outputs=None, hazardous_temperature=90, script_module=None):
        
        """Creates a component object."""
        # Keep track of image paths for visual state changes
        self.img_path = img
        self.img_on_path = img_on if img_on is None or isinstance(img_on, (str, Path)) else None

        super().__init__(img, scale)
        self.center_x, self.center_y = position
        self.angle = rotation 
        self.dname = display_name
        self.script_module = script_module

        # --- Component Identity ---
        self.connectivity = connectivity 
        self.generator = generator       
        self.is_pwrd = is_pwrd           

        # --- Energy Storage ---
        self.max_energy = max_energy     
        self.energy_stored = 0.0         
        
        # --- Energy Flow ---
        self.consume_rate = consume      
        self.max_output = max_output     
        self.current_load = current_load 
        self.resistance = resistance     

        # --- Physics & Damage ---
        self.integrity = integrity       
        self.temperature = temperature   
        self.hazardous_temperature = hazardous_temperature 
        self.thermal_cost = thermal_cost 
        self.cooling_rate = cooling_rate 

        # --- The Logic Inbox/Outbox ---
        self.energy_inbox = energy_inbox
        self.energy_outbox = energy_outbox

        # --- Grid Connectivity ---
        self.base_inputs = inputs        
        self.base_outputs = outputs      
        self.connected_inputs = connected_inputs if connected_inputs is not None else []
        self.connected_outputs = connected_outputs if connected_outputs is not None else []
        
        self.RUX_TO_SEC = 1 / 3600
        self.grid_pos = (0, 0)

        # --- Textures for visual states (use registry-provided textures if available) ---
        if _tex_off is not None:
            self._tex_off = _tex_off
        else:
            try:
                self._tex_off = arcade.load_texture(self.img_path)
            except Exception:
                self._tex_off = None

        if _tex_on is not None:
            self._tex_on = _tex_on
        elif self.img_on_path:
            try:
                self._tex_on = arcade.load_texture(self.img_on_path)
            except Exception:
                self._tex_on = None
        else:
            self._tex_on = None

        # Ensure the correct visual is set on creation
        self.update_visual()

        # Trigger creation event
        self.trigger_event("on_create")

    def trigger_event(self, event_name, **kwargs):
        """Checks if the attached script has a function with event_name and calls it."""
        if self.script_module and hasattr(self.script_module, event_name):
            try:
                getattr(self.script_module, event_name)(self, **kwargs)
            except Exception as e:
                print(f"Script Error ({self.dname} - {event_name}): {e}")

    def update_visual(self):
        """Switch the sprite texture based on power state and available on-texture."""
        if getattr(self, '_tex_on', None) and getattr(self, 'is_pwrd', False):
            self.texture = self._tex_on
        elif getattr(self, '_tex_off', None):
            self.texture = self._tex_off
        # If textures failed to load for some reason, do nothing and let the sprite keep its current state

    def get_port_direction(self, side_index):
        return (side_index + (self.angle // 90)) % 4
    
    def update_physics(self, delta_time):
        self.trigger_event("on_tick", delta_time=delta_time)

        # 1. Heat Generation
        heat_produced = (self.current_load * self.resistance) + (self.current_load * self.thermal_cost)
        self.temperature += heat_produced * delta_time
        
        # 2. Natural Cooling
        if self.temperature > 20:
            self.temperature -= self.cooling_rate * delta_time
            self.temperature = max(20, self.temperature)

        # 3. Damage Logic
        if self.temperature >= self.hazardous_temperature:
            overheat_severity = self.temperature - self.hazardous_temperature
            damage = overheat_severity * 0.5 * delta_time
            self.integrity -= damage
            self.color = (255, 100, 100) if int(arcade.time.get_time() * 5) % 2 else (255, 255, 255)
        else:
            self.color = (255, 255, 255)

        if self.integrity <= 0:
            self.on_destroyed()

    def on_destroyed(self):
        print(f"Component {self.dname} at {self.grid_pos} has melted!")
        self.trigger_event("on_destroyed")
        self.kill() 
        
    def get_actual_input_sides(self):
        return [(side + int(self.angle // 90)) % 4 for side in self.base_inputs]

    def get_actual_output_sides(self):
        return [(side + int(self.angle // 90)) % 4 for side in self.base_outputs]

    def get_drain_per_tick(self, delta_time):
        return (self.consume_rate * self.RUX_TO_SEC) * delta_time
# ==========================================================
# 2. THE GRID MANAGER (The World Logic)
# ==========================================================
class GridManager:
    def __init__(self, tile_size=16):
        self.tile_size = tile_size
        self.world_grid = {} 

    def add_component(self, x, y, component):
        self.world_grid[(x, y)] = component
        component.grid_pos = (x, y)
        self.rebuild_connections(x, y)
        # Also rebuild neighbors so they see the new component
        self.update_neighbors(x, y)

    def update_neighbors(self, x, y):
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            self.rebuild_connections(x + dx, y + dy)

    def rebuild_connections(self, x, y):
        comp = self.world_grid.get((x, y))
        if not comp: return

        neighbors = [(0, 1, 0), (1, 0, 1), (0, -1, 2), (-1, 0, 3)]
        comp.connected_inputs.clear()
        comp.connected_outputs.clear()

        for dx, dy, side in neighbors:
            neighbor = self.world_grid.get((x + dx, y + dy))
            if neighbor:
                my_outputs = comp.get_actual_output_sides()
                my_inputs = comp.get_actual_input_sides()
                n_inputs = neighbor.get_actual_input_sides()
                n_outputs = neighbor.get_actual_output_sides()
                opposite_side = (side + 2) % 4

                if side in my_outputs and opposite_side in n_inputs:
                    comp.connected_outputs.append(neighbor)
                if side in my_inputs and opposite_side in n_outputs:
                    comp.connected_inputs.append(neighbor)
# ==========================================================
# 3. THE COMPONENT REGISTRY (The Pre-Caching Factory)
# ==========================================================
class ComponentRegistry:
    def __init__(self, objs_dir, sprite_dir):
        self.objs_dir = objs_dir
        self.sprite_dir = sprite_dir
        self.blueprints = {} # Pre-cache RAM storage

    def load_all_from_objs(self):
        """Scans folder and loads JSON/JSONC blueprints into RAM."""
        for filename in os.listdir(self.objs_dir):
            if filename.endswith(".json") or filename.endswith(".jsonc"):
                path = os.path.join(self.objs_dir, filename)
                try:
                    with open(path, 'r') as f:
                        # READ ALL LINES AND STRIP COMMENTS
                        content = ""
                        for line in f:
                            # Remove whitespace and check if it starts with //
                            if line.strip().startswith("//"):
                                continue
                            # Remove inline comments (simple version)
                            content += line.split("//")[0]
                        
                        # Now load the cleaned string
                        data = json.loads(content)

                        # --- SCRIPT LOADING ---
                        if "script" in data:
                            script_path = self.objs_dir / data["script"]
                            if script_path.exists():
                                try:
                                    spec = importlib.util.spec_from_file_location(data["script"], str(script_path))
                                    mod = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(mod)
                                    data["script_module"] = mod
                                except Exception as e:
                                    print(f"Failed to load script {data['script']}: {e}")

                        self.blueprints.update(data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

        # Preload textures for each blueprint to avoid per-component texture loading
        for comp_id, data in self.blueprints.items():
            try:
                data['_tex_off'] = arcade.load_texture(self.sprite_dir / data['img'])
            except Exception as e:
                data['_tex_off'] = arcade.load_texture(self.sprite_dir / "default.png")
                print(f"Failed to load texture for {comp_id}: {e}")

            if data.get('img_on'):
                try:
                    data['_tex_on'] = arcade.load_texture(self.sprite_dir / data['img_on'])
                except Exception as e:
                    data['_tex_on'] = None
                    print(f"Failed to load on-texture for {comp_id}: {e}")
            else:
                data['_tex_on'] = None

        print(f"Registry: {len(self.blueprints)} blueprints pre-cached.")
        print(self.blueprints)

    def create_component(self, comp_id, grid_pos):
        data = self.blueprints.get(comp_id)
        if not data: return None

        screen_pos = (grid_pos[0] * TILE_SIZE + (TILE_SIZE / 2), grid_pos[1] * TILE_SIZE + (TILE_SIZE / 2))

        return component(
            display_name=data.get('display_name', comp_id.title()),
            img=(self.sprite_dir / data['img']),
            scale=data.get('scale', 1.0),
            position=screen_pos,
            connectivity=data.get('connectivity', 10),
            generator=data.get('generator', False),
            max_energy=data.get('max_energy', 0),
            consume=data.get('consume', 0),
            max_output=data.get('max_output', 1),
            thermal_cost=data.get('thermal_cost', 0.1),
            hazardous_temperature=data.get('hazardous_temperature', 90),
            cooling_rate=data.get('cooling_rate', 0.1),
            integrity=data.get('integrity', 100),
            inputs=data.get('inputs', [0, 2]),
            outputs=data.get('outputs', [1, 3]),
            img_on=(self.sprite_dir / data['img_on']) if data.get('img_on') else None,
            _tex_off=data.get('_tex_off'),
            _tex_on=data.get('_tex_on'),
            script_module=data.get('script_module')
        )