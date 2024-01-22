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

import zmq
import json

pyQTfileName = "coopd.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(pyQTfileName)

class MyApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.get_settings_value()
        self.load_settings()
        self.timer_update = QTimer()

        #ZeroMQ
        self.ctx = zmq.Context()
        self.puller = self.ctx.socket(zmq.PULL)
        self.puller.bind("tcp://200.131.64.237:7006")
        self.poller = zmq.Poller()
        self.poller.register(self.puller, zmq.POLLIN)

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
    
    def recv_cmd_pull(self):
        socks = dict(self.poller.poll(50))
        if socks.get(self.puller) == zmq.POLLIN:
            msg_pull = self.puller.recv_string()
            try:
                msg_pull = json.loads(msg_pull)
                action = msg_pull.get("action")
                cmd = action.get("cmd")
                self._client_id = msg_pull.get("clientId") 
                if cmd == "STATUS":
                    self.weather_handle.public_weather()
            except:
                pass
    
    def get_settings_value(self):
        self.setting_variables = QSettings('coopd', 'variables')
    
    def save_settings(self):
        """GOES"""
        self.setting_variables.setValue("dir_goes_coopd", self.dir_goes_coopd.text())
        self.setting_variables.setValue("dir_down_goes", self.dir_down_goes.text())
        self.setting_variables.setValue("dir_goes_off", self.dir_goes_off.text())
        """BACKUP DB"""
        self.setting_variables.setValue("db_user", self.db_user.text())
        self.setting_variables.setValue("db_password", self.db_password.text())
        self.setting_variables.setValue("db_hour", self.db_hour.value())
        self.setting_variables.setValue("db_host", self.db_host.text())
        self.setting_variables.setValue("db_name", self.db_name.text())
        self.setting_variables.setValue("db_bkp_folder", self.db_bkp_folder.text())
        """FILE TCSPD WEATHER"""
        self.setting_variables.setValue("dest_weather_tcspd", self.dest_weather_tcspd.text())
        self.setting_variables.setValue("source_weather_tcspd", self.source_weather_tcspd.text())
        self.setting_variables.setValue("db_user_2", self.db_user_2.text())
        self.setting_variables.setValue("db_password_2", self.db_password_2.text())
        self.setting_variables.setValue("db_host_2", self.db_host_2.text())
        self.setting_variables.setValue("db_name_2", self.db_name_2.text())
        """ALLSKY 1"""
        self.setting_variables.setValue("ftp_allsky_1", self.ftp_allsky_1.text())
        self.setting_variables.setValue("dir_allsky_1", self.dir_allsky_1.text())
        self.setting_variables.setValue("img_off_1", self.img_off_1.text())
        self.setting_variables.setValue("angle_allsky_1", self.angle_allsky_1.value())
        """ALLSKY 2"""
        self.setting_variables.setValue("ftp_allsky_2", self.ftp_allsky_2.text())
        self.setting_variables.setValue("dir_allsky_2", self.dir_allsky_2.text())
        self.setting_variables.setValue("img_off_2", self.img_off_2.text())
        self.setting_variables.setValue("angle_allsky_2", self.angle_allsky_2.value())        
        self.setting_variables.setValue("check_skymap", self.check_skymap.isChecked())

    def load_settings(self):
        """GOES"""
        self.dir_goes_coopd.setText(self.setting_variables.value("dir_goes_coopd"))
        self.dir_down_goes.setText(self.setting_variables.value("dir_down_goes"))
        self.dir_goes_off.setText(self.setting_variables.value("dir_goes_off"))
        """BACKUP DB"""
        self.db_user.setText(self.setting_variables.value("db_user"))
        self.db_password.setText(self.setting_variables.value("db_password"))
        if self.setting_variables.value("db_hour"):
            self.db_hour.setValue(self.setting_variables.value("db_hour"))
        self.db_host.setText(self.setting_variables.value("db_host"))
        self.db_name.setText(self.setting_variables.value("db_name"))
        self.db_bkp_folder.setText(self.setting_variables.value("db_bkp_folder"))
        """FILE TCSPD WEATHER"""
        self.dest_weather_tcspd.setText(self.setting_variables.value("dest_weather_tcspd"))
        self.source_weather_tcspd.setText(self.setting_variables.value("source_weather_tcspd"))
        self.db_user_2.setText(self.setting_variables.value("db_user_2"))
        self.db_password_2.setText(self.setting_variables.value("db_password_2"))        
        self.db_host_2.setText(self.setting_variables.value("db_host_2"))
        self.db_name_2.setText(self.setting_variables.value("db_name_2"))
        """ALLSKY 1"""
        self.ftp_allsky_1.setText(self.setting_variables.value("ftp_allsky_1"))
        self.dir_allsky_1.setText(self.setting_variables.value("dir_allsky_1"))
        self.img_off_1.setText(self.setting_variables.value("img_off_1"))
        if self.setting_variables.value("angle_allsky_1"):
            self.angle_allsky_1.setValue(int(self.setting_variables.value("angle_allsky_1")))
        """ALLSKY 2"""
        self.ftp_allsky_2.setText(self.setting_variables.value("ftp_allsky_2"))
        self.dir_allsky_2.setText(self.setting_variables.value("dir_allsky_2"))
        self.img_off_2.setText(self.setting_variables.value("img_off_2"))
        if self.setting_variables.value("angle_allsky_2"):
            self.angle_allsky_2.setValue(int(self.setting_variables.value("angle_allsky_2")))
        if self.setting_variables.value("check_skymap") == 'True':
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
        self.weather_handle = ClimaTCSPD.GetWeather(source_file, dest_file, db_name, user, password, host, port)
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