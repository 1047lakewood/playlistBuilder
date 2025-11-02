class KeyboardBindings:
    
    bindings  = {
        "open": (["<Control-o>", "<Control-O>"], "Ctrl+O"),
        "save": (["<Control-s>"], "Ctrl+S"),
        "save_as": (["<Control-Shift-s>"], "Ctrl+Shift+S"),
        "test": (["<Control-t>"], "Ctrl+T"),
        "test2": (["<Control-u>"], "Ctrl+U"),
        "copy": (["<Control-c>", "<Control-C>"], "Ctrl+C"),
        "paste": (["<Control-v>", "<Control-V>"], "Ctrl+V"),
        "cut": (["<Control-x>", "<Control-X>"], "Ctrl+X"),
        "delete": (["<Delete>"], "Delete"),
        "search": (["<Control-f>", "<Control-F>"], "Ctrl+F"),
        # "toggle_api_playlist": (["<Control-a>"], "Ctrl+A"),
    }
    
    def __init__(self, root):
        self.root = root


    def bind(self, actions: dict):

        for name, action in actions.items():
            if name not in self.bindings:
                continue
            for i in self.bindings[name][0]:
                self.root.bind(i, action)
        
    
    def get_display_name(self, action_name: str):
        if action_name not in self.bindings:
            return ""
        return self.bindings[action_name][1]