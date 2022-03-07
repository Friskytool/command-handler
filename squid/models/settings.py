class Setting(object):
    def __init__(self, name, typ, default, description):
        self.name = name
        self.typ = typ
        self.default = default
        self.description = description

    @classmethod
    def from_data(cls, data: dict):
        typ = data.pop("type", None)
        return cls(typ=typ, **data)
