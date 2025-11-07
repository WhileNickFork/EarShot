# test_uc8179_pillow_L.py
import time, board, busio, digitalio
from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.uc8179 import Adafruit_UC8179
from PIL import Image, ImageDraw, ImageFont

# SPI: CLK->SCK, DIN->MOSI (MISO can be unconnected)
spi  = busio.SPI(board.SCK, board.MOSI, board.MISO)

# Control pins (match your wiring)
cs   = digitalio.DigitalInOut(board.D8)    # CE0 (GPIO8, pin 24)
dc   = digitalio.DigitalInOut(board.D25)   # GPIO25, pin 22
rst  = digitalio.DigitalInOut(board.D17)   # GPIO17, pin 11
busy = digitalio.DigitalInOut(board.D24)   # GPIO24, pin 18

# HAT power enable (GPIO18, pin 12)
pwr  = digitalio.DigitalInOut(board.D18)
pwr.direction = digitalio.Direction.OUTPUT
pwr.value = True
time.sleep(0.05)

display = Adafruit_UC8179(
    800, 480, spi,
    cs_pin=cs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy
)

# Required for UC8179 5.83"/7.5" mono panels
display.set_black_buffer(1, False)
display.set_color_buffer(1, False)

display.rotation = 1
display.fill(Adafruit_EPD.WHITE)

# Build grayscale canvas ("L"): 255=white, 0=black
img = Image.new("L", (display.width, display.height), 255)
draw = ImageDraw.Draw(img)

# Font
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
except Exception:
    font = ImageFont.load_default()

# Draw
draw.text((10, 10), "Hello Tachyon!", font=font, fill=0)
draw.rectangle((8, 8, 300, 60), outline=0, width=1)
draw.line((10, 70, 790, 70), fill=0, width=1)

# Send to panel
display.image(img)          # 'img' is already "L"
display.display()
