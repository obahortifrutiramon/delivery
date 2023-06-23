import streamlit as st
import requests
import pandas as pd
import time
import hmac
import hashlib
import json
import pysftp
from datetime import datetime, timedelta


def getActiveStores(key, token):
    url = "https://obagalleria.vtexcommercestable.com.br/api/catalog_system/pvt/seller/list"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-VTEX-API-AppKey": key,
        "X-VTEX-API-AppToken": token
    }
    rVtexSellers = requests.get(url, headers=headers)
    sellerList = rVtexSellers.json()

    sellersDisabled = []
    sellerListActive = [""]
    for seller in sellerList:
        if seller['IsActive'] == True:
            if (seller['SellerId'] not in sellersDisabled) & (seller['SellerId'] != '1'):
                sellerListActive.append(seller['SellerId'])

    return sellerListActive



def getOrders(key, token, storeId):
    today = datetime.today().strftime('%Y-%m-%d')
    url = "https://{accountName}.{environment}.com.br/api/oms/pvt/orders?f_creationDate=creationDate%3A%5B{dtStart}T00%3A00%3A00.000Z%20TO%20{dtEnd}T23%3A59%3A59.999Z%5D&per_page={per_page}".format(
    accountName=storeId, environment="vtexcommercestable", dtStart=today, dtEnd=today, per_page=100)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-VTEX-API-AppKey": key,
        "X-VTEX-API-AppToken": token
    }
    rVtexOrders = requests.get(url, headers=headers)

    ordersDict = {}
    for order in rVtexOrders.json()['list']:
        if order['status'] == 'invoiced': # invoiced = Faturado / 'handling' = Preparanado entrega
            orderNameString = order['orderId'] + " | " + order['clientName']
            ordersDict[orderNameString] = order['orderId']

    return ordersDict



def getStoreInfo(key, token, storeId):
    url = "https://{accountName}.{environment}.com.br/api/logistics/pvt/configuration/pickuppoints".format(
    accountName=storeId, environment="vtexcommercestable")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "X-VTEX-API-AppKey": key,
        "X-VTEX-API-AppToken": token
    }

    rVtexStore = requests.get(url, headers=headers)

    storeName = rVtexStore.json()[0]['name']
    street = rVtexStore.json()[0]['address']['street']
    number = rVtexStore.json()[0]['address']['number']
    neighborhood = rVtexStore.json()[0]['address']['neighborhood']
    complement = rVtexStore.json()[0]['address']['complement']
    city = rVtexStore.json()[0]['address']['city']
    state = rVtexStore.json()[0]['address']['state']
    postalCode = rVtexStore.json()[0]['address']['postalCode']
    storeLat = rVtexStore.json()[0]['address']['location']['latitude']
    storeLng = rVtexStore.json()[0]['address']['location']['longitude']

    if (complement != None) & (complement != ""):
        storeAddress = "{street}, {number}, {complement} - {neighborhood}, {city} - {state}, {postalCode}".format(
            street=street, number=number, complement=complement, neighborhood=neighborhood, city=city, state=state, postalCode=postalCode)
    else:
        storeAddress = "{street}, {number} - {neighborhood}, {city} - {state}, {postalCode}".format(
            street=street, number=number, neighborhood=neighborhood, city=city, state=state, postalCode=postalCode)
        
    d = dict({
        'storeName':storeName,
        'storeStreet':street,
        'storeNumber':number,
        'storeNeighborhood':neighborhood,
        'storeComplement':complement,
        'storeCity':city,
        'storeState':state,
        'storePostalCode':postalCode,
        'storeAddress':storeAddress,
        'storeLat':storeLat,
        'storeLng':storeLng
        })
    
    return d



def getClientInfo(key, token, storeId, orderId):
    url = "https://{accountName}.{environment}.com.br/api/oms/pvt/orders/{orderId}".format(
        accountName=storeId, environment="vtexcommercestable", orderId=orderId)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "X-VTEX-API-AppKey": key,
        "X-VTEX-API-AppToken": token
    }
    rVtexClient = requests.get(url, headers=headers)
    
    clientName = rVtexClient.json()['clientProfileData']['firstName'] + " " + rVtexClient.json()['clientProfileData']['lastName']
    clientPhone = rVtexClient.json()['clientProfileData']['phone']
    street = rVtexClient.json()['shippingData']['address']['street']
    number = rVtexClient.json()['shippingData']['address']['number']
    neighborhood = rVtexClient.json()['shippingData']['address']['neighborhood']
    complement = rVtexClient.json()['shippingData']['address']['complement']
    city = rVtexClient.json()['shippingData']['address']['city']
    state = rVtexClient.json()['shippingData']['address']['state']
    postalCode = rVtexClient.json()['shippingData']['address']['postalCode']
    clientLat = rVtexClient.json()['shippingData']['address']['geoCoordinates'][1]
    clientLng = rVtexClient.json()['shippingData']['address']['geoCoordinates'][0]

    if (complement != None) & (complement != ""):
        clientAddress = "{street}, {number}, {complement} - {neighborhood}, {city} - {state}, {postalCode}".format(
            street=street, number=number, complement=complement, neighborhood=neighborhood, city=city, state=state, postalCode=postalCode)
    else:
        clientAddress = "{street}, {number} - {neighborhood}, {city} - {state}, {postalCode}".format(
            street=street, number=number, neighborhood=neighborhood, city=city, state=state, postalCode=postalCode)
        
    d = dict({
        'clientName':clientName,
        'clientPhone':clientPhone,
        'clientStreet':street,
        'clientNumber':number,
        'clientNeighborhood':neighborhood,
        'clientComplement':complement,
        'clientCity':city,
        'clientState':state,
        'clientPostalCode':postalCode,
        'clientAddress': clientAddress,
        'clientLat':clientLat,
        'clientLng':clientLng,
        })
    
    return d



def getQuotations(key, secret, service, storeLat, storeLng, storeAddress, clientLat, clientLng, clientAddress):
    path = '/v3/quotations'
    region = 'BR'
    method = 'POST'
    timestamp = int(round(time.time() * 1000))

    body = {
        "data": {
            #"scheduleAt": [],
            "serviceType": service,
            "specialRequests": [],
            "language": "pt_BR",
            "stops": [
                {
                    "coordinates": {
                        "lat": str(storeLat),
                        "lng": str(storeLng)
                    },
                    "address": storeAddress
                },
                {
                    "coordinates": {
                        "lat": str(clientLat),
                        "lng": str(clientLng)
                    },
                    "address": clientAddress
                }
            ]
        }
    }

    rawSignature = "{timestamp}\r\n{method}\r\n{path}\r\n\r\n{body}".format(
        timestamp=timestamp, method=method, path=path, body=json.dumps(body))
    signature = hmac.new(secret.encode(), rawSignature.encode(),
                        hashlib.sha256).hexdigest()
    url = "https://rest.sandbox.lalamove.com"
    headers = {
        'Content-type': 'application/json; charset=utf-8',
        'Authorization': "hmac {key}:{timestamp}:{signature}".format(key=key, timestamp=timestamp, signature=signature),
        'Accept': 'application/json',
        'Market': region
    }
    rQuotation = requests.post(url+path, data=json.dumps(body), headers=headers)
    print(rQuotation.json())
    quotationId = rQuotation.json()['data']['quotationId']
    storeStopId = rQuotation.json()['data']['stops'][0]['stopId']
    storeStopAdreess = rQuotation.json()['data']['stops'][0]['address']
    clientStopId = rQuotation.json()['data']['stops'][1]['stopId']
    clientStopAdreess = rQuotation.json()['data']['stops'][0]['address']
    price = rQuotation.json()['data']['priceBreakdown']['total']
    distance = rQuotation.json()['data']['distance']['value']
    
    d = dict({
        'quotationId':quotationId,
        'storeStopId':storeStopId,
        'storeStopAdreess':storeStopAdreess,
        'clientStopId':clientStopId,
        'clientStopAdreess':clientStopAdreess,
        'price':price,
        'distance':distance,
        })
    
    return d



def placeOrder(key, secret, quotationId, storeStopId, storeName, clientStopId, clientName, clientPhone, observation):
    if clientPhone[:3] == '+55':
        pass
    else:
        clientPhone = "+55" + clientPhone   
    path = '/v3/orders'
    region = 'BR'
    method = 'POST'
    timestamp = int(round(time.time() * 1000))

    body = {
        "data": {
            "quotationId": quotationId,
            "sender": {
                "stopId": str(storeStopId),
                "name": storeName,
                "phone": "+5511955555555"
            },
            "recipients": [
                {
                    "stopId": str(clientStopId),
                    "name": clientName,
                    "phone": clientPhone,
                    "remarks": observation # optional
                }
            ],
            "isPODEnabled": True, # POD = Proof Of Delivery - optional 
            "isRecipientSMSEnabled": False, # For SMS to be sent, please first check with your account manager for details - optional
            "partner": "Lalamove Partner 1", # optional
            "metadata": {
                "restaurantOrderId": "1234",
                "restaurantName": "Oba hortifruti"
            }
        }
    }
    rawSignature = "{timestamp}\r\n{method}\r\n{path}\r\n\r\n{body}".format(
        timestamp=timestamp, method=method, path=path, body=json.dumps(body))
    signature = hmac.new(secret.encode(), rawSignature.encode(),
                        hashlib.sha256).hexdigest()
    url = "https://rest.sandbox.lalamove.com"
    headers = {
        'Content-type': 'application/json; charset=utf-8',
        'Authorization': "hmac {key}:{timestamp}:{signature}".format(key=key, timestamp=timestamp, signature=signature),
        'Accept': 'application/json',
        'Market': region
    }
    rOrder = requests.post(url+path, data=json.dumps(body), headers=headers)
    print(rOrder.json())
    orderId = rOrder.json()['data']['orderId']
    shareLink = rOrder.json()['data']['shareLink']
    price = rOrder.json()['data']['priceBreakdown']['total']
    d = dict({
        'orderId':orderId,
        'shareLink':shareLink,
        'price':price,
        })
    
    return d


@st.cache_data
def getServices(key, secret, storeCity):
    path = '/v3/cities'
    region = 'BR'
    method = 'GET'
    timestamp = int(round(time.time() * 1000))

    rawSignature = "{timestamp}\r\n{method}\r\n{path}\r\n\r\n".format(
        timestamp=timestamp, method=method, path=path)
    signature = hmac.new(secret.encode(), rawSignature.encode(),
                        hashlib.sha256).hexdigest()
    startTime = int(round(time.time() * 1000))
    url = "https://rest.sandbox.lalamove.com"

    headers = {
        'Content-type': 'application/json; charset=utf-8',
        'Authorization': "hmac {key}:{timestamp}:{signature}".format(key=key, timestamp=timestamp, signature=signature),
        'Accept': 'application/json',
        'Market': region
    }
    rCity = requests.get(url+path, headers=headers)
    
    servicesDict = {"":""}
    for locode in rCity.json()['data']:
        if locode['name'] == storeCity:
            for service in locode['services']:
                
                serviceKey = service['key']
                serviceLength = service['dimensions']['length']['value']
                serviceWidth = service['dimensions']['width']['value']
                serviceHeight = service['dimensions']['height']['value']
                serviceDimention = "{} x {} x {}".format(serviceLength, serviceWidth, serviceHeight)
                serviceLoad = int(service['load']['value'])
                
                serviceString = "Dimensão: {} m | Carga: {} kg".format(serviceDimention, serviceLoad)
                servicesDict[service['key']] = serviceString

    return servicesDict



def saveSellerOrder(sftpUsername, sftpPassword, storeId, partner, clientName, service, price, orderId):
    df = pd.DataFrame({'seller': storeId,
                       'partner': partner,
                       'clientName': clientName,
                       'service': service,
                       'price': price,
                       'orderId': orderId,}, index=[0])

    # SFTP credentials
    myHostname = "sftp.redeoba.com.br"
    port = 6591
    
    # Conexion
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    sftp = pysftp.Connection(host=myHostname, port=port,
                             username=sftpUsername, password=sftpPassword, cnopts=cnopts)

    # Update schedule file
    # Read existent file
    try:
        with sftp.open('/dados/delivery_apis/sellers_orders.csv', "r") as f:
            currentFile = pd.read_csv(f, delimiter=';')
        # Append new schedules
        newFile = currentFile.append(df)
    except:
        newFile = df

    # Save into SFTP
    with sftp.open('/dados/delivery_apis/sellers_orders.csv', "w") as f:
        f.write(newFile.to_csv(index=False, sep=';', encoding='latin-1'))



#def saveSellerOrderDw():
    



def readOrdersStatus(sftpUsername, sftpPassword, storeId):
    # SFTP credentials
    myHostname = "sftp.redeoba.com.br"
    port = 6591
    # Conexion
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    sftp = pysftp.Connection(host=myHostname, port=port,
                             username=sftpUsername, password=sftpPassword, cnopts=cnopts)
    try:
        with sftp.open('/dados/delivery_apis/sellers_orders.csv', "r") as f:
            orders = pd.read_csv(f, delimiter=';')
        with sftp.open('/dados/delivery_apis/orders_status.csv', "r") as f:
            status = pd.read_csv(f, delimiter=';')
        
        df = orders.merge(status, how='left', on='orderId')
        df.index += 1
        df_ajustado = df[(df['seller'] == storeId) & (df['status'] != 'COMPLETED')].dropna()
        return st.dataframe(df_ajustado) if len(df_ajustado) > 0 else st.write('Nenhuma entrega agendada até o momento.')
    except:
        return st.write('Sem arquivo.')


@st.cache_data(ttl=timedelta(minutes=5))
def quotationDataFrame():
    priceList = []
    serviceList = []
    keyList = []
    quotationIdList = []
    storeStopIdList = []
    clientStopIdList = []
    percent_complete = 0
    my_bar = st.progress(0, text="Por favor, aguarde. Estamos cotando os preços...")
    for service in servicesDict.keys():
        print(service)
        quotations = getQuotations(
            sbLalamoveKey, sbLalamoveSecret, service,
            storeInfo['storeLat'], storeInfo['storeLng'], storeInfo['storeAddress'],
            clientInfo['clientLat'], clientInfo['clientLng'], clientInfo['clientAddress']
        )
        serviceList.append(service)
        priceList.append(round(float(quotations['price']), 2))
        quotationIdList.append(quotations['quotationId'])
        storeStopIdList.append(quotations['storeStopId'])
        clientStopIdList.append(quotations['clientStopId'])
        keyList.append("{}".format(servicesDict[service]))
        
        percent_complete += 1 / len(servicesDict.keys())
        my_bar.progress(round(percent_complete, 2), text="Por favor, aguarde. Estamos cotando os preços...")
        
    df = pd.DataFrame({
        'Veículo':serviceList,
        'Preço':priceList,
        'quotationId':quotationIdList,
        'storeStopId':storeStopIdList,
        'clientStopId':clientStopIdList,
        'Capacidade': keyList
    }).sort_values('Preço').reset_index(drop=True)
    df.index += 1
    
    return df



if __name__ == "__main__":
    # Keys
    sbLalamoveKey = 'pk_test_b09995e52245a91524eccee5c279a9f6'
    sbLalamoveSecret = 'sk_test_YPqi6Q14jnW/iTk2cVayjVskH7s29Q6TDsb3bS47sAFyLtCb8eUY6IXfUW22sc1p'
    VtexAppKey = "vtexappkey-obahortifruti-YMXCMB"
    VtexAppToken = "RMDTMWLVLBIRRNSTCHUONAUEDPWBDWOZZAGYIJHPUONZEFZMIZTPJZKXTRXDGKRJGXXKOPXFTOFMZTJRCABADYJGXBDJEVFEWGQDSKKEVENQRIPJJIBTISQIFYNREZDB"
    sftpUsername = "report_ti_ecomm"
    sftpPassword = "k*R6@scQ"
    
    # Titulo da pagina
    st.set_page_config(page_title="Delivery Oba")
    
    # Título do aplicativo
    st.title('DELIVERY\n')
    
    # Inputs
    storeSelect = st.sidebar.selectbox(label="Escolha a sua loja", options=getActiveStores(VtexAppKey, VtexAppToken))
    action = st.sidebar.selectbox(label="Escolha uma ação", options=['', 'Chamar parceiro','Ver status das entregas'])
    if storeSelect != "":
        # i=0
        # while i < 2:
        #     try:
                if action == 'Ver status das entregas':
                    readOrdersStatus(sftpUsername, sftpPassword, storeSelect)
                elif action == 'Chamar parceiro':
                    ordersDict = getOrders(VtexAppKey, VtexAppToken, storeSelect)
                    if len(ordersDict) == 0:
                        st.error("Não existem pedidos para entrega no momento.")
                    else:
                        storeInfo = getStoreInfo(VtexAppKey, VtexAppToken, storeSelect)
                        orderSelected = st.sidebar.radio(label="Escolha o pedido para a entrega", options=ordersDict.keys())
                        order = ordersDict[orderSelected]
                        
                        clientInfo = getClientInfo(VtexAppKey, VtexAppToken, storeSelect, order)

                        st.write("")
                        partner = st.sidebar.selectbox(label="Escolha o parceiro para a entrega", options=['','Lalamove'])
                        
                        if partner == 'Lalamove':
                            st.write("")
                            servicesDict = getServices(sbLalamoveKey, sbLalamoveSecret, storeInfo['storeCity'])
                            serviceSelected = st.sidebar.selectbox(label="Selecione o veículo de acordo com a cotação", options=servicesDict.keys())
                            
                            if serviceSelected == "":
                                df = quotationDataFrame()                                
                                'dataframe:', df[['Veículo','Preço','Capacidade']]
                            else:
                                st.sidebar.write("")
                                st.sidebar.write("Confira se todos as informações estão corretas e clique em CHAMAR PARCEIRO.")
                                
                                if st.sidebar.button('CHAMAR PARCEIRO'):
                                    quotations = getQuotations(
                                            sbLalamoveKey, sbLalamoveSecret, serviceSelected,
                                            storeInfo['storeLat'], storeInfo['storeLng'], storeInfo['storeAddress'],
                                            clientInfo['clientLat'], clientInfo['clientLng'], clientInfo['clientAddress']
                                        )
                                    
                                    orderPlaced = placeOrder(
                                        sbLalamoveKey, sbLalamoveSecret,
                                        quotations['quotationId'], quotations['storeStopId'], storeInfo['storeName'],
                                        quotations['clientStopId'], clientInfo['clientName'], clientInfo['clientPhone'],
                                        observation=""
                                    )

                                    # Save data into SFTP
                                    saveSellerOrder(sftpUsername, sftpPassword, 
                                                    storeSelect, partner, clientInfo['clientName'],
                                                    serviceSelected, orderPlaced['price'], orderPlaced['orderId'])

                                    st.write(orderPlaced['orderId'])
                                    st.write(orderPlaced['shareLink'])
                                    st.success('Pedido enviado ao parceiro.')
            #     i = 2
            # except:
            #     i += 1