""" maintains a database of a twitter users followers and unfollowers. """

import os
import sys
import argparse
import tweepy

import api_minions
import db_minions

def create_user_database(file_path):
    file_path = str(file_path)

    if not os.path.isfile(file_path):
        print("* database '" + file_path + "' does not exist.")
        create_db = input("do you wish to create it? (y/n): ")

        create_db = "{0}".format(create_db)
        if create_db.lower().strip() == "y":
            db_minions.create_database(file_path)
        else:
            print("* no database. exiting.")
            sys.exit()

def get_arguments():
    parser = argparse.ArgumentParser(description='maintains a database of a twitter users ' \
                                     'followers and unfollowers.')

    parser.add_argument('-u', '--user', help="twitter user @name or numeric id", \
                        type=api_minions.valid_user_id, required=True)

    parser.add_argument('-upd', '--update', help="make a tweepy_api.followers " \
                        "request that updates user data for all database follower records",
                        required=False, action='store_true')

    args = parser.parse_args()

    return args

def main():
    # twitter api application keys
    app_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', 'None')
    app_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', 'None')
    app_access_key = os.environ.get('TWITTER_ACCESS_KEY', 'None')
    app_access_secret = os.environ.get('TWITTER_ACCESS_SECRET', 'None')

    user_args = get_arguments()

    tweepy_api = api_minions.get_api(app_consumer_key, app_consumer_secret, \
                                     app_access_key, app_access_secret)

    twitter_user = api_minions.get_users(tweepy_api, [user_args.user])
    if len(twitter_user) < 1:
        print("* unable to retrieve user: {0}".format(user_args.user))
        sys.exit()
    twitter_user = twitter_user[0]

    api_minions.print_user_summary(twitter_user)

    # db name is the same as the twitter user id
    user_database_name = "{0}.sqlite".format(twitter_user.id)
    print("* user database: {0}".format(user_database_name))

    # db resides in same directory as the script
    current_directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    user_database_path = "{0}/{1}".format(current_directory, user_database_name)

    create_user_database(user_database_path)

    db_connection = db_minions.create_connection(user_database_path)
    if not db_connection:
        print("* unable to make a database connection: {0}".format(user_database_name))
        sys.exit()

    # get list of follower ids from db
    db_id_list = db_minions.get_follower_ids(db_connection)
    print("* followers in database: {0}".format(len(db_id_list)))

    # get list of follower ids from api request
    twitter_id_list = api_minions.get_follower_ids(tweepy_api, twitter_user.id)
    print("* twitter 'tweepy_api.followers_ids': {0}".format(len(twitter_id_list)))

    # if no db followers ask to do a full update
    if not user_args.update and len(db_id_list) < 1:

        print("* no records in the database. please collect some followers by using the " \
            "'-upd' updates option or select 'y'.")
        collect_followers = input("do you wish to collect followers now? (y/n): ")

        collect_followers = "{0}".format(collect_followers)
        if collect_followers.lower().strip() == "y":
            user_args.update = True
        else:
            print("* no database followers. exiting.")
            db_connection.close()
            sys.exit()

    # if not a full update compare db and api follower ids
    if not user_args.update:

        # unfollowers - id in db but not in api results
        unfollowers_id_list = []
        for db_follower_id in db_id_list:
            if db_follower_id not in twitter_id_list:
                unfollowers_id_list.append(db_follower_id)

        # new followers - id in api results but not in db
        new_followers_id_list = []
        for tweepy_follower_id in twitter_id_list:
            if tweepy_follower_id not in db_id_list:
                new_followers_id_list.append(tweepy_follower_id)

        # insert new followers in db
        if new_followers_id_list:
            print("* new followers ids: {0}".format(len(new_followers_id_list)))

            inserted_followers = 0
            new_followers = api_minions.get_users(tweepy_api, new_followers_id_list)
            for follower in new_followers:
                print("+ inserting new follower: {0} - {1}".format(follower.id, \
                    follower.screen_name))
                inserted_followers += db_minions.insert_followers(db_connection, [follower])

            print("+ new followers inserted: {0}".format(inserted_followers))

        # insert unfollowers in db, remove followers from db
        if unfollowers_id_list:
            print("* unfollowers ids: {0}".format(len(unfollowers_id_list)))
            if len(unfollowers_id_list) <= 10:
                print("  {}".format(unfollowers_id_list))

            inserted_unfollowers = 0
            inserted_unfollowers = db_minions.insert_unfollowers(db_connection, unfollowers_id_list)
            print("- inserted database unfollowers: {0}".format(inserted_unfollowers))

            removed_followers = 0
            removed_followers = db_minions.remove_followers(db_connection, unfollowers_id_list)
            print("- removed database followers: {0}".format(removed_followers))

    # full update of follower records in db using api followers request
    else:
        twitter_followers = tweepy.Cursor(tweepy_api.followers, user_id=twitter_user.id).items()

        updated_followers = 0
        inserted_followers = 0

        while True:
            try:
                follower = next(twitter_followers)
            except tweepy.TweepError as err:
                print("tweepy_api.followers cursor error: {0} (continue)".format(err))
                continue
            except StopIteration:
                break

            # if follower in db then update their db record
            if follower.id in db_id_list:
                updated_followers += db_minions.update_followers(db_connection, [follower])

                if follower.id in db_id_list:
                    db_id_list.remove(follower.id)
                else:
                    print("* trying remove follower {0} - not in db_id_list".format(follower.id))

            # if follower not in db then insert new follower
            else:
                print("+ inserting new follower: {0} - {1}".format(follower.id, \
                    follower.screen_name))
                inserted_followers += db_minions.insert_followers(db_connection, [follower])

            if follower.id in twitter_id_list:
                twitter_id_list.remove(follower.id)
            else:
                print("* trying remove follower {0} - not in twitter_id_list".format(follower.id))

        # if follower in db but not in api results add to unfollower list
        unfollower_id_list = db_id_list
        if unfollower_id_list:
            unfollower_id_list.sort()
            print("* ids in database not in 'tweepy_api.followers': " \
                  "{0}".format(len(unfollower_id_list)))

            if len(unfollower_id_list) <= 5:
                print("  {0}".format(unfollower_id_list))

        # spare followers - follower in api followers id results but not in api followers results
        if twitter_id_list:
            twitter_id_list.sort()
            print("* ids in 'tweepy_api.followers_ids' not in 'tweepy_api.followers': " \
                  "{0}".format(len(twitter_id_list)))

            if len(twitter_id_list) <= 5:
                print("  {0}".format(twitter_id_list))

            db_id_list = db_minions.get_follower_ids(db_connection)

            # get user objects for each spare follower
            spare_followers = api_minions.get_users(tweepy_api, twitter_id_list)

            for follower in spare_followers:
                if follower.id in db_id_list:
                    print("^ updating spare: {0} - {1}".format(follower.id, follower.screen_name))
                    updated_followers += db_minions.update_followers(db_connection, [follower])
                else:
                    print("+ inserting spare: {0} - {1}".format(follower.id, follower.screen_name))
                    inserted_followers += db_minions.insert_followers(db_connection, [follower])

                # if in spare follower list then not an unfollower
                if follower.id in unfollower_id_list:
                    unfollower_id_list.remove(follower.id)
                else:
                    print("* trying remove spare follower {0} " \
                          "- not in unfollower_id_list".format(follower.id))

        print("^ updated database followers: {0}".format(updated_followers))
        print("+ new followers inserted: {0}".format(inserted_followers))

        # *** test ***
        #test_ids = []
        #unfollower_id_list += test_ids

        # unfollowers
        if unfollower_id_list:
            inserted_unfollowers = db_minions.insert_unfollowers(db_connection, unfollower_id_list)
            print("- inserted database unfollowers: {0}".format(inserted_unfollowers))

            removed_followers = db_minions.remove_followers(db_connection, unfollower_id_list)
            print("- removed database followers: {0}".format(removed_followers))

    # end of updates path

    db_connection.close()

    print("end.")

if __name__ == '__main__':
    main()
