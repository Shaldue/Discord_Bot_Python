import disnake
from disnake.ext import commands, tasks
import json
import requests
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

bot = commands.Bot(command_prefix="/",
                   intents=disnake.Intents.all(),
                   activity=disnake.Game(name="В разработке"))

with open('config.json') as f:
    config = json.load(f)

token = config['botToken']
version = config['version']
useGifs = config['useGifs']
useImages = config['useImages']

#///////EVENTS///////#
#-------------------->
@bot.event
async def on_ready():
    
    await loadBD()
    
    print(f"Bot {bot.user} is ready to work!")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    await writeMessageInSQL(message)
#///////COMMANDS///////#
#---------------------->
@bot.slash_command(description="Информация о сервере",)
async def server(inter):
    await inter.response.send_message(
        f"Название сервера: {inter.guild.name}\nВсего участников: {inter.guild.member_count}"
    )

@bot.slash_command(description="Информация о боте",)
async def info(inter):
    global version
    global useGifs
    global useImages
    await inter.response.send_message(
        f"Версия Бота: {version}\nИспользовать GIFs: {useGifs}\nИспользовать IMGs: {useImages}"
    )

@bot.slash_command(description="Сформировать графики",)
async def graphs(inter):
    
    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/userMessages.db')
    cursor = connection.cursor()

    x = np.arange(5)
    height = []
    userNames = []

    date = datetime.now().date()
   
    cursor.execute(f'''SELECT 
        guild,
        username,
        COUNT(DISTINCT message) AS countMessages
        FROM messages
        WHERE guild = "{inter.guild.name}"
        GROUP BY username
        ORDER BY countMessages DESC
        LIMIT 5
        ''')
    all_results = cursor.fetchall()
    for row in all_results:
        height.append(row[2])
        userNames.append(row[1])

    fig = plt.figure(figsize = (10, 5))
    
    plt.bar(x, height, width = 0.4)
    plt.title(f"Количество сообщений на сервере: {guildName}. Дата: {date}")
    plt.ylabel("кол-во")
    plt.xlabel("пользователь")
    plt.xticks(x, userNames)

    plt.savefig(f"graphs/messages_{date}.png")
    #plt.show()

    x = np.arange(10)
    height = []
    words = []

    cursor.execute(f'''SELECT 
        word,
        SUM(amount) AS amount_sum
        FROM words
        WHERE guild = "ＰＯＴＡＳＯＦＫＡ"
        GROUP BY word
        ORDER BY amount_sum DESC
        LIMIT 10
        ''')
    all_results = cursor.fetchall()
    for row in all_results:
        height.append(row[1])
        words.append(row[0])

    plt.bar(x, height, width = 0.4, color = "red")
    plt.title(f"Частота использований слов на сервере: {guildName}. Дата: {date}")
    plt.ylabel("кол-во")
    plt.xlabel("слово")
    plt.xticks(x, words)

    #plt.show()
    plt.savefig(f"graphs/words_{date}.png")

    await inter.send(file = disnake.File(f"graphs/messages_{date}.png"))
    await inter.send(file = disnake.File(f"graphs/words_{date}.png"))
    
#///////SERVICE///////#
#--------------------->
async def loadBD():
    
    connection = sqlite3.connect('DBs/userMessages.db')
    cursor = connection.cursor()

    # Создаем таблицу userMessages
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    guild TEXT NOT NULL,
    channel TEXT NOT NULL,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    date DATE
    )
    ''')

    # Создаем таблицу words
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY,
    guild TEXT NOT NULL,
    username TEXT NOT NULL,
    word TEXT NOT NULL,
    amount INTEGER NOT NULL,
    date DATE
    )
    ''')

    # Сохраняем изменения и закрываем соединение
    connection.commit()
    connection.close()
    
async def writeMessageInSQL(message):

    connection = sqlite3.connect('DBs/userMessages.db')
    cursor = connection.cursor()

    channel = message.channel.name
    guild = message.guild.name
    username = message.author.name
    messageContent = message.content.split() 
    messageText = ' '.join(message.content.split())
    date = message.created_at

    #print(message.content.split())
    words = message.content.lower().split()

    if len(words) > 0:
        #Запись сообщения
        cursor.execute('INSERT INTO messages (guild, channel, username, message, date) VALUES (?, ?, ?, ?, ?)', (guild, channel, username, messageText.lower(), date))
        connection.commit()
        
    connection.close()

    if len(words) > 0:
        await updateWords(words, guild, username, date)

async def updateWords(words, guild, username, date):
    
    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/userMessages.db')
    cursor = connection.cursor()

    updateWords = []
    newWords = []
    notWords = []
    
    cursor.execute('SELECT id, word, username, guild, amount FROM words WHERE (username = ?) AND (guild = ?)', (username, guild))
    all_results = cursor.fetchall()

    for row in all_results:
        if row[1] in words:
            updateWords.append(row)
            notWords.append(row[1])
            words.remove(row[1])

    for word in words:
        if len(word) > 10:
            continue
        
        if not word in newWords and not word in notWords:
            newWords.append(word)
    
    print(f"Новые слова {newWords}")
    print(f"Слова на обновление {updateWords}")
    
    for newWord in newWords:
        cursor.execute('INSERT INTO words (guild, username, word, amount, date) VALUES (?, ?, ?, ?, ?)', (guild, username, newWord.lower(), 1, date))

    for updWord in updateWords:
        cursor.execute('UPDATE words SET amount = ? WHERE id = ?', (updWord[4] + 1, updWord[0]))

    
    connection.commit()
    connection.close()
    #cursor.execute('SELECT * FROM words;')
#///////STARTING BOT///////#
#-------------------------->    
bot.run(token)
