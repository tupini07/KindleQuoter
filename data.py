import os
import re
import string
from datetime import datetime
from typing import List

import constants as c

_printable_character_set = set(string.printable)

DB_FILE = "data/processed.db"


class Clipping():
    book_title: str
    author: str
    location: str
    date_highlighted: datetime
    body: str

    def __init__(self, book_title: str, author: str, location: str, date_highlighted: str, body: str):
        self.book_title = book_title
        self.author = author
        self.location = location
        self.date_highlighted = datetime.strptime(
            date_highlighted, "%B %d, %Y %I:%M:%S %p")
        self.body = body

    def get_id(s) -> str:
        no_newline_body = ''.join(x for x in s.body if x != '\n')
        return f"{s.book_title} - {s.author} - {s.location} - {s.date_highlighted.isoformat()} - {no_newline_body}"

    def __str__(self):
        return f"<Clipping @book_title='{self.book_title}' @author='{self.author}' @body='{self.body}'>"


def _sanitize_raw_clipping(raw_clipping: str) -> str:
    special_chars = {
        "—": "-"
    }

    sanitized = raw_clipping
    sanitized = [special_chars[c]
                 if c in special_chars else c for c in sanitized]
    sanitized = [c for c in sanitized if c in _printable_character_set]

    return ''.join(sanitized)


def _process_raw_clipping(raw_clipping: str) -> Clipping:
    sanitized = _sanitize_raw_clipping(raw_clipping)

    # get header and quote body
    [header, quote_body] = sanitized.split("\n\n")

    [title_part, location_date_part] = header.split("\n")

    # get the title and author
    title_author_search = re.search(r'^(.*) \((.*)\)$', title_part)
    [title, author] = title_author_search.groups()

    # Do swaps for title and author if necessary
    if title_swap := c.TITLE_SWAPS.get(title):
        title = title_swap

    if author_swap := c.AUTHOR_SWAPS.get(author):
        author = author_swap

    # get the location and highlight date
    location_date_search = re.search(
        r'^.* Location (.*) \| Added on \w+, (.*)$', location_date_part)
    [location, str_date] = location_date_search.groups()

    return Clipping(
        book_title=title,
        author=author,
        location=location,
        date_highlighted=str_date,
        body=quote_body
    )


def _read_clippings_file() -> List[Clipping]:
    """
    Returns instances of Clipping representing each clipping in the clipping file.
    The returned list is ordered from OLDEST to NEWEST clipping.
    """
    with open("./data/My Clippings.txt", 'r') as d_file:
        raw_clippings = [c.strip() for c in d_file.read().split(
            "==========") if c.strip() != ""]

        # process all clippings
        processed_clippings = []
        for i, rc in enumerate(raw_clippings):

            # if the current clipping is a bookmark then ignore it
            if "your bookmark on" in rc.lower():
                continue

            try:
                processed_clippings.append(
                    _process_raw_clipping(rc)
                )
            except:
                raise AttributeError("Error while processing clipping:\n" + rc)

        # sort read clippings by date (from oldest to newest)
        return sorted(processed_clippings, key=lambda x: x.date_highlighted)


def get_oldest_unprocessed_clipping() -> Clipping:
    clippings = _read_clippings_file()

    # if we have no DB file then we know oldest clipping hasn't been processed
    if not os.path.exists(DB_FILE):
        return clippings[0]

    with open(DB_FILE, 'r') as db_file:
        contents = db_file.read().split("\n")

    for clip in clippings:
        if clip.get_id() not in contents:
            return clip

    # if we get here then it means we have no oldest unprocessed clip
    raise Exception("There is no unprocessed clipping!")


def mark_clipping_as_processed(clip: Clipping) -> None:
    contents = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as db_file:
            contents = db_file.read().split('\n')

    with open(DB_FILE, 'a+') as db_file:
        clip_id = clip.get_id()
        if clip_id in contents:
            raise Exception(
                "Trying to add clipping to DB but there's already an entry for it. Clipping id: " + clip_id)

        db_file.write(clip_id + '\n')


def get_clippings_marked_for_skipping() -> List[Clipping]:
    clippings = _read_clippings_file()
    to_skip = []

    for clip in clippings:
        if clip.book_title.startswith(">> "):
            # remove the marker
            clip.book_title = clip.book_title[3:]
            to_skip.append(clip)

    return to_skip
