import sys
import argparse
import tweepy
import prettytable

def valid_user_id(user_id):
    user_id = str(user_id)

    if user_id.isdigit():
        return user_id
    else:
        if user_id[0] != '@':
            msg = "user name must start with @."
            raise argparse.ArgumentTypeError(msg)

        if len(user_id) > 16 or len(user_id) < 2:
            msg = "user names are 16 characters or less."
            raise argparse.ArgumentTypeError(msg)

        user_name_temp = user_id[1:]
        for char in user_name_temp:
            if not char.isalnum() and char != '_':
                msg = "user name characters are alphanumeric or _."
                raise argparse.ArgumentTypeError(msg)

        return user_id

def get_api(app_consumer_key, app_consumer_secret, app_access_key, app_access_secret):
    try:
        auth = tweepy.OAuthHandler(app_consumer_key, app_consumer_secret)
        auth.set_access_token(app_access_key, app_access_secret)

        api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, \
            compression=True)
    except tweepy.TweepError as err:
        print("get_api error: {0}".format(err))
        sys.exit()

    return api

def print_user_summary(twitter_user):
    user_table = prettytable.PrettyTable(["user", "id", "friends", "followers", "ratio"])
    user_table.align = "l"

    user_name = "@{0}".format(twitter_user.screen_name)

    ratio = 0
    if twitter_user.friends_count > 0:
        ratio = float(twitter_user.followers_count) / float(twitter_user.friends_count)

    ratio = "{0:.2f}".format(ratio)

    user_table.add_row([user_name, str(twitter_user.id), str(twitter_user.friends_count),
                        str(twitter_user.followers_count), str(ratio)])

    print(user_table)

def get_users(tweepy_api, user_ids):
    users = []
    for uid in user_ids:
        try:
            user = tweepy_api.get_user(uid)
            users.append(user)
        except tweepy.TweepError as err:
            print("get_users error: {0}".format(err))
            continue

    return users

def get_follower_ids(api, uid):
    follower_ids = []
    follower_id_pages = tweepy.Cursor(api.followers_ids, user_id=uid,
                                      cursor=-1).pages()
    while True:
        try:
            follower_id_page = next(follower_id_pages)
        except tweepy.TweepError as err:
            print("get_follower_ids error: {0}".format(err))
            continue
        except StopIteration:
            break

        follower_ids.extend(follower_id_page)

    # *** test ***
    #test_ids = []
    #for test in test_ids:
    #    if test in follower_ids:
    #        follower_ids.remove(test)

    return follower_ids
