import disnake
from disnake.ext import commands, tasks
import json
import requests
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import random

bot = commands.Bot(command_prefix="/",
                   intents=disnake.Intents.all(),
                   activity=disnake.Game(name="В разработке"))

with open('config.json') as f:
    config = json.load(f)

answerChanse = 3
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
    
    if message.author == bot.user:
        return
    
    global answerChanse
    
    chanse = random.randint(1, 10)
    if chanse >= 10 - answerChanse:
        await sayPhrase(message)

    
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
    await inter.response.send_message(f'''Версия Бота: {version}\n
                                        Использовать GIFs: {useGifs}\n
                                        Использовать IMGs: {useImages}
                                        ''')


@bot.slash_command(description="Записать фразу в базу данных",)
async def write(inter, phrase: str):

    await writePharse(inter.guild.name, inter.author.name, phrase, inter.created_at)
    await inter.send(f"Фраза записана", delete_after = 10)


@bot.slash_command(description="Приказ боту говорить!",)
async def say(inter):

    randomPhrase = await getRandomPhrase()
    await inter.send(randomPhrase)
   
  
@bot.slash_command(description="Сформировать графики",)
async def graphs(inter):
    
    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()

    x = np.arange(10)
    height = []
    userNames = []

    date = datetime.now().date()

    #Особенность сервера
    guildName = ""
    if inter.guild.name == "ＰＯＴＡＳＯＦＫＡ":
        guildName = "Potasofka"
    else:
        guildName = inter.guild.name
    
    cursor.execute(f'''SELECT 
        guild,
        username,
        COUNT(DISTINCT message) AS countMessages
        FROM messages
        WHERE guild = "{inter.guild.name}"
        GROUP BY username
        ORDER BY countMessages DESC
        LIMIT 10
        ''')
    all_results = cursor.fetchall()
    for row in all_results:
        height.append(row[2])
        userNames.append(row[1])

    fig = plt.figure(figsize = (15, 5))
    
    plt.bar(x, height, width = 0.4)
    plt.title(f"Количество сообщений на сервере: {guildName}. Дата: {date}")
    plt.ylabel("кол-во")
    plt.xlabel("пользователь")
    plt.xticks(x, userNames)

    plt.savefig(f"graphs/messages_{date}.png")
    #plt.show()
    plt.close()
    
    height = []
    words = []

    cursor.execute(f'''SELECT 
        word,
        SUM(amount) AS amount_sum
        FROM words
        WHERE guild = "{inter.guild.name}"
        GROUP BY word
        ORDER BY amount_sum DESC
        LIMIT 10
        ''')
    all_results = cursor.fetchall()
    connection.close()
    
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
    
    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()

    # Создаем таблицу messages
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

    # Создаем таблицу phrases
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY,
    guild TEXT NOT NULL,
    author TEXT NOT NULL,
    phrase TEXT NOT NULL,
    date DATE
    )
    ''')

    # Сохраняем изменения и закрываем соединение
    connection.commit()
    connection.close()

async def writePharse(guild, username, phrase, date):

    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()
    
    #Запись сообщения
    cursor.execute('''INSERT INTO phrases (
                    guild,
                    author,
                    phrase,
                    date)
                    VALUES (?, ?, ?, ?)''',
                    (guild, username, phrase.lower(), date))
            
    connection.commit() 
    connection.close()
    
async def writeMessageInSQL(message):

    connection = sqlite3.connect('DBs/main.db')
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
        cursor.execute('''INSERT INTO messages (
                        guild,
                        channel,
                        username,
                        message,
                        date)
                        VALUES (?, ?, ?, ?, ?)''',
                       (guild, channel, username, messageText.lower(), date))
        
        connection.commit()
        
    connection.close()

    if len(words) > 0:
        await updateWords(words, guild, username, date)

async def updateWords(words, guild, username, date):

    if username == bot.user.name:
        return
    
    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/main.db')
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

async def getRandomPhrase():

    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()

    cursor.execute('''SELECT 
        id,
        phrase
        FROM phrases
        ''')
    all_results = cursor.fetchall()
    connection.close()
    randomNum = random.randint(1, len(all_results))
    return all_results[randomNum - 1][1]


async def sayPhrase(message):

    randomPhrase = await getRandomPhrase()
    await message.channel.send(randomPhrase)

    
#///////STARTING BOT///////#
#-------------------------->    
bot.run(token)
