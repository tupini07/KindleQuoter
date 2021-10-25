import time

import tweepy

import constants as c
from data import Clipping
from tqdm import tqdm

auth = tweepy.OAuthHandler(c.API_KEY, c.API_SECRET_KEY)
auth.set_access_token(c.ACCESS_TOKEN, c.ACCESS_TOKEN_SECRET)


api = tweepy.API(auth)
_TIMEOUT_WAIT_TIME = 15*60


def _tqdm_wait(duration, msg):
    tqdm.write(msg)
    for _ in tqdm(range(duration)):
        time.sleep(1)


def _limit_handled(cursor):
    while True:
        try:
            yield next(cursor)
        except tweepy.TooManyRequests:
            _tqdm_wait(
                _TIMEOUT_WAIT_TIME, f'Timout from Twitter. Waiting {_TIMEOUT_WAIT_TIME} seconds')
        except StopIteration:
            return


def _execute_with_timout_handle(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except tweepy.TooManyRequests:
            _tqdm_wait(
                _TIMEOUT_WAIT_TIME, f'Timout from Twitter. Waiting {_TIMEOUT_WAIT_TIME} seconds')


def is_person_following_me(person_screen_name: str) -> bool:
    relation = _execute_with_timout_handle(
        api.lookup_friendships, person_screen_name)

    if relation is None or len(relation) == 0:
        return False
    elif relation[0].following:
        return True

    return False


def unfollow_unfollowers(num: int):
    tqdm.write(
        f"Will try to unfollow the oldest '{num}' accounts which are not following back")
    all_friends_ids = []

    for friend_id in tqdm(_limit_handled(tweepy.Cursor(api.get_friend_ids, count=5000).items())):
        all_friends_ids.append(friend_id)

    # we want to unfollow oldest first
    all_friends_ids.reverse()
    processed = 0
    for user_id in all_friends_ids:
        relation = _execute_with_timout_handle(
            api.get_friendship, source_id=user_id, target_screen_name=c.USER_SCREEN_NAME)[0]

        if not relation.following:
            tqdm.write(f"Destroying friendship with '{relation.screen_name}'")
            _execute_with_timout_handle(
                api.destroy_friendship, user_id=user_id)
            processed += 1
            _tqdm_wait(60, "Waiting a minute to prevent flooding Twitter API")

        if processed >= num:
            tqdm.write('Finished unfollowing bad friends')
            break


def follow_all_followers():
    # follow all that have retweeted
    tqdm.write(f"Following all users that have retweeted")
    for tweet in tqdm(_limit_handled(tweepy.Cursor(api.get_retweets_of_me, count=100, trim_user=True, include_entities=False, include_user_entities=False).items())):
        retweeters_ids = [rtid for rtid in _limit_handled(
            tweepy.Cursor(api.get_retweeter_ids, count=100, id=tweet.id).items())]

        retweet_ids_chunks = [[]]
        for rtid in retweeters_ids:
            current_chunk = retweet_ids_chunks[-1]
            if len(current_chunk) == 100:
                retweet_ids_chunks.append([])
                current_chunk = retweet_ids_chunks[-1]

            current_chunk.append(rtid)

        for retweeter_ids_in_chunk in retweet_ids_chunks:
            if len(retweet_ids_chunks == 0):
                return
            for retweeter in _execute_with_timout_handle(api.lookup_users, user_id=retweeter_ids_in_chunk, include_entities=False, tweet_mode=False):
                if not retweeter.following:
                    tqdm.write(
                        f"Starting to follow retweeter user: {retweeter.name}")
                    _execute_with_timout_handle(retweeter.follow)
                    _tqdm_wait(
                        60, "Waiting a minute to prevent flooding Twitter API")

    # TODO follow all that have liked
    # tqdm.write(f"Following all users that have liked")
    # for tweet in tqdm(_limit_handled(tweepy.Cursor(api.list_timeline, count=100, trim_user=True, include_entities=False, include_user_entities=False).items())):
    #     pass

    # follow all followers
    tqdm.write(f"Ensure that we're following all followers")
    for follower in tqdm(_limit_handled(tweepy.Cursor(api.get_followers, count=200).items(400))):
        if not follower.following:
            tqdm.write(f"Starting to follow follower user: {follower.name}")
            _execute_with_timout_handle(follower.follow)
            _tqdm_wait(60, "Waiting a minute to prevent flooding Twitter API")


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
