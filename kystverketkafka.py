# Henter ut ais data kontinuerlig fra kystverket.no
# Dataen lagres i SQLITE3-databasen og pushes til kafka.
# Dette er hovedprogrammet
import socket
import Dictcargotypes as d
import ais.stream
import re
import sqlite3
from datetime import datetime
from pykafka import KafkaClient
import json
import pandas as pd
import sys
#kobler seg opp til den lokale databasen
conn = sqlite3.connect('aisversion1.db', timeout=10)

#definerer ip og port til kystverket.no
KYSTINFO_HOST = '153.44.253.27'
KYSTINFO_PORT = 5631
BUFFER_SIZE = 8192

#oppretter sockets
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((KYSTINFO_HOST, KYSTINFO_PORT))
f = s.makefile()
#returnerer en kafka klient som er lokal på pcen
def get_kafka_client():
    return KafkaClient(hosts='127.0.0.1:9092')

if __name__ == "__main__":
    #kobler seg opp til kafka.
    client = get_kafka_client()
    #defininerer hvilke topic en skal skrive til
    topic = client.topics['aismessages']
    #oppretter en produsent av meldinger
    producer = topic.get_sync_producer()
    #oppretter en loop som lytter til nye ais meldinger
    for msg in ais.stream.decode(f):
        print(msg)
        #kafka
        #kafkamessagejson = json.dumps(msg).encode('utf-8')
        #producer.produce(kafkamessagejson)
        #kafka

        # print('id:{id:2}, msg: {msg}'.format(id=msg['id'], msg=msg))
        
        #Her velger jeg AIS-meldinger av type 1,2,3. Altså data angående posisjon og bevegelse til fartøyet.
        if (msg['id'] == 1 or msg['id'] == 2 or msg['id'] == 3):
            # print('id:{id:2}, mmsi: {mmsi}, nav_status: {nav_status}'.format(id=msg['id'], mmsi=msg['mmsi'], nav_status=msg['nav_status']))
            dateTimeObj = datetime.now()
            # dtg = str(dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S.%f"))
            dtg = str(dateTimeObj.strftime("%Y-%m-%d %H:%M:%S"))
            statuss = "'" + " " + "'"
            if (msg['nav_status'] in d.status):
                statuss = "'" + str(re.sub('\W+', '', d.status[msg['nav_status']].lower())) + "'"
            #SQL insert statement -> uten update. -> Dette gir oss historiske AIS-data.
            sql = "INSERT INTO AIS (message_id, nav_status, status, mmsi, sog, pos_accuracy, pos_x, pos_y, cog, true_heading, special_manoeuvre,datetimedmyhms) VALUES (" + str(
                msg['id']) + "," + str(msg['nav_status']) + "," + statuss + "," + str(msg['mmsi']) + "," + "'" + str(
                msg['sog']) + "'" + "," + str(msg['position_accuracy']) + "," + "'" + str(msg['x']) + "'" + "," + "'" + str(
                msg['y']) + "'" + "," + str(msg['cog']) + "," + str(msg['true_heading']) + "," + str(
                msg['special_manoeuvre']) + "," + "'" + str(dtg) + "'" + ")"

            conn.execute(sql)
            conn.commit()

            #SQL insert statement med update -> for å slippe å skrive en ny linje mellom hver gang
            sql = "INSERT INTO AISREALTIME (mmsi, nav_status, status, sog, pos_accuracy, pos_x, pos_y, cog, true_heading, special_manoeuvre,datetimedmyhms) VALUES (" + str(
                msg['mmsi']) + "," + str(msg['nav_status']) + "," + statuss + ", " + "'" + str(
                msg['sog']) + "'" + "," + str(msg['position_accuracy']) + "," + "'" + str(msg['x']) + "'" + "," + "'" + str(
                msg['y']) + "'" + "," + str(msg['cog']) + "," + str(msg['true_heading']) + "," + str(
                msg['special_manoeuvre']) + "," + "'" + str(
                dtg) + "'" + ")" + " ON CONFLICT(mmsi)" + " DO UPDATE SET sog = " + "'" + str(
                msg['sog']) + "'" + "," + " nav_status =" + str(
                msg['nav_status']) + ", " + "status = " + statuss + " ," + "pos_accuracy = " + str(
                msg['position_accuracy']) + ", " + "pos_x = " + "'" + str(msg['x']) + "'" + "," + "pos_y =" + "'" + str(
                msg['y']) + "'" + "," + "cog = " + str(msg['cog']) + ", true_heading = " + str(
                msg['true_heading']) + ", special_manoeuvre = " + str(
                msg['special_manoeuvre']) + ", datetimedmyhms = " + "'" + str(dtg) + "'"

            conn.execute(sql)
            conn.commit()
            
            # kafka
            msgkafka = {"mmsi": msg['mmsi'], "nav_status": statuss, "pos_x": msg['x'], "pos_y": msg['y'], "dtg": dtg, "true_heading": msg['true_heading'], "sog": msg['sog']}
            kafkamessagejson = json.dumps(msgkafka).encode('utf-8')
            #print(kafkamessagejson)
            producer.produce(kafkamessagejson)

        #her velger jeg meldingstype 5, altså mer statisk info om fartøyet
        elif (msg['id'] == 5):

            callsign = "'" + str(re.sub('\W+', '', msg['callsign'])) + "'"
            name = "'" + str(re.sub('\W+', '', msg['name'].lower())) + "'"
            cargotype = "'" + " " + "'"
            destination = "'" + str(re.sub('\W+', '', msg['destination'])) + "'"
            if (msg['type_and_cargo'] in d.cargo):
                cargotype = "'" + str(re.sub('\W+', '', d.cargo[msg['type_and_cargo']].lower())) + "'"
            dateTimeObj = datetime.now()
            dtg = str(dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S.%d"))
            sql = "INSERT INTO AIS (message_id,mmsi,imo_num,callsign,name,type_and_cargo,type_string,eta_month,eta_day,eta_hour,eta_minute,draught,destination,datetimedmyhms) VALUES (" + str(
                msg['id']) + "," + str(msg['mmsi']) + "," + str(
                msg['imo_num']) + "," + callsign + "," + name + "," + "'" + str(
                msg['type_and_cargo']) + "'" + "," + cargotype + "," + str(msg['eta_month']) + "," + str(
                msg['eta_day']) + "," + str(msg['eta_hour']) + "," + str(msg['eta_minute']) + "," + "'" + str(
                msg['draught']) + "'" + "," + destination + "," + "'" + str(dtg) + "'" + ")"

            conn.execute(sql)
            conn.commit()
            # legger inn i min unike database realtime-data mmsi sutrain. Har lagt til en on conflict replace the specific colonoms. not the row.
            sql = "INSERT INTO AISREALTIME (mmsi,imo_num,callsign,name,type_and_cargo,type_string,eta_month,eta_day,eta_hour,eta_minute,draught,destination,datetimedmyhms) VALUES (" + str(
                msg['mmsi']) + "," + str(msg['imo_num']) + "," + callsign + "," + name + "," + "'" + str(
                msg['type_and_cargo']) + "'" + "," + cargotype + "," + str(msg['eta_month']) + "," + str(
                msg['eta_day']) + "," + str(msg['eta_hour']) + "," + str(msg['eta_minute']) + "," + "'" + str(
                msg['draught']) + "'" + "," + destination + "," + "'" + str(
                dtg) + "'" + ")" + " ON CONFLICT(mmsi)" + " DO UPDATE SET imo_num = " + str(msg[
                                                                                                'imo_num']) + ", " + " callsign = " + callsign + ", " + "name = " + name + "," + "type_and_cargo =" + "'" + str(
                msg['type_and_cargo']) + "'" + "," + "type_string = " + cargotype + ", eta_month = " + str(
                msg['eta_month']) + ", eta_day = " + str(msg['eta_day']) + ", eta_hour = " + str(
                msg['eta_hour']) + ", eta_minute = " + str(msg['eta_minute']) + ", draught = " + "'" + str(
                msg['draught']) + "'" + ", destination = " + destination + " , datetimedmyhms = " + "'" + str(dtg) + "'"

            conn.execute(sql)
            conn.commit()

conn.close()
s.close()

