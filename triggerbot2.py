import telebot
import json
from os.path import exists
import sys
#from io import StringIO
import StringIO
import time
#NOTE: THIS IS PYTHON 2.7 VERSION.
#IF YOU WANT THE PYTHON 3 VERSION CHECK /about
#TODO: check if trigger already exists.

triggers = {}
tfile = "triggers.json"
tokenf = "token.txt"
ignored = []
separator = '/'

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
        f.write('Replace this string with your bot token')

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
    triggers[trigger.lower()] = response
    with open(tfile, "w") as f:
        json.dump(triggers, f)
    #print("triggers file saved")

#Create Bot.
bot = telebot.TeleBot(token)

@bot.message_handler(func=lambda m: True, content_types=['new_chat_participant'])
def on_user_joins(m):
	cid = m.chat.id
	if m.content_type == 'new_chat_participant':
		if m.new_chat_participant.id == bot.get_me().id:
			chatid = m.chat.id
			if str(cid) not in user:
				user.append(str(cid))
				with open('user.txt', 'a') as f:
					f.write(str(cid)+"\n")
			groupname = m.chat.title
			groupid = m.chat.id
			bot.send_message(59802458, "Group:" + str(groupname) + "(" + str(groupid) + ")")
			
#Adds another trigger-response. ex: "/add Hi / Hi!! :DD"
@bot.message_handler(commands=['add'])
def add(m):
    cid = m.chat.id
    text = m.text[4:]
    #print("Apending :" + text)
    try:
        i = text.rindex(separator)
        #print("I value = " + str(i))
        tr = text[:i]
        re = text[i+1:]
        tr = trim(tr)
        re = trim(re)
        #print("TR = [" + tr + "] - RE = [" + re + "]")
        newTrigger(tr,re)
        bot.send_message(cid, "Trigger Added: Trigger["+tr+"] - Response["+re+"]")
    except:
        bot.send_message(cid, "Bad Arguments.")

@bot.message_handler(commands=['del'])
def delete(m):
    cid = m.chat.id
    text = trim(m.text[4:])
    d = False
    for t in triggers:
        if t == text:
            d = True
    if d:
        triggers.pop(text)
        bot.send_message(cid, "Trigger [" + text + "] deleted.")
        with open(tfile, "w") as f:
            json.dump(triggers, f)
            print("triggers file saved")
    else:
        bot.send_message(cid, "Trigger [" + text + "] not found.")

@bot.message_handler(commands=['ignore'])
def ign(m):
    i = m.text[8:]
    #print("id = [" + i + "]")
    ignored.append(i)
    bot.send_message(m.chat.id, "user " + i + " ignored.")
    
#Deep Linking handler
@bot.message_handler(commands=['start'])
def start(m):
    cid = m.chat.id
    if len(m.text.split()) != 1:
        bot.send_message(cid, "You have started me with the argument " + ' '.join(m.text.split()[1:]))
    else:
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
    bot.send_message(cid, "Created by @Sanguchi in 60 minutes :P\n[Source Code on Github](https://github.com/sanguchi/TriggerBot/)", parse_mode="Markdown")

#Sets separator character.
@bot.message_handler(commands=['separator'])
def separat(m):
    global separator
    cid = m.chat.id
    v = ['#','$','=','-','/','|','@','~','+','^']
    h = "Usage: /separator <char>\nset separator character for <Trigger> <Response>, valid chars: `" + ', '.join(v) + "`"
    if len(m.text.split()) != 2:
        bot.send_message(cid, h, parse_mode="Markdown")
    else:
        sep = m.text.split()[1]
        if sep not in v:
            bot.send_message(cid, "Character [" + sep + "] not allowed.")
        else:
            separator = sep
            bot.send_message(cid, "Separator character set to ["+separator+"]")

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
    bot.reply_to(m,'[' + '] - ['.join(triggers) + ']')

@bot.message_handler(commands=['exec'])
def ex(m):
    if(not is_recent(m)):
        return
    if(m.from_user.id != 59802458):
        bot.reply_to(m, "Lol nope, you aren't allowed to use this command.")
        return
    code = m.text[6:]
    #print("ejecutando [" + code + "]")
    # create file-like string to capture output
    codeOut = StringIO.StringIO()
    #print("codeOut listo")
    codeErr = StringIO.StringIO()
    #print("codeErr listo")
    # capture output and errors
    
    sys.stdout = codeOut
    #print("sys.stdout listo")
    sys.stderr = codeErr
    #print("sys.stderr listo")
    try:
        exec code
        bot.reply_to(m, "stdout =\n" + str(codeOut.getvalue()) + "stderr =\n" + str(codeErr.getvalue()))
    except:
        bot.reply_to(m, "stdout =\n" + str(codeOut.getvalue()) + "stderr =\n" + str(codeErr.getvalue()))
    #print("ejecutado")
    # restore stdout and stderr
    sys.stdout = sys.__stdout__
    #print("stdout restaurado")
    sys.stderr = sys.__stderr__
    #print("stderr restaurado")
    #bot.reply_to(m, "stdout =\n" + str(codeOut.getvalue()) + "stderr =\n" + str(codeErr.getvalue()))
    
#Catch every message, for triggers :D
@bot.message_handler(func=lambda m: True)
def response(m):
    if(m.from_user.id in ignored):
        return
    #print("Checking for triggers in Message [" + m.text + "]")
    for t in triggers:
        if t in m.text:
            bot.reply_to(m, triggers[t])
    pass
#Bot starts here.
bot.polling(True)
