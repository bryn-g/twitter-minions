""" handles the bulk of the tweepy api operations """

import tweepy

# todo: _follower_ids & property and setter, follower_ids_count property
# get_follower_ids consistent with db version

class APIMinions(object):
    """ minions tweepy api class. """

    def __init__(self):
        """ create the object with empty properties. """
        self.api = None
        self.user = None

        self.follower_ids = []

    def init_api(self, app_consumer_key, app_consumer_secret, app_access_key, app_access_secret):
        """ creates a tweepy api object. """

        try:
            auth = tweepy.OAuthHandler(app_consumer_key, app_consumer_secret)
            auth.set_access_token(app_access_key, app_access_secret)

            self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, \
                compression=True)
        except tweepy.TweepError as err:
            print("get_api error: {0}".format(err))

    def get_users(self, user_ids):
        """ gets tweepy user objects for a list of user ids.

        returns:
            list: a list of user objects.
        """
        users = []
        for uid in user_ids:
            try:
                user = self.api.get_user(uid)
                users.append(user)
            except tweepy.TweepError as err:
                print("get_users error: {0}".format(err))
                continue

        return users

    def get_follower_count(self):
        """ gets the current follower id count.

        returns:
            int: the number of ids in the follower_ids list.
        """
        return len(self.follower_ids)

    def get_follower_ids(self):
        """ gets the follower ids for the users followers from api.followers_ids request.

        returns:
            list: follower ids.
        """

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
        #return follower_ids
