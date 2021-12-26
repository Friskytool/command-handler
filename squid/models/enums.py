from enum import Enum 

__all__ = (
    "InteractionType",
    "ApplicationCommandType",
    "ApplicationCommandOptionType",
)

class InteractionType(Enum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4

class ApplicationCommandType(Enum):
    CHAT_INPUT = 1   # Slash commands; a text-based command that shows up when a user types /
    USER	= 2	        # A UI-based command that shows up when you right click or tap on a user
    MESSAGE	= 3	        # A UI-based command that shows up when you right click or tap on a message

class ApplicationCommandOptionType(Enum):
    SUB_COMMAND	=1	
    SUB_COMMAND_GROUP = 2	
    STRING	= 3	
    INTEGER	= 4	#       Any integer between -2^53 and 2^53
    BOOLEAN	= 5	
    USER	= 6	
    CHANNEL	= 7	#       Includes all channel types + categories
    ROLE	= 8	
    MENTIONABLE	= 9 #   Includes users and roles
    NUMBER	= 10 #      Any double between -2^53 and 2^53
