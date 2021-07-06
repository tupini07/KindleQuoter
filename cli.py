import click

import data
import twitter


@click.group()
def cli():
    pass


@cli.command()
def post_single_quote():
    """
    Posts a single unprocessed quote to Twitter
    """

    unprocessed_clip = data.get_oldest_unprocessed_clipping()
    twitter.post_tweet(unprocessed_clip)

    data.mark_clipping_as_processed(unprocessed_clip)
    print("Tweet posted!")
