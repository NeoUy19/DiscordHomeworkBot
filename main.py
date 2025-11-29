import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime
from discord.ext import tasks
from datetime import datetime, timedelta

connection = sqlite3.connect('assignments.db')
cursor = connection.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT UNIQUE NOT NULL
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        assignment_name TEXT NOT NULL,
        due_date TEXT NOT NULL,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        UNIQUE(class_id, assignment_name)
    )
''')

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename="discord.log", encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

admin = "admin"

@bot.event
async def on_ready():
    print("BOMBACLATTTT")

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server {member.name}! ")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


#______________ ADMIN COMMANDS ___________#

@bot.command()
@commands.has_role(admin)
async def addclass(ctx, class_name:str):
    if discord.utils.get(ctx.guild.roles, name =class_name): #check if the role is already in the server
        await ctx.send(f"Class '{class_name}' already exists")
        return
    #add role if it does not exist
    new_role = await ctx.guild.create_role(name=class_name) #add the role
    # check if class is already in the database
    try:
        cursor.execute("INSERT INTO classes (class_name) VALUES (?)", (class_name,))
        connection.commit()
        await ctx.send(f"Class '{class_name}' has been added!")
    except sqlite3.IntegrityError:
        await ctx.send(f"Class '{class_name}' already exists in database")


@bot.command()
@commands.has_role(admin)
async def deleteclass (ctx, class_name:str):
    cursor.execute(
        """DELETE FROM classes
        WHERE class_name = ?""",
        (class_name,))
    if cursor.rowcount > 0:
        connection.commit()
        role = discord.utils.get(ctx.guild.roles, name=class_name)
        if role:
            await role.delete()
            await ctx.send(f"Class '{class_name}' and its role have been deleted!")
        else:
            await ctx.send(f"Class '{class_name}' has been deleted!")
    else:
        await ctx.send(f"Class '{class_name}' not found")

@bot.command()
@commands.has_role(admin)
async def addassignment(ctx, class_name:str, assignment_name:str, due_date:str):
    cursor.execute("SELECT id FROM classes WHERE class_name = ? LIMIT 1", 
                   (class_name,))
    result = cursor.fetchone()
    if not result:
        await ctx.send (f"Class '{class_name}' does not exist")
        return
    class_id = result[0]
    cursor.execute(
        "SELECT 1 FROM assignments WHERE class_id = ? AND assignment_name = ? LIMIT 1",
        (class_id, assignment_name)
    )
    if cursor.fetchone():
        await ctx.send(f"Assignment '{assignment_name}' already exists in '{class_name}'")
        return
    cursor.execute(
        "INSERT INTO assignments (class_id, assignment_name, due_date) VALUES (?,?,?)",
        (class_id,assignment_name,due_date)
    )
    connection.commit()
    await ctx.send(f"Assignment '{assignment_name}' has been added to class '{class_name}', due, '{due_date}'")
@bot.command()
@commands.has_role(admin)
async def deleteassignment (ctx, class_name:str, assignment_name:str):
        cursor.execute("""
        DELETE FROM assignments 
        WHERE class_id = (SELECT id FROM classes WHERE class_name = ?)
        AND assignment_name = ?
    """, (class_name, assignment_name))
        if cursor.rowcount > 0:
            connection.commit()
            await ctx.send(f"'{assignment_name}' has been removed from '{class_name}'")

#______________ ADMIN COMMANDS END ___________#
#______________ ALL COMMANDS ___________#
@bot.command()
async def listassignments(ctx, class_name: str):
    cursor.execute("""
        SELECT a.assignment_name, a.due_date 
        FROM assignments a
        JOIN classes c ON a.class_id = c.id
        WHERE c.class_name = ?
        ORDER BY a.due_date
    """, (class_name,))
    rows = cursor.fetchall()
    if not rows:
        await ctx.send (f"No assignments found for '{class_name}' ... lucky!!")
        return
    
    printList = f"**Assignments for {class_name}:**\n\n"
    for assignment_name, due_date in rows:
        printList += f"**{assignment_name}** - Due: '{due_date}' \n"

    await ctx.send(printList)

#______________ ALL COMMANDS END ___________#
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
