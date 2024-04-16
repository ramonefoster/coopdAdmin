import sys, os
import time

from PyQt5 import  QtWidgets, uic
from PyQt5.QtCore import QTimer, QSettings
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMainWindow, QMessageBox

import goes.download as get_goes
import backup.database_bkp as DBbackuper
import weather.weather_tcspd as ClimaTCSPD
import allsky.allsky as AllSky
from allsky.meteor import MeteorDetection


import zmq
import json

pyQTfileName = "coopd.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(pyQTfileName)

class MyApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.setup_goes = self.load_config("goes")
        self.setup_allsky = self.load_config("allsky")
        self.setup_weather = self.load_config("weather")
        self.setup_database = self.load_config("database")
        self.load_settings()
        
        self.timer_update = QTimer()

        self.start_zmq()
        self.meteor_detection = MeteorDetection()

        self.goes = None        
        self.start_goes()
        self.goes_gif()
        self.btn_start_goes.clicked.connect(self.start_goes)
        self.btn_stop_goes.clicked.connect(self.stop_goes)

        self.backuper = None
        self.start_backuper()
        self.btn_backup.clicked.connect(self.do_backup)
        self.btn_start_backup.clicked.connect(self.start_backuper)
        self.btn_stop_backup.clicked.connect(self.stop_backuper)
        self.btn_reload_backup.clicked.connect(self.update_backuper)

        self.weather_handle = None
        self.start_weather_tcspd()
        self.btn_start_clima_tcspd.clicked.connect(self.start_weather_tcspd)
        self.btn_stop_clima_tcspd.clicked.connect(self.stop_weather)
        self.btn_reload_weather_tcspd.clicked.connect(self.update_weather_tcspd)

        self.allsky_handler = None
        self.start_allsky_handler()
        self.btn_start_allsky.clicked.connect(self.start_allsky_handler)
        self.btn_stop_allsky.clicked.connect(self.stop_allsky)
        self.btn_reload_allsky.clicked.connect(self.update_allsky_config)

        self.start_timer()  
    
    def detect_meteor(self, path):
        self.meteor_detection.detect(path)

    def start_zmq(self):
        try:
            self.ctx = zmq.Context()
            self.puller = self.ctx.socket(zmq.PULL)
            self.puller.bind(f"tcp://{self.txtIP.text()}:{self.txtPull.text()}")

            self.publisher = self.ctx.socket(zmq.PUB)
            self.publisher.bind(f"tcp://{self.txtIP.text()}:{self.txtPub.text()}")
            self.poller = zmq.Poller()
            self.poller.register(self.puller, zmq.POLLIN)
        except:
            self.poller = None
            self.publisher = None

    def load_config(self, item):        
        with open("config/config.json", 'r+') as file:
            setup = json.load(file)
            return setup[item]
    
    def recv_cmd_pull(self):
        if self.poller:
            socks = dict(self.poller.poll(50))
            if socks.get(self.puller) == zmq.POLLIN:
                msg_pull = self.puller.recv_string()
                try:
                    msg_pull = json.loads(msg_pull)
                    cmd = msg_pull.get("action")
                    self._client_id = msg_pull.get("clientId") 
                    if cmd == "STATUS":
                        self.weather_handle.public_weather()
                except:
                    pass
    
    def save_config(self, device, keys, value):        
        with open("config/config.json", 'r+') as file:
            setup = json.load(file)
            current_dict = setup[device]
            for key in keys[:-1]:
                current_dict = current_dict[key]
            
            current_dict[keys[-1]] = value

            file.seek(0)
            json.dump(setup, file, indent=4)
            file.truncate()
    
    def save_handler(self, device, config_values):
        """Save configuration settings for a specific device."""
        for keys, value in config_values.items():
            self.save_config(device, keys, value)

    def save_settings(self):
        """GOES"""
        self.save_handler("goes", {
            ("coopd",): self.dir_goes_coopd.text(),
            ("download",): self.dir_down_goes.text(),
            ("offline",): self.dir_goes_off.text()
        })
        """BACKUP DB"""
        self.save_handler("database", {
            ("coopd", "host"): self.db_host.text(),
            ("coopd", "name"): self.db_name.text(),
            ("coopd", "username"): self.db_user.text(),
            ("coopd", "password"): self.db_password.text(),
            ("coopd", "local_backup"): self.db_bkp_folder.text(),
            ("coopd", "backup_hour"): self.db_hour.value()
        })
        """DATABASE"""
        self.save_handler("database", {
            ("weather", "host"): self.db_host_2.text(),
            ("weather", "name"): self.db_name_2.text(),
            ("weather", "username"): self.db_user_2.text(),
            ("weather", "password"): self.db_password_2.text(),
            ("weather", "local_backup"): self.db_bkp_folder.text(),
            ("weather", "backup_hour"): self.db_hour.value()
        })
        """WEATHER"""
        self.save_handler("weather", {
            ("station_file",): self.source_weather_tcspd.text(),
            ("tcspd_file",): self.dest_weather_tcspd.text(),
            ("zeromq", "ip"): self.txtIP.text(),
            ("zeromq", "pub_port"): self.txtPub.text(),
            ("zeromq", "pull_port"): self.txtPull.text(),
        })
        """ALLSKY"""
        self.save_handler("allsky", {
            ("skymap",): self.check_skymap.isChecked(),
            ("allsky_picole", "angle"): self.angle_allsky_1.value(),
            ("allsky_picole", "ftp"): self.ftp_allsky_1.text(),
            ("allsky_picole", "coopd"): self.dir_allsky_1.text(),
            ("allsky_picole", "offline"): self.img_off_1.text(),
            ("allsky_container", "angle"): self.angle_allsky_2.value(),
            ("allsky_container", "ftp"): self.ftp_allsky_2.text(),
            ("allsky_container", "coopd"): self.dir_allsky_2.text(),
            ("allsky_container", "offline"): self.img_off_2.text(),
        })

    def load_settings(self):
        """GOES"""
        self.dir_goes_coopd.setText(self.setup_goes.get("coopd"))
        self.dir_down_goes.setText(self.setup_goes.get("download"))
        self.dir_goes_off.setText(self.setup_goes.get("offline"))
        """BACKUP DB"""
        db_coopd = self.setup_database.get("coopd")
        self.db_user.setText(db_coopd.get("username"))
        self.db_password.setText(db_coopd.get("password"))
        if db_coopd.get("backup_hour"):
            self.db_hour.setValue(db_coopd.get("backup_hour"))
        self.db_host.setText(db_coopd.get("host"))
        self.db_name.setText(db_coopd.get("name"))
        self.db_bkp_folder.setText(db_coopd.get("local_backup"))
        """FILE TCSPD WEATHER"""
        db_weather = self.setup_database.get("weather")
        self.dest_weather_tcspd.setText(self.setup_weather.get("tcspd_file"))
        self.source_weather_tcspd.setText(self.setup_weather.get("station_file"))
        self.txtIP.setText(self.setup_weather.get("zeromq").get("ip"))
        self.txtPub.setText(self.setup_weather.get("zeromq").get("pub_port"))
        self.txtPull.setText(self.setup_weather.get("zeromq").get("pull_port"))
        self.db_user_2.setText(db_weather.get("username"))
        self.db_password_2.setText(db_weather.get("password"))        
        self.db_host_2.setText(db_weather.get("host"))
        self.db_name_2.setText(db_weather.get("name"))
        """ALLSKY 1"""
        picole = self.setup_allsky.get("allsky_picole")
        self.ftp_allsky_1.setText(picole.get("ftp"))
        self.dir_allsky_1.setText(picole.get("coopd"))
        self.img_off_1.setText(picole.get("offline"))
        if picole.get("angle"):
            self.angle_allsky_1.setValue(int(picole.get("angle")))
        """ALLSKY 2"""
        container = self.setup_allsky.get("allsky_container")
        self.ftp_allsky_2.setText(container.get("ftp"))
        self.dir_allsky_2.setText(container.get("coopd"))
        self.img_off_2.setText(container.get("offline"))
        if container.get("angle"):
            self.angle_allsky_2.setValue(int(container.get("angle")))
        if self.setup_allsky.get("skymap") == 'True':
            self.check_skymap.setChecked(True)
        else:
            self.check_skymap.setChecked(False)
    
    def start_allsky_handler(self):
        directory_to_watch = self.ftp_allsky_1.text()
        destination_directory = self.dir_allsky_1.text()
        directory_to_watch_2 = self.ftp_allsky_2.text()
        destination_directory_2 = self.dir_allsky_2.text()
        skymap = self.check_skymap.isChecked()
        offline = self.img_off_1.text()   
        offline_2 = self.img_off_2.text()      
        self.allsky_handler = AllSky.AllskyWork(directory_to_watch, destination_directory, skymap, offline, directory_to_watch_2, destination_directory_2, offline_2)
        self.allsky_handler.start()
    
    def update_allsky_config(self):
        # ADD BOTAO UI
        directory_to_watch = self.ftp_allsky_1.text()
        directory_to_watch_2 = self.ftp_allsky_2.text()
        destination_directory = self.dir_allsky_1.text()
        self.allsky_handler.update(directory_to_watch, directory_to_watch_2, destination_directory)
    
    def stop_allsky(self):
        if self.allsky_handler:
            self.allsky_handler.stop()
            self.allsky_handler.join()
    
    def is_image_modified(self, path):
        if not os.path.exists(path):
            return False

        current_mod_time = os.path.getmtime(path)
        if hasattr(self, 'previous_mod_time') and self.previous_mod_time != current_mod_time:
            self.previous_mod_time = current_mod_time
            return True
        else:
            self.previous_mod_time = current_mod_time
            return False
    
    def update_image(self):
        path = self.dir_allsky_1.text()+r'\allsky_picole.jpg'
        path2 = self.dir_allsky_2.text()+r'\allsky340c.jpg'
        if self.allsky_handler:
            if self.is_image_modified(path):
                pixmap = QPixmap(path)
                self.img_allsky_1.setPixmap(pixmap)
            if not self.allsky_handler.check_online(self.ftp_allsky_1.text()):
                if os.path.exists(self.img_off_1.text()):
                    pixmap = QPixmap(self.img_off_1.text())
                    self.img_allsky_1.setPixmap(pixmap)
            if self.is_image_modified(path2):
                pixmap2 = QPixmap(path2)
                self.img_allsky_2.setPixmap(pixmap2)
            if not self.allsky_handler.check_online(self.ftp_allsky_2.text()):
                if os.path.exists(self.img_off_2.text()):
                    pixmap2 = QPixmap(self.img_off_2.text())
                    self.img_allsky_2.setPixmap(pixmap2)
    
    def start_weather_tcspd(self):
        source_file = self.source_weather_tcspd.text()
        dest_file = self.dest_weather_tcspd.text()
        host = self.db_host_2.text()
        user = self.db_user_2.text()
        password = self.db_password_2.text()
        db_name = self.db_name_2.text()
        port = '5432'
        self.weather_handle = ClimaTCSPD.GetWeather(source_file, dest_file, db_name, user, password, host, port, self.publisher)
        self.weather_handle.start()
        self.weather_handle.public_weather() 
    
    def update_weather_tcspd(self):        
        # ADD BOTAO UI
        source_file = self.source_weather_tcspd.text()
        dest_file = self.dest_weather_tcspd.text()
        self.weather_handle.update_files(source_file, dest_file)
    
    def stop_weather(self):
        if self.weather_handle:
            self.weather_handle.stop()
            self.weather_handle.join()            

    def do_backup(self):
         self.backuper.do_work()

    def start_backuper(self):
        hour = self.db_hour.value()
        host = self.db_host.text()
        user = self.db_user.text()
        password = self.db_password.text()
        db_name = self.db_name.text()
        dir_name = self.db_bkp_folder.text()
        
        self.backuper = DBbackuper.BackupDB(hour, host, user, password, db_name, dir_name) 
        self.backuper.start() 

    def update_backuper(self):
        hour = self.db_hour.value()
        host = self.db_host.text()
        user = self.db_user.text()
        password = self.db_password.text()
        db_name = self.db_name.text()
        dir = self.db_bkp_folder.text()
        if self.backuper:
            self.backuper.update_config(hour, host, user, password, db_name, dir)

    def stop_backuper(self):
        if self.backuper:
            self.backuper.stop() 
            self.backuper.join()   
    
    def start_goes(self):  
        arg1 = self.combo_goes.currentText()  
        arg2 = str(self.box_band_goes.value()) 
        arg3 = self.dir_down_goes.text() 
        gif_path = self.dir_goes_coopd.text()
        try:
            self.goes = get_goes.DownloadFile(arg1, arg2, arg3, gif_path)
            self.goes.start() 
        except Exception as e:
            self.txtGoesError.setText(str(e))
    
    def stop_goes(self):
        if self.goes:            
            self.goes.stop()
            self.goes.join()   
    
    def goes_gif(self):
        try:
            original = self.dir_goes_coopd.text()
            movie = QMovie(original)
            self.img_goes.setMovie(movie)

            # Start the movie
            movie.start()
        except Exception as e: 
            self.txtGoesError.setText(str(e))
    
    def main_status(self):
        if self.goes:
            if self.goes.is_alive():
                self.main_stat_goes.setStyleSheet("background-color: lightgreen")
                self.main_stat_goes.setText("ON")
            else:
                self.main_stat_goes.setStyleSheet("background-color: indianred")
                self.main_stat_goes.setText("OFF")
        if self.backuper:
            if self.backuper.is_alive():
                self.main_stat_backup.setStyleSheet("background-color: lightgreen")
                self.main_stat_backup.setText("ON")
            else:
                self.main_stat_backup.setStyleSheet("background-color: indianred")
                self.main_stat_backup.setText("OFF")
        if self.weather_handle:
            if self.weather_handle.is_alive():
                self.main_stat_weather_tcspd.setStyleSheet("background-color: lightgreen")
                self.main_stat_weather_tcspd.setText("ON")
            else:
                self.main_stat_weather_tcspd.setStyleSheet("background-color: indianred")
                self.main_stat_weather_tcspd.setText("OFF")
        if self.allsky_handler:                
            if self.allsky_handler.is_alive():
                if os.path.exists(self.ftp_allsky_1.text()):
                    is_allsky_on = self.allsky_handler.check_online(self.ftp_allsky_1.text())
                    if is_allsky_on:
                        self.main_stat_allsky_1.setStyleSheet("background-color: lightgreen")
                        self.main_stat_allsky_1.setText("ON")
                    else:
                        self.main_stat_allsky_1.setStyleSheet("background-color: gold")
                        self.main_stat_allsky_1.setText("!!!")
                if os.path.exists(self.ftp_allsky_2.text()):
                    is_allsky2_on = self.allsky_handler.check_online(self.ftp_allsky_2.text())
                    if is_allsky2_on:
                        self.main_stat_allsky_2.setStyleSheet("background-color: lightgreen")
                        self.main_stat_allsky_2.setText("ON")
                    else:
                        self.main_stat_allsky_2.setStyleSheet("background-color: gold")
                        self.main_stat_allsky_2.setText("!!!")
            else:
                self.main_stat_allsky_1.setStyleSheet("background-color: indianred")
                self.main_stat_allsky_1.setText("OFF")
                self.main_stat_allsky_2.setStyleSheet("background-color: indianred")
                self.main_stat_allsky_2.setText("OFF")
    
    def update_status(self): 
        self.recv_cmd_pull() 
        if round(time.time()%15) == 1:
            self.weather_handle.public_weather() 
        if round(time.time()%55) == 1:
            path = self.dir_allsky_1.text()+r'\allsky_picole.jpg'
            path2 = self.dir_allsky_2.text()+r'\allsky340c.jpg'
            is_allsky_on = self.allsky_handler.check_online(self.ftp_allsky_1.text())
            if is_allsky_on:
                self.detect_meteor(path)
            is_allsky2_on = self.allsky_handler.check_online(self.ftp_allsky_2.text())
            if is_allsky2_on:
                self.detect_meteor(path2)  
        self.update_image()
        self.main_status() 
        if self.weather_handle:
            weather_msg = self.weather_handle.stat_msg 
            self.txt_msg_extras_2.setText(weather_msg)  
        if self.backuper:            
            backuper_msg = self.backuper.stat_msg  
            self.txt_msg_extras.setText(backuper_msg)
        if self.goes:
            goes_msg = self.goes.stat_msg
            self.txt_msg_goes.setText(str(goes_msg)+'\n')
        if self.allsky_handler:
            allsky_msg = self.allsky_handler.stat_msg        
            self.txt_msg_allsky.setText(allsky_msg)        

        try:            
            if "Concluido" in goes_msg:
                self.goes_gif()               
            if self.goes:
                down_percent = self.goes.status_progress()
                self.progressBar.setValue(down_percent)
            
        except Exception as e:  
            self.txt_msg_goes.setText(str(e))     
        
    def start_timer(self):
        self.timer_update.timeout.connect(self.update_status)
        self.timer_update.stop()
        self.timer_update.start(1000)

    def closeEvent(self, event):
        """Close application"""
        close = QMessageBox()
        close.setText("Deseja salvar alterações?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        close = close.exec()

        if close == QMessageBox.Yes:   
            self.save_settings()         
            self.stop_goes() 
            self.stop_backuper()
            self.stop_weather()
            self.stop_allsky()
            event.accept()
        else:     
            self.stop_backuper()       
            self.stop_goes() 
            self.stop_weather()
            self.stop_allsky()
            event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()

    window.show()
    sys.exit(app.exec_())