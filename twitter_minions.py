""" maintains a database of a twitter users followers and unfollowers. """

import os
import sys
import argparse
import json
import sqlite3
import tweepy
import prettytable

def check_sqlite_database(file_path):
    """ checks if the sqlite database exists and gives the
    option to create one if it doesn't.
    """

    file_path = str(file_path)

    if not os.path.isfile(file_path):
        print("* database '" + file_path + "' does not exist.")
        # raw_input
        create_database = input("do you wish to create it? (y/n): ")

        create_database = "{0}".format(create_database)
        if create_database.lower().strip() == "y":
            create_follower_database(file_path)
        else:
            print("* no database. exiting.")
            sys.exit()

def valid_twitter_user(user_id):
    """ passes a twitter user identifier through a filter and raises an
    exception if it is not valid.
    """

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

def get_follower_ids(tweepy_api, uid):
    """ returns an id list of the users followers. """

    follower_ids = []
    follower_id_pages = tweepy.Cursor(tweepy_api.followers_ids, user_id=uid,
                                      cursor=-1).pages()

    while True:
        try:
            follower_id_page = next(follower_id_pages)
        except tweepy.TweepError as err:
            print(err)
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

def get_users(tweepy_api, follower_ids):
    """ returns a list of users objects for followers ids. """

    followers = []
    for uid in follower_ids:
        try:
            user = tweepy_api.get_user(uid)

            followers.append(user)
        except tweepy.TweepError as err:
            print(err)
            continue

    return followers

def create_sqlite3_connection(db_file):
    """ creates a connection object for a sqlite database. """

    try:
        db_conn = sqlite3.connect(db_file)
        return db_conn
    except sqlite3.IntegrityError as err:
        print(err)

    return None

def get_db_follower_ids(db_connection):
    """ gets a list of follower ids from the database. """

    sql_followers = "SELECT user_id FROM followers"

    db_id_list = []
    try:
        db_cursor = db_connection.cursor()
        db_cursor.execute(sql_followers)
        all_rows = db_cursor.fetchall()

        for row in all_rows:
            # stopped working for 2.7 after unicode changes
            #db_id_list.append(row[str('user_id')])
            #db_id_list.append(row[0])
            db_id_list.append(row['user_id'])

    except sqlite3.IntegrityError as err:
        print(err)

    #exit()
    return db_id_list

def insert_followers(db_connection, followers_list):
    """ inserts a list of followers into the database. """

    sql_insert = "INSERT INTO followers (user_id, user_name, user_screen_name, " \
        "user_time_found, user_json) VALUES (?, ?, ?, datetime('now'), ?);"

    inserted_followers = 0

    try:
        db_cursor = db_connection.cursor()

        for user in followers_list:

            db_cursor.execute(sql_insert, (user.id, user.name, user.screen_name,
                                           json.dumps(user._json)))

            inserted_followers += 1

        db_connection.commit()

    except sqlite3.IntegrityError as err:
        print("* database insert error - {0} {1}".format(user.id, user.screen_name))
        print(err)

    return inserted_followers

def update_followers(db_connection, followers_list):
    """ updates a list of followers in the database. """

    sql_update = "UPDATE followers SET user_name=?, user_screen_name=?, " \
                 "user_time_updated=datetime('now'), user_json=? WHERE user_id=?;"

    updated_followers = 0

    try:
        db_cursor = db_connection.cursor()

        for user in followers_list:
            db_cursor.execute(sql_update, (user.name, user.screen_name, json.dumps(user._json),
                                           user.id))
            updated_followers += 1

        db_connection.commit()

    except sqlite3.IntegrityError as err:
        print("* database update error - {0} {1}".format(user.id, user.screen_name))
        print(err)

    return updated_followers

def remove_followers(db_connection, followers_id_list):
    """ removes followers from the followers table. """

    placeholders = ', '.join(['?']*len(followers_id_list))
    sql_remove = "DELETE FROM followers WHERE user_id IN ({0});".format(placeholders)

    removed_followers = 0

    try:
        db_cursor = db_connection.cursor()

        db_cursor.execute(sql_remove, followers_id_list)
        db_connection.commit()

        removed_followers = len(followers_id_list)

    except sqlite3.IntegrityError as err:
        print(err)

    return removed_followers

def insert_unfollowers(db_connection, followers_id_list):
    """ copies followers from the followers table into the unfollowers table. """

    placeholders = ', '.join(['?']*len(followers_id_list))
    sql_unfollowers = "SELECT * FROM followers WHERE user_id IN ({0});".format(placeholders)

    inserted_unfollowers = 0

    # *** test ***
    #print("un- followers_id_list: {}".format(followers_id_list))
    #print("placeholders: {}".format(placeholders))
    #print("sql_unfollowers: {}".format(sql_unfollowers))

    try:
        db_cursor = db_connection.cursor()
        db_cursor.execute(sql_unfollowers, followers_id_list)
        all_rows = db_cursor.fetchall()

        for row in all_rows:
            #print("row: {0}".format(row))
            sql_insert = "INSERT INTO unfollowers (user_id, user_name, user_screen_name, " \
                         "user_time_found, user_time_lost) VALUES (?, ?, ?, ?, datetime('now'));"

            db_cursor.execute(sql_insert, [row['user_id'], row['user_name'],
                                           row['user_screen_name'], row['user_time_found']])

            inserted_unfollowers += 1
            print("- unfollower: {0} - {1} - {2}".format(row['user_id'], row['user_name'], \
                row['user_screen_name']))

        db_connection.commit()

    except sqlite3.IntegrityError as err:
        print(err)

    return inserted_unfollowers

def create_follower_database(db_name):
    """ creates a new sqlite database with followers and unfollowers tables. """

    db_connection = sqlite3.connect(db_name)
    db_cursor = db_connection.cursor()

    sql_create_followers_table = "CREATE TABLE 'followers' (" \
        "'user_id' INTEGER PRIMARY KEY  NOT NULL," \
        "'user_name' VARCHAR," \
        "'user_screen_name' VARCHAR DEFAULT (null)," \
        "'user_time_found' DATETIME DEFAULT (null)," \
        "'user_time_updated' DATETIME DEFAULT (CURRENT_TIMESTAMP)," \
        "'user_json' TEXT);"

    sql_create_unfollowers_table = "CREATE TABLE 'unfollowers' (" \
        "'id' INTEGER PRIMARY KEY  NOT NULL," \
        "'user_id' INTEGER," \
        "'user_name' VARCHAR," \
        "'user_screen_name' VARCHAR," \
        "'user_time_found' DATETIME," \
        "'user_time_lost' DATETIME DEFAULT (CURRENT_TIMESTAMP));"

    try:
        db_cursor.execute(sql_create_followers_table)
        db_cursor.execute(sql_create_unfollowers_table)
    except sqlite3.IntegrityError as err:
        print(err)
        sys.exit()

    db_connection.commit()

    print("* created {0}".format(db_name))

    db_connection.close()

def get_arguments():
    """ parse and return user supplied arguments. """

    parser = argparse.ArgumentParser(description='maintains a database of a twitter users ' \
                                     'followers and unfollowers.')

    parser.add_argument('-u', '--user', help="twitter user @name or numeric id", \
                        type=valid_twitter_user, required=True)

    #parser.add_argument('-nu', '--noupdates', help="do not make a tweepy_api.followers " \
    #                    "request that updates user data for all database follower records",
    #                    required=False, action='store_true')

    parser.add_argument('-upd', '--update', help="make a tweepy_api.followers " \
                        "request that updates user data for all database follower records",
                        required=False, action='store_true')

    args = parser.parse_args()

    return args

def print_user(twitter_user):
    """ print some simple information about a twitter user. """

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

def main():
    """ maintains a sqlite3 database of an individual twitter users followers and unfollowers
    with timestamps. the database has two tables 'followers' and 'unfollowers'.
    """

    # twitter api application keys
    app_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', 'None')
    app_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', 'None')
    app_access_key = os.environ.get('TWITTER_ACCESS_KEY', 'None')
    app_access_secret = os.environ.get('TWITTER_ACCESS_SECRET', 'None')

    user_args = get_arguments()

    try:
        auth = tweepy.OAuthHandler(app_consumer_key, app_consumer_secret)
        auth.set_access_token(app_access_key, app_access_secret)

        tweepy_api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, \
            compression=True)
    except tweepy.TweepError as err:
        print("tweepy error: {0}".format(err))
        sys.exit()

    twitter_user = None

    # print some information about the twitter user that script is collecting followers for
    # note that this uses a single /users/show/:id API request if counting resources
    try:
        twitter_user = tweepy_api.get_user(user_args.user)
    except tweepy.TweepError as err:
        print("tweepy.get_user error: {0}".format(err))
        sys.exit()

    print_user(twitter_user)

    # db name is the same as the twitter user id with sqlite extension
    user_database_name = "{0}.sqlite".format(twitter_user.id)
    print("* user database: {0}".format(user_database_name))

    # db resides in same directory as the script
    current_directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    user_database_path = "{0}/{1}".format(current_directory, user_database_name)

    # checks if the db file exists (but not validity)
    check_sqlite_database(user_database_path)

    # create a connection to the db
    db_connection = create_sqlite3_connection(user_database_path)
    db_connection.row_factory = sqlite3.Row

    # list of twitter user ids for followers in the db
    db_id_list = get_db_follower_ids(db_connection)

    print("* followers in database: {0}".format(len(db_id_list)))

    # list of twitter user ids returned from tweepy followers_ids api request
    twitter_id_list = get_follower_ids(tweepy_api, twitter_user.id)

    print("* twitter 'tweepy_api.followers_ids': {0}".format(len(twitter_id_list)))

    #if user_args.noupdates and len(db_id_list) < 1:
    if not user_args.update and len(db_id_list) < 1:
        print("* no records in the database. please collect some followers by using the " \
            "'-upd' updates option or select 'y'.")
        # raw_input
        collect_followers = input("do you wish to collect followers now? (y/n): ")

        collect_followers = "{0}".format(collect_followers)
        if collect_followers.lower().strip() == "y":
            #user_args.noupdates = False
            user_args.update = True
        else:
            print("* no database followers. exiting.")
            db_connection.close()
            sys.exit()

    # if 'no updates' option then compare db_id_list to twitter_id_list, insert new followers
    # and remove unfollowers but don't update existing follower records in db.

    if not user_args.update:
    #if user_args.noupdates:

        # unfollowers
        unfollowers_id_list = []
        for db_follower_id in db_id_list:
            if db_follower_id not in twitter_id_list:
                unfollowers_id_list.append(db_follower_id)

        # new followers
        new_followers_id_list = []
        for tweepy_follower_id in twitter_id_list:
            if tweepy_follower_id not in db_id_list:
                new_followers_id_list.append(tweepy_follower_id)

        if new_followers_id_list:
            print("* new followers ids: {0}".format(len(new_followers_id_list)))
            #if len(new_followers_id_list) <= 10:
            #    print("  " + str(new_followers_id_list))

            inserted_followers = 0
            new_followers = get_users(tweepy_api, new_followers_id_list)
            for follower in new_followers:
                print("+ inserting new follower: {0} - {1}".format(follower.id, \
                    follower.screen_name))
                inserted_followers += insert_followers(db_connection, [follower])

            print("+ new followers inserted: {0}".format(inserted_followers))

        if unfollowers_id_list:
            print("* unfollowers ids: {0}".format(len(unfollowers_id_list)))
            if len(unfollowers_id_list) <= 10:
                print("  {}".format(unfollowers_id_list))

            inserted_unfollowers = 0
            inserted_unfollowers = insert_unfollowers(db_connection, unfollowers_id_list)
            print("- inserted database unfollowers: {0}".format(inserted_unfollowers))

            removed_followers = 0
            removed_followers = remove_followers(db_connection, unfollowers_id_list)
            print("- removed database followers: {0}".format(removed_followers))

    # end 'no updates' option path
    # -upd or updates path
    else:
        # start of updates path using 'tweepy_api.followers' insert new followers and removes
        # unfollowers but also updates all existing follower records in the db.

        twitter_followers = tweepy.Cursor(tweepy_api.followers, user_id=twitter_user.id).items()

        follower = None
        updated_followers = 0
        inserted_followers = 0

        while True:
            try:
                follower = next(twitter_followers)
            except tweepy.TweepError as err:
                print("tweepy_api.followers cursor error: {0} (continue)".format(err))
                #follower = next(twitter_followers)
                continue
            except StopIteration:
                break

            # update db for existing follower
            if follower.id in db_id_list:
                #print("^ updating: " + str(follower.id) + " - " + follower.screen_name)
                updated_followers += update_followers(db_connection, [follower])

                if follower.id in db_id_list:
                    db_id_list.remove(follower.id)
                else:
                    print("* trying remove follower {0} - not in db_id_list".format(follower.id))
            else:
                # insert new follower into db
                print("+ inserting new follower: {0} - {1}".format(follower.id, \
                    follower.screen_name))
                inserted_followers += insert_followers(db_connection, [follower])

            if follower.id in twitter_id_list:
                twitter_id_list.remove(follower.id)
            else:
                print("* trying remove follower {0} - not in twitter_id_list".format(follower.id))

        unfollower_id_list = db_id_list
        if unfollower_id_list:
            unfollower_id_list.sort()
            print("* ids in database not in 'tweepy_api.followers': " \
                  "{0}".format(len(unfollower_id_list)))

            if len(unfollower_id_list) <= 5:
                print("  {0}".format(unfollower_id_list))

        # deal with spare followers missing from 'tweepy_api.followers' result
        if twitter_id_list:
            twitter_id_list.sort()
            print("* ids in 'tweepy_api.followers_ids' not in 'tweepy_api.followers': " \
                  "{0}".format(len(twitter_id_list)))

            if len(twitter_id_list) <= 5:
                print("  {0}".format(twitter_id_list))

            db_id_list = get_db_follower_ids(db_connection)
            spare_followers = get_users(tweepy_api, twitter_id_list)

            for follower in spare_followers:
                if follower.id in db_id_list:
                    print("^ updating spare: {0} - {1}".format(follower.id, follower.screen_name))
                    updated_followers += update_followers(db_connection, [follower])
                else:
                    print("+ inserting spare: {0} - {1}".format(follower.id, follower.screen_name))
                    inserted_followers += insert_followers(db_connection, [follower])

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
            inserted_unfollowers = insert_unfollowers(db_connection, unfollower_id_list)
            print("- inserted database unfollowers: {0}".format(inserted_unfollowers))

            removed_followers = remove_followers(db_connection, unfollower_id_list)
            print("- removed database followers: {0}".format(removed_followers))

    # end of updates path

    db_connection.close()

    print("end.")

if __name__ == '__main__':
    main()
