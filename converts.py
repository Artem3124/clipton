import re
import utils
from settings import setting

# Convert something to another thing automatically when copied to clipboard
def convert_text(text: str) -> str:
  if utils.space(text): return text

  if setting("converts")["youtube_music"]:
    regex = re.compile(r"https://music\.youtube\.com/(watch\?v=([\w-]+)|playlist\?list=([\w-]+))")
    match = regex.search(text)

    if match and match.group(2):
      video_id = match.group(2)
      new_text = f'https://www.youtube.com/watch?v={video_id}'
      return new_text

    if match and match.group(3):
      playlist_id = match.group(3)
      new_text = f'https://www.youtube.com/playlist?list={playlist_id}'
      return new_text

  return text