from telebot import asyncio_filters
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup

import configparser
import time

from data_manager import DataManager

# Get token from config.ini
config = configparser.ConfigParser()
config.read(r'./config.ini')
token = config['teleCfg']['token']
bot = AsyncTeleBot(token, state_storage=StateMemoryStorage())

# Get dict from json
elements = DataManager()


class MyStates(StatesGroup):
    name = State()
    add_project = State()
    add_task = State()
    project_name = State()
    worktime = State()
    message = State()


# Convert seconds to conviniant time
def convert_seconds(sec) -> str:
    ty_res = time.gmtime(sec)
    return time.strftime("%H:%M:%S", ty_res)


# Start info
@bot.message_handler(commands=['start'])
async def start(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, 'Бот предназначен для учёта графика работы сотрудников.\n\
GitHub проекта - https://github.com/Kurkiev06/telegramChatbot')
    await bot.send_message(message.chat.id, 'Для просмотра возможностей \
напишите /help')


# Help info
@bot.message_handler(commands=['help'])
async def help(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, '''
/help - помощь по командам
/start - общая информация
/addproject - добавить проект
/addtask - добавить задание
/worktime - посмотреть затраченное на задачу время
/project - выбрать задачу и Начать/Закончить работу''')


# get all time info
@bot.message_handler(commands=['worktime'])
async def worktime(message):
    await bot.set_state(message.from_user.id, MyStates.worktime,
                        message.chat.id)
    await bot.send_message(message.chat.id, "Введите Имя, \
чтобы посмотреть время работы над задачами")


# Get info about worker
@bot.message_handler(state=MyStates.worktime)
async def worktime(message):
    workerName = message.text
    workerNameSplit = {names for names in workerName.lower().split()}
    result = workerName + ":\n"
    for project in elements.data:
        for task in elements.data[project]:
            for name in elements.data[project][task]:
                nameSplit = {names for names in name.lower().split()}
                if nameSplit == workerNameSplit:
                    nowTime = convert_seconds(
                                elements.data[project][task][name]["time"])
                    result += f"Проработал {nowTime} над \
задачей {task} проекта {project}\n"
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, result)


# Add new project
@bot.message_handler(commands=['addproject'])
async def add_project(message):
    await bot.send_message(message.chat.id, "Введите название проекта")
    await bot.set_state(message.from_user.id,
                        MyStates.add_project,
                        message.chat.id)


# Add new task to project
@bot.message_handler(commands=['addtask'])
async def add_task(message):
    await bot.send_message(message.chat.id,
                           "Введите название проекта, куда добавить задание")
    await bot.set_state(message.from_user.id,
                        MyStates.project_name,
                        message.chat.id)


# Choose project
@bot.message_handler(commands=['project'])
async def get_projects(message):
    def get_projects_from_data() -> InlineKeyboardMarkup():
        keyboard = InlineKeyboardMarkup()
        projects = list(elements.data.keys())
        for project in projects:
            button = InlineKeyboardButton(project,
                                          callback_data=f"project:{project}")
            keyboard.row(button)
        return keyboard

    keyboard = get_projects_from_data()
    await bot.delete_state(message.from_user.id,
                           message.chat.id)
    await bot.send_message(message.chat.id,
                           "Выберите проект",
                           reply_markup=keyboard)


# Get project name and request task name
@bot.message_handler(state=MyStates.project_name)
async def get_project_name(message):
    project = message.text
    await bot.set_state(message.from_user.id,
                        MyStates.add_task,
                        message.chat.id)
    async with bot.retrieve_data(message.from_user.id,
                                 message.chat.id) as info:
        info['project'] = project
    await bot.send_message(message.chat.id, "Введите название задания")


# Get task name
@bot.message_handler(state=MyStates.add_task)
async def get_task_name(message):
    async with bot.retrieve_data(message.from_user.id,
                                 message.chat.id) as info:
        project = info['project']
    task = message.text
    elements.update_json(project, task)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id,
                           f"Задание {task} успешно добавлено в {project}!")


# Get project name
@bot.message_handler(state=MyStates.add_project)
async def get_project_name(message):
    project = message.text
    elements.update_json(project)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id,
                           f"Проект {project} успешно добавлен!")


# Choose project
@bot.callback_query_handler(func=lambda call: call.data.startswith('project'))
async def callback_project(call):
    def get_tasks_from_project(project) -> InlineKeyboardMarkup():
        keyboard = InlineKeyboardMarkup()
        tasks = list(elements.data[project].keys())
        for task in tasks:
            button = InlineKeyboardButton(
                        task,
                        callback_data=f"task:{project}:{task}")
            keyboard.row(button)
        return keyboard

    project = call.data.split(':')[1]
    if project not in elements.data\
       or len(list(elements.data[project].keys())) == 0:
        await bot.answer_callback_query(call.id, "Список заданий пуст")
    else:
        keyboard = get_tasks_from_project(project)
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    text="Выберите задание",
                                    message_id=call.message.id,
                                    reply_markup=keyboard)


# Choose task
@bot.callback_query_handler(func=lambda call: call.data.startswith('task'))
async def callback_task(call):
    infoFromCallback = call.data.split(':')
    project = infoFromCallback[1]
    task = infoFromCallback[2]

    if project not in elements.data or task not in elements.data[project]:
        await bot.answer_callback_query(call.id, "Список заданий пуст")

    await bot.set_state(call.from_user.id, MyStates.name, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id,
                                 call.message.chat.id) as info:
        info['project'] = project
        info['task'] = task
    await bot.send_message(call.message.chat.id, text="Введите своё Имя")


# Get name
@bot.message_handler(state=MyStates.name)
async def get_name(message):
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Начать", callback_data="Начать")
    keyboard.row(button)
    button = InlineKeyboardButton("Закончить", callback_data="Закончить")
    keyboard.row(button)
    async with bot.retrieve_data(message.from_user.id,
                                 message.chat.id) as info:
        info['name'] = message.text
        project = info['project']
        task = info['task']
    await bot.set_state(message.from_user.id,
                        MyStates.message,
                        message.chat.id)
    await bot.send_message(message.chat.id,
                           f"Начать/Закончить {task} в {project}",
                           reply_markup=keyboard)


# Choose Start or Finish
@bot.callback_query_handler(func=lambda call:
                            call.data in ["Начать", "Закончить"])
async def callback_task(call):
    async with bot.retrieve_data(call.from_user.id,
                                 call.message.chat.id) as info:
        name = info['name']
        name = name.lower()
        task = info['task']
        project = info['project']
        if name not in elements.data[project][task]:
            elements.update_json(project, task, name, {"start": 0, "time": 0})
        if call.data == "Начать":
            times = {"start": int(time.time()),
                     "time": elements.data[project][task][name]["time"]}
            elements.update_json(
                project,
                task,
                name,
                times)
        else:
            if elements.data[project][task][name]["start"] != 0:
                nameDict = elements.data[project][task][name]
                times = nameDict["time"] + int(time.time()) - nameDict["start"]
                elements.update_json(
                    project,
                    task,
                    name,
                    {"start": nameDict["start"],
                     "time": times})
        nowTime = convert_seconds(elements.data[project][task][name]["time"])
    await bot.send_message(
            call.message.chat.id,
            f"Операция выполнена успешна, вы проработали: {nowTime}")


# Handler for any stranger text
@bot.message_handler(content_types=['text'])
async def get_text_messages(message):
    await bot.send_message(message.chat.id, "Для помощи напишите /help.")

# Register filter
bot.add_custom_filter(asyncio_filters.StateFilter(bot))
