import tweepy

import constants as c
from data import Clipping

auth = tweepy.OAuthHandler(c.API_KEY, c.API_SECRET_KEY)
auth.set_access_token(c.ACCESS_TOKEN, c.ACCESS_TOKEN_SECRET)


api = tweepy.API(auth)


def post_tweet(clip: Clipping):
    tweet = f"{clip.body}\n\n{clip.book_title} ({clip.author})"

    # respect twitter max tweet length
    if len(tweet) > 280:
        raise Exception(
            "Trying to tweet something longer than Twitter max limit! Tweet: " + tweet)

    print(f"Posting tweet of length: {len(tweet)}" )
    api.update_status(tweet)
