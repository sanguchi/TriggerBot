# -*- coding: utf-8 -*-
import telebot, json, time
from os.path import exists

#comment to use default timeout. (3.5)
telebot.apihelper.CONNECT_TIMEOUT = 9999

#TODO: /lock command.

triggers = {}
tfile = "triggers.json"
tokenf = "token.txt"
ignored = []
separator = '/'

admin = 59802458

def is_recent(m):
    return (time.time() - m.date) < 60

#Check if Triggers file exists.
if exists(tfile):
    with open(tfile) as f:
        triggers = json.load(f)
else:
    #print("Triggers file not found, creating.")
    with open(tfile,'w') as f:
        json.dump({}, f)

#Check if Token file exists, if not, create.
if exists(tokenf):
    with open(tokenf) as f:
        token = f.readline().rstrip('\n')
    #print("Token = [" + token + "]")
else:
    #print("Token File not found, creating.")
    with open(tokenf,'w') as f:
        try:
            token = raw_input('Token not found, please paste/write your token.\n> ')
        except NameError:
            token = input('Token not found, please paste/write your token.\n> ')
        f.write(token)

#Function to add new Trigger - Response
def newTrigger(trigger, response):
    triggers[trigger.lower()] = response
    with open(tfile, "w") as f:
        json.dump(triggers, f, indent=1)
    #print("triggers file saved")


          
#Create Bot.
bot = telebot.TeleBot(token)

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
bot.set_update_listener(logging_to_console)

		
help_text = '''
Main commands: 
/add <trigger> / <response>
/del <trigger>
Other Commands:
/about
/source
/all
'''

about_text = '''
Created by @Sanguchi in 60 minutes :P
[Source Code on Github](https://github.com/sanguchi/TriggerBot/)
'''
#Adds another trigger-response. ex: "/add Hi / Hi!! :DD"
@bot.message_handler(commands=['add'])
def add(m):
    if(len(m.text.split()) > 1):
        rest = m.text.split(' ', 1)[1]
        if(m.text.find('/') != -1):
            trigger, response = [x.strip() for x in rest.split('/', 1)]
            if(len(trigger) >= 4):
                newTrigger(trigger, response)
                bot.reply_to(m, "Trigger Added: Trigger[%s] - Response[%s]" % (trigger, response))
            else:
                bot.reply_to(m, "Trigger too short. [chars < 4]")
        else:
            bot.reply_to(m, 'Separator not found.')
    else:
        bot.reply_to(m, 'Usage: /add <trigger> / <response>')
        
@bot.message_handler(commands=['del'])
def delete(m):
    if(len(m.text.split()) > 1):
        if(m.text.split()[1] in triggers.keys()):
            triggers.pop(m.text.split()[1])
            bot.reply_to(m, 'Trigger [%s] deleted.' % m.text.split()[1])
            with open(tfile, "w") as f:
                json.dump(triggers, f)
                print("triggers file saved")
        else:
            bot.reply_to(m, 'Trigger not found.')
    else:
        bot.reply_to(m, 'Usage: /del <trigger>')

#Answers with the size of triggers.
@bot.message_handler(commands=['size'])
def size(m):
    bot.reply_to(m, 'Size of triggers list: %s' % len(triggers))

#Help message.
@bot.message_handler(commands=['help'])
def help(m):
    bot.reply_to(m, help_text)

#About message.
@bot.message_handler(commands=['about'])
def about(m):
    bot.reply_to(m, about_text, parse_mode="Markdown")

#Sends source file (THIS FILE)
@bot.message_handler(commands=['source'])
def source(m):
    cid = m.chat.id
    if exists(__file__):
        bot.send_document(cid, open(__file__,'rb'))
    else:
        bot.reply_to(m, "No source file found :x")

@bot.message_handler(commands=['all'])
def all(m):
    bot.reply_to(m,'Triggers:\n%s' % '\n'.join(triggers.keys()))

#Catch every message, for triggers :D
@bot.message_handler(func=lambda m: True)
def response(m):
    #print("Checking for triggers in Message [" + m.text + "]")
    for t in triggers.keys():
        if t in m.text:
            bot.reply_to(m, triggers[t])

bot.send_message(admin, "Bot iniciado")
print('Bot started')
#Bot starts here.
bot.polling(True)
