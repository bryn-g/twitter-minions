""" maintains a database of a twitter users followers and unfollowers. """

import os
import sys
import argparse
import tweepy
import prettytable

import api_minions
import db_minions

class MinionSummaryList(object):
    """ limited list of followers summary data captured during processing. """
    def __init__(self, summary_list_size=10):
        self.list_size = summary_list_size
        self._count = 0

        self._minions = {}
        for num in range(0, self.list_size):
            self._minions[num] = None

    @property
    def minions(self):
        """ returns list of minions objects. """
        return self._minions

    @minions.setter
    def minions(self, minion_summary):
        """ add minion object to list, overwrites previous entries when self.list_size reached. """
        if self._count == self.list_size:
            self._count = 0

        self._minions[self._count] = minion_summary
        self._count += 1

class MinionSummary(object):
    """ summary data about a follower. """
    def __init__(self, prefix, user_id, screen_name, name):
        self.prefix = prefix
        self.user_id = user_id
        self.screen_name = "@{0}".format(screen_name)
        self.name = name

    def get_minion_summary(self):
        """ return formated output of object properties. """
        return "{0} - {1} - @{2} - {3}".format(self.prefix, self.user_id, \
                                               self.screen_name, self.name)

def get_arguments():
    """ script arguments, user id is a required parameter. """
    parser = argparse.ArgumentParser(description='maintains a database of a twitter users ' \
                                     'followers and unfollowers.')
    parser.add_argument('-u', '--user', help="twitter user @name or numeric id", \
                        type=valid_user_id, required=True)
    parser.add_argument('-upd', '--update', help="make a tweepy_api.followers " \
                        "request that updates user data for all database follower records",
                        required=False, action='store_true')

    args = parser.parse_args()

    return args

def valid_user_id(user_id):
    """ checks provided user id meets twitter constraints. """
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

def get_user_database_path(user_id):
    """ returns expected database path. uses numeric user id as database name
        and current directory as directory path. """

    user_database_name = "{0}.sqlite".format(user_id)

    current_directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    user_database_path = os.path.join(current_directory, user_database_name)

    return user_database_path

def process_unfollowers(dbm, apim):
    """ performs insertion of unfollowers into unfollowers table and
        the removal of unfollowers from followers table. """
    dbm.unfollower_ids = []

    # ids in database but not returned from api requests are unfollowers
    for follower_id in dbm.follower_ids:
        if follower_id not in apim.follower_ids:
            dbm.unfollower_ids.append(follower_id)

    if dbm.unfollower_ids:
        dbm.insert_unfollowers(dbm.unfollower_ids)
        dbm.remove_followers(dbm.unfollower_ids)

def process_follower_ids(dbm, apim):
    """ performs database insertion of new followers as determined by comparing
        database ids and /followers/ids api results. prints a summary of new followers.

        * does not update followers records in the database. """

    summary_followers_count = 20
    new_follower_summary = MinionSummaryList(summary_followers_count)

    # new followers, id in list returned from api request but not in database
    dbm.new_follower_ids = []
    for follower_id in apim.follower_ids:
        if follower_id not in dbm.follower_ids:
            dbm.new_follower_ids.append(follower_id)

    # insert new followers in database
    if dbm.new_follower_ids:

        # gets the user objects for new followers using api /users/show/:id request
        new_followers = apim.get_users(dbm.new_follower_ids)
        for follower in new_followers:
            #print("+ inserting new follower: {0} - @{1}".format(follower.id, \
            #    follower.screen_name), end='\r')
            dbm.insert_followers([follower])

            minion = MinionSummary(dbm.inserted_followers, follower.id, \
                                   follower.screen_name, follower.name)
            new_follower_summary.minions = minion

        # print summary of followers inserted into database
        if dbm.inserted_followers:
            last_followers_txt = ""
            if dbm.inserted_followers > summary_followers_count:
                last_followers_txt = "(last {0})".format(summary_followers_count)

            title = "+ new followers: {0} {1}".format(dbm.inserted_followers, last_followers_txt)
            print_follower_summary(new_follower_summary.minions, title)

def process_followers(dbm, apim):
    """ performs insertion of new followers and updating of existing followers database
        records. user objects from api /followers/list results are used to insert new and
        update existing followers records. user ids found in /followers/ids api results but
        not /followers/list results are called spares and added to the spares list. prints a
        summary of new followers.

        * updates followers records in the database. """

    summary_followers_count = 20
    new_follower_summary = MinionSummaryList(summary_followers_count)

    # decrementing list
    spare_follower_ids = list(apim.follower_ids)

    api_followers = tweepy.Cursor(apim.api.followers, user_id=apim.user.id).items()

    while True:
        try:
            follower = next(api_followers)
        except tweepy.TweepError as err:
            print("tweepy_api.followers cursor error: {0} (continue)".format(err))
            continue
        except StopIteration:
            break

        # if follower in database then update their database record
        if follower.id in dbm.follower_ids:
            dbm.update_followers([follower])

        # if follower not in database then insert new follower
        else:
            #print("+ new follower: {0} - @{1}".format(follower.id, \
            #    follower.screen_name), end='\r') # end='\r'
            dbm.insert_followers([follower])

            minion = MinionSummary(dbm.inserted_followers, follower.id, \
                                   follower.screen_name, follower.name)
            new_follower_summary.minions = minion

        # eliminate follower from spare followers list
        if follower.id in spare_follower_ids:
            spare_follower_ids.remove(follower.id)
        else:
            # so id in /followers but not /follower_ids - unusual but happens sometimes
            print("* trying remove follower {0} - not in spare_follower_ids".format(follower.id))

    # print summary of followers inserted into database
    if dbm.inserted_followers:
        last_followers_txt = ""
        if dbm.inserted_followers > summary_followers_count:
            last_followers_txt = "(last {0})".format(summary_followers_count)

        title = "+ new followers: {0} {1}".format(dbm.inserted_followers, last_followers_txt)
        print_follower_summary(new_follower_summary.minions, title)

    # remainder user ids in spare_follower_ids are spare followers
    if spare_follower_ids:
        process_spare_followers(dbm, apim, spare_follower_ids)

def process_spare_followers(dbm, apim, spare_follower_ids):
    """ retrieves user objects for each spare follower and inserts a new follower or updates
        the follower record depending on if their id is in the database. prints a summary
        of new and updated followers. """

    summary_followers_count = 10
    spare_follower_summary = MinionSummaryList(summary_followers_count)

    # get user objects for spare followers using api /users/show/:id request
    spare_followers = apim.get_users(spare_follower_ids)

    for follower in spare_followers:
        prefix = ""

        if follower.id in dbm.follower_ids:
            dbm.update_followers([follower])
            prefix = "^"
        else:
            dbm.insert_followers([follower])
            prefix = "+"

        minion = MinionSummary(prefix, follower.id, follower.screen_name, follower.name)
        spare_follower_summary.minions = minion

    # print summary of spare followers updated or inserted into database
    last_followers_txt = ""
    if len(spare_follower_ids) > summary_followers_count:
        last_followers_txt = "(last {0})".format(summary_followers_count)

    title = "^ spare ids in '/followers/ids' not in '/followers/list':" \
        "{0} {1}".format(len(spare_follower_ids), last_followers_txt)
    print_follower_summary(spare_follower_summary.minions, title)

# accepts MinionSummaryList.minions dictionary
def print_follower_summary(minions, title):
    """ print a table of summary data about followers. """
    print(title)

    minion_table = prettytable.PrettyTable(["", "screen name", "name"], header=False)
    minion_table.align = "l"

    for i, minion in sorted(minions.items()):
        if minion:
            minion_table.add_row([minion.prefix, minion.screen_name, minion.name])

    print(minion_table)

def print_unfollowers(dbm):
    """ formats captured data about unfollowers into a standard minions summary format.
        prints a summary of unfollowers. """

    if dbm.unfollowers:
        summary_unfollowers_count = 20
        unfollower_summary = MinionSummaryList(summary_unfollowers_count)

        for unfollower in dbm.unfollowers:
            minion = MinionSummary(unfollower['i'], unfollower['user_id'], \
                                   "@{0}".format(unfollower['user_screen_name']), \
                                   unfollower['user_name'])
            unfollower_summary.minions = minion

        last_followers_txt = ""
        if len(dbm.unfollowers) > summary_unfollowers_count:
            last_followers_txt = "(last {0})".format(summary_unfollowers_count)

        title = "- unfollowers: {0} {1}".format(len(dbm.unfollowers), last_followers_txt)
        print_follower_summary(unfollower_summary.minions, title)

def print_user_summary(user):
    """ prints a table with some data about the twitter user. accepts a user object. """

    user_table = prettytable.PrettyTable(["user", "id", "friends", "followers", "ratio"])
    user_table.align = "l"

    user_name = "@{0}".format(user.screen_name)

    ratio = 0
    if user.friends_count > 0:
        ratio = float(user.followers_count) / float(user.friends_count)

    ratio = "{0:.2f}".format(ratio)

    user_table.add_row([user_name, str(user.id), str(user.friends_count),
                        str(user.followers_count), str(ratio)])

    print(user_table)

def print_stats(dbm):
    """ prints a summary about processing from DBMinions processing counters. """

    stats_table = prettytable.PrettyTable(["attr", "value"], header=False)
    stats_table.align = "l"

    stats_table.add_row(["new followers", dbm.inserted_followers])
    stats_table.add_row(["updated followers", dbm.updated_followers])
    unfollowers_str = "{} ({})".format(dbm.removed_followers, dbm.inserted_unfollowers)
    stats_table.add_row(["unfollowers", unfollowers_str])

    print(stats_table)

def main():
    """ retrieves, processes and databases a users followers. """

    app_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', 'None')
    app_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', 'None')
    app_access_key = os.environ.get('TWITTER_ACCESS_KEY', 'None')
    app_access_secret = os.environ.get('TWITTER_ACCESS_SECRET', 'None')

    user_args = get_arguments()

    apim = api_minions.APIMinions(app_consumer_key, app_consumer_secret, \
                                  app_access_key, app_access_secret)

    if not apim.api:
        print("* unable to initialize the tweepy api.")
        sys.exit()

    apim.user = apim.get_users([user_args.user])[0]
    if not apim.user:
        print("* unable to retrieve user: {0}".format(user_args.user))
        sys.exit()

    print_user_summary(apim.user)

    dbm = db_minions.DBMinions(get_user_database_path(apim.user.id))

    if not dbm.connection:
        print("* unable to make a database connection: {0}".format(dbm.path))
        sys.exit()

    dbm.get_follower_ids()
    print("* followers in database: {0}".format(dbm.follower_ids_count))

    apim.get_follower_ids()
    print("* followers in '/followers/ids': {0}".format(apim.follower_ids_count))

    # if no db followers ask to do a full update
    if not user_args.update and dbm.follower_ids_count < 1:

        print("* no records in the database. please collect some followers by using the " \
            "'-upd' updates option or select 'y'.")
        collect_followers = input("  do you wish to collect followers now? (y/n): ")

        if collect_followers.lower().strip() == "y":
            user_args.update = True
        else:
            print("* no database followers. exiting.")
            dbm.close_connection()
            sys.exit()

    # process followers
    if not user_args.update:
        process_follower_ids(dbm, apim)
    else:
        process_followers(dbm, apim)

    # process unfollowers
    process_unfollowers(dbm, apim)
    print_unfollowers(dbm)

    # summary of processing
    print("* summary:")
    print_stats(dbm)

    dbm.close_connection()
    print("end.")

if __name__ == '__main__':
    main()
