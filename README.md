# BokehBioImageDataVis

## What is BokehBioImageDataVis?
BokehBioImageDataVis is a simple but very effective extension of the Bokeh visualization library to link numerical data with diverse media types (e.g. metadata, images, videos) for interactive data exploration and sharing in collaborative scientific research. The core interaction mechanism of the framework is an interactive scatterplot, where users can select and display numerical features or dimensionality reduction embeddings of their dataset. Hovering over scatter points displays media data linked to each data point.

<p align="center">
  <img src="https://github.com/JoeGreiner/BokehBioImageDataVis/assets/24453528/57d99753-c8d7-4ce4-bd87-c4ddcb01ceb3" alt="bokeh">
  <br>
  <em>Interactive scatterplot visualization from BokehBioImageDataVis demonstrating cardiomyocyte organelle segmentation.</em>
</p>

## 🏠 Table of Contents

* [Setup](#setup-)
* [Basic Use](#basic-use-)
* [Frequently Asked Questions (FAQ)](#faq-)

## Setup [🏠](#-table-of-contents)

0. Optional: Create a conda environment and activate it. 
```bash
conda create --name bokeh_vis python=3.9
conda activate bokeh_vis
```
1. Install BokehBioImageDataVis using pip.
```bash
pip install git+https://github.com/JoeGreiner/BokehBioImageDataVis.git
```

## Basic Use [🏠](#-table-of-contents)
### Code
0. Define dataframe with numeric data (x1, x2, x3) and media data paths. The paths can be relative or absolute, but have to link to existing files. If they link to non-existing files, a 'missing data' image will be displayed. In a real-world scenario, you would load your experimental results, and construct matching paths for each datapoint. Media (plots, figures, images, 3D renders, ...) need to be generated previously.
 
```python
import pandas as pd
data = pd.DataFrame({'x1': [1, 2, 3],
                     'x2': [1, 4, 16],
                     'x3': [1, 8, 64],
                     'path_to_images': ['data/pictures/cat1.jpg',
                                        'data/pictures/dog1.jpg',
                                        'data/pictures/dog2.jpg'],
                     'path_to_videos': ['data/videos/cat1.mp4',
                                        'data/videos/dog1.mp4',
                                        'data/videos/dog2.mp4']
                     })

# helper function that downloads example files
from BokehBioImageDataVis.src.utils import download_files_simple_example_1
download_files_simple_example_1()
```

1. Create Main BokehBioImageDataVis figure and scatter plot object.
```python
bokeh_fig = BokehBioImageDataVis(data, output_filename='example_simple_1/vis.html')
scatter_plot = bokeh_fig.create_scatter_figure()
```

2. Create image and video elements, and link them to the paths in the DataFrame by specifying their keys. Additionally, create a text element, that will display all available data for each datapoint in textform.
```python
img_hover = bokeh_fig.add_image_hover(key='path_to_images')
vid_hover = bokeh_fig.add_video_hover(key='path_to_videos')
text_hover = bokeh_fig.create_hover_text()
```

3. Compose the final layout.
```python
from bokeh.layouts import column, row

bokeh_fig.show_bokeh(
    row([
        column([scatter_plot, text_hover]),
        column([img_hover, vid_hover]),
    ])
)
```
### Expected Results
Running the code should open the website shown below. If the website does not automatically open, navigate to the output directory (here: 'example_simple_1', and open the website (here: 'vis.html'). The resulted website is portable, i.e., you can share them with others by sending around the output folder (you probably want to create an archive/zip to do so).

<p align="center">
  <img src="https://github.com/JoeGreiner/BokehBioImageDataVis/assets/24453528/93612315-b19b-4ac2-b58c-74172231bc05" alt="bokeh">
  <br>
  <em>Expected outcome of the basic usage example.</em>
</p>

## FAQ [🏠](#-table-of-contents)

* How do I generate (automated) visualisations?

This depends really on what you want to visualise, for many applications, matplotlib (2D figures) and ParaView (3D renders) are a great choice. Please do not hesitate to contact me if you're stuck here.

* I get 'missing data' symbols in my visualisation. Why?

The paths that you have specified do not exist, and therefore can't be linked. Make sure that the paths are correct. It does not matter if you use relative or absolute paths, the framework will copy all media to the output directory next to the website and link them relatively, so that the output folder can be moved to other computers with the links still working.

* How do I share a website?

Just share the whole output folder - the website will work seamlessly on different locations. Alternatively, you can also host the website online.

* I've shared the website with a collaborator, however, he doesn't see any media elements. Why?

I've realised that occacionally, when I send collaborators a visualisation as an archive, they don't unzip/extract the archive, but try to run the website from within the archive. Doing so will not show any media elements, as the paths are incorrect. If you send an archive/zip, people need to extract/unarchive the folder first before visiting the website. I now generate a textfile stating 'PLEASE_MAKE_SURE_IM_UNZIPPED.txt', I hope that helps to circumvent these issues :-)
