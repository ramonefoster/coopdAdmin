import os
import time
import datetime
import threading
import weather.weather2db as SaveWeather

import zmq
import json

class GetWeather(threading.Thread):
    def __init__(self, station_file, destination_file, db_name, user, password, host, port, publisher):
        super().__init__()
        self._stop_event = threading.Event()
        self.station_file = station_file
        self.destination_file = destination_file
        self.stat_msg = None
        self.flag = True
        self.save2db = SaveWeather.WeatherToDB(station_file, db_name, user, password, host, port)

        self.publisher = publisher        
        self.last_line = None

        try:
            with open(station_file, "rb") as file:
                file.seek(-2, 2)  
                while file.read(1) != b"\n":
                    file.seek(-2, 1)  
                self.last_line = file.readline().decode()            
        except Exception as e:
            print(e)        
    
    def update_files(self, source, destination):
        self.station_file = source
        self.destination_folder = destination
    
    def stop(self):
        self.flag = False
        self._stop_event.set()

    def save_last_line(self, station_file, destination_file):
        source_modified_time = os.path.getmtime(station_file)
        destination_exists = os.path.exists(destination_file)
        
        if not destination_exists or source_modified_time > os.path.getmtime(destination_file):
            try:
                with open(station_file, "rb") as file:
                    file.seek(-2, 2)  
                    while file.read(1) != b"\n":
                        file.seek(-2, 1)  
                    self.last_line = file.readline().decode()                              

                t0 = time.time()
                with open(destination_file, 'w') as file:
                    file.write('\n'+self.last_line)
                delta_t = (time.time() - t0)

                if self.save2db:
                    self.stat_msg = self.save2db.save_to_db() 
                
                current_time = datetime.datetime.now()
                formatted_time = current_time.strftime("%H:%M")

                self.stat_msg = f"{formatted_time} Última linha salva em: '{destination_file}' | Levou {delta_t}s."

                self.public_weather()
                
            except Exception as e:
                print(e)
                self.stat_msg = "Falha no arquivo: "+str(e)            
        else:
            self.stat_msg = "Nenhuma modificação no arquivo da estação."
    
    def public_weather(self):
        try:
            data = self.last_line.split()                    
            
            message = {
                        "broker": "Weather160",
                        "version": "1.0.0",                        
                        "date" : data[0],
                        "hour": data[1],
                        "outTemp": data[2],
                        "hiTemp": data[3],
                        "lowTemp": data[4],
                        "outHumidity": data[5],
                        "dewOut": data[6],
                        "windSpeed": data[7],
                        "windDirection": data[8], 
                        "windRun": data[9],
                        "hiSpeed": data[10],
                        "hiDir": data[11],
                        "windChill": data[12],                        
                        "heatIndex": data[13],
                        "THWIndex": data[14],
                        "THSWIndex": data[15],
                        "pressure": data[16],
                        "rain": data[17], 
                        "rainRate": data[18],
                        "solarRad": data[19],
                        "solarEnergy": data[20],
                        "hiSolarRad": data[21],
                        "UVIndex": data[22],
                        "UVDose": data[23],
                        "hiUV": data[24],
                        "headDD": data[25],
                        "coolDD": data[26],
                        "inTemp": data[27],
                        "inHumidity": data[28], 
                        "dewIn": data[29],
                        "inHeat": data[30],
                        "inEMC": data[31],
                        "inAirDensity": data[32],
                        "2ndTemp": data[33],
                        "2ndHumidity": data[34],
                        "ET": data[35],
                        "leaf": data[36], 
                        "windSamp": data[37],
                        "windTx": data[38],
                        "ISSRecept": data[39],
                        "arcInt": data[40],
                        }
            
            if self.publisher:
                serialized_message = json.dumps(message)
                self.publisher.send_string(serialized_message)
                self.stat_msg = f"ZMQ {message}"
        except Exception as e:
            self.stat_msg = f"Error ZMQ pub weather {str(e)}"

    def run(self):
        while self.flag:
            try:
                parent_dir = os.path.dirname(self.destination_file)
                current_time = datetime.datetime.now()
                formatted_time = current_time.strftime("%H:%M")

                if os.path.exists(parent_dir) and os.path.exists(self.station_file):          
                    self.save_last_line(self.station_file, self.destination_file)
                    self.stat_msg += f"\n{formatted_time} Arquivo Clima atualizado."
                else:
                    self.stat_msg = f"Arquivos ou pastas inexistentes."
                
            except Exception as e:
                self.stat_msg = "Error: "+str(e)
            self._stop_event.wait(timeout=10)