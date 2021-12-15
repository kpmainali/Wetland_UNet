# Wetland_UNet
This repo provides complete script used for wetland mapping (delineation of boundaries) using UNet, an architecture developed out of deep-learning model. The input variables comprise of multiple bands of Sentinel-2 and of NAIP. We have also trained a more complex model that includes LiDAR and geomorphons.

## Data
The data used in this repo are in TFRecords format. The data was exported using Google Earth Engine in Google Colab environment.

## Script
The python script used to train UNet model are available in this repo.

## Model
The model we trained in Azure is available.

## Storymap
Electric Power Research Institute has developed a storymap out of this work. The storymap provides details of the data, method, model evaluation scores, types of models, etc. The storymap is availabe here: https://storymaps.arcgis.com/stories/4f98297b48a94efbbbe0199681539980

<img width="1727" alt="Screen Shot 2021-12-15 at 1 21 27 AM" src="https://user-images.githubusercontent.com/14167540/146134249-eb17f3af-237d-4222-9497-4579876cb769.png">


## Webapp
Our model output can be compared against wetland reference data. Conservation Innovation Center of Chesapeake Conservancy has developed a webapp where you can load various layers of input data of the model. The webapp is available here: https://cicgis.org/portal/apps/webappviewer/index.html?id=7bd206c0a2f0462ea6a821d9c4c2de68

<img width="1727" alt="Screen Shot 2021-12-15 at 1 08 39 AM" src="https://user-images.githubusercontent.com/14167540/146134083-209d1131-4f01-4643-99f7-25ac66b61cb2.png">


https://user-images.githubusercontent.com/14167540/146135300-963d7843-9150-4c9d-84d8-3d77f88a6af5.mov




https://user-images.githubusercontent.com/14167540/146135799-629dcb68-c258-4172-874f-9a351d488f6f.mov


