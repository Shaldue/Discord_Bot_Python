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
                   activity=disnake.Game(name="Minecraft 1.12.2"))

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


@bot.event
async def on_thread_member_join(member):
    print(member)

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

    await writePhrase(inter.guild.name, inter.author.name, phrase, inter.created_at)
    await inter.send(f"Фраза записана", delete_after = 10)


@bot.slash_command(description="Записать анекдот в базу данных",)
async def joke_write(inter, joke: str):

    await writeJoke(inter.guild.name, inter.author.name, joke, inter.created_at)
    await inter.send(f"Анекдот записан", delete_after = 10)


@bot.slash_command(description="Приказ боту говорить!",)
async def say(inter):

    randomPhrase = await getRandomPhrase()
    await inter.send(randomPhrase)


@bot.slash_command(description="Вызвать анекдот",)
async def joke(inter):

    joke = await getRandomJoke()
    await inter.send(joke)
    
  
@bot.slash_command(description="Сформировать графики",)
async def graphs(inter):
    
    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()

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
    col_num = 0
    for row in all_results:
        height.append(row[2])
        userNames.append(row[1])
        col_num += 1

    x = np.arange(col_num)
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
    col_num = 0
    for row in all_results:
        height.append(row[1])
        words.append(row[0])
        col_num += 1

    x = np.arange(col_num)
    plt.bar(x, height, width = 0.4, color = "red")
    plt.title(f"Частота использований слов на сервере: {guildName}. Дата: {date}")
    plt.ylabel("кол-во")
    plt.xlabel("слово")
    plt.xticks(x, words)

    #plt.show()
    plt.savefig(f"graphs/words_{date}.png")
    plt.close()

    height = []
    words = []

    cursor.execute(f'''SELECT 
        author,
        COUNT(phrase) as count_phrases
        FROM phrases
        WHERE guild = "{inter.guild.name}"
        GROUP BY author
        ORDER BY count_phrases DESC
        LIMIT 10
        ''')
    all_results = cursor.fetchall()
    connection.close()
    col_num = 0
    for row in all_results:
        height.append(row[1])
        words.append(row[0])
        col_num += 1

    x = np.arange(col_num)
    plt.bar(x, height, width = 0.4, color = "green")
    plt.title(f"Число загруженных фраз на сервере: {guildName}. Дата: {date}")
    plt.ylabel("кол-во")
    plt.xlabel("пользователь")
    plt.xticks(x, words)

    #plt.show()
    plt.savefig(f"graphs/phrases_{date}.png")
    plt.close()
    
    await inter.send(file = disnake.File(f"graphs/messages_{date}.png"))
    await inter.send(file = disnake.File(f"graphs/words_{date}.png"))
    await inter.send(file = disnake.File(f"graphs/phrases_{date}.png"))


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

    # Создаем таблицу jokes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jokes (
    id INTEGER PRIMARY KEY,
    guild TEXT NOT NULL,
    author TEXT NOT NULL,
    joke TEXT NOT NULL,
    params INTEGER NOT NULL,
    date DATE
    )
    ''')

    # Сохраняем изменения и закрываем соединение
    connection.commit()
    connection.close()

async def writePhrase(guild, username, phrase, date):

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


async def writeJoke(guild, username, joke, date):

    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()

    joke = joke.replace("[перенос]", "\n")
    
    countParams = joke.count("[вставка")
    
    #Запись сообщения
    cursor.execute('''INSERT INTO jokes (
                    guild,
                    author,
                    joke,
                    params,
                    date)
                    VALUES (?, ?, ?, ?, ?)''',
                    (guild, username, joke, countParams, date))
            
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


async def getRandomJoke():

    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect('DBs/main.db')
    cursor = connection.cursor()

    cursor.execute('''SELECT 
        id,
        joke,
        params
        FROM jokes
        ''')
    all_results = cursor.fetchall()
    connection.close()
    randomNum = random.randint(1, len(all_results))

    jokeRow = all_results[randomNum - 1]
    jokeText = jokeRow[1]
    
    params = 1
    while params <= jokeRow[2]:
        phrase = await getRandomPhrase()
        jokeText = jokeText.replace(("[вставка" + str(params) + "]"), phrase)
        params += 1
    
    return jokeText


async def sayPhrase(message):

    randomPhrase = await getRandomPhrase()

    chanse = random.randint(0, 2)
    if chanse == 0:
        await message.channel.send(randomPhrase)
    elif chanse == 1:
        await message.channel.send(f"{message.author.mention} {randomPhrase}")
    else:
        randomPhrase1 = await getRandomPhrase()
        await message.channel.send(f"А может {randomPhrase} и {randomPhrase1}")
  
#///////STARTING BOT///////#
#-------------------------->    
bot.run(token)
