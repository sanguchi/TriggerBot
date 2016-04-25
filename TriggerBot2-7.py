# -*- coding: utf-8 -*-
import telebot
import json
from os.path import exists
import time

#PYTHON 2.7 VERSION.
#Git Repo:
#https://github.com/sanguchi/TriggerBot

##GLOBAL VARIABLES.
#Bot owner, replace with your user_id.
owner = 59802458
#Variable to hold all Triggers.
triggers = {}
#Separator character.
separator = '/'
#Check if a message is too old.
def is_recent(m):
    return (time.time() - m.date) < 60
##END OF GLOBAL VARIABLES SECTION.

##TRIGGERS SECTION
#Check if Triggers file exists and load, if not, is created.
if exists('triggers.json'):
    with open('triggers.json') as f:
        triggers = json.load(f)
    print('Triggers file loaded.')
else:
    with open('triggers.json', 'w') as f:
        json.dump({}, f)

#Function to save triggers list to a file.
def save_triggers():
    with open('triggers.json', 'w') as f:
        json.dump(triggers, f, indent=4)
    print('Triggers file saved.')
#Function to get triggers list for a group.
def get_triggers(group_id):
    if(str(group_id) in triggers.keys()):
        return triggers[str(group_id)]
    else:
        return False

##END OF TRIGGERS SECTION

##BOT INIT SECTION.
token = ''

#Check if Token file exists, if not, create.
if exists('token.txt'):
    with open('token.txt') as f:
        token = f.readline().strip()
    print('Token Loaded')
else:
    token = raw_input('No token file detected, please paste or type here your token:\n> ')
    with open('token.txt', 'w') as f:
        f.write(token)  
    print('Token File saved.')

#Define a custom Listener to print messages to console.
def listener(messages):
    for m in messages:
        cid = m.chat.id
        name = m.from_user.first_name.encode('ascii', 'ignore').decode('ascii')
        if(m.content_type == 'text'):
            message_text = m.text.encode('ascii', 'ignore').decode('ascii')
        else:
            message_text = m.content_type
        print('{}[{}]:{}'.format(name, cid, message_text))

#Function to check if a message is too old(60 seconds) to answer.
def is_recent(m):
    return (time.time() - m.date) < 60
    
#Create Bot.
bot = telebot.TeleBot(token)
#Bot user ID.
bot_id = bot.get_me().id 
#Tell owner the bot has started.
bot.send_message(owner, 'Bot Started')            
#Set custom listener.
bot.set_update_listener(listener)

##END OF BOT INITIALIZATION SECTION.

##GLOBAL MESSAGES SECTION.
about_message = '''
Created by @Sanguchi in ~60 minutes :P
[Source Code on Github](https://github.com/sanguchi/TriggerBot/)
[Give me 5 Stars](https://telegram.me/storebot?start=TriggerResponseBot)
'''

help_message = '''
You need help!
Add Triggers: There are two ways.
1)/add <trigger> / <response>
Example:
/add hi / Hi! How're You?
Also works via reply.
[In Reply to Another Message]:
2)/add <trigger>
Delete Command:
/del <trigger>
Deletes a defined trigger, example:
/del hi
Others Commands:
/size
Returns size of triggers list.
/all
Show you all triggers.
/help
This message.
/source
Returns source code.
/solve <response>
Tries to resolve what trigger causes the given response, if exists.
Also works by reply:
Reply to any bot response with the command to get the trigger.
/about
About this bot.
'''
 
added_message = '''
New Trigger Created:
Trigger [{}]
Response [{}]
'''
##END OF GLOBAL MESSAGES SECTION.

##COMMAND IMPLEMENTATION SECTION.

@bot.message_handler(commands=['add'])
def add(m):
    if(not is_recent(m)):
        return
    if(m.reply_to_message):
        if(m.reply_to_message.text):
            if(len(m.reply_to_message.text.split()) < 2):
                bot.reply_to(m, 'Bad Arguments')
                return
            trigger_word = u'' + m.text.split(' ', 1)[1].strip()
            trigger_response = u'' + m.reply_to_message.text.strip()
        else:
            bot.reply_to(m, 'Only text triggers are supported.')
            return
    else:    
        if(len(m.text.split()) < 2):
            bot.reply_to(m, 'Bad Arguments')
            return
        if(m.text.find(separator, 1) == -1):
            bot.reply_to(m, 'Separator not found')
            return
        rest_text = m.text.split(' ', 1)[1]
        trigger_word = u'' + rest_text.split(separator)[0].strip().lower()
        trigger_response = u'' + rest_text.split(separator, 1)[1].strip()

    if(len(trigger_word) < 4):
        bot.reply_to(m, 'Trigger too short. [chars < 4]')
        return
    if(len(trigger_response) < 1):
        bot.reply_to(m, 'Invalid Response.')
        return
    if(m.chat.type in ['group', 'supergroup']):
        if(get_triggers(m.chat.id)):
            get_triggers(m.chat.id)[trigger_word] = trigger_response
        else:
            triggers[str(m.chat.id)] = {trigger_word : trigger_response}
        msg = u'' + added_message.format(trigger_word, trigger_response)
        bot.reply_to(m, msg)
        save_triggers()
    else:
        if(m.chat.id != owner):
            return

@bot.message_handler(commands=['del'])
def delete(m):
    if(not is_recent(m)):
        return
    if(len(m.text.split()) < 2):
        bot.reply_to(m, 'Bad Arguments')
        return
    del_text = m.text.split(' ', 1)[1].strip()
    if(m.chat.type in ['group', 'supergroup']):
        trg = get_triggers(m.chat.id)
        if(trg and del_text in trg.keys()):
            trg.pop(del_text)
            bot.reply_to(m, 'Trigger [{}] deleted.'.format(del_text))
            save_triggers()
        else:
            bot.reply_to(m, 'Trigger [{}] not found.'.format(del_text))

@bot.message_handler(commands=['size'])
def size(m):
    if(not is_recent(m)):
        return
    if(m.chat.type in ['group', 'supergroup']):
        trg = get_triggers(m.chat.id)
        if(trg):
            msg = 'Size of Triggers List = {}'.format(len(trg))
            bot.reply_to(m, msg)
        else:
            bot.reply_to(m, 'Size of Triggers List = 0')

@bot.message_handler(commands=['all'])
def all(m):
    if(not is_recent(m)):
        return
    if(m.chat.type in ['group', 'supergroup']):
        trg = get_triggers(m.chat.id)
        if(trg):
            if(len(trg.keys()) == 0):
                bot.reply_to(m, 'This group doesn\'t have triggers.')
            else:
                bot.reply_to(m,'Trigers:\n' + '\n'.join(trg))
        else:
            bot.reply_to(m, 'This group doesn\'t have triggers.')
            


@bot.message_handler(commands=['help'])
def help(m):
    if(not is_recent(m)):
        return
    bot.reply_to(m, help_message)

@bot.message_handler(commands=['source'])
def source(m):
    if(not is_recent(m)):
        return
    if exists(__file__):
        bot.send_document(m.chat.id, open(__file__,'rb'))
    else:
        bot.reply_to(m, "No source file found :x")

@bot.message_handler(commands=['solve'])
def solve(m):
    if(not is_recent(m)):
        return
    rp = m.reply_to_message
    rw = ''
    ts = 'Trigger not Found.'
    if(len(m.text.split()) >= 2):
        rw = m.text.split(' ', 1)[1]
    if(rp and rp.from_user.id == bot_id and rp.text):
        rw = rp.text
    if(m.chat.type in ['group', 'supergroup']):
        trg = get_triggers(m.chat.id)
        if(trg):
            for x in trg.keys():
                if(trg[x].lower() == rw.lower()):
                    ts = 'Trigger = ' + x
        bot.reply_to(m, ts)

@bot.message_handler(commands=['about'])

def about(m):
    if(not is_recent(m)):
        return
    bot.reply_to(m, about_message, parse_mode="Markdown")


##END OF COMMAND IMPLEMENTATION SECTION.

##TRIGGER PROCESS SECTION.
#Catch every message, for triggers.
@bot.message_handler(func=lambda m: True)
def response(m):
    if(not is_recent(m)):
        return
    if(m.chat.type in ['group', 'supergroup']):
        trg = get_triggers(m.chat.id)
        if(trg):
            for t in trg.keys():
                if t in m.text.lower():
                    bot.reply_to(m, trg[t])

#Bot starts here.
print('Bot Started')
bot.polling(True)
