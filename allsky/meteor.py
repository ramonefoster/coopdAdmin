from keras.models import load_model # TensorFlow is required for Keras to work 
from PIL import Image, ImageOps     # Install pillow instead of PIL 
import numpy as np                  # Numpy provides numeric processing 
import shutil
import datetime                     # What time is it for solar altitude 

class MeteorDetection():
    def __init__(self):        
        np.set_printoptions(suppress=True) 

        # Load the model 
        self.model = load_model(r"config\keras_model.h5", compile=False) 

        # Load the labels 
        self.class_names = open(r"config\labels.txt", "r").readlines() 

        
        self.data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32) 

    def detect(self, path):
        # If the sun is up don't bother running the model 
        date = datetime.datetime.now() 
        date_str = date.timestamp()
        date_str = str(date_str)
        # Load the image from the AllSkyCam 
        image = Image.open(path).convert("RGB") 

        # resizing the image to be at least 224x224 cropped from the center 
        size = (224, 224) 
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS) 

        # turn the image into a numpy array 
        image_array = np.asarray(image) 

        # Normalize the image 
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1 

        # Load the image into the array 
        self.data[0] = normalized_image_array 

        # Run the image through the model 
        prediction = self.model.predict(self.data) 
        index = np.argmax(prediction) 
        class_name = self.class_names[index] 
        confidence_score = prediction[0][index] 

        new_file_path = "allsky/meteors" + "/Meteor-" + date_str + ".jpg"
        if index == 0 and confidence_score > 0.75:
            shutil.copyfile(path, new_file_path)

