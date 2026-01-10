import arcade
import os
import json
from pathlib import Path

# Import your custom logic
from baseclasses import GridManager, ComponentRegistry, SPRITE_DIR

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = arcade.get_display_size()
TILE_SIZE = 16 # ALSO UPDATE IN BASECLASSES.PY IF CHANGED
SIDEBAR_WIDTH = 200

appdata = Path(os.getenv("LOCALAPPDATA"))

ROOT_FOLDER = appdata / "CircuitMayhem"

class Sidebar:
    def __init__(self, registry):
        self.width = SIDEBAR_WIDTH
        self.icons = arcade.SpriteList()
        self.registry = registry
        
        # Pre-calculate labels for display names
        self.labels = []
        
        for i, (comp_id, data) in enumerate(registry.blueprints.items()):
            # Create icon
            icon = arcade.Sprite(SPRITE_DIR / data['img'], scale=1.0)
            icon.center_x = self.width // 2
            icon.center_y = SCREEN_HEIGHT - 60 - (i * 100)
            icon.comp_id = comp_id  # Link the icon to the registry ID
            self.icons.append(icon)
            
            # Create text label
            label = arcade.Text(
                data.get('display_name', comp_id),
                icon.center_x,
                icon.center_y - 45,
                arcade.color.WHITE,
                10,
                anchor_x="center"
            )
            self.labels.append(label)

    def draw(self):
        # Sidebar background
        arcade.draw_lrbt_rectangle_filled(0, self.width, 0, SCREEN_HEIGHT, (40, 44, 52, 255))
        arcade.draw_line(self.width, 0, self.width, SCREEN_HEIGHT, arcade.color.BLACK, 2)
        
        self.icons.draw()
        for label in self.labels:
            label.draw()

class CircuitMayhem(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Circuit Mayhem", fullscreen=True)
        arcade.set_background_color(arcade.color.AIR_SUPERIORITY_BLUE)
        
        # Path setup
        self.objs_path = ROOT_FOLDER / "objs"
        
        # Core Systems
        self.grid_manager = GridManager(tile_size=TILE_SIZE)
        self.registry = ComponentRegistry(self.objs_path, SPRITE_DIR)
        
        # Rendering
        self.component_list = arcade.SpriteList()
        self.sidebar = None
        
        # Interaction
        self.selected_comp_id = None
        self.ghost_sprite = None
        self.mouse_pos = (0, 0)

    def setup(self):
        """ Initialize the board and registry """
        self.registry.load_all_from_objs()
        self.sidebar = Sidebar(self.registry)

    def add_to_grid(self, x, y, component):
        """Helper to keep sprite list and logic grid in sync"""
        component.center_x += self.sidebar.width
        self.grid_manager.add_component(x, y, component)
        self.component_list.append(component)

    def on_draw(self):
        self.clear()
        
        # 1. Draw Background Grid
        for x in range(self.sidebar.width, SCREEN_WIDTH + TILE_SIZE, TILE_SIZE):
            arcade.draw_line(x, 0, x, SCREEN_HEIGHT, (255, 255, 255, 30), 1)
        for y in range(0, SCREEN_HEIGHT, TILE_SIZE):
            arcade.draw_line(self.sidebar.width, y, SCREEN_WIDTH, y, (255, 255, 255, 30), 1)
            
        # 2. Draw Components in world
        self.component_list.draw()
        
        # 3. Draw Ghost (Preview) - FIXED DRAW METHOD
        if self.ghost_sprite:
            arcade.draw_sprite(self.ghost_sprite)
            
        # 4. Draw UI
        if self.sidebar:
            self.sidebar.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_pos = (x, y)
        
        if self.selected_comp_id and self.ghost_sprite:
            # Snap the ghost to the grid (Accounting for sidebar offset)
            grid_x = (x - self.sidebar.width) // TILE_SIZE
            grid_y = y // TILE_SIZE
            
            self.ghost_sprite.center_x = (grid_x * TILE_SIZE) + (TILE_SIZE // 2) + self.sidebar.width
            self.ghost_sprite.center_y = (grid_y * TILE_SIZE) + (TILE_SIZE // 2)
            self.ghost_sprite.alpha = 150 

    def on_mouse_press(self, x, y, button, modifiers):
        # Right Click to Deselect
        if button == arcade.MOUSE_BUTTON_RIGHT:
            self.selected_comp_id = None
            self.ghost_sprite = None
            return

        # 1. Sidebar Interaction
        if x < self.sidebar.width:
            hits = arcade.get_sprites_at_point((x, y), self.sidebar.icons)
            if hits:
                self.selected_comp_id = hits[0].comp_id
                data = self.registry.blueprints[self.selected_comp_id]
                # Re-create the ghost sprite from the registry image
                self.ghost_sprite = arcade.Sprite(SPRITE_DIR / data['img'], scale=data.get('scale', 1.0))
            return

        # 2. Grid Interaction (Place item)
        if self.selected_comp_id:
            grid_x = (x - self.sidebar.width) // TILE_SIZE
            grid_y = y // TILE_SIZE
            
            if (grid_x, grid_y) not in self.grid_manager.world_grid:
                new_comp = self.registry.create_component(self.selected_comp_id, (grid_x, grid_y))
                if new_comp:
                    self.add_to_grid(grid_x, grid_y, new_comp)

    def on_update(self, delta_time):
        # 1. Generation & Consumption
        for comp in self.grid_manager.world_grid.values():
            if comp.generator:
                comp.energy_outbox += comp.max_output * delta_time
            
            drain = comp.get_drain_per_tick(delta_time)
            comp.energy_stored -= drain
            comp.energy_stored = max(0, min(comp.energy_stored, comp.max_energy))

        # 2. Transfer
        for comp in self.grid_manager.world_grid.values():
            if comp.energy_outbox > 0 and comp.connected_outputs:
                share = comp.energy_outbox / len(comp.connected_outputs)
                for target in comp.connected_outputs:
                    target.energy_inbox += share
                comp.energy_outbox = 0

        # 3. Resolution
        for comp in self.grid_manager.world_grid.values():
            comp.energy_stored += comp.energy_inbox
            comp.current_load = comp.energy_inbox 
            comp.energy_inbox = 0
            comp.update_physics(delta_time)
            comp.is_pwrd = comp.energy_stored > 0

def main():
    game = CircuitMayhem()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()