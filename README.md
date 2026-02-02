_This project is for greenhouse controllers running off **raspberry pi's**_
The point of this project is to make gardening more simpler. 
Future: 
1. planning to add tunneling and making it main-stream
2. Adding More options/featurees
3. Better UI
   
You need to install **flask** via **pip install flask --break-system-packages** to get the web based server working.
Needed is also **w1thermsensor** by doing **pip install w1thermsensor --break-system-packages**
enable **1- wire**, **SPI** and **I2C** form **sudo raspi-config** under **Interface options**
And to execute use **sudo python3 app.py** or **sudo -E python app.py**
