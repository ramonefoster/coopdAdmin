import boto3
from numpy import array, argmin, abs
from datetime import datetime
import os
from botocore import UNSIGNED            # boto3 config
from botocore.config import Config       # boto3 config
import threading
import goes.goes as goes
import time

class DownloadFile(threading.Thread):
    def __init__(self, satellite, band, dest_path, gif_path):
        super().__init__()
        self._stop_event = threading.Event()
        # set up access to aws server
        self.s3 = boto3.resource('s3')
        self.bucket_name = satellite
        self.bucket = self.s3.Bucket(self.bucket_name)
        self.product_name = 'ABI-L2-CMIPF'
        self.band = band
        self.done = 0
        self.dest_path = dest_path
        self.gif_path = gif_path
        self.stat_msg = None
        self.flag = True
    
    def stop(self):
        self.flag = False
        self._stop_event.set()
    
    def calc_utc_time(self):
        """Gets date in format: YYYYdoyHH"""
        current_date = datetime.utcnow()
        formatted_date = current_date.strftime("%Y%j%H")

        return formatted_date
    
    def status_msg(self):
        return (self.stat_msg)
    
    def status_progress(self):
        return self.done

    def run(self):
        goes_x = goes.Goes16Plot()

        while self.flag:
            band_x = 0  
            try:
                yyyydoyhh = self.calc_utc_time()
                # Initializes the S3 client
                s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
                if int(self.band)<10:
                    band_x = '0'+self.band
                else:
                    band_x = self.band
                # File structure
                #dps das 18hs (utc=21) muda para banda 13 (IR)
                if 8<float(yyyydoyhh[7:9])<21:
                    band_x = '02'
                    self.product_name = 'ABI-L2-MCMIPF'
                    prefix = f'{self.product_name}/{yyyydoyhh[0:4]}/{yyyydoyhh[4:7]}/{yyyydoyhh[7:9]}/OR_{self.product_name}-M6_G16_s{yyyydoyhh}'
                else:
                    band_x = '13'
                    self.product_name = 'ABI-L2-CMIPF'
                    prefix = f'{self.product_name}/{yyyydoyhh[0:4]}/{yyyydoyhh[4:7]}/{yyyydoyhh[7:9]}/OR_{self.product_name}-M6C{band_x}_G16_s{yyyydoyhh}'
                # Seach for the file on the server
                s3_result = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix, Delimiter = "/")
                path_dest = self.dest_path
                if 'Contents' not in s3_result: 
                    self.stat_msg = "Nenhum arquivo GOES novo no momento."        
                else:
                    # get last file
                    all = s3_result['Contents']        
                    latest = max(all, key=lambda x: x['LastModified'])
                    key = latest['Key']
                    
                    file_name = key.split('/')[-1].split('.')[0]   
                    meta_data = s3_client.head_object(Bucket=self.bucket_name, Key=key)
                    total_length = int(meta_data.get('ContentLength', 0))
                    downloaded = 0   

                    def progress(chunk):
                        nonlocal downloaded
                        downloaded += chunk
                        self.done = int(100 * downloaded / total_length)

                    # Download the file
                    if os.path.exists(f'{path_dest}/{file_name}.nc'):
                        self.stat_msg = "Arquivo GOES existente é o mais recente."
                    else:       
                        self.stat_msg = "Iniciando Download."                 
                        dir_name = path_dest
                        nc_old_files = os.listdir(dir_name)
                        for item in nc_old_files:
                            if ".nc" in item:
                                try:
                                    os.remove(os.path.join(dir_name, item))
                                except Exception as e:
                                    self.stat_msg = "Erro ao tentar remover arquivos GOES antigos."
                        try:
                            s3_client.download_file(self.bucket_name, key, f'{path_dest}/{file_name}.nc', Callback=progress)                        
                            path = ((f'{path_dest}/{file_name}.nc').replace("/", "\\"))
                            if self.done == 100:
                                self._stop_event.wait(timeout=1)
                                date_file = format(latest['LastModified'], '%Y-%m-%d %H:%M:%S')                                
                                goes_x.start_plot(path, date_file, self.gif_path)
                                if goes_x.stat_msg:
                                    self.stat_msg = goes_x.stat_msg
                                self._stop_event.wait(timeout=60)
                                goes_x.close_prog()
                                self.done=0
                        except Exception as e:
                            self.stat_msg = f"Erro: {str(e)}"
            except Exception as e:
                self.stat_msg = f"Problemas de conexão. Erro: {str(e)}"
            self._stop_event.wait(timeout=30)
