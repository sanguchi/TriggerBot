# -*- coding: utf-8 -*-
#TRIGGERBOT 0.6.2
import telebot, json
from time import time, asctime, sleep
from os.path import exists
from telebot.apihelper import ApiException
#comment to use default timeout. (3.5)
#telebot.apihelper.CONNECT_TIMEOUT = 9999
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
    return (time() - m.date) < 60
    
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
        json.dump(triggers, f, indent=2)
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
    msg = 'No token file detected, please paste or type here your token:\n> '
    try:
        token = raw_input(msg)
    except NameError:
        token = input(msg)
    with open('token.txt', 'w') as f:
        f.write(token)  
    print('Token File saved.')

#Function to check if a message is too old(60 seconds) to answer.
def is_recent(m):
    return (time() - m.date) < 60
    
#Create Bot.
bot = telebot.TeleBot(token)
#Bot user ID.
bot_id = int(token.split(':')[0])
print('Bot ID [%s]' % bot_id)
#Define a custom Listener to print messages to console.

#Python2 version
def listener(messages):
    for m in messages:
        cid = m.chat.id
        name = m.from_user.first_name.encode('ascii', 'ignore').decode('ascii')
        if(m.content_type == 'text'):
            message_text = m.text.encode('ascii', 'ignore').decode('ascii')
        else:
            message_text = m.content_type
        print('{}[{}]:{}'.format(name, cid, message_text))
        
#Python3 version.
logging_to_console = lambda m: print('\n'.join(['%s[%s]:%s' %(x.from_user.first_name, x.chat.id, x.text if x.text else x.content_type) for x in m]))

#Change to listener if this complains about encoding.
bot.set_update_listener(listener)

##END OF BOT INITIALIZATION SECTION.

##GLOBAL MESSAGES SECTION.
about_message = '''
TriggerBot *0.6.2*
Created by @Sanguchi in ~60 minutes :P
[Source Code on Github](https://github.com/sanguchi/TriggerBot/)
[Give me 5 Stars](https://telegram.me/storebot?start=TriggerResponseBot)
'''
  
help_message = '''
You need help!
*Commands:*
`/add <trigger> / <response>`
 |-_Adds a new trigger._
`/del <trigger>`
 |-_deletes trigger if exists._
*More:*
/about - /size - /all - /source
*For a detailed help send /help in private.*
'''

full_help = '''
You really need help!
*Main Functions:*
*Add Triggers:* There are two ways.
1)`/add <trigger> / <response>`
Example:
*/add Hello / Hello there!*
Also works via reply.
_In Reply to Another Message:_
2)`/add <trigger>`
*Delete Triggers:*
`/del <trigger>`
Deletes a defined trigger, example:
`/del hello`
*Misc:*
/size
_Returns size of triggers list._
/all
_List all triggers._
/help
_This message._
/source
_Sends source code TriggerBot.py_
/solve <response>
_Resolve what trigger causes the given response, if exists._
*Also works by reply:*
_Reply to any bot response with the command to get the trigger._
/about
_About this bot._
'''
 
added_message = '''
New Trigger Created:
Trigger [{}]
Response [{}]
'''

gadded_message = '''
New Global Trigger Created:
Trigger [{}]
Response [{}]
'''

gdeleted_message = '''
Trigger [{}] deleted from {} Groups.
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
            trigger_word = u'' + m.text.split(' ', 1)[1].strip().lower()
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
    if(len(trigger_response) > 4700):
        bot.reply_to(m, 'Response too long. [chars > 4700]')
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
                bot.reply_to(m,'Triggers:\n' + '\n'.join(trg))
        else:
            bot.reply_to(m, 'This group doesn\'t have triggers.')
            


@bot.message_handler(commands=['help'])
def help(m):
    if(m.chat.id == m.from_user.id):
        bot.send_message(m.chat.id, full_help, True, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, help_message, True, parse_mode="Markdown")

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

##ADMIN COMMANDS
@bot.message_handler(commands=['broadcast'])
def bcast(m):
    if(m.from_user.id != owner):
        return
    if(len(m.text.split()) == 1):
        bot.send_message(m.chat.id, 'No text provided.!')
        return
    count = 0
    for g in triggers.keys():
        try:
            bot.send_message(int(g), m.text.split(' ', 1)[1])
            count += 1
        except:
            continue
    bot.send_message(m.chat.id, 
    'Broadcast sent to {} groups of {}'.format(
    count, len(triggers.keys())))

@bot.message_handler(commands=['triggers'])
def send_triggers(m):
    if(m.from_user.id == owner):
        bot.send_document(owner, open('triggers.json'))

@bot.message_handler(commands=['gadd'])
def add_global_trigger(m):
    if(m.from_user.id == owner):
        if(len(m.text.split()) == 1):
            bot.reply_to(m, 'Usage:\n/gadd <trigger> / <response>\n[In reply]:\n/gadd <trigger>')
            return
        if(m.reply_to_message):
            if(m.reply_to_message.text):
                trigger_response = m.reply_to_message.text
                trigger_word = m.text
        else:
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
        for g in triggers.keys():
            triggers[g][trigger_word] = trigger_response
        bot.reply_to(m, gadded_message.format(trigger_word, trigger_response))
        save_triggers()

@bot.message_handler(commands=['gdel'])
def global_delete(m):
    if(m.from_user.id == owner):
        if(len(m.text.split()) == 1):
            bot.reply_to(m, 'Usage: /gdel <trigger>')
        else:
            trigger_word = m.text.split(' ', 1)[1]
            count = 0
            for g in triggers.keys():
                if(trigger_word in triggers[g]):
                    triggers[g].pop(trigger_word)
                    count += 1
            bot.reply_to(m, gdeleted_message.format(trigger_word, count))
            save_triggers()

@bot.message_handler(commands=['gsearch'])
def global_search(m):
    if(m.from_user.id == owner):
        if(len(m.text.split()) == 1):
            bot.reply_to(m, 'Usage: /gsearch <trigger>')
        else:
            trigger_word = m.text.split(' ', 1)[1]
            results = []
            for g in triggers.keys():
                #print('g > %s = %s' % (g.__class__.__name__, g))
                if(trigger_word in triggers[g].keys()):
                    txt = triggers[g][trigger_word]
                    results.append('[%s]:\n%s' % (g, txt if len(txt) < 30 else txt[:27] + '...'))
            if(len(results) == 0):
                result_text = 'Trigger not found'
            else:
                result_text = 'Trigger found in these groups:\n%s' % '\n-----\n'.join(results)
            bot.reply_to(m, result_text)

##TRIGGER PROCESSING SECTION.
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


#This makes the bot unstoppable :^)
#Notice this is single-threaded.
def safepolling(bot):
    if(bot.skip_pending):
        lid = bot.get_updates()[-1].update_id
    else:
        lid = 0
    while(1):
        try:
            updates = bot.get_updates(lid + 1, 50)
            #print('len updates = %s' % len(updates))
            if(len(updates) > 0):
                lid = updates[-1].update_id
                bot.process_new_updates(updates)
        except ApiException as a:
            print(a)
        except Exception as e:
            print('Exception at %s \n%s' % (asctime(), e))
            now = int(time())
            while(1):
                error_text = 'Exception at %s:\n%s' % (asctime(), str(e) if len(str(e)) < 3600 else str(e)[:3600])
                try:
                    #print('Trying to send message to owner.')
                    offline = int(time()) - now
                    bot.send_message(owner, error_text + '\nBot went offline for %s seconds' % offline)
                    #print('Message sent, returning to polling.')
                    break
                except:
                    sleep(0.25)

#Bot starts here.
print('Bot started.')
print('Bot username:[%s]' % bot.get_me().username)
#Tell owner the bot has started.
bot.send_message(owner, 'Bot Started')  
print('Safepolling Start.')
safepolling(bot)
#Nothing beyond this line will be executed.
