from functools import wraps
import inspect
from flask import jsonify
from discord import Embed

from squid.models.interaction import InteractionResponse


def flask_compat(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)

        if not isinstance(response, InteractionResponse):
            raise TypeError(
                "Response must be an InteractionResponse object but recieved {}: ({})".format(
                    type(response), response.__repr__()
                )
            )

        return jsonify(response.to_dict())

    return wrapper
