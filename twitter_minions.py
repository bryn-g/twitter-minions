""" maintains a database of a twitter users followers and unfollowers. """

import os
import sys
import argparse
import tweepy
import prettytable

import api_minions
import db_minions

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

def get_arguments():
    parser = argparse.ArgumentParser(description='maintains a database of a twitter users ' \
                                     'followers and unfollowers.')
    parser.add_argument('-u', '--user', help="twitter user @name or numeric id", \
                        type=valid_user_id, required=True)
    parser.add_argument('-upd', '--update', help="make a tweepy_api.followers " \
                        "request that updates user data for all database follower records",
                        required=False, action='store_true')

    args = parser.parse_args()

    return args

def process_unfollowers(dbm, apim):
    # unfollowers - id in db but not in api results
    dbm.unfollower_ids = []

    for follower_id in dbm.follower_ids:
        if follower_id not in apim.follower_ids:
            dbm.unfollower_ids.append(follower_id)

    # insert unfollowers in db, remove followers from db
    if dbm.unfollower_ids:
        dbm.insert_unfollowers(dbm.unfollower_ids)
        dbm.remove_followers(dbm.unfollower_ids)

def print_unfollowers(dbm):
    if dbm.unfollowers:
        print("\n- unfollowers:")
        for unfollower in dbm.unfollowers:
            print("    {0} - @{1} - {2}".format(unfollower['id'], unfollower['screen_name'], unfollower['name']))

def process_follower_ids(dbm, apim):

    # new followers - id in api results but not in db
    dbm.new_follower_ids = []
    for follower_id in apim.follower_ids:
        if follower_id not in dbm.follower_ids:
            dbm.new_follower_ids.append(follower_id)

    # insert new followers in db
    if dbm.new_follower_ids:

        display_new_followers = ""

        new_followers = apim.get_users(dbm.new_follower_ids)
        for follower in new_followers:
            #print("+ inserting new follower: {0} - @{1}".format(follower.id, \
            #    follower.screen_name), end='\r')
            dbm.insert_followers([follower])

            if dbm.inserted_followers <= 10:
                display_new_followers += "    {1} - @{2} - {3}".format(dbm.inserted_followers, \
                    follower.id, follower.screen_name, follower.name)
            else:
                display_new_followers = "    {1} - @{2} - {3}".format(dbm.inserted_followers, \
                    follower.id, follower.screen_name, follower.name)

        if dbm.inserted_followers:
            print("\n+ new followers:")
            print(display_new_followers)

    # unfollowers
    process_unfollowers(dbm, apim)
    print_unfollowers(dbm)

def process_followers(dbm, apim):

    display_new_followers = ""

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

        # if follower in db then update their db record
        if follower.id in dbm.follower_ids:
            dbm.update_followers([follower])

        # if follower not in db then insert new follower
        else:
            #print("+ new follower: {0} - @{1}".format(follower.id, \
            #    follower.screen_name), end='\r') # end='\r'
            dbm.insert_followers([follower])

            if dbm.inserted_followers <= 10:
                display_new_followers += "    {1} - @{2} - {3}".format(dbm.inserted_followers, \
                    follower.id, follower.screen_name, follower.name)
            else:
                display_new_followers = "    {1} - @{2} - {3}".format(dbm.inserted_followers, \
                    follower.id, follower.screen_name, follower.name)

        # remove follower from spare followers
        if follower.id in spare_follower_ids:
            spare_follower_ids.remove(follower.id)
        else:
            # so id in /followers but not /follower_ids - happens sometimes
            print("* trying remove follower {0} - not in spare_follower_ids".format(follower.id))

    if dbm.inserted_followers:
        print("\n+ new followers:")
        print(display_new_followers)

    if spare_follower_ids:
        print("\n^ ids in '/followers/ids' not in '/followers/list': " \
              "{0}".format(len(spare_follower_ids)))

        spare_followers = apim.get_users(spare_follower_ids)

        for follower in spare_followers:
            if follower.id in dbm.follower_ids:
                print("    {0} - @{1} - {2}".format(follower.id, follower.screen_name, follower.name))
                dbm.update_followers([follower])
            else:
                print("    {0} - @{1} - {2}".format(follower.id, follower.screen_name, follower.name))
                dbm.insert_followers([follower])

    # unfollowers
    process_unfollowers(dbm, apim)
    print_unfollowers(dbm)

def print_user_summary(user):
    """ prints a brief summary of user information. """

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

def get_user_database_path(user_id):
    # db name is the same as the twitter user id
    user_database_name = "{0}.sqlite".format(user_id)
    #print("* user database: {0}".format(user_database_name))

    # db resides in same directory as the script
    current_directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    user_database_path = os.path.join(current_directory, user_database_name)

    return user_database_path

def main():
    app_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', 'None')
    app_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', 'None')
    app_access_key = os.environ.get('TWITTER_ACCESS_KEY', 'None')
    app_access_secret = os.environ.get('TWITTER_ACCESS_SECRET', 'None')

    user_args = get_arguments()

    apim = api_minions.APIMinions()
    apim.init_api(app_consumer_key, app_consumer_secret, \
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
    print("* followers in '/followers/ids': {0}".format(apim.get_follower_count()))

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

    # if not a full update compare db and api follower ids
    if not user_args.update:
        process_follower_ids(dbm, apim)

    # full update
    else:
        process_followers(dbm, apim)

    stats_table = prettytable.PrettyTable(["attr", "value"], header=False)
    stats_table.align = "l"

    stats_table.add_row(["new followers", dbm.inserted_followers])
    stats_table.add_row(["updated followers", dbm.updated_followers])
    unfollowers_str = "{} ({})".format(dbm.removed_followers, dbm.inserted_unfollowers)
    stats_table.add_row(["unfollowers", unfollowers_str])

    print(stats_table)

    dbm.close_connection()

    print("end.")

if __name__ == '__main__':
    main()
