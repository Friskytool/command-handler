from functools import wraps
import inspect
from flask import jsonify
from discord import Embed

from squid.models.interaction import InteractionResponse


def flask_compat(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)

        if not isinstance(response, InteractionResponse) or not hasattr(
            response, "to_dict"
        ):
            raise TypeError(
                "Response must be an InteractionResponse or contain a to_dict() method object but recieved {}: ({})".format(
                    type(response), response.__repr__()
                )
            )

        return jsonify(response.to_dict())

    return wrapper
