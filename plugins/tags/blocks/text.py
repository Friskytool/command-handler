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


class ContainsBlock(Block):
    def will_accept(self, ctx: Context) -> bool:
        return ctx.verb.declaration.lower() == ""

    def process(self, ctx: Context) -> Optional[str]:
        if not ctx.verb.payload:
            return "ERROR: No payload provided"
        if not ctx.verb.parameter:
            return "ERROR: No parameter provided"

        payload = helper_split(ctx.verb.payload)

        return ctx.verb.parameter in payload


class InBlock(Block):
    def will_accept(self, ctx: Context) -> bool:
        return ctx.verb.declaration.lower() == "in"

    def process(self, ctx: Context) -> Optional[str]:
        if not ctx.verb.payload:
            return "ERROR: No payload provided"
        if not ctx.verb.parameter:
            return "ERROR: No parameter provided"

        return ctx.verb.parameter in ctx.verb.payload
