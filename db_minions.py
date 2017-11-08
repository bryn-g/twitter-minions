""" handles the sqlite database operations """

import os
import json
import sqlite3

class DBMinions(object):
    """ minions sqlite3 database helper class. """

    def __init__(self, path):
        self._path = ""
        self._connection = None
        self._cursor = None

        self.path = path

        self._follower_ids = []

        self.unfollower_ids = []
        self.unfollowers = []

        self.new_follower_ids = []

        self.inserted_followers = 0
        self.updated_followers = 0
        self.removed_followers = 0
        self.inserted_unfollowers = 0

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

        if not os.path.isfile(self.path):
            print("* database '{0}' does not exist.".format(self.path))
            create_db = input("  do you wish to create it? (y/n): ")

            if create_db.lower().strip() == "y":
                self._create_database()
        else:
            self._create_connection()

    @property
    def connection(self):
        return self._connection

    @connection.setter
    def connection(self, value):
        self._connection = value

    @property
    def cursor(self):
        return self._cursor

    @cursor.setter
    def cursor(self, value):
        self._cursor = value

    @property
    def follower_ids(self):
        return self._follower_ids

    @follower_ids.setter
    def follower_ids(self, ids):
        self._follower_ids += ids

    @property
    def follower_ids_count(self):
        return len(self._follower_ids)

    @property
    def unfollower_ids_count(self):
        return len(self.unfollower_ids)

    @property
    def new_follower_ids_count(self):
        return len(self.new_follower_ids)

    def _create_database(self):
        self._create_connection()

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
            self.cursor.execute(sql_create_followers_table)
            self.cursor.execute(sql_create_unfollowers_table)

            self.connection.commit()

            print("* created {0}".format(self.path))
        except sqlite3.Error as err:
            print("create_database error: {0}".format(err))

    def _create_connection(self):
        try:
            self.connection = sqlite3.connect(self.path)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()

        except sqlite3.Error as err:
            print("create_connection error: {0}".format(err))

    def close_connection(self):
        self._connection.close()

    def get_follower_ids(self):
        sql_followers = "SELECT user_id FROM followers"

        self.follower_ids = []
        try:
            self.cursor.execute(sql_followers)
            all_rows = self.cursor.fetchall()

            for row in all_rows:
                self.follower_ids = [row['user_id']]

        except sqlite3.Error as err:
            print("dbm, error: {0}".format(err))

    def insert_followers(self, followers_list):
        sql_insert = "INSERT INTO followers (user_id, user_name, user_screen_name, " \
            "user_time_found, user_json) VALUES (?, ?, ?, datetime('now'), ?);"

        inserted_followers = 0
        try:
            for user in followers_list:
                self.cursor.execute(sql_insert, (user.id, user.name, user.screen_name,
                                                 json.dumps(user._json)))
                inserted_followers += 1

            self.connection.commit()

        except sqlite3.Error as err:
            print("* database insert error - {0} {1}".format(user.id, user.screen_name))
            print(err)

        self.inserted_followers += inserted_followers

    def update_followers(self, followers_list):
        sql_update = "UPDATE followers SET user_name=?, user_screen_name=?, " \
                     "user_time_updated=datetime('now'), user_json=? WHERE user_id=?;"

        updated_followers = 0
        try:
            for user in followers_list:
                self.cursor.execute(sql_update, (user.name, user.screen_name, json.dumps(user._json),
                                                 user.id))
                updated_followers += 1

            self.connection.commit()

        except sqlite3.Error as err:
            print("* database update error - {0} {1}".format(user.id, user.screen_name))
            print(err)

        self.updated_followers += updated_followers

    def remove_followers(self, followers_id_list):
        placeholders = ', '.join(['?']*len(followers_id_list))
        sql_remove = "DELETE FROM followers WHERE user_id IN ({0});".format(placeholders)

        removed_followers = 0
        try:
            self.cursor.execute(sql_remove, followers_id_list)
            self.connection.commit()

            removed_followers = len(followers_id_list)

        except sqlite3.Error as err:
            print("remove_followers error: {0}".format(err))

        self.removed_followers += removed_followers

    def insert_unfollowers(self, followers_id_list):
        placeholders = ', '.join(['?']*len(followers_id_list))
        sql_unfollowers = "SELECT * FROM followers WHERE user_id IN ({0});".format(placeholders)

        inserted_unfollowers = 0
        try:
            self.cursor.execute(sql_unfollowers, followers_id_list)
            all_rows = self.cursor.fetchall()

            for row in all_rows:
                sql_insert = "INSERT INTO unfollowers (user_id, user_name, user_screen_name, " \
                             "user_time_found, user_time_lost) VALUES (?, ?, ?, ?, datetime('now'));"

                self.cursor.execute(sql_insert, [row['user_id'], row['user_name'],
                                                 row['user_screen_name'], row['user_time_found']])

                inserted_unfollowers += 1
                self.unfollowers.append({"i": inserted_unfollowers, "user_id": row['user_id'], "user_screen_name": row['user_screen_name'], \
                                         "user_name": row['user_name'], "user_time_found": row['user_time_found']})

            self.connection.commit()

        except sqlite3.Error as err:
            print("insert_unfollowers error: {0}".format(err))

        self.inserted_unfollowers += inserted_unfollowers
