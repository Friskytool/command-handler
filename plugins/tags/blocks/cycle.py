"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from typing import Optional

from TagScriptEngine import Context, Block, helper_split


class CycleBlock(Block):
    # This is an undocumented block and should not be used.
    def will_accept(self, ctx: Context) -> bool:
        return ctx.verb.declaration.lower() == "cycle"

    def process(self, ctx: Context) -> Optional[str]:
        items = helper_split(ctx.verb.payload)

        if param := ctx.verb.parameter:
            try:
                index = int(param)
            except ValueError:
                return None
        else:
            index = 0

        return items[index % len(items)]


class ListBlock(Block):
    # This is an undocumented block and should not be used.
    def will_accept(self, ctx: Context) -> bool:
        return ctx.verb.declaration.lower() == "list"

    def process(self, ctx: Context) -> Optional[str]:
        items = helper_split(ctx.verb.payload)

        if param := ctx.verb.parameter:
            try:
                index = int(param)
            except ValueError:
                return "ERROR: Invalid index"
        else:
            index = 0

        if index >= len(items):
            return "null"
        return items[index]
