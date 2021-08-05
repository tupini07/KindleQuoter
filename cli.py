import click
from colorama import Back, Fore

import data
import twitter


@click.group()
def cli():
    pass


@cli.command()
@click.option('--skip', is_flag=True, help="If specified, the next clipping will be marked as processed but won't actually be posted to twitter")
def post_single_quote(skip):
    """
    Posts a single unprocessed quote to Twitter
    """

    unprocessed_clip = data.get_oldest_unprocessed_clipping()

    if not skip:
        twitter.post_tweet(unprocessed_clip)
        print(Fore.GREEN + "Tweet posted!")
    else: 
        print(Fore.YELLOW + "Skipping tweet!")
        print(Fore.LIGHTCYAN_EX + Back.MAGENTA + unprocessed_clip.body)

    data.mark_clipping_as_processed(unprocessed_clip)
