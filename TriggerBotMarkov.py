# -*- coding: utf-8 -*-
import telebot
from peewee import *
from decouple import config
import markovify
import logging
from time import time, asctime, sleep
from telebot.apihelper import ApiException
from typing import List

__version__ = 0.01

debug_mode = config('DEBUG', cast=bool)
if(debug_mode):
    logging.basicConfig(level=logging.DEBUG)

# comment to use default timeout. (3.5)
telebot.apihelper.CONNECT_TIMEOUT = 9999

# ORM models
# TODO: use a model instead of this or add an ignored field to user table or add a table about user configs
ignored_users = []

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
    state_size = IntegerField(default=3)


# Model to store all messages
class UserMessageModel(BaseModel):
    user = ForeignKeyField(TGUserModel, 'messages')
    message_text = CharField(max_length=3000)


class GeneratedMessageModel(BaseModel):
    user = ForeignKeyField(TGUserModel, 'generated_messages')
    message_text = CharField(max_length=3000)


# Create database file if it doesn't exists.
db.create_tables([TGUserModel, UserMessageModel, GeneratedMessageModel], safe=True)
# Bot instance initialization.
bot = telebot.TeleBot(config('BOT_TOKEN'))


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


# Tries to generate a response, if it already exists, then return none
def create_message_or_reject(tguser: TGUserModel, state_size=3) -> str:
    # Get all user messages
    user_messages = UserMessageModel.select(UserMessageModel.message_text).where(UserMessageModel.user == tguser)
    if (not user_messages.count()):
        logging.info("No messages found from {}[{}]".format(tguser.first_name, tguser.chat_id))
        return None
    total_messages = user_messages.count()
    logging.info("Fetched {} messages from {}[{}]".format(total_messages, tguser.first_name, tguser.chat_id))
    # Markov chain generation.
    markov_feed = '\n'.join([user_message.message_text for user_message in user_messages])
    text_model = markovify.NewlineText(markov_feed, state_size=state_size)
    result = text_model.make_short_sentence(255)
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
Hi, just add me to any group and wait until i start to learning from your members.
I will answer every time i can generate a response.
You can try /stats
'''


@bot.message_handler(commands=['start', 'help'])
def greet_user(message: telebot.types.Message):
    bot.reply_to(message, bot_help_text)


@bot.message_handler(commands=['stats'])
def send_user_statistics(message: telebot.types.Message):
    user_obj = get_user_from_message(message)
    message_count = user_obj.messages.count()
    generated_messages = user_obj.generated_messages.count()
    message_count_text = "Hi, i have {} messages from you\n".format(message_count)
    if(generated_messages):
        message_response_text = "and i generated {} responses from your messages :)".format(generated_messages)
    else:
        message_response_text = "but i never generated a response from your messages :("
    bot.reply_to(message, message_count_text + message_response_text)


@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(message, about_message, parse_mode="Markdown")


@bot.message_handler(commands=['trigger'])
def generate_response(message):
    user_obj = get_user_from_message(message)
    if(user_obj.messages.count() > 100):
        for _ in range(100):
            response = create_message_or_reject(user_obj, 2)
            if(response):
                bot.reply_to(message, response)
                return
        bot.reply_to(message, "Not this time, please talk more.")
    else:
        bot.reply_to(message, "I need at least 100 messages from you. :(")


@bot.message_handler(commands=['ignoreme'])
def ignore_user(message: telebot.types.Message):
    if(message.from_user.id in ignored_users):
        ignored_users.remove(message.from_user.id)
        bot.reply_to(message, "Ok, i'll start to answer your messages.")
    else:
        ignored_users.append(message.from_user.id)
        bot.reply_to(message, "Ah ok, nvm cya :)")


# Try to reply to every text message
@bot.message_handler(func=lambda m: True)
def reply_intent(message: telebot.types.Message):
    if(message.content_type == "text" and not message.text.startswith('/') and message.text.count(' ') >= 2):
        if(message.from_user.id in ignored_users):
            return
        user_obj = get_user_from_message(message)
        response = create_message_or_reject(user_obj)
        if(response):
            bot.reply_to(message, response)


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
            sleep(0.25)


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
    # Bot starts here.
    logging.info('Bot started.')
    try:
        logging.debug('Bot username:[%s]' % bot.get_me().username)
    except ApiException:
        logging.critical('The given token [%s] is invalid, please fix it')
        exit(1)
    # Tell owner the bot has started.
    if(debug_mode):
        try:
            bot.send_message(config('OWNER_ID'), 'Bot Started')
        except ApiException:
            logging.critical('''Make sure you have started your bot https://telegram.me/%s.
                And configured the owner variable.''' % bot.get_me().username)
            exit(1)
    logging.info('Safepolling Start.')
    safepolling()

# Nothing beyond this line will be executed.
