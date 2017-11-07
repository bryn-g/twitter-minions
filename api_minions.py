import sys
import argparse
import tweepy
import prettytable

class APIMinions(object):
    def __init__(self):
        self.api = None
        self.user = None

        self.follower_ids = []
        self.followers = []

    def get_follower_count(self):
        return len(self.follower_ids)

    def init_api(self, app_consumer_key, app_consumer_secret, app_access_key, app_access_secret):
        try:
            auth = tweepy.OAuthHandler(app_consumer_key, app_consumer_secret)
            auth.set_access_token(app_access_key, app_access_secret)

            self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, \
                compression=True)
        except tweepy.TweepError as err:
            print("get_api error: {0}".format(err))

    def get_users(self, user_ids):
        users = []
        for uid in user_ids:
            try:
                user = self.api.get_user(uid)
                users.append(user)
            except tweepy.TweepError as err:
                print("get_users error: {0}".format(err))
                continue

        return users

    def print_user_summary(self):
        user_table = prettytable.PrettyTable(["user", "id", "friends", "followers", "ratio"])
        user_table.align = "l"

        user_name = "@{0}".format(self.user.screen_name)

        ratio = 0
        if self.user.friends_count > 0:
            ratio = float(self.user.followers_count) / float(self.user.friends_count)

        ratio = "{0:.2f}".format(ratio)

        user_table.add_row([user_name, str(self.user.id), str(self.user.friends_count),
                            str(self.user.followers_count), str(ratio)])

        print(user_table)

    def get_follower_ids(self):
        follower_ids = []
        follower_id_pages = tweepy.Cursor(self.api.followers_ids, user_id=self.user.id,
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

        self.follower_ids = follower_ids
        return follower_ids

    # tba
    def get_followers(self):
        followers = []
        follower_items = tweepy.Cursor(self.api.followers, user_id=self.user.id).items()
