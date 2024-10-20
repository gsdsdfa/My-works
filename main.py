import telebot
from telebot import types

bot = telebot.TeleBot('')

CHANNEL_ID = "-1001607712686"  # Replace with your channel ID
nonte = "1756650011"


@bot.message_handler(commands=['start'])
def start(message):
    channel_link = "https://t.me/julia_sorokina_coaching"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard = types.KeyboardButton(text="Подписался")
    markup.add(keyboard)
    chat_id = message.chat.id
    user = message.chat.first_name

    bot.send_message(chat_id, f"Чтобы забрать свой подарок подпишись на мой канал 💫\n"
                              f"\n"
                              f"Здесь ты найдешь:\n"

                              f"- ежедневную мотивацию\n"

                              f"- вопросы и техники самокоучинга\n"

                              f"- эффективные инструменты по постановке целей и их достижению\n"

                              f"- техники планирования и увеличения производительности\n"

                              f"- практики и техники поиска любимого дела и предназначения\n"

                              f"- техники на поддержание ресурсного состояния\n"
                              f"- чек-листы и гайды с наглядной информацией.\n"
                              f"-интенсивы и марафоны на актуальные темы.\n"

                              f"{channel_link}", reply_markup=markup)


@bot.message_handler(content_types=['text'])
def text(message):
    if message.text == "Подписался":
        chat_member = bot.get_chat_member(CHANNEL_ID, message.from_user.id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            fzan(message)

        else:
            bot.send_message(message.chat.id, "Вы не подписаны на канал!")


def fzan(message):
    bot.send_message(message.chat.id,
                     f"Лови мой подарок «Гайд по прокачке самоценности и развитию уверенности в себе» 💫 \n"
                     f"\n"
                     f"И не выключай уведомления, чтобы не пропустить по-настоящему важные активности и события. \n",
                     reply_markup=types.ReplyKeyboardRemove()
                     )
    file = open('Подарок.pdf', 'rb')
    bot.send_document(message.chat.id, file)
    osnov(message)
def osnov(message):
    lllal = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_a = types.KeyboardButton(text='Ознакомиться с моими услугами')
    button_b = types.KeyboardButton(text='Ознакомиться с моими воркбуками')
    lllal.add(button_a, button_b)
    bot.send_message(message.chat.id,f"Друзья, всем привет! Меня зовут Юлия, и я - психолог и женский life-коуч.\n"
                     f"\n"
                     f"Моя миссия помогать людям менять свое мышление с ограничений на возможности, выстраивать гармоничные отношения с собой и окружающими, ставить амбициозные цели и достигать их. Я готова стать наставником и проводником для тех, кто действительно хочет изменить свою жизнь в лучшую сторону, сделать ее ярче и добиться выдающихся результатов.\n"
                     f"\n"
                     f"Немного о себе:\n"
                     f"⚡️ получила диплом педагога-психолога\n"
                     f"⚡️ получила сертификаты по коучингу:\n"
                     f"- детско-родительских отношений "
                     f"- семейных отношений"     
                     f"- предназначения"
                     f"- Life-коучингу"
                     f"- бизнес-коучингу"                
                     f"⚡️ Прошла обучение на ментора-наставника.\n"
                     f"⚡️ 2,5 года опыта в психологическом консультировании;\n"
                     f"⚡️ Опыт проведения тренингов для детей начальных классов;\n"
                     f"⚡️ Опыт проведения командообразующих тренингов в крупной телеком организации;\n"
                     f"⚡️ Создала свое сообщество и развиваю его, провожу здесь марафоны, интенсивы и челленджи;\n"
                     f"⚡️ Создала 5 своих воркбуков и активно провожу по ним обучение.\n",
                     reply_markup=lllal
                     )
    bot.register_next_step_handler(message, vvvzzz)
def vvvzzz(message):

    if message.text == 'Ознакомиться с моими воркбуками':
        vvzz(message)
    elif message.text == 'Ознакомиться с моими услугами':
        aass(message)

def vvzz(message):
    lllal1 = types.InlineKeyboardMarkup()
    far = types.InlineKeyboardButton(text="Самоценность", callback_data='samo')
    sar = types.InlineKeyboardButton(text="Превращай мечты в цели", callback_data='pre')
    tar = types.InlineKeyboardButton(text="Любовь к себе", callback_data='lub')
    fir = types.InlineKeyboardButton(text="Достижение цели", callback_data='dost')
    fii = types.InlineKeyboardButton(text="Женственность", callback_data='zhens')
    kol = types.InlineKeyboardButton(text="Назад", callback_data='back1')
    lllal1.add(far)
    lllal1.add(sar)
    lllal1.add(tar)
    lllal1.add(fir)
    lllal1.add(fii)
    lllal1.add(kol)
    bot.send_message(message.chat.id, 'Выберите воркбук:',reply_markup=lllal1)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    message = call.message
    if call.data == 'back':
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id - 0)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 400 and 'message to delete not found' in e.description:
                pass  # Ignore if the message has already been deleted
    elif call.data == 'back1':
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id - 0)
            bot.delete_message(call.message.chat.id, call.message.message_id - 1)
            bot.delete_message(call.message.chat.id, call.message.message_id - 2)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 400 and 'message to delete not found' in e.description:
                pass  # Ignore if the message has already been deleted
        osnov(message)  # вызываем функцию vvzz
    elif call.data == 'samo':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./firstphoto.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'pre':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./fivephoto.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'lub':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./fourphoto.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'dost':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./secondphoto.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'zhens':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./thirdphoto.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'samo1':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./dia.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'pre1':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./mak.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'lub1':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./masterjpg.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'dost1':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./kou3.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)
    elif call.data == 'zhens1':
        lllal2 = types.InlineKeyboardMarkup()
        fora = types.InlineKeyboardButton(text="Назад", callback_data='back')
        fare1 = types.InlineKeyboardButton(text="Заказать", url="https://t.me/sorokina_juliya")
        lllal2.add(fare1, fora)
        file = open('./kou1.jpg', 'rb')
        bot.send_photo(message.chat.id, file, reply_markup=lllal2)

def aass(message):
        lllal1 = types.InlineKeyboardMarkup()
        far = types.InlineKeyboardButton(text="Диагностическая сессия", callback_data='samo1')
        sar = types.InlineKeyboardButton(text="Мак-сессия", callback_data='pre1')
        tar = types.InlineKeyboardButton(text="Мастермайнд", callback_data='lub1')
        fir = types.InlineKeyboardButton(text="Коучинговое сопровождение - 1 месяц", callback_data='dost1')
        fii = types.InlineKeyboardButton(text="Коучинговое сопровождение - 3 месяца", callback_data='zhens1')
        kol = types.InlineKeyboardButton(text="Назад", callback_data='back1')
        lllal1.add(far)
        lllal1.add(sar)
        lllal1.add(tar)
        lllal1.add(fir)
        lllal1.add(fii)
        lllal1.add(kol)
        bot.send_message(message.chat.id, 'Выберите услугу:', reply_markup=lllal1)
    
bot.polling(none_stop=True)
