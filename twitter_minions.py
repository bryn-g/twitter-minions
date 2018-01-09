""" maintains a database of a twitter users followers and unfollowers. """

import os
import sys
import re
import textwrap
import argparse
import tweepy
import prettytable
import colorama
from colorama import Fore, Back, Style

import api_minions
import db_minions

VERSION = "0.2"

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
        """ add minion object to list, because reverse order results currently only getting first
            'self.list_size' number (for latest 'self.list_size' followers). """
        if self._count == self.list_size:
            return
            #self._count = 0

        self._minions[self._count] = minion_summary
        self._count += 1

class MinionSummary(object):
    """ summary data about a follower. """
    def __init__(self, prefix, user_id, screen_name, name, description=""):
        self.prefix = prefix
        self.user_id = user_id
        self.screen_name = "@{0}".format(screen_name)
        self.name = name
        self.description = description

        if str(self.description).strip() == "":
            self.description = "(no description)"

    def get_minion_summary(self):
        """ return formated output of object properties. """
        return "{0} - {1} - @{2} - {3} - {4}".format(self.prefix, self.user_id, \
                                               self.screen_name, self.name, self.description)

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

# accepts numeric id or twitter screen name (@name)
def valid_user_id(user_id):
    user_id = str(user_id)

    user_id_match = re.match(r'^@\w{1,15}$', user_id)

    if user_id_match or user_id.isdigit():
        return user_id
    else:
        msg = "must start with @, be alphanumeric and < 16 characters or be a numeric id."
        raise argparse.ArgumentTypeError(msg)

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

    #dbm.unfollower_ids = [follower_id
    #                      for follower_id in dbm.follower_ids
    #                      if follower_id not in apim.follower_ids]

    if dbm.unfollower_ids:
        dbm.insert_unfollowers(dbm.unfollower_ids)
        dbm.remove_followers(dbm.unfollower_ids)

def process_follower_ids(dbm, apim):
    """ performs database insertion of new followers as determined by comparing
        database ids and /followers/ids api results. prints a summary of new followers.

        * does not update followers records in the database. """

    new_follower_summary = MinionSummaryList()

    # new followers, id in list returned from api request but not in database
    dbm.new_follower_ids = []
    for follower_id in apim.follower_ids:
        if follower_id not in dbm.follower_ids:
            dbm.new_follower_ids.append(follower_id)

    #dbm.new_follower_ids = [follower_id
    #                        for follower_id in apim.follower_ids
    #                        if follower_id not in dbm.follower_ids]

    # insert new followers in database
    if dbm.new_follower_ids:

        #summary_faux_counter = copy.copy(apim.follower_ids_count)
        summary_faux_counter = apim.follower_ids_count

        # gets the user objects for new followers using api /users/show/:id request
        new_followers = apim.get_users(dbm.new_follower_ids)
        for follower in new_followers:
            #print("+ inserting new follower: {0} - @{1}".format(follower.id, \
            #    follower.screen_name), end='\r')
            dbm.insert_followers([follower])

            # dbm.inserted_followers
            minion = MinionSummary(summary_faux_counter, follower.id, \
                                   follower.screen_name, follower.name, follower.description)
            new_follower_summary.minions = minion

            summary_faux_counter -= 1

        # print summary of followers inserted into database
        if dbm.inserted_followers:
            print_follower_summary(new_follower_summary, Fore.GREEN + "+ new followers:", dbm.inserted_followers, Fore.GREEN)

def process_followers(dbm, apim):
    """ performs insertion of new followers and updating of existing followers database
        records. user objects from api /followers/list results are used to insert new and
        update existing followers records. user ids found in /followers/ids api results but
        not /followers/list results are called spares and added to the spares list. prints a
        summary of new followers.

        * updates followers records in the database. """

    new_follower_summary = MinionSummaryList()

    # decrementing list
    spare_follower_ids = list(apim.follower_ids)

    if apim.follower_ids_count:
        # max 200 followers per request
        calc_reqs_value = int(apim.follower_ids_count) / 200
        calc_reqs_string = "* est. {0}{1} requests{2}. (limit of 15 requests " \
            "per 15 minutes)".format(Fore.MAGENTA, int(round(calc_reqs_value)) if calc_reqs_value > 1 \
            else "< 1", colorama.Fore.WHITE)
        print(calc_reqs_string)

        # if will take more than the request limit for 15 mins
        if calc_reqs_value >= 15:
            #calc_reqs_value = int(math.ceil(calc_reqs_value / 15.0)) * 15 # rounds up nearest 15
            calc_reqs_value = calc_reqs_value - (calc_reqs_value%15) # rounds down nearest 15
            print("* operation is likely to take {0}~{1} minutes.".format(Fore.MAGENTA, calc_reqs_value))
            calc_reqs = input("  do you wish to continue? (y/n): ")

            if calc_reqs.lower().strip() != "y":
                print("* exiting.")
                dbm.close_connection()
                sys.exit();

    api_followers = tweepy.Cursor(apim.api.followers, user_id=apim.user.id, count=200).items()

    #summary_faux_counter = copy.copy(apim.follower_ids_count)
    summary_faux_counter = apim.follower_ids_count

    iteration_counter = 0

    while True:
        try:
            follower = next(api_followers)
        except tweepy.TweepError as err:
            print("tweepy_api.followers cursor error: {0} (continue)".format(err))
            continue
        except StopIteration:
            break

        iteration_counter += 1

        # if follower in database then update their database record
        if follower.id in dbm.follower_ids:
            dbm.update_followers([follower])

        # if follower not in database then insert new follower
        else:
            #print("+ new follower: {0} - @{1}".format(follower.id, \
            #    follower.screen_name), end='\r') # end='\r'
            dbm.insert_followers([follower])

            # dbm.inserted_followers
            minion = MinionSummary(summary_faux_counter, follower.id, \
                                   follower.screen_name, follower.name, follower.description)
            new_follower_summary.minions = minion

            summary_faux_counter -= 1

        # eliminate follower from spare followers list
        if follower.id in spare_follower_ids:
            spare_follower_ids.remove(follower.id)
        else:
            # so id in /followers but not /follower_ids - unusual but happens sometimes
            print("* trying remove follower {0} - not in spare_follower_ids".format(follower.id))

    pad_to = 22
    print("{0:<{1}s}{2}{3}".format("followers (api list):", pad_to, Fore.GREEN, iteration_counter))

    # print summary of followers inserted into database
    if dbm.inserted_followers:
        print_follower_summary(new_follower_summary, Fore.GREEN + "+ new followers:", dbm.inserted_followers, Fore.GREEN)

    # remainder user ids in spare_follower_ids are spare followers
    if spare_follower_ids:
        process_spare_followers(dbm, apim, spare_follower_ids)

def process_spare_followers(dbm, apim, spare_follower_ids):
    """ retrieves user objects for each spare follower and inserts a new follower or updates
        the follower record depending on if their id is in the database. prints a summary
        of new and updated followers. """

    spare_follower_summary = MinionSummaryList()

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

        minion = MinionSummary(prefix, follower.id, follower.screen_name, follower.name, follower.description)
        spare_follower_summary.minions = minion

    # print summary of spare followers updated or inserted into database
    #title = "^ spare ids in '/followers/ids' not in '/followers/list':"
    title = Fore.GREEN + "* spare ids in '/followers/ids' not in '/followers/list':"
    print_follower_summary(spare_follower_summary, title, len(spare_follower_ids), Fore.GREEN)

def format_summary_table_row(index, row, table_color):
    #minion_description = textwrap.fill(minion.description, 60)

    minion_prefix, minion_screen_name, minion_name, minion_description = row

    text_color = ["", ""]
    if not index%2:
        text_color = [table_color, Style.RESET_ALL]

    minion_prefix = "{0}{1}{2}".format(text_color[0], minion_prefix, text_color[1])
    minion_screen_name = "{0}{1}{2}".format(text_color[0], minion_screen_name, text_color[1])

    minion_name = "{0}{1}{2}{3}".format(text_color[0], row[2][:24], ".." if len(row[2])>=24 else "", text_color[1])

    minion_description = ""
    minion_description_lines = textwrap.wrap(row[3], 60)
    for line in minion_description_lines:
        minion_description += text_color[0] + line + text_color[1] + "\n"

    if minion_description[-1:] is "\n":
        minion_description = minion_description[:-1]

    return [minion_prefix, minion_screen_name, minion_name, minion_description]

# accepts MinionSummaryList.minions dictionary
def print_follower_summary(minions_summary, title, num_followers, table_color):
    """ print a table of summary data about followers. """

    last_followers_txt = ""
    if num_followers > minions_summary.list_size:
        last_followers_txt = "(last {0})".format(minions_summary.list_size)
    print("{0} {1} {2}".format(title, num_followers, last_followers_txt))

    minion_table = prettytable.PrettyTable(["index", "screen name", "name", "description"], header=False) # hrules=True
    minion_table.align = "l"

    for index, minion in sorted(minions_summary.minions.items()):
        if minion:
            row = format_summary_table_row(index, [minion.prefix, minion.screen_name, minion.name, minion.description], table_color)

            #minion_table.add_row([minion.prefix, minion.screen_name, minion_name, minion_description])
            minion_table.add_row(row)

    #minion_table.sortby = "index"

    print(minion_table)

def print_unfollowers(dbm):
    """ formats captured data about unfollowers into a standard minions summary format.
        prints a summary of unfollowers. """

    if dbm.unfollowers:
        unfollower_summary = MinionSummaryList()

        for unfollower in dbm.unfollowers:
            # removed @ from screen name
            minion = MinionSummary(unfollower['i'], unfollower['user_id'], \
                                   "{0}".format(unfollower['user_screen_name']), \
                                   unfollower['user_name'], unfollower['user_time_found'])
            unfollower_summary.minions = minion

        print_follower_summary(unfollower_summary, Fore.CYAN + "- unfollowers:", len(dbm.unfollowers), Fore.CYAN)

def print_user_summary(user):
    """ prints a table with some data about the twitter user. accepts a user object. """

    ratio = 0
    if user.friends_count > 0:
        ratio = float(user.followers_count) / float(user.friends_count)

    pad_to = 11
    print("{0:<{1}s}{2}@{3}".format("user:", pad_to, Fore.MAGENTA, user.screen_name))
    print("{0:<{1}s}{2}".format("name:", pad_to, user.name))
    print("{0:<{1}s}{2}.sqlite".format("db:", pad_to, user.id))
    print("{0:<{1}s}{2}{3}".format("friends:", pad_to, Fore.YELLOW, user.friends_count))
    print("{0:<{1}s}{2}{3}".format("followers:", pad_to, Fore.GREEN, user.followers_count))
    print("{0:<{1}s}{2}{3:.2f}".format("ratio:", pad_to, Fore.WHITE if ratio < 1 else Fore.GREEN, ratio))
    print()

def print_stats(dbm):
    """ prints a summary about processing from DBMinions processing counters. """

    pad_to = 19
    print()
    print("{0:<{1}s}{2}{3}".format("new followers:", pad_to, Fore.GREEN, dbm.inserted_followers))
    print("{0:<{1}s}{2}{3}".format("updated followers:", pad_to, Fore.YELLOW, dbm.updated_followers))
    print("{0:<{1}s}{2}{3} ({4})".format("unfollowers:", pad_to, Fore.CYAN, dbm.removed_followers, \
                                         dbm.inserted_unfollowers))

def print_art():
    print("{0}twitter-_  _  ___  _  __   .___   ___\n" \
             "/  _ ` _ `(_)/ _ `(_)/ _`\/' _ `/',__)\n" \
             "| ( | | ) | | ( ) | ( (_) | ( ) \\__, \\\n" \
             "|_| |_| |_(_(_| (_(_`\___/(_| (_(____/ {1}v{2}\n".format(Fore.CYAN, Fore.YELLOW, VERSION))

def main():
    """ retrieves, processes and databases a users followers. """

    colorama.init(autoreset=True)

    print_art()

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

    user_obj = apim.get_users([user_args.user])
    if user_obj:
        apim.user = user_obj[0]
    else:
        print("* unable to retrieve user: {0}".format(user_args.user))
        sys.exit()

    print_user_summary(apim.user)

    dbm = db_minions.DBMinions(get_user_database_path(apim.user.id))

    if not dbm.connection:
        print("* unable to make a database connection: {0}".format(dbm.path))
        sys.exit()

    pad_to = 22
    # db follower ids
    dbm.get_follower_ids()
    print("{0:<{1}s}{2}{3}".format("followers (db):", pad_to, Fore.GREEN, dbm.follower_ids_count))

    # api follower ids
    apim.get_follower_ids()
    print("{0:<{1}s}{2}{3}".format("followers (api ids):", pad_to, Fore.GREEN, apim.follower_ids_count))

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
    print_stats(dbm)

    dbm.close_connection()
    print("end.")

if __name__ == '__main__':
    main()
