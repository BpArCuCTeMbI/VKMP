# VKMP

This program pulls info about all audio tracks in your VK.COM account and stores it in the file [./dump] in a working directory in format `<Performer> - <Track name>`

Program is developed and tested on Python 3.4.2.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 main.py

# Dump in csv format
python3 main.py --csv

# Dump csv, login with email and specify track numbers to fetch
python3 main.py --csv --email <your@email.com> -n 3224
```
