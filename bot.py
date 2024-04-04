"""
discord quote bot
https://twitter.com/notcosmatic speedrunning to 1 follower

requirements:
- discord.py installed (pip install discord.py)
- default python packages installed
- PIL installed (pip install pillow)
- better_profanity installed (pip install better_profanity)
- background image (4k prefered) saved as background.png
- discord bot token created and placed as a string bellow
"""

TOKEN = "<YOUR TOKEN HERE>"

# imports
import discord
import json
from discord.ext import commands, tasks
from better_profanity import (
    profanity,
)  # might be a virus package idk im too lazy to check
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import time
from pathlib import Path

intents = discord.Intents.default()  # set intents
intents.messages = True

bot = commands.Bot(command_prefix="", intents=intents)

# wipe data and set up files to store data
try:
    files = os.listdir("images")
    # Loop through the files and delete them
    for file in files:
        file_path = os.path.join("images", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
except:
    os.mkdir("images")

my_file = Path("stats.json")
if not my_file.is_file():
    with open("stats.json", "w") as f:
        f.write(
            '{"quotes": 0, "cooldown": [], "expires": {}}'
        )  # not formatting the json cuz im lazy


@bot.event
async def on_ready():
    # reset cooldowns
    with open("stats.json") as f:
        data = json.loads(f.read())
    data["cooldown"] = []
    data["expires"] = {}
    with open("stats.json", "w") as f:
        f.write(json.dumps(data, indent=2))

    update_database.start()

    print(f"Logged in as {bot.user.name} ({bot.user.id})")


def get_text_dimensions(text_string, font):
    # get the width and height of a string of a specific font
    ascent, descent = font.getmetrics()
    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent
    return (text_width, text_height)  # return the sizes


async def add_text_to_image(image_path, quote, author, username, output_path):
    # load the images
    image = Image.open("background.png")
    pfp = Image.open(image_path)

    # get the sizes and resize as needed
    image_width, image_height = image.size
    pfp = pfp.resize((image_width // 3, image_width // 3))

    # draw pfp onto larger image and make it a circle
    mask = Image.new("L", (image_width // 3, image_width // 3), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, image_width // 3, image_width // 3), fill=255)
    pfp.putalpha(mask)
    image.paste(
        pfp,
        (
            int((image.width * 0.35 - pfp.width) * 0.5),
            int((image.height - pfp.width) * 0.5),
        ),
        pfp,
    )
    font = ImageFont.truetype("arial.ttf", 100)  # set the font and font size

    text_image = Image.new(
        "RGBA", image.size, (255, 255, 255, 0)
    )  # make a new text layer
    text_draw = ImageDraw.Draw(text_image)
    font_width, font_height = get_text_dimensions(
        quote, font
    )  # get the total size of the quote
    left_margin = image.width * 0.05  # set margins
    right_margin = image.width * 0.05
    available_width = (
        (image.width * 0.7) - left_margin - right_margin
    )  # set size boundries for the text
    total_text_width = get_text_dimensions(quote, font)[0]
    total_text_height = get_text_dimensions(quote, font)[1]
    y = (image.height - total_text_height) / 2 + (
        image.height * 0.5
    )  # help center th etext
    words = quote.split()  # split the quote into individual words
    current_line = ""
    size = 0  # stores total height of the quote on the image
    for (
        word
    ) in (
        words
    ):  # basically just calculates when to start a new line to prevent overflow, not explaining allat
        test_line = f"{current_line} {word}".strip()
        text_width, _ = get_text_dimensions(test_line, font)
        if text_width <= available_width:
            current_line = test_line
        else:
            x = (
                left_margin
                + (image.width * 0.3)
                + (available_width - get_text_dimensions(current_line, font)[0]) / 2
            )
            text_draw.text(
                (
                    x,
                    ((y - (image.height * 0.5))),
                ),
                current_line,
                font=font,
                fill="white",
            )
            y += get_text_dimensions(current_line, font)[1]
            size += get_text_dimensions(current_line, font)[1]
            current_line = word
    if current_line:  # add the final line
        x = (
            left_margin
            + +(image.width * 0.3)
            + (available_width - get_text_dimensions(current_line, font)[0]) / 2
        )
        text_draw.text(
            (
                x,
                ((y - (image.height * 0.5))),
            ),
            current_line,
            font=font,
            fill="white",
        )
        y += get_text_dimensions(current_line, font)[1]
        size += get_text_dimensions(current_line, font)[1]
    author = "\n- " + author + f" (@{username})"
    if author:  # add the author at the bottom
        x = (
            left_margin
            + +(image.width * 0.3)
            + (available_width - get_text_dimensions(author, font)[0]) / 2
        )
        text_draw.text(
            (
                x,
                ((y - (image.height * 0.5))),
            ),
            author,
            font=font,
            fill="white",
        )
        y += get_text_dimensions(author, font)[1]
        size += get_text_dimensions(current_line, font)[1]
    rotated_text_image = text_image.rotate(
        0, expand=True
    )  # why the hell is this here, these next 6 lines are completely useless, dev pls fix
    rotated_text_width, rotated_text_height = rotated_text_image.size
    rotated_center_x = (image.width - rotated_text_width) / 2
    rotated_center_y = (image.height - rotated_text_height) / 2 - (
        total_text_height * 0.5
    )

    # put the quote onto the background image
    image.paste(
        rotated_text_image,
        (int(rotated_center_x), int(rotated_center_y - (size / 2))),
        rotated_text_image,
    )
    image.save(output_path)  # export the image


async def download_image(url, save_path):
    # downloads a image from a url (used to download discord pfps)
    response = requests.get(url)
    if response.status_code == 200:  # 200 == good :thumbsup:
        with open(save_path, "wb") as f:
            f.write(response.content)
    else:
        print("Failed to download image.")  # womp womp
        # program will probably crash and burn idk


@bot.event
async def on_message(message):
    if f"<@{bot.user.id}> quote" in message.content:  # check if the keywords are said
        if message.reference:  # if the message is replying to another
            if message.content != None:  # if the message has words
                with open("stats.json") as f:
                    data = json.loads(f.read())
                if (
                    message.channel.id not in data["cooldown"]
                ):  # make sure the channel hasnt had a quote recently to prevent spam

                    replied_message = (
                        await message.channel.fetch_message(  # get the message
                            message.reference.message_id
                        )
                    )
                    quote = replied_message.content
                    if (
                        str(quote) == ""
                    ):  # prevent program from exploding (your welcome)
                        await message.channel.send(
                            "The message must have text!", reference=message
                        )
                        return

                    quote = profanity.censor(
                        quote
                    )  # removes slurs and such using the maybe virus package

                    try:
                        avatar_url = (
                            replied_message.author.avatar.url
                        )  # get the avatar url
                    except:  # prevent program from exploding (again)
                        await message.channel.send(
                            "Cannot quote a user with no profile photo, please set one",
                            reference=message,
                        )
                        return

                    await download_image(
                        avatar_url, f"images/{replied_message.id}.png"
                    )  # download the image
                    username = replied_message.author.name  # get usernames and such
                    display = replied_message.author.display_name
                    await add_text_to_image(  # call the function to create the image
                        f"images/{replied_message.id}.png",
                        quote,
                        display,
                        username,
                        f"images/{replied_message.id}_out.png",
                    )
                    os.remove(
                        f"images/{replied_message.id}.png"
                    )  # remove the old images, i dont have the storage to save them all
                    with open(
                        f"images/{replied_message.id}_out.png", "rb"
                    ) as f:  # upload the quote pic to discord and send it
                        picture = discord.File(f)
                    await message.channel.send(file=picture, reference=message)
                    # os.remove(
                    # f"images/{replied_message.id}_out.png"
                    # )  # remove the quote pic after its sent

                    data["cooldown"].append(
                        message.channel.id
                    )  # add the channel to the cooldown list
                    data["expires"].update(
                        {message.channel.id: {"expires": int(time.time() + 60)}}
                    )
                    with open("stats.json", "w") as f:
                        f.write(json.dumps(data, indent=2))
                else:
                    await message.channel.send(
                        "Only one quote can be made per channel per minute!",
                        reference=message,
                    )
            else:
                await message.channel.send(
                    "The message must have text!", reference=message
                )
        else:
            await message.channel.send(
                "You must be replying to a message!", reference=message
            )


@tasks.loop(seconds=15)  # this is terrible horrible implimentation but i do not care
async def update_database():
    with open("stats.json") as f:  # get data
        data = json.loads(f.read())

    x = 0
    for i in data["cooldown"]:  # loop through all the data
        if (
            int(time.time()) > data["expires"][str(i)]["expires"]
        ):  # check if its been a min
            del data["cooldown"][x]  # if yes, remove it from the cooldown
            del data["expires"][str(i)]
        x += 1
    with open("stats.json", "w") as f:  # write the changed data
        f.write(json.dumps(data, indent=2))


bot.run(TOKEN)  # run the bot
