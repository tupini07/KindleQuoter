import tweepy

import constants as c

auth = tweepy.OAuthHandler(c.API_KEY, c.API_SECRET_KEY)
auth.set_access_token(c.ACCESS_TOKEN, c.ACCESS_TOKEN_SECRET)


api = tweepy.API(auth)


def post_tweet(tweet: str):
    api.update_status(tweet)
