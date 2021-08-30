from datetime import datetime

import click
from colorama import Back, Fore

import data
import twitter


@click.group()
def cli():
    pass


@cli.command()
def skip_selected():
    """
    Add marked quotes as skipped

    Prepend any "quote(s)" in "My Clippings.txt" with `>> ` (without backticks) and it will
    be added as an already processed quote. Useful when reviewing clippings for stuff that 
    shouldn't be posted.
    """
    to_skip = data.get_clippings_marked_for_skipping()
    print(Fore.YELLOW + datetime.now().isoformat())
    print(Fore.GREEN + f"Adding {len(to_skip)} as processed tweets")

    for clip in to_skip:
        data.mark_clipping_as_processed(clip)


@cli.command()
@click.option('--skip', is_flag=True, help="If specified, the next clipping will be marked as processed but won't actually be posted to twitter")
def post_single_quote(skip):
    """
    Posts a single unprocessed quote to Twitter
    """

    unprocessed_clip = data.get_oldest_unprocessed_clipping()

    print(Fore.YELLOW + datetime.now().isoformat())

    if not skip:
        twitter.post_tweet(unprocessed_clip)
        print(Fore.GREEN + "Tweet posted!")
    else:
        print(Fore.YELLOW + "Skipping tweet!")
        print(Fore.LIGHTCYAN_EX + Back.MAGENTA + unprocessed_clip.body)

    data.mark_clipping_as_processed(unprocessed_clip)
