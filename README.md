# TriggerBot
Python 2.7/3.5 Bot for Telegram. 

#### Setup:
Run `sudo pip install -r requirements.txt` on your terminal.    
Then just run one of the following: 

##### TriggerBot.py:
-This version saves triggers for each group separately.

##### TriggerBot_old.py:
-This version saves triggers globally.

##### TriggerBotTornado.py:
-Same as TriggerBot.py, but runs on top of a tornado webserver.  


##### TriggerBotMarkov.py:
-This version does not store triggers, it stores messages and tries to generate sentences.

##### TriggerBotSqlite.py:
-Same as TriggerBot.py, but uses a sqlite database to store triggers.
