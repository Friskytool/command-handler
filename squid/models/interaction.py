from .enums import InteractionType, ApplicationCommandType, ApplicationCommandOptionType
from .member import Member, User

__all__ = ("Interaction", "ApplicationCommand", "ApplicationCommandOption")


class Interaction(object):

    CONSTRUCTORS = {
        InteractionType.PING: "default_constructor",
        InteractionType.APPLICATION_COMMAND: "application_command_constructor",
        InteractionType.MESSAGE_COMPONENT: "message_component_constructor",
        InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE: "application_command_autocomplete_constructor",
    }

    def __init__(
        self,
        *,
        id,
        application_id,
        type,
        data,
        guild_id,
        channel_id,
        member,
        user,
        token,
        version,
        message,
    ):
        self.id = id
        self.application_id = application_id
        self.type = type
        self.data = data
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.member = member
        self.user = user
        self.token = token
        self.version = version
        self.message = message

    def __repr__(self):
        return f"<Interaction id={self.id} application_id={self.application_id} type={self.type} data={self.data} guild_id={self.guild_id} channel_id={self.channel_id} member={self.member} user={self.user} token={self.token} version={self.version} message={self.message}>"

    @classmethod
    def from_json(cls, data):
        typ = InteractionType(data["type"])

        return getattr(
            cls,
            cls.CONSTRUCTORS.get(typ, "default_constructor"),
        )(data)

    @staticmethod
    def _default_constructor(data):
        return dict(
            id=data["id"],
            application_id=data["application_id"],
            type=InteractionType(data["type"]),
            data=data.get("data", {}),
            guild_id=data.get("guild_id", 0),
            channel_id=data.get("channel_id", 0),
            member=(Member.from_json(data["member"]) if data.get("member") else None),
            user=(User.from_json(data["user"]) if data.get("user") else None),
            token=data["token"],
            version=data["version"],
            message=data.get("message"),
        )

    @classmethod
    def default_constructor(cls, data):
        return cls(**cls._default_constructor(data))

    @classmethod
    def application_command_constructor(cls, data):
        default = cls._default_constructor(data)
        default.pop("data")
        return cls(data=ApplicationCommand.from_json(data["data"]), **default)


class ApplicationCommand(object):
    def __init__(self, *, id, name, type, resolved=None, options=[]):
        self.id = id
        self.name = name
        self.type = ApplicationCommandType(type)
        self.resolved = resolved
        self.options = [
            ApplicationCommandOption.from_json(option) for option in options
        ]

    def __repr__(self):
        return f"<ApplicationCommand id={self.id} name={self.name} type={self.type} resolved={self.resolved} options={self.options}>"

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class ApplicationCommandOption(object):
    def __init__(self, *, name, type, value, options, focused):
        self.name = name
        self.type = type
        self.value = value
        self.options = options
        self.focused = focused

    def __repr__(self):
        return f"<ApplicationCommandOption name={self.name} type={self.type} value={self.value} options={self.options} focused={self.focused}>"

    @classmethod
    def from_json(cls, data):
        return cls(
            name=data["name"],
            type=ApplicationCommandOptionType(data["type"]),
            value=data.get("value"),
            options=map(cls.from_json, data.get("options", [])),
            focused=data.get("focused", False),
        )


class ApplicationCommandOptionChoice(object):
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"<ApplicationCommandOptionChoice name={self.name} value={self.value}>"

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)
