from squid.bot import command, SquidPlugin
from discord import Embed, Color
import shlex
import random

raw = """
It is certain.
It is decidedly so.
Without a doubt.
Yes – definitely.
You may rely on it.
The stars say yes.
As I see it, yes.
Most likely.
Outlook good.
Yes.
Signs point to yes.
Reply hazy, try again.
Ask again later.
Better not tell you now.
Cannot predict now.
Concentrate and ask again.
Don't count on it.
My reply is no.
My sources say no.
Outlook not so good.
Very doubtful."""
normal8ball = [i.strip() for i in raw.split("\n") if i.strip()]
programming8ball = """
It's a hardware problem, give it to the hardware team
It's a software problem, give it to the software team
Cosmic rays flipped a parity bit
It's a feature, not a bug
Talk to a rubber duck
Tell the duck
PEBKAC
Users lie
You let out the magic smoke
8ball.exe has stopped responding
;
404
works on my machine
duplicate question
did you google it?
git gud
undefined
syntax error
drop the table
merge conflict
give it to the junior
sudo
Have you tried turning it off and on again?
undefined is not a function
git reset --hard
git push --force
Check Stack Overflow
You need to reach Ballmer's peak
Not your responsibility.
Try Rebooting
Kernel Panic
404 File not found
This worked just fine, yesterday
Out of Memory
undefined is not a function
RTFM
Should be easy!
HTTP 418
#define true false
#define false true
#define true ((rand()&15)!=15) // I know I'm evil
rm -rf /
fix the merge conflicts
Compiler raised 468 errors while trying to answer your question
an error occured while displaying the previous error
You have to use asyncio to run a coroutine
Resolving deltas
git pull""".split(
    "\n"
)

_morse = {
    "a": ".-",
    "b": "-...",
    "c": "-.-.",
    "d": "-..",
    "e": ".",
    "f": "..-.",
    "g": "--.",
    "h": "....",
    "i": "..",
    "j": ".---",
    "k": "-.-",
    "l": ".-..",
    "m": "--",
    "n": "-.",
    "o": "---",
    "p": ".--.",
    "q": "--.-",
    "r": ".-.",
    "s": "...",
    "t": "-",
    "u": "..-",
    "v": "...-",
    "w": ".--",
    "x": "-..-",
    "y": "-.--",
    "z": "--..",
    " ": "/",
    ".": ".-.-.- ",
    ",": "--..--",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
}

inv_morse = {k: v for v, k in _morse.items()}


def to_keycap(c: int) -> str:
    return "\N{KEYCAP TEN}" if c == 10 else str(c) + "\u20e3"


def morse_translate(morse):
    morse = morse.lower()
    text = morse.replace(".", "").replace("-", "").replace("/", "").strip()
    if text:
        _d = _morse
        iterator = iter(morse)
        more = " "
    else:
        _d = inv_morse
        iterator = iter(morse.split(" "))
        more = ""

    return more.join([_d.get(i, i) for i in iterator])


class Fun(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    # @command()
    # def pp(self, ctx, users: ):
    #     if not users:
    #         users = [ctx.author]

    #     users = list(set(users[:10]))  # get's kinda spammy tbh

    #     sizes = "\n".join(
    #         [
    #             f"{to_keycap(pos)}  {x}"
    #             for pos, x in enumerate(
    #                 sorted(
    #                     [
    #                         f'**{user.display_name}**\n> 8{random.choice([random.randint(0,10),random.randint(20,30)]) *"="}D'
    #                         for user in users
    #                     ],
    #                     key=lambda x: len(x.split("\n")[-1]),
    #                 ),
    #                 start=1,
    #             )
    #         ]
    #     )
    #     sizes = sizes.replace(to_keycap(1), ":first_place:")
    #     sizes = sizes.replace(to_keycap(2), ":second_place:")
    #     sizes = sizes.replace(to_keycap(3), ":third_place:")

    #     storage = self.storage(ctx.guild.id)
    #     storage.set(
    #         ":".join([str(i.id) for i in list(set(users))]) + ":pp", sizes, ex=60
    #     )

    #     return sizes + "\n*Bigger doesn't always mean better*"

    @command()
    def morse(self, ctx, *, message: str):
        """
        Translate to and from morse code!

        If no message is provided friskytool will comb the chat logs for a message containing morse code and decode it
        """

        res = morse_translate(message)[:2000]
        return ctx.respond(
            embed=Embed(description=res, color=ctx.me.color).set_author(
                name=message, icon_url=ctx.author.avatar_url
            )
        )

    @command()
    def roll(self, ctx, _max: int = 6, _min: int = 1):
        """Roll a number from the maximum {default:5} to the minimum {default:0}
        +roll 1 6 > returns number between (and including) 1 and 6"""

        if _max < _min:
            _max, _min = _min, _max

        return ctx.respond(content=f"I rolled a **{random.randint(_min, _max)}**")

    @command(name="coinflip", aliases=["cf"])
    def coinflip(self, ctx, choice: str = "heads"):
        c = random.choice(["heads", "tails"])

        if c == choice.lower():

            return ctx.respond(
                embed=Embed(
                    title="Coinflip",
                    description=f"It landed on **{c.title()}**!\n```diff\n+ You won!\n```",
                    color=self.bot.colors["primary"],
                )
            )
        return ctx.respond(
            embed=Embed(
                title="Coinflip",
                description=f"It landed on **{c.title()}**!\n```diff\n- You lost!\n```",
                color=self.bot.colors["secondary"],
            )
        )

    @command(name="choose")
    def choose(self, ctx, *, choices):
        """Choose a random item out of the choices\nChoices can be seperated by \"|\" and \",\" """

        if "|" in choices:
            args = choices.split("|")
        elif "," in choices:
            args = [i.strip() for i in choices.split(",") if bool(i.strip())]
        else:
            args = shlex.split(choices)

        return ctx.respond(
            embed=Embed(
                description=f"I choose `{random.choice(args)}`", color=Color.green()
            )
        )

    @command(name="percent")
    def cool(self, ctx, thing: str = "you", adjective: str = "cool"):
        """Give a percentage about something like you!\nEnter in a <thing> to take the percentage on and an adjective like cool and watch our powerful machines do the rest"""
        thing = thing[:200]
        percent = random.randint(0, 100)

        colorc = Color.green()
        if percent < 34:
            colorc = Color.red()
        elif percent < 67:
            colorc = Color(0xFFD300)
        return ctx.respond(
            embed=Embed(
                description=f"I calculate **{thing}** as {percent}% {adjective}!",
                color=colorc,
            )
        )

    @command(name="8ball")
    def _8ball(self, ctx, *, question: str = None):
        """Ask a question and recieve a response"""
        choice = random.choice(normal8ball)
        limit = 200
        question = question[:limit] if question is str else question

        return ctx.respond(
            embed=Embed(description=choice, color=Color.blue()).set_author(
                name=question or ctx.author.display_name, icon_url=ctx.author.avatar_url
            )
        )

    @command(name="programmer8ball", aliases=["p8ball"])
    def p8ball(self, ctx, *, question: str = None):
        """ "Ask a question and get a programmer-like response"""
        choice = random.choice(programming8ball)
        limit = 200
        question = question[:limit] if question is str else question

        return ctx.respond(
            embed=Embed(description=choice, color=Color.blue()).set_author(
                name=question or ctx.author.display_name, icon_url=ctx.author.avatar_url
            )
        )


def setup(bot):
    bot.add_plugin(Fun(bot))
