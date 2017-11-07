""" maintains a database of a twitter users followers and unfollowers. """

import os
import sys
import argparse
import tweepy

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

    print("* unfollowers: ", dbm.get_unfollower_count())

    # insert unfollowers in db, remove followers from db
    if dbm.unfollower_ids:
        num_unfollowers = dbm.get_unfollower_count()
        print("* unfollowers ids: {0}".format(num_unfollowers))
        if num_unfollowers <= 10:
            print("  {0}".format(dbm.unfollower_ids))

        inserted_unfollowers = dbm.insert_unfollowers(dbm.unfollower_ids)
        print("- inserted database unfollowers: {0}".format(inserted_unfollowers))

        removed_followers = dbm.remove_followers(dbm.unfollower_ids)
        print("- removed database followers: {0}".format(removed_followers))

def process_follower_ids(dbm, apim):

    # new followers - id in api results but not in db
    dbm.new_follower_ids = []
    for follower_id in apim.follower_ids:
        if follower_id not in dbm.follower_ids:
            dbm.new_follower_ids.append(follower_id)

    # insert new followers in db
    if dbm.new_follower_ids:
        print("* new followers ids: {0}".format(dbm.get_new_follower_count()))

        inserted_followers = 0
        new_followers = apim.get_users(dbm.new_follower_ids)
        for follower in new_followers:
            print("+ inserting new follower: {0} - {1}".format(follower.id, \
                follower.screen_name))
            inserted_followers += dbm.insert_followers([follower])

        print("+ new followers inserted: {0}".format(inserted_followers))

    # unfollowers
    process_unfollowers(dbm, apim)

def process_followers(dbm, apim):

    inserted_followers = 0
    updated_followers = 0
    inserted_unfollowers = 0
    removed_followers = 0

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
            updated_followers += dbm.update_followers([follower])

        # if follower not in db then insert new follower
        else:
            print("+ inserting new follower: {0} - {1}".format(follower.id, \
                follower.screen_name))
            inserted_followers += dbm.insert_followers([follower])

        # remove follower from spare followers
        if follower.id in spare_follower_ids:
            spare_follower_ids.remove(follower.id)
        else:
            print("* trying remove follower {0} - not in spare_follower_ids".format(follower.id))

    if spare_follower_ids:
        print("* ids in 'tweepy_api.followers_ids' not in 'tweepy_api.followers': " \
              "{0}".format(len(spare_follower_ids)))

        spare_followers = apim.get_users(spare_follower_ids)

        for follower in spare_followers:
            if follower.id in dbm.follower_ids:
                print("^ updating spare: {0} - {1}".format(follower.id, follower.screen_name))
                updated_followers += dbm.update_followers([follower])
            else:
                print("+ inserting spare: {0} - {1}".format(follower.id, follower.screen_name))
                inserted_followers += dbm.insert_followers([follower])

    print("^ updated database followers: {0}".format(updated_followers))
    print("+ new followers inserted: {0}".format(inserted_followers))

    # unfollowers
    process_unfollowers(dbm, apim)

def main():
    # twitter api application keys
    app_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', 'None')
    app_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', 'None')
    app_access_key = os.environ.get('TWITTER_ACCESS_KEY', 'None')
    app_access_secret = os.environ.get('TWITTER_ACCESS_SECRET', 'None')

    user_args = get_arguments()

    apim = api_minions.APIMinions()
    apim.init_api(app_consumer_key, app_consumer_secret, \
                  app_access_key, app_access_secret)

    if not apim.api:
        print("* unable to init the tweepy api.")
        sys.exit()

    apim.user = apim.get_users([user_args.user])[0]

    if not apim.user:
        print("* unable to retrieve user: {0}".format(user_args.user))
        sys.exit()

    apim.print_user_summary()

    # db name is the same as the twitter user id
    user_database_name = "{0}.sqlite".format(apim.user.id)
    print("* user database: {0}".format(user_database_name))

    # db resides in same directory as the script
    current_directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    user_database_path = os.path.join(current_directory, user_database_name)

    dbm = db_minions.DBMinions()
    dbm.init_database(user_database_path)

    if not dbm.connection:
        print("* unable to make a database connection: {0}".format(dbm.path))
        sys.exit()

    dbm.get_follower_ids()
    print("* followers in database: {0}".format(dbm.get_follower_count()))

    apim.get_follower_ids()
    print("* twitter 'tweepy_api.followers_ids': {0}".format(apim.get_follower_count()))

    # if no db followers ask to do a full update
    if not user_args.update and dbm.get_follower_count() < 1:

        print("* no records in the database. please collect some followers by using the " \
            "'-upd' updates option or select 'y'.")
        collect_followers = input("do you wish to collect followers now? (y/n): ")

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

    dbm.close_connection()

    print("end.")

if __name__ == '__main__':
    main()
