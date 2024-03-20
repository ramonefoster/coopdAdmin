import os
import datetime, time
import shutil
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import allsky.constellations.skymap as SkyMap
import cv2

class AllskyWork(threading.Thread):
    def __init__(self, directory_to_watch, destination_directory, skymap, offline_file, directory_to_watch_2, destination_directory_2, offline_file_2):
        super().__init__()
        self._stop_event = threading.Event()
        self.event_handler = FileHandler(directory_to_watch, destination_directory, skymap)
        self.event_handler2 = FileHandler(directory_to_watch_2, destination_directory_2, skymap)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, directory_to_watch, recursive=True)
        self.observer.schedule(self.event_handler2, directory_to_watch_2, recursive=True)
        self.stat_msg = None
        self.destination_directory = destination_directory
        self.offline_file = offline_file
        self.offline_file_2 = offline_file_2
        self.flag = True
    
    def update(self, directory_to_watch1, directory_to_watch2, destination_directory):
        self.event_handler.update_directories(directory_to_watch1, destination_directory)
        self.event_handler2.update_directories(directory_to_watch2, destination_directory)
        self.stat_msg = "Directories updated."  

    def is_file_stale(self, file_path):
        modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        time_difference = current_time - modified_time
        time_difference_minutes = time_difference / 60
        return time_difference_minutes > 5

    def check_online(self, directory_path):
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if "AllSky" in file:
                    file_path = os.path.join(root, file)
                    if self.is_file_stale(file_path):
                        parent_folder = os.path.basename(os.path.dirname(file_path))
                        if "allsky340c" in parent_folder:
                            new_file_name = "allsky340c.jpg"
                            off = self.offline_file_2
                        else:
                            new_file_name = "allsky_picole.jpg"
                            off = self.offline_file
                        new_file_path = os.path.join(self.destination_directory, new_file_name)
                        if os.path.exists(off):
                            if self.stat_msg:
                                if "Offline" not in self.stat_msg:
                                    shutil.copyfile(off, new_file_path)
                            self.stat_msg = f"Imagem Allsky Offline movida."
                        return False
        return True 
    
    def run(self):
        self.observer.start()
        while self.flag:
            self.stat_msg = self.event_handler.stat_msg
            self._stop_event.wait(timeout=10)
    
    def stop(self):
        self.flag = False
        self._stop_event.set()
        self.observer.stop()
        self.observer.join()        

class FileHandler(FileSystemEventHandler):
    def __init__(self, directory_to_watch, destination_directory, skymap):
        self.directory_to_watch = directory_to_watch
        self.destination_directory = destination_directory
        self.stat_msg = None
        self.skymap = skymap    
    
    def generate_skymap(self, allsky_img):
        #path of original allsky image
        allsky_img = allsky_img
        #path of destination skymap image
        skymap_img = os.path.join(self.destination_directory, "allsky_picole.png")

        skyMap = SkyMap.SkyMap()
        skyMap.run(allsky_img, skymap_img)
    
    def update_directories(self, directory_to_watch, destination_directory):
        self.directory_to_watch = directory_to_watch
        self.destination_directory = destination_directory        

    def on_created(self, event):
        self.process(event)

    def on_modified(self, event):
        self.process(event)
    
    def enhance_img(self, img_path, destiny):
        img = cv2.imread(img_path)

        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=.7, tileGridSize=(10, 10))
        clahe_l = clahe.apply(l)

        enhanced_lab = cv2.merge((clahe_l, a, b))

        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        cv2.imwrite(destiny, enhanced_bgr)

    def process(self, event):
        if not event.is_directory:
            try:
                file_path = event.src_path
                file_name = os.path.basename(file_path)
                parent_folder = os.path.basename(os.path.dirname(file_path))
                if "allsky340c" in parent_folder:
                    if "AllSky" in file_name:
                        new_file_name = "allsky340c.jpg"  # Rename the file if desired
                        new_file_path = os.path.join(self.destination_directory, new_file_name)
                        shutil.copyfile(file_path, new_file_path)
                        self.enhance_img(new_file_path, new_file_path)
                        current_time = datetime.datetime.now()
                        formatted_time = current_time.strftime("%H:%M")
                        self.stat_msg = f"{formatted_time} Imagem Allsky340C movida. (mod)"
                        if self.skymap:
                            self.generate_skymap(new_file_path)
                else:
                    if "AllSky" in file_name:
                        new_file_name = "allsky_picole.jpg"  # Rename the file if desired
                        new_file_path = os.path.join(self.destination_directory, new_file_name)
                        shutil.copyfile(file_path, new_file_path)
                        self.enhance_img(new_file_path, new_file_path)
                        current_time = datetime.datetime.now()
                        formatted_time = current_time.strftime("%H:%M")
                        self.stat_msg = f"{formatted_time} Imagem Allsky movida. (mod)"
                        if self.skymap:
                            self.generate_skymap(new_file_path)
            except Exception as e:
                self.stat_msg = "Error Allsky: "+str(e)

