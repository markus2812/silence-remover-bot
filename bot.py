import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from pydub import AudioSegment
from pydub.silence import split_on_silence

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Тут встав свій токен, бро.
# Або краще задай його як змінну оточення BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Йо! Кидай сюди аудіофайл, а я виріжу з нього всю зайву тишу. Зробимо звук чітким! 🎧"
    )

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⏳ Отримав файл. Качаю..."
    )

    try:
        # Отримуємо файл (voice або audio)
        if update.message.voice:
            file_id = update.message.voice.file_id
            file_ext = ".ogg"
            original_filename = f"voice_{file_id}.ogg"
        else:
            file_id = update.message.audio.file_id
            file_name = update.message.audio.file_name
            if file_name:
                original_filename = file_name
                file_ext = os.path.splitext(file_name)[1]
            else:
                original_filename = f"audio_{file_id}.mp3"
                file_ext = ".mp3"

        new_file = await context.bot.get_file(file_id)
        
        # Завантажуємо
        input_path = f"input_{file_id}{file_ext}"
        await new_file.download_to_drive(input_path)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text="✂️ Обробляю аудіо... Це може зайняти трохи часу."
        )

        # Магія pydub
        sound = AudioSegment.from_file(input_path)
        
        # Параметри для пошуку тиші (можна підкрутити під конкретні потреби)
        # min_silence_len: мінімальна довжина тиші в мс (наприклад, 500 мс)
        # silence_thresh: поріг тиші в dBFS (наприклад, -40)
        # keep_silence: скільки тиші лишити (наприклад, 100 мс для м'якості)
        chunks = split_on_silence(
            sound, 
            min_silence_len=500,
            silence_thresh=-40,
            keep_silence=100
        )

        if not chunks:
             await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text="⚠️ Щось пішло не так. Не зміг знайти тишу або розбити файл."
            )
             # Прибираємо сміття
             if os.path.exists(input_path):
                os.remove(input_path)
             return

        # Склеюємо назад
        output_sound = AudioSegment.empty()
        for chunk in chunks:
            output_sound += chunk

        output_path = f"processed_{file_id}.mp3"
        output_sound.export(output_path, format="mp3")

        # Відправляємо назад
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(output_path, 'rb'),
            filename=original_filename,
            caption="✅ Готово! Тишу вирізано."
        )

        # Чистимо за собою
        os.remove(input_path)
        os.remove(output_path)
        
        # Видаляємо повідомлення про статус, щоб не засмічувати чат
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id
        )

    except Exception as e:
        logging.error(f"Error: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text=f"❌ Сталася помилка: {e}"
        )
        # На всяк випадок чистимо, якщо файли лишились
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)

if __name__ == '__main__':
    if TOKEN == "YOUR_TOKEN_HERE":
        print("⚠️ Бро, не забудь вставити токен бота в код або змінну оточення!")
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    audio_handler = MessageHandler(filters.AUDIO | filters.VOICE, process_audio)
    
    application.add_handler(start_handler)
    application.add_handler(audio_handler)
    
    print("Bot started! (Бот запущено)")
    application.run_polling()

