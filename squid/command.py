class SquidCommand(object):
    def __init__(self, name, aliases, description, options):
        self.name = name
        self.aliases = aliases
        self.description = description
        self.options = options
    
    def __repr__(self):
        return f"<SquidCommand name={self.name} aliases={self.aliases} description={self.description} options={self.options}>" 
        