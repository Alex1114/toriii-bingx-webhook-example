import json
import config
import time, datetime
import math
from flask import Flask, request, jsonify, render_template
import bingx

import telegram
from telegram.ext import Updater, CommandHandler, Dispatcher, MessageHandler, Filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

############### Telegram BOT Setting ###############
updater = Updater(token=config.TELEGRAM_TOKEN, use_context=False)
bot = telegram.Bot(token=config.TELEGRAM_TOKEN)
chat_id = config.TELEGRAM_CHAT_ID

############### BingX Function ###############
APIURL = 'https://api-swap-rest.bingbon.pro'
APIKEY = config.API_KEY
SECRETKEY = config.API_SECRET
marginType = "Isolated"
leverage = 10
safeOrderAmount = 2000 #2000
initialCapital = 1256.48
startDate = "2022/08/02"

def futures_order(side, orderPrice, quantity, symbol, leverage, leverage_side, action, order_type="Market"):
	try:
		ts = time.time()
		bingx.setMarginMode(symbol, marginType, APIKEY, APIURL, SECRETKEY)

	except Exception as e:
		if str(e) == "APIError(code=-4046): No need to change margin type.":
			pass
		else:
			print("an exception occured - {}".format(e))
			bot.sendMessage(chat_id=chat_id, text=f"[Fail] Futures order\n-\n{side} {quantity} {symbol} {leverage}x\nAn exception occured - {e}")
			return False

	try:
		print(f"sending futures order {order_type} - {side} {quantity} {symbol}")
		bingx.setLeverage(symbol, leverage_side, leverage, APIKEY, APIURL, SECRETKEY)
		order = json.loads(bingx.placeOrder(symbol, side, orderPrice, quantity, order_type, action, APIKEY, APIURL, SECRETKEY))

	except Exception as e:
		print("an exception occured - {}".format(e))
		bot.sendMessage(chat_id=chat_id, text=f"[Fail] Futures order\n-\n{side} {quantity} {symbol} {leverage}x\nAn exception occured - {e}")

		return False

	return order

def flat_future_order(symbol, orderAmount):
	pricePrecision, volumePrecision = get_futures_precision(symbol = symbol)

	try:
		get_futures_order_response = json.loads(bingx.getPositions(symbol, APIKEY, APIURL, SECRETKEY))

		if get_futures_order_response["data"]["positions"] != None:
			totalQuantity = get_futures_order_response["data"]["positions"][0]["availableVolume"]
			entryPrice = float(get_futures_order_response["data"]["positions"][0]["avgPrice"])
			markPrice = float(json.loads(bingx.tickerPrice(symbol, APIURL))["data"]["indexPrice"])
			positionSide = get_futures_order_response["data"]["positions"][0]["positionSide"]
			safeQuantity = safeOrderAmount / markPrice
			times = abs(int(totalQuantity / safeQuantity)) + 1
			quantity = math.floor(float(totalQuantity / times) * math.pow(10, volumePrecision)) / math.pow(10, volumePrecision)

			# Closing positions in batches
			if positionSide == "Long":
				side = "Ask"
				leverage_side = "Short"
			else:
				side = "Bid"
				leverage_side = "Long"
		else:
			# bot.sendMessage(chat_id=chat_id, text=f"The {symbol} position is already closed.")
			return True

	except Exception as e:
		bot.sendMessage(chat_id=chat_id, text=f"[Fail] The {symbol} position closed error.")

		return {
			"code": "error",
			"message": "The position closed error."
		}

	# execute    
	if times > 1:
		for t in range(times-1):
			order_response = futures_order(side, markPrice, abs(quantity), symbol, leverage, leverage_side, "Close")
		order_response = futures_order(side, markPrice, abs((totalQuantity - (quantity * (times-1)))), symbol, leverage, leverage_side, "Close")
	if times == 1:
		order_response = futures_order(side, markPrice, abs(totalQuantity), symbol, leverage, leverage_side, "Close")

	if order_response:
		profit = round((float(markPrice) - float(entryPrice))
					   * float(totalQuantity), 2)
		percent = round((profit / (orderAmount / leverage)) * 100, 2)
		TgSymbol = symbol.split("-")[0] + symbol.split("-")[1]
		if side == "Bid":
			side = "BUY"
		else:
			side = "SELL"
		bot.sendMessage(chat_id=chat_id, text=f"[Success] Futures order\n-\n{side} ${orderAmount} {TgSymbol} {leverage}x\n-\nProfit: ${str(profit)} ({str(percent)}%)")

	return order_response

def get_futures_precision(symbol):
	try:
		allContract = json.loads(bingx.getContracts(APIURL))

		for i in range(len(allContract["data"]["contracts"])):
			if allContract["data"]["contracts"][i]["symbol"] == symbol:
				pricePrecision = allContract["data"]["contracts"][i]["pricePrecision"]
				volumePrecision = allContract["data"]["contracts"][i]["volumePrecision"]

				if pricePrecision >= 1:
					pricePrecision = pricePrecision - 1 

	except Exception as e:
		print("an exception occured - {}".format(e))
		return False

	return pricePrecision, volumePrecision

################ Trading Webhook ###############
@app.route('/')
def welcome():
	return render_template('index.html')

################ Futures Webhook ###############
@app.route('/webhook_futures', methods=['POST'])
def webhook_futures():
	order_response = False
	data = json.loads(request.data)

	# check passphrase
	if data['passphrase'] != config.WEBHOOK_PASSPHRASE:
		bot.sendMessage(chat_id=chat_id, text="[Invalid passphrase]\nSomeone tried to hack your trading system.")
		
		return {
			"code": "error",
			"message": "Invalid passphrase! Someone tried to hack your trading system."
		}

	# order info
	market_position = data['strategy']['market_position']
	prev_market_position = data['strategy']['prev_market_position']
	ticker = data['ticker'].split("USDT")[0] + "-USDT"
	margin = int(data['margin'])
	orderAmount = leverage * margin
	orderPrice = data['strategy']['order_price']
	# minutes = data['time'].split(":")[1]

	# if minutes in ["58", "59", "00", "01", "02"]:
	# Precision and quantity
	pricePrecision, volumePrecision = get_futures_precision(symbol = ticker)
	quantity = float(round(orderAmount / orderPrice, volumePrecision))

	# Order side
	# Flat
	if market_position == "flat":
		order_response = flat_future_order(ticker, orderAmount)

	# Long
	if market_position == "long":
		if prev_market_position == "long":
			side = "Bid"
			leverage_side = "Long"
			order_response = futures_order(side, orderPrice, quantity, ticker, leverage, leverage_side, "Open")

			if order_response:
				TgSymbol = ticker.split("-")[0] + ticker.split("-")[1]
				bot.sendMessage(chat_id=chat_id, text=f"[Success] Futures order\n-\nBUY ${orderAmount} {TgSymbol} {leverage}x")

		else:
			order_response = flat_future_order(ticker, orderAmount)

			if order_response:
				side = "Bid"
				leverage_side = "Long"
				order_response = futures_order(side, orderPrice, quantity, ticker, leverage, leverage_side, "Open")

				if order_response:
					TgSymbol = ticker.split("-")[0] + ticker.split("-")[1]
					bot.sendMessage(chat_id=chat_id, text=f"[Success] Futures order\n-\nBUY ${orderAmount} {TgSymbol} {leverage}x")

			else:
				pass

	# Short
	if market_position == "short":
		if prev_market_position == "short":
			side = "Ask"
			leverage_side = "Short"
			order_response = futures_order(side, orderPrice, quantity, ticker, leverage, leverage_side, "Open")

			if order_response:
				TgSymbol = ticker.split("-")[0] + ticker.split("-")[1]
				bot.sendMessage(chat_id=chat_id, text=f"[Success] Futures order\n-\nSELL ${orderAmount} {TgSymbol} {leverage}x")

		else:
			order_response = flat_future_order(ticker, orderAmount)

			if order_response:
				side = "Ask"
				leverage_side = "Short"
				order_response = futures_order(side, orderPrice, quantity, ticker, leverage, leverage_side, "Open")

				if order_response:
					TgSymbol = ticker.split("-")[0] + ticker.split("-")[1]
					bot.sendMessage(chat_id=chat_id, text=f"[Success] Futures order\n-\nSELL ${orderAmount} {TgSymbol} {leverage}x")

			else:
				pass

	if order_response:
		print("Order success")	
		return {
			"code": "success",
			"message": "order executed"
		}
	else:
		print("Order failed")
		return {
			"code": "error",
			"message": "order failed"
		}


@app.route('/develop_test', methods=['POST']) 
def develop_test():
	data = json.loads(request.data)

	# order info
	market_position = data['strategy']['market_position']
	prev_market_position = data['strategy']['prev_market_position']
	ticker = data['ticker'].split("USDT")[0] + "-USDT"
	margin = int(data['margin'])
	orderAmount = leverage * margin
	orderPrice = data['strategy']['order_price']

	getPositions = json.loads(bingx.getPositions(ticker, APIKEY, APIURL, SECRETKEY))
	# getBalance = json.loads(bingx.getBalance(APIKEY, APIURL, SECRETKEY))
	# tickerPrice = json.loads(bingx.tickerPrice(ticker, APIURL))
	# getContracts = json.loads(bingx.getContracts(APIURL))
	# setMarginMode = json.loads(bingx.setMarginMode(ticker, "Isolated", APIKEY, APIURL, SECRETKEY))
	# setLeverage = json.loads(bingx.setLeverage(ticker, "Long", 10, APIKEY, APIURL, SECRETKEY))
	# order_response = json.loads(bingx.placeOrder(ticker, "Ask", 23151.9, 0.004319, "Market", "Close", APIKEY, APIURL, SECRETKEY))
	# order_response = json.loads(bingx.closeOnePosition(ticker, 1554154564800741376, APIKEY, APIURL, SECRETKEY))
	# order_response = json.loads(bingx.closeAllPositions(APIKEY, APIURL, SECRETKEY))
		
	# check order result
	if getPositions:
		return {
			"code": "success",
			"message": getPositions
		}
	else:
		print("order failed")
		return {
			"code": "error",
			"message": "order failed"
		}

############### Telegram ###############
@app.route("/telegram_callback", methods=['POST'])
def webhook_handler():
	if request.method == "POST":
		update = telegram.Update.de_json(request.get_json(force=True), bot)
		# chat_id = update.message.chat.id
		# msg_id = update.message.message_id
		# text = update.message.text.encode('utf-8').decode()

		dispatcher.process_update(update)
	return 'ok', 200

def telegram_callback(bot, update):
	try:
		operation = str(bot.message.text.split(" ")[0]).upper()
		ticker = str(bot.message.text.split(" ")[1]).upper()
	except Exception as e:
		pass

	if operation == "GET":
		try:
			position_text = "Futures order\n-\n"
			totalUnrealizedProfit = 0
			has_position = False
			get_futures_order_response = json.loads(bingx.getPositions("", APIKEY, APIURL, SECRETKEY))

			for i in range(len(get_futures_order_response["data"]["positions"])):
				has_position = True
				symbol = get_futures_order_response["data"]["positions"][i]["symbol"]
				entryPrice = round(float(get_futures_order_response["data"]["positions"][i]["avgPrice"]), 6)
				margin = float(get_futures_order_response["data"]["positions"][i]["margin"]) + abs(float(get_futures_order_response["data"]["positions"][i]["unrealisedPNL"]))
				leverageLevel = get_futures_order_response["data"]["positions"][i]["leverage"]
				unrealizedProfit = round(float(get_futures_order_response["data"]["positions"][i]["unrealisedPNL"]), 2)
				markPrice = round(float(json.loads(bingx.tickerPrice(symbol, APIURL))["data"]["indexPrice"]), 6)
				percent = round((unrealizedProfit / margin) * 100, 2)
				totalUnrealizedProfit += unrealizedProfit
				side = get_futures_order_response["data"]["positions"][i]["positionSide"]
				tmp_text = f"Symbol: {symbol}\nSide: {side}\nMargin: {str(margin)}\nLeverage: {str(leverageLevel)}x\nEntry Price: {str(entryPrice)}\nMark Price: {str(markPrice)}\n-\nUnrealized Profit: ${str(unrealizedProfit)} ({str(percent)}%)\n\n==========\n\n"

				position_text = position_text + tmp_text

			if has_position == False:
				bot.message.reply_text(text="No position.")
			else:
				position_text = position_text + "Total Unrealized Profit: $" + str(round(totalUnrealizedProfit, 2))
				bot.message.reply_text(text=position_text)
					
		except Exception as e:
			print("Fail to get futures orders.")
			bot.message.reply_text(text="Fail to get futures orders.")


	elif operation == "CLOSE":
		if ticker == "ALL":
			try:
				position_text = "[Success] Futures order\n-\n"
				totalProfit = 0

				get_futures_order_response = json.loads(bingx.getPositions("", APIKEY, APIURL, SECRETKEY))

				for i in range(len(get_futures_order_response["data"]["positions"])):
					has_position = True
					symbol = get_futures_order_response["data"]["positions"][i]["symbol"]
					entryPrice = round(float(get_futures_order_response["data"]["positions"][i]["avgPrice"]), 6)
					margin = float(get_futures_order_response["data"]["positions"][i]["margin"]) + abs(float(get_futures_order_response["data"]["positions"][i]["unrealisedPNL"]))
					leverageLevel = get_futures_order_response["data"]["positions"][i]["leverage"]
					profit = round(float(get_futures_order_response["data"]["positions"][i]["unrealisedPNL"]), 2)
					markPrice = round(float(json.loads(bingx.tickerPrice(symbol, APIURL))["data"]["indexPrice"]), 6)
					percent = round((profit / margin) * 100, 2)
					totalProfit += profit
					side = get_futures_order_response["data"]["positions"][i]["positionSide"]
					tmp_text = f"Closed {symbol} {leverageLevel}x\nMargin: {margin}\nEntry Price: {str(entryPrice)}\nExit Price: {str(markPrice)}\n-\nProfit: ${str(profit)} ({str(percent)}%)\n\n==========\n\n"
					position_text = position_text + tmp_text

				order_response = json.loads(bingx.closeAllPositions(APIKEY, APIURL, SECRETKEY))

				if order_response["data"]["orders"] != None:
					position_text = position_text + "Total Profit: $" + str(round(totalProfit, 2))
					bot.message.reply_text(text=position_text)
				else:
					bot.message.reply_text(text="No position.")

			except Exception as e:
				bot.message.reply_text(text=f"All futures closed failed.")

		else:
			try:
				get_futures_order_response = json.loads(bingx.getPositions("", APIKEY, APIURL, SECRETKEY))
				ticker = ticker + "-USDT"
				has_position = False

				for i in range(len(get_futures_order_response["data"]["positions"])):
					if get_futures_order_response["data"]["positions"][i]["symbol"] == ticker:
						has_position = True
						margin = float(get_futures_order_response["data"]["positions"][i]["margin"]) + abs(float(get_futures_order_response["data"]["positions"][i]["unrealisedPNL"]))
						orderAmount = leverage * margin

						order_response = flat_future_order(ticker, orderAmount)

				if has_position == False:
					bot.message.reply_text(text=f"The {ticker} position is already closed.")

			except Exception as e:
				bot.message.reply_text(text="Futures closed failed.")

	elif operation == "PROFIT":
		get_futures_order_response = json.loads(bingx.getBalance(APIKEY, APIURL, SECRETKEY))

		walletBalance = round(float(get_futures_order_response["data"]["account"]["equity"]), 2)
		totalRevenue = round(float(walletBalance - initialCapital), 2)
		totalPercent = round(float((totalRevenue / initialCapital) * 100), 2)

		struct_time = time.strptime(startDate, "%Y/%m/%d")
		time_stamp = int(time.mktime(struct_time))
		nowTime = time.time()
		day = math.ceil((nowTime - time_stamp) / 86400)

		if totalPercent <= 0:
			tmp_text = f"【 Performance - Start From {startDate} 】\n-\nInitial Capital: ${str(initialCapital)}\nWallet Balance: ${str(walletBalance)}\nTotal Revenue: ${str(totalRevenue)} ({str(totalPercent)}%)\n"
		else:
			tmp_text = f"【 Performance - Start From {startDate} 】\n-\nInitial Capital: ${str(initialCapital)}\nWallet Balance: ${str(walletBalance)}\nTotal Revenue: ${str(totalRevenue)} ({str(totalPercent)}%)\nAPR: {str(round(totalPercent * (365 / day), 2))}%\n"

		bot.message.reply_text(text=tmp_text)

	else:
		pass
		# bot.message.reply_text(text="Please enter the correct command format.\n\nInput: [operation] [symbol]\nex.\nclose ETH\nclose all\nget")

	return 'ok', 200


# Add handler for handling message, there are many kinds of message. For this handler, it particular handle text message.
dispatcher = Dispatcher(bot, None)
dispatcher.add_handler(MessageHandler(Filters.text, telegram_callback))