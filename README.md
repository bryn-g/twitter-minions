# twitter-minions
Maintains simple ad hoc database of a twitter users followers and unfollowers. Data is collected using the python [tweepy](http://www.tweepy.org/) wrapper for the [twitter api](https://developer.twitter.com/en/docs/api-reference-index) and stored in a sqlite3 database.

This project was created to figure out who has unfollowed or followed me when I notice changes in my twitter follower count. Additional data such as follower json is stored as it may be useful for some analytics in the future.

Unfollowers and followers are determined by comparing current followers to the database records. People who both follow and then unfollow in-between instances of running the script will not be captured in the database.

### Requirements

```python (3.6)``` ```sqlite3 (2.6)```
```tweepy (3.5.0)``` ```prettytable (0.7.2)```

### Usage

```
usage: twitter_minions.py [-h] -u USER [-upd]

maintains a database of a twitter users followers and unfollowers.

optional arguments:
  -h, --help            show this help message and exit
  -u USER, --user USER  twitter user @name or numeric id
  -upd, --update        make a tweepy_api.followers request that updates user
                        data for all database follower records
```

### Database

A database will be created per user in the scripts local directory and named after their twitter user id so that it is unique.
```sh
$ python twitter-minions.py -u @ladygaga
```
```
+-----------+----------+---------+-----------+--------+
| user      | id       | friends | followers | ratio  |
+-----------+----------+---------+-----------+--------+
| @ladygaga | 14230524 | 128746  | 72253874  | 561.21 |
+-----------+----------+---------+-----------+--------+
* user database: 14230524.sqlite
* database 'twitter-minions/14230524.sqlite' does not exist.
do you wish to create it? (y/n): y
* created 14230524.sqlite
```
The database will have two tables ```followers``` and ```unfollowers``` that store follower records. Records data is derived from the twitter api user objects returned from either ```tweepy.followers``` or ```tweepy.get_user``` api requests. Records also have timestamps to track when a follower was added, updated or unfollowed.

#### ```followers``` table

| field | description
| :----- | :----- |
| user_id | unique twitter id of the follower
| user_name | twitter users full name in profile
| user_screen_name | twitter users screen name, their @name
| user_time_found | time that the follower record was entered into the table
| user_time_updated | time that the follower record data was last updated
| user_json | raw json about the follower from the api user json attribute

#### ```unfollowers``` table

| field | description
| :----- | :----- |
| id | unique unfollow record id
| user_id | twitter id of the follower
| user_name | twitter users full name in profile
| user_screen_name | twitter users screen name, their @name
| user_time_found | time that the follower record was entered into the table
| user_time_lost | time that the follower became an unfollower

### Processing

If new followers are found the script inserts their data into the ```followers``` table. If unfollowers are found their follower records are copied into the ```unfollowers``` table and removed from the ```followers``` table.

If the ```--update``` option is used then user objects will be retrieved for all users in the ```followers``` table of the database and all fields except ```user_id``` and ```user_time_found``` updated per record. This means the database will have an updated data record for a follower as of the last time the script was run.

The first time the script is run for a user it will need to do a full update to populate the database. This can be very slow and may require many lengthy pauses whilst the twitter api rate limits reset.

After the initial run the he default id only processing is available that only requests user objects for new followers. In this case the follower database records will not reflect recent changes that have occurred since the last ```update```.
```ruby
end.
```
