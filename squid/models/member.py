class User(object):
    def __init__(
        self,
        *,
        id,
        username,
        discriminator,
        avatar,
        bot,
        system,
        mfa_enabled,
        banner,
        accent_color,
        locale,
        verified,
        email,
        flags,
        premium_type,
        public_flags,
        premium_since,
        created_at,
    ):
        self.id = id
        self.username = username
        self.discriminator = discriminator
        self.avatar = avatar
        self.bot = bot
        self.system = system
        self.mfa_enabled = mfa_enabled
        self.banner = banner
        self.accent_color = accent_color
        self.locale = locale
        self.verified = verified
        self.email = email
        self.flags = flags
        self.premium_type = premium_type
        self.public_flags = public_flags
        self.premium_since = premium_since
        self.created_at = created_at

    def __repr__(self):
        return f"<User id={self.id} username={self.username} discriminator={self.discriminator} avatar={self.avatar} bot={self.bot} system={self.system} mfa_enabled={self.mfa_enabled} banner={self.banner} accent_color={self.accent_color} locale={self.locale} verified={self.verified} email={self.email} flags={self.flags} premium_type={self.premium_type} public_flags={self.public_flags} premium_since={self.premium_since} created_at={self.created_at}>"

    @classmethod
    def from_json(cls, data):
        return cls(
            id=data["id"],
            username=data["username"],
            discriminator=data["discriminator"],
            avatar=data["avatar"],
            bot=data.get("bot", False),
            system=data.get("system", False),
            mfa_enabled=data.get("mfa_enabled", False),
            banner=data.get("banner", None),
            accent_color=data.get("accent_color", None),
            locale=data.get("locale", None),
            verified=data.get("verified", False),
            email=data.get("email", None),
            flags=data.get("flags", 0),
            premium_type=data.get("premium_type", 0),
            public_flags=data.get("public_flags", 0),
            premium_since=data.get("premium_since", None),
            created_at=data.get("created_at", None),
        )


class Member:

    AVATAR_URL = "https://cdn.discordapp.com/avatars/{id}/{avatar}.webp?size=256"

    def __init__(
        self,
        *,
        user,
        nick,
        avatar,
        roles,
        joined_at,
        premium_since,
        deaf,
        mute,
        pending,
        permissions,
    ):
        self.user = user
        self.nick = nick
        self.avatar = avatar
        self.roles = roles
        self.joined_at = joined_at
        self.premium_since = premium_since
        self.deaf = deaf
        self.mute = mute
        self.pending = pending
        self.permissions = permissions

    def __repr__(self):
        return f"<Member user={self.user} nick={self.nick} avatar={self.avatar} roles={self.roles} joined_at={self.joined_at} premium_since={self.premium_since} deaf={self.deaf} mute={self.mute} pending={self.pending} permissions={self.permissions}>"

    @property
    def avatar_url(self):
        return self.AVATAR_URL.format(
            id=self.user.id, avatar=self.avatar or self.user.avatar
        )

    @property
    def id(self):
        return self.user.id

    @property
    def name(self):
        return self.nick or self.user.username

    @property
    def safe_name(self):
        return (self.name if len(self.name) <= 32 else self.name[:32] + "...").replace(
            "@", "@\u200b"
        )

    @property
    def bot(self):
        return self.user.bot

    @property
    def system(self):
        return self.user.system

    @property
    def mfa_enabled(self):
        return self.user.mfa_enabled

    @classmethod
    def from_json(cls, data):
        return cls(
            user=User.from_json(data["user"]),
            nick=data.get("nick"),
            avatar=data.get("avatar"),
            roles=data.get("roles"),
            joined_at=data.get("joined_at"),
            premium_since=data.get("premium_since"),
            deaf=data.get("deaf"),
            mute=data.get("mute"),
            pending=data.get("pending"),
            permissions=data.get("permissions"),
        )
