from .plugin import Tags
from .views import TagView

def setup(bot):
    bot.add_plugin(Tags(bot))
    bot.add_handler(TagView)
