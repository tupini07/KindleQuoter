import tweepy

import constants as c
from data import Clipping

auth = tweepy.OAuthHandler(c.API_KEY, c.API_SECRET_KEY)
auth.set_access_token(c.ACCESS_TOKEN, c.ACCESS_TOKEN_SECRET)


api = tweepy.API(auth)


def post_tweet(clip: Clipping):
    # don't add extra hashtags if c.HASHTAGS is empty or None
    extra_hashtags = f"\n{c.HASHTAGS}" if c.HASHTAGS else ""

    tweet = f"{clip.body}\n\n{clip.book_title} ({clip.author}){extra_hashtags}"

    # respect twitter max tweet length
    if len(tweet) > 280:
        raise Exception(
            "Trying to tweet something longer than Twitter max limit! Tweet: " + tweet)

    print(f"Posting tweet of length: {len(tweet)}")
    api.update_status(tweet)
