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
-Runs on top of a tornado webserver.  
_Requires tornado._
> `sudo pip install tornado`

##### TriggerBotMarkov.py:
-Requires [Markovify](https://github.com/jsvine/markovify), [Peewee](https://pypi.org/project/peewee/) and [Python-decouple](https://pypi.org/project/python-decouple/) libraries.  
> `sudo pip install markovify peewee python-decouple`

##### TriggerBotSqlite.py:
-Runs using Sqlite as database engine.  
_Requires peewee._  
> `sudo pip install peewee`
