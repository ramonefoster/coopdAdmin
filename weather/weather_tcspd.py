import os
import datetime
import threading
import weather.weather2db as SaveWeather

class GetWeather(threading.Thread):
    def __init__(self, station_file, destination_file, db_name, user, password, host, port):
        super().__init__()
        self._stop_event = threading.Event()
        self.station_file = station_file
        self.destination_file = destination_file
        self.stat_msg = None
        self.flag = True
        self.save2db = SaveWeather.WeatherToDB(station_file, db_name, user, password, host, port)
    
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
            with open(station_file, 'r') as file:
                lines = file.readlines()
                last_line = lines[-1]

            with open(destination_file, 'w') as file:
                file.write(last_line)
                print(last_line)
                if self.save2db:
                    print("save2db exists")
                    self.stat_msg = self.save2db.save_to_db()
                else:
                    print(self.save2db)
            
            current_time = datetime.datetime.now()
            formatted_time = current_time.strftime("%H:%M")

            self.stat_msg = f"{formatted_time} Última linha salva em: '{destination_file}'."
        else:
            self.stat_msg = "Nenhuma modificação no arquivo da estação."

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