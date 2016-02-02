import telebot
import json
from os.path import exists
#TODO: check if trigger already exists.

triggers = {}
tfile = "triggers.json"
tokenf = "token.txt"

separator = '/'

#Check if Triggers file exists.
if(exists(tfile)):
    with open(tfile) as f:
        #If exists, but is empty, don't load.
        if(f.readline() == ''):
            print("Triggers File is Empty.")
            f.close
        else:
            f = open(tfile)
            triggers = json.load(f)
else:
    print("Triggers file not found, creating.")
    f = open(tfile, 'w')
    f.close()

#Check if Token file exists, if not, create.
if(exists(tokenf)):
    with open(tokenf) as g:
        token = g.readline()
        #Here we cut the last char in token because is a newline char.
        token = token[:len(token) -1]
        print("Token = [" + token + "]")
else:
    print("Token File not found, creating.")
    g = open(tokenf, 'w')
    g.write("YOUR TOKEN HERE")
    f.close()

#Delete whitespaces at start & end
def trim(s):
    i = 0
    while(s[i] == ' '):
        i += 1
    s = s[i:]
    i = len(s)-1
    while(s[i] == ' '):
        i-= 1
    s = s[:i+1]
    return s

#Function to add new Trigger - Response
def newTrigger(trigger, response):
    trigger = trim(trigger)
    triggers[trigger.lower()] = trim(response)
    with open(tfile, "w") as f:
        json.dump(triggers, f)
    print("triggers file saved")

#Create Bot.
bot = telebot.TeleBot(token)

#Adds another trigger-response. ex: "/add Hi / Hi!! :DD"
@bot.message_handler(commands=['add'])
def add(m):
    cid = m.chat.id
    text = m.text[4:]
    print("Apending :" + text)
    try:
        i = text.rindex(separator)
        print("I value = " + str(i))
        tr = text[:i]
        re = text[i+1:]
        print("TR = " + tr + " - RE = " + re)
        newTrigger(tr,re)
        bot.send_message(cid, "Trigger Added: Trigger["+tr+"] - Response["+re+"]")
    except:
        bot.send_message(cid, "Bad Arguments.")


#Deep Linking handler
@bot.message_handler(commands=['start'])
def start(m):
    cid = m.chat.id
    try:
        i = m.text.rindex(' ')
        bot.send_message(cid, "You have started me with the argument " + m.text[i+1:])
    except:
        bot.send_message(cid, "You have started me with no arguments.")

#Answers with the size of triggers.
@bot.message_handler(commands=['size'])
def size(m):
    cid = m.chat.id
    bot.send_message(cid, "Size of Triggers list = " + str(len(triggers)))



#Help message.
@bot.message_handler(commands=['help'])
def help(m):
    cid = m.chat.id
    h ="Usage: /add <trigger> / <response>\nOthers Commands:\n/size\n/about\n/separator\n/source"
    bot.send_message(cid,h)

#About message.
@bot.message_handler(commands=['about'])
def about(m):
    cid = m.chat.id
    bot.send_message(cid, "Created by @Sanguchi in 60 minutes :P")

#Sets separator character.
@bot.message_handler(commands=['separator'])
def separat(m):
    global separator
    v = "#$=*-/|@~+^º"
    h = "Usage: /separator <char>\nset separator character for <Trigger> <Response>, valid chars: "+v
    cid = m.chat.id
    try:
        m.text.rindex(' ')
        sep = m.text[11:]
        if(sep in v):
            separator = sep
            bot.send_message(cid, "Separator character set to ["+separator+"]")
        else:
            bot.send_message(cid, "Character ["+sep+"] not allowed.")
    except:
        bot.send_message(cid, h + "\nCurrent separator char is ["+separator+"]")


#Sends source file (THIS FILE)
@bot.message_handler(commands=['source'])
def source(m):
    try:
        src = open('triggerbot.py')
        bot.send_document(m.chat.id, src)
    except:
        bot.reply_to(m, "No source file found :x")

@bot.message_handler(commands=['all'])
def all(m):
    build = ''
    for t in triggers:
        build = build + t +" - "
    bot.reply_to(m, build)

#Catch every message, for triggers :D
@bot.message_handler(func=lambda m: True)
def response(m):
    print("Checking for triggers in Message [" + m.text + "]")
    for t in triggers:
        if(t in m.text):
            bot.reply_to(m, triggers[t])

#Bot starts here.
bot.polling()