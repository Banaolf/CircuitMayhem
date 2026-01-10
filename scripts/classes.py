import arcade

from CircuitMayhem.scripts.baseclasses import SPRITE_DIR
from CircuitMayhem.scripts.game import SCREEN_HEIGHT


class SidebarIcon(arcade.Sprite):
    def __init__(self, comp_id, texture, x, y):
        super().__init__(texture, scale=0.5)
        self.comp_id = comp_id # e.g. "battery_small"
        self.center_x = x
        self.center_y = y

class Sidebar:
    def __init__(self, registry):
        self.icons = arcade.SpriteList()
        self.width = 200
        self.active_selection = None
        
        # Populate sidebar from registry
        for i, comp_id in enumerate(registry.definitions.keys()):
            tex = SPRITE_DIR / registry.definitions[comp_id]['texture']
            icon = SidebarIcon(comp_id, tex, 100, SCREEN_HEIGHT - 50 - (i * 80))
            self.icons.append(icon)

    def draw(self):
        # Draw background panel
        arcade.draw_lrtb_rectangle_filled(0, self.width, SCREEN_HEIGHT, 0, arcade.color.DARK_SLATE_GRAY)
        self.icons.draw()