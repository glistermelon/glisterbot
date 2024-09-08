import pymunk
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps
from wordbomb import Game
from io import BytesIO
import bot
import discord

space = None
ball_body = None
ball = None
pegs = None
font = None

def draw_circle(im_draw, pos, r, color):
    x = pos[0]
    y = pos[1]
    if type(x) is not int: x = int(x)
    if type(y) is not int: y = int(y)
    if type(r) is not int: r = int(r)
    im_draw.ellipse((x - r, y - r, x + r, y + r), color)

class Plinko():

    ball_diameter = 30
    ball_radius = ball_diameter / 2
    peg_radius = ball_diameter / 7
    layers = 6
    gap_width =  ball_diameter * 1.1 + peg_radius * 2
    gap_height = ball_diameter * 1.3 + peg_radius * 2
    vertical_offset = 70
    width = gap_width * (layers + 2.5)
    height = gap_height * (layers + 2)
    goal_height = vertical_offset + gap_height * (layers + 0.5)
    font_size = ball_diameter

    physics_rate = 60
    graphics_proportion = 2 # 1 in every 2 physics frames written to gif
    extra_seconds = 10

    def __init__(self):
        self.frame = 0
        self.images = []
    
    def step_physics(self):
        space.step(1 / 60)
        self.frame += 1
        if self.frame % Plinko.graphics_proportion == 0:
            self.frame = 0
            self.step_graphics()
    
    def step_graphics(self):

        im = Image.new('RGB', (int(Plinko.width), int(Plinko.height)), (30, 33, 36))

        draw = ImageDraw.Draw(im)

        draw_circle(draw, ball_body.position, Plinko.ball_radius, (255, 0, 0))
        for peg in pegs:
            draw_circle(draw, peg.position, Plinko.peg_radius, (255, 255, 255))

        for i in range(-1, -1 - (Plinko.layers + 2), -1):
            text = Image.new('RGB', (int(Plinko.width), Plinko.font_size))
            text_draw = ImageDraw.Draw(text)
            text_draw.text((0, 0), '500', font=font, fill=(255, 0, 0))
            
            corner = [0, 0]
            for x in range(text.size[0]):
                for y in range(text.size[1]):
                    r,g,b = text.getpixel((x, y))
                    if r != 0 or g != 0 or b != 0:
                        if x > corner[0]: corner[0] = x
                        if y > corner[1]: corner[1] = y
            corner = [corner[0] + 1, corner[1] + 1]
            text = text.crop((0, 0, corner[0], corner[1]))

            paste = text.rotate(0, expand=1)
            im.paste(
                im=paste,
                box=(100, 100)
            )

        self.images.append(im)
    
    def generate_images(self):
        for im in self.images[1:]: yield im
        extra_images = int(Plinko.extra_seconds / (Plinko.graphics_proportion / Plinko.physics_rate))
        for _ in range(extra_images): yield self.images[-1]
    
    def play(self) -> BytesIO:
        x = Plinko.width / 2 + 0.95 * random.uniform(-Plinko.gap_width, Plinko.gap_width)
        if x == 0: x = 0.1
        ball_body.position = x, -Plinko.ball_diameter
        while ball_body.position[1] < Plinko.goal_height:
            self.step_physics()
        self.frame = 0
        data = BytesIO()
        self.images[0].save(
            data, 'GIF',
            save_all=True,
            append_images=self.generate_images(),
            optimize=True,
            loop=0,
            duration=int(Plinko.graphics_proportion / Plinko.physics_rate * 1000)
        )
        return data

space = pymunk.Space()
space.gravity = 0, 1000

ball_body = pymunk.Body()
ball_body.position = Plinko.width / 2 + 0.2, -Plinko.ball_diameter
ball = pymunk.Circle(ball_body, Plinko.ball_radius)
ball.mass = 10
ball.friction = 1
space.add(ball_body, ball)

def add_pegs(num_pegs : int = 3, layer : int = 0):
    bodies = []
    offset = Plinko.width / 2 - Plinko.gap_width - Plinko.gap_width / 2 * layer
    for i in range(num_pegs):
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        y = Plinko.vertical_offset + layer * Plinko.gap_height
        body.position = offset + i * Plinko.gap_width, y
        shape = pymunk.Circle(body, Plinko.peg_radius)
        shape.friction = 1
        space.add(body, shape)
        bodies.append(body)
    if layer + 1 < Plinko.layers: bodies += add_pegs(num_pegs + 1, layer + 1)
    return bodies
    
pegs = add_pegs()

font = ImageFont.load_default(Plinko.font_size)

@bot.tree.command(name='plinko', description='Play plinko on Discord!')
async def callback(ctx : discord.Interaction):
    print(Plinko.goal_height)
    if ctx.user.id != 674819147963564054:
        await ctx.response.send_message('This command is under development! Try again later.', ephemeral=True)
        return
    if not Game.is_channel_free(ctx.channel):
        await ctx.response.send_message('There is already a game present in this channel!',ephemeral=True)
        return
    plinko = Plinko()
    gif = plinko.play()
    gif.seek(0)
    embed = discord.Embed(
        title='Plinko!'
    )
    embed.set_image(url='attachment://plinko.gif')
    await ctx.response.send_message(
        embed=embed,
        file=discord.File(gif, filename='plinko.gif')
    )