from api_helper import ShoonyaApiPy, get_time
from fastapi import FastAPI, Query
from datetime import datetime
import uvicorn
import time
import yaml
import pandas as pd
import tkinter as tk
from datetime import datetime,timedelta
from tkinter import simpledialog
import logging
import os 

    
LOG_DIR = 'All_Order_Log'

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

#global setting
LOG_NEEDED = True
AUTO_PLACE_ORDER = False
NORMAL_LOG = False  

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Starting the application')

cred = None
li = ['17APR','01MAY','17JUL','02OCT','25DEC']

def update_otp_in_yaml(otp):
    with open('cred.yml') as f:
        cred = yaml.load(f, Loader=yaml.FullLoader)

    cred['factor2'] = otp

    with open('cred.yml', 'w') as f:
        yaml.dump(cred, f)
        print(cred)
    
def create_otp_gui():
    def _create_gui(): 
        root = tk.Tk()
        root.withdraw()
        otp = simpledialog.askstring("OTP", "Enter your OTP:", parent=root)
        if otp:
            update_otp_in_yaml(otp)
        else:
            print("No OTP provided. Exiting...")
        root.destroy()

    # Create a separate thread for GUI
    _create_gui()
    
if LOG_NEEDED or AUTO_PLACE_ORDER:
    create_otp_gui()

    api = ShoonyaApiPy()

    with open('cred.yml') as f:
        cred = yaml.load(f, Loader=yaml.FullLoader)
        print(cred)

    ret = api.login(userid=cred['user'], password=cred['pwd'], twoFA=cred['factor2'], vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])
    print(ret)
        
def get_log_file_path(symbol):
    date_str = time.strftime("%d-%m-%Y", time.localtime())
    return os.path.join(LOG_DIR, f"order_log_{symbol}-{date_str}.txt")

def make_log(symbol,message):
    t = time.strftime("%d-%m-%Y %H:%M:%S",time.localtime())
    log_file_path = get_log_file_path(symbol)
    with open(log_file_path,"a")as file:
        file.write(f"{t} {message}" + "\n")


order = {}

def generate_transformed_symbol(symbol):

    today = datetime.now()
    current_year = str(datetime.now().year%100)
    next_wednesday = today + timedelta((2 - today.weekday() + 7) % 7)
    expiry =   str(next_wednesday.day).zfill(2) + next_wednesday.strftime("%b").upper() 
    if expiry in li and (expiry == today.strftime("%d%b").upper()):
        next_wednesday += timedelta(days=7)
    elif expiry in li:
        next_wednesday -= timedelta(days=1) 
    expiry =  str(next_wednesday.day).zfill(2) + next_wednesday.strftime("%b").upper()
    option_type = symbol[-2]

    if 'BANKNIFTYWK' and '-I' in symbol:
        option_type = symbol[-3]
        strike_price = symbol[11:-3]
        transformed_symbol = 'BANKNIFTY'+expiry+current_year+option_type+strike_price
    elif 'BANKNIFTYWK' in symbol:
        option_type = symbol[-2]
        strike_price = symbol[11:-2]
        transformed_symbol = 'BANKNIFTY'+expiry+current_year+option_type+strike_price
    else:
        transformed_symbol = symbol.replace("-WK-",expiry+current_year+option_type)[:-2]
    return transformed_symbol



app = FastAPI()

@app.get("/buy")
async def my_api(
        symbol: str = Query(...),
        timeframe: str = Query(...),
        price: str = Query(...),
        qty: int = Query(...),
        date: str = Query(...),
        state: str = Query(...)
    ):
    he = symbol
    s = timeframe
    p = price
    d = date
    t = "buy"

    if symbol not in order:
        if LOG_NEEDED or AUTO_PLACE_ORDER:
            updated_symbol = generate_transformed_symbol(symbol)
            print(updated_symbol)
            print('came to buy order progress')
            rett = api.searchscrip(exchange='NFO',searchtext=updated_symbol)
            print(rett,'rett')
            order[symbol]={'state':None,'updated_symbol':updated_symbol,'token':rett['values'][0]['token']}
        else:
            order[symbol]={'state':None,'updated_symbol':None,'token':None}
        #order[symbol]={'state':None,'updated_symbol':updated_symbol}
    if order[symbol].get('state') == None: 
        order[symbol]['state'] = 'buy'
        print(f"\n Processing {t.capitalize()} Order - Symbol: {symbol}, Timeframe: {timeframe}, Price: {price}, Date: {date}", flush=True)

        if AUTO_PLACE_ORDER:
            ret = api.place_order(buy_or_sell='B', product_type='M',
                              exchange='NFO', tradingsymbol=order[symbol]['updated_symbol'],
                              quantity=15, discloseqty=0, price_type='MKT', price=0.00, trigger_price=None,
                              retention='DAY', remarks='amibroker')
            print(ret)
        
        if LOG_NEEDED:
            print('hello')
            ret = api.get_quotes(exchange='NFO', token=order[symbol]['token'])
            mktbuy = ret.get('sp1')
            make_log(symbol,f"Buy Order Executed for {symbol} at {mktbuy}") 

        if NORMAL_LOG:
            make_log(symbol,f"Buy Order Executed for {symbol} at {price}") 
    
        

@app.get("/sell")
async def my_ap(
    symbol: str = Query(...),
    timeframe: str = Query(...),
    price: str = Query(...),
    qty: str = Query(...),
    date: str = Query(...),
    state: str = Query(...)
    ):
    
    he = symbol
    s = timeframe
    p = price
    d = date
    t = "sell"

    if symbol in order and order[symbol]['state'] == 'buy':
        print('Sell order executed')
        if AUTO_PLACE_ORDER:
            ret = api.place_order(buy_or_sell='S', product_type='M',
                              exchange='NFO', tradingsymbol=order[symbol]['updated_symbol'],
                              quantity=15, discloseqty=0, price_type='MKT', price=0.00, trigger_price=None,
                              retention='DAY', remarks='amibroker')
            print(ret)
        
        if LOG_NEEDED:
            ret = api.get_quotes(exchange='NFO', token=order[symbol]['token'])
            mktsell = ret.get('bp1')
            make_log(symbol,f"Sell Order Executed for {symbol} at {mktsell}\n-----------------------------------------------------------------") 
        
        if NORMAL_LOG:
            make_log(symbol,f"Sell Order Executed for {symbol} at {price}\n-----------------------------------------------------------------") 


        order[symbol]['state'] = None
@app.get("/orderbook")
async def get_order_book():
    try:
        ret = api.get_order_book()
        return ret
    except Exception as e:
        return {"error": str(e)}

        
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
