import os
import time
import datetime
import pipes
import zipfile
import backup.drive_uploader as uploader
import threading

class BackupDB(threading.Thread):
    def __init__(self, hour, host, user, password, db_name, bkp_folder):
        super().__init__()
        self.hour = hour
        self._stop_event = threading.Event()
        self.stat_msg = "Inicializando script backup DB"
        self.progress = 0
        self.DB_HOST = host 
        self.DB_USER = user
        self.DB_USER_PASSWORD = password
        self.DB_NAME = db_name
        self.BACKUP_DIR = bkp_folder
        self.flag = True
    
    def update_config(self, hour, host, user, password, db_name, bkp_folder):
        self.hour = hour
        self.DB_HOST = host 
        self.DB_USER = user
        self.DB_USER_PASSWORD = password
        self.DB_NAME = db_name
        self.BACKUP_DIR = bkp_folder.replace("\\", "/")
    
    def stop(self):
        self.flag = False
        self._stop_event.set()

    def zip_files(self, file_path, zip_name):
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:        
            zipf.write(file_path, os.path.basename(file_path))
    
    def do_work(self):
        self.progress = 0
        DATETIME = time.strftime('%Y%m%d-%H%M%S')
        TODAYBACKUPPATH = self.BACKUP_DIR + '/' + DATETIME
        
        # Checking if backup folder already exists or not. If not exists will create it.
        try:
            os.stat(TODAYBACKUPPATH)
        except:
            os.mkdir(TODAYBACKUPPATH)
                
        self.progress = 10
        
        # Code for checking if you want to take single database backup or assinged multiple backups in self.DB_NAME.
        self.stat_msg = "checking for databases names file."
        if os.path.exists(self.DB_NAME):            
            file1 = open(self.DB_NAME)
            multi = 1
            self.stat_msg = "Databases file found..."
            self.stat_msg = f"Starting backup of all dbs listed in file {self.DB_NAME}"
        else:
            self.stat_msg = "Databases file not found..."
            self.stat_msg =  f"Starting backup of database {self.DB_NAME}"
            multi = 0
        
        self.progress = 20
        # Starting actual database backup process.
        try:
            if multi:
                in_file = open(self.DB_NAME,"r")
                flength = len(in_file.readlines())
                in_file.close()
                p = 1
                dbfile = open(self.DB_NAME,"r")
                self.progress = 30
            
                while p <= flength:
                    db = dbfile.readline()   # reading database name from file
                    db = db[:-1]         # deletes extra line
                    dumpcmd = "mysqldump -h " + self.DB_HOST + " -u " + self.DB_USER + " -p" + self.DB_USER_PASSWORD + " " + db + " > " + pipes.quote(TODAYBACKUPPATH) + "/" + db + ".sql"
                    os.system(dumpcmd)
                    p = p + 1
                dbfile.close()
            else:
                db = self.DB_NAME
                dumpcmd = "mysqldump -h " + self.DB_HOST + " -u " + self.DB_USER + " -p" + self.DB_USER_PASSWORD + " " + db + " > " + pipes.quote(TODAYBACKUPPATH) + "/" + db + ".sql"
                os.system(dumpcmd)
            self.progress = 50
        except Exception as e:
            self.stat_msg = "Error: " + str(e)
        
        try:
            self.stat_msg = "Backup script completed"
            file_path = TODAYBACKUPPATH + '/observacoes.sql'
            self.zip_files(file_path, (TODAYBACKUPPATH+"/db_backup.zip"))
            self.progress = 80
            # uploader.upload_basic(TODAYBACKUPPATH+'/db_backup.zip')
        except Exception as e:
            self.stat_msg = "Erro no upload: " + str(e)
        self.progress = 100

    
    def run(self): 
        while self.flag:
            self.progress = 0
            hour = datetime.datetime.now().hour
            minutes = datetime.datetime.now().minute

            #backups DB every 20th day of the month, at 13:00pm
            if hour == 12 and minutes == 0 :
                self.do_work()
            self._stop_event.wait(timeout=60)
    