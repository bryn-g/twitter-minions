""" twitter api rate limit data using tweepy wrapper. """

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import datetime
import tweepy
import prettytable

def print_rate_limits(tweepy_api):
    """ prints a table of rate limit or resource information. """

    try:
        api_rate_limit = tweepy_api.rate_limit_status()

    except tweepy.TweepError as err:
        print "tweepy_api.rate_limit_status error: " + str(err.message)
        return

    rate_table = prettytable.PrettyTable(["twitter api resource", "reset", "limit", "remaining"])
    rate_table.align = "l"

    for attr, value in api_rate_limit['resources'].iteritems():
        for sattr, svalue in api_rate_limit['resources'][attr].iteritems():

            # only print resources that are not at limit or have been recently used
            if svalue['limit'] != svalue['remaining']:
                reset = svalue['reset']
                # convert from unix timestamp to readable date time
                utc_time = datetime.datetime.utcfromtimestamp(reset)
                reset = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")

                limit = str(svalue['limit'])
                remaining = str(svalue['remaining'])

                rate_table.add_row([str(sattr), reset, limit, remaining])

    print rate_table

def main():
    """ twitter api rate limit information. """

    app_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', 'None')
    app_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET', 'None')
    app_access_key = os.environ.get('TWITTER_ACCESS_KEY', 'None')
    app_access_secret = os.environ.get('TWITTER_ACCESS_SECRET', 'None')

    auth = tweepy.OAuthHandler(app_consumer_key, app_consumer_secret)
    auth.set_access_token(app_access_key, app_access_secret)

    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True,
                     compression=True)

    print_rate_limits(api)

if __name__ == '__main__':
    main()
