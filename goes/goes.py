import numpy as np
from datetime import datetime
import xarray
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import threading
import time
import os
import glob
from PIL import Image
import imageio.v2 as imageio

class Goes16Plot():
    def __init__(self):
        self.t_thread = None
        self.stat_msg = None
    
    def start_plot(self, file_path, date_file, gif_path):
        xd = file_path
        self.t_thread = threading.Thread(target = self.plot_goes, args=(xd, date_file, gif_path))
        self.t_thread.start()
        self.t_thread.join()
    
    def close_prog(self):
        self.t_thread.join()
    
    def contrast_correction(self, data_nc, color, contrast):
        """
        Modify the contrast of an RGB
        See: #www.dfstudios.co.uk/articles/programming/image-programming-algorithms/image-processing-algorithms-part-5-contrast-adjustment/

        Input:
            C - contrast level
        """
        data_nc = (259*(contrast + 255))/(255.*259-contrast)
        COLOR = data_nc*(color-.5)+.5
        COLOR = np.minimum(COLOR, 1)
        COLOR = np.maximum(COLOR, 0)
        return COLOR
        
    # Function to create a GIF from the stored images
    def create_gif(self, image_dir, gif_filename):
        images = []
        try:
            for file in sorted(glob.glob(os.path.join(image_dir, '*.png')))[-7:]:
                if "goes_16_" in file:
                    images.append((file))
            if len(images) >= 7:
                frames = [Image.open(image) for image in images]
                frame_one = frames[0]
                duration_list = [800] * (len(frames) - 1)  # Duration for all frames except the last one
                duration_list.append(3000)
                frame_one.save(gif_filename, format="GIF", append_images=frames[1:],
               save_all=True, duration=duration_list, loop=0)
                os.remove(images[0])
                return "Concluido: Gif criado."
        except Exception as e:
            return("Error gif:" + str(e))

    def plot_goes(self, file_path, date_file, gif_path):        
        data_nc = xarray.open_dataset(file_path)

        # Scan's start time, converted to datetime object
        scan_start = datetime.strptime(data_nc.time_coverage_start, "%Y-%m-%dT%H:%M:%S.%fZ")

        # I'm not a fan of numpy datetime, so I convert it to a regular datetime object
        midpoint = str(data_nc["t"].data)[:-8]
        scan_mid = datetime.strptime(midpoint, "%Y-%m-%dT%H:%M:%S.%f")

        # Satellite height
        sat_h = data_nc["goes_imager_projection"].perspective_point_height

        # Satellite longitude
        sat_lon = data_nc["goes_imager_projection"].longitude_of_projection_origin

        # Satellite sweep
        sat_sweep = data_nc["goes_imager_projection"].sweep_angle_axis

        # The projection x and y coordinates equals the scanning angle (in radians) multiplied by the satellite height
        # See details here: https://proj4.org/operations/projections/geos.html?highlight=geostationary
        x = data_nc["x"][:] * sat_h
        y = data_nc["y"][:] * sat_h

        m = Basemap(
            projection="geos",
            lon_0=sat_lon,
            resolution="i",
            area_thresh=100,
            rsphere=(6378137.00,6356752.3142),
            llcrnrx=x.min(),
            llcrnry=y.min(),
            urcrnrx=x.max(),
            urcrnry=y.max(),
        )

        plt.figure(figsize=[15, 12]) 
        
        if "M6C13" in file_path:
            channel = "CH: 13"
            m.imshow(np.flipud(data_nc['CMI'][:]), cmap='Greys')  # Since "images" are upside down, we flip the RGB up/down
        elif "M6C02" in file_path:
            channel = "CH: 02"
            m.imshow(np.flipud(data_nc['CMI'][:]), vmin=0, vmax=1, cmap='Greys_r')  # Since "images" are upside down, we flip the RGB up/down
        elif "MCMIPF" in file_path:
            # Load the RGB arrays
            R = data_nc['CMI_C02'][:].data
            G = data_nc['CMI_C03'][:].data
            B = data_nc['CMI_C01'][:].data

            # Apply range limits for each channel. RGB values must be between 0 and 1
            R = np.clip(R, 0, 1)
            G = np.clip(G, 0, 1)
            B = np.clip(B, 0, 1)

            # Apply the gamma correction
            gamma = 2.2
            R = np.power(R, 1/gamma)
            G = np.power(G, 1/gamma)
            B = np.power(B, 1/gamma)

            # Calculate the "True" Green
            G_true = 0.48358168 * R + 0.45706946 * B + 0.06038137 * G
            G_true = np.maximum(G_true, 0)
            G_true = np.minimum(G_true, 1)

            cleanIR = data_nc['CMI_C13'].data

            # Normalize the channel between a range. e.g. cleanIR = (cleanIR-minimum)/(maximum-minimum)
            cleanIR = (cleanIR-90)/(313-90)

            # Apply range limits for each channel. RGB values must be between 0 and 1
            cleanIR = np.clip(cleanIR, 0, 1)

            # Invert colors so that cold clouds are white
            cleanIR = 1 - cleanIR

            # Lessen the brightness of the coldest clouds so they don't appear so bright when we overlay it on the true color image
            cleanIR = cleanIR/1.4

            # Amount of contrast
            contrast_amount = 105
            # Apply contrast correction
            RGB_contrast = self.contrast_correction(data_nc, np.dstack([R, G_true, B]), contrast_amount)
            # Add in clean IR
            RGB_contrast_IR = np.dstack([np.maximum(RGB_contrast[:,:,0], cleanIR), np.maximum(RGB_contrast[:,:,1], cleanIR), np.maximum(RGB_contrast[:,:,2], cleanIR)])
            # The final RGB array :)
            # RGB = np.dstack([R, G_true, B])
            m.imshow(np.flipud(RGB_contrast_IR ))
            channel = "00"
        else:
            channel = ""
            m.imshow(np.flipud(data_nc['CMI'][:]), cmap='Greys')  # Since "images" are upside down, we flip the RGB up/down
            
        m.drawcoastlines(color='yellow', linewidth=.7)
        m.drawcountries(color='yellow')
        m.drawstates(color='yellow')
        lons = [-45.5825]
        lats = [-22.5344]

        x,y = m(lons, lats)
        pts = m.scatter(x, y, c ='r', marker = 'o', s = 85, alpha = .7)

        plt.title("GOES-16 | "+channel, loc="left", fontweight="semibold", fontsize=17, color='white')
        plt.title(date_file, loc="right", color='white', fontsize=17)
        # plt.xlim(6000000, 9800000)
        # plt.ylim(2200000,5500000)
        plt.xlim(7600000, 8800000)
        plt.ylim(2500000,3600000)
        plt.savefig(r'goes\goes_data\goes_16.png',dpi=50,bbox_inches='tight', pad_inches=0, transparent=True) # uncomment to save figure        
        timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
        plt.savefig(f'goes/goes_data/goes_16_{timestamp}.png',dpi=50,bbox_inches='tight', pad_inches=0, transparent=True)
        plt.clf()
        plt.close()
        self.stat_msg = self.create_gif(r'goes\goes_data', gif_path)

        

