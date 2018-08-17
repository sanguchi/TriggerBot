# -*- coding: utf-8 -*-
import telebot
from peewee import *
from decouple import config
import markovify
import logging
from time import time, asctime, sleep
from telebot.apihelper import ApiException
from typing import List
import random

# VERSION 0.2: removed ignored users array and added chance field on user model, and a settings panel.
# TODO: Inline buttons
__version__ = 0.2

debug_mode = config('DEBUG', cast=bool)
if(debug_mode):
    logging.basicConfig(level=logging.DEBUG)

# comment to use default timeout. (3.5)
telebot.apihelper.CONNECT_TIMEOUT = 9999

# Define database connector, comment/uncomment what you want to use.
db = PostgresqlDatabase(config('PG_DTBS'), user=config('PG_USER'), password=config('PG_PASS'), host=config('PG_HOST'))
# db = SqliteDatabase('{}.db'.format(__file__))


# Base class, every model inherits the database connector
class BaseModel(Model):
    class Meta:
        database = db


# Telegram user model
class TGUserModel(BaseModel):
    chat_id = CharField()
    first_name = CharField()
    username = CharField(null=True)
    # TODO: let users set the complexity of messages.
    state_size = IntegerField(default=3)
    # How much chances are of getting a response automatically.
    autoreply_chance = IntegerField(default=15)
    # this means only generate messages of 255 chars max, enabling this could cause large spam messages.
    large_messages = BooleanField(default=False)


# Model to store all messages
class UserMessageModel(BaseModel):
    user = ForeignKeyField(TGUserModel, 'messages')
    message_text = CharField(max_length=4000)


class GeneratedMessageModel(BaseModel):
    user = ForeignKeyField(TGUserModel, 'generated_messages')
    message_text = CharField(max_length=4000)


# Create database file if it doesn't exists.
db.create_tables([TGUserModel, UserMessageModel, GeneratedMessageModel], safe=True)
# Bot instance initialization.
bot = telebot.TeleBot(config('BOT_TOKEN'))

# Bot starts here.
logging.info('Bot started.')
try:
    bot_info = bot.get_me()
except ApiException:
    logging.critical('The given token [{0}] is invalid, please fix it'.format(config('BOT_TOKEN')))
    exit(1)
logging.debug('{bot_info.first_name} @{bot_info.username}[{bot_info.id}]'.format(bot_info=bot_info))


# Return a TGUser instance based on telegram message instance.
def get_user_from_message(message: telebot.types.Message) -> TGUserModel:
    # Handle forwarded messages.
    if(message.forward_date):
        # Check if this message is from a channel or a user.
        # If it was forwarder from a user, return forwarded message's user, else return forwarder user.
        if(message.forward_from):
            user = message.forward_from
        else:
            user = message.from_user
    else:
        user = message.from_user
    # Search user on database or create if it doesn't exists

    try:
        db_user = TGUserModel.get(chat_id=user.id)
    except DoesNotExist:
        db_user = TGUserModel.create(
            chat_id=user.id,
            first_name=user.first_name.lower(),
            username=user.username.lower() if user.username else None)
    # Update/Fill nickname and username
    return db_user


# Tries to return a short dumb response, if it already exists, return none
def create_message_or_reject(tguser: TGUserModel, state_size=2, short_sentence=True) -> str:
    # Get all user messages
    user_messages = UserMessageModel.select(UserMessageModel.message_text).where(UserMessageModel.user == tguser)
    if (not user_messages.count()):
        logging.info("No messages found from {tguser.first_name}[{tguser.chat_id}]".format(tguser=tguser))
        return None
    total_messages = user_messages.count()
    logging.info("Fetched {} messages from {}[{}]".format(total_messages, tguser.first_name, tguser.chat_id))
    # Markov chain generation.
    markov_feed = '\n'.join([user_message.message_text for user_message in user_messages])
    text_model = markovify.NewlineText(markov_feed, state_size=state_size)
    logging.debug("Generating {0} sentence.".format("short" if short_sentence else "long"))
    sentence_length = 255 if short_sentence else 4000
    result = text_model.make_short_sentence(sentence_length)
    if (result):
        # Only return new fresh responses.
        response, created = GeneratedMessageModel.get_or_create(user=tguser, message_text=result)
        if (created):
            logging.info("Response generated: {}".format(result))
            return result
        else:
            logging.info("Rejecting response: {}".format(result))
            return None
    else:
        logging.info("No response generated.")
        return None


# Add every text message to the database
def text_model_processor(messages: List[telebot.types.Message]):
    logging.debug("Processing %s new messages", len(messages))
    data_source = []
    for message in messages:
        user = get_user_from_message(message)
        # Only process text messages that are not commands and contains at least 3 words.
        if message.content_type == "text" and not message.text.startswith('/') and message.text.count(' ') >= 2:
            data_source.append({'user': user, 'message_text': message.text.lower()})
            # UserMessageModel.create(user=user, message_text=message.text).save()
    logging.debug("Saving {} text messages to the database".format(len(data_source)))
    if(data_source):
        with db.atomic():
            UserMessageModel.insert_many(data_source).execute()
    # Change to listener2 if this complains about encoding
    listener3(messages)


# Define a custom Listener to print messages to console.
# Python2 version
def listener2(messages: List[telebot.types.Message]):
    for message in messages:
        cid = message.chat.id
        name = message.from_user.first_name.encode('ascii', 'ignore').decode('ascii')
        if(message.content_type == 'text'):
            message_text = message.text.encode('ascii', 'ignore').decode('ascii')
        else:
            message_text = message.content_type
        logging.info('{}[{}]:{}'.format(name, cid, message_text))


# Python3 version.
def listener3(messages: List[telebot.types.Message]):
    logging.info('\n'.join(
        ['{}[{}]:{}'.format(
            message.from_user.first_name, message.chat.id, message.text if message.text else message.content_type)
         for message in messages]))


bot.set_update_listener(text_model_processor)

# GLOBAL MESSAGES SECTION.
about_message = '''
TriggerBot *%s*
[Source Code on Github](https://github.com/sanguchi/TriggerBot/)
[Give me 5 Stars](https://telegram.me/storebot?start=TriggerResponseBot)
''' % __version__

bot_help_text = '''
Hi, i'm *Trigger!*, i can learn from people's messages and chat like them.
If you want me to generate a message, you can mention me, say my nickname, reply to any of my messages, or use:
`/trigger`
(These methods only work if i have at least 100 messages from you)
You can try /settings to adjust autoreply chance.
'''

settings_text = '''
Settings for {user.first_name}[{user.chat_id}]:
Messages registered: {messages}
Messages generated: {generated}
Autoreply chance: {user.autoreply_chance}
'''


@bot.message_handler(commands=['start', 'help'])
def greet_user(message: telebot.types.Message):
    bot.reply_to(message, bot_help_text, parse_mode="Markdown")


@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(message, about_message, parse_mode="Markdown")


@bot.message_handler(commands=['settings'])
def send_user_statistics(message: telebot.types.Message):
    user_obj = get_user_from_message(message)
    message_count = user_obj.messages.count()
    generated_messages = user_obj.generated_messages.count()
    bot.reply_to(message, settings_text.format(user=user_obj, messages=message_count, generated=generated_messages))


def should_reply(message: telebot.types.Message):
    if(message.content_type == "text"):
        if(any([word in message.text for word in ['/trigger', bot_info.first_name, bot_info.username]])):
            return True
        if(message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id):
            return True
    return False


@bot.message_handler(func=should_reply)
def generate_response(message):
    user_obj = get_user_from_message(message)
    if(user_obj.messages.count() > 100):
        for _ in range(100):
            response = create_message_or_reject(user_obj, 2, user_obj.large_messages)
            if(response):
                bot.reply_to(message, response)
                return
        bot.reply_to(message, "Not this time, please talk more.")
    else:
        if('/trigger' in message.text):
            bot.reply_to(message, "I need at least 100 messages from you. :(")


# Try to reply to every text message
@bot.message_handler(func=lambda m: True)
def reply_intent(message: telebot.types.Message):
    if(message.content_type == "text" and not message.text.startswith('/') and message.text.count(' ') >= 3):
        user_obj = get_user_from_message(message)
        if(user_obj.autoreply_chance == 0):
            return
        # with chance of 90% there is a 90/100 chances of getting a randon number below or equal 90
        # this means you will get True 90 percent of the time.
        if(random.randint(0, 100) <= user_obj.autoreply_chance):
            for _ in range(100):
                response = create_message_or_reject(user_obj, 2)
                if (response):
                    bot.reply_to(message, response)
                    return


def notify_exceptions(exception_instance: Exception):
    logging.warning('Exception at %s \n%s', asctime(), exception_instance)
    now = int(time())
    logging.debug('Trying to send exception message to owner.')
    while (1):
        error_text = 'Exception at %s:\n%s' % (
            asctime(),
            str(exception_instance) if len(str(exception_instance)) < 3600 else str(exception_instance)[:3600])
        try:
            offline_time = int(time()) - now
            bot.send_message(config('OWNER_ID'), error_text + '\nBot went offline for %s seconds' % offline_time)
            logging.debug('Message sent, returning to polling.')
            break
        except:
            sleep(3)


# This makes the bot unstoppable :^)
def safepolling():
    if(bot.skip_pending):
        last_update_id = bot.get_updates()[-1].update_id
    else:
        last_update_id = 0
    while(1):
        logging.debug("Getting updates using update id %s", last_update_id)
        try:
            updates = bot.get_updates(last_update_id + 1, 50)
            logging.debug('Fetched %s updates', len(updates))
            if(len(updates) > 0):
                last_update_id = updates[-1].update_id
                bot.process_new_updates(updates)
        except ApiException as api_exception:
            logging.warning(api_exception)
        except Exception as exception_instance:
            if(debug_mode):
                notify_exceptions(exception_instance)


if(__name__ == '__main__'):
    # Tell owner the bot has started.
    bot.remove_webhook()
    if(debug_mode):
        try:
            bot.send_message(config('OWNER_ID'), 'Bot Started')
        except ApiException:
            logging.critical('''Make sure you have started your bot https://telegram.me/%s.
                And configured the owner variable.''' % bot_info.username)
            exit(1)
    logging.info('Safepolling Start.')
    safepolling()

# Nothing beyond this line will be executed.
