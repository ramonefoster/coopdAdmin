import os
from datetime import datetime
import psycopg2

wind_dir_dict = {
    'N': 0, 
    'NNE': 22.5, 
    'NE' : 45, 
    'ENE': 67.5, 
    'E': 90, 
    'ESE': 112.5, 
    'SE': 135, 
    'SSE': 157.5, 
    'S': 180, 
    'SSW': 202.5, 
    'SW': 225,
    'WSW': 247.5,
    'W' : 270,
    'WNW': 292.5,
    'NW': 315,
    'NNW': 337.5,
    '---': None
}

class WeatherToDB():
    def __init__(self, directory, database, user, password, host, port):
        self.weather_file = directory
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def read_file(self):
        if self.weather_file and os.path.exists(self.weather_file):
            try:
                weather = open(str(self.weather_file), 'r')
                lines = weather.read().splitlines()
                last_line = lines[-1]
                return last_line
            except:
                return None

    def create_connection(self):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = psycopg2.connect(database=self.database, user=self.user, password=self.password, host=self.host, port=self.port)
            return conn
        except Exception as e:
            return None

    def create_task(self, conn, task):
        sql = f''' INSERT INTO api_weather(datetime,temperature,humidity,wind_speed,wind_dir,wind_angle,bar,solar_rad, uv_dose, wind_val, leaf) VALUES '''
        cur = conn.cursor()
        args = ','.join(cur.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", i).decode('utf-8')
                    for i in task)
        cur.execute(sql + args)
        conn.commit()
        cur.close()

    def save_to_db(self):
        control_line = ""         
        last_line = self.read_file()      
        if last_line != None and last_line != control_line:            
            control_line = last_line
            try:
                conn = self.create_connection()
                
                weather_date = last_line.split()[0]                
                weather_time = last_line.split()[1]
                if len(weather_time)==4:
                    weather_time = '0'+weather_time
                datetime_var = weather_date + " " + weather_time
                datetime_object = datetime.strptime(datetime_var, '%d/%m/%y %H:%M')
                outside_temp = last_line.split()[2]
                if '---' in outside_temp:
                    outside_temp = None
                else:
                    float(outside_temp)
                humidity = last_line.split()[5]
                if '---' in humidity:
                    humidity = None
                else:
                    float(humidity)
                wind_speed = last_line.split()[7]
                if '---' in wind_speed:
                    wind_speed = None
                else:
                    float(wind_speed)
                if wind_speed != '---':
                    if float(wind_speed)>40:
                        wind_val='40+'
                    elif 30<float(wind_speed)<=40:
                        wind_val = '30-40'
                    elif 20<float(wind_speed)<=30:
                        wind_val = '20-30'
                    elif 10<float(wind_speed)<=20:
                        wind_val = '10-20'
                    elif 0<=float(wind_speed)<=10:
                        wind_val = '0-10'  
                    else:
                        wind_val = 'Calm'
                else:
                    wind_val = 'Calm'               
                wind_dir = last_line.split()[8]
                if '---' in wind_dir:
                    wind_dir = None                
                wind_dir_angle = wind_dir_dict.get(wind_dir)
                weather_bar = last_line.split()[16]
                if '---' in weather_bar:
                    weather_bar = None
                else:
                    float(weather_bar)
                solar_rad = last_line.split()[20]  
                if '---' in solar_rad:
                    solar_rad = None
                else:
                    float(solar_rad)
                uv_dose = last_line.split()[22]
                if '---' in uv_dose:
                    uv_dose = None
                else:
                    float(uv_dose)
                leaf = last_line.split()[36]
                if '---' in leaf:
                    leaf = None
                else:
                    float(leaf)
                if conn:
                    weather_to_insert = [[datetime_object, outside_temp, humidity, wind_speed, wind_dir, wind_dir_angle, weather_bar, solar_rad, uv_dose, wind_val, leaf]]
                    self.create_task(conn, weather_to_insert)
                    current_time = datetime.now()
                    formatted_time = current_time.strftime("%H:%M")
                    return (f"{formatted_time} - Salvo no BD.")
            except Exception as e:
                return ("Error BD: " + str(e))

