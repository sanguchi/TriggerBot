# -*- coding: utf-8 -*-
import telebot
from peewee import *
from decouple import config
import markovify
import logging
from time import time, asctime, sleep
from telebot.apihelper import ApiException
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, User, CallbackQuery
from typing import List
import random

# VERSION 0.3: removed 100 messages limit, removed chain size and text size(defaults 3 and 1024), added algorithm and group settings.
# VERSION 0.2: removed ignored users array and added chance field on user model, and a settings panel.
# TODO: Inline buttons
__version__ = 0.2

debug_mode = config('DEBUG', cast=bool)
if(debug_mode):
    logging.basicConfig(level=logging.DEBUG)

# comment to use default timeout. (3.5)
telebot.apihelper.CONNECT_TIMEOUT = 9999


markov_algorithms = ["all_messages", "last_message"]
# Define database connector, comment/uncomment what you want to use.
# db = PostgresqlDatabase(config('PG_DTBS'), user=config('PG_USER'), password=config('PG_PASS'), host=config('PG_HOST'))
db = SqliteDatabase('{}.db'.format(__file__))
# db = MySQLDatabase(config('PG_DTBS'), user=config('PG_USER'), password=config('PG_PASS'), host=config('PG_HOST'), charset='utf8mb4')


# Base class, every model inherits the database connector
class BaseModel(Model):
    class Meta:
        database = db


# Telegram user model
class TGUserModel(BaseModel):
    # Telegram data
    chat_id = CharField()
    first_name = CharField()
    username = CharField(null=True)
    language_code = CharField(default="en")
    # Markov settings
    # Chances of getting a response automatically. 10/50/90 % /mute for 0
    autoreply_chance = IntegerField(default=0)
    # Fixed chance of replying after 50/200/1000/5000 messages /mute for 0
    autoreply_fixed = IntegerField(default=200)
    # True for random chance | False for fixed
    random_autoreply = BooleanField(default=True)
    markov_algorithm = CharField(default="last_message", choices=markov_algorithms)


# Model to store all messages
class UserMessageModel(BaseModel):
    user = ForeignKeyField(TGUserModel, backref='messages')
    message_id = CharField()
    chat_id = CharField()
    message_text = CharField(max_length=4000)


class GeneratedMessageModel(BaseModel):
    user = ForeignKeyField(TGUserModel, backref='generated_messages')
    chat_id = CharField(default="")
    message_text = CharField(max_length=1000)


# Store group admins and settings.
class GroupSettings(BaseModel):
    user = ForeignKeyField(TGUserModel)
    chat_id = CharField()
    override_settings = BooleanField(default=False)
    admins = ManyToManyField(TGUserModel, backref="groups")


# Create database file if it doesn't exists.
db.create_tables([TGUserModel, UserMessageModel, GeneratedMessageModel, GroupSettings,
                  GroupSettings.admins.get_through_model()], safe=True)

# Bot instance initialization.
bot = telebot.TeleBot(config('BOT_TOKEN'))

# Bot starts here.
logging.info('Bot started.')
try:
    bot_info = bot.get_me()
    logging.debug('{bot_info.first_name} @{bot_info.username}[{bot_info.id}]'.format(bot_info=bot_info))
except ApiException:
    logging.critical('The given token [{0}] is invalid, please fix it'.format(config('BOT_TOKEN')))
    exit(1)


# Return a TGUser instance based on telegram message instance.
def get_user_from_message(message: telebot.types.Message) -> TGUserModel:
    if(message.forward_from):
        logging.debug("Received a forwarded message.")
        user = message.forward_from  # If it was forwarder from a user, return forwarded message's user.
    elif(message.reply_to_message):
        logging.debug("Received a replied message.")
        user = message.reply_to_message.from_user  # If reply, user is resolved from the replied message.
    else:
        logging.debug("Received a normal message.")
        user: User = message.from_user   # Resolve user as message sender
    # Search user on database or create if it doesn't exists
    logging.debug("Using user {user.id} from message {message.message_id}".format(user=user, message=message))
    try:
        db_user: TGUserModel = TGUserModel.get(chat_id=user.id)
    # Update/Fill nickname and username
    except DoesNotExist:
        logging.debug("Creating user {user.id} {user.first_name} {user.username} {user.language_code}".format(user=user))
        db_user = TGUserModel.create(
            chat_id=user.id,
            first_name=user.first_name,
            username=user.username if user.username else None,
            language_code=user.language_code if user.language_code else 'en')
    return db_user


def get_group_from_message(message: Message) -> GroupSettings:
    # Create TGUser with group info. (YES i store chat groups as users)
    group_obj, created = TGUserModel.get_or_create(chat_id=message.chat.id, first_name=message.chat.title, username=message.chat.username)
    try:
        group_settings: GroupSettings = GroupSettings.get(GroupSettings.user == group_obj)
    except DoesNotExist:
        group_settings = GroupSettings.create(user=group_obj, chat_id=message.chat.id)
        admins_id = [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]
        group_settings.admins = TGUserModel.select().where(TGUserModel.chat_id.in_(admins_id))
    return group_settings


# Add every text message to the database
def text_model_processor(messages: List[Message]):
    # logging.info("Processing %s new messages", len(messages))
    data_source = []
    for message in messages:
        # Only process text messages that are not commands and contains at least 3 words.
        if message.content_type == "text" and not message.text.startswith('/') and message.text.count(' ') >= 2:
            user = get_user_from_message(message)
            data_source.append({
                'user': user, 'message_text': message.text.lower(),
                'message_id': message.message_id, 'chat_id': message.chat.id
            })
            # UserMessageModel.create(user=user, message_text=message.text).save()
    logging.info("Saving {} text messages to the database".format(len(data_source)))
    if(data_source):
        with db.atomic():
            UserMessageModel.insert_many(data_source).execute()


bot.set_update_listener(text_model_processor)

# GLOBAL MESSAGES SECTION.
about_message = '''
TriggerBot *%s*
[Source Code on Github](https://github.com/sanguchi/TriggerBot/)
[Give me 5 Stars](https://telegram.me/storebot?start=TriggerResponseBot)
Author: @Pekatarina
''' % __version__

bot_help_text = '''
Hi, i'm *Trigger!*, i can learn from people's messages and chat like them.
If you want me to generate a message, you can mention me, say my nickname, reply to any of my messages, or use:
`/trigger`
'''

settings_text = '''
{user.first_name}[{user.chat_id}]:
Messages sent: {messages} | generated: {generated}
Markov Algorithm: {algorithm} | Autoreply: {method}|{value}
'''

# When bot is added to group, get all admins and add them to internal admin list for this group
@bot.message_handler(content_types=['new_chat_members'])
def bot_added_to_chat(message: Message):
    if(any([user.id == bot_info.id for user in message.new_chat_members])):
        logging.info("Bot added to group {message.chat.id} {message.chat.title} by {message.from_user.id} {message.from_user.first_name}".format(message=message))
        get_group_from_message(message)


def is_private_chat(message: Message):
    return message.chat.type == 'private'


@bot.message_handler(commands=['start', 'help'], func=is_private_chat)
def greet_user(message: Message):
    bot.reply_to(message, bot_help_text, parse_mode="Markdown")


@bot.message_handler(commands=['about'], func=is_private_chat)
def about(message: Message):
    bot.reply_to(message, about_message, parse_mode="Markdown")


def get_statistics(user_obj: TGUserModel):
    message_count = user_obj.messages.count()
    generated_messages = user_obj.generated_messages.count()
    algorithm = user_obj.markov_algorithm
    method = "Random" if user_obj.random_autoreply else "Fixed"
    value = user_obj.autoreply_chance if user_obj.random_autoreply else user_obj.autoreply_fixed
    return settings_text.format(
        user=user_obj, messages=message_count, generated=generated_messages,
        algorithm=algorithm, method=method, value=value
    )


def generate_settings_keyboard(user_obj: TGUserModel):
    keyboard = InlineKeyboardMarkup(4)
    if(user_obj.random_autoreply):
        autoreply_type: InlineKeyboardButton = InlineKeyboardButton('Change autoreply to fixed', None, 'autoreply')
        chances: List[InlineKeyboardButton] = [
            InlineKeyboardButton(str(chance), None, str(chance)) for chance in [0, 10, 50, 90]
        ]
    else:
        autoreply_type: InlineKeyboardButton = InlineKeyboardButton('Change autoreply to random', None, 'autoreply')
        chances: List[InlineKeyboardButton] = [
            InlineKeyboardButton(str(chance), None, str(chance)) for chance in [0, 20, 200, 2000]
        ]
    keyboard.add(autoreply_type)
    keyboard.add(*chances)
    keyboard.add(InlineKeyboardButton("Markov Algorithm", None, 'algorithm'), InlineKeyboardButton("X", None, "close"))
    return keyboard


def get_group_statistics(group: GroupSettings):
    message_count = UserMessageModel.select().where(UserMessageModel.chat_id==group.chat_id).count()
    generated_messages = GeneratedMessageModel.select().where(GeneratedMessageModel.chat_id == group.chat_id).count()
    algorithm = group.user.markov_algorithm
    method = "Random" if group.user.random_autoreply else "Fixed"
    value = group.user.autoreply_chance if group.user.random_autoreply else group.user.autoreply_fixed
    return settings_text.format(
        user=group.user, messages=message_count, generated=generated_messages,
        algorithm=algorithm, method=method, value=value
    ) + "\nOverride User Settings: {}".format("YES" if group.override_settings else "NO")


def group_keyboard(group: GroupSettings, admin: TGUserModel):
    keyboard = InlineKeyboardMarkup(4)
    if(group.user.random_autoreply):
        autoreply_type: InlineKeyboardButton = InlineKeyboardButton('Change autoreply to fixed', None, 'group_autoreply')
        chances: List[InlineKeyboardButton] = [
            InlineKeyboardButton(str(chance), None, 'group_{}'.format(chance)) for chance in [0, 10, 50, 90]
        ]
    else:
        autoreply_type: InlineKeyboardButton = InlineKeyboardButton('Change autoreply to random', None, 'group_autoreply')
        chances: List[InlineKeyboardButton] = [
            InlineKeyboardButton(str(chance), None, 'group_{}'.format(chance)) for chance in [0, 20, 200, 2000]
        ]
    override_button: InlineKeyboardButton = InlineKeyboardButton('Toggle Override User Settings', None, 'group_override')
    keyboard.add(autoreply_type)
    keyboard.add(*chances)
    keyboard.add(InlineKeyboardButton("Markov Algorithm", None, 'group_algorithm'), override_button)
    keyboard.add(InlineKeyboardButton("See personal settings", None, "personal_{}".format(admin.chat_id)), InlineKeyboardButton("X", None, "close"))
    return keyboard


@bot.message_handler(commands=['settings'])
def send_user_statistics(message: Message):
    user_obj: TGUserModel = get_user_from_message(message)
    keyboard: InlineKeyboardMarkup = None
    stats: str = get_statistics(user_obj)
    # If private chat
    if(is_private_chat(message)):
        logging.debug('Settings in private chat')
        keyboard: InlineKeyboardMarkup = generate_settings_keyboard(user_obj)
    if(message.chat.type in ['group', 'supergroup']):
        group: GroupSettings = GroupSettings.get(GroupSettings.chat_id == message.chat.id)
        if (user_obj in group.admins):
            stats = get_group_statistics(group)
            keyboard = group_keyboard(group, user_obj)
    bot.reply_to(message, stats, reply_markup=keyboard)


# Mute is shortcut to setting all chances to zero, for groups and users.
@bot.message_handler(commands=['mute'])
def mute_bot(message: Message):
    user_obj: TGUserModel = get_user_from_message(message)
    if(message.chat.type in ['group', 'supergroup']):
        group: GroupSettings = GroupSettings.get(GroupSettings.chat_id == message.chat.id)
        if (user_obj in group.admins):
            group.override_settings = True
            group.user.autoreply_chance = 0
            group.user.autoreply_fixed = 0
            group.save()
            bot.reply_to(message, "I will not reply randomly anymore.")
        else:
            user_obj.autoreply_chance = 0
            user_obj.autoreply_fixed = 0
            bot.reply_to(message, "I will not randomly reply to your messages anymore.")
    else:
        user_obj.autoreply_chance = 0
        user_obj.autoreply_fixed = 0
        bot.reply_to(message, "I will not randomly reply to your messages anymore.")
    user_obj.save()


# Message fetching algorithm
def fetch_all_messages(user: TGUserModel, group: GroupSettings = None):
    if(group is None):
        logging.debug("Fetching {} messages from user {}".format(user.messages.count(), user.chat_id))
        return [message.message_text for message in user.messages]
    chat_messages = UserMessageModel.select().where(UserMessageModel.chat_id == group.chat_id)
    logging.debug("Fetching {} messages from chat {}".format(chat_messages.count(), group.chat_id))
    return [message.message_text for message in chat_messages]


def fetch_latest_messages(user: TGUserModel, group: GroupSettings = None):
    if(group is None):
        logging.debug("Fetching {} messages from user {}".format(user.messages.limit(100).count(), user.chat_id))
        return [message.message_text for message in user.messages.limit(100)]
    chat_messages = UserMessageModel.select().where(UserMessageModel.chat_id == group.chat_id).limit(100)
    logging.debug("Fetching {} messages from chat {}".format(chat_messages.count(), group.chat_id))
    return [message.message_text for message in chat_messages]


def fetch_all_included(user: TGUserModel, keyword: str, group: GroupSettings = None):
    if(group is None):
        selected_messages = UserMessageModel.select().where((UserMessageModel.user == user) & (UserMessageModel.message_text.contains(keyword)))
        logging.debug("Fetching {} messages from user {}".format(selected_messages.count(), user.chat_id))
        return [message.message_text for message in selected_messages]
    selected_messages = UserMessageModel.select().where((UserMessageModel.chat_id == group.chat_id) & UserMessageModel.message_text.contains(keyword))
    logging.debug("Fetching {} messages from chat {}".format(selected_messages.count(), group.chat_id))
    return [message.message_text for message in selected_messages]


def fetch_messages(user: TGUserModel, group: GroupSettings = None, keyword: str = None) -> List[str]:
    if(keyword):
        return fetch_all_included(user, keyword, group)
    if(user.markov_algorithm == "last_message"):
        return fetch_latest_messages(user, group)
    else:
        return fetch_all_messages(user, group)


# Tries to return a short dumb response, if it already exists, return none
def generate_markov(messages: List[str]) -> str:
    if(not messages):
        return None
    # More messages from db means more complex responses.
    if(len(messages) < 100):
        state_size = 1
    elif(500 > len(messages) >= 100):
        state_size = 2
    else:
        state_size = 3
    text_model = markovify.NewlineText(messages, state_size=state_size)
    result = text_model.make_short_sentence(1024)
    return result


def check_duplicated(message_text: str, user: TGUserModel, group: GroupSettings = None):
    chat_id = user.chat_id
    if(group):
        chat_id = group.chat_id
    response, created = GeneratedMessageModel.get_or_create(user=user, message_text=message_text, chat_id=chat_id)
    if(created):
        logging.debug("New message: %s" % response.message_text)
    return not created


@bot.message_handler(commands=['trigger'])
def trigger_bot(message: Message):
    keyword = message.text.split(' ')
    user_obj: TGUserModel = get_user_from_message(message)
    group = get_group_from_message(message) if message.chat.type != 'private' else None
    keyword = ' '.join(keyword[1:]) if(len(keyword) >= 2) else None
    generated_message = generate_markov(fetch_messages(user_obj, group, keyword))
    if(generated_message and not check_duplicated(generated_message, user_obj, group)):
        bot.reply_to(message, generated_message)
    else:
        bot.reply_to(message, "<i>Cannot generate a message, please talk more.</i>", parse_mode="HTML")


def should_reply(user: TGUserModel, group: GroupSettings = None) -> bool:
    if(group and group.override_settings):
        if(group.user.random_autoreply and group.user.autoreply_chance is not 0):
            chances = random.randint(1, 100)
            logging.debug("random number: {} autoreply chance: {}".format(chances, group.user.autoreply_chance))
            return chances <= group.user.autoreply_chance
        else:
            counter = UserMessageModel.select().where(UserMessageModel.chat_id == group.chat_id).count()
            logging.debug("message counter: {} autoreply fixed: {}".format(counter, group.user.autoreply_fixed))
            return counter % group.user.autoreply_fixed is 0 if group.user.autoreply_fixed is not 0 else False
    else:
        if (user.random_autoreply and user.autoreply_chance is not 0):
            chances = random.randint(1, 100)
            logging.debug("random number: {} autoreply chance: {}".format(chances, user.autoreply_chance))
            return chances <= user.autoreply_chance
        else:
            counter = user.messages.count()
            logging.debug("message counter: {} autoreply fixed: {}".format(counter, user.autoreply_fixed))
            return counter % user.autoreply_fixed is 0 if user.autoreply_fixed is not 0 else False


@bot.message_handler(regexp='{}|{}'.format(bot_info.first_name, bot_info.username))
def reply_on_mention(message: Message):
    user_obj: TGUserModel = get_user_from_message(message)
    group: GroupSettings = get_group_from_message(message) if message.chat.type != 'private' else None
    if(group and group.override_settings):  # Use group's settings
        settings: TGUserModel = group.user
    else:
        group = None
        settings = user_obj
    generated_message = generate_markov(fetch_messages(settings, group))
    if (generated_message and not check_duplicated(generated_message, user_obj, group)):
        bot.reply_to(message, generated_message)


@bot.message_handler(content_types=['text'], func=lambda m: m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id)
def reply_on_reply(message: Message):
    reply_on_mention(message)  # I'm not lazy, i just realized that i was about to rewrite that function again but only for replies.


# Try to reply to every text message
@bot.message_handler(content_types=['text'])
def reply_intent(message: Message):
    user_obj: TGUserModel = get_user_from_message(message)
    group: GroupSettings = get_group_from_message(message) if message.chat.type != 'private' else None
    if (group and group.override_settings):  # Use group's settings
        settings: TGUserModel = group.user
    else:
        group = None
        settings = user_obj
    if(should_reply(settings, group)):
        generated_message = generate_markov(fetch_messages(settings, group))
        if (generated_message and not check_duplicated(generated_message, user_obj, group)):
            bot.reply_to(message, generated_message)


def get_user_from_callback(query: CallbackQuery) -> TGUserModel:
    try:
        db_user: TGUserModel = TGUserModel.get(chat_id=query.from_user.id)
    except DoesNotExist:
        db_user = TGUserModel.create(
            chat_id=query.from_user.id,
            first_name=query.from_user.first_name.lower(),
            username=query.from_user.username.lower() if query.from_user.username else None,
            language_code=query.from_user.language_code)
    return db_user

# INLINE BUTTONS
@bot.callback_query_handler(func=lambda q: q.data in ["0", "10", "20", "50", "90", "200", "2000"])
def set_autoreply_chance(query: CallbackQuery):
    db_user: TGUserModel = get_user_from_callback(query)
    if(db_user.random_autoreply):
        db_user.autoreply_chance = int(query.data)
        bot.answer_callback_query(query.id, "Random chances set to {}%".format(query.data))
    else:
        db_user.autoreply_fixed = int(query.data)
        bot.answer_callback_query(query.id, "Fixed chances set to {}%".format(query.data))
    db_user.save()

    bot.edit_message_text(
        get_statistics(db_user),
        query.from_user.id,
        query.message.message_id,
        reply_markup=generate_settings_keyboard(db_user))


@bot.callback_query_handler(func=lambda q: q.data == 'close')
def close_settings_keyboard(query: CallbackQuery):
    bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, reply_markup=None)


@bot.callback_query_handler(func=lambda q: q.data == 'autoreply')
def toggle_autoreply_type(query: CallbackQuery):
    db_user: TGUserModel = get_user_from_callback(query)
    db_user.random_autoreply = not db_user.random_autoreply
    db_user.save()
    bot.edit_message_text(
        get_statistics(db_user),
        query.from_user.id,
        query.message.message_id,
        reply_markup=generate_settings_keyboard(db_user))


@bot.callback_query_handler(func=lambda q: q.data == 'algorithm')
def toggle_fetch_algorithm(query: CallbackQuery):
    db_user: TGUserModel = get_user_from_callback(query)
    logging.debug("user {} alg: {}".format(db_user.chat_id, db_user.markov_algorithm))
    db_user.markov_algorithm = "last_message" if db_user.markov_algorithm == "all_messages" else "all_messages"
    db_user.save()
    bot.edit_message_text(
        get_statistics(db_user),
        query.from_user.id,
        query.message.message_id,
        reply_markup=generate_settings_keyboard(db_user))

# GROUP INLINE BUTTONS FOR ADMINS
@bot.callback_query_handler(func=lambda q: q.data.startswith('group_') and q.data.split('_')[1] in ["0", "10", "20", "50", "90", "200", "2000"])
def set_autoreply_chance(query: CallbackQuery):
    user_obj: TGUserModel = get_user_from_callback(query)
    group: GroupSettings = get_group_from_message(query.message)
    chances = int(query.data.split('_')[1])
    if (user_obj in group.admins):
        if(group.user.random_autoreply):
            group.user.autoreply_chance = chances
            bot.answer_callback_query(query.id, "Random chances set to {}%".format(chances))
        else:
            group.user.autoreply_fixed = chances
            bot.answer_callback_query(query.id, "Fixed chances set to {}%".format(chances))
        group.user.save()
        bot.edit_message_text(
            get_group_statistics(group),
            query.message.chat.id,
            query.message.message_id,
            reply_markup=group_keyboard(group, user_obj))
    else:
        bot.answer_callback_query(query.id)


@bot.callback_query_handler(func=lambda q: q.data == "group_override")
def toggle_group_override(query: CallbackQuery):
    user_obj: TGUserModel = get_user_from_message(query.message)
    group: GroupSettings = get_group_from_message(query.message)
    if (user_obj in group.admins):
        group.override_settings = not group.override_settings
        group.save()
        bot.edit_message_text(
            get_group_statistics(group),
            query.message.chat.id,
            query.message.message_id,
            reply_markup=group_keyboard(group, user_obj))


@bot.callback_query_handler(func=lambda q: q.data == 'group_algorithm')
def toggle_group_fetch_algorithm(query: CallbackQuery):
    user_obj: TGUserModel = get_user_from_message(query.message)
    group: GroupSettings = get_group_from_message(query.message)
    if (user_obj in group.admins):
        group.user.markov_algorithm = "last_message" if group.user.markov_algorithm == "all_messages" else "all_messages"
        group.user.save()
        bot.edit_message_text(
            get_group_statistics(group),
            query.message.chat.id,
            query.message.message_id,
            reply_markup=group_keyboard(group, user_obj))


@bot.callback_query_handler(func=lambda q: q.data == "group_autoreply")
def toggle_group_autoreply_type(query: CallbackQuery):
    user_obj: TGUserModel = get_user_from_message(query.message)
    group: GroupSettings = get_group_from_message(query.message)
    if(user_obj in group.admins):
        group.user.random_autoreply = not group.user.random_autoreply
        group.user.save()
        bot.edit_message_text(
            get_group_statistics(group),
            query.message.chat.id,
            query.message.message_id,
            reply_markup=group_keyboard(group, user_obj))
    else:
        bot.answer_callback_query(query.id)


@bot.callback_query_handler(func=lambda q: q.data.startswith("personal_"))
def show_user_statistics(query: CallbackQuery):
    user_obj: TGUserModel = TGUserModel.get(TGUserModel.chat_id == query.data.split("_")[1])
    bot.edit_message_text(
        get_statistics(user_obj),
        query.message.chat.id,
        query.message.message_id,
        reply_markup=None)


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
