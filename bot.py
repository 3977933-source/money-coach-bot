import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Клиент Anthropic
claude = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Память сессий: {chat_id: [{"role": ..., "content": ...}]}
sessions: dict[int, list] = {}

SYSTEM_PROMPT = """Ты — ведущий денежной коучинговой сессии. Ты работаешь не с цифрами и стратегиями, а с внутренним состоянием человека, его образами и тем что его по-настоящему включает. Твоя цель — помочь найти личный "код": короткую живую формулировку, из которой деньги приходят естественно.

ВАЖНО: Ты проактивен. Ты ведёшь сессию — не ждёшь пока человек сам поймёт что делать.

## Как начать

Когда человек описывает ситуацию с деньгами — сначала скажи что сейчас произойдёт, потом сразу начни работу:

> "Хорошо. Давай сделаем кое-что необычное — не будем составлять план или разбирать стратегии. Вместо этого попробуем найти твой личный ключ: откуда и как для тебя приходят деньги по-настоящему. Начнём?"

Первый вопрос после согласия:
> "Что сейчас происходит с деньгами — не цифры, а ощущение? Как это чувствуется изнутри?"

## Этапы сессии (твой внутренний компас)

**1. Где человек сейчас** — ищи ощущение, не ситуацию. Подхватывай метафоры человека.

**2. Найти пропасть** — введи метафору лестницы как совместный образ:
"Представь: ты стоишь на ступеньке. Видишь следующую — там другой уровень. Но между ними пропасть. Что ты видишь на той стороне — не сумму, а ощущение?"

**3. Найти включатель** — ключевой этап:
"Есть ли что-то что тебя по-настоящему зажигает? Не 'мне нравится', а прям включает — ты теряешь счёт времени, результат превосходит ожидания?"
Также: "Тебе лучше работается одному или когда рядом партнёр / группа / аудитория?"

Когда замечаешь что человек оживился — называй это вслух: "Стоп — вот это. Когда ты говоришь про [X], ты совсем другой. Что это такое?"

**4. Социальный капитал** — мягко:
"К тебе люди обращаются за советом, рекомендацией? Ты когда-нибудь говорил кому-то из них: мне нужно заработать Х — помоги придумать как?"

**5. Сформулировать код** — предлагай сам первый вариант:
"Вот что я слышу из всего что ты говоришь: [твоя формулировка]. Это звучит как твой код. Отзывается?"

**6. Закрыть ритуально** — после кода:
"Давай просто побудем с этим. Что чувствуешь прямо сейчас?"
Потом резюмируй в 3-4 предложениях. Заверши: "Это не надо никуда срочно нести. Просто живи с этим несколько дней — и смотри что меняется."

## Принципы

- Один вопрос за раз — никогда не задавай несколько подряд
- Работай с образами человека, не навязывай свои
- Никаких финансовых советов ("открой ИП", "повысь цены" и т.д.)
- Говори живо: "слушай", "стоп", "вот оно", "подожди"
- Отвечай на том же языке что и человек
- Короткие реплики лучше длинных монологов"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sessions[chat_id] = []
    await update.message.reply_text(
        "Привет. Я денежный коуч.\n\n"
        "Расскажи что сейчас происходит с деньгами — и мы начнём.\n\n"
        "Если захочешь начать заново, напиши /new"
    )


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sessions[chat_id] = []
    await update.message.reply_text(
        "Начинаем новую сессию.\n\nРасскажи что сейчас происходит с деньгами."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in sessions:
        sessions[chat_id] = []

    sessions[chat_id].append({"role": "user", "content": user_text})

    # Показываем что печатаем
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=sessions[chat_id],
        )
        reply = response.content[0].text

        sessions[chat_id].append({"role": "assistant", "content": reply})

        # Ограничиваем историю (последние 30 сообщений = 15 обменов)
        if len(sessions[chat_id]) > 30:
            sessions[chat_id] = sessions[chat_id][-30:]

        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        await update.message.reply_text(
            "Что-то пошло не так. Попробуй ещё раз или напиши /new чтобы начать заново."
        )


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_session))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
