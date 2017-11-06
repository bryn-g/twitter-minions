import sys
import json
import sqlite3

def create_database(db_name):
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
        db_connection.commit()
    except sqlite3.Error as err:
        print("create_database error: {0}".format(err))
        sys.exit()

    print("* created {0}".format(db_name))
    db_connection.close()

def create_connection(db_file):
    try:
        db_connection = sqlite3.connect(db_file)
        db_connection.row_factory = sqlite3.Row

        return db_connection

    except sqlite3.Error as err:
        print("create_connection error: {0}".format(err))

    return None

def get_follower_ids(db_connection):
    sql_followers = "SELECT user_id FROM followers"

    db_id_list = []
    try:
        db_cursor = db_connection.cursor()
        db_cursor.execute(sql_followers)
        all_rows = db_cursor.fetchall()

        for row in all_rows:
            db_id_list.append(row['user_id'])

    except sqlite3.Error as err:
        print("get_follower_ids error: {0}".format(err))

    return db_id_list

def insert_followers(db_connection, followers_list):
    sql_insert = "INSERT INTO followers (user_id, user_name, user_screen_name, " \
        "user_time_found, user_json) VALUES (?, ?, ?, datetime('now'), ?);"

    inserted_followers = 0
    try:
        db_cursor = db_connection.cursor()

        # followers list contains user objects
        for user in followers_list:
            db_cursor.execute(sql_insert, (user.id, user.name, user.screen_name,
                                           json.dumps(user._json)))
            inserted_followers += 1

        db_connection.commit()

    except sqlite3.Error as err:
        print("* database insert error - {0} {1}".format(user.id, user.screen_name))
        print(err)

    return inserted_followers

def update_followers(db_connection, followers_list):
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

    # IntegrityError
    except sqlite3.Error as err:
        print("* database update error - {0} {1}".format(user.id, user.screen_name))
        print(err)

    return updated_followers

def remove_followers(db_connection, followers_id_list):
    placeholders = ', '.join(['?']*len(followers_id_list))
    sql_remove = "DELETE FROM followers WHERE user_id IN ({0});".format(placeholders)

    removed_followers = 0
    try:
        db_cursor = db_connection.cursor()

        db_cursor.execute(sql_remove, followers_id_list)
        db_connection.commit()

        removed_followers = len(followers_id_list)

    except sqlite3.Error as err:
        print("remove_followers error: {0}".format(err))

    return removed_followers

def insert_unfollowers(db_connection, followers_id_list):
    placeholders = ', '.join(['?']*len(followers_id_list))
    sql_unfollowers = "SELECT * FROM followers WHERE user_id IN ({0});".format(placeholders)

    # *** test ***
    #print("un- followers_id_list: {}".format(followers_id_list))
    #print("placeholders: {}".format(placeholders))
    #print("sql_unfollowers: {}".format(sql_unfollowers))

    inserted_unfollowers = 0
    try:
        db_cursor = db_connection.cursor()
        db_cursor.execute(sql_unfollowers, followers_id_list)
        all_rows = db_cursor.fetchall()

        for row in all_rows:
            sql_insert = "INSERT INTO unfollowers (user_id, user_name, user_screen_name, " \
                         "user_time_found, user_time_lost) VALUES (?, ?, ?, ?, datetime('now'));"

            db_cursor.execute(sql_insert, [row['user_id'], row['user_name'],
                                           row['user_screen_name'], row['user_time_found']])

            inserted_unfollowers += 1
            print("- unfollower: {0} - {1} - {2}".format(row['user_id'], row['user_name'], \
                row['user_screen_name']))

        db_connection.commit()

    except sqlite3.Error as err:
        print("insert_unfollowers error: {0}".format(err))

    return inserted_unfollowers
