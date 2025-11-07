Here you go—clean and reproducible.

# README (Tachyon + Waveshare 7.5" e-Paper HAT / UC8179)

Tested on **Particle Tachyon** (Ubuntu **20.04**, aarch64) with **Waveshare 7.5" e-Paper HAT (SKU 13504, 800×480, mono)** using **Blinka + Adafruit_CircuitPython_EPD**.

## 0) System prep (APT)

```bash
sudo apt-get update
sudo apt-get install -y python3-venv libgpiod2 libgpiod-dev python3-libgpiod
```

## 1) Enable SPI/GPIO access for your user (no sudo needed to run)

```bash
# create groups if missing
sudo groupadd -f spi
sudo groupadd -f gpio

# add your user
sudo usermod -aG spi,gpio $USER

# udev rules (use SUBSYSTEM for spidev)
echo 'SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"' | sudo tee /etc/udev/rules.d/90-spi.rules
echo 'KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/90-gpio.rules

# reload and re-probe
sudo udevadm control --reload-rules
sudo modprobe -r spidev && sudo modprobe spidev

# log out/in (or reboot) so group membership is active
```

**Verify:**

```bash
ls -l /dev/spidev0.0
# expect: crw-rw---- 1 root spi ... /dev/spidev0.0

ls -l /dev/gpiochip*
# expect group 'gpio' on gpiochip* nodes

groups
# expect your user is in 'spi' and 'gpio'
```

## 2) Python env (venv that can read system libgpiod)

```bash
cd ~/einkT2
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

**Quick probe:**

```bash
python - <<'PY'
import board, busio
print("Blinka OK, has SPI:", hasattr(board, "SCK"), hasattr(board, "MOSI"))
PY
# expect: True True
```

## 3) Hardware wiring (GPIO numbers = BCM; pins = 40-pin header)

* **CLK → SCK** (GPIO11, pin 23)
* **DIN → MOSI** (GPIO10, pin 19)
* **CS  → CE0** (GPIO8,  pin 24)
* **DC  → GPIO25** (pin 22)
* **RST → GPIO17** (pin 11)
* **BUSY → GPIO24** (pin 18)
* **PWR → GPIO18** (pin 12) — **must drive HIGH** before init
* **5V + GND** to HAT power header

## 4) HAT DIP/switch settings

* **Interface**: **4-line SPI** (not 3-wire/“3R”).
* **Display Config**: **B** (for 7.5" mono 800×480 UC8179).

## 5) Run a simple test (Pillow path)

Your working script should:

* Set **PWR** (GPIO18) **HIGH**
* Create `Adafruit_UC8179(800, 480, ...)`
* Call:

  ```python
  display.set_black_buffer(1, False)
  display.set_color_buffer(1, False)
  ```
* Use **Pillow** (`Image.new("L", (w,h), 255)`) then:

  ```python
  display.image(img)   # where img.mode == "L" or "RGB"
  display.display()
  ```

## 6) Troubleshooting quick hits

* If the display stays blank: confirm **PWR** is HIGH, and 5V is connected.
* If permissions error on `/dev/spidev0.0`: recheck udev rule/group; re-`modprobe spidev`.
* If Blinka says it can’t find libgpiod: ensure `python3-libgpiod` is installed and the venv was created with `--system-site-packages`.
* If visual artifacts: reduce SPI clock by configuring `busio.SPI` right after creation:

  ```python
  while not spi.try_lock(): pass
  spi.configure(baudrate=1_000_000, polarity=0, phase=0)
  spi.unlock()
  ```


