import urllib.request
import base64
import hmac
import time
import requests

def genSignature(path, method, paramsMap, SECRETKEY):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr = method + path + paramsStr
    return hmac.new(SECRETKEY.encode("utf-8"), paramsStr.encode("utf-8"), digestmod="sha256").digest()

def post(url, body):
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req).read()

def tickerPrice(symbol, APIURL):
    paramsMap = {
        'symbol': symbol
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    url = "%s/api/v1/market/getLatestPrice?symbol=%s" % (APIURL, symbol)
    req = requests.request("GET", url, headers={'User-Agent': 'Mozilla/5.0'}, data=paramsStr)
    return req.text

def getContracts(APIURL):
    url = "%s/api/v1/market/getAllContracts" % APIURL
    req = requests.request("GET", url, headers={'User-Agent': 'Mozilla/5.0'})
    return req.text

def getBalance(APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "apiKey": APIKEY,
        "timestamp": int(time.time()*1000),
        "currency": "USDT",
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/getBalance", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/getBalance" % APIURL
    return post(url, paramsStr)

def getPositions(symbol, APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "symbol": symbol,
        "apiKey": APIKEY,
        "timestamp": int(time.time()*1000),
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/getPositions", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/getPositions" % APIURL
    return post(url, paramsStr)

def placeOrder(symbol, side, price, volume, tradeType, action, APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "symbol": symbol,
        "apiKey": APIKEY,
        "side": side,
        "entrustPrice": price,
        "entrustVolume": volume,
        "tradeType": tradeType,
        "action": action,
        "timestamp": int(time.time()*1000),
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/trade", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/trade" % APIURL
    return post(url, paramsStr)

def setMarginMode(symbol, marginMode, APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "symbol": symbol,
        "apiKey": APIKEY,
        "marginMode": marginMode,
        "timestamp": int(time.time()*1000),
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/setMarginMode", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/setMarginMode" % APIURL
    return post(url, paramsStr)

def setLeverage(symbol, side, leverage, APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "symbol": symbol,
        "apiKey": APIKEY,
        "side": side,
        "leverage": leverage,
        "timestamp": int(time.time()*1000),
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/setLeverage", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/setLeverage" % APIURL
    return post(url, paramsStr)

def closeOnePosition(symbol, positionId, APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "symbol": symbol,
        "apiKey": APIKEY,
        "positionId": positionId,
        "timestamp": int(time.time()*1000),
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/oneClickClosePosition", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/oneClickClosePosition" % APIURL
    return post(url, paramsStr)

def closeAllPositions(APIKEY, APIURL, SECRETKEY):
    paramsMap = {
        "apiKey": APIKEY,
        "timestamp": int(time.time()*1000),
    }
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    paramsStr += "&sign=" + urllib.parse.quote(base64.b64encode(genSignature("/api/v1/user/oneClickCloseAllPositions", "POST", paramsMap, SECRETKEY)))
    url = "%s/api/v1/user/oneClickCloseAllPositions" % APIURL
    return post(url, paramsStr)