import os
import time
from colorama.ansi import Fore
from datetime import datetime

import tweepy
from tqdm import tqdm

import constants as c
from data import Clipping

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
        except tweepy.errors.TweepyException:
            wait_seconds = 20
            _tqdm_wait(
                wait_seconds, f'Misc error while processing. Waiting {wait_seconds} seconds before retrying..')
        except StopIteration:
            return


def _execute_with_timout_handle(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except tweepy.TooManyRequests:
            _tqdm_wait(
                _TIMEOUT_WAIT_TIME, f'Timout from Twitter. Waiting {_TIMEOUT_WAIT_TIME} seconds')
        except tweepy.errors.TweepyException:
            wait_seconds = 20
            _tqdm_wait(
                wait_seconds, f'Misc error while processing. Waiting {wait_seconds} seconds before retrying..')


def is_person_following_me(person_screen_name: str) -> bool:
    relation = _execute_with_timout_handle(
        api.lookup_friendships, person_screen_name)

    if relation is None or len(relation) == 0:
        return False
    elif relation[0].following:
        return True

    return False


def unfollow_unfollowers(num: int):
    if not os.path.exists("./data/work_dir"):
        os.mkdir("./data/work_dir")

    previously_unfollowed_user_ids = []
    if os.path.exists("./data/work_dir/previously_unfollowed.txt"):
        previously_unfollowed_user_ids = [s.split(" - ")[0] for s in open(
            "./data/work_dir/previously_unfollowed.txt", "r").read().split("\n") if s != ""]

    tqdm.write(
        f"Will try to unfollow the oldest {Fore.CYAN}'{num}' {Fore.RESET}accounts which are not following back")
    all_friends_ids = []

    for friend_id in tqdm(_limit_handled(tweepy.Cursor(api.get_friend_ids, count=5000).items())):
        all_friends_ids.append(friend_id)

    # we want to unfollow oldest first
    all_friends_ids.reverse()
    processed = 0
    for user_id in all_friends_ids:
        if user_id in previously_unfollowed_user_ids:
            tqdm.write(
                f"{Fore.YELLOW}WARNING: {Fore.WHITE}Not unfollowing {Fore.CYAN}{user_id} {Fore.WHITE}since we had already unfollowed them in the past")
            continue

        relation = _execute_with_timout_handle(
            api.get_friendship, source_id=user_id, target_screen_name=c.USER_SCREEN_NAME)[0]

        if not relation.following:
            tqdm.write(
                f"[{Fore.YELLOW}{processed+1}{Fore.RESET}/{Fore.YELLOW}{num}{Fore.RESET}] Destroying friendship with '{Fore.CYAN}{relation.screen_name}'")
            _execute_with_timout_handle(
                api.destroy_friendship, user_id=user_id)
            processed += 1
            with open("./data/work_dir/previously_unfollowed.txt", "a+") as ff:
                ff.write(f"{user_id} - {relation.screen_name}\n")
            _tqdm_wait(60, "Waiting a minute to prevent flooding Twitter API")

        if processed >= num:
            tqdm.write(
                f'{Fore.YELLOW}Finished unfollowing bad friends - {datetime.now()}')
            break


def follow_all_followers():
    # follow all followers
    tqdm.write(f"--- Ensure that we're following all followers ---")
    for follower in tqdm(_limit_handled(tweepy.Cursor(api.get_followers, count=200).items(400))):
        if not follower.following:
            tqdm.write(f"Starting to follow follower user: {follower.name}")
            _execute_with_timout_handle(follower.follow)
            _tqdm_wait(60, "Waiting a minute to prevent flooding Twitter API")

    # follow all that have retweeted
    tqdm.write(f"--- Following all users that have retweeted ---")
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
            if len(retweeter_ids_in_chunk) == 0:
                continue

            try:
                for retweeter in _execute_with_timout_handle(api.lookup_users, user_id=retweeter_ids_in_chunk, include_entities=False, tweet_mode=False):
                    if not retweeter.following:
                        tqdm.write(
                            f"Starting to follow retweeter user: {retweeter.name}")
                        try:
                            _execute_with_timout_handle(retweeter.follow)
                        except:
                            raise Exception(
                                f"Couldn't follow user {retweeter.name} [retweeter.id]")
                        _tqdm_wait(
                            60, "Waiting a minute to prevent flooding Twitter API")
            except tweepy.NotFound:
                raise Exception(
                    "Failed to lookup users with ids: " + str(retweeter_ids_in_chunk))

    # TODO follow all that have liked
    # tqdm.write(f"Following all users that have liked")
    # for tweet in tqdm(_limit_handled(tweepy.Cursor(api.list_timeline, count=100, trim_user=True, include_entities=False, include_user_entities=False).items())):
    #     pass


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


def follow_followers_of_others(target_amount, handlers):
    num_followed = 0
    self_id = _execute_with_timout_handle(
        api.verify_credentials).id
    for handler in handlers:
        tqdm.write(f"--- Starting to follow followers of {handler} ---")
        for follower in tqdm(_limit_handled(tweepy.Cursor(api.get_followers, screen_name=handler, count=200).items())):
            if (follower.id == self_id):
                continue
            if not follower.following and not follower.protected:
                num_followed += 1
                tqdm.write(
                    f"[{num_followed}/{target_amount}] Starting to follow user: {follower.screen_name}")
                _execute_with_timout_handle(follower.follow)
                _tqdm_wait(
                    60, "Waiting a minute to prevent flooding Twitter API")

            if num_followed >= target_amount:
                return
