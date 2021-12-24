from functools import wraps
import inspect
from flask import jsonify
from discord import Embed


def flask_compat(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        embed = f(*args, **kwargs)

        if not isinstance(embed, Embed):
            raise TypeError(
                "Response must be an Embed object but recieved {}: ({})".format(
                    type(embed), embed.__repr__()
                )
            )

        r = jsonify({"type": 4, "data": {"embeds": [embed.to_dict()]}})
        print(r)
        return r

    return wrapper
