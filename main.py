import asyncio
import logging
import datetime
import time
import socket
from typing import Callable, Dict, Any, Awaitable
import aiohttp
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8644433769:AAGP4VjXPU-_Kpx6VtZaPzhHu8dkYTYKAtc"
PUB_ID = "35ddcc86-1bc0-4f83-ae44-ad3abbeaf4ca"

# СЮДА ВСТАВЬ ССЫЛКУ НА ФОТКУ КИПО (URL должен заканчиваться на .jpg или .png)
PHOTO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS_P6FpSZIVbH1i0zSlfke0Kko0YfEtTrtIaUJgn-wY6Q&s=10" 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- АНТИФЛУД МИДЛВАРЬ (не более 5 запросов за 30 секунд) ---
user_timestamps: Dict[int, list] = {}

class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)
            
        user_id = event.from_user.id
        current_time = time.time()
        
        if user_id not in user_timestamps:
            user_timestamps[user_id] = []
            
        # Очищаем старые запросы
        user_timestamps[user_id] = [t for t in user_timestamps[user_id] if current_time - t < 30]
        
        # ЛИМИТ: 5 запросов
        if len(user_timestamps[user_id]) >= 5:
            await event.answer("⚠️ Слишком часто! Подождите 30 секунд перед отправкой следующей команды.")
            return
            
        user_timestamps[user_id].append(current_time)
        return await handler(event, data)

dp.message.middleware(ThrottlingMiddleware())


class ScheduleForm(StatesGroup):
    waiting_for_student_group = State()
    waiting_for_teacher_name = State()
    waiting_for_day = State()

# --- СПРАВОЧНИКИ ---

TEACHERS_LIST = [
    {"id":598,"fio":"Абрамова С.А."},{"id":1281,"fio":"Абрамова* С.А."},{"id":684,"fio":"Аверина Л.А."},{"id":745,"fio":"Аветисян А.С."},{"id":152,"fio":"Аветисян Г.Г."},{"id":802,"fio":"Агаян А.А."},{"id":649,"fio":"Азанов И.Е."},{"id":60,"fio":"Алексеенко И.Ю."},{"id":527,"fio":"Алексеенко Ю.А."},{"id":1303,"fio":"Алексеенко* Ю.А."},{"id":890,"fio":"Алексян Л.Г."},{"id":1288,"fio":"Алексян* Л.Г."},{"id":1226,"fio":"Алиева А.А."},{"id":90,"fio":"Андреева Е.А."},{"id":1231,"fio":"Арустомян М.А."},{"id":292,"fio":"Архипова В.А."},{"id":1259,"fio":"Архипова* В.А."},{"id":828,"fio":"Архипова М.В."},{"id":161,"fio":"Ашинова М.А."},{"id":97,"fio":"Ашинова С.Б."},{"id":1284,"fio":"Бажанова А.Г."},{"id":241,"fio":"Балацкая Е.В."},{"id":1062,"fio":"Баранникова А.Н."},{"id":177,"fio":"Баранникова И.Г."},{"id":1321,"fio":"Баранникова* И.Г."},{"id":992,"fio":"Баранов А.А."},{"id":134,"fio":"Баранов А.А."},{"id":237,"fio":"Баранов А.А."},{"id":1315,"fio":"Баранов*А.А."},{"id":1162,"fio":"Белосова А.А."},{"id":65,"fio":"Белоус Ю.А."},{"id":1290,"fio":"Белоус* Ю.А."},{"id":564,"fio":"Беляева Л.Л."},{"id":929,"fio":"Беляевский Е.В."},{"id":1252,"fio":"Бендина И.А."},{"id":217,"fio":"Берсан К.А."},{"id":1127,"fio":"Берцулевич Н.А."},{"id":559,"fio":"Бирюкова А.В."},{"id":31,"fio":"Блинов А.Ю."},{"id":218,"fio":"Блинов А.Ю."},{"id":979,"fio":"Блинов А.Ю."},{"id":1270,"fio":"Блинов* А.Ю."},{"id":1272,"fio":"Блинов**А.Ю."},{"id":12,"fio":"Боброва Д.А."},{"id":370,"fio":"Богданова Е.А."},{"id":1304,"fio":"Богданова* Е.А."},{"id":1132,"fio":"Болтенкова А.А."},{"id":479,"fio":"Бондаренко А.Ю."},{"id":1318,"fio":"Бондаренко* А.Ю."},{"id":1054,"fio":"Бугаева Л.М."},{"id":1271,"fio":"Бугаева* Л.М."},{"id":1225,"fio":"Буданок А.А."},{"id":1108,"fio":"Булатасова Г.Х."},{"id":1223,"fio":"Бурмак Н.С."},{"id":1244,"fio":"Вак17,Вак3"},{"id":1230,"fio":"Вак5РЯ"},{"id":1237,"fio":"Вак8Общ"},{"id":1234,"fio":"ВакГречко"},{"id":1274,"fio":"ВакЗУ"},{"id":1254,"fio":"ВакОДЛ"},{"id":1287,"fio":"ВакСавина"},{"id":8,"fio":"Варкентин В.Ф."},{"id":44,"fio":"Васильева И.В."},{"id":1305,"fio":"Васильева* И.В."},{"id":324,"fio":"Вершина М.Ю."},{"id":396,"fio":"Витяева Т.В."},{"id":1149,"fio":"Вихор Л.А."},{"id":52,"fio":"Волкодав В.А."},{"id":898,"fio":"Воронова Е.А."},{"id":808,"fio":"Вылобкова И.Н."},{"id":801,"fio":"Вязовец Е.Н."},{"id":1257,"fio":"Вязовец* Е.Н."},{"id":6,"fio":"Гаврилов А.Ю."},{"id":316,"fio":"Гаврилюк В.М."},{"id":1308,"fio":"Гаврилюк* В.М."},{"id":963,"fio":"Гайворонская Н.С."},{"id":922,"fio":"Гайкалова А.Н."},{"id":770,"fio":"Галактионова С.В."},{"id":63,"fio":"Гамалей В.Г."},{"id":1261,"fio":"Гамалей* В.Г."},{"id":538,"fio":"Гаркуша В.М."},{"id":897,"fio":"Головко Д.Г."},{"id":575,"fio":"Голубева Т.В."},{"id":420,"fio":"Гончаренко Н.Г."},{"id":1265,"fio":"Горенкова Е.А."},{"id":130,"fio":"Горохова Н.А."},{"id":1082,"fio":"Гулян А.С."},{"id":1291,"fio":"Гусаренко Т.А."},{"id":1227,"fio":"Дайчева Л.Г."},{"id":55,"fio":"Данилец А.М."},{"id":1269,"fio":"Данилец* А.М."},{"id":584,"fio":"Дарина А.В."},{"id":169,"fio":"Девочкин А.А."},{"id":159,"fio":"Дегтярев А.Ю."},{"id":93,"fio":"Дмитренко О.Д."},{"id":272,"fio":"Дмитрук С.В."},{"id":1195,"fio":"Должикова Е.А."},{"id":114,"fio":"Домбровская Т.Н."},{"id":1306,"fio":"Домбровская* Т.Н."},{"id":1088,"fio":"Ерохина Ю.В."},{"id":1296,"fio":"Ерохина* Ю.В."},{"id":809,"fio":"Ефимова Н.В."},{"id":223,"fio":"Жерикова Е.В."},{"id":1312,"fio":"Жерикова* Е.В."},{"id":87,"fio":"Жукова С.В."},{"id":112,"fio":"Жукова Т.С."},{"id":1301,"fio":"Жукова* Т.С."},{"id":105,"fio":"Журкина М.Г."},{"id":144,"fio":"Забашта Т.А."},{"id":1264,"fio":"Забашта* Т.А."},{"id":1104,"fio":"Запорощенко К.О."},{"id":1310,"fio":"Запорощенко* К.О."},{"id":200,"fio":"Звягина А.Н."},{"id":1232,"fio":"Зипа В.С."},{"id":1295,"fio":"Зубова В.В."},{"id":969,"fio":"Ивасенко Н.А."},{"id":199,"fio":"Ильина С.П."},{"id":1240,"fio":"Кагирова Ю.А."},{"id":1309,"fio":"Кагирова* Ю.А."},{"id":225,"fio":"Кадеева Л.С."},{"id":119,"fio":"Казновская В.В."},{"id":1280,"fio":"Казновская* В.В."},{"id":900,"fio":"Карцева А.И."},{"id":1313,"fio":"Карцева* А.И."},{"id":137,"fio":"Касакова Е.В."},{"id":1220,"fio":"Кассай М.С."},{"id":1248,"fio":"Каширский* Д."},{"id":1224,"fio":"Каширский Д.О."},{"id":1262,"fio":"Каширский Д.О."},{"id":79,"fio":"Кизим С.Х."},{"id":1112,"fio":"Киселева А.Д."},{"id":525,"fio":"Клименко С.В."},{"id":1297,"fio":"Клименко* С.В."},{"id":13,"fio":"Коврижных О.С."},{"id":202,"fio":"Козырева И.В."},{"id":935,"fio":"Комбарова Ю.В."},{"id":973,"fio":"Комиссарова И.Е."},{"id":205,"fio":"Копытко А.А."},{"id":394,"fio":"Костенко Л.В."},{"id":977,"fio":"Костенко Л.В."},{"id":175,"fio":"Костенко Л.В."},{"id":991,"fio":"Костюкова Е.В."},{"id":1228,"fio":"Костюченко О.В."},{"id":188,"fio":"Котенко И.Ю."},{"id":683,"fio":"Котивец К.А"},{"id":596,"fio":"Кочанкова К.А."},{"id":1273,"fio":"Кочанкова* К.А."},{"id":903,"fio":"Крылепова В.В."},{"id":1164,"fio":"Крюк В.С."},{"id":1298,"fio":"Крюк* В.С."},{"id":1219,"fio":"Кудрина Е.В."},{"id":1238,"fio":"Кузина Ю.Ю."},{"id":871,"fio":"Кулиева А.С."},{"id":1249,"fio":"Куликова К.Ю."},{"id":955,"fio":"Курочка М.А."},{"id":914,"fio":"Кушковая В.В."},{"id":17,"fio":"Левичев К.С."},{"id":173,"fio":"Литвинов М.В."},{"id":116,"fio":"Лиханская А.А."},{"id":189,"fio":"Лозинская С.А."},{"id":209,"fio":"Лукащук Т.С."},{"id":1266,"fio":"Лукащук* Т.С."},{"id":975,"fio":"Лукьянова В.К."},{"id":901,"fio":"Лунин А.И."},{"id":1146,"fio":"Лысова А.О."},{"id":21,"fio":"Лютая О.В."},{"id":800,"fio":"Лякова Л.Н."},{"id":47,"fio":"Мастюгина О.В."},{"id":1258,"fio":"Мастюгина* О.В."},{"id":1299,"fio":"Мастюгина** О.В."},{"id":924,"fio":"Матвеев О.Г."},{"id":1319,"fio":"Матвеев* О.Г."},{"id":33,"fio":"Мащенко Ю.В."},{"id":1118,"fio":"Меграбян П.Е."},{"id":902,"fio":"Медведева Л.В."},{"id":1222,"fio":"Мелоян В.Г."},{"id":1294,"fio":"Мероприятие"},{"id":1307,"fio":"Мероприятие*"},{"id":458,"fio":"Миллер В.А."},{"id":456,"fio":"Миллер В.А."},{"id":1275,"fio":"Миллер* В.А."},{"id":1268,"fio":"Миллер*В.А."},{"id":1251,"fio":"Мисюк Н.В."},{"id":1034,"fio":"Михайлова Л.А."},{"id":18,"fio":"Мищенюк Е.С."},{"id":1278,"fio":"Мищенюк* Е.С."},{"id":834,"fio":"Молчанова И.Б."},{"id":1024,"fio":"Нарожная Л.С."},{"id":891,"fio":"Нефедова К.А."},{"id":198,"fio":"Новикова Н.П."},{"id":213,"fio":"Новиков В.В."},{"id":544,"fio":"Носуль В.А."},{"id":925,"fio":"Овчинникова Н.П."},{"id":1183,"fio":"Онищенко Е.Е."},{"id":269,"fio":"Орел Е.В."},{"id":156,"fio":"Осенняя М.Г."},{"id":1229,"fio":"Остапенко О.А."},{"id":71,"fio":"Острая Ж.А."},{"id":416,"fio":"Павлова Т.А."},{"id":529,"fio":"Павловский Д.В."},{"id":739,"fio":"Панфилова Е.В."},{"id":1256,"fio":"Панфилова* Е.В."},{"id":158,"fio":"Парыгина Л.В."},{"id":255,"fio":"Перфильева А.Г."},{"id":436,"fio":"Перфильева А.Г."},{"id":980,"fio":"Перфильева А.Г."},{"id":109,"fio":"Перфильев Д.А."},{"id":434,"fio":"Перфильев Д.А."},{"id":1245,"fio":"Перфильев* Д.А."},{"id":1253,"fio":"Перфильев** Д.А."},{"id":1279,"fio":"Перфильев** Д.А."},{"id":949,"fio":"Петренко В.А."},{"id":34,"fio":"Петренко Н.Н."},{"id":1311,"fio":"Петренко* Н.Н."},{"id":24,"fio":"Петрова О.А."},{"id":155,"fio":"Петросян М.Р."},{"id":497,"fio":"Писарев А.С."},{"id":819,"fio":"Пожидаев Р.В."},{"id":191,"fio":"Покровская Е.А."},{"id":951,"fio":"Прозоровская Е.М."},{"id":1292,"fio":"Прозоровская* Е.М."},{"id":633,"fio":"Пустовая С.Н."},{"id":5,"fio":"Пясецкий С.А."},{"id":57,"fio":"Руснак И.В."},{"id":1260,"fio":"Руснак* И.В."},{"id":1246,"fio":"Рыбалко О.С."},{"id":30,"fio":"Савина М.П."},{"id":41,"fio":"Савинкова Е.Э."},{"id":1277,"fio":"Савинкова* Е.Э."},{"id":1192,"fio":"Савлучинская А.В."},{"id":595,"fio":"Савчук Л.И."},{"id":522,"fio":"Садайло И.В."},{"id":78,"fio":"Салионова Г.Г."},{"id":594,"fio":"Северова Д.С."},{"id":524,"fio":"Селезнёва С.В."},{"id":1242,"fio":"Семендяева Е.И."},{"id":91,"fio":"Семенова А.А."},{"id":49,"fio":"Сенюта С.В."},{"id":242,"fio":"Сидоренко Е.М."},{"id":111,"fio":"Сидоренко Я.В."},{"id":1316,"fio":"Сидоренко* Я.В."},{"id":124,"fio":"Силиштян Л.Л."},{"id":74,"fio":"Сирота Н.В."},{"id":179,"fio":"Скворцов Р.И."},{"id":555,"fio":"Слесарева А.О."},{"id":1276,"fio":"Слесарева* А.О."},{"id":167,"fio":"Соловьев С.В."},{"id":1263,"fio":"Сорокина Ю.С."},{"id":92,"fio":"Сотникова Е.С."},{"id":710,"fio":"Сотский В.В."},{"id":1235,"fio":"СРС"},{"id":579,"fio":"Струкова А.А."},{"id":647,"fio":"Суконина А.В."},{"id":1302,"fio":"Суконина* А.В."},{"id":16,"fio":"Суконина С.В."},{"id":100,"fio":"Сычевская Г.В."},{"id":469,"fio":"Тайков Д.С."},{"id":136,"fio":"Тасева А.А."},{"id":1241,"fio":"Таций А.Е."},{"id":85,"fio":"Тимофеева В.Н."},{"id":1289,"fio":"Тимофеева* В.Н."},{"id":61,"fio":"Тишкевич А.С."},{"id":1317,"fio":"Тишкевич* А.С."},{"id":593,"fio":"Тишкевич Э.В."},{"id":1250,"fio":"Ткачев Б.С."},{"id":952,"fio":"Толкачева Е.С."},{"id":736,"fio":"Толстоусова О.В."},{"id":77,"fio":"Трофимова Н.Г."},{"id":1285,"fio":"Трофимова* Н.Г."},{"id":530,"fio":"Трунов Д.И."},{"id":1131,"fio":"Трухан О.В."},{"id":1267,"fio":"Трухан* О.В."},{"id":933,"fio":"Усова А.А."},{"id":1320,"fio":"Усова* А.А."},{"id":392,"fio":"Фарафонова Н.П."},{"id":88,"fio":"Хан Е.И."},{"id":1180,"fio":"Хот С.Х."},{"id":1247,"fio":"Хусаинова А.В."},{"id":195,"fio":"Цимбалистова Д.И."},{"id":231,"fio":"Цыркова Л.М."},{"id":154,"fio":"Чайковский М.А."},{"id":1203,"fio":"Чалая Е.Н."},{"id":1293,"fio":"Чалая* Е.Н."},{"id":827,"fio":"Чеботарев В.И."},{"id":23,"fio":"Чемов О.В."},{"id":201,"fio":"Черник Е.Н."},{"id":1314,"fio":"Черник* Е.Н."},{"id":738,"fio":"Черных Т.В."},{"id":43,"fio":"Четошникова Л.А."},{"id":1300,"fio":"Четошникова* Л.А."},{"id":68,"fio":"Шаломай К.С."},{"id":1239,"fio":"Шаляпина Е.Ю."},{"id":1018,"fio":"Шаповалова В.В."},{"id":556,"fio":"Шаповалова М.Н."},{"id":302,"fio":"Шаталова С.Н."},{"id":895,"fio":"Шванева В.В."},{"id":1221,"fio":"Шванева Е.В."},{"id":196,"fio":"Шеина А.В."},{"id":244,"fio":"Шестакова Э.В."},{"id":987,"fio":"Шестакова Э.В."},{"id":76,"fio":"Шестакова Э.В."},{"id":121,"fio":"Шпилевая О.Н."},{"id":722,"fio":"Шушкевич А.Л."},{"id":142,"fio":"Юдицкая О.Е."},{"id":427,"fio":"Юханова О.И."},{"id":1148,"fio":"Яковлева Т.В."},{"id":147,"fio":"Ярчевский Е.Ю."},{"id":1255,"fio":"Ярчевский* Е.Ю."}
]

GROUPS_LIST = [
    {"id":32,"name":"23-ЗУ1-9"},{"id":33,"name":"23-ЗУ2-9"},{"id":34,"name":"23-ЗУ3-9"},{"id":35,"name":"23-ЗУ4-9"},{"id":208,"name":"23-ЗУ5-9"},{"id":13,"name":"23-ИСП1-9"},{"id":14,"name":"23-ИСП2-9"},{"id":15,"name":"23-ИСП3-9"},{"id":145,"name":"23-ПД1-9"},{"id":146,"name":"23-ПД2-9"},{"id":147,"name":"23-ПД3-9"},{"id":148,"name":"23-ПД4-9"},{"id":149,"name":"23-ПД5-9"},{"id":186,"name":"23-ПНК1-9"},{"id":187,"name":"23-ПНК2-9"},{"id":188,"name":"23-ПНК3-9"},{"id":189,"name":"23-ПНК4-9"},{"id":221,"name":"23-ПР-9 ЗФО"},{"id":202,"name":"23-СДО-9"},{"id":286,"name":"24-БД 1-9"},{"id":301,"name":"24-БД 2-9"},{"id":298,"name":"24-ЗУ-11"},{"id":295,"name":"24-ЗУ1-9"},{"id":296,"name":"24-ЗУ2-9"},{"id":297,"name":"24-ЗУ3-9"},{"id":274,"name":"24-ИСП-11"},{"id":227,"name":"24-ИСП1-9"},{"id":228,"name":"24-ИСП2-9"},{"id":229,"name":"24-ИСП3-9"},{"id":259,"name":"24-ИСП4-9"},{"id":230,"name":"24-ИСР1-9"},{"id":231,"name":"24-ИСР2-9"},{"id":299,"name":"24-ЛД 1-9"},{"id":300,"name":"24-ЛД 2-9"},{"id":284,"name":"24-МО1-9"},{"id":285,"name":"24-МО2-9"},{"id":241,"name":"24-ОДЛ1-9"},{"id":242,"name":"24-ОДЛ2-9"},{"id":243,"name":"24-ОДЛ3-9"},{"id":244,"name":"24-ОДЛ4-9"},{"id":245,"name":"24-ОДЛ5-9"},{"id":224,"name":"24-ПД-11"},{"id":260,"name":"24-ПД1-9"},{"id":261,"name":"24-ПД2-9"},{"id":262,"name":"24-ПД3-9"},{"id":263,"name":"24-ПД4-9"},{"id":264,"name":"24-ПД5-9"},{"id":288,"name":"24-ПД6-9"},{"id":277,"name":"24-ПНК-11"},{"id":289,"name":"24-ПНК1-9"},{"id":290,"name":"24-ПНК2-9"},{"id":291,"name":"24-ПНК3-9"},{"id":292,"name":"24-ПНК4-9"},{"id":280,"name":"24-СД1-11-ОЗФО"},{"id":235,"name":"24-СД1-9"},{"id":281,"name":"24-СД2-11-ОЗФО"},{"id":236,"name":"24-СД2-9"},{"id":237,"name":"24-СД3-9"},{"id":238,"name":"24-СД4-9"},{"id":239,"name":"24-СД5-9"},{"id":293,"name":"24-СДО-9"},{"id":232,"name":"24-СР1-9"},{"id":233,"name":"24-СР2-9"},{"id":234,"name":"24-СР3-9"},{"id":267,"name":"24-ТГГ1-9"},{"id":268,"name":"24-ТГГ2-9"},{"id":269,"name":"24-ТГГ3-9"},{"id":265,"name":"24-ТГТ1-9"},{"id":266,"name":"24-ТГТ2-9"},{"id":249,"name":"24-Ф1-9"},{"id":250,"name":"24-Ф2-9"},{"id":251,"name":"24-Ф3-9"},{"id":252,"name":"24-Ф4-9"},{"id":253,"name":"24-Ф5-9"},{"id":254,"name":"24-Ф6-9"},{"id":255,"name":"24-Ф7-9"},{"id":247,"name":"24-ФИН1-9"},{"id":248,"name":"24-ФИН2-9"},{"id":287,"name":"24-ФИН3-9"},{"id":240,"name":"24-ЭБ-9"},{"id":270,"name":"24-ЮСА1-9"},{"id":271,"name":"24-ЮСА2-9"},{"id":272,"name":"24-ЮСА3-9"},{"id":273,"name":"24-ЮСА4-9"},{"id":307,"name":"24-ЮСО-11 ЗФО"},{"id":308,"name":"24-ЮСО-9 ЗФО"},{"id":256,"name":"24-ЮСО1-9"},{"id":257,"name":"24-ЮСО2-9"},{"id":258,"name":"24-ЮСО3-9"},{"id":359,"name":"25-БД1-9"},{"id":360,"name":"25-БД2-9"},{"id":383,"name":"25-БД3-9"},{"id":331,"name":"25-ДОА-9"},{"id":377,"name":"25-ЗУ-11"},{"id":373,"name":"25-ЗУ1-9"},{"id":374,"name":"25-ЗУ2-9"},{"id":375,"name":"25-ЗУ3-9"},{"id":365,"name":"25-ИСП-11"},{"id":316,"name":"25-ИСП1-9"},{"id":317,"name":"25-ИСП2-9"},{"id":318,"name":"25-ИСП3-9"},{"id":387,"name":"25-ИСП4-9"},{"id":319,"name":"25-ИСР1-9"},{"id":320,"name":"25-ИСР2-9"},{"id":370,"name":"25-ЛД1-9"},{"id":371,"name":"25-ЛД2-9"},{"id":344,"name":"25-ЛЧД1-9"},{"id":345,"name":"25-ЛЧД2-9"},{"id":372,"name":"25-ОДЛ-11"},{"id":332,"name":"25-ОДЛ1-9"},{"id":333,"name":"25-ОДЛ2-9"},{"id":334,"name":"25-ОДЛ3-9"},{"id":335,"name":"25-ОДЛ4-9"},{"id":336,"name":"25-ОДЛ5-9"},{"id":351,"name":"25-ПД-11"},{"id":321,"name":"25-ПД1-9"},{"id":322,"name":"25-ПД2-9"},{"id":323,"name":"25-ПД3-9"},{"id":324,"name":"25-ПД4-9"},{"id":325,"name":"25-ПД5-9"},{"id":376,"name":"25-ПНК-11"},{"id":355,"name":"25-ПНК1-9"},{"id":356,"name":"25-ПНК2-9"},{"id":357,"name":"25-ПНК3-9"},{"id":367,"name":"25-СД1-11-ОЗФО"},{"id":327,"name":"25-СД1-9"},{"id":368,"name":"25-СД2-11-ОЗФО"},{"id":328,"name":"25-СД2-9"},{"id":329,"name":"25-СД3-9"},{"id":330,"name":"25-СД4-9"},{"id":353,"name":"25-СДО1-9"},{"id":354,"name":"25-СДО2-9"},{"id":326,"name":"25-СР-9"},{"id":361,"name":"25-ТГГ-9"},{"id":363,"name":"25-ТГТ1-9"},{"id":364,"name":"25-ТГТ2-9"},{"id":362,"name":"25-ТГТ3-9"},{"id":366,"name":"25-Ф-11"},{"id":339,"name":"25-Ф1-9"},{"id":340,"name":"25-Ф2-9"},{"id":341,"name":"25-Ф3-9"},{"id":342,"name":"25-Ф4-9"},{"id":343,"name":"25-Ф5-9"},{"id":337,"name":"25-ФИН1-9"},{"id":338,"name":"25-ФИН2-9"},{"id":358,"name":"25-ЭБ-9"},{"id":346,"name":"25-ЮСА1-9"},{"id":347,"name":"25-ЮСА2-9"},{"id":348,"name":"25-ЮСА3-9"},{"id":349,"name":"25-ЮСА4-9"},{"id":386,"name":"25-ЮСА5-9"},{"id":352,"name":"25-ЮСО-11"},{"id":389,"name":"25-ЮСО-11 ЗФО"},{"id":350,"name":"25-ЮСО-9"},{"id":388,"name":"25-ЮСО-9 ЗФО"},{"id":405,"name":"26-БД1-9"},{"id":406,"name":"26-БД2-9"},{"id":407,"name":"26-БД3-9"},{"id":459,"name":"26-ВР1-9"},{"id":460,"name":"26-ВР2-9"},{"id":464,"name":"26-ДОА1-9"},{"id":465,"name":"26-ДОА2-9"},{"id":453,"name":"26-ЗУ-11"},{"id":454,"name":"26-ЗУ1-9"},{"id":455,"name":"26-ЗУ2-9"},{"id":456,"name":"26-ЗУ3-9"},{"id":423,"name":"26-ЛД1-9"},{"id":424,"name":"26-ЛД2-9"},{"id":390,"name":"26-ЛЧД1-9"},{"id":391,"name":"26-ЛЧД2-9"},{"id":392,"name":"26-ЛЧД3-9"},{"id":450,"name":"26-ОДЛ-11"},{"id":408,"name":"26-ОДЛ1-9"},{"id":409,"name":"26-ОДЛ2-9"},{"id":410,"name":"26-ОДЛ3-9"},{"id":411,"name":"26-ОДЛ4-9"},{"id":412,"name":"26-ОДЛ5-9"},{"id":401,"name":"26-ПД-11"},{"id":413,"name":"26-ПД1-9"},{"id":414,"name":"26-ПД2-9"},{"id":415,"name":"26-ПД3-9"},{"id":416,"name":"26-ПД4-9"},{"id":417,"name":"26-ПД5-9"},{"id":418,"name":"26-ПД6-9"},{"id":449,"name":"26-ПНК-11"},{"id":419,"name":"26-ПНК1-9"},{"id":420,"name":"26-ПНК2-9"},{"id":421,"name":"26-ПНК3-9"},{"id":422,"name":"26-ПНК4-9"},{"id":458,"name":"26-РИС-11"},{"id":461,"name":"26-РИС1-9"},{"id":462,"name":"26-РИС2-9"},{"id":463,"name":"26-РИС3-9"},{"id":447,"name":"26-СД1-11-ОЗФО"},{"id":396,"name":"26-СД1-9"},{"id":448,"name":"26-СД2-11-ОЗФО"},{"id":397,"name":"26-СД2-9"},{"id":398,"name":"26-СД3-9"},{"id":399,"name":"26-СД4-9"},{"id":400,"name":"26-СД5-9"},{"id":393,"name":"26-СДО1-9"},{"id":394,"name":"26-СДО2-9"},{"id":395,"name":"26-СДО3-9"},{"id":425,"name":"26-СР1-9"},{"id":426,"name":"26-СР2-9"},{"id":427,"name":"26-ТГГ1-9"},{"id":428,"name":"26-ТГГ2-9"},{"id":429,"name":"26-ТГТ1-9"},{"id":430,"name":"26-ТГТ2-9"},{"id":431,"name":"26-ТГТ3-9"},{"id":451,"name":"26-Ф1-11"},{"id":432,"name":"26-Ф1-9"},{"id":452,"name":"26-Ф2-11"},{"id":433,"name":"26-Ф2-9"},{"id":434,"name":"26-Ф3-9"},{"id":435,"name":"26-Ф4-9"},{"id":436,"name":"26-Ф5-9"},{"id":437,"name":"26-Ф6-9"},{"id":438,"name":"26-ФИН1-9"},{"id":439,"name":"26-ФИН2-9"},{"id":440,"name":"26-ЭБ-9"},{"id":402,"name":"26-ЮСА-11"},{"id":441,"name":"26-ЮСА1-9"},{"id":442,"name":"26-ЮСА2-9"},{"id":443,"name":"26-ЮСА3-9"},{"id":444,"name":"26-ЮСА4-9"},{"id":445,"name":"26-ЮСО1-9"},{"id":446,"name":"26-ЮСО2-9"},{"id":380,"name":"Мероприятие"},{"id":466,"name":"Мероприятие*"}
]

TEACHERS_DICT = {t["fio"].lower(): t["id"] for t in TEACHERS_LIST}
GROUPS_DICT = {g["name"].lower(): g["id"] for g in GROUPS_LIST}

DAYS_MAPPING = {
    "понедельник": 1,
    "вторник": 2,
    "среда": 3,
    "четверг": 4,
    "пятница": 5,
    "суббота": 6
}

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨‍‍🎓 Я студент")],
            [KeyboardButton(text="👨‍🏫 Я преподаватель")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите вашу роль..."
    )

def get_days_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Понедельник"), KeyboardButton(text="Вторник")],
            [KeyboardButton(text="Среда"), KeyboardButton(text="Четверг")],
            [KeyboardButton(text="Пятница"), KeyboardButton(text="Суббота")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите день недели..."
    )

# --- РАБОТА С API ---

async def fetch_schedule_json(entity_id: int, role: str, target_weekday: int) -> dict:
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    target_date_obj = monday + datetime.timedelta(days=target_weekday - 1)
    target_date_str = target_date_obj.strftime("%Y-%m-%d")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if role == "student":
        url = "https://schedule.mstimetables.ru/api/publications/group/lessons"
        payload = {"publicationId": PUB_ID, "groupId": str(entity_id), "date": target_date_str}
    else:
        url = "https://schedule.mstimetables.ru/api/publications/teacher/lessons"
        payload = {"publicationId": PUB_ID, "teacherId": str(entity_id), "date": target_date_str}
    
    try:
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        async with aiohttp.ClientSession(connector=connector) as api_session:
            async with api_session.post(url, json=payload, headers=headers, ssl=False) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        logging.error(f"API Error: {e}")
        
    return None

def format_day_schedule(lessons_data: list, target_weekday: int, day_name: str, pretty_name: str, role: str) -> str:
    day_lessons = [l for l in lessons_data if l.get("weekday") == target_weekday]
    
    header = f"📌 <b>Расписание для: {pretty_name}</b>\n📅 <b>День: {day_name}</b>\n\n"
    
    if not day_lessons:
        return header + "🏖 <b>Пар нет (отдыхаем).</b>"

    day_lessons.sort(key=lambda x: x.get("lesson", 0))
    result = header
    
    for lesson in day_lessons:
        num = lesson.get("lesson", "")
        time = f"{lesson.get('startTime', '')} - {lesson.get('endTime', '')}"
        subject = lesson.get("subject", {}).get("name", "Предмет")
        
        cabinet_data = lesson.get("cabinet", {})
        cabinet_name = cabinet_data.get("name", "—")
        building_name = cabinet_data.get("building", {}).get("name", "")
        
        result += f"<b>{num}. {subject}</b>\n"
        result += f"⏰ <b>Время:</b> {time}\n"
        if building_name:
            result += f"🏢 <b>Корпус:</b> {building_name}\n"
        result += f"📍 <b>Аудитория:</b> {cabinet_name}\n"
        
        if role == "student":
            teachers = ", ".join([t["fio"] for t in lesson.get("teachers", []) if "fio" in t]) or "—"
            result += f"👨‍🏫 <b>Преподаватель:</b> {teachers}\n\n"
        else:
            groups = ", ".join([g["group"]["name"] for g in lesson.get("unionGroups", []) if "group" in g]) or "—"
            result += f"👥 <b>Группа:</b> {groups}\n\n"
        
    return result

# --- ХЭНДЛЕРЫ БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Получаем имя пользователя из Телеграма (если скрыто, ставим "студент")
    user_name = message.from_user.first_name or "студент"
    
    text = (
        f"👋 Привет, {user_name}! Ты попал в бота - расписание КИПО.\n\n"
        "Выбери на кнопку ниже кто ты:"
    )
    
    try:
        # Пробуем отправить сообщение с картинкой
        await message.answer_photo(
            photo=PHOTO_URL,
            caption=text,
            reply_markup=get_main_keyboard()
        )
    except Exception:
        # Если ссылка на картинку битая, отправляем просто текст
        await message.answer(
            text,
            reply_markup=get_main_keyboard()
        )

# --- ВЕТКА ПРЕПОДАВАТЕЛЕЙ ---
@dp.message(F.text == "👨‍🏫 Я преподаватель")
async def process_teacher_role(message: Message, state: FSMContext):
    await message.answer(
        "Введите вашу фамилию:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)
    )
    await state.set_state(ScheduleForm.waiting_for_teacher_name)

@dp.message(ScheduleForm.waiting_for_teacher_name)
async def fetch_teacher_name_step(message: Message, state: FSMContext):
    query = message.text.strip().lower()
    
    if query == "🔙 назад":
        await state.clear()
        # Вызываем стартовую функцию напрямую, чтобы при возврате тоже была фотка (опционально)
        await cmd_start(message, state)
        return

    teacher_id = None
    pretty_name = query
    
    for fio, tid in TEACHERS_DICT.items():
        if query in fio:
            teacher_id = tid
            pretty_name = next(t["fio"] for t in TEACHERS_LIST if t["id"] == tid)
            break
            
    if not teacher_id:
        await message.answer("Преподаватель не найден. Проверьте правильность ввода.")
        return

    await state.update_data(entity_id=teacher_id, role="teacher", pretty_name=pretty_name)
    await message.answer(f"✅ Преподаватель найден: <b>{pretty_name}</b>\nТеперь выберите день недели:", parse_mode="HTML", reply_markup=get_days_keyboard())
    await state.set_state(ScheduleForm.waiting_for_day)

# --- ВЕТКА СТУДЕНТОВ ---
@dp.message(F.text == "👨‍🎓 Я студент")
async def process_student_role(message: Message, state: FSMContext):
    await message.answer(
        "Напиши номер своей группы (Пример: 26-РИС1-9 или 25-ЗУ-11):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)
    )
    await state.set_state(ScheduleForm.waiting_for_student_group)

@dp.message(ScheduleForm.waiting_for_student_group)
async def fetch_student_group_step(message: Message, state: FSMContext):
    query = message.text.strip().lower()
    
    if query == "🔙 назад":
        await state.clear()
        await cmd_start(message, state)
        return

    group_id = None
    pretty_name = query
    
    for g_name, gid in GROUPS_DICT.items():
        if query in g_name: 
            group_id = gid
            pretty_name = next(g["name"] for g in GROUPS_LIST if g["id"] == gid)
            break
            
    if not group_id:
        await message.answer("Группа не найдена. Проверьте правильность ввода.")
        return

    await state.update_data(entity_id=group_id, role="student", pretty_name=pretty_name)
    await message.answer(f"✅ Группа найдена: <b>{pretty_name}</b>\nТеперь выберите день недели:", parse_mode="HTML", reply_markup=get_days_keyboard())
    await state.set_state(ScheduleForm.waiting_for_day)

# --- ВЫБОР ДНЯ И ВЫДАЧА РАСПИСАНИЯ ---
@dp.message(ScheduleForm.waiting_for_day)
async def fetch_schedule_by_day(message: Message, state: FSMContext):
    day_text = message.text.strip().lower()
    
    if day_text == "🔙 назад":
        await state.clear()
        await cmd_start(message, state)
        return
        
    if day_text not in DAYS_MAPPING:
        await message.answer("Пожалуйста, используйте кнопки меню для выбора дня недели.")
        return
        
    target_weekday = DAYS_MAPPING[day_text]
    day_name = message.text.strip()
    
    data_state = await state.get_data()
    entity_id = data_state.get("entity_id")
    role = data_state.get("role")
    pretty_name = data_state.get("pretty_name")
    
    await message.answer(f"🔍 Загружаю расписание на {day_name}...")
    
    data = await fetch_schedule_json(entity_id, role, target_weekday)
    
    if data and "lessons" in data:
         text = format_day_schedule(data["lessons"], target_weekday, day_name, pretty_name, role)
         await message.answer(text, parse_mode="HTML", reply_markup=get_days_keyboard())
    else:
         await message.answer("Не удалось получить данные с сервера КИПО.", reply_markup=get_days_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
