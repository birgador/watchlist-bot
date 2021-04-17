import os
import http
import json
import traceback

from flask import Flask, request
from werkzeug.wrappers import Response


import binance.client
from pycoingecko import CoinGeckoAPI

from telegram import Update,Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, Dispatcher

from google.cloud import storage

cg = CoinGeckoAPI()
coins = cg.get_coins_list()

coin_list= {ids['id']:ids['symbol'] for ids in coins}

coin_ids = [coin['id'] for coin in coins]
coin_symbols = [coin['symbol'] for coin in coins]

ids_to_symbols = dict(zip(coin_ids,coin_symbols))
symbols_to_ids = dict(zip(coin_symbols,coin_ids))

storage_client = storage.Client()
bucket = storage_client.get_bucket('watchlist-bot')



token = 'telegram-token'

app = Flask(__name__)
# excep = ''

#Add token
def addToken(update,context):

    try:
        watchlist = json.loads(bucket.get_blob('watchlist.json').download_as_string())
        message = update.message.text.split('/add')[1].lstrip()
        parsed_coin = message.split(' ')[0]
        desc=''
        # Check if coin in watchlist and then if in coingecko
        if parsed_coin not in watchlist and symbols_to_ids[parsed_coin] not in watchlist:
            for word in message.split(' ')[1:]:
                    desc += word+' '
            if parsed_coin in coin_ids or parsed_coin.lower() in coin_ids:
                coin = parsed_coin    
            elif parsed_coin in coin_symbols or parsed_coin.lower() in coin_symbols:
                coin = symbols_to_ids[parsed_coin]
            else:
                coin=''
                context.bot.send_message(chat_id = update.effective_chat.id,text='Cannot add '+parsed_coin+' to watchlist. It is not listed on Coingecko!')
            #Add coin to watchlist
            if coin != '':
                watchlist[coin] = desc
                bucket.get_blob('watchlist.json').upload_from_string(json.dumps(watchlist))
                context.bot.send_message(chat_id = update.effective_chat.id,text='Added '+coin+' to watchlist!')
        else:
            context.bot.send_message(chat_id = update.effective_chat.id,text='Not to FOMO or anything, but coin already in watchlist ( ͡° ͜ʖ ͡°)')
    except:
        # excep = traceback.format_exc()
        context.bot.send_message(chat_id = update.effective_chat.id,text='Something went wrong. Please use /exc to see the error')
        context.bot.send_message(chat_id = update.effective_chat.id,text='The syntax is /add token Description')

#List tokens
def tokens(update,context):
    watchlist = json.loads(bucket.get_blob('watchlist.json').download_as_string())
    message = ''
    
    for coin in watchlist:
        symb = ids_to_symbols[coin]
        message += symb.upper()+'\n'
    bot.send_message(chat_id = update.effective_chat.id,text = message)

# def exc(update,context):
#     if excep != '':
#         context.bot.send_message(chat_id = update.effective_chat.id,text=excep)
#     else:
#         context.bot.send_message(chat_id = update.effective_chat.id,text='No errors!')

#Show token info
def show(update,context):
    watchlist = json.loads(bucket.get_blob('watchlist.json').download_as_string())
    message = update.message.text
    try:
        parsed_coin = message.split(' ')[1]
        if parsed_coin in symbols_to_ids or parsed_coin.lower() in symbols_to_ids:
            coin = symbols_to_ids[parsed_coin]
        elif parsed_coin in ids_to_symbols or parsed_coin.lower() in ids_to_symbols:
            coin = parsed_coin
        # str(cg.get_price(ids=coin,vs_currencies='usd')[coin]['usd'])
        api_call = cg.get_coin_by_id(coin)
        market_cap_rank = str(api_call['market_data']['market_cap_rank'])
        market_cap = str(api_call['market_data']['market_cap']['usd'])
        price = str(api_call['market_data']['current_price']['usd'])
        price_24 = str(round(api_call['market_data']['price_change_percentage_24h'],2))
        ath = str(api_call['market_data']['ath']['usd'])
        ath_date = str(api_call['market_data']['ath_date']['usd'])
        ath_change_percentage = str(round(api_call['market_data']['ath_change_percentage']['usd'],2))

        context.bot.send_message(
            chat_id = update.effective_chat.id,
            text=coin+': \n'+
            ' Desc: '+watchlist[coin]+'\n'
            ' Price: '+price+' usd ('+price_24+'% 24h) \n'+
            ' Market cap: '+market_cap+' ('+market_cap_rank+')'+'\n'+
            ' ATH: '+ath+' ('+ath_change_percentage+' % since ath)'
            )
    except:
        # print(traceback.format_exc())
        # context.bot.send_message(chat_id = update.effective_chat.id,text=traceback.format_exc())
        context.bot.send_message(chat_id = update.effective_chat.id,text='Wrong name. This token is not in watchlist')


#Telegram api and wrapper logic
bot = Bot(token=token)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0)


add_token_handler = CommandHandler('add',addToken)
dispatcher.add_handler(add_token_handler)

show_token_handler = CommandHandler('show',show)
dispatcher.add_handler(show_token_handler)

# exc_handler = CommandHandler('exc',exc)
# dispatcher.add_handler(exc_handler)

tokens_handler = CommandHandler('tokens',tokens)
dispatcher.add_handler(tokens_handler)



@app.route("/", methods=["POST"])
def index() -> Response:
    dispatcher.process_update(
        Update.de_json(request.get_json(force=True), bot))

    return "OMG", http.HTTPStatus.NO_CONTENT