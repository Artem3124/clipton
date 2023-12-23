#!/usr/bin/env python

import re
import sys
import json
import html
import shutil
import subprocess
from pathlib import Path
from typing import List

import utils
from settings import setting
from converts import convert_text

# Items are held here internally
items = []

# Path to the json file
filepath: Path

# Style for rofi windows
rofi_style = '-me-select-entry "" -me-accept-entry "MousePrimary" \
  -theme-str "window {width: 66%;}"'

# Get a rofi prompt
def rofi_prompt(s: str) -> str:
  return f'rofi -dmenu -markup-rows -i -p "{s}"'

# Show the rofi menu with the items
def show_picker(selected: int = 0) -> None:
  opts: List[str] = []
  date_now = utils.get_seconds()
  asterisk = f"<span> * </span>"

  for item in items:
    line = item["text"].strip()
    line = html.escape(line)
    line = re.sub(" *\n *", "\n", line)
    line = line.replace("\n", asterisk)
    line = re.sub(" +", " ", line)
    line = re.sub("</span> +", "</span>", line)
    num_lines = str(item["num_lines"]) + ")"
    num_lines = num_lines.ljust(5, " ")
    mins = round((date_now - item["date"]) / 60)
    timeago = utils.get_timeago(mins)
    title = ""

    if "title" in item:
      title = item["title"]

      if title and title != "":
        title = title.replace("\n", "").strip()
        title = html.escape(title)
        line += f" ({title})"

    opts.append(f"<span>{timeago}(Lines: {num_lines}</span>{line}")

  prompt = rofi_prompt("Alt+1 Delete | Alt+(2-9) Join | Alt+0 Clear")
  proc = subprocess.Popen(f"{prompt} -format i {rofi_style} -selected-row {selected}", stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, text=True)
  ans = proc.communicate("\n".join(opts))[0].strip()

  if ans != "":
    code = proc.returncode
    index = int(ans)

    if code == 10:
      delete_item(index)
      show_picker(index)
    elif code >= 11 and code <= 18:
      join_items(code - 9)
    elif code == 19:
      confirm_delete_items()
    else:
      select_item(index)

# Copy text to clipboar
def copy_text(text: str) -> None:
  proc = subprocess.Popen("xclip -sel clip -f", stdout = subprocess.PIPE, stdin = subprocess.PIPE, shell = True, text = True)
  proc.communicate(text, timeout = 3)

# When an item is selected through the rofi menu
def select_item(index: int) -> None:
  text = items[index]["text"]
  copy_text(text)

# Delete an item from the item list
def delete_item(index: int) -> None:
  del items[index]
  update_file()

# Delete all items
def confirm_delete_items() -> None:
  opts = ["No", "Yes"]
  prompt = rofi_prompt("Delete all items?")
  proc = subprocess.Popen(f"{prompt} {rofi_style} -selected-row 0", stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, text=True)
  ans = proc.communicate("\n".join(opts))[0].strip()

  if ans == "Yes":
    delete_items()

# Delete all the items
def delete_items() -> None:
  global items
  items = []
  update_file()

# Join 2 or more items into one
def join_items(num: int) -> None:
  s = " ".join(item["text"].strip() for item in reversed(items[0:num]))
  del items[0:num]
  update_file()
  copy_text(s)

# Read the items file and parse it to json
def get_items() -> None:
  global items
  global filepath

  configdir = Path("~/.config/clipton").expanduser()

  if not configdir.exists():
    configdir.mkdir(parents=True)

  filepath = configdir / Path("items.json")
  filepath.touch(exist_ok=True)

  file = open(filepath, "r")
  content = file.read().strip()

  if content == "":
    content = "[]"

  items = json.loads(content)
  file.close()

# Stringify the json object and save it into the file
def update_file() -> None:
  file = open(filepath, "w")
  file.write(json.dumps(items))
  file.close()

# Add an item to the items array
# It performs some checks
# It removes duplicates
def add_item(text: str) -> None:
  global items
  text = text.rstrip()

  if text == "":
    return

  if text.startswith("file://"):
    return

  if len(text) > setting("heavy_paste"):
    return

  if setting("enable_converts"):
    text = convert_text(text)

  item_exists = False

  for item in items:
    if item["text"] == text:
      the_item = item
      item_exists = True
      items.remove(the_item)
      break

  if not item_exists:
    title = ""

    if setting("enable_titles"):
      title = utils.get_title(text)

    num_lines = text.count("\n") + 1
    the_item = {"date": utils.get_seconds(), "text": text, "num_lines": num_lines, "title": title}

  items.insert(0, the_item)
  items = items[0:setting("max_items")]
  update_file()

# Start the clipboard watcher
def start_watcher() -> None:
  if shutil.which("copyevent") is None:
    print("The watcher needs 'copyevent' to be installed.")
    exit(1)

  herepath = Path(__file__).parent.resolve()
  max_iterations = 100
  iterations = 0

  while True:
    try:
      iterations += 1

      if iterations > max_iterations:
        utils.log("Too many iterations")
        exit(1)

      ans = subprocess.run("copyevent -s clipboard", capture_output = True, shell = True)

      if ans.returncode == 0:
        ans = subprocess.run("xclip -o -sel clip", capture_output = True, shell = True, timeout = 3)

        if ans.returncode == 0:
          clip = ans.stdout.decode()

          if clip:
            get_items()
            add_item(clip)
            iterations = 0
    except Exception as err:
      utils.log(err)

# Main function
def main() -> None:
  mode = "show"

  if len(sys.argv) > 1:
    mode = sys.argv[1]

  if mode == "watcher":
    try:
      start_watcher()
    except KeyboardInterrupt:
      exit(0)

  elif mode == "show":
    get_items()
    show_picker()

if __name__ == "__main__":
  main()