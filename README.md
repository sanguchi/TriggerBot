# TriggerBot
Python 2.7/3.5 Bot for Telegram. 

#### Setup:
##### Install libraries:
Run `sudo pip install pyTelegramBotAPI` on your terminal.  
Then clone or Download & Unzip.  
Just run `TriggerBot.py` or `TriggerBot_old.py`  

##### TriggerBot.py:
-This version saves triggers for each group separately.

##### TriggerBot_old.py:
-This version saves triggers globally.

##### TriggerBotTornado.py:
-Runs on top of a tornado webserver.  
_Requires tornado._
> `sudo pip install tornado`

##### TriggerBotSqlite.py: 
-Runs using Sqlite as database engine.  
_Requires peewee._
> `sudo pip install peewee`

**SSL Certificate:**  
It uses [Ngrok](https://ngrok.com/) to get a custom url.
Simply launch ngrok first:
> `ngrok http -bind-tls=true 8888`

then start the script.
