"""
Module contains a custom implementation of the help command for BoopliBot
"""

import itertools
import functools
import re
from io import BytesIO
from typing import (
    Tuple
)


import discord
from discord.ext import commands
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)


import BoopliBot


class HelpCommand(commands.HelpCommand):
    """
    Custom implementation of the help command
    """
    NO_CATEGORY = "Other"
    # The patter to use to split texts (uses spaces)
    SPLIT_PATTERN = re.compile(r"(\s+)", re.MULTILINE)
    # Max width of the help img
    HELP_IMG_WIDTH = 3000
    TEXT_INDENTS = 20
    FONT_SIZE = 50
    LINE_SPACING = FONT_SIZE // 2

    async def send_bot_help(self, mapping):
        """
        Handles generalised help for this bot
        """
        # channel = self.get_destination()
        ctx = self.context
        channel = ctx.channel
        bot = ctx.bot
        description = bot.description

        # \u200b
        # no_category = "{0}:".format(HelpCommand.NO_CATEGORY)
        def get_category(command):
            # nonlocal no_category

            cog = command.cog
            string = cog.qualified_name if cog is not None else HelpCommand.NO_CATEGORY
            return string + ":"

        def make_imagetexts(
            string: str,
            font: ImageFont.FreeTypeFont,
            max_text_width: int,
            prefix: str="",
            suffix: str="",
            text_color: Tuple[int, int, int, int]=(255, 255, 255, 255),
            stroke_fill: Tuple[int, int, int, int]=(0, 0, 0, 255),
            text_offsets: Tuple[int, int]=(0, 0)
        ):
            images = list()
            string_size = font.getsize_multiline(string)

            # If this text is too long, we split it
            if string_size[0] > max_text_width:
                word_list = re.split(HelpCommand.SPLIT_PATTERN, string)
                max_id = len(word_list) - 1
                curr_id = 0

                while curr_id <= max_id:
                    this_word = word_list[curr_id]
                    # We may get empty matches, we should skip them
                    if not this_word:
                        curr_id += 1
                        continue
                    this_word_size = font.getsize_multiline(this_word)

                    # if this_word_size[0] > max_text_width:
                    #     # TODO: split long words too or nah?
                    #     # For now just render as is
                    #     pass

                    # Try to concatenate with the next word if possible
                    while curr_id != max_id and this_word_size[0] < max_text_width:
                        next_word = word_list[curr_id + 1]
                        temp_word = this_word + next_word#f"{this_word} {next_word}"
                        temp_word_size = font.getsize_multiline(temp_word)

                        if temp_word_size[0] < max_text_width:
                            this_word = temp_word
                            this_word_size = temp_word_size
                            curr_id += 1

                        else:
                            break

                    img = Image.new("RGBA", (this_word_size[0], this_word_size[1] + HelpCommand.LINE_SPACING), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    draw.text(text_offsets, this_word, fill=text_color, font=font, stroke_fill=stroke_fill, stroke_width=3)

                    images.append(img)

                    curr_id += 1

            else:
                img = Image.new("RGBA", (string_size[0], string_size[1] + HelpCommand.LINE_SPACING), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.text(text_offsets, string, fill=text_color, font=font, stroke_fill=stroke_fill, stroke_width=3)

                images.append(img)

            return images

        def get_max_size(commands):
            """
            """
            as_lengths = (
                discord.utils._string_width(c.name)
                for c in commands
            )
            return max(as_lengths, default=0)

        filtered_cmds = await self.filter_commands(bot.commands, sort=True, key=get_category)
        max_size = get_max_size(filtered_cmds)
        iter_items = itertools.groupby(filtered_cmds, key=get_category)
        font = ImageFont.truetype("Menlo-Regular.ttf", size=HelpCommand.FONT_SIZE)
        max_text_width = HelpCommand.HELP_IMG_WIDTH - 2*HelpCommand.TEXT_INDENTS

        imgtexts = list()
        imgtexts += make_imagetexts(" " + description + "\n", font=font, max_text_width=max_text_width)

        for category, commands in iter_items:
            commands = sorted(commands, key=lambda c: c.name)
            imgtexts += make_imagetexts("\n " + category, font=font, max_text_width=max_text_width)

            for cmd in commands:
                width = max_size - (discord.utils._string_width(cmd.name) - len(cmd.name))
                text = "{0}{1:<{width}} {2}".format(5 * " ", cmd.name, cmd.short_doc, width=width)

                imgtexts += make_imagetexts(text, font=font, max_text_width=max_text_width)

        total_imgtexts_height = functools.reduce(
            lambda total_value, image: total_value + image.height,
            imgtexts,
            0
        )
        total_imgtexts_height += 2 * HelpCommand.TEXT_INDENTS
        base_img = Image.new("RGBA", (HelpCommand.HELP_IMG_WIDTH, total_imgtexts_height), (255, 255, 255, 0))
        next_offset = HelpCommand.TEXT_INDENTS

        for img in imgtexts:
            base_img.paste(img, box=(HelpCommand.TEXT_INDENTS, next_offset), mask=img)
            next_offset += img.height

        buffer = BytesIO()
        base_img.save(buffer, "PNG")
        buffer.seek(0)

        img_file = discord.File(buffer, filename="booplibothelp.png")
        embed = discord.Embed()
        embed.set_image(url="attachment://booplibothelp.png")

        await channel.send(file=img_file, embed=embed)
        # await channel.send(file=img_file)
