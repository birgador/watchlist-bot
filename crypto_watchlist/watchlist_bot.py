# import os
import http
# import json
# import traceback

from flask import Flask, request
from werkzeug.wrappers import Response


# import binance.client
from pycoingecko import CoinGeckoAPI

from telegram import Update,Bot, InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, Dispatcher, PicklePersistence, CallbackQueryHandler
from GoogleCloudStoragePersistence import GoogleCloudStoragePersistence

# watchlist = json.loads(bucket.get_blob('watchlist.json').download_as_string())
''' HELPING FUNCTIONS GO HERE '''
def merge_into_dict(test_list):

    res = {key: list({sub[key] for sub in test_list if key in sub})
      for key in {key for sub in test_list for key in sub}}

    return res
def print_cg_data(update,context,coin):
    api_call = cg.get_coin_by_id(coin)
    market_cap_rank = str(api_call['market_data']['market_cap_rank'])
    market_cap = str(api_call['market_data']['market_cap']['usd'])
    price = str(api_call['market_data']['current_price']['usd'])
    if api_call['market_data']['price_change_percentage_24h'] != None:
        price_24 = str(round(api_call['market_data']['price_change_percentage_24h'],2))
    else:
        price_24 = 'None'
    ath = str(api_call['market_data']['ath']['usd'])
    ath_date = str(api_call['market_data']['ath_date']['usd'])
    ath_change_percentage = str(round(api_call['market_data']['ath_change_percentage']['usd'],2))
    watchlist = context.chat_data['watchlist']
    context.bot.send_message(
        chat_id = update.effective_chat.id,
        text=coin+': \n'+
        ' Desc: '+watchlist[coin]+'\n'
        ' Price: '+price+' usd ('+price_24+'% 24h) \n'+
        ' Market cap: '+market_cap+' ('+market_cap_rank+')'+'\n'+
        ' ATH: '+ath+' ('+ath_change_percentage+' % since ath)'
        )


''' TELEGRAM BOT CONF AND SETUP GOES HERE '''

cg = CoinGeckoAPI()

coins = cg.get_coins_list(include_platform=True)

symbols_list = [{coin['symbol']:coin['id']} for coin in coins]
symbols_to_ids = merge_into_dict(symbols_list)

ids = {coin['id']:{'name':coin['name'],'symbol':coin['symbol'],'platforms':coin['platforms']} for coin in coins}

token = 'TOKEN'

watchlist_persistence = GoogleCloudStoragePersistence(filename='watchlist.json',bucketname='crypto-watchlist')


app = Flask(__name__)


''' BOT COMMANDS AND LOGIC GO HERE '''

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    # context.chat_data.clear()
    if 'watchlist' not in context.chat_data:
        context.chat_data['watchlist'] = {}
    update.message.reply_text("Let's go get some tendies ($_$)")
    update.message.reply_animation("https://media1.tenor.com/images/bf327be1ebbde7f32baf5136042bf118/tenor.gif?itemid=14563637")

def clear(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    context.chat_data.clear()
    context.chat_data['watchlist'] = {}
    update.message.reply_text("Clearrr")
   
def addToken(update, context):
    """Usage: /get uuid"""
    # Seperate ID from command
    desc = ''
    for arg in context.args[1:]:
        desc+=arg+" "
    coin = context.args[0]

    if coin not in  context.chat_data['watchlist']:     #Check if coin id already in watchlist. This applies for coins where id = symbol
        
        if coin in symbols_to_ids:      #They should use symbols to add coins and get prompted duplicates to use id
            if len(symbols_to_ids[coin]) > 1:   # If there are more than 1 candidates for same symbol
                update.message.reply_text('I have found these coin-ids for symbol: {coin}. Please try choose one and try again'.format(coin = coin))
                candidates = symbols_to_ids[coin].copy()
                for candidate in candidates:
                    if candidate in context.chat_data['watchlist']:
                        candidates.pop(candidates.index(candidate))

                keyboard = [
                    [InlineKeyboardButton(i, callback_data=i+"desc:"+desc) for i in candidates]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text('Please choose:', reply_markup=reply_markup)
            else:
                id = symbols_to_ids[coin][0]
                context.chat_data['watchlist'][id] = desc
                update.message.reply_text('Added {coin} to watchlist!'.format(coin = id))
        elif coin in ids:
            context.chat_data['watchlist'][coin] = desc
            update.message.reply_text('Added {coin} to watchlist!'.format(coin = coin))
        else:
            update.message.reply_text('Cannot add {coin}. It is not listed on Coingecko!'.format(coin = coin))

#List tokens
def tokens(update,context):
    watchlist = context.chat_data['watchlist']
    
    if watchlist != {}:
        message = ''
        for id in watchlist:
            symb = ids[id]['symbol']
            name = ids[id]['name']
            message += id+' ('+symb.upper()+', '+name+')\n'
    else:
        message = 'No coins in wathclist yet'
    context.bot.send_message(chat_id = update.effective_chat.id,text = message)


def show(update,context):
    
    # message = update.message.text

    coin = context.args[0]
    if coin in context.chat_data['watchlist']:      #They have written /show coinId
        print_cg_data(update,context,coin)
    elif coin in symbols_to_ids and(True in [id in context.chat_data['watchlist'] for id in symbols_to_ids[coin]]):             #They have written /show coinSymbol
        # [id for id in symbols_to_ids[coin] if id in context.chat_data['watchlist']]
        # print([id for id in symbols_to_ids[coin] if id in context.chat_data['watchlist']])
        keyboard = [
                    [InlineKeyboardButton(id, callback_data='show:'+id) for id in symbols_to_ids[coin] if id in context.chat_data['watchlist']]
                ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Found one or more coins in watchlist with symbol: {coin}. Please choose one coin id.'.format(coin=coin), reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id = update.effective_chat.id,text='Wrong name. This token is not in watchlist')

''' InlineKeyboardButton logic goes here '''


def buttonAdd(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query.answer()
    partition = query.data.partition("desc:")
    coin = partition[0]
    desc = partition[2]
    context.chat_data['watchlist'][coin] = desc
    query.edit_message_text(text=f"Added: {coin} to watchlist!")


def buttonShow(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    partition = query.data.partition("show:")
    coin = partition[2]
    query.edit_message_text(text=f"Showing: {coin}")
    print_cg_data(update,context,coin)

#Telegram api and wrapper logic
bot = Bot(token=token)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0, persistence=watchlist_persistence, use_context=True)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("clear", clear))
dispatcher.add_handler(CommandHandler('add', addToken))
dispatcher.add_handler(CommandHandler('tokens', tokens))
dispatcher.add_handler(CommandHandler('show', show))
dispatcher.add_handler(CallbackQueryHandler(buttonShow,pattern='show:'))
dispatcher.add_handler(CallbackQueryHandler(buttonAdd,pattern='.*desc:.*'))

@app.route("/", methods=["POST"])
def index() -> Response:
    dispatcher.process_update(
        Update.de_json(request.get_json(force=True), bot))

    return "OMG", http.HTTPStatus.NO_CONTENT
