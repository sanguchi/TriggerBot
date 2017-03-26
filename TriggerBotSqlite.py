import argparse
import re
from time import time, asctime, sleep
import tempfile
from peewee import *
import telebot
from telebot.apihelper import ApiException

__version__ = 0.1

# database section
db = SqliteDatabase('{}.db'.format(__file__))

# Set this to False to check the database for every message.
# This setting does not affect the /lock, /del and /add commands.
triggers_dict = False


class BaseModel(Model):
    class Meta:
        database = db


class TGUserModel(BaseModel):
    chat_id = CharField()
    first_name = CharField()
    username = CharField(null=True)


class ConfigModel(BaseModel):
    bot_user = ForeignKeyField(TGUserModel)
    token = CharField()
    owner = IntegerField()


class TextTriggerModel(BaseModel):
    chat = ForeignKeyField(TGUserModel, 'chat_triggers')
    trigger_text = CharField(max_length=3000)
    response_text = CharField(max_length=3000)
    locked_by = IntegerField(default=0)


class MediaTriggerModel(BaseModel):
    chat = ForeignKeyField(TGUserModel, 'media_triggers')
    trigger_text = CharField(max_length=3000)
    file_id = CharField()
    file_type = CharField()
    locked_by = IntegerField(default=0)

db.create_tables([TGUserModel, TextTriggerModel, MediaTriggerModel, ConfigModel], safe=True)


# Check command line arguments,  -t --token <token>, -o --owner <user_id>.
def check_args():
    print("checking args")
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--token', help="Token received from botfather.")
    parser.add_argument('-o', '--owner', help="Telegram chat ID to send status messages.", type=int)
    parser.add_argument('-d', '--dict', help="Keep database as a dict object stored in ram", default=False)
    args = parser.parse_args()
    if(args.dict):
        global triggers_dict
        triggers_dict = True
    if (args.token):
        if (args.owner):
            try:
                dummy_bot = telebot.TeleBot(args.token)
                bot_info = dummy_bot.get_me()
                bot_user, created = TGUserModel.get_or_create(
                    chat_id=bot_info.id,
                    first_name=bot_info.first_name,
                    username=bot_info.username
                )
                bot_user.save()
                try:
                    dummy_bot.send_message(args.owner, "This bot is ready!")
                    bot_cfg = ConfigModel.create(bot_user=bot_user, token=args.token, owner=args.owner)
                    bot_cfg.save()
                except ApiException as ae:
                    print('''Make sure you have started your bot https://telegram.me/{}.
                        And configured the owner variable.
                        ApiException: {}'''.format(bot_info.username, ae))
                    exit(1)
            except ApiException as ApiError:
                print("Invalid token[{}]: {}".format(args.token, ApiError))
                exit(1)
            except Exception as e:
                print(e)
                exit(1)
        else:
            print("Owner ID not supplied")
            exit(1)

if(ConfigModel.select().count() == 0):
    check_args()
try:
    bot_instance_from_db = ConfigModel.get()
except DoesNotExist:
    print("First create your bot with:\n{} --token <token> --owner <chat_id>".format(__file__))
    exit(1)

bot = telebot.TeleBot(bot_instance_from_db.token)
owner = bot_instance_from_db.owner


# Define a custom Listener to print messages to console.

# Python2 version
def listener2(messages):
    for m in messages:
        cid = m.chat.id
        name = m.from_user.first_name.encode('ascii', 'ignore').decode('ascii')
        if(m.content_type == 'text'):
            message_text = m.text.encode('ascii', 'ignore').decode('ascii')
        else:
            message_text = m.content_type
        print('{}[{}]:{}'.format(name, cid, message_text))


# Python3 version.
def listener3(messages):
    for m in messages:
        print('%s[%s]:%s' % (m.from_user.first_name, m.chat.id, m.text if m.text else m.content_type))

# Change to listener2 if this complains about encoding.
bot.set_update_listener(listener3)

help_message = '''
You need help!
*Commands:*
`/add <trigger> / <response>`
 |-_Adds a new trigger._
`/del <trigger>`
 |-_deletes trigger if exists._
 `/lock <trigger>`
 |-_locks trigger if exists._
*For a detailed help send /help in private.*
'''

full_help_message = '''
You really need help!
*Main Functions:*
*Add Triggers:*
`/add <trigger> / <response>`
Example:
`/add Hello / Hello there!`
Also works via reply.
_Just send_ `/add <trigger>` _in Reply to Another Message:_
*Delete Triggers:*
`/del <trigger>`
Deletes a defined trigger, example:
`/del hello`
Also works via reply.
_Just send_ `/del` _in Reply to a bot's Message:_
*Lock/Unlock Triggers:*
`/lock <trigger>`
Locks a trigger so nobody can delete it unless you unlock it, example:
`/lock hello`
Also works via reply.
_Just send_ `/lock` _in Reply to a bot's Message:_
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
_Just send_ `/solve` _in Reply to a bot's Message:_
/about
_About this bot._
'''


def db2dict():
    global triggers_dict
    if(triggers_dict):
        triggers_dict = {}
        for chat in TGUserModel.select():
            triggers_list = dict()
            for trigger in chat.chat_triggers:
                triggers_list[trigger.trigger_text] = trigger.response_text
            triggers_dict[chat.chat_id] = triggers_list
            print(chat.chat_id, "loaded", len(triggers_dict[chat.chat_id]), "triggers.")
        print("Loaded ", len(triggers_dict.keys()), "chats.")
db2dict()


def get_chat_from_message(msg):
    try:
        chat = TGUserModel.get(TGUserModel.chat_id == msg.chat.id)
    except DoesNotExist:
        chat = TGUserModel.create(
            chat_id=msg.chat.id,
            first_name=msg.chat.first_name if msg.chat.first_name else msg.chat.title,
            username=msg.chat.username)
        chat.save()
    return chat


@bot.message_handler(regexp=r'/add .{4,3000}/.{1,3000}')
def add_trigger(msg):
    trigger, response = re.search(r'/add(.{5,3000})/(.{1,3000})', msg.text).groups()
    chat = get_chat_from_message(msg)
    trigger, created = TextTriggerModel.get_or_create(
        chat=chat,
        trigger_text=trigger.lower().strip(),
        response_text=response.strip())
    if(created):
        trigger.save()
        bot.reply_to(msg, "Trigger created.")
        db2dict()
    else:
        if(trigger.locked_by):
            who_locked = TGUserModel.get(TGUserModel.chat_id == trigger.locked_by)
            bot.reply_to(msg, "You can't override this trigger, it's locked by {}".format(
                '@' + who_locked.username if who_locked.username else '{}[{}]'.format(
                    who_locked.first_name, who_locked.chat_id)))
        else:
            trigger.response_text = response.strip()
            trigger.save()
            bot.reply_to(msg, "Trigger saved.")
            db2dict()


@bot.message_handler(func=lambda m: m.reply_to_message, regexp=r'/add .{4,3000}')
def add_trigger_on_reply(msg):
    if(msg.reply_to_message.text):
        reply_len = len(msg.reply_to_message.text)
        if(0 < reply_len < 3000):
            chat = get_chat_from_message(msg)
            trigger_text = msg.text.split(' ', 1)[1].strip().lower()
            response_text = msg.reply_to_message.text
            try:
                trigger = TextTriggerModel.get(
                    TextTriggerModel.chat == chat,
                    TextTriggerModel.trigger_text == trigger_text)
                if(trigger.locked_by):
                    who_locked = TGUserModel.get(TGUserModel.chat_id == trigger.locked_by)
                    bot.reply_to(msg, "You can't override this trigger, it's locked by {}".format(
                       '@' + who_locked.username if who_locked.username else '{}[{}]'.format(
                           who_locked.first_name, who_locked.chat_id)))
                else:
                    trigger.response_text = response_text
                    trigger.save()
                    bot.reply_to(msg, "Trigger response modified.")
            except DoesNotExist:
                trigger = TextTriggerModel.create(chat=chat, trigger_text=trigger_text, response_text=response_text)
                bot.reply_to(msg, "Trigger created.")
                trigger.save()
                db2dict()
        else:
            bot.reply_to(msg, "Response text too long: length is greater than 3000 characters.")
    else:
        bot.reply_to(msg, "Media responses are coming soon.")


@bot.message_handler(regexp=r'/del .{4,3000}')
def del_trigger(msg):
    chat = get_chat_from_message(msg)
    trigger_text = msg.text.split(' ', 1)[1].strip()
    try:
        trigger = TextTriggerModel.get(TextTriggerModel.chat == chat, TextTriggerModel.trigger_text == trigger_text)
        if(trigger.locked_by):
            who_locked = TGUserModel.get(TGUserModel.chat_id == trigger.locked_by)
            bot.reply_to(msg, "You can't delete this trigger, it's locked by {}".format(
                '@' + who_locked.username if who_locked.username else '{}[{}]'.format(
                    who_locked.first_name, who_locked.chat_id)))
        else:
            trigger.delete_instance()
            bot.reply_to(msg, "Trigger deleted.")
            db2dict()
    except DoesNotExist:
        bot.reply_to(msg, "Trigger not found")


@bot.message_handler(func=lambda m: m.reply_to_message, commands=['del'])
def del_trigger_on_reply(msg):
    chat = get_chat_from_message(msg)
    if(msg.reply_to_message.text):
        try:
            trigger = TextTriggerModel.get(
                TextTriggerModel.chat == chat, TextTriggerModel.response_text == msg.reply_to_message.text)
            if(trigger.locked_by):
                who_locked = TGUserModel.get(TGUserModel.chat_id == trigger.locked_by)
                bot.reply_to(msg, "You can't delete this trigger, it's locked by {}.".format(
                    '@' + who_locked.username if who_locked.username else '{}[{}]'.format(
                        who_locked.first_name, who_locked.chat_id)))
            else:
                trigger.delete_instance()
                bot.reply_to(msg, "Trigger deleted.")
                db2dict()
        except DoesNotExist:
            bot.reply_to(msg, "Trigger not found.")
    else:
        bot.reply_to(msg, "Media triggers are not supported yet.")


@bot.message_handler(regexp=r'/lock .{4,3000}')
def lock_trigger(msg):
    chat = get_chat_from_message(msg)
    trigger_text = msg.text.split(' ', 1)[1].strip()
    try:
        trigger = TextTriggerModel.get(TextTriggerModel.chat == chat, TextTriggerModel.trigger_text == trigger_text)
        if(trigger.locked_by):
            who_locked = TGUserModel.get(TGUserModel.chat_id == trigger.locked_by)
            if(trigger.locked_by == msg.from_user.id):
                trigger.locked_by = 0
                trigger.save()
                bot.reply_to(msg, "Trigger unlocked.")
            else:
                bot.reply_to(msg, "You can't unlock this trigger, it's locked by {}".format(
                    '@' + who_locked.username if who_locked.username else '{}[{}]'.format(
                        who_locked.first_name, who_locked.chat_id)))
        else:
            trigger.locked_by = msg.from_user.id
            trigger.save()
            bot.reply_to(msg, "Trigger locked.")
    except DoesNotExist:
        bot.reply_to(msg, "Trigger not found")


@bot.message_handler(func=lambda m: m.reply_to_message, commands=['lock'])
def lock_trigger_on_reply(msg):
    chat = get_chat_from_message(msg)
    if (msg.reply_to_message.text):
        try:
            trigger = TextTriggerModel.get(
                TextTriggerModel.chat == chat, TextTriggerModel.response_text == msg.reply_to_message.text)
            if (trigger.locked_by):
                who_locked = TGUserModel.get(TGUserModel.chat_id == trigger.locked_by)
                if (trigger.locked_by == msg.from_user.id):
                    trigger.locked_by = 0
                    trigger.save()
                    bot.reply_to(msg, "Trigger unlocked.")
                else:
                    bot.reply_to(msg, "You can't unlock this trigger, it's locked by {}".format(
                        '@' + who_locked.username if who_locked.username else '{}[{}]'.format(
                            who_locked.first_name, who_locked.chat_id)))
            else:
                trigger.locked_by = msg.from_user.id
                trigger.save()
                bot.reply_to(msg, "Trigger locked.")
        except DoesNotExist:
            bot.reply_to(msg, "Trigger not found.")
    else:
        bot.reply_to(msg, "Media triggers are not supported yet.")


@bot.message_handler(func=lambda m: m.reply_to_message, commands=['solve'])
def solve_trigger(msg):
    chat = get_chat_from_message(msg)
    if(msg.reply_to_message.text):
        try:
            trigger = TextTriggerModel.get(
                TextTriggerModel.chat == chat, TextTriggerModel.response_text == msg.reply_to_message.text)
            bot.reply_to(msg, "Trigger: \n {}".format(trigger.trigger_text))
        except DoesNotExist:
            bot.reply_to(msg, "Trigger not found.")
    else:
        bot.reply_to(msg, "Media triggers are not supported yet.")


@bot.message_handler(commands=['size'])
def get_triggers_size(msg):
    chat = get_chat_from_message(msg)
    bot.reply_to(msg, "This chat has {} triggers".format(chat.chat_triggers.count()))


@bot.message_handler(commands=['all'])
def get_triggers_list(msg):
    chat = get_chat_from_message(msg)
    if(len(chat.chat_triggers) > 0):
        trigger_listing = "Triggers:\n{}".format(','.join([trigger.trigger_text for trigger in chat.chat_triggers]))
        if(len(trigger_listing) > 3000):
            with tempfile.NamedTemporaryFile('w') as tmpfile:
                tmpfile.write(trigger_listing)
                bot.send_document(msg.chat.id, tmpfile, msg.message_id)
        else:
            bot.reply_to(msg, trigger_listing)
    else:
        bot.reply_to(msg, "This chat doesn't have triggers.")


@bot.message_handler(commands=['about'])
def send_about_message(msg):
    about_message = '''
    TriggerBot *%s* (SQLite version)
    [Source Code on Github](https://github.com/sanguchi/TriggerBot/)
    [Give me 5 Stars](https://telegram.me/storebot?start=TriggerResponseBot)
    ''' % __version__
    bot.reply_to(msg, about_message, parse_mode="Markdown")


@bot.message_handler(commands=['help', 'start'])
def send_help_message(msg):
    bot.reply_to(msg, full_help_message if msg.chat.id == msg.from_user.id else help_message, parse_mode="Markdown")


@bot.message_handler(commands=['source'])
def send_source_code(msg):
    bot.send_document(msg.chat.id, open(__file__, 'rb'), msg.message_id, "Libraries needed:\npyTelegramBotAPI, peewee")


@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == owner)
def admin_broadcast(msg):
    if(msg.text.count(' ') > 0):
        broadcast_text = msg.text.split(' ', 1)[1]
        for user in TGUserModel.select():
            bot.send_message(user.chat_id, broadcast_text)
        bot.send_message(msg.chat.id, "Broadcast sent.")
    else:
        bot.send_message(msg.chat.id, "No text provided, usage:\n-->`/broadcast <text>`", parse_mode="Markdown")


@bot.message_handler(commands=['database'], func=lambda m: m.from_user.id == owner)
def admin_send_database(msg):
    bot.send_document(msg.chat.id, open('{}.db'.format(__file__), 'rb'))


# TODO: admin commands: clean, stats.
# TODO: inline triggers, media.
# TODO: main loop that listen to messages to trigger.
# TODO: fix database mode.

# Catch every message, for triggers.
@bot.message_handler(content_types=['text'])
def catch_messages(msg):
    if(triggers_dict):
        print("Using dict")
        trigger_list = triggers_dict[str(msg.chat.id)]
        print("Trigger list: ", trigger_list)
        for trigger_text in trigger_list.keys():
            print("Checking against: ", trigger_text)
            if(trigger_text in msg.text.lower()):
                bot.reply_to(msg, trigger_list[trigger_text])
    else:
        print("Using database")
        try:
            chat = TGUserModel.get(TGUserModel.chat_id == msg.chat.id)
        except DoesNotExist:
            chat = TGUserModel.create(chat_id=msg.chat.id, first_name=msg.chat.first_name, username=msg.chat.username)
            chat.save()
        # print("Trigger count for", chat.chat_id, ": ", chat.chat_triggers.count())
        for trigger_model in chat.chat_triggers:
            print("Checking against: ", trigger_model.trigger_text)
            if(trigger_model.trigger_text in msg.text.lower()):
                bot.reply_to(msg, trigger_model.response_text)

# print("Starting")
# bot.polling()


# This makes the bot unstoppable :^)
def safepolling(bot_instance):
    if(bot_instance.skip_pending):
        lid = bot_instance.get_updates()[-1].update_id
    else:
        lid = 0
    while(1):
        try:
            updates = bot_instance.get_updates(lid + 1, 50)
            # print('len updates = %s' % len(updates))
            if(len(updates) > 0):
                lid = updates[-1].update_id
                bot_instance.process_new_updates(updates)
        except ApiException as a:
            print(a)
        except Exception as e:
            print('Exception at %s \n%s' % (asctime(), e))
            now = int(time())
            while(1):
                error_text = 'Exception at %s:\n%s' % (asctime(), str(e) if len(str(e)) < 3600 else str(e)[:3600])
                try:
                    # print('Trying to send message to owner.')
                    offline = int(time()) - now
                    bot_instance.send_message(owner, error_text + '\nBot went offline for %s seconds' % offline)
                    # print('Message sent, returning to polling.')
                    break
                except:
                    sleep(0.25)


if(__name__ == '__main__'):
    # Bot starts here.

    print('Bot started.')
    try:
        print('Bot username:[%s]' % bot.get_me().username)
    except ApiException:
        print('The given token [%s] is invalid, please fix it')
        exit(1)
    # Tell owner the bot has started.
    try:
        bot.send_message(owner, 'Bot Started')
    except ApiException:
        print('''Make sure you have started your bot https://telegram.me/%s.
    And configured the owner variable.''' % bot.get_me().username)
        exit(1)
    print('Safepolling Start.')
    safepolling(bot)

# Nothing beyond this line will be executed.
